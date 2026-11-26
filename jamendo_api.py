# jamendo_api.py
import requests
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QByteArray

CLIENT_ID = "58e2dbd9"
TRACKS_URL = "https://api.jamendo.com/v3.0/tracks/"


def _request_tracks(params):
    query = {
        "client_id": CLIENT_ID,
        "format": "json",
        "audioformat": "mp32",
    }
    query.update(params)

    response = requests.get(
        TRACKS_URL,
        params=query,
        timeout=15,
        headers={"User-Agent": "Pulse/1.0", "Accept": "application/json"},
    )
    response.raise_for_status()
    data = response.json()
    headers = data.get("headers") or {}
    results = data.get("results") or []

    print(
        "[JAMENDO] status={status} code={code} count={count} error={error}".format(
            status=headers.get("status"),
            code=headers.get("code"),
            count=headers.get("results_count"),
            error=headers.get("error_message") or "-",
        )
    )

    if headers.get("status") != "success":
        return []

    playable = [track for track in results if track.get("audio")]
    return playable


def fetch_trending_tracks(limit=4):
    queries = [
        {"limit": limit, "order": "popularity_week"},
        {"limit": limit, "order": "popularity_total"},
        {"limit": limit, "tags": "ambient"},
        {"limit": limit, "search": "piano"},
    ]

    try:
        for params in queries:
            results = _request_tracks(params)
            if results:
                print(f"[JAMENDO] Successfully fetched {len(results)} tracks.")
                print(f"[JAMENDO] Sample Audio URL: {results[0].get('audio')}")
                return results

        print("[JAMENDO] No playable tracks. Check the status lines above.")
        return []
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
        response = requests.get(url, timeout=10, headers={"User-Agent": "Pulse/1.0"})
        response.raise_for_status()
        image = QImage()
        if image.loadFromData(QByteArray(response.content)):
            return QPixmap(image)
    except Exception as e:
        print(f"[IMAGE ERROR] {e}")
    return None