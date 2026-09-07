/* riesgomapas — prototipo Araucanía
 *
 * REGLA DE DECISIÓN (explícita a propósito: si el sitio le dice a alguien que su
 * casa está en riesgo, tiene que poder mostrar exactamente por qué lo dijo).
 *
 *   ALTO    ≥1 punto crítico de inundación de nivel Muy Alto/Alto a ≤300 m
 *           o ≥3 puntos de inundación de cualquier nivel a ≤300 m
 *   MEDIO   ≥1 punto crítico de inundación a ≤500 m
 *   BAJO    ningún punto a ≤500 m, pero sí alguno a ≤1500 m
 *   SIN DATO ningún punto a ≤1500 m
 *
 * "SIN DATO" NO es "seguro". Es ausencia de registro, que en comunas con poca
 * capacidad técnica municipal es exactamente lo que se espera encontrar.
 */
'use strict';

const RADIOS = { cercano: 300, medio: 500, contexto: 1500 };

/* Alcance del prototipo. Una sola definición: antes el bbox estaba copiado a
 * mano en las dos URL del geocodificador y no lo conocía nadie más, así que el
 * mapa se dejaba desplazar hasta Arica y un clic allá devolvía una ficha entera
 * vacía. Eso es lo peor que puede hacer este visor: «sin registros» leído como
 * «no se inunda» es exactamente el error que el resto del sitio se esfuerza en
 * evitar. Fuera del recuadro no se responde nada — se dice que no se sabe.
 *
 * El bbox es el mismo de config/araucania.yaml. Si la región cambia, se cambia
 * acá y en el YAML.
 */
const REGION = {
  nombre: 'La Araucanía',
  bbox: [-73.70, -39.65, -70.90, -37.35],   // [oeste, sur, este, norte]
  // Margen para poder ver el borde de la región sin que quede pegado al canto
  // de la pantalla. No amplía el alcance: `dentroDeRegion` usa el bbox pelado.
  margenGrados: 0.30,
};

const dentroDeRegion = (lon, lat) => {
  const [o, s, e, n] = REGION.bbox;
  return lon >= o && lon <= e && lat >= s && lat <= n;
};

/** Límites de desplazamiento del mapa, en el formato que espera MapLibre. */
const limitesMapa = () => {
  const [o, s, e, n] = REGION.bbox;
  const m = REGION.margenGrados;
  return [[o - m, s - m], [e + m, n + m]];
};

const estado = {
  puntos: null,        // FeatureCollection de puntos críticos de inundación
  jrc: null,           // FeatureCollection mancha modelada RP100
  gore: null,          // amenaza modelada regional del GORE 2016 (~35 m)
  sar: null,           // capa B — huella de agua observada por Sentinel-1
  sarCobertura: null,  // dónde el satélite SÍ pudo mirar (imprescindible: sin
                       // esto, "no hay huella" se confunde con "no se inundó")
  sarIndice: null,     // resumen del evento y de cada pasada
  comunas: null,
  mapa: null,
  marcador: null,
  ultimo: null,        // último resultado, para compartir
  base: 'calles',      // mapa base activo: 'calles' o 'satelite'
  estadoComunas: null, // qué tiene y qué le falta a cada comuna
  laminas: null,       // capa A DERIVADA: láminas que vectorizamos nosotros
  areasRiesgo: null,   // capa A normativa (MINVU)
  planos: null,        // planos de PRC georreferenciados
  campamentos: null,   // campamentos MINVU en área de riesgo
  // Precisión en metros que informó el GPS del aparato, o null si la posición
  // no viene de ahí (una dirección escrita, un toque en el mapa). Decide el
  // ancho de la franja donde el veredicto no puede distinguir adentro de
  // afuera, así que arrastrar la del GPS a una dirección escrita sería mentir.
  precisionPos: null,
};

const $ = (sel) => document.querySelector(sel);
const elEstado = () => $('#estado');

/* ------------------------------------------------------------------ datos */

async function cargarJSON(ruta) {
  const r = await fetch(ruta);
  if (!r.ok) throw new Error(`${ruta}: HTTP ${r.status}`);
  return r.json();
}

async function cargarDatos() {
  const [puntos, comunas] = await Promise.all([
    cargarJSON('data/puntos-criticos-inundacion.geojson'),
    cargarJSON('data/indice-comunas.json'),
  ]);
  estado.puntos = puntos;
  estado.comunas = comunas;
  // Capas opcionales: si aún no se generaron, el sitio funciona igual.
  try { estado.jrc = await cargarJSON('data/jrc/rp100.geojson'); } catch { estado.jrc = null; }
  try { estado.gore = await cargarJSON('data/gore/amenaza-inundacion.geojson'); }
  catch { estado.gore = null; }
  try {
    estado.areasRiesgo = await cargarJSON('data/areas-riesgo-inundacion.geojson');
  } catch { estado.areasRiesgo = null; }
  // Índice de planos de plan regulador georreferenciados. Sólo el índice: las
  // imágenes pesan ~900 KB cada una y se cargan cuando hacen falta (ver
  // `mostrarPlano`), no al abrir el sitio.
  try {
    estado.planos = (await cargarJSON('data/planos/indice.json')).planos || [];
  } catch { estado.planos = []; }

  // Inventario del vacío por comuna. Es lo que se comparte: «en mi comuna no
  // hay ningún mapa de inundación» es un hecho verificable que no predice nada
  // y no asusta a nadie hacia una mala decisión, al revés que un veredicto
  // sobre una casa. Ver docs/DIFUSION.md §0b.
  // Capa A DERIVADA: láminas que convertimos nosotros desde documentos
  // impresos. Va aparte de `areasRiesgo` a propósito y nunca se fusiona: el
  // vectorial del MINVU tiene efecto legal y esto no.
  try {
    estado.laminas = await cargarJSON('data/laminas/vectorizadas.geojson');
  } catch { estado.laminas = null; }

  try {
    estado.estadoComunas =
      (await cargarJSON('data/estado-comunas.json')).comunas || [];
  } catch { estado.estadoComunas = []; }
  try {
    estado.campamentos = await cargarJSON('data/campamentos-inundacion.geojson');
  } catch { estado.campamentos = null; }
  // Capa B — huella observada por Sentinel-1. Las tres piezas se cargan por
  // separado a propósito: la cobertura vale por sí sola aunque no haya ninguna
  // huella (sirve para responder "el satélite miró y no vio agua"), y el índice
  // sólo aporta el resumen del evento.
  try { estado.sar = await cargarJSON('data/sar/huella-observada.geojson'); }
  catch { estado.sar = null; }
  try { estado.sarCobertura = await cargarJSON('data/sar/cobertura-sar.geojson'); }
  catch { estado.sarCobertura = null; }
  try { estado.sarIndice = await cargarJSON('data/sar/indice.json'); }
  catch { estado.sarIndice = null; }

  const p = puntos.procedencia || {};
  $('#sello-datos').textContent =
    `${puntos.features.length} puntos críticos de origen hídrico · ` +
    `${p.fecha_dato || ''} · datos generados ${(p.generado || '').slice(0, 10)}`;
}

/* --------------------------------------------------------------- geometría */

function distancia(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function dentroAnillo(lon, lat, anillo) {
  let dentro = false;
  for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
    const [xi, yi] = anillo[i], [xj, yj] = anillo[j];
    if ((yi > lat) !== (yj > lat) &&
        lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) dentro = !dentro;
  }
  return dentro;
}

/** Devuelve los features del FeatureCollection que contienen el punto. */
function poligonosQueContienen(lon, lat, fc) {
  const dentro = [];
  if (!fc) return dentro;
  for (const f of fc.features) {
    const g = f.geometry;
    if (!g) continue;
    const polis = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
    for (const poli of polis) {
      if (dentroAnillo(lon, lat, poli[0]) &&
          !poli.slice(1).some((h) => dentroAnillo(lon, lat, h))) { dentro.push(f); break; }
    }
  }
  return dentro;
}

function dentroDeMancha(lon, lat, fc) {
  return poligonosQueContienen(lon, lat, fc).length > 0;
}

/* --------------------------------------------------------- borde del dato
 *
 * El sitio pide «mira la mancha, no su borde» y a la vez respondía «no cae
 * dentro» a un punto que estaba a tres metros de esa mancha. Las dos cosas no
 * pueden ser ciertas: si el borde tiene ±7,7 m de incertidumbre —el píxel de la
 * figura de Angol— y tu ubicación otros tantos, adentro y afuera no se
 * distinguen a esa distancia, y decir «no» con la misma cara que se dice «no» a
 * un kilómetro es afirmar algo que el dato no sostiene.
 *
 * Medido el 6-sep-2026 sobre las manzanas del Censo 2024: en Catripulli el 37 %
 * de la gente vive a menos de 10 m del borde de la mancha derivada. Una de cada
 * tres personas estaba recibiendo un veredicto binario sobre una franja donde el
 * dato no alcanza a decidir.
 */

/** Cota mínima del borde de un polígono que no declara su incertidumbre.
 *  No sale de la fuente: es una elección del visor, del orden del grosor de una
 *  línea de trazo a la escala de un plan regulador (0,5 mm a 1:20.000 son 10 m).
 *  Los datos que SÍ la declaran —las láminas que vectorizamos— usan la suya. */
const BORDE_MINIMO_M = 10;

function _distPuntoSegmento(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay;
  if (dx === 0 && dy === 0) return Math.hypot(px - ax, py - ay);
  let t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy);
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

/** Incertidumbre del borde de un polígono, en metros: la que declare el dato, o
 *  la cota mínima del visor. */
function incertidumbreBorde(f) {
  const i = Number(f && f.properties && f.properties.incertidumbre_borde_m);
  return Number.isFinite(i) && i > 0 ? i : BORDE_MINIMO_M;
}

/** El polígono cuyo borde está más cerca del punto, y a cuántos metros, dentro
 *  de `tope`. Devuelve null si ninguno cae dentro del tope.
 *
 *  Trabaja en metros locales (la latitud fija la escala de la longitud), que a
 *  estas distancias es indistinguible de hacerlo sobre el elipsoide y no obliga
 *  a traer una librería de proyecciones a una PWA que tiene que caber en pocos
 *  kilobytes. El pre-filtro por caja envolvente es lo que permite recorrer las
 *  2.539 manchas del modelo regional sin que la consulta se note. */
function bordeMasCercano(lon, lat, fc, tope) {
  if (!fc || !fc.features) return null;
  const mLat = 111320, mLon = 111320 * Math.cos(lat * Math.PI / 180);
  const gLat = tope / mLat, gLon = tope / mLon;
  let mejor = null;
  for (const f of fc.features) {
    const g = f.geometry;
    if (!g) continue;
    const polis = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
    for (const poli of polis) {
      for (const anillo of poli) {
        // Caja envolvente del anillo, ampliada por el tope.
        let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
        for (const [x, y] of anillo) {
          if (x < w) w = x; if (x > e) e = x;
          if (y < s) s = y; if (y > n) n = y;
        }
        if (lon < w - gLon || lon > e + gLon || lat < s - gLat || lat > n + gLat) continue;
        const px = lon * mLon, py = lat * mLat;
        for (let i = 1; i < anillo.length; i++) {
          const d = _distPuntoSegmento(px, py,
            anillo[i - 1][0] * mLon, anillo[i - 1][1] * mLat,
            anillo[i][0] * mLon, anillo[i][1] * mLat);
          if (d <= tope && (!mejor || d < mejor.d)) mejor = { d, f };
        }
      }
    }
  }
  return mejor;
}

/** Planos de plan regulador cuya hoja cubre este punto. */
function planosQueCubren(lon, lat) {
  return (estado.planos || []).filter((p) => {
    const [w, s, e, n] = p.bounds_wgs84;
    return lon >= w && lon <= e && lat >= s && lat <= n;
  });
}

// Zoom mínimo para cargar la imagen de un plano. Por debajo de esto la hoja
// mide menos de 50 px en pantalla —a zoom regional son 9x7 px, invisibles— y
// cargar 23 imágenes de ~870 KB para no mostrar nada es lo peor de los dos
// mundos: el usuario cree que el control no funciona mientras baja 19 MB.
/** Las ocho casillas que encienden capas del mapa. Vive acá arriba porque la
 *  usan dos cosas: el botón «todas / ninguna» y la sincronización que corre
 *  cuando el mapa termina de agregar capas. */
const CASILLAS_CAPAS = ['cap-areas', 'cap-derivadas', 'cap-planos', 'cap-sar',
                        'cap-gore', 'cap-jrc', 'cap-puntos', 'cap-camp'];

const ZOOM_MIN_PLANO = 11;
const MAX_PLANOS_SIMULTANEOS = 6;

/** Rectángulos con la extensión de cada plano. Son 23 polígonos: se pueden
 *  mostrar a cualquier zoom y sirven para que se VEA dónde hay plano
 *  disponible, en vez de dejar al usuario adivinando. */
function huellasGeoJSON() {
  return {
    type: 'FeatureCollection',
    features: (estado.planos || []).map((p, i) => {
      const [w, s, e, n] = p.bounds_wgs84;
      return {
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] },
        properties: { i, titulo: p.titulo, rmse: p.rmse_loo_m, archivo: p.archivo },
      };
    }),
  };
}

/** Agrega la imagen del plano al mapa. Se carga acá y no al inicio: cada plano
 *  pesa cerca de 1 MB y cargarlos todos volvería inusable el sitio en 3G. */
function mostrarPlano(p) {
  const m = estado.mapa;
  if (!m || !m.isStyleLoaded()) return false;
  const id = `plano-${p.archivo.replace(/[^\w]/g, '')}`;
  if (m.getLayer(id)) {
    m.setLayoutProperty(id, 'visibility', 'visible');
    return true;
  }
  const [w, s, e, n] = p.bounds_wgs84;
  m.addSource(id, {
    type: 'image',
    // encodeURIComponent por si algún nombre trae caracteres no-ASCII. Los
    // archivos se publican ya normalizados a ASCII (script 10), pero un 404 acá
    // no da error visible: la capa simplemente se ve vacía, que es el peor modo
    // de fallar. Cinturón y tirantes.
    url: `data/planos/${encodeURIComponent(p.archivo)}`,
    coordinates: [[w, n], [e, n], [e, s], [w, s]],
  });
  // Debajo de los puntos críticos y de las áreas de riesgo: el plano es el
  // fondo documental, no debe tapar las capas de datos.
  const primera = ['ar-fill', 'pc-circ'].find((c) => m.getLayer(c));
  m.addLayer({ id, type: 'raster', source: id,
               paint: { 'raster-opacity': 0.9, 'raster-fade-duration': 200 } }, primera);
  return true;
}

function ocultarPlanos() {
  const m = estado.mapa;
  if (!m) return;
  // Se LIBERAN, no se ocultan. Cada plano es una textura de ~870 KB en memoria
  // de video, y `MAX_PLANOS_SIMULTANEOS` limita cuántos se ven a la vez, no
  // cuántos quedan cargados: al panear la región se llegaban a acumular las 20.
  // El público objetivo son celulares de gama baja, donde eso es la diferencia
  // entre un mapa que anda y una pestaña que el sistema mata.
  //
  // ⚠️ NO se pone `isStyleLoaded()` como guardián.
  //
  // Apagar la capa ocurre justo después de cargar una imagen, que es cuando el
  // estilo está ocupado y `isStyleLoaded()` devuelve false. Con esa guarda la
  // limpieza se saltaba ENTERA y en silencio: no había error, sólo texturas que
  // quedaban vivas para siempre. `getLayer`/`removeLayer` funcionan igual
  // mientras el estilo exista; si todavía no existe, se reintenta al quedar
  // quieto el mapa.
  let listo = true;
  for (const p of estado.planos || []) {
    const id = `plano-${p.archivo.replace(/[^\w]/g, '')}`;
    try {
      if (m.getLayer(id)) m.removeLayer(id);
      if (m.getSource(id)) m.removeSource(id);
    } catch { listo = false; }
  }
  if (!listo) m.once('idle', ocultarPlanos);
}

function planosEnVista() {
  const m = estado.mapa;
  if (!m) return [];
  const b = m.getBounds();
  return (estado.planos || []).filter((p) => {
    const [w, s, e, n] = p.bounds_wgs84;
    return e >= b.getWest() && w <= b.getEast() && n >= b.getSouth() && s <= b.getNorth();
  });
}

/** Carga los planos de la vista, con guardas de zoom y de cantidad. */
function actualizarPlanos(avisar = false) {
  const m = estado.mapa;
  const casilla = $('#cap-planos');
  if (!m || !casilla || !casilla.checked || !m.isStyleLoaded()) return;

  if (m.getZoom() < ZOOM_MIN_PLANO) {
    ocultarPlanos();
    if (avisar) {
      elEstado().textContent =
        'Los recuadros marcan dónde hay plano. Acerca el mapa a uno (o tócalo) ' +
        'para verlo: a esta escala la hoja mide unos pocos píxeles.';
    }
    return;
  }
  const enVista = planosEnVista();
  if (!enVista.length) {
    if (avisar) {
      elEstado().textContent = 'No hay planos de plan regulador en esta zona.';
    }
    return;
  }
  const cargar = enVista.slice(0, MAX_PLANOS_SIMULTANEOS);
  cargar.forEach(mostrarPlano);
  elEstado().textContent = enVista.length > cargar.length
    ? `Mostrando ${cargar.length} de ${enVista.length} planos; acerca más para el resto.`
    : '';
}

/* ------------------------------------------------------------------ fechas */

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
               'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

/** "2026-08-04" → "4 de agosto de 2026". Devuelve null si la fuente no trae una
 *  fecha con forma de fecha: el año no se inventa ni se rellena. Se parsea a
 *  mano y no con `new Date`, que interpreta la cadena en UTC y en Chile puede
 *  mostrar el día anterior. */
function fechaLarga(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso ?? ''));
  if (!m) return null;
  const mes = MESES[+m[2] - 1];
  return mes ? `${+m[3]} de ${mes} de ${m[1]}` : null;
}

/** Fechas distintas de pasada del satélite sobre este punto, ya legibles. */
function fechasDePasada(features) {
  return [...new Set((features || [])
    .map((f) => f.properties?.fecha_observacion).filter(Boolean))]
    .sort()
    .map((d) => fechaLarga(d) || d);
}

function listaEnEspanol(xs) {
  if (xs.length <= 1) return xs[0] || '';
  return `${xs.slice(0, -1).join(', ')} y ${xs[xs.length - 1]}`;
}

/* ------------------------------------------------------------- evaluación */

function evaluar(lon, lat) {
  const cerca = [];
  for (const f of estado.puntos.features) {
    const [flon, flat] = f.geometry.coordinates;
    const d = distancia(lat, lon, flat, flon);
    if (d <= RADIOS.contexto) cerca.push({ f, d });
  }
  cerca.sort((a, b) => a.d - b.d);

  const en = (r) => cerca.filter((c) => c.d <= r);
  const graves = en(RADIOS.cercano)
    .filter((c) => ['Muy Alto', 'Alto'].includes(c.f.properties.nivel));

  // Capa A: áreas de riesgo del plan regulador. Es la única con efecto legal,
  // así que si el punto cae dentro de una, manda sobre el resto.
  const areas = poligonosQueContienen(lon, lat, estado.areasRiesgo);

  // Capa B: huella observada por radar. Manda con la misma fuerza que el área
  // normativa —y se evalúa antes— porque no es una declaración ni un modelo:
  // es agua medida en el terreno en una fecha concreta. Las dos ramas dejan el
  // nivel en 'alto', así que el orden sólo decide qué titular se muestra.
  const sar = poligonosQueContienen(lon, lat, estado.sar);
  const coberturaSar = poligonosQueContienen(lon, lat, estado.sarCobertura);

  // Capa A DERIVADA: las láminas de peligro que vectorizamos nosotros desde el
  // documento impreso. Se dibujaban en el mapa y no entraban acá, así que un
  // vecino de Angol parado dentro del AR-2a de su propio plan regulador leía
  // «no cae dentro de un área de riesgo»: Angol y Curarrehue no tienen ni un
  // polígono en el vectorial del MINVU, de modo que ésta es la única evidencia
  // normativa que existe para ellas y era justo la que el veredicto no miraba.
  const laminas = poligonosQueContienen(lon, lat, estado.laminas);
  const gore = poligonosQueContienen(lon, lat, estado.gore);
  const enMancha = dentroDeMancha(lon, lat, estado.jrc);

  // Si no cae dentro de nada, ¿cae en la franja donde el dato ya no distingue?
  const precision = estado.precisionPos || 0;
  let borde = null;
  if (!sar.length && !areas.length && !laminas.length) {
    for (const [capa, fc] of [['normativa', estado.areasRiesgo],
                              ['derivada', estado.laminas],
                              ['observada', estado.sar]]) {
      if (!fc) continue;
      const tope = BORDE_MINIMO_M * 2 + precision;
      const b = bordeMasCercano(lon, lat, fc, tope);
      if (b && b.d <= incertidumbreBorde(b.f) * 2 + precision &&
          (!borde || b.d < borde.d)) borde = { ...b, capa };
    }
  }

  let nivel, titulo;
  if (sar.length >= 1) {
    nivel = 'alto';
    const f = fechaLarga(sar[0].properties.fecha_observacion);
    titulo = f ? `El agua llegó hasta acá el ${f}`
               : 'El agua llegó hasta acá: huella observada por satélite';
  } else if (areas.length >= 1) {
    nivel = 'alto';
    // El fenómeno se nombra acá, no sólo en la pestaña de detalle. Que el río
    // se salga y que el colector no dé abasto son cosas distintas —otra física,
    // otra mitigación y otro servicio a quién reclamarle—, el sitio lo argumenta
    // en todas partes, y el titular seguía llamando «inundación» a los seis
    // polígonos de anegamiento, napa y marejada.
    const t = areas[0].properties.tipo_hidrico;
    titulo = t && t !== 'fluvial'
      ? `Estás en un área de riesgo por ${FENOMENO_CORTO[t] || t} del plan regulador`
      : 'Estás en un área de riesgo por inundación del plan regulador';
  } else if (laminas.length >= 1) {
    nivel = 'alto';
    // El título distingue lo que la fuente distingue: 26 de estos polígonos son
    // el área de riesgo de un plan regulador aprobado —traen `efecto_legal`— y
    // el resto son levantamientos de riesgo sin efecto normativo propio.
    titulo = laminas.some((f) => f.properties.efecto_legal)
      ? 'Estás en un área de riesgo por inundación del plan regulador'
      : 'Estás dentro de la zona que el estudio de riesgo de tu comuna marcó como inundable';
  } else if (borde) {
    // Ni dentro ni fuera: en la franja donde el borde del dato y la precisión
    // de tu ubicación se superponen. Decir «no» acá sería afirmar de más.
    nivel = 'medio';
    titulo = 'Estás justo en el borde de un área marcada como inundable';
  } else if (graves.length >= 1 || en(RADIOS.cercano).length >= 3) {
    nivel = 'alto';
    titulo = 'Tu sector tiene registro de inundaciones';
  } else if (en(RADIOS.medio).length >= 1) {
    nivel = 'medio';
    titulo = 'Hay registros de inundación cerca';
  } else if (cerca.length >= 1) {
    nivel = 'bajo';
    titulo = 'Registros de inundación a cierta distancia';
  } else if (gore.length || enMancha) {
    // No hay registro NI norma, pero un modelo sí dice algo de este punto.
    // «Sin registros en las fuentes consultadas» era falso acá: el modelo
    // regional es una fuente consultada, se muestra en la misma ficha, y a
    // veces clasifica el punto como amenaza máxima. Las capas no se fusionan
    // (REGLAS §1.3), así que el modelo no levanta el nivel — pero el titular
    // deja de negar lo que la ficha de más abajo afirma.
    nivel = 'sindato';
    titulo = 'Sin registros observados ni norma, pero un modelo sí marca este punto';
  } else {
    nivel = 'sindato';
    titulo = 'Sin registros en las fuentes consultadas';
  }

  return { nivel, titulo, cerca, areas, sar, coberturaSar, laminas, borde,
           enCoberturaSar: coberturaSar.length > 0,
           planos: planosQueCubren(lon, lat),
           campamentos: poligonosQueContienen(lon, lat, estado.campamentos),
           enMancha, gore };
}

/* ------------------------------------------------- estado de la comuna */

/** Busca en el inventario la comuna a la que pertenece el punto consultado.
 *  Se resuelve por el punto crítico más cercano, que ya trae su comuna: es más
 *  fiable que geocodificar de vuelta y funciona sin señal. */
function comunaDe(res, lon, lat) {
  if (!estado.estadoComunas || !estado.puntos) return null;
  // Se busca en TODOS los puntos, no sólo en los de 1,5 km.
  //
  // Con el radio de contexto, un lugar sin registros cerca no tenía comuna — y
  // ése es justo el caso donde el inventario más importa: quien recibe «sin
  // registros» es quien más necesita leer «tu comuna no tiene mapa». Era la
  // única persona que no lo veía.
  //
  // Cerca de un deslinde esto puede atribuir la comuna vecina. Por eso el
  // bloque muestra el nombre en grande: un error se ve al tiro. Resolverlo bien
  // pide el límite administrativo oficial, que el proyecto todavía no tiene.
  //
  // Antes de recurrir al punto más cercano se mira si el punto cae DENTRO de
  // algún polígono que ya declare su comuna. Eso es exacto y no depende de
  // distancias. Importa porque el vecino sólo funcionaba con los puntos de
  // inundación fluvial, y hay comunas que no tienen ninguno: Temuco y Victoria
  // no podían salir NUNCA. La Plaza de Temuco se atribuía a Padre Las Casas, a
  // 1,6 km, y con ella el inventario y la solicitud por Ley 20.285 salían a
  // nombre de otra comuna.
  let mejor = null;
  let dmin = Infinity;
  for (const fc of [estado.areasRiesgo, estado.laminas, estado.campamentos]) {
    for (const f of poligonosQueContienen(lon, lat, fc)) {
      if (f.properties && f.properties.comuna) { mejor = f.properties.comuna; dmin = 0; break; }
    }
    if (mejor) break;
  }
  if (!mejor) {
    for (const f of estado.puntos.features) {
      const [flon, flat] = f.geometry.coordinates;
      const d = distancia(lat, lon, flat, flon);
      if (d < dmin) { dmin = d; mejor = f.properties.comuna; }
    }
    // Más allá de esto el punto más cercano ya no dice nada de la comuna: en el
    // mar frente a Saavedra el más cercano estaba a 16 km, y el visor mostraba
    // el inventario de esa comuna como si el punto fuera suyo.
    if (dmin > 8000) return null;
  }
  if (!mejor) return null;
  const k = (t) => String(t || '').normalize('NFD')
    .replace(/[̀-ͯ]/g, '').replace(/[^a-z]/gi, '').toLowerCase();
  const c = estado.estadoComunas.find((x) => k(x.comuna) === k(mejor));
  return c ? { ...c, _km: Math.round(dmin / 100) / 10 } : null;
}

/** Qué tiene y qué le falta a la comuna, en la pestaña de detalle.
 *
 *  Es deliberadamente la unidad que se comparte, y no la ficha de un punto.
 *  «En mi comuna no hay ningún mapa de inundación» es verificable, no predice
 *  nada y no empuja a nadie a una mala decisión; un veredicto sobre una casa
 *  reenviado por WhatsApp sí puede. Ver docs/DIFUSION.md §0b.
 */
function bloqueComuna(c) {
  if (!c) return '';
  const n = (v) => (v === null || v === undefined)
    ? '<span class="incert">sin dato</span>' : v.toLocaleString('es-CL');
  const tiene = [];
  if (c.poligonos_area_riesgo) {
    tiene.push(`${c.poligonos_area_riesgo} polígono(s) de área de riesgo en el
                vectorial público del MINVU`);
  }
  if (c.laminas_localizadas) {
    tiene.push(`${c.laminas_localizadas} lámina(s) de cartografía localizadas
                dentro de ${c.documentos} documento(s) públicos`);
  }
  if (c.planos_georreferenciados) {
    const est = Object.entries(c.planos_por_estado || {})
      .map(([k, v]) => `${v} ${k.toLowerCase()}`).join(', ');
    tiene.push(`${c.planos_georreferenciados} plano(s) ubicados sobre el mapa
                (${esc(est)})`);
  }
  if (c.poligonos_vectorizados_por_nosotros) {
    tiene.push(`${c.poligonos_vectorizados_por_nosotros} polígono(s) que
                convertimos nosotros desde una lámina impresa`);
  }

  return `<div class="evidencia bloque-comuna">
    <h3>Con qué cuenta ${esc(c.comuna)} <span class="etiqueta">INVENTARIO</span></h3>
    <p class="incert">Esto no dice si tu casa se inunda. Dice qué información
       existe para saberlo, y es lo que hace falta para exigir que la haya.</p>
    <ul class="cifras-comuna">
      <li><strong>${n(c.personas)}</strong> habitantes (Censo 2024)</li>
      <li><strong>${n(c.puntos_inundacion)}</strong> puntos donde el municipio
          reportó inundación, <strong>${n(c.puntos_cronicos)}</strong> de ellos
          repetidos en 3 o más temporadas</li>
    </ul>
    ${tiene.length
      ? `<p><strong>Qué hay:</strong></p><ul><li>${tiene.join('</li><li>')}</li></ul>`
      : '<p><strong>No encontramos nada consultable para esta comuna.</strong></p>'}
    ${c.le_falta.length
      ? `<p><strong>Qué falta:</strong></p><ul class="falta"><li>${
          c.le_falta.map(esc).join('</li><li>')}</li></ul>`
      : '<p>No detectamos vacíos en las fuentes que revisamos.</p>'}
    <div class="acciones">
      <button type="button" class="secundario" id="btn-compartir-comuna">
        Compartir el estado de ${esc(c.comuna)}</button>
      <button type="button" class="secundario" id="btn-solicitud">
        Pedirle el mapa a la autoridad</button>
    </div>
    <p class="incert">La solicitud usa la <strong>Ley 20.285</strong>: el
       organismo está obligado a responderte por escrito en 20 días hábiles. Se
       envía en
       <a href="https://www.portaltransparencia.cl" rel="noopener"
          target="_blank">portaltransparencia.cl</a>, es gratis y no necesitas
       abogado.</p>
  </div>`;
}

/** Solicitud de acceso a información, Ley 20.285, lista para enviar.
 *
 *  Por qué el visor la genera en vez de sólo mostrar el vacío: porque el vacío
 *  sin un camino de acción es sólo una queja. Un organismo del Estado está
 *  obligado a responder por escrito en 20 días hábiles, y **las dos respuestas
 *  posibles sirven**: si el mapa existe, se pide y el visor mejora; si no
 *  existe, el vacío queda documentado con timbre y fecha, que es lo que
 *  convierte «lo dicen dos geólogos» en «lo dice el organismo».
 *
 *  Se dirige al organismo que corresponde según lo que falte, no a uno
 *  genérico: el instrumento es del MINVU, la amenaza hidráulica es de la DGA.
 */
function textoSolicitud(c) {
  const sinArea = !c.poligonos_area_riesgo;
  const l = [
    `Solicitud de acceso a información pública (Ley N° 20.285)`,
    ``,
    `Materia: cartografía de amenaza y áreas de riesgo por inundación en la `
    + `comuna de ${c.comuna}, Región de La Araucanía.`,
    ``,
    `De acuerdo a la Ley N° 20.285 sobre Acceso a la Información Pública, `
    + `solicito la siguiente información:`,
    ``,
    `1. Si esa institución dispone de cartografía de amenaza o de áreas de `
    + `riesgo por inundación fluvial para la comuna de ${c.comuna}, indicando `
    + `su fecha de elaboración y la metodología empleada.`,
    `2. En caso afirmativo, copia digital de dicha cartografía en formato `
    + `vectorial (shapefile, GeoJSON o equivalente), junto con el estudio que `
    + `la fundamenta.`,
    `3. En caso negativo, indicar si existe algún estudio en curso o `
    + `programado, y qué organismo tiene la competencia para elaborarlo.`,
  ];
  if (sinArea) {
    l.push(`4. Si el Plan Regulador Comunal vigente de ${c.comuna} define áreas `
           + `de riesgo por inundación conforme al artículo 2.1.17 de la `
           + `Ordenanza General de Urbanismo y Construcciones, y por qué razón `
           + `dicha cartografía no se encuentra disponible en el servicio `
           + `público de datos territoriales del MINVU.`);
  }
  l.push(``,
    `Fundamento de la consulta: al revisar fuentes públicas no fue posible `
    + `encontrar esta información en formato consultable para la comuna. `
    + `Específicamente:`);
  for (const f of c.le_falta) l.push(`   • ${f}`);
  l.push(``,
    `Solicito la respuesta en formato digital al correo electrónico que indico `
    + `en este formulario.`,
    ``,
    `Saluda atentamente,`);
  return l.join('\n');
}

/** El texto que se reenvía. Se arma acá y no se deriva del HTML para que diga
 *  exactamente lo mismo que la pantalla, sin adornos ni recortes. */
function textoComuna(c) {
  const l = [`${c.comuna.toUpperCase()} — ¿qué información hay sobre inundaciones?`, ''];
  if (c.personas) l.push(`${c.personas.toLocaleString('es-CL')} habitantes (Censo 2024)`);
  l.push(`${c.puntos_inundacion} puntos con inundación reportada por el municipio`
         + (c.puntos_cronicos ? `, ${c.puntos_cronicos} de ellos crónicos` : ''));
  l.push('');
  if (c.le_falta.length) {
    l.push('LO QUE FALTA:');
    for (const f of c.le_falta) l.push(`• ${f}`);
  } else {
    l.push('No detectamos vacíos en las fuentes que revisamos.');
  }
  l.push('',
    'Que falte el mapa NO significa que no se inunde: significa que nadie lo ha',
    'levantado. Chile no tiene un mapa nacional de inundaciones.',
    '',
    'Proyecto abierto de Nicolás Mendoza y Roberto Laregla, geólogos.',
    'A título personal, sin respaldo institucional.',
    'No es información oficial ni un pronóstico.');
  return l.join('\n');
}

/* ---------------------------------------------------------------- resumen */

/** La frase que explica el veredicto, en una línea y sin jerga.
 *
 *  Nombra la evidencia que MANDÓ, no todas: quien pregunta si se le inunda la
 *  casa necesita una razón, no un inventario. El inventario está a un toque.
 */
function porQue(res) {
  if (res.sar.length) {
    const f = fechaLarga(res.sar[0].properties.fecha_observacion);
    return `Un satélite midió agua sobre este punto${f ? ` el ${f}` : ''}. No es un
            modelo: es agua que estuvo ahí.`;
  }
  if (res.areas.length) {
    const t = res.areas[0].properties.tipo_hidrico;
    return `El plan regulador de tu comuna declaró esta zona <strong>área de riesgo
            por ${esc(t && t !== 'fluvial' ? (FENOMENO_CORTO[t] || t) : 'inundación')}</strong>.
            Es la única fuente con efecto legal.`;
  }
  if (res.laminas.length) {
    const p = res.laminas[0].properties;
    const norma = res.laminas.some((f) => f.properties.efecto_legal);
    return `${norma
      ? `El plano del plan regulador de tu comuna raya esta zona como
         <strong>área de riesgo por inundación</strong>`
      : `El estudio de riesgo de tu comuna (${esc(p.anio)}) marcó esta zona como
         <strong>${esc(String(p.clase).toLowerCase())}</strong>`}.
      Ese documento existe sólo en papel: la mancha la dibujamos nosotros desde
      la lámina impresa, con ±${esc(num(incertidumbreBorde(res.laminas[0])))} m
      de incertidumbre en el borde.`;
  }
  if (res.borde) {
    const i = incertidumbreBorde(res.borde.f);
    return `Estás a ${Math.round(res.borde.d)} metros del borde de un área marcada
            como inundable. Ese borde tiene ±${num(i)} m de incertidumbre${
              estado.precisionPos ? ` y tu ubicación ±${Math.round(estado.precisionPos)} m` : ''},
            así que a esta distancia <strong>adentro y afuera no se distinguen</strong>.`;
  }
  const cercanos = res.cerca.filter((c) => c.d <= RADIOS.medio);
  if (cercanos.length) {
    const cronicos = cercanos.filter((c) => c.f.properties.cronico).length;
    return `Hay ${cercanos.length} punto${cercanos.length > 1 ? 's' : ''} donde el
            municipio reportó inundación a menos de 500 metros` +
           (cronicos ? `, y ${cronicos} se ${cronicos > 1 ? 'repiten' : 'repite'}
            temporada tras temporada.` : '.');
  }
  if (res.cerca.length) {
    return `El registro más cercano de inundación está a
            ${Math.round(res.cerca[0].d)} metros.`;
  }
  // Antes esta frase se mostraba también cuando el modelo regional clasificaba
  // el punto como amenaza máxima cuatro párrafos más abajo, en la misma ficha.
  if (res.gore.length || res.enMancha) {
    const cl = res.gore.length ? String(res.gore[0].properties.clase || '').toLowerCase() : '';
    return `Ningún registro observado ni norma alcanza este punto, pero
            ${res.gore.length
              ? `el modelo regional de 2016 lo clasifica como amenaza
                 <strong>${esc(cl)}</strong>`
              : `cae dentro de la mancha modelada para una crecida de 100 años`}.
            Un modelo no es un registro: dice dónde podría llegar el agua, no
            dónde llegó.`;
  }
  return `Ninguna de las fuentes consultadas registra inundación en este punto.`;
}

/** Respuesta corta: veredicto, una razón, y el camino a la evidencia. */
function resumen(res, etiqueta) {
  const cont = $('#respuesta');
  let html = `
    <div class="veredicto v-${res.nivel}">
      <span class="icono" aria-hidden="true">${ICONO[res.nivel]}</span>
      <h2>${esc(res.titulo)}</h2>
    </div>
    <p class="direccion">📍 ${esc(etiqueta)}</p>
    <p class="por-que">${porQue(res)}</p>`;

  // «Sin registros» es el veredicto que más fácil se lee al revés. La aclaración
  // va pegada al titular, no enterrada — y viaja también en el texto que se
  // comparte por WhatsApp.
  if (res.nivel === 'sindato') {
    html += `<p class="aviso-fuerte">Que no haya registro <strong>no significa que
             acá no se inunde</strong>. Significa que nadie lo ha levantado. En
             comunas con poca capacidad técnica municipal es lo esperable.</p>`;
  }
  html += `<div class="acciones">
    <button type="button" id="btn-ver-detalle">Ver todo el detalle y las fuentes</button>
    <button type="button" class="secundario" id="btn-compartir-corto">Compartir</button>
  </div>`;
  cont.innerHTML = html;
  cont.classList.remove('oculto');
  $('#btn-ver-detalle').addEventListener('click', () => irAPestana('detalle'));
  $('#btn-compartir-corto').addEventListener('click', compartir);
}

/* ----------------------------------------------------------------- render */

const ICONO = { alto: '⚠️', medio: '⚡', bajo: 'ℹ️', sindato: '❔' };

/* Cómo se nombra cada fenómeno hídrico en pantalla. Sólo se muestra cuando NO
 * es fluvial: el visor es de inundación fluvial, así que lo que hay que
 * advertir es cuando un polígono declara otra cosa. */
/** El fenómeno en dos palabras, para el titular. La versión larga de abajo
 *  explica; ésta sólo tiene que evitar que un anegamiento se lea como desborde. */
const FENOMENO_CORTO = {
  anegamiento: 'anegamiento',
  napa_freatica: 'afloramiento de napa',
  litoral: 'inundación litoral',
};
const FENOMENO = {
  anegamiento: 'anegamiento, no desborde',
  napa_freatica: 'afloramiento de napa',
  litoral: 'inundación litoral (marejada), no fluvial',
};
const CLASE_NIVEL = {
  'Muy Alto': 'p-muyalto', 'Alto': 'p-alto', 'Medio': 'p-medio', 'Bajo': 'p-bajo',
};

function esc(t) {
  return String(t ?? '').replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/** Línea de atribución. Todo dato mostrado tiene que decir de dónde salió y de
 *  cuándo es: un área de riesgo de un plan regulador de 1978 no significa lo
 *  mismo que una de 2022, y un modelo de 2016 no conoce las obras posteriores.
 *  Se lee del sello que cada feature trae pegado, no de una constante del
 *  frontend, para que no se pueda desincronizar del dato. */
/** Un número en el español de Chile: coma decimal. El resto del sitio ya lo
 *  hace en la ficha del satélite; la incertidumbre del borde salía «7.7 m». */
function num(x) {
  return String(x).replace('.', ',');
}

function atribucion(fc, primerFeature) {
  const p = primerFeature?.properties || {};
  const proc = fc?.procedencia || {};
  const fuente = p.fuente || proc.fuente || 'fuente no declarada';
  // Sin un polígono concreto no hay año que atribuir. Antes se caía al año de
  // la procedencia, que describe la descarga y no el instrumento: bajo un punto
  // de Angol —que no tiene ni un polígono en el vectorial del MINVU— salía
  // «Año: 2010», que es el del plan de Temuco.
  const anio = primerFeature ? (p.anio || proc.fecha_dato || 'año no declarado') : null;
  const bajado = (proc.generado || '').slice(0, 10);
  return `<p class="fuente"><strong>Fuente:</strong> ${esc(fuente)}` +
         (anio ? ` · <strong>Año:</strong> ${esc(anio)}` : '') +
         (bajado ? ` · <span class="incert">datos obtenidos ${esc(bajado)}</span>` : '') +
         `</p>`;
}

function render(res, etiqueta, lon, lat) {
  // La evidencia completa vive en la pestaña de detalle. Acá no se recorta
  // nada: lo que cambió es dónde se muestra, no cuánto se cuenta.
  const cont = $('#detalle-ficha');
  resumen(res, etiqueta);
  const cercanos = res.cerca.slice(0, 5);
  const cronicos = res.cerca.filter((c) => c.f.properties.cronico);
  const responsables = [...new Set(
    res.cerca.filter((c) => c.d <= RADIOS.medio).map((c) => c.f.properties.responsable)
  )].filter(Boolean);

  let html = `
    <div class="veredicto v-${res.nivel}">
      <span class="icono" aria-hidden="true">${ICONO[res.nivel]}</span>
      <span>${esc(res.titulo)}</span>
    </div>
    <p class="direccion">📍 ${esc(etiqueta)}</p>`;

  /* --- Capa A: plan regulador. Va primera porque es la única con efecto legal --- */
  html += `<div class="evidencia">
    <h3>Plan Regulador Comunal <span class="etiqueta">A · NORMATIVO</span></h3>`;
  if (res.areas.length) {
    html += `<p>Este punto cae dentro de <strong>${res.areas.length}</strong>
             ${res.areas.length === 1 ? 'área de riesgo declarada' : 'áreas de riesgo declaradas'}
             por el plan regulador:</p><ul>`;
    for (const a of res.areas) {
      const p = a.properties;
      html += `<li><strong>${esc(p.clasificacion || 'Área de riesgo')}</strong>`;
      // El fenómeno, dicho aparte del código de la zona. No es lo mismo que el
      // río se salga a que el colector no dé abasto: otra física, otra
      // mitigación y otro servicio a quién reclamarle. El sitio argumenta esa
      // distinción en todas partes y aun así los mostraba a todos juntos.
      if (p.tipo_hidrico && p.tipo_hidrico !== 'fluvial') {
        html += ` <span class="sello sello-anteproyecto">${esc(
          FENOMENO[p.tipo_hidrico] || p.tipo_hidrico)}</span>`;
      }
      if (p.zona) html += ` <span class="incert">(zona ${esc(p.zona)})</span>`;
      if (p.usos_prohibidos) {
        html += `<br><span class="incert">Usos prohibidos: ${esc(p.usos_prohibidos)}</span>`;
      }
      // Sólo se ofrece el enlace si el dato dice que sigue vigente: 9 de los 63
      // polígonos traen URL y varias llevaban a un 404. Un enlace roto en la
      // única capa con efecto legal es peor que no ofrecer ninguno.
      if (p.ordenanza_url && p.ordenanza_url_vigente) {
        html += `<br><a href="${esc(p.ordenanza_url)}" rel="noopener">Ver ordenanza</a>`;
      } else {
        html += `<br><span class="incert">La ordenanza de este plan no está
                 publicada en un enlace estable: pídela en la Dirección de Obras
                 de tu municipalidad.</span>`;
      }
      html += `</li>`;
    }
    html += `</ul><p>Esto <strong>sí tiene efecto legal</strong>: condiciona permisos
             de edificación y usos de suelo en ese terreno.</p>
             <p class="incert">Ojo con lo que esto significa: un área de riesgo
             <strong>no prohíbe construir, condiciona</strong>. La Ordenanza General
             (art. 2.1.17) permite autorizar proyectos si se acompaña un
             <strong>estudio fundado de un profesional especialista</strong>, aprobado
             por el organismo competente, que defina las obras de mitigación, y esas
             obras se ejecutan. Distinto es una <em>zona no edificable</em>, que sí
             prohíbe.</p>`;
  } else if (estado.areasRiesgo) {
    // Con cuidado: este bloque habla del VECTORIAL que publica el MINVU, no de
    // «el plan regulador» a secas. Decir «no cae dentro de un área declarada en
    // el plan regulador» era falso en Angol y Curarrehue, donde el plan sí la
    // declara —en un plano de papel que nosotros vectorizamos— y el titular de
    // esta misma ficha lo dice cuatro centímetros más arriba. Una ficha que se
    // contradice consigo misma no se puede usar para decidir nada.
    html += res.laminas.length
      ? `<p>Este punto no está en el vectorial que publica el MINVU. Sí está
         dentro de la cartografía del propio documento comunal, que aparece más
         abajo: el organismo todavía no la publica en formato consultable.</p>`
      : `<p>Este punto no cae dentro de un área de riesgo por inundación
         declarada en el plan regulador.</p>`;
    html += `<p class="incert">Que no aparezca no significa que no exista: esta capa
             sólo trae instrumentos ya vigentes y publicados, y va por detrás de las
             aprobaciones. Además, la mayoría de las comunas de la región no ha
             declarado ningún área de riesgo. Consulta en la Dirección de Obras de tu
             municipalidad.</p>`;
  }
  // Sin polígono en el punto no hay año que atribuir: pasarle el primero de la
  // capa mostraba el año del instrumento de OTRA comuna —«Año: 2010», que es el
  // de Temuco— bajo un punto de Angol que no tiene ni un polígono del MINVU.
  html += atribucion(estado.areasRiesgo, res.areas[0] || null);
  if (res.areas.length) {
    const conEae = res.areas.filter((a) => a.properties.eae_fecha_ingreso);
    if (conEae.length) {
      const a = conEae[0].properties;
      html += `<p class="incert">El año del plan regulador no está declarado en la
               capa publicada por MINVU. Lo que sí consta: el procedimiento
               «${esc(a.eae_procedimiento)}» ingresó a Evaluación Ambiental
               Estratégica el ${esc(a.eae_fecha_ingreso)} y su estado es
               «${esc(a.eae_estado)}». Eso indica actividad de actualización, no la
               vigencia del polígono que estás viendo.</p>`;
    }
  }
  html += `<p class="incert">Sólo existen dentro del límite urbano de comunas cuyo
           plan regulador las haya zonificado: que no haya polígono no significa
           que no se inunde, significa que el plan no lo declaró.</p></div>`;

  /* --- Capa A DERIVADA: cartografía que existía sólo en papel y que
     convertimos en geometría. Va inmediatamente después del bloque normativo
     porque en Angol y Curarrehue es la ÚNICA evidencia normativa que hay —esas
     comunas no tienen ni un polígono en el vectorial del MINVU—, y hasta el
     7-sep-2026 no aparecía en ninguna parte de esta ficha: se dibujaba en el
     mapa y nada más. El sello dice «derivado» con TEXTO, no sólo con el
     achurado del borde, porque REGLAS §1.5 lo exige y porque el color no se
     lee en blanco y negro ni se escucha en un lector de pantalla. --- */
  if (res.laminas.length) {
    const p = res.laminas[0].properties;
    const norma = res.laminas.some((f) => f.properties.efecto_legal);
    html += `<div class="evidencia">
      <h3>Cartografía del documento comunal
          <span class="etiqueta">A · DERIVADO</span></h3>
      <p>Este punto cae dentro de <strong>${res.laminas.length}</strong>
         ${res.laminas.length === 1 ? 'zona marcada' : 'zonas marcadas'} como
         inundable en la cartografía de tu comuna:</p><ul>`;
    for (const f of res.laminas) {
      const q = f.properties;
      html += `<li><strong>${esc(q.clase)}</strong>`;
      if (q.descripcion) html += ` <span class="incert">(${esc(q.descripcion)})</span>`;
      html += ` <span class="sello sello-anteproyecto">trazado derivado</span>`;
      html += `<br><span class="incert">${esc(q.fuente)}</span>`;
      if (q.efecto_legal) {
        html += `<br><span class="incert"><strong>Efecto legal:</strong>
                 ${esc(q.efecto_legal)}</span>`;
      }
      if (q.metodo_original) {
        html += `<br><span class="incert">Método del estudio original:
                 ${esc(q.metodo_original)}</span>`;
      }
      html += `</li>`;
    }
    html += `</ul>
      <p class="incert"><strong>Qué es nuestro y qué no.</strong> El contenido es
      del documento de tu comuna, con su año y su método${norma
        ? `, y su efecto legal rige: es el plano de un plan regulador aprobado`
        : `; es un levantamiento de riesgo, no una norma`}. Lo que construimos
      nosotros es el <strong>trazado</strong>: esa cartografía existe sólo como
      figura impresa, así que la georreferenciamos y la convertimos en geometría.
      El borde tiene ±${esc(num(incertidumbreBorde(res.laminas[0])))} m de
      incertidumbre, y no es el borde del vectorial oficial del MINVU.</p>`;
    html += atribucion(estado.laminas, res.laminas[0]);
    html += `</div>`;
  }

  /* --- Capa B: huella observada por radar. Va pegada al bloque normativo
     porque es la evidencia más fuerte que tiene el visor: no es lo que la
     norma declara ni lo que un modelo estima, es agua medida en una fecha.
     Los cuatro casos —vio agua, miró y no vio, no miró, y no tenemos la
     capa— están escritos: el que más importa es el tercero. --- */
  html += `<div class="evidencia">
    <h3>Huella de inundación observada por satélite
        <span class="etiqueta">B · OBSERVADO</span></h3>`;
  if (res.sar.length) {
    const p = res.sar[0].properties;
    const f = fechaLarga(p.fecha_observacion);
    html += `<p>El radar del satélite <strong>detectó agua justo en este
             punto</strong>${f ? ` el <strong>${esc(f)}</strong>` : ''}.</p>`;
    if (p.evento) {
      html += `<p>Corresponde al evento <strong>${esc(p.evento)}</strong>. Esto no
               es una zonificación ni un modelo: es agua medida desde el espacio
               ese día.</p>`;
    }
    html += `<ul>`;
    if (p.hectareas != null) {
      html += `<li>La mancha de agua que contiene este punto mide
               <strong>${esc(Number(p.hectareas).toLocaleString('es-CL',
                 { maximumFractionDigits: 1 }))} hectáreas</strong>.</li>`;
    }
    if (p.track) {
      // La dirección de la órbita se traduce, pero sólo si se reconoce: si la
      // fuente trae otra cosa se muestra tal cual, sin inventarle significado.
      const dir = { descending: 'descendente', ascending: 'ascendente' }[p.direccion]
                  || p.direccion;
      const detalle = [
        p.orbita_relativa != null ? `órbita relativa ${p.orbita_relativa}` : null,
        dir || null,
      ].filter(Boolean).join(', ');
      html += `<li>Pasada <strong>${esc(p.track)}</strong>` +
              (detalle ? ` (${esc(detalle)})` : '') +
              (p.plataforma ? ` del satélite ${esc(p.plataforma.toUpperCase())}` : '') +
              `.</li>`;
    }
    const refs = (p.fechas_referencia || []).map((d) => fechaLarga(d) || d);
    if (refs.length && p.caida_db != null && p.umbral_agua_db != null) {
      html += `<li>Se comparó con ${refs.length}
               ${refs.length === 1 ? 'pasada previa' : 'pasadas previas'} de la misma
               órbita (${esc(listaEnEspanol(refs))}): para contar como agua, el
               eco del radar tenía que caer al menos
               ${esc(String(Math.abs(p.caida_db)).replace('.', ','))} dB y quedar bajo
               ${esc(String(p.umbral_agua_db).replace('.', ','))} dB, que es la firma
               del agua abierta —lisa, devuelve la señal lejos de la antena y por eso
               se ve negra.</li>`;
    }
    html += `</ul>`;
    html += atribucion(estado.sar, res.sar[0]);
    html += `<p class="incert">Es la foto del instante en que pasó el satélite, no
             el máximo del evento: donde el agua subió y bajó entre dos pasadas,
             la huella queda corta. Lo que sí está: acá hubo agua.</p>`;
  } else if (res.enCoberturaSar) {
    const fechas = fechasDePasada(res.coberturaSar);
    const cuando = fechas.length === 1
      ? ` el <strong>${esc(fechas[0])}</strong>`
      : fechas.length ? ` los días <strong>${esc(listaEnEspanol(fechas))}</strong>` : '';
    html += `<p>El satélite <strong>sí miró este punto</strong>${cuando}
             y <strong>no detectó agua</strong>
             ${fechas.length > 1 ? 'en esas pasadas' : 'en esa pasada'}.</p>
             <p><strong>Eso no quiere decir que no se haya inundado.</strong> El radar
             tiene cuatro límites conocidos, y los cuatro empujan en la misma
             dirección: hacia quedarse corto.</p>
             <ul class="limitaciones">
               <li><strong>No ve el agua bajo bosque cerrado.</strong> El dosel
                   devuelve la señal antes de que llegue al suelo.</li>
               <li><strong>Subestima en zona urbana densa</strong> —justo donde vive
                   más gente—: el rebote entre la pared y el suelo inundado mantiene
                   la señal alta, así que el agua se lee como ciudad seca.</li>
               <li><strong>No ve el agua con viento.</strong> El oleaje rompe el
                   espejo que hace que el agua se vea negra en el radar.</li>
               <li><strong>Es la foto de un instante</strong>, no el máximo del
                   evento. El agua que subió y bajó entre dos pasadas no aparece en
                   ninguna de las dos.</li>
             </ul>
             <p class="incert">Un caso real de este mismo evento, para que se
             entienda cuánto pesa el último límite: en <strong>Angol</strong> el
             estero Rehue se desbordó la madrugada del <strong>2 de agosto</strong>
             y el agua superó 1,5 m dentro de las casas. Las dos pasadas satelitales
             sobre Angol fueron el <strong>3</strong>, y no vieron nada: el agua ya
             había bajado. Esta capa registra 7,7 ha en esa comuna, y la inundación
             fue de las peores de la región.</p>`;
    html += atribucion(estado.sarCobertura, res.coberturaSar[0]);
  } else if (estado.sarCobertura) {
    const ev = estado.sarIndice?.evento || {};
    const desde = fechaLarga(ev.fecha_inicio);
    const hasta = fechaLarga(ev.fecha_fin);
    html += `<p><strong>El satélite no pasó por acá</strong>` +
            (desde && hasta
              ? ` entre el ${esc(desde)} y el ${esc(hasta)}, que es la ventana del evento`
              : ' en la ventana del evento') +
            `, o pasó con una geometría que no alcanza a cubrir este punto.</p>
             <p><strong>No observado no es lo mismo que no inundado.</strong> Este
             visor puede decir dónde vio agua; donde el radar no miró no tiene nada
             que declarar, y ese vacío no es evidencia de que acá estuviste a
             salvo.</p>`;
    html += atribucion(estado.sarCobertura, estado.sarCobertura.features[0]);
  } else {
    html += `<p>La huella de inundación observada por satélite <strong>todavía no
             está publicada</strong> en esta instalación del visor.</p>
             <p><strong>Que no esté observada no significa que no se inunde:</strong>
             es un dato que falta, no un riesgo descartado.</p>`;
  }
  html += `</div>`;

  /* --- El plano original, si lo tenemos georreferenciado --- */
  if (res.planos.length) {
    const p = res.planos[0];
    // El estado de tramitación va en el ENCABEZADO, no en la letra chica: es la
    // diferencia entre «esto rige tu terreno» y «esto es una propuesta», y quien
    // sólo lee el título tiene que enterarse igual.
    const anteproyecto = (p.estado_tramite || '').toLowerCase() === 'anteproyecto';
    html += `<div class="evidencia">
      <h3>El plano de tu comuna
        <span class="sello ${anteproyecto ? 'sello-anteproyecto' : 'sello-vigente'}"
              >${esc(p.estado_tramite || 'estado no declarado')}</span></h3>
      <p>Tenemos el plano del plan regulador que cubre este punto, ubicado sobre el
         mapa a partir de su propia grilla de coordenadas impresa.</p>
      <ul><li><strong>${esc(p.titulo)}</strong><br>
        <span class="incert">${p.puntos_control} puntos de control ·
        ajuste con ${p.rmse_loo_m} m de residuo · ${p.resolucion_m_px} m por píxel</span>
      </li></ul>
      <p class="${anteproyecto ? 'aviso-fuerte' : 'incert'}">
        ${esc(p.estado_tramite_nota || '')}</p>
      <button type="button" class="secundario" id="btn-plano">Ver el plano sobre el mapa</button>
      <p class="incert">Es el documento tal cual, sin retocar. Lo único que hicimos
         fue darle coordenadas.</p></div>`;
  }

  /* --- Capa D: registro municipal --- */
  html += `<div class="evidencia">
    <h3>Registro oficial de puntos críticos <span class="etiqueta">D · OPERACIONAL</span></h3>`;
  if (cercanos.length) {
    html += `<p>Hay <strong>${res.cerca.length}</strong> ${res.cerca.length === 1 ? 'punto crítico registrado' : 'puntos críticos registrados'}
             a menos de ${RADIOS.contexto} m. Los más cercanos:</p><ul>`;
    for (const { f, d } of cercanos) {
      const p = f.properties;
      html += `<li><strong>${Math.round(d)} m</strong> — ${esc(p.causa || 'sin causa declarada')}
        <span class="pill ${CLASE_NIVEL[p.nivel] || ''}">${esc(p.nivel || '?')}</span>
        ${p.sector ? `<br><span class="incert">${esc(p.sector)}</span>` : ''}
        ${p.cronico ? `<br><span class="incert">Registrado en ${p.temporadas_registrado} temporadas — problema crónico</span>` : ''}
        </li>`;
    }
    html += `</ul>`;
    if (cronicos.length) {
      html += `<p><strong>${cronicos.length}</strong> de estos puntos aparece en 3 o más
               temporadas del Programa Invierno: no es un evento aislado.</p>`;
    }
    if (responsables.length) {
      html += `<p>Responsable declarado de la solución:
               <strong>${esc(responsables.join(', '))}</strong>.</p>`;
    }
  } else {
    html += `<p>No hay puntos críticos registrados a menos de ${RADIOS.contexto} m.</p>`;
  }
  html += atribucion(estado.puntos, cercanos[0]?.f || estado.puntos.features[0]);
  html += `<p class="incert">Son puntos, no polígonos, y reflejan lo que el
           municipio reportó. La ausencia de registro no equivale a ausencia de
           riesgo.</p></div>`;

  /* --- Capa C: modelo global --- */
  html += `<div class="evidencia">
    <h3>Modelo global de inundación <span class="etiqueta">C · MODELADO</span></h3>`;
  if (estado.jrc) {
    html += res.enMancha
      ? `<p>Este punto cae <strong>dentro</strong> de la mancha modelada para una
         crecida de 100 años de período de retorno.</p>`
      : `<p>Este punto queda fuera de la mancha modelada de 100 años.</p>`;
    html += atribucion(estado.jrc, estado.jrc.features[0]);
    html += `<p class="incert">Resolución ~1 km: un píxel cubre varias manzanas y el
             modelo no representa el drenaje urbano. Además es un modelo de 2016,
             así que no incorpora obras fluviales ni cambios de uso de suelo
             posteriores. Sirve como contexto regional, <strong>no</strong> para
             decidir sobre una propiedad concreta.</p>`;
  }
  // Segundo modelo, treinta veces más fino y de la propia región. Va en el mismo
  // bloque C porque es la misma clase de evidencia, y se muestra aparte porque
  // dice algo distinto: el global habla en períodos de retorno y éste en clases
  // ordinales sin significado físico. Mezclarlos sería inventar una equivalencia.
  if (estado.gore) {
    const clase = res.gore.length ? res.gore[0].properties.clase : null;
    html += clase
      ? `<p>El modelo regional del Gobierno Regional clasifica este punto como
         amenaza de inundación <strong>${clase === 'MAXIMA' ? 'máxima' : 'media'}</strong>.</p>`
      : `<p>El modelo regional del Gobierno Regional <strong>no</strong> clasifica
         este punto en sus dos categorías más altas.</p>`;
    html += atribucion(estado.gore, res.gore[0] || estado.gore.features[0]);
    html += `<p class="incert">Resolución ~35 m, mucho más fina que el modelo
             global, pero sus clases <strong>no significan un período de retorno</strong>:
             «máxima» no equivale a ningún «cada tantos años». Más detalle espacial,
             menos interpretable. Se contrastó contra los puntos críticos de
             SENAPRED, que no participaron en su elaboración: el 39,5 % de los
             desbordes reales cae en la clase máxima, que ocupa el 8,2 % del
             territorio. El estudio que lo encargó nunca llegó a aprobarse.</p>`;
  } else {
    html += `<p class="incert">Capa no disponible en esta instalación.</p>`;
  }
  html += `</div>`;

  /* --- Campamentos: quiénes viven en el área de riesgo --- */
  if (res.campamentos.length) {
    const p = res.campamentos[0].properties;
    html += `<div class="evidencia">
      <h3>Viviendas en el área de riesgo <span class="etiqueta">D · OPERACIONAL</span></h3>
      <p>Este punto está dentro del campamento <strong>${esc(p.nombre)}</strong>,
         que el catastro nacional registra con <strong>${p.hogares}</strong>
         ${p.hogares === 1 ? 'hogar' : 'hogares'} en área de riesgo por
         ${esc((p.tipo_riesgo || 'inundación').toLowerCase())}.</p>`;
    html += atribucion(estado.campamentos, res.campamentos[0]);
    html += `<p class="incert">El catastro es de ${esc(p.anio)}: el campamento
             puede haber crecido, cambiado o haber sido erradicado desde
             entonces. El número de hogares es el del levantamiento, no un dato
             de hoy.</p></div>`;
  }

  /* Cierre de la ficha. Cada capa ya declaró arriba su fuente y su error; lo que
     falta decir es lo que ninguna dice por separado y la gente necesita oír: que
     ninguna de ellas es un pronóstico, y que el borde de la mancha es justo
     donde el mapa se equivoca más. Va acá y no en el encabezado a propósito —
     antes de leer la evidencia suena a excusa, después suena a instrucción. */
  html += bloqueComuna(comunaDe(res, lon, lat));

  html += `<p class="incert cierre-ficha">Ninguno de estos mapas predice la
           próxima inundación: cada uno es la conclusión de un estudio, con su
           fecha y su método, y están hechos con métodos distintos. <strong>Mira
           la mancha, no su borde</strong> — quedar justo afuera no es una buena
           noticia. <a href="#como-leer">Cómo leer un mapa de inundación</a>.</p>`;

  html += `<div class="acciones">
    <button type="button" id="btn-compartir">Compartir esta ficha</button>
    <button type="button" class="secundario" id="btn-centrar">Ver en el mapa</button>
  </div>`;

  cont.innerHTML = html;
  cont.classList.remove('oculto');
  cont.focus();

  estado.ultimo = { res, etiqueta, lon, lat };
  $('#btn-compartir').addEventListener('click', compartir);
  $('#btn-centrar').addEventListener('click', () =>
    estado.mapa && estado.mapa.flyTo({ center: [lon, lat], zoom: 14 }));

  const btnComuna = $('#btn-compartir-comuna');
  if (btnComuna) {
    btnComuna.addEventListener('click', async () => {
      const c = comunaDe(res, lon, lat);
      if (!c) return;
      const texto = textoComuna(c);
      if (navigator.share) {
        try { await navigator.share({ title: `Inundaciones en ${c.comuna}`, text: texto }); return; }
        catch { /* el usuario canceló */ }
      }
      try {
        await navigator.clipboard.writeText(texto);
        elEstado().textContent = `Estado de ${c.comuna} copiado. Ya lo puedes pegar.`;
      } catch { elEstado().textContent = 'No se pudo copiar automáticamente.'; }
    });
  }

  const btnSol = $('#btn-solicitud');
  if (btnSol) {
    btnSol.addEventListener('click', async () => {
      const c = comunaDe(res, lon, lat);
      if (!c) return;
      const texto = textoSolicitud(c);
      try {
        await navigator.clipboard.writeText(texto);
        elEstado().textContent =
          'Solicitud copiada. Pégala en portaltransparencia.cl, dirigida al '
          + 'MINVU (SEREMI de La Araucanía), a la DGA o a tu municipalidad.';
      } catch {
        elEstado().textContent = 'No se pudo copiar automáticamente.';
      }
    });
  }

  const btnPlano = $('#btn-plano');
  if (btnPlano) {
    btnPlano.addEventListener('click', () => {
      const p = res.planos[0];
      btnPlano.disabled = true;
      btnPlano.textContent = 'Cargando el plano…';
      const casilla = $('#cap-planos');
      if (casilla && !casilla.checked) {
        // Se dispara el evento, no sólo se marca la casilla: si no, las huellas
        // no se encienden y el estado del control queda mintiendo.
        casilla.checked = true;
        casilla.dispatchEvent(new Event('change'));
      }
      if (estado.mapa) {
        const [w, s, e, n] = p.bounds_wgs84;
        estado.mapa.fitBounds([[w, s], [e, n]], { padding: 30 });
        estado.mapa.once('moveend', () => mostrarPlano(p));
        document.querySelector('.mapa-envoltorio')
          .scrollIntoView({ behavior: 'smooth' });
      }
      const ok = mostrarPlano(p);
      // «Cargado» sería una promesa sobre algo que todavía no ocurre:
      // mostrarPlano agrega la capa, la imagen se baja después. Si esa descarga
      // falla —sin señal, por ejemplo— el mapa avisa por su evento de error y
      // el texto se corrige solo (ver el manejador en crearMapa).
      btnPlano.textContent = ok ? 'Plano agregado al mapa'
                                : 'El mapa no está disponible en este dispositivo';
    });
  }
}

/* --------------------------------------------------------------- acciones */

function textoFicha() {
  const { res, etiqueta } = estado.ultimo;
  const l = [`${res.titulo.toUpperCase()}`, `Ubicación: ${etiqueta}`, ''];
  // La huella observada va arriba: es el dato más concreto de la ficha —una
  // fecha en que hubo agua acá— y es el que la gente reenvía.
  if (res.sar.length) {
    const p = res.sar[0].properties;
    const f = fechaLarga(p.fecha_observacion) || p.fecha_observacion || 'fecha no declarada';
    l.push(`Huella de inundación OBSERVADA por satélite: el agua llegó hasta acá el ${f}.`);
    if (p.evento) l.push(`• Evento: ${p.evento}`);
    l.push(`  Fuente: ${p.fuente || estado.sar?.procedencia?.fuente || 'fuente no declarada'}` +
           ` (año: ${p.anio || 'no declarado'})`);
    l.push('');
  } else if (res.enCoberturaSar) {
    const fechas = fechasDePasada(res.coberturaSar);
    const cuando = fechas.length === 1 ? ` el ${fechas[0]}`
                 : fechas.length ? ` los días ${listaEnEspanol(fechas)}` : '';
    l.push(`El satélite miró este punto${cuando} y no detectó agua.`);
    l.push('  Ojo: el radar no ve agua bajo bosque cerrado ni en zona urbana densa,');
    l.push('  y es la foto del instante de la pasada, no el máximo del evento.');
    l.push('');
  } else if (estado.sarCobertura) {
    l.push('El satélite no pasó por acá en la ventana del evento.');
    l.push('  No observado NO es lo mismo que no inundado.');
    l.push('');
  }
  if (res.areas.length) {
    const p0 = res.areas[0].properties;
    l.push('Plan Regulador — área de riesgo declarada:');
    for (const a of res.areas) l.push(`• ${a.properties.clasificacion || 'Área de riesgo'}`);
    l.push(`  Fuente: ${p0.fuente} (año: ${p0.anio})`);
    l.push('');
  }
  const cerca = res.cerca.slice(0, 3);
  if (cerca.length) {
    l.push('Puntos críticos registrados cerca:');
    for (const { f, d } of cerca) {
      l.push(`• ${Math.round(d)} m — ${f.properties.causa} (riesgo ${f.properties.nivel})`);
    }
    l.push(`  Fuente: ${cerca[0].f.properties.fuente} (temporada ${cerca[0].f.properties.anio})`);
  } else {
    l.push('Sin puntos críticos registrados en 1,5 km.');
  }
  // La aclaración viaja en el texto compartido, no sólo en la pantalla: la
  // ficha se reenvía por WhatsApp y ahí «sin registros» queda solo, sin el
  // contexto que lo matiza.
  // El nivel vive en `estado.ultimo.res.nivel`, no en `estado.ultimo.nivel`:
  // leerlo mal hacía que esta advertencia —la más importante que tiene el
  // sitio— no viajara NUNCA en el texto que se reenvía, justo en el veredicto
  // donde más falta hace. En pantalla sí estaba, así que no se notaba.
  if (estado.ultimo && estado.ultimo.res && estado.ultimo.res.nivel === 'sindato') {
    l.push('', 'OJO: que no haya registro NO significa que acá no se inunde.',
           'Significa que nadie lo ha levantado.');
  }
  l.push('', 'Esto NO es información oficial ni un pronóstico.',
         'En emergencia: SENAPRED y tu municipio.');
  return l.join('\n');
}

async function compartir() {
  const texto = textoFicha();
  if (navigator.share) {
    try { await navigator.share({ title: '¿Se inunda donde vivo?', text: texto }); return; }
    catch { /* el usuario canceló */ }
  }
  try {
    await navigator.clipboard.writeText(texto);
    elEstado().textContent = 'Ficha copiada. Ya puedes pegarla en WhatsApp.';
  } catch {
    elEstado().textContent = 'No se pudo copiar automáticamente.';
  }
}

/* ------------------------------------------------------------ geocodifica */

async function geocodificar(texto) {
  // Nominatim: gratuito y sin clave, pero con política de uso estricta.
  // Para producción hay que montar geocodificador propio o usar el de IDE Chile.
  const url = 'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1'
            + '&countrycodes=cl&accept-language=es'
            + `&viewbox=${REGION.bbox[0]},${REGION.bbox[3]},${REGION.bbox[2]},${REGION.bbox[1]}`
            + `&bounded=1&q=${encodeURIComponent(texto)}`;
  const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
  if (!r.ok) throw new Error(`geocodificador HTTP ${r.status}`);
  const j = await r.json();
  if (!j.length) return null;
  // Nominatim responde lo más parecido que encuentra: si el número no existe,
  // devuelve la CALLE entera y su punto medio, que puede quedar a cientos de
  // metros. Sin decirlo, el visor respondía sobre un punto que la persona no
  // eligió. Se compara lo pedido con lo devuelto y se avisa.
  const pidioNumero = /\d/.test(texto);
  const tipo = j[0].addresstype || j[0].category || '';
  const aproximado = pidioNumero && !/house|building|address/.test(tipo);
  return { lon: +j[0].lon, lat: +j[0].lat, etiqueta: j[0].display_name, aproximado };
}

/* ------------------------------------------------------------ sugerencias */

const SUG = { items: [], activo: -1, timer: null, aborto: null };

/** Comunas que coinciden con lo escrito. Salen del índice ya cargado, así que
 *  aparecen al instante y —a diferencia de las direcciones— siguen funcionando
 *  sin señal, que es cuando este visor más se necesita. */
function sugerenciasLocales(texto) {
  const t = normalizaTexto(texto);
  if (t.length < 2) return [];
  return (estado.comunas?.comunas || [])
    .filter((c) => normalizaTexto(c.comuna).includes(t))
    .slice(0, 4)
    .map((c) => ({
      tipo: 'comuna',
      titulo: c.comuna,
      detalle: `${c.puntos_inundacion} puntos críticos de inundación`,
      accion: () => { cerrarSugerencias(); zoomComuna(c); },
    }));
}

function normalizaTexto(t) {
  return (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

async function sugerenciasDirecciones(texto) {
  if (texto.trim().length < 4) return [];
  // Se cancela la petición anterior: sin esto, escribir rápido deja varias
  // respuestas compitiendo y gana la que llegue última, que puede ser de un
  // texto ya borrado.
  if (SUG.aborto) SUG.aborto.abort();
  SUG.aborto = new AbortController();
  const url = 'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5'
            + '&countrycodes=cl&accept-language=es'
            + `&viewbox=${REGION.bbox[0]},${REGION.bbox[3]},${REGION.bbox[2]},${REGION.bbox[1]}`
            + `&bounded=1&q=${encodeURIComponent(texto)}`;
  try {
    const r = await fetch(url, { signal: SUG.aborto.signal });
    if (!r.ok) return [];
    return (await r.json()).map((d) => ({
      tipo: 'direccion',
      titulo: d.display_name.split(',').slice(0, 2).join(',').trim(),
      detalle: d.display_name.split(',').slice(2, 5).join(',').trim(),
      accion: () => {
        cerrarSugerencias();
        $('#q').value = d.display_name.split(',').slice(0, 3).join(',').trim();
        consultar(+d.lon, +d.lat, d.display_name);
      },
    }));
  } catch { return []; }   // abortada o sin red: no es un error que mostrar
}

function pintarSugerencias(items) {
  const ul = $('#sugerencias');

  // Las comunas se pintan al instante y las direcciones llegan ~medio segundo
  // después, así que la lista se repinta. Si el repintado reseteara la
  // selección, alguien que baje con el teclado y espere perdería lo que tenía
  // marcado justo cuando llegan más resultados. Se conserva por título.
  const marcado = SUG.activo >= 0 ? SUG.items[SUG.activo]?.titulo : null;

  SUG.items = items;
  if (!items.length) { cerrarSugerencias(); return; }
  SUG.activo = marcado ? items.findIndex((s) => s.titulo === marcado) : -1;
  ul.innerHTML = items.map((s, i) => `
    <li role="option" id="sug-${i}" aria-selected="false" data-i="${i}">
      <span class="sug-icono" aria-hidden="true">${s.tipo === 'comuna' ? '◧' : '⌖'}</span>
      <span class="sug-txt"><strong>${esc(s.titulo)}</strong>
        ${s.detalle ? `<small>${esc(s.detalle)}</small>` : ''}</span>
    </li>`).join('');
  ul.classList.remove('oculto');
  $('#q').setAttribute('aria-expanded', 'true');
  ul.querySelectorAll('li').forEach((li) => {
    li.addEventListener('mousedown', (e) => {   // mousedown: antes del blur
      e.preventDefault();
      items[+li.dataset.i].accion();
    });
  });
  if (SUG.activo >= 0) marcarSugerencia(SUG.activo);
}

function marcarSugerencia(i) {
  SUG.activo = i;
  $('#sugerencias').querySelectorAll('li').forEach((li, k) => {
    const act = k === i;
    li.classList.toggle('activa', act);
    li.setAttribute('aria-selected', String(act));
  });
  $('#q').setAttribute('aria-activedescendant', `sug-${i}`);
}

function cerrarSugerencias() {
  const ul = $('#sugerencias');
  ul.classList.add('oculto');
  ul.innerHTML = '';
  SUG.items = [];
  SUG.activo = -1;
  $('#q').setAttribute('aria-expanded', 'false');
  $('#q').removeAttribute('aria-activedescendant');
}

function moverSugerencia(delta) {
  if (!SUG.items.length) return;
  marcarSugerencia((SUG.activo + delta + SUG.items.length) % SUG.items.length);
}

function pedirSugerencias() {
  const texto = $('#q').value;
  clearTimeout(SUG.timer);
  if (normalizaTexto(texto).length < 2) { cerrarSugerencias(); return; }

  // Las comunas se pintan de inmediato; las direcciones llegan después. La
  // política de uso de Nominatim pide no más de una consulta por segundo, así
  // que se espera a que la persona deje de escribir.
  pintarSugerencias(sugerenciasLocales(texto));
  SUG.timer = setTimeout(async () => {
    const dirs = await sugerenciasDirecciones(texto);
    if ($('#q').value !== texto) return;         // ya escribió otra cosa
    pintarSugerencias([...sugerenciasLocales(texto), ...dirs]);
  }, 450);
}

async function consultar(lon, lat, etiqueta) {
  // La interfaz se enlaza antes de que lleguen los datos, a propósito. Si
  // alguien alcanza a consultar en ese rato, se le dice — que es infinitamente
  // mejor que un error de JavaScript o una ficha en blanco.
  if (!estado.puntos) {
    elEstado().textContent = 'Todavía se están cargando los datos. Un momento…';
    return;
  }
  // Fuera del alcance no se evalúa. Si se dejara pasar, `evaluar` devolvería
  // «SIN DATO» —que es una afirmación sobre La Araucanía— para un punto de
  // Antofagasta, y la ficha se leería como que ahí no se inunda.
  if (!dentroDeRegion(lon, lat)) { renderFuera(etiqueta, lon, lat); return; }
  const res = evaluar(lon, lat);
  render(res, etiqueta, lon, lat);
  ponerMarcador(lon, lat);
  estado.mapa && estado.mapa.flyTo({ center: [lon, lat], zoom: 14 });
}

/** Respuesta para un punto fuera del prototipo. No dice «sin riesgo»: dice que
 *  este sitio no tiene nada que decir sobre ese lugar, que es distinto. */
function renderFuera(etiqueta, lon, lat) {
  const cont = $('#respuesta');
  $('#detalle-ficha').innerHTML =
    '<p class="nota">El punto que elegiste queda fuera de La Araucanía, '
    + 'así que no hay evidencia que mostrar.</p>';
  cont.innerHTML = `
    <div class="veredicto v-fuera">
      <span class="icono" aria-hidden="true">🧭</span>
      <span>Fuera del alcance de este prototipo</span>
    </div>
    <p class="direccion">📍 ${esc(etiqueta)}</p>
    <div class="evidencia">
      <p>Este visor cubre <strong>sólo la Región de ${esc(REGION.nombre)}</strong>,
         y el punto que elegiste queda afuera.</p>
      <p class="incert"><strong>Eso no dice nada sobre el riesgo de ese lugar.</strong>
         No es que no se inunde: es que acá no hay dato para responder. El resto
         de Chile tampoco tiene un mapa nacional de inundaciones — esa es
         justamente la razón de este proyecto.</p>
      <p class="incert">Para ese sector, consulta la Dirección de Obras de su
         municipalidad y el plan regulador de su comuna. En emergencia,
         <a href="https://senapred.cl" rel="noopener">SENAPRED</a>.</p>
    </div>`;
  cont.classList.remove('oculto');
  cont.focus();
  estado.ultimo = null;   // no hay ficha que compartir
}

async function buscar() {
  const q = $('#q').value.trim();
  if (!q) return;
  estado.precisionPos = null;   // esta posición no viene del GPS
  const btn = $('#btn-buscar');
  btn.disabled = true;
  elEstado().textContent = 'Buscando la dirección…';
  try {
    const hit = await geocodificar(q);
    if (!hit) { elEstado().textContent = 'No se encontró esa dirección en La Araucanía.'; return; }
    elEstado().textContent = hit.aproximado
      ? 'No se encontró ese número exacto: la respuesta es para un punto medio de '
        + 'esa calle. Si puedes, toca el mapa sobre el lugar preciso.'
      : '';
    await consultar(hit.lon, hit.lat, hit.etiqueta);
  } catch (e) {
    elEstado().textContent = `No se pudo buscar (${e.message}). Prueba tocando el mapa.`;
  } finally {
    btn.disabled = false;
  }
}

function ubicarme() {
  if (!navigator.geolocation) {
    elEstado().textContent = 'Tu navegador no permite compartir ubicación.';
    return;
  }
  elEstado().textContent = 'Obteniendo tu ubicación…';
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { longitude: lon, latitude: lat, accuracy } = pos.coords;
      // La precisión que informa el aparato se guarda y se usa: decide el ancho
      // de la franja donde el veredicto no puede distinguir adentro de afuera.
      // Se descartaba, y con ella la única medida de cuánto se puede confiar en
      // la posición desde la que se responde.
      estado.precisionPos = Number.isFinite(accuracy) ? accuracy : null;
      // Se avisa ANTES de consultar: quien abre esto desde otra región merece
      // saber por qué no obtiene respuesta, en vez de deducirlo de una ficha
      // vacía.
      elEstado().textContent = dentroDeRegion(lon, lat) ? ''
        : `Estás fuera de ${REGION.nombre}: este prototipo sólo cubre esa región.`;
      consultar(lon, lat, 'Tu ubicación actual');
    },
    (err) => {
      // err.message lo escribe el navegador y viene en su idioma, casi siempre
      // en inglés: «User denied Geolocation». Se traduce el caso que importa.
      const MOTIVO = {
        1: 'no diste permiso de ubicación a esta página',
        2: 'tu dispositivo no pudo determinar dónde está',
        3: 'la ubicación tardó demasiado',
      };
      elEstado().textContent =
        `No se pudo obtener tu ubicación: ${MOTIVO[err.code] || err.message}. `
        + 'Puedes tocar el mapa o escribir una dirección.';
    },
    { enableHighAccuracy: true, timeout: 12000 }
  );
}

/* -------------------------------------------------------------- pestañas */

const PESTANAS = ['respuesta', 'detalle'];

/** Cambia de pestaña. Mueve el foco al panel para que quien navega con teclado
 *  o lector de pantalla llegue al contenido, no se quede en el botón. */
function irAPestana(cual, moverFoco = true) {
  if (!PESTANAS.includes(cual)) cual = 'respuesta';
  for (const p of PESTANAS) {
    const tab = $(`#tab-${p}`);
    const panel = $(`#panel-${p}`);
    if (!tab || !panel) continue;
    const activa = p === cual;
    tab.setAttribute('aria-selected', activa ? 'true' : 'false');
    tab.tabIndex = activa ? 0 : -1;
    panel.hidden = !activa;
  }
  // El mapa vive en el primer panel: si estuvo oculto, MapLibre midió cero y
  // hay que decirle que vuelva a medirse o queda un lienzo en blanco.
  if (cual === 'respuesta' && estado.mapa) estado.mapa.resize();
  if (moverFoco) {
    const panel = $(`#panel-${cual}`);
    if (panel) panel.focus({ preventScroll: true });
  }
  if (location.hash.slice(1) !== cual) history.replaceState(null, '', `#${cual}`);
}

function enlazarPestanas() {
  PESTANAS.forEach((p, i) => {
    const tab = $(`#tab-${p}`);
    if (!tab) return;
    tab.addEventListener('click', () => irAPestana(p));
    tab.addEventListener('keydown', (e) => {
      const salto = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (!salto) return;
      e.preventDefault();
      const destino = PESTANAS[(i + salto + PESTANAS.length) % PESTANAS.length];
      irAPestana(destino);
      $(`#tab-${destino}`).focus();
    });
  });
  // Los enlaces internos del detalle («Cómo leer un mapa») apuntan a secciones
  // que ahora viven en la otra pestaña: sin esto no llevan a ninguna parte.
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;
    const destino = document.querySelector(a.getAttribute('href'));
    if (!destino) return;
    const panel = destino.closest('[role="tabpanel"]');
    if (panel && panel.hidden) {
      irAPestana(panel.id.replace('panel-', ''), false);
      requestAnimationFrame(() => destino.scrollIntoView({ block: 'start' }));
    }
  });
  irAPestana(location.hash.slice(1) || 'respuesta', false);
}

/* -------------------------------------------------------------------- mapa */

/* Dos mapas base, y no es un adorno.
 *
 * El de calles ubica: dice en qué esquina estás. El satelital muestra el
 * terreno — dónde está el cauce de verdad, qué es potrero y qué está
 * construido, si la mancha cae sobre casas o sobre un paño vacío. Para juzgar
 * un área de riesgo, ver el suelo real cambia la lectura más que cualquier
 * leyenda.
 *
 * ⚠️ Las dos fuentes son de terceros y ninguna admite tráfico de producción bajo
 * su política de uso: OSM lo dice explícitamente y Esri exige atribución y
 * limita el uso. Para publicar hay que montar teselas propias. Está anotado
 * también en docs/PROXIMA_SESION.md.
 */
const BASES = {
  calles: {
    id: 'osm',
    tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
    atribucion: '© OpenStreetMap',
    maxzoom: 19,
  },
  satelite: {
    id: 'sat',
    // El esquema de Esri invierte el orden {y}/{x} respecto del de OSM.
    tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/'
            + 'World_Imagery/MapServer/tile/{z}/{y}/{x}'],
    atribucion: 'Imágenes © Esri, Maxar, Earthstar Geographics',
    maxzoom: 19,
  },
};

const ESTILO = {
  version: 8,
  sources: Object.fromEntries(Object.values(BASES).map((b) => [b.id, {
    type: 'raster', tiles: b.tiles, tileSize: 256,
    attribution: b.atribucion, maxzoom: b.maxzoom,
  }])),
  // Los dos van en el estilo desde el principio y se alternan por visibilidad,
  // no agregando y quitando capas: así las capas de datos —que se agregan
  // después y por tanto quedan encima— no se pierden al cambiar de base.
  layers: Object.values(BASES).map((b) => ({
    id: b.id, type: 'raster', source: b.id,
    layout: { visibility: b.id === 'osm' ? 'visible' : 'none' },
  })),
};

/** Cuál de los dos mapas base está activo. Se recuerda entre visitas. */
function baseGuardada() {
  try {
    const v = localStorage.getItem('riesgomapas.base');
    return (v && BASES[v]) ? v : 'calles';
  } catch { return 'calles'; }
}

function aplicarBase(cual) {
  const m = estado.mapa;
  if (!m || !BASES[cual]) return;
  for (const [nombre, b] of Object.entries(BASES)) {
    if (!m.getLayer(b.id)) continue;
    m.setLayoutProperty(b.id, 'visibility', nombre === cual ? 'visible' : 'none');
  }
  estado.base = cual;
  try { localStorage.setItem('riesgomapas.base', cual); } catch { /* modo privado */ }
  // Sobre la imagen satelital el texto oscuro de las etiquetas se pierde; la
  // hoja de estilos usa esta marca para aclararlas.
  document.body.classList.toggle('base-satelite', cual === 'satelite');
  // El selector tiene que mostrar lo que de verdad está activo, incluida la
  // preferencia recordada de una visita anterior.
  const radio = $(`#base-${cual}`);
  if (radio && !radio.checked) radio.checked = true;
}

function ponerMarcador(lon, lat) {
  if (!estado.mapa) return;
  if (estado.marcador) estado.marcador.remove();
  estado.marcador = new maplibregl.Marker({ color: '#4cc2e0' })
    .setLngLat([lon, lat]).addTo(estado.mapa);
}

function iniciarMapa() {
  const m = new maplibregl.Map({
    container: 'mapa', style: ESTILO,
    center: [-72.6, -38.75], zoom: 7.2, attributionControl: true,
    // El prototipo es regional: no se deja salir del recuadro ni alejar hasta
    // ver el país entero. Además de acotar el alcance, evita que alguien
    // termine tocando Santiago y reciba una ficha vacía. Ver REGION.
    maxBounds: limitesMapa(), minZoom: 6.5,
  });
  estado.mapa = m;

  // Que una imagen de plano no llegue tiene que verse. Sin esto, sin señal el
  // botón decía «Plano cargado sobre el mapa» mientras el mapa seguía vacío:
  // el peor modo de falla del proyecto, un resultado plausible y equivocado.
  m.on('error', (ev) => {
    const id = ev && ev.sourceId;
    if (!id || !String(id).startsWith('plano-')) return;
    const btn = $('#btn-plano');
    if (btn) btn.textContent = 'No se pudo cargar la imagen del plano';
    elEstado().textContent =
      'La imagen del plano no se pudo cargar. Si estás sin señal, sólo están '
      + 'los planos que ya habías abierto antes.';
  });

  m.addControl(new maplibregl.NavigationControl(), 'top-right');
  m.addControl(new maplibregl.ScaleControl({ unit: 'metric' }));

  // Las capas se agregan cuando el ESTILO está listo, no en el evento 'load'.
  // 'load' espera además al primer cuadro renderizado, así que en una pestaña en
  // segundo plano, con la ventana minimizada o en un dispositivo que no compone
  // (gama baja, contexto WebGL perdido) no dispara nunca y el mapa queda vacío
  // sin ningún error visible.
  let capasPuestas = false;
  const agregarCapas = () => {
    // La condición es que el estilo ACEPTE capas, no que esté «cargado».
    // `isStyleLoaded()` sólo es cierto cuando además terminaron de bajar las
    // teselas del mapa base, así que sin señal —o con el servidor de teselas
    // caído, que es el escenario para el que existe este sitio— se quedaba
    // permanentemente en falso y el mapa nunca recibía NINGUNA capa de datos:
    // ni áreas de riesgo, ni puntos críticos, ni la huella del satélite. Sin
    // error y con las casillas ofreciendo encender lo que no existe. Que la
    // capa base ya esté en el estilo sí es una condición sobre contenido, y es
    // suficiente para agregar: el flag de más abajo evita repetirlo.
    if (capasPuestas || !(m.getLayer('osm') || m.isStyleLoaded())) return;
    capasPuestas = true;

    // En tema oscuro el mapa base de OSM queda como un rectángulo blanco dentro
    // de una interfaz oscura. Se atenúa la CAPA DE TESELAS, no el contenedor:
    // un filtro CSS sobre el canvas apagaría también los colores de amenaza, que
    // son justamente lo que tiene que resaltar.
    if (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches
        && m.getLayer('osm')) {
      m.setPaintProperty('osm', 'raster-brightness-max', 0.72);
      m.setPaintProperty('osm', 'raster-saturation', -0.35);
      m.setPaintProperty('osm', 'raster-contrast', -0.08);
    }
    if (estado.jrc) {
      m.addSource('jrc', { type: 'geojson', data: estado.jrc });
      m.addLayer({
        id: 'jrc-fill', type: 'fill', source: 'jrc',
        layout: { visibility: 'none' },
        paint: { 'fill-color': '#2f6fb0', 'fill-opacity': 0.35 },
      });
    }
    // Amenaza regional del GORE 2016: mismo tipo de evidencia que el JRC pero a
    // ~35 m en vez de ~1 km. Va justo encima porque es más fina, y en dos tonos
    // porque sus clases son ordinales — pintarlas de un solo color perdería lo
    // único que el modelo distingue.
    if (estado.gore) {
      m.addSource('gore', { type: 'geojson', data: estado.gore });
      m.addLayer({
        id: 'gore-fill', type: 'fill', source: 'gore',
        layout: { visibility: 'none' },
        paint: {
          'fill-color': ['match', ['get', 'clase'],
                         'MAXIMA', '#1d4f8c', 'MEDIA', '#5b93c9', '#5b93c9'],
          'fill-opacity': ['match', ['get', 'clase'], 'MAXIMA', 0.55, 0.32],
        },
      });
    }
    // Capa B, agregada justo después del JRC: queda SOBRE la mancha modelada y
    // BAJO las áreas normativas y los puntos críticos, que se añaden más abajo.
    // El orden de apilado es el orden de evidencia, y así se lee sin leyenda.
    if (estado.sar) {
      m.addSource('sar', { type: 'geojson', data: estado.sar });
      m.addLayer({
        id: 'sar-fill', type: 'fill', source: 'sar',
        layout: { visibility: 'none' },
        paint: { 'fill-color': '#c9268f', 'fill-opacity': 0.5 },
      });
      m.addLayer({
        id: 'sar-line', type: 'line', source: 'sar',
        layout: { visibility: 'none' },
        paint: { 'line-color': '#ff5fc0', 'line-width': 1.6 },
      });
      // Sin popup a propósito: tocar la huella tiene que consultar el punto, que
      // es lo que responde "el agua llegó hasta acá el tal día" con toda la ficha
      // detrás. Un globo con menos información sería un peor destino del clic.
    }
    if (estado.laminas) {
      m.addSource('lam', { type: 'geojson', data: estado.laminas });
      // ACHURADO, no relleno sólido: la simbología tiene que decir sola que
      // esto no es el vectorial oficial. Un relleno igual al de la capa
      // normativa haría pasar por instrumento legal algo que construimos
      // nosotros desde una figura impresa.
      m.addLayer({
        id: 'lam-fill', type: 'fill', source: 'lam',
        layout: { visibility: 'none' },
        paint: { 'fill-color': '#c98a1e', 'fill-opacity': 0.28 },
      });
      m.addLayer({
        id: 'lam-line', type: 'line', source: 'lam',
        layout: { visibility: 'none' },
        paint: { 'line-color': '#c98a1e', 'line-width': 1.4, 'line-dasharray': [3, 2] },
      });
    }
    if (estado.areasRiesgo) {
      m.addSource('ar', { type: 'geojson', data: estado.areasRiesgo });
      m.addLayer({
        id: 'ar-fill', type: 'fill', source: 'ar',
        paint: { 'fill-color': '#b4453f', 'fill-opacity': 0.32 },
      });
      m.addLayer({
        id: 'ar-line', type: 'line', source: 'ar',
        paint: { 'line-color': '#e5484d', 'line-width': 1.2 },
      });
      m.on('click', 'ar-fill', (e) => {
        const p = e.features[0].properties;
        new maplibregl.Popup({ maxWidth: '300px' }).setLngLat(e.lngLat).setHTML(
          `<strong>${esc(p.clasificacion || 'Área de riesgo')}</strong><br>` +
          `<span style="font-size:.85em">Plan Regulador de ${esc(p.comuna || '')}` +
          (p.zona ? ` · zona ${esc(p.zona)}` : '') + `</span>` +
          (p.usos_prohibidos
            ? `<br><span style="font-size:.8em">Prohibido: ${esc(p.usos_prohibidos)}</span>`
            : '') +
          `<hr style="margin:.4em 0"><span style="font-size:.75em">` +
          `${esc(p.fuente || 'fuente no declarada')}<br>Año: ${esc(p.anio || 'no declarado')}` +
          `</span>`).addTo(m);
      });
    }
    if (estado.campamentos) {
      m.addSource('camp', { type: 'geojson', data: estado.campamentos });
      m.addLayer({
        id: 'camp-fill', type: 'fill', source: 'camp',
        layout: { visibility: 'none' },
        paint: { 'fill-color': '#6a3fa0', 'fill-opacity': 0.45 },
      });
      m.addLayer({
        id: 'camp-line', type: 'line', source: 'camp',
        layout: { visibility: 'none' },
        paint: { 'line-color': '#6a3fa0', 'line-width': 1.5 },
      });
      m.on('click', 'camp-fill', (e) => {
        const p = e.features[0].properties;
        new maplibregl.Popup({ maxWidth: '290px' }).setLngLat(e.lngLat).setHTML(
          `<strong>${esc(p.nombre)}</strong><br>` +
          `<span style="font-size:.85em">${p.hogares} hogares · ${esc(p.comuna)}<br>` +
          `Área de riesgo: ${esc(p.tipo_riesgo || '')}</span>` +
          `<hr style="margin:.4em 0"><span style="font-size:.75em">` +
          `${esc(p.fuente)}<br>Catastro: ${esc(p.anio)}</span>`).addTo(m);
      });
      m.on('mouseenter', 'camp-fill', () => { m.getCanvas().style.cursor = 'pointer'; });
      m.on('mouseleave', 'camp-fill', () => { m.getCanvas().style.cursor = ''; });
    }
    m.addSource('pc', { type: 'geojson', data: estado.puntos });
    m.addLayer({
      id: 'pc-circ', type: 'circle', source: 'pc',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 2.5, 12, 6, 16, 10],
        'circle-color': [
          'match', ['get', 'nivel'],
          'Muy Alto', '#e5484d', 'Alto', '#f07f2b',
          'Medio', '#e8c33c', 'Bajo', '#6bbf59',
          '#8899a0',
        ],
        'circle-stroke-width': 1,
        'circle-stroke-color': 'rgba(0,0,0,.55)',
        'circle-opacity': 0.85,
      },
    });

    m.on('click', 'pc-circ', (e) => {
      const p = e.features[0].properties;
      new maplibregl.Popup({ maxWidth: '280px' })
        .setLngLat(e.lngLat)
        .setHTML(
          `<strong>${esc(p.sector || 'Punto crítico')}</strong><br>` +
          `${esc(p.causa || '')}<br>Riesgo: <strong>${esc(p.nivel || '?')}</strong><br>` +
          `<span style="font-size:.8em">${esc(p.comuna || '')} · ` +
          `responsable: ${esc(p.responsable || 'no declarado')}</span>` +
          `<hr style="margin:.4em 0"><span style="font-size:.75em">` +
          `${esc(p.fuente || 'fuente no declarada')}<br>` +
          `Temporada: ${esc(p.anio || 'no declarada')}</span>`)
        .addTo(m);
    });
    m.on('mouseenter', 'pc-circ', () => { m.getCanvas().style.cursor = 'pointer'; });
    m.on('mouseleave', 'pc-circ', () => { m.getCanvas().style.cursor = ''; });

    // Huellas de los planos: rectángulos con la extensión de cada hoja.
    if ((estado.planos || []).length) {
      m.addSource('huellas', { type: 'geojson', data: huellasGeoJSON() });
      m.addLayer({
        id: 'huellas-fill', type: 'fill', source: 'huellas',
        layout: { visibility: 'none' },
        paint: { 'fill-color': '#4cc2e0', 'fill-opacity': 0.12 },
      });
      m.addLayer({
        id: 'huellas-line', type: 'line', source: 'huellas',
        layout: { visibility: 'none' },
        paint: { 'line-color': '#4cc2e0', 'line-width': 2, 'line-dasharray': [2, 1] },
      });
      m.on('click', 'huellas-fill', (e) => {
        const i = e.features[0].properties.i;
        const p = estado.planos[i];
        if (!p) return;
        const [w, s, ee, n] = p.bounds_wgs84;
        m.fitBounds([[w, s], [ee, n]], { padding: 25 });
        m.once('moveend', () => { mostrarPlano(p); elEstado().textContent = ''; });
      });
      m.on('mouseenter', 'huellas-fill', () => { m.getCanvas().style.cursor = 'zoom-in'; });
      m.on('mouseleave', 'huellas-fill', () => { m.getCanvas().style.cursor = ''; });
    }

    // Al mover o hacer zoom se recalcula qué planos corresponde cargar.
    m.on('moveend', () => actualizarPlanos(false));

    // Tocar el mapa consulta ese punto: alternativa al buscador cuando la
    // dirección no existe en OSM, que en zonas rurales es lo habitual.
    m.on('click', (e) => {
      // Las capas que abren su propio popup no disparan además la consulta
      // completa: un toque daba dos respuestas a la vez, el popup y la ficha,
      // y la segunda tapaba a la primera. Faltaban las áreas de riesgo y los
      // campamentos, que sí tienen popup desde antes.
      const capas = ['pc-circ', 'huellas-fill', 'ar-fill', 'camp-fill']
        .filter((c) => m.getLayer(c));
      if (m.queryRenderedFeatures(e.point, { layers: capas }).length) return;
      estado.precisionPos = null;   // un toque en el mapa no tiene precisión de GPS
      consultar(e.lngLat.lng, e.lngLat.lat,
        `Punto seleccionado (${e.lngLat.lat.toFixed(4)}, ${e.lngLat.lng.toFixed(4)})`);
    });
  };

  // Cada vez que el estilo se recarga hay que volver a fijar cuál base se
  // muestra: MapLibre la deja en su valor por defecto.
  // Las capas se agregan apagadas y cada casilla las enciende. Si alguien marca
  // una casilla ANTES de que su capa exista —el mapa tarda, la pestaña está en
  // segundo plano, el dispositivo es lento— el manejador no encuentra la capa,
  // no hace nada y no avisa: la casilla queda marcada y la capa apagada. La
  // interfaz miente sobre lo que se está viendo, que es el mismo modo de falla
  // que este proyecto persigue en los datos. Después de agregar capas se
  // vuelven a aplicar las casillas ya marcadas, reusando la lógica de cada una.
  const sincronizarCasillas = () => {
    for (const id of CASILLAS_CAPAS) {
      const el = $(`#${id}`);
      if (el && el.checked) el.dispatchEvent(new Event('change'));
    }
  };
  const intentar = () => { agregarCapas(); aplicarBase(estado.base); sincronizarCasillas(); };
  m.on('styledata', intentar);
  m.on('style.load', intentar);
  m.on('load', intentar);
  intentar();

  // Y un reintento por RELOJ, que es la red de seguridad de todo lo anterior.
  //
  // `agregarCapas` no hace nada mientras `isStyleLoaded()` sea falso, y el
  // estilo puede pasar a listo SIN emitir ningún evento más: entonces la última
  // llamada llegó demasiado temprano, no hay una siguiente, y el mapa se queda
  // con la base y NINGUNA capa de datos. Sin error, sin aviso, con las casillas
  // ofreciendo encender capas que no existen. Visto el 7-sep-2026 en una
  // pestaña nueva: estilo cargado, los siete GeoJSON en memoria, cero capas.
  // Esperar por CONTENIDO y no por un evento es la misma regla que el proyecto
  // ya aplica en sus pruebas (REGLAS §4.4).
  let intentos = 0;
  const reloj = setInterval(() => {
    intentar();
    if (m.getLayer('pc-circ') || ++intentos > 80) {   // ~20 s
      clearInterval(reloj);
      if (!m.getLayer('pc-circ')) {
        elEstado().textContent = 'El mapa no pudo dibujar las capas de datos. '
          + 'La consulta por dirección y por ubicación funciona igual.';
      }
    }
  }, 250);
  aplicarBase(baseGuardada());

  const alternar = (id, capa) => $(id).addEventListener('change', (e) => {
    if (m.getLayer(capa)) {
      m.setLayoutProperty(capa, 'visibility', e.target.checked ? 'visible' : 'none');
    }
  });
  // La capa derivada enciende relleno y borde a la vez: el achurado punteado
  // del borde es lo que la distingue de la normativa.
  $('#cap-derivadas').addEventListener('change', (e) => {
    const v = e.target.checked ? 'visible' : 'none';
    for (const c of ['lam-fill', 'lam-line']) {
      if (m.getLayer(c)) m.setLayoutProperty(c, 'visibility', v);
    }
    if (e.target.checked && !estado.laminas) {
      elEstado().textContent = 'Las láminas vectorizadas no están en esta '
        + 'instalación: corre el script 19 para publicarlas.';
    }
  });
  alternar('#cap-puntos', 'pc-circ');
  alternar('#cap-jrc', 'jrc-fill');
  alternar('#cap-gore', 'gore-fill');
  // La huella observada son dos capas (relleno y borde), así que no puede usar
  // `alternar`, que maneja una sola. Y si la capa no existe, el control lo dice
  // en vez de quedarse mudo: una casilla que no hace nada se lee como visor roto.
  $('#cap-sar').addEventListener('change', (e) => {
    const ver = e.target.checked ? 'visible' : 'none';
    const pintar = () => {
      const capas = ['sar-fill', 'sar-line'].filter((c) => m.getLayer(c));
      for (const c of capas) m.setLayoutProperty(c, 'visibility', ver);
      return capas.length > 0;
    };
    if (!e.target.checked) { pintar(); elEstado().textContent = ''; return; }
    // Las dos razones por las que puede no haber nada que dibujar son distintas
    // y el visor no puede confundirlas: que el dato no exista es información
    // sobre el mundo, que el mapa no haya terminado de cargar es un problema
    // nuestro y se resuelve solo.
    if (!estado.sar) {
      elEstado().textContent =
        'Todavía no hay huella observada por satélite publicada en este visor, ' +
        'así que no hay nada que dibujar. Que no esté observada no significa ' +
        'que no se inunde.';
      return;
    }
    if (!m.isStyleLoaded()) {
      elEstado().textContent = 'Preparando el mapa…';
      m.once('idle', () => { pintar(); elEstado().textContent = ''; });
      return;
    }
    elEstado().textContent = pintar()
      ? '' : 'La huella observada no se pudo dibujar en este dispositivo.';
  });
  $('#cap-camp').addEventListener('change', (e) => {
    for (const capa of ['camp-fill', 'camp-line']) {
      if (m.getLayer(capa)) {
        m.setLayoutProperty(capa, 'visibility', e.target.checked ? 'visible' : 'none');
      }
    }
  });
  $('#cap-planos').addEventListener('change', (e) => {
    const ver = e.target.checked ? 'visible' : 'none';
    for (const capa of ['huellas-fill', 'huellas-line']) {
      if (m.getLayer(capa)) m.setLayoutProperty(capa, 'visibility', ver);
    }
    if (!e.target.checked) {
      ocultarPlanos();
      elEstado().textContent = '';
      return;
    }
    if (!m.isStyleLoaded()) {
      // Pedirle al usuario que reintente es trasladarle un problema nuestro:
      // se espera al estilo y se continúa solo.
      elEstado().textContent = 'Preparando el mapa…';
      m.once('idle', () => {
        for (const capa of ['huellas-fill', 'huellas-line']) {
          if (m.getLayer(capa)) m.setLayoutProperty(capa, 'visibility', 'visible');
        }
        actualizarPlanos(true);
      });
      return;
    }
    actualizarPlanos(true);
  });
  $('#cap-areas').addEventListener('change', (e) => {
    for (const capa of ['ar-fill', 'ar-line']) {
      if (m.getLayer(capa)) {
        m.setLayoutProperty(capa, 'visibility', e.target.checked ? 'visible' : 'none');
      }
    }
  });
}

/* ---------------------------------------------------------------- comunas */

function renderComunas() {
  const cont = $('#tabla-comunas');
  const top = estado.comunas.comunas.filter((c) => c.puntos_inundacion > 0).slice(0, 12);
  const max = Math.max(1, ...top.map((c) => c.inundacion_riesgo_alto));
  cont.innerHTML = '';
  for (const c of top) {
    const b = document.createElement('button');
    b.className = 'fila-comuna';
    b.type = 'button';
    // La barra codifica la magnitud además del número: en algo que se opera de
    // un vistazo, la forma comunica antes que la cifra.
    b.innerHTML =
      `<span class="n">${esc(c.comuna)}</span>` +
      `<span class="cr">${c.cronicos} crónicos</span>` +
      `<span class="pill p-alto">${c.inundacion_riesgo_alto}</span>` +
      `<span class="barra" aria-hidden="true"><span style="width:${
        Math.round(100 * c.inundacion_riesgo_alto / max)}%"></span></span>`;
    b.setAttribute('aria-label',
      `${c.comuna}: ${c.inundacion_riesgo_alto} puntos críticos de inundación de ` +
      `riesgo alto o muy alto, ${c.cronicos} crónicos`);
    b.addEventListener('click', () => zoomComuna(c));
    cont.appendChild(b);
  }
}

/** Cifras de portada. Se calculan de los datos cargados y no se escriben a mano:
 *  una portada con números fijos empieza a mentir en cuanto cambia el pipeline. */
function renderCifras() {
  const cont = $('#cifras');
  if (!cont) return;
  const cronicos = estado.puntos.features.filter((f) => f.properties.cronico).length;
  const comunasConArea = new Set(
    (estado.areasRiesgo?.features || []).map((f) => f.properties.comuna)).size;
  const camp = estado.campamentos?.features || [];
  const hogares = camp.reduce((a, f) => a + (f.properties.hogares || 0), 0);
  const datos = [
    { n: estado.puntos.features.length,
      t: 'puntos críticos de inundación registrados por SENAPRED' },
    { n: cronicos, t: 'de ellos son crónicos: se repiten temporada tras temporada' },
    { n: estado.areasRiesgo?.features.length || 0,
      t: `áreas de riesgo con efecto legal, en ${comunasConArea} comunas` },
    { n: estado.planos?.length || 0,
      t: 'planos de plan regulador ubicados sobre el mapa' },
  ];
  // Hectáreas con agua observada. Salen del resumen del propio índice SAR, no
  // de un recuento del frontend ni de un número escrito a mano: si el pipeline
  // reprocesa el evento, la portada cambia sola.
  const haObservadas = Math.round(estado.sarIndice?.resumen?.hectareas || 0);
  if (haObservadas) {
    const ev = estado.sarIndice?.evento?.nombre;
    datos.push({ n: haObservadas,
      t: `hectáreas donde el satélite vio agua${ev ? ` — ${ev}` : ''}` });
  }
  // La cifra de hogares va sólo si hay dato: es la que le da peso humano al
  // resto, y una cifra en cero acá se leería como "no hay nadie expuesto".
  if (hogares) {
    datos.push({ n: hogares,
      t: `hogares en ${camp.length} campamentos dentro de área de riesgo por inundación` });
  }
  cont.innerHTML = datos.map((d) => `<div class="cifra">
      <span class="cifra-num">${d.n.toLocaleString('es-CL')}</span>
      <span class="cifra-txt">${esc(d.t)}</span>
    </div>`).join('');
}

/** Nota del control de la capa B. El evento y las fechas salen del índice del
 *  propio dato y no del HTML: escritas a mano quedarían mintiendo en cuanto se
 *  procese otro evento. Si la capa no está, el panel también lo dice. */
function notaSar() {
  const el = $('#nota-sar');
  if (!el) return;
  if (!estado.sar) {
    el.textContent = 'La huella de inundación observada por satélite todavía no está ' +
      'publicada en este visor. Que no esté observada no significa que no se inunde.';
    return;
  }
  const ev = estado.sarIndice?.evento || {};
  const km2 = estado.sarIndice?.resumen?.km2;
  const fechas = fechasDePasada(estado.sar.features);
  el.textContent =
    `Huella observada${ev.nombre ? ` del ${ev.nombre}` : ''}` +
    (fechas.length ? `, pasadas del ${listaEnEspanol(fechas)}` : '') +
    (km2 ? ` · ${Number(km2).toLocaleString('es-CL', { maximumFractionDigits: 1 })} km² con agua detectada` : '') +
    '. Donde el satélite no pasó no hay huella, y eso no es lo mismo que no inundado.';
}

function zoomComuna(c) {
  if (!estado.puntos) return;
  const feats = estado.puntos.features.filter((f) => f.properties.comuna === c.comuna);
  if (!feats.length) return;
  const lons = feats.map((f) => f.geometry.coordinates[0]);
  const lats = feats.map((f) => f.geometry.coordinates[1]);
  if (estado.mapa) {
    estado.mapa.fitBounds(
      [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
      { padding: 50, maxZoom: 13 });
  }
  // Y además se RESPONDE, no sólo se mueve el mapa.
  //
  // Elegir «Angol» en las sugerencias movía la vista y nada más: quien navega
  // con teclado, quien usa lector de pantalla o quien tiene el mapa caído por
  // WebGL elegía su comuna y no obtenía ninguna ficha. El mapa quedaba como
  // única vía real de respuesta, que es justo lo contrario de lo que este visor
  // necesita — y el caso rural, el más frecuente, es el que peor lo pasaba.
  const cx = (Math.min(...lons) + Math.max(...lons)) / 2;
  const cy = (Math.min(...lats) + Math.max(...lats)) / 2;
  consultar(cx, cy, `${c.comuna} (centro de los registros de la comuna)`);
}

/* ------------------------------------------------------------------ inicio */

/** Enlaza todos los controles. Se llama ANTES de cargar los datos para que la
 *  interfaz responda desde el primer instante: en una conexión lenta, un botón
 *  que no hace nada durante un minuto se lee como sitio roto. Los manejadores
 *  que necesitan datos comprueban que estén; los que no, funcionan igual. */
function enlazarInterfaz() {
  for (const cual of Object.keys(BASES)) {
    const el = $(`#base-${cual}`);
    if (el) el.addEventListener('change', () => { if (el.checked) aplicarBase(cual); });
  }
  enlazarPestanas();
  const imp = $('#btn-imprimir');
  if (imp) imp.addEventListener('click', () => window.print());

  // El botón «Buscar» no tenía manejador desde el 25-ago-2026: sólo respondía
  // Enter. Quien toca un botón que no hace nada concluye que el sitio no
  // funciona, y en un celular Enter no es obvio.
  const btnBuscar = $('#btn-buscar');
  if (btnBuscar) btnBuscar.addEventListener('click', () => { cerrarSugerencias(); buscar(); });

  // Encender / apagar todo. Con las capas agrupadas por familia, comparar «lo
  // que dice la norma» contra «lo que se midió» es el gesto más útil del visor,
  // y a mano son siete toques.
  const todas = (encender) => {
    for (const id of CASILLAS_CAPAS) {
      const el = $(`#${id}`);
      if (!el || el.checked === encender) continue;
      el.checked = encender;
      el.dispatchEvent(new Event('change'));   // reusa la lógica de cada capa
    }
  };
  $('#btn-capas-todas').addEventListener('click', () => todas(true));
  $('#btn-capas-ninguna').addEventListener('click', () => todas(false));
  $('#btn-ubicacion').addEventListener('click', () => { cerrarSugerencias(); ubicarme(); });

  const campo = $('#q');
  campo.addEventListener('input', pedirSugerencias);
  campo.addEventListener('focus', pedirSugerencias);
  campo.addEventListener('blur', () => setTimeout(cerrarSugerencias, 120));
  campo.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); moverSugerencia(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); moverSugerencia(-1); }
    else if (e.key === 'Escape') { cerrarSugerencias(); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      // Enter con una sugerencia marcada la elige; sin marcar, busca el texto.
      if (SUG.activo >= 0 && SUG.items[SUG.activo]) SUG.items[SUG.activo].accion();
      else { cerrarSugerencias(); buscar(); }
    }
  });

}


async function inicio() {
  // Los controles se enlazan ANTES de esperar los datos.
  //
  // `cargarDatos` baja del orden de 3,7 MB de GeoJSON. En 3G eso es más de un
  // minuto en que tocar «Buscar» no hacía absolutamente nada y la pantalla no
  // decía nada: el sitio parecía roto justo para quien tiene peor conexión, que
  // es buena parte del público de esto. Ahora el botón responde desde el primer
  // instante, y si los datos aún no están, lo dice.
  enlazarInterfaz();
  elEstado().textContent = 'Cargando los datos de la región…';
  try {
    await cargarDatos();
    elEstado().textContent = '';
  } catch (e) {
    elEstado().textContent = `No se pudieron cargar los datos: ${e.message}`;
    return;
  }
  // El mapa es secundario: lo que importa es la respuesta. Si el dispositivo no
  // soporta WebGL —gama baja, que es justo el público objetivo— el sitio tiene
  // que seguir funcionando por buscador y por ubicación.
  try {
    iniciarMapa();
  } catch (e) {
    document.querySelector('.mapa-envoltorio').innerHTML =
      '<p class="nota">El mapa no se puede mostrar en este dispositivo, pero la ' +
      'consulta por dirección y por ubicación funciona igual.</p>';
  }
  renderCifras();
  renderComunas();
  notaSar();
  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    navigator.serviceWorker.register('sw.js').catch(() => { /* offline opcional */ });
  }
}

inicio();
