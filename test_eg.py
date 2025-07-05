# test_eg.py
import unittest
from eg_model import *
from eg_logic import *

class TestEGModel(unittest.TestCase):
    """Tests the foundational data structures in eg_model.py."""
    def setUp(self):
        self.eg = ExistentialGraph(); self.editor = EGEditor(self.eg); self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Model Test: {self._testMethodName} -----")
    def test_context_nesting(self):
        """Verifies that the Context tree and nesting levels are calculated correctly."""
        self.assertEqual(self.soa.get_nesting_level(), 0)
        cut1 = self.editor.add_cut(self.soa); self.assertEqual(cut1.get_nesting_level(), 1)
        cut2 = self.editor.add_cut(cut1); self.assertEqual(cut2.get_nesting_level(), 2)
        print("  - OK: Nesting levels (0, 1, 2) are correct.")
    def test_ligature_creation_and_merge(self):
        """Tests the core logic of creating and merging Ligatures via the editor."""
        p1 = self.editor.add_predicate("p", 2, self.soa); p2 = self.editor.add_predicate("q", 1, self.soa)
        self.editor.connect(p1.hooks[0], p1.hooks[1]); self.assertIsNotNone(p1.hooks[0].ligature)
        self.assertIs(p1.hooks[0].ligature, p1.hooks[1].ligature); print("  - OK: Initial ligature created.")
        self.editor.connect(p1.hooks[0], p2.hooks[0]); self.assertIs(p2.hooks[0].ligature, p1.hooks[0].ligature)
        self.assertEqual(len(p2.hooks[0].ligature.hooks), 3); print("  - OK: Ligatures merged correctly.")
    def test_ligature_starting_context(self):
        """Tests that a ligature spanning a parent and child context has the correct scope."""
        cut1 = self.editor.add_cut(self.soa); p_outer = self.editor.add_predicate("P", 1, self.soa)
        p_inner = self.editor.add_predicate("Q", 1, cut1); self.editor.connect(p_outer.hooks[0], p_inner.hooks[0])
        self.assertIs(p_outer.hooks[0].ligature.get_starting_context(), self.soa)
        print("  - OK: Ligature starting context is correctly identified as the outermost.")
    def test_ligature_starting_context_lca(self):
        """Tests the Least Common Ancestor (LCA) logic for a ligature spanning sibling cuts."""
        outer_cut = self.editor.add_cut(self.soa); cat_cut = self.editor.add_cut(outer_cut)
        animal_cut = self.editor.add_cut(outer_cut); p_cat = self.editor.add_predicate("cat", 1, cat_cut)
        p_animal = self.editor.add_predicate("animal", 1, animal_cut); lig = Ligature()
        p_cat.hooks[0].ligature = lig; p_animal.hooks[0].ligature = lig
        lig.hooks.add(p_cat.hooks[0]); lig.hooks.add(p_animal.hooks[0])
        self.assertIs(lig.get_starting_context(), outer_cut)
        print("  - OK: Ligature scope for sibling cuts is the correct LCA.")

class TestTransformations(unittest.TestCase):
    """Tests the Validator and the Editor's transformation methods."""
    def setUp(self):
        self.eg = ExistentialGraph(); self.editor = EGEditor(self.eg)
        self.validator = Validator(self.eg); self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Transformation Test: {self._testMethodName} -----")
    def test_can_insert_and_erase(self):
        """Validates the Insertion (odd contexts) and Erasure (even contexts) rules."""
        cut1 = self.editor.add_cut(self.soa)
        p_on_soa = self.editor.add_predicate("P", 0, self.soa)
        p_in_cut1 = self.editor.add_predicate("Q", 0, cut1)
        
        # To test the rule, we must operate on a Subgraph, not a raw Predicate.
        subgraph_on_soa = Subgraph({p_on_soa})
        subgraph_in_cut1 = Subgraph({p_in_cut1})
        
        print("  - Validating insertion/erasure permissions by context parity.")
        self.assertFalse(self.validator.can_insert(self.soa))
        self.assertTrue(self.validator.can_insert(cut1))
        
        # Now pass the Subgraph objects to the validator.
        self.assertTrue(self.validator.can_erase(subgraph_on_soa))
        self.assertFalse(self.validator.can_erase(subgraph_in_cut1))
        print("  - OK: Rules validated.")    
    def test_add_double_cut_around_subgraph(self):
        """Tests wrapping an existing predicate with a double cut."""
        p = self.editor.add_predicate("P", 0, self.soa)
        subgraph = Subgraph({p})
        self.assertTrue(self.validator.can_add_double_cut())
        self.editor.wrap_subgraph_with_double_cut(subgraph)
        outer_cut = self.soa.children[0]
        inner_cut = outer_cut.children[0]
        self.assertIn(p, inner_cut.predicates)
        expected_clif = "(not (not (P)))"
        actual_clif = ClifTranslator(self.eg).translate()
        print(f"  - Testing wrap with double cut.\n  - Expected: {expected_clif}\n  - Actual:   {actual_clif}")
        self.assertEqual(actual_clif, expected_clif)
        print("  - OK")
    def test_can_remove_double_cut(self):
        """Validates the basic check for the Double Cut rule."""
        dc_outer = self.editor.add_cut(self.soa); self.editor.add_cut(dc_outer)
        self.assertTrue(self.validator.can_remove_double_cut(dc_outer))
        dc_outer_2 = self.editor.add_cut(self.soa); self.editor.add_cut(dc_outer_2)
        self.editor.add_predicate("P", 0, dc_outer_2); self.assertFalse(self.validator.can_remove_double_cut(dc_outer_2))
        print("  - OK: Double cut validation is correct.")
    def test_iteration_validation(self):
        """Validates the logic for where a subgraph is permitted to be iterated."""
        cut1 = self.editor.add_cut(self.soa); p = self.editor.add_predicate("P", 0, cut1)
        cut2 = self.editor.add_cut(cut1); subgraph = Subgraph({p})
        self.assertTrue(self.validator.can_iterate(subgraph, cut2))
        self.assertFalse(self.validator.can_iterate(subgraph, self.soa))
        print("  - OK: Iteration validation is correct.")
    def test_iteration_transformation(self):
        """Tests the actual transformation of iterating a simple proposition."""
        cut1 = self.editor.add_cut(self.soa); p_original = self.editor.add_predicate("P", 0, cut1)
        cut2 = self.editor.add_cut(cut1); subgraph_to_iterate = Subgraph({p_original})
        self.editor.iterate(subgraph_to_iterate, cut2)
        self.assertEqual(len(cut2.predicates), 1); self.assertEqual(cut2.predicates[0].name, "P")
        translator = ClifTranslator(self.eg)
        self.assertEqual(translator.translate(), "(not (and (P) (not (P))))")
        print("  - OK: Iteration of a simple proposition works.")
    def test_iteration_with_external_ligature(self):
        """Tests iterating a subgraph that is connected to the outer graph."""
        p_r = self.editor.add_predicate("R", 1, self.soa); cut = self.editor.add_cut(self.soa)
        p_p_original = self.editor.add_predicate("P", 1, cut)
        self.editor.connect(p_r.hooks[0], p_p_original.hooks[0]); original_ligature = p_r.hooks[0].ligature
        subgraph_to_iterate = Subgraph({p_p_original, original_ligature})
        self.editor.iterate(subgraph_to_iterate, cut); self.assertEqual(len(cut.predicates), 2)
        p_copy = cut.predicates[1]; self.assertEqual(p_copy.name, "P")
        self.assertEqual(len(original_ligature.hooks), 3); translator = ClifTranslator(self.eg)
        self.assertEqual(translator.translate(), "(exists (x1) (and (R x1) (not (and (P x1) (P x1)))))")
        print("  - OK: Iteration with external ligature works.")
    def test_deiteration(self):
        """Tests the full de-iteration workflow: validation, transformation, and final state."""
        cut1 = self.editor.add_cut(self.soa); p_original = self.editor.add_predicate("P", 0, cut1)
        cut2 = self.editor.add_cut(cut1); p_copy = self.editor.add_predicate("P", 0, cut2)
        self.assertTrue(self.validator.can_deiterate(Subgraph({p_copy})))
        self.assertFalse(self.validator.can_deiterate(Subgraph({p_original})))
        self.editor.deiterate(Subgraph({p_copy})); translator = ClifTranslator(self.eg)
        self.assertEqual(translator.translate(), "(not (and (P) (not true)))")
        print("  - OK: De-iteration validation and transformation are correct.")


class TestClifTranslator(unittest.TestCase):
    def setUp(self):
        self.eg = ExistentialGraph(); self.editor = EGEditor(self.eg); self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Translator Test: {self._testMethodName} -----")
    def test_empty_graph(self):
        """Confirms an empty graph translates to 'true'."""
        translator = ClifTranslator(self.eg)
        expected, actual = "true", translator.translate()
        print(f"  - Testing empty graph.\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected); print("OK")
    def test_simple_negation(self):
        """Confirms a simple negation (P) translates correctly."""
        cut = self.editor.add_cut(self.soa); self.editor.add_predicate("P", 0, cut)
        translator = ClifTranslator(self.eg); expected, actual = "(not (P))", translator.translate()
        print(f"  - Testing (P).\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected); print("OK")
    def test_simple_implication(self):
        """Confirms a simple implication (P(Q)) translates correctly."""
        outer_cut = self.editor.add_cut(self.soa); self.editor.add_predicate("P", 0, outer_cut)
        inner_cut = self.editor.add_cut(outer_cut); self.editor.add_predicate("Q", 0, inner_cut)
        translator = ClifTranslator(self.eg); expected = "(not (and (P) (not (Q))))"; actual = translator.translate()
        print(f"  - Testing (P(Q)).\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected); print("OK")
    def test_quantified_conjunction(self):
        """Confirms a simple quantified conjunction translates with deterministic variables."""
        p_cat = self.editor.add_predicate("cat", 1, self.soa); p_mat = self.editor.add_predicate("mat", 1, self.soa)
        p_on = self.editor.add_predicate("on", 2, self.soa)
        self.editor.connect(p_cat.hooks[0], p_on.hooks[0]); self.editor.connect(p_mat.hooks[0], p_on.hooks[1])
        translator = ClifTranslator(self.eg); expected = "(exists (x1 x2) (and (cat x1) (mat x2) (on x1 x2)))"
        actual = translator.translate(); print(f"  - Testing cat-on-mat.\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected); print("OK")
    def test_universal_quantifier(self):
        """Confirms a universal quantifier translates correctly using the LCA scope logic."""
        outer_cut = self.editor.add_cut(self.soa); cat_cut = self.editor.add_cut(outer_cut)
        animal_cut = self.editor.add_cut(outer_cut); p_cat = self.editor.add_predicate("cat", 1, cat_cut)
        p_animal = self.editor.add_predicate("animal", 1, animal_cut); lig = Ligature()
        p_cat.hooks[0].ligature = lig; p_animal.hooks[0].ligature = lig
        lig.hooks.add(p_cat.hooks[0]); lig.hooks.add(p_animal.hooks[0])
        translator = ClifTranslator(self.eg)
        expected = "(not (exists (x1) (and (not (animal x1)) (not (cat x1)))))"
        actual = translator.translate(); print(f"  - Testing ((cat-)(animal-)).\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected); print("OK")
    def test_negated_identity(self):
        """Tests the translation of a graph with negated identity."""
        # Represents: (exists (x y) (and (sun x) (sun y) (not (= x y))))
        # This is built by putting the identity predicate inside a cut.
        p_sun1 = self.editor.add_predicate("sun", 1, self.soa)
        p_sun2 = self.editor.add_predicate("sun", 1, self.soa)

        # The identity assertion is inside the negative context
        neg_cut = self.editor.add_cut(self.soa)
        p_eq = self.editor.add_predicate("=", 2, neg_cut)

        # Connect the two suns to the identity predicate
        self.editor.connect(p_sun1.hooks[0], p_eq.hooks[0])
        self.editor.connect(p_sun2.hooks[0], p_eq.hooks[1])

        translator = ClifTranslator(self.eg)
        expected = "(exists (x1 x2) (and (sun x1) (sun x2) (not (= x1 x2))))"
        actual = translator.translate()
        print(f"  - Testing negated identity.\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected)
        print("  - OK")


class TestConstants(unittest.TestCase):
    """Tests the implementation of constants."""
    def setUp(self):
        self.eg = ExistentialGraph(); self.editor = EGEditor(self.eg); self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Constants Test: {self._testMethodName} -----")
    def test_constant_translation(self):
        """Tests that a constant is translated as a name, not a quantified variable."""
        p_man = self.editor.add_predicate("man", 1, self.soa)
        p_socrates = self.editor.add_predicate("Socrates", 1, self.soa, p_type=PredicateType.CONSTANT)
        self.editor.connect(p_man.hooks[0], p_socrates.hooks[0]); translator = ClifTranslator(self.eg)
        expected, actual = "(man Socrates)", translator.translate()
        print(f"  - Testing: 'man(Socrates)'\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected); print("OK")
    def test_existence_of_constants_rule(self):
        """Tests that creating an isolated constant doesn't break the translator."""
        self.editor.add_predicate("Plato", 1, self.soa, p_type=PredicateType.CONSTANT)
        translator = ClifTranslator(self.eg)
        self.assertEqual(translator.translate(), "true")
        print("OK")
    def test_apply_constant_identity_rule(self):
        """Tests the application of the Constant Identity Rule transformation."""
        p_socrates1 = self.editor.add_predicate("Socrates", 1, self.soa, p_type=PredicateType.CONSTANT)
        p_socrates2 = self.editor.add_predicate("Socrates", 1, self.soa, p_type=PredicateType.CONSTANT)

        # Connect hooks to themselves to create distinct ligatures initially
        self.editor.connect(p_socrates1.hooks[0], p_socrates1.hooks[0])
        self.editor.connect(p_socrates2.hooks[0], p_socrates2.hooks[0])

        # Ensure they are initially on different ligatures
        self.assertNotEqual(p_socrates1.hooks[0].ligature.id, p_socrates2.hooks[0].ligature.id)

        # Apply the rule
        self.editor.apply_constant_identity(p_socrates1, p_socrates2)

        # Now, they should be on the same ligature
        self.assertEqual(p_socrates1.hooks[0].ligature.id, p_socrates2.hooks[0].ligature.id)
        print("  - OK: Constant Identity Rule correctly merged ligatures.")        

class TestFunctions(unittest.TestCase):
    """Tests the implementation of functions."""
    def setUp(self):
        self.eg = ExistentialGraph(); self.editor = EGEditor(self.eg)
        self.validator = Validator(self.eg); self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Function Test: {self._testMethodName} -----")

    def test_function_translation(self):
        """Tests that a function is translated into a CLIF functional term with equality."""
        # Represents: y = add(x, "7")
        p_add = self.editor.add_predicate("add", 3, self.soa, p_type=PredicateType.FUNCTION)
        p_7 = self.editor.add_predicate("7", 1, self.soa, p_type=PredicateType.CONSTANT)
        
        # Create ligatures for x and y
        lig_x = Ligature()
        lig_y = Ligature()

        # Connect inputs: hook0->x, hook1->"7"
        self.editor.connect(p_add.hooks[0], p_add.hooks[0]) # connect to self to assign a ligature
        p_add.hooks[0].ligature = lig_x
        lig_x.hooks.add(p_add.hooks[0])
        
        self.editor.connect(p_add.hooks[1], p_7.hooks[0])
        
        # Connect output: hook2->y
        self.editor.connect(p_add.hooks[2], p_add.hooks[2]) # connect to self to assign a ligature
        p_add.hooks[2].ligature = lig_y
        lig_y.hooks.add(p_add.hooks[2])

        translator = ClifTranslator(self.eg)
        actual = translator.translate()
        expected = "(exists (x1 x2) (= x2 (add x1 7)))"
        
        print(f"  - Testing function translation.\n  - Expected: {expected}\n  - Actual:   {actual}")
        self.assertEqual(actual, expected)
        print("  - OK")

    def test_functional_property_rule(self):
        """Tests validation of the Functional Property (uniqueness) rule."""
        # Represents y1 = add(x, 7) and y2 = add(x, 7)
        p_x = self.editor.add_predicate("x", 1, self.soa, p_type=PredicateType.CONSTANT)
        p_7 = self.editor.add_predicate("7", 1, self.soa, p_type=PredicateType.CONSTANT)
        
        p_add1 = self.editor.add_predicate("add", 3, self.soa, p_type=PredicateType.FUNCTION)
        p_add2 = self.editor.add_predicate("add", 3, self.soa, p_type=PredicateType.FUNCTION)

        # Connect inputs for first call (hooks 0 and 1)
        self.editor.connect(p_add1.hooks[0], p_x.hooks[0])
        self.editor.connect(p_add1.hooks[1], p_7.hooks[0])

        # Connect inputs for second call (hooks 0 and 1)
        self.editor.connect(p_add2.hooks[0], p_x.hooks[0])
        self.editor.connect(p_add2.hooks[1], p_7.hooks[0])
        
        can_apply = self.validator.can_apply_functional_property(p_add1, p_add2)
        print(f"  - Can apply functional property? Expected: True. Got: {can_apply}")
        self.assertTrue(can_apply)
        print("  - OK")
        
    def test_apply_functional_property_rule(self):
        """Tests the application of the Functional Property Rule transformation."""
        # Represents y1 = add(x, 7) and y2 = add(x, 7)
        p_x = self.editor.add_predicate("x", 1, self.soa, p_type=PredicateType.CONSTANT)
        p_7 = self.editor.add_predicate("7", 1, self.soa, p_type=PredicateType.CONSTANT)
        
        p_add1 = self.editor.add_predicate("add", 3, self.soa, p_type=PredicateType.FUNCTION)
        p_add2 = self.editor.add_predicate("add", 3, self.soa, p_type=PredicateType.FUNCTION)

        # Connect inputs for both function calls to be identical
        self.editor.connect(p_add1.hooks[0], p_x.hooks[0]) # input 1 for add1
        self.editor.connect(p_add1.hooks[1], p_7.hooks[0]) # input 2 for add1
        self.editor.connect(p_add2.hooks[0], p_x.hooks[0]) # input 1 for add2
        self.editor.connect(p_add2.hooks[1], p_7.hooks[0]) # input 2 for add2
        
        # Connect outputs to themselves to create distinct ligatures initially
        self.editor.connect(p_add1.hooks[2], p_add1.hooks[2]) # output for add1
        self.editor.connect(p_add2.hooks[2], p_add2.hooks[2]) # output for add2
        
        # Ensure the outputs are initially on different ligatures
        self.assertNotEqual(p_add1.hooks[2].ligature.id, p_add2.hooks[2].ligature.id)
        
        # Apply the rule
        self.editor.apply_functional_property(p_add1, p_add2)
        
        # Now, the outputs should be on the same ligature
        self.assertEqual(p_add1.hooks[2].ligature.id, p_add2.hooks[2].ligature.id)
        print("  - OK: Functional Property Rule correctly merged output ligatures.")


class TestRoundTrip(unittest.TestCase):
    """Tests the full round-trip translation: EG -> CLIF -> EG -> CLIF."""
    def setUp(self):
        self.eg = ExistentialGraph()
        self.editor = EGEditor(self.eg)
        self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Round-Trip Test: {self._testMethodName} -----")

    def test_s_expression_parser(self):
        """Tests the internal CLIF string parser."""
        parser = ClifParser()
        test_string = "(and (P x1) (not (Q y1)))"
        tokens = parser._tokenize(test_string)
        ast, _ = parser._parse_s_expression(tokens)
        
        expected_ast = ['and', ['P', 'x1'], ['not', ['Q', 'y1']]]
        print(f"  - Testing S-expression parser.\n  - Expected: {expected_ast}\n  - Actual:   {ast}")
        self.assertEqual(ast, expected_ast)
        print("  - OK")

    def test_round_trip_simple(self):
        """Tests a simple round-trip with relations and quantifiers."""
        # 1. Arrange: Create the 'cat on mat' graph
        p_cat = self.editor.add_predicate("cat", 1, self.soa)
        p_mat = self.editor.add_predicate("mat", 1, self.soa)
        p_on = self.editor.add_predicate("on", 2, self.soa)
        self.editor.connect(p_cat.hooks[0], p_on.hooks[0])
        self.editor.connect(p_mat.hooks[0], p_on.hooks[1])
        
        # 2. Act 1: Translate to CLIF
        translator1 = ClifTranslator(self.eg)
        clif_string1 = translator1.translate()
        print(f"  - Original CLIF: {clif_string1}")
        
        # 3. Act 2: Parse back into a new EG model
        parser = ClifParser()
        new_eg = parser.parse(clif_string1)
        
        # 4. Act 3: Translate the new model back to CLIF
        translator2 = ClifTranslator(new_eg)
        clif_string2 = translator2.translate()
        print(f"  - Round-trip CLIF: {clif_string2}")

        # 5. Assert: The two strings must be identical
        self.assertEqual(clif_string1, clif_string2)
        print("  - OK")

        
if __name__ == '__main__':
    unittest.main()