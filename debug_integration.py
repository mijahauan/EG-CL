#!/usr/bin/env python3
"""
Debug script to identify why movement validation and ligature updates aren't working.
Focuses on the integration between graphics items and the interaction manager.
"""

import sys
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QMainWindow
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

# Import our modules
from eg_model import ExistentialGraph, Node, Hyperedge, GraphObjectType
from eg_logic import EGEditor
from interaction_manager import InteractionManager
from interaction_modes import InteractionMode
from enhanced_graphics_items import EnhancedPredicateItem, EnhancedCutItem
from ligature_item import LigatureItem

class DebugWindow(QMainWindow):
    """Simple debug window to test integration issues."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Debug Integration Issues")
        self.setGeometry(100, 100, 800, 600)
        
        # Create scene and view
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.setCentralWidget(self.view)
        
        # Create graph and interaction manager
        self.graph = ExistentialGraph()
        self.editor = EGEditor(self.graph)
        self.interaction_manager = InteractionManager(self.scene, self.graph, self.editor)
        
        # Set to constrained mode for testing
        self.interaction_manager.set_interaction_mode(InteractionMode.CONSTRAINED)
        
        self.setup_test_graph()
        
    def setup_test_graph(self):
        """Create a simple test graph to debug with."""
        print("Setting up test graph...")
        
        # Create nodes in the graph model
        cat_node = Node(GraphObjectType.PREDICATE, {'name': 'Cat', 'arity': 1})
        animal_node = Node(GraphObjectType.PREDICATE, {'name': 'Animal', 'arity': 1})
        cut_node = Node(GraphObjectType.CUT, {})
        
        self.graph.objects[cat_node.id] = cat_node
        self.graph.objects[animal_node.id] = animal_node
        self.graph.objects[cut_node.id] = cut_node
        
        print(f"Created nodes: {cat_node.id}, {animal_node.id}, {cut_node.id}")
        
        # Create ligature
        ligature = Hyperedge('ligature', [
            {'node_id': cat_node.id, 'hook_index': 0},
            {'node_id': animal_node.id, 'hook_index': 0}
        ])
        self.graph.objects[ligature.id] = ligature
        
        print(f"Created ligature: {ligature.id}")
        
        # Create graphics items with interaction manager reference
        print("Creating graphics items...")
        
        # Create cut item (container)
        cut_item = EnhancedCutItem(
            cut_node.id, 
            QRectF(50, 50, 300, 200), 
            self.graph, 
            self.interaction_manager
        )
        self.scene.addItem(cut_item)
        self.interaction_manager.register_cut_item(cut_node.id, cut_item)
        print(f"Created cut item at {cut_item.boundingRect()}")
        
        # Create predicate items inside the cut
        cat_item = EnhancedPredicateItem(
            cat_node.id, 
            "Cat", 
            self.graph, 
            1, 
            self.interaction_manager
        )
        cat_item.setPos(100, 100)  # Inside the cut
        self.scene.addItem(cat_item)
        self.interaction_manager.register_predicate_item(cat_node.id, cat_item)
        print(f"Created Cat item at {cat_item.pos()}")
        
        animal_item = EnhancedPredicateItem(
            animal_node.id, 
            "Animal", 
            self.graph, 
            1, 
            self.interaction_manager
        )
        animal_item.setPos(200, 100)  # Inside the cut
        self.scene.addItem(animal_item)
        self.interaction_manager.register_predicate_item(animal_node.id, animal_item)
        print(f"Created Animal item at {animal_item.pos()}")
        
        # Create ligature item
        ligature_item = LigatureItem(
            ligature.id,
            [
                {'node_id': cat_node.id, 'hook_index': 0, 'item': cat_item},
                {'node_id': animal_node.id, 'hook_index': 0, 'item': animal_item}
            ]
        )
        self.scene.addItem(ligature_item)
        self.interaction_manager.register_ligature_item(ligature.id, ligature_item)
        print(f"Created ligature item: {ligature_item}")
        
        # Test initial state
        print("\nTesting initial state...")
        print(f"Cut items registered: {list(self.interaction_manager.cut_items.keys())}")
        print(f"Predicate items registered: {list(self.interaction_manager.predicate_items.keys())}")
        print(f"Ligature items registered: {list(self.interaction_manager.ligature_items.keys())}")
        
        # Test movement validation
        print("\nTesting movement validation...")
        test_positions = [
            (QPointF(150, 125), "Inside cut (should be valid)"),
            (QPointF(400, 100), "Outside cut (should be invalid)")
        ]
        
        for position, description in test_positions:
            is_valid = self.interaction_manager.validate_movement(cat_node.id, position)
            print(f"{description}: {is_valid}")
            
        print("\nDebug setup complete. Try moving the Cat predicate to test validation.")
        print("Expected behavior:")
        print("- Moving Cat inside the cut should work")
        print("- Moving Cat outside the cut should be prevented")
        print("- Ligature should update when Cat moves")

def main():
    """Run the debug application."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("Starting Integration Debug")
    print("=" * 40)
    
    window = DebugWindow()
    window.show()
    
    print("\nDebug window created. Test the following:")
    print("1. Try to drag 'Cat' outside the cut boundary")
    print("2. Try to drag 'Cat' within the cut")
    print("3. Observe ligature behavior")
    print("4. Check console output for validation messages")
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

