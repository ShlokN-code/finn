// FINN service worker: the app opens offline with the last Brief it showed.
// - Pages (navigations): network first, falling back to the cached page (then the cached /brief).
// - Hashed build assets (/_next/static), fonts, icons: cache first (immutable).
// - The showcase day and the demo Brief (GET): stale-while-revalidate.
// - Everything else (POST /api/brief, research, Ask, Telegram) goes to the network untouched. The Brief's data comes
//   from this phone's last copy in localStorage, so the cached shell renders it with its "data as of" stamp.
const VERSION = "finn-v1";
const SHELL = ["/brief", "/portfolio", "/rules", "/research", "/showcase/brief.json", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).catch(() => undefined));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) caches.open(VERSION).then((c) => c.put(req, res.clone()));
          return res;
        })
        .catch(async () => (await caches.match(req)) || (await caches.match("/brief")) || Response.error()),
    );
    return;
  }
  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/") || /\.(woff2?|png|svg)$/.test(url.pathname)) {
    e.respondWith(
      caches.match(req).then(
        (hit) =>
          hit ||
          fetch(req).then((res) => {
            if (res.ok) caches.open(VERSION).then((c) => c.put(req, res.clone()));
            return res;
          }),
      ),
    );
    return;
  }
  if (url.pathname === "/showcase/brief.json" || url.pathname === "/api/brief/demo" || url.pathname === "/nse-symbols.json") {
    e.respondWith(
      caches.open(VERSION).then(async (c) => {
        const hit = await c.match(req);
        const net = fetch(req)
          .then((res) => {
            if (res.ok) c.put(req, res.clone());
            return res;
          })
          .catch(() => hit);
        return hit || net;
      }),
    );
  }
});
