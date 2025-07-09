"""
Main parser module that provides a unified interface for CGIF and CL parsing.
"""

from .cgif_parser import CGIFParser, CGIFValidator, CGIFErrorHandler
from .cl_parser import CLParser, CLValidator, CLErrorHandler
from .common import ProcessingResult

class Parser:
    """
    Unified parser interface for CGIF and CL expressions.
    
    This class provides a common interface for parsing both CGIF and CL
    expressions, handling syntax validation, and generating error messages.
    """
    
    # Expression types
    TYPE_CGIF = "CGIF"
    TYPE_CL = "CL"
    
    def __init__(self):
        """Initialize the parser."""
        self.cgif_parser = CGIFParser()
        self.cgif_validator = CGIFValidator()
        self.cgif_error_handler = CGIFErrorHandler()
        
        self.cl_parser = CLParser()
        self.cl_validator = CLValidator()
        self.cl_error_handler = CLErrorHandler()
    
    def parse(self, text, expression_type):
        """
        Parse an expression and return the result.
        
        Args:
            text (str): The expression to parse
            expression_type (str): The type of expression (CGIF or CL)
            
        Returns:
            ProcessingResult: Result of parsing
        """
        if expression_type == self.TYPE_CGIF:
            return self.parse_cgif(text)
        elif expression_type == self.TYPE_CL:
            return self.parse_cl(text)
        else:
            return ProcessingResult(
                False, 
                errors=[{
                    "error_type": "INVALID_TYPE",
                    "message": f"Invalid expression type: {expression_type}",
                    "position": None,
                    "suggestions": ["Use 'CGIF' or 'CL' as the expression type"]
                }]
            )
    
    def parse_cgif(self, text):
        """
        Parse a CGIF expression.
        
        Args:
            text (str): The CGIF expression to parse
            
        Returns:
            ProcessingResult: Result of parsing
        """
        # Parse the expression
        result = self.cgif_parser.parse(text)
        
        # If parsing was successful, validate the AST
        if result.success:
            errors = self.cgif_validator.validate(result.ast)
            if errors:
                result.success = False
                result.errors = errors
        
        return result
    
    def parse_cl(self, text):
        """
        Parse a CL expression.
        
        Args:
            text (str): The CL expression to parse
            
        Returns:
            ProcessingResult: Result of parsing
        """
        # Parse the expression
        result = self.cl_parser.parse(text)
        
        # If parsing was successful, validate the AST
        if result.success:
            errors = self.cl_validator.validate(result.ast)
            if errors:
                result.success = False
                result.errors = errors
        
        return result
    
    def suggest_corrections(self, error, expression_type):
        """
        Suggest corrections for an error.
        
        Args:
            error: The error to suggest corrections for
            expression_type (str): The type of expression (CGIF or CL)
            
        Returns:
            list: List of suggested corrections
        """
        if expression_type == self.TYPE_CGIF:
            return self.cgif_error_handler.suggest_corrections(error)
        elif expression_type == self.TYPE_CL:
            return self.cl_error_handler.suggest_corrections(error)
        else:
            return []
