from collections import defaultdict
from eg_model import Cut, Predicate

class ClifTranslator:
    """Translates an EG model graph into CLIF notation."""
    def __init__(self, model):
        self.model = model
        self.variable_counter = 0
        self.variables = {}  # ligature_id -> variable_name

    def _get_variable_for_ligature(self, ligature_id):
        if ligature_id not in self.variables:
            self.variable_counter += 1
            self.variables[ligature_id] = f"?v{self.variable_counter}"
        return self.variables[ligature_id]

    def translate(self):
        self.variables.clear()
        self.variable_counter = 0
        return self._translate_context(self.model.sheet_of_assertion.id)

    def _translate_context(self, context_id):
        context = self.model.get_object(context_id)
        if not context:
            return ""

        clauses = []
        quantified_vars = set()

        for child_id in context.children:
            child = self.model.get_object(child_id)
            if isinstance(child, Predicate):
                clause, vars = self._translate_predicate(child)
                clauses.append(clause)
                quantified_vars.update(vars)
            elif isinstance(child, Cut):
                clause = self._translate_cut(child)
                clauses.append(clause)

        # Remove variables that are defined in an outer scope
        parent_id = self.model.get_object(context_id).parent_id
        outer_vars = self._get_vars_in_context_and_above(parent_id)
        quantified_vars -= outer_vars

        if not clauses:
            return ""
        
        # Sort clauses for deterministic output
        sorted_clauses = sorted(clauses)
        body = f"(and {' '.join(sorted_clauses)})" if len(sorted_clauses) > 1 else sorted_clauses[0]

        if quantified_vars:
            return f"(exists ({' '.join(sorted(list(quantified_vars)))}) {body})"
        else:
            return body

    def _translate_cut(self, cut):
        return f"(not {self._translate_context(cut.id)})"

    def _translate_predicate(self, predicate):
        if predicate.p_type == 'constant':
            # Constants have no variables and are just their label
            return f"{predicate.label}", set()

        terms = []
        quantified_vars = set()
        
        # Separate input and output hooks for functions
        output_term = None
        input_terms = []

        # Handle nullary predicates (no hooks)
        if not predicate.hooks:
            return predicate.label, set()

        for hook_index, ligature_id in sorted(predicate.hooks.items()):
            if ligature_id:
                var_name = self._get_variable_for_ligature(ligature_id)
                quantified_vars.add(var_name)
                if predicate.is_functional and hook_index == predicate.output_hook:
                    output_term = var_name
                else:
                    input_terms.append(var_name)
            else:
                # Unconnected hooks might be existentially quantified fresh variables
                self.variable_counter += 1
                var_name = f"?v{self.variable_counter}"
                quantified_vars.add(var_name)
                if predicate.is_functional and hook_index == predicate.output_hook:
                    output_term = var_name
                else:
                    input_terms.append(var_name)
        
        if predicate.is_functional:
            if not output_term:
                # If output is unconnected, it's a fresh variable
                self.variable_counter += 1
                output_term = f"?v{self.variable_counter}"
                quantified_vars.add(output_term)
            
            func_call = f"({predicate.label} {' '.join(input_terms)})"
            return f"(= {output_term} {func_call})", quantified_vars
        else:
            return f"({predicate.label} {' '.join(input_terms)})", quantified_vars
            
    def _get_vars_in_context_and_above(self, context_id):
        vars_in_scope = set()
        current_id = context_id
        while current_id is not None:
            context = self.model.get_object(current_id)
            if hasattr(context, 'children'):
                for child_id in context.children:
                    child = self.model.get_object(child_id)
                    if isinstance(child, Predicate):
                        for lig_id in child.hooks.values():
                            if lig_id and lig_id in self.variables:
                                vars_in_scope.add(self.variables[lig_id])
            current_id = getattr(context, 'parent_id', None)
        return vars_in_scope