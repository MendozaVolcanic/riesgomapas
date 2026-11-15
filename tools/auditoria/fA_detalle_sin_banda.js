/* fA_detalle_sin_banda.js : cuando el titular es «Estás justo en el borde…», ¿la
 * pestaña de detalle (la que se imprime como PDF) explica la banda, o dice
 * «no cae dentro» sin más?
 *
 * POR QUÉ. index.html ofrece «Imprimir o guardar como PDF» la pestaña de
 * detalle «para mostrárselo a quien te vende el terreno». La explicación de la
 * banda de borde vive sólo en porQue(), que va en el resumen y no en el
 * detalle. Si es así, el PDF lleva el titular de borde y, debajo, la frase
 * negativa de la capa normativa, sin distancia ni incertidumbre.
 *
 * Método: se buscan puntos reales a 3-15 m por fuera de cada área del MINVU y
 * de cada polígono derivado, se corre evaluar() y render() reales, y en los
 * que salen con titular de borde se mira el HTML del detalle.
 *
 * LAS DOS PREGUNTAS DEL INSTRUMENTO
 *  1. Si el detalle sí explicara la banda, ¿lo vería? Sí: se busca «metros del
 *     borde» o «±» en el detalle. CONTROL positivo: en un punto DENTRO de un
 *     polígono derivado el detalle sí trae «±» (lo imprime el bloque A
 *     derivado); si el control no lo encuentra, el detector está roto.
 *  2. Si el instrumento estuviera muerto, ¿se vería distinto? Si no aparece
 *     ningún punto con titular de borde, sale SIN DATO, no «0 defectos».
 *
 * Uso: node tools/auditoria/fA_detalle_sin_banda.js
 */
'use strict';
const { cargar } = require('./fA_harness_evaluar.js');
const L = (s) => String(s).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');

(async () => {
  const h = await cargar();
  let n = 0, sinExplicar = 0, conNegativa = 0, ejemplo = null;
  for (const capa of ['areasRiesgo', 'laminas']) {
    const nf = h.run(`estado.${capa}.features.length`);
    for (let i = 0; i < nf; i++) {
      const g = h.run(`estado.${capa}.features[${i}].geometry`);
      const anillo = g.type === 'Polygon' ? g.coordinates[0] : g.coordinates[0][0];
      const v = anillo[0];
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        for (const m of [3, 8, 15]) {
          const lat = v[1] + dy * m / 111320, lon = v[0] + dx * m / (111320 * Math.cos(v[1] * Math.PI / 180));
          const r = h.evaluar(lon, lat, null);
          if (!r.borde) continue;
          n++;
          const det = L(h.renderDetalle(r, lon, lat).detalle);
          const explica = /metros del borde|adentro y afuera|±/.test(det);
          if (!explica) sinExplicar++;
          const neg = /Este punto no cae dentro de un área de riesgo/.test(det);
          if (!explica && neg) { conNegativa++; if (!ejemplo) ejemplo = { lon: +lon.toFixed(6), lat: +lat.toFixed(6), d: +r.borde.d.toFixed(1), capa: r.borde.capa, titulo: r.titulo }; }
          break;
        }
      }
    }
  }
  // Control positivo.
  const c = h.evaluar(-72.6867, -37.78499, null);
  const ctrl = /metros del borde|adentro y afuera|±/.test(L(h.renderDetalle(c, -72.6867, -37.78499).detalle));
  console.log(`CONTROL (dentro de derivado, el detalle trae «±»): ${ctrl ? 'OK' : 'DETECTOR ROTO'}`);
  if (!n) { console.log('SIN DATO: ningún punto con titular de borde'); process.exit(2); }
  console.log(`puntos con titular de borde: ${n}`);
  console.log(`  detalle SIN explicación de la banda: ${sinExplicar}`);
  console.log(`  ... y además con «Este punto no cae dentro de un área de riesgo»: ${conNegativa}`);
  console.log(`  ejemplo: ${JSON.stringify(ejemplo)}`);
  process.exit(ctrl ? 0 : 2);
})().catch((e) => { console.error(e); process.exit(2); });
