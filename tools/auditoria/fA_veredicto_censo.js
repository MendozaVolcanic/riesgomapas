/* fA_veredicto_censo.js : corre el evaluar() REAL sobre los puntos del censo que
 * prepara fA_veredicto_censo.py y cuenta personas por defecto de la lógica.
 *
 * LAS DOS PREGUNTAS DEL INSTRUMENTO
 *  1. Si el defecto no existiera, ¿la cuenta daría cero? Sí: cada defecto se
 *     clasifica con `clasificar()` a partir de la salida de evaluar() y porQue().
 *     --control inyecta en `estado` un caso sintético de cada defecto (en el mar
 *     frente a Saavedra, donde no hay ninguna capa) y exige que `clasificar()`
 *     lo marque; si alguno no se marca, sale con código 1.
 *  2. Si el instrumento estuviera muerto, ¿se vería distinto? El arnés lanza si
 *     alguna capa no cargó, y este script aborta si evalúa menos puntos de los
 *     que recibió.
 *
 * Uso: node tools/auditoria/fA_veredicto_censo.js PUNTOS.json
 *      node tools/auditoria/fA_veredicto_censo.js --control
 */
'use strict';
const fs = require('fs');
const { cargar } = require('./fA_harness_evaluar.js');

const MEDIAS = new Set(['Medio', 'Susceptibilidad media']);

function decisor(r) {
  if (r.sar.length) return 'B observado';
  if (r.areas.length) return 'A normativo MINVU';
  if (r.laminas.length) return 'A derivado';
  if (r.borde) return 'banda de borde';
  if (/registro de inundaciones$/.test(r.titulo)) return 'D puntos (alto)';
  if (/cerca$/.test(r.titulo)) return 'D puntos (medio)';
  if (/cierta distancia$/.test(r.titulo)) return 'D puntos (bajo)';
  if (/modelo/.test(r.titulo)) return 'C modelo (sin dato)';
  return 'nada (sin dato)';
}

function clasificar(h, r, p) {
  const out = [];
  const graves = r.cerca.filter((c) => c.d <= 300 && ['Muy Alto', 'Alto'].includes(c.f.properties.nivel));
  const en300 = r.cerca.filter((c) => c.d <= 300).length;
  const dec = decisor(r);
  if (dec === 'banda de borde' && (graves.length >= 1 || en300 >= 3)) out.push('D1 borde rebaja alto->medio');
  if (dec === 'A derivado' && r.laminas.every((f) => MEDIAS.has(f.properties.clase))) out.push('D2 clase media -> nivel alto');
  if (r.campamentos.length && r.nivel !== 'alto') out.push('D3 campamento en AR sin nivel alto');
  if (r.campamentos.length && r.nivel === 'sindato') out.push('D3b campamento en AR con «sin registros»');
  const gMax = r.gore.some((f) => f.properties.clase === 'MAXIMA');
  if (gMax && (dec === 'D puntos (bajo)' || dec === 'D puntos (medio)')) {
    const pq = h.porQue(r);
    if (!/modelo/.test(pq)) out.push('D4 GORE máxima callada en el resumen');
  }
  if (r.enCoberturaSar && !r.sar.length && p.apto === false) out.push('D5 «sí miró» en terreno que el radar excluye');
  if (p.geoide && p.geoide.length && !r.areas.length && !r.laminas.length) {
    out.push('D6 dentro de AR hídrica GeoIDE Angol, sin capa A en el visor');
    if (p.geoide.includes('AR-2a')) out.push('D6a ... y es AR-2a inundable');
  }
  if (p.geoide && p.geoide.includes('AR-2b') && !p.geoide.includes('AR-2a') && r.laminas.length)
    out.push('D7 AR-2b anegamiento GeoIDE, el visor lo titula inundación');
  return { dec, defectos: out };
}

function fmt(n) { return n.toLocaleString('es-CL'); }

async function principal(ruta) {
  const h = await cargar();
  const pts = JSON.parse(fs.readFileSync(ruta, 'utf8'));
  const porNivel = {}, porDec = {}, porDef = {}, ejemplos = {};
  let evaluados = 0, totalN = 0;
  const t0 = Date.now();
  for (const p of pts) {
    const r = h.evaluar(p.lon, p.lat, null);
    evaluados++; totalN += p.n;
    const { dec, defectos } = clasificar(h, r, p);
    porNivel[r.nivel] = (porNivel[r.nivel] || 0) + p.n;
    porDec[dec] = porDec[dec] || { n: 0, u: 0 }; porDec[dec].n += p.n; porDec[dec].u++;
    for (const d of defectos) {
      porDef[d] = porDef[d] || { n: 0, u: 0, rio: 0, comunas: {} };
      porDef[d].n += p.n; porDef[d].u++; porDef[d].rio += p.rio || 0;
      porDef[d].comunas[p.comuna] = (porDef[d].comunas[p.comuna] || 0) + p.n;
      if (!ejemplos[d] || p.n > ejemplos[d].n) ejemplos[d] = { lon: +p.lon.toFixed(5), lat: +p.lat.toFixed(5), n: p.n, comuna: p.comuna, titulo: r.titulo, nivel: r.nivel };
    }
  }
  if (evaluados !== pts.length) throw new Error('INSTRUMENTO MUERTO: no se evaluaron todos');
  console.log(`evaluados ${evaluados} puntos, ${fmt(totalN)} personas, ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  console.log('\nPERSONAS POR NIVEL:', JSON.stringify(porNivel));
  console.log('\nPOR CAPA QUE DECIDE (personas / unidades):');
  for (const [k, v] of Object.entries(porDec).sort((a, b) => b[1].n - a[1].n)) console.log(`  ${k.padEnd(22)} ${fmt(v.n).padStart(10)} / ${v.u}`);
  console.log('\nDEFECTOS (personas / unidades / personas con agua de río):');
  for (const [k, v] of Object.entries(porDef).sort()) {
    const top = Object.entries(v.comunas).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([c, n]) => `${c} ${fmt(n)}`).join(', ');
    console.log(`  ${k}: ${fmt(v.n)} / ${v.u} / ${fmt(v.rio)}  [${top}]`);
    console.log(`     ejemplo: ${JSON.stringify(ejemplos[k])}`);
  }
}

async function control() {
  const h = await cargar();
  const lon = -73.6, lat = -38.8;   // mar frente a Saavedra: ninguna capa
  const d = 0.001;
  const cuadro = (x, y, s) => ({ type: 'Polygon', coordinates: [[[x - s, y - s], [x + s, y - s], [x + s, y + s], [x - s, y + s], [x - s, y - s]]] });
  const casos = [];
  const base = h.evaluar(lon, lat, null);
  casos.push(['base sin defectos', clasificar(h, base, { apto: true }).defectos.length === 0]);

  // D1: área MINVU sintética, punto 5 m fuera del borde, punto crítico Alto a 100 m.
  h.ctx.__g = cuadro(lon, lat, d);
  h.run(`estado.areasRiesgo.features.push({type:'Feature',geometry:__g,properties:{comuna:'X'}});
         estado.puntos.features.push({type:'Feature',geometry:{type:'Point',coordinates:[${lon + d + 0.0012}, ${lat}]},properties:{nivel:'Alto',comuna:'X'}});`);
  const fuera = lon + d + 5 / (111320 * Math.cos(lat * Math.PI / 180));
  const r1 = h.evaluar(fuera, lat, null);
  casos.push(['D1 detectado', clasificar(h, r1, { apto: true }).defectos.includes('D1 borde rebaja alto->medio')]);
  h.run('estado.areasRiesgo.features.pop(); estado.puntos.features.pop();');

  // D2: lámina sintética de clase Medio.
  h.run(`estado.laminas.features.push({type:'Feature',geometry:__g,properties:{clase:'Medio',anio:'2013',comuna:'X'}});`);
  const r2 = h.evaluar(lon, lat, null);
  casos.push(['D2 detectado', clasificar(h, r2, { apto: true }).defectos.includes('D2 clase media -> nivel alto')]);
  h.run('estado.laminas.features.pop();');

  // D3: campamento sintético en área de riesgo.
  h.run(`estado.campamentos.features.push({type:'Feature',geometry:__g,properties:{nombre:'X',hogares:10,comuna:'X',tipo_riesgo:'Inundación',anio:2024}});`);
  const r3 = h.evaluar(lon, lat, null);
  casos.push(['D3b detectado', clasificar(h, r3, { apto: true }).defectos.includes('D3b campamento en AR con «sin registros»')]);
  h.run('estado.campamentos.features.pop();');

  // D5: cobertura SAR sintética sobre terreno no apto.
  h.run(`estado.sarCobertura.features.push({type:'Feature',geometry:__g,properties:{fecha_observacion:'2026-08-03'}});`);
  const r5 = h.evaluar(lon, lat, null);
  casos.push(['D5 detectado', clasificar(h, r5, { apto: false }).defectos.includes('D5 «sí miró» en terreno que el radar excluye')]);
  casos.push(['D5 no se marca si apto', !clasificar(h, r5, { apto: true }).defectos.some((x) => x.startsWith('D5'))]);
  h.run('estado.sarCobertura.features.pop();');

  // D6: rótulo GeoIDE sintético.
  casos.push(['D6 detectado', clasificar(h, base, { apto: true, geoide: ['AR-2a'] }).defectos.includes('D6a ... y es AR-2a inundable')]);

  let ok = true;
  for (const [n, v] of casos) { console.log(`  ${v ? 'OK   ' : 'FALLA'} ${n}`); ok = ok && v; }
  console.log(ok ? 'CONTROL: el instrumento ve cada defecto fabricado' : 'CONTROL FALLIDO');
  process.exit(ok ? 0 : 1);
}

if (process.argv.includes('--control')) control().catch((e) => { console.error(e); process.exit(2); });
else principal(process.argv[2]).catch((e) => { console.error(e); process.exit(2); });
