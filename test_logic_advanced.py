# test_logic_advanced.py
import unittest
from eg_model import *
from eg_logic import *

class TestAdvancedLogic(unittest.TestCase):
    """
    Tests the more complex logical features, especially those related to
    ligature interpretation and derived transformation rules.
    """
    def setUp(self):
        self.eg = ExistentialGraph()
        self.editor = EGEditor(self.eg)
        self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Advanced Logic Test: {self._testMethodName} -----")

    def test_negated_identity_translation(self):
        """
        Tests the translation of a graph with negated identity, which creates
        a non-single-object ligature.
        Graph: (exists (x y) (and (sun x) (sun y) (not (= x y))))
        "There are at least two suns."
        """
        # Arrange: Build the graph structure
        p_sun1 = self.editor.add_predicate("sun", 1, self.soa)
        p_sun2 = self.editor.add_predicate("sun", 1, self.soa)
        neg_cut = self.editor.add_cut(self.soa)
        p_eq = self.editor.add_predicate("=", 2, neg_cut)

        # Act: Connect the predicates
        self.editor.connect(p_sun1.hooks[0], p_eq.hooks[0])
        self.editor.connect(p_sun2.hooks[0], p_eq.hooks[1])
        
        # Assert
        translator = ClifTranslator(self.eg)
        actual = translator.translate()
        # The variable names (x1, x2) are deterministic based on ligature analysis
        expected = "(exists (x1 x2) (and (sun x1) (sun x2) (not (= x1 x2))))"
        
        print(f"  - Testing negated identity.\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected)
        print("  - OK")

    def test_move_ligature_branch_preserves_logic(self):
        """
        Tests that moving a branch along a ligature results in a logically
        equivalent graph.
        """
        # Arrange: Create a graph: P(x), Q(x), R(x)
        p_P = self.editor.add_predicate("P", 1, self.soa)
        p_Q = self.editor.add_predicate("Q", 1, self.soa)
        p_R = self.editor.add_predicate("R", 1, self.soa)
        
        # Connect them all to the same ligature
        self.editor.connect(p_P.hooks[0], p_Q.hooks[0])
        self.editor.connect(p_Q.hooks[0], p_R.hooks[0])

        # Translate the original graph
        translator1 = ClifTranslator(self.eg)
        clif1 = translator1.translate()
        print(f"  - CLIF before moving branch: {clif1}")
        
        # Act: Move the branch of R from Q to P
        self.editor.move_ligature_branch(p_R.hooks[0], p_P.hooks[0])

        # Assert: The new graph should be logically equivalent
        translator2 = ClifTranslator(self.eg)
        clif2 = translator2.translate()
        print(f"  - CLIF after moving branch:  {clif2}")
        
        # The specific variable names might change, but the structure should be the same
        self.assertEqual(clif1, clif2)
        print("  - OK: Moving branch preserved logical structure.")

    def test_round_trip_with_function(self):
        """Tests a full round-trip for a graph containing a function."""
        # Arrange: Build the graph for `y = add(x, 7)`
        clif_string1 = "(exists (x1 x2) (= x2 (add x1 7)))"
        print(f"  - Original CLIF: {clif_string1}")
        
        # Act 1: Parse the CLIF string into an EG model
        parser = ClifParser()
        new_eg = parser.parse(clif_string1)
        
        # Act 2: Translate the new model back to CLIF
        translator = ClifTranslator(new_eg)
        clif_string2 = translator.translate()
        print(f"  - Round-trip CLIF: {clif_string2}")

        # Assert: The two strings must be identical
        self.assertEqual(clif_string1, clif_string2)
        print("  - OK")

    def test_round_trip_negated_identity(self):
        """Tests a full round-trip for a graph with non-single-object ligature."""
        clif_string1 = "(exists (x1 x2) (and (sun x1) (sun x2) (not (= x1 x2))))"
        print(f"  - Original CLIF: {clif_string1}")
        
        parser = ClifParser()
        new_eg = parser.parse(clif_string1)
        
        translator = ClifTranslator(new_eg)
        clif_string2 = translator.translate()
        print(f"  - Round-trip CLIF: {clif_string2}")

        self.assertEqual(clif_string1, clif_string2)
        print("  - OK")


if __name__ == '__main__':
    unittest.main()

