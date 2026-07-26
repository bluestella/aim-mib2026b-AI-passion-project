/* Service worker — offline support for DALOY Scan v1.
 *
 * Offline matters more here than in most apps: the user is often standing in front
 * of a junkshop or a bin on a street with poor signal, and the whole app is a few
 * kilobytes of static files. Everything is precached on install.
 *
 * Bump CACHE when app data or code changes — scripts/build_app_data.py rewrites
 * data/rules.json, and a stale cached copy would show outdated pathways.
 */

const CACHE = 'daloy-v1-2026-07-26';

const ASSETS = [
  './',
  'index.html',
  'styles.css',
  'app.js',
  'manifest.webmanifest',
  'data/rules.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  // Network-first for the rules bundle so a rebuilt version is picked up as soon as
  // there is signal; cache-first for everything else, which never changes between
  // deploys. Either way the app works with no connection at all.
  const isRules = event.request.url.includes('data/rules.json');

  if (isRules) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
