from PySide6.QtCore import QPointF, Qt, QRectF, QLineF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsLineItem
from PySide6.QtGui import QPen, QBrush, QColor, QPainterPath
from enum import Enum
from eg_model import GraphModel, Cut, Predicate
from eg_editor import EGEditor
from enhanced_graphics_items import HookItem, LigatureItem, EnhancedCutItem

class InteractionMode(Enum):
    SELECT = 1
    CREATE_CUT = 2
    CREATE_PREDICATE = 3
    CREATE_LIGATURE = 4

class InteractionManager:
    """Manages user interactions with the graphics scene in a state-driven way."""
    def __init__(self, view, editor: EGEditor, on_item_created):
        self.view = view
        self.scene = view.scene()
        self.editor = editor
        self.on_item_created = on_item_created
        self.mode = InteractionMode.SELECT
        
        # State for an action in progress
        self.preview_item = None
        self.start_pos = None
        self.start_hook = None

    def set_mode(self, mode: InteractionMode):
        self.mode = mode
        self.scene.clearSelection()

    def mouse_press(self, event):
        self.start_pos = self.view.mapToScene(event.position().toPoint())
        items_at_pos = self.scene.items(self.start_pos)
        top_item = items_at_pos[0] if items_at_pos else None

        # A hook click can start a ligature, regardless of the current mode.
        if isinstance(top_item, HookItem):
            self.start_hook = top_item
            self.preview_item = QGraphicsLineItem()
            self.preview_item.setPen(QPen(Qt.red, 1.5, Qt.DashLine))
            self.scene.addItem(self.preview_item)
            self.preview_item.setLine(QLineF(self.start_pos, self.start_pos))
            return True

        if self.mode == InteractionMode.CREATE_CUT:
            self.preview_item = QGraphicsRectItem()
            self.preview_item.setPen(QPen(Qt.blue, 1, Qt.DashLine))
            self.scene.addItem(self.preview_item)
            return True
        
        elif self.mode == InteractionMode.CREATE_LIGATURE:
            self.preview_item = QGraphicsLineItem()
            self.preview_item.setPen(QPen(Qt.blue, 1.5, Qt.DashLine))
            self.scene.addItem(self.preview_item)
            self.preview_item.setLine(QLineF(self.start_pos, self.start_pos))
            return True
            
        elif self.mode == InteractionMode.SELECT and top_item is None:
            self.preview_item = QGraphicsRectItem()
            self.preview_item.setPen(QPen(Qt.black, 1, Qt.DashLine))
            self.scene.addItem(self.preview_item)
            return True

        return False

    def mouse_move(self, event):
        if not self.preview_item: return False
        
        end_pos = self.view.mapToScene(event.position().toPoint())
        if isinstance(self.preview_item, QGraphicsLineItem):
            self.preview_item.setLine(QLineF(self.start_pos, end_pos))
        elif isinstance(self.preview_item, QGraphicsRectItem):
            self.preview_item.setRect(QRectF(self.start_pos, end_pos).normalized())
        return True

    def mouse_release(self, event):
        rect = None
        if self.preview_item and isinstance(self.preview_item, QGraphicsRectItem):
            rect = self.preview_item.rect()

        if self.preview_item:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None

        end_pos = self.view.mapToScene(event.position().toPoint())
        items_at_end = self.scene.items(end_pos)
        end_item = items_at_end[0] if items_at_end else None
        
        if self.start_hook:
            end_hook = end_item if isinstance(end_item, HookItem) else None
            if end_hook and self.start_hook != end_hook:
                self.on_item_created('ligature-connect-hooks', start_hook=self.start_hook, end_hook=end_hook)
        
        elif self.mode == InteractionMode.CREATE_CUT and rect and rect.width() > 5:
            self.on_item_created('cut', rect=rect)
            self.set_mode(InteractionMode.SELECT)
            
        elif self.mode == InteractionMode.CREATE_LIGATURE and self.start_pos != end_pos:
            self.on_item_created('ligature-detached', start_pos=self.start_pos, end_pos=end_pos)
            self.set_mode(InteractionMode.SELECT)
            
        elif self.mode == InteractionMode.CREATE_PREDICATE:
            self.on_item_created('predicate', pos=end_pos, label="P", hooks=1)
            self.set_mode(InteractionMode.SELECT)
        
        elif self.mode == InteractionMode.SELECT and rect:
            path = QPainterPath(); path.addRect(rect)
            self.scene.setSelectionArea(path)

        self.start_pos = None
        self.start_hook = None