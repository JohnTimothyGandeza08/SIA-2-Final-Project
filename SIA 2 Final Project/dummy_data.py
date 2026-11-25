# dummy_data.py
from dataclasses import dataclass

@dataclass
class Track:
    title: str
    album: str
    added: str
    length: str
    artist: str

TRACKS = [
    Track("Gymnopédie No. 1", "Erik Satie, Alexandre Tharaud", "2 days Ago", "03:12", "Erik Satie"),
    Track("Suite Bergamasque, L. 75: III. Clair de Lune", "Claude Debussy, Alexis Weissenberg", "2 days Ago", "04:45", "Claude Debussy"),
    Track("Spiegel im Spiegel", "Arvo Pärt, Vladimir Spivakov", "2 days Ago", "08:14", "Arvo Pärt"),
    Track("Variations on the Kanon by Pachelbel", "George Winston", "2 days Ago", "05:21", "George Winston"),
    Track("6 Klavierstücke, Op. 118: No. 2, Intermezzo in A Major", "Johannes Brahms, Radu Lupu", "2 days Ago", "06:05", "Johannes Brahms"),
]