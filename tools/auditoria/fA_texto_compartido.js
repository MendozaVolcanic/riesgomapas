/* fA_texto_compartido.js : ¿el texto que se reenvía (textoFicha) nombra la
 * evidencia que decidió el titular?
 *
 * POR QUÉ. El titular viaja en mayúsculas en la primera línea del texto que se
 * comparte por WhatsApp. Si la capa que lo decidió no aparece después, quien lo
 * recibe lee «ESTÁS EN UN ÁREA DE RIESGO…» sin fuente, sin año y sin la
 * advertencia de que el trazado es derivado. Se consultan casos reales, uno por
 * capa que puede decidir, con el evaluar() y el textoFicha() reales.
 *
 * LAS DOS PREGUNTAS DEL INSTRUMENTO
 *  1. Si textoFicha nombrara todas las capas, ¿esto daría todo OK? Sí, y hay
 *     controles positivos: los casos B (satélite) y A MINVU, que textoFicha sí
 *     cubre, tienen que salir OK. Si salieran FALTA, el detector está mal.
 *  2. Si el instrumento estuviera muerto, ¿se vería distinto? Si un caso no
 *     encuentra su punto (la capa no tiene features que cumplan), sale
 *     SIN DATO, nunca OK.
 *
 * Uso: node tools/auditoria/fA_texto_compartido.js
 */
'use strict';
const { cargar } = require('./fA_harness_evaluar.js');

const limpiar = (s) => String(s).replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();

(async () => {
  const h = await cargar();
  const { ctx } = h;
  // Busca un punto interior de un feature por grilla dentro de su caja.
  const interior = (capa, filtro, extra = () => true) => {
    const n = h.run(`estado.${capa}.features.length`);
    for (let i = 0; i < n; i++) {
      const f = h.run(`estado.${capa}.features[${i}]`);
      if (!filtro(f)) continue;
      const anillo = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates[0][0];
      const xs = anillo.map((c) => c[0]), ys = anillo.map((c) => c[1]);
      const [w, e, s, nn] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
      for (let a = 1; a < 8; a++) for (let b = 1; b < 8; b++) {
        const lon = w + (e - w) * a / 8, lat = s + (nn - s) * b / 8;
        const r = h.evaluar(lon, lat, null);
        if (extra(r, f)) return { lon, lat, r };
      }
    }
    return null;
  };
  const casos = [
    ['A derivado AR-2a (efecto legal)', () => interior('laminas', (f) => f.properties.clase === 'AR-2a', (r) => r.laminas.length && !r.areas.length && !r.sar.length),
      /l[aá]mina|derivad|trazado|documento comunal|estudio/i, false],
    ['A derivado clase Medio (estudio 2013)', () => interior('laminas', (f) => f.properties.clase === 'Medio', (r) => r.laminas.length && r.laminas.every((x) => x.properties.clase === 'Medio') && !r.areas.length && !r.sar.length),
      /l[aá]mina|derivad|trazado|estudio/i, false],
    ['GORE máxima sin puntos (modelo)', () => interior('gore', (f) => f.properties.clase === 'MAXIMA', (r) => r.nivel === 'sindato' && r.gore.length),
      /modelo|GORE|Gobierno Regional/i, false],
    ['Campamento en área de riesgo', () => interior('campamentos', () => true, (r) => r.campamentos.length && !r.areas.length && !r.laminas.length),
      /campamento/i, false],
    ['CONTROL + B observado', () => interior('sar', () => true, (r) => r.sar.length),
      /sat[eé]lite/i, true],
    ['CONTROL + A MINVU', () => interior('areasRiesgo', () => true, (r) => r.areas.length && !r.sar.length),
      /Plan Regulador/i, true],
  ];
  let detectorSano = true;
  for (const [nombre, buscar, patron, esControl] of casos) {
    const c = buscar();
    if (!c) { console.log(`SIN DATO  ${nombre}: no se encontró punto`); continue; }
    const t = h.textoFicha(c.r, 'punto de prueba');
    const cuerpo = t.split('\n').slice(1).join('\n');  // sin la línea del titular
    const ok = patron.test(cuerpo);
    if (esControl && !ok) detectorSano = false;
    console.log(`${ok ? 'NOMBRA ' : 'FALTA  '} ${nombre} @ ${c.lon.toFixed(5)}, ${c.lat.toFixed(5)}`);
    console.log(`   nivel=${c.r.nivel} titular="${c.r.titulo}"`);
    console.log(`   por qué (pantalla): ${limpiar(h.porQue(c.r)).slice(0, 200)}`);
    console.log('   texto compartido:\n      ' + t.split('\n').join('\n      '));
  }
  // F-07 (2026-09-06), segunda mitad: ¿el texto dice cuántos puntos hay cuando recorta a 3?
  // Se elige el punto crítico con más vecinos a 1,5 km: es donde el recorte pesa.
  let r = null;
  for (const [x, y] of h.run('estado.puntos.features.map((f) => f.geometry.coordinates)')) {
    const q = h.evaluar(x, y, null);
    if (!r || q.cerca.length > r.cerca.length) { r = q; r.__ll = [x, y]; }
  }
  console.log(`\npunto con más registros a 1,5 km: ${r.__ll.join(', ')}`);
  const t = h.textoFicha(r, 'punto de prueba');
  console.log(`\nRECORTE: puntos a ≤1500 m = ${r.cerca.length}; líneas «•» de puntos en el texto = ${(t.match(/^• \d+ m/mg) || []).length}; ¿dice el total? ${new RegExp(`\\b${r.cerca.length}\\b`).test(t)}`);
  console.log(detectorSano ? 'controles positivos OK' : 'DETECTOR ROTO: un control positivo dio FALTA');
  process.exit(detectorSano ? 0 : 2);
})().catch((e) => { console.error(e); process.exit(2); });
