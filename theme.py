# theme.py
DARK_THEME = """
QMainWindow, QWidget#MainContainer { 
background-color: #000000; 
}
QWidget#ContentArea { 
background-color: #0f0f0f; 
}
QLabel { 
color: #e0e0e0; 
font-family: "Segoe UI", Arial, sans-serif; 
}
QLabel#SectionTitle { 
font-size: 12px; 
font-weight: bold; 
color: #888888; 
letter-spacing: 1px; 
}

/* --- HEADER --- */
QWidget#TopHeader { 
background-color: #050505; 
border-bottom: 1px solid #1a1a1a; 
}

/* Segmented Control - FIXED SIZING TO PREVENT SQUISHING */
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
    font-size: 12px; 
    font-weight: bold;
}
QPushButton#SegBtn:hover { color: white; }
QPushButton#SegBtnActive { 
    background-color: #1e1e1e; 
    color: white; 
    border: none; 
    border-radius: 12px; 
}

/* --- NAVBAR --- */
QWidget#TopNavBar { 
background-color: #0a0a0a; 
border-bottom: 1px solid #1a1a1a; 
}
QPushButton#NavTopBtn { 
background-color: transparent; 
color: #888; 
border: none; 
font-size: 13px; 
font-weight: bold; 
padding: 6px 16px; 
border-radius: 6px; 
}
QPushButton#NavTopBtn:hover { 
color: white; 
}
QPushButton#NavTopBtnActive { 
background-color: #0055ff; 
color: white; 
border: none; 
font-size: 13px; 
font-weight: bold; 
padding: 6px 16px; 
border-radius: 6px; 
}

/* --- SEARCH & FILTERS --- */
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
color: #888; 
border: 1px solid #333; 
border-radius: 15px;
padding: 4px 15px; 
font-size: 12px; 
}
QPushButton#FilterBtn:hover, QPushButton#FilterBtnActive {
 background-color: #0055ff;
 color: white;
 border: 1px solid #0055ff; 
}

/* --- CARDS --- */
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
QFrame#RecentCard { 
background-color: #181a1f; 
border-radius: 6px; 
border: 1px solid #222; 
}
QFrame#RecentCard:hover { 
background-color: #22252c; 
}
QFrame#LikedBanner { 
background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e3a8a, stop:0.5 #0055ff, stop:1 #6b21a8); 
border-radius: 10px; 
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
QFrame#TableContainer { 
background-color: #0c0c0c; 
border-radius: 8px; 
border: 1px solid #1a1a1a; 
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
border-radius: 18px; 
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
QSlider::sub-page:horizontal { 
background: white; 
border-radius: 2px; 
}
"""