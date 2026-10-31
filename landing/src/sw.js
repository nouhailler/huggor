// Service worker de la vitrine uniquement. Il est indépendant de l'application HF Explorer
// (service web distinct, sur un autre domaine) : il ne met en cache que les fichiers statiques
// de ce site et ne rend en aucun cas l'application utilisable hors connexion.
const CACHE_NAME = 'huggor-landing-{{BUILD_ID}}';
const CORE_ASSETS = ['/', '/installer/', '/styles.css', '/main.js', '/estimator.js', '/favicon.svg', '/manifest.webmanifest'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) => Promise.all(names.filter((name) => name.startsWith('huggor-landing-') && name !== CACHE_NAME).map((name) => caches.delete(name))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }
  if (request.mode === 'navigate') {
    // Réseau d'abord : le contenu à jour prime, le cache ne sert qu'en secours.
    event.respondWith(fetch(request).catch(() => caches.match('/')));
    return;
  }
  // Réseau d'abord pour tout le reste aussi : pas de décalage entre HTML et scripts après un déploiement ;
  // le cache ne sert qu'en l'absence de réseau.
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(() => caches.match(request)),
  );
});
