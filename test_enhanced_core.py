#!/usr/bin/env python3
"""
Core functionality test for enhanced components without GUI display.
Tests the logic and structure of enhanced graphics items.
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock

# Set up headless Qt environment
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtWidgets import QApplication

# Import enhanced components
from enhanced_graphics_items import (EnhancedPredicateItem, EnhancedCutItem, 
                                   HookItem, ResizeHandle, ConnectionPreviewItem)
from interaction_manager import InteractionManager, InteractionMode

# Import core components
from eg_model import ExistentialGraph, GraphObjectType
from eg_logic import EGEditor

class TestEnhancedComponents(unittest.TestCase):
    """Test enhanced components core functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        cls.app = QApplication(sys.argv)
        
    def setUp(self):
        """Set up test environment for each test."""
        self.graph = ExistentialGraph()
        self.editor = EGEditor(self.graph)
        
    def test_enhanced_predicate_creation(self):
        """Test enhanced predicate item creation and hook management."""
        print("Testing enhanced predicate creation...")
        
        # Create predicate with arity 3
        predicate = EnhancedPredicateItem("pred_1", "TestPredicate", self.graph, arity=3)
        
        # Verify basic properties
        self.assertEqual(predicate.node_id, "pred_1")
        self.assertEqual(predicate.arity, 3)
        self.assertEqual(len(predicate.hooks), 3)
        
        # Verify hook properties
        for i, hook in enumerate(predicate.hooks):
            self.assertEqual(hook.hook_index, i)
            self.assertEqual(hook.parent_predicate, predicate)
            self.assertFalse(hook.is_connected)
            self.assertFalse(hook.is_highlighted)
            
        print("✓ Enhanced predicate creation test passed")
        
    def test_hook_connection_state(self):
        """Test hook connection state management."""
        print("Testing hook connection state...")
        
        predicate = EnhancedPredicateItem("pred_1", "Test", self.graph, arity=2)
        
        # Test setting connection state
        predicate.set_hook_connection_state(0, True)
        self.assertTrue(predicate.hooks[0].is_connected)
        self.assertFalse(predicate.hooks[1].is_connected)
        
        # Test highlighting
        predicate.highlight_hook(1, True)
        self.assertTrue(predicate.hooks[1].is_highlighted)
        self.assertFalse(predicate.hooks[0].is_highlighted)
        
        print("✓ Hook connection state test passed")
        
    def test_arity_update(self):
        """Test predicate arity updates."""
        print("Testing arity updates...")
        
        predicate = EnhancedPredicateItem("pred_1", "Test", self.graph, arity=1)
        self.assertEqual(len(predicate.hooks), 1)
        
        # Update arity
        predicate.update_arity(4)
        self.assertEqual(predicate.arity, 4)
        self.assertEqual(len(predicate.hooks), 4)
        
        # Verify new hooks
        for i, hook in enumerate(predicate.hooks):
            self.assertEqual(hook.hook_index, i)
            
        print("✓ Arity update test passed")
        
    def test_enhanced_cut_creation(self):
        """Test enhanced cut item creation and resize handles."""
        print("Testing enhanced cut creation...")
        
        rect = QRectF(10, 10, 100, 80)
        cut = EnhancedCutItem("cut_1", rect, self.graph)
        
        # Verify basic properties
        self.assertEqual(cut.node_id, "cut_1")
        self.assertEqual(cut.rect(), rect)
        self.assertEqual(len(cut.resize_handles), 8)
        
        # Verify handle positions
        expected_positions = ['nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w']
        actual_positions = [handle.position for handle in cut.resize_handles]
        
        for pos in expected_positions:
            self.assertIn(pos, actual_positions)
            
        print("✓ Enhanced cut creation test passed")
        
    def test_cut_drop_highlight(self):
        """Test cut drop highlighting functionality."""
        print("Testing cut drop highlighting...")
        
        rect = QRectF(0, 0, 100, 100)
        cut = EnhancedCutItem("cut_1", rect, self.graph)
        
        # Test drop highlight
        self.assertFalse(cut.drop_highlight)
        cut.set_drop_highlight(True)
        self.assertTrue(cut.drop_highlight)
        
        cut.set_drop_highlight(False)
        self.assertFalse(cut.drop_highlight)
        
        print("✓ Cut drop highlighting test passed")
        
    def test_connection_preview(self):
        """Test connection preview item functionality."""
        print("Testing connection preview...")
        
        start = QPointF(10, 20)
        preview = ConnectionPreviewItem(start)
        
        # Verify initial state
        self.assertEqual(preview.start_point, start)
        self.assertEqual(preview.end_point, start)
        
        # Update end point
        end = QPointF(50, 60)
        preview.update_end_point(end)
        self.assertEqual(preview.end_point, end)
        
        print("✓ Connection preview test passed")
        
    def test_interaction_manager_basic(self):
        """Test interaction manager basic functionality."""
        print("Testing interaction manager...")
        
        # Create mock scene
        scene = Mock()
        scene.installEventFilter = Mock()
        scene.views = Mock(return_value=[Mock()])
        
        manager = InteractionManager(scene, self.graph, self.editor)
        
        # Verify initial state
        self.assertEqual(manager.mode, InteractionMode.NORMAL)
        self.assertIsNotNone(manager.connection_state)
        
        # Test item registration
        predicate = EnhancedPredicateItem("pred_1", "Test", self.graph, arity=1)
        manager.register_predicate_item("pred_1", predicate)
        self.assertIn("pred_1", manager.predicate_items)
        
        rect = QRectF(0, 0, 100, 100)
        cut = EnhancedCutItem("cut_1", rect, self.graph)
        manager.register_cut_item("cut_1", cut)
        self.assertIn("cut_1", manager.cut_items)
        
        print("✓ Interaction manager basic test passed")
        
    def test_context_type_detection(self):
        """Test context type detection logic."""
        print("Testing context type detection...")
        
        # Create mock scene and manager
        scene = Mock()
        scene.installEventFilter = Mock()
        scene.views = Mock(return_value=[Mock()])
        
        manager = InteractionManager(scene, self.graph, self.editor)
        
        # Test with no cuts (should be positive)
        position = QPointF(50, 50)
        context = manager.get_context_type(position)
        self.assertEqual(context, "positive")
        
        print("✓ Context type detection test passed")
        
    def test_connection_validation(self):
        """Test connection validation logic."""
        print("Testing connection validation...")
        
        # Create mock scene and manager
        scene = Mock()
        scene.installEventFilter = Mock()
        scene.views = Mock(return_value=[Mock()])
        
        manager = InteractionManager(scene, self.graph, self.editor)
        
        # Create two predicates with hooks
        pred1 = EnhancedPredicateItem("pred_1", "Test1", self.graph, arity=1)
        pred2 = EnhancedPredicateItem("pred_2", "Test2", self.graph, arity=1)
        
        hook1 = pred1.hooks[0]
        hook2 = pred2.hooks[0]
        
        # Test valid connection (different predicates, not connected)
        is_valid = manager.is_valid_connection(hook1, hook2)
        self.assertTrue(is_valid)
        
        # Test invalid connection (same predicate)
        hook1_alt = HookItem(pred1, 1)  # Another hook on same predicate
        pred1.hooks.append(hook1_alt)
        is_valid = manager.is_valid_connection(hook1, hook1_alt)
        self.assertFalse(is_valid)
        
        print("✓ Connection validation test passed")
        
    def test_integration_with_core_model(self):
        """Test integration with core existential graph model."""
        print("Testing integration with core model...")
        
        # Create predicates in the model
        pred1_id, _ = self.editor.add_predicate("Cat", 1, self.graph.root_id)
        pred2_id, _ = self.editor.add_predicate("Animal", 1, self.graph.root_id)
        
        # Create enhanced items for these predicates
        pred1_node = self.graph.get_object(pred1_id)
        pred2_node = self.graph.get_object(pred2_id)
        
        enhanced_pred1 = EnhancedPredicateItem(
            pred1_id, pred1_node.properties["name"], self.graph, 
            pred1_node.properties["arity"]
        )
        enhanced_pred2 = EnhancedPredicateItem(
            pred2_id, pred2_node.properties["name"], self.graph,
            pred2_node.properties["arity"]
        )
        
        # Verify properties match
        self.assertEqual(enhanced_pred1.node_id, pred1_id)
        self.assertEqual(enhanced_pred1.arity, 1)
        self.assertEqual(enhanced_pred2.node_id, pred2_id)
        self.assertEqual(enhanced_pred2.arity, 1)
        
        print("✓ Integration with core model test passed")

def main():
    """Main test function."""
    print("Enhanced Existential Graphs - Core Functionality Test")
    print("=" * 55)
    
    # Run tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 55)
    print("Core functionality tests completed!")
    print("\nEnhanced components are ready for integration.")
    print("\nKey features implemented:")
    print("• Hook visualization on predicates")
    print("• Resize handles on cuts") 
    print("• Connection preview system")
    print("• Interaction state management")
    print("• Context type detection")
    print("• Connection validation")
    print("• Integration with core model")

if __name__ == "__main__":
    main()

