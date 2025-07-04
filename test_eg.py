# test_eg.py
import unittest
import re
from eg_model import *
from eg_logic import *

class TestEGModel(unittest.TestCase):
    """Tests the foundational data structures in eg_model.py."""

    def setUp(self):
        self.eg = ExistentialGraph()
        self.editor = EGEditor(self.eg)
        self.soa = self.eg.sheet_of_assertion
        print("\n" + ("-" * 20))
        print(f"Running: {self._testMethodName}")

    def test_context_nesting(self):
        """Verifies that the Context tree and nesting levels are calculated correctly."""
        self.assertEqual(self.soa.get_nesting_level(), 0)
        cut1 = self.editor.add_cut(self.soa)
        self.assertEqual(cut1.get_nesting_level(), 1)
        cut2 = self.editor.add_cut(cut1)
        self.assertEqual(cut2.get_nesting_level(), 2)
        print("OK: Context nesting levels are correct.")

    def test_ligature_creation_and_merge(self):
        """Tests the core logic of creating and merging Ligatures via the editor."""
        p1 = self.editor.add_predicate("p", 2, self.soa)
        p2 = self.editor.add_predicate("q", 1, self.soa)
        self.editor.connect(p1.hooks[0], p1.hooks[1])
        self.assertIsNotNone(p1.hooks[0].ligature)
        self.assertIs(p1.hooks[0].ligature, p1.hooks[1].ligature)
        self.editor.connect(p1.hooks[0], p2.hooks[0])
        self.assertIs(p2.hooks[0].ligature, p1.hooks[0].ligature)
        self.assertEqual(len(p2.hooks[0].ligature.hooks), 3)
        print("OK: Ligatures created and merged correctly.")

    def test_ligature_starting_context(self):
        """Tests that a ligature spanning a parent and child context has the correct scope."""
        cut1 = self.editor.add_cut(self.soa)
        p_outer = self.editor.add_predicate("P", 1, self.soa)
        p_inner = self.editor.add_predicate("Q", 1, cut1)
        self.editor.connect(p_outer.hooks[0], p_inner.hooks[0])
        ligature = p_outer.hooks[0].ligature
        self.assertIs(ligature.get_starting_context(), self.soa)
        print("OK: Ligature starting context is correctly identified as the outermost.")

    def test_ligature_starting_context_lca(self):
        """Tests the Least Common Ancestor (LCA) logic for a ligature spanning sibling cuts."""
        outer_cut = self.editor.add_cut(self.soa)
        cat_cut = self.editor.add_cut(outer_cut)
        animal_cut = self.editor.add_cut(outer_cut)
        p_cat = self.editor.add_predicate("cat", 1, cat_cut)
        p_animal = self.editor.add_predicate("animal", 1, animal_cut)
        lig = Ligature()
        p_cat.hooks[0].ligature = lig
        p_animal.hooks[0].ligature = lig
        lig.hooks.add(p_cat.hooks[0])
        lig.hooks.add(p_animal.hooks[0])
        self.assertIs(lig.get_starting_context(), outer_cut)
        print("OK: Ligature scope for sibling cuts is the correct LCA.")

class TestTransformations(unittest.TestCase):
    """Tests the Validator and the Editor's transformation methods."""

    def setUp(self):
        self.eg = ExistentialGraph()
        self.editor = EGEditor(self.eg)
        self.validator = Validator(self.eg)
        self.soa = self.eg.sheet_of_assertion
        print("\n" + ("-" * 20))
        print(f"Running: {self._testMethodName}")

    def test_can_insert_and_erase(self):
        """Validates the Insertion (odd contexts) and Erasure (even contexts) rules."""
        soa = self.soa
        cut1 = self.editor.add_cut(soa)
        cut2 = self.editor.add_cut(cut1)
        p_on_soa = self.editor.add_predicate("P", 0, soa)
        p_in_cut1 = self.editor.add_predicate("Q", 0, cut1)
        p_in_cut2 = self.editor.add_predicate("R", 0, cut2)
        self.assertFalse(self.validator.can_insert(soa))
        self.assertTrue(self.validator.can_insert(cut1))
        self.assertFalse(self.validator.can_insert(cut2))
        self.assertTrue(self.validator.can_erase(p_on_soa))
        self.assertFalse(self.validator.can_erase(p_in_cut1))
        self.assertTrue(self.validator.can_erase(p_in_cut2))
        print("OK: Insertion/Erasure rules correctly validated.")

    def test_can_remove_double_cut(self):
        """Validates the basic check for the Double Cut rule."""
        dc_outer = self.editor.add_cut(self.soa)
        self.editor.add_cut(dc_outer)
        self.assertTrue(self.validator.can_remove_double_cut(dc_outer))
        dc_outer_2 = self.editor.add_cut(self.soa)
        self.editor.add_cut(dc_outer_2)
        self.editor.add_predicate("P", 0, dc_outer_2)
        self.assertFalse(self.validator.can_remove_double_cut(dc_outer_2))
        print("OK: Double cut validation is correct.")
        
    def test_iteration_validation(self):
        """Validates the logic for where a subgraph is permitted to be iterated."""
        cut1 = self.editor.add_cut(self.soa)
        p = self.editor.add_predicate("P", 0, cut1)
        cut2 = self.editor.add_cut(cut1)
        subgraph = Subgraph({p})
        self.assertTrue(self.validator.can_iterate(subgraph, cut2))
        self.assertFalse(self.validator.can_iterate(subgraph, self.soa))
        print("OK: Iteration validation is correct.")

    def test_iteration_transformation(self):
        """Tests the actual transformation of iterating a simple proposition."""
        cut1 = self.editor.add_cut(self.soa)
        p_original = self.editor.add_predicate("P", 0, cut1)
        cut2 = self.editor.add_cut(cut1)
        subgraph_to_iterate = Subgraph({p_original})
        
        self.editor.iterate(subgraph_to_iterate, cut2)
        
        self.assertEqual(len(cut2.predicates), 1)
        self.assertEqual(cut2.predicates[0].name, "P")
        
        translator = ClifTranslator(self.eg)
        expected_clif = "(not (and (P) (not (P))))"
        self.assertEqual(translator.translate(), expected_clif)
        print("OK: Iteration of a simple proposition works.")

    def test_iteration_with_external_ligature(self):
        """Tests iterating a subgraph that is connected to the outer graph."""
        p_r = self.editor.add_predicate("R", 1, self.soa)
        cut = self.editor.add_cut(self.soa)
        p_p_original = self.editor.add_predicate("P", 1, cut)
        
        self.editor.connect(p_r.hooks[0], p_p_original.hooks[0])
        original_ligature = p_r.hooks[0].ligature
        
        subgraph_to_iterate = Subgraph({p_p_original, original_ligature})

        self.editor.iterate(subgraph_to_iterate, cut)
        
        self.assertEqual(len(cut.predicates), 2)
        p_copy = cut.predicates[1]
        self.assertEqual(p_copy.name, "P")
        self.assertEqual(len(original_ligature.hooks), 3)

        translator = ClifTranslator(self.eg)
        expected = "(exists (x1) (and (R x1) (not (and (P x1) (P x1)))))"
        self.assertEqual(translator.translate(), expected)
        print("OK: Iteration with external ligature works.")
        
    def test_deiteration(self):
        """Tests the full de-iteration workflow: validation, transformation, and final state."""
        cut1 = self.editor.add_cut(self.soa)
        p_original = self.editor.add_predicate("P", 0, cut1)
        cut2 = self.editor.add_cut(cut1)
        p_copy = self.editor.add_predicate("P", 0, cut2)
        
        self.assertTrue(self.validator.can_deiterate(Subgraph({p_copy})))
        self.assertFalse(self.validator.can_deiterate(Subgraph({p_original})))

        self.editor.deiterate(Subgraph({p_copy}))
        
        translator = ClifTranslator(self.eg)
        expected = "(not (and (P) (not true)))"
        self.assertEqual(translator.translate(), expected)
        print("OK: De-iteration validation and transformation are correct.")

class TestClifTranslator(unittest.TestCase):
    """Tests the end-to-end translation of various specific graph structures."""

    def setUp(self):
        self.eg = ExistentialGraph()
        self.editor = EGEditor(self.eg)
        self.soa = self.eg.sheet_of_assertion
        print("\n" + ("-" * 20))
        print(f"Running: {self._testMethodName}")

    def test_empty_graph(self):
        """Confirms an empty graph translates to 'true'."""
        translator = ClifTranslator(self.eg)
        expected, actual = "true", translator.translate()
        print(f"  - Testing empty graph.\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected)
        print("OK")

    def test_simple_negation(self):
        """Confirms a simple negation (P) translates correctly."""
        cut = self.editor.add_cut(self.soa)
        self.editor.add_predicate("P", 0, cut)
        translator = ClifTranslator(self.eg)
        expected, actual = "(not (P))", translator.translate()
        print(f"  - Testing (P).\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected)
        print("OK")

    def test_simple_implication(self):
        """Confirms a simple implication (P(Q)) translates correctly."""
        outer_cut = self.editor.add_cut(self.soa)
        self.editor.add_predicate("P", 0, outer_cut)
        inner_cut = self.editor.add_cut(outer_cut)
        self.editor.add_predicate("Q", 0, inner_cut)
        translator = ClifTranslator(self.eg)
        expected = "(not (and (P) (not (Q))))"
        actual = translator.translate()
        print(f"  - Testing (P(Q)).\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected)
        print("OK")
        
    def test_quantified_conjunction(self):
        """Confirms a simple quantified conjunction translates with deterministic variables."""
        p_cat = self.editor.add_predicate("cat", 1, self.soa)
        p_mat = self.editor.add_predicate("mat", 1, self.soa)
        p_on = self.editor.add_predicate("on", 2, self.soa)
        self.editor.connect(p_cat.hooks[0], p_on.hooks[0])
        self.editor.connect(p_mat.hooks[0], p_on.hooks[1])
        translator = ClifTranslator(self.eg)
        expected = "(exists (x1 x2) (and (cat x1) (mat x2) (on x1 x2)))"
        actual = translator.translate()
        print(f"  - Testing cat-on-mat.\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected)
        print("OK")

    def test_universal_quantifier(self):
        """Confirms a universal quantifier translates correctly using the LCA scope logic."""
        outer_cut = self.editor.add_cut(self.soa)
        cat_cut = self.editor.add_cut(outer_cut)
        animal_cut = self.editor.add_cut(outer_cut)
        p_cat = self.editor.add_predicate("cat", 1, cat_cut)
        p_animal = self.editor.add_predicate("animal", 1, animal_cut)
        lig = Ligature()
        p_cat.hooks[0].ligature = lig
        p_animal.hooks[0].ligature = lig
        lig.hooks.add(p_cat.hooks[0])
        lig.hooks.add(p_animal.hooks[0])
        translator = ClifTranslator(self.eg)
        expected = "(not (exists (x1) (and (not (animal x1)) (not (cat x1)))))"
        actual = translator.translate()
        print(f"  - Testing ((cat-)(animal-)).\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected)
        print("OK")

if __name__ == '__main__':
    unittest.main()