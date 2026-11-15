/* vA_sondas.js : sondas del verificador (frente A) sobre web/app.js REAL.
 *
 * Reutiliza el arnés fA_harness_evaluar.js (carga app.js y web/data/ reales en
 * Node, con DOM y fetch simulados). Lo uso porque ejecutar el archivo real mide
 * el visor y no una copia de su regla.
 *
 * LAS DOS PREGUNTAS DEL INSTRUMENTO
 *  1. Si lo medido estuviera roto, ¿fallaría? Cada sonda trae un CONTROL que
 *     produce el fenómeno a propósito (p. ej. un punto dentro de un polígono
 *     derivado) y exige que la medida lo vea; si no lo ve, imprime DETECTOR ROTO.
 *  2. Si el instrumento estuviera muerto (capas vacías), ¿se vería distinto?
 *     El arnés lanza «ARNÉS MUERTO» si una capa viene vacía; las sondas
 *     imprimen SIN DATO cuando la muestra es 0.
 * Uso: node tools/auditoria/vA_sondas.js [sonda...]   (sin argumentos: todas)
 */
'use strict';
const { cargar } = require('./fA_harness_evaluar.js');
const L = (s) => String(s).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const quiero = new Set(process.argv.slice(2));
const corre = (k) => !quiero.size || quiero.has(k);
const PASO = Number(process.env.PASO || 4);   // 1 de cada PASO polígonos (la evaluación completa tarda minutos)

// puntos a m metros de un vértice de cada polígono, en 4 direcciones
function* vecindad(h, capa, ms) {
  const nf = h.run(`estado.${capa}.features.length`);
  for (let i = 0; i < nf; i += PASO) {
    const g = h.run(`estado.${capa}.features[${i}].geometry`);
    const anillos = g.type === 'Polygon' ? [g.coordinates[0]] : g.coordinates.map((p) => p[0]);
    for (const an of anillos) {
      const v = an[0];
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) for (const m of ms) {
        yield [v[0] + dx * m / (111320 * Math.cos(v[1] * Math.PI / 180)), v[1] + dy * m / 111320, capa, i];
      }
    }
  }
}

(async () => {
  const h = await cargar();

  if (corre('F100')) {
    console.log('== F-100: ¿el detalle explica la banda?, ¿y qué más se imprime?');
    let n = 0, sinExp = 0, resumenExp = 0, neg = 0;
    for (const capa of ['areasRiesgo', 'laminas']) for (const [lon, lat] of vecindad(h, capa, [3, 8, 15])) {
      const r = h.evaluar(lon, lat, null); if (!r.borde) continue; n++;
      const o = h.renderDetalle(r, lon, lat);
      const det = L(o.detalle), res = L(o.resumen);
      if (!/metros del borde|adentro y afuera|±/.test(det)) sinExp++;
      if (/adentro y afuera no se distinguen/.test(res)) resumenExp++;
      if (/no cae dentro de un área de riesgo/.test(det)) neg++;
    }
    console.log(`  puntos con titular de borde: ${n}; detalle sin explicar banda: ${sinExp}; resumen (panel que TAMBIEN se imprime) explica la banda: ${resumenExp}; detalle dice "no cae dentro": ${neg}`);
    const c = h.evaluar(-72.6867, -37.78499, null);
    console.log(`  CONTROL (dentro de lámina el detalle trae ±): ${/±/.test(L(h.renderDetalle(c, -72.6867, -37.78499).detalle)) ? 'OK' : 'DETECTOR ROTO'}`);
  }

  if (corre('F101')) {
    console.log('== F-101: elegir comuna con el zoomComuna REAL');
    const cs = h.run('estado.comunas.comunas.filter((c) => c.puntos_inundacion > 0)');
    let sd = 0, tot = 0; const filas = [];
    for (const c of cs) {
      const ctx = h.ctx; ctx.__c = { comuna: c.comuna };
      const cap = ctx.__capturas; cap['#respuesta'] = ctx.__elemento(); cap['#detalle-ficha'] = ctx.__elemento();
      h.run('estado.precisionPos = null; zoomComuna(__c)');
      const txt = L(cap['#respuesta'].innerHTML);
      const t = (txt.match(/^(.*?)📍/) || [null, txt.slice(0, 80)])[1].trim();
      delete cap['#respuesta']; delete cap['#detalle-ficha'];
      tot++; if (/Sin registros/.test(t)) sd++;
      filas.push(`${c.comuna.padEnd(16)} puntos=${String(c.puntos_inundacion).padStart(3)} ${t}`);
    }
    console.log(filas.join('\n'));
    console.log(`  comunas con registros: ${tot}; titular "Sin registros" al elegirlas: ${sd}`);
    console.log(`  comunas totales en estado-comunas: ${h.run('estado.comunas.comunas.length')}`);
  }

  if (corre('F102')) {
    console.log('== F-102: texto compartido en punto dentro de lámina derivada y en borde');
    const [lon, lat] = [-72.6867, -37.78499];
    const r = h.evaluar(lon, lat, null);
    console.log(`  [lamina] titular: ${r.titulo}\n` + h.textoFicha(r, 'x').split('\n').map((s) => '    | ' + s).join('\n'));
    for (const [lo, la] of vecindad(h, 'laminas', [8])) {
      const rb = h.evaluar(lo, la, null); if (!rb.borde) continue;
      console.log(`  [borde] titular: ${rb.titulo}\n` + h.textoFicha(rb, 'x').split('\n').map((s) => '    | ' + s).join('\n')); break;
    }
  }

  if (corre('F105')) {
    console.log('== F-105: borde rebaja alto a medio cuando hay registros graves');
    let n = 0, alto = 0, ej = null;
    for (const capa of ['areasRiesgo', 'laminas']) for (const [lon, lat] of vecindad(h, capa, [3, 8, 15])) {
      const r = h.evaluar(lon, lat, null); if (!r.borde) continue; n++;
      const c300 = r.cerca.filter((c) => c.d <= 300);
      const graves = c300.filter((c) => ['Muy Alto', 'Alto'].includes(c.f.properties.nivel));
      if (graves.length >= 1 || c300.length >= 3) { alto++; if (!ej) ej = { lon, lat, nivel: r.nivel, titulo: r.titulo, graves: graves.length, c300: c300.length }; }
    }
    console.log(`  puntos con borde: ${n}; de ellos con graves>=1 o >=3 en 300 m (alto sin la regla de borde): ${alto}`);
    console.log('  ejemplo', JSON.stringify(ej));
  }

  if (corre('F106')) {
    console.log('== F-106: precisionPos tras consultar() (camino de las sugerencias)');
    h.ctx.__ll = [-72.68, -37.797];
    h.run('estado.precisionPos = 80');
    const antes = h.run('estado.precisionPos');
    await h.run('consultar(__ll[0], __ll[1], "direccion elegida")');
    console.log(`  precisionPos antes=${antes} despues de consultar()=${h.run('estado.precisionPos')}`);
    h.run('estado.precisionPos = null');
  }

  if (corre('F110')) {
    console.log('== F-110: gore calla en el resumen cuando hay un registro lejano');
    let n = 0, ej = null;
    const pts = h.run('estado.puntos.features');
    for (const f of pts) for (const [dx, dy, m] of [[1, 0, 700], [0, 1, 900], [-1, 0, 1100], [0, -1, 1300]]) {
      const [x, y] = f.geometry.coordinates;
      const lon = x + dx * m / (111320 * Math.cos(y * Math.PI / 180)), lat = y + dy * m / 111320;
      const r = h.evaluar(lon, lat, null);
      if (r.nivel === 'bajo' && (r.gore.length || r.enMancha)) {
        n++;
        const pq = L(h.porQue(r));
        if (!ej && !/modelo/.test(pq)) ej = { lon, lat, gore: r.gore[0] && r.gore[0].properties.clase, enMancha: r.enMancha, porQue: pq };
      }
    }
    console.log(`  puntos nivel bajo con gore/mancha: ${n}; ejemplo con porQue que NO menciona modelo: ${JSON.stringify(ej)}`);
  }

  if (corre('F114')) {
    console.log('== F-114: dos láminas superpuestas con distinta incertidumbre/año');
    let sup = 0, difI = 0, difA = 0, ej = null; const vistos = new Set();
    for (const [lon, lat] of vecindad(h, 'laminas', [-1, -3, 1, 3])) {
      const r = h.evaluar(lon, lat, null);
      if (r.laminas.length < 2) continue;
      const k = r.laminas.map((f) => f.properties.origen_lamina + f.properties.clase).sort().join('|');
      if (vistos.has(k)) continue; vistos.add(k); sup++;
      const is = new Set(r.laminas.map((f) => f.properties.incertidumbre_borde_m)), as = new Set(r.laminas.map((f) => f.properties.anio));
      if (is.size > 1) difI++; if (as.size > 1) difA++;
      if (!ej && (is.size > 1 || as.size > 1)) ej = r.laminas.map((f) => [f.properties.clase, f.properties.anio, f.properties.incertidumbre_borde_m]);
    }
    console.log(`  combinaciones distintas con >=2 láminas: ${sup}; con incertidumbre distinta: ${difI}; con año distinto: ${difA}; ejemplo: ${JSON.stringify(ej)}`);
  }

  if (corre('F117')) {
    console.log('== F-117: incertidumbres declaradas > 10 m');
    for (const capa of ['laminas', 'areasRiesgo', 'sar', 'gore']) {
      const v = h.run(`estado.${capa}.features.map((f) => f.properties.incertidumbre_borde_m).filter((x) => x != null)`);
      console.log(`  ${capa}: declaran=${v.length}, max=${v.length ? Math.max(...v) : 'n/a'}, >10: ${v.filter((x) => x > 10).length}`);
    }
  }

  if (corre('F120')) {
    console.log('== F-120: veredicto en el mar dentro del bbox');
    for (const [lon, lat] of [[-73.6, -38.5], [-73.69, -37.4]]) {
      const r = h.evaluar(lon, lat, null);
      console.log(`  (${lon},${lat}) dentroDeRegion=${h.run(`dentroDeRegion(${lon},${lat})`)} -> ${r.nivel}: ${r.titulo}`);
    }
  }
})().catch((e) => { console.error(e); process.exit(2); });
