# jamendo_api.py
import json
from PySide6.QtCore import QUrl
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest

NETWORK_MANAGER = QNetworkAccessManager()
CLIENT_ID = "58e2dbd9" 

def fetch_trending_tracks(limit=4):
    # Added &include=name+artist_name+image+audio to force Jamendo to send the fields we need
    url_str = f"https://api.jamendo.com/v3.0/tracks/?client_id={CLIENT_ID}&format=json&limit={limit}&order=popularity_month&include=name+artist_name+image+audio"
    url = QUrl(url_str)
    request = QNetworkRequest(url)
    
    reply = NETWORK_MANAGER.get(request)
    while not reply.isFinished():
        QApplication.processEvents() 
        
    if reply.error():
        print(f"[JAMENDO ERROR] Qt Network: {reply.errorString()}")
        return []
        
    raw_data = bytes(reply.readAll())
    
    try:
        data = json.loads(raw_data)
        # DEBUG PRINT: See what Jamendo is actually sending back
        print(f"[JAMENDO DEBUG] Headers: {data.get('headers')}")
        
        results = data.get("results", [])
        print(f"[JAMENDO] Successfully fetched {len(results)} tracks.")
        return results
    except Exception as e:
        print(f"[JAMENDO ERROR] JSON Parse failed: {e}")
        print(f"Raw Response: {raw_data[:200]}") # Print first 200 chars to see the error
        return []

def download_image(url_string):
    if not url_string or not url_string.strip():
        return None
        
    url = QUrl(url_string)
    request = QNetworkRequest(url)
    reply = NETWORK_MANAGER.get(request)
    
    while not reply.isFinished():
        QApplication.processEvents()
        
    if reply.error():
        return None
        
    image = QImage()
    image.loadFromData(reply.readAll())
    return QPixmap(image)