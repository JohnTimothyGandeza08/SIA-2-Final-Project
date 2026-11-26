# jamendo_api.py
import requests
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QByteArray

CLIENT_ID = "58e2dbd9"
TRACKS_URL = "https://api.jamendo.com/v3.0/tracks/"


def stream_url(track_id):
    # Signed "from=" links from the API often 404. This plain link is the one that plays.
    return f"https://prod-1.storage.jamendo.com/?trackid={track_id}&format=mp32"


def _audio_is_live(url):
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.jamendo.com/",
                "Range": "bytes=0-15",
            },
            timeout=8,
            stream=True,
        )
        chunk = next(response.iter_content(16), b"")
        response.close()
        if response.status_code not in (200, 206):
            return False
        content_type = response.headers.get("Content-Type", "")
        return content_type.startswith("audio") or chunk.startswith(b"ID3") or chunk[:1] == b"\xff"
    except Exception:
        return False


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
    return data.get("results") or []


def fetch_trending_tracks(limit=20):
    queries = [
        {"limit": 15, "order": "popularity_week"},
        {"limit": 15, "order": "popularity_total"},
        {"limit": 15, "tags": "ambient"},
    ]
    try:
        playable = []
        seen = set()
        for params in queries:
            for track in _request_tracks(params):
                track_id = track.get("id")
                if not track_id or track_id in seen:
                    continue
                seen.add(track_id)
                url = stream_url(track_id)
                if not _audio_is_live(url):
                    print(f"[JAMENDO] Skipping dead file: {track.get('name')}")
                    continue
                track["audio"] = url
                playable.append(track)
                if len(playable) >= limit:
                    print(f"[JAMENDO] Successfully fetched {len(playable)} playable tracks.")
                    print(f"[JAMENDO] Sample Audio URL: {playable[0]['audio']}")
                    return playable
            if playable:
                break

        print(f"[JAMENDO] Successfully fetched {len(playable)} playable tracks.")
        return playable
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