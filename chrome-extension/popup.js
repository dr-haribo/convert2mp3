// Popup Script für die Extension

document.addEventListener('DOMContentLoaded', async () => {
    // Lade gespeicherte Einstellungen
    const settings = await chrome.storage.sync.get({
        serverUrl: 'http://localhost:8765',
        downloadFolder: 'downloads',
        quality: '192',
        artist: '',
        album: ''
    });

    // Setze Formularwerte
    document.getElementById('serverUrl').value = settings.serverUrl;
    document.getElementById('downloadFolder').value = settings.downloadFolder;
    document.getElementById('quality').value = settings.quality;
    document.getElementById('artist').value = settings.artist;
    document.getElementById('album').value = settings.album;

    // Prüfe Server-Verbindung
    checkServerConnection(settings.serverUrl);

    // Event Listeners
    document.getElementById('saveBtn').addEventListener('click', saveSettings);
    document.getElementById('convertBtn').addEventListener('click', convertFromPopup);
    
    // Prüfe Verbindung bei URL-Änderung
    document.getElementById('serverUrl').addEventListener('blur', (e) => {
        checkServerConnection(e.target.value);
    });
});

async function checkServerConnection(serverUrl) {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    statusIndicator.className = 'status-indicator';
    statusText.textContent = 'Verbinde mit Server...';
    
    try {
        const response = await fetch(`${serverUrl}/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(3000)
        });
        
        if (response.ok) {
            statusIndicator.classList.add('connected');
            statusText.textContent = '✓ Server verbunden';
        } else {
            throw new Error('Server antwortet nicht korrekt');
        }
    } catch (error) {
        statusIndicator.classList.add('disconnected');
        statusText.textContent = '✗ Server nicht erreichbar';
        console.error('Server-Verbindungsfehler:', error);
    }
}

async function saveSettings() {
    const settings = {
        serverUrl: document.getElementById('serverUrl').value.trim(),
        downloadFolder: document.getElementById('downloadFolder').value.trim(),
        quality: document.getElementById('quality').value,
        artist: document.getElementById('artist').value.trim(),
        album: document.getElementById('album').value.trim()
    };

    await chrome.storage.sync.set(settings);
    
    // Prüfe Verbindung mit neuer URL
    checkServerConnection(settings.serverUrl);
    
    // Zeige Bestätigung
    const saveBtn = document.getElementById('saveBtn');
    const originalText = saveBtn.textContent;
    saveBtn.textContent = '✓ Gespeichert!';
    saveBtn.style.background = '#4CAF50';
    saveBtn.style.color = 'white';
    
    setTimeout(() => {
        saveBtn.textContent = originalText;
        saveBtn.style.background = '';
        saveBtn.style.color = '';
    }, 2000);
}

async function convertFromPopup() {
    const videoUrl = document.getElementById('videoUrl').value.trim();
    
    if (!videoUrl) {
        alert('Bitte gib eine YouTube URL ein');
        return;
    }

    if (!videoUrl.includes('youtube.com') && !videoUrl.includes('youtu.be')) {
        alert('Bitte gib eine gültige YouTube URL ein');
        return;
    }

    const settings = await chrome.storage.sync.get({
        serverUrl: 'http://localhost:8765',
        downloadFolder: 'downloads',
        quality: '192',
        artist: '',
        album: ''
    });

    const convertBtn = document.getElementById('convertBtn');
    convertBtn.disabled = true;
    convertBtn.textContent = '⏳ Konvertiere...';

    try {
        const response = await fetch(`${settings.serverUrl}/convert`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: videoUrl,
                quality: settings.quality,
                artist: settings.artist,
                album: settings.album,
                downloadFolder: settings.downloadFolder
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Server-Fehler');
        }

        const result = await response.json();
        
        if (result.success) {
            convertBtn.textContent = '✓ Erfolg!';
            convertBtn.style.background = '#4CAF50';
            document.getElementById('videoUrl').value = '';
            
            setTimeout(() => {
                convertBtn.textContent = 'Konvertieren';
                convertBtn.style.background = '';
                convertBtn.disabled = false;
            }, 2000);
        } else {
            throw new Error(result.error || 'Unbekannter Fehler');
        }
    } catch (error) {
        console.error('Konvertierungsfehler:', error);
        alert('Fehler: ' + error.message);
        convertBtn.textContent = 'Konvertieren';
        convertBtn.disabled = false;
    }
}


