#!/usr/bin/env python3
"""
Selectable ligature graphics item for existential graphs.
Provides visual representation and interaction capabilities for ligatures.
"""

from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QColor, QPainterPath, QPainter, QPainterPathStroker
from typing import List, Optional, Dict, Any

class LigatureItem(QGraphicsPathItem):
    """A selectable graphics item representing a ligature connection."""
    
    def __init__(self, ligature_id: str, endpoints: List[Dict[str, Any]]):
        super().__init__()
        self.ligature_id = ligature_id
        self.endpoints = endpoints
        self.connected_items = {}  # Map endpoint to graphics item
        
        # Set up visual properties
        self.normal_pen = QPen(QColor("black"), 2, Qt.SolidLine)
        self.selected_pen = QPen(QColor("red"), 3, Qt.SolidLine)
        self.hover_pen = QPen(QColor("blue"), 2, Qt.SolidLine)
        
        self.setPen(self.normal_pen)
        
        # Enable interaction
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)  # Make ligatures movable
        self.setAcceptHoverEvents(True)
        
        # Set z-value to appear above cuts but below predicates
        self.setZValue(1)  # Above cuts (0) but below predicates (2)
        
    def add_connected_item(self, endpoint: Dict[str, Any], item):
        """Add a connected graphics item for an endpoint."""
        key = f"{endpoint['node_id']}_{endpoint['hook_index']}"
        self.connected_items[key] = item
        
    def remove_connected_item(self, endpoint: Dict[str, Any]):
        """Remove a connected graphics item for an endpoint."""
        key = f"{endpoint['node_id']}_{endpoint['hook_index']}"
        self.connected_items.pop(key, None)
        
    def update_path(self):
        """Update the ligature path based on connected item positions."""
        print(f"Updating ligature path for {self.ligature_id}")
        print(f"Connected items: {list(self.connected_items.keys())}")
        
        if len(self.connected_items) < 1:
            print("No connected items, skipping path update")
            return
            
        points = []
        for endpoint in self.endpoints:
            key = f"{endpoint['node_id']}_{endpoint['hook_index']}"
            print(f"Looking for endpoint: {key}")
            
            if key in self.connected_items:
                item = self.connected_items[key]
                print(f"Found connected item: {item}")
                
                if hasattr(item, 'get_hook_scene_position'):
                    # For predicate items with hooks
                    hook_pos = item.get_hook_scene_position(endpoint['hook_index'])
                    scene_pos = self.mapFromScene(hook_pos)
                    points.append(scene_pos)
                    print(f"Added hook position: {hook_pos} -> {scene_pos}")
                elif hasattr(item, 'scenePos'):
                    # For other items, use center position
                    item_pos = item.scenePos()
                    scene_pos = self.mapFromScene(item_pos)
                    points.append(scene_pos)
                    print(f"Added item position: {item_pos} -> {scene_pos}")
            else:
                print(f"Endpoint {key} not found in connected items")
                    
        print(f"Total points collected: {len(points)}")
        
        if len(points) >= 2:
            # Create path connecting all points
            path = QPainterPath()
            path.moveTo(points[0])
            
            if len(points) == 2:
                # Simple line for two points
                path.lineTo(points[1])
                print(f"Created line from {points[0]} to {points[1]}")
            else:
                # For multiple points, create a more complex path
                for i in range(1, len(points)):
                    path.lineTo(points[i])
                    print(f"Added line to {points[i]}")
                    
            self.setPath(path)
            print("Path updated successfully")
            
        elif len(points) == 1:
            # Create a stub for single endpoint
            path = QPainterPath()
            start = points[0]
            end = QPointF(start.x(), start.y() + 20)
            path.moveTo(start)
            path.lineTo(end)
            self.setPath(path)
            print(f"Created stub from {start} to {end}")
        else:
            print("No valid points, clearing path")
            self.setPath(QPainterPath())
            
    def paint(self, painter, option, widget):
        """Override paint to handle selection highlighting."""
        if self.isSelected():
            self.setPen(self.selected_pen)
        else:
            self.setPen(self.normal_pen)
            
        super().paint(painter, option, widget)
        
    def hoverEnterEvent(self, event):
        """Handle mouse hover enter."""
        if not self.isSelected():
            self.setPen(self.hover_pen)
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        """Handle mouse hover leave."""
        if not self.isSelected():
            self.setPen(self.normal_pen)
        super().hoverLeaveEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse press for selection."""
        if event.button() == Qt.LeftButton:
            self.setSelected(True)
        super().mousePressEvent(event)
        
    def contextMenuEvent(self, event):
        """Handle right-click context menu (placeholder for future features)."""
        # TODO: Implement context menu for ligature operations
        # - Delete ligature
        # - Add endpoint
        # - Ligature properties
        pass
        
    def boundingRect(self):
        """Return bounding rectangle with some padding for easier selection."""
        rect = super().boundingRect()
        # Add padding to make selection easier
        padding = 5
        return rect.adjusted(-padding, -padding, padding, padding)
        
    def shape(self):
        """Return shape for more precise hit testing."""
        # Create a slightly thicker shape for easier selection
        stroker = QPainterPathStroker()
        stroker.setWidth(8)  # Thicker for hit testing
        stroker.setCapStyle(Qt.RoundCap)
        stroker.setJoinStyle(Qt.RoundJoin)
        return stroker.createStroke(self.path())

