#!/usr/bin/env python3
"""
Graph clipboard system for copying and pasting existential graph fragments.
Supports mode-aware operations and transformation rule validation.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from copy import deepcopy
import json

from PySide6.QtCore import QObject, Signal, QPointF, QRectF
from PySide6.QtWidgets import QGraphicsItem

from eg_model import ExistentialGraph, Node, Hyperedge, GraphObjectType
from interaction_modes import InteractionMode, ValidationLevel

@dataclass
class GraphFragment:
    """Represents a copyable fragment of an existential graph."""
    nodes: Dict[str, Node]  # node_id -> Node
    hyperedges: Dict[str, Hyperedge]  # hyperedge_id -> Hyperedge
    root_nodes: List[str]  # Top-level nodes in this fragment
    bounding_rect: QRectF  # Visual bounds of the fragment
    source_mode: InteractionMode  # Mode where fragment was created
    metadata: Dict[str, Any]  # Additional information

class ContextAnalyzer:
    """Analyzes graph contexts for transformation rule validation."""
    
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph
        
    def get_context_type(self, position: QPointF, cut_items: Dict) -> str:
        """Determine if a position is in a positive or negative context."""
        # Count the number of cuts containing this position
        containing_cuts = 0
        
        for cut_id, cut_item in cut_items.items():
            if cut_item.sceneBoundingRect().contains(position):
                containing_cuts += 1
                
        # Even number of cuts = positive context
        # Odd number of cuts = negative context
        # Root (0 cuts) = positive context
        return "negative" if containing_cuts % 2 == 1 else "positive"
        
    def can_insert_at_position(self, position: QPointF, cut_items: Dict) -> bool:
        """Check if insertion is allowed at position (negative context only)."""
        context = self.get_context_type(position, cut_items)
        return context == "negative"
        
    def get_containing_cuts(self, position: QPointF, cut_items: Dict) -> List[str]:
        """Get list of cuts containing the given position."""
        containing = []
        for cut_id, cut_item in cut_items.items():
            if cut_item.sceneBoundingRect().contains(position):
                containing.append(cut_id)
        return containing

class GraphClipboard(QObject):
    """Manages copying and pasting of graph fragments with mode awareness."""
    
    # Signals
    fragment_copied = Signal(object)  # GraphFragment
    fragment_pasted = Signal(object, QPointF)  # GraphFragment, position
    paste_rejected = Signal(str)  # reason
    
    def __init__(self, graph: ExistentialGraph):
        super().__init__()
        self.graph = graph
        self.context_analyzer = ContextAnalyzer(graph)
        self.clipboard: Optional[GraphFragment] = None
        
    def copy_selection(self, selected_items: List[QGraphicsItem], 
                      source_mode: InteractionMode) -> bool:
        """Copy selected graphics items to clipboard as a graph fragment."""
        try:
            print(f"Copying selection in {source_mode} mode")
            
            # Extract node IDs from selected items
            node_ids = set()
            for item in selected_items:
                if hasattr(item, 'node_id'):
                    node_ids.add(item.node_id)
                    
            if not node_ids:
                print("No valid nodes selected for copying")
                return False
                
            # Build fragment
            fragment = self._build_fragment(node_ids, selected_items, source_mode)
            
            if fragment:
                self.clipboard = fragment
                print(f"Copied fragment with {len(fragment.nodes)} nodes and {len(fragment.hyperedges)} hyperedges")
                self.fragment_copied.emit(fragment)
                return True
            else:
                print("Failed to build fragment")
                return False
                
        except Exception as e:
            print(f"Error copying selection: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def _build_fragment(self, node_ids: Set[str], selected_items: List[QGraphicsItem],
                       source_mode: InteractionMode) -> Optional[GraphFragment]:
        """Build a graph fragment from selected node IDs."""
        
        # Collect nodes
        nodes = {}
        for node_id in node_ids:
            node = self.graph.get_object(node_id)
            if node and isinstance(node, Node):
                # Create a copy of the node
                node_copy = Node(node.node_type, deepcopy(node.properties))
                node_copy.id = node.id  # Keep original ID for now
                nodes[node_id] = node_copy
                
        # Collect hyperedges (ligatures) that connect selected nodes
        hyperedges = {}
        for obj_id, obj in self.graph.objects.items():
            if isinstance(obj, Hyperedge):
                # Check if this hyperedge connects any selected nodes
                connected_nodes = set()
                for endpoint in obj.endpoints:
                    if endpoint['node_id'] in node_ids:
                        connected_nodes.add(endpoint['node_id'])
                        
                # Include hyperedge if it connects at least 2 selected nodes
                if len(connected_nodes) >= 2:
                    hyperedge_copy = Hyperedge(obj.edge_type, deepcopy(obj.endpoints))
                    hyperedge_copy.id = obj.id
                    hyperedges[obj_id] = hyperedge_copy
                    
        # Calculate bounding rectangle
        bounding_rect = self._calculate_bounding_rect(selected_items)
        
        # Determine root nodes (nodes not contained in other selected nodes)
        root_nodes = self._find_root_nodes(node_ids)
        
        # Create metadata
        metadata = {
            'creation_time': str(QPointF().x()),  # Placeholder timestamp
            'node_count': len(nodes),
            'hyperedge_count': len(hyperedges),
            'source_description': f"Fragment from {source_mode} mode"
        }
        
        return GraphFragment(
            nodes=nodes,
            hyperedges=hyperedges,
            root_nodes=root_nodes,
            bounding_rect=bounding_rect,
            source_mode=source_mode,
            metadata=metadata
        )
        
    def _calculate_bounding_rect(self, items: List[QGraphicsItem]) -> QRectF:
        """Calculate bounding rectangle of selected items."""
        if not items:
            return QRectF()
            
        # Start with first item's bounding rect
        bounding = items[0].sceneBoundingRect()
        
        # Union with all other items
        for item in items[1:]:
            bounding = bounding.united(item.sceneBoundingRect())
            
        return bounding
        
    def _find_root_nodes(self, node_ids: Set[str]) -> List[str]:
        """Find nodes that are not contained within other selected nodes."""
        root_nodes = []
        
        for node_id in node_ids:
            node = self.graph.get_object(node_id)
            if not node:
                continue
                
            # Check if this node is contained in any other selected node
            parent = self.graph.get_parent(node_id)
            is_root = True
            
            while parent:
                if parent.id in node_ids:
                    is_root = False
                    break
                parent = self.graph.get_parent(parent.id)
                
            if is_root:
                root_nodes.append(node_id)
                
        return root_nodes
        
    def can_paste_at_position(self, position: QPointF, target_mode: InteractionMode,
                            cut_items: Dict) -> Tuple[bool, str]:
        """Check if clipboard fragment can be pasted at the given position."""
        if not self.clipboard:
            return False, "No fragment in clipboard"
            
        # Mode-specific validation
        if target_mode == InteractionMode.COMPOSITION:
            # Composition mode allows pasting anywhere
            return True, "Composition mode allows free pasting"
            
        elif target_mode == InteractionMode.CONSTRAINED:
            # Constrained mode requires structural validity
            # For now, allow pasting but this could be enhanced
            return True, "Constrained mode allows pasting with validation"
            
        elif target_mode == InteractionMode.TRANSFORMATION:
            # Transformation mode requires rule compliance
            return self._validate_transformation_paste(position, cut_items)
            
        return False, "Unknown target mode"
        
    def _validate_transformation_paste(self, position: QPointF, 
                                     cut_items: Dict) -> Tuple[bool, str]:
        """Validate paste operation for transformation mode (insertion rule)."""
        
        # Peirce's insertion rule: graphs can only be inserted in negative contexts
        context = self.context_analyzer.get_context_type(position, cut_items)
        
        if context == "negative":
            return True, "Insertion allowed in negative context"
        else:
            return False, "Insertion rule violation: can only insert in negative contexts"
            
    def paste_at_position(self, position: QPointF, target_mode: InteractionMode,
                         cut_items: Dict, scene_items: Dict) -> bool:
        """Paste clipboard fragment at the specified position."""
        
        if not self.clipboard:
            self.paste_rejected.emit("No fragment in clipboard")
            return False
            
        # Validate paste operation
        can_paste, reason = self.can_paste_at_position(position, target_mode, cut_items)
        
        if not can_paste:
            print(f"Paste rejected: {reason}")
            self.paste_rejected.emit(reason)
            return False
            
        try:
            # Calculate offset from original position
            original_center = self.clipboard.bounding_rect.center()
            offset = position - original_center
            
            print(f"Pasting fragment at {position} with offset {offset}")
            print(f"Validation: {reason}")
            
            # Create new nodes and hyperedges in the graph
            id_mapping = {}  # old_id -> new_id
            
            # Add nodes to graph
            for old_id, node in self.clipboard.nodes.items():
                new_node = Node(node.node_type, deepcopy(node.properties))
                self.graph.objects[new_node.id] = new_node
                id_mapping[old_id] = new_node.id
                print(f"Created new node {new_node.id} from {old_id}")
                
            # Add hyperedges to graph with updated endpoint references
            for old_id, hyperedge in self.clipboard.hyperedges.items():
                new_hyperedge = Hyperedge(hyperedge.edge_type, [])
                
                # Update endpoint references
                for endpoint in hyperedge.endpoints:
                    old_node_id = endpoint['node_id']
                    if old_node_id in id_mapping:
                        new_endpoint = deepcopy(endpoint)
                        new_endpoint['node_id'] = id_mapping[old_node_id]
                        new_hyperedge.endpoints.append(new_endpoint)
                        
                self.graph.objects[new_hyperedge.id] = new_hyperedge
                print(f"Created new hyperedge {new_hyperedge.id} from {old_id}")
                
            # Emit success signal
            self.fragment_pasted.emit(self.clipboard, position)
            
            print(f"Successfully pasted fragment with {len(id_mapping)} nodes")
            return True
            
        except Exception as e:
            print(f"Error pasting fragment: {e}")
            import traceback
            traceback.print_exc()
            self.paste_rejected.emit(f"Paste error: {str(e)}")
            return False
            
    def has_clipboard_content(self) -> bool:
        """Check if clipboard has content."""
        return self.clipboard is not None
        
    def get_clipboard_info(self) -> Optional[Dict[str, Any]]:
        """Get information about clipboard content."""
        if not self.clipboard:
            return None
            
        return {
            'node_count': len(self.clipboard.nodes),
            'hyperedge_count': len(self.clipboard.hyperedges),
            'source_mode': self.clipboard.source_mode,
            'bounding_rect': self.clipboard.bounding_rect,
            'metadata': self.clipboard.metadata
        }
        
    def clear_clipboard(self):
        """Clear the clipboard."""
        self.clipboard = None
        print("Clipboard cleared")
        
    def export_fragment_to_json(self) -> Optional[str]:
        """Export clipboard fragment to JSON string."""
        if not self.clipboard:
            return None
            
        try:
            # Convert fragment to serializable format
            data = {
                'nodes': {nid: {
                    'node_type': node.node_type.name if hasattr(node.node_type, 'name') else str(node.node_type),
                    'properties': node.properties
                } for nid, node in self.clipboard.nodes.items()},
                'hyperedges': {hid: {
                    'edge_type': str(hyperedge.edge_type),  # Convert to string
                    'endpoints': hyperedge.endpoints
                } for hid, hyperedge in self.clipboard.hyperedges.items()},
                'root_nodes': self.clipboard.root_nodes,
                'source_mode': self.clipboard.source_mode.name,
                'metadata': self.clipboard.metadata
            }
            
            return json.dumps(data, indent=2)
            
        except Exception as e:
            print(f"Error exporting fragment: {e}")
            return None

