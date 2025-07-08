import unittest
from eg_editor import EGEditor
from clif_translation import ClifTranslator
from eg_model import LineOfIdentity

class TestTranslation(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.translator = ClifTranslator(self.editor)

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
        expected = "(exists (?v1) (and (P ?v1) (Q ?v1)))"
        self.assertEqual(self.translator.translate(), expected)

    def test_negated_identity_translation(self):
        cut = self.editor.add_cut()
        p1 = self.editor.add_predicate('P', 1, parent_id=cut)
        p2 = self.editor.add_predicate('Q', 1, parent_id='SA')
        self.editor.connect([(p1, 1), (p2, 1)])
        expected = "(exists (?v1) (and (Q ?v1) (not (P ?v1))))"
        self.assertEqual(self.translator.translate(), expected)
    
    def test_constant_translation(self):
        self.editor.add_constant('Socrates')
        self.assertEqual(self.translator.translate(), "(exists (?v1) (Socrates ?v1))")

    def test_function_translation(self):
        # Create two lines. Sorting their IDs ensures deterministic variable assignment (?v1, ?v2)
        line1 = LineOfIdentity()
        line2 = LineOfIdentity()
        if line1.id > line2.id: line1, line2 = line2, line1
        
        self.editor.model.add_object(line1)
        self.editor.model.add_object(line2)

        # Create the function and manually connect its hooks
        func_id = self.editor.add_predicate('PlusOne', 2, is_functional=True)
        func_pred = self.editor.model.get_object(func_id)
        # Hook 1 is input (?v1), Hook 2 is output (?v2)
        func_pred.hooks[1] = line1.id
        func_pred.hooks[2] = line2.id
        
        # Create visual ligatures so the lines are "in" the graph
        self.editor.connect([(func_id, 1)])
        self.editor.connect([(func_id, 2)])
        
        expected = "(exists (?v1 ?v2) (= ?v2 (PlusOne ?v1)))"
        self.assertEqual(self.translator.translate(), expected)