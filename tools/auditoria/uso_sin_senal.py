"""Modo sin señal: ¿qué capas llegan a la ficha cuando no hay red?

Preguntas del instrumento:
 (1) Si el precaché estuviera roto, ¿fallaría?  Sí: se lista qué hay en la caché
     del service worker y qué capas quedan en `estado` tras recargar SIN red; una
     capa ausente sale como false. Control positivo: con red, todas son true.
 (2) Si el instrumento estuviera muerto, ¿se vería distinto?  Sí: no habría JSON
     de salida. Y se espera a que `cargarDatos` TERMINE (#estado deja de decir
     «Cargando…»), no a que empiece: la primera versión de esta prueba leía a
     mitad de carga y acusaba capas que sí llegaban.

Uso: python tools/auditoria/uso_sin_senal.py  (sirve web/ en :8791)
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

FLAGS = ("() => ({puntos: !!estado.puntos, areas: !!estado.areasRiesgo, laminas: !!estado.laminas, "
         "gore: !!estado.gore, jrc: !!estado.jrc, sar: !!estado.sar, cob: !!estado.sarCobertura, "
         "sarIndice: !!estado.sarIndice, camp: !!estado.campamentos, planos: (estado.planos||[]).length, "
         "estadoComunas: (estado.estadoComunas||[]).length})")
CARGA_TERMINADA = "() => !!estado.puntos && !document.querySelector('#estado').innerText.startsWith('Cargando')"
R = {}

with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    ctx = nav.new_context(viewport={'width': 1280, 'height': 900})
    page = ctx.new_page()
    page.goto(BASE + '/')
    page.wait_for_function(CARGA_TERMINADA, timeout=60000)
    R['con_red'] = page.evaluate(FLAGS)
    page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller !== null", timeout=30000)
    # Esperar a que la instalación termine de llenar la caché del armazón.
    page.wait_for_function(
        "() => caches.keys().then(ks => Promise.all(ks.filter(k => k.endsWith('-app')).map(k => caches.open(k).then(c => c.keys()))).then(ls => ls.flat().length >= 24))",
        timeout=90000)
    R['cache'] = page.evaluate(
        "() => caches.keys().then(ks => Promise.all(ks.map(k => caches.open(k).then(c => c.keys()).then(rs => [k, rs.map(r => r.url.replace(location.origin + '/', ''))]))))")
    print('CACHÉ:', json.dumps(R['cache'], ensure_ascii=False)[:1500])

    ctx.set_offline(True)
    page.goto(BASE + '/')
    page.wait_for_function(CARGA_TERMINADA, timeout=60000)
    R['sin_red'] = page.evaluate(FLAGS)
    R['sin_red_estado'] = page.locator('#estado').inner_text()
    print('SIN RED flags:', R['sin_red'], '| #estado:', R['sin_red_estado'])

    page.evaluate("() => consultar(-72.5945, -38.7636, 'Auditoría offline PLC')")
    page.wait_for_function("() => document.querySelector('#respuesta').innerText.includes('Auditoría offline PLC')", timeout=8000)
    R['ficha_plc'] = page.locator('#detalle-ficha').inner_text()
    (EVID / '15_offline_ficha_plc.txt').write_text(R['ficha_plc'], encoding='utf-8')
    page.evaluate("() => consultar(-72.43769380639036, -37.96136005453543, 'Auditoría offline Collipulli área')")
    page.wait_for_function("() => document.querySelector('#respuesta').innerText.includes('Auditoría offline Collipulli')", timeout=8000)
    R['corto_collipulli'] = page.locator('#respuesta').inner_text()
    print('OFFLINE Collipulli (dentro de área MINVU con red):', R['corto_collipulli'][:160].replace('\n', ' | '))

    page.fill('#q', 'Balmaceda 500, Temuco')
    page.press('#q', 'Enter')
    page.wait_for_function("() => /No se pudo|No se encontr/.test(document.querySelector('#estado').innerText)", timeout=15000)
    R['buscar'] = page.locator('#estado').inner_text()
    page.fill('#q', 'ang')
    page.wait_for_function("() => document.querySelectorAll('#sugerencias li').length > 0", timeout=5000)
    R['sugerencias'] = page.locator('#sugerencias').inner_text()
    # Mapa base satelital sin red: ¿alguna tesela responde?
    fallidas = []
    page.on('requestfailed', lambda r: fallidas.append(r.url) if 'arcgisonline' in r.url or 'openstreetmap' in r.url else None)
    # El selector vive dentro de un <details> plegado: se abre como lo haría la persona.
    page.evaluate("() => { document.querySelector('.capas-plegable').open = true; }")
    page.click('#base-satelite')
    page.wait_for_timeout(2500)   # ausencia: tiempo acotado
    R['teselas_fallidas_satelite'] = len([u for u in fallidas if 'arcgisonline' in u])
    page.screenshot(path=str(EVID / '15_offline_satelite.png'))
    page.goto(BASE + '/documentos.html')
    page.wait_for_function("() => document.querySelector('#resumen').innerText.length > 0 || document.querySelector('#lista').innerText.length > 0", timeout=15000)
    R['catalogo'] = page.locator('#resumen').inner_text() or page.locator('#lista').inner_text()[:200]
    ctx.set_offline(False)
    print('buscar:', R['buscar'], '| sugerencias:', R['sugerencias'].replace('\n', ' '), '| teselas sat fallidas:', R['teselas_fallidas_satelite'], '| catálogo:', R['catalogo'])
    nav.close()

(EVID / 'resultados_offline.json').write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding='utf-8')
print('OK')
