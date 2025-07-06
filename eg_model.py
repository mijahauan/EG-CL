# eg_model.py
from __future__ import annotations
import uuid
from enum import Enum, auto
from typing import List, Optional, Set, Dict, Any, Union

## NEW ##
# This file defines a general-purpose property hypergraph model.
# EG-specific concepts are now implemented as types of nodes and hyperedges.

class GraphObjectType(Enum):
    """Defines the types of objects in the graph model."""
    PREDICATE = auto()
    CUT = auto()
    LIGATURE = auto()
    # Future types like CONCEPT, RELATION can be added here.

class GraphObject:
    """Base class for all elements in the graph, providing a unique ID."""
    def __init__(self):
        self.id = str(uuid.uuid4())

class Node(GraphObject):
    """
    Represents a node in the graph, such as a predicate or a cut.
    A node has a type, a set of properties, and an ordered list of contents.
    """
    def __init__(self, node_type: GraphObjectType, properties: Dict[str, Any] = None):
        super().__init__()
        self.node_type = node_type
        self.properties = properties if properties is not None else {}
        # The `contents` list preserves creation order, solving the layout problem.
        self.contents: List[str] = [] # List of IDs of contained objects

class Hyperedge(GraphObject):
    """
    Represents a hyperedge that can connect multiple node endpoints.
    Used to implement ligatures.
    """
    def __init__(self, edge_type: GraphObjectType, endpoints: List[Dict[str, Any]] = None):
        super().__init__()
        self.edge_type = edge_type
        # An endpoint is a dictionary, e.g., {'node_id': '...', 'hook_index': 0}
        self.endpoints: List[Dict[str, Any]] = endpoints if endpoints is not None else []

class ExistentialGraph:
    """
    The top-level container for the graph, holding all objects
    and a reference to the root context (Sheet of Assertion).
    """
    def __init__(self):
        self.objects: Dict[str, Union[Node, Hyperedge]] = {}
        
        # Create the Sheet of Assertion as the root node
        soa_node = Node(GraphObjectType.CUT, properties={"name": "Sheet of Assertion"})
        self.root_id = soa_node.id
        self.objects[self.root_id] = soa_node
        
    def get_object(self, obj_id: str) -> Union[Node, Hyperedge, None]:
        return self.objects.get(obj_id)

    def get_parent(self, obj_id: str) -> Optional[Node]:
        """Finds the containing parent Node (a Cut) for any graph object."""
        for obj in self.objects.values():
            if isinstance(obj, Node) and obj.node_type == GraphObjectType.CUT:
                if obj_id in obj.contents:
                    return obj
        return None

    def get_nesting_level(self, node_id: str) -> int:
        """Calculates the nesting depth of a node."""
        level = -1 # Start at -1 so the SOA (which has no parent) is level 0
        curr = self.get_object(node_id)
        while curr:
            level += 1
            curr = self.get_parent(curr.id)
        return level

    def get_ligature_starting_context(self, hyperedge_id: str) -> Optional[Node]:
        """
        Determines the outermost context where a ligature is quantified.
        This is the Least Common Ancestor (LCA) of all nodes it connects to.
        """
        hyperedge = self.get_object(hyperedge_id)
        if not isinstance(hyperedge, Hyperedge) or not hyperedge.endpoints:
            return None

        paths = []
        for endpoint in hyperedge.endpoints:
            path = []
            curr_node = self.get_object(endpoint['node_id'])
            curr_context = self.get_parent(curr_node.id)
            while curr_context:
                path.append(curr_context)
                curr_context = self.get_parent(curr_context.id)
            paths.append(path)
        
        if not paths: return None

        common_ancestors = set(paths[0])
        for other_path in paths[1:]:
            common_ancestors.intersection_update(other_path)
        
        if not common_ancestors: return self.get_object(self.root_id)
        
        return max(common_ancestors, key=lambda c: self.get_nesting_level(c.id))