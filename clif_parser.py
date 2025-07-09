from clif_sexpr_parser import SexprParser
from eg_model import GraphModel, Cut, Predicate, LineOfIdentity

class ClifParser:
    """Parses a CLIF string into an EG model, with robust handling for nested functions."""
    def __init__(self, editor):
        self.editor = editor
        self.model = editor.model
        self.sexpr_parser = SexprParser()
        self.variable_map = {}

    def parse(self, clif_string):
        """Public method to parse a CLIF string."""
        if not clif_string:
            return
        s_expression = self.sexpr_parser.parse(clif_string)
        self._parse_expression(s_expression, self.model.sheet_of_assertion.id)

    def _get_or_create_line(self, var_name):
        """Ensures a line of identity exists for a given variable name."""
        if var_name not in self.variable_map:
            line = LineOfIdentity()
            self.model.add_object(line)
            self.variable_map[var_name] = line.id
        return self.variable_map[var_name]

    def _parse_term(self, term, context_id):
        """
        Recursively parses a term. A term can be a variable/constant (string)
        or a function call (list). Returns the line_id for the term's output.
        """
        if isinstance(term, str):
            return self._get_or_create_line(term)
        
        func_name = term[0]
        input_terms = term[1:]
        
        input_line_ids = [self._parse_term(t, context_id) for t in input_terms]

        output_line = LineOfIdentity()
        self.model.add_object(output_line)

        num_hooks = len(input_terms) + 1
        pred_id = self.editor.add_predicate(func_name, num_hooks, parent_id=context_id, is_functional=True)
        pred = self.model.get_object(pred_id)

        for i, line_id in enumerate(input_line_ids):
            pred.hooks[i + 1] = line_id
        pred.hooks[num_hooks] = output_line.id

        for i in range(1, num_hooks + 1):
            self.editor.connect([(pred_id, i)])
            
        return output_line.id

    def _parse_expression(self, expr, context_id):
        """Recursively parses a CLIF s-expression."""
        if not isinstance(expr, list) or not expr:
            return

        operator = expr[0]

        if operator == 'exists':
            self._parse_expression(expr[2], context_id)
        elif operator == 'and':
            for clause in expr[1:]:
                self._parse_expression(clause, context_id)
        elif operator == 'not':
            cut_id = self.editor.add_cut(parent_id=context_id)
            self._parse_expression(expr[1], cut_id)
        elif operator == 'forall':
            cut1_id = self.editor.add_cut(parent_id=context_id)
            cut2_id = self.editor.add_cut(parent_id=cut1_id)
            self._parse_expression(expr[2], cut2_id)
        elif operator == 'if':
            cut1_id = self.editor.add_cut(parent_id=context_id)
            self._parse_expression(expr[1], cut1_id)
            cut2_id = self.editor.add_cut(parent_id=cut1_id)
            self._parse_expression(expr[2], cut2_id)
        
        elif operator == '=':
            line1_id = self._parse_term(expr[1], context_id)
            line2_id = self._parse_term(expr[2], context_id)
            
            line1 = self.model.get_object(line1_id)
            line2 = self.model.get_object(line2_id)
            
            if line1 and line2 and line1.ligatures and line2.ligatures:
                lig1_id = next(iter(line1.ligatures))
                lig2_id = next(iter(line2.ligatures))
                
                lig1 = self.model.get_object(lig1_id)
                lig2 = self.model.get_object(lig2_id)
                
                if lig1 and lig2 and lig1.attachments and lig2.attachments:
                    attach1 = next(iter(lig1.attachments))
                    attach2 = next(iter(lig2.attachments))
                    self.editor.connect([attach1, attach2])

        else: # Standard atomic predicate
            predicate_name = expr[0]
            variable_names = expr[1:]
            
            pred_id = self.editor.add_predicate(predicate_name, len(variable_names), parent_id=context_id)
            pred = self.model.get_object(pred_id)
            
            for i, var_name in enumerate(variable_names):
                line_id = self._get_or_create_line(var_name)
                pred.hooks[i+1] = line_id
                self.editor.connect([(pred_id, i+1)])