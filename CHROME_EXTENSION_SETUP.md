# Chrome Extension Setup - Convert2MP3

Diese Anleitung erklärt, wie du die Chrome Extension für Convert2MP3 einrichtest und verwendest.

## Übersicht

Die Chrome Extension ermöglicht es dir, YouTube-Videos direkt von der YouTube-Seite zu MP3 zu konvertieren, ohne die URL manuell kopieren zu müssen.

## Voraussetzungen

1. Python 3.x installiert
2. Alle Python-Abhängigkeiten installiert (siehe `requirements.txt`)
3. FFmpeg installiert (für Audio-Konvertierung)
4. Google Chrome Browser

## Installation

### Schritt 1: Python-Abhängigkeiten installieren

```bash
cd /Users/finnringhoff/Desktop/coding/convert2mp3
pip install -r requirements.txt
```

### Schritt 2: Backend-Server starten

```bash
python server.py
```

Der Server startet auf `http://localhost:8765`. Lasse dieses Terminal-Fenster geöffnet.

### Schritt 3: Chrome Extension installieren

1. Öffne Google Chrome
2. Gehe zu `chrome://extensions/`
3. Aktiviere den **Entwicklermodus** (Toggle oben rechts)
4. Klicke auf **"Entpackte Erweiterung laden"**
5. Wähle den Ordner `chrome-extension` aus diesem Projekt aus
6. Die Extension sollte jetzt in der Liste erscheinen

### Schritt 4: Extension konfigurieren

1. Klicke auf das Extension-Icon in der Chrome-Toolbar (rechts oben)
2. Das Popup öffnet sich
3. Überprüfe die Einstellungen:
   - **Server URL**: Sollte `http://localhost:8765` sein
   - **Download-Ordner**: Standard ist `downloads` (relativ zum Projektverzeichnis)
   - **Audio-Qualität**: Wähle 128, 192 oder 320 kbps
   - **Standard-Artist/Album**: Optional, wird für alle Downloads verwendet
4. Klicke auf **"Einstellungen speichern"**
5. Der Status sollte auf "✓ Server verbunden" wechseln

## Verwendung

### Methode 1: Button auf YouTube (Empfohlen)

1. Öffne ein YouTube-Video in Chrome
2. Unter dem Video erscheint automatisch ein **"🎵 Zu MP3"** Button
3. Klicke auf den Button
4. Das Video wird im Hintergrund konvertiert
5. Die MP3-Datei wird im konfigurierten Download-Ordner gespeichert

### Methode 2: Extension Popup

1. Klicke auf das Extension-Icon in der Chrome-Toolbar
2. Gib eine YouTube URL in das Eingabefeld ein
3. Klicke auf **"Konvertieren"**
4. Die Konvertierung startet

## Features

- ✅ **Direkter Button auf YouTube**: Kein Kopieren der URL nötig
- ✅ **Automatische Metadaten**: Titel, Artist, Album werden automatisch gesetzt
- ✅ **Thumbnail als Cover**: Das Video-Thumbnail wird als Album-Cover eingebettet
- ✅ **Konfigurierbare Qualität**: 128, 192 oder 320 kbps
- ✅ **Server-Status**: Siehst sofort, ob der Server erreichbar ist
- ✅ **Playlist-Support**: Unterstützt auch YouTube-Playlists

## Fehlerbehebung

### "Server nicht erreichbar"

**Problem**: Die Extension zeigt "✗ Server nicht erreichbar"

**Lösungen**:
1. Stelle sicher, dass `server.py` läuft
2. Prüfe, ob Port 8765 frei ist: `lsof -i :8765`
3. Überprüfe die Server URL in den Extension-Einstellungen
4. Prüfe die Firewall-Einstellungen

### Button erscheint nicht auf YouTube

**Problem**: Der "🎵 Zu MP3" Button erscheint nicht unter dem Video

**Lösungen**:
1. Aktualisiere die YouTube-Seite (F5)
2. Öffne die Browser-Konsole (F12) und prüfe auf Fehler
3. Stelle sicher, dass die Extension aktiviert ist (`chrome://extensions/`)
4. Prüfe, ob Content Scripts aktiviert sind

### Download funktioniert nicht

**Problem**: Die Konvertierung startet nicht oder schlägt fehl

**Lösungen**:
1. Prüfe die Server-Logs in `server.log`
2. Stelle sicher, dass FFmpeg installiert ist: `ffmpeg -version`
3. Überprüfe, ob der Download-Ordner existiert und beschreibbar ist
4. Prüfe die Browser-Konsole (F12) auf Fehler

### FFmpeg nicht gefunden

**Problem**: `ffmpeg: command not found`

**Lösungen**:
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg` (Ubuntu/Debian) oder `sudo yum install ffmpeg` (CentOS/RHEL)
- **Windows**: Lade FFmpeg von https://ffmpeg.org/download.html und füge es zum PATH hinzu

## Erweiterte Konfiguration

### Download-Ordner ändern

Du kannst einen absoluten Pfad angeben:
- Beispiel: `/Users/DeinName/Music/Downloads`
- Oder einen relativen Pfad: `downloads` (relativ zum Projektverzeichnis)

### Server-Port ändern

Falls Port 8765 belegt ist, kannst du den Port in `server.py` ändern:

```python
app.run(host='localhost', port=8766, debug=False)  # Port ändern
```

Vergiss nicht, die Server URL in den Extension-Einstellungen anzupassen!

## Technische Details

- **Backend**: Flask REST API auf Port 8765
- **Extension**: Chrome Manifest V3
- **Kommunikation**: JSON über HTTP
- **Download-Engine**: yt-dlp
- **Audio-Format**: MP3 mit ID3-Tags

## Sicherheit

⚠️ **Wichtig**: Der Server läuft nur auf `localhost` und ist nicht für den Einsatz im Internet gedacht. Er sollte nur lokal verwendet werden.

## Support

Bei Problemen:
1. Prüfe die Logs: `server.log` und Browser-Konsole (F12)
2. Stelle sicher, dass alle Abhängigkeiten installiert sind
3. Prüfe, ob FFmpeg korrekt installiert ist

## Nächste Schritte

- [ ] Extension im Chrome Web Store veröffentlichen (optional)
- [ ] Automatische Updates implementieren
- [ ] Download-Fortschrittsanzeige in der Extension
- [ ] Mehrere Downloads gleichzeitig


