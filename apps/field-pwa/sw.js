/* Aarogya Mesh field PWA service worker. Same-origin shell only; never touches the hub. */
// dist/sw-version.js is stamped with a content hash by `npm run build`, so every
// rebuild gets a fresh cache name automatically (no manual bump needed).
try {
  importScripts("./dist/sw-version.js");
} catch (e) {
  /* not built yet: fall back to a fixed name */
}
const CACHE_NAME = "aarogya-field-pwa-v3-" + (self.SW_BUILD || "dev");
const SHELL_ASSETS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./dist/app.js",
  "./dist/app.css",
  "./icons/icon.svg",
  "./icons/icon-maskable.svg",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

/**
 * True when this worker may answer the request: same-origin GET inside the worker's scope
 * (scopePath, e.g. "/" or "/phone/"), excluding api/ and ws/ under the scope root and at the
 * origin root. Everything else (hub paths like /health) falls through to the network.
 */
function shouldHandle(request, selfOrigin, scopePath) {
  if (request.method !== "GET") return false;
  const url = new URL(request.url);
  if (url.origin !== selfOrigin) return false; // hub is cross-origin: never intercept
  let scope = scopePath || "/";
  if (!scope.endsWith("/")) scope += "/";
  const path = url.pathname;
  if (!path.startsWith(scope)) return false;
  for (const base of ["/", scope]) {
    if (path.startsWith(base + "api/") || path.startsWith(base + "ws/")) return false;
  }
  return true;
}

function scopePathOf() {
  try {
    return new URL(self.registration.scope).pathname;
  } catch (e) {
    return "/";
  }
}

self.addEventListener("install", (event) => {
  // No automatic skipWaiting: the page offers "update now" and posts SKIP_WAITING.
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)));
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") self.skipWaiting();
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
  if (!shouldHandle(request, self.location.origin, scopePathOf())) return;

  if (request.mode === "navigate") {
    // Network first, fall back to the cached shell (works in Airplane Mode).
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((c) => c.put("./index.html", copy));
          }
          return response;
        })
        .catch(() => caches.match("./index.html").then((r) => r || caches.match("./"))),
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
