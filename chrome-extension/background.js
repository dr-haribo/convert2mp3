// Background Service Worker für die Extension

chrome.runtime.onInstalled.addListener(() => {
    console.log('Convert2MP3 Extension installiert');
});

// Optional: Handle Downloads
chrome.downloads.onCreated.addListener((downloadItem) => {
    console.log('Download gestartet:', downloadItem);
});


