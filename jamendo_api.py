# jamendo_api.py
import requests
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QByteArray

# ONLY USE THE CLIENT ID (Never put your Secret Key here)
CLIENT_ID = "58e2dbd9" 

def fetch_trending_tracks(limit=4):
    url = f"https://api.jamendo.com/v3.0/tracks/?client_id=58e2dbd9&format=json&limit={limit}&order=popularity_month"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get("results", [])
    except Exception as e:
        print(f"Error fetching Jamendo tracks: {e}")
    return []

def download_image(url):
    """Downloads an image from a URL and returns a QPixmap."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            image = QImage()
            image.loadFromData(QByteArray(response.content))
            return QPixmap(image)
    except Exception as e:
        print(f"Image failed: {e}")
    return None