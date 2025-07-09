"""
Translator module for converting between CGIF and CL expressions.

This module provides functionality for translating between CGIF and CL
representations while preserving semantic equivalence.
"""

from src.parser.common import (
    Node, ProcessingResult,
    NODE_CONCEPT, NODE_RELATION, NODE_QUANTIFIER, NODE_CONTEXT, NODE_NEGATION, 
    NODE_FUNCTION, NODE_COREFERENCE,
    QUANTIFIER_EXISTENTIAL, QUANTIFIER_UNIVERSAL
)

class CGIFtoCLTranslator:
    """Translator for converting CGIF to CL."""
    
    def __init__(self):
        """Initialize the translator."""
        self.variable_map = {}  # Maps CGIF coreference labels to CL variables
        self.next_var_id = 0    # Counter for generating unique variable names
    
    def translate(self, cgif_ast):
        """
        Translate a CGIF AST to a CL AST.
        
        Args:
            cgif_ast (Node): The CGIF AST to translate
            
        Returns:
            Node: The translated CL AST
        """
        # Reset state
        self.variable_map = {}
        self.next_var_id = 0
        
        # Translate the root node
        return self._translate_node(cgif_ast)
    
    def _translate_node(self, node):
        """
        Translate a CGIF node to a CL node.
        
        Args:
            node (Node): The CGIF node to translate
            
        Returns:
            Node: The translated CL node
        """
        if node.node_type == "EXPRESSION":
            # Translate expression (root node)
            return self._translate_expression(node)
        elif node.node_type == NODE_CONCEPT:
            # Translate concept
            return self._translate_concept(node)
        elif node.node_type == NODE_RELATION:
            # Translate relation
            return self._translate_relation(node)
        elif node.node_type == NODE_QUANTIFIER:
            # Translate quantifier
            return self._translate_quantifier(node)
        elif node.node_type == NODE_NEGATION:
            # Translate negation
            return self._translate_negation(node)
        elif node.node_type == NODE_CONTEXT:
            # Translate context
            return self._translate_context(node)
        elif node.node_type == NODE_FUNCTION:
            # Translate function
            return self._translate_function(node)
        else:
            # Unknown node type
            raise ValueError(f"Unknown node type: {node.node_type}")
    
    def _translate_expression(self, node):
        """
        Translate a CGIF expression to a CL expression.
        
        Args:
            node (Node): The CGIF expression node
            
        Returns:
            Node: The translated CL expression node
        """
        # First pass: collect all defining labels
        self._collect_defining_labels(node)
        
        # Translate all child nodes
        translated_children = []
        for child in node.children:
            translated = self._translate_node(child)
            if translated:
                if isinstance(translated, list):
                    translated_children.extend(translated)
                else:
                    translated_children.append(translated)
        
        # Create a new expression node
        return Node("EXPRESSION", None, translated_children, node.position)
    
    def _collect_defining_labels(self, node):
        """
        Collect all defining labels in the AST and map them to CL variables.
        
        Args:
            node (Node): The root node of the AST
        """
        if node.node_type == NODE_CONCEPT:
            # Check for defining label
            if node.value.get("defining_label"):
                label = node.value["defining_label"]
                if label not in self.variable_map:
                    var_name = f"x{self.next_var_id}"
                    self.next_var_id += 1
                    self.variable_map[label] = var_name
        
        # Process children
        for child in node.children:
            self._collect_defining_labels(child)
    
    def _translate_concept(self, node):
        """
        Translate a CGIF concept to a CL relation.
        
        Args:
            node (Node): The CGIF concept node
            
        Returns:
            Node: The translated CL relation node
        """
        type_label = node.value.get("type_label")
        referent = node.value.get("referent")
        defining_label = node.value.get("defining_label")
        bound_label = node.value.get("bound_label")
        
        if not type_label:
            # Untyped concept, just return the referent
            if defining_label:
                # This is a defining label, will be handled by quantifier
                return None
            elif bound_label:
                # This is a bound label, use the mapped variable
                var_name = self.variable_map.get(bound_label.replace("?", "*"), bound_label)
                return Node(NODE_RELATION, {
                    "type": "Thing",  # Default type
                    "args": [var_name]
                }, [], node.position)
            else:
                # Just a constant
                return Node(NODE_RELATION, {
                    "type": "Thing",  # Default type
                    "args": [referent]
                }, [], node.position)
        
        # Typed concept
        if defining_label:
            # This is a defining label, will be handled by quantifier
            return None
        elif bound_label:
            # This is a bound label, use the mapped variable
            var_name = self.variable_map.get(bound_label.replace("?", "*"), bound_label)
            return Node(NODE_RELATION, {
                "type": type_label,
                "args": [var_name]
            }, [], node.position)
        else:
            # Just a constant
            return Node(NODE_RELATION, {
                "type": type_label,
                "args": [referent]
            }, [], node.position)
    
    def _translate_relation(self, node):
        """
        Translate a CGIF relation to a CL relation.
        
        Args:
            node (Node): The CGIF relation node
            
        Returns:
            Node: The translated CL relation node
        """
        relation_type = node.value.get("type")
        args = node.value.get("args", [])
        
        # Map any bound labels to variables
        mapped_args = []
        for arg in args:
            if isinstance(arg, str) and arg.startswith("?"):
                # This is a bound label, use the mapped variable
                var_name = self.variable_map.get(arg.replace("?", "*"), arg)
                mapped_args.append(var_name)
            else:
                mapped_args.append(arg)
        
        return Node(NODE_RELATION, {
            "type": relation_type,
            "args": mapped_args
        }, [], node.position)
    
    def _translate_quantifier(self, node):
        """
        Translate a CGIF quantifier to a CL quantifier.
        
        Args:
            node (Node): The CGIF quantifier node
            
        Returns:
            Node: The translated CL quantifier node
        """
        quantifier_type = node.value
        
        # Get the concept node (should be the only child)
        if not node.children:
            return None
        
        concept = node.children[0]
        type_label = concept.value.get("type_label")
        defining_label = concept.value.get("defining_label")
        
        if not defining_label:
            # Not a proper quantifier
            return self._translate_node(concept)
        
        # Get the variable name
        var_name = self.variable_map.get(defining_label, defining_label)
        
        # Create the quantifier node
        if quantifier_type == QUANTIFIER_EXISTENTIAL:
            return Node(NODE_QUANTIFIER, {
                "type": QUANTIFIER_EXISTENTIAL,
                "variables": [var_name],
                "types": [type_label] if type_label else []
            }, [], node.position)
        else:  # QUANTIFIER_UNIVERSAL
            return Node(NODE_QUANTIFIER, {
                "type": QUANTIFIER_UNIVERSAL,
                "variables": [var_name],
                "types": [type_label] if type_label else []
            }, [], node.position)
    
    def _translate_negation(self, node):
        """
        Translate a CGIF negation to a CL negation.
        
        Args:
            node (Node): The CGIF negation node
            
        Returns:
            Node: The translated CL negation node
        """
        # Translate the child node
        if not node.children:
            return Node(NODE_NEGATION, None, [], node.position)
        
        child = self._translate_node(node.children[0])
        
        return Node(NODE_NEGATION, None, [child] if child else [], node.position)
    
    def _translate_context(self, node):
        """
        Translate a CGIF context to a CL expression.
        
        Args:
            node (Node): The CGIF context node
            
        Returns:
            Node: The translated CL expression node
        """
        # Translate all child nodes
        translated_children = []
        for child in node.children:
            translated = self._translate_node(child)
            if translated:
                if isinstance(translated, list):
                    translated_children.extend(translated)
                else:
                    translated_children.append(translated)
        
        # If there's only one child, return it directly
        if len(translated_children) == 1:
            return translated_children[0]
        
        # Otherwise, create an AND node
        return Node("AND", None, translated_children, node.position)
    
    def _translate_function(self, node):
        """
        Translate a CGIF function to a CL equals expression.
        
        Args:
            node (Node): The CGIF function node
            
        Returns:
            Node: The translated CL equals expression node
        """
        function_type = node.value.get("type")
        args = node.value.get("args", [])
        results = node.value.get("results", [])
        
        # Map any bound labels to variables
        mapped_args = []
        for arg in args:
            if isinstance(arg, str) and arg.startswith("?"):
                # This is a bound label, use the mapped variable
                var_name = self.variable_map.get(arg.replace("?", "*"), arg)
                mapped_args.append(var_name)
            else:
                mapped_args.append(arg)
        
        # Map any result labels to variables
        mapped_results = []
        for result in results:
            if isinstance(result, str) and result.startswith("?"):
                # This is a bound label, use the mapped variable
                var_name = self.variable_map.get(result.replace("?", "*"), result)
                mapped_results.append(var_name)
            elif isinstance(result, str) and result.startswith("*"):
                # This is a defining label, use the mapped variable
                var_name = self.variable_map.get(result, result)
                mapped_results.append(var_name)
            else:
                mapped_results.append(result)
        
        # Create a function application node
        function_node = Node("FUNCTION_CALL", {
            "name": function_type,
            "args": mapped_args
        }, [], node.position)
        
        # Create an equals node
        if mapped_results:
            return Node("EQUALS", None, [mapped_results[0], function_node], node.position)
        else:
            return function_node


class CLtoCGIFTranslator:
    """Translator for converting CL to CGIF."""
    
    def __init__(self):
        """Initialize the translator."""
        self.variable_map = {}  # Maps CL variables to CGIF coreference labels
        self.next_label_id = 0  # Counter for generating unique label names
    
    def translate(self, cl_ast):
        """
        Translate a CL AST to a CGIF AST.
        
        Args:
            cl_ast (Node): The CL AST to translate
            
        Returns:
            Node: The translated CGIF AST
        """
        # Reset state
        self.variable_map = {}
        self.next_label_id = 0
        
        # Translate the root node
        return self._translate_node(cl_ast)
    
    def _translate_node(self, node):
        """
        Translate a CL node to a CGIF node.
        
        Args:
            node (Node): The CL node to translate
            
        Returns:
            Node: The translated CGIF node
        """
        if node.node_type == "EXPRESSION":
            # Translate expression (root node)
            return self._translate_expression(node)
        elif node.node_type == NODE_RELATION:
            # Translate relation
            return self._translate_relation(node)
        elif node.node_type == NODE_QUANTIFIER:
            # Translate quantifier
            return self._translate_quantifier(node)
        elif node.node_type == NODE_NEGATION:
            # Translate negation
            return self._translate_negation(node)
        elif node.node_type == "AND":
            # Translate AND
            return self._translate_and(node)
        elif node.node_type == "OR":
            # Translate OR
            return self._translate_or(node)
        elif node.node_type == "IF":
            # Translate IF
            return self._translate_if(node)
        elif node.node_type == "IFF":
            # Translate IFF
            return self._translate_iff(node)
        elif node.node_type == "EQUALS":
            # Translate EQUALS
            return self._translate_equals(node)
        elif node.node_type == "FUNCTION_CALL":
            # Translate FUNCTION_CALL
            return self._translate_function_call(node)
        else:
            # Unknown node type
            raise ValueError(f"Unknown node type: {node.node_type}")
    
    def _translate_expression(self, node):
        """
        Translate a CL expression to a CGIF expression.
        
        Args:
            node (Node): The CL expression node
            
        Returns:
            Node: The translated CGIF expression node
        """
        # First pass: collect all variables
        self._collect_variables(node)
        
        # Translate all child nodes
        translated_children = []
        for child in node.children:
            translated = self._translate_node(child)
            if translated:
                if isinstance(translated, list):
                    translated_children.extend(translated)
                else:
                    translated_children.append(translated)
        
        # Create a new expression node
        return Node("EXPRESSION", None, translated_children, node.position)
    
    def _collect_variables(self, node):
        """
        Collect all variables in the AST and map them to CGIF coreference labels.
        
        Args:
            node (Node): The root node of the AST
        """
        if node.node_type == NODE_QUANTIFIER:
            # Get variables from quantifier
            variables = node.value.get("variables", [])
            types = node.value.get("types", [])
            
            for i, var in enumerate(variables):
                if var not in self.variable_map:
                    label = f"*v{self.next_label_id}"
                    self.next_label_id += 1
                    self.variable_map[var] = {
                        "label": label,
                        "type": types[i] if i < len(types) else "Thing"
                    }
        
        # Process children
        for child in node.children:
            self._collect_variables(child)
    
    def _translate_relation(self, node):
        """
        Translate a CL relation to a CGIF relation or concept.
        
        Args:
            node (Node): The CL relation node
            
        Returns:
            Node: The translated CGIF relation or concept node
        """
        relation_type = node.value.get("type")
        args = node.value.get("args", [])
        
        # Check if this is a unary relation (concept)
        if len(args) == 1:
            arg = args[0]
            
            # Check if the argument is a variable
            if arg in self.variable_map:
                # This is a variable, create a concept with type label
                var_info = self.variable_map[arg]
                label = var_info["label"] if isinstance(var_info, dict) else var_info
                bound_label = label.replace("*", "?")
                
                return Node(NODE_CONCEPT, {
                    "type_label": relation_type,
                    "referent": label,
                    "defining_label": None,
                    "bound_label": bound_label,
                    "universal": False
                }, [], node.position)
            else:
                # This is a constant, create a concept with type label and referent
                return Node(NODE_CONCEPT, {
                    "type_label": relation_type,
                    "referent": arg,
                    "defining_label": None,
                    "bound_label": None,
                    "universal": False
                }, [], node.position)
        
        # Map any variables to coreference labels
        mapped_args = []
        for arg in args:
            if arg in self.variable_map:
                # This is a variable, use the mapped label
                var_info = self.variable_map[arg]
                label = var_info["label"] if isinstance(var_info, dict) else var_info
                mapped_args.append(label.replace("*", "?"))
            else:
                mapped_args.append(arg)
        
        # Create a relation node
        return Node(NODE_RELATION, {
            "type": relation_type,
            "args": mapped_args
        }, [], node.position)
    
    def _translate_quantifier(self, node):
        """
        Translate a CL quantifier to a CGIF concept with quantifier.
        
        Args:
            node (Node): The CL quantifier node
            
        Returns:
            list: List of translated CGIF nodes
        """
        quantifier_type = node.value.get("type")
        variables = node.value.get("variables", [])
        types = node.value.get("types", [])
        
        # Create concepts for each variable
        concepts = []
        for i, var in enumerate(variables):
            # Get the type if available
            type_label = types[i] if i < len(types) else "Thing"
            
            # Get the coreference label
            var_info = self.variable_map.get(var)
            label = var_info["label"] if isinstance(var_info, dict) else var_info
            
            # Use the type from the variable map if available
            if isinstance(var_info, dict) and "type" in var_info and var_info["type"] != "Thing":
                type_label = var_info["type"]
            
            # Create a concept node
            concept = Node(NODE_CONCEPT, {
                "type_label": type_label,
                "referent": label,
                "defining_label": label,
                "bound_label": None,
                "universal": quantifier_type == QUANTIFIER_UNIVERSAL
            }, [], node.position)
            
            # Wrap in quantifier node if universal
            if quantifier_type == QUANTIFIER_UNIVERSAL:
                concept = Node(NODE_QUANTIFIER, QUANTIFIER_UNIVERSAL, [concept], node.position)
            else:
                concept = Node(NODE_QUANTIFIER, QUANTIFIER_EXISTENTIAL, [concept], node.position)
            
            concepts.append(concept)
        
        # Translate the body
        body_nodes = []
        for child in node.children:
            translated = self._translate_node(child)
            if translated:
                if isinstance(translated, list):
                    body_nodes.extend(translated)
                else:
                    body_nodes.append(translated)
        
        # Combine concepts and body
        return concepts + body_nodes
    
    def _translate_negation(self, node):
        """
        Translate a CL negation to a CGIF negation.
        
        Args:
            node (Node): The CL negation node
            
        Returns:
            Node: The translated CGIF negation node
        """
        # Translate the child node
        if not node.children:
            return Node(NODE_NEGATION, None, [], node.position)
        
        child = self._translate_node(node.children[0])
        
        # Create a context node to hold the child
        context = Node(NODE_CONTEXT, None, [child] if child else [], node.position)
        
        # Create a negation node
        return Node(NODE_NEGATION, None, [context], node.position)
    
    def _translate_and(self, node):
        """
        Translate a CL AND to a list of CGIF nodes.
        
        Args:
            node (Node): The CL AND node
            
        Returns:
            list: List of translated CGIF nodes
        """
        # Translate all child nodes
        translated_children = []
        for child in node.children:
            translated = self._translate_node(child)
            if translated:
                if isinstance(translated, list):
                    translated_children.extend(translated)
                else:
                    translated_children.append(translated)
        
        return translated_children
    
    def _translate_or(self, node):
        """
        Translate a CL OR to a CGIF negation of AND of negations.
        
        Args:
            node (Node): The CL OR node
            
        Returns:
            Node: The translated CGIF negation node
        """
        # Translate all child nodes and negate them
        negated_children = []
        for child in node.children:
            translated = self._translate_node(child)
            if translated:
                if isinstance(translated, list):
                    # Create a context node to hold the list
                    context = Node(NODE_CONTEXT, None, translated, node.position)
                    # Create a negation node
                    negation = Node(NODE_NEGATION, None, [context], node.position)
                    negated_children.append(negation)
                else:
                    # Create a negation node
                    negation = Node(NODE_NEGATION, None, [translated], node.position)
                    negated_children.append(negation)
        
        # Create a context node to hold the negated children
        context = Node(NODE_CONTEXT, None, negated_children, node.position)
        
        # Create a negation node (negation of AND of negations = OR)
        return Node(NODE_NEGATION, None, [context], node.position)
    
    def _translate_if(self, node):
        """
        Translate a CL IF to a CGIF negation of antecedent AND negation of consequent.
        
        Args:
            node (Node): The CL IF node
            
        Returns:
            Node: The translated CGIF negation node
        """
        if len(node.children) < 2:
            # Not enough children
            return None
        
        # Translate antecedent and consequent
        antecedent = self._translate_node(node.children[0])
        consequent = self._translate_node(node.children[1])
        
        # Create a negation of consequent
        neg_consequent = Node(NODE_NEGATION, None, [consequent], node.position)
        
        # Create a context node to hold antecedent and negation of consequent
        context = Node(NODE_CONTEXT, None, [antecedent, neg_consequent], node.position)
        
        # Create a negation node (negation of antecedent AND negation of consequent = IF)
        return Node(NODE_NEGATION, None, [context], node.position)
    
    def _translate_iff(self, node):
        """
        Translate a CL IFF to a CGIF combination of IF nodes.
        
        Args:
            node (Node): The CL IFF node
            
        Returns:
            list: List of translated CGIF nodes
        """
        if len(node.children) < 2:
            # Not enough children
            return None
        
        # Translate antecedent and consequent
        antecedent = self._translate_node(node.children[0])
        consequent = self._translate_node(node.children[1])
        
        # Create IF in one direction
        neg_consequent = Node(NODE_NEGATION, None, [consequent], node.position)
        context1 = Node(NODE_CONTEXT, None, [antecedent, neg_consequent], node.position)
        if1 = Node(NODE_NEGATION, None, [context1], node.position)
        
        # Create IF in the other direction
        neg_antecedent = Node(NODE_NEGATION, None, [antecedent], node.position)
        context2 = Node(NODE_CONTEXT, None, [consequent, neg_antecedent], node.position)
        if2 = Node(NODE_NEGATION, None, [context2], node.position)
        
        return [if1, if2]
    
    def _translate_equals(self, node):
        """
        Translate a CL EQUALS to a CGIF relation or function.
        
        Args:
            node (Node): The CL EQUALS node
            
        Returns:
            Node: The translated CGIF relation or function node
        """
        if len(node.children) < 2:
            # Not enough children
            return None
        
        # Check if the second child is a function call
        if node.children[1].node_type == "FUNCTION_CALL":
            # This is a function call
            function_node = node.children[1]
            result = node.children[0]
            
            function_name = function_node.value.get("name")
            args = function_node.value.get("args", [])
            
            # Map any variables to coreference labels
            mapped_args = []
            for arg in args:
                if arg in self.variable_map:
                    # This is a variable, use the mapped label
                    mapped_args.append(self.variable_map[arg].replace("*", "?"))
                else:
                    mapped_args.append(arg)
            
            # Map result to coreference label
            mapped_result = None
            if result in self.variable_map:
                # This is a variable, use the mapped label
                mapped_result = self.variable_map[result].replace("*", "?")
            else:
                mapped_result = result
            
            # Create a function node
            return Node(NODE_FUNCTION, {
                "type": function_name,
                "args": mapped_args,
                "results": [mapped_result]
            }, [], node.position)
        
        # Otherwise, create a relation
        return Node(NODE_RELATION, {
            "type": "Equals",
            "args": [node.children[0], node.children[1]]
        }, [], node.position)
    
    def _translate_function_call(self, node):
        """
        Translate a CL FUNCTION_CALL to a CGIF function.
        
        Args:
            node (Node): The CL FUNCTION_CALL node
            
        Returns:
            Node: The translated CGIF function node
        """
        function_name = node.value.get("name")
        args = node.value.get("args", [])
        
        # Map any variables to coreference labels
        mapped_args = []
        for arg in args:
            if arg in self.variable_map:
                # This is a variable, use the mapped label
                mapped_args.append(self.variable_map[arg].replace("*", "?"))
            else:
                mapped_args.append(arg)
        
        # Create a function node with no result
        return Node(NODE_FUNCTION, {
            "type": function_name,
            "args": mapped_args,
            "results": []
        }, [], node.position)


class Translator:
    """
    Unified translator interface for CGIF and CL expressions.
    
    This class provides a common interface for translating between CGIF and CL
    expressions, preserving semantic equivalence.
    """
    
    # Translation directions
    CGIF_TO_CL = "CGIF_TO_CL"
    CL_TO_CGIF = "CL_TO_CGIF"
    
    def __init__(self):
        """Initialize the translator."""
        self.cgif_to_cl = CGIFtoCLTranslator()
        self.cl_to_cgif = CLtoCGIFTranslator()
    
    def translate(self, ast, direction):
        """
        Translate an AST in the specified direction.
        
        Args:
            ast (Node): The AST to translate
            direction (str): The translation direction (CGIF_TO_CL or CL_TO_CGIF)
            
        Returns:
            Node: The translated AST
        """
        if direction == self.CGIF_TO_CL:
            return self.cgif_to_cl.translate(ast)
        elif direction == self.CL_TO_CGIF:
            return self.cl_to_cgif.translate(ast)
        else:
            raise ValueError(f"Invalid translation direction: {direction}")
    
    def format_output(self, ast, format_type):
        """
        Format the AST as a string in the specified format.
        
        Args:
            ast (Node): The AST to format
            format_type (str): The format type (CGIF or CL)
            
        Returns:
            str: The formatted string
        """
        if format_type == "CGIF":
            return self._format_cgif(ast)
        elif format_type == "CL":
            return self._format_cl(ast)
        else:
            raise ValueError(f"Invalid format type: {format_type}")
    
    def _format_cgif(self, node, indent=0):
        """
        Format a CGIF AST as a string.
        
        Args:
            node (Node): The CGIF AST node
            indent (int): The indentation level
            
        Returns:
            str: The formatted string
        """
        if node.node_type == "EXPRESSION":
            # Format expression
            return "\n".join(self._format_cgif(child, indent) for child in node.children)
        elif node.node_type == NODE_CONCEPT:
            # Format concept
            type_label = node.value.get("type_label")
            referent = node.value.get("referent")
            defining_label = node.value.get("defining_label")
            bound_label = node.value.get("bound_label")
            universal = node.value.get("universal")
            
            if universal:
                return " " * indent + f"[{type_label}: @every {defining_label}]"
            elif type_label and (defining_label or bound_label):
                return " " * indent + f"[{type_label}: {defining_label or bound_label}]"
            elif type_label and referent:
                return " " * indent + f"[{type_label}: {referent}]"
            elif defining_label:
                return " " * indent + f"[{defining_label}]"
            elif bound_label:
                return " " * indent + f"[{bound_label}]"
            else:
                return " " * indent + f"[{referent}]"
        elif node.node_type == NODE_RELATION:
            # Format relation
            relation_type = node.value.get("type")
            args = node.value.get("args", [])
            
            return " " * indent + f"({relation_type} {' '.join(str(arg) for arg in args)})"
        elif node.node_type == NODE_QUANTIFIER:
            # Format quantifier
            if node.value == QUANTIFIER_UNIVERSAL:
                return self._format_cgif(node.children[0], indent)
            else:
                return self._format_cgif(node.children[0], indent)
        elif node.node_type == NODE_NEGATION:
            # Format negation
            if not node.children:
                return " " * indent + "~[]"
            
            return " " * indent + "~" + self._format_cgif(node.children[0], indent)
        elif node.node_type == NODE_CONTEXT:
            # Format context
            if not node.children:
                return " " * indent + "[]"
            
            content = "\n".join(self._format_cgif(child, indent + 2) for child in node.children)
            return " " * indent + "[\n" + content + "\n" + " " * indent + "]"
        elif node.node_type == NODE_FUNCTION:
            # Format function
            function_type = node.value.get("type")
            args = node.value.get("args", [])
            results = node.value.get("results", [])
            
            if results:
                return " " * indent + f"({function_type} {' '.join(str(arg) for arg in args)} | {' '.join(str(result) for result in results)})"
            else:
                return " " * indent + f"({function_type} {' '.join(str(arg) for arg in args)})"
        else:
            # Unknown node type
            return " " * indent + f"<Unknown node type: {node.node_type}>"
    
    def _format_cl(self, node, indent=0):
        """
        Format a CL AST as a string.
        
        Args:
            node (Node): The CL AST node
            indent (int): The indentation level
            
        Returns:
            str: The formatted string
        """
        if node.node_type == "EXPRESSION":
            # Format expression
            return "\n".join(self._format_cl(child, indent) for child in node.children)
        elif node.node_type == NODE_RELATION:
            # Format relation
            relation_type = node.value.get("type")
            args = node.value.get("args", [])
            
            return " " * indent + f"({relation_type} {' '.join(str(arg) for arg in args)})"
        elif node.node_type == NODE_QUANTIFIER:
            # Format quantifier
            quantifier_type = node.value.get("type")
            variables = node.value.get("variables", [])
            types = node.value.get("types", [])
            
            # Format variable list
            var_list = []
            for i, var in enumerate(variables):
                if i < len(types) and types[i]:
                    var_list.append(f"({var} {types[i]})")
                else:
                    var_list.append(var)
            
            # Format body
            body = "\n".join(self._format_cl(child, indent + 2) for child in node.children)
            
            if quantifier_type == QUANTIFIER_UNIVERSAL:
                return " " * indent + f"(forall ({' '.join(var_list)})\n{body})"
            else:
                return " " * indent + f"(exists ({' '.join(var_list)})\n{body})"
        elif node.node_type == NODE_NEGATION:
            # Format negation
            if not node.children:
                return " " * indent + "(not ())"
            
            body = self._format_cl(node.children[0], indent + 2)
            return " " * indent + f"(not\n{body})"
        elif node.node_type == "AND":
            # Format AND
            if not node.children:
                return " " * indent + "(and)"
            
            body = "\n".join(self._format_cl(child, indent + 2) for child in node.children)
            return " " * indent + f"(and\n{body})"
        elif node.node_type == "OR":
            # Format OR
            if not node.children:
                return " " * indent + "(or)"
            
            body = "\n".join(self._format_cl(child, indent + 2) for child in node.children)
            return " " * indent + f"(or\n{body})"
        elif node.node_type == "IF":
            # Format IF
            if len(node.children) < 2:
                return " " * indent + "(if)"
            
            antecedent = self._format_cl(node.children[0], indent + 2)
            consequent = self._format_cl(node.children[1], indent + 2)
            return " " * indent + f"(if\n{antecedent}\n{consequent})"
        elif node.node_type == "IFF":
            # Format IFF
            if len(node.children) < 2:
                return " " * indent + "(iff)"
            
            left = self._format_cl(node.children[0], indent + 2)
            right = self._format_cl(node.children[1], indent + 2)
            return " " * indent + f"(iff\n{left}\n{right})"
        elif node.node_type == "EQUALS":
            # Format EQUALS
            if len(node.children) < 2:
                return " " * indent + "(=)"
            
            left = self._format_cl(node.children[0], indent + 2) if isinstance(node.children[0], Node) else str(node.children[0])
            right = self._format_cl(node.children[1], indent + 2) if isinstance(node.children[1], Node) else str(node.children[1])
            return " " * indent + f"(= {left} {right})"
        elif node.node_type == "FUNCTION_CALL":
            # Format FUNCTION_CALL
            function_name = node.value.get("name")
            args = node.value.get("args", [])
            
            return " " * indent + f"({function_name} {' '.join(str(arg) for arg in args)})"
        else:
            # Unknown node type
            return " " * indent + f"<Unknown node type: {node.node_type}>"
