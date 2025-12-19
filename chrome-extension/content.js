// Content Script für YouTube-Seiten
// Injiziert einen "Zu MP3 konvertieren" Button auf YouTube-Videoseiten

(function() {
    'use strict';

    // Warte bis die Seite geladen ist
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        // Prüfe ob wir auf einer YouTube-Videoseite sind
        const videoId = getVideoId();
        if (!videoId) {
            return;
        }

        // Warte auf das Video-Element
        waitForElement('#primary-inner', () => {
            injectDownloadButton();
        });
    }

    function getVideoId() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('v');
    }

    function waitForElement(selector, callback) {
        const element = document.querySelector(selector);
        if (element) {
            callback();
        } else {
            setTimeout(() => waitForElement(selector, callback), 500);
        }
    }

    function injectDownloadButton() {
        // Prüfe ob Button bereits existiert
        if (document.getElementById('convert2mp3-button')) {
            return;
        }

        // Finde den Container für die Video-Aktionen (Like, Dislike, etc.)
        const menuContainer = document.querySelector('#menu-container, #top-level-buttons-computed, ytd-menu-renderer');
        
        if (!menuContainer) {
            // Fallback: Suche nach dem Like-Button Container
            const likeButton = document.querySelector('#top-level-buttons-computed, ytd-menu-renderer');
            if (likeButton && likeButton.parentElement) {
                createButton(likeButton.parentElement);
            }
            return;
        }

        // Versuche verschiedene Positionen
        const targetContainer = menuContainer.parentElement || menuContainer;
        createButton(targetContainer);
    }

    function createButton(container) {
        const button = document.createElement('button');
        button.id = 'convert2mp3-button';
        button.className = 'convert2mp3-btn';
        button.innerHTML = '🎵 Zu MP3';
        button.title = 'Video als MP3 herunterladen';
        
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            const videoId = getVideoId();
            if (videoId) {
                button.disabled = true;
                button.textContent = '⏳ Konvertiere...';
                
                try {
                    await convertToMP3(videoId);
                    button.textContent = '✅ Fertig!';
                    setTimeout(() => {
                        button.textContent = '🎵 Zu MP3';
                        button.disabled = false;
                    }, 2000);
                } catch (error) {
                    console.error('Fehler beim Konvertieren:', error);
                    button.textContent = '❌ Fehler';
                    alert('Fehler beim Konvertieren: ' + error.message);
                    setTimeout(() => {
                        button.textContent = '🎵 Zu MP3';
                        button.disabled = false;
                    }, 3000);
                }
            }
        });

        // Füge Button hinzu
        container.appendChild(button);
    }

    async function convertToMP3(videoId) {
        const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;
        
        // Hole Einstellungen aus Storage
        const settings = await chrome.storage.sync.get({
            downloadFolder: 'downloads',
            quality: '192',
            artist: '',
            album: '',
            serverUrl: 'http://localhost:8765'
        });

        // Sende Anfrage an Backend-Server
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
            // Zeige Erfolgsmeldung
            showNotification('Download gestartet!', 'Das MP3 wird heruntergeladen...');
        } else {
            throw new Error(result.error || 'Unbekannter Fehler');
        }
    }

    function showNotification(message, details) {
        // Erstelle eine einfache Notification
        const notification = document.createElement('div');
        notification.className = 'convert2mp3-notification';
        notification.innerHTML = `
            <strong>${message}</strong>
            <div>${details}</div>
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Beobachte URL-Änderungen (YouTube ist eine SPA)
    let lastUrl = location.href;
    new MutationObserver(() => {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            setTimeout(init, 1000);
        }
    }).observe(document, { subtree: true, childList: true });
})();


