# jamendo_api.py
import requests
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QByteArray

CLIENT_ID = "58e2dbd9"

def fetch_trending_tracks(limit=4):
    url = f"https://api.jamendo.com/v3.0/tracks/?client_id={CLIENT_ID}&format=json&limit={limit}&order=popularity_month&include=name+artist_name+image+audio"
    try:
        print(f"Fetching from Jamendo...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"[JAMENDO] Successfully fetched {len(results)} tracks.")
            return results
        else:
            print(f"[JAMENDO ERROR] Status {response.status_code}: {response.text}")
            return []
            
    except Exception as e:
        print(f"[JAMENDO ERROR] Python Exception: {e}")
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