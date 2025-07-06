# main_gui.py
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                               QLabel, QPushButton, QHBoxLayout, QInputDialog,
                               QGraphicsView, QGraphicsScene, QGraphicsRectItem,
                               QGraphicsTextItem, QGraphicsPathItem, QGraphicsItem)
## MODIFIED ##
# Added QRectF to the import list
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QFont, QBrush, QPen, QColor, QPainterPath

from eg_model import ExistentialGraph, GraphObjectType, Node, Hyperedge
from eg_logic import EGEditor, ClifTranslator
from eg_renderer import Renderer

## MODIFIED ##
# The __init__ method now correctly expects a QRectF object.
class CutItem(QGraphicsRectItem):
    """A selectable, movable QGraphicsItem to represent a Cut."""
    def __init__(self, node_id, rect: QRectF, graph_model):
        super().__init__(rect)
        self.node_id = node_id
        self.graph_model = graph_model
        
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True) 
        
        level = self.graph_model.get_nesting_level(self.node_id)
        if level % 2 != 0:
            self.setBrush(QBrush(QColor("#e9e9e9")))
        else:
            self.setBrush(QBrush(QColor("#ffffff")))
            
    def paint(self, painter, option, widget):
        """Override paint to draw a highlight when selected."""
        original_pen = self.pen()
        if self.isSelected():
            highlight_pen = QPen(QColor("red"), 2, Qt.SolidLine)
            self.setPen(highlight_pen)
        
        super().paint(painter, option, widget)
        self.setPen(original_pen)

class PredicateItem(QGraphicsTextItem):
    """A selectable QGraphicsItem to represent a Predicate."""
    def __init__(self, node_id, text):
        super().__init__(text)
        self.node_id = node_id
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def paint(self, painter, option, widget):
        """Override paint to draw a highlight when selected."""
        super().paint(painter, option, widget)
        if self.isSelected():
            pen = QPen(QColor("red"), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.boundingRect())


class MainWindow(QMainWindow):
    """The main application window, now using QGraphicsView."""
    
    def __init__(self):
        super().__init__()
        
        self.graph = ExistentialGraph()
        self.editor = EGEditor(self.graph)
        self.renderer = Renderer(self.graph)
        
        self.setWindowTitle("Existential Graphs Application")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
        toolbar_layout = QHBoxLayout()
        self.add_predicate_button = QPushButton("Add Predicate")
        self.add_predicate_button.clicked.connect(self.on_add_predicate)
        toolbar_layout.addWidget(self.add_predicate_button)
        self.add_cut_button = QPushButton("Add Cut")
        self.add_cut_button.clicked.connect(self.on_add_cut)
        toolbar_layout.addWidget(self.add_cut_button)
        toolbar_layout.addStretch()

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor("white")))
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.selected_item_id = None
        
        self.linear_form_label = QLabel("Linear form will appear here.")
        self.linear_form_label.setFont(QFont("Courier New", 12))
        self.linear_form_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-top: 1px solid #ccc;")
        self.linear_form_label.setAlignment(Qt.AlignCenter)
        
        self.main_layout.addLayout(toolbar_layout)
        self.main_layout.addWidget(self.view, 5)
        self.main_layout.addWidget(self.linear_form_label, 1)
        
        self.create_initial_graph()
        self.refresh_display()

    def refresh_display(self):
        print("INFO: Refreshing display...")
        self.scene.clear()
        
        self.scene_items = {} 

        self.renderer._calculate_layout(self.graph.root_id)
        
        self._draw_node_on_scene(self.graph.root_id, 0, 0)
        
        self._draw_ligatures_on_scene()

        translator = ClifTranslator(self.graph)
        clif_string = translator.translate()
        self.linear_form_label.setText(clif_string)
        print("INFO: Display updated.")

    def _draw_node_on_scene(self, node_id, parent_abs_x, parent_abs_y):
        node = self.graph.get_object(node_id)
        node_layout = self.renderer.layout.get(node_id, {})
        
        abs_x = parent_abs_x + node_layout.get("x", 0)
        abs_y = parent_abs_y + node_layout.get("y", 0)

        item = None
        if node.node_type == GraphObjectType.CUT:
            if self.graph.get_parent(node_id):
                ## MODIFIED ##
                # Create a QRectF object instead of a tuple of points.
                width = node_layout.get("width", 0)
                height = node_layout.get("height", 0)
                rect = QRectF(0, 0, width, height)
                # Pass the single QRectF object to the constructor.
                item = CutItem(node_id, rect, self.graph)
        
        elif node.node_type == GraphObjectType.PREDICATE:
            text = node.properties.get("name", "")
            item = PredicateItem(node_id, text)
            item.setFont(QFont(self.renderer.config['font_family'], self.renderer.config['font_size']))
            text_x_offset = self.renderer.config['predicate_padding_x']
            text_y_offset = self.renderer.config['predicate_padding_y']
            abs_x += text_x_offset
            abs_y += text_y_offset
        
        if item:
            item.setPos(abs_x, abs_y)
            self.scene.addItem(item)
            self.scene_items[node_id] = item
        
        if node.node_type == GraphObjectType.CUT:
            for content_id in node.contents:
                content_obj = self.graph.get_object(content_id)
                if isinstance(content_obj, Node):
                    self._draw_node_on_scene(content_id, abs_x, abs_y)
    
    def _draw_ligatures_on_scene(self):
        all_ligatures = [obj for obj in self.graph.objects.values() if isinstance(obj, Hyperedge)]
        for lig in all_ligatures:
            if len(lig.endpoints) < 1: continue

            points = []
            for ep in lig.endpoints:
                node = self.graph.get_object(ep['node_id'])
                node_item = self.scene_items.get(node.id)
                if not node_item: continue

                num_hooks = node.properties.get("arity", 0)
                denominator = num_hooks + 1 if num_hooks > 0 else 1
                hook_rel_x = (node_item.boundingRect().width() * (ep['hook_index'] + 1) / denominator)
                hook_rel_y = node_item.boundingRect().height()

                abs_hook_pos = node_item.mapToScene(QPointF(hook_rel_x, hook_rel_y))
                points.append(abs_hook_pos)

            if len(points) >= 2:
                path = QPainterPath()
                path.moveTo(points[0])
                for i in range(1, len(points)):
                    path.lineTo(points[i])
                item = QGraphicsPathItem(path)
                item.setPen(QPen(QColor("black"), 2))
                self.scene.addItem(item)
            elif len(points) == 1:
                path = QPainterPath()
                p1 = points[0]
                p2 = QPointF(p1.x(), p1.y() + self.renderer.config['line_stub_length'])
                path.moveTo(p1)
                path.lineTo(p2)
                item = QGraphicsPathItem(path)
                item.setPen(QPen(QColor("black"), 2))
                self.scene.addItem(item)

    def on_add_predicate(self):
        parent_id = self.graph.root_id
        name, ok = QInputDialog.getText(self, "Add Predicate", "Enter Predicate Name (e.g., 'Man', 'Mortal'):")
        if ok and name.strip():
            arity, ok = QInputDialog.getInt(self, "Add Predicate", "Enter Arity (number of hooks):", 
                                            value=1, minValue=0, maxValue=10)
            if ok:
                self.editor.add_predicate(name.strip(), arity, parent_id)
                self.refresh_display()

    def on_add_cut(self):
        parent_id = self.graph.root_id
        self.editor.add_cut(parent_id)
        self.refresh_display()
    
    def create_initial_graph(self):
        soa_id = self.graph.root_id
        cut_id, _ = self.editor.add_cut(soa_id)
        p_cat_id, _ = self.editor.add_predicate("Cat", 1, cut_id, p_type='relation')
        endpoint = {"node_id": p_cat_id, "hook_index": 0}
        self.editor.sever_endpoint(endpoint)

    def on_selection_changed(self):
        selected_items = self.scene.selectedItems()
        if selected_items:
            # Check if the selected item is one of our custom types with a node_id
            if hasattr(selected_items[0], 'node_id'):
                self.selected_item_id = selected_items[0].node_id
                selected_node = self.graph.get_object(self.selected_item_id)
                print(f"INFO: Selected item with ID: {self.selected_item_id} (Type: {selected_node.node_type.name})")
        else:
            self.selected_item_id = None
            print("INFO: Selection cleared.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())