# eg_logic.py
from eg_model import *
from typing import Set, Dict, List, Tuple, Union
import re

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
            for hook in list(lig2.hooks): hook.ligature = lig1; lig1.hooks.add(hook)
        elif lig1: hook2.ligature = lig1; lig1.hooks.add(hook2)
        elif lig2: hook1.ligature = lig2; lig2.hooks.add(hook1)
        else:
            new_ligature = Ligature(); hook1.ligature = new_ligature
            hook2.ligature = new_ligature; new_ligature.hooks.add(hook1)
            new_ligature.hooks.add(hook2)
    def _copy_subgraph(self, source_subgraph: Subgraph, target_context: Context) -> Dict[str, Union[Predicate, Context]]:
        id_map: Dict[str, Union[Predicate, Context]] = {};
        for element in source_subgraph.elements:
            if isinstance(element, Predicate):
                new_p = self.add_predicate(element.name, element.arity, target_context, element.type)
                id_map[element.id] = new_p
        return id_map
    def iterate(self, source_subgraph: Subgraph, target_context: Context):
        if not Validator(self.graph).can_iterate(source_subgraph, target_context): raise ValueError("Invalid iteration.")
        id_map = self._copy_subgraph(source_subgraph, target_context)
        ligatures_in_source = {elem for elem in source_subgraph.elements if isinstance(elem, Ligature)}
        for lig in ligatures_in_source:
            hooks_in_subgraph = [h for h in lig.hooks if h.predicate.id in id_map]
            if len(hooks_in_subgraph) == len(lig.hooks):
                new_hooks = [id_map[h.predicate.id].hooks[h.index] for h in hooks_in_subgraph]
                if len(new_hooks) > 1:
                    for i in range(len(new_hooks) - 1): self.connect(new_hooks[i], new_hooks[i+1])
            else:
                for hook in list(lig.hooks):
                    if hook.predicate.id in id_map:
                        new_predicate = id_map[hook.predicate.id]
                        new_hook = new_predicate.hooks[hook.index]
                        self.connect(hook, new_hook)
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
        """Wraps an existing subgraph with a new double cut."""
        if not Validator().can_add_double_cut():
            # This check is trivial and always true, but good practice.
            raise ValueError("This operation should always be valid.")

        parent_context = subgraph_to_wrap.root_context
        if not parent_context:
            # Cannot wrap a subgraph that doesn't exist in a context (e.g., the whole SoA).
            raise ValueError("Cannot wrap a subgraph that has no root context.")
        
        # Create the new double cut within the subgraph's original context.
        inner_cut = self.add_double_cut(parent_context)
        
        # Re-parent the root elements of the subgraph to the new inner cut.
        # Iterate over a copy of the elements, as we will be modifying the original lists.
        for element in list(subgraph_to_wrap.elements):
            # Check if this element is a direct child of the subgraph's root context.
            if isinstance(element, Predicate):
                if element.context and element.context.id == parent_context.id:
                    parent_context.predicates.remove(element)
                    inner_cut.predicates.append(element)
                    element.context = inner_cut
            elif isinstance(element, Context):
                 if element.parent and element.parent.id == parent_context.id:
                    parent_context.children.remove(element)
                    inner_cut.children.append(element)
                    element.parent = inner_cut
    def erase_subgraph(self, subgraph_to_erase: Subgraph):
        """Erases all elements of a validated subgraph from the model."""
        if not self.validator.can_erase(subgraph_to_erase):
            raise ValueError("Invalid erase operation.")

        for element in list(subgraph_to_erase.elements):
            if isinstance(element, Predicate):
                # Disconnect all hooks of the predicate first
                for hook in element.hooks:
                    if hook.ligature:
                        hook.ligature.hooks.discard(hook)
                # Remove predicate from its context
                if element.context:
                    element.context.predicates.remove(element)
            elif isinstance(element, Context):
                # Remove cut from its parent
                if element.parent:
                    element.parent.children.remove(element)
    def apply_functional_property(self, p1: Predicate, p2: Predicate):
        """
        Applies the Functional Property Rule by connecting the output hooks
        of two function predicates that have identical inputs.
        [cite_start]This asserts that their outputs are identical. [cite: 548-549]
        """
        if not self.validator.can_apply_functional_property(p1, p2):
            raise ValueError("Invalid Functional Property rule application.")
        
        # The last hook of a function is its output.
        output_hook1 = p1.hooks[-1]
        output_hook2 = p2.hooks[-1]
        self.connect(output_hook1, output_hook2)
        print(f"  - Applied Functional Property Rule: Connected outputs of '{p1.name}'.")

    def apply_constant_identity(self, p1: Predicate, p2: Predicate):
        """
        Applies the Constant Identity Rule by connecting the hooks of two
        identical constant predicates. [cite_start]This asserts their identity. [cite: 4909]
        """
        if not self.validator.can_apply_constant_identity(p1, p2):
            raise ValueError("Invalid Constant Identity rule application.")

        # Constants have an arity of 1, so they have one hook.
        self.connect(p1.hooks[0], p2.hooks[0])
        print(f"  - Applied Constant Identity Rule: Connected two instances of '{p1.name}'.")

class Validator:
    def __init__(self, graph: ExistentialGraph = None): self.graph = graph
    def can_insert(self, context: Context) -> bool: return context.get_nesting_level() % 2 != 0
    def can_remove_double_cut(self, outer_cut: Context) -> bool: return len(outer_cut.children) == 1 and not outer_cut.predicates
    def can_erase(self, subgraph_to_erase: Subgraph) -> bool:
        """
        Checks if a subgraph can be erased. Allowed only if the subgraph as a whole
        [cite_start]resides in a positive (evenly enclosed) context [cite: 3223-3224].
        """
        if not subgraph_to_erase or not subgraph_to_erase.root_context:
            return False
        return subgraph_to_erase.root_context.get_nesting_level() % 2 == 0
    def can_iterate(self, source_subgraph: Subgraph, target_context: Context) -> bool:
        source_context = source_subgraph.root_context
        if not source_context or not target_context: return False
        if target_context.get_nesting_level() < source_context.get_nesting_level(): return False
        if any(elem.id == target_context.id for elem in source_subgraph.elements if isinstance(elem, Context)): return False
        return True
    def _get_subgraphs_on_area(self, context: Context) -> List[Subgraph]: return [Subgraph({p}) for p in context.predicates]
    def _are_isomorphic(self, g1: Subgraph, g2: Subgraph) -> bool:
        g1_preds = {p for p in g1.elements if isinstance(p, Predicate)}; g2_preds = {p for p in g2.elements if isinstance(p, Predicate)}
        if len(g1_preds) != len(g2_preds): return False
        g1_sigs = sorted([(p.name, p.arity, p.type) for p in g1_preds]); g2_sigs = sorted([(p.name, p.arity, p.type) for p in g2_preds])
        return g1_sigs == g2_sigs
    def can_add_double_cut(self) -> bool:
        """Confirms that adding a double cut is always a valid operation."""
        return True
    def can_deiterate(self, selection: Subgraph) -> bool:
        if not self.graph: raise ValueError("Validator needs a graph to check de-iteration.")
        if not selection.root_context or not selection.root_context.parent: return False
        search_context = selection.root_context.parent
        while search_context:
            for original in self._get_subgraphs_on_area(search_context):
                if self._are_isomorphic(selection, original): return True
            search_context = search_context.parent
        return False
    def can_erase_isolated_constant(self, predicate: Predicate) -> bool:
        if predicate.type != PredicateType.CONSTANT: return False
        return not any(h.ligature for h in predicate.hooks)
    def can_apply_functional_property(self, p1: Predicate, p2: Predicate) -> bool:
        """Checks if two function applications have identical inputs."""
        if not (p1.type == PredicateType.FUNCTION and p2.type == PredicateType.FUNCTION): return False
        if p1.name != p2.name or p1.arity != p2.arity: return False
        
        # Check if all input hooks are connected to the same ligatures
        # The last hook is the output, so we check up to arity - 1.
        for i in range(p1.arity - 1):
            h1 = p1.hooks[i]
            h2 = p2.hooks[i]
            # Both hooks must be connected, and to the same ligature
            if not (h1.ligature and h2.ligature and h1.ligature.id == h2.ligature.id):
                return False
        return True
    def can_apply_constant_identity(self, p1: Predicate, p2: Predicate) -> bool:
        """
        Checks if the Constant Identity rule can be applied.
        This rule allows asserting identity between two instances of the same constant.
        [cite_start][cite: 5885, 4909]
        """
        if not (p1.type == PredicateType.CONSTANT and p2.type == PredicateType.CONSTANT):
            return False
        if p1.name == p2.name:
            return True
        return False

class ClifTranslator:
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph; self.variable_map: Dict[str, str] = {}; self.constant_map: Dict[str, str] = {}
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
    def translate(self) -> str:
        all_ligatures = self._get_all_ligatures()
        for lig in all_ligatures:
            for hook in lig.hooks:
                if hook.predicate.type == PredicateType.CONSTANT:
                    self.constant_map[lig.id] = hook.predicate.name; break
        var_ligatures = [lig for lig in all_ligatures if lig.id not in self.constant_map]
        def get_ligature_sort_key(ligature: Ligature) -> tuple:
            if not ligature.hooks: return tuple()
            return tuple(sorted((h.predicate.name, h.index) for h in ligature.hooks))
        sorted_ligatures = sorted(list(var_ligatures), key=get_ligature_sort_key)
        for i, ligature in enumerate(sorted_ligatures): self.variable_map[ligature.id] = f"x{i+1}"
        return self._recursive_translate(self.graph.sheet_of_assertion)
    def _recursive_translate(self, context: Context) -> str:
        """Recursively translates a context and its contents into a CLIF substring."""
        # This helper needs access to the instance's variable_map and constant_map
        all_ligs = self._get_all_ligatures()
        
        starting_ligs = [
            lig for lig in all_ligs 
            if lig.get_starting_context() == context and lig.id not in self.constant_map
        ]
        quantified_vars = sorted([self.variable_map.get(lig.id) for lig in starting_ligs if lig.id in self.variable_map])

        atoms = []
        for p in context.predicates:
            if p.type == PredicateType.CONSTANT:
                continue

            hook_terms = []
            for h in p.hooks:
                if h.ligature:
                    term = self.constant_map.get(h.ligature.id, self.variable_map.get(h.ligature.id))
                    if term:
                        hook_terms.append(term)
            
            if len(hook_terms) != p.arity:
                raise ValueError(f"Arity mismatch on predicate '{p.name}'")

            # --- NEW LOGIC FOR EQUALITY ---
            if p.name == "=":
                if p.arity != 2:
                    raise ValueError("Equality predicate must have arity of 2.")
                atoms.append(f"(= {hook_terms[0]} {hook_terms[1]})")
            # --- END NEW LOGIC ---
            elif p.type == PredicateType.FUNCTION:
                # An n-ary function has n-1 inputs and 1 output (the last hook)
                if p.arity < 1:
                    raise ValueError(f"Function {p.name} must have arity of at least 1.")
                
                output_term = hook_terms[-1]
                input_terms = hook_terms[:-1]
                args_str = f" {' '.join(input_terms)}" if input_terms else ""
                # Format as: (= <output> (<function_name> <inputs>...))
                atoms.append(f"(= {output_term} ({p.name}{args_str}))")
            else: # It's a RELATION
                args_str = f" {' '.join(hook_terms)}" if hook_terms else ""
                atoms.append(f"({p.name}{args_str})")

        child_translations = [f"(not {self._recursive_translate(child)})" for child in context.children]
        all_parts = sorted(atoms) + sorted(child_translations)
        
        content = ""
        if len(all_parts) > 1: content = f"(and {' '.join(all_parts)})"
        elif len(all_parts) == 1: content = all_parts[0]
        
        if quantified_vars: return f"(exists ({' '.join(quantified_vars)}) {content})"
        return content if content else "true"

# This new class replaces the old placeholder at the end of eg_logic.py

class ClifParser:
    """Parses a CLIF string and builds an ExistentialGraph model."""

    def _tokenize(self, clif_string: str) -> List[str]:
        """A simple lexer to split a CLIF string into tokens."""
        return re.findall(r'\(|\)|[\w\d:-]+|="?|"[^"]*"', clif_string)

    def _parse_s_expression(self, tokens: List[str]) -> Tuple[list, List[str]]:
        """Recursively parses a flat list of tokens into a nested list (S-expression)."""
        if not tokens:
            raise ValueError("Unexpected EOF while parsing")
        
        token = tokens.pop(0)
        if token == '(':
            ast = []
            while tokens[0] != ')':
                sub_ast, remaining_tokens = self._parse_s_expression(tokens)
                ast.append(sub_ast)
                tokens = remaining_tokens
            tokens.pop(0) # Pop off ')'
            return ast, tokens
        else:
            return token, tokens

    def parse(self, clif_string: str) -> ExistentialGraph:
        """Top-level method to parse a CLIF string into a full EG model."""
        tokens = self._tokenize(clif_string)
        if not tokens:
            return ExistentialGraph() # Return empty graph for empty string
        
        ast, _ = self._parse_s_expression(tokens)
        
        graph = ExistentialGraph()
        editor = EGEditor(graph)
        self._build_graph_from_ast(ast, editor, graph.sheet_of_assertion, {})
        return graph

    def _build_graph_from_ast(self, ast: list, editor: EGEditor, context: Context, var_map: Dict[str, Ligature]):
        """Recursively builds the EG data model from a CLIF AST."""
        if not isinstance(ast, list) or not ast:
            return

        operator = ast[0]
        
        if operator == 'exists':
            # Create new ligatures for quantified variables
            for var_name in ast[1]:
                var_map[var_name] = Ligature()
            self._build_graph_from_ast(ast[2], editor, context, var_map)
        
        elif operator == 'not':
            new_cut = editor.add_cut(context)
            self._build_graph_from_ast(ast[1], editor, new_cut, var_map)

        elif operator == 'and':
            for conjunct in ast[1:]:
                self._build_graph_from_ast(conjunct, editor, context, var_map)

        elif operator == '=':
            # This is a function definition, e.g., ['=', 'y1', ['add', 'x1', '7']]
            output_term_name = ast[1]
            func_expr = ast[2]
            func_name = func_expr[0]
            input_term_names = func_expr[1:]
            
            # Arity is inputs + 1 for the output
            p_func = editor.add_predicate(func_name, len(input_term_names) + 1, context, p_type=PredicateType.FUNCTION)
            
            # Connect input hooks
            for i, term_name in enumerate(input_term_names):
                if term_name not in var_map: # It's a constant
                     p_const = editor.add_predicate(term_name, 1, context, p_type=PredicateType.CONSTANT)
                     editor.connect(p_func.hooks[i], p_const.hooks[0])
                else: # It's a variable
                    editor.connect(p_func.hooks[i], p_func.hooks[i]) # Create a placeholder hook connection
                    p_func.hooks[i].ligature = var_map[term_name]
                    var_map[term_name].hooks.add(p_func.hooks[i])
            
            # Connect output hook
            output_ligature = var_map.get(output_term_name)
            if not output_ligature:
                output_ligature = Ligature()
                var_map[output_term_name] = output_ligature
            editor.connect(p_func.hooks[-1], p_func.hooks[-1])
            p_func.hooks[-1].ligature = output_ligature
            output_ligature.hooks.add(p_func.hooks[-1])

        else: # It's a relation atom, e.g., ['cat', 'x1']
            pred_name = ast[0]
            term_names = ast[1:]
            
            pred = editor.add_predicate(pred_name, len(term_names), context)
            
            for i, term_name in enumerate(term_names):
                if term_name not in var_map: # It's a constant
                     p_const = editor.add_predicate(term_name, 1, context, p_type=PredicateType.CONSTANT)
                     editor.connect(pred.hooks[i], p_const.hooks[0])
                else: # It's a variable
                    ligature = var_map[term_name]
                    editor.connect(pred.hooks[i], pred.hooks[i]) # Create placeholder connection
                    pred.hooks[i].ligature = ligature
                    ligature.hooks.add(pred.hooks[i])