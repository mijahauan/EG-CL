import unittest
from eg_model import GraphModel, Cut, Predicate
from eg_editor import EGEditor
from clif_translation import ClifTranslator

class TestAdvancedLogic(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.model = self.editor.model

    def test_negated_identity_translation(self):
        """Tests correct variable scoping in a negated context."""
        cut = self.editor.add_cut()
        p1 = self.editor.add_predicate('P', 1, parent_id=cut)
        p2 = self.editor.add_predicate('Q', 1, parent_id='SA')
        self.editor.connect([(p1, 1), (p2, 1)])
        translator = ClifTranslator(self.model)
        expected = "(exists (?v1) (and (Q ?v1) (not (P ?v1))))"
        self.assertEqual(translator.translate(), expected)

    def test_ligature_traversal_path(self):
        """Tests that a ligature correctly identifies the cuts it traverses."""
        c1_id = self.editor.add_cut(parent_id='SA')
        c2_id = self.editor.add_cut(parent_id=c1_id)
        c3_id = self.editor.add_cut(parent_id='SA')
        p1_id = self.editor.add_predicate('P1', 1, parent_id=c2_id)
        p2_id = self.editor.add_predicate('P2', 1, parent_id=c3_id)
        ligature_id = self.editor.connect([(p1_id, 1), (p2_id, 1)])
        ligature = self.model.get_object(ligature_id)
        expected_traversed_cuts = {c1_id, c2_id, c3_id}
        self.assertEqual(ligature.traversed_cuts, expected_traversed_cuts)

    def test_iteration_with_external_ligature(self):
        """Tests iterating a subgraph connected to an external ligature."""
        # P on SA is connected to Q in C1. We iterate Q into C2 (inside C1).
        # The new Q' must also be connected to the ligature from P.
        p_id = self.editor.add_predicate('P', 1, parent_id='SA')
        c1_id = self.editor.add_cut(parent_id='SA')
        q_id = self.editor.add_predicate('Q', 1, parent_id=c1_id)
        c2_id = self.editor.add_cut(parent_id=c1_id)

        # Connect P and Q
        ligature_id = self.editor.connect([(p_id, 1), (q_id, 1)])
        
        # Iterate Q into C2
        self.editor.iterate([q_id], c2_id)

        # Find the new copy of Q
        q_copy_id = None
        c2_children = self.model.get_object(c2_id).children
        for child_id in c2_children:
            child = self.model.get_object(child_id)
            if isinstance(child, Predicate) and child.label == 'Q':
                q_copy_id = child.id
                break
        
        self.assertIsNotNone(q_copy_id, "Copy of Q was not found in the target context.")

        # Check that the new Q is connected to the original ligature
        q_copy = self.model.get_object(q_copy_id)
        self.assertEqual(q_copy.hooks[1], ligature_id)

class TestAdvancedTransformations(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.model = self.editor.model

# The following tests are placeholders for future, more complex rules.
# class TestParserRobustness(unittest.TestCase):
#     def setUp(self):
#         self.parser = ClifParser()
#
#     def test_unclosed_parenthesis(self):
#         with self.assertRaises(ValueError):
#             self.parser.parse("(exists (?x) (P ?x)")