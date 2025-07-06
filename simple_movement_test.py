#!/usr/bin/env python3
"""
Simple test to verify that itemChange is being called and working correctly.
"""

import sys
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QMainWindow, QGraphicsTextItem
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsItem

class TestPredicateItem(QGraphicsTextItem):
    """Simple test predicate item to verify itemChange behavior."""
    
    def __init__(self, text: str):
        super().__init__(text)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        print(f"Created test item: {text}")
        print(f"ItemIsMovable flag: {self.flags() & QGraphicsItem.ItemIsMovable}")
        
    def itemChange(self, change, value):
        """Test itemChange method."""
        if change == QGraphicsItem.ItemPositionChange:
            print(f"TEST: Position changing to {value}")
            
            # Simple validation test - prevent moving beyond x=300
            if value.x() > 300:
                print("TEST: Movement rejected - beyond x=300")
                return QPointF(300, value.y())
                
        elif change == QGraphicsItem.ItemPositionHasChanged:
            print(f"TEST: Position changed to {value}")
            
        return super().itemChange(change, value)

class SimpleTestWindow(QMainWindow):
    """Simple test window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Movement Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Create scene and view
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.setCentralWidget(self.view)
        
        # Add test item
        test_item = TestPredicateItem("Test Predicate")
        test_item.setPos(100, 100)
        self.scene.addItem(test_item)
        
        print("Simple test setup complete.")
        print("Try dragging the 'Test Predicate' item.")
        print("Movement should be prevented when x > 300.")

def main():
    """Run the simple test."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("Simple Movement Test")
    print("=" * 30)
    
    window = SimpleTestWindow()
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

