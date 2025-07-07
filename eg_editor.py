import uuid
import copy
from eg_model import GraphModel, Cut, Predicate, Ligature, LineOfIdentity
from eg_logic import Validator

class EGEditor:
    """Provides an API for manipulating the Existential Graph model."""
    def __init__(self):
        self.model = GraphModel()
        self.validator = Validator(self)

    def add_constant(self, constant_name, parent_id='SA'):
        """Implements the Existence of Constants Rule correctly."""
        # A constant is a unary predicate.
        pred_id = self.add_predicate(constant_name, 1, parent_id, p_type='constant')
        # Asserting it requires connecting its single hook to a new Line of Identity.
        self.connect([(pred_id, 1)])
        return pred_id

    # ... (the rest of the file remains unchanged but is included for completeness)
    
    def erase_constant(self, predicate_id):
        pred = self.model.get_object(predicate_id)
        if not pred or pred.p_type != 'constant':
            raise ValueError("Target is not a constant.")
        line_id = pred.hooks.get(1)
        if line_id:
            line = self.model.get_object(line_id)
            # A standalone constant's line will have exactly one ligature with one attachment.
            if line and len(line.ligatures) == 1:
                lig = self.model.get_object(list(line.ligatures)[0])
                if lig and len(lig.attachments) == 1:
                    self.model.remove_object(lig.id)
                    self.model.remove_object(line_id)
                else:
                    raise ValueError("Cannot erase constant; it is connected to other predicates.")
            else:
                 raise ValueError("Cannot erase constant; it is connected to other predicates.")
        # Finally, remove the predicate itself and its reference in the parent
        parent_id = self.get_parent_context(predicate_id)
        if parent_id:
            self.model.get_object(parent_id).children.remove(predicate_id)
        self.model.remove_object(predicate_id)


    def apply_total_function_rule(self, function_name, arity, input_line_ids, parent_id='SA'):
        func_pred_id = self.add_predicate(function_name, arity, parent_id, is_functional=True)
        func_pred = self.model.get_object(func_pred_id)
        for i, line_id in enumerate(input_line_ids):
            func_pred.hooks[i + 1] = line_id
        output_line = LineOfIdentity()
        self.model.add_object(output_line)
        func_pred.hooks[arity] = output_line.id
        return func_pred_id

    def get_parent_context(self, obj_id):
        for parent in self.model.objects.values():
            if hasattr(parent, 'children') and obj_id in parent.children:
                return parent.id
        return None
        
    def add_cut(self, parent_id='SA'):
        parent = self.model.get_object(parent_id)
        if not parent or not hasattr(parent, 'children'): raise ValueError("Parent context not found or invalid.")
        cut = Cut(parent_id=parent_id)
        self.model.add_object(cut)
        parent.children.add(cut.id)
        return cut.id

    def add_predicate(self, label, hooks, parent_id='SA', p_type='relation', is_functional=False):
        parent = self.model.get_object(parent_id)
        if not parent or not hasattr(parent, 'children'): raise ValueError("Parent context not found or invalid.")
        predicate = Predicate(label, hooks, p_type=p_type, is_functional=is_functional)
        self.model.add_object(predicate)
        parent.children.add(predicate.id)
        return predicate.id

    def add_ligature(self, parent_id='SA'):
        line = LineOfIdentity()
        self.model.add_object(line)
        ligature = Ligature(line.id)
        self.model.add_object(ligature)
        line.ligatures.add(ligature.id)
        return ligature.id

    def connect(self, pred_hook_pairs):
        if not pred_hook_pairs: return None
        primary_line_id = None
        for pred_id, hook_index in pred_hook_pairs:
            pred = self.model.get_object(pred_id)
            if pred and pred.hooks.get(hook_index):
                primary_line_id = pred.hooks[hook_index]
                break
        if not primary_line_id:
            line = LineOfIdentity()
            self.model.add_object(line)
            primary_line_id = line.id
        for pred_id, hook_index in pred_hook_pairs:
            pred = self.model.get_object(pred_id)
            if not pred: continue
            existing_line_id = pred.hooks.get(hook_index)
            if existing_line_id and existing_line_id != primary_line_id:
                self._merge_lines(primary_line_id, existing_line_id)
            pred.hooks[hook_index] = primary_line_id
        new_ligature = Ligature(primary_line_id)
        new_ligature.attachments.update(pred_hook_pairs)
        self.model.add_object(new_ligature)
        primary_line = self.model.get_object(primary_line_id)
        primary_line.ligatures.add(new_ligature.id)
        self._calculate_traversed_cuts(new_ligature)
        return new_ligature.id

    def _merge_lines(self, primary_line_id, other_line_id):
        primary_line = self.model.get_object(primary_line_id)
        other_line = self.model.get_object(other_line_id)
        if not primary_line or not other_line: return
        for lig_id in list(other_line.ligatures):
            lig = self.model.get_object(lig_id)
            if lig:
                lig.line_of_identity_id = primary_line_id
                primary_line.ligatures.add(lig_id)
        for obj in self.model.objects.values():
            if isinstance(obj, Predicate):
                for hook, line_id in obj.hooks.items():
                    if line_id == other_line_id:
                        obj.hooks[hook] = primary_line_id
        self.model.remove_object(other_line_id)
    
    def _get_ancestors(self, context_id):
        ancestors = []
        current_id = context_id
        while current_id is not None:
            ancestors.append(current_id)
            current_id = self.get_parent_context(current_id)
        return ancestors

    def _find_lca(self, context_ids):
        if not context_ids: return None
        paths = [self._get_ancestors(cid) for cid in context_ids]
        lca_path = paths[0]
        for path in paths[1:]:
            lca_path = [node for node in lca_path if node in path]
        return lca_path[0] if lca_path else None

    def _calculate_traversed_cuts(self, ligature):
        attachments = list(ligature.attachments)
        if len(attachments) < 2: return
        context_ids = [self.get_parent_context(pred_id) for pred_id, _ in attachments]
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

    def insert_double_cut(self, selection_ids=None, parent_id='SA'):
        if selection_ids: parent_id = self.get_parent_context(selection_ids[0])
        outer_cut_id = self.add_cut(parent_id)
        inner_cut_id = self.add_cut(outer_cut_id)
        if selection_ids:
            original_parent = self.model.get_object(parent_id)
            inner_cut = self.model.get_object(inner_cut_id)
            for obj_id in selection_ids:
                if obj_id in original_parent.children: original_parent.children.remove(obj_id)
                inner_cut.children.add(obj_id)
        return outer_cut_id, inner_cut_id

    def remove_double_cut(self, outer_cut_id):
        if not self.validator.can_remove_double_cut(outer_cut_id): raise ValueError("Not a valid double cut.")
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

    def iterate(self, selection_ids, target_context_id):
        if not self.validator.can_iterate(selection_ids, target_context_id): raise ValueError("Iteration not valid.")
        id_map = {obj_id: str(uuid.uuid4()) for obj_id in selection_ids}
        for obj_id in selection_ids:
            original_obj = self.model.get_object(obj_id)
            new_obj = copy.deepcopy(original_obj)
            new_obj.id = id_map[obj_id]
            target_parent = self.model.get_object(target_context_id)
            target_parent.children.add(new_obj.id)
            self.model.add_object(new_obj)
            if isinstance(new_obj, Predicate):
                for hook_index, line_id in original_obj.hooks.items():
                    if line_id:
                        new_obj.hooks[hook_index] = line_id

    def apply_functional_property_rule(self, pred1_id, pred2_id):
        if not self.validator.can_apply_functional_property_rule(pred1_id, pred2_id): raise ValueError("Cannot apply rule.")
        pred1 = self.model.get_object(pred1_id)
        output_hook = pred1.output_hook
        self.connect([(pred1_id, output_hook), (pred2_id, output_hook)])