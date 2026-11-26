# jamendo_api.py
from concurrent.futures import ThreadPoolExecutor
import requests
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QByteArray

CLIENT_ID = "58e2dbd9"
TRACKS_URL = "https://api.jamendo.com/v3.0/tracks/"
ARTISTS_URL = "https://api.jamendo.com/v3.0/artists/"


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


def _request_json(url, params):
    query = {
        "client_id": CLIENT_ID,
        "format": "json",
    }
    query.update(params)
    response = requests.get(
        url,
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


def _request_tracks(params):
    query = {"audioformat": "mp32"}
    query.update(params)
    return _request_json(TRACKS_URL, query)


def _request_artists(params):
    return _request_json(ARTISTS_URL, params)


def _filter_playable_tracks(tracks, limit=20, seen=None):
    if seen is None:
        seen = set()

    candidates = []
    for track in tracks:
        track_id = track.get("id")
        if not track_id or track_id in seen:
            continue
        seen.add(track_id)
        url = stream_url(track_id)
        candidates.append((track, url))

    if not candidates:
        return []

    with ThreadPoolExecutor(max_workers=8) as pool:
        live_flags = list(pool.map(lambda item: _audio_is_live(item[1]), candidates))

    playable = []
    for (track, url), is_live in zip(candidates, live_flags):
        if not is_live:
            print(f"[JAMENDO] Skipping dead file: {track.get('name')}")
            continue
        track["audio"] = url
        playable.append(track)
        if len(playable) >= limit:
            break
    return playable


def fetch_trending_tracks(limit=20):
    query_limit = min(max(limit * 2, 25), 200)
    queries = [
        {"limit": query_limit, "order": "popularity_week"},
        {"limit": query_limit, "order": "popularity_total"},
        {"limit": query_limit, "tags": "ambient"},
    ]
    try:
        playable = []
        seen = set()
        for params in queries:
            remaining = limit - len(playable)
            if remaining <= 0:
                break
            raw_tracks = _request_tracks(params)
            playable.extend(_filter_playable_tracks(raw_tracks, limit=remaining, seen=seen))

        print(f"[JAMENDO] Successfully fetched {len(playable)} playable tracks.")
        if playable:
            print(f"[JAMENDO] Sample Audio URL: {playable[0]['audio']}")
        return playable
    except requests.RequestException as e:
        print(f"[JAMENDO NETWORK ERROR] {e}")
        return []
    except Exception as e:
        print(f"[JAMENDO ERROR] {e}")
        return []


def search_artists(query, limit=4):
    query = (query or "").strip()
    if not query:
        return []
    try:
        return _request_artists({"namesearch": query, "limit": limit})
    except requests.RequestException as e:
        print(f"[JAMENDO ARTIST NETWORK ERROR] {e}")
        return []
    except Exception as e:
        print(f"[JAMENDO ARTIST ERROR] {e}")
        return []


def fetch_artist_tracks(artist_id, limit=6):
    if not artist_id:
        return []
    try:
        raw_tracks = _request_tracks({
            "artist_id": artist_id,
            "limit": min(max(limit * 2, 15), 200),
            "order": "popularity_total",
        })
        return _filter_playable_tracks(raw_tracks, limit=limit)
    except requests.RequestException as e:
        print(f"[JAMENDO ARTIST TRACKS NETWORK ERROR] {e}")
        return []
    except Exception as e:
        print(f"[JAMENDO ARTIST TRACKS ERROR] {e}")
        return []


def search_tracks(query, limit=20):
    query = (query or "").strip()
    if not query:
        return []
    try:
        raw_tracks = _request_tracks({
            "search": query,
            "limit": min(max(limit * 2, 30), 200),
        })
        return _filter_playable_tracks(raw_tracks, limit=limit)
    except requests.RequestException as e:
        print(f"[JAMENDO TRACK SEARCH NETWORK ERROR] {e}")
        return []
    except Exception as e:
        print(f"[JAMENDO TRACK SEARCH ERROR] {e}")
        return []


def search_catalog(query, artist_limit=4, artist_tracks_limit=6, track_limit=20):
    query = (query or "").strip()
    if not query:
        return {"artists": [], "tracks": []}

    artists = search_artists(query, limit=artist_limit)
    if artists:
        with ThreadPoolExecutor(max_workers=min(len(artists), 4)) as pool:
            artist_track_lists = list(
                pool.map(lambda a: fetch_artist_tracks(a.get("id"), limit=artist_tracks_limit), artists)
            )
        for artist, a_tracks in zip(artists, artist_track_lists):
            artist["tracks"] = a_tracks
            if not artist.get("image") and a_tracks:
                artist["image"] = a_tracks[0].get("album_image") or a_tracks[0].get("image") or ""

    tracks = search_tracks(query, limit=track_limit)

    # Ensure matched artists' playable songs also appear in the Songs results
    seen_ids = {t.get("id") for t in tracks if t.get("id")}
    for artist in artists:
        for t in artist.get("tracks", []):
            tid = t.get("id")
            if tid and tid not in seen_ids and len(tracks) < track_limit:
                seen_ids.add(tid)
                tracks.append(t)

    return {"artists": artists, "tracks": tracks}


def download_image_bytes(url):
    if not url or not url.strip():
        return None
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Pulse/1.0"})
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"[IMAGE ERROR] {e}")
    return None


def download_image(url):
    data = download_image_bytes(url)
    if not data:
        return None
    image = QImage()
    if image.loadFromData(QByteArray(data)):
        return QPixmap(image)
    return None