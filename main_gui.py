# main_gui.py
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                               QLabel, QPushButton, QHBoxLayout, QInputDialog)
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QFont

from eg_model import ExistentialGraph
from eg_logic import EGEditor, ClifTranslator
from eg_renderer import Renderer

class MainWindow(QMainWindow):
    """The main application window with interactive controls."""
    
    def __init__(self):
        super().__init__()
        
        # -- Initialize Backend Components --
        self.graph = ExistentialGraph()
        self.editor = EGEditor(self.graph)
        self.renderer = Renderer(self.graph)
        
        # -- Window Setup --
        self.setWindowTitle("Existential Graphs Application")
        self.setGeometry(100, 100, 800, 600)
        
        # -- Main Layout --
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
        # -- Toolbar for Controls --
        toolbar_layout = QHBoxLayout()
        self.add_predicate_button = QPushButton("Add Predicate")
        self.add_predicate_button.clicked.connect(self.on_add_predicate)
        toolbar_layout.addWidget(self.add_predicate_button)
        self.add_cut_button = QPushButton("Add Cut")
        self.add_cut_button.clicked.connect(self.on_add_cut)
        toolbar_layout.addWidget(self.add_cut_button)
        toolbar_layout.addStretch()

        # -- SVG Display Widget --
        self.svg_widget = QSvgWidget()
        self.svg_widget.setStyleSheet("background-color: white;")
        
        # -- Linear Form Display Label --
        self.linear_form_label = QLabel("Linear form will appear here.")
        ## MODIFIED ##
        # Using a more common font name to avoid warnings.
        # Other options include "Monaco", "Consolas", or generic "Monospace".
        self.linear_form_label.setFont(QFont("Courier New", 12))
        self.linear_form_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-top: 1px solid #ccc;")
        self.linear_form_label.setAlignment(Qt.AlignCenter)
        
        # -- Add all widgets to the main layout --
        self.main_layout.addLayout(toolbar_layout)
        self.main_layout.addWidget(self.svg_widget, 5)
        self.main_layout.addWidget(self.linear_form_label, 1)
        
        # -- Initial Render --
        self.create_initial_graph()
        self.refresh_display()

    def create_initial_graph(self):
        """Creates the initial sample graph when the application starts."""
        soa_id = self.graph.root_id
        cut_id, _ = self.editor.add_cut(soa_id)
        p_cat_id, _ = self.editor.add_predicate("Cat", 1, cut_id, p_type='relation')
        endpoint = {"node_id": p_cat_id, "hook_index": 0}
        self.editor.sever_endpoint(endpoint)

    def refresh_display(self):
        """
        Rerenders the current state of the graph and updates the display widgets.
        """
        print("INFO: Refreshing display...")
        
        renderer = Renderer(self.graph)
        svg_string = renderer.to_svg()
        svg_bytes = QByteArray(svg_string.encode('utf-8'))
        self.svg_widget.load(svg_bytes)
        
        translator = ClifTranslator(self.graph)
        clif_string = translator.translate()
        self.linear_form_label.setText(clif_string)
        print(f"INFO: Display updated. CLIF: {clif_string}")

    def on_add_predicate(self):
        """
        Event handler for the 'Add Predicate' button.
        """
        parent_id = self.graph.root_id
        
        name, ok = QInputDialog.getText(self, "Add Predicate", "Enter Predicate Name (e.g., 'Man', 'Mortal'):")
        
        if ok and name.strip():
            ## MODIFIED ##
            # Corrected the keyword arguments from 'min'/'max' to 'minValue'/'maxValue'.
            arity, ok = QInputDialog.getInt(self, "Add Predicate", "Enter Arity (number of hooks):", 
                                            value=1, minValue=0, maxValue=10)
            if ok:
                self.editor.add_predicate(name.strip(), arity, parent_id)
                self.refresh_display()

    def on_add_cut(self):
        """
        Event handler for the 'Add Cut' button.
        """
        parent_id = self.graph.root_id
        self.editor.add_cut(parent_id)
        self.refresh_display()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())