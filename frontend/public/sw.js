// Minimal service worker required for PWA installability (Chrome)
// Uses network-first strategy - always tries network, falls back to cache if offline

const CACHE_NAME = "klarnow-v1";

const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Klarnow AI - Offline</title>
</head>
<body style="font-family:system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#fafafa;color:#333">
  <h1 style="font-size:1.25rem;font-weight:600;margin-bottom:0.5rem">You're offline</h1>
  <p style="color:#666;margin-bottom:1rem">Check your connection and try again.</p>
  <button onclick="location.reload()" style="padding:0.5rem 1rem;font-size:1rem;cursor:pointer;background:#000;color:#fff;border:none;border-radius:0.25rem">Retry</button>
</body>
</html>`;

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
      .then((response) => {
        const clone = response.clone();
        if (response.ok && response.status === 200) {
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(async () => {
        const cachedResponse = await caches.match(event.request);
        if (cachedResponse) return cachedResponse;

        return new Response(OFFLINE_HTML, {
          status: 503,
          statusText: "Service Unavailable",
          headers: { "Content-Type": "text/html; charset=utf-8" },
        });
      }),
  );
});
