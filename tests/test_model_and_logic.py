import unittest
from eg_editor import EGEditor
from eg_model import LineOfIdentity

class TestModelAndLogic(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.model = self.editor.model

    def test_context_nesting(self):
        """Verifies that the Context tree and nesting levels are calculated correctly."""
        c1 = self.editor.add_cut()
        c2 = self.editor.add_cut(c1)
        self.assertEqual(self.editor.get_parent_context(c2), c1)

    def test_ligature_creation_and_merge(self):
        """Tests the core logic of creating and merging Lines of Identity."""
        p1 = self.editor.add_predicate('P', 1)
        p2 = self.editor.add_predicate('Q', 1)
        self.editor.connect([(p1, 1)])
        self.editor.connect([(p2, 1)])
        p1_line = self.model.get_object(p1).hooks[1]
        p2_line = self.model.get_object(p2).hooks[1]
        self.assertNotEqual(p1_line, p2_line)
        self.editor.connect([(p1, 1), (p2, 1)])
        self.assertEqual(self.model.get_object(p1).hooks[1], self.model.get_object(p2).hooks[1])

    def test_single_line_creation(self):
        """Tests that connecting two hooks creates a single Line of Identity."""
        p1_id = self.editor.add_predicate('P', 1)
        p2_id = self.editor.add_predicate('Q', 1)
        ligature_id = self.editor.connect([(p1_id, 1), (p2_id, 1)])
        p1 = self.model.get_object(p1_id)
        p2 = self.model.get_object(p2_id)
        ligature = self.model.get_object(ligature_id)
        self.assertIsNotNone(p1.hooks[1])
        self.assertEqual(p1.hooks[1], p2.hooks[1])
        self.assertEqual(ligature.line_of_identity_id, p1.hooks[1])
        line_of_identity = self.model.get_object(p1.hooks[1])
        self.assertIn(ligature_id, line_of_identity.ligatures)

    def test_line_merging(self):
        """Tests that connecting two existing Lines of Identity correctly merges them."""
        p1_id = self.editor.add_predicate('P', 1)
        q1_id = self.editor.add_predicate('Q', 1)
        lig1_id = self.editor.connect([(p1_id, 1), (q1_id, 1)])
        line1_id = self.model.get_object(p1_id).hooks[1]
        r1_id = self.editor.add_predicate('R', 1)
        s1_id = self.editor.add_predicate('S', 1)
        lig2_id = self.editor.connect([(r1_id, 1), (s1_id, 1)])
        line2_id = self.model.get_object(r1_id).hooks[1]
        self.assertNotEqual(line1_id, line2_id)
        merge_lig_id = self.editor.connect([(q1_id, 1), (r1_id, 1)])
        final_line_id = self.model.get_object(p1_id).hooks[1]
        self.assertEqual(final_line_id, self.model.get_object(q1_id).hooks[1])
        self.assertEqual(final_line_id, self.model.get_object(r1_id).hooks[1])
        self.assertEqual(final_line_id, self.model.get_object(s1_id).hooks[1])
        self.assertIsNone(self.model.get_object(line2_id))
        final_line = self.model.get_object(final_line_id)
        self.assertIn(lig1_id, final_line.ligatures)
        self.assertIn(lig2_id, final_line.ligatures)
        self.assertIn(merge_lig_id, final_line.ligatures)
        
    def test_three_way_line_merging(self):
        """Tests that connecting three separate lines results in one line."""
        p_id = self.editor.add_predicate('P', 1)
        q_id = self.editor.add_predicate('Q', 1)
        r_id = self.editor.add_predicate('R', 1)
        self.editor.connect([(p_id, 1)])
        self.editor.connect([(q_id, 1)])
        self.editor.connect([(r_id, 1)])
        self.editor.connect([(p_id, 1), (q_id, 1), (r_id, 1)])
        final_line_id = self.model.get_object(p_id).hooks[1]
        self.assertEqual(final_line_id, self.model.get_object(q_id).hooks[1])
        self.assertEqual(final_line_id, self.model.get_object(r_id).hooks[1])