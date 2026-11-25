# dashboard.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame,
    QSlider, QGridLayout, QStackedWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from theme import DARK_THEME


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aura - UI Layout")
        self.resize(1100, 800)
        self.setStyleSheet(DARK_THEME)

        # Setup basic player (No API, just for UI visuals)
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        # Build Pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.build_home_page())  # Index 0
        self.stacked_widget.addWidget(self.build_search_page())  # Index 1
        self.stacked_widget.addWidget(self.build_library_page())  # Index 2

        # Main Layout
        main_widget = QWidget()
        main_widget.setObjectName("MainContainer")
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        main_layout.addWidget(self.create_sidebar())

        # Right Side (Content + Player)
        right_widget = QWidget()
        right_widget.setObjectName("ContentArea")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(40, 20, 40, 0)
        right_layout.setSpacing(0)

        # Top Bar
        top_bar = QHBoxLayout()
        top_search = QLineEdit()
        top_search.setObjectName("SearchBar")
        top_search.setPlaceholderText("🔍 Search catalog...")
        top_search.setFixedSize(300, 36)

        profile_icon = QLabel("J")
        profile_icon.setFixedSize(35, 35)
        profile_icon.setAlignment(Qt.AlignCenter)
        profile_icon.setStyleSheet("background: white; color: black; border-radius: 17px; font-weight: bold;")

        top_bar.addWidget(top_search)
        top_bar.addStretch()
        top_bar.addWidget(profile_icon)

        right_layout.addLayout(top_bar)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.stacked_widget, 1)
        right_layout.addSpacing(20)

        main_layout.addWidget(right_widget, 1)

        # Bottom Player Bar Assembly
        main_layout.removeWidget(right_widget)
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        content_h_layout = QHBoxLayout()
        content_h_layout.setContentsMargins(0, 0, 0, 0)
        content_h_layout.setSpacing(0)
        content_h_layout.addWidget(self.create_sidebar())
        content_h_layout.addWidget(right_widget, 1)

        outer_layout.addLayout(content_h_layout, 1)
        outer_layout.addWidget(self.create_player_bar())

        new_central = QWidget()
        new_central.setObjectName("MainContainer")
        new_central.setLayout(outer_layout)
        self.setCentralWidget(new_central)

    def switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        for btn, idx in self.nav_buttons:
            btn.setObjectName("NavLabelActive" if idx == index else "NavLabel")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ==========================================
    # PAGE 1: HOME
    # ==========================================
    def build_home_page(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent; border: none;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 20)
        layout.setSpacing(0)

        # Greeting
        greet = QLabel("Good morning, Julian.")
        greet.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")
        sub = QLabel("Quiet spaces and restored analog tone for your morning.")
        sub.setStyleSheet("color: #888; font-size: 13px;")

        layout.addWidget(greet)
        layout.addWidget(sub)
        layout.addSpacing(25)

        # Featured Card
        featured = QFrame()
        featured.setFixedHeight(220)
        featured.setStyleSheet("background-color: #181818; border-radius: 8px;")
        f_layout = QHBoxLayout(featured)
        f_layout.setContentsMargins(30, 30, 0, 30)

        f_text = QVBoxLayout()
        f_text.setAlignment(Qt.AlignVCenter)
        tag = QLabel("FEATURED LISTENING");
        tag.setStyleSheet("color: #ff5555; font-size: 10px; font-weight: bold;")
        title = QLabel("Quiet Architecture: Japanese Ambient\n1982–1990");
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        desc = QLabel("Synthesized environmental tapestries designed for contemplation.");
        desc.setStyleSheet("color: #aaa; font-size: 12px;")

        btn = QPushButton("▶ Play Session");
        btn.setFixedSize(130, 36);
        btn.setStyleSheet("background-color: black; color: white; border-radius: 18px; font-weight: bold;")

        f_text.addWidget(tag);
        f_text.addWidget(title);
        f_text.addWidget(desc);
        f_text.addSpacing(10)
        f_text.addWidget(btn, alignment=Qt.AlignLeft)

        f_img = QLabel();
        f_img.setFixedWidth(350);
        f_img.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #8a6c4f, stop:1 #3a2e25); border-top-right-radius: 8px; border-bottom-right-radius: 8px;")

        f_layout.addLayout(f_text, 1)
        f_layout.addWidget(f_img)
        layout.addWidget(featured)
        layout.addSpacing(35)

        # Recently Played Section
        rp_header = QHBoxLayout()
        rp_title = QLabel("Recently Played")
        rp_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        rp_see_all = QLabel("See All History →")
        rp_see_all.setStyleSheet("color: #ff5555; font-size: 12px;")
        rp_header.addWidget(rp_title)
        rp_header.addStretch()
        rp_header.addWidget(rp_see_all)
        layout.addLayout(rp_header)
        layout.addSpacing(15)

        # Recently Played Cards
        rp_layout = QHBoxLayout()
        rp_layout.setSpacing(20)
        for i in range(5):
            card = QFrame()
            card.setFixedSize(160, 210)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(0, 0, 0, 0)

            art = QLabel()
            art.setFixedSize(160, 160)
            art.setStyleSheet(
                f"background-color: #{['d4d4d4', 'a3a3a3', 'e0e0e0', '8c8c8c', 'b5b5b5'][i]}; border-radius: 6px;")

            t = QLabel(f"Recent Track {i + 1}")
            t.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
            a = QLabel("Artist Name")
            a.setStyleSheet("color: #888; font-size: 11px;")

            c_layout.addWidget(art)
            c_layout.addSpacing(5)
            c_layout.addWidget(t)
            c_layout.addWidget(a)
            rp_layout.addWidget(card)
        rp_layout.addStretch()
        layout.addLayout(rp_layout)
        layout.addSpacing(35)

        # Curated Tracks
        ct_title = QLabel("Curated Tracks")
        ct_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(ct_title)
        layout.addSpacing(15)

        tracks = [
            ("Pavane pour une infante défunte", "Maurice Ravel", "05:42", True),
            ("April 14th", "Aphex Twin", "02:35", False),
            ("On The Nature of Daylight", "Max Richter", "06:11", False),
        ]
        for i, (t, a, dur, active) in enumerate(tracks):
            row = QHBoxLayout()
            num = QLabel(f"{i + 1:02d}");
            num.setFixedWidth(30);
            num.setStyleSheet("color: #ff5555;" if active else "color: #888;")
            art = QLabel();
            art.setFixedSize(40, 40);
            art.setStyleSheet("background-color: #333; border-radius: 4px;")
            info = QVBoxLayout()
            t_lbl = QLabel(t);
            t_lbl.setStyleSheet("color: #ff5555; font-weight: bold;" if active else "color: white;")
            a_lbl = QLabel(a);
            a_lbl.setStyleSheet("color: #888; font-size: 11px;")
            info.addWidget(t_lbl);
            info.addWidget(a_lbl)
            dur_lbl = QLabel(dur);
            dur_lbl.setStyleSheet("color: #888;")

            row.addWidget(num);
            row.addWidget(art);
            row.addLayout(info, 1);
            row.addWidget(dur_lbl)
            layout.addLayout(row)

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

        # Centered Search
        search_wrapper = QHBoxLayout()
        search_wrapper.addStretch()
        big_search = QLineEdit()
        big_search.setObjectName("SearchBar")
        big_search.setText("Nils Frahm")
        big_search.setFixedSize(500, 45)
        big_search.setStyleSheet("font-size: 14px; padding-left: 15px; border-radius: 8px; background-color: #1a1a1a;")

        clear_btn = QPushButton("✕")
        clear_btn.setStyleSheet("background: transparent; color: #888; border: none; font-size: 14px;")
        search_bar_layout = QHBoxLayout(big_search)
        search_bar_layout.setContentsMargins(0, 0, 15, 0)
        search_bar_layout.addStretch()
        search_bar_layout.addWidget(clear_btn)

        search_wrapper.addWidget(big_search)
        search_wrapper.addStretch()

        # Filters
        filter_wrapper = QHBoxLayout()
        filter_wrapper.addStretch()
        for i, f in enumerate(["ALL", "ARTISTS", "ALBUMS", "SONGS"]):
            btn = QPushButton(f)
            btn.setObjectName("FilterBtnActive" if i == 0 else "FilterBtn")
            btn.setCursor(Qt.PointingHandCursor)
            filter_wrapper.addWidget(btn)
        filter_wrapper.addStretch()

        # Artist Card
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
        artist_tag = QLabel("ARTIST");
        artist_tag.setStyleSheet("color: #ff5555; font-size: 10px; font-weight: bold;")
        artist_name = QLabel("Nils Frahm");
        artist_name.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")
        artist_stats = QLabel("1.2M Monthly\nListeners");
        artist_stats.setStyleSheet("color: #aaa; font-size: 12px;")
        info_layout.addWidget(artist_tag);
        info_layout.addWidget(artist_name);
        info_layout.addWidget(artist_stats)

        play_btn = QPushButton("▶")
        play_btn.setObjectName("MainPlayBtn")
        play_btn.setFixedSize(50, 50)

        tracks_layout = QVBoxLayout()
        tracks_layout.setSpacing(10)
        for i, track in enumerate([("Says", "Spaces", "08:18"), ("All Melody", "All Melody", "09:30"),
                                   ("Ambre", "Wintermusik", "03:48")]):
            t_row = QHBoxLayout()
            t_num = QLabel(str(i + 1));
            t_num.setFixedWidth(20);
            t_num.setStyleSheet("color: #888;")
            t_name = QLabel(track[0]);
            t_name.setStyleSheet("color: white; font-size: 13px;")
            t_album = QLabel(track[1]);
            t_album.setStyleSheet("color: #888; font-size: 11px;")
            t_time = QLabel(track[2]);
            t_time.setStyleSheet("color: #888; font-size: 11px;")
            t_heart = QLabel("♡" if i != 1 else "♥");
            t_heart.setStyleSheet("color: #ff5555;" if i == 1 else "color: #888;")

            t_row.addWidget(t_num);
            t_row.addWidget(t_name, 1);
            t_row.addWidget(t_album, 1);
            t_row.addWidget(t_time);
            t_row.addWidget(t_heart)
            tracks_layout.addLayout(t_row)

        ac_layout.addWidget(art_img);
        ac_layout.addLayout(info_layout, 1);
        ac_layout.addWidget(play_btn);
        ac_layout.addLayout(tracks_layout, 2)

        # Explorations
        explore_lbl = QLabel("EXPLORATIONS");
        explore_lbl.setObjectName("SectionTitle");
        explore_lbl.setContentsMargins(0, 20, 0, 10)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)

        for i, (title, sub) in enumerate(
                [("Ambient", "Deep focus"), ("Classical", "Piano & strings"), ("Lo-Fi", "Quiet beats"),
                 ("Field Notes", "Atmospheres")]):
            card = QFrame()
            card.setObjectName("LibraryCard")
            card.setFixedHeight(100)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 15, 15, 15)
            c_title = QLabel(title);
            c_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
            c_sub = QLabel(sub);
            c_sub.setStyleSheet("color: #888; font-size: 11px;")
            c_layout.addWidget(c_title);
            c_layout.addStretch();
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
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title_row = QHBoxLayout()
        title = QLabel("Library")
        title.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")
        title_row.addWidget(title)
        title_row.addStretch()

        for i, f in enumerate(["All", "Playlists", "Liked"]):
            btn = QPushButton(f)
            btn.setObjectName("FilterBtnActive" if i == 0 else "FilterBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedWidth(60)
            title_row.addWidget(btn)

        layout.addLayout(title_row)
        layout.addSpacing(20)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        c1 = QFrame();
        c1.setObjectName("LibraryCard")
        c1_layout = QVBoxLayout(c1);
        c1_layout.setContentsMargins(15, 15, 15, 15)
        c1_icon = QLabel("❤️");
        c1_icon.setStyleSheet("font-size: 20px; background: transparent;")
        c1_title = QLabel("Liked Songs");
        c1_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold; background: transparent;")
        c1_sub = QLabel("432 tracks");
        c1_sub.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        c1_layout.addWidget(c1_icon);
        c1_layout.addStretch();
        c1_layout.addWidget(c1_title);
        c1_layout.addWidget(c1_sub)

        c2 = QFrame();
        c2.setObjectName("LibraryCard")
        c2_layout = QVBoxLayout(c2);
        c2_layout.setContentsMargins(15, 15, 15, 15)
        c2_icon = QLabel("🎵");
        c2_icon.setStyleSheet("font-size: 20px; background: transparent;")
        c2_title = QLabel("Playlists");
        c2_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold; background: transparent;")
        c2_sub = QLabel("12 playlists");
        c2_sub.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        c2_layout.addWidget(c2_icon);
        c2_layout.addStretch();
        c2_layout.addWidget(c2_title);
        c2_layout.addWidget(c2_sub)

        c3 = QFrame();
        c3.setObjectName("AddPlaylistCard");
        c3.setCursor(Qt.PointingHandCursor)
        c3_layout = QVBoxLayout(c3);
        c3_layout.setAlignment(Qt.AlignCenter)
        c3_icon = QLabel("+");
        c3_icon.setStyleSheet("font-size: 24px; color: #888;")
        c3_title = QLabel("Create Playlist");
        c3_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        c3_layout.addWidget(c3_icon, alignment=Qt.AlignCenter);
        c3_layout.addWidget(c3_title, alignment=Qt.AlignCenter)

        for c in [c1, c2, c3]:
            c.setFixedHeight(120)
            cards_layout.addWidget(c, 1)

        layout.addLayout(cards_layout)
        layout.addSpacing(30)

        toolbar = QHBoxLayout()
        f_input = QLineEdit()
        f_input.setPlaceholderText("Filter your collection...")
        f_input.setFixedSize(250, 30)
        f_input.setStyleSheet(
            "background-color: transparent; border: none; border-bottom: 1px solid #333; color: white;")

        sort_lbl = QLabel("SORT BY:")
        sort_lbl.setStyleSheet("color: #666; font-size: 10px; font-weight: bold;")

        toolbar.addWidget(f_input)
        toolbar.addStretch()
        toolbar.addWidget(sort_lbl)
        toolbar.addWidget(QLabel("Recently Added ▼"))
        layout.addLayout(toolbar)
        layout.addSpacing(15)

        headers = QHBoxLayout()
        headers.setContentsMargins(10, 0, 10, 0)
        headers.setSpacing(15)

        h_num = QLabel("#");
        h_num.setFixedWidth(30);
        h_num.setStyleSheet("color: #666; font-size: 10px;")
        h_title = QLabel("TITLE");
        h_title.setStyleSheet("color: #666; font-size: 10px;")
        h_time = QLabel("🕒");
        h_time.setStyleSheet("color: #666; font-size: 10px;")

        headers.addWidget(h_num);
        headers.addSpacing(55);
        headers.addWidget(h_title, 1);
        headers.addWidget(h_time)
        layout.addLayout(headers)
        layout.addSpacing(10)

        tracks = [
            ("Gymnopédie No. 1", "Erik Satie, Alexandre Tharaud", "03:12", True),
            ("Suite Bergamasque, L. 75: III. Clair de Lune", "Claude Debussy", "04:45", False),
            ("Spiegel im Spiegel", "Arvo Pärt", "08:14", False),
            ("Variations on the Kanon by Pachelbel", "George Winston", "05:21", False),
            ("6 Klavierstücke, Op. 118: No. 2", "Johannes Brahms", "06:05", False),
        ]

        for i, (t, a, dur, active) in enumerate(tracks):
            row = QHBoxLayout()
            row.setContentsMargins(10, 5, 10, 5)

            num = QLabel("🔊" if active else f"{i + 1:02d}")
            num.setFixedWidth(30)
            num.setStyleSheet("color: #ff5555; font-size: 12px;" if active else "color: #888; font-size: 11px;")

            art = QLabel()
            art.setFixedSize(40, 40)
            art.setStyleSheet("background-color: #e0e0e0; border-radius: 2px;")

            info = QVBoxLayout()
            info.setSpacing(2)
            t_lbl = QLabel(t)
            t_lbl.setStyleSheet(
                "color: #ff5555; font-size: 13px; font-weight: bold;" if active else "color: white; font-size: 13px;")
            a_lbl = QLabel(a)
            a_lbl.setStyleSheet("color: #888; font-size: 11px;")
            info.addWidget(t_lbl)
            info.addWidget(a_lbl)

            dur_lbl = QLabel(dur)
            dur_lbl.setStyleSheet("color: #888; font-size: 11px;")

            row.addWidget(num)
            row.addWidget(art)
            row.addSpacing(10)
            row.addLayout(info, 1)
            row.addWidget(dur_lbl)

            layout.addLayout(row)

        layout.addStretch()

        footer = QLabel("432 COMPOSITIONS")
        footer.setStyleSheet("color: #666; font-size: 10px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(footer)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(content)
        return scroll

    # ==========================================
    # SIDEBAR & PLAYER BAR HELPERS
    # ==========================================
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 30, 20, 20)
        layout.setSpacing(10)

        logo_layout = QHBoxLayout()
        logo_dot = QLabel("●");
        logo_dot.setStyleSheet("color: #ff4444; font-size: 20px;")
        logo_text = QLabel("Aura");
        logo_text.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        logo_layout.addWidget(logo_dot);
        logo_layout.addWidget(logo_text);
        logo_layout.addStretch()
        layout.addLayout(logo_layout)
        layout.addSpacing(30)

        self.nav_buttons = []
        for text, icon, index in [("Home", "🏠", 0), ("Search", "🔍", 1), ("Your Library", "📚", 2)]:
            btn = QLabel(f"{icon}   {text}")
            btn.setObjectName("NavLabel")
            btn.setCursor(Qt.PointingHandCursor)
            self.nav_buttons.append((btn, index))
            btn.mousePressEvent = lambda event, i=index: self.switch_page(i)
            layout.addWidget(btn)

        self.switch_page(0)

        layout.addSpacing(30)
        curated_lbl = QLabel("CURATED")
        curated_lbl.setObjectName("SectionTitle")
        layout.addWidget(curated_lbl)
        layout.addSpacing(10)

        for text, icon in [("Playlists", "🎵"), ("Favorites", "❤️")]:
            btn = QLabel(f"{icon}   {text}")
            btn.setObjectName("NavLabel")
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)

        layout.addStretch()
        return sidebar

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
        now = QLabel("01:24");
        now.setStyleSheet("color: #888; font-size: 10px;")
        slider = QSlider(Qt.Horizontal);
        slider.setValue(30)
        total = QLabel("05:42");
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
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())