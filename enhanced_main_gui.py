import sys
from PySide6.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene,
                               QMainWindow, QToolBar)
from PySide6.QtGui import QPainter, QAction, QActionGroup
from PySide6.QtCore import Qt

from eg_editor import EGEditor
from interaction_manager import InteractionManager, InteractionMode
from enhanced_graphics_items import EnhancedPredicateItem, EnhancedCutItem, LigatureItem

class EnhancedGraphView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.interaction_manager = None
        self.setRenderHint(QPainter.Antialiasing)

    def set_manager(self, manager):
        self.interaction_manager = manager

    def mousePressEvent(self, event):
        if self.interaction_manager and self.interaction_manager.mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.interaction_manager and self.interaction_manager.mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.interaction_manager:
            self.interaction_manager.mouse_release(event)
        super().mouseReleaseEvent(event)

class EnhancedMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.editor = EGEditor()
        self.scene = QGraphicsScene()
        self.item_map = {}
        
        self.view = EnhancedGraphView(self.scene, self)
        self.setCentralWidget(self.view)
        
        manager = InteractionManager(self.view, self.editor, self.on_item_created)
        self.view.set_manager(manager)
        
        self.resize(1024, 768)
        self.setWindowTitle("Existential Graphs")
        self.setup_toolbar()
        self.populate_scene()

    def add_item_to_scene(self, logical_id, item):
        self.scene.addItem(item)
        self.item_map[logical_id] = item

    def on_item_created(self, item_type, **kwargs):
        if item_type == 'cut':
            rect = kwargs.get('rect')
            cut_id = self.editor.add_cut()
            new_item = EnhancedCutItem(cut_id, rect.x(), rect.y(), rect.width(), rect.height())
            self.add_item_to_scene(cut_id, new_item)
        
        elif item_type == 'predicate':
            pos = kwargs.get('pos')
            pred_id = self.editor.add_predicate(kwargs.get('label', 'P'), kwargs.get('hooks', 1))
            new_item = EnhancedPredicateItem(pred_id, kwargs.get('label', 'P'), kwargs.get('hooks', 1), pos.x(), pos.y())
            self.add_item_to_scene(pred_id, new_item)
            
        elif item_type == 'ligature-connect-hooks':
            start_hook = kwargs.get('start_hook'); end_hook = kwargs.get('end_hook')
            ligature_id = self.editor.connect([(start_hook.owner_id, start_hook.hook_index), (end_hook.owner_id, end_hook.hook_index)])
            new_ligature_item = LigatureItem(ligature_id, [start_hook, end_hook])
            self.add_item_to_scene(ligature_id, new_ligature_item)
            
        elif item_type == 'ligature-detached':
            start_pos = kwargs.get('start_pos'); end_pos = kwargs.get('end_pos')
            ligature_id = self.editor.add_ligature()
            new_ligature_item = LigatureItem(ligature_id, [start_pos, end_pos])
            self.add_item_to_scene(ligature_id, new_ligature_item)

    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)
        actions = [
            ("Select", InteractionMode.SELECT, True),
            ("Create Cut", InteractionMode.CREATE_CUT, False),
            ("Create Predicate", InteractionMode.CREATE_PREDICATE, False),
            ("Create Ligature", InteractionMode.CREATE_LIGATURE, False)
        ]
        for name, mode, checked in actions:
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(checked)
            action.triggered.connect(lambda m=mode: self.view.interaction_manager.set_mode(m))
            toolbar.addAction(action)
            mode_group.addAction(action)

    def populate_scene(self):
        p_id = self.editor.add_predicate("Human", 1)
        cut_id = self.editor.add_cut()
        q_id = self.editor.add_predicate("Mortal", 1, parent_id=cut_id)
        p_item = EnhancedPredicateItem(p_id, "Human", 1, 100, 100)
        cut_item = EnhancedCutItem(cut_id, 250, 50, 200, 200)
        q_item = EnhancedPredicateItem(q_id, "Mortal", 1, 300, 120)
        self.add_item_to_scene(p_id, p_item)
        self.add_item_to_scene(cut_id, cut_item)
        self.add_item_to_scene(q_id, q_item)

def main():
    app = QApplication(sys.argv)
    window = EnhancedMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()