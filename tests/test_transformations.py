import unittest
from eg_editor import EGEditor
from eg_model import Predicate, Cut, LineOfIdentity

class TestTransformations(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.model = self.editor.model

    def test_can_insert_and_erase(self):
        c1 = self.editor.add_cut()
        self.assertTrue(self.editor.validator.is_positive_context('SA'))
        self.assertTrue(self.editor.validator.is_negative_context(c1))

    def test_insert_and_remove_double_cut(self):
        p_id = self.editor.add_predicate('P', 1, parent_id='SA')
        outer_cut_id, inner_cut_id = self.editor.insert_double_cut(selection_ids=[p_id])
        self.assertEqual(self.editor.get_parent_context(p_id), inner_cut_id)
        self.editor.remove_double_cut(outer_cut_id)
        self.assertEqual(self.editor.get_parent_context(p_id), 'SA')

    def test_insert_empty_double_cut(self):
        initial_cuts = len([o for o in self.model.objects.values() if isinstance(o, Cut)])
        self.editor.insert_double_cut()
        final_cuts = len([o for o in self.model.objects.values() if isinstance(o, Cut)])
        self.assertEqual(final_cuts, initial_cuts + 2)

    def test_iteration_validation_and_action(self):
        p_id = self.editor.add_predicate('P', 1, parent_id='SA')
        c1_id = self.editor.add_cut(parent_id='SA')
        c2_id = self.editor.add_cut(parent_id=c1_id)
        self.assertTrue(self.editor.validator.can_iterate([p_id], c2_id))
        self.editor.iterate([p_id], c2_id)
        c2_children_preds = [
            obj for obj in self.model.objects.values()
            if isinstance(obj, Predicate) and self.editor.get_parent_context(obj.id) == c2_id
        ]
        self.assertEqual(len(c2_children_preds), 1)

    def test_iteration_with_external_ligature(self):
        p_id = self.editor.add_predicate('P', 1, parent_id='SA')
        c1_id = self.editor.add_cut(parent_id='SA')
        q_id = self.editor.add_predicate('Q', 1, parent_id=c1_id)
        c2_id = self.editor.add_cut(parent_id=c1_id)
        self.editor.connect([(p_id, 1), (q_id, 1)])
        original_line_id = self.model.get_object(q_id).hooks[1]
        self.editor.iterate([q_id], c2_id)
        q_copy_id = next(
            child.id for child in (self.model.get_object(obj_id) for obj_id in self.model.get_object(c2_id).children)
            if isinstance(child, Predicate) and child.label == 'Q'
        )
        self.assertIsNotNone(q_copy_id)
        q_copy = self.model.get_object(q_copy_id)
        self.assertEqual(q_copy.hooks[1], original_line_id)
        
    def test_iteration_of_nested_subgraph(self):
        """Tests iterating a subgraph that itself contains a cut."""
        c1_id = self.editor.add_cut('SA')
        p_id = self.editor.add_predicate('P', 0, parent_id=c1_id)
        
        c2_id = self.editor.add_cut('SA')
        
        # Iterate the cut C1 (containing P) into C2
        self.editor.iterate([c1_id], c2_id)
        
        # Verify the structure
        c2_children = self.model.get_object(c2_id).children
        self.assertEqual(len(c2_children), 1)
        c1_copy_id = list(c2_children)[0]
        c1_copy = self.model.get_object(c1_copy_id)
        self.assertIsInstance(c1_copy, Cut)
        
        c1_copy_children = c1_copy.children
        self.assertEqual(len(c1_copy_children), 1)
        p_copy_id = list(c1_copy_children)[0]
        p_copy = self.model.get_object(p_copy_id)
        self.assertIsInstance(p_copy, Predicate)
        self.assertEqual(p_copy.label, 'P')

    def test_existence_of_constants_rule(self):
        initial_preds = len([o for o in self.model.objects.values() if isinstance(o, Predicate)])
        const_id = self.editor.add_constant('Socrates')
        self.assertEqual(len([o for o in self.model.objects.values() if isinstance(o, Predicate)]), initial_preds + 1)
        self.editor.erase_constant(const_id)
        self.assertEqual(len([o for o in self.model.objects.values() if isinstance(o, Predicate)]), initial_preds)

    def test_illegal_erase_of_connected_constant(self):
        const_id = self.editor.add_constant('Socrates')
        p_id = self.editor.add_predicate('P', 1)
        self.editor.connect([(const_id, 1), (p_id, 1)])
        with self.assertRaises(ValueError):
            self.editor.erase_constant(const_id)

    def test_total_function_rule(self):
        input_lig_id = self.editor.add_ligature()
        input_line_id = self.model.get_object(input_lig_id).line_of_identity_id
        func_id = self.editor.apply_total_function_rule('PlusOne', 2, [input_line_id])
        func_pred = self.model.get_object(func_id)
        self.assertEqual(func_pred.hooks[1], input_line_id)
        self.assertIsNotNone(func_pred.hooks[2])
        self.assertNotEqual(func_pred.hooks[1], func_pred.hooks[2])