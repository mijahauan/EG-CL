from collections import defaultdict
from eg_model import Cut, Predicate

class ClifTranslator:
    """Translates an EG model graph into CLIF notation using a robust, two-pass approach."""
    def __init__(self, editor):
        self.editor = editor
        self.model = editor.model
        self.variable_counter = 0
        self.line_to_variable_map = {}
        # Caches the calculated scope for each line to avoid redundant computation
        self.line_scope_cache = {}

    def _get_line_scope(self, line_id):
        """Finds the shallowest context (LCA) where a line appears."""
        if line_id in self.line_scope_cache:
            return self.line_scope_cache[line_id]

        line = self.model.get_object(line_id)
        if not line: return None

        attachment_contexts = set()
        # A line's attachments are spread across its constituent ligatures
        for lig_id in line.ligatures:
            lig = self.model.get_object(lig_id)
            if lig:
                for pred_id, _ in lig.attachments:
                    parent_context = self.editor.get_parent_context(pred_id)
                    if parent_context:
                        attachment_contexts.add(parent_context)
        
        if not attachment_contexts:
            # A detached line "exists" on the sheet of assertion by default
            return self.model.sheet_of_assertion.id

        # The scope is the Least Common Ancestor of all its attachment points
        lca = self.editor._find_lca(list(attachment_contexts))
        self.line_scope_cache[line_id] = lca
        return lca

    def _get_variable_for_line(self, line_id):
        """Creates or retrieves a variable name for a given Line of Identity."""
        if line_id not in self.line_to_variable_map:
            self.variable_counter += 1
            self.line_to_variable_map[line_id] = f"?v{self.variable_counter}"
        return self.line_to_variable_map[line_id]

    def translate(self):
        """Starts the translation from the top-level Sheet of Assertion."""
        self.line_to_variable_map.clear()
        self.variable_counter = 0
        self.line_scope_cache.clear()
        return self._translate_context(self.model.sheet_of_assertion)

    def _translate_context(self, context):
        """Recursively translates a context, handling variable quantification."""
        clauses = []
        lines_in_subgraph = set()

        # First pass: discover all lines that appear anywhere in this context's subtree
        nodes_to_visit = [context]
        visited_contexts = {context.id}
        while nodes_to_visit:
            current_context = nodes_to_visit.pop(0)
            for child_id in current_context.children:
                child = self.model.get_object(child_id)
                if isinstance(child, Predicate):
                    for line_id in child.hooks.values():
                        if line_id:
                            lines_in_subgraph.add(line_id)
                elif isinstance(child, Cut) and child.id not in visited_contexts:
                    nodes_to_visit.append(child)
                    visited_contexts.add(child.id)

        # Determine which of those lines are scoped to *this* context specifically
        vars_to_quantify = {
            self._get_variable_for_line(line_id)
            for line_id in lines_in_subgraph
            if self._get_line_scope(line_id) == context.id
        }
        
        # Second pass: translate the immediate children of this context
        for child_id in context.children:
            child = self.model.get_object(child_id)
            if isinstance(child, Predicate):
                clauses.append(self._translate_predicate(child))
            elif isinstance(child, Cut):
                clauses.append(self._translate_context(child))
        
        if not clauses: return ""
        
        sorted_clauses = sorted(clauses)
        body = f"(and {' '.join(sorted_clauses)})" if len(sorted_clauses) > 1 else sorted_clauses[0]
        
        # If the context is a cut, wrap its body in a 'not'
        if isinstance(context, Cut):
            body = f"(not {body})"

        # Finally, wrap with an 'exists' clause if necessary
        if vars_to_quantify:
            return f"(exists ({' '.join(sorted(list(vars_to_quantify)))}) {body})"
        else:
            return body

    def _translate_predicate(self, predicate):
        """Translates a Predicate into its CLIF representation."""
        if predicate.is_functional:
            output_hook = predicate.output_hook
            # Ensure all hooks have a line before proceeding
            if not all(predicate.hooks.get(i) for i in predicate.hooks):
                return "(error: functional predicate has unconnected hooks)"

            output_var = self._get_variable_for_line(predicate.hooks.get(output_hook))
            input_vars = [
                self._get_variable_for_line(predicate.hooks.get(i))
                for i in sorted(predicate.hooks.keys()) if i != output_hook
            ]
            func_call = f"({predicate.label}{' ' if input_vars else ''}{' '.join(input_vars)})"
            return f"(= {output_var} {func_call})"
        else:
            if not predicate.hooks:
                return predicate.label
            terms = [
                self._get_variable_for_line(predicate.hooks.get(i))
                for i in sorted(predicate.hooks.keys()) if predicate.hooks.get(i)
            ]
            return f"({predicate.label} {' '.join(terms)})"