from PySide6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsPathItem
from PySide6.QtGui import QPen, QBrush, QPainterPath
from PySide6.QtCore import Qt, QPointF

class HookItem(QGraphicsEllipseItem):
    def __init__(self, owner_id, hook_index, x, y, parent=None):
        super().__init__(-4, -4, 8, 8, parent)
        self.setPos(x, y)
        self.owner_id = owner_id
        self.hook_index = hook_index
        self.setBrush(QBrush(Qt.gray)); self.setPen(QPen(Qt.black, 1))

class LigatureItem(QGraphicsPathItem):
    def __init__(self, ligature_id, attachments, parent=None):
        super().__init__(parent)
        self.ligature_id = ligature_id; self.attachments = attachments
        self.setPen(QPen(Qt.black, 2)); self.setZValue(1)
    def get_pos_of_attachment(self, attachment):
        if isinstance(attachment, QGraphicsItem): return attachment.scenePos()
        elif isinstance(attachment, QPointF): return attachment
        return QPointF()
    def update_path(self):
        if len(self.attachments) < 2: self.setPath(QPainterPath()); return
        path = QPainterPath(); start_pos = self.get_pos_of_attachment(self.attachments[0])
        path.moveTo(start_pos)
        for attachment in self.attachments[1:]:
            path.lineTo(self.get_pos_of_attachment(attachment))
        self.setPath(path)
    def paint(self, painter, option, widget):
        self.update_path(); super().paint(painter, option, widget)

class CutItem(QGraphicsEllipseItem):
    def __init__(self, cut_id, x, y, width, height, parent=None):
        super().__init__(x, y, width, height, parent)
        self.cut_id = cut_id
        self.setPen(QPen(Qt.black, 2)); self.setBrush(QBrush(Qt.transparent))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setZValue(0)

class PredicateItem(QGraphicsItem):
    def __init__(self, predicate_id, label, hook_count, x, y, parent=None):
        super().__init__(parent)
        self.predicate_id = predicate_id; self.setPos(x, y)
        self.text = QGraphicsTextItem(label, self); self.hooks = {}
        text_rect = self.text.boundingRect()
        for i in range(1, hook_count + 1):
            hook_x = (i / (hook_count + 1)) * text_rect.width()
            hook_y = text_rect.height()
            self.hooks[i] = HookItem(predicate_id, i, hook_x, hook_y, self)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setZValue(1)
    def boundingRect(self):
        return self.childrenBoundingRect()
    def paint(self, painter, option, widget):
        pass