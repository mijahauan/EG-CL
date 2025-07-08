from collections import defaultdict
from eg_model import Cut, Predicate

class ClifTranslator:
    """Translates an EG model graph into CLIF notation using a robust, two-pass approach."""
    def __init__(self, editor):
        self.editor = editor
        self.model = editor.model
        self.variable_counter = 0
        self.line_to_variable_map = {}
        self.line_scope_cache = {}

    def _get_line_scope(self, line_id):
        if line_id in self.line_scope_cache:
            return self.line_scope_cache[line_id]

        line = self.model.get_object(line_id)
        if not line or not line.ligatures: return None

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

    def _get_variable_for_line(self, line_id):
        if line_id not in self.line_to_variable_map:
            self.variable_counter += 1
            self.line_to_variable_map[line_id] = f"?v{self.variable_counter}"
        return self.line_to_variable_map[line_id]

    def translate(self):
        self.line_to_variable_map.clear()
        self.variable_counter = 0
        self.line_scope_cache.clear()
        return self._translate_context(self.model.sheet_of_assertion)

    def _translate_context(self, context):
        clauses = []
        lines_in_subgraph = set()

        nodes_to_visit = [context]
        visited_contexts = {context.id}
        while nodes_to_visit:
            current_context = nodes_to_visit.pop(0)
            for child_id in current_context.children:
                child = self.model.get_object(child_id)
                if isinstance(child, Predicate):
                    for line_id in child.hooks.values():
                        if line_id: lines_in_subgraph.add(line_id)
                elif isinstance(child, Cut) and child.id not in visited_contexts:
                    nodes_to_visit.append(child)
                    visited_contexts.add(child.id)
        
        # Sort discovered lines to ensure deterministic variable assignment
        sorted_lines = sorted(list(lines_in_subgraph))

        vars_to_quantify = {
            self._get_variable_for_line(line_id)
            for line_id in sorted_lines
            if self._get_line_scope(line_id) == context.id
        }
        
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
        if predicate.is_functional:
            output_hook = predicate.output_hook
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
                for i in sorted(predicate.hooks.keys())
            ]
            return f"({predicate.label} {' '.join(terms)})"