/* fA_zoom_comuna.js : ¿qué titular recibe quien elige su COMUNA en las
 * sugerencias o en la tabla «Comunas con más registros»?
 *
 * POR QUÉ. zoomComuna() (web/app.js) consulta el centro de la caja envolvente
 * de los puntos críticos de la comuna y le pone la etiqueta «X (centro de los
 * registros de la comuna)». Ese centro es un punto que nadie eligió: puede caer
 * en un potrero lejos de todos los registros, y el titular sale como si fuera
 * una casa («Sin registros en las fuentes consultadas») para una comuna que
 * tiene decenas de registros.
 *
 * LAS DOS PREGUNTAS DEL INSTRUMENTO
 *  1. Si el centro siempre cayera cerca de los registros, ¿esto lo vería? Sí:
 *     se cuenta, por comuna, el titular contra el número de puntos de la
 *     comuna. CONTROL: se evalúa además el punto crítico más cercano al centro,
 *     que por construcción tiene registro a 0 m; tiene que salir distinto de
 *     «sin dato». Si el control sale «sin dato», el detector está roto.
 *  2. Si el instrumento estuviera muerto (no hay comunas, no hay puntos), sale
 *     SIN DATO con código 2.
 *
 * Uso: node tools/auditoria/fA_zoom_comuna.js
 */
'use strict';
const { cargar } = require('./fA_harness_evaluar.js');

(async () => {
  const h = await cargar();
  const comunas = h.run('estado.comunas.comunas.filter((c) => c.puntos_inundacion > 0).map((c) => c.comuna)');
  if (!comunas.length) { console.log('SIN DATO'); process.exit(2); }
  const puntos = h.run('estado.puntos.features');
  const filas = [];
  let ctrlOk = true;
  for (const com of comunas) {
    const fs = puntos.filter((f) => f.properties.comuna === com);
    if (!fs.length) continue;
    const xs = fs.map((f) => f.geometry.coordinates[0]), ys = fs.map((f) => f.geometry.coordinates[1]);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    const r = h.evaluar(cx, cy, null);
    const masCerca = fs.map((f) => [f, Math.hypot(f.geometry.coordinates[0] - cx, f.geometry.coordinates[1] - cy)]).sort((a, b) => a[1] - b[1])[0][0];
    const rc = h.evaluar(...masCerca.geometry.coordinates, null);
    if (rc.nivel === 'sindato') ctrlOk = false;
    filas.push({ com, n: fs.length, nivel: r.nivel, titulo: r.titulo, cerca: r.cerca.length });
  }
  filas.sort((a, b) => b.n - a.n);
  for (const f of filas) console.log(`${f.com.padEnd(18)} puntos=${String(f.n).padStart(3)}  a1,5km=${String(f.cerca).padStart(2)}  ${f.nivel.padEnd(7)} ${f.titulo}`);
  const sd = filas.filter((f) => f.nivel === 'sindato');
  console.log(`\ncomunas con registros: ${filas.length}; titular «sin dato» al elegir la comuna: ${sd.length} (${sd.reduce((a, f) => a + f.n, 0)} registros en esas comunas)`);
  console.log(`CONTROL (punto crítico más cercano al centro no es «sin dato»): ${ctrlOk ? 'OK' : 'DETECTOR ROTO'}`);
  process.exit(ctrlOk ? 0 : 2);
})().catch((e) => { console.error(e); process.exit(2); });
