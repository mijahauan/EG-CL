import unittest
from PySide6.QtWidgets import QApplication, QGraphicsScene
from eg_editor import EGEditor
from eg_model import GraphModel, Cut 
from enhanced_main_gui import EnhancedGraphView
from interaction_manager import InteractionManager, InteractionMode

app = QApplication([])

class TestEnhancedCore(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.scene = QGraphicsScene()
        self.view = EnhancedGraphView(self.scene, self.editor)
        self.manager = self.view.interaction_manager

    def test_mode_switching(self):
        self.manager.set_mode(InteractionMode.CREATE_CUT)
        self.assertEqual(self.manager.mode, InteractionMode.CREATE_CUT)
        self.manager.set_mode(InteractionMode.SELECT)
        self.assertEqual(self.manager.mode, InteractionMode.SELECT)

    def test_add_cut_interaction(self):
        initial_count = len([obj for obj in self.editor.model.objects.values() if isinstance(obj, Cut)])
        self.editor.add_cut()
        new_count = len([obj for obj in self.editor.model.objects.values() if isinstance(obj, Cut)])
        self.assertEqual(new_count, initial_count + 1)