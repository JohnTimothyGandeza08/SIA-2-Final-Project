# components.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt, Signal

class TopNavBar(QWidget):
    page_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        self.setStyleSheet("background-color: #0a0a0a; border-bottom: 1px solid #1a1a1a;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 0, 30, 0)
        layout.setSpacing(20)

        # Page Links
        self.buttons = {}
        for text, icon in [("Home", "🏠"), ("Search", "🔍"), ("Your Library", "📚")]:
            btn = QPushButton(f"{icon}  {text}")
            btn.setObjectName("NavTopBtnActive" if text == "Home" else "NavTopBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, t=text: self.set_active(t))
            layout.addWidget(btn)
            self.buttons[text] = btn

        layout.addStretch()
        self.active_page = "Home"

    def set_active(self, page_name):
        self.active_page = page_name
        for name, btn in self.buttons.items():
            btn.setObjectName("NavTopBtnActive" if name == page_name else "NavTopBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.page_changed.emit(page_name.lower())