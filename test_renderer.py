import unittest
from eg_model import GraphModel
from eg_editor import EGEditor
from eg_renderer import Renderer

class TestRenderer(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.model = self.editor.model
        self.renderer = Renderer(self.model)

    def test_render_empty_graph(self):
        output = self.renderer.render()
        self.assertIn('<svg', output)

    def test_render_single_predicate(self):
        self.editor.add_predicate('P', 0)
        output = self.renderer.render()
        self.assertIn('>P</text>', output)

    def test_render_single_empty_cut(self):
        self.editor.add_cut()
        output = self.renderer.render()
        self.assertIn('<rect', output)

    def test_render_cut_with_predicate(self):
        cut_id = self.editor.add_cut()
        self.editor.add_predicate('P', 0, parent_id=cut_id)
        output = self.renderer.render()
        # Basic check: both elements should be present
        self.assertIn('<rect', output)
        self.assertIn('>P</text>', output)

    def test_render_multiple_predicates(self):
        self.editor.add_predicate('P', 0)
        self.editor.add_predicate('Q', 0)
        output = self.renderer.render()
        self.assertIn('>P</text>', output)
        self.assertIn('>Q</text>', output)

    # Ligature and double cut rendering tests are complex and would need
    # a more sophisticated layout algorithm and position checking.