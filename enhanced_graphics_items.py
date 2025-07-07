from PySide6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsPathItem
from PySide6.QtGui import QPen, QBrush, QColor, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

class HookItem(QGraphicsEllipseItem):
    """A small, clickable circle representing a predicate's hook."""
    def __init__(self, owner_id, hook_index, x, y, parent=None):
        super().__init__(-4, -4, 8, 8, parent) # Centered ellipse
        self.setPos(x, y)
        self.owner_id = owner_id
        self.hook_index = hook_index
        self.setBrush(QBrush(Qt.gray))
        self.setPen(QPen(Qt.black, 1))

class LigatureItem(QGraphicsPathItem):
    """A QGraphicsItem to visually represent a ligature."""
    def __init__(self, ligature_id, start_item: HookItem, end_item: HookItem, parent=None):
        super().__init__(parent)
        self.ligature_id = ligature_id
        self.start_item = start_item
        self.end_item = end_item
        self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True) # Make ligature selectable
        self.update_path()

    def update_path(self):
        """Updates the path of the ligature based on its connected hooks."""
        path = QPainterPath()
        # Get scene positions of the hooks
        start_pos = self.start_item.scenePos()
        end_pos = self.end_item.scenePos()
        # Map scene positions to this item's coordinate system
        path.moveTo(self.mapFromScene(start_pos))
        path.lineTo(self.mapFromScene(end_pos))
        self.setPath(path)

    def paint(self, painter, option, widget):
        """
        Overridden paint method to ensure the path is always up-to-date
        before drawing, which keeps it attached to moving items.
        """
        self.update_path()
        super().paint(painter, option, widget)


class EnhancedCutItem(QGraphicsEllipseItem):
    """A QGraphicsItem representing a Cut, enabling movement."""
    def __init__(self, cut_id, x, y, width, height, parent=None):
        super().__init__(x, y, width, height, parent)
        self.cut_id = cut_id
        self.setPen(QPen(Qt.black, 2))
        self.setBrush(QBrush(Qt.transparent))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

class EnhancedPredicateItem(QGraphicsItem):
    """A QGraphicsItem for a Predicate, with visible hooks."""
    def __init__(self, predicate_id, label, hook_count, x, y, parent=None):
        super().__init__(parent)
        self.predicate_id = predicate_id
        self.setPos(x, y)
        
        self.text = QGraphicsTextItem(label, self)
        self.hooks = {} # hook_index -> HookItem
        
        text_width = self.text.boundingRect().width()
        for i in range(1, hook_count + 1):
            hook_x = (i / (hook_count + 1)) * text_width
            hook_y = self.text.boundingRect().height() + 5
            hook = HookItem(predicate_id, i, hook_x, hook_y, self)
            self.hooks[i] = hook

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def boundingRect(self):
        return self.childrenBoundingRect()

    def paint(self, painter, option, widget):
        pass