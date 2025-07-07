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
    def __init__(self, view, editor: EGEditor):
        self.view = view
        self.scene = view.scene()
        self.editor = editor
        self.mode = InteractionMode.SELECT
        self.selection_box = None
        self.start_pos = None
        self.preview_line = None
        self.start_item = None

    def set_mode(self, mode: InteractionMode):
        self.mode = mode
        self.scene.clearSelection()

    def mouse_press(self, event):
        self.start_pos = self.view.mapToScene(event.position().toPoint())
        items_at_pos = self.scene.items(self.start_pos)
        self.start_item = items_at_pos[0] if items_at_pos else None

        if self.mode == InteractionMode.CREATE_LIGATURE or isinstance(self.start_item, HookItem):
            self.preview_line = QGraphicsLineItem()
            self.preview_line.setPen(QPen(Qt.red, 1.5, Qt.DashLine))
            self.scene.addItem(self.preview_line)
            self.preview_line.setLine(QLineF(self.start_pos, self.start_pos))
            return True
        
        elif self.mode == InteractionMode.SELECT and not any(item.flags() & QGraphicsItem.ItemIsSelectable for item in items_at_pos):
            self.selection_box = QGraphicsRectItem()
            self.selection_box.setPen(QPen(Qt.black, 1, Qt.DashLine))
            self.scene.addItem(self.selection_box)
        
        return False

    def mouse_move(self, event):
        end_pos = self.view.mapToScene(event.position().toPoint())
        if self.preview_line:
            self.preview_line.setLine(QLineF(self.start_pos, end_pos))
            return True
        elif self.selection_box:
            rect = QRectF(self.start_pos, end_pos).normalized()
            self.selection_box.setRect(rect)
            return True
        return False

    def mouse_release(self, event):
        if not self.preview_line:
            # Handle non-ligature-drawing releases
            if self.selection_box:
                # ... selection box logic ...
                self.scene.removeItem(self.selection_box)
                self.selection_box = None
            return

        # --- Ligature Drawing Release Logic ---
        self.scene.removeItem(self.preview_line)
        self.preview_line = None
        end_pos = self.view.mapToScene(event.position().toPoint())
        items_at_end = self.scene.items(end_pos)
        end_item = items_at_end[0] if items_at_end else None

        start_hook = self.start_item if isinstance(self.start_item, HookItem) else None
        end_hook = end_item if isinstance(end_item, HookItem) else None
        target_ligature = end_item if isinstance(end_item, LigatureItem) else None

        if start_hook and end_hook and start_hook != end_hook:
            # Case 1: Hook to Hook
            lig_id = self.editor.connect([(start_hook.owner_id, start_hook.hook_index), (end_hook.owner_id, end_hook.hook_index)])
            self.scene.addItem(LigatureItem(lig_id, [start_hook, end_hook]))
        
        elif start_hook and target_ligature:
            # Case 2: Hook to existing Ligature
            lig_id = target_ligature.ligature_id
            self.editor.connect([(start_hook.owner_id, start_hook.hook_index), *self.editor.model.get_object(lig_id).connections])
            new_attachments = [start_hook] + target_ligature.attachments
            self.scene.removeItem(target_ligature)
            self.scene.addItem(LigatureItem(lig_id, new_attachments))

        elif start_hook:
            # Case 3: Hook to Empty Space
            lig_id = self.editor.add_ligature()
            self.editor.connect([(start_hook.owner_id, start_hook.hook_index)])
            self.scene.addItem(LigatureItem(lig_id, [start_hook, end_pos]))

        elif self.mode == InteractionMode.CREATE_LIGATURE:
            # Case 4: Empty Space to Empty Space
            lig_id = self.editor.add_ligature()
            self.scene.addItem(LigatureItem(lig_id, [self.start_pos, end_pos]))

        self.start_item = None
        if self.mode != InteractionMode.SELECT:
            self.set_mode(InteractionMode.SELECT)