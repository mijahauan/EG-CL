"""
CGIF Lexer and Parser implementation.

This module provides functionality for tokenizing and parsing CGIF expressions,
validating syntax, and generating helpful error messages.
"""

import re
from .common import (
    Node, Error, ProcessingResult,
    NODE_CONCEPT, NODE_RELATION, NODE_QUANTIFIER, NODE_CONTEXT, NODE_NEGATION, 
    NODE_FUNCTION, NODE_COREFERENCE,
    ERROR_SYNTAX, ERROR_SEMANTIC, ERROR_REFERENCE,
    QUANTIFIER_EXISTENTIAL, QUANTIFIER_UNIVERSAL
)

class CGIFLexer:
    """Tokenizer for CGIF expressions."""
    
    # Token types
    TOKEN_LBRACKET = "LBRACKET"      # [
    TOKEN_RBRACKET = "RBRACKET"      # ]
    TOKEN_LPAREN = "LPAREN"          # (
    TOKEN_RPAREN = "RPAREN"          # )
    TOKEN_COLON = "COLON"            # :
    TOKEN_PIPE = "PIPE"              # |
    TOKEN_NEGATION = "NEGATION"      # ~
    TOKEN_DEFINING_LABEL = "DEFINING_LABEL"  # *x
    TOKEN_BOUND_LABEL = "BOUND_LABEL"        # ?x
    TOKEN_UNIVERSAL = "UNIVERSAL"    # @every
    TOKEN_IDENTIFIER = "IDENTIFIER"  # Any other identifier
    TOKEN_WHITESPACE = "WHITESPACE"  # Spaces, tabs, newlines
    TOKEN_ERROR = "ERROR"            # Invalid token
    
    def __init__(self):
        """Initialize the lexer."""
        # Token patterns
        self.token_specs = [
            (self.TOKEN_WHITESPACE, r'\s+'),
            (self.TOKEN_LBRACKET, r'\['),
            (self.TOKEN_RBRACKET, r'\]'),
            (self.TOKEN_LPAREN, r'\('),
            (self.TOKEN_RPAREN, r'\)'),
            (self.TOKEN_COLON, r':'),
            (self.TOKEN_PIPE, r'\|'),
            (self.TOKEN_NEGATION, r'~'),
            (self.TOKEN_UNIVERSAL, r'@every'),
            (self.TOKEN_DEFINING_LABEL, r'\*[a-zA-Z0-9_]+'),
            (self.TOKEN_BOUND_LABEL, r'\?[a-zA-Z0-9_]+'),
            (self.TOKEN_IDENTIFIER, r'[a-zA-Z0-9_]+'),
            (self.TOKEN_ERROR, r'.'),  # Any other character
        ]
        
        # Build the regex pattern
        self.pattern = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.token_specs)
        self.regex = re.compile(self.pattern)
    
    def tokenize(self, text):
        """
        Tokenize the input text.
        
        Args:
            text (str): The CGIF expression to tokenize
            
        Returns:
            list: List of (token_type, value, position) tuples
        """
        tokens = []
        line_num = 1
        line_start = 0
        
        for match in self.regex.finditer(text):
            token_type = match.lastgroup
            value = match.group()
            start = match.start()
            end = match.end()
            column = start - line_start + 1
            position = (line_num, column)
            
            # Skip whitespace tokens
            if token_type == self.TOKEN_WHITESPACE:
                # Update line number and line start for newlines
                newlines = value.count('\n')
                if newlines > 0:
                    line_num += newlines
                    line_start = start + value.rindex('\n') + 1
                continue
            
            # Add token to the list
            tokens.append((token_type, value, position))
        
        return tokens


class CGIFParser:
    """Parser for CGIF expressions."""
    
    def __init__(self):
        """Initialize the parser."""
        self.lexer = CGIFLexer()
        self.tokens = []
        self.current_token_idx = 0
        self.errors = []
        self.coreference_map = {}  # Maps defining labels to their nodes
    
    def parse(self, text):
        """
        Parse CGIF text and return an AST or errors.
        
        Args:
            text (str): The CGIF expression to parse
            
        Returns:
            ProcessingResult: Result of parsing
        """
        # Reset parser state
        self.tokens = self.lexer.tokenize(text)
        self.current_token_idx = 0
        self.errors = []
        self.coreference_map = {}
        
        # Parse the expression
        try:
            ast = self.parse_expression()
            
            # Check for unresolved references
            self.check_references()
            
            if self.errors:
                return ProcessingResult(False, errors=self.errors)
            else:
                return ProcessingResult(True, ast=ast)
        except Exception as e:
            # Add unexpected error
            self.add_error(ERROR_SYNTAX, f"Unexpected error: {str(e)}", self.current_position())
            return ProcessingResult(False, errors=self.errors)
    
    def parse_expression(self):
        """
        Parse a complete CGIF expression.
        
        Returns:
            Node: Root node of the AST
        """
        # A CGIF expression is a list of concepts and relations
        nodes = []
        
        while self.current_token_idx < len(self.tokens):
            if self.match(CGIFLexer.TOKEN_LBRACKET):
                # Parse concept
                concept = self.parse_concept()
                nodes.append(concept)
            elif self.match(CGIFLexer.TOKEN_LPAREN):
                # Parse relation
                relation = self.parse_relation()
                nodes.append(relation)
            elif self.match(CGIFLexer.TOKEN_NEGATION):
                # Parse negation
                negation = self.parse_negation()
                nodes.append(negation)
            else:
                # Unexpected token
                token_type, value, position = self.current_token()
                self.add_error(
                    ERROR_SYNTAX,
                    f"Unexpected token '{value}', expected '[', '(', or '~'",
                    position,
                    ["Try starting with a concept '[...]' or relation '(...)'"]
                )
                self.advance()  # Skip the unexpected token
        
        # Create a root node to hold all the nodes
        return Node("EXPRESSION", children=nodes)
    
    def parse_concept(self):
        """
        Parse a concept node: [Type: Referent] or [*x] or [:Referent]
        
        Returns:
            Node: Concept node
        """
        # We've already consumed the '['
        position = self.previous_position()
        
        # Check for negation in context
        is_negated = False
        if self.match(CGIFLexer.TOKEN_NEGATION):
            is_negated = True
        
        # Parse type label if present
        type_label = None
        if self.match(CGIFLexer.TOKEN_IDENTIFIER):
            type_label = self.previous_value()
        
        # Parse colon if present
        has_colon = self.match(CGIFLexer.TOKEN_COLON)
        
        # Parse referent if present
        referent = None
        defining_label = None
        bound_label = None
        universal = False
        
        # Check for universal quantifier
        if self.match(CGIFLexer.TOKEN_UNIVERSAL):
            universal = True
        
        # Check for defining label
        if self.match(CGIFLexer.TOKEN_DEFINING_LABEL):
            defining_label = self.previous_value()
            referent = defining_label
        # Check for bound label
        elif self.match(CGIFLexer.TOKEN_BOUND_LABEL):
            bound_label = self.previous_value()
            referent = bound_label
        # Check for identifier referent
        elif self.match(CGIFLexer.TOKEN_IDENTIFIER):
            referent = self.previous_value()
        
        # Expect closing bracket
        if not self.match(CGIFLexer.TOKEN_RBRACKET):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ']', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close concept brackets"]
            )
        
        # Create concept node
        concept = Node(NODE_CONCEPT, {
            "type_label": type_label,
            "referent": referent,
            "defining_label": defining_label,
            "bound_label": bound_label,
            "universal": universal
        }, position=position)
        
        # If this is a defining label, add it to the coreference map
        if defining_label:
            self.coreference_map[defining_label] = concept
            
            # If universal, add quantifier node
            if universal:
                return Node(NODE_QUANTIFIER, QUANTIFIER_UNIVERSAL, [concept], position=position)
            else:
                return Node(NODE_QUANTIFIER, QUANTIFIER_EXISTENTIAL, [concept], position=position)
        
        # If this is a negated context, wrap in negation node
        if is_negated:
            return Node(NODE_NEGATION, None, [concept], position=position)
        
        return concept
    
    def parse_relation(self):
        """
        Parse a relation node: (RelationType Arg1 Arg2 ... | Result)
        
        Returns:
            Node: Relation node
        """
        # We've already consumed the '('
        position = self.previous_position()
        
        # Parse relation type
        relation_type = None
        if self.match(CGIFLexer.TOKEN_IDENTIFIER):
            relation_type = self.previous_value()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected relation type, found '{self.current_value()}'",
                self.current_position(),
                ["Relations must start with a type identifier"]
            )
        
        # Parse arguments
        args = []
        while (self.current_token_idx < len(self.tokens) and 
               self.current_type() != CGIFLexer.TOKEN_RPAREN and
               self.current_type() != CGIFLexer.TOKEN_PIPE):
            
            # Parse argument (identifier or label)
            if self.match(CGIFLexer.TOKEN_IDENTIFIER):
                args.append(self.previous_value())
            elif self.match(CGIFLexer.TOKEN_DEFINING_LABEL):
                args.append(self.previous_value())
            elif self.match(CGIFLexer.TOKEN_BOUND_LABEL):
                args.append(self.previous_value())
            else:
                self.add_error(
                    ERROR_SYNTAX,
                    f"Expected argument, found '{self.current_value()}'",
                    self.current_position(),
                    ["Arguments must be identifiers or labels"]
                )
                self.advance()  # Skip the unexpected token
        
        # Check for function (actor) with output
        results = []
        if self.match(CGIFLexer.TOKEN_PIPE):
            # Parse results
            while (self.current_token_idx < len(self.tokens) and 
                   self.current_type() != CGIFLexer.TOKEN_RPAREN):
                
                # Parse result (identifier or label)
                if self.match(CGIFLexer.TOKEN_IDENTIFIER):
                    results.append(self.previous_value())
                elif self.match(CGIFLexer.TOKEN_DEFINING_LABEL):
                    results.append(self.previous_value())
                elif self.match(CGIFLexer.TOKEN_BOUND_LABEL):
                    results.append(self.previous_value())
                else:
                    self.add_error(
                        ERROR_SYNTAX,
                        f"Expected result, found '{self.current_value()}'",
                        self.current_position(),
                        ["Results must be identifiers or labels"]
                    )
                    self.advance()  # Skip the unexpected token
        
        # Expect closing parenthesis
        if not self.match(CGIFLexer.TOKEN_RPAREN):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ')', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close relation parentheses"]
            )
        
        # Create relation or function node
        if results:
            return Node(NODE_FUNCTION, {
                "type": relation_type,
                "args": args,
                "results": results
            }, position=position)
        else:
            return Node(NODE_RELATION, {
                "type": relation_type,
                "args": args
            }, position=position)
    
    def parse_negation(self):
        """
        Parse a negation: ~[...]
        
        Returns:
            Node: Negation node
        """
        # We've already consumed the '~'
        position = self.previous_position()
        
        # Expect opening bracket
        if not self.match(CGIFLexer.TOKEN_LBRACKET):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected '[' after '~', found '{self.current_value()}'",
                self.current_position(),
                ["Negation must be followed by a context in brackets"]
            )
            return Node(NODE_NEGATION, None, [], position=position)
        
        # Parse the context
        context = self.parse_context()
        
        return Node(NODE_NEGATION, None, [context], position=position)
    
    def parse_context(self):
        """
        Parse a context: [...] (contents of a context)
        
        Returns:
            Node: Context node
        """
        # We've already consumed the '['
        position = self.previous_position()
        
        # Parse contents (concepts and relations)
        contents = []
        while (self.current_token_idx < len(self.tokens) and 
               self.current_type() != CGIFLexer.TOKEN_RBRACKET):
            
            if self.match(CGIFLexer.TOKEN_LBRACKET):
                # Parse nested concept
                concept = self.parse_concept()
                contents.append(concept)
            elif self.match(CGIFLexer.TOKEN_LPAREN):
                # Parse relation
                relation = self.parse_relation()
                contents.append(relation)
            elif self.match(CGIFLexer.TOKEN_NEGATION):
                # Parse negation
                negation = self.parse_negation()
                contents.append(negation)
            else:
                # Unexpected token
                token_type, value, position = self.current_token()
                self.add_error(
                    ERROR_SYNTAX,
                    f"Unexpected token '{value}' in context, expected '[', '(', or '~'",
                    position,
                    ["Context can contain concepts, relations, or negations"]
                )
                self.advance()  # Skip the unexpected token
        
        # Expect closing bracket
        if not self.match(CGIFLexer.TOKEN_RBRACKET):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ']', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close context brackets"]
            )
        
        return Node(NODE_CONTEXT, None, contents, position=position)
    
    def check_references(self):
        """Check that all bound labels refer to existing defining labels."""
        # Collect all bound labels
        bound_labels = set()
        self._collect_bound_labels(bound_labels)
        
        # Check each bound label
        for label in bound_labels:
            # Convert ?x to *x
            defining_label = '*' + label[1:]
            if defining_label not in self.coreference_map:
                self.add_error(
                    ERROR_REFERENCE,
                    f"Bound label '{label}' has no corresponding defining label '{defining_label}'",
                    None,
                    [f"Add a concept with defining label '{defining_label}'"]
                )
    
    def _collect_bound_labels(self, bound_labels, node=None):
        """
        Recursively collect all bound labels in the AST.
        
        Args:
            bound_labels (set): Set to collect bound labels
            node (Node, optional): Current node to process
        """
        if node is None:
            # Start with the root node
            if hasattr(self, 'root') and self.root:
                self._collect_bound_labels(bound_labels, self.root)
            return
        
        # Check node type
        if node.node_type == NODE_CONCEPT:
            if node.value.get('bound_label'):
                bound_labels.add(node.value['bound_label'])
        elif node.node_type == NODE_RELATION:
            for arg in node.value['args']:
                if arg.startswith('?'):
                    bound_labels.add(arg)
        elif node.node_type == NODE_FUNCTION:
            for arg in node.value['args']:
                if arg.startswith('?'):
                    bound_labels.add(arg)
            for result in node.value['results']:
                if result.startswith('?'):
                    bound_labels.add(result)
        
        # Process children
        for child in node.children:
            self._collect_bound_labels(bound_labels, child)
    
    # Helper methods for token handling
    
    def current_token(self):
        """Get the current token."""
        if self.current_token_idx < len(self.tokens):
            return self.tokens[self.current_token_idx]
        return None, None, None
    
    def current_type(self):
        """Get the type of the current token."""
        token_type, _, _ = self.current_token()
        return token_type
    
    def current_value(self):
        """Get the value of the current token."""
        _, value, _ = self.current_token()
        return value
    
    def current_position(self):
        """Get the position of the current token."""
        _, _, position = self.current_token()
        return position
    
    def previous_position(self):
        """Get the position of the previous token."""
        if self.current_token_idx > 0:
            _, _, position = self.tokens[self.current_token_idx - 1]
            return position
        return None
    
    def previous_value(self):
        """Get the value of the previous token."""
        if self.current_token_idx > 0:
            _, value, _ = self.tokens[self.current_token_idx - 1]
            return value
        return None
    
    def advance(self):
        """Advance to the next token."""
        self.current_token_idx += 1
        return self.current_token()
    
    def match(self, expected_type):
        """
        Check if the current token matches the expected type and advance if it does.
        
        Args:
            expected_type (str): The expected token type
            
        Returns:
            bool: True if the token matches, False otherwise
        """
        if self.current_type() == expected_type:
            self.advance()
            return True
        return False
    
    def add_error(self, error_type, message, position, suggestions=None):
        """
        Add an error to the error list.
        
        Args:
            error_type (str): Type of error
            message (str): Error message
            position (tuple): Position in source (line, column)
            suggestions (list, optional): Suggested corrections
        """
        self.errors.append(Error(error_type, message, position, suggestions))


class CGIFValidator:
    """Validator for CGIF syntax and semantics."""
    
    def __init__(self):
        """Initialize the validator."""
        pass
    
    def validate(self, ast):
        """
        Validate the AST against CGIF rules.
        
        Args:
            ast (Node): The AST to validate
            
        Returns:
            list: List of errors, empty if valid
        """
        errors = []
        
        # Implement validation rules here
        
        return errors


class CGIFErrorHandler:
    """Handler for CGIF syntax and semantic errors."""
    
    def __init__(self):
        """Initialize the error handler."""
        pass
    
    def suggest_corrections(self, error):
        """
        Suggest corrections for common errors.
        
        Args:
            error (Error): The error to suggest corrections for
            
        Returns:
            list: List of suggested corrections
        """
        suggestions = []
        
        # Implement correction suggestions here
        
        return suggestions
