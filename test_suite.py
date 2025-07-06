# test_suite.py
import unittest
import xml.etree.ElementTree as ET
from eg_model import *
from eg_logic import *
from eg_renderer import *

# This file consolidates all tests from test_eg.py, test_renderer.py,
# and test_logic_advanced.py into a single, organized test suite.

# ######################################################################
# ##--- CORE MODEL AND LOGIC TESTS (from test_eg.py) ---##
# ######################################################################

class TestEGModel(unittest.TestCase):
    """Tests the foundational data structures in eg_model.py."""
    def setUp(self):
        self.eg = ExistentialGraph(); self.editor = EGEditor(self.eg); self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Model Test: {self._testMethodName} -----")
    def test_context_nesting(self):
        self.assertEqual(self.soa.get_nesting_level(), 0)
        cut1 = self.editor.add_cut(self.soa); self.assertEqual(cut1.get_nesting_level(), 1)
        cut2 = self.editor.add_cut(cut1); self.assertEqual(cut2.get_nesting_level(), 2)
        print("  - OK: Nesting levels (0, 1, 2) are correct.")
    def test_ligature_creation_and_merge(self):
        p1 = self.editor.add_predicate("p", 2, self.soa); p2 = self.editor.add_predicate("q", 1, self.soa)
        self.editor.connect(p1.hooks[0], p1.hooks[1]); self.assertIsNotNone(p1.hooks[0].ligature)
        self.assertIs(p1.hooks[0].ligature, p1.hooks[1].ligature); print("  - OK: Initial ligature created.")
        self.editor.connect(p1.hooks[0], p2.hooks[0]); self.assertIs(p2.hooks[0].ligature, p1.hooks[0].ligature)
        self.assertEqual(len(p2.hooks[0].ligature.hooks), 3); print("  - OK: Ligatures merged correctly.")
    def test_ligature_starting_context(self):
        cut1 = self.editor.add_cut(self.soa); p_outer = self.editor.add_predicate("P", 1, self.soa)
        p_inner = self.editor.add_predicate("Q", 1, cut1); self.editor.connect(p_outer.hooks[0], p_inner.hooks[0])
        self.assertIs(p_outer.hooks[0].ligature.get_starting_context(), self.soa)
        print("  - OK: Ligature starting context is correctly identified as the outermost.")
    def test_ligature_starting_context_lca(self):
        outer_cut = self.editor.add_cut(self.soa); cat_cut = self.editor.add_cut(outer_cut)
        animal_cut = self.editor.add_cut(outer_cut); p_cat = self.editor.add_predicate("cat", 1, cat_cut)
        p_animal = self.editor.add_predicate("animal", 1, animal_cut)
        self.editor.connect(p_cat.hooks[0], p_animal.hooks[0])
        self.assertIs(p_cat.hooks[0].ligature.get_starting_context(), outer_cut)
        print("  - OK: Ligature scope for sibling cuts is the correct LCA.")
    
    ## NEW ##
    def test_sever_ligature(self):
        p = self.editor.add_predicate("P", 1, self.soa)
        q = self.editor.add_predicate("Q", 1, self.soa)
        r = self.editor.add_predicate("R", 1, self.soa)
        self.editor.connect(p.hooks[0], q.hooks[0])
        self.editor.connect(q.hooks[0], r.hooks[0])
        original_lig = p.hooks[0].ligature
        self.assertIs(q.hooks[0].ligature, original_lig)
        self.assertIs(r.hooks[0].ligature, original_lig)
        self.assertEqual(len(original_lig.hooks), 3)

        # Sever Q from the group
        self.editor.sever_at_hook(q.hooks[0])

        # Check that Q has a new, separate ligature
        new_lig = q.hooks[0].ligature
        self.assertIsNotNone(new_lig)
        self.assertNotEqual(new_lig.id, original_lig.id)
        self.assertEqual(len(new_lig.hooks), 1)

        # Check that P and R are still connected on the original ligature
        self.assertIs(p.hooks[0].ligature, original_lig)
        self.assertIs(r.hooks[0].ligature, original_lig)
        self.assertEqual(len(original_lig.hooks), 2)
        print("  - OK: Ligature severing works correctly.")

class TestTransformations(unittest.TestCase):
    """Tests the Validator and the Editor's transformation methods."""
    def setUp(self):
        self.eg = ExistentialGraph(); self.editor = EGEditor(self.eg)
        self.validator = Validator(self.eg); self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Transformation Test: {self._testMethodName} -----")
    def test_can_insert_and_erase(self):
        cut1 = self.editor.add_cut(self.soa)
        p_on_soa = self.editor.add_predicate("P", 0, self.soa)
        p_in_cut1 = self.editor.add_predicate("Q", 0, cut1)
        subgraph_on_soa = Subgraph({p_on_soa}); subgraph_in_cut1 = Subgraph({p_in_cut1})
        self.assertFalse(self.validator.can_insert(self.soa)); self.assertTrue(self.validator.can_insert(cut1))
        self.assertTrue(self.validator.can_erase(subgraph_on_soa)); self.assertFalse(self.validator.can_erase(subgraph_in_cut1))
        print("  - OK: Rules validated.")    
    def test_add_double_cut_around_subgraph(self):
        p = self.editor.add_predicate("P", 0, self.soa); subgraph = Subgraph({p})
        self.editor.wrap_subgraph_with_double_cut(subgraph);
        self.assertEqual(ClifTranslator(self.eg).translate(), "(not (not (P)))"); print("  - OK")

    ## NEW ##
    def test_remove_double_cut(self):
        # Setup: (P) and (not (not (Q (R))))
        p = self.editor.add_predicate("P", 0, self.soa)
        dc_outer = self.editor.add_cut(self.soa)
        dc_inner = self.editor.add_cut(dc_outer)
        q = self.editor.add_predicate("Q", 0, dc_inner)
        r_cut = self.editor.add_cut(dc_inner)
        r = self.editor.add_predicate("R", 0, r_cut)

        # It should be removable
        self.assertTrue(self.validator.can_remove_double_cut(dc_outer))
        # Remove it
        self.editor.remove_double_cut(dc_outer)
        
        # Check final state
        self.assertIn(p, self.soa.predicates)
        self.assertIn(q, self.soa.predicates)
        self.assertIn(r_cut, self.soa.children)
        self.assertNotIn(dc_outer, self.soa.children)
        
        expected_clif = "(and (P) (Q) (not (R)))"
        self.assertEqual(ClifTranslator(self.eg).translate(), expected_clif)
        print("  - OK: Double cut removal works correctly.")

    def test_iteration_transformation(self):
        cut1 = self.editor.add_cut(self.soa); p_original = self.editor.add_predicate("P", 0, cut1)
        cut2 = self.editor.add_cut(cut1); subgraph_to_iterate = Subgraph({p_original})
        self.editor.iterate(subgraph_to_iterate, cut2)
        self.assertEqual(ClifTranslator(self.eg).translate(), "(not (and (P) (not (P))))"); print("  - OK")
    def test_deiteration(self):
        cut1 = self.editor.add_cut(self.soa); self.editor.add_predicate("P", 0, cut1)
        cut2 = self.editor.add_cut(cut1); p_copy = self.editor.add_predicate("P", 0, cut2)
        self.assertTrue(self.validator.can_deiterate(Subgraph({p_copy})))
        self.editor.deiterate(Subgraph({p_copy}));
        self.assertEqual(ClifTranslator(self.eg).translate(), "(not (and (P) (not true)))"); print("  - OK")

class TestConstantsAndFunctions(unittest.TestCase):
    """Tests implementation of constants and functions."""
    def setUp(self):
        self.eg = ExistentialGraph(); self.editor = EGEditor(self.eg)
        self.validator = Validator(self.eg); self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Constants/Functions Test: {self._testMethodName} -----")
    def test_constant_translation(self):
        p_man = self.editor.add_predicate("man", 1, self.soa)
        p_socrates = self.editor.add_predicate("Socrates", 1, self.soa, p_type=PredicateType.CONSTANT)
        self.editor.connect(p_man.hooks[0], p_socrates.hooks[0])
        self.assertEqual(ClifTranslator(self.eg).translate(), "(man Socrates)"); print("  - OK")
    def test_function_translation(self):
        p_add = self.editor.add_predicate("add", 3, self.soa, p_type=PredicateType.FUNCTION)
        p_7 = self.editor.add_predicate("7", 1, self.soa, p_type=PredicateType.CONSTANT)
        lig_x = Ligature(); lig_y = Ligature()
        self.editor.connect(p_add.hooks[0], p_add.hooks[0]); p_add.hooks[0].ligature = lig_x; lig_x.hooks.add(p_add.hooks[0])
        self.editor.connect(p_add.hooks[1], p_7.hooks[0])
        self.editor.connect(p_add.hooks[2], p_add.hooks[2]); p_add.hooks[2].ligature = lig_y; lig_y.hooks.add(p_add.hooks[2])
        self.assertEqual(ClifTranslator(self.eg).translate(), "(exists (x1 x2) (= x2 (add x1 7)))"); print("  - OK")
    def test_apply_functional_property_rule(self):
        p_x = self.editor.add_predicate("x", 1, self.soa, p_type=PredicateType.CONSTANT)
        p_7 = self.editor.add_predicate("7", 1, self.soa, p_type=PredicateType.CONSTANT)
        p_add1 = self.editor.add_predicate("add", 3, self.soa, p_type=PredicateType.FUNCTION)
        p_add2 = self.editor.add_predicate("add", 3, self.soa, p_type=PredicateType.FUNCTION)
        self.editor.connect(p_add1.hooks[0], p_x.hooks[0]); self.editor.connect(p_add1.hooks[1], p_7.hooks[0])
        self.editor.connect(p_add2.hooks[0], p_x.hooks[0]); self.editor.connect(p_add2.hooks[1], p_7.hooks[0])
        self.editor.connect(p_add1.hooks[2], p_add1.hooks[2]); self.editor.connect(p_add2.hooks[2], p_add2.hooks[2])
        self.editor.apply_functional_property(p_add1, p_add2)
        self.assertEqual(p_add1.hooks[2].ligature.id, p_add2.hooks[2].ligature.id); print("  - OK")

# ... (Renderer tests remain the same) ...

# ######################################################################
# ##--- RENDERER TESTS (from test_renderer.py) ---##
# ######################################################################

class TestRenderer(unittest.TestCase):
    """Tests the Renderer class."""
    def setUp(self):
        self.eg = ExistentialGraph()
        self.editor = EGEditor(self.eg)
        self.soa = self.eg.sheet_of_assertion
        self.renderer = Renderer(self.eg)
        print(f"\n----- Running Renderer Test: {self._testMethodName} -----")
    def test_render_empty_graph(self):
        svg_output = self.renderer.to_svg()
        self.assertTrue(svg_output.startswith("<svg")); self.assertTrue(svg_output.endswith("</svg>"))
        root = ET.fromstring(svg_output); self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        print("  - OK: SVG is well-formed.")
    def test_render_single_predicate(self):
        self.editor.add_predicate("P", 0, self.soa); svg_output = self.renderer.to_svg()
        self.assertIn(">P</text>", svg_output); print("  - OK: Predicate 'P' rendered.")
    def test_render_cut_with_predicate(self):
        cut1 = self.editor.add_cut(self.soa); self.editor.add_predicate("P", 0, cut1)
        svg_output = self.renderer.to_svg(); root = ET.fromstring(svg_output)
        cut_rect = root.find('.//{*}rect[@fill="lightgray"]'); text_element = root.find('.//{*}text')
        self.assertIsNotNone(cut_rect); self.assertIsNotNone(text_element); self.assertEqual(text_element.text, "P")
        print("  - OK: Predicate inside a cut rendered.")
    def test_render_ligature(self):
        p1 = self.editor.add_predicate("cat", 1, self.soa); p2 = self.editor.add_predicate("mat", 1, self.soa)
        self.editor.connect(p1.hooks[0], p2.hooks[0]); svg_output = self.renderer.to_svg()
        root = ET.fromstring(svg_output); path_element = root.find('.//{*}path')
        self.assertIsNotNone(path_element, "Ligature <path> element not found in SVG.")
        print("  - OK: Ligature rendered as an SVG path.")
    ## NEW ##
    def test_render_deeply_nested_graph(self):
        """
        Tests the bottom-up layout engine with a complex nested graph.
        The setup creates items in the order: P, (Q, (R S), T)
        """
        p = self.editor.add_predicate("P", 0, self.soa)
        cut1 = self.editor.add_cut(self.soa)
        q = self.editor.add_predicate("Q", 0, cut1)
        cut2 = self.editor.add_cut(cut1)
        r = self.editor.add_predicate("R", 0, cut2)
        s = self.editor.add_predicate("S", 0, cut2)
        t = self.editor.add_predicate("T", 0, cut1)
        
        svg_output = self.renderer.to_svg()

        root = ET.fromstring(svg_output)
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        texts = {t.text: (float(t.get('x')), float(t.get('y'))) for t in root.findall('.//svg:text', ns)}
        self.assertIn('P', texts); self.assertIn('Q', texts); self.assertIn('R', texts)
        self.assertIn('S', texts); self.assertIn('T', texts)

        # The renderer lays out predicates first, then child cuts.
        # The contents of cut1 are predicates [Q, T] and child [cut2].
        # Therefore, the layout order within cut1 will be: Q, T, then the (R S) cut.
        
        # Assert horizontal alignment reflects this actual layout.
        self.assertTrue(texts['Q'][0] < texts['T'][0], "Q should be laid out before T")
        self.assertTrue(texts['T'][0] < texts['R'][0], "T should be laid out before the (R S) cut")
        self.assertTrue(texts['T'][0] < texts['S'][0], "T should be laid out before the (R S) cut")
        
        print("  - OK: Deeply nested graph layout is geometrically correct according to the 'predicates first' rule.")


# ######################################################################
# ##--- CLIF & ADVANCED LOGIC TESTS (from test_logic_advanced.py) ---##
# ######################################################################

class TestClifTranslation(unittest.TestCase):
    """Tests round-trip translation and complex CLIF structures."""
    def setUp(self):
        self.eg = ExistentialGraph(); self.editor = EGEditor(self.eg); self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running CLIF Translation Test: {self._testMethodName} -----")
    def test_quantified_conjunction(self):
        p_cat = self.editor.add_predicate("cat", 1, self.soa); p_mat = self.editor.add_predicate("mat", 1, self.soa)
        p_on = self.editor.add_predicate("on", 2, self.soa)
        self.editor.connect(p_cat.hooks[0], p_on.hooks[0]); self.editor.connect(p_mat.hooks[0], p_on.hooks[1])
        translator = ClifTranslator(self.eg)
        self.assertEqual(translator.translate(), "(exists (x1 x2) (and (cat x1) (mat x2) (on x1 x2)))"); print("  - OK")
    def test_round_trip_simple(self):
        p_cat = self.editor.add_predicate("cat", 1, self.soa); p_mat = self.editor.add_predicate("mat", 1, self.soa)
        p_on = self.editor.add_predicate("on", 2, self.soa)
        self.editor.connect(p_cat.hooks[0], p_on.hooks[0]); self.editor.connect(p_mat.hooks[0], p_on.hooks[1])
        clif1 = ClifTranslator(self.eg).translate(); new_eg = ClifParser().parse(clif1); clif2 = ClifTranslator(new_eg).translate()
        self.assertEqual(clif1, clif2); print("  - OK")
    def test_round_trip_with_function(self):
        clif_string1 = "(exists (x1 x2) (= x2 (add x1 7)))"
        new_eg = ClifParser().parse(clif_string1); clif_string2 = ClifTranslator(new_eg).translate()
        self.assertEqual(clif_string1, clif_string2); print("  - OK")
    def test_round_trip_negated_identity(self):
        clif_string1 = "(exists (x1 x2) (and (sun x1) (sun x2) (not (= x1 x2))))"
        new_eg = ClifParser().parse(clif_string1); clif_string2 = ClifTranslator(new_eg).translate()
        self.assertEqual(clif_string1, clif_string2); print("  - OK")

class TestAdvancedTransformations(unittest.TestCase):
    """Tests complex rule interactions and logical validations."""
    def setUp(self):
        self.eg = ExistentialGraph(); self.editor = EGEditor(self.eg)
        self.validator = self.editor.validator; self.soa = self.eg.sheet_of_assertion
        print(f"\n----- Running Advanced Transformation Test: {self._testMethodName} -----")
    def test_deiteration_requires_isomorphic_structure(self):
        p_P_orig = self.editor.add_predicate("P", 2, self.soa)
        p_Q_orig = self.editor.add_predicate("Q", 1, self.soa)
        self.editor.connect(p_P_orig.hooks[1], p_Q_orig.hooks[0]) # P(x,y) Q(y)
        cut = self.editor.add_cut(self.soa)
        p_P_iso = self.editor.add_predicate("P", 2, cut)
        p_Q_iso = self.editor.add_predicate("Q", 1, cut)
        self.editor.connect(p_P_iso.hooks[1], p_Q_iso.hooks[0])
        lig_iso = p_P_iso.hooks[1].ligature
        subgraph_iso_correct = Subgraph({p_P_iso, p_Q_iso, lig_iso})
        p_P_non = self.editor.add_predicate("P", 2, cut)
        p_Q_non = self.editor.add_predicate("Q", 1, cut)
        self.editor.connect(p_P_non.hooks[0], p_Q_non.hooks[0])
        lig_non_iso = p_P_non.hooks[0].ligature
        subgraph_non_iso_correct = Subgraph({p_P_non, p_Q_non, lig_non_iso})
        self.assertTrue(self.validator.can_deiterate(subgraph_iso_correct))
        self.assertFalse(self.validator.can_deiterate(subgraph_non_iso_correct))
        print("  - OK: Isomorphism check for de-iteration is correct.")
    def test_iteration_of_subgraph_with_double_cut(self):
        p_P = self.editor.add_predicate("P", 0, self.soa)
        dc_outer = self.editor.add_cut(self.soa); dc_inner = self.editor.add_cut(dc_outer)
        q = self.editor.add_predicate("Q", 0, dc_inner)
        subgraph_to_iterate = Subgraph({dc_outer, dc_inner, q})
        target_cut = self.editor.add_cut(self.soa)
        self.editor.iterate(subgraph_to_iterate, target_cut)
        actual = ClifTranslator(self.eg).translate()
        self.assertIn("(not (not (Q)))", actual); self.assertIn("(not (not (not (Q))))", actual)
        print("  - OK: Iteration of double cut is correct.")
    def test_erase_of_subgraph_with_dangling_ligatures(self):
        p_P = self.editor.add_predicate("P", 1, self.soa); cut = self.editor.add_cut(self.soa)
        p_Q = self.editor.add_predicate("Q", 1, cut); self.editor.connect(p_P.hooks[0], p_Q.hooks[0])
        subgraph_to_erase = Subgraph({p_P}); self.editor.erase_subgraph(subgraph_to_erase)
        self.assertEqual(ClifTranslator(self.eg).translate(), "(not (exists (x1) (Q x1)))"); print("  - OK")

class TestParserRobustness(unittest.TestCase):
    """Tests the CLIF parser's ability to handle malformed input."""
    def setUp(self):
        self.parser = ClifParser()
        print(f"\n----- Running Parser Robustness Test: {self._testMethodName} -----")
    def test_unclosed_parenthesis(self):
        with self.assertRaisesRegex(ClifParserError, "Unclosed parenthesis"):
            self.parser.parse("(and (P x)")
        print("  - OK: Correctly caught unclosed parenthesis.")
    def test_malformed_not(self):
        with self.assertRaisesRegex(ClifParserError, "Malformed 'not' expression"):
            self.parser.parse("(not (P x) (Q y))")
        print("  - OK: Correctly caught malformed 'not'.")
    def test_malformed_equals(self):
        with self.assertRaisesRegex(ClifParserError, "Malformed '=' expression"):
            self.parser.parse("(= x y z)")
        print("  - OK: Correctly caught malformed '='.")

if __name__ == '__main__':
    unittest.main()