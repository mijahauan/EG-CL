import uuid
import copy
from eg_model import GraphModel, Cut, Predicate, Ligature
from eg_logic import Validator

class EGEditor:
    """Provides an API for manipulating the Existential Graph model."""
    def __init__(self):
        self.model = GraphModel()
        self.validator = Validator(self)

    def get_parent_context(self, obj_id):
        for parent in self.model.objects.values():
            if hasattr(parent, 'children') and obj_id in parent.children:
                return parent.id
        return None

    def _get_ancestors(self, context_id):
        ancestors = []
        current_id = context_id
        while current_id is not None:
            ancestors.append(current_id)
            current_id = self.get_parent_context(current_id)
        return ancestors

    def _find_lca(self, context_ids):
        if not context_ids:
            return None
        paths = [self._get_ancestors(cid) for cid in context_ids]
        lca_path = paths[0]
        for path in paths[1:]:
            lca_path = [node for node in lca_path if node in path]
        return lca_path[0] if lca_path else None

    def _calculate_traversed_cuts(self, ligature, pred_hook_pairs):
        if len(pred_hook_pairs) < 2:
            return
        context_ids = [self.get_parent_context(pair[0]) for pair in pred_hook_pairs]
        lca_id = self._find_lca(context_ids)
        traversed = set()
        for cid in context_ids:
            current_id = cid
            while current_id is not None and current_id != lca_id:
                context = self.model.get_object(current_id)
                if isinstance(context, Cut):
                    traversed.add(current_id)
                current_id = self.get_parent_context(current_id)
        ligature.traversed_cuts = traversed

    def connect(self, pred_hook_pairs):
        """Connects predicate hooks, reusing an existing ligature if one is provided."""
        existing_ligature = None
        
        # Check if any of the hooks are already connected
        for pred_id, hook_index in pred_hook_pairs:
            predicate = self.model.get_object(pred_id)
            if predicate and predicate.hooks.get(hook_index):
                existing_ligature = self.model.get_object(predicate.hooks[hook_index])
                if existing_ligature:
                    break

        ligature_to_use = existing_ligature if existing_ligature else Ligature()
        if not existing_ligature:
            self.model.add_object(ligature_to_use)

        for pred_id, hook_index in pred_hook_pairs:
            predicate = self.model.get_object(pred_id)
            if predicate and hook_index in predicate.hooks:
                # Disconnect from any old ligature first
                old_lig_id = predicate.hooks[hook_index]
                if old_lig_id and old_lig_id != ligature_to_use.id:
                    old_ligature = self.model.get_object(old_lig_id)
                    if old_ligature and (pred_id, hook_index) in old_ligature.connections:
                         old_ligature.connections.remove((pred_id, hook_index))
                
                # Connect to the new or existing ligature
                predicate.hooks[hook_index] = ligature_to_use.id
                ligature_to_use.connections.add((pred_id, hook_index))
        
        self._calculate_traversed_cuts(ligature_to_use, list(ligature_to_use.connections))
        
        return ligature_to_use.id
        
    def add_cut(self, parent_id='SA'):
        parent = self.model.get_object(parent_id)
        if not parent or not hasattr(parent, 'children'):
            raise ValueError("Parent context not found or invalid.")
        cut = Cut(parent_id=parent_id)
        self.model.add_object(cut)
        parent.children.add(cut.id)
        return cut.id

    def add_predicate(self, label, hooks, parent_id='SA', p_type='relation', is_functional=False):
        parent = self.model.get_object(parent_id)
        if not parent or not hasattr(parent, 'children'):
            raise ValueError("Parent context not found or invalid.")
        predicate = Predicate(label, hooks, p_type=p_type, is_functional=is_functional)
        self.model.add_object(predicate)
        parent.children.add(predicate.id)
        return predicate.id

    def erase(self, selection_ids):
        if not self.validator.can_erase(selection_ids):
            raise ValueError("Erasure is not valid in this context.")
        for obj_id in selection_ids:
            parent_id = self.get_parent_context(obj_id)
            parent = self.model.get_object(parent_id)
            if obj_id in parent.children:
                parent.children.remove(obj_id)
            obj = self.model.get_object(obj_id)
            if isinstance(obj, Predicate):
                for hook, lig_id in obj.hooks.items():
                    if lig_id:
                        ligature = self.model.get_object(lig_id)
                        if ligature and (obj_id, hook) in ligature.connections:
                            ligature.connections.remove((obj_id, hook))
            self.model.remove_object(obj_id)

    def iterate(self, selection_ids, target_context_id):
        if not self.validator.can_iterate(selection_ids, target_context_id):
            raise ValueError("Iteration to this context is not valid.")
        
        id_map = {obj_id: str(uuid.uuid4()) for obj_id in selection_ids}
        
        for obj_id in selection_ids:
            original_obj = self.model.get_object(obj_id)
            new_obj = copy.deepcopy(original_obj)
            new_obj.id = id_map[obj_id]
            
            target_parent = self.model.get_object(target_context_id)
            target_parent.children.add(new_obj.id)
            self.model.add_object(new_obj)
        
        for obj_id in selection_ids:
            original_obj = self.model.get_object(obj_id)
            if not isinstance(original_obj, Predicate):
                continue
            
            new_obj_id = id_map[obj_id]
            for hook_index, lig_id in original_obj.hooks.items():
                if not lig_id:
                    continue
                
                ligature = self.model.get_object(lig_id)
                is_internal = all(conn[0] in selection_ids for conn in ligature.connections)
                
                if is_internal:
                    # Logic to create new, copied internal ligatures
                    pass
                else:
                    # Connect the hook of the new object to the existing external ligature
                    self.connect([(new_obj_id, hook_index)])

    def deiterate(self, selection_ids):
        original_ids = self._find_isomorphic_original(selection_ids)
        if not original_ids:
            raise ValueError("No valid original found for de-iteration.")
        
        if not self.validator.can_deiterate(selection_ids, original_ids):
             raise ValueError("De-iteration is not valid.")
        
        self.erase(selection_ids)

    def _find_isomorphic_original(self, selection_ids):
        return []

    def insert_double_cut(self, selection_ids=None, parent_id='SA'):
        if selection_ids:
            parent_id = self.get_parent_context(selection_ids[0])
        
        outer_cut_id = self.add_cut(parent_id)
        inner_cut_id = self.add_cut(outer_cut_id)
        
        if selection_ids:
            original_parent = self.model.get_object(parent_id)
            inner_cut = self.model.get_object(inner_cut_id)
            for obj_id in selection_ids:
                if obj_id in original_parent.children:
                    original_parent.children.remove(obj_id)
                inner_cut.children.add(obj_id)
            
        return outer_cut_id, inner_cut_id

    def remove_double_cut(self, outer_cut_id):
        if not self.validator.can_remove_double_cut(outer_cut_id):
            raise ValueError("This is not a valid double cut to remove.")
        outer_cut = self.model.get_object(outer_cut_id)
        inner_cut_id = list(outer_cut.children)[0]
        inner_cut = self.model.get_object(inner_cut_id)
        parent_id = self.get_parent_context(outer_cut_id)
        parent = self.model.get_object(parent_id)
        for child_id in list(inner_cut.children):
            inner_cut.children.remove(child_id)
            parent.children.add(child_id)
        parent.children.remove(outer_cut_id)
        self.model.remove_object(outer_cut_id)
        self.model.remove_object(inner_cut_id)
        
    def set_functional(self, predicate_id, is_functional=True):
        predicate = self.model.get_object(predicate_id)
        if not isinstance(predicate, Predicate):
            raise ValueError("Object is not a predicate.")
        predicate.is_functional = is_functional

    def apply_functional_property_rule(self, pred1_id, pred2_id):
        if not self.validator.can_apply_functional_property_rule(pred1_id, pred2_id):
            raise ValueError("Cannot apply functional property rule.")
        pred1 = self.model.get_object(pred1_id)
        output_hook = pred1.output_hook
        self.connect([(pred1_id, output_hook), (pred2_id, output_hook)])