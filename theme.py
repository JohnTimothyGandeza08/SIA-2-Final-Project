# theme.py
DARK_THEME = """

QMainWindow, QWidget#MainContainer { 
background-color: #000000; 
}

QWidget#Sidebar { 
background-color: #000000; 
border-right: 1px solid #1a1a1a; 
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

QLabel#NavLabel { 
color: #aaaaaa; 
font-size: 14px; 
font-weight: bold; 
padding: 8px 0px; 
}

QLabel#NavLabel:hover { 
color: #ffffff; 
}

QLabel#NavLabelActive { 
color: #0055ff; 
font-size: 14px; 
font-weight: bold; 
padding: 8px 0px;
}


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
    order: 1px solid #0055ff;
}


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
background-color: #000000; 
border-radius: 8px; 
}

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
QFrame#HeroBanner {
    background-color: #11141a;
    border-radius: 12px;
    border: 1px solid #222;
}

QFrame#MixCard {
    background-color: #181a1f;
    border-radius: 10px;
    border: 1px solid #222;
}

QFrame#MixCard:hover, QFrame#RecentCard:hover, QFrame#ArtistCard:hover {
    background-color: #22252c;
}

QFrame#RecentCard {
    background-color: #181a1f;
    border-radius: 8px;
}

QFrame#ArtistCard {
    background-color: #181a1f;
    border-radius: 8px;
    border: 1px solid #222;
}

QFrame#PlaylistRow {
    background-color: transparent;
    border-radius: 6px;
}
QFrame#PlaylistRow:hover {
    background-color: #181818;
}

QFrame#LikedBanner {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1e3a8a, stop:0.5 #0055ff, stop:1 #6b21a8);
    border-radius: 12px;
}
"""