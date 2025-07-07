import unittest
from eg_editor import EGEditor
from clif_translation import ClifTranslator
from eg_model import Predicate, Cut

class TestTransformationRules(unittest.TestCase):
    def setUp(self):
        """Set up a fresh editor for each test."""
        self.editor = EGEditor()

    def test_insert_and_remove_double_cut(self):
        """Test wrapping a predicate in a double cut and removing it."""
        p_id = self.editor.add_predicate('P', 1, parent_id='SA')
        
        outer_cut_id, inner_cut_id = self.editor.insert_double_cut(selection_ids=[p_id])
        
        self.assertIn(outer_cut_id, self.editor.model.objects)
        self.assertIn(inner_cut_id, self.editor.model.objects)
        self.assertEqual(self.editor.get_parent_context(inner_cut_id), outer_cut_id)
        self.assertEqual(self.editor.get_parent_context(p_id), inner_cut_id)

        self.editor.remove_double_cut(outer_cut_id)

        self.assertNotIn(outer_cut_id, self.editor.model.objects)
        self.assertNotIn(inner_cut_id, self.editor.model.objects)
        self.assertEqual(self.editor.get_parent_context(p_id), 'SA')

    def test_insert_empty_double_cut(self):
        """Tests inserting a double cut onto an empty area."""
        initial_cuts = len([o for o in self.editor.model.objects.values() if isinstance(o, Cut)])
        self.editor.insert_double_cut() # No selection
        final_cuts = len([o for o in self.editor.model.objects.values() if isinstance(o, Cut)])
        self.assertEqual(final_cuts, initial_cuts + 2)
        
    def test_iteration_validation_and_action(self):
        """Test the iteration rule and its validation."""
        p_id = self.editor.add_predicate('P', 1, parent_id='SA')
        c1_id = self.editor.add_cut(parent_id='SA')
        c2_id = self.editor.add_cut(parent_id=c1_id)

        self.assertTrue(self.editor.validator.can_iterate([p_id], c2_id))
        
        p2_id = self.editor.add_predicate('P2', 1, parent_id=c1_id)
        self.assertFalse(self.editor.validator.can_iterate([p2_id], 'SA'))

        self.editor.iterate([p_id], c2_id)
        
        c2_children_preds = [
            obj for obj in self.editor.model.objects.values() 
            if isinstance(obj, Predicate) and self.editor.get_parent_context(obj.id) == c2_id
        ]
        self.assertEqual(len(c2_children_preds), 1)
        self.assertEqual(c2_children_preds[0].label, 'P')

    def test_clif_translation_for_constant(self):
        """Test that a constant is translated correctly to CLIF."""
        self.editor.add_predicate('Socrates', hooks=0, p_type='constant')
        translator = ClifTranslator(self.editor.model)
        clif_output = translator.translate()
        self.assertEqual(clif_output, "Socrates")
        
    def test_clif_translation_for_function(self):
        """Test that a functional predicate translates to a CLIF equality."""
        editor = EGEditor()
        func_id = editor.add_predicate('PlusOne', hooks=2, is_functional=True)
        translator = ClifTranslator(editor.model)
        clif_output = translator.translate()
        
        self.assertIn("exists", clif_output)
        self.assertIn("=", clif_output)
        self.assertIn("PlusOne", clif_output)

    def test_functional_property_rule(self):
        """Test connecting outputs of two identical function calls."""
        p1_id = self.editor.add_predicate('f', 2, is_functional=True)
        p2_id = self.editor.add_predicate('f', 2, is_functional=True)

        self.editor.connect([(p1_id, 1), (p2_id, 1)])
        
        self.assertTrue(self.editor.validator.can_apply_functional_property_rule(p1_id, p2_id))
        self.editor.apply_functional_property_rule(p1_id, p2_id)
        
        p1 = self.editor.model.get_object(p1_id)
        p2 = self.editor.model.get_object(p2_id)
        self.assertIsNotNone(p1.hooks[2])
        self.assertEqual(p1.hooks[2], p2.hooks[2])