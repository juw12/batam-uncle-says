/* Batam Uncle Says - offline cache. Bump VERSION when files change. */
const VERSION = "bus-2026-11-12-p0700";
const FILES = [
  "./",
  "index.html",
  "data.js",
  "photos.js",
  "partners.js",
  "manifest.webmanifest",
  "fonts/instrument-serif-latin-italic.woff2",
  "fonts/instrument-serif-latin.woff2",
  "fonts/inter-latin.woff2",
  "img/ferry-batam-centre.jpg",
  "img/ferry-harbour-bay.jpg",
  "img/ferry-sekupang.jpg",
  "img/ferry-waterfront.jpg",
  "img/food-fish.jpg",
  "img/food-gonggong.jpg",
  "img/food-squid.jpg",
  "img/hero-barelang.jpg",
  "img/money-rupiah.jpg",
  "img/place-barelang.jpg",
  "img/place-golden-prawn.jpg",
  "img/place-grand-batam.jpg",
  "img/place-harbour-bay-seafood.jpg",
  "img/place-maitreya.jpg",
  "img/place-mega-mall.jpg",
  "img/place-montigo.jpg",
  "img/place-nagoya-hill.jpg",
  "img/place-nongsa-point.jpg",
  "img/place-turi-beach.jpg",
  "icons/icon-180.png",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/icon-maskable-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }
  /* data.js holds the daily events and prices: ask the network first so the first open of the day
     is current, and fall back to the saved copy when offline or slow (3 seconds). */
  if (url.pathname.endsWith("/data.js")) {
    event.respondWith(
      caches.open(VERSION).then(async (cache) => {
        const cached = await cache.match(request, { ignoreSearch: true });
        const fresh = fetch(request, { cache: "no-cache" }).then((response) => {
          if (response.ok) {
            cache.put(request, response.clone());
          }
          return response;
        });
        if (!cached) {
          return fresh;
        }
        const giveUp = new Promise((resolve) => setTimeout(() => resolve(cached), 3000));
        return Promise.race([fresh.catch(() => cached), giveUp]);
      })
    );
    return;
  }
  event.respondWith(
    caches.open(VERSION).then(async (cache) => {
      const cached = await cache.match(request, { ignoreSearch: true });
      const network = fetch(request)
        .then((response) => {
          if (response.ok) {
            cache.put(request, response.clone());
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
