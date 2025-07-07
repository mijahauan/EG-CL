import sys
from PySide6.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene,
                               QMainWindow, QToolBar)
from PySide6.QtGui import QPainter, QAction, QActionGroup
from PySide6.QtCore import Qt

from eg_editor import EGEditor
from eg_model import GraphModel, Cut, Predicate
from interaction_manager import InteractionManager, InteractionMode
from enhanced_graphics_items import EnhancedPredicateItem, EnhancedCutItem, LigatureItem

class EnhancedGraphView(QGraphicsView):
    def __init__(self, scene, editor: EGEditor, parent=None):
        super().__init__(scene, parent)
        self.editor = editor
        self.interaction_manager = InteractionManager(self, self.editor)
        self.setRenderHint(QPainter.Antialiasing)

    def mousePressEvent(self, event):
        handled = self.interaction_manager.mouse_press(event)
        if not handled:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Let the manager handle custom drags first
        handled = self.interaction_manager.mouse_move(event)
        # If not handled, let the default behavior take over for item moving
        if not handled:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.interaction_manager.mouse_release(event)
        super().mouseReleaseEvent(event)

class EnhancedMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.editor = EGEditor()
        self.scene = QGraphicsScene()
        self.view = EnhancedGraphView(self.scene, self.editor, self)
        self.setCentralWidget(self.view)
        
        self.resize(1024, 768)
        self.setWindowTitle("Existential Graphs")

        self.setup_toolbar()
        self.populate_scene()

    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)

        select_action = QAction("Select", self)
        select_action.setCheckable(True)
        select_action.setChecked(True)
        select_action.triggered.connect(lambda: self.view.interaction_manager.set_mode(InteractionMode.SELECT))
        toolbar.addAction(select_action)
        mode_group.addAction(select_action)

        cut_action = QAction("Create Cut", self)
        cut_action.setCheckable(True)
        cut_action.triggered.connect(lambda: self.view.interaction_manager.set_mode(InteractionMode.CREATE_CUT))
        toolbar.addAction(cut_action)
        mode_group.addAction(cut_action)

        predicate_action = QAction("Create Predicate", self)
        predicate_action.setCheckable(True)
        predicate_action.triggered.connect(lambda: self.view.interaction_manager.set_mode(InteractionMode.CREATE_PREDICATE))
        toolbar.addAction(predicate_action)
        mode_group.addAction(predicate_action)

    def populate_scene(self):
        """Adds initial items to the scene for demonstration."""
        p_id = self.editor.add_predicate("Human", 1, parent_id='SA')
        cut_id = self.editor.add_cut(parent_id='SA')
        q_id = self.editor.add_predicate("Mortal", 1, parent_id=cut_id)

        p_item = EnhancedPredicateItem(p_id, "Human", 1, 100, 100)
        cut_item = EnhancedCutItem(cut_id, 250, 50, 200, 200)
        q_item = EnhancedPredicateItem(q_id, "Mortal", 1, 300, 120)

        self.scene.addItem(p_item)
        self.scene.addItem(cut_item)
        self.scene.addItem(q_item)

def main():
    app = QApplication(sys.argv)
    window = EnhancedMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()