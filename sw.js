// Danabus Service Worker - Task 005 Production Release Acceptance & Project Closure Gate (Build 20260929_v11)
const CACHE_NAME = 'danabus-cache-v11';
const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './css/app.css?v=20260929_v11',
  './js/icons.js?v=20260929_v11',
  './js/app.js?v=20260929_v11',
  './js/busService.js?v=20260929_v11',
  './js/mapService.js?v=20260929_v11',
  './assets/logo.svg',
  './assets/icons/icon-192.png',
  './assets/icons/icon-512.png',
  './data/danangbus_routes.json',
  './data/danangbus_routes_compact.json',
  './data/danangbus_stops.json',
  './data/danangbus_streets.json',
  './data/danangbus_summary.json'
];

self.addEventListener('install', event => {
  console.log('[Danabus SW] Installing new service worker version:', CACHE_NAME);
  event.waitUntil(
    caches.open(CACHE_NAME).then(async cache => {
      console.log('[Danabus SW] Pre-caching static assets with fresh fetch');
      const assetPromises = STATIC_ASSETS.map(async url => {
        try {
          const req = new Request(url, { cache: 'reload' });
          const res = await fetch(req);
          if (res && res.status === 200) {
            await cache.put(url, res);
          }
        } catch (err) {
          console.warn('[Danabus SW] Failed to pre-cache asset:', url, err);
        }
      });
      await Promise.all(assetPromises);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  console.log('[Danabus SW] Activating and purging stale caches');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME)
          .map(name => {
            console.log('[Danabus SW] Deleted obsolete cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const requestUrl = new URL(event.request.url);

  // 1. Same-origin requests (HTML, JS, CSS, JSON Data) -> ALWAYS Network-First with Cache Fallback
  if (requestUrl.origin === location.origin) {
    event.respondWith(
      fetch(event.request, { cache: 'no-cache' })
        .then(networkResponse => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseToCache));
          }
          return networkResponse;
        })
        .catch(() => {
          console.warn('[Danabus SW] Network failed, serving cached fallback for:', requestUrl.pathname);
          return caches.match(event.request);
        })
    );
    return;
  }

  // 2. Third-party CDN assets (Leaflet tiles, Google Fonts, Tailwind) -> Stale-While-Revalidate
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      const fetchPromise = fetch(event.request).then(networkResponse => {
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseToCache));
        }
        return networkResponse;
      }).catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
