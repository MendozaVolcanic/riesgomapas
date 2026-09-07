#!/usr/bin/env node
/* Arnés de auditoría: somete el ray-casting REAL del visor a casos adversariales.
 *
 * Qué mide: para cada caso {fc, puntos}, qué features de `fc` dice el visor que
 * contienen cada punto, usando `dentroAnillo` y `poligonosQueContienen` tal
 * como están escritas en web/app.js. No reimplementa nada.
 *
 * Cómo carga las funciones: extrae su texto de web/app.js con expresiones
 * regulares y lo evalúa en un `vm` aislado. Se eligió eso y no evaluar el
 * archivo entero con `document`/`window`/`L` falsos porque app.js termina con
 * `inicio()` (toca fetch, navigator, DOM, MapLibre) y cualquier stub que falte
 * revienta —o peor, no revienta y deja funciones a medio definir. Con la
 * extracción el arnés imprime la línea inicial y el SHA-1 de cada función
 * extraída: quien lea el informe puede comprobar contra el archivo que se
 * auditó exactamente ese código. Si falta una de las cuatro, el arnés muere
 * con código 2 en vez de responder con algo parecido.
 *
 * Las dos preguntas del instrumento:
 *  (1) si el ray-casting estuviera roto, ¿esto falla?  Sí: --autocontrol
 *      evalúa un cuadrado con un punto claramente adentro y otro claramente
 *      afuera, y el modo comparación (raycasting_vs_shapely.py) contrasta
 *      punto a punto con shapely.
 *  (2) si el instrumento estuviera muerto, ¿se vería distinto?  Sí: si la
 *      extracción no encuentra las funciones sale con código 2; y se puede
 *      apuntar --app a una copia adulterada para ver que los controles fallan.
 *
 * Uso:
 *   node tools/auditoria/raycasting_adversarial.js --autocontrol [--app web/app.js]
 *   node tools/auditoria/raycasting_adversarial.js --casos casos.json [--app web/app.js] > salida.json
 *
 * casos.json: { "casos": [ { "id": "...", "fc": <FeatureCollection>, "puntos": [[lon,lat],...] } ] }
 * salida:     { "extraccion": {...}, "resultados": [ { "id", "contiene": [[idx,...], ...] } ] }
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const raiz = path.resolve(__dirname, '..', '..');
const appPath = path.resolve(opt('--app', path.join(raiz, 'web', 'app.js')));
const fuente = fs.readFileSync(appPath, 'utf8');

const NOMBRES = ['distancia', 'dentroAnillo', 'poligonosQueContienen', 'dentroDeMancha'];

/** Extrae `function nombre(...) { ... }` contando llaves desde la firma. */
function extraer(nombre) {
  const re = new RegExp(`^function ${nombre}\\s*\\(`, 'm');
  const m = re.exec(fuente);
  if (!m) return null;
  let i = fuente.indexOf('{', m.index);
  let prof = 0;
  for (let j = i; j < fuente.length; j++) {
    if (fuente[j] === '{') prof++;
    else if (fuente[j] === '}') { prof--; if (prof === 0) {
      const texto = fuente.slice(m.index, j + 1);
      const linea = fuente.slice(0, m.index).split('\n').length;
      return { nombre, texto, linea,
               sha1: crypto.createHash('sha1').update(texto).digest('hex').slice(0, 12) };
    } }
  }
  return null;
}

const extraidas = NOMBRES.map(extraer);
const faltan = NOMBRES.filter((n, i) => !extraidas[i]);
if (faltan.length) {
  console.error(`NO SE PUDIERON EXTRAER: ${faltan.join(', ')} de ${appPath}`);
  process.exit(2);
}
const ctx = {};
vm.createContext(ctx);
vm.runInContext(extraidas.map((e) => e.texto).join('\n') +
  '\nthis.__f = { distancia, dentroAnillo, poligonosQueContienen, dentroDeMancha };', ctx);
const F = ctx.__f;
const extraccion = {
  archivo: path.relative(raiz, appPath).replace(/\\/g, '/'),
  funciones: extraidas.map(({ nombre, linea, sha1 }) => ({ nombre, linea, sha1 })),
};

function indicesQueContienen(lon, lat, fc) {
  const hits = F.poligonosQueContienen(lon, lat, fc);
  return hits.map((f) => fc.features.indexOf(f));
}

if (args.includes('--autocontrol')) {
  const cuadrado = { type: 'FeatureCollection', features: [{ type: 'Feature', properties: {},
    geometry: { type: 'Polygon', coordinates: [[[-72.7, -37.8], [-72.6, -37.8], [-72.6, -37.7], [-72.7, -37.7], [-72.7, -37.8]]] } }] };
  const dentro = indicesQueContienen(-72.65, -37.75, cuadrado);
  const fuera = indicesQueContienen(-72.5, -37.75, cuadrado);
  const okD = dentro.length === 1, okF = fuera.length === 0;
  console.log(JSON.stringify({ extraccion,
    control_positivo: { punto: [-72.65, -37.75], contiene: dentro, ok: okD },
    control_negativo: { punto: [-72.5, -37.75], contiene: fuera, ok: okF },
    dentroDeMancha_positivo: F.dentroDeMancha(-72.65, -37.75, cuadrado),
    distancia_1grado_lat_m: F.distancia(-38, -72, -37, -72) }, null, 1));
  process.exit(okD && okF ? 0 : 1);
}

const casosPath = opt('--casos');
if (!casosPath) { console.error('falta --casos o --autocontrol'); process.exit(2); }
const { casos } = JSON.parse(fs.readFileSync(casosPath, 'utf8'));
const resultados = casos.map((c) => ({
  id: c.id,
  contiene: c.puntos.map(([lon, lat]) => indicesQueContienen(lon, lat, c.fc)),
}));
process.stdout.write(JSON.stringify({ extraccion, resultados }));
