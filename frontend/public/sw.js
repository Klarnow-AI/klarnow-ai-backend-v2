// Minimal service worker required for PWA installability (Chrome)
// Uses network-first strategy - always tries network, falls back to cache if offline

const CACHE_NAME = "klarnow-v1";

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  // Bypass SW for subresources — lets images, fonts, etc. load natively.
  // Fixes poster thumbnails and other images not loading in PWA.
  const dest = event.request.destination;
  if (dest && dest !== "document" && event.request.mode !== "navigate") {
    return;
  }
  event.respondWith(
    fetch(event.request)
      .then((response) => response)
      .catch(() => caches.match(event.request)),
  );
});
