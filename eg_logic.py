# eg_logic.py
from eg_model import *
from typing import Set, Dict, List, Tuple, Union

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

class Validator:
    def __init__(self, graph: ExistentialGraph = None): self.graph = graph
    def can_insert(self, context: Context) -> bool: return context.get_nesting_level() % 2 != 0
    def can_erase(self, predicate: Predicate) -> bool: return predicate.context.get_nesting_level() % 2 == 0
    def can_remove_double_cut(self, outer_cut: Context) -> bool: return len(outer_cut.children) == 1 and not outer_cut.predicates
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
        starting_ligs = [lig for lig in self._get_all_ligatures() if lig.get_starting_context() == context and lig.id not in self.constant_map]
        quantified_vars = sorted([self.variable_map.get(lig.id) for lig in starting_ligs if lig.id in self.variable_map])
        predicate_atoms = []
        for p in context.predicates:
            if p.type == PredicateType.CONSTANT: continue
            hook_terms = []
            for h in p.hooks:
                if h.ligature:
                    term = self.constant_map.get(h.ligature.id, self.variable_map.get(h.ligature.id))
                    if term: hook_terms.append(term)
            if len(hook_terms) != p.arity: raise ValueError(f"Arity mismatch on {p.name}")
            args_str = f" {' '.join(hook_terms)}" if hook_terms else ""; predicate_atoms.append(f"({p.name}{args_str})")
        child_translations = [f"(not {self._recursive_translate(child)})" for child in context.children]
        all_parts = sorted(predicate_atoms) + sorted(child_translations)
        content = ""
        if len(all_parts) > 1: content = f"(and {' '.join(all_parts)})"
        elif len(all_parts) == 1: content = all_parts[0]
        if quantified_vars: return f"(exists ({' '.join(quantified_vars)}) {content})"
        return content if content else "true"

class ClifParser:
    """(Placeholder) Parses a CLIF string and builds an ExistentialGraph model."""
    def parse(self, clif_string: str) -> ExistentialGraph:
        print("\nNOTE: ClifParser.parse() is a placeholder.")
        return ExistentialGraph()