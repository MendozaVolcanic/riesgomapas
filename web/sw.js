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
const VERSION = 'riesgomapas-v26';
const CACHE_APP = `${VERSION}-app`;
// La caché de teselas NO lleva la versión en el nombre, a propósito: son
// imágenes del mapa base que no cambian cuando cambia el sitio, y son lo más
// caro de volver a bajar. Llevándola, cada publicación —y REGLAS §7.4 obliga a
// publicar en cada cambio del frontend— dejaba a quien ya había navegado su
// comuna sin mapa base la próxima vez que se quedara sin señal, que es
// exactamente el escenario para el que existe este archivo.
const CACHE_TILES = 'riesgomapas-tiles';

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
  'data/estado-comunas.json',
  'data/poblacion-expuesta.json',
  'data/inventario.json',
  'data/laminas/vectorizadas.geojson',
];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE_APP);
    // addAll falla entero si un recurso falta; se agregan de a uno para que
    // una capa opcional ausente no impida instalar el service worker.
    await Promise.all(ARMAZON.map((u) => c.add(u).catch(() => null)));
    await c.add('data/jrc/rp100.geojson').catch(() => null);
    // Capa C regional del GORE. Faltaba, y su ausencia MENTÍA: sin señal la
    // ficha decía «capa no disponible en esta instalación» para una capa que sí
    // está publicada — y es la más fina que tiene el visor.
    await c.add('data/gore/amenaza-inundacion.geojson').catch(() => null);
    await c.add('data/planos/indice.json').catch(() => null);
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
    await Promise.all(nombres
      .filter((n) => !n.startsWith(VERSION) && n !== CACHE_TILES)
      .map((n) => caches.delete(n)));
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

  // Las dos bases del visor van a la caché de teselas. La satelital quedaba
  // fuera y caía en la rama de la app: quien dejó elegida esa vista abría el
  // visor durante un corte y recibía un lienzo vacío.
  if (url.hostname.includes('tile.openstreetmap.org')
      || url.hostname.includes('arcgisonline.com')) {
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
      const hit = await c.match(req);
      if (hit) return hit;
      // Sin red y sin copia. El index.html sólo sirve como respaldo de una
      // NAVEGACIÓN; devolverlo para cualquier cosa hacía que un PNG de plano o
      // un GeoJSON volvieran con 200 OK y contenido HTML, y el visor los daba
      // por buenos: el botón llegaba a decir «Plano cargado sobre el mapa» sin
      // que hubiera plano ninguno. Un error visible es mejor que un éxito falso.
      if (req.mode === 'navigate') {
        const inicio = await c.match('index.html');
        if (inicio) return inicio;
      }
      return new Response('sin red y sin copia guardada de este archivo',
        { status: 504, statusText: 'sin red', headers: { 'Content-Type': 'text/plain' } });
    }
  })());
});
