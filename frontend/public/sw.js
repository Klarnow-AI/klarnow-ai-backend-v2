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
  // Only handle top-level/document GET requests in this minimal SW.
  // All API/subresource requests are left to the browser/network stack.
  if (event.request.method !== "GET") {
    return;
  }
  const dest = event.request.destination;
  const isDocumentRequest =
    event.request.mode === "navigate" || dest === "document";
  if (!isDocumentRequest) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => response)
      .catch(async () => {
        const cachedResponse = await caches.match(event.request);
        if (cachedResponse) return cachedResponse;

        return new Response("Offline", {
          status: 503,
          statusText: "Service Unavailable",
          headers: { "Content-Type": "text/plain; charset=utf-8" },
        });
      }),
  );
});
