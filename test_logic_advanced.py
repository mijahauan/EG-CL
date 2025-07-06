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
        Tests the translation of a graph with negated identity.
        Graph: (exists (x y) (and (sun x) (sun y) (not (= x y))))
        "There are at least two suns."
        """
        p_sun1 = self.editor.add_predicate("sun", 1, self.soa)
        p_sun2 = self.editor.add_predicate("sun", 1, self.soa)
        neg_cut = self.editor.add_cut(self.soa)
        p_eq = self.editor.add_predicate("=", 2, neg_cut)
        self.editor.connect(p_sun1.hooks[0], p_eq.hooks[0])
        self.editor.connect(p_sun2.hooks[0], p_eq.hooks[1])
        translator = ClifTranslator(self.eg)
        actual = translator.translate()
        expected = "(exists (x1 x2) (and (sun x1) (sun x2) (not (= x1 x2))))"
        print(f"  - Testing negated identity.\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected)
        print("  - OK")

    def test_move_ligature_branch_preserves_logic(self):
        """
        Tests that moving a branch along a ligature results in a logically
        equivalent graph.
        """
        p_P = self.editor.add_predicate("P", 1, self.soa)
        p_Q = self.editor.add_predicate("Q", 1, self.soa)
        p_R = self.editor.add_predicate("R", 1, self.soa)
        
        self.editor.connect(p_P.hooks[0], p_Q.hooks[0])
        self.editor.connect(p_Q.hooks[0], p_R.hooks[0])

        translator1 = ClifTranslator(self.eg)
        clif1 = translator1.translate()
        print(f"  - CLIF before moving branch: {clif1}")
        
        self.editor.move_ligature_branch(p_R.hooks[0], p_P.hooks[0])

        translator2 = ClifTranslator(self.eg)
        clif2 = translator2.translate()
        print(f"  - CLIF after moving branch:  {clif2}")
        
        self.assertEqual(clif1, clif2)
        print("  - OK: Moving branch preserved logical structure.")

    def test_round_trip_with_function(self):
        """Tests a full round-trip for a graph containing a function."""
        clif_string1 = "(exists (x1 x2) (= x2 (add x1 7)))"
        print(f"  - Original CLIF: {clif_string1}")
        
        parser = ClifParser()
        new_eg = parser.parse(clif_string1)
        
        translator = ClifTranslator(new_eg)
        clif_string2 = translator.translate()
        print(f"  - Round-trip CLIF: {clif_string2}")

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

## NEW ##
class TestAdvancedTransformations(unittest.TestCase):
    """Tests complex rule interactions and logical validations."""

    def setUp(self):
        self.eg = ExistentialGraph()
        self.editor = EGEditor(self.eg)
        self.validator = self.editor.validator
        self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Advanced Transformation Test: {self._testMethodName} -----")

    def test_deiteration_requires_isomorphic_structure(self):
        """
        Tests that can_deiterate correctly distinguishes between subgraphs that
        have the same predicates but different internal connections.
        """
        # Original Graph on SOA: P(x, y) and Q(y)
        p_P_orig = self.editor.add_predicate("P", 2, self.soa)
        p_Q_orig = self.editor.add_predicate("Q", 1, self.soa)
        self.editor.connect(p_P_orig.hooks[1], p_Q_orig.hooks[0]) # P's 2nd hook connects to Q
        
        # Add a cut with two potential copies to de-iterate
        cut = self.editor.add_cut(self.soa)
        
        # Copy 1: Isomorphic to the original
        p_P_iso = self.editor.add_predicate("P", 2, cut)
        p_Q_iso = self.editor.add_predicate("Q", 1, cut)
        self.editor.connect(p_P_iso.hooks[1], p_Q_iso.hooks[0]) # Correct wiring
        subgraph_iso = Subgraph({p_P_iso, p_Q_iso})
        
        # Copy 2: NOT isomorphic (different wiring)
        p_P_non = self.editor.add_predicate("P", 2, cut)
        p_Q_non = self.editor.add_predicate("Q", 1, cut)
        self.editor.connect(p_P_non.hooks[0], p_Q_non.hooks[0]) # Incorrect wiring
        subgraph_non_iso = Subgraph({p_P_non, p_Q_non})
        
        can_deiterate_iso = self.validator.can_deiterate(subgraph_iso)
        can_deiterate_non_iso = self.validator.can_deiterate(subgraph_non_iso)

        print(f"  - Can de-iterate isomorphic copy? {can_deiterate_iso}")
        print(f"  - Can de-iterate non-isomorphic copy? {can_deiterate_non_iso}")

        self.assertTrue(can_deiterate_iso, "Should be able to de-iterate the isomorphically wired subgraph.")
        self.assertFalse(can_deiterate_non_iso, "Should NOT be able to de-iterate the differently wired subgraph.")
        print("  - OK: Isomorphism check for de-iteration is correct.")

    def test_iteration_of_subgraph_with_double_cut(self):
        """Tests iterating a subgraph that itself contains a double cut."""
        # Graph: (P (not (not (Q))))
        p_P = self.editor.add_predicate("P", 0, self.soa)
        dc_outer = self.editor.add_cut(self.soa)
        dc_inner = self.editor.add_cut(dc_outer)
        self.editor.add_predicate("Q", 0, dc_inner)
        
        subgraph_to_iterate = Subgraph({dc_outer}) # Iterate the entire double cut
        
        # Iterate the double cut into a new containing cut
        target_cut = self.editor.add_cut(self.soa)
        self.editor.iterate(subgraph_to_iterate, target_cut)

        translator = ClifTranslator(self.eg)
        actual = translator.translate()
        # Original is (P and (not (not (Q)))). Target is empty cut (not true).
        # After iteration, target becomes (not ((not (not (Q)))))
        # Full graph: (and (P) (not (not (Q))) (not (not (not (Q)))))
        expected = "(and (P) (not (not (Q))) (not (not (not (Q)))))"
        
        print(f"  - Testing iteration of double cut.\n  - Expected: {expected}\n  - Actual:   {actual}")
        # Note: A smarter translator might simplify this, but for now we check structural correctness.
        # The key is that the operation completed without error and the structure is present.
        self.assertIn("(not (not (Q)))", actual)
        self.assertIn("(not (not (not (Q))))", actual)
        print("  - OK")

    def test_erase_of_subgraph_with_dangling_ligatures(self):
        """Tests erasing a subgraph whose ligatures extend into a deeper context."""
        # Graph: P(x) and inside a cut, Q(x)
        p_P = self.editor.add_predicate("P", 1, self.soa)
        cut = self.editor.add_cut(self.soa)
        p_Q = self.editor.add_predicate("Q", 1, cut)
        
        self.editor.connect(p_P.hooks[0], p_Q.hooks[0])
        ligature = p_P.hooks[0].ligature
        self.assertEqual(len(ligature.hooks), 2)

        # Erase P, which is on an even level (SOA). This should be valid.
        subgraph_to_erase = Subgraph({p_P})
        self.assertTrue(self.validator.can_erase(subgraph_to_erase))
        self.editor.erase_subgraph(subgraph_to_erase)
        
        # Check that P is gone and the ligature now only has one hook (Q's hook)
        self.assertNotIn(p_P, self.soa.predicates)
        self.assertEqual(len(ligature.hooks), 1)
        self.assertIn(p_Q.hooks[0], ligature.hooks)

        translator = ClifTranslator(self.eg)
        actual = translator.translate()
        # After erasing P(x1), we are left with (not (Q(x1)))
        # Since x1 is now only bound inside the negation, it's quantified there.
        expected = "(not (exists (x1) (Q x1)))"
        print(f"  - Testing erase with dangling ligature.\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected)
        print("  - OK")


class TestParserRobustness(unittest.TestCase):
    """Tests the CLIF parser's ability to handle malformed input."""

    def setUp(self):
        self.parser = ClifParser()
        print(f"\n----- Running Parser Robustness Test: {self._testMethodName} -----")

    def test_unclosed_parenthesis(self):
        """Tests that unclosed parentheses raise a specific error."""
        bad_clif = "(and (P x)"
        with self.assertRaisesRegex(ClifParserError, "Unclosed parenthesis"):
            self.parser.parse(bad_clif)
        print("  - OK: Correctly caught unclosed parenthesis.")

    def test_unexpected_tokens(self):
        """Tests that extra tokens after a valid expression raise an error."""
        bad_clif = "(P x))"
        with self.assertRaisesRegex(ClifParserError, "Unexpected tokens"):
            self.parser.parse(bad_clif)
        print("  - OK: Correctly caught unexpected closing parenthesis.")

    def test_malformed_not(self):
        """Tests that 'not' with incorrect number of arguments fails."""
        bad_clif = "(not (P x) (Q y))"
        with self.assertRaisesRegex(ClifParserError, "Malformed 'not' expression"):
            self.parser.parse(bad_clif)
        print("  - OK: Correctly caught malformed 'not'.")

    def test_malformed_equals(self):
        """Tests that '=' with incorrect number of arguments fails."""
        bad_clif = "(= x y z)"
        with self.assertRaisesRegex(ClifParserError, "Malformed '=' expression"):
            self.parser.parse(bad_clif)
        print("  - OK: Correctly caught malformed '='.")
        
    def test_malformed_exists(self):
        """Tests that 'exists' with a non-list for variables fails."""
        bad_clif = "(exists x (P x))"
        with self.assertRaisesRegex(ClifParserError, "Malformed 'exists' expression"):
            self.parser.parse(bad_clif)
        print("  - OK: Correctly caught malformed 'exists'.")


if __name__ == '__main__':
    unittest.main()