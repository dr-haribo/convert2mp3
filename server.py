"""
Backend Server für die Chrome Extension
Bietet eine REST API für die YouTube-zu-MP3 Konvertierung
"""
import os
import re
import logging
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
import requests
from PIL import Image

# Setup Logging
logging.basicConfig(
    filename="server.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Only allow requests from this specific extension, not from arbitrary websites the
# user happens to have open - this server has no auth and can trigger downloads
# and filesystem writes, so it must not be reachable from normal http(s) origins.
# The ID below is pinned via the "key" field in chrome-extension/manifest.json.
EXTENSION_ID = "ndceendcjncnppkaeidbplbbhaadaing"
CORS(app, origins=[f"chrome-extension://{EXTENSION_ID}"])

BASE_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

YOUTUBE_URL_PATTERN = re.compile(
    r'^(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|playlist\?list=)[\w-]+|youtu\.be/[\w-]+)'
)

# Globale Variablen für Download-Status
download_status = {}


def is_valid_youtube_url(url):
    """Validate that the URL points to YouTube, not an arbitrary host"""
    return bool(YOUTUBE_URL_PATTERN.match(url))


def resolve_download_folder(download_folder):
    """
    Resolve a user-supplied folder name to a path confined to BASE_DOWNLOAD_DIR.
    Rejects absolute paths and '..' traversal so a request can't make the server
    write files outside its own downloads directory.
    """
    download_folder = (download_folder or 'downloads').strip()
    candidate = os.path.normpath(os.path.join(BASE_DOWNLOAD_DIR, download_folder))
    base = os.path.normpath(BASE_DOWNLOAD_DIR)
    if candidate != base and not candidate.startswith(base + os.sep):
        return None
    return candidate


def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def save_thumbnail(info, filename, download_directory):
    """Download and embed thumbnail in MP3 file"""
    try:
        if "thumbnail" in info:
            thumbnail_url = info["thumbnail"]
            thumbnail_name = f"{info['title']}.jpg"
            thumbnail_name = sanitize_filename(thumbnail_name.replace(" ", "_"))
            thumbnail_path = os.path.join(download_directory, thumbnail_name)

            thumbnail = requests.get(thumbnail_url, stream=True)
            if thumbnail.status_code == 200:
                with open(thumbnail_path, "wb") as file:
                    for chunk in thumbnail.iter_content(1024):
                        file.write(chunk)
                
                # Resize the image
                img = Image.open(thumbnail_path)
                img.thumbnail((500, 500))
                img.save(thumbnail_path, "JPEG", quality=85)

                logger.info(f"Thumbnail saved: {thumbnail_path}")
                audio_file = MP3(filename, ID3=ID3)
                try:
                    audio_file.add_tags()
                except Exception:
                    pass
                with open(thumbnail_path, "rb") as img:
                    audio_file.tags.add(
                        APIC(
                            encoding=3,
                            mime="image/jpeg",
                            type=3,
                            desc="Cover",
                            data=img.read(),
                        )
                    )
                audio_file.save(v2_version=3)
                os.remove(thumbnail_path)
                return True
    except Exception as e:
        logger.error(f"Failed to save thumbnail: {e}")
    return False


def download_audio_async(video_url, output_folder, artist, album, quality, download_id):
    """Download audio in a separate thread"""
    try:
        # Check if output directory is writable
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        output_template = f'{output_folder}/%(title)s.%(ext)s'
        
        # Build yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
            'outtmpl': output_template,
            'nocheckcertificate': True,
            'quiet': False,
            'no_warnings': False,
        }
        
        download_status[download_id] = {
            'status': 'downloading',
            'progress': 0,
            'message': 'Starte Download...'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            
            if '_type' in info and info['_type'] == 'playlist':
                for entry in info['entries']:
                    filename = ydl.prepare_filename(entry).replace(".webm", ".mp3").replace(".m4a", ".mp3").replace(".mp4", ".mp3")
                    audio = EasyID3(filename)
                    audio["artist"] = artist or "Unknown"
                    audio["album"] = album or "Unknown"
                    audio["title"] = entry.get("title", "Unknown Title")
                    audio.save()
                    save_thumbnail(entry, filename, output_folder)
            else:
                filename = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3").replace(".mp4", ".mp3")
                audio = EasyID3(filename)
                audio["artist"] = artist or "Unknown"
                audio["album"] = album or "Unknown"
                audio["title"] = info.get("title", "Unknown Title")
                audio.save()
                save_thumbnail(info, filename, output_folder)
        
        download_status[download_id] = {
            'status': 'completed',
            'progress': 100,
            'message': 'Download abgeschlossen!',
            'filename': filename
        }
        logger.info(f"Download completed: {filename}")
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        download_status[download_id] = {
            'status': 'error',
            'progress': 0,
            'message': f'Fehler: {str(e)}',
            'error': str(e)
        }


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Server läuft'})


@app.route('/convert', methods=['POST'])
def convert():
    """Convert YouTube video to MP3"""
    try:
        data = request.json
        
        video_url = data.get('url')
        quality = data.get('quality', '192')
        artist = data.get('artist', '')
        album = data.get('album', '')
        download_folder = data.get('downloadFolder', 'downloads')
        
        if not video_url:
            return jsonify({'success': False, 'error': 'Keine URL angegeben'}), 400

        if not is_valid_youtube_url(video_url):
            return jsonify({'success': False, 'error': 'Ungültige YouTube-URL'}), 400

        # Resolve download folder path, confined to BASE_DOWNLOAD_DIR
        download_folder = resolve_download_folder(download_folder)
        if download_folder is None:
            return jsonify({'success': False, 'error': 'Ungültiger Download-Ordner'}), 400

        # Generate download ID
        import uuid
        download_id = str(uuid.uuid4())
        
        # Start download in background thread
        thread = threading.Thread(
            target=download_audio_async,
            args=(video_url, download_folder, artist, album, quality, download_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'download_id': download_id,
            'message': 'Download gestartet'
        })
        
    except Exception as e:
        logger.error(f"Convert error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/status/<download_id>', methods=['GET'])
def get_status(download_id):
    """Get download status"""
    if download_id in download_status:
        return jsonify(download_status[download_id])
    else:
        return jsonify({'status': 'not_found'}), 404


if __name__ == '__main__':
    print("=" * 50)
    print("Convert2MP3 Backend Server")
    print("=" * 50)
    print("Server startet auf http://localhost:8765")
    print("Stelle sicher, dass die Chrome Extension diese URL verwendet.")
    print("=" * 50)
    
    app.run(host='localhost', port=8765, debug=False)

