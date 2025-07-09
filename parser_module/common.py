"""
Common data structures and utilities for CGIF and CL parsers.
"""

class Node:
    """Base class for AST nodes."""
    
    def __init__(self, node_type, value=None, children=None, position=None):
        """
        Initialize a new AST node.
        
        Args:
            node_type (str): Type of the node (e.g., CONCEPT, RELATION)
            value (any, optional): Value associated with the node
            children (list, optional): Child nodes
            position (tuple, optional): Position in source (line, column)
        """
        self.node_type = node_type
        self.value = value
        self.children = children or []
        self.position = position
    
    def __repr__(self):
        return f"Node({self.node_type}, {self.value}, {len(self.children)} children)"


class Error:
    """Class representing a syntax or semantic error."""
    
    def __init__(self, error_type, message, position, suggestions=None):
        """
        Initialize a new error.
        
        Args:
            error_type (str): Type of error (e.g., SYNTAX, SEMANTIC)
            message (str): Error message
            position (tuple): Position in source (line, column)
            suggestions (list, optional): Suggested corrections
        """
        self.error_type = error_type
        self.message = message
        self.position = position
        self.suggestions = suggestions or []
    
    def __repr__(self):
        return f"Error({self.error_type}, '{self.message}', {self.position})"


class ProcessingResult:
    """Class representing the result of processing an expression."""
    
    def __init__(self, success, ast=None, errors=None, output_text=None, latex_code=None):
        """
        Initialize a new processing result.
        
        Args:
            success (bool): Whether processing was successful
            ast (Node, optional): Abstract syntax tree if successful
            errors (list, optional): List of errors if unsuccessful
            output_text (str, optional): Formatted output text
            latex_code (str, optional): Generated LaTeX code
        """
        self.success = success
        self.ast = ast
        self.errors = errors or []
        self.output_text = output_text
        self.latex_code = latex_code
    
    def __repr__(self):
        if self.success:
            return f"ProcessingResult(success=True, ast={self.ast})"
        else:
            return f"ProcessingResult(success=False, errors={self.errors})"


# Node types
NODE_CONCEPT = "CONCEPT"
NODE_RELATION = "RELATION"
NODE_QUANTIFIER = "QUANTIFIER"
NODE_CONTEXT = "CONTEXT"
NODE_NEGATION = "NEGATION"
NODE_FUNCTION = "FUNCTION"
NODE_COREFERENCE = "COREFERENCE"

# Error types
ERROR_SYNTAX = "SYNTAX"
ERROR_SEMANTIC = "SEMANTIC"
ERROR_REFERENCE = "REFERENCE"

# Quantifier types
QUANTIFIER_EXISTENTIAL = "EXISTENTIAL"
QUANTIFIER_UNIVERSAL = "UNIVERSAL"
