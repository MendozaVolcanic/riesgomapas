/* fA_precision_arrastrada.js : ¿la precisión del GPS de una consulta anterior se
 * arrastra a una dirección elegida desde las sugerencias?
 *
 * POR QUÉ. web/app.js guarda la precisión del GPS en estado.precisionPos y la
 * suma al ancho de la banda de borde. buscar() y el toque en el mapa la ponen
 * en null antes de consultar; la acción de una sugerencia de dirección
 * (sugerenciasDirecciones -> accion -> consultar) no. Si eso es así, quien
 * primero pidió «mi ubicación» y luego eligió una dirección sugerida recibe
 * una banda ensanchada por un GPS que no tiene nada que ver con esa dirección,
 * y el «por qué» le dice «tu ubicación ±N m».
 *
 * Se ejecuta el código real: sugerenciasDirecciones() con un fetch falso que
 * imita la respuesta de Nominatim, y la accion() que devuelve.
 *
 * LAS DOS PREGUNTAS DEL INSTRUMENTO
 *  1. Si el defecto no existiera (la acción reseteara la precisión), ¿la prueba
 *     lo vería? Sí: el CONTROL hace la misma consulta por buscar(), que sí
 *     resetea, y exige que ahí NO haya banda. Si las dos rutas dan lo mismo, la
 *     prueba no distingue y lo dice.
 *  2. Si el instrumento estuviera muerto, ¿se vería distinto? Si consultar()
 *     no corre, estado.ultimo queda null y el script sale con código 2.
 *
 * Uso: node tools/auditoria/fA_precision_arrastrada.js
 */
'use strict';
const { cargar } = require('./fA_harness_evaluar.js');

(async () => {
  const h = await cargar();
  const { ctx } = h;
  // Punto de prueba: a ~30 m fuera de un área de riesgo del MINVU, donde la
  // banda sin GPS (2 x 10 m) no alcanza y con GPS de 65 m sí.
  let prueba = null;
  const nA = h.run('estado.areasRiesgo.features.length');
  for (let i = 0; i < nA && !prueba; i++) {
    const v = h.run(`estado.areasRiesgo.features[${i}].geometry.type === 'Polygon'
      ? estado.areasRiesgo.features[${i}].geometry.coordinates[0][0]
      : estado.areasRiesgo.features[${i}].geometry.coordinates[0][0][0]`);
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]]) {
      const lat = v[1] + dy * 30 / 111320;
      const lon = v[0] + dx * 30 / (111320 * Math.cos(v[1] * Math.PI / 180));
      const r = h.evaluar(lon, lat, null);
      ctx.__p = [lon, lat];
      const b = h.run('bordeMasCercano(__p[0], __p[1], estado.areasRiesgo, 200)');
      if (!r.areas.length && !r.laminas.length && !r.sar.length && !r.borde && b && b.d > 22 && b.d < 40) {
        prueba = { lon, lat, d: b.d, comuna: h.run(`estado.areasRiesgo.features[${i}].properties.comuna`) };
        break;
      }
    }
  }
  if (!prueba) { console.log('SIN DATO: no se encontró punto de prueba'); process.exit(2); }
  console.log(`punto de prueba: ${prueba.lon.toFixed(6)}, ${prueba.lat.toFixed(6)} (${prueba.comuna}), borde MINVU a ${prueba.d.toFixed(1)} m`);

  const nominatim = async (url) => {
    if (String(url).includes('nominatim')) {
      return { ok: true, status: 200, json: async () => ([{ lon: String(prueba.lon), lat: String(prueba.lat),
        display_name: 'Calle de prueba 123, ' + prueba.comuna + ', La Araucanía', addresstype: 'house' }]) };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  };
  const capt = ctx.__capturas, el = ctx.__elemento;
  const preparar = () => {
    capt['#detalle-ficha'] = el(); capt['#respuesta'] = el();
    capt['#q'] = el(); capt['#q'].value = 'Calle de prueba 123';
    capt['#btn-buscar'] = el();
  };

  // RUTA 1: GPS primero (precisión 65 m), luego dirección elegida en sugerencias.
  preparar();
  const fetchOriginal = ctx.fetch;
  ctx.fetch = nominatim;
  h.run('estado.precisionPos = 65; estado.ultimo = null;');
  const items = await h.run("sugerenciasDirecciones('Calle de prueba 123')");
  if (!items.length) { console.log('INSTRUMENTO MUERTO: la sugerencia no llegó'); process.exit(2); }
  items[0].accion();
  await new Promise((r) => setTimeout(r, 50));
  const u1 = h.run('estado.ultimo');
  if (!u1) { console.log('INSTRUMENTO MUERTO: consultar no corrió'); process.exit(2); }
  const resp1 = capt['#respuesta'].innerHTML;
  console.log(`RUTA sugerencia tras GPS: precisionPos=${h.run('estado.precisionPos')} nivel=${u1.res.nivel} titulo="${u1.res.titulo}"`);
  console.log(`   «por qué» menciona «tu ubicación ±65 m»: ${/tu ubicación ±65 m/.test(resp1)}`);

  // RUTA 2 (CONTROL): misma dirección por buscar(), que sí resetea.
  preparar();
  h.run('estado.precisionPos = 65; estado.ultimo = null;');
  await h.run('buscar()');
  const u2 = h.run('estado.ultimo');
  console.log(`RUTA buscar() tras GPS:    precisionPos=${h.run('estado.precisionPos')} nivel=${u2 && u2.res.nivel} titulo="${u2 && u2.res.titulo}"`);
  ctx.fetch = fetchOriginal;

  const defecto = u1.res.borde && !(u2 && u2.res.borde);
  console.log(defecto
    ? 'DEFECTO CONFIRMADO: la misma dirección da «borde» por sugerencia y no por buscar(); la precisión del GPS se arrastró.'
    : 'Sin diferencia entre rutas: o no hay defecto o el punto no discrimina.');
  process.exit(defecto ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
