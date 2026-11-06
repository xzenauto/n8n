// Service worker de FitCoach: guarda la app para abrir rápido y funcionar sin conexión.
// Los datos (Supabase) nunca se cachean.
const CACHE = 'appgym-v14';

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(['./', './index.html', './manifest.webmanifest', './img/icon-192.png'])));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith('appgym-') && k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});

// Primero la red; sin conexión, la copia guardada.
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== self.location.origin || !url.pathname.startsWith(new URL(self.registration.scope).pathname)) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copia = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copia));
        return res;
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match('./index.html')))
  );
});

// Notificaciones push (frase de las 8:00 y recordatorio de hábitos de las 21:00)
self.addEventListener('push', (e) => {
  let d = {};
  try {
    d = e.data ? e.data.json() : {};
  } catch {
    d = { body: e.data ? e.data.text() : '' };
  }
  e.waitUntil(
    Promise.all([
      self.registration.showNotification(d.title || 'FitCoach', {
        body: d.body || '',
        icon: 'img/icon-192.png',
        badge: 'img/icon-192.png',
        data: { url: d.url || './' },
      }),
      // Diagnóstico: avisa a la app abierta de que ha llegado la notificación
      self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => list.forEach((c) => c.postMessage({ type: 'push', title: d.title, body: d.body }))),
    ])
  );
});

// La app pregunta qué versión del service worker está activa
self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'version' && e.ports && e.ports[0]) e.ports[0].postMessage(CACHE);
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || './', self.registration.scope).href;
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const c of list) if (c.url.startsWith(self.registration.scope) && 'focus' in c) return c.focus();
      return self.clients.openWindow(url);
    })
  );
});
