const CACHE = "scout-hub-v3";
const SHELL = [
  "/",
  "/static/app.css",
  "/static/app.js",
  "/static/icons/icon.svg",
  "/manifest.webmanifest",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // Toujours réseau d'abord pour JS/HTML/API marché (évite shell obsolète)
  const networkFirst =
    url.pathname === "/" ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".css") ||
    url.pathname.startsWith("/api/");

  if (networkFirst) {
    e.respondWith(
      fetch(req)
        .then((r) => {
          if (url.pathname === "/" || url.pathname.startsWith("/static/")) {
            const copy = r.clone();
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return r;
        })
        .catch(() => caches.match(req).then((c) => c || new Response("Offline", { status: 503 })))
    );
    return;
  }

  e.respondWith(
    fetch(req)
      .then((r) => r)
      .catch(() => caches.match(req).then((c) => c || new Response("Offline", { status: 503 })))
  );
});
