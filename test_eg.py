import unittest
from eg_model import GraphModel
from eg_editor import EGEditor
from clif_translation import ClifTranslator

class TestEGModel(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.model = self.editor.model
        self.soa = self.model.sheet_of_assertion

    def test_context_nesting(self):
        c1 = self.editor.add_cut(self.soa.id)
        c2 = self.editor.add_cut(c1)
        self.assertEqual(self.editor.get_parent_context(c2), c1)
        self.assertEqual(self.editor.get_parent_context(c1), self.soa.id)

    def test_ligature_creation_and_merge(self):
        p1 = self.editor.add_predicate('P', 1)
        p2 = self.editor.add_predicate('Q', 1)
        lig1 = self.editor.connect([(p1, 1)])
        lig2 = self.editor.connect([(p2, 1)])
        self.assertNotEqual(lig1, lig2)
        
        # Merge by connecting both to a new ligature
        merged_lig = self.editor.connect([(p1, 1), (p2, 1)])
        pred1_obj = self.model.get_object(p1)
        pred2_obj = self.model.get_object(p2)
        self.assertEqual(pred1_obj.hooks[1], merged_lig)
        self.assertEqual(pred2_obj.hooks[1], merged_lig)

class TestTransformations(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()

    def test_can_insert_and_erase(self):
        c1 = self.editor.add_cut()
        # Even context (SA) is positive, can erase
        self.assertTrue(self.editor.validator.is_positive_context('SA'))
        # Odd context (c1) is negative, can insert
        self.assertTrue(self.editor.validator.is_negative_context(c1))
        
    def test_add_double_cut_around_subgraph(self):
        p1 = self.editor.add_predicate('P', 1)
        self.editor.insert_double_cut([p1])
        self.assertNotEqual(self.editor.get_parent_context(p1), 'SA')
        outer_cut_id = self.editor.get_parent_context(self.editor.get_parent_context(p1))
        self.assertTrue(self.editor.validator.can_remove_double_cut(outer_cut_id))

class TestClifTranslator(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.translator = ClifTranslator(self.editor.model)

    def test_empty_graph(self):
        self.assertEqual(self.translator.translate(), "")

    def test_simple_negation(self):
        cut_id = self.editor.add_cut()
        self.editor.add_predicate('P', 0, parent_id=cut_id)
        self.assertEqual(self.translator.translate(), "(not P)")

    def test_quantified_conjunction(self):
        p_id = self.editor.add_predicate('P', 1)
        q_id = self.editor.add_predicate('Q', 1)
        self.editor.connect([(p_id, 1), (q_id, 1)])
        # Variable names are deterministic now
        expected = "(exists (?v1) (and (P ?v1) (Q ?v1)))"
        self.assertEqual(self.translator.translate(), expected)