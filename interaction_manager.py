from PySide6.QtCore import QPointF, Qt, QRectF, QLineF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsLineItem
from PySide6.QtGui import QPen, QBrush, QColor, QPainterPath
from enum import Enum
from eg_model import GraphModel, Cut, Predicate
from eg_editor import EGEditor
from enhanced_graphics_items import HookItem, LigatureItem

class InteractionMode(Enum):
    SELECT = 1
    CREATE_CUT = 2
    CREATE_PREDICATE = 3
    DRAW_LIGATURE = 4

class InteractionManager:
    """Manages user interactions with the graphics scene."""
    def __init__(self, view, editor: EGEditor):
        self.view = view
        self.scene = view.scene()
        self.editor = editor
        self.mode = InteractionMode.SELECT
        self.selection_box = None
        self.start_pos = None
        
        self.ligature_preview = None
        self.start_hook = None

    def set_mode(self, mode: InteractionMode):
        self.mode = mode
        self.scene.clearSelection()

    def mouse_press(self, event):
        self.start_pos = self.view.mapToScene(event.position().toPoint())
        items_at_pos = self.scene.items(self.start_pos)
        top_item = items_at_pos[0] if items_at_pos else None

        if isinstance(top_item, HookItem):
            self.mode = InteractionMode.DRAW_LIGATURE
            self.start_hook = top_item
            self.ligature_preview = QGraphicsLineItem()
            self.ligature_preview.setPen(QPen(Qt.red, 1.5, Qt.DashLine))
            self.scene.addItem(self.ligature_preview)
            self.ligature_preview.setLine(QLineF(self.start_pos, self.start_pos))
            return True
        
        elif self.mode == InteractionMode.SELECT and not any(item.flags() & QGraphicsItem.ItemIsSelectable for item in items_at_pos):
            self.selection_box = QGraphicsRectItem()
            self.selection_box.setPen(QPen(Qt.black, 1, Qt.DashLine))
            self.scene.addItem(self.selection_box)
        
        return False

    def mouse_move(self, event):
        end_pos = self.view.mapToScene(event.position().toPoint())
        
        if self.ligature_preview:
            self.ligature_preview.setLine(QLineF(self.start_pos, end_pos))
            return True # Event handled
            
        elif self.selection_box:
            rect = QRectF(self.start_pos, end_pos).normalized()
            self.selection_box.setRect(rect)
            return True # Event handled
            
        return False # Event not handled, pass to default

    def mouse_release(self, event):
        end_pos = self.view.mapToScene(event.position().toPoint())
        
        if self.ligature_preview:
            self.scene.removeItem(self.ligature_preview)
            self.ligature_preview = None
            
            items_at_end = self.scene.items(end_pos)
            end_hook = next((item for item in items_at_end if isinstance(item, HookItem)), None)

            if end_hook and self.start_hook and end_hook != self.start_hook:
                ligature_id = self.editor.connect([
                    (self.start_hook.owner_id, self.start_hook.hook_index),
                    (end_hook.owner_id, end_hook.hook_index)
                ])
                new_ligature_item = LigatureItem(ligature_id, self.start_hook, end_hook)
                self.scene.addItem(new_ligature_item)
                
            self.start_hook = None
            self.mode = InteractionMode.SELECT

        elif self.selection_box:
            selector_path = QPainterPath()
            selector_path.addRect(self.selection_box.rect())
            self.scene.setSelectionArea(selector_path)
            self.scene.removeItem(self.selection_box)
            self.selection_box = None
        
        elif self.mode == InteractionMode.CREATE_CUT:
            rect = QRectF(self.start_pos, end_pos).normalized()
            if rect.width() > 5 and rect.height() > 5:
                cut_id = self.editor.add_cut(parent_id='SA')
                print(f"Logic: Created Cut {cut_id} in model.")
        
        self.start_pos = None