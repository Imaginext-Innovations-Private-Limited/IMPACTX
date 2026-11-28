/* Aarogya Mesh Tier-0 Watch Companion service worker (cache-first offline shell; cross-origin Hub requests bypass SW). */
const CACHE_NAME = "aarogya-watch-companion-v1";
const SHELL_ASSETS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./dist/watch.js",
];

function shouldHandle(request, selfOrigin) {
  if (request.method !== "GET") return false;
  const url = new URL(request.url);
  if (url.origin !== selfOrigin) return false;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws/")) return false;
  return true;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (!shouldHandle(request, self.location.origin)) return;

  if (request.mode === "navigate") {
    event.respondWith(
      caches.match("./index.html").then(
        (cached) =>
          cached ||
          fetch(request)
            .then((response) => {
              if (response.ok) {
                const copy = response.clone();
                caches.open(CACHE_NAME).then((c) => c.put("./index.html", copy));
              }
              return response;
            })
            .catch(() => caches.match("./")),
      ),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request).then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((c) => c.put(request, copy));
          }
          return response;
        }),
    ),
  );
});
