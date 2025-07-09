"""
CL (Common Logic) Lexer and Parser implementation.

This module provides functionality for tokenizing and parsing CL expressions,
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

class CLLexer:
    """Tokenizer for CL (CLIF dialect) expressions."""
    
    # Token types
    TOKEN_LPAREN = "LPAREN"          # (
    TOKEN_RPAREN = "RPAREN"          # )
    TOKEN_AND = "AND"                # and
    TOKEN_OR = "OR"                  # or
    TOKEN_NOT = "NOT"                # not
    TOKEN_IF = "IF"                  # if
    TOKEN_IFF = "IFF"                # iff
    TOKEN_EXISTS = "EXISTS"          # exists
    TOKEN_FORALL = "FORALL"          # forall
    TOKEN_EQUALS = "EQUALS"          # =
    TOKEN_IDENTIFIER = "IDENTIFIER"  # Any other identifier
    TOKEN_WHITESPACE = "WHITESPACE"  # Spaces, tabs, newlines
    TOKEN_ERROR = "ERROR"            # Invalid token
    
    def __init__(self):
        """Initialize the lexer."""
        # Token patterns
        self.token_specs = [
            (self.TOKEN_WHITESPACE, r'\s+'),
            (self.TOKEN_LPAREN, r'\('),
            (self.TOKEN_RPAREN, r'\)'),
            (self.TOKEN_AND, r'and'),
            (self.TOKEN_OR, r'or'),
            (self.TOKEN_NOT, r'not'),
            (self.TOKEN_IF, r'if'),
            (self.TOKEN_IFF, r'iff'),
            (self.TOKEN_EXISTS, r'exists'),
            (self.TOKEN_FORALL, r'forall'),
            (self.TOKEN_EQUALS, r'='),
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
            text (str): The CL expression to tokenize
            
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


class CLParser:
    """Parser for CL (CLIF dialect) expressions."""
    
    def __init__(self):
        """Initialize the parser."""
        self.lexer = CLLexer()
        self.tokens = []
        self.current_token_idx = 0
        self.errors = []
        self.variables = set()  # Track variables for scope checking
    
    def parse(self, text):
        """
        Parse CL text and return an AST or errors.
        
        Args:
            text (str): The CL expression to parse
            
        Returns:
            ProcessingResult: Result of parsing
        """
        # Reset parser state
        self.tokens = self.lexer.tokenize(text)
        self.current_token_idx = 0
        self.errors = []
        self.variables = set()
        
        # Parse the expression
        try:
            ast = self.parse_expression()
            
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
        Parse a complete CL expression.
        
        Returns:
            Node: Root node of the AST
        """
        # A CL expression is a list of sentences
        nodes = []
        
        while self.current_token_idx < len(self.tokens):
            if self.match(CLLexer.TOKEN_LPAREN):
                # Parse sentence
                sentence = self.parse_sentence()
                nodes.append(sentence)
            else:
                # Unexpected token
                token_type, value, position = self.current_token()
                self.add_error(
                    ERROR_SYNTAX,
                    f"Unexpected token '{value}', expected '('",
                    position,
                    ["CL expressions must start with '('"]
                )
                self.advance()  # Skip the unexpected token
        
        # Create a root node to hold all the nodes
        return Node("EXPRESSION", children=nodes)
    
    def parse_sentence(self):
        """
        Parse a CL sentence: (predicate arg1 arg2 ...) or logical expression.
        
        Returns:
            Node: Sentence node
        """
        # We've already consumed the '('
        position = self.previous_position()
        
        # Check for logical operators
        if self.match(CLLexer.TOKEN_AND):
            return self.parse_and_expression(position)
        elif self.match(CLLexer.TOKEN_OR):
            return self.parse_or_expression(position)
        elif self.match(CLLexer.TOKEN_NOT):
            return self.parse_not_expression(position)
        elif self.match(CLLexer.TOKEN_IF):
            return self.parse_if_expression(position)
        elif self.match(CLLexer.TOKEN_IFF):
            return self.parse_iff_expression(position)
        elif self.match(CLLexer.TOKEN_EXISTS):
            return self.parse_exists_expression(position)
        elif self.match(CLLexer.TOKEN_FORALL):
            return self.parse_forall_expression(position)
        elif self.match(CLLexer.TOKEN_EQUALS):
            return self.parse_equals_expression(position)
        
        # Parse atomic sentence (predicate with arguments)
        return self.parse_atomic_sentence(position)
    
    def parse_atomic_sentence(self, position):
        """
        Parse an atomic sentence: (predicate arg1 arg2 ...)
        
        Args:
            position (tuple): Position of the opening parenthesis
            
        Returns:
            Node: Relation node
        """
        # Parse predicate
        predicate = None
        if self.match(CLLexer.TOKEN_IDENTIFIER):
            predicate = self.previous_value()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected predicate, found '{self.current_value()}'",
                self.current_position(),
                ["Atomic sentences must start with a predicate"]
            )
        
        # Parse arguments
        args = []
        while (self.current_token_idx < len(self.tokens) and 
               self.current_type() != CLLexer.TOKEN_RPAREN):
            
            # Parse argument (identifier)
            if self.match(CLLexer.TOKEN_IDENTIFIER):
                args.append(self.previous_value())
            # Parse nested expression
            elif self.match(CLLexer.TOKEN_LPAREN):
                nested = self.parse_sentence()
                args.append(nested)
            else:
                self.add_error(
                    ERROR_SYNTAX,
                    f"Expected argument, found '{self.current_value()}'",
                    self.current_position(),
                    ["Arguments must be identifiers or nested expressions"]
                )
                self.advance()  # Skip the unexpected token
        
        # Expect closing parenthesis
        if not self.match(CLLexer.TOKEN_RPAREN):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ')', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close parentheses"]
            )
        
        # Create relation node
        return Node(NODE_RELATION, {
            "type": predicate,
            "args": args
        }, position=position)
    
    def parse_and_expression(self, position):
        """
        Parse an 'and' expression: (and expr1 expr2 ...)
        
        Args:
            position (tuple): Position of the opening parenthesis
            
        Returns:
            Node: And node
        """
        # Parse subexpressions
        expressions = []
        while (self.current_token_idx < len(self.tokens) and 
               self.current_type() != CLLexer.TOKEN_RPAREN):
            
            if self.match(CLLexer.TOKEN_LPAREN):
                expr = self.parse_sentence()
                expressions.append(expr)
            else:
                self.add_error(
                    ERROR_SYNTAX,
                    f"Expected '(', found '{self.current_value()}'",
                    self.current_position(),
                    ["'and' expressions must contain subexpressions"]
                )
                self.advance()  # Skip the unexpected token
        
        # Expect closing parenthesis
        if not self.match(CLLexer.TOKEN_RPAREN):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ')', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close parentheses"]
            )
        
        # Create and node
        return Node("AND", None, expressions, position=position)
    
    def parse_or_expression(self, position):
        """
        Parse an 'or' expression: (or expr1 expr2 ...)
        
        Args:
            position (tuple): Position of the opening parenthesis
            
        Returns:
            Node: Or node
        """
        # Parse subexpressions
        expressions = []
        while (self.current_token_idx < len(self.tokens) and 
               self.current_type() != CLLexer.TOKEN_RPAREN):
            
            if self.match(CLLexer.TOKEN_LPAREN):
                expr = self.parse_sentence()
                expressions.append(expr)
            else:
                self.add_error(
                    ERROR_SYNTAX,
                    f"Expected '(', found '{self.current_value()}'",
                    self.current_position(),
                    ["'or' expressions must contain subexpressions"]
                )
                self.advance()  # Skip the unexpected token
        
        # Expect closing parenthesis
        if not self.match(CLLexer.TOKEN_RPAREN):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ')', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close parentheses"]
            )
        
        # Create or node
        return Node("OR", None, expressions, position=position)
    
    def parse_not_expression(self, position):
        """
        Parse a 'not' expression: (not expr)
        
        Args:
            position (tuple): Position of the opening parenthesis
            
        Returns:
            Node: Not node
        """
        # Parse subexpression
        if self.match(CLLexer.TOKEN_LPAREN):
            expr = self.parse_sentence()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected '(', found '{self.current_value()}'",
                self.current_position(),
                ["'not' expressions must contain a subexpression"]
            )
            expr = None
        
        # Expect closing parenthesis
        if not self.match(CLLexer.TOKEN_RPAREN):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ')', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close parentheses"]
            )
        
        # Create not node
        return Node(NODE_NEGATION, None, [expr] if expr else [], position=position)
    
    def parse_if_expression(self, position):
        """
        Parse an 'if' expression: (if antecedent consequent)
        
        Args:
            position (tuple): Position of the opening parenthesis
            
        Returns:
            Node: If node
        """
        # Parse antecedent
        antecedent = None
        if self.match(CLLexer.TOKEN_LPAREN):
            antecedent = self.parse_sentence()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected '(', found '{self.current_value()}'",
                self.current_position(),
                ["'if' expressions must have an antecedent"]
            )
        
        # Parse consequent
        consequent = None
        if self.match(CLLexer.TOKEN_LPAREN):
            consequent = self.parse_sentence()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected '(', found '{self.current_value()}'",
                self.current_position(),
                ["'if' expressions must have a consequent"]
            )
        
        # Expect closing parenthesis
        if not self.match(CLLexer.TOKEN_RPAREN):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ')', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close parentheses"]
            )
        
        # Create if node
        children = []
        if antecedent:
            children.append(antecedent)
        if consequent:
            children.append(consequent)
        
        return Node("IF", None, children, position=position)
    
    def parse_iff_expression(self, position):
        """
        Parse an 'iff' expression: (iff expr1 expr2)
        
        Args:
            position (tuple): Position of the opening parenthesis
            
        Returns:
            Node: Iff node
        """
        # Parse first expression
        expr1 = None
        if self.match(CLLexer.TOKEN_LPAREN):
            expr1 = self.parse_sentence()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected '(', found '{self.current_value()}'",
                self.current_position(),
                ["'iff' expressions must have two subexpressions"]
            )
        
        # Parse second expression
        expr2 = None
        if self.match(CLLexer.TOKEN_LPAREN):
            expr2 = self.parse_sentence()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected '(', found '{self.current_value()}'",
                self.current_position(),
                ["'iff' expressions must have two subexpressions"]
            )
        
        # Expect closing parenthesis
        if not self.match(CLLexer.TOKEN_RPAREN):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ')', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close parentheses"]
            )
        
        # Create iff node
        children = []
        if expr1:
            children.append(expr1)
        if expr2:
            children.append(expr2)
        
        return Node("IFF", None, children, position=position)
    
    def parse_exists_expression(self, position):
        """
        Parse an 'exists' expression: (exists (var1 var2 ...) expr)
        
        Args:
            position (tuple): Position of the opening parenthesis
            
        Returns:
            Node: Exists node
        """
        # Parse variable list
        variables = []
        if self.match(CLLexer.TOKEN_LPAREN):
            # Parse variables
            while (self.current_token_idx < len(self.tokens) and 
                   self.current_type() != CLLexer.TOKEN_RPAREN):
                
                if self.match(CLLexer.TOKEN_LPAREN):
                    # Parse typed variable: (var Type)
                    if self.match(CLLexer.TOKEN_IDENTIFIER):
                        var_name = self.previous_value()
                        variables.append(var_name)
                        self.variables.add(var_name)
                        
                        # Parse type
                        if self.match(CLLexer.TOKEN_IDENTIFIER):
                            var_type = self.previous_value()
                        else:
                            self.add_error(
                                ERROR_SYNTAX,
                                f"Expected type, found '{self.current_value()}'",
                                self.current_position(),
                                ["Typed variables must have a type"]
                            )
                    
                    # Expect closing parenthesis for typed variable
                    if not self.match(CLLexer.TOKEN_RPAREN):
                        self.add_error(
                            ERROR_SYNTAX,
                            f"Expected ')', found '{self.current_value()}'",
                            self.current_position(),
                            ["Make sure to close parentheses for typed variables"]
                        )
                
                elif self.match(CLLexer.TOKEN_IDENTIFIER):
                    # Parse untyped variable
                    var_name = self.previous_value()
                    variables.append(var_name)
                    self.variables.add(var_name)
                
                else:
                    self.add_error(
                        ERROR_SYNTAX,
                        f"Expected variable, found '{self.current_value()}'",
                        self.current_position(),
                        ["Variables must be identifiers"]
                    )
                    self.advance()  # Skip the unexpected token
            
            # Expect closing parenthesis for variable list
            if not self.match(CLLexer.TOKEN_RPAREN):
                self.add_error(
                    ERROR_SYNTAX,
                    f"Expected ')', found '{self.current_value()}'",
                    self.current_position(),
                    ["Make sure to close parentheses for variable list"]
                )
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected '(', found '{self.current_value()}'",
                self.current_position(),
                ["'exists' expressions must have a variable list"]
            )
        
        # Parse body expression
        body = None
        if self.match(CLLexer.TOKEN_LPAREN):
            body = self.parse_sentence()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected '(', found '{self.current_value()}'",
                self.current_position(),
                ["'exists' expressions must have a body expression"]
            )
        
        # Expect closing parenthesis for exists expression
        if not self.match(CLLexer.TOKEN_RPAREN):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ')', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close parentheses for 'exists' expression"]
            )
        
        # Create exists node
        return Node(NODE_QUANTIFIER, {
            "type": QUANTIFIER_EXISTENTIAL,
            "variables": variables
        }, [body] if body else [], position=position)
    
    def parse_forall_expression(self, position):
        """
        Parse a 'forall' expression: (forall (var1 var2 ...) expr)
        
        Args:
            position (tuple): Position of the opening parenthesis
            
        Returns:
            Node: Forall node
        """
        # Parse variable list
        variables = []
        if self.match(CLLexer.TOKEN_LPAREN):
            # Parse variables
            while (self.current_token_idx < len(self.tokens) and 
                   self.current_type() != CLLexer.TOKEN_RPAREN):
                
                if self.match(CLLexer.TOKEN_LPAREN):
                    # Parse typed variable: (var Type)
                    if self.match(CLLexer.TOKEN_IDENTIFIER):
                        var_name = self.previous_value()
                        variables.append(var_name)
                        self.variables.add(var_name)
                        
                        # Parse type
                        if self.match(CLLexer.TOKEN_IDENTIFIER):
                            var_type = self.previous_value()
                        else:
                            self.add_error(
                                ERROR_SYNTAX,
                                f"Expected type, found '{self.current_value()}'",
                                self.current_position(),
                                ["Typed variables must have a type"]
                            )
                    
                    # Expect closing parenthesis for typed variable
                    if not self.match(CLLexer.TOKEN_RPAREN):
                        self.add_error(
                            ERROR_SYNTAX,
                            f"Expected ')', found '{self.current_value()}'",
                            self.current_position(),
                            ["Make sure to close parentheses for typed variables"]
                        )
                
                elif self.match(CLLexer.TOKEN_IDENTIFIER):
                    # Parse untyped variable
                    var_name = self.previous_value()
                    variables.append(var_name)
                    self.variables.add(var_name)
                
                else:
                    self.add_error(
                        ERROR_SYNTAX,
                        f"Expected variable, found '{self.current_value()}'",
                        self.current_position(),
                        ["Variables must be identifiers"]
                    )
                    self.advance()  # Skip the unexpected token
            
            # Expect closing parenthesis for variable list
            if not self.match(CLLexer.TOKEN_RPAREN):
                self.add_error(
                    ERROR_SYNTAX,
                    f"Expected ')', found '{self.current_value()}'",
                    self.current_position(),
                    ["Make sure to close parentheses for variable list"]
                )
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected '(', found '{self.current_value()}'",
                self.current_position(),
                ["'forall' expressions must have a variable list"]
            )
        
        # Parse body expression
        body = None
        if self.match(CLLexer.TOKEN_LPAREN):
            body = self.parse_sentence()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected '(', found '{self.current_value()}'",
                self.current_position(),
                ["'forall' expressions must have a body expression"]
            )
        
        # Expect closing parenthesis for forall expression
        if not self.match(CLLexer.TOKEN_RPAREN):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ')', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close parentheses for 'forall' expression"]
            )
        
        # Create forall node
        return Node(NODE_QUANTIFIER, {
            "type": QUANTIFIER_UNIVERSAL,
            "variables": variables
        }, [body] if body else [], position=position)
    
    def parse_equals_expression(self, position):
        """
        Parse an equals expression: (= term1 term2)
        
        Args:
            position (tuple): Position of the opening parenthesis
            
        Returns:
            Node: Equals node
        """
        # Parse first term
        term1 = None
        if self.match(CLLexer.TOKEN_IDENTIFIER):
            term1 = self.previous_value()
        elif self.match(CLLexer.TOKEN_LPAREN):
            term1 = self.parse_sentence()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected term, found '{self.current_value()}'",
                self.current_position(),
                ["Equals expressions must have two terms"]
            )
        
        # Parse second term
        term2 = None
        if self.match(CLLexer.TOKEN_IDENTIFIER):
            term2 = self.previous_value()
        elif self.match(CLLexer.TOKEN_LPAREN):
            term2 = self.parse_sentence()
        else:
            self.add_error(
                ERROR_SYNTAX,
                f"Expected term, found '{self.current_value()}'",
                self.current_position(),
                ["Equals expressions must have two terms"]
            )
        
        # Expect closing parenthesis
        if not self.match(CLLexer.TOKEN_RPAREN):
            self.add_error(
                ERROR_SYNTAX,
                f"Expected ')', found '{self.current_value()}'",
                self.current_position(),
                ["Make sure to close parentheses"]
            )
        
        # Create equals node
        return Node("EQUALS", None, [term1, term2] if term1 and term2 else [], position=position)
    
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


class CLValidator:
    """Validator for CL syntax and semantics."""
    
    def __init__(self):
        """Initialize the validator."""
        pass
    
    def validate(self, ast):
        """
        Validate the AST against CL rules.
        
        Args:
            ast (Node): The AST to validate
            
        Returns:
            list: List of errors, empty if valid
        """
        errors = []
        
        # Implement validation rules here
        
        return errors


class CLErrorHandler:
    """Handler for CL syntax and semantic errors."""
    
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
