# video_api.py
from PySide6.QtCore import QObject, Signal, QUrl, QUrlQuery
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import json
from urllib.parse import quote


class VideoSearchClient(QObject):
    results_ready = Signal(list)
    search_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nam = QNetworkAccessManager(self)
        self._pending_metadata = 0
        self._collected_videos = []
        self._metadata_replies = []

    def search(self, query: str, limit: int = 24):
        query = query.strip()
        if not query:
            return
        self._collected_videos = []
        self._pending_metadata = 0

        url = QUrl("https://archive.org/advancedsearch.php")
        query_obj = QUrlQuery()
        safe_query = (
            f"({query}) AND mediatype:movies AND "
            "(collection:feature_films OR collection:classic_tv OR collection:silent_films)"
        )
        query_obj.addQueryItem("q", safe_query)
        query_obj.addQueryItem("fl[]", "identifier")
        query_obj.addQueryItem("fl[]", "title")
        query_obj.addQueryItem("rows", str(limit))
        query_obj.addQueryItem("output", "json")
        url.setQuery(query_obj)

        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "VidStreamApp/1.0")
        reply = self.nam.get(request)
        reply.finished.connect(self._on_search_reply)
        self._search_reply = reply

    def fetch_trending(self, limit: int = 12):
        self._collected_videos = []
        self._pending_metadata = 0
        url = QUrl("https://archive.org/advancedsearch.php")
        query_obj = QUrlQuery()
        safe_query = (
            "mediatype:movies AND "
            "(collection:feature_films OR collection:classic_tv OR collection:silent_films)"
        )
        query_obj.addQueryItem("q", safe_query)
        query_obj.addQueryItem("sort[]", "downloads desc")
        query_obj.addQueryItem("fl[]", "identifier")
        query_obj.addQueryItem("fl[]", "title")
        query_obj.addQueryItem("rows", str(limit))
        query_obj.addQueryItem("output", "json")
        url.setQuery(query_obj)

        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "VidStreamApp/1.0")
        reply = self.nam.get(request)
        reply.finished.connect(self._on_search_reply)
        self._search_reply = reply

    def fetch_latest(self, limit: int = 12):
        self._collected_videos = []
        self._pending_metadata = 0
        url = QUrl("https://archive.org/advancedsearch.php")
        query_obj = QUrlQuery()
        safe_query = (
            "mediatype:movies AND "
            "(collection:feature_films OR collection:classic_tv OR collection:silent_films)"
        )
        query_obj.addQueryItem("q", safe_query)
        query_obj.addQueryItem("sort[]", "publicdate desc")
        query_obj.addQueryItem("fl[]", "identifier")
        query_obj.addQueryItem("fl[]", "title")
        query_obj.addQueryItem("rows", str(limit))
        query_obj.addQueryItem("output", "json")
        url.setQuery(query_obj)

        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "VidStreamApp/1.0")
        reply = self.nam.get(request)
        reply.finished.connect(self._on_search_reply)
        self._search_reply = reply

    def _on_search_reply(self):
        reply = self._search_reply
        self._search_reply = None
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.search_failed.emit(f"Search request failed: {reply.errorString()}")
                return

            data = json.loads(reply.readAll().data().decode())
            docs = data.get("response", {}).get("docs", [])
            if not docs:
                self.search_failed.emit("No related videos found.")
                return

            self._pending_metadata = len(docs)

            for doc in docs:
                identifier = doc.get("identifier")
                title = doc.get("title", "Untitled")
                if identifier:
                    self._fetch_metadata(identifier, title)
                else:
                    self._pending_metadata -= 1

            if self._pending_metadata == 0:
                self._finish()

        finally:
            reply.deleteLater()

    def _fetch_metadata(self, identifier: str, title: str):
        metadata_url = QUrl(f"https://archive.org/metadata/{identifier}")
        request = QNetworkRequest(metadata_url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "VidStreamApp/1.0")
        reply = self.nam.get(request)
        reply.finished.connect(lambda: self._on_metadata_reply(reply, identifier, title))
        self._metadata_replies.append(reply)

    def _on_metadata_reply(self, reply, identifier: str, title: str):
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                return

            data = json.loads(reply.readAll().data().decode())
            files = data.get("files", [])

            playable_url = None
            duration = 0

            for f in files:
                name = f.get("name", "")
                if name.lower().endswith(".mp4"):
                    playable_url = f"https://archive.org/download/{quote(identifier)}/{quote(name, safe='/')}"
                    if "length" in f:
                        try:
                            duration = int(float(f["length"]))
                        except (TypeError, ValueError):
                            pass
                    break

            if playable_url:
                video_data = {
                    "title": title,
                    "genre": "Public Domain Film",
                    "desc": "Streaming from Internet Archive.",
                    "image_url": f"https://archive.org/services/img/{identifier}",
                    "source": playable_url,
                    "rating": None,
                    "duration": duration,
                }
                self._collected_videos.append(video_data)

        finally:
            reply.deleteLater()
            if reply in self._metadata_replies:
                self._metadata_replies.remove(reply)
            self._pending_metadata -= 1
            if self._pending_metadata <= 0:
                self._finish()

    def _finish(self):
        if self._collected_videos:
            self.results_ready.emit(self._collected_videos)
        else:
            self.search_failed.emit("No playable video files were found.")


class PixabayVideoClient(QObject):
    results_ready = Signal(list)
    search_failed = Signal(str)

    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.nam = QNetworkAccessManager(self)

    def search(self, query: str, limit: int = 20):
        url = QUrl("https://pixabay.com/api/videos/")
        query_obj = QUrlQuery()
        query_obj.addQueryItem("key", self.api_key)
        query_obj.addQueryItem("q", query)
        query_obj.addQueryItem("per_page", str(limit))
        query_obj.addQueryItem("safesearch", "true")
        url.setQuery(query_obj)

        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.UserAgentHeader, "VidStreamApp/1.0")
        reply = self.nam.get(request)
        reply.finished.connect(lambda: self._on_reply(reply))

    def _on_reply(self, reply):
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.search_failed.emit(f"Pixabay search failed: {reply.errorString()}")
                return

            data = json.loads(reply.readAll().data().decode())
            hits = data.get("hits", [])

            if not hits:
                self.search_failed.emit("No videos found on Pixabay.")
                return

            videos = []
            for hit in hits:
                video_files = hit.get("videos", {})
                medium_vid = video_files.get("medium", {})
                playable_url = medium_vid.get("url")
                thumbnail_url = medium_vid.get("thumbnail")

                if playable_url and thumbnail_url:
                    videos.append({
                        "title": hit.get("tags", "Stock Video").title()[:40],
                        "genre": "Pixabay Stock",
                        "desc": f"Resolution: {medium_vid.get('width')}x{medium_vid.get('height')}",
                        "image_url": thumbnail_url,
                        "source": playable_url,
                        "rating": None,
                        "duration": hit.get("duration", 0),
                    })

            self.results_ready.emit(videos)
        finally:
            reply.deleteLater()
