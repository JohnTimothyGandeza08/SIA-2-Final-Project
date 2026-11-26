# jamendo_api.py
import requests
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QByteArray

CLIENT_ID = "58e2dbd9"

def fetch_trending_tracks(limit=4):
    url = (
        "https://api.jamendo.com/v3.0/tracks/"
        f"?client_id={CLIENT_ID}"
        f"&format=json"
        f"&limit={limit}"
        f"&order=popularity_week"
        f"&audioformat=mp32"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get("headers", {}).get("status") != "success":
            print(f"[JAMENDO ERROR] {data.get('headers', {}).get('error_message')}")
            return []

        results = data.get("results", [])
        print(f"[JAMENDO] Successfully fetched {len(results)} tracks.")

        if results:
            print(f"[JAMENDO] Sample Audio URL: {results[0].get('audio')}")

        return results

    except requests.RequestException as e:
        print(f"[JAMENDO NETWORK ERROR] {e}")
        return []
    except Exception as e:
        print(f"[JAMENDO ERROR] {e}")
        return []


def download_image(url):
    if not url or not url.strip():
        return None

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        image = QImage()
        if image.loadFromData(QByteArray(response.content)):
            return QPixmap(image)
        return None

    except Exception as e:
        print(f"[IMAGE ERROR] {e}")
        return None