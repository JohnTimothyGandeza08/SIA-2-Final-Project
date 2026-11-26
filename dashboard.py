# dashboard.py
import sys
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame,
    QSlider, QGridLayout, QStackedWidget
)
from PySide6.QtCore import Qt, QPointF, QUrl, QThread, Signal, QByteArray
from PySide6.QtGui import QPainter, QColor, QPolygonF, QBrush, QPixmap, QImage
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from theme import DARK_THEME
import jamendo_api


class ClickableFrame(QFrame):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SearchWorker(QThread):
    finished_search = Signal(int, str, dict, dict)

    def __init__(self, request_id, query):
        super().__init__()
        self.request_id = request_id
        self.query = query

    def run(self):
        results = jamendo_api.search_catalog(
            self.query,
            artist_limit=4,
            artist_tracks_limit=6,
            track_limit=20,
        )

        # Pre-fetch raw image bytes off the GUI thread (QPixmap conversion stays on main thread)
        urls = set()
        for artist in results.get("artists", []):
            if artist.get("image"):
                urls.add(artist["image"])
            for t in artist.get("tracks", []):
                img = t.get("album_image") or t.get("image")
                if img:
                    urls.add(img)
        for t in results.get("tracks", []):
            img = t.get("album_image") or t.get("image")
            if img:
                urls.add(img)

        image_bytes = {}
        url_list = list(urls)
        if url_list:
            with ThreadPoolExecutor(max_workers=8) as pool:
                fetched = list(pool.map(jamendo_api.download_image_bytes, url_list))
            for url, raw in zip(url_list, fetched):
                if raw:
                    image_bytes[url] = raw

        self.finished_search.emit(self.request_id, self.query, results, image_bytes)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pulse")
        self.resize(1100, 800)
        self.setStyleSheet(DARK_THEME)

        # Setup Media Player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.current_audio_url = ""
        self.current_playlist = []
        self.current_index = -1
        self._expected_duration_ms = 0
        self._seeking = False

        self.home_play_buttons = []
        self.search_play_buttons = []
        self.home_duration_labels = []
        self.search_duration_labels = []

        self._pixmap_cache = {}
        self._search_request_id = 0
        self._active_workers = set()
        self.search_filter = "ALL"
        self.last_search_results = None

        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.audio_output.setVolume(0.8)

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
        self.header_search = QLineEdit()
        self.header_search.setObjectName("SearchBar")
        self.header_search.setPlaceholderText("🔍 Search artists or songs...")
        self.header_search.setFixedSize(240, 30)
        self.header_search.returnPressed.connect(self._on_header_search)

        profile = QLabel("J")
        profile.setFixedSize(30, 30)
        profile.setAlignment(Qt.AlignCenter)
        profile.setStyleSheet("background: white; color: black; border-radius: 15px; font-weight: bold; font-size: 12px;")

        h_layout.addLayout(logo_box)
        h_layout.addStretch()
        h_layout.addWidget(seg_widget)
        h_layout.addStretch()
        h_layout.addWidget(self.header_search)
        h_layout.addWidget(profile)

        # --- 2. NAVBAR ---
        navbar = QWidget()
        navbar.setObjectName("TopNavBar")
        navbar.setFixedHeight(56)
        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(30, 0, 30, 0)
        nav_layout.setSpacing(15)

        self.nav_buttons = []
        nav_items = [("🏠  Home", 0), ("🔍  Search", 1), ("📚  Your Library", 2)]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("NavTopBtnActive" if index == 0 else "NavTopBtn")
            btn.setCursor(Qt.PointingHandCursor)
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

    def set_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setObjectName("NavTopBtnActive" if i == index else "NavTopBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _pixmap_from_url(self, url, width, height):
        if not url:
            return None
        pixmap = self._pixmap_cache.get(url)
        if pixmap is None:
            pixmap = jamendo_api.download_image(url)
            if pixmap:
                self._pixmap_cache[url] = pixmap
        if pixmap:
            return pixmap.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        return None

    def play_track(self, track, playlist=None, index=0):
        audio_url = track.get("audio")
        track_name = track.get("name", "Unknown Track")
        artist_name = track.get("artist_name", "Unknown Artist")
        duration_sec = track.get("duration", 0)
        img_url = track.get("album_image") or track.get("image")

        if playlist is not None:
            self.current_playlist = list(playlist)
            self.current_index = index

        self.play_jamendo_track(
            audio_url,
            track_name,
            artist_name,
            duration_sec=duration_sec,
            img_url=img_url,
        )

    def play_jamendo_track(self, audio_url, track_name, artist_name, duration_sec=0, img_url=None):
        if not audio_url or not audio_url.startswith("http"):
            print(f"[PLAYER ERROR] Invalid audio URL: {audio_url}")
            return

        same_track = self.current_audio_url == audio_url
        if same_track and self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            return

        if not same_track:
            print(f"Playing: {track_name} from {audio_url}")
            self.current_audio_url = audio_url
            self.player_title.setText(track_name)
            self.player_artist.setText(artist_name or "Unknown Artist")

            # Update player bar art
            scaled_art = self._pixmap_from_url(img_url, 50, 50)
            if scaled_art:
                self.player_art.setPixmap(scaled_art)
            else:
                self.player_art.clear()

            # Sync song bar immediately with the track's known duration
            self._expected_duration_ms = max(0, int(duration_sec or 0) * 1000)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setRange(0, self._expected_duration_ms)
            self.progress_slider.setValue(0)
            self.progress_slider.blockSignals(False)
            self.time_now.setText("00:00")
            self.time_total.setText(self._format_time(self._expected_duration_ms))

            self.media_player.setSource(QUrl(audio_url))

        self.media_player.play()

    def play_previous_track(self):
        if not self.current_playlist:
            return
        if self.media_player.position() > 3000:
            self.media_player.setPosition(0)
            return
        if self.current_index > 0:
            new_idx = self.current_index - 1
            self.play_track(self.current_playlist[new_idx], self.current_playlist, new_idx)

    def play_next_track(self):
        if not self.current_playlist:
            return
        if self.current_index + 1 < len(self.current_playlist):
            new_idx = self.current_index + 1
            self.play_track(self.current_playlist[new_idx], self.current_playlist, new_idx)

    def toggle_play_pause(self):
        if not self.current_audio_url:
            return
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _refresh_play_buttons(self, playing):
        if hasattr(self, "play_pause_btn"):
            self.play_pause_btn.setText("⏸" if playing else "▶")
        for btn, url in self.home_play_buttons + self.search_play_buttons:
            btn.setText("⏸" if playing and url == self.current_audio_url else "▶")

    def _on_playback_state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._refresh_play_buttons(playing)

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next_track()

    def _format_time(self, ms):
        seconds = max(0, int(ms // 1000))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _on_position_changed(self, position):
        if self._seeking or not hasattr(self, "progress_slider"):
            return
        if position > self.progress_slider.maximum():
            self.progress_slider.setMaximum(position)
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(position)
        self.progress_slider.blockSignals(False)
        self.time_now.setText(self._format_time(position))

    def _on_duration_changed(self, duration):
        if not hasattr(self, "progress_slider"):
            return
        effective_duration = duration if duration > 0 else self._expected_duration_ms
        self.progress_slider.setMaximum(max(effective_duration, 0))
        self.time_total.setText(self._format_time(effective_duration))

        if duration > 0:
            formatted = self._format_time(duration)
            for lbl, url in self.home_duration_labels + self.search_duration_labels:
                if url == self.current_audio_url:
                    lbl.setText(formatted)

    def _on_seek_pressed(self):
        self._seeking = True

    def _on_seek_released(self):
        self._seeking = False
        self.media_player.setPosition(self.progress_slider.value())

    def _on_seek_moved(self, value):
        self.time_now.setText(self._format_time(value))

    def _on_volume_changed(self, value):
        self.audio_output.setVolume(value / 100)

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
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

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

        # --- LIVE JAMENDO TRACKS ---
        mf_head = QHBoxLayout()
        mf_title = QLabel("Trending on Jamendo")
        mf_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        tracks = jamendo_api.fetch_trending_tracks(limit=20)
        mf_count = QLabel(f"{len(tracks)} tracks")
        mf_count.setStyleSheet("color: #666; font-size: 10px;")
        mf_head.addWidget(mf_title)
        mf_head.addStretch()
        mf_head.addWidget(mf_count)
        layout.addLayout(mf_head)

        if not tracks:
            layout.addWidget(QLabel("Failed to load Jamendo tracks. Check terminal for details."))
        else:
            mf_grid = QGridLayout()
            mf_grid.setSpacing(15)

            for idx, track in enumerate(tracks):
                card = QFrame()
                card.setObjectName("MixCard")
                card.setFixedHeight(125)
                c_layout = QHBoxLayout(card)
                c_layout.setContentsMargins(12, 12, 12, 12)

                # Album Art
                art_label = QLabel()
                art_label.setFixedSize(84, 84)
                art_label.setStyleSheet("background-color: #333; border-radius: 6px;")

                img_url = track.get("album_image") or track.get("image")
                pixmap = self._pixmap_from_url(img_url, 84, 84)
                if pixmap:
                    art_label.setPixmap(pixmap)

                # Text Info
                text_col = QVBoxLayout()
                text_col.setSpacing(3)

                top_meta = QHBoxLayout()
                tag = QLabel("TRACK")
                tag.setStyleSheet("color: #0055ff; font-size: 8px; font-weight: bold; letter-spacing: 0.5px;")
                dur_ms = max(0, int(track.get("duration") or 0) * 1000)
                dur_lbl = QLabel(self._format_time(dur_ms))
                dur_lbl.setStyleSheet("color: #777; font-size: 9px;")
                top_meta.addWidget(tag)
                top_meta.addStretch()
                top_meta.addWidget(dur_lbl)

                full_name = track.get("name", "Unknown Track")
                display_name = full_name if len(full_name) <= 18 else full_name[:16] + "..."
                t = QLabel(display_name)
                t.setToolTip(full_name)
                t.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")

                artist_name = track.get("artist_name", "Unknown Artist")
                display_artist = artist_name if len(artist_name) <= 22 else artist_name[:20] + "..."
                s = QLabel(display_artist)
                s.setToolTip(artist_name)
                s.setStyleSheet("color: #888; font-size: 10px;")

                text_col.addLayout(top_meta)
                text_col.addWidget(t)
                text_col.addWidget(s)
                text_col.addStretch()

                # Play Button
                play_btn = QPushButton("▶")
                play_btn.setFixedSize(26, 26)
                play_btn.setCursor(Qt.PointingHandCursor)
                play_btn.setStyleSheet("background-color: #1a1a1a; color: #0055ff; border-radius: 13px; font-weight: bold; font-size: 10px;")

                audio_url = track.get("audio")
                if audio_url:
                    self.home_play_buttons.append((play_btn, audio_url))
                    self.home_duration_labels.append((dur_lbl, audio_url))
                    play_btn.clicked.connect(
                        lambda checked, tr=track, pl=tracks, i=idx: self.play_track(tr, pl, i)
                    )

                c_layout.addWidget(art_label)
                c_layout.addSpacing(8)
                c_layout.addLayout(text_col, 1)
                c_layout.addWidget(play_btn, alignment=Qt.AlignBottom)

                mf_grid.addWidget(card, idx // 4, idx % 4)

            for col in range(4):
                mf_grid.setColumnStretch(col, 1)
            layout.addLayout(mf_grid)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ==========================================
    # PAGE 2: SEARCH
    # ==========================================
    def build_search_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(18)

        # Search input row
        search_wrapper = QHBoxLayout()
        search_wrapper.addStretch()
        self.big_search = QLineEdit()
        self.big_search.setObjectName("SearchBar")
        self.big_search.setPlaceholderText("Search artists, songs, or tags...")
        self.big_search.setFixedSize(420, 38)
        self.big_search.setStyleSheet("font-size: 12px; padding-left: 15px; padding-right: 36px; border-radius: 6px; background-color: #1a1a1a; border: 1px solid #333;")
        self.big_search.returnPressed.connect(lambda: self.run_search(self.big_search.text()))

        clear_btn = QPushButton("✕")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("background: transparent; color: #888; border: none; font-size: 12px;")
        clear_btn.clicked.connect(self._clear_search)

        sbl = QHBoxLayout(self.big_search)
        sbl.setContentsMargins(0, 0, 12, 0)
        sbl.addStretch()
        sbl.addWidget(clear_btn)

        search_go_btn = QPushButton("Search")
        search_go_btn.setFixedHeight(38)
        search_go_btn.setCursor(Qt.PointingHandCursor)
        search_go_btn.setStyleSheet("background-color: #0055ff; color: white; border-radius: 6px; padding: 0 16px; font-weight: bold; font-size: 12px;")
        search_go_btn.clicked.connect(lambda: self.run_search(self.big_search.text()))

        search_wrapper.addWidget(self.big_search)
        search_wrapper.addSpacing(8)
        search_wrapper.addWidget(search_go_btn)
        search_wrapper.addStretch()

        # Filter tabs
        filter_wrapper = QHBoxLayout()
        filter_wrapper.addStretch()
        self.search_filter_buttons = {}
        for f in ["ALL", "ARTISTS", "SONGS"]:
            btn = QPushButton(f)
            btn.setObjectName("FilterBtnActive" if f == self.search_filter else "FilterBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, mode=f: self._set_search_filter(mode))
            filter_wrapper.addWidget(btn)
            self.search_filter_buttons[f] = btn
        filter_wrapper.addStretch()

        layout.addLayout(search_wrapper)
        layout.addLayout(filter_wrapper)

        self.search_status_label = QLabel("Search Jamendo for an artist or song title.")
        self.search_status_label.setAlignment(Qt.AlignCenter)
        self.search_status_label.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(self.search_status_label)

        # Dynamic results container
        self.search_results_layout = QVBoxLayout()
        self.search_results_layout.setSpacing(16)
        layout.addLayout(self.search_results_layout)

        # Explorations
        explore_lbl = QLabel("EXPLORATIONS")
        explore_lbl.setObjectName("SectionTitle")
        layout.addWidget(explore_lbl)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        explorations = [
            ("Ambient", "Deep focus"),
            ("Classical", "Piano & strings"),
            ("Lo-Fi", "Quiet beats"),
            ("Electronic", "Synth & pulse"),
        ]
        for i, (title, sub) in enumerate(explorations):
            card = ClickableFrame()
            card.setObjectName("TableContainer")
            card.setFixedHeight(90)
            card.setCursor(Qt.PointingHandCursor)
            card.clicked.connect(lambda q=title: self._quick_search(q))
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
        scroll.setWidget(content)
        return scroll

    def _on_header_search(self):
        query = self.header_search.text().strip()
        if not query:
            return
        self.set_page(1)
        self.big_search.setText(query)
        self.run_search(query)

    def _quick_search(self, query):
        self.big_search.setText(query)
        self.run_search(query)

    def _clear_search(self):
        self._search_request_id += 1
        self.big_search.clear()
        self.last_search_results = None
        self._clear_search_results_ui()
        self.search_status_label.setText("Search Jamendo for an artist or song title.")
        self.search_status_label.show()

    def _set_search_filter(self, mode):
        self.search_filter = mode
        for f, btn in self.search_filter_buttons.items():
            btn.setObjectName("FilterBtnActive" if f == mode else "FilterBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if self.last_search_results is not None:
            self._render_search_results(self.last_search_results)

    def run_search(self, query):
        query = (query or "").strip()
        if not query:
            self._clear_search()
            return

        self._search_request_id += 1
        request_id = self._search_request_id
        self.search_status_label.setText(f'Searching Jamendo for "{query}"...')
        self.search_status_label.show()

        worker = SearchWorker(request_id, query)
        self._active_workers.add(worker)
        worker.finished_search.connect(self._on_search_finished)
        worker.finished.connect(lambda w=worker: self._active_workers.discard(w))
        worker.start()

    def _on_search_finished(self, request_id, query, results, image_bytes):
        if request_id != self._search_request_id:
            return

        # Convert downloaded image bytes to QPixmap on the GUI thread
        for url, raw in image_bytes.items():
            if url not in self._pixmap_cache:
                img = QImage()
                if img.loadFromData(QByteArray(raw)):
                    self._pixmap_cache[url] = QPixmap(img)

        self.last_search_results = results
        self._render_search_results(results)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _clear_search_results_ui(self):
        self.search_play_buttons.clear()
        self.search_duration_labels.clear()
        self._clear_layout(self.search_results_layout)

    def _toggle_heart(self, btn):
        liked = btn.text() == "♥"
        btn.setText("♡" if liked else "♥")
        btn.setStyleSheet(
            "background: transparent; border: none; color: #888; font-size: 13px;"
            if liked
            else "background: transparent; border: none; color: #ff5555; font-size: 13px;"
        )

    def _render_search_results(self, results):
        self._clear_search_results_ui()

        artists = results.get("artists", [])
        tracks = results.get("tracks", [])
        show_artists = self.search_filter in ("ALL", "ARTISTS")
        show_songs = self.search_filter in ("ALL", "SONGS")

        if (not show_artists or not artists) and (not show_songs or not tracks):
            self.search_status_label.setText("No matching artists or playable songs found.")
            self.search_status_label.show()
            return

        self.search_status_label.hide()

        # --- ARTISTS + THEIR SONGS ---
        if show_artists and artists:
            artists_lbl = QLabel("ARTISTS")
            artists_lbl.setObjectName("SectionTitle")
            self.search_results_layout.addWidget(artists_lbl)

            for artist in artists:
                artist_tracks = artist.get("tracks", [])
                artist_card = QFrame()
                artist_card.setObjectName("TableContainer")
                ac_layout = QHBoxLayout(artist_card)
                ac_layout.setContentsMargins(20, 18, 20, 18)
                ac_layout.setSpacing(20)

                art_img = QLabel()
                art_img.setFixedSize(130, 130)
                art_img.setStyleSheet("background-color: #333; border-radius: 6px;")
                pixmap = self._pixmap_from_url(artist.get("image"), 130, 130)
                if pixmap:
                    art_img.setPixmap(pixmap)

                info_layout = QVBoxLayout()
                info_layout.setAlignment(Qt.AlignVCenter)
                artist_tag = QLabel("ARTIST")
                artist_tag.setStyleSheet("color: #ff5555; font-size: 9px; font-weight: bold;")
                artist_name_lbl = QLabel(artist.get("name", "Unknown Artist"))
                artist_name_lbl.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
                artist_name_lbl.setWordWrap(True)
                track_count = len(artist_tracks)
                artist_stats = QLabel(f"{track_count} playable song{'s' if track_count != 1 else ''}")
                artist_stats.setStyleSheet("color: #aaa; font-size: 11px;")
                info_layout.addWidget(artist_tag)
                info_layout.addWidget(artist_name_lbl)
                info_layout.addWidget(artist_stats)

                main_play_btn = QPushButton("▶")
                main_play_btn.setObjectName("MainPlayBtn")
                main_play_btn.setFixedSize(44, 44)
                main_play_btn.setCursor(Qt.PointingHandCursor)
                if artist_tracks:
                    first_url = artist_tracks[0].get("audio")
                    if first_url:
                        self.search_play_buttons.append((main_play_btn, first_url))
                    main_play_btn.clicked.connect(
                        lambda checked, tr=artist_tracks[0], pl=artist_tracks: self.play_track(tr, pl, 0)
                    )
                else:
                    main_play_btn.setEnabled(False)

                tracks_layout = QVBoxLayout()
                tracks_layout.setSpacing(10)
                if not artist_tracks:
                    empty_lbl = QLabel("No playable tracks available for this artist.")
                    empty_lbl.setStyleSheet("color: #777; font-size: 11px;")
                    tracks_layout.addWidget(empty_lbl)
                else:
                    for idx, tr in enumerate(artist_tracks):
                        t_row = QHBoxLayout()
                        t_play = QPushButton("▶")
                        t_play.setFixedSize(22, 22)
                        t_play.setCursor(Qt.PointingHandCursor)
                        t_play.setStyleSheet("background: transparent; color: #aaa; border: none; font-size: 10px;")

                        t_name = QLabel(tr.get("name", "Unknown Track"))
                        t_name.setStyleSheet("color: white; font-size: 12px;")
                        t_album = QLabel(tr.get("album_name") or "Single")
                        t_album.setStyleSheet("color: #888; font-size: 11px;")

                        dur_ms = max(0, int(tr.get("duration") or 0) * 1000)
                        t_time = QLabel(self._format_time(dur_ms))
                        t_time.setStyleSheet("color: #888; font-size: 11px;")

                        t_heart = QPushButton("♡")
                        t_heart.setCursor(Qt.PointingHandCursor)
                        t_heart.setStyleSheet("background: transparent; border: none; color: #888; font-size: 13px;")
                        t_heart.clicked.connect(lambda checked, b=t_heart: self._toggle_heart(b))

                        audio_url = tr.get("audio")
                        if audio_url:
                            self.search_play_buttons.append((t_play, audio_url))
                            self.search_duration_labels.append((t_time, audio_url))
                            t_play.clicked.connect(
                                lambda checked, item=tr, pl=artist_tracks, i=idx: self.play_track(item, pl, i)
                            )

                        t_row.addWidget(t_play)
                        t_row.addWidget(t_name, 1)
                        t_row.addWidget(t_album, 1)
                        t_row.addWidget(t_time)
                        t_row.addSpacing(8)
                        t_row.addWidget(t_heart)
                        tracks_layout.addLayout(t_row)

                ac_layout.addWidget(art_img)
                ac_layout.addLayout(info_layout, 1)
                ac_layout.addWidget(main_play_btn)
                ac_layout.addLayout(tracks_layout, 2)
                self.search_results_layout.addWidget(artist_card)

        # --- SONGS LIST ---
        if show_songs and tracks:
            songs_lbl = QLabel(f"SONGS ({len(tracks)})")
            songs_lbl.setObjectName("SectionTitle")
            self.search_results_layout.addWidget(songs_lbl)

            songs_container = QFrame()
            songs_container.setObjectName("TableContainer")
            sc_layout = QVBoxLayout(songs_container)
            sc_layout.setContentsMargins(16, 12, 16, 12)
            sc_layout.setSpacing(6)

            for idx, tr in enumerate(tracks):
                row = QFrame()
                row.setObjectName("PlaylistRow")
                r_layout = QHBoxLayout(row)
                r_layout.setContentsMargins(4, 6, 4, 6)
                r_layout.setSpacing(12)

                play_btn = QPushButton("▶")
                play_btn.setFixedSize(26, 26)
                play_btn.setCursor(Qt.PointingHandCursor)
                play_btn.setStyleSheet("background-color: #222; color: #0055ff; border: none; border-radius: 13px; font-size: 10px;")

                thumb = QLabel()
                thumb.setFixedSize(36, 36)
                thumb.setStyleSheet("background-color: #333; border-radius: 4px;")
                img_url = tr.get("album_image") or tr.get("image")
                pixmap = self._pixmap_from_url(img_url, 36, 36)
                if pixmap:
                    thumb.setPixmap(pixmap)

                title_col = QVBoxLayout()
                title_col.setSpacing(1)
                title_lbl = QLabel(tr.get("name", "Unknown Track"))
                title_lbl.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
                artist_lbl = QLabel(tr.get("artist_name", "Unknown Artist"))
                artist_lbl.setStyleSheet("color: #888; font-size: 10px;")
                title_col.addWidget(title_lbl)
                title_col.addWidget(artist_lbl)

                album_lbl = QLabel(tr.get("album_name") or "Single")
                album_lbl.setStyleSheet("color: #777; font-size: 11px;")

                dur_ms = max(0, int(tr.get("duration") or 0) * 1000)
                dur_lbl = QLabel(self._format_time(dur_ms))
                dur_lbl.setStyleSheet("color: #888; font-size: 11px;")

                heart_btn = QPushButton("♡")
                heart_btn.setCursor(Qt.PointingHandCursor)
                heart_btn.setStyleSheet("background: transparent; border: none; color: #888; font-size: 13px;")
                heart_btn.clicked.connect(lambda checked, b=heart_btn: self._toggle_heart(b))

                audio_url = tr.get("audio")
                if audio_url:
                    self.search_play_buttons.append((play_btn, audio_url))
                    self.search_duration_labels.append((dur_lbl, audio_url))
                    play_btn.clicked.connect(
                        lambda checked, item=tr, pl=tracks, i=idx: self.play_track(item, pl, i)
                    )

                r_layout.addWidget(play_btn)
                r_layout.addWidget(thumb)
                r_layout.addLayout(title_col, 2)
                r_layout.addWidget(album_lbl, 1)
                r_layout.addWidget(dur_lbl)
                r_layout.addWidget(heart_btn)
                sc_layout.addWidget(row)

            self.search_results_layout.addWidget(songs_container)

        # Keep active play/pause icon state synchronized after re-rendering
        playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self._refresh_play_buttons(playing)

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

        layout = QHBoxLayout(player_bar)
        layout.setContentsMargins(20, 10, 20, 10)

        left = QHBoxLayout()
        self.player_art = QLabel()
        self.player_art.setFixedSize(50, 50)
        self.player_art.setStyleSheet("background-color: #222; border-radius: 4px;")
        info = QVBoxLayout()
        info.setSpacing(2)

        self.player_title = QLabel("Select a track")
        self.player_title.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        self.player_artist = QLabel("Jamendo")
        self.player_artist.setStyleSheet("color: #888; font-size: 10px;")

        info.addWidget(self.player_title)
        info.addWidget(self.player_artist)
        left.addWidget(self.player_art)
        left.addSpacing(10)
        left.addLayout(info)
        left.addStretch()

        center = QVBoxLayout()
        center.setSpacing(5)
        controls = QHBoxLayout()
        controls.setAlignment(Qt.AlignCenter)

        prev_btn = QPushButton("⏮")
        prev_btn.setObjectName("PlayControls")
        prev_btn.setCursor(Qt.PointingHandCursor)
        prev_btn.clicked.connect(self.play_previous_track)
        controls.addWidget(prev_btn)

        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setObjectName("MainPlayBtn")
        self.play_pause_btn.setFixedSize(32, 32)
        self.play_pause_btn.setCursor(Qt.PointingHandCursor)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        controls.addWidget(self.play_pause_btn)

        next_btn = QPushButton("⏭")
        next_btn.setObjectName("PlayControls")
        next_btn.setCursor(Qt.PointingHandCursor)
        next_btn.clicked.connect(self.play_next_track)
        controls.addWidget(next_btn)

        progress = QHBoxLayout()
        self.time_now = QLabel("00:00")
        self.time_now.setStyleSheet("color: #888; font-size: 9px;")
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderPressed.connect(self._on_seek_pressed)
        self.progress_slider.sliderReleased.connect(self._on_seek_released)
        self.progress_slider.sliderMoved.connect(self._on_seek_moved)
        self.time_total = QLabel("00:00")
        self.time_total.setStyleSheet("color: #888; font-size: 9px;")
        progress.addWidget(self.time_now)
        progress.addWidget(self.progress_slider)
        progress.addWidget(self.time_total)
        center.addLayout(controls)
        center.addLayout(progress)

        right = QHBoxLayout()
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("color: #888; font-size: 12px;")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(100)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        right.addWidget(vol_icon)
        right.addWidget(self.vol_slider)

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