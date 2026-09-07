"""Arnés de USO: consulta puntos reales en el visor y guarda lo que la persona ve.

Preguntas del instrumento:
 (1) Si el veredicto estuviera roto (no se dibuja, texto vacío, capa que no
     entra), ¿fallaría?  Sí: cada consulta espera por CONTENIDO (la etiqueta del
     punto en #respuesta) y guarda el texto crudo; un veredicto vacío o el
     anterior se ve en el archivo. Además se produce a propósito un punto que
     SÍ cae en cada capa y se comprueba que la medida lo ve (control positivo).
 (2) Si el instrumento estuviera muerto, ¿se vería distinto?  Sí: no habría
     archivos en evidencia_uso/ ni JSON de resultados; y el control positivo
     (Collipulli dentro de área MINVU) tiene que decir «cae dentro».

Uso: python tools/auditoria/uso_veredicto_por_punto.py  (sirve web/ en :8791)
"""
import http.server
import io
import json
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
RAIZ = Path(__file__).resolve().parents[2]
WEB = RAIZ / 'web'
EVID = RAIZ / 'tools' / 'auditoria' / 'evidencia_uso'
EVID.mkdir(exist_ok=True)
PUERTO = 8791


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(WEB), **k)

    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(('127.0.0.1', PUERTO), H)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{PUERTO}'

R = {}  # resultados


def guardar():
    (EVID / 'resultados.json').write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding='utf-8')

JS_EVAL = """([lon,lat]) => { const r = evaluar(lon, lat);
  return {nivel:r.nivel, titulo:r.titulo, areas:r.areas.length, sar:r.sar.length,
          cerca:r.cerca.length, gore:r.gore.length, enMancha:r.enMancha,
          lam: poligonosQueContienen(lon, lat, estado.laminas).length,
          areasTipo: r.areas.map(a=>a.properties.tipo_hidrico)}; }"""


def consultar(page, nombre, lon, lat, etiqueta):
    page.evaluate("([lon,lat,e]) => consultar(lon, lat, e)", [lon, lat, etiqueta])
    page.wait_for_function(
        "(e) => document.querySelector('#respuesta').innerText.includes(e)",
        arg=etiqueta, timeout=8000)
    corto = page.locator('#respuesta').inner_text()
    largo = page.locator('#detalle-ficha').inner_text()
    compartido = page.evaluate("() => estado.ultimo ? textoFicha() : null")
    nivel = page.evaluate(
        "() => { const v = document.querySelector('#respuesta .veredicto'); return v ? v.className : null; }")
    comuna = page.evaluate(
        "([lon,lat]) => { const c = comunaDe(null, lon, lat); return c ? [c.comuna, c._km] : null; }",
        [lon, lat])
    ev = page.evaluate(JS_EVAL, [lon, lat])
    (EVID / f'{nombre}.txt').write_text(
        f'PUNTO {nombre} lon={lon} lat={lat}\nNIVEL CSS: {nivel}\n'
        f'COMUNA (comunaDe): {comuna}\nEVALUAR: {json.dumps(ev, ensure_ascii=False)}\n\n'
        f'=== #respuesta ===\n{corto}\n\n=== #detalle-ficha ===\n{largo}\n\n'
        f'=== textoFicha() (lo que se comparte) ===\n{compartido}\n', encoding='utf-8')
    page.screenshot(path=str(EVID / f'{nombre}.png'), full_page=False)
    R[nombre] = {'lon': lon, 'lat': lat, 'nivel': nivel, 'comuna': comuna, 'evaluar': ev,
                 'corto': corto, 'compartido': compartido, 'largo_len': len(largo)}
    print(f'--- {nombre}: nivel={nivel} comuna={comuna} eval={json.dumps(ev, ensure_ascii=False)}')
    return corto, largo, compartido


def centroide_que_cae(page, coleccion, filtro_js, extra_js='[]'):
    """Centroide del primer polígono de `coleccion` que cumple `filtro_js` y que
    de verdad contiene su propio centroide (control: se verifica con la misma
    función que usa el visor)."""
    return page.evaluate(f"""() => {{
      for (const f of {coleccion}.features) {{
        const p = f.properties;
        if (!({filtro_js})) continue;
        const an = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates[0][0];
        let x=0,y=0; for (const [a,b] of an) {{x+=a;y+=b;}} x/=an.length; y/=an.length;
        if (poligonosQueContienen(x, y, {coleccion}).length) return [x, y, ...({extra_js})];
      }} return null; }}""")


with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    ctx = nav.new_context(viewport={'width': 1280, 'height': 900},
                          geolocation={'longitude': -72.5904, 'latitude': -38.7359},
                          permissions=['geolocation'])
    page = ctx.new_page()
    errores = []
    page.on('pageerror', lambda e: errores.append(str(e)))
    page.goto(BASE + '/')
    page.wait_for_function("() => !!estado.puntos && !!estado.laminas && !!estado.areasRiesgo", timeout=60000)
    page.wait_for_function("() => estado.mapa && estado.mapa.isStyleLoaded()", timeout=60000)

    # 1. Collipulli dentro de un área MINVU fluvial (control positivo capa A)
    pA = centroide_que_cae(page, 'estado.areasRiesgo',
                           "p.comuna === 'Collipulli' && p.tipo_hidrico === 'fluvial'", '[p.clasificacion]')
    print('área Collipulli elegida:', pA)
    consultar(page, '01_collipulli_area_minvu', pA[0], pA[1], 'Auditoría Collipulli área')

    # 2. Angol dentro de una lámina vectorizada y FUERA del vectorial MINVU
    pL = page.evaluate("""() => {
      for (const f of estado.laminas.features) {
        if (f.properties.comuna !== 'ANGOL') continue;
        const an = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates[0][0];
        let x=0,y=0; for (const [a,b] of an) {x+=a;y+=b;} x/=an.length; y/=an.length;
        if (poligonosQueContienen(x, y, estado.laminas).length && !poligonosQueContienen(x, y, estado.areasRiesgo).length)
          return [x, y, f.properties.clase, f.properties.amenaza, f.properties.anio];
      } return null; }""")
    print('lámina elegida:', pL)
    consultar(page, '02_angol_lamina_vectorizada', pL[0], pL[1], 'Auditoría Angol lámina')

    # 3-7. Padre Las Casas (plaza), Temuco (plaza), mar, fuera de región, sin dato
    consultar(page, '03_padre_las_casas', -72.5945, -38.7636, 'Auditoría Padre Las Casas')
    consultar(page, '04_temuco_plaza', -72.5904, -38.7359, 'Auditoría Temuco plaza')
    consultar(page, '05_mar_frente_a_saavedra', -73.55, -38.90, 'Auditoría mar')
    consultar(page, '06_santiago_fuera', -70.65, -33.44, 'Auditoría Santiago')
    consultar(page, '07_sin_dato_nororiente', -71.0, -37.5, 'Auditoría sin dato')

    # 8. Área MINVU NO fluvial (litoral / anegamiento): ¿qué titular sale?
    pN = centroide_que_cae(page, 'estado.areasRiesgo', "p.tipo_hidrico !== 'fluvial'",
                           '[p.tipo_hidrico, p.comuna]')
    print('área no fluvial elegida:', pN)
    consultar(page, '08_area_no_fluvial', pN[0], pN[1], 'Auditoría área no fluvial')

    # 9. Sugerencia de comuna -> zoomComuna (qué punto se evalúa)
    page.evaluate("() => zoomComuna(estado.comunas.comunas.find(c => c.comuna === 'ANGOL'))")
    page.wait_for_function(
        "() => document.querySelector('#respuesta').innerText.includes('centro de los registros')", timeout=8000)
    R['09_sugerencia_comuna_angol'] = page.locator('#respuesta').inner_text()
    (EVID / '09_sugerencia_comuna_angol.txt').write_text(R['09_sugerencia_comuna_angol'], encoding='utf-8')
    print('--- 09 sugerencia comuna:', R['09_sugerencia_comuna_angol'][:200].replace('\n', ' | '))

    # 10. Geolocalización dentro (Temuco) y fuera (Santiago); y denegada
    page.click('#btn-ubicacion')
    page.wait_for_function(
        "() => document.querySelector('#respuesta').innerText.includes('Tu ubicación actual')", timeout=8000)
    R['10_geo_dentro'] = {'estado': page.locator('#estado').inner_text(),
                          'corto': page.locator('#respuesta').inner_text()[:300]}
    ctx.set_geolocation({'longitude': -70.65, 'latitude': -33.44})
    page.click('#btn-ubicacion')
    page.wait_for_function(
        "() => document.querySelector('#respuesta').innerText.includes('Fuera del alcance')", timeout=8000)
    R['10_geo_fuera'] = {'estado': page.locator('#estado').inner_text(),
                         'corto': page.locator('#respuesta').inner_text()[:300]}
    print('--- 10 geo:', R['10_geo_dentro']['estado'], '|', R['10_geo_fuera']['estado'])
    ctx2 = nav.new_context(viewport={'width': 1280, 'height': 900})
    p2 = ctx2.new_page()
    p2.goto(BASE + '/')
    p2.wait_for_function("() => !!estado.puntos", timeout=60000)
    p2.click('#btn-ubicacion')
    try:
        # app.js pide la posición con timeout de 12 s: se espera un poco más.
        p2.wait_for_function(
            "() => /ubicaci/i.test(document.querySelector('#estado').innerText) && !/Obteniendo/.test(document.querySelector('#estado').innerText)",
            timeout=30000)
    except Exception as e:
        R['10_geo_denegada_nota'] = f'timeout: {str(e)[:60]}'
    R['10_geo_denegada'] = p2.locator('#estado').inner_text()
    print('--- 10 geo denegada:', R['10_geo_denegada'])
    ctx2.close()

    # 11a. El botón «Buscar»: ¿hace algo? Prueba negativa: se cuenta si sale
    # alguna petición al geocodificador y si #estado cambia. Como lo que se
    # mide es una AUSENCIA, se espera un tiempo acotado (2,5 s) — y el control
    # positivo es la misma acción con Enter, justo después.
    peticiones = []
    page.on('request', lambda r: peticiones.append(r.url) if 'nominatim' in r.url else None)
    # limit=1 es la petición de buscar(); limit=5 la de las sugerencias.
    page.fill('#q', 'Balmaceda 500, Temuco')
    page.evaluate("() => { document.querySelector('#sugerencias').innerHTML=''; }")
    page.click('#btn-buscar')
    page.wait_for_timeout(2500)
    R['11a_boton_buscar'] = {'estado': page.locator('#estado').inner_text(),
                             'peticiones_nominatim': len(peticiones),
                             'peticiones_de_buscar_limit1': sum('limit=1&' in u for u in peticiones),
                             'peticiones_de_sugerencias_limit5': sum('limit=5&' in u for u in peticiones),
                             'listener': page.evaluate("() => typeof getEventListeners === 'function' ? 'devtools' : 'n/a'")}
    print('--- 11a botón Buscar:', R['11a_boton_buscar'])
    # 11b. Buscador por Enter: sin red (bloqueo de nominatim) y con red
    page.route('**/nominatim.openstreetmap.org/**', lambda r: r.abort())
    page.fill('#q', 'Balmaceda 500, Temuco')
    page.press('#q', 'Enter')
    page.wait_for_function(
        "() => /No se pudo|No se encontr/.test(document.querySelector('#estado').innerText)", timeout=15000)
    R['11_buscar_sin_red'] = {'estado': page.locator('#estado').inner_text(), 'peticiones': len(peticiones)}
    page.unroute('**/nominatim.openstreetmap.org/**')
    page.fill('#q', 'Balmaceda 500, Temuco')
    page.press('#q', 'Enter')
    page.wait_for_function(
        "() => /Balmaceda/.test(document.querySelector('#respuesta').innerText) || /No se/.test(document.querySelector('#estado').innerText)",
        timeout=25000)
    R['11_buscar_con_red'] = {'estado': page.locator('#estado').inner_text(),
                              'corto': page.locator('#respuesta').inner_text()[:400]}
    page.fill('#q', 'Avenida Providencia 1000, Santiago')
    page.press('#q', 'Enter')
    page.wait_for_function(
        "() => /No se/.test(document.querySelector('#estado').innerText) || /Providencia/.test(document.querySelector('#respuesta').innerText)",
        timeout=25000)
    R['11_buscar_santiago'] = {'estado': page.locator('#estado').inner_text(),
                               'corto': page.locator('#respuesta').inner_text()[:300]}
    print('--- 11 buscar:', R['11_buscar_sin_red'], '|', R['11_buscar_con_red']['estado'],
          R['11_buscar_con_red']['corto'][:120].replace('\n', ' '), '|', R['11_buscar_santiago'])

    # 12. Capas: encender cada una y leer visibilidad real + #estado
    caps = {}
    MAPA_CAPAS = {'cap-areas': ['ar-fill'], 'cap-derivadas': ['lam-fill', 'lam-line'],
                  'cap-planos': ['huellas-fill'], 'cap-sar': ['sar-fill'], 'cap-gore': ['gore-fill'],
                  'cap-jrc': ['jrc-fill'], 'cap-puntos': ['pc-circ'], 'cap-camp': ['camp-fill']}
    for cid, layers in MAPA_CAPAS.items():
        page.evaluate(
            "(id) => { const el = document.getElementById(id); if (!el.checked) { el.checked = true; el.dispatchEvent(new Event('change')); } }",
            cid)
        vis = page.evaluate(
            "(ls) => ls.map(l => estado.mapa.getLayer(l) ? (estado.mapa.getLayoutProperty(l, 'visibility') || 'visible') : 'NO EXISTE')",
            layers)
        caps[cid] = {'vis': vis, 'estado': page.locator('#estado').inner_text()}
    R['12_capas'] = caps
    print('--- 12 capas:', json.dumps(caps, ensure_ascii=False))
    guardar()

    # 13. Clic sobre un polígono MINVU en el mapa: ¿popup y consulta a la vez?
    try:
        page.evaluate("() => document.querySelector('#mapa').scrollIntoView()")
        page.evaluate("([lon,lat]) => estado.mapa.jumpTo({center:[lon,lat], zoom:15})", [pA[0], pA[1]])
        try:
            page.wait_for_function("() => !estado.mapa.isMoving() && estado.mapa.isStyleLoaded() && estado.mapa.areTilesLoaded()", timeout=20000)
        except Exception as e:
            R['13_nota'] = f'no se esperó a las teselas: {str(e)[:80]}'
        box = page.locator('#mapa').bounding_box()
        page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.wait_for_function(
            "() => document.querySelector('#respuesta').innerText.includes('Punto seleccionado') || document.querySelector('.maplibregl-popup')",
            timeout=8000)
        page.wait_for_timeout(700)
        R['13_clic_area'] = {
            'popup': page.evaluate("() => { const p = document.querySelector('.maplibregl-popup'); return p ? p.innerText : null; }"),
            'respuesta': page.locator('#respuesta').inner_text()[:160], 'box': box}
        page.screenshot(path=str(EVID / '13_clic_area.png'))
    except Exception as e:
        R['13_clic_area'] = {'error': str(e)[:200], 'respuesta': page.locator('#respuesta').inner_text()[:160]}
    print('--- 13 clic área:', json.dumps(R['13_clic_area'], ensure_ascii=False)[:400])
    guardar()

    # 14. Cifras de portada y sello
    R['14_cifras'] = page.locator('#cifras').inner_text()
    R['14_sello'] = page.locator('#sello-datos').inner_text()
    R['14_nota_sar'] = page.locator('#nota-sar').inner_text()
    print('--- 14 cifras:', R['14_cifras'].replace('\n', ' | '), '| sello:', R['14_sello'])

    # 15. Modo sin señal: esperar SW, recargar offline, consultar
    page.wait_for_function(
        "() => navigator.serviceWorker && navigator.serviceWorker.controller !== null", timeout=30000)
    page.wait_for_function("() => caches.keys().then(k => k.length > 0)", timeout=30000)
    page.wait_for_function(
        "() => caches.open('riesgomapas-v21-app').then(c => c.keys()).then(k => k.length >= 20)", timeout=60000)
    ctx.set_offline(True)
    page.goto(BASE + '/')
    page.wait_for_function("() => !!estado.puntos", timeout=30000)
    off = {}
    off['cargadas'] = page.evaluate(
        "() => ({puntos: !!estado.puntos, areas: !!estado.areasRiesgo, laminas: !!estado.laminas, gore: !!estado.gore, jrc: !!estado.jrc, sar: !!estado.sar, cob: !!estado.sarCobertura, camp: !!estado.campamentos, planos: (estado.planos||[]).length, estadoComunas: (estado.estadoComunas||[]).length})")
    off['estado'] = page.locator('#estado').inner_text()
    page.evaluate("() => consultar(-72.5945, -38.7636, 'Auditoría offline PLC')")
    page.wait_for_function(
        "() => document.querySelector('#respuesta').innerText.includes('Auditoría offline PLC')", timeout=8000)
    off['respuesta'] = page.locator('#respuesta').inner_text()[:300]
    page.fill('#q', 'Balmaceda 500, Temuco')
    page.press('#q', 'Enter')
    page.wait_for_function(
        "() => /No se pudo|No se encontr/.test(document.querySelector('#estado').innerText)", timeout=15000)
    off['buscar'] = page.locator('#estado').inner_text()
    page.fill('#q', 'ang')
    page.wait_for_function("() => document.querySelectorAll('#sugerencias li').length > 0", timeout=5000)
    off['sugerencias'] = page.locator('#sugerencias').inner_text()
    page.screenshot(path=str(EVID / '15_offline.png'))
    page.goto(BASE + '/documentos.html')
    page.wait_for_function(
        "() => document.querySelector('#resumen').innerText.length > 0 || document.querySelector('#lista').innerText.length > 0",
        timeout=15000)
    off['catalogo'] = page.locator('#resumen').inner_text() or page.locator('#lista').inner_text()[:200]
    ctx.set_offline(False)
    R['15_offline'] = off
    print('--- 15 offline:', json.dumps(off, ensure_ascii=False)[:900])

    R['errores_js'] = errores
    print('--- errores JS:', errores)
    nav.close()

(EVID / 'resultados.json').write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding='utf-8')
print('OK evidencia en', EVID)
