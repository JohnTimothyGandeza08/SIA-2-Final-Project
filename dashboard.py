# dashboard.py
import sys
from dataclasses import dataclass
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame,
    QSlider, QGridLayout, QStackedWidget
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPolygonF, QBrush, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from theme import DARK_THEME
from components import TopNavBar

@dataclass
class TrackData:
    title: str
    album: str
    length: str

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pulse")
        self.resize(1100, 800)
        self.setStyleSheet(DARK_THEME)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        main_widget = QWidget()
        main_widget.setObjectName("MainContainer")
        self.setCentralWidget(main_widget)
        outer_layout = QVBoxLayout(main_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # --- 1. TOP HEADER (Logo, Segmented Control, Search) ---
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet("background-color: #050505; border-bottom: 1px solid #1a1a1a;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(30, 0, 30, 0)
        
        # Logo
        logo_box = QHBoxLayout()
        logo_icon = QLabel("▶")
        logo_icon.setStyleSheet("background: #0055ff; color: white; border-radius: 4px; padding: 2px 6px; font-size: 12px;")
        logo_text = QLabel("Pulse")
        logo_text.setStyleSheet("color: white; font-weight: bold; font-size: 16px; margin-left: 5px;")
        logo_box.addWidget(logo_icon)
        logo_box.addWidget(logo_text)
        
        # Segmented Control
        seg_widget = QWidget()
        seg_widget.setObjectName("SegmentedControl")
        seg_widget.setFixedSize(200, 30)
        seg_layout = QHBoxLayout(seg_widget)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(2)
        for i, (icon, text) in enumerate([("🎵", "Music"), ("🎬", "Video"), ("🎮", "Games")]):
            btn = QPushButton(f"{icon} {text}")
            btn.setObjectName("SegBtnActive" if i == 0 else "SegBtn")
            btn.setCursor(Qt.PointingHandCursor)
            seg_layout.addWidget(btn)

        # Right Side (Search + Profile)
        search = QLineEdit()
        search.setObjectName("SearchBar")
        search.setPlaceholderText("🔍 Search catalog...")
        search.setFixedSize(240, 30)

        profile = QLabel("J")
        profile.setFixedSize(30, 30)
        profile.setAlignment(Qt.AlignCenter)
        profile.setStyleSheet("background: white; color: black; border-radius: 15px; font-weight: bold; font-size: 12px;")

        h_layout.addLayout(logo_box)
        h_layout.addSpacing(50)
        h_layout.addWidget(seg_widget)
        h_layout.addStretch()
        h_layout.addWidget(search)
        h_layout.addWidget(profile)

        # --- 2. TOP NAVBAR (Home, Search, Library) ---
        self.navbar = TopNavBar()
        self.navbar.page_changed.connect(self.switch_page)

        # --- 3. STACKED WIDGET ---
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.build_home_page())     # Index 0
        self.stacked_widget.addWidget(self.build_search_page())   # Index 1
        self.stacked_widget.addWidget(self.build_library_page())  # Index 2

        # Add everything to the main outer layout
        outer_layout.addWidget(header)
        outer_layout.addWidget(self.navbar)
        outer_layout.addWidget(self.stacked_widget, 1)
        outer_layout.addWidget(self.create_player_bar())

    def switch_page(self, page_name):
        mapping = {"home": 0, "search": 1, "your library": 2}
        if page_name in mapping:
            self.stacked_widget.setCurrentIndex(mapping[page_name])

    # Helper for the circular play button
    def _create_play_icon(self, size=40, color="#ffffff", bg_color="#0055ff"):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.setBrush(QBrush(QColor(color)))
        triangle = QPolygonF([
            QPointF(size * 0.38, size * 0.28),
            QPointF(size * 0.38, size * 0.72),
            QPointF(size * 0.72, size * 0.5)
        ])
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
        h_art.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #4a3a2a, stop:1 #1a1a1a); border-radius: 8px;")

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
        h_btn.setCursor(Qt.PointingHandCursor)

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
            ("Nils Frahm Radio", "Artist Mix", "#333"),
            ("Deep Focus Playlist", "42 tracks · Ambient", "#111"),
            ("All Melody", "Nils Frahm", "#222"),
            ("remember", "Ólafur Arnalds", "#1a1a1a"),
            ("Eusa", "Hania Rani", "#333"),
            ("Singularity", "Jon Hopkins", "#111"),
        ]
        for title, sub, color in recents:
            card = QFrame()
            card.setFixedSize(150, 185)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setSpacing(5)
            
            art = QLabel()
            art.setFixedSize(150, 150)
            art.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
            
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
            s = QLabel(sub)
            s.setStyleSheet("color: #888; font-size: 10px;")
            
            c_layout.addWidget(art)
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
            card.setFixedHeight(120)
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

        # --- CURATED MOODS ---
        cm_title = QLabel("Curated Moods")
        cm_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(cm_title)

        cm_grid = QGridLayout()
        cm_grid.setSpacing(15)
        moods = [
            ("Cinematic", "Widescreen strings & synth swells", "#0f172a"),
            ("Study Session", "Minimal beats without lyrics", "#1e1b4b"),
            ("Sleep", "Slow harmonic drones & rain", "#450a0a"),
            ("Sunday Morning", "Warm acoustic piano & sunlight", "#1c1917"),
        ]
        for i, (title, sub, color) in enumerate(moods):
            card = QFrame()
            card.setObjectName("MoodCard")
            card.setFixedHeight(90)
            card.setStyleSheet(f"background-color: {color};")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 15, 15, 15)
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
            s = QLabel(sub)
            s.setStyleSheet("color: #aaa; font-size: 9px;")
            c_layout.addWidget(t)
            c_layout.addStretch()
            c_layout.addWidget(s)
            cm_grid.addWidget(card, i // 4, i % 4)
        layout.addLayout(cm_grid)

        # --- NEW RELEASES ---
        nr_title = QLabel("New Releases")
        nr_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(nr_title)

        nr_layout = QHBoxLayout()
        nr_layout.setSpacing(15)
        releases = [("Some Kind of Peace", "Ólafur Arnalds"), ("Ghosts", "Hania Rani"), ("Day", "Nils Frahm"), ("Ritual", "Jon Hopkins")]
        for title, artist in releases:
            card = QFrame()
            card.setFixedSize(140, 180)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setSpacing(5)
            
            art = QLabel()
            art.setFixedSize(140, 140)
            art.setStyleSheet("background-color: #222; border-radius: 6px;")
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 11px; font-weight: bold;")
            a = QLabel(artist)
            a.setStyleSheet("color: #888; font-size: 10px;")
            
            c_layout.addWidget(art)
            c_layout.addWidget(t)
            c_layout.addWidget(a)
            nr_layout.addWidget(card)
        nr_layout.addStretch()
        layout.addLayout(nr_layout)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ==========================================
    # PAGE 2: SEARCH
    # ==========================================
    def build_search_page(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)

        # Search bar
        search_wrapper = QHBoxLayout()
        search_wrapper.addStretch()
        big_search = QLineEdit()
        big_search.setObjectName("SearchBar")
        big_search.setText("Nils Frahm")
        big_search.setFixedSize(400, 38)
        big_search.setStyleSheet("font-size: 12px; padding-left: 15px; border-radius: 6px; background-color: #1a1a1a; border: 1px solid #333;")
        clear_btn = QPushButton("✕")
        clear_btn.setStyleSheet("background: transparent; color: #888; border: none; font-size: 12px;")
        sbl = QHBoxLayout(big_search)
        sbl.setContentsMargins(0, 0, 15, 0)
        sbl.addStretch()
        sbl.addWidget(clear_btn)
        search_wrapper.addWidget(big_search)
        search_wrapper.addStretch()

        # Filter pills
        filter_wrapper = QHBoxLayout()
        filter_wrapper.addStretch()
        for i, f in enumerate(["ALL", "ARTISTS", "SONGS"]):
            btn = QPushButton(f)
            btn.setObjectName("FilterBtnActive" if i == 0 else "FilterBtn")
            btn.setCursor(Qt.PointingHandCursor)
            filter_wrapper.addWidget(btn)
        filter_wrapper.addStretch()

        layout.addLayout(search_wrapper)
        layout.addSpacing(10)
        layout.addLayout(filter_wrapper)
        layout.addSpacing(15)

        # Artist Card
        artist_card = QFrame()
        artist_card.setObjectName("TableContainer")
        artist_card.setFixedHeight(180)
        ac_layout = QHBoxLayout(artist_card)
        ac_layout.setContentsMargins(20, 20, 20, 20)
        ac_layout.setSpacing(25)

        art_img = QLabel()
        art_img.setFixedSize(140, 140)
        art_img.setStyleSheet("background-color: #333; border-radius: 6px;")

        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignVCenter)
        artist_tag = QLabel("ARTIST")
        artist_tag.setStyleSheet("color: #ff5555; font-size: 9px; font-weight: bold;")
        artist_name = QLabel("Nils Frahm")
        artist_name.setStyleSheet("color: white; font-size: 26px; font-weight: bold;")
        artist_stats = QLabel("1.2M Monthly Listeners")
        artist_stats.setObjectName("ArtistStat")
        info_layout.addWidget(artist_tag)
        info_layout.addWidget(artist_name)
        info_layout.addWidget(artist_stats)

        play_btn = QPushButton("▶")
        play_btn.setObjectName("MainPlayBtn")
        play_btn.setFixedSize(45, 45)

        tracks_layout = QVBoxLayout()
        tracks_layout.setSpacing(12)
        for i, (t, a, dur) in enumerate([("Says", "Spaces", "08:18"), ("All Melody", "All Melody", "09:30"), ("Ambre", "Wintermusik", "03:48")]):
            t_row = QHBoxLayout()
            t_num = QLabel("▶" if i == 0 else str(i + 1))
            t_num.setObjectName("TrackRowNum")
            t_name = QLabel(t)
            t_name.setStyleSheet("color: white; font-size: 12px;")
            t_album = QLabel(a)
            t_album.setStyleSheet("color: #888; font-size: 11px;")
            t_time = QLabel(dur)
            t_time.setStyleSheet("color: #888; font-size: 11px;")
            t_heart = QLabel("♡" if i != 1 else "♥")
            t_heart.setStyleSheet("color: #ff5555;" if i == 1 else "color: #888;")

            t_row.addWidget(t_num)
            t_row.addWidget(t_name, 1)
            t_row.addWidget(t_album, 1)
            t_row.addWidget(t_time)
            t_row.addWidget(t_heart)
            tracks_layout.addLayout(t_row)

        ac_layout.addWidget(art_img)
        ac_layout.addLayout(info_layout, 1)
        ac_layout.addWidget(play_btn)
        ac_layout.addLayout(tracks_layout, 2)
        layout.addWidget(artist_card)

        # Explorations
        explore_lbl = QLabel("EXPLORATIONS")
        explore_lbl.setObjectName("SectionTitle")
        layout.addWidget(explore_lbl)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        for i, (title, sub) in enumerate([("Ambient", "Deep focus"), ("Classical", "Piano & strings"), ("Lo-Fi", "Quiet beats"), ("Field Notes", "Atmospheres")]):
            card = QFrame()
            card.setObjectName("TableContainer")
            card.setFixedHeight(90)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 15, 15, 15)
            c_title = QLabel(title)
            c_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
            c_sub = QLabel(sub)
            c_sub.setStyleSheet("color: #888; font-size: 10px;")
            c_layout.addWidget(c_title)
            c_layout.addStretch()
            c_layout.addWidget(c_sub)
            grid_layout.addWidget(card, i // 4, i % 4)

        layout.addLayout(grid_layout)
        layout.addStretch()
        return content

    # ==========================================
    # PAGE 3: LIBRARY
    # ==========================================
    def build_library_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)

        # Header
        title_row = QHBoxLayout()
        title = QLabel("Your Library")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        title_row.addWidget(title)
        title_row.addStretch()
        for i, f in enumerate(["All", "Playlists", "Artists", "Albums", "Podcasts"]):
            btn = QPushButton(f)
            btn.setObjectName("FilterBtnActive" if i == 0 else "FilterBtn")
            btn.setCursor(Qt.PointingHandCursor)
            title_row.addWidget(btn)
        layout.addLayout(title_row)

        # Liked Songs Banner
        liked_banner = QFrame()
        liked_banner.setObjectName("LikedBanner")
        liked_banner.setFixedHeight(120)
        lb_layout = QHBoxLayout(liked_banner)
        lb_layout.setContentsMargins(20, 20, 20, 20)
        
        heart_box = QFrame()
        heart_box.setFixedSize(80, 80)
        heart_box.setStyleSheet("background-color: white; border-radius: 8px;")
        hb_layout = QVBoxLayout(heart_box)
        hb_layout.setAlignment(Qt.AlignCenter)
        heart_icon = QLabel("♥")
        heart_icon.setStyleSheet("color: #0055ff; font-size: 36px; background: transparent;")
        hb_layout.addWidget(heart_icon)

        lb_text = QVBoxLayout()
        lb_text.setAlignment(Qt.AlignVCenter)
        lb_tag = QLabel("FAVORITES")
        lb_tag.setStyleSheet("color: #ccc; font-size: 9px; font-weight: bold; background: transparent;")
        lb_title = QLabel("Liked Songs")
        lb_title.setStyleSheet("color: white; font-size: 22px; font-weight: bold; background: transparent;")
        lb_sub = QLabel("128 hearted tracks · Includes All Melody by Nils Frahm")
        lb_sub.setStyleSheet("color: #eee; font-size: 10px; background: transparent;")
        lb_text.addWidget(lb_tag)
        lb_text.addWidget(lb_title)
        lb_text.addWidget(lb_sub)
        
        lb_play = self._create_play_icon(40, bg_color="#ffffff", color="#0055ff")
        
        lb_layout.addWidget(heart_box)
        lb_layout.addSpacing(15)
        lb_layout.addLayout(lb_text, 1)
        lb_layout.addWidget(lb_play)
        layout.addWidget(liked_banner)

        # Recently Played
        rp_title = QLabel("Recently Played")
        rp_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(rp_title)

        rp_layout = QHBoxLayout()
        rp_layout.setSpacing(15)
        recents = [("All Melody", "Nils Frahm", "#222"), ("remember", "Ólafur Arnalds", "#fff"), ("On Giacometti", "Hania Rani", "#333"), ("Singularity", "Jon Hopkins", "#111")]
        for title, sub, color in recents:
            card = QFrame()
            card.setObjectName("RecentCard")
            card.setFixedSize(200, 60)
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(5, 5, 10, 5)
            c_layout.setSpacing(10)
            
            art = QLabel()
            art.setFixedSize(50, 50)
            art.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            
            info = QVBoxLayout()
            info.setSpacing(2)
            info.setAlignment(Qt.AlignVCenter)
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 11px; font-weight: bold;")
            s = QLabel(sub)
            s.setStyleSheet("color: #888; font-size: 10px;")
            info.addWidget(t)
            info.addWidget(s)
            
            c_layout.addWidget(art)
            c_layout.addLayout(info, 1)
            rp_layout.addWidget(card)
        rp_layout.addStretch()
        layout.addLayout(rp_layout)

        # Your Playlists (Table)
        yp_header = QHBoxLayout()
        yp_title = QLabel("Your Playlists")
        yp_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        yp_count = QLabel("4 playlists")
        yp_count.setStyleSheet("color: #888; font-size: 10px;")
        yp_header.addWidget(yp_title)
        yp_header.addStretch()
        yp_header.addWidget(yp_count)
        layout.addLayout(yp_header)

        table_container = QFrame()
        table_container.setObjectName("TableContainer")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(15, 10, 15, 10)
        table_layout.setSpacing(0)

        # Headers
        th = QHBoxLayout()
        for text, stretch in [("TITLE", 1), ("SONGS", 0), ("DATE CREATED", 0), ("", 0)]:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #666; font-size: 9px; font-weight: bold;")
            if stretch:
                th.addWidget(lbl, 1)
            else:
                lbl.setFixedWidth(100 if text else 40)
                th.addWidget(lbl)
        table_layout.addLayout(th)
        table_layout.addSpacing(10)

        playlists = [("Deep Focus Architecture", "42", "Nov 12, 2026"), ("Late Night Felt Piano", "28", "Oct 24, 2026"), ("Rainy Studio Sessions", "19", "Sep 08, 2026")]
        for title, songs, date in playlists:
            row = QFrame()
            row.setObjectName("PlaylistRow")
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(0, 10, 0, 10)
            
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: white; font-size: 12px;")
            s_lbl = QLabel(songs)
            s_lbl.setFixedWidth(100)
            s_lbl.setStyleSheet("color: #888; font-size: 11px;")
            d_lbl = QLabel(date)
            d_lbl.setFixedWidth(100)
            d_lbl.setStyleSheet("color: #888; font-size: 11px;")
            
            p_btn = QPushButton("▶")
            p_btn.setFixedSize(24, 24)
            p_btn.setStyleSheet("background-color: #222; color: white; border: none; border-radius: 12px; font-size: 9px;")
            
            r_layout.addWidget(t_lbl, 1)
            r_layout.addWidget(s_lbl)
            r_layout.addWidget(d_lbl)
            r_layout.addWidget(p_btn)
            table_layout.addWidget(row)
            
        layout.addWidget(table_container)

        # Followed Artists
        fa_title = QLabel("Followed Artists")
        fa_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(fa_title)

        fa_layout = QHBoxLayout()
        fa_layout.setSpacing(15)
        artists = [("Nils Frahm", "#333"), ("Ólafur Arnalds", "#222"), ("Hania Rani", "#444"), ("Jon Hopkins", "#111")]
        for name, color in artists:
            card = QFrame()
            card.setObjectName("ArtistCard")
            card.setFixedSize(140, 160)
            c_layout = QVBoxLayout(card)
            c_layout.setAlignment(Qt.AlignCenter)
            c_layout.setContentsMargins(15, 15, 15, 15)
            art = QLabel()
            art.setFixedSize(100, 100)
            art.setStyleSheet(f"background-color: {color}; border-radius: 50px;")
            t = QLabel(name)
            t.setStyleSheet("color: white; font-size: 11px; font-weight: bold; margin-top: 10px;")
            c_layout.addWidget(art)
            c_layout.addWidget(t, alignment=Qt.AlignCenter)
            fa_layout.addWidget(card)
        fa_layout.addStretch()
        layout.addLayout(fa_layout)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ==========================================
    # PLAYER BAR
    # ==========================================
    def create_player_bar(self):
        player_bar = QWidget()
        player_bar.setObjectName("PlayerBar")
        player_bar.setFixedHeight(80)
        player_bar.setStyleSheet("background-color: #0f0f0f; border-top: 1px solid #1a1a1a;")
        
        layout = QHBoxLayout(player_bar)
        layout.setContentsMargins(20, 10, 20, 10)

        # Left (Track Info)
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

        # Center (Controls)
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

        # Right (Volume)
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