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
  if (!m || !m.isStyleLoaded()) return;
  for (const p of estado.planos || []) {
    const id = `plano-${p.archivo.replace(/[^\w]/g, '')}`;
    if (m.getLayer(id)) m.setLayoutProperty(id, 'visibility', 'none');
  }
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

  let nivel, titulo;
  if (sar.length >= 1) {
    nivel = 'alto';
    const f = fechaLarga(sar[0].properties.fecha_observacion);
    titulo = f ? `El agua llegó hasta acá el ${f}`
               : 'El agua llegó hasta acá: huella observada por satélite';
  } else if (areas.length >= 1) {
    nivel = 'alto';
    titulo = 'Estás en un área de riesgo por inundación del plan regulador';
  } else if (graves.length >= 1 || en(RADIOS.cercano).length >= 3) {
    nivel = 'alto';
    titulo = 'Tu sector tiene registro de inundaciones';
  } else if (en(RADIOS.medio).length >= 1) {
    nivel = 'medio';
    titulo = 'Hay registros de inundación cerca';
  } else if (cerca.length >= 1) {
    nivel = 'bajo';
    titulo = 'Registros de inundación a cierta distancia';
  } else {
    nivel = 'sindato';
    titulo = 'Sin registros en las fuentes consultadas';
  }

  return { nivel, titulo, cerca, areas, sar, coberturaSar,
           enCoberturaSar: coberturaSar.length > 0,
           planos: planosQueCubren(lon, lat),
           campamentos: poligonosQueContienen(lon, lat, estado.campamentos),
           enMancha: dentroDeMancha(lon, lat, estado.jrc),
           gore: poligonosQueContienen(lon, lat, estado.gore) };
}

/* ----------------------------------------------------------------- render */

const ICONO = { alto: '⚠️', medio: '⚡', bajo: 'ℹ️', sindato: '❔' };
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
function atribucion(fc, primerFeature) {
  const p = primerFeature?.properties || {};
  const proc = fc?.procedencia || {};
  const fuente = p.fuente || proc.fuente || 'fuente no declarada';
  const anio = p.anio || proc.fecha_dato || 'año no declarado';
  const bajado = (proc.generado || '').slice(0, 10);
  return `<p class="fuente"><strong>Fuente:</strong> ${esc(fuente)} · ` +
         `<strong>Año:</strong> ${esc(anio)}` +
         (bajado ? ` · <span class="incert">datos obtenidos ${esc(bajado)}</span>` : '') +
         `</p>`;
}

function render(res, etiqueta, lon, lat) {
  const cont = $('#respuesta');
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
      if (p.zona) html += ` <span class="incert">(zona ${esc(p.zona)})</span>`;
      if (p.usos_prohibidos) {
        html += `<br><span class="incert">Usos prohibidos: ${esc(p.usos_prohibidos)}</span>`;
      }
      if (p.ordenanza_url) {
        html += `<br><a href="${esc(p.ordenanza_url)}" rel="noopener">Ver ordenanza</a>`;
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
    html += `<p>Este punto no cae dentro de un área de riesgo por inundación
             declarada en el plan regulador.</p>
             <p class="incert">Que no aparezca no significa que no exista: esta capa
             sólo trae instrumentos ya vigentes y publicados, y va por detrás de las
             aprobaciones. Además, la mayoría de las comunas de la región no ha
             declarado ningún área de riesgo. Consulta en la Dirección de Obras de tu
             municipalidad.</p>`;
  }
  html += atribucion(estado.areasRiesgo, res.areas[0] || estado.areasRiesgo?.features[0]);
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
               órbita (${esc(listaEnEspanol(refs))}): el eco del radar cayó
               ${esc(String(Math.abs(p.caida_db)).replace('.', ','))} dB y quedó bajo
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
    html += `<div class="evidencia">
      <h3>El plano original de tu comuna <span class="etiqueta">A · NORMATIVO</span></h3>
      <p>Tenemos el plano del plan regulador que cubre este punto, ubicado sobre el
         mapa a partir de su propia grilla de coordenadas impresa.</p>
      <ul><li><strong>${esc(p.titulo)}</strong><br>
        <span class="incert">${p.puntos_control} puntos de control ·
        error de ubicación ${p.rmse_loo_m} m · ${p.resolucion_m_px} m por píxel</span>
      </li></ul>
      <button type="button" class="secundario" id="btn-plano">Ver el plano sobre el mapa</button>
      <p class="incert">Es el documento oficial tal cual, sin retocar. Lo único que
         hicimos fue darle coordenadas.</p></div>`;
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
      btnPlano.textContent = ok ? 'Plano cargado sobre el mapa'
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
  l.push('', 'Esto NO es información oficial. En emergencia: SENAPRED y tu municipio.');
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
            + `&viewbox=-73.7,-37.35,-70.9,-39.65&bounded=1&q=${encodeURIComponent(texto)}`;
  const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
  if (!r.ok) throw new Error(`geocodificador HTTP ${r.status}`);
  const j = await r.json();
  if (!j.length) return null;
  return { lon: +j[0].lon, lat: +j[0].lat, etiqueta: j[0].display_name };
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
            + `&viewbox=-73.7,-37.35,-70.9,-39.65&bounded=1&q=${encodeURIComponent(texto)}`;
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
  const res = evaluar(lon, lat);
  render(res, etiqueta, lon, lat);
  ponerMarcador(lon, lat);
  estado.mapa && estado.mapa.flyTo({ center: [lon, lat], zoom: 14 });
}

async function buscar() {
  const q = $('#q').value.trim();
  if (!q) return;
  const btn = $('#btn-buscar');
  btn.disabled = true;
  elEstado().textContent = 'Buscando la dirección…';
  try {
    const hit = await geocodificar(q);
    if (!hit) { elEstado().textContent = 'No se encontró esa dirección en La Araucanía.'; return; }
    elEstado().textContent = '';
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
      elEstado().textContent = '';
      consultar(pos.coords.longitude, pos.coords.latitude, 'Tu ubicación actual');
    },
    (err) => { elEstado().textContent = `No se pudo obtener la ubicación (${err.message}).`; },
    { enableHighAccuracy: true, timeout: 12000 }
  );
}

/* -------------------------------------------------------------------- mapa */

const ESTILO = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap',
    },
  },
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
};

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
  });
  estado.mapa = m;
  m.addControl(new maplibregl.NavigationControl(), 'top-right');
  m.addControl(new maplibregl.ScaleControl({ unit: 'metric' }));

  // Las capas se agregan cuando el ESTILO está listo, no en el evento 'load'.
  // 'load' espera además al primer cuadro renderizado, así que en una pestaña en
  // segundo plano, con la ventana minimizada o en un dispositivo que no compone
  // (gama baja, contexto WebGL perdido) no dispara nunca y el mapa queda vacío
  // sin ningún error visible.
  let capasPuestas = false;
  const agregarCapas = () => {
    if (capasPuestas || !m.isStyleLoaded()) return;
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
      const capas = ['pc-circ', 'huellas-fill'].filter((c) => m.getLayer(c));
      if (m.queryRenderedFeatures(e.point, { layers: capas }).length) return;
      consultar(e.lngLat.lng, e.lngLat.lat,
        `Punto seleccionado (${e.lngLat.lat.toFixed(4)}, ${e.lngLat.lng.toFixed(4)})`);
    });
  };

  m.on('styledata', agregarCapas);
  m.on('load', agregarCapas);
  agregarCapas();

  const alternar = (id, capa) => $(id).addEventListener('change', (e) => {
    if (m.getLayer(capa)) {
      m.setLayoutProperty(capa, 'visibility', e.target.checked ? 'visible' : 'none');
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
  const feats = estado.puntos.features.filter((f) => f.properties.comuna === c.comuna);
  if (!feats.length || !estado.mapa) return;
  const lons = feats.map((f) => f.geometry.coordinates[0]);
  const lats = feats.map((f) => f.geometry.coordinates[1]);
  estado.mapa.fitBounds(
    [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
    { padding: 50, maxZoom: 13 });
  document.querySelector('.mapa-envoltorio').scrollIntoView({ behavior: 'smooth' });
}

/* ------------------------------------------------------------------ inicio */

async function inicio() {
  try {
    await cargarDatos();
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
  $('#btn-buscar').addEventListener('click', () => { cerrarSugerencias(); buscar(); });
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

  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    navigator.serviceWorker.register('sw.js').catch(() => { /* offline opcional */ });
  }
}

inicio();
