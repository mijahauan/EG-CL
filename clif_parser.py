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
        # A robust tokenizer would be needed for production. This is simplified.
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
        
        # --- LOGICAL OPERATORS (handle recursion first) ---
        if operator == 'exists':
            # '(exists (vars...) body)'
            # The variables are noted, but identity is established by the atomic sentences.
            # We first parse the body to establish those identities.
            self._parse_expression(expr[2], context_id)
        
        elif operator == 'and':
            # '(and clause1 clause2 ...)' - parse all clauses recursively.
            for clause in expr[1:]:
                self._parse_expression(clause, context_id)
        
        elif operator == 'not':
            # '(not body)' - create a new cut and parse the body inside it.
            cut_id = self.editor.add_cut(parent_id=context_id)
            self._parse_expression(expr[1], cut_id)
        
        # --- ATOMIC PREDICATE (base case) ---
        else:
            predicate_name = expr[0]
            variable_names = expr[1:]
            
            # Create the logical predicate in the current context.
            pred_id = self.editor.add_predicate(predicate_name, len(variable_names), parent_id=context_id)
            pred = self.model.get_object(pred_id)
            
            # Connect hooks to corresponding Lines of Identity.
            for i, var_name in enumerate(variable_names):
                line_id = self.variable_map.get(var_name)
                # If this is the first time we see this variable, create its Line of Identity.
                if line_id is None:
                    line = LineOfIdentity()
                    self.model.add_object(line)
                    line_id = line.id
                    self.variable_map[var_name] = line_id
                
                # Logically connect the hook to the line.
                pred.hooks[i + 1] = line_id
                # Create the visual ligature segment for this connection.
                self.editor.connect([(pred_id, i + 1)])