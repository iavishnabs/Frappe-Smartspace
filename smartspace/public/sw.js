// SmartSpace Service Worker
const CACHE_VERSION = "v4";
const STATIC_CACHE = `smartspace-static-${CACHE_VERSION}`;
const PAGE_CACHE = `smartspace-pages-${CACHE_VERSION}`;
const API_CACHE = `smartspace-api-${CACHE_VERSION}`;

// App shell - static assets to cache on install
const APP_SHELL = [
  "/home",
  "/spaces",
  "/contact",
  "/signin",
  "/offline",
  "/assets/smartspace/manifest.json",
  "/assets/smartspace/icon-192.svg",
  "/assets/smartspace/icon-512.svg",
  "https://cdn.tailwindcss.com",
];

// Install - cache app shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(APP_SHELL).catch(() => {});
    })
  );
  self.skipWaiting();
});

// Activate - clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith("smartspace-") && !name.endsWith(CACHE_VERSION))
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Helper: determine cache strategy based on request
function handleRequest(event) {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle GET requests
  if (request.method !== "GET") {
    return fetch(request);
  }

  // API calls - stale-while-revalidate
  if (url.pathname.startsWith("/api/") || url.pathname.includes("/api/method/")) {
    return caches.open(API_CACHE).then((cache) => {
      return cache.match(request).then((cachedResponse) => {
        const fetchPromise = fetch(request)
          .then((response) => {
            if (response && response.status === 200) {
              cache.put(request, response.clone());
            }
            return response;
          })
          .catch(() => cachedResponse);
        return cachedResponse || fetchPromise;
      });
    });
  }

  // Navigation requests (HTML pages) - network-first, fallback to cache, then offline
  if (request.mode === "navigate") {
    return fetch(request)
      .then((response) => {
        const responseClone = response.clone();
        caches.open(PAGE_CACHE).then((cache) => {
          cache.put(request, responseClone);
        });
        return response;
      })
      .catch(() => {
        return caches.match(request).then((cached) => {
          if (cached) return cached;
          return caches.match("/offline");
        });
      });
  }

  // Static assets (CSS, JS, images, fonts) - cache-first
  if (
    request.destination === "style" ||
    request.destination === "script" ||
    request.destination === "image" ||
    request.destination === "font" ||
    url.pathname.startsWith("/assets/")
  ) {
    return caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        const responseClone = response.clone();
        caches.open(STATIC_CACHE).then((cache) => {
          cache.put(request, responseClone);
        });
        return response;
      });
    });
  }

  // Default - network-first
  return fetch(request).catch(() => caches.match(request));
}

self.addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event));
});

// Listen for messages from clients (e.g., skip waiting for updates)
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
