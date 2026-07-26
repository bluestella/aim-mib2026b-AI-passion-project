/* Service worker — offline support for DALOY Scan.
 *
 * Offline matters more here than in most apps: the user is often standing in front
 * of a bin or a junkshop on a street with poor signal.
 *
 * This is a runtime cache, not a precache. The vanilla build listed its files
 * explicitly, which Next.js makes impossible — asset filenames are content-hashed at
 * build time, so there is no fixed list to enumerate. Instead:
 *
 *   - /_next/static/* is immutable by construction (the hash IS the version), so it
 *     is cache-first and never revalidated.
 *   - Navigations are network-first with a cache fallback, so a deploy is picked up
 *     as soon as there is signal but the app still opens with none.
 *
 * The rules bundle needs no special case any more: it is imported into the JS
 * chunks, so it is versioned by the same content hash as the code that reads it.
 * A stale bundle can no longer pair with fresh code.
 */

const CACHE = 'daloy-v2';
const OFFLINE_FALLBACK = '/';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.add(OFFLINE_FALLBACK))
      .then(() => self.skipWaiting())
      // A failed precache must not wedge the install; the runtime cache still works.
      .catch(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Immutable build output: hash in the name means a hit is always correct.
  if (url.pathname.startsWith('/_next/static/')) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy));
            return response;
          }),
      ),
    );
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() =>
          caches.match(request).then((cached) => cached || caches.match(OFFLINE_FALLBACK)),
        ),
    );
    return;
  }

  // Everything else: cache with background refresh.
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
