from eg_model import Cut

class Validator:
    """Contains methods to validate transformation rule preconditions."""
    def __init__(self, editor):
        self.editor = editor

    def get_context_depth(self, context_id):
        depth = 0
        current_id = context_id
        while current_id is not None and current_id != self.editor.model.sheet_of_assertion.id:
            parent_id = self.editor.get_parent_context(current_id)
            if parent_id is None: # Should only happen for SA
                break
            depth += 1
            current_id = parent_id
        return depth

    def is_positive_context(self, context_id):
        return self.get_context_depth(context_id) % 2 == 0

    def is_negative_context(self, context_id):
        return not self.is_positive_context(context_id)

    def can_erase(self, selection):
        if not selection:
            return False
        context_id = self.editor.get_parent_context(selection[0])
        return self.is_positive_context(context_id)

    def can_insert(self, context_id):
        return self.is_negative_context(context_id)

    def can_iterate(self, selection, target_context_id):
        if not selection or not target_context_id:
            return False
        source_context_id = self.editor.get_parent_context(selection[0])

        # Cannot iterate into the same or an outer context.
        if source_context_id == target_context_id:
            return False
        
        current_id = target_context_id
        # Walk up the tree from the target until we find the source or hit the top
        while current_id is not None:
            if current_id == source_context_id:
                return True # Found the source as an ancestor of the target. This is valid.
            current_id = self.editor.get_parent_context(current_id)
        
        return False # Walked to the top and never found the source context.
        
    def can_deiterate(self, selection, original_selection):
        if not selection or not original_selection:
            return False
        
        # Placeholder for complex de-iteration validation
        return True # Simplified for now

    def can_remove_double_cut(self, cut_id):
        outer_cut = self.editor.model.get_object(cut_id)
        if not isinstance(outer_cut, Cut) or len(outer_cut.children) != 1:
            return False
        
        inner_cut_id = list(outer_cut.children)[0]
        inner_cut = self.editor.model.get_object(inner_cut_id)
        if not isinstance(inner_cut, Cut):
            return False
            
        return True # Simplified for now
        
    def can_apply_functional_property_rule(self, pred1_id, pred2_id):
        pred1 = self.editor.model.get_object(pred1_id)
        pred2 = self.editor.model.get_object(pred2_id)

        if not (pred1 and pred2 and pred1.is_functional and pred2.is_functional):
            return False
        if pred1.label != pred2.label or len(pred1.hooks) != len(pred2.hooks):
            return False
            
        output_hook_index = pred1.output_hook
        for i in range(1, output_hook_index):
            if pred1.hooks[i] != pred2.hooks[i]:
                return False
        
        if pred1.hooks[output_hook_index] == pred2.hooks[output_hook_index] and pred1.hooks[output_hook_index] is not None:
            return False
            
        return True