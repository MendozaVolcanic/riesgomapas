/* fA_harness_evaluar.js : carga web/app.js REAL en Node, con los datos REALES
 * de web/data/, y expone evaluar(), porQue(), textoFicha() y el objeto estado.
 *
 * POR QUÉ. Reimplementar la regla de decisión en Python mediría la copia, no el
 * visor. Este arnés ejecuta el mismo archivo que baja el navegador; sólo se
 * reemplazan el DOM (por un objeto que absorbe todo) y fetch (por lectura de
 * disco). MapLibre no existe acá, así que iniciarMapa() lanza y el propio
 * app.js lo atrapa, igual que en un celular sin WebGL.
 *
 * LAS DOS PREGUNTAS DEL INSTRUMENTO
 *  1. Si evaluar() estuviera roto (no consultara una capa), ¿lo vería? Sí: el
 *     arnés llama la función real; cualquier cambio en web/app.js cambia su
 *     salida. --control lo demuestra consultando un punto conocido dentro del
 *     AR-2a derivado de Angol y exigiendo el titular de la capa derivada.
 *  2. Si el arnés estuviera muerto (app.js no cargó, datos vacíos), ¿se vería
 *     distinto? Sí: cargar() lanza si estado.puntos es null o si cualquiera de
 *     las capas que el visor declara opcionales viene vacía, en vez de seguir
 *     con ceros.
 *
 * Uso como módulo: const { cargar } = require('./fA_harness_evaluar.js');
 *                  const ctx = await cargar(); ctx.evaluar(lon, lat)
 * Uso directo:     node tools/auditoria/fA_harness_evaluar.js --control
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const RAIZ = path.resolve(__dirname, '..', '..');
const WEB = path.join(RAIZ, 'web');

function stub() {
  // Un objeto que acepta cualquier propiedad, llamada o asignación.
  const f = function () { return p; };
  const p = new Proxy(f, {
    get(t, k) {
      if (k === Symbol.toPrimitive) return () => '';
      if (k === 'then') return undefined;
      if (k === 'textContent' || k === 'innerHTML' || k === 'value') return t['_' + k] || '';
      if (k === 'checked') return false;
      if (k === 'style') return {};
      if (k === 'classList') return { add() {}, remove() {}, toggle() {}, contains() { return false; } };
      return p;
    },
    set(t, k, v) { t['_' + String(k)] = v; return true; },
    apply() { return p; },
  });
  return p;
}

async function cargar() {
  const capturas = {};   // selector -> elemento que guarda lo escrito
  const elemento = () => ({ _h: '', set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h; },
    textContent: '', classList: { add() {}, remove() {}, toggle() {} }, focus() {},
    addEventListener() {}, setAttribute() {}, removeAttribute() {}, querySelectorAll: () => [] });
  const doc = {
    querySelector: (s) => capturas[s] || stub(),
    querySelectorAll: () => [],
    getElementById: () => stub(),
    createElement: () => elemento(),
    addEventListener() {},
    body: stub(), documentElement: stub(),
  };
  const ctx = {
    __capturas: capturas, __elemento: elemento,
    console,
    document: doc,
    window: {},
    navigator: {},
    location: { protocol: 'file:', hash: '' },
    addEventListener() {}, history: { replaceState() {} },
    matchMedia: () => ({ matches: false }),
    setTimeout, clearTimeout,
    AbortController,
    Event: function () {},
    fetch: async (ruta) => {
      const f = path.join(WEB, ruta);
      if (!fs.existsSync(f)) return { ok: false, status: 404, json: async () => ({}) };
      const txt = fs.readFileSync(f, 'utf8');
      return { ok: true, status: 200, json: async () => JSON.parse(txt) };
    },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  const src = fs.readFileSync(path.join(WEB, 'app.js'), 'utf8');
  vm.runInContext(src, ctx, { filename: 'web/app.js' });
  // inicio() es async y corre al cargar; se espera a que estado.puntos exista.
  for (let i = 0; i < 400; i++) {
    const ok = vm.runInContext('estado.puntos && estado.laminas && estado.gore && estado.sar && estado.sarCobertura && estado.campamentos && estado.areasRiesgo && estado.jrc ? 1 : 0', ctx);
    if (ok) break;
    await new Promise((r) => setTimeout(r, 25));
  }
  const vacias = vm.runInContext(`['puntos','laminas','gore','sar','sarCobertura','campamentos','areasRiesgo','jrc']
    .filter((k) => !estado[k] || !estado[k].features || !estado[k].features.length)`, ctx);
  if (vacias.length) throw new Error('ARNÉS MUERTO: capas vacías o no cargadas: ' + vacias.join(','));
  const api = {
    ctx,
    run: (code) => vm.runInContext(code, ctx),
    evaluar: (lon, lat, precision = null) => {
      ctx.__a = [lon, lat, precision];
      return vm.runInContext('estado.precisionPos = __a[2]; evaluar(__a[0], __a[1])', ctx);
    },
    porQue: (res) => { ctx.__r = res; return vm.runInContext('porQue(__r)', ctx); },
    textoFicha: (res, etiqueta = 'punto') => {
      ctx.__r = res; ctx.__e = etiqueta;
      return vm.runInContext('estado.ultimo = { res: __r, etiqueta: __e, lon: 0, lat: 0 }; textoFicha()', ctx);
    },
    renderDetalle: (res, lon, lat) => {
      // render() escribe en #detalle-ficha y resumen() en #respuesta: se
      // capturan esos dos elementos y se devuelve lo escrito.
      capturas['#detalle-ficha'] = elemento();
      capturas['#respuesta'] = elemento();
      ctx.__r = res; ctx.__ll = [lon, lat];
      vm.runInContext("render(__r, 'punto', __ll[0], __ll[1])", ctx);
      const out = { detalle: capturas['#detalle-ficha'].innerHTML, resumen: capturas['#respuesta'].innerHTML };
      delete capturas['#detalle-ficha']; delete capturas['#respuesta'];
      return out;
    },
  };
  return api;
}

module.exports = { cargar };

if (require.main === module) {
  (async () => {
    const h = await cargar();
    const n = h.run('[estado.puntos.features.length, estado.laminas.features.length, estado.gore.features.length, estado.sar.features.length, estado.areasRiesgo.features.length, estado.campamentos.features.length]');
    console.log('capas cargadas (puntos, laminas, gore, sar, areasRiesgo, campamentos):', JSON.stringify(n));
    if (process.argv.includes('--control')) {
      // Punto del caso F-01 de la auditoría 2026-09-06: dentro del AR-2a derivado.
      const r = h.evaluar(-72.6867, -37.78499);
      const ok = r.laminas.length > 0 && /plan regulador/.test(r.titulo);
      console.log('CONTROL Angol AR-2a derivado:', r.nivel, '|', r.titulo, '| laminas', r.laminas.length, ok ? 'OK' : 'FALLA');
      // Control negativo: el mar frente a Saavedra no puede tener capas dentro.
      const m = h.evaluar(-73.6, -38.8);
      console.log('CONTROL mar:', m.nivel, '|', m.titulo);
      process.exit(ok ? 0 : 1);
    }
  })().catch((e) => { console.error(e); process.exit(2); });
}
