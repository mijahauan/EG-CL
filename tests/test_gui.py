import unittest
from PySide6.QtWidgets import QApplication, QGraphicsScene
from eg_editor import EGEditor
from enhanced_main_gui import EnhancedGraphView
from interaction_manager import InteractionManager, InteractionMode
from eg_renderer import Renderer

app = QApplication([])

class TestGUI(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.scene = QGraphicsScene()
        self.view = EnhancedGraphView(self.scene, self.editor)
        self.manager = self.view.interaction_manager
        self.renderer = Renderer(self.editor.model)

    def test_mode_switching(self):
        """Tests that the interaction manager can switch modes correctly."""
        self.manager.set_mode(InteractionMode.CREATE_CUT)
        self.assertEqual(self.manager.mode, InteractionMode.CREATE_CUT)

    def test_render_empty_graph(self):
        """Tests rendering a graph with nothing on the Sheet of Assertion."""
        output = self.renderer.render()
        self.assertIn('<svg', output)

    def test_render_single_predicate(self):
        """Tests rendering a graph with a single predicate."""
        self.editor.add_predicate('P', 0)
        output = self.renderer.render()
        self.assertIn('>P</text>', output)