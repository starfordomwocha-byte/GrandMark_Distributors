self.addEventListener('install', (e) => {
  console.log('[Service Worker] Installed');
});

self.addEventListener('fetch', (e) => {
  // Allows the app to work efficiently on mobile networks
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});