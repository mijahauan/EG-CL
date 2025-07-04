# eg_logic.py
from eg_model import *
from typing import Set, Dict, List, Tuple, Union

# --- Part 1: Subgraph Representation ---
class Subgraph:
    """Represents a selection of graph elements, validated to ensure it forms a coherent subgraph."""
    def __init__(self, elements: Set[Union[Predicate, Context, Ligature]]):
        if not elements:
            raise ValueError("Subgraph cannot be empty.")
        self.elements = elements
        self.root_context = self._find_root_context()

    def _find_root_context(self) -> Optional[Context]:
        """Finds the single outermost context containing all elements of the subgraph."""
        outermost_level = float('inf')
        root_ctx = None
        for element in self.elements:
            containing_context = self._get_element_context(element)
            if containing_context and containing_context.get_nesting_level() < outermost_level:
                outermost_level = containing_context.get_nesting_level()
                root_ctx = containing_context
        return root_ctx

    def _get_element_context(self, element: Union[Predicate, Context, Ligature]) -> Optional[Context]:
        """Helper to get the context that *contains* a given graph element."""
        if isinstance(element, Ligature):
            return element.get_starting_context()
        if isinstance(element, Predicate):
            return element.context
        if isinstance(element, Context):
            return element.parent
        return None

# --- Part 2: The Editor Logic ---
class EGEditor:
    """Provides a rich API to programmatically construct and transform an ExistentialGraph."""
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph

    def add_predicate(self, name: str, arity: int, context: Context) -> Predicate:
        predicate = Predicate(name, arity)
        predicate.context = context
        context.predicates.append(predicate)
        return predicate

    def add_cut(self, parent_context: Context) -> Context:
        cut = Context(parent=parent_context)
        parent_context.children.append(cut)
        return cut

    def add_double_cut(self, context: Context) -> Context:
        outer_cut = self.add_cut(context)
        inner_cut = self.add_cut(outer_cut)
        return inner_cut

    def connect(self, hook1: Hook, hook2: Hook):
        lig1, lig2 = hook1.ligature, hook2.ligature
        if lig1 and lig2:
            if lig1.id == lig2.id: return
            if len(lig1.hooks) < len(lig2.hooks): lig1, lig2 = lig2, lig1
            for hook in lig2.hooks:
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

    def _copy_subgraph(self, source_subgraph: Subgraph, target_context: Context) -> Tuple[Subgraph, Dict[str, Union[Predicate, Context, Ligature]]]:
        id_map: Dict[str, Union[Predicate, Context, Ligature]] = {}
        new_elements: Set[Union[Predicate, Context, Ligature]] = set()
        all_elements = list(source_subgraph.elements)
        for element in all_elements:
            if isinstance(element, Predicate):
                new_p = Predicate(element.name, element.arity, element.type)
                id_map[element.id] = new_p
                new_elements.add(new_p)
            elif isinstance(element, Context):
                new_c = Context()
                id_map[element.id] = new_c
                new_elements.add(new_c)
        for original_element in all_elements:
            if original_element.id not in id_map or not isinstance(original_element, (Predicate, Context)): continue
            new_element = id_map[original_element.id]
            original_parent = original_element.parent if isinstance(original_element, Context) else original_element.context
            new_parent = id_map.get(original_parent.id, target_context)
            if isinstance(new_element, Context):
                new_element.parent = new_parent
                new_parent.children.append(new_element)
            elif isinstance(new_element, Predicate):
                new_element.context = new_parent
                new_parent.predicates.append(new_element)
        ligatures_in_subgraph = {elem for elem in all_elements if isinstance(elem, Ligature)}
        for lig in ligatures_in_subgraph:
            is_internal = all(h.predicate.id in id_map for h in lig.hooks)
            if is_internal:
                new_lig = Ligature()
                id_map[lig.id] = new_lig
                new_elements.add(new_lig)
                for original_hook in lig.hooks:
                    new_predicate = id_map[original_hook.predicate.id]
                    new_hook = new_predicate.hooks[original_hook.index]
                    new_hook.ligature = new_lig
                    new_lig.hooks.add(new_hook)
        return Subgraph(new_elements), id_map

    def iterate(self, source_subgraph: Subgraph, target_context: Context) -> Subgraph:
        if not Validator(self.graph).can_iterate(source_subgraph, target_context):
            raise ValueError("Invalid iteration: Target context is not valid.")
        copied_subgraph, id_map = self._copy_subgraph(source_subgraph, target_context)
        ligatures_in_source = {elem for elem in source_subgraph.elements if isinstance(elem, Ligature)}
        for lig in ligatures_in_source:
            if lig.id not in id_map:
                for original_hook in lig.hooks:
                    if original_hook.predicate.id in id_map:
                        new_predicate = id_map[original_hook.predicate.id]
                        new_hook = new_predicate.hooks[original_hook.index]
                        self.connect(original_hook, new_hook)
        return copied_subgraph

    def deiterate(self, subgraph_to_erase: Subgraph):
        """Erases a subgraph after validation confirms it is a redundant copy."""
        if not Validator(self.graph).can_deiterate(subgraph_to_erase):
            raise ValueError("Invalid de-iteration: The selection is not a valid redundant copy.")
        
        all_hooks = {h for p in subgraph_to_erase.elements if isinstance(p, Predicate) for h in p.hooks}
        for hook in all_hooks:
            if hook.ligature:
                hook.ligature.hooks.discard(hook)
                hook.ligature = None

        for element in list(subgraph_to_erase.elements):
            if isinstance(element, Predicate):
                if element.context and element in element.context.predicates:
                    element.context.predicates.remove(element)
            elif isinstance(element, Context):
                if element.parent and element in element.parent.children:
                    element.parent.children.remove(element)

# --- Part 3: The Validator Logic ---
class Validator:
    def __init__(self, graph: ExistentialGraph = None):
        self.graph = graph

    def can_insert(self, context: Context) -> bool:
        return context.get_nesting_level() % 2 != 0

    def can_erase(self, element: Union[Predicate, Ligature]) -> bool:
        if isinstance(element, Predicate): return element.context.get_nesting_level() % 2 == 0
        if isinstance(element, Ligature): return element.get_starting_context().get_nesting_level() % 2 == 0
        return False

    def can_remove_double_cut(self, outer_cut: Context) -> bool:
        if len(outer_cut.children) != 1 or outer_cut.predicates: return False
        return True

    def can_iterate(self, source_subgraph: Subgraph, target_context: Context) -> bool:
        source_context = source_subgraph.root_context
        if not source_context or not target_context: return False
        if target_context.get_nesting_level() < source_context.get_nesting_level(): return False
        if any(elem.id == target_context.id for elem in source_subgraph.elements if isinstance(elem, Context)): return False
        return True

    def _get_subgraphs_on_area(self, context: Context) -> List[Subgraph]:
        """(Helper) Finds all single-predicate subgraphs on a given context's area."""
        return [Subgraph({p}) for p in context.predicates]

    def _are_isomorphic(self, g1: Subgraph, g2: Subgraph) -> bool:
        """(Helper) A simplified check for structural isomorphism."""
        g1_preds = {p for p in g1.elements if isinstance(p, Predicate)}
        g2_preds = {p for p in g2.elements if isinstance(p, Predicate)}
        if len(g1_preds) != len(g2_preds): return False
        g1_sigs = sorted([(p.name, p.arity) for p in g1_preds])
        g2_sigs = sorted([(p.name, p.arity) for p in g2_preds])
        return g1_sigs == g2_sigs

    def can_deiterate(self, selection: Subgraph) -> bool:
        """Corrected logic: Checks if a selection is a valid copy."""
        if not self.graph:
             raise ValueError("Validator must be initialized with a graph to check de-iteration.")
        if not selection.root_context or not selection.root_context.parent:
            return False

        # Start search for an original in the parent context and move outwards.
        search_context = selection.root_context.parent
        while search_context:
            potential_originals = self._get_subgraphs_on_area(search_context)
            for original in potential_originals:
                if self._are_isomorphic(selection, original):
                    # NOTE: A full check would also validate the connecting ligatures.
                    return True
            search_context = search_context.parent
        return False

# --- Part 4: The Translation Logic ---
class ClifTranslator:
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph
        self.variable_map: Dict[str, str] = {}
    def translate(self) -> str:
        all_ligatures = self._get_all_ligatures()
        def get_ligature_sort_key(ligature: Ligature) -> tuple:
            if not ligature.hooks: return tuple()
            return tuple(sorted((h.predicate.name, h.index) for h in ligature.hooks))
        sorted_ligatures = sorted(list(all_ligatures), key=get_ligature_sort_key)
        for i, ligature in enumerate(sorted_ligatures):
            self.variable_map[ligature.id] = f"x{i+1}"
        return self._recursive_translate(self.graph.sheet_of_assertion)
    def _get_all_ligatures(self) -> Set[Ligature]:
        ligatures: Set[Ligature] = set()
        contexts_to_visit: List[Context] = [self.graph.sheet_of_assertion]
        visited_contexts: Set[str] = set()
        while contexts_to_visit:
            context = contexts_to_visit.pop(0)
            if context.id in visited_contexts: continue
            visited_contexts.add(context.id)
            for p in context.predicates:
                for h in p.hooks:
                    if h.ligature: ligatures.add(h.ligature)
            contexts_to_visit.extend(context.children)
        return ligatures
    def _recursive_translate(self, context: Context) -> str:
        all_ligs = self._get_all_ligatures()
        starting_ligs = [lig for lig in all_ligs if lig.get_starting_context() == context]
        quantified_vars = sorted([self.variable_map[lig.id] for lig in starting_ligs])
        predicate_atoms = []
        for p in context.predicates:
            hook_vars = [self.variable_map[h.ligature.id] for h in p.hooks if h.ligature]
            if len(hook_vars) != p.arity: raise ValueError(f"Arity mismatch on {p.name}")
            args_str = f" {' '.join(hook_vars)}" if hook_vars else ""
            predicate_atoms.append(f"({p.name}{args_str})")
        child_translations = [f"(not {self._recursive_translate(child)})" for child in context.children]
        all_parts = sorted(predicate_atoms) + sorted(child_translations)
        content = ""
        if len(all_parts) > 1: content = f"(and {' '.join(all_parts)})"
        elif len(all_parts) == 1: content = all_parts[0]
        if quantified_vars: return f"(exists ({' '.join(quantified_vars)}) {content})"
        return content if content else "true"

class ClifParser:
    def parse(self, clif_string: str) -> ExistentialGraph:
        print("\nNOTE: ClifParser.parse() is a placeholder for reverse translation.")
        return ExistentialGraph()