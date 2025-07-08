from eg_editor import EGEditor
from eg_model import LineOfIdentity

class ClifParser:
    """Parses a CLIF string using an 'inside-out' recursive descent method."""
    def __init__(self, editor: EGEditor):
        self.editor = editor
        self.model = editor.model
        # Maps variable names (e.g., '?x') to Line of Identity IDs
        self.variable_map = {}

    def parse(self, clif_string: str):
        """Public method to parse a CLIF string."""
        self.variable_map.clear()
        s_expression = self._tokenize(clif_string)
        self._parse_expression(s_expression, 'SA')

    def _tokenize(self, clif_string: str):
        """A simple tokenizer for s-expressions."""
        clif_string = clif_string.replace('(', ' ( ').replace(')', ' ) ')
        tokens = clif_string.split()
        
        def read_from_tokens(tokens):
            if not tokens: raise SyntaxError("Unexpected EOF")
            token = tokens.pop(0)
            if token == '(':
                L = []
                while tokens and tokens[0] != ')':
                    L.append(read_from_tokens(tokens))
                if not tokens: raise SyntaxError("Unexpected EOF, expecting ')'")
                tokens.pop(0)
                return L
            elif token == ')': raise SyntaxError("Unexpected ')'")
            else: return token
        
        return read_from_tokens(tokens)

    def _parse_expression(self, expr, context_id):
        """Recursively parses a CLIF s-expression from the inside out."""
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
        
        elif operator == '=':
            # Handle function: (= output_var (func_name input_var1 ...))
            output_var = expr[1]
            func_call = expr[2]
            func_name = func_call[0]
            input_vars = func_call[1:]
            
            # Ensure lines of identity exist for all variables
            all_vars = [output_var] + input_vars
            for var in all_vars:
                if var not in self.variable_map:
                    line = LineOfIdentity()
                    self.model.add_object(line)
                    self.variable_map[var] = line.id

            # Create the functional predicate
            num_hooks = len(input_vars) + 1
            pred_id = self.editor.add_predicate(func_name, num_hooks, parent_id=context_id, is_functional=True)
            pred = self.model.get_object(pred_id)

            # Connect input and output hooks
            for i, var_name in enumerate(input_vars):
                pred.hooks[i + 1] = self.variable_map[var_name]
            pred.hooks[num_hooks] = self.variable_map[output_var] # Last hook is output
            
            # Create the visual connections
            for i in range(1, num_hooks + 1):
                self.editor.connect([(pred_id, i)])

        else: # Standard atomic predicate
            predicate_name = expr[0]
            variable_names = expr[1:]
            
            pred_id = self.editor.add_predicate(predicate_name, len(variable_names), parent_id=context_id)
            pred = self.model.get_object(pred_id)
            
            for i, var_name in enumerate(variable_names):
                line_id = self.variable_map.get(var_name)
                if line_id is None:
                    line = LineOfIdentity()
                    self.model.add_object(line)
                    line_id = line.id
                    self.variable_map[var_name] = line_id
                
                pred.hooks[i + 1] = line_id
                self.editor.connect([(pred_id, i + 1)])