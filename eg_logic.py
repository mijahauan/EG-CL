# eg_logic.py
from __future__ import annotations
from eg_model import *
from typing import Set, Dict, List, Tuple, Union, Optional
import re
from collections import defaultdict
import itertools

class ClifParserError(ValueError):
    """Custom exception for errors encountered during CLIF parsing."""
    pass

class Subgraph:
    def __init__(self, elements: Set[Union[Predicate, Context, Ligature]]):
        if not elements: raise ValueError("Subgraph cannot be empty.")
        self.elements = elements
        self.root_context = self._find_root_context()

    def _find_root_context(self) -> Optional[Context]:
        outermost_level = float('inf'); root_ctx = None
        for element in self.elements:
            containing_context = self._get_element_context(element)
            if containing_context and containing_context.get_nesting_level() < outermost_level:
                outermost_level = containing_context.get_nesting_level(); root_ctx = containing_context
        return root_ctx

    def _get_element_context(self, element: Union[Predicate, Context, Ligature]) -> Optional[Context]:
        if isinstance(element, Ligature): return element.get_starting_context()
        if isinstance(element, Predicate): return element.context
        if isinstance(element, Context): return element.parent
        return None

class EGEditor:
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph
        self.validator = Validator(graph)
    def add_predicate(self, name: str, arity: int, context: Context, p_type: PredicateType = PredicateType.RELATION) -> Predicate:
        predicate = Predicate(name, arity, p_type); predicate.context = context
        context.predicates.append(predicate); return predicate
    def add_cut(self, parent_context: Context) -> Context:
        cut = Context(parent=parent_context); parent_context.children.append(cut); return cut
    def add_double_cut(self, context: Context) -> Context:
        outer_cut = self.add_cut(context); inner_cut = self.add_cut(outer_cut); return inner_cut
    def connect(self, hook1: Hook, hook2: Hook):
        lig1, lig2 = hook1.ligature, hook2.ligature
        if lig1 and lig2:
            if lig1.id == lig2.id: return
            if len(lig1.hooks) < len(lig2.hooks): lig1, lig2 = lig2, lig1
            for hook in list(lig2.hooks):
                hook.ligature = lig1
                lig1.hooks.add(hook)
        elif lig1:
            hook2.ligature = lig1
            lig1.hooks.add(hook2)
        elif lig2:
            hook1.ligature = lig2
            lig2.hooks.add(hook1)
        else:
            new_ligature = Ligature()
            hook1.ligature = new_ligature
            hook2.ligature = new_ligature
            new_ligature.hooks.add(hook1)
            new_ligature.hooks.add(hook2)

    def _copy_subgraph(self, source_subgraph: Subgraph, target_context: Context) -> Dict[str, Union[Predicate, Context]]:
        """
        Recursively copies a subgraph, including nested contexts, into a target context.
        Returns a map from old element IDs to the newly created elements.
        """
        id_map: Dict[str, Union[Predicate, Context]] = {}
        
        q: List[Tuple[Context, Context]] = [] 

        for element in source_subgraph.elements:
            if isinstance(element, Predicate) and element.context == source_subgraph.root_context:
                new_p = self.add_predicate(element.name, element.arity, target_context, element.type)
                id_map[element.id] = new_p

        for element in source_subgraph.elements:
            if isinstance(element, Context) and element.parent == source_subgraph.root_context:
                q.append((element, target_context))

        while q:
            source_ctx, target_parent_ctx = q.pop(0)
            
            new_ctx = self.add_cut(target_parent_ctx)
            id_map[source_ctx.id] = new_ctx

            for p_in_ctx in source_ctx.predicates:
                new_p = self.add_predicate(p_in_ctx.name, p_in_ctx.arity, new_ctx, p_in_ctx.type)
                id_map[p_in_ctx.id] = new_p

            for child_ctx in source_ctx.children:
                q.append((child_ctx, new_ctx))
                
        return id_map

    def iterate(self, source_subgraph: Subgraph, target_context: Context):
        if not Validator(self.graph).can_iterate(source_subgraph, target_context): raise ValueError("Invalid iteration.")
        id_map = self._copy_subgraph(source_subgraph, target_context)

        source_preds = {elem for elem in source_subgraph.elements if isinstance(elem, Predicate)}
        
        ligatures_in_source = set()
        for p in source_preds:
            for h in p.hooks:
                if h.ligature:
                    ligatures_in_source.add(h.ligature)

        for lig in ligatures_in_source:
            hooks_in_subgraph = [h for h in lig.hooks if h.predicate in source_preds]
            hooks_outside_subgraph = [h for h in lig.hooks if h.predicate not in source_preds]

            if not hooks_outside_subgraph:
                new_hooks = [id_map[h.predicate.id].hooks[h.index] for h in hooks_in_subgraph]
                if len(new_hooks) > 1:
                    for i in range(len(new_hooks) - 1): self.connect(new_hooks[i], new_hooks[i+1])
            else:
                for original_hook in hooks_in_subgraph:
                    if original_hook.predicate.id not in id_map: continue
                    new_predicate = id_map[original_hook.predicate.id]
                    new_hook = new_predicate.hooks[original_hook.index]
                    self.connect(new_hook, hooks_outside_subgraph[0])

    def deiterate(self, subgraph_to_erase: Subgraph):
        if not Validator(self.graph).can_deiterate(subgraph_to_erase): raise ValueError("Invalid de-iteration.")
        for element in list(subgraph_to_erase.elements):
            if isinstance(element, Predicate):
                for hook in element.hooks:
                    if hook.ligature: hook.ligature.hooks.discard(hook)
                if element.context: element.context.predicates.remove(element)
            elif isinstance(element, Context):
                if element.parent: element.parent.children.remove(element)

    def wrap_subgraph_with_double_cut(self, subgraph_to_wrap: Subgraph):
        if not Validator().can_add_double_cut(): raise ValueError("This operation should always be valid.")
        parent_context = subgraph_to_wrap.root_context
        if not parent_context: raise ValueError("Cannot wrap a subgraph that has no root context.")
        inner_cut = self.add_double_cut(parent_context)
        for element in list(subgraph_to_wrap.elements):
            if isinstance(element, Predicate):
                if element.context and element.context.id == parent_context.id:
                    parent_context.predicates.remove(element); inner_cut.predicates.append(element); element.context = inner_cut
            elif isinstance(element, Context):
                 if element.parent and element.parent.id == parent_context.id:
                    parent_context.children.remove(element); inner_cut.children.append(element); element.parent = inner_cut

    ## NEW ##
    def remove_double_cut(self, outer_cut: Context):
        """
        Removes a valid double cut, moving any contents of the inner cut
        to the parent context of the outer cut.
        """
        if not self.validator.can_remove_double_cut(outer_cut):
            raise ValueError("Invalid double cut removal operation.")
        
        parent_context = outer_cut.parent
        inner_cut = outer_cut.children[0]
        
        # Move all predicates from inner_cut to the parent_context
        for p in list(inner_cut.predicates):
            inner_cut.predicates.remove(p)
            parent_context.predicates.append(p)
            p.context = parent_context
            
        # Move all child contexts from inner_cut to the parent_context
        for c in list(inner_cut.children):
            inner_cut.children.remove(c)
            parent_context.children.append(c)
            c.parent = parent_context

        # Remove the now-empty outer_cut
        parent_context.children.remove(outer_cut)

    ## NEW ##
    def sever_at_hook(self, hook_to_detach: Hook):
        """
        Sever a line of identity at a specific hook. The hook is detached
        from its current ligature and placed on a new, distinct ligature.
        """
        original_ligature = hook_to_detach.ligature
        
        # It only makes sense to sever if the hook is part of a larger connection
        if not original_ligature or len(original_ligature.hooks) < 2:
            return # Or raise an error, but returning is safer.
            
        # Remove the hook from the original ligature
        original_ligature.hooks.remove(hook_to_detach)
        
        # Create a new ligature for the detached hook
        new_ligature = Ligature()
        hook_to_detach.ligature = new_ligature
        new_ligature.hooks.add(hook_to_detach)

    def erase_subgraph(self, subgraph_to_erase: Subgraph):
        if not self.validator.can_erase(subgraph_to_erase): raise ValueError("Invalid erase operation.")
        for element in list(subgraph_to_erase.elements):
            if isinstance(element, Predicate):
                for hook in element.hooks:
                    if hook.ligature:
                        hook.ligature.hooks.discard(hook)
                if element.context:
                    element.context.predicates.remove(element)
            elif isinstance(element, Context):
                if element.parent:
                    element.parent.children.remove(element)

    def apply_functional_property(self, p1: Predicate, p2: Predicate):
        if not self.validator.can_apply_functional_property(p1, p2): raise ValueError("Invalid Functional Property rule application.")
        output_hook1 = p1.hooks[-1]; output_hook2 = p2.hooks[-1]; self.connect(output_hook1, output_hook2)
    def apply_constant_identity(self, p1: Predicate, p2: Predicate):
        if not self.validator.can_apply_constant_identity(p1, p2): raise ValueError("Invalid Constant Identity rule application.")
        self.connect(p1.hooks[0], p2.hooks[0])

    def move_ligature_branch(self, hook_to_move: Hook, new_anchor_hook: Hook):
        if not self.validator.can_move_ligature_branch(hook_to_move, new_anchor_hook):
            raise ValueError("Invalid branch move operation.")
        
        original_ligature = hook_to_move.ligature
        
        if original_ligature:
            original_ligature.hooks.discard(hook_to_move)
        hook_to_move.ligature = None

        self.connect(hook_to_move, new_anchor_hook)
        
    def split_branching_point(self, ligature: Ligature, hooks_to_move: List[Hook], target_context: Context):
        print("NOTE: split_branching_point is a complex derived rule and is not fully implemented.")
        pass


class Validator:
    def __init__(self, graph: ExistentialGraph = None): self.graph = graph
    def can_insert(self, context: Context) -> bool: return context.is_negative()
    def can_remove_double_cut(self, outer_cut: Context) -> bool:
        # A double cut is removable if the outer cut is negative, has no predicates
        # of its own, and has exactly one child, which is the inner cut.
        if not outer_cut.is_negative(): return False
        if len(outer_cut.children) != 1: return False
        if outer_cut.predicates: return False
        return True
    def can_erase(self, subgraph_to_erase: Subgraph) -> bool:
        if not subgraph_to_erase or not subgraph_to_erase.root_context: return False
        return subgraph_to_erase.root_context.is_positive()
    def can_iterate(self, source_subgraph: Subgraph, target_context: Context) -> bool:
        source_context = source_subgraph.root_context
        if not source_context or not target_context: return False
        if target_context.get_nesting_level() <= source_context.get_nesting_level(): return False
        if any(elem.id == target_context.id for elem in source_subgraph.elements if isinstance(elem, Context)): return False
        return True
    def _get_subgraphs_on_area(self, context: Context) -> List[Subgraph]: return [Subgraph({p}) for p in context.predicates]
    
    def _get_connection_signature(self, p: Predicate, subgraph_preds: Set[Predicate], id_map: Dict[str, int]) -> tuple:
        sig = []
        for i, hook in enumerate(p.hooks):
            if not hook.ligature:
                sig.append(f"{i}:-")
                continue
            
            conn_details = []
            for other_hook in hook.ligature.hooks:
                if other_hook.id == hook.id: continue
                
                other_pred = other_hook.predicate
                if other_pred in subgraph_preds:
                    conn_details.append(f"INT:{id_map[other_pred.id]}:{other_hook.index}")
                else:
                    conn_details.append(f"EXT:{hook.ligature.id}")
            
            sig.append(f"{i}:{','.join(sorted(conn_details))}")
            
        return tuple(sorted(sig))

    def _are_isomorphic(self, g1: Subgraph, g2: Subgraph) -> bool:
        g1_preds = {p for p in g1.elements if isinstance(p, Predicate)}
        g2_preds = {p for p in g2.elements if isinstance(p, Predicate)}

        if len(g1_preds) != len(g2_preds):
            return False

        g1_pred_sigs = sorted([(p.name, p.arity, p.type) for p in g1_preds])
        g2_pred_sigs = sorted([(p.name, p.arity, p.type) for p in g2_preds])
        if g1_pred_sigs != g2_pred_sigs:
            return False

        g1_sorted_preds = sorted(list(g1_preds), key=lambda p: p.id)
        g2_sorted_preds = sorted(list(g2_preds), key=lambda p: p.id)
        g1_id_map = {p.id: i for i, p in enumerate(g1_sorted_preds)}
        g2_id_map = {p.id: i for i, p in enumerate(g2_sorted_preds)}

        g1_conn_sigs = {self._get_connection_signature(p, g1_preds, g1_id_map) for p in g1_preds}
        g2_conn_sigs = {self._get_connection_signature(p, g2_preds, g2_id_map) for p in g2_preds}

        return g1_conn_sigs == g2_conn_sigs

    def can_add_double_cut(self) -> bool: return True

    def can_deiterate(self, selection: Subgraph) -> bool:
        if not self.graph: raise ValueError("Validator needs a graph to check de-iteration.")
        if not selection.root_context or not selection.root_context.parent: return False
        
        search_context = selection.root_context.parent
        selection_preds = {p for p in selection.elements if isinstance(p, Predicate)}
        
        while search_context:
            potential_preds = [p for p in search_context.predicates]
            
            from itertools import combinations
            if len(potential_preds) >= len(selection_preds):
                for combo in combinations(potential_preds, len(selection_preds)):
                    candidate_subgraph = Subgraph(set(combo))
                    ligatures_to_add = set()
                    for p in combo:
                        for h in p.hooks:
                            if h.ligature:
                                ligatures_to_add.add(h.ligature)
                    candidate_subgraph.elements.update(ligatures_to_add)

                    if self._are_isomorphic(selection, candidate_subgraph):
                        return True
            
            search_context = search_context.parent
        return False

    def can_erase_isolated_constant(self, predicate: Predicate) -> bool:
        if predicate.type != PredicateType.CONSTANT: return False
        return not any(h.ligature for h in predicate.hooks)
    def can_apply_functional_property(self, p1: Predicate, p2: Predicate) -> bool:
        if not (p1.type == PredicateType.FUNCTION and p2.type == PredicateType.FUNCTION): return False
        if p1.name != p2.name or p1.arity != p2.arity: return False
        for i in range(p1.arity - 1):
            h1, h2 = p1.hooks[i], p2.hooks[i]
            if not (h1.ligature and h2.ligature and h1.ligature.id == h2.ligature.id): return False
        return True
    def can_apply_constant_identity(self, p1: Predicate, p2: Predicate) -> bool:
        if not (p1.type == PredicateType.CONSTANT and p2.type == PredicateType.CONSTANT): return False
        return p1.name == p2.name
    def can_move_ligature_branch(self, hook_to_move: Hook, new_anchor_hook: Hook) -> bool:
        if not hook_to_move.ligature or not new_anchor_hook.ligature: return False
        if hook_to_move.ligature.id != new_anchor_hook.ligature.id: return False
        ctx1 = hook_to_move.predicate.context
        ctx2 = new_anchor_hook.predicate.context
        return ctx1 and ctx2 and ctx1.id == ctx2.id

# ... (ClifTranslator and ClifParser remain the same) ...
class ClifTranslator:
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph
        self.ligature_map: Dict[str, str] = {}
        self.var_counter = 0

    def _get_new_var(self) -> str:
        self.var_counter += 1
        return f"x{self.var_counter}"

    def _get_all_ligatures(self) -> Set[Ligature]:
        ligatures: Set[Ligature] = set(); q: List[Context] = [self.graph.sheet_of_assertion]; visited = set()
        while q:
            context = q.pop(0)
            if context.id in visited: continue
            visited.add(context.id)
            for p in context.predicates:
                for h in p.hooks:
                    if h.ligature: ligatures.add(h.ligature)
            q.extend(context.children)
        return ligatures

    def _analyze_ligatures(self):
        all_ligatures = self._get_all_ligatures()
        
        def get_ligature_signature(lig: Ligature) -> str:
            if not lig.hooks: return ""
            hook_sigs = []
            for h in lig.hooks:
                p = h.predicate
                sig_tuple = (p.context.get_nesting_level(), p.name, p.arity, h.index, p.id)
                hook_sigs.append(str(sig_tuple))
            return "".join(sorted(hook_sigs))

        sorted_ligatures = sorted(list(all_ligatures), key=get_ligature_signature)

        for lig in sorted_ligatures:
            if lig.id in self.ligature_map: continue

            constant_name = None
            for hook in lig.hooks:
                if hook.predicate.type == PredicateType.CONSTANT:
                    constant_name = hook.predicate.name
                    break
            
            term_name = constant_name if constant_name else self._get_new_var()
            self.ligature_map[lig.id] = term_name

    def translate(self) -> str:
        self.ligature_map = {}
        self.var_counter = 0
        self._analyze_ligatures()
        return self._recursive_translate(self.graph.sheet_of_assertion)

    def _recursive_translate(self, context: Context) -> str:
        quantified_vars = set()
        all_ligs_in_graph = self._get_all_ligatures()

        for lig in all_ligs_in_graph:
            if lig.id in self.ligature_map and self.ligature_map[lig.id].startswith('x'):
                if lig.get_starting_context().id == context.id:
                    quantified_vars.add(self.ligature_map[lig.id])

        atoms = []
        for p in context.predicates:
            if p.type == PredicateType.CONSTANT: continue

            hook_terms = []
            for h in p.hooks:
                if h.ligature:
                    term = self.ligature_map.get(h.ligature.id)
                    if term: hook_terms.append(term)
            
            if len(hook_terms) != p.arity:
                continue

            if p.name == "=":
                if p.arity != 2: raise ValueError("Equality predicate must have arity of 2.")
                sorted_terms = sorted(hook_terms)
                atoms.append(f"(= {sorted_terms[0]} {sorted_terms[1]})")
            elif p.type == PredicateType.FUNCTION:
                if p.arity < 1: raise ValueError(f"Function {p.name} must have arity of at least 1.")
                output_term, input_terms = hook_terms[-1], hook_terms[:-1]
                args_str = f" {' '.join(input_terms)}" if input_terms else ""
                atoms.append(f"(= {output_term} ({p.name}{args_str}))")
            else: # RELATION
                args_str = f" {' '.join(hook_terms)}" if hook_terms else ""
                atoms.append(f"({p.name}{args_str})")

        child_translations = [f"(not {self._recursive_translate(child)})" for child in context.children]
        
        all_parts = sorted(atoms) + sorted(child_translations)
        
        content = ""
        if len(all_parts) > 1: content = f"(and {' '.join(all_parts)})"
        elif len(all_parts) == 1: content = all_parts[0]
        
        if quantified_vars:
            return f"(exists ({' '.join(sorted(list(quantified_vars)))}) {content or 'true'})"
        return content or "true"


class ClifParser:
    def _tokenize(self, clif_string: str) -> List[str]:
        return re.findall(r'\(|\)|[\w\d:.-]+|="?|"[^"]*"', clif_string)

    def _parse_s_expression(self, tokens: List[str]) -> Tuple[list, List[str]]:
        if not tokens: raise ClifParserError("Unexpected end of file while parsing.")
        token = tokens.pop(0)
        if token == '(':
            ast = []
            while tokens and tokens[0] != ')':
                sub_ast, remaining_tokens = self._parse_s_expression(tokens)
                ast.append(sub_ast)
                tokens = remaining_tokens
            if not tokens: raise ClifParserError("Unclosed parenthesis in CLIF string.")
            tokens.pop(0)
            return ast, tokens
        else: return token, tokens

    def parse(self, clif_string: str) -> ExistentialGraph:
        tokens = self._tokenize(clif_string)
        if not tokens: return ExistentialGraph()
        
        ast, remaining = self._parse_s_expression(tokens)
        if remaining:
            raise ClifParserError(f"Unexpected tokens after main expression: {remaining}")
        
        graph = ExistentialGraph()
        editor = EGEditor(graph)
        self._build_graph_from_ast(ast, editor, graph.sheet_of_assertion, {})
        return graph

    def _build_graph_from_ast(self, ast: list, editor: EGEditor, context: Context, var_map: Dict[str, Ligature]):
        if not isinstance(ast, list) or not ast: return

        operator = ast[0]
        
        try:
            if operator == 'exists':
                if len(ast) != 3 or not isinstance(ast[1], list):
                    raise ClifParserError(f"Malformed 'exists' expression: {ast}")
                child_var_map = var_map.copy()
                for var_name in ast[1]:
                    if var_name not in child_var_map: child_var_map[var_name] = Ligature()
                self._build_graph_from_ast(ast[2], editor, context, child_var_map)
            
            elif operator == 'not':
                if len(ast) != 2:
                    raise ClifParserError(f"Malformed 'not' expression: {ast}")
                new_cut = editor.add_cut(context)
                self._build_graph_from_ast(ast[1], editor, new_cut, var_map)

            elif operator == 'and':
                for conjunct in ast[1:]:
                    self._build_graph_from_ast(conjunct, editor, context, var_map)

            elif operator == '=':
                if len(ast) != 3:
                    raise ClifParserError(f"Malformed '=' expression: {ast}")
                term1, term2 = ast[1], ast[2]
                
                if isinstance(term1, list):
                    func_expr, output_term_name = term1, term2
                elif isinstance(term2, list):
                    func_expr, output_term_name = term2, term1
                else: 
                    term1_name, term2_name = sorted([term1, term2])
                    p_eq = editor.add_predicate("=", 2, context)
                    self._connect_term(editor, p_eq.hooks[0], term1_name, context, var_map)
                    self._connect_term(editor, p_eq.hooks[1], term2_name, context, var_map)
                    return

                func_name, input_term_names = func_expr[0], func_expr[1:]
                p_func = editor.add_predicate(func_name, len(input_term_names) + 1, context, p_type=PredicateType.FUNCTION)
                
                for i, term_name in enumerate(input_term_names):
                    self._connect_term(editor, p_func.hooks[i], term_name, context, var_map)

                self._connect_term(editor, p_func.hooks[-1], output_term_name, context, var_map)

            else: 
                pred_name, term_names = ast[0], ast[1:]
                pred = editor.add_predicate(pred_name, len(term_names), context)
                
                for i, term_name in enumerate(term_names):
                    self._connect_term(editor, pred.hooks[i], term_name, context, var_map)
        
        except (IndexError, TypeError) as e:
            raise ClifParserError(f"Failed to parse malformed AST element '{ast}': {e}") from e

    def connect_hook_to_ligature(self, hook: Hook, ligature: Ligature, editor: EGEditor):
        if hook.ligature:
            if hook.ligature.id != ligature.id:
                 if ligature.hooks:
                     editor.connect(hook, list(ligature.hooks)[0])
                 else:
                     hook.ligature.hooks.remove(hook)
                     hook.ligature = ligature
                     ligature.hooks.add(hook)
        else:
            hook.ligature = ligature
            ligature.hooks.add(hook)

    def _connect_term(self, editor: EGEditor, hook: Hook, term_name: str, context: Context, var_map: Dict[str, Ligature]):
        if term_name in var_map:
            ligature = var_map.setdefault(term_name, Ligature())
            self.connect_hook_to_ligature(hook, ligature, editor)
        else:
            p_const = editor.add_predicate(term_name, 1, context, p_type=PredicateType.CONSTANT)
            editor.connect(hook, p_const.hooks[0])