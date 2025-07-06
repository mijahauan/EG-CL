# eg_logic.py
from __future__ import annotations
from eg_model import *
from session_model import Action
from typing import Set, Dict, List, Tuple, Union, Any, Optional
import re
from collections import defaultdict

class ClifParserError(ValueError):
    pass

class EGEditor:
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph

    def add_predicate(self, name: str, arity: int, parent_cut_id: str, p_type: str = "relation") -> Tuple[str, Action]:
        parent_cut = self.graph.get_object(parent_cut_id)
        if parent_cut.node_type != GraphObjectType.CUT:
            raise ValueError("Predicates can only be added to cuts.")
        props = {"name": name, "arity": arity, "type": p_type}
        node = Node(GraphObjectType.PREDICATE, properties=props)
        self.graph.objects[node.id] = node
        parent_cut.contents.append(node.id)
        action = Action('add_predicate', {'parent_id': parent_cut_id, 'new_id': node.id, 'name': name, 'arity': arity, 'p_type': p_type})
        return node.id, action

    def add_cut(self, parent_cut_id: str) -> Tuple[str, Action]:
        parent_cut = self.graph.get_object(parent_cut_id)
        if parent_cut.node_type != GraphObjectType.CUT:
            raise ValueError("Cuts can only be added inside other cuts.")
        cut_node = Node(GraphObjectType.CUT)
        self.graph.objects[cut_node.id] = cut_node
        parent_cut.contents.append(cut_node.id)
        action = Action('add_cut', {'parent_id': parent_cut_id, 'new_id': cut_node.id})
        return cut_node.id, action
    
    def connect(self, endpoint1: Dict, endpoint2: Dict) -> Action:
        lig1_id = self.find_ligature_for_endpoint(endpoint1)
        lig2_id = self.find_ligature_for_endpoint(endpoint2)
        if lig1_id and lig2_id:
            if lig1_id == lig2_id: return Action('connect', {'status': 'noop', 'endpoints': [endpoint1, endpoint2]})
            lig1 = self.graph.get_object(lig1_id)
            lig2 = self.graph.get_object(lig2_id)
            if len(lig1.endpoints) < len(lig2.endpoints): lig1, lig2 = lig2, lig1
            for ep in lig2.endpoints:
                lig1.endpoints.append(ep)
            del self.graph.objects[lig2.id]
        elif lig1_id:
            self.graph.get_object(lig1_id).endpoints.append(endpoint2)
        elif lig2_id:
            self.graph.get_object(lig2_id).endpoints.append(endpoint1)
        else:
            lig = Hyperedge(GraphObjectType.LIGATURE, endpoints=[endpoint1, endpoint2])
            self.graph.objects[lig.id] = lig
        return Action('connect', {'endpoint1': endpoint1, 'endpoint2': endpoint2})
    
    def find_ligature_for_endpoint(self, endpoint: Dict) -> Optional[str]:
        for obj in self.graph.objects.values():
            if isinstance(obj, Hyperedge) and obj.edge_type == GraphObjectType.LIGATURE:
                if endpoint in obj.endpoints:
                    return obj.id
        return None

    def sever_endpoint(self, endpoint: Dict) -> Action:
        lig_id = self.find_ligature_for_endpoint(endpoint)
        if not lig_id:
            new_lig = Hyperedge(GraphObjectType.LIGATURE, endpoints=[endpoint])
            self.graph.objects[new_lig.id] = new_lig
        else:
            lig = self.graph.get_object(lig_id)
            if len(lig.endpoints) >= 2:
                lig.endpoints.remove(endpoint)
                new_lig = Hyperedge(GraphObjectType.LIGATURE, endpoints=[endpoint])
                self.graph.objects[new_lig.id] = new_lig
        return Action('sever_endpoint', {'endpoint': endpoint})

class ClifTranslator:
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph
        self.ligature_map: Dict[str, str] = {}
        self.var_counter = 0

    def _get_new_var(self) -> str:
        self.var_counter += 1
        return f"x{self.var_counter}"

    def _analyze_ligatures(self):
        all_ligatures = [obj for obj in self.graph.objects.values() if isinstance(obj, Hyperedge)]
        
        # Sort ligatures for deterministic variable naming
        sorted_ligatures = sorted(all_ligatures, key=lambda lig: lig.id)

        for lig in sorted_ligatures:
            if lig.id in self.ligature_map: continue
            constant_name = None
            for endpoint in lig.endpoints:
                node = self.graph.get_object(endpoint['node_id'])
                if node.properties.get('type') == 'constant':
                    constant_name = node.properties.get('name')
                    break
            term_name = constant_name if constant_name else self._get_new_var()
            self.ligature_map[lig.id] = term_name

    def translate(self) -> str:
        self.ligature_map.clear()
        self.var_counter = 0
        self._analyze_ligatures()
        return self._recursive_translate(self.graph.root_id)

    def _recursive_translate(self, cut_id: str) -> str:
        cut = self.graph.get_object(cut_id)
        quantified_vars = set()
        
        for lig_id, var_name in self.ligature_map.items():
            if var_name.startswith('x'):
                starting_ctx = self.graph.get_ligature_starting_context(lig_id)
                if starting_ctx and starting_ctx.id == cut_id:
                    quantified_vars.add(var_name)
        
        child_cuts = [c for c in cut.contents if self.graph.get_object(c).node_type == GraphObjectType.CUT]
        predicates = [p for p in cut.contents if self.graph.get_object(p).node_type == GraphObjectType.PREDICATE]

        atoms = []
        for p_id in predicates:
            p = self.graph.get_object(p_id)
            if p.properties.get('type') == 'constant': continue
            
            hook_terms = [""] * p.properties.get('arity', 0)
            for lig_id, term in self.ligature_map.items():
                lig = self.graph.get_object(lig_id)
                for ep in lig.endpoints:
                    if ep['node_id'] == p.id:
                        hook_terms[ep['hook_index']] = term
            
            if any(t == "" for t in hook_terms): continue
            
            p_name = p.properties.get('name', '')
            args_str = f" {' '.join(hook_terms)}" if hook_terms else ""
            atoms.append(f"({p_name}{args_str})")

        child_translations = [f"(not {self._recursive_translate(child_id)})" for child_id in child_cuts]
        all_parts = sorted(atoms) + sorted(child_translations)
        
        content = ""
        if len(all_parts) > 1: content = f"(and {' '.join(all_parts)})"
        elif len(all_parts) == 1: content = all_parts[0]
        
        if quantified_vars:
            return f"(exists ({' '.join(sorted(list(quantified_vars)))}) {content or 'true'})"
        return content or "true"

class Validator:
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph

    def is_positive(self, node_id: str) -> bool:
        """A context is positive if it's evenly enclosed (nesting level 0, 2, 4...)."""
        return self.graph.get_nesting_level(node_id) % 2 == 0

    def is_negative(self, node_id: str) -> bool:
        """A context is negative if it's oddly enclosed (nesting level 1, 3, 5...)."""
        return not self.is_positive(node_id)

    def can_insert(self, parent_cut_id: str) -> bool:
        """Insertion is permitted in any negative context."""
        return self.is_negative(parent_cut_id)

    def can_erase(self, subgraph: Subgraph) -> bool:
        """Erasure is permitted for any subgraph on a positive context."""
        if not subgraph.root_context_id: return False
        return self.is_positive(subgraph.root_context_id)

    def can_iterate(self, subgraph: Subgraph, target_cut_id: str) -> bool:
        """
        Iteration is permitted if the target context is nested deeper than
        the source context.
        """
        source_cut_id = subgraph.root_context_id
        if not source_cut_id or not target_cut_id: return False
        
        source_level = self.graph.get_nesting_level(source_cut_id)
        target_level = self.graph.get_nesting_level(target_cut_id)
        
        return target_level > source_level

    def can_deiterate(self, subgraph: Subgraph) -> bool:
        """De-iteration is permitted if an isomorphic copy exists in a less-nested context."""
        # This requires the complex isomorphism check, which can be refined later.
        # For now, this is a placeholder for the logic.
        print("WARN: can_deiterate validation is not fully implemented.")
        return False