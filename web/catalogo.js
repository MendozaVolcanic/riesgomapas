/* Catálogo de documentos de planificación con cartografía de riesgo.
 *
 * Criterio de presentación: primero las comunas con más láminas encontradas, y
 * dentro de cada comuna primero los documentos que efectivamente traen mapas.
 * Un listado ordenado alfabéticamente escondería el hallazgo útil bajo decenas
 * de documentos de trámite.
 */
'use strict';

let CATALOGO = null;

const $ = (s) => document.querySelector(s);

function esc(t) {
  return String(t ?? '').replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function normaliza(t) {
  return (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

function nombreLegible(archivo) {
  // Los nombres vienen del expediente: "04_Anteproyecto-Planos_PRC_Vilcún.pdf.pdf"
  return archivo
    .replace(/\.pdf(\.pdf)?$/i, '')
    .replace(/^\d+_/, '')
    .replace(/_/g, ' ')
    .trim();
}

function tarjetaLamina(l, urlDoc) {
  const g = l.georreferenciada;
  const medida = l.cm ? `${l.cm[0]}×${l.cm[1]} cm` : '';
  const tipo = l.tipo === 'plano' ? `plano de plóter ${medida}` : 'figura en el informe';
  // El fragmento #page=N lo entienden los visores de PDF (navegador incluido):
  // abre el documento directamente en la página del mapa. Es la diferencia entre
  // "está en este PDF de 300 páginas" y "está acá".
  let html = `<li class="lamina">
    <a class="pag" href="${esc(urlDoc)}#page=${l.pagina}" rel="noopener"
       title="Abre el PDF oficial en esa página">pág. ${l.pagina} →</a>
    <span class="tipo">${esc(tipo)}</span>
    <span class="terminos">${esc((l.terminos || []).slice(0, 3).join(' · '))}</span>`;
  if (g) {
    html += `<span class="geo" title="Georreferenciada automáticamente desde la grilla UTM impresa">
      ✓ georreferenciada · ${g.resolucion_m_px} m/px · error ${g.rmse_loo_m} m</span>`;
  }
  return html + `</li>`;
}

function tarjetaDocumento(d) {
  const conMapa = d.laminas.length > 0;
  // Los documentos bajados de sitios municipales no pasaron por Evaluación
  // Ambiental Estratégica, así que no tienen fecha de ingreso. Si se arma la
  // frase igual, queda "ingresó a evaluación ambiental el · estado: ..." —
  // cortada a la mitad. Cada dato se agrega sólo si existe.
  const meta = [esc(d.procedimiento), esc(d.instrumento)];
  if (d.fecha_ingreso_eae) {
    meta.push(`ingresó a evaluación ambiental el ${esc(d.fecha_ingreso_eae)}`);
  }
  if (d.estado_eae) meta.push(esc(d.estado_eae));

  let html = `<div class="doc ${conMapa ? 'con-mapa' : ''}">
    <a class="doc-titulo" href="${esc(d.url)}" rel="noopener">${esc(nombreLegible(d.archivo))}</a>
    <p class="doc-meta">${meta.filter(Boolean).join(' · ')}</p>`;
  if (conMapa) {
    html += `<p class="doc-hallazgo"><strong>${d.laminas.length}</strong>
             ${d.laminas.length === 1 ? 'lámina con contenido de inundación' :
                                        'láminas con contenido de inundación'}
             — toca el número de página para abrir el PDF ahí mismo:</p>
             <ul class="laminas">${d.laminas.map((l) => tarjetaLamina(l, d.url)).join('')}</ul>`;
  } else {
    html += `<p class="doc-meta incert">Sin cartografía de inundación detectada.</p>`;
  }
  return html + `</div>`;
}

function render(filtro = '') {
  const f = normaliza(filtro);
  const comunas = CATALOGO.comunas.filter((c) => !f || normaliza(c.comuna).includes(f));
  const cont = $('#lista');

  const totLam = comunas.reduce((a, c) => a + c.n_laminas, 0);
  const totDoc = comunas.reduce((a, c) => a + c.n_documentos, 0);
  $('#resumen').textContent =
    `${comunas.length} comunas · ${totDoc} documentos · ${totLam} láminas con contenido de inundación`;

  if (!comunas.length) {
    cont.innerHTML = `<p class="nota">No hay documentos indexados para esa comuna.
      Prueba con otra, o revisa la advertencia al final de la página.</p>`;
    return;
  }

  cont.innerHTML = comunas.map((c) => `
    <details class="comuna" ${comunas.length <= 3 ? 'open' : ''}>
      <summary>
        <span class="c-nombre">${esc(c.comuna)}</span>
        <span class="c-cifras">${c.n_laminas} láminas · ${c.n_documentos} documentos${
          c.n_georreferenciadas ? ` · ${c.n_georreferenciadas} georreferenciadas` : ''}</span>
      </summary>
      ${c.documentos.map(tarjetaDocumento).join('')}
    </details>`).join('');
}

async function inicio() {
  try {
    const r = await fetch('data/catalogo-documentos.json');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    CATALOGO = await r.json();
  } catch (e) {
    $('#lista').innerHTML = `<p class="nota">No se pudo cargar el catálogo (${esc(e.message)}).</p>`;
    return;
  }
  const p = CATALOGO.procedencia || {};
  $('#sello-datos').textContent =
    `${p.fuente || ''} · índice generado ${(p.generado || '').slice(0, 10)}`;
  render();
  $('#q').addEventListener('input', (e) => render(e.target.value));

  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
}

inicio();
