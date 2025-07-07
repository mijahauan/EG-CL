import unittest
from eg_editor import EGEditor
from clif_translation import ClifTranslator

class TestTranslation(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.translator = ClifTranslator(self.editor)

    def test_empty_graph(self):
        """Confirms an empty graph translates to an empty string."""
        self.assertEqual(self.translator.translate(), "")

    def test_simple_negation(self):
        """Confirms a simple negation (P) translates correctly."""
        cut_id = self.editor.add_cut()
        self.editor.add_predicate('P', 0, parent_id=cut_id)
        self.assertEqual(self.translator.translate(), "(not P)")

    def test_quantified_conjunction(self):
        """Confirms a simple quantified conjunction translates with deterministic variables."""
        p_id = self.editor.add_predicate('P', 1)
        q_id = self.editor.add_predicate('Q', 1)
        self.editor.connect([(p_id, 1), (q_id, 1)])
        expected = "(exists (?v1) (and (P ?v1) (Q ?v1)))"
        self.assertEqual(self.translator.translate(), expected)

    def test_negated_identity_translation(self):
        """Tests correct variable scoping in a negated context."""
        cut = self.editor.add_cut()
        p1 = self.editor.add_predicate('P', 1, parent_id=cut)
        p2 = self.editor.add_predicate('Q', 1, parent_id='SA')
        self.editor.connect([(p1, 1), (p2, 1)])
        expected = "(exists (?v1) (and (Q ?v1) (not (P ?v1))))"
        self.assertEqual(self.translator.translate(), expected)
    
    def test_constant_translation(self):
        """Tests that a constant is translated as a quantified unary relation."""
        self.editor.add_constant('Socrates')
        self.assertEqual(self.translator.translate(), "(exists (?v1) (Socrates ?v1))")

    def test_function_translation(self):
        """Tests that a function is translated into a CLIF functional term with equality."""
        # Create a line to be the input to the function
        input_lig_id = self.editor.add_ligature()
        input_line_id = self.editor.model.get_object(input_lig_id).line_of_identity_id
        
        # Apply the total function rule to create the function call
        self.editor.apply_total_function_rule('PlusOne', 2, [input_line_id])
        
        expected = "(exists (?v1 ?v2) (= ?v2 (PlusOne ?v1)))"
        self.assertEqual(self.translator.translate(), expected)