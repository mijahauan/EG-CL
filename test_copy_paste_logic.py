#!/usr/bin/env python3
"""
Logic-only test for copy/paste functionality.
Tests the core logic without requiring Qt display components.
"""

from PySide6.QtCore import QPointF, QRectF

# Import our modules
from eg_model import ExistentialGraph, Node, Hyperedge, GraphObjectType
from interaction_modes import InteractionMode
from graph_clipboard import GraphClipboard, ContextAnalyzer, GraphFragment

def test_copy_paste_logic():
    """Test the core copy/paste logic without GUI components."""
    
    print("Testing Copy/Paste Logic (No GUI)")
    print("=" * 40)
    
    # Create test graph
    graph = ExistentialGraph()
    
    # Create nodes
    cat_node = Node(GraphObjectType.PREDICATE, {'name': 'Cat', 'arity': 1})
    animal_node = Node(GraphObjectType.PREDICATE, {'name': 'Animal', 'arity': 1})
    cut_node = Node(GraphObjectType.CUT, {})
    
    graph.objects[cat_node.id] = cat_node
    graph.objects[animal_node.id] = animal_node
    graph.objects[cut_node.id] = cut_node
    
    # Create ligature
    ligature = Hyperedge('ligature', [
        {'node_id': cat_node.id, 'hook_index': 0},
        {'node_id': animal_node.id, 'hook_index': 0}
    ])
    graph.objects[ligature.id] = ligature
    
    print(f"Created graph with {len(graph.objects)} objects")
    
    # Test clipboard
    clipboard = GraphClipboard(graph)
    
    print("\n1. Testing Fragment Creation...")
    
    # Create mock selected items
    class MockItem:
        def __init__(self, node_id, rect):
            self.node_id = node_id
            self._rect = rect
            
        def sceneBoundingRect(self):
            return self._rect
    
    selected_items = [
        MockItem(cat_node.id, QRectF(100, 100, 50, 30)),
        MockItem(animal_node.id, QRectF(200, 100, 50, 30))
    ]
    
    # Test copying
    copy_success = clipboard.copy_selection(selected_items, InteractionMode.COMPOSITION)
    print(f"Copy success: {copy_success}")
    
    if copy_success:
        info = clipboard.get_clipboard_info()
        print(f"Clipboard info: {info}")
    
    print("\n2. Testing Context Analysis...")
    
    # Create mock cut items for context analysis
    class MockCutItem:
        def __init__(self, rect):
            self._rect = rect
            
        def sceneBoundingRect(self):
            return self._rect
    
    cut_items = {
        cut_node.id: MockCutItem(QRectF(50, 50, 250, 150))
    }
    
    context_analyzer = ContextAnalyzer(graph)
    
    test_positions = [
        (QPointF(150, 125), "Inside cut"),
        (QPointF(400, 100), "Outside cut")
    ]
    
    for position, description in test_positions:
        context = context_analyzer.get_context_type(position, cut_items)
        can_insert = context_analyzer.can_insert_at_position(position, cut_items)
        
        print(f"{description}: context={context}, can_insert={can_insert}")
    
    print("\n3. Testing Mode-Aware Paste Validation...")
    
    modes_to_test = [
        InteractionMode.COMPOSITION,
        InteractionMode.CONSTRAINED,
        InteractionMode.TRANSFORMATION
    ]
    
    # Test paste validation for each mode
    inside_cut = QPointF(150, 125)  # Negative context
    outside_cut = QPointF(400, 100)  # Positive context
    
    for mode in modes_to_test:
        print(f"\n{mode.name} Mode:")
        
        # Test inside cut (negative context)
        can_paste_inside, reason_inside = clipboard.can_paste_at_position(
            inside_cut, mode, cut_items
        )
        print(f"  Inside cut: {can_paste_inside} - {reason_inside}")
        
        # Test outside cut (positive context)
        can_paste_outside, reason_outside = clipboard.can_paste_at_position(
            outside_cut, mode, cut_items
        )
        print(f"  Outside cut: {can_paste_outside} - {reason_outside}")
    
    print("\n4. Testing JSON Export...")
    
    if clipboard.has_clipboard_content():
        json_export = clipboard.export_fragment_to_json()
        if json_export:
            print("JSON export successful!")
            print("Sample:", json_export[:100] + "...")
        else:
            print("JSON export failed")
    
    print("\n5. Testing Paste Operation...")
    
    # Test actual paste operation (simulated)
    original_count = len(graph.objects)
    print(f"Original object count: {original_count}")
    
    # Simulate paste in negative context (should work in transformation mode)
    paste_success = clipboard.paste_at_position(
        inside_cut, InteractionMode.TRANSFORMATION, cut_items, {}
    )
    
    new_count = len(graph.objects)
    print(f"After paste: {new_count} objects")
    print(f"Paste success: {paste_success}")
    print(f"Objects added: {new_count - original_count}")
    
    print("\n" + "=" * 40)
    print("Copy/Paste Logic Test Complete!")
    
    return {
        'copy_success': copy_success,
        'paste_success': paste_success,
        'objects_added': new_count - original_count,
        'json_export_success': json_export is not None
    }

if __name__ == "__main__":
    results = test_copy_paste_logic()
    print(f"\nTest Results: {results}")

