#!/usr/bin/env python3
"""
Enhanced QGraphicsItem implementations for existential graphs with direct manipulation capabilities.
Includes hook visualization for predicates and resize handles for cuts.
"""

from PySide6.QtWidgets import (QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem, 
                               QGraphicsItem, QGraphicsPathItem, QApplication)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QObject
from PySide6.QtGui import QFont, QBrush, QPen, QColor, QPainterPath, QPainter, QCursor

from typing import List, Optional, Dict, Any
import math

class HookItem(QGraphicsEllipseItem):
    """A visual hook on a predicate that can be used for ligature connections."""
    
    def __init__(self, parent_predicate, hook_index: int, radius: float = 4.0):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.parent_predicate = parent_predicate
        self.hook_index = hook_index
        self.radius = radius
        self.is_connected = False
        self.is_highlighted = False
        
        # Set up visual properties
        self.setBrush(QBrush(QColor("#4CAF50")))  # Green for unconnected
        self.setPen(QPen(QColor("#2E7D32"), 1))
        
        # Enable interaction
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Set parent
        self.setParentItem(parent_predicate)
        
    def set_connected(self, connected: bool):
        """Update visual state based on connection status."""
        self.is_connected = connected
        if connected:
            self.setBrush(QBrush(QColor("#FF9800")))  # Orange for connected
        else:
            self.setBrush(QBrush(QColor("#4CAF50")))  # Green for unconnected
            
    def set_highlighted(self, highlighted: bool):
        """Update visual state for highlighting during connection operations."""
        self.is_highlighted = highlighted
        if highlighted:
            self.setPen(QPen(QColor("#FF5722"), 3))  # Red highlight
            self.setBrush(QBrush(QColor("#FFEB3B")))  # Yellow highlight
        else:
            self.setPen(QPen(QColor("#2E7D32"), 1))
            self.set_connected(self.is_connected)  # Restore connection state
            
    def hoverEnterEvent(self, event):
        """Handle mouse hover enter."""
        if not self.is_highlighted:
            self.setPen(QPen(QColor("#1976D2"), 2))  # Blue hover
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        """Handle mouse hover leave."""
        if not self.is_highlighted:
            self.setPen(QPen(QColor("#2E7D32"), 1))  # Restore normal
        super().hoverLeaveEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse press for connection operations."""
        if event.button() == Qt.LeftButton:
            # Notify parent predicate of hook interaction
            self.parent_predicate.hook_pressed(self, event)
        super().mousePressEvent(event)


class ResizeHandle(QGraphicsRectItem):
    """A resize handle for cut manipulation."""
    
    def __init__(self, parent_cut, position: str, size: float = 8.0):
        super().__init__(-size/2, -size/2, size, size)
        self.parent_cut = parent_cut
        self.position = position  # 'nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'
        self.size = size
        
        # Set up visual properties
        self.setBrush(QBrush(QColor("#2196F3")))
        self.setPen(QPen(QColor("#1976D2"), 1))
        
        # Enable interaction
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        
        # Set appropriate cursor based on position
        cursor_map = {
            'nw': Qt.SizeFDiagCursor, 'se': Qt.SizeFDiagCursor,
            'ne': Qt.SizeBDiagCursor, 'sw': Qt.SizeBDiagCursor,
            'n': Qt.SizeVerCursor, 's': Qt.SizeVerCursor,
            'e': Qt.SizeHorCursor, 'w': Qt.SizeHorCursor
        }
        self.setCursor(QCursor(cursor_map.get(position, Qt.SizeAllCursor)))
        
        # Set parent
        self.setParentItem(parent_cut)
        
    def hoverEnterEvent(self, event):
        """Handle mouse hover enter."""
        self.setBrush(QBrush(QColor("#64B5F6")))  # Lighter blue on hover
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        """Handle mouse hover leave."""
        self.setBrush(QBrush(QColor("#2196F3")))  # Restore normal
        super().hoverLeaveEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle resize dragging."""
        self.parent_cut.handle_resize(self, event)
        super().mouseMoveEvent(event)


class EnhancedPredicateItem(QGraphicsTextItem):
    """Enhanced predicate item with hook visualization and interaction capabilities."""
    
    def __init__(self, node_id: str, text: str, graph_model, arity: int = 0, interaction_manager=None):
        super().__init__(text)
        self.node_id = node_id
        self.graph_model = graph_model
        self.arity = arity
        self.hooks: List[HookItem] = []
        self.is_dragging_connection = False
        self.connection_preview_line = None
        self.interaction_manager = interaction_manager  # Reference to interaction manager
        
        # Set up basic properties
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(2)  # Above ligatures (1) and cuts (0)
        
        # Create hooks based on arity
        self.create_hooks()
        
    def create_hooks(self):
        """Create hook items based on predicate arity."""
        # Clear existing hooks
        for hook in self.hooks:
            hook.setParentItem(None)
        self.hooks.clear()
        
        # Create new hooks
        for i in range(self.arity):
            hook = HookItem(self, i)
            self.hooks.append(hook)
            
        # Position hooks
        self.position_hooks()
        
    def position_hooks(self):
        """Position hooks along the bottom edge of the predicate."""
        if not self.hooks:
            return
            
        rect = self.boundingRect()
        bottom_y = rect.bottom() + 5  # Slightly below the text
        
        if len(self.hooks) == 1:
            # Single hook in center
            center_x = rect.center().x()
            self.hooks[0].setPos(center_x, bottom_y)
        else:
            # Multiple hooks distributed along bottom edge
            left_x = rect.left() + 10
            right_x = rect.right() - 10
            width = right_x - left_x
            
            for i, hook in enumerate(self.hooks):
                if len(self.hooks) > 1:
                    x = left_x + (width * i / (len(self.hooks) - 1))
                else:
                    x = rect.center().x()
                hook.setPos(x, bottom_y)
                
    def hook_pressed(self, hook: HookItem, event):
        """Handle hook press events for connection operations."""
        print(f"Hook {hook.hook_index} pressed on predicate {self.node_id}")
        # TODO: Implement connection logic
        # This would typically start a connection operation or complete one
        
    def update_arity(self, new_arity: int):
        """Update the arity and recreate hooks."""
        self.arity = new_arity
        self.create_hooks()
        
    def set_hook_connection_state(self, hook_index: int, connected: bool):
        """Update the connection state of a specific hook."""
        if 0 <= hook_index < len(self.hooks):
            self.hooks[hook_index].set_connected(connected)
            
    def highlight_hook(self, hook_index: int, highlighted: bool):
        """Highlight a specific hook."""
        if 0 <= hook_index < len(self.hooks):
            self.hooks[hook_index].set_highlighted(highlighted)
            
    def get_hook_scene_position(self, hook_index: int) -> QPointF:
        """Get the scene position of a specific hook."""
        if 0 <= hook_index < len(self.hooks):
            return self.hooks[hook_index].scenePos()
        return QPointF()
        
    def paint(self, painter, option, widget):
        """Override paint to draw selection highlight."""
        super().paint(painter, option, widget)
        if self.isSelected():
            pen = QPen(QColor("red"), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.boundingRect())
            
    def itemChange(self, change, value):
        """Handle item changes, particularly position changes."""
        if change == QGraphicsItem.ItemPositionChange:
            print(f"Predicate {self.node_id} position changing to {value}")
            
            # Validate movement before it happens
            if self.interaction_manager:
                if not self.interaction_manager.validate_movement(self.node_id, value):
                    print(f"Movement rejected for {self.node_id}")
                    # Return current position to prevent movement
                    return self.pos()
                    
        elif change == QGraphicsItem.ItemPositionHasChanged:
            print(f"Predicate {self.node_id} position changed to {value}")
            
            # Reposition hooks when predicate moves
            self.position_hooks()
            
            # Update ligature routing
            if self.interaction_manager:
                print(f"Updating ligature routing for {self.node_id}")
                self.interaction_manager.update_ligature_routing_for_item(self)
                
        return super().itemChange(change, value)


class EnhancedCutItem(QGraphicsRectItem):
    """Enhanced cut item with resize handles and drag-drop feedback."""
    
    def __init__(self, node_id: str, rect: QRectF, graph_model, interaction_manager=None):
        super().__init__(rect)
        self.node_id = node_id
        self.graph_model = graph_model
        self.resize_handles: List[ResizeHandle] = []
        self.is_resizing = False
        self.original_rect = rect
        self.drop_highlight = False
        self.interaction_manager = interaction_manager  # Reference to interaction manager
        
        # Set up basic properties
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setAcceptDrops(True)
        self.setAcceptHoverEvents(True)
        self.setZValue(0)  # Bottom layer - behind ligatures (1) and predicates (2)
        
        # Set visual properties based on nesting level
        level = self.graph_model.get_nesting_level(self.node_id)
        if level % 2 != 0:
            self.setBrush(QBrush(QColor("#e9e9e9")))
        else:
            self.setBrush(QBrush(QColor("#ffffff")))
            
        # Create resize handles
        self.create_resize_handles()
        
    def create_resize_handles(self):
        """Create resize handles at corners and edges."""
        # Clear existing handles
        for handle in self.resize_handles:
            handle.setParentItem(None)
        self.resize_handles.clear()
        
        # Create handles for corners and edges
        positions = ['nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w']
        for pos in positions:
            handle = ResizeHandle(self, pos)
            self.resize_handles.append(handle)
            
        # Position handles
        self.position_resize_handles()
        
    def position_resize_handles(self):
        """Position resize handles around the cut boundary."""
        rect = self.rect()
        
        handle_positions = {
            'nw': QPointF(rect.left(), rect.top()),
            'ne': QPointF(rect.right(), rect.top()),
            'sw': QPointF(rect.left(), rect.bottom()),
            'se': QPointF(rect.right(), rect.bottom()),
            'n': QPointF(rect.center().x(), rect.top()),
            's': QPointF(rect.center().x(), rect.bottom()),
            'e': QPointF(rect.right(), rect.center().y()),
            'w': QPointF(rect.left(), rect.center().y())
        }
        
        for handle in self.resize_handles:
            pos = handle_positions.get(handle.position, QPointF())
            handle.setPos(pos)
            
    def handle_resize(self, handle: ResizeHandle, event):
        """Handle resize operations from resize handles."""
        if not self.is_resizing:
            self.is_resizing = True
            self.original_rect = self.rect()
            
        # Calculate new rectangle based on handle position and movement
        current_rect = self.rect()
        delta = event.scenePos() - event.lastScenePos()
        
        # Apply resize based on handle position
        new_rect = QRectF(current_rect)
        
        if 'n' in handle.position:
            new_rect.setTop(current_rect.top() + delta.y())
        if 's' in handle.position:
            new_rect.setBottom(current_rect.bottom() + delta.y())
        if 'w' in handle.position:
            new_rect.setLeft(current_rect.left() + delta.x())
        if 'e' in handle.position:
            new_rect.setRight(current_rect.right() + delta.x())
            
        # Enforce minimum size
        min_size = 50
        if new_rect.width() < min_size:
            if 'w' in handle.position:
                new_rect.setLeft(new_rect.right() - min_size)
            else:
                new_rect.setRight(new_rect.left() + min_size)
                
        if new_rect.height() < min_size:
            if 'n' in handle.position:
                new_rect.setTop(new_rect.bottom() - min_size)
            else:
                new_rect.setBottom(new_rect.top() + min_size)
                
        # Update rectangle
        self.setRect(new_rect)
        self.position_resize_handles()
        
    def set_drop_highlight(self, highlight: bool):
        """Set visual feedback for drag-drop operations."""
        self.drop_highlight = highlight
        if highlight:
            self.setPen(QPen(QColor("#4CAF50"), 3, Qt.DashLine))  # Green dashed border
        else:
            self.setPen(QPen(QColor("black"), 1))  # Normal border
            
    def dragEnterEvent(self, event):
        """Handle drag enter events."""
        # Check if the dragged item can be dropped here
        # TODO: Implement proper validation based on transformation rules
        self.set_drop_highlight(True)
        event.acceptProposedAction()
        
    def dragLeaveEvent(self, event):
        """Handle drag leave events."""
        self.set_drop_highlight(False)
        
    def dropEvent(self, event):
        """Handle drop events."""
        self.set_drop_highlight(False)
        # TODO: Implement actual drop logic
        print(f"Item dropped on cut {self.node_id}")
        event.acceptProposedAction()
        
    def paint(self, painter, option, widget):
        """Override paint to draw selection highlight and drop feedback."""
        # Draw the cut with rounded corners
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set brush and pen
        painter.setBrush(self.brush())
        
        if self.isSelected():
            painter.setPen(QPen(QColor("red"), 2, Qt.SolidLine))
        elif self.drop_highlight:
            painter.setPen(QPen(QColor("#4CAF50"), 3, Qt.DashLine))
        else:
            painter.setPen(self.pen())
            
        # Draw rounded rectangle
        painter.drawRoundedRect(self.rect(), 15, 15)
        
    def itemChange(self, change, value):
        """Handle item changes."""
        if change == QGraphicsItem.ItemPositionChange:
            print(f"Cut {self.node_id} position changing to {value}")
            
            # Validate movement before it happens
            if self.interaction_manager:
                if not self.interaction_manager.validate_movement(self.node_id, value):
                    print(f"Movement rejected for cut {self.node_id}")
                    # Return current position to prevent movement
                    return self.pos()
                    
        elif change == QGraphicsItem.ItemPositionHasChanged:
            print(f"Cut {self.node_id} position changed to {value}")
            
            # Update handle positions when cut moves
            self.position_resize_handles()
            
            # Update ligature routing
            if self.interaction_manager:
                print(f"Updating ligature routing for cut {self.node_id}")
                self.interaction_manager.update_ligature_routing_for_item(self)
                
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            # Show/hide resize handles based on selection
            for handle in self.resize_handles:
                handle.setVisible(value)
        return super().itemChange(change, value)
        
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.LeftButton:
            self.is_resizing = False
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if self.is_resizing:
            self.is_resizing = False
            # TODO: Notify graph model of size change
            print(f"Cut {self.node_id} resized to {self.rect()}")
        super().mouseReleaseEvent(event)


class ConnectionPreviewItem(QGraphicsPathItem):
    """A temporary visual item for previewing ligature connections."""
    
    def __init__(self, start_point: QPointF):
        super().__init__()
        self.start_point = start_point
        self.end_point = start_point
        
        # Set up visual properties
        self.setPen(QPen(QColor("#FF9800"), 2, Qt.DashLine))
        
        # Update path
        self.update_path()
        
    def update_end_point(self, end_point: QPointF):
        """Update the end point of the preview line."""
        self.end_point = end_point
        self.update_path()
        
    def update_path(self):
        """Update the path based on start and end points."""
        path = QPainterPath()
        path.moveTo(self.start_point)
        path.lineTo(self.end_point)
        self.setPath(path)

