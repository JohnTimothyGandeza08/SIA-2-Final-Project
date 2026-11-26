# dashboard.py
import sys
from dataclasses import dataclass
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame,
    QSlider, QGridLayout, QStackedWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPolygonF, QBrush, QPixmap
from PySide6.QtCore import QPointF
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from theme import DARK_THEME
from components import Sidebar, TrackRow


@dataclass
class TrackData:
    title: str
    album: str
    length: str


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aura - UI Layout")
        self.resize(1100, 800)
        self.setStyleSheet(DARK_THEME)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        # Build Pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.build_home_page())     # Index 0
        self.stacked_widget.addWidget(self.build_search_page())   # Index 1
        self.stacked_widget.addWidget(self.build_library_page())  # Index 2

        # Main Layout (Sidebar + Content + Player Bar)
        main_widget = QWidget()
        main_widget.setObjectName("MainContainer")
        self.setCentralWidget(main_widget)

        outer_layout = QVBoxLayout(main_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        content_h_layout = QHBoxLayout()
        content_h_layout.setContentsMargins(0, 0, 0, 0)
        content_h_layout.setSpacing(0)

        # Sidebar (uses component)
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.handle_page_change)
        content_h_layout.addWidget(self.sidebar)

        # Right Side
        right_widget = QWidget()
        right_widget.setObjectName("ContentArea")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(40, 20, 40, 0)
        right_layout.setSpacing(0)

        # Top bar
        top_bar = QHBoxLayout()
        top_search = QLineEdit()
        top_search.setObjectName("SearchBar")
        top_search.setPlaceholderText("🔍 Search catalog...")
        top_search.setFixedSize(300, 36)

        profile_icon = QLabel("J")
        profile_icon.setFixedSize(35, 35)
        profile_icon.setAlignment(Qt.AlignCenter)
        profile_icon.setStyleSheet(
            "background: white; color: black; border-radius: 17px; font-weight: bold;")

        top_bar.addWidget(top_search)
        top_bar.addStretch()
        top_bar.addWidget(profile_icon)

        right_layout.addLayout(top_bar)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.stacked_widget, 1)
        right_layout.addSpacing(20)

        content_h_layout.addWidget(right_widget, 1)
        outer_layout.addLayout(content_h_layout, 1)
        outer_layout.addWidget(self.create_player_bar())

    def handle_page_change(self, page_name):
        """Routes sidebar nav clicks to the stacked widget."""
        mapping = {"home": 0, "search": 1, "your library": 2}
        if page_name in mapping:
            self.stacked_widget.setCurrentIndex(mapping[page_name])

    # ==========================================
    # HELPER: Circular Play Button (QPainter)
    # ==========================================
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
            QPointF(size * 0.35, size * 0.25),
            QPointF(size * 0.35, size * 0.75),
            QPointF(size * 0.75, size * 0.5)
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
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent; border: none;")
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 10, 20)
        layout.setSpacing(25)

        # --- Hero Banner (Editor's Pick) ---
        hero = QFrame()
        hero.setFixedHeight(200)
        hero.setObjectName("HeroBanner")
        h_layout = QHBoxLayout(hero)
        h_layout.setContentsMargins(30, 30, 30, 30)
        h_layout.setSpacing(30)

        h_art = QLabel()
        h_art.setFixedSize(140, 140)
        h_art.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #3a2e25, stop:1 #1a1a1a); border-radius: 8px;")

        h_text = QVBoxLayout()
        h_text.setAlignment(Qt.AlignVCenter)
        h_tag = QLabel("EDITOR'S PICK · ALBUM OF THE WEEK")
        h_tag.setStyleSheet("color: #ff5555; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        h_title = QLabel("On Giacometti — Hania Rani")
        h_title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        h_desc = QLabel("Recorded in the Swiss Alps, full of snow and silence and long "
                        "reverb tails that invite meditative space for deep listening.")
        h_desc.setWordWrap(True)
        h_desc.setStyleSheet("color: #aaa; font-size: 13px;")

        h_btn = QPushButton("▶ Play Album")
        h_btn.setFixedSize(120, 36)
        h_btn.setStyleSheet(
            "background-color: #0055ff; color: white; border-radius: 18px; font-weight: bold;")
        h_btn.setCursor(Qt.PointingHandCursor)

        h_text.addWidget(h_tag)
        h_text.addWidget(h_title)
        h_text.addWidget(h_desc)
        h_text.addSpacing(10)
        h_text.addWidget(h_btn, alignment=Qt.AlignLeft)

        h_layout.addWidget(h_art)
        h_layout.addLayout(h_text, 1)
        layout.addWidget(hero)

        # --- Jump Back In ---
        jb_header = QHBoxLayout()
        jb_title = QLabel("Jump Back In")
        jb_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        jb_see = QLabel("See All History →")
        jb_see.setStyleSheet("color: #888; font-size: 12px;")
        jb_header.addWidget(jb_title)
        jb_header.addStretch()
        jb_header.addWidget(jb_see)
        layout.addLayout(jb_header)

        jb_layout = QHBoxLayout()
        jb_layout.setSpacing(15)
        recents = [
            ("Nils Frahm Radio", "Artist Mix", "#333"),
            ("Deep Focus Playlist", "52 tracks", "#444"),
            ("All Melody", "Nils Frahm", "#222"),
            ("remember", "Ólafur Arnalds", "#111"),
            ("Eusa", "Hania Rani", "#333"),
            ("Singularity", "Jon Hopkins", "#444"),
        ]
        for title, sub, color in recents:
            card = QFrame()
            card.setFixedSize(140, 185)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(0, 0, 0, 0)
            art = QLabel()
            art.setFixedSize(140, 140)
            art.setStyleSheet(f"background-color: {color}; border-radius: 8px;")
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 13px; font-weight: bold; margin-top: 5px;")
            s = QLabel(sub)
            s.setStyleSheet("color: #888; font-size: 11px;")
            c_layout.addWidget(art)
            c_layout.addWidget(t)
            c_layout.addWidget(s)
            jb_layout.addWidget(card)
        jb_layout.addStretch()
        layout.addLayout(jb_layout)

        # --- Made For You ---
        mf_title = QLabel("Made For You")
        mf_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
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
            tag = QLabel("PERSONALIZED MIX")
            tag.setStyleSheet("color: #0055ff; font-size: 9px; font-weight: bold;")
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
            s = QLabel(sub)
            s.setWordWrap(True)
            s.setStyleSheet("color: #888; font-size: 11px;")
            text_col.addWidget(tag)
            text_col.addWidget(t)
            text_col.addWidget(s)
            text_col.addStretch()

            play = self._create_play_icon(32, bg_color="#1a1a1a", color="#0055ff")
            c_layout.addLayout(text_col, 1)
            c_layout.addWidget(play, alignment=Qt.AlignBottom)
            mf_layout.addWidget(card, 1)
        layout.addLayout(mf_layout)

        # --- Curated Moods ---
        cm_title = QLabel("Curated Moods")
        cm_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
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
            card.setFixedHeight(100)
            card.setStyleSheet(
                f"background-color: {color}; border-radius: 10px; border: 1px solid #333;")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 15, 15, 15)
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
            s = QLabel(sub)
            s.setStyleSheet("color: #aaa; font-size: 11px;")
            c_layout.addWidget(t)
            c_layout.addStretch()
            c_layout.addWidget(s)
            cm_grid.addWidget(card, i // 4, i % 4)
        layout.addLayout(cm_grid)

        # --- New Releases ---
        nr_title = QLabel("New Releases")
        nr_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(nr_title)

        nr_layout = QHBoxLayout()
        nr_layout.setSpacing(15)
        releases = [("Some Kind of Peace", "Ólafur Arnalds"),
                    ("Ghosts", "Hania Rani"),
                    ("Day", "Nils Frahm"),
                    ("Ritual", "Jon Hopkins")]
        for title, artist in releases:
            card = QFrame()
            card.setFixedSize(160, 200)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(0, 0, 0, 0)
            art = QLabel()
            art.setFixedSize(160, 160)
            art.setStyleSheet("background-color: #222; border-radius: 6px;")
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 13px; font-weight: bold; margin-top: 5px;")
            a = QLabel(artist)
            a.setStyleSheet("color: #888; font-size: 11px;")
            c_layout.addWidget(art)
            c_layout.addWidget(t)
            c_layout.addWidget(a)
            nr_layout.addWidget(card)
        nr_layout.addStretch()
        layout.addLayout(nr_layout)

        layout.addStretch()
        scroll_area.setWidget(content)
        return scroll_area

    # ==========================================
    # PAGE 2: SEARCH
    # ==========================================
    def build_search_page(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Centered Search Bar
        search_wrapper = QHBoxLayout()
        search_wrapper.addStretch()
        big_search = QLineEdit()
        big_search.setObjectName("SearchBar")
        big_search.setText("Nils Frahm")
        big_search.setFixedSize(500, 45)
        big_search.setStyleSheet(
            "font-size: 14px; padding-left: 15px; border-radius: 8px; background-color: #1a1a1a;")
        clear_btn = QPushButton("✕")
        clear_btn.setStyleSheet(
            "background: transparent; color: #888; border: none; font-size: 14px;")
        sbl = QHBoxLayout(big_search)
        sbl.setContentsMargins(0, 0, 15, 0)
        sbl.addStretch()
        sbl.addWidget(clear_btn)
        search_wrapper.addWidget(big_search)
        search_wrapper.addStretch()

        # Filter Pills
        filter_wrapper = QHBoxLayout()
        filter_wrapper.addStretch()
        for i, f in enumerate(["ALL", "ARTISTS", "ALBUMS", "SONGS"]):
            btn = QPushButton(f)
            btn.setObjectName("FilterBtnActive" if i == 0 else "FilterBtn")
            btn.setCursor(Qt.PointingHandCursor)
            filter_wrapper.addWidget(btn)
        filter_wrapper.addStretch()

        # Artist Result Card
        artist_card = QFrame()
        artist_card.setObjectName("TableContainer")
        artist_card.setFixedHeight(180)
        ac_layout = QHBoxLayout(artist_card)
        ac_layout.setContentsMargins(30, 20, 30, 20)
        ac_layout.setSpacing(30)

        art_img = QLabel()
        art_img.setFixedSize(120, 120)
        art_img.setStyleSheet("background-color: #333; border-radius: 8px;")

        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignVCenter)
        artist_tag = QLabel("ARTIST")
        artist_tag.setStyleSheet("color: #ff5555; font-size: 10px; font-weight: bold;")
        artist_name = QLabel("Nils Frahm")
        artist_name.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")
        artist_stats = QLabel("1.2M Monthly\nListeners")
        artist_stats.setStyleSheet("color: #aaa; font-size: 12px;")
        info_layout.addWidget(artist_tag)
        info_layout.addWidget(artist_name)
        info_layout.addWidget(artist_stats)

        play_btn = QPushButton("▶")
        play_btn.setObjectName("MainPlayBtn")
        play_btn.setFixedSize(50, 50)

        tracks_layout = QVBoxLayout()
        tracks_layout.setSpacing(10)
        for i, (t, a, dur) in enumerate([("Says", "Spaces", "08:18"),
                                         ("All Melody", "All Melody", "09:30"),
                                         ("Ambre", "Wintermusik", "03:48")]):
            t_row = QHBoxLayout()
            t_num = QLabel(str(i + 1))
            t_num.setFixedWidth(20)
            t_num.setStyleSheet("color: #888;")
            t_name = QLabel(t)
            t_name.setStyleSheet("color: white; font-size: 13px;")
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

        # Explorations
        explore_lbl = QLabel("EXPLORATIONS")
        explore_lbl.setObjectName("SectionTitle")
        explore_lbl.setContentsMargins(0, 20, 0, 10)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)
        for i, (title, sub) in enumerate([("Ambient", "Deep focus"),
                                           ("Classical", "Piano & strings"),
                                           ("Lo-Fi", "Quiet beats"),
                                           ("Field Notes", "Atmospheres")]):
            card = QFrame()
            card.setObjectName("LibraryCard")
            card.setFixedHeight(100)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 15, 15, 15)
            c_title = QLabel(title)
            c_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
            c_sub = QLabel(sub)
            c_sub.setStyleSheet("color: #888; font-size: 11px;")
            c_layout.addWidget(c_title)
            c_layout.addStretch()
            c_layout.addWidget(c_sub)
            grid_layout.addWidget(card, i // 4, i % 4)

        layout.addLayout(search_wrapper)
        layout.addSpacing(15)
        layout.addLayout(filter_wrapper)
        layout.addSpacing(20)
        layout.addWidget(artist_card)
        layout.addSpacing(20)
        layout.addWidget(explore_lbl)
        layout.addLayout(grid_layout)
        layout.addStretch()
        return content

    # ==========================================
    # PAGE 3: LIBRARY
    # ==========================================
    def build_library_page(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent; border: none;")
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 10, 20)
        layout.setSpacing(25)

        # Header & Filters
        title_row = QHBoxLayout()
        title = QLabel("Your Library")
        title.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")
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
        liked_banner.setFixedHeight(140)
        lb_layout = QHBoxLayout(liked_banner)
        lb_layout.setContentsMargins(30, 20, 30, 20)
        heart_icon = QLabel("♥")
        heart_icon.setStyleSheet("color: white; font-size: 40px; background: transparent;")
        lb_text = QVBoxLayout()
        lb_text.setAlignment(Qt.AlignVCenter)
        lb_tag = QLabel("FAVORITES")
        lb_tag.setStyleSheet("color: #ccc; font-size: 10px; font-weight: bold; background: transparent;")
        lb_title = QLabel("Liked Songs")
        lb_title.setStyleSheet("color: white; font-size: 24px; font-weight: bold; background: transparent;")
        lb_sub = QLabel("128 hearted tracks · Includes All Melody by Nils Frahm")
        lb_sub.setStyleSheet("color: #eee; font-size: 12px; background: transparent;")
        lb_text.addWidget(lb_tag)
        lb_text.addWidget(lb_title)
        lb_text.addWidget(lb_sub)
        lb_play = self._create_play_icon(50, bg_color="#ffffff", color="#0055ff")
        lb_layout.addWidget(heart_icon)
        lb_layout.addSpacing(15)
        lb_layout.addLayout(lb_text, 1)
        lb_layout.addWidget(lb_play)
        layout.addWidget(liked_banner)

        # Recently Played
        rp_title = QLabel("Recently Played")
        rp_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(rp_title)

        rp_layout = QHBoxLayout()
        rp_layout.setSpacing(15)
        recents = [("All Melody", "Nils Frahm", "#222"),
                   ("remember", "Ólafur Arnalds", "#333"),
                   ("On Giacometti", "Hania Rani", "#444"),
                   ("Singularity", "Jon Hopkins", "#111")]
        for title, sub, color in recents:
            card = QFrame()
            card.setObjectName("RecentCard")
            card.setFixedSize(180, 60)
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(5, 5, 10, 5)
            art = QLabel()
            art.setFixedSize(50, 50)
            art.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            info = QVBoxLayout()
            info.setSpacing(2)
            info.setAlignment(Qt.AlignVCenter)
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
            s = QLabel(sub)
            s.setStyleSheet("color: #888; font-size: 10px;")
            info.addWidget(t)
            info.addWidget(s)
            c_layout.addWidget(art)
            c_layout.addLayout(info, 1)
            rp_layout.addWidget(card)
        rp_layout.addStretch()
        layout.addLayout(rp_layout)

        # Playlists Table
        yp_header = QHBoxLayout()
        yp_title = QLabel("Your Playlists")
        yp_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        yp_count = QLabel("4 playlists")
        yp_count.setStyleSheet("color: #888; font-size: 11px;")
        yp_header.addWidget(yp_title)
        yp_header.addStretch()
        yp_header.addWidget(yp_count)
        layout.addLayout(yp_header)

        th = QHBoxLayout()
        th.setContentsMargins(15, 0, 15, 0)
        for text, stretch in [("TITLE", 1), ("SONGS", 0), ("DATE CREATED", 0), ("", 0)]:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #666; font-size: 10px; font-weight: bold;")
            if stretch:
                th.addWidget(lbl, 1)
            else:
                lbl.setFixedWidth(80 if text else 40)
                th.addWidget(lbl)
        layout.addLayout(th)

        playlists = [
            ("Deep Focus Architecture", "42", "Nov 12, 2026"),
            ("Late Night Felt Piano", "28", "Oct 24, 2026"),
            ("Rainy Studio Sessions", "19", "Sep 08, 2026"),
        ]
        for title, songs, date in playlists:
            row = QFrame()
            row.setObjectName("PlaylistRow")
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(15, 10, 15, 10)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: white; font-size: 13px;")
            s_lbl = QLabel(songs)
            s_lbl.setFixedWidth(80)
            s_lbl.setStyleSheet("color: #888; font-size: 12px;")
            d_lbl = QLabel(date)
            d_lbl.setFixedWidth(80)
            d_lbl.setStyleSheet("color: #888; font-size: 12px;")
            p_btn = QPushButton("▶")
            p_btn.setFixedSize(30, 30)
            p_btn.setStyleSheet(
                "background-color: transparent; color: white; border: 1px solid #444; border-radius: 15px;")
            r_layout.addWidget(t_lbl, 1)
            r_layout.addWidget(s_lbl)
            r_layout.addWidget(d_lbl)
            r_layout.addWidget(p_btn)
            layout.addWidget(row)

        # Followed Artists
        fa_title = QLabel("Followed Artists")
        fa_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(fa_title)

        fa_layout = QHBoxLayout()
        fa_layout.setSpacing(15)
        artists = [("Nils Frahm", "#333"), ("Ólafur Arnalds", "#222"),
                   ("Hania Rani", "#444"), ("Jon Hopkins", "#111")]
        for name, color in artists:
            card = QFrame()
            card.setObjectName("ArtistCard")
            card.setFixedSize(140, 160)
            c_layout = QVBoxLayout(card)
            c_layout.setAlignment(Qt.AlignCenter)
            c_layout.setContentsMargins(10, 10, 10, 10)
            art = QLabel()
            art.setFixedSize(100, 100)
            art.setStyleSheet(f"background-color: {color}; border-radius: 50px;")
            t = QLabel(name)
            t.setStyleSheet("color: white; font-size: 12px; font-weight: bold; margin-top: 5px;")
            c_layout.addWidget(art)
            c_layout.addWidget(t, alignment=Qt.AlignCenter)
            fa_layout.addWidget(card)
        fa_layout.addStretch()
        layout.addLayout(fa_layout)

        # Downloads
        dl_title = QLabel("Downloads & Offline Mode")
        dl_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(dl_title)

        dl_layout = QHBoxLayout()
        dl_layout.setSpacing(15)
        downloads = [("Spaces", "Nils Frahm"), ("On Giacometti", "Hania Rani"),
                     ("Deep Focus Architecture", "Playlist")]
        for title, sub in downloads:
            card = QFrame()
            card.setObjectName("RecentCard")
            card.setFixedSize(220, 60)
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(5, 5, 10, 5)
            art = QLabel()
            art.setFixedSize(50, 50)
            art.setStyleSheet("background-color: #222; border-radius: 4px;")
            info = QVBoxLayout()
            info.setSpacing(2)
            info.setAlignment(Qt.AlignVCenter)
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
            s = QLabel(sub)
            s.setStyleSheet("color: #888; font-size: 10px;")
            info.addWidget(t)
            info.addWidget(s)
            c_layout.addWidget(art)
            c_layout.addLayout(info, 1)
            dl_layout.addWidget(card)
        dl_layout.addStretch()
        layout.addLayout(dl_layout)

        layout.addStretch()
        scroll_area.setWidget(content)
        return scroll_area

    # ==========================================
    # PLAYER BAR
    # ==========================================
    def create_player_bar(self):
        player_bar = QWidget()
        player_bar.setObjectName("PlayerBar")
        player_bar.setFixedHeight(85)
        layout = QHBoxLayout(player_bar)
        layout.setContentsMargins(20, 10, 20, 10)

        left = QHBoxLayout()
        art = QLabel()
        art.setFixedSize(50, 50)
        art.setStyleSheet("background-color: #333; border-radius: 4px;")
        info = QVBoxLayout()
        t = QLabel("Pavane pour une infante défunte")
        t.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        a = QLabel("Maurice Ravel")
        a.setStyleSheet("color: #888; font-size: 11px;")
        info.addWidget(t)
        info.addWidget(a)
        left.addWidget(art)
        left.addLayout(info)
        left.addStretch()

        center = QVBoxLayout()
        controls = QHBoxLayout()
        controls.setAlignment(Qt.AlignCenter)
        btn2 = QPushButton("⏮")
        btn3 = QPushButton("⏸")
        btn3.setObjectName("MainPlayBtn")
        btn3.setFixedSize(36, 36)
        btn4 = QPushButton("⏭")
        for b in [btn2, btn3, btn4]:
            b.setObjectName("PlayControls")
            controls.addWidget(b)

        progress = QHBoxLayout()
        now = QLabel("01:24")
        now.setStyleSheet("color: #888; font-size: 10px;")
        slider = QSlider(Qt.Horizontal)
        slider.setValue(30)
        total = QLabel("05:42")
        total.setStyleSheet("color: #888; font-size: 10px;")
        progress.addWidget(now)
        progress.addWidget(slider)
        progress.addWidget(total)
        center.addLayout(controls)
        center.addLayout(progress)

        right = QHBoxLayout()
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("color: #888;")
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