// Network first (fresh data when online), cache fallback (last data when offline).
const CACHE = "job-watcher-v5";
const SHELL = ["./", "index.html", "browse.html", "market.html", "app.css", "app.js", "country.js", "manifest.webmanifest", "icon-192.png", "icon-512.png"];
const DATA = ["data/history.csv", "data/status.json"];  // cached at install so the first visit works offline

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL).then(() => c.addAll(DATA.map((u) => new Request(u, { cache: "reload" }))))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith(
    fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(async () => {
      const hit = await caches.match(req, { ignoreSearch: true });
      if (!hit) return Response.error();
      const h = new Headers(hit.headers); h.set("x-from-cache", "1");
      return new Response(await hit.blob(), { status: hit.status, headers: h });
    })
  );
});
