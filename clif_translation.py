from collections import defaultdict
from eg_model import Cut, Predicate, LineOfIdentity

class ClifTranslator:
    """Translates an EG model graph into CLIF notation using a robust, multi-pass approach."""
    def __init__(self, editor):
        self.editor = editor
        self.model = editor.model
        self.variable_counter = 0
        self.line_to_variable_map = {}
        self.line_scope_cache = {}

    def _get_line_scope(self, line_id):
        """Finds the shallowest context (LCA) where a line appears."""
        if line_id in self.line_scope_cache:
            return self.line_scope_cache[line_id]

        line = self.model.get_object(line_id)
        if not line or not line.ligatures:
            return self.model.sheet_of_assertion.id

        attachment_contexts = {
            self.editor.get_parent_context(pred_id)
            for lig_id in line.ligatures
            if (lig := self.model.get_object(lig_id))
            for pred_id, _ in lig.attachments
            if self.editor.get_parent_context(pred_id) is not None
        }
        
        if not attachment_contexts:
            return self.model.sheet_of_assertion.id

        lca = self.editor._find_lca(list(attachment_contexts))
        self.line_scope_cache[line_id] = lca
        return lca

    def _assign_variable_for_line(self, line_id):
        """Assigns a variable name to a Line of Identity if it doesn't have one."""
        if line_id not in self.line_to_variable_map:
            self.variable_counter += 1
            self.line_to_variable_map[line_id] = f"?v{self.variable_counter}"
        return self.line_to_variable_map[line_id]

    def translate(self):
        """Starts the translation from the top-level Sheet of Assertion."""
        self.line_to_variable_map.clear()
        self.variable_counter = 0
        self.line_scope_cache.clear()

        # Pass 1: Deterministically assign all variable names.
        all_lines = [obj for obj in self.model.objects.values() if isinstance(obj, LineOfIdentity)]
        sorted_lines = sorted(all_lines, key=lambda x: x.id)
        for line in sorted_lines:
            self._assign_variable_for_line(line.id)

        # Pass 2: Pre-cache all scopes.
        for line in sorted_lines:
            self._get_line_scope(line.id)

        # Pass 3: Recursively translate.
        return self._translate_context(self.model.sheet_of_assertion)

    def _translate_context(self, context):
        """Recursively translates a context, handling variable quantification."""
        clauses = []
        
        # Determine which variables are scoped to *this specific context*
        vars_to_quantify = {
            var_name
            for line_id, var_name in self.line_to_variable_map.items()
            if self.line_scope_cache.get(line_id) == context.id
        }
        
        # Translate the immediate children of this context
        for child_id in context.children:
            child = self.model.get_object(child_id)
            if isinstance(child, Predicate):
                clauses.append(self._translate_predicate(child))
            elif isinstance(child, Cut):
                clauses.append(self._translate_context(child))
        
        if not clauses: return ""
        
        sorted_clauses = sorted(clauses)
        body = f"(and {' '.join(sorted_clauses)})" if len(sorted_clauses) > 1 else sorted_clauses[0]
        
        if isinstance(context, Cut):
            body = f"(not {body})"

        if vars_to_quantify:
            return f"(exists ({' '.join(sorted(list(vars_to_quantify)))}) {body})"
        else:
            return body

    def _translate_predicate(self, predicate):
        """Translates a Predicate into its CLIF representation."""
        if predicate.is_functional:
            output_hook = predicate.output_hook
            output_var = self.line_to_variable_map.get(predicate.hooks.get(output_hook))
            
            input_vars = [
                self.line_to_variable_map.get(predicate.hooks.get(i))
                for i in sorted(predicate.hooks.keys()) if i != output_hook
            ]
            func_call = f"({predicate.label}{' ' if input_vars else ''}{' '.join(input_vars)})"
            return f"(= {output_var} {func_call})"
        else:
            if not predicate.hooks:
                return predicate.label
            terms = [
                self.line_to_variable_map.get(predicate.hooks.get(i))
                for i in sorted(predicate.hooks.keys())
            ]
            return f"({predicate.label} {' '.join(terms)})"