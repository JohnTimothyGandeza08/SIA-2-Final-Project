# jamendo_api.py
import requests
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QByteArray

CLIENT_ID = "58e2dbd9" 

def fetch_trending_tracks(limit=4):
    url = f"https://api.jamendo.com/v3.0/tracks/?client_id={CLIENT_ID}&format=json&limit={limit}&order=popularity_month"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Print to console so you can see it actually worked
            print(f"Successfully fetched {len(data.get('results', []))} tracks.")
            return data.get("results", [])
    except Exception as e:
        print(f"CRITICAL API ERROR: {e}")
    return []

def download_image(url):
    # Check if URL is empty or None to prevent crash
    if not url:
        return None
        
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            image = QImage()
            image.loadFromData(QByteArray(response.content))
            return QPixmap(image)
    except Exception as e:
        print(f"Image download failed: {e}")
    return None