# Convert2MP3 Chrome Extension

Chrome Extension zum direkten Konvertieren von YouTube-Videos zu MP3 direkt von der YouTube-Seite.

## Installation

### 1. Backend-Server starten

Zuerst muss der Python-Backend-Server gestartet werden:

```bash
# Im Hauptverzeichnis des Projekts
python server.py
```

Der Server läuft standardmäßig auf `http://localhost:8765`.

### 2. Chrome Extension installieren

1. Öffne Chrome und gehe zu `chrome://extensions/`
2. Aktiviere den "Entwicklermodus" (oben rechts)
3. Klicke auf "Entpackte Erweiterung laden"
4. Wähle den `chrome-extension` Ordner aus

### 3. Extension konfigurieren

1. Klicke auf das Extension-Icon in der Chrome-Toolbar
2. Stelle sicher, dass die Server URL auf `http://localhost:8765` steht
3. Konfiguriere deine bevorzugten Einstellungen:
   - Download-Ordner
   - Audio-Qualität (128/192/320 kbps)
   - Standard-Artist und Album (optional)
4. Klicke auf "Einstellungen speichern"

## Verwendung

### Methode 1: Button auf YouTube

1. Öffne ein YouTube-Video
2. Ein "🎵 Zu MP3" Button erscheint automatisch unter dem Video
3. Klicke auf den Button, um das Video zu konvertieren

### Methode 2: Extension Popup

1. Klicke auf das Extension-Icon in der Chrome-Toolbar
2. Gib eine YouTube URL ein
3. Klicke auf "Konvertieren"

## Features

- ✅ Direkter Download-Button auf YouTube-Videoseiten
- ✅ Automatische Metadaten (Artist, Album, Titel)
- ✅ Thumbnail wird als Cover-Art eingebettet
- ✅ Konfigurierbare Audio-Qualität
- ✅ Popup-Interface für manuelle URLs
- ✅ Server-Status-Anzeige

## Technische Details

- **Backend**: Python Flask Server (Port 8765)
- **Extension**: Chrome Manifest V3
- **Kommunikation**: REST API zwischen Extension und Backend
- **Download**: Verwendet yt-dlp für YouTube-Downloads

## Fehlerbehebung

### Server nicht erreichbar

- Stelle sicher, dass `server.py` läuft
- Prüfe, ob Port 8765 frei ist
- Überprüfe die Server URL in den Extension-Einstellungen

### Download funktioniert nicht

- Prüfe die Server-Logs (`server.log`)
- Stelle sicher, dass FFmpeg installiert ist
- Überprüfe, ob der Download-Ordner existiert und beschreibbar ist

### Button erscheint nicht auf YouTube

- Aktualisiere die YouTube-Seite
- Prüfe die Browser-Konsole auf Fehler (F12)
- Stelle sicher, dass die Extension aktiviert ist

## Icons

Die Extension benötigt Icons in verschiedenen Größen. Du kannst:

1. Die vorhandenen Icons im `icons/` Ordner verwenden
2. Oder eigene Icons erstellen (16x16, 48x48, 128x128 Pixel)
