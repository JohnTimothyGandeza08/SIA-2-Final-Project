# theme.py
DARK_THEME = """
QMainWindow, QWidget#MainContainer { 
    background-color: #000000; 
}
QWidget#ContentArea { 
    background-color: #0f0f0f; 
    border-top-left-radius: 12px; 
    border-bottom-left-radius: 12px; 
}
QLabel { 
    color: #e0e0e0; 
    font-family: "Segoe UI", Arial, sans-serif; 
}
QLabel#HeaderTitle { 
    font-size: 32px; 
    font-weight: bold; 
    color: white; 
}
QLabel#SectionTitle { 
    font-size: 12px; 
    font-weight: bold; 
    color: #888888; 
    letter-spacing: 1px; 
}

/* --- TOP NAVIGATION --- */
QPushButton#NavTopBtn {
    background-color: transparent;
    color: #888;
    border: none;
    font-size: 12px;
    font-weight: bold;
    padding: 6px 12px;
    border-radius: 6px;
}
QPushButton#NavTopBtn:hover {
    color: white;
}
QPushButton#NavTopBtnActive {
    background-color: #0055ff;
    color: white;
    border: none;
    font-size: 12px;
    font-weight: bold;
    padding: 6px 12px;
    border-radius: 6px;
}

/* --- HEADER SEGMENTED CONTROL --- */
QWidget#SegmentedControl {
    background-color: #141414;
    border-radius: 16px;
    border: 1px solid #222;
}
QPushButton#SegBtn {
    background-color: transparent;
    color: #888;
    border: none;
    border-radius: 12px;
    padding: 5px 15px; /* FIXED PADDING */
    font-size: 11px;
    font-weight: bold;
}
QPushButton#SegBtn:hover { 
    color: white; 
}
QPushButton#SegBtnActive {
    background-color: #1e1e1e;
    color: white;
    border: none;
    border-radius: 12px;
    padding: 5px 15px; /* FIXED PADDING */
    font-size: 11px;
    font-weight: bold;
}

/* --- SEARCH BAR & FILTERS --- */
QLineEdit#SearchBar {
    background-color: #1a1a1a; 
    border: none; 
    border-radius: 6px;
    padding-left: 15px; 
    color: white; 
    font-size: 13px;
}
QPushButton#FilterBtn {
    background-color: transparent; 
    color: #888888; 
    border: 1px solid #333;
    border-radius: 15px; 
    padding: 4px 15px; 
    font-size: 12px;
}
QPushButton#FilterBtn:hover, QPushButton#FilterBtnActive {
    background-color: #0055ff; 
    color: white; 
    border: 1px solid #0055ff; /* Fixed 'order:' typo */
}

/* --- CARDS --- */
QFrame#LibraryCard {
    background-color: #181818; 
    border-radius: 8px;
}
QFrame#LibraryCard:hover { 
    background-color: #282828; 
}
QFrame#AddPlaylistCard {
    background-color: transparent;
    border: 1px dashed #444; 
    border-radius: 8px;
}
QFrame#AddPlaylistCard:hover { 
    border: 1px dashed #0055ff; 
    background-color: #0f0f0f; 
}
QFrame#TableContainer { 
    background-color: #0c0c0c; 
    border-radius: 8px; 
    border: 1px solid #1a1a1a;
}
QFrame#HeroBanner {
    background-color: #11141a;
    border-radius: 12px;
    border: 1px solid #1f1f1f;
}
QFrame#MixCard {
    background-color: #181a1f;
    border-radius: 8px;
    border: 1px solid #222;
}
QFrame#MixCard:hover { 
    background-color: #22252c; 
}
QFrame#MoodCard {
    border-radius: 8px;
    border: 1px solid #333;
}
QFrame#MoodCard:hover { 
    border: 1px solid #555; 
}
QFrame#RecentCard {
    background-color: #181a1f;
    border-radius: 6px;
    border: 1px solid #222;
}
QFrame#RecentCard:hover { 
    background-color: #22252c; 
}
QFrame#LikedBanner {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1e3a8a, stop:0.5 #0055ff, stop:1 #6b21a8);
    border-radius: 10px;
}
QFrame#ArtistCard {
    background-color: #181a1f;
    border-radius: 8px;
    border: 1px solid #222;
}
QFrame#ArtistCard:hover { 
    background-color: #22252c; 
}
QFrame#PlaylistRow {
    background-color: transparent;
    border-radius: 6px;
}
QFrame#PlaylistRow:hover { 
    background-color: #181818; 
}

/* --- TRACK ROWS --- */
QWidget#TrackRowWidget:hover { 
    background-color: #181818; 
    border-radius: 4px;
}
QLabel#TrackIndex { 
    color: #888888; 
    font-size: 11px;
}
QLabel#TrackIndexActive { 
    color: #0055ff; 
    font-size: 11px; 
    font-weight: bold; 
}
QLabel#TrackTitle { 
    color: #ffffff; 
    font-size: 13px; 
}
QLabel#TrackTitleActive { 
    color: #0055ff; 
    font-size: 13px; 
    font-weight: bold; 
}
QLabel#TrackSub { 
    color: #888888; 
    font-size: 11px; 
}
QLabel#TrackTime {
    color: #888888; 
    font-size: 11px; 
}

/* --- PLAYER BAR --- */
QWidget#PlayerBar { 
    background-color: #0f0f0f; 
    border-top: 1px solid #1a1a1a; 
}
QPushButton#PlayControls { 
    background-color: transparent; 
    color: white; 
    border: none; 
    font-size: 18px; 
}
QPushButton#PlayControls:hover { 
    color: #0055ff; 
}
QPushButton#MainPlayBtn { 
    background-color: white; 
    color: black; 
    border: none; 
    border-radius: 20px; 
    font-size: 16px; 
}
QPushButton#MainPlayBtn:hover { 
    background-color: #0055ff; 
    color: white; 
}

/* --- SLIDERS --- */
QSlider::groove:horizontal { 
    border: none; 
    height: 4px; 
    background: #333; 
    border-radius: 2px; 
}
QSlider::handle:horizontal { 
    background: white; 
    border: none; 
    width: 12px; 
    height: 12px; 
    margin: -4px 0;
    border-radius: 6px; 
}
QSlider::handle:horizontal:hover { 
    background: #0055ff; 
}
QSlider::sub-page:horizontal { 
    background: white; 
    border-radius: 2px; 
}
"""