#!/usr/bin/env python3
"""
Enhanced main GUI for existential graphs with direct manipulation capabilities.
Integrates enhanced graphics items with hook visualization and resize handles.
"""

import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                               QLabel, QPushButton, QHBoxLayout, QInputDialog,
                               QGraphicsView, QGraphicsScene, QMessageBox,
                               QToolBar, QStatusBar, QSplitter)
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer
from PySide6.QtGui import QFont, QBrush, QPen, QColor, QAction, QKeySequence, QPainter

from enhanced_graphics_items import (EnhancedPredicateItem, EnhancedCutItem, 
                                   ConnectionPreviewItem)
from ligature_item import LigatureItem
from interaction_manager import InteractionManager, InteractionMode
from eg_model import ExistentialGraph, GraphObjectType, Node, Hyperedge
from eg_logic import EGEditor, ClifTranslator
from eg_renderer import Renderer

class EnhancedMainWindow(QMainWindow):
    """Enhanced main application window with direct manipulation capabilities."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize core components
        self.graph = ExistentialGraph()
        self.editor = EGEditor(self.graph)
        self.renderer = Renderer(self.graph)
        
        # Initialize GUI components
        self.setup_ui()
        self.setup_scene()
        self.setup_interaction_manager()
        self.setup_actions()
        self.setup_status_bar()
        
        # Create initial graph
        self.create_initial_graph()
        self.refresh_display()
        
    def setup_ui(self):
        """Set up the user interface layout."""
        self.setWindowTitle("Enhanced Existential Graphs Editor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # Graphics view for the graph
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor("white")))
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        self.view.setRenderHint(QPainter.Antialiasing)
        
        # Status and info panel
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # CLIF translation display
        self.clif_label = QLabel("CLIF translation will appear here.")
        self.clif_label.setFont(QFont("Courier New", 10))
        self.clif_label.setStyleSheet("""
            background-color: #f0f0f0; 
            padding: 10px; 
            border: 1px solid #ccc;
            border-radius: 5px;
        """)
        self.clif_label.setWordWrap(True)
        
        # Interaction mode display
        self.mode_label = QLabel("Mode: Normal")
        self.mode_label.setFont(QFont("Arial", 9))
        self.mode_label.setStyleSheet("padding: 5px; background-color: #e3f2fd;")
        
        info_layout.addWidget(QLabel("CLIF Translation:"))
        info_layout.addWidget(self.clif_label)
        info_layout.addWidget(self.mode_label)
        
        # Add to splitter
        splitter.addWidget(self.view)
        splitter.addWidget(info_widget)
        splitter.setSizes([600, 200])
        
    def setup_scene(self):
        """Set up the graphics scene."""
        self.scene_items = {}  # Map node_id to graphics items
        
        # Connect scene selection changes
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
    def setup_interaction_manager(self):
        """Set up the interaction manager."""
        self.interaction_manager = InteractionManager(self.scene, self.graph, self.editor)
        
        # Connect signals
        self.interaction_manager.ligature_created.connect(self.on_ligature_created)
        self.interaction_manager.ligature_removed.connect(self.on_ligature_removed)
        self.interaction_manager.element_moved.connect(self.on_element_moved)
        self.interaction_manager.cut_resized.connect(self.on_cut_resized)
        
    def setup_actions(self):
        """Set up menu actions and toolbar."""
        # Create toolbar
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Add predicate action
        add_predicate_action = QAction("Add Predicate", self)
        add_predicate_action.setShortcut(QKeySequence("Ctrl+P"))
        add_predicate_action.triggered.connect(self.on_add_predicate)
        toolbar.addAction(add_predicate_action)
        
        # Add cut action
        add_cut_action = QAction("Add Cut", self)
        add_cut_action.setShortcut(QKeySequence("Ctrl+C"))
        add_cut_action.triggered.connect(self.on_add_cut)
        toolbar.addAction(add_cut_action)
        
        toolbar.addSeparator()
        
        # Connection mode toggle
        self.connection_mode_action = QAction("Connection Mode", self)
        self.connection_mode_action.setCheckable(True)
        self.connection_mode_action.setShortcut(QKeySequence("Ctrl+L"))
        self.connection_mode_action.triggered.connect(self.toggle_connection_mode)
        toolbar.addAction(self.connection_mode_action)
        
        toolbar.addSeparator()
        
        # Clear selection action
        clear_selection_action = QAction("Clear Selection", self)
        clear_selection_action.setShortcut(QKeySequence("Escape"))
        clear_selection_action.triggered.connect(self.clear_selection)
        toolbar.addAction(clear_selection_action)
        
        # Refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self.refresh_display)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # Mode switching controls
        from interaction_modes import InteractionMode
        
        # Constrained mode
        constrained_action = QAction("Constrained Mode", self)
        constrained_action.setShortcut(QKeySequence("Ctrl+1"))
        constrained_action.triggered.connect(lambda: self.set_interaction_mode(InteractionMode.CONSTRAINED))
        toolbar.addAction(constrained_action)
        
        # Composition mode  
        composition_action = QAction("Composition Mode", self)
        composition_action.setShortcut(QKeySequence("Ctrl+2"))
        composition_action.triggered.connect(lambda: self.set_interaction_mode(InteractionMode.COMPOSITION))
        toolbar.addAction(composition_action)
        
        # Transformation mode
        transformation_action = QAction("Transformation Mode", self)
        transformation_action.setShortcut(QKeySequence("Ctrl+3"))
        transformation_action.triggered.connect(lambda: self.set_interaction_mode(InteractionMode.TRANSFORMATION))
        toolbar.addAction(transformation_action)
        
        toolbar.addSeparator()
        
        # Copy/Paste actions
        copy_action = QAction("Copy", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy_selection)
        toolbar.addAction(copy_action)
        
        paste_action = QAction("Paste", self)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.paste_at_cursor)
        toolbar.addAction(paste_action)
        
    def setup_status_bar(self):
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def create_initial_graph(self):
        """Create an initial graph with some example content."""
        soa_id = self.graph.root_id
        
        # Add a cut with a predicate
        cut_id, _ = self.editor.add_cut(soa_id)
        cat_id, _ = self.editor.add_predicate("Cat", 1, cut_id)
        
        # Add another predicate outside the cut
        animal_id, _ = self.editor.add_predicate("Animal", 1, soa_id)
        
        # Create a ligature connection
        cat_endpoint = {"node_id": cat_id, "hook_index": 0}
        animal_endpoint = {"node_id": animal_id, "hook_index": 0}
        self.editor.connect(cat_endpoint, animal_endpoint)
        
    def refresh_display(self):
        """Refresh the entire display."""
        print("Refreshing display...")
        
        # Clear scene
        self.scene.clear()
        self.scene_items.clear()
        
        # Recalculate layout
        self.renderer._calculate_layout(self.graph.root_id)
        
        # Draw nodes
        self._draw_node_on_scene(self.graph.root_id, 0, 0)
        
        # Draw ligatures
        self._draw_ligatures_on_scene()
        
        # Update CLIF translation
        self.update_clif_display()
        
        print("Display refreshed.")
        
    def _draw_node_on_scene(self, node_id: str, parent_abs_x: float, parent_abs_y: float):
        """Draw a node and its children on the scene using enhanced items."""
        node = self.graph.get_object(node_id)
        node_layout = self.renderer.layout.get(node_id, {})
        
        abs_x = parent_abs_x + node_layout.get("x", 0)
        abs_y = parent_abs_y + node_layout.get("y", 0)
        
        item = None
        
        if node.node_type == GraphObjectType.CUT:
            if self.graph.get_parent(node_id):  # Don't draw rect for SOA
                width = node_layout.get("width", 100)
                height = node_layout.get("height", 100)
                rect = QRectF(0, 0, width, height)
                
                # Create enhanced cut item
                item = EnhancedCutItem(node_id, rect, self.graph, self.interaction_manager)
                item.setPos(abs_x, abs_y)
                
                # Register with interaction manager
                self.interaction_manager.register_cut_item(node_id, item)
                
        elif node.node_type == GraphObjectType.PREDICATE:
            text = node.properties.get("name", "")
            arity = node.properties.get("arity", 0)
            
            # Create enhanced predicate item
            item = EnhancedPredicateItem(node_id, text, self.graph, arity, self.interaction_manager)
            item.setFont(QFont(self.renderer.config['font_family'], 
                              self.renderer.config['font_size']))
            
            # Position with padding
            text_x_offset = self.renderer.config['predicate_padding_x']
            text_y_offset = self.renderer.config['predicate_padding_y']
            item.setPos(abs_x + text_x_offset, abs_y + text_y_offset)
            
            # Register with interaction manager
            self.interaction_manager.register_predicate_item(node_id, item)
            
            # Connect hook interactions
            for hook in item.hooks:
                hook.mousePressEvent = lambda event, h=hook, p=item: self.on_hook_pressed(h, p, event)
                
        if item:
            self.scene.addItem(item)
            self.scene_items[node_id] = item
            
        # Draw children
        if node.node_type == GraphObjectType.CUT:
            for content_id in node.contents:
                content_obj = self.graph.get_object(content_id)
                if isinstance(content_obj, Node):
                    self._draw_node_on_scene(content_id, abs_x, abs_y)
                    
    def _draw_ligatures_on_scene(self):
        """Draw ligatures on the scene using LigatureItem."""
        all_ligatures = [obj for obj in self.graph.objects.values() 
                        if isinstance(obj, Hyperedge)]
        
        for lig in all_ligatures:
            if len(lig.endpoints) < 1:
                continue
                
            # Create ligature item using interaction manager
            ligature_item = self.interaction_manager.create_ligature_item(lig.id, lig.endpoints)
            
            # Update hook connection states
            for ep in lig.endpoints:
                node = self.graph.get_object(ep['node_id'])
                if node and node.id in self.scene_items:
                    item = self.scene_items[node.id]
                    if isinstance(item, EnhancedPredicateItem):
                        # Update hook connection state
                        item.set_hook_connection_state(ep['hook_index'], True)
                
    def on_hook_pressed(self, hook, predicate, event):
        """Handle hook press events."""
        if event.button() == Qt.LeftButton:
            self.interaction_manager.handle_hook_interaction(hook, predicate)
            
    def on_add_predicate(self):
        """Handle add predicate action."""
        name, ok = QInputDialog.getText(self, "Add Predicate", 
                                       "Enter Predicate Name:")
        if ok and name.strip():
            arity, ok = QInputDialog.getInt(self, "Add Predicate", 
                                           "Enter Arity (number of hooks):", 
                                           value=1, minValue=0, maxValue=10)
            if ok:
                # Add to root for now - could be enhanced to add to selected cut
                parent_id = self.graph.root_id
                self.editor.add_predicate(name.strip(), arity, parent_id)
                self.refresh_display()
                
    def on_add_cut(self):
        """Handle add cut action."""
        # Add to root for now - could be enhanced to add to selected cut
        parent_id = self.graph.root_id
        self.editor.add_cut(parent_id)
        self.refresh_display()
        
    def toggle_connection_mode(self):
        """Toggle connection mode."""
        if self.connection_mode_action.isChecked():
            self.mode_label.setText("Mode: Connection")
            self.status_bar.showMessage("Connection mode active - click hooks to connect")
        else:
            self.mode_label.setText("Mode: Normal")
            self.status_bar.showMessage("Normal mode")
            self.interaction_manager.cancel_connection()
            
    def clear_selection(self):
        """Clear all selections."""
        self.scene.clearSelection()
        self.interaction_manager.cancel_connection()
        
    def update_clif_display(self):
        """Update the CLIF translation display."""
        translator = ClifTranslator(self.graph)
        clif_string = translator.translate()
        self.clif_label.setText(clif_string)
        
    def on_selection_changed(self):
        """Handle selection changes."""
        selected_items = self.scene.selectedItems()
        if selected_items:
            item = selected_items[0]
            if hasattr(item, 'node_id'):
                node = self.graph.get_object(item.node_id)
                self.status_bar.showMessage(f"Selected: {node.node_type.name} ({item.node_id[:8]})")
        else:
            self.status_bar.showMessage("Ready")
            
    def on_ligature_created(self, source_id: str, source_hook: int, 
                           target_id: str, target_hook: int):
        """Handle ligature creation."""
        self.status_bar.showMessage(f"Ligature created between {source_id[:8]} and {target_id[:8]}")
        self.refresh_display()  # Refresh to show new ligature
        
    def on_ligature_removed(self, ligature_id: str):
        """Handle ligature removal."""
        self.status_bar.showMessage(f"Ligature removed: {ligature_id[:8]}")
        self.refresh_display()
        
    def on_element_moved(self, element_id: str, new_position: QPointF):
        """Handle element movement."""
        self.status_bar.showMessage(f"Element moved: {element_id[:8]}")
        
    def on_cut_resized(self, cut_id: str, new_rect):
        """Handle cut resizing."""
        self.status_bar.showMessage(f"Cut resized: {cut_id[:8]}")
        
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self.clear_selection()
        elif event.key() == Qt.Key_Delete:
            self.delete_selected_items()
        else:
            super().keyPressEvent(event)
            
    def delete_selected_items(self):
        """Delete selected items (placeholder for future implementation)."""
        selected_items = self.scene.selectedItems()
        if selected_items:
            reply = QMessageBox.question(self, "Delete Items", 
                                       f"Delete {len(selected_items)} selected item(s)?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                # TODO: Implement deletion with proper validation
                self.status_bar.showMessage("Deletion not yet implemented")
                
    def set_interaction_mode(self, mode):
        """Set the interaction mode and update UI."""
        self.interaction_manager.set_interaction_mode(mode)
        
        # Update mode display
        mode_name = self.interaction_manager.mode_manager.get_mode_display_name(mode)
        self.mode_label.setText(f"Mode: {mode_name}")
        
        # Update status bar
        description = self.interaction_manager.get_mode_description()
        self.status_bar.showMessage(f"Mode: {mode_name} - {description}")
        
        print(f"GUI mode switched to: {mode_name}")
        
    def copy_selection(self):
        """Copy selected items to clipboard."""
        if self.interaction_manager.copy_selection():
            clipboard_info = self.interaction_manager.get_clipboard_info()
            if clipboard_info:
                count = clipboard_info['node_count']
                mode = clipboard_info['source_mode'].name
                self.status_bar.showMessage(f"Copied {count} items from {mode} mode")
            else:
                self.status_bar.showMessage("Items copied to clipboard")
        else:
            self.status_bar.showMessage("No items selected to copy")
            
    def paste_at_cursor(self):
        """Paste clipboard content at cursor position."""
        # Get cursor position in scene coordinates
        cursor_pos = self.view.mapToScene(self.view.mapFromGlobal(self.view.cursor().pos()))
        
        # Check if paste is allowed at this position
        can_paste, reason = self.interaction_manager.can_paste_at_position(cursor_pos)
        
        if can_paste:
            if self.interaction_manager.paste_at_cursor(cursor_pos):
                self.status_bar.showMessage(f"Pasted at {cursor_pos.x():.0f}, {cursor_pos.y():.0f}")
                self.refresh_display()  # Refresh to show new items
            else:
                self.status_bar.showMessage("Paste operation failed")
        else:
            self.status_bar.showMessage(f"Cannot paste: {reason}")
            print(f"Paste rejected: {reason}")
            
    def get_scene_center(self):
        """Get the center point of the visible scene area."""
        view_rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        return view_rect.center()
                
    def closeEvent(self, event):
        """Handle application close."""
        self.interaction_manager.cleanup()
        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Enhanced Existential Graphs Editor")
    app.setApplicationVersion("1.0")
    
    # Create and show main window
    window = EnhancedMainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

