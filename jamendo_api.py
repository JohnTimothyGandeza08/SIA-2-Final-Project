# jamendo_api.py
import requests
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QByteArray

CLIENT_ID = "58e2dbd9"

def fetch_trending_tracks(limit=4):
    # audioformat=mp32 forces Jamendo to send a valid playable MP3 link
    url = f"https://api.jamendo.com/v3.0/tracks/?client_id=58e2dbd9&format=json&limit={limit}&order=popularity_week&audioformat=mp32"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"[JAMENDO] Successfully fetched {len(results)} tracks.")
            
            # Debug: Show the first audio URL to prove it's valid
            if results:
                print(f"[JAMENDO] Sample Audio URL: {results[0].get('audio')}")
            return results
        return []
    except Exception as e:
        print(f"[JAMENDO ERROR] {e}")
        return []

def download_image(url):
    if not url or not url.strip():
        return None
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            image = QImage()
            image.loadFromData(QByteArray(response.content))
            return QPixmap(image)
    except Exception as e:
        print(f"[IMAGE ERROR] {e}")
    return None