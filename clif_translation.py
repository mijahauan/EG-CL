from collections import defaultdict
from eg_model import Cut, Predicate, LineOfIdentity

class ClifTranslator:
    """
    Translates an EG model into a canonical CLIF notation using a
    topology-based sorting key for deterministic, idempotent output.
    """
    def __init__(self, editor):
        self.editor = editor
        self.model = editor.model
        self.variable_counter = 0
        self.line_to_variable_map = {}
        self.line_scope_cache = {}
        self.context_depth_cache = {}

    def _get_context_depth(self, context_id):
        """Helper to calculate and cache the nesting depth of a context."""
        if context_id in self.context_depth_cache:
            return self.context_depth_cache[context_id]
        
        depth = 0
        current_id = context_id
        while current_id != self.model.sheet_of_assertion.id:
            # Assumes editor has a method to get a parent context id.
            # If not, this might need to be adapted to traverse the model directly.
            parent_context = self.editor.get_parent_context(current_id)
            if not parent_context:
                break 
            depth += 1
            current_id = parent_context
        
        self.context_depth_cache[context_id] = depth
        return depth

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

    def _discover_and_assign_variables(self):
        """
        Pre-pass to assign canonical variable names based on a truly stable
        topological key: (deepest_nesting, predicate_label, hook_number).
        """
        all_lines = [obj for obj in self.model.objects.values() if isinstance(obj, LineOfIdentity)]
        
        def get_stable_sort_key(line):
            """Create a canonical sorting key from a line's connections."""
            attachments = []
            if line.ligatures:
                for lig_id in line.ligatures:
                    if (lig := self.model.get_object(lig_id)):
                        for pred_id, hook_num in lig.attachments:
                            pred = self.model.get_object(pred_id)
                            if pred:
                                parent_context_id = self.editor.get_parent_context(pred_id)
                                depth = self._get_context_depth(parent_context_id)
                                # Sort by depth (inside-out), then label, then hook number.
                                attachments.append((-depth, pred.label, hook_num))
            attachments.sort()
            return tuple(attachments)

        all_lines.sort(key=get_stable_sort_key)
        
        for line in all_lines:
            if line.id not in self.line_to_variable_map:
                self.variable_counter += 1
                self.line_to_variable_map[line.id] = f"?v{self.variable_counter}"

    def translate(self):
        self.line_to_variable_map.clear()
        self.variable_counter = 0
        self.line_scope_cache.clear()
        self.context_depth_cache.clear()
        self._discover_and_assign_variables()
        return self._translate_context(self.model.sheet_of_assertion)

    def _translate_context(self, context):
        predicates = [self.model.get_object(cid) for cid in context.children if isinstance(self.model.get_object(cid), Predicate)]
        cuts = [self.model.get_object(cid) for cid in context.children if isinstance(self.model.get_object(cid), Cut)]
        
        pred_clauses = sorted([self._translate_predicate(p) for p in predicates])
        cut_clauses = sorted([self._translate_context(c) for c in cuts if self._translate_context(c)])

        all_clauses = pred_clauses + cut_clauses
        
        if not all_clauses: return ""

        vars_to_quantify = sorted([
            var_name for line_id, var_name in self.line_to_variable_map.items()
            if self._get_line_scope(line_id) == context.id
        ])

        if len(all_clauses) > 1:
            body = f"(and {' '.join(all_clauses)})"
        else:
            body = all_clauses[0]
            if isinstance(context, Cut) and body.startswith('(') and body.endswith(')'):
                if ' ' not in body and not body.startswith('(= '):
                     body = body[1:-1]
        
        if isinstance(context, Cut):
            return f"(not {body})"

        if vars_to_quantify:
            return f"(exists ({' '.join(vars_to_quantify)}) {body})"
        else:
            return body

    def _translate_predicate(self, predicate):
        """Translate a predicate, preserving argument order by sorting hooks numerically."""
        terms = [
            self.line_to_variable_map.get(predicate.hooks[i])
            for i in sorted(predicate.hooks.keys())
            if self.line_to_variable_map.get(predicate.hooks.get(i)) is not None
        ]

        if predicate.is_functional:
            output_var = self.line_to_variable_map.get(predicate.hooks.get(predicate.output_hook))
            input_vars = [term for term in terms if term != output_var]
            func_call = f"({predicate.label}{' ' if input_vars else ''}{' '.join(input_vars)})"
            return f"(= {output_var} {func_call})"
        else:
            if not terms:
                return f"({predicate.label})"
            return f"({predicate.label} {' '.join(terms)})"