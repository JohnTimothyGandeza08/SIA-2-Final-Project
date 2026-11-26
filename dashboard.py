# dashboard.py
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame,
    QSlider, QGridLayout, QStackedWidget
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPolygonF, QBrush, QPixmap

from theme import DARK_THEME

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pulse")
        self.resize(1100, 800)
        self.setStyleSheet(DARK_THEME)

        main_widget = QWidget()
        main_widget.setObjectName("MainContainer")
        self.setCentralWidget(main_widget)
        outer_layout = QVBoxLayout(main_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # --- 1. TOP HEADER ---
        header = QWidget()
        header.setObjectName("TopHeader")
        header.setFixedHeight(64)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(30, 0, 30, 0)
        
        # Left: Logo
        logo_box = QHBoxLayout()
        logo_icon = QLabel("▶")
        logo_icon.setStyleSheet("background: #0055ff; color: white; border-radius: 4px; padding: 2px 6px; font-size: 12px;")
        logo_text = QLabel("Pulse")
        logo_text.setStyleSheet("color: white; font-weight: bold; font-size: 16px; margin-left: 5px;")
        logo_box.addWidget(logo_icon)
        logo_box.addWidget(logo_text)
        
        # Center: Segmented Control 
        seg_widget = QWidget()
        seg_widget.setObjectName("SegmentedControl")
        seg_widget.setFixedSize(240, 34) 
        
        seg_layout = QHBoxLayout(seg_widget)
        seg_layout.setContentsMargins(4, 4, 4, 4)
        seg_layout.setSpacing(0)
        
        for i, text in enumerate(["Music", "Video", "Games"]):
            btn = QPushButton(text)
            btn.setObjectName("SegBtnActive" if i == 0 else "SegBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedWidth(77) 
            seg_layout.addWidget(btn)

        # Right: Search + Profile
        search = QLineEdit()
        search.setObjectName("SearchBar")
        search.setPlaceholderText("🔍 Search catalog...")
        search.setFixedSize(240, 30)

        profile = QLabel("J")
        profile.setFixedSize(30, 30)
        profile.setAlignment(Qt.AlignCenter)
        profile.setStyleSheet("background: white; color: black; border-radius: 15px; font-weight: bold; font-size: 12px;")

        h_layout.addLayout(logo_box)
        h_layout.addStretch()
        h_layout.addWidget(seg_widget)
        h_layout.addStretch()
        h_layout.addWidget(search)
        h_layout.addWidget(profile)

        # --- 2. NAVBAR ---
        navbar = QWidget()
        navbar.setObjectName("TopNavBar")
        navbar.setFixedHeight(56)
        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(30, 0, 30, 0)
        nav_layout.setSpacing(15)
        
        self.nav_buttons = []
        # Store the buttons so we can change their active state later
        nav_items = [("🏠  Home", 0), ("🔍  Search", 1), ("📚  Your Library", 2)]
        
        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("NavTopBtnActive" if index == 0 else "NavTopBtn")
            btn.setCursor(Qt.PointingHandCursor)
            # Connect button click to switch pages
            btn.clicked.connect(lambda checked, i=index: self.set_page(i))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            
        nav_layout.addStretch()

        # --- 3. STACKED WIDGET ---
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.build_home_page())      # Index 0
        self.stacked_widget.addWidget(self.build_search_page())    # Index 1
        self.stacked_widget.addWidget(self.build_library_page())   # Index 2

        # --- 4. ASSEMBLE ---
        outer_layout.addWidget(header)
        outer_layout.addWidget(navbar)
        outer_layout.addWidget(self.stacked_widget, 1)
        outer_layout.addWidget(self.create_player_bar())

    # --- PAGE SWITCHING LOGIC ---
    def set_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        # Update button styles (Active vs Inactive)
        for i, btn in enumerate(self.nav_buttons):
            btn.setObjectName("NavTopBtnActive" if i == index else "NavTopBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _create_play_icon(self, size=40, color="#ffffff", bg_color="#0055ff"):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.setBrush(QBrush(QColor(color)))
        triangle = QPolygonF([QPointF(size * 0.38, size * 0.28), QPointF(size * 0.38, size * 0.72), QPointF(size * 0.72, size * 0.5)])
        painter.drawPolygon(triangle)
        painter.end()
        lbl = QLabel()
        lbl.setPixmap(pixmap)
        lbl.setFixedSize(size, size)
        return lbl

    # ==========================================
    # PAGE 1: HOME
    # ==========================================
    def build_home_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(25)

        # --- HERO BANNER ---
        hero = QFrame()
        hero.setObjectName("HeroBanner")
        hero.setFixedHeight(220)
        h_layout = QHBoxLayout(hero)
        h_layout.setContentsMargins(20, 20, 20, 20)
        h_layout.setSpacing(25)

        h_art = QLabel()
        h_art.setFixedSize(180, 180)
        h_art.setStyleSheet("background: #333; border-radius: 8px;")

        h_text = QVBoxLayout()
        h_text.setAlignment(Qt.AlignVCenter)
        h_text.setSpacing(6)
        h_tag = QLabel("EDITOR'S PICK · ALBUM OF THE WEEK")
        h_tag.setStyleSheet("color: #ff5555; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        h_title = QLabel("On Giacometti — Hania Rani")
        h_title.setStyleSheet("color: white; font-size: 26px; font-weight: bold;")
        h_desc = QLabel("Recorded in the Swiss Alps, full of snow and silence and long reverb tails that invite meditative space for deep, uninterrupted listening.")
        h_desc.setWordWrap(True)
        h_desc.setStyleSheet("color: #aaa; font-size: 12px;")
        
        h_btn = QPushButton("▶ Play Album")
        h_btn.setFixedSize(110, 32)
        h_btn.setStyleSheet("background-color: #0055ff; color: white; border-radius: 16px; font-weight: bold; font-size: 11px;")
        
        h_text.addWidget(h_tag)
        h_text.addWidget(h_title)
        h_text.addWidget(h_desc)
        h_text.addSpacing(10)
        h_text.addWidget(h_btn, alignment=Qt.AlignLeft)

        h_layout.addWidget(h_art)
        h_layout.addLayout(h_text, 1)
        layout.addWidget(hero)

        # --- JUMP BACK IN ---
        jb_head = QHBoxLayout()
        jb_title = QLabel("Jump Back In")
        jb_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        jb_sub = QLabel("Recent listening history")
        jb_sub.setStyleSheet("color: #666; font-size: 10px;")
        jb_head.addWidget(jb_title)
        jb_head.addStretch()
        jb_head.addWidget(jb_sub)
        layout.addLayout(jb_head)

        jb_layout = QHBoxLayout()
        jb_layout.setSpacing(15)
        recents = [
            ("Nils Frahm Radio", "Artist Mix"),
            ("Deep Focus Playlist", "42 tracks · Ambient"),
            ("All Melody", "Nils Frahm"),
            ("remember", "Ólafur Arnalds"),
            ("Eusa", "Hania Rani"),
            ("Singularity", "Jon Hopkins"),
        ]
        for title, sub in recents:
            card = QFrame()
            card.setFixedSize(150, 195) 
            card.setStyleSheet("background-color: #181818; border-radius: 6px; border: 1px solid #222;") 
            
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(10, 10, 10, 10)
            c_layout.setSpacing(5)
            
            art = QLabel()
            art.setFixedSize(130, 130)
            art.setStyleSheet("background-color: #333; border-radius: 6px;")
            
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
            s = QLabel(sub)
            s.setStyleSheet("color: #888; font-size: 10px;")
            
            c_layout.addWidget(art, alignment=Qt.AlignCenter)
            c_layout.addWidget(t)
            c_layout.addWidget(s)
            jb_layout.addWidget(card)
        jb_layout.addStretch()
        layout.addLayout(jb_layout)

        # --- MADE FOR YOU ---
        mf_title = QLabel("Made For You")
        mf_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(mf_title)

        mf_layout = QHBoxLayout()
        mf_layout.setSpacing(15)
        mixes = [
            ("Daily Mix 1", "Nils Frahm, Ólafur Arnalds, Hania Rani"),
            ("Deep Focus Mix", "Jon Hopkins, Brian Eno, Aphex Twin"),
            ("Late Night Piano", "Hania Rani, Debussy, Erik Satie"),
            ("Nordic Soundscapes", "Ólafur Arnalds, Hania Rani, Nils Frahm"),
        ]
        for title, sub in mixes:
            card = QFrame()
            card.setObjectName("MixCard")
            card.setFixedHeight(130) 
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(15, 15, 15, 15)

            text_col = QVBoxLayout()
            text_col.setSpacing(3)
            tag = QLabel("PERSONALIZED MIX")
            tag.setStyleSheet("color: #0055ff; font-size: 8px; font-weight: bold; letter-spacing: 0.5px;")
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
            s = QLabel(sub)
            s.setWordWrap(True)
            s.setStyleSheet("color: #888; font-size: 9px;")
            
            text_col.addWidget(tag)
            text_col.addWidget(t)
            text_col.addWidget(s)
            text_col.addStretch()

            play = self._create_play_icon(26, bg_color="#1a1a1a", color="#0055ff")
            c_layout.addLayout(text_col, 1)
            c_layout.addWidget(play, alignment=Qt.AlignBottom)
            mf_layout.addWidget(card, 1)
        layout.addLayout(mf_layout)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ==========================================
    # PAGE 2: SEARCH (Placeholder)
    # ==========================================
    def build_search_page(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 20, 30, 20)
        
        # Reuse the main search bar style
        big_search = QLineEdit()
        big_search.setObjectName("SearchBar")
        big_search.setPlaceholderText("🔍 Search for songs, artists, or albums...")
        big_search.setFixedHeight(45)
        big_search.setStyleSheet("font-size: 16px; padding-left: 20px; border-radius: 8px; background-color: #1a1a1a;")
        
        layout.addWidget(big_search)
        layout.addStretch()
        return content

    # ==========================================
    # PAGE 3: LIBRARY (Placeholder)
    # ==========================================
    def build_library_page(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 20, 30, 20)
        
        title = QLabel("Your Library")
        title.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")
        
        layout.addWidget(title)
        layout.addStretch()
        return content

    def create_player_bar(self):
        player_bar = QWidget()
        player_bar.setObjectName("PlayerBar")
        player_bar.setFixedHeight(80)
        
        layout = QHBoxLayout(player_bar)
        layout.setContentsMargins(20, 10, 20, 10)

        left = QHBoxLayout()
        art = QLabel()
        art.setFixedSize(50, 50)
        art.setStyleSheet("background-color: #222; border-radius: 4px;")
        info = QVBoxLayout()
        info.setSpacing(2)
        t = QLabel("All Melody")
        t.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        a = QLabel("Nils Frahm")
        a.setStyleSheet("color: #888; font-size: 10px;")
        info.addWidget(t)
        info.addWidget(a)
        left.addWidget(art)
        left.addSpacing(10)
        left.addLayout(info)
        left.addStretch()

        center = QVBoxLayout()
        center.setSpacing(5)
        controls = QHBoxLayout()
        controls.setAlignment(Qt.AlignCenter)
        for icon in ["⏮", "⏸", "⏭"]:
            btn = QPushButton(icon)
            btn.setObjectName("MainPlayBtn" if icon == "⏸" else "PlayControls")
            if icon == "⏸": btn.setFixedSize(32, 32)
            controls.addWidget(btn)

        progress = QHBoxLayout()
        now = QLabel("02:41")
        now.setStyleSheet("color: #888; font-size: 9px;")
        slider = QSlider(Qt.Horizontal)
        slider.setValue(30)
        total = QLabel("09:30")
        total.setStyleSheet("color: #888; font-size: 9px;")
        progress.addWidget(now)
        progress.addWidget(slider)
        progress.addWidget(total)
        center.addLayout(controls)
        center.addLayout(progress)

        right = QHBoxLayout()
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("color: #888; font-size: 12px;")
        vol_slider = QSlider(Qt.Horizontal)
        vol_slider.setFixedWidth(100)
        right.addWidget(vol_icon)
        right.addWidget(vol_slider)

        layout.addLayout(left, 1)
        layout.addLayout(center, 2)
        layout.addLayout(right, 1)
        return player_bar

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())