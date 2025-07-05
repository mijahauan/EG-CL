# test_renderer.py
import unittest
import xml.etree.ElementTree as ET
from eg_model import *
from eg_logic import *
from eg_renderer import *

class TestRenderer(unittest.TestCase):
    """Tests the Renderer class."""
    def setUp(self):
        self.eg = ExistentialGraph()
        self.editor = EGEditor(self.eg)
        self.soa = self.eg.sheet_of_assertion
        self.renderer = Renderer(self.eg)
        print(f"\n----- Running Renderer Test: {self._testMethodName} -----")

    def test_render_empty_graph(self):
        """Tests rendering a graph with nothing on the Sheet of Assertion."""
        svg_output = self.renderer.to_svg()
        print("  - Generated SVG for empty graph.")

        # Basic sanity check
        self.assertTrue(svg_output.startswith("<svg"))
        self.assertTrue(svg_output.endswith("</svg>"))

        # Parse the XML to ensure it's well-formed
        try:
            root = ET.fromstring(svg_output)
            # Check for the tag name including the SVG namespace
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            print("  - OK: SVG is well-formed.")
        except ET.ParseError as e:
            self.fail(f"SVG parsing failed: {e}")

    def test_render_single_predicate(self):
        """Tests rendering a graph with a single predicate."""
        self.editor.add_predicate("P", 0, self.soa)
        svg_output = self.renderer.to_svg()
        
        print("  - Generated SVG for single predicate 'P'.")
        # You can optionally save the SVG to inspect it visually:
        # with open("single_predicate.svg", "w") as f:
        #     f.write(svg_output)
            
        self.assertIn(">P</text>", svg_output)
        
        try:
            root = ET.fromstring(svg_output)
            # Find the text element
            text_element = root.find('.//{*}text')
            self.assertIsNotNone(text_element, "Text element for 'P' not found in SVG.")
            self.assertEqual(text_element.text, "P")
            print("  - OK: Predicate 'P' rendered correctly.")
        except ET.ParseError as e:
            self.fail(f"SVG parsing failed: {e}")

    def test_render_multiple_predicates(self):
        """Tests rendering multiple predicates laid out horizontally."""
        p1 = self.editor.add_predicate("cat", 0, self.soa)
        p2 = self.editor.add_predicate("is", 0, self.soa)
        p3 = self.editor.add_predicate("on", 0, self.soa)
        p4 = self.editor.add_predicate("mat", 0, self.soa)
        
        svg_output = self.renderer.to_svg()
        print("  - Generated SVG for multiple predicates.")
        
        # with open("multiple_predicates.svg", "w") as f:
        #     f.write(svg_output)
            
        try:
            root = ET.fromstring(svg_output)
            texts = root.findall('.//{*}text')
            self.assertEqual(len(texts), 4)
            
            rendered_texts = {t.text for t in texts}
            self.assertEqual(rendered_texts, {"cat", "is", "on", "mat"})
            
            # Check that they are laid out horizontally (different x-coordinates)
            x_coords = {float(t.get('x')) for t in texts}
            self.assertEqual(len(x_coords), 4, "Predicates should have distinct x-coordinates.")
            print("  - OK: Multiple predicates rendered correctly.")
        except ET.ParseError as e:
            self.fail(f"SVG parsing failed: {e}")

    def test_render_single_empty_cut(self):
        """Tests rendering of a single, empty, negative context (cut)."""
        self.editor.add_cut(self.soa)
        svg_output = self.renderer.to_svg()

        # with open("single_cut.svg", "w") as f:
        #     f.write(svg_output)
        
        try:
            root = ET.fromstring(svg_output)
            # Find the <rect> element for the cut
            cut_rect = root.find('.//{*}rect[@fill="lightgray"]')
            self.assertIsNotNone(cut_rect, "Could not find shaded rect for negative cut.")
            print("  - OK: Empty negative cut rendered correctly.")
        except ET.ParseError as e:
            self.fail(f"SVG parsing failed: {e}")

    def test_render_cut_with_predicate(self):
        """Tests rendering a predicate inside a single cut."""
        cut1 = self.editor.add_cut(self.soa)
        self.editor.add_predicate("P", 0, cut1)
        svg_output = self.renderer.to_svg()

        # with open("cut_with_predicate.svg", "w") as f:
        #     f.write(svg_output)
            
        try:
            root = ET.fromstring(svg_output)
            cut_rect = root.find('.//{*}rect[@fill="lightgray"]')
            text_element = root.find('.//{*}text')

            self.assertIsNotNone(cut_rect)
            self.assertIsNotNone(text_element)
            self.assertEqual(text_element.text, "P")

            # Check if the text is inside the rectangle
            rect_x, rect_y = float(cut_rect.get('x')), float(cut_rect.get('y'))
            rect_w, rect_h = float(cut_rect.get('width')), float(cut_rect.get('height'))
            text_x, text_y = float(text_element.get('x')), float(text_element.get('y'))

            self.assertTrue(text_x > rect_x)
            self.assertTrue(text_y < rect_y + rect_h) # Text y is baseline, so it's near the bottom
            print("  - OK: Predicate inside a cut rendered correctly.")
        except ET.ParseError as e:
            self.fail(f"SVG parsing failed: {e}")

    def test_render_double_cut(self):
        """Tests that a double cut renders as a shaded rect containing a white rect."""
        self.editor.add_double_cut(self.soa)
        svg_output = self.renderer.to_svg()
        
        # with open("double_cut.svg", "w") as f:
        #     f.write(svg_output)

        try:
            root = ET.fromstring(svg_output)
            outer_cut = root.find('.//{*}rect[@fill="lightgray"]')
            inner_cut = root.find('.//{*}rect[@fill="white"]')
            
            self.assertIsNotNone(outer_cut, "Outer (odd) cut not found.")
            self.assertIsNotNone(inner_cut, "Inner (even) cut not found.")
            
            outer_x, outer_w = float(outer_cut.get('x')), float(outer_cut.get('width'))
            inner_x, inner_w = float(inner_cut.get('x')), float(inner_cut.get('width'))
            
            self.assertTrue(inner_x > outer_x)
            self.assertTrue((inner_x + inner_w) < (outer_x + outer_w))
            print("  - OK: Double cut rendered with correct nesting and shading.")
        except ET.ParseError as e:
            self.fail(f"SVG parsing failed: {e}")

    def test_render_ligature(self):
        """Tests that a ligature between two predicates is rendered."""
        p1 = self.editor.add_predicate("cat", 1, self.soa)
        p2 = self.editor.add_predicate("mat", 1, self.soa)
        self.editor.connect(p1.hooks[0], p2.hooks[0])

        svg_output = self.renderer.to_svg()
        # with open("ligature.svg", "w") as f:
        #     f.write(svg_output)
        
        try:
            root = ET.fromstring(svg_output)
            path_element = root.find('.//{*}path')
            self.assertIsNotNone(path_element, "Ligature <path> element not found in SVG.")
            
            path_data = path_element.get('d')
            self.assertIsNotNone(path_data, "Path element has no 'd' attribute.")
            self.assertTrue(path_data.startswith("M "), "Path data should start with a 'Move To' command.")
            self.assertIn("L ", path_data, "Path data should contain a 'Line To' command.")
            print("  - OK: Ligature rendered as an SVG path.")
        except ET.ParseError as e:
            self.fail(f"SVG parsing failed: {e}")


if __name__ == '__main__':
    unittest.main()