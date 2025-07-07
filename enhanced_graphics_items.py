from PySide6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsPathItem
from PySide6.QtGui import QPen, QBrush, QColor, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

class HookItem(QGraphicsEllipseItem):
    """A small, clickable circle representing a predicate's hook."""
    def __init__(self, owner_id, hook_index, x, y, parent=None):
        super().__init__(-4, -4, 8, 8, parent)
        self.setPos(x, y)
        self.owner_id = owner_id
        self.hook_index = hook_index
        self.setBrush(QBrush(Qt.gray))
        self.setPen(QPen(Qt.black, 1))

class LigatureItem(QGraphicsPathItem):
    """A flexible QGraphicsItem to visually represent a ligature."""
    def __init__(self, ligature_id, attachments, parent=None):
        super().__init__(parent)
        self.ligature_id = ligature_id
        # attachments can be a mix of HookItems and QPointFs
        self.attachments = attachments
        self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.update_path()

    def get_pos_of_attachment(self, attachment):
        """Helper to get the scene position of any attachment type."""
        if isinstance(attachment, HookItem):
            return attachment.scenePos()
        elif isinstance(attachment, QPointF):
            return attachment
        return QPointF()

    def update_path(self):
        """Updates the path of the ligature based on its attachments."""
        if len(self.attachments) < 2:
            self.setPath(QPainterPath())
            return
            
        path = QPainterPath()
        # Start the path at the first attachment
        start_pos = self.get_pos_of_attachment(self.attachments[0])
        path.moveTo(self.mapFromScene(start_pos))
        
        # Draw lines to all subsequent attachments
        for attachment in self.attachments[1:]:
            pos = self.get_pos_of_attachment(attachment)
            path.lineTo(self.mapFromScene(pos))
        self.setPath(path)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            move_delta = value - self.pos()
            # Move any attached predicates
            for attachment in self.attachments:
                if isinstance(attachment, HookItem) and attachment.parentItem():
                    # Use a flag to avoid recursive moves
                    if not hasattr(attachment.parentItem(), '_is_moving'):
                        attachment.parentItem()._is_moving = True
                        attachment.parentItem().moveBy(move_delta.x(), move_delta.y())
                        del attachment.parentItem()._is_moving
            # Also move any free points
            for i, attachment in enumerate(self.attachments):
                if isinstance(attachment, QPointF):
                    self.attachments[i] = attachment + move_delta

        return super().itemChange(change, value)

    def paint(self, painter, option, widget):
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
        self.hooks = {}
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