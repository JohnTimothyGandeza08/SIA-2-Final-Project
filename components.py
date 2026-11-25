# components.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class Sidebar(QWidget):
    page_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        layout.setSpacing(10)

        # Logo
        logo_layout = QHBoxLayout()
        logo_dot = QLabel("●")
        logo_dot.setStyleSheet("color: #ff4444; font-size: 20px;")
        logo_text = QLabel("Aura")
        logo_text.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        logo_layout.addWidget(logo_dot)
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)
        layout.addSpacing(30)

        # Main Nav
        for text, icon in [("Home", "🏠"), ("Search", "🔍"), ("Your Library", "📚")]:
            btn = QLabel(f"{icon}   {text}")
            btn.setObjectName("NavLabelActive" if text == "Your Library" else "NavLabel")
            btn.setCursor(Qt.PointingHandCursor)
            btn.mousePressEvent = lambda event, t=text: self.page_changed.emit(t.lower())
            layout.addWidget(btn)

        layout.addSpacing(30)
        curated_lbl = QLabel("CURATED")
        curated_lbl.setObjectName("SectionTitle")
        layout.addWidget(curated_lbl)
        layout.addSpacing(10)

        # Curated Nav
        for text, icon in [("Playlists", "🎵"), ("Favorites", "❤️")]:
            btn = QLabel(f"{icon}   {text}")
            btn.setObjectName("NavLabel")
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)

        layout.addStretch()


class TrackRow(QWidget):
    clicked = Signal(object)

    def __init__(self, index, data, is_active=False):
        super().__init__()
        self.setObjectName("TrackRowWidget")
        self.setFixedHeight(64)
        self.setCursor(Qt.PointingHandCursor)
        self.track_data = data

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(15)

        # Index / Play Icon
        if is_active:
            num = QLabel("⏸")  # Active indicator
            num.setObjectName("TrackIndexActive")
        else:
            num = QLabel(f"{index:02d}")
            num.setObjectName("TrackIndex")
        num.setFixedWidth(30)
        num.setAlignment(Qt.AlignCenter)

        # Album Art
        art = QLabel()
        art.setFixedSize(40, 40)
        art.setStyleSheet("background-color: #333; border-radius: 4px;")

        # Title & Artist
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        title_layout.setAlignment(Qt.AlignVCenter)

        title = QLabel(data.title)
        title.setObjectName("TrackTitleActive" if is_active else "TrackTitle")
        sub = QLabel(data.album)
        sub.setObjectName("TrackSub")
        title_layout.addWidget(title)
        title_layout.addWidget(sub)

        # Time
        length = QLabel(data.length)
        length.setObjectName("TrackTime")
        length.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        length.setFixedWidth(60)

        layout.addWidget(num)
        layout.addWidget(art)
        layout.addWidget(title_container, 1)
        layout.addWidget(length)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.track_data)
        super().mousePressEvent(event)