/* Service worker — el sitio tiene que funcionar SIN SEÑAL.
 *
 * Es el requisito de diseño más importante del proyecto: durante una emergencia
 * por inundación se corta la energía y con ella la conexión. Un visor que
 * necesita internet justo en ese momento no sirve para nada.
 *
 * Estrategia:
 *   - El armazón (HTML/CSS/JS/datos) se precachea en la instalación.
 *   - Los datos se sirven "network first" con caída a caché: si hay señal
 *     traen la versión fresca, si no, la última que se descargó.
 *   - Los tiles del mapa base se cachean a medida que se navegan
 *     ("stale while revalidate"): la comuna que ya miraste queda disponible.
 */
// Subir este número en cada publicación: al activarse, el service worker borra
// las cachés de versiones anteriores.
const VERSION = 'riesgomapas-v8';
const CACHE_APP = `${VERSION}-app`;
const CACHE_TILES = `${VERSION}-tiles`;

const ARMAZON = [
  './',
  'index.html',
  'documentos.html',
  'style.css',
  'app.js',
  'catalogo.js',
  'manifest.json',
  'data/catalogo-documentos.json',
  'vendor/maplibre-gl.js',
  'vendor/maplibre-gl.css',
  'data/puntos-criticos-inundacion.geojson',
  'data/areas-riesgo-inundacion.geojson',
  'data/campamentos-inundacion.geojson',
  'data/indice-comunas.json',
];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE_APP);
    // addAll falla entero si un recurso falta; se agregan de a uno para que
    // una capa opcional ausente no impida instalar el service worker.
    await Promise.all(ARMAZON.map((u) => c.add(u).catch(() => null)));
    await c.add('data/jrc/rp100.geojson').catch(() => null);
    // Capa B (huella observada por Sentinel-1). Igual que el JRC: se agregan de
    // a uno y con `.catch`, porque todavía pueden no existir y un 404 dentro de
    // `addAll` dejaría al service worker sin instalar — o sea, sin visor offline,
    // que es justo lo que se necesita durante una inundación.
    for (const u of ['data/sar/huella-observada.geojson',
                     'data/sar/cobertura-sar.geojson',
                     'data/sar/indice.json']) {
      await c.add(u).catch(() => null);
    }
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const nombres = await caches.keys();
    await Promise.all(
      nombres.filter((n) => !n.startsWith(VERSION)).map((n) => caches.delete(n)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Nunca cachear el geocodificador: una dirección buscada offline debe fallar
  // de forma visible, no devolver un resultado viejo de otra consulta.
  if (url.hostname.includes('nominatim')) return;

  if (url.hostname.includes('tile.openstreetmap.org')) {
    e.respondWith((async () => {
      const c = await caches.open(CACHE_TILES);
      const hit = await c.match(req);
      const red = fetch(req).then((r) => { if (r.ok) c.put(req, r.clone()); return r; })
                            .catch(() => hit);
      return hit || red;
    })());
    return;
  }

  e.respondWith((async () => {
    const c = await caches.open(CACHE_APP);
    try {
      // `cache: 'no-cache'` fuerza a REVALIDAR contra el servidor en vez de
      // aceptar lo que tenga la caché HTTP del navegador. Sin esto, después de
      // publicar una corrección el usuario sigue viendo la versión anterior y no
      // hay forma de que se entere: nos pasó con una hoja de estilos que quedó
      // vieja y hacía parecer rotos controles que funcionaban.
      // No es caro: si el archivo no cambió, el servidor responde 304.
      const r = await fetch(req, { cache: 'no-cache' });
      if (r.ok) c.put(req, r.clone());
      return r;
    } catch {
      const hit = await c.match(req) || await c.match('index.html');
      if (hit) return hit;
      throw new Error('sin red y sin caché');
    }
  })());
});
