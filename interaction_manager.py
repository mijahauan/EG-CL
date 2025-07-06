#!/usr/bin/env python3
"""
Interaction manager for handling complex interactions between enhanced graphics items.
Manages ligature creation, transformation rule validation, and drag-drop operations.
"""

from PySide6.QtCore import QObject, Signal, QPointF, Qt, QEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
from PySide6.QtGui import QCursor

from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

class EditingState(Enum):
    """States for editing operations like connection creation."""
    NORMAL = "normal"
    CONNECTING = "connecting"
    RESIZING = "resizing"

from ligature_item import LigatureItem
from interaction_modes import (InteractionModeManager, ModeAwareValidator, 
                              ModeAwareLigatureManager, InteractionMode)
from enhanced_graphics_items import (EnhancedPredicateItem, EnhancedCutItem, 
                                   HookItem, ConnectionPreviewItem)
from graph_clipboard import GraphClipboard, ContextAnalyzer
from eg_model import ExistentialGraph, GraphObjectType
from eg_logic import EGEditor

class ConnectionState:
    """State information for ligature connection operations."""
    def __init__(self):
        self.source_hook: Optional[HookItem] = None
        self.source_predicate: Optional[EnhancedPredicateItem] = None
        self.preview_item: Optional[ConnectionPreviewItem] = None
        self.valid_targets: List[HookItem] = []

class InteractionManager(QObject):
    """Manages complex interactions between enhanced graphics items."""
    
    # Signals for communication with main application
    ligature_created = Signal(str, int, str, int)  # source_id, source_hook, target_id, target_hook
    ligature_removed = Signal(str)  # ligature_id
    element_moved = Signal(str, QPointF)  # element_id, new_position
    cut_resized = Signal(str, object)  # cut_id, new_rect
    
    def __init__(self, scene: QGraphicsScene, graph: ExistentialGraph, editor: EGEditor):
        super().__init__()
        self.scene = scene
        self.graph = graph
        self.editor = editor
        
        # Mode-aware system
        self.mode_manager = InteractionModeManager()
        self.validator = ModeAwareValidator(self.mode_manager)
        self.ligature_manager = ModeAwareLigatureManager(self.mode_manager)
        
        # Clipboard system
        self.clipboard = GraphClipboard(self.graph)
        self.context_analyzer = ContextAnalyzer(self.graph)
        
        # Editing state (different from interaction mode)
        self.editing_state = EditingState.NORMAL
        self.connection_state = ConnectionState()
        
        # Track enhanced items
        self.predicate_items: Dict[str, EnhancedPredicateItem] = {}
        self.cut_items: Dict[str, EnhancedCutItem] = {}
        self.ligature_items: Dict[str, LigatureItem] = {}  # Track ligature graphics items
        
        # Install event filter on scene
        self.scene.installEventFilter(self)
        
    def set_interaction_mode(self, mode: InteractionMode):
        """Set the interaction mode and update behaviors accordingly."""
        self.mode_manager.set_mode(mode)
        print(f"Interaction mode set to: {self.mode_manager.get_mode_display_name(mode)}")
        
    def get_interaction_mode(self) -> InteractionMode:
        """Get the current interaction mode."""
        return self.mode_manager.get_mode()
        
    def get_mode_description(self) -> str:
        """Get description of current mode."""
        return self.mode_manager.get_mode_description()
        
    def copy_selection(self) -> bool:
        """Copy selected items to clipboard."""
        selected_items = self.scene.selectedItems()
        if not selected_items:
            print("No items selected for copying")
            return False
            
        current_mode = self.mode_manager.get_mode()
        return self.clipboard.copy_selection(selected_items, current_mode)
        
    def paste_at_cursor(self, position: QPointF) -> bool:
        """Paste clipboard content at the specified position."""
        if not self.clipboard.has_clipboard_content():
            print("No content in clipboard to paste")
            return False
            
        current_mode = self.mode_manager.get_mode()
        return self.clipboard.paste_at_position(position, current_mode, self.cut_items, {})
        
    def can_paste_at_position(self, position: QPointF) -> Tuple[bool, str]:
        """Check if clipboard content can be pasted at position."""
        if not self.clipboard.has_clipboard_content():
            return False, "No content in clipboard"
            
        current_mode = self.mode_manager.get_mode()
        return self.clipboard.can_paste_at_position(position, current_mode, self.cut_items)
        
    def get_clipboard_info(self) -> Optional[Dict[str, Any]]:
        """Get information about clipboard content."""
        return self.clipboard.get_clipboard_info()
        
    def clear_clipboard(self):
        """Clear the clipboard."""
        self.clipboard.clear_clipboard()
        
    def register_predicate_item(self, node_id: str, item: EnhancedPredicateItem):
        """Register a predicate item for interaction management."""
        self.predicate_items[node_id] = item
        
    def register_cut_item(self, node_id: str, item: EnhancedCutItem):
        """Register a cut item for interaction management."""
        self.cut_items[node_id] = item
        
    def register_ligature_item(self, ligature_id: str, item: LigatureItem):
        """Register a ligature item for interaction management."""
        self.ligature_items[ligature_id] = item
        
    def unregister_item(self, node_id: str):
        """Unregister an item from interaction management."""
        self.predicate_items.pop(node_id, None)
        self.cut_items.pop(node_id, None)
        self.ligature_items.pop(node_id, None)
        
    def start_connection(self, source_hook: HookItem, source_predicate: EnhancedPredicateItem):
        """Start a ligature connection operation."""
        if self.editing_state != EditingState.NORMAL:
            return
            
        self.editing_state = EditingState.CONNECTING
        self.connection_state.source_hook = source_hook
        self.connection_state.source_predicate = source_predicate
        
        # Create preview item
        start_pos = source_hook.scenePos()
        self.connection_state.preview_item = ConnectionPreviewItem(start_pos)
        self.scene.addItem(self.connection_state.preview_item)
        
        # Highlight source hook
        source_hook.set_highlighted(True)
        
        # Find and highlight valid targets
        self.update_valid_connection_targets()
        
        # Change cursor
        self.scene.views()[0].setCursor(QCursor(Qt.CrossCursor))
        
    def update_connection_preview(self, scene_pos: QPointF):
        """Update the connection preview line."""
        if self.mode == InteractionMode.CONNECTING and self.connection_state.preview_item:
            self.connection_state.preview_item.update_end_point(scene_pos)
            
    def complete_connection(self, target_hook: HookItem, target_predicate: EnhancedPredicateItem):
        """Complete a ligature connection operation."""
        if self.mode != InteractionMode.CONNECTING:
            return
            
        # Validate connection
        if self.is_valid_connection(self.connection_state.source_hook, target_hook):
            # Create ligature in the model
            source_endpoint = {
                "node_id": self.connection_state.source_predicate.node_id,
                "hook_index": self.connection_state.source_hook.hook_index
            }
            target_endpoint = {
                "node_id": target_predicate.node_id,
                "hook_index": target_hook.hook_index
            }
            
            # Use editor to create connection
            self.editor.connect(source_endpoint, target_endpoint)
            
            # Update visual state
            self.connection_state.source_hook.set_connected(True)
            target_hook.set_connected(True)
            
            # Emit signal
            self.ligature_created.emit(
                self.connection_state.source_predicate.node_id,
                self.connection_state.source_hook.hook_index,
                target_predicate.node_id,
                target_hook.hook_index
            )
            
        self.cancel_connection()
        
    def cancel_connection(self):
        """Cancel the current connection operation."""
        if self.mode != InteractionMode.CONNECTING:
            return
            
        # Remove preview item safely
        if self.connection_state.preview_item:
            try:
                if self.connection_state.preview_item.scene() == self.scene:
                    self.scene.removeItem(self.connection_state.preview_item)
            except RuntimeError:
                # Item already deleted, ignore
                pass
            self.connection_state.preview_item = None
            
        # Clear highlights safely
        if self.connection_state.source_hook:
            try:
                self.connection_state.source_hook.set_highlighted(False)
            except RuntimeError:
                # Hook already deleted, ignore
                pass
            
        for hook in self.connection_state.valid_targets:
            try:
                hook.set_highlighted(False)
            except RuntimeError:
                # Hook already deleted, ignore
                pass
        # Clear connection state
        self.connection_state = ConnectionState()
        self.editing_state = EditingState.NORMAL
        
        # Restore cursor safely
        try:
            if self.scene.views():
                self.scene.views()[0].setCursor(QCursor(Qt.ArrowCursor))
        except (RuntimeError, IndexError):
            # View already deleted or no views, ignore
            pass
        
    def update_valid_connection_targets(self):
        """Update the list of valid connection targets."""
        self.connection_state.valid_targets.clear()
        
        if not self.connection_state.source_hook:
            return
            
        # Find all hooks that can be connected to the source
        for predicate_item in self.predicate_items.values():
            if predicate_item == self.connection_state.source_predicate:
                continue  # Skip self-connections
                
            for hook in predicate_item.hooks:
                if self.is_valid_connection(self.connection_state.source_hook, hook):
                    self.connection_state.valid_targets.append(hook)
                    hook.set_highlighted(True)
                    
    def is_valid_connection(self, source_hook: HookItem, target_hook: HookItem) -> bool:
        """Check if a connection between two hooks is valid."""
        # Basic validation - can be extended with transformation rule logic
        
        # Don't connect to self
        if source_hook.parent_predicate == target_hook.parent_predicate:
            return False
            
        # Check if hooks are already connected
        if source_hook.is_connected and target_hook.is_connected:
            # Check if they're connected to the same ligature
            source_endpoint = {
                "node_id": source_hook.parent_predicate.node_id,
                "hook_index": source_hook.hook_index
            }
            target_endpoint = {
                "node_id": target_hook.parent_predicate.node_id,
                "hook_index": target_hook.hook_index
            }
            
            source_lig = self.editor.find_ligature_for_endpoint(source_endpoint)
            target_lig = self.editor.find_ligature_for_endpoint(target_endpoint)
            
            if source_lig == target_lig:
                return False  # Already connected
                
        # TODO: Add more sophisticated validation based on transformation rules
        # - Check context compatibility
        # - Check quantification scope rules
        # - Check logical constraints
        
        return True
        
    def handle_hook_interaction(self, hook: HookItem, predicate: EnhancedPredicateItem):
        """Handle interaction with a predicate hook."""
        if self.mode == InteractionMode.NORMAL:
            # Start new connection
            self.start_connection(hook, predicate)
        elif self.mode == InteractionMode.CONNECTING:
            if hook in self.connection_state.valid_targets:
                # Complete connection
                self.complete_connection(hook, predicate)
            else:
                # Cancel connection
                self.cancel_connection()
                
    def handle_cut_resize(self, cut_item: EnhancedCutItem, new_rect):
        """Handle cut resize operations."""
        # Update the model if necessary
        # TODO: Implement model updates for cut resizing
        
        # Emit signal
        self.cut_resized.emit(cut_item.node_id, new_rect)
        
    def handle_element_move(self, item, new_position: QPointF):
        """Handle element movement operations with validation and ligature updates."""
        # Validate movement is within proper containment
        if hasattr(item, 'node_id'):
            if not self.validate_movement(item.node_id, new_position):
                # Revert to valid position
                self.revert_to_valid_position(item)
                return
        
        # Update ligature routing for connected items
        self.update_ligature_routing_for_item(item)
        
        # Emit signal
        if hasattr(item, 'node_id'):
            self.element_moved.emit(item.node_id, new_position)
            
    def update_ligature_routing(self):
        """Update visual routing of all ligatures."""
        for ligature_item in self.ligature_items.values():
            ligature_item.update_path()
            
    def update_ligature_routing_for_item(self, moved_item):
        """Update ligature routing for a specific moved item using mode-aware manager."""
        print(f"Updating ligature routing for moved item: {moved_item}")
        
        if not hasattr(moved_item, 'node_id'):
            print("Item has no node_id, skipping ligature update")
            return
            
        print(f"Item node_id: {moved_item.node_id}")
        print(f"Available ligatures: {list(self.ligature_items.keys())}")
        
        # Find all ligatures connected to this item
        updated_count = 0
        for ligature_id, ligature_item in self.ligature_items.items():
            print(f"Checking ligature {ligature_id}")
            print(f"Ligature endpoints: {ligature_item.endpoints}")
            
            # Check if this item is connected to the ligature
            for endpoint in ligature_item.endpoints:
                print(f"Checking endpoint: {endpoint}")
                if endpoint['node_id'] == moved_item.node_id:
                    print(f"Found connection! Checking if should update...")
                    
                    # Use mode-aware ligature manager to determine update behavior
                    if self.ligature_manager.should_update_ligature(ligature_item, moved_item):
                        print(f"Updating ligature {ligature_id}")
                        ligature_item.update_path()
                        updated_count += 1
                    else:
                        print(f"Mode-aware manager says not to update ligature {ligature_id}")
                    break
                    
        print(f"Updated {updated_count} ligatures")
                    
    def validate_movement(self, node_id: str, new_position: QPointF) -> bool:
        """Validate movement using mode-aware validator."""
        print(f"Validating movement for {node_id} to {new_position} in mode {self.mode_manager.get_mode()}")
        
        # Use mode-aware validator
        is_valid = self.validator.validate_movement(node_id, new_position, self.graph, self.cut_items)
        
        print(f"Movement validation result: {is_valid}")
        return is_valid
        
    def revert_to_valid_position(self, item):
        """Revert item to its last valid position."""
        if hasattr(item, 'node_id'):
            node_id = item.node_id
            parent_id = self.graph.get_parent(node_id)
            
            if parent_id and parent_id in self.cut_items:
                parent_cut = self.cut_items[parent_id]
                parent_rect = parent_cut.sceneBoundingRect()
                
                # Move to center of parent cut
                center = parent_rect.center()
                item.setPos(center)
                
                print(f"Reverted {node_id} to valid position within parent cut")
            else:
                # Move to scene center if no parent cut
                scene_rect = self.scene.sceneRect()
                center = scene_rect.center()
                item.setPos(center)
                
    def create_ligature_item(self, ligature_id: str, endpoints: List[Dict[str, Any]]) -> LigatureItem:
        """Create a new ligature graphics item."""
        ligature_item = LigatureItem(ligature_id, endpoints)
        
        # Connect endpoints to graphics items
        for endpoint in endpoints:
            node_id = endpoint['node_id']
            if node_id in self.predicate_items:
                predicate_item = self.predicate_items[node_id]
                ligature_item.add_connected_item(endpoint, predicate_item)
                
        # Add to scene and register
        self.scene.addItem(ligature_item)
        self.register_ligature_item(ligature_id, ligature_item)
        
        # Update path
        ligature_item.update_path()
        
        return ligature_item
        
    def get_context_type(self, position: QPointF) -> str:
        """Determine if a position is in a positive or negative context."""
        # Count the number of cuts containing the position
        cut_count = 0
        
        for cut_item in self.cut_items.values():
            if cut_item.contains(cut_item.mapFromScene(position)):
                cut_count += 1
                
        return "positive" if cut_count % 2 == 0 else "negative"
        
    def validate_transformation_operation(self, operation: str, element_id: str, 
                                        target_position: QPointF) -> bool:
        """Validate transformation operations based on Peirce's rules."""
        context_type = self.get_context_type(target_position)
        
        # Apply Peirce's transformation rules
        if operation == "insertion":
            return context_type == "negative"
        elif operation == "erasure":
            return context_type == "positive"
        elif operation == "iteration":
            # TODO: Implement iteration validation
            return True
        elif operation == "de-iteration":
            # TODO: Implement de-iteration validation
            return True
        elif operation == "double_cut":
            return True  # Can be applied in any context
            
        return False
        
    def eventFilter(self, obj, event):
        """Filter scene events for interaction management."""
        if obj == self.scene:
            if event.type() == QEvent.GraphicsSceneMouseMove:
                if self.editing_state == EditingState.CONNECTING:
                    self.update_connection_preview(event.scenePos())
            elif event.type() == QEvent.GraphicsSceneMousePress:
                if event.button() == Qt.RightButton and self.editing_state == EditingState.CONNECTING:
                    self.cancel_connection()
                    return True
                    
        return super().eventFilter(obj, event)
        
    def cleanup(self):
        """Clean up resources and state."""
        self.cancel_connection()
        self.predicate_items.clear()
        self.cut_items.clear()
        self.scene.removeEventFilter(self)

