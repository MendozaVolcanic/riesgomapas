"""Auditoría funcional end-to-end del visor, en un navegador real.

Por qué existe: durante el desarrollo el panel de navegador de la sesión no
compone cuadros, así que MapLibre nunca inicializaba y era imposible verificar lo
más importante —que el mapa dibuje— sin pedírselo a una persona. Este arnés
levanta Chromium de verdad, ejerce cada funcionalidad y deja capturas.

Encuentra la clase de bug que los tests unitarios no ven: controles tapados por
otros elementos, capas que no se dibujan, errores de JavaScript en runtime,
recursos que no cargan, desbordes de layout en celular.

Uso:
    python tests/auditoria_e2e.py                    # servidor propio, puerto libre
    python tests/auditoria_e2e.py --url http://localhost:8788
    python tests/auditoria_e2e.py --ver              # con ventana visible
"""
from __future__ import annotations

import argparse
import http.server
import json
import math
import socket
import socketserver
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"
CAPTURAS = RAIZ / "data" / "processed" / "auditoria"


# --------------------------------------------------------------- servidor

def servir(directorio: Path) -> tuple[str, socketserver.TCPServer]:
    """Servidor propio en un puerto libre.

    Se usa uno propio y no el de desarrollo para que la auditoría no dependa de
    que alguien lo haya dejado corriendo, y para partir sin service worker ni
    caché heredada — que fue justamente el origen de un bug real.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(directorio), **k)

        def log_message(self, *a):  # silencio
            pass

        def end_headers(self):
            # Sin caché: cada corrida audita el código actual, no una copia vieja.
            self.send_header("Cache-Control", "no-store, must-revalidate")
            super().end_headers()

    httpd = socketserver.TCPServer(("127.0.0.1", puerto), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{puerto}", httpd


# --------------------------------------------------------------- hallazgos

class Auditoria:
    def __init__(self):
        self.hallazgos: list[dict] = []
        self.pasos: list[str] = []

    def falla(self, area: str, detalle: str, gravedad: str = "alta"):
        self.hallazgos.append({"area": area, "gravedad": gravedad, "detalle": detalle})
        print(f"  [X] {area}: {detalle}")

    def ok(self, area: str, detalle: str = ""):
        self.pasos.append(area)
        print(f"  [OK] {area}" + (f" — {detalle}" if detalle else ""))

    def resumen(self) -> int:
        print("\n" + "=" * 72)
        print(f"AUDITORÍA: {len(self.pasos)} comprobaciones OK, "
              f"{len(self.hallazgos)} hallazgos")
        for h in self.hallazgos:
            print(f"  [{h['gravedad'].upper()}] {h['area']}: {h['detalle']}")
        return len(self.hallazgos)


# ----------------------------------------------------------------- pruebas

def _colores_distintos(ruta: Path) -> int:
    from PIL import Image
    im = Image.open(ruta).convert("RGB")
    im.thumbnail((320, 320))
    return len(set(im.getdata()))


def esperar_mapa(page, aud: Auditoria, etiqueta: str) -> bool:
    """El estilo de MapLibre tarda; sin él ninguna capa existe."""
    for _ in range(60):
        if page.evaluate("() => !!(window.estado && estado.mapa && estado.mapa.isStyleLoaded())"):
            return True
        page.wait_for_timeout(500)
    aud.falla(etiqueta, "MapLibre no terminó de cargar el estilo en 30 s")
    return False


def contraste(hex_fondo: str, hex_texto: str) -> float:
    """Razón de contraste WCAG entre dos colores `rgb(r, g, b)`."""
    def lum(c: str) -> float:
        n = [int(x) / 255 for x in c[c.find("(") + 1:c.find(")")].split(",")[:3]]
        n = [v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4 for v in n]
        return .2126 * n[0] + .7152 * n[1] + .0722 * n[2]
    a, b = lum(hex_fondo), lum(hex_texto)
    return (max(a, b) + .05) / (min(a, b) + .05)


_FICHA_JS = """([lon, lat]) => {
    // La misma cadena que recorre la persona, sin el mapa: evaluar, la razón
    // en pantalla y el texto que se reenvía. Se fija la precisión en null para
    // que el bloque no herede la de un bloque anterior (REGLAS §4.3).
    estado.precisionPos = null;
    const r = evaluar(lon, lat);
    estado.ultimo = { res: r, etiqueta: 'Auditoría', lon, lat };
    const plano = (h) => String(h).replace(/<[^>]+>/g, ' ').replace(/\\s+/g, ' ');
    return { nivel: r.nivel, titulo: r.titulo, porQue: plano(porQue(r)),
             texto: textoFicha(), gore: r.gore.length, mancha: !!r.enMancha,
             borde: !!r.borde, ncerca: r.cerca.length, laminas: r.laminas.length,
             graves300: r.cerca.filter((c) => c.d <= 300 &&
               ['Muy Alto', 'Alto'].includes(c.f.properties.nivel)).length };
}"""

_RANGO = {"sindato": 0, "bajo": 1, "medio": 2, "alto": 3}


def auditar_lo_que_dice_el_veredicto(page, aud: Auditoria, etq: str) -> None:
    """Familia 3 de la auditoría del 15-nov-2026: lo que el veredicto le dice a
    la persona. Cada comprobación usa un punto real del informe y exige que el
    punto todavía tenga la condición que lo hace útil; si no la tiene, falla
    como «no corre» en vez de dar un verde que no miró nada (REGLAS §4.2).
    """
    ficha = lambda ll: page.evaluate(_FICHA_JS, ll)  # noqa: E731

    # F-101: elegir una comuna respondía sobre el centro de la caja de sus
    # registros, un punto que nadie eligió: «Sin registros» en 22 de 30 comunas
    # con registros. Pucón tiene decenas y era una de las 22.
    n_pucon = page.evaluate("() => estado.puntos.features.filter((f) => "
                            "f.properties.comuna === 'PUCÓN').length")
    page.fill("#q", "Pucón")
    try:
        page.wait_for_function(
            "() => [...document.querySelectorAll('#sugerencias li')]"
            ".some((li) => /puc[oó]n/i.test(li.textContent))", timeout=5000)
        page.locator("#sugerencias li", has_text="Pucón").first.click(timeout=3000)
        page.wait_for_function(
            "() => /puc[oó]n/i.test(document.querySelector('#respuesta').innerText)",
            timeout=5000)
        t = page.locator("#respuesta").inner_text()
        if n_pucon and "sin registros" not in t.lower() and str(n_pucon) in t:
            aud.ok(f"elegir una comuna responde sobre la comuna [{etq}]",
                   f"Pucón, {n_pucon} registros")
        else:
            aud.falla(f"elegir una comuna [{etq}]",
                      f"Pucón tiene {n_pucon} registros y la respuesta dice: "
                      f"«{t[:120]}»")
    except Exception as exc:
        aud.falla(f"elegir una comuna [{etq}]",
                  f"no se pudo elegir Pucón: {str(exc).splitlines()[0][:100]}")
    page.fill("#q", "")

    # F-106: la precisión del GPS no puede sobrevivir a una consulta que no
    # viene del GPS. Se prueba en consultar(), que es por donde pasan todas.
    quedo = page.evaluate("""async () => {
        estado.precisionPos = 65;
        await consultar(-72.6, -38.74, 'Auditoría precisión');
        const p = estado.precisionPos; estado.precisionPos = null; return p; }""")
    if quedo is None:
        aud.ok(f"la precisión del GPS no se arrastra a otra consulta [{etq}]")
    else:
        aud.falla(f"precisión del GPS arrastrada [{etq}]",
                  f"tras consultar una dirección quedó precisionPos={quedo}")

    # F-100: con titular de borde, la pestaña de detalle (la que se imprime)
    # explicaba nada y decía «no cae dentro» debajo.
    page.evaluate("() => consultar(-72.620737, -38.761129, 'Auditoría borde')")
    page.wait_for_function(
        "() => estado.ultimo && estado.ultimo.etiqueta === 'Auditoría borde'", timeout=5000)
    if page.evaluate("() => !!estado.ultimo.res.borde"):
        det = page.evaluate("() => document.querySelector('#detalle-ficha').innerText")
        if "adentro y afuera" in det and "Este punto no cae dentro" not in det:
            aud.ok(f"el detalle explica la banda de borde [{etq}]")
        else:
            aud.falla(f"detalle bajo titular de borde [{etq}]",
                      "no explica la banda o dice «no cae dentro» bajo un titular de borde")
    else:
        aud.falla(f"punto de borde para el detalle [{etq}]", "ya no es de borde: no corre")

    # F-105: acercarse al borde no puede bajar el nivel que dan los registros.
    # Punto 5 m afuera del área de riesgo de Nueva Imperial. Hasta el 15-nov
    # era el borde del ZR-1 viejo; GeoIDE trajo la versión de 2025 y ese punto
    # quedó 24 m adentro, así que se movió al borde nuevo más cercano.
    lat0, lon0 = -38.746458701710466, -72.9569970087293
    niveles = []
    for m in (0, 60, 120):
        r = ficha([lon0 + m / (111320 * math.cos(math.radians(lat0))), lat0])
        niveles.append((m, r["nivel"], r["borde"], r["graves300"]))
    if not (niveles[0][2] and niveles[0][3]):
        aud.falla(f"punto de borde con registro grave [{etq}]", f"no corre: {niveles}")
    elif _RANGO[niveles[0][1]] >= max(_RANGO[n[1]] for n in niveles[1:]):
        aud.ok(f"el borde no rebaja el nivel de los registros [{etq}]",
               " · ".join(f"{m} m {n}" for m, n, _, _ in niveles))
    else:
        aud.falla(f"el borde rebaja el nivel [{etq}]",
                  " · ".join(f"{m} m {n}" for m, n, _, _ in niveles))

    # F-110: con un registro a 501-1.500 m el resumen callaba el modelo.
    r = ficha([-73.123908, -38.70824819942508])
    if r["nivel"] != "bajo" or not r["gore"]:
        aud.falla(f"punto bajo con modelo [{etq}]", f"no corre: {r['nivel']}, gore={r['gore']}")
    elif "modelo" in r["porQue"]:
        aud.ok(f"el resumen nombra el modelo bajo un registro lejano [{etq}]")
    else:
        aud.falla(f"el modelo queda callado [{etq}]", r["porQue"][:120])

    # F-102: el texto que se reenvía tiene que nombrar la capa que decidió.
    for nombre, ll, exige, patron in [
        # estudio de Angol de 2013, a más de 500 m de toda área normativa. El
        # punto anterior estaba en la lámina del plan de Angol, que desde el
        # 15-nov queda de respaldo porque GeoIDE publica ese plan.
        ("lámina derivada", [-72.670902, -37.788388], "laminas", "trazado"),
        ("modelo sin registros", [-73.08786, -38.68423], "gore", "modelo"),
        ("borde", [-72.620737, -38.761129], "borde", "borde"),
    ]:
        r = ficha(ll)
        cuerpo = r["texto"].split("\n", 1)[1]   # sin el titular
        if not r[exige]:
            aud.falla(f"texto compartido, {nombre} [{etq}]", "el punto ya no sirve: no corre")
        elif patron in cuerpo.lower():
            aud.ok(f"el texto compartido nombra la capa que decidió: {nombre} [{etq}]")
        else:
            aud.falla(f"texto compartido sin la capa que decidió: {nombre} [{etq}]",
                      cuerpo[:140].replace("\n", " / "))

    # F-113: si el texto lista 3 puntos, tiene que decir cuántos hay.
    r = ficha([-71.942799, -39.278511])
    if r["ncerca"] <= 3:
        aud.falla(f"punto con muchos registros [{etq}]", f"no corre: {r['ncerca']}")
    elif f"1,5 km: {r['ncerca']}" in r["texto"]:
        aud.ok(f"el texto compartido dice cuántos registros hay [{etq}]", str(r["ncerca"]))
    else:
        aud.falla(f"el texto recorta sin decir el total [{etq}]",
                  f"hay {r['ncerca']} y el texto no lo dice")
    page.evaluate("() => irAPestana('respuesta', false)")


def auditar(page, aud: Auditoria, base: str, movil: bool, oscuro: bool = False) -> None:
    etq = ("móvil" if movil else "escritorio") + (" oscuro" if oscuro else "")
    errores_js: list[str] = []
    fallos_red: list[str] = []
    page.on("pageerror", lambda e: errores_js.append(str(e)))
    page.on("requestfailed",
            lambda r: fallos_red.append(f"{r.url.split('/')[-1]}: {r.failure}"))
    page.on("response", lambda r: fallos_red.append(f"{r.url.split('/')[-1]}: HTTP {r.status}")
            if r.status >= 400 else None)

    # ---------------------------------------------------------- portada
    page.goto(f"{base}/index.html", wait_until="networkidle")
    page.wait_for_timeout(1500)

    if not esperar_mapa(page, aud, f"mapa [{etq}]"):
        return
    aud.ok(f"mapa carga [{etq}]")

    capas = page.evaluate("() => estado.mapa.getStyle().layers.map(l => l.id)")
    for esperada in ["osm", "pc-circ", "ar-fill", "huellas-fill", "camp-fill",
                     "sar-fill", "sar-line", "gore-fill"]:
        if esperada in capas:
            aud.ok(f"capa {esperada} [{etq}]")
        else:
            aud.falla(f"capa {esperada} [{etq}]", "no se agregó al mapa")

    CAPTURAS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(CAPTURAS / f"01_portada_{etq}.png"), full_page=False)

    # ¿el mapa dibuja algo, o es un rectángulo vacío?
    #
    # Se mide sobre una CAPTURA del elemento, no con gl.readPixels: MapLibre crea
    # el contexto sin `preserveDrawingBuffer`, así que leer el búfer después de
    # presentar el cuadro devuelve un lienzo en blanco y da un falso positivo de
    # "el mapa no dibuja". Ese error costó una acusación equivocada al mapa.
    ruta_mapa = CAPTURAS / f"01b_mapa_{etq}.png"
    page.locator("#mapa").screenshot(path=str(ruta_mapa))
    colores = _colores_distintos(ruta_mapa)
    if colores > 50:
        aud.ok(f"el mapa dibuja contenido [{etq}]", f"{colores} colores distintos")
    else:
        aud.falla(f"render del mapa [{etq}]",
                  f"la captura del mapa tiene sólo {colores} colores — ¿tiles no cargan?")

    # ------------------------- para qué sirve, y qué se puede hacer con esto
    #
    # El uso principal no es la emergencia: es la decisión previa —comprar un
    # sitio, construir, firmar— y el reclamo posterior. Durante una inundación
    # la gente ya no puede actuar sobre esta información. Si el sitio deja de
    # decirlo, vuelve a leerse como una herramienta de emergencia, que es
    # justamente lo que no debe ser.
    page.evaluate("() => irAPestana('respuesta', false)")
    page.wait_for_timeout(200)
    pq = page.locator(".para-que")
    if pq.count() and "antes de comprar" in pq.inner_text().lower():
        aud.ok(f"el sitio declara que sirve antes de comprar o construir [{etq}]")
    else:
        aud.falla(f"para qué sirve [{etq}]",
                  "no dice que el uso es la decisión previa; sin eso se lee como "
                  "herramienta de emergencia, que es cuando ya no se puede actuar")

    page.evaluate("() => consultar(-72.5904, -38.7359, 'Auditoría acciones')")
    page.wait_for_timeout(700)
    page.evaluate("() => irAPestana('detalle', false)")
    page.wait_for_timeout(300)
    if page.locator("#btn-imprimir").count():
        aud.ok(f"la evidencia se puede imprimir o guardar como PDF [{etq}]")
    else:
        aud.falla(f"ficha imprimible [{etq}]",
                  "no se puede llevar el respaldo a la Dirección de Obras ni "
                  "adjuntarlo a un reclamo")
    if page.locator("#btn-solicitud").count():
        aud.ok(f"se puede generar la solicitud de transparencia [{etq}]")
        # El texto tiene que citar la ley y nombrar la comuna: una plantilla
        # genérica no sirve para presentarla.
        txt = page.evaluate(
            "() => { const c = comunaDe(estado.ultimo.res, estado.ultimo.lon, "
            "estado.ultimo.lat); return c ? textoSolicitud(c) : ''; }")
        falta = [x for x in ("20.285", "inundación") if x not in txt]
        if txt and not falta:
            aud.ok(f"la solicitud cita la ley y es específica [{etq}]",
                   f"{len(txt)} caracteres")
        else:
            aud.falla(f"solicitud de transparencia [{etq}]",
                      f"texto vacío o le falta: {falta}")
    else:
        aud.falla(f"solicitud de transparencia [{etq}]",
                  "el vacío se muestra pero no hay camino para reclamarlo")

    # En papel NO puede faltar la evidencia: la hoja viaja sola, sin nadie que
    # la explique, y la pestaña oculta no se imprimiría sin la regla de @media.
    css = (WEB / "style.css").read_text(encoding="utf-8")
    if '[role="tabpanel"][hidden] { display: block !important; }' in css:
        aud.ok(f"al imprimir se incluye la evidencia completa [{etq}]")
    else:
        aud.falla(f"impresión [{etq}]",
                  "la pestaña oculta no se imprime: el papel saldría con el "
                  "veredicto y sin las fuentes")

    # ------------------------------------ inventario: qué tenemos y con qué peso
    #
    # Pedido de Nicolás (16-nov-2026). Las cifras se contrastan contra el JSON
    # leído del disco, no contra lo que el visor dice: si el visor dejara de
    # cargarlo o mostrara otro número, esta comprobación lo ve. Y el peso legal no
    # puede inflarse: los anteproyectos tienen que decir que no rigen.
    inv = json.loads((WEB / "data" / "inventario.json").read_text(encoding="utf-8"))
    page.evaluate("() => irAPestana('detalle', false)")
    page.wait_for_timeout(250)
    sec = page.locator("#inventario")
    if not sec.count() or not sec.is_visible():
        aud.falla(f"inventario [{etq}]", "la sección no se ve")
    else:
        txt = sec.inner_text()
        n = inv["normativo"]
        esperado = [
            f"{n['poligonos']} polígonos en {n['comunas']} comunas",
            f"{inv['planos']['planos']} planos de {inv['planos']['comunas']} comunas",
            f"{len(inv['sin_cartografia'])} comunas sin ningún mapa",
            *[d["comuna"] for d in n["con_resolucion"]],
            *inv["sin_cartografia"],
        ]
        falta = [x for x in esperado if x not in txt]
        if falta:
            aud.falla(f"inventario [{etq}]", f"no dice: {falta}")
        else:
            aud.ok(f"el inventario cuadra con inventario.json [{etq}]",
                   f"{n['comunas']} comunas con área, {len(inv['sin_cartografia'])} sin mapa")
        if "anteproyectos: todavía no rigen" in txt and "no declara su resolución" in txt:
            aud.ok(f"el inventario no infla el peso legal [{etq}]")
        else:
            aud.falla(f"peso legal en el inventario [{etq}]",
                      "no advierte que los anteproyectos no rigen o que el dato no "
                      "declara la resolución")
        ancho = page.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        if ancho > 1:
            aud.falla(f"inventario desborda [{etq}]", f"{ancho} px de scroll lateral")

    # ------------------------------------ quiénes lo hacen y para qué
    #
    # La autoría explícita y el «esperamos dejar de hacer falta» no son adorno:
    # son lo que separa un proyecto ciudadano de algo que se puede leer como
    # información oficial, y lo que desarma la lectura de «un particular
    # compitiendo con el Estado». Si desaparecen, cambia el encuadre legal del
    # sitio entero. Ver docs/DIFUSION.md §5.
    page.evaluate("() => irAPestana('detalle', false)")
    page.wait_for_timeout(250)
    t_pag = page.locator("main").inner_text().lower() + " " +         page.locator("footer").inner_text().lower()
    for etiqueta, aguja in {
        "nombra a sus autores": "roberto laregla",
        "declara que no tiene respaldo institucional": "sin respaldo institucional",
        "dice que espera dejar de hacer falta": "se pueda apagar",
    }.items():
        if aguja in t_pag:
            aud.ok(f"el sitio {etiqueta} [{etq}]")
        else:
            aud.falla(f"encuadre del proyecto [{etq}]",
                      f"falta que {etiqueta}: no aparece «{aguja}»")

    # Toda fuente cuyo dato se publique tiene que estar en el pie. Faltaban
    # MINVU —la única capa con efecto legal— y el GORE —la más grande—, lo que
    # contradecía la regla del propio sitio.
    pie = page.locator("footer").inner_text().lower()
    faltan = [f for f in ("minvu", "gobierno regional", "senapred", "ine",
                          "openstreetmap", "esri") if f not in pie]
    if not faltan:
        aud.ok(f"el pie declara todas las fuentes publicadas [{etq}]")
    else:
        aud.falla(f"atribución de fuentes [{etq}]",
                  f"el pie no menciona: {faltan}; el sitio publica sus datos")
    if "no registra nada" in pie:
        aud.ok(f"el sitio declara que no registra datos personales [{etq}]")
    else:
        aud.falla(f"aviso de privacidad [{etq}]",
                  "no declara que la consulta ocurre en el dispositivo; la Ley "
                  "21.719 rige desde el 1-dic-2026 y la ubicación es dato personal",
                  gravedad="media")
    page.evaluate("() => irAPestana('respuesta', false)")
    page.wait_for_timeout(200)

    # -------------------------------- el inventario del vacío por comuna
    #
    # Es la unidad que se comparte, y la razón es de fondo: «en mi comuna no hay
    # mapa» es verificable y no empuja a nadie a una mala decisión; un veredicto
    # sobre una casa reenviado por WhatsApp sí puede. Si este bloque
    # desapareciera, el sitio perdería justo lo que puede mover a una
    # institución. Ver docs/DIFUSION.md §0b.
    page.evaluate("() => consultar(-72.5904, -38.7359, 'Auditoría inventario')")
    page.wait_for_timeout(700)
    page.evaluate("() => irAPestana('detalle', false)")
    page.wait_for_timeout(300)
    bloque = page.locator(".bloque-comuna")
    if bloque.count():
        t = bloque.inner_text().lower()
        aud.ok(f"la ficha dice con qué cuenta la comuna [{etq}]")
        if "no dice si tu casa se inunda" in t:
            aud.ok(f"el inventario se distingue de la evidencia de amenaza [{etq}]")
        else:
            aud.falla(f"inventario de la comuna [{etq}]",
                      "no aclara que habla de la información disponible, no del "
                      "riesgo; «acá no hay mapa» se leería como «acá no se inunda»")
        if page.locator("#btn-compartir-comuna").count():
            aud.ok(f"el estado de la comuna se puede compartir [{etq}]")
        else:
            aud.falla(f"inventario de la comuna [{etq}]", "no se puede compartir")
    else:
        aud.falla(f"inventario de la comuna [{etq}]",
                  "no aparece el bloque de qué tiene y qué le falta a la comuna")
    page.evaluate("() => irAPestana('respuesta', false)")
    page.wait_for_timeout(200)

    # ------------------------------------- lo que arregló la auditoría
    #
    # Cuatro fallas que no daban error y se manifestaban como «el sitio no hace
    # nada» o «acá no hay dato». Cada una con su comprobación, porque un arreglo
    # sin prueba se deshace solo en el siguiente cambio.

    # (a) Los planos se LIBERAN al apagarlos, no se ocultan: cada uno es una
    #     textura de ~870 KB en memoria de video y se acumulaban al panear.
    page.evaluate("() => irAPestana('respuesta', false)")
    page.evaluate("() => document.querySelector('details.capas-plegable').open = true")
    # El panel del mapa venía OCULTO del bloque anterior, así que MapLibre midió
    # cero. Tras volver a mostrarlo hay que dejar que se reasiente: si no,
    # `getBounds()` devuelve la vista vieja, `planosEnVista()` no encuentra
    # ninguno y la comprobación siguiente se queda sin nada que mirar.
    page.evaluate("() => estado.mapa.resize()")
    page.wait_for_timeout(800)
    # Hay que ACERCARSE primero: los planos sólo se cargan desde zoom 11, así que
    # comprobar la liberación a escala regional pasaría sin haber cargado ninguno
    # —«0 capas → 0 capas»— y no probaría nada.
    page.evaluate("() => { const p = estado.planos && estado.planos[0]; "
                  "if (!p) return; const b = p.bounds_wgs84; "
                  "estado.mapa.jumpTo({center: [(b[0]+b[2])/2, (b[1]+b[3])/2], "
                  "zoom: 13}); }")
    page.wait_for_timeout(900)
    page.locator("#cap-planos").click(timeout=3000)
    page.wait_for_timeout(3500)
    con = page.evaluate("() => estado.mapa.getStyle().layers.filter(l => "
                        "l.id.startsWith('plano-')).length")
    page.locator("#cap-planos").click(timeout=3000)
    page.wait_for_timeout(900)
    sin = page.evaluate("() => estado.mapa.getStyle().layers.filter(l => "
                        "l.id.startsWith('plano-')).length")
    fuentes = page.evaluate("() => Object.keys(estado.mapa.getStyle().sources)"
                            ".filter(k => k.startsWith('plano-')).length")
    if con == 0:
        aud.falla(f"fuga de planos [{etq}]",
                  "no se cargó ningún plano, así que la comprobación de liberación "
                  "no miró nada: es un verde que no dice nada")
    elif sin == 0 and fuentes == 0:
        aud.ok(f"los planos liberan memoria al apagarlos [{etq}]",
               f"{con} capa(s) cargadas → 0 capas y 0 fuentes")
    else:
        aud.falla(f"fuga de planos [{etq}]",
                  f"quedaron {sin} capa(s) y {fuentes} fuente(s) tras apagar")

    # (b) La capa regional del GORE tiene que estar precacheada: sin ella, sin
    #     señal la ficha decía «no disponible» para una capa que sí existe.
    sw = (WEB / "sw.js").read_text(encoding="utf-8")
    if "data/gore/amenaza-inundacion.geojson" in sw:
        aud.ok(f"la capa regional se precachea para uso sin señal [{etq}]")
    else:
        aud.falla(f"precaché de la capa regional [{etq}]",
                  "sin ella el visor offline afirma que no está publicada")

    # (c) Elegir una comuna en las sugerencias tiene que ENTREGAR respuesta, no
    #     sólo mover el mapa: es la única vía para quien no usa el mapa.
    page.fill("#q", "Angol")
    page.wait_for_timeout(600)
    sug = page.locator("#sugerencias li")
    if sug.count():
        sug.first.click(timeout=3000)
        page.wait_for_timeout(900)
        t = page.locator("#respuesta").inner_text().lower()
        if "angol" in t and len(t) > 60:
            aud.ok(f"elegir una comuna entrega ficha, no sólo mueve el mapa [{etq}]")
        else:
            aud.falla(f"sugerencia de comuna [{etq}]",
                      "mueve el mapa pero no responde; sin mapa no hay respuesta")
    else:
        aud.falla(f"sugerencia de comuna [{etq}]", "no aparecieron sugerencias")
    page.fill("#q", "")

    # ------------------------------------------------------- las pestañas
    #
    # La primera contesta; la segunda respalda. Se comprueba que la respuesta
    # corta traiga veredicto y una razón, que el descargo se lea ANTES de
    # cualquier consulta, y que la evidencia completa siga estando entera —
    # simplificar no puede significar esconder de dónde sale el dato.
    page.evaluate("() => irAPestana('respuesta', false)")
    page.wait_for_timeout(200)
    if page.locator("#panel-detalle").is_hidden() and page.locator("#panel-respuesta").is_visible():
        aud.ok(f"parte en la pestaña de respuesta [{etq}]")
    else:
        aud.falla(f"pestaña inicial [{etq}]", "no arranca mostrando la respuesta")

    desc = page.locator(".descargo-fijo")
    if desc.count() and desc.is_visible():
        t = desc.inner_text().lower()
        falta = [x for x in ("no es información oficial", "no es un pronóstico")
                 if x not in t]
        if not falta:
            aud.ok(f"el descargo se lee antes de consultar [{etq}]")
        else:
            aud.falla(f"descargo permanente [{etq}]", f"le falta: {falta}")
    else:
        aud.falla(f"descargo permanente [{etq}]",
                  "no hay descargo visible antes de la primera consulta")

    page.evaluate("() => consultar(-72.5904, -38.7359, 'Auditoría pestañas')")
    page.wait_for_timeout(700)
    corto = page.locator("#respuesta").inner_text().lower()
    if len(corto) and "📍" in page.locator("#respuesta").inner_text():
        aud.ok(f"la respuesta corta muestra el punto consultado [{etq}]")
    else:
        aud.falla(f"respuesta corta [{etq}]", "no muestra la dirección consultada")
    if page.locator("#respuesta .por-que").count():
        aud.ok(f"la respuesta corta explica por qué [{etq}]")
    else:
        aud.falla(f"respuesta corta [{etq}]",
                  "da un veredicto sin decir en qué se basa")
    # La respuesta corta tiene que ser CORTA: si crece, deja de ser una respuesta
    # y vuelve a ser el expediente que se quiso mover a la otra pestaña.
    if len(corto) < 900:
        aud.ok(f"la respuesta corta se mantiene breve [{etq}]", f"{len(corto)} caracteres")
    else:
        aud.falla(f"respuesta corta [{etq}]",
                  f"creció a {len(corto)} caracteres; la evidencia va en la otra pestaña",
                  gravedad="media")

    page.locator("#btn-ver-detalle").click(timeout=3000)
    page.wait_for_timeout(300)
    if page.locator("#panel-detalle").is_visible():
        aud.ok(f"el botón lleva al detalle [{etq}]")
    else:
        aud.falla(f"botón ver detalle [{etq}]", "no cambia de pestaña")
    largo = page.locator("#detalle-ficha").inner_text()
    if len(largo) > len(corto) * 2:
        aud.ok(f"la evidencia completa sigue entera [{etq}]",
               f"{len(largo)} caracteres contra {len(corto)} del resumen")
    else:
        aud.falla(f"evidencia en el detalle [{etq}]",
                  f"el detalle tiene {len(largo)} caracteres: se perdió contenido")
    page.evaluate("() => irAPestana('respuesta', false)")
    page.wait_for_timeout(200)

    # -------------------------------------------- controles de capa clicables
    #
    # Viven dentro de un <details> plegado: la primera pestaña muestra sólo lo
    # necesario para obtener una respuesta. Se abre primero, que es exactamente
    # lo que hace una persona.
    plegable = page.locator("details.capas-plegable")
    if plegable.count():
        page.evaluate("() => document.querySelector('details.capas-plegable').open = true")
        aud.ok(f"las capas del mapa están plegadas por omisión [{etq}]")
    else:
        aud.falla(f"plegable de capas [{etq}]", "no existe details.capas-plegable")
    # Las capas van agrupadas y con su peso legal a la vista. Los 20 planos
    # publicados son ANTEPROYECTOS —propuestas en tramitación, sin efecto legal—
    # y el visor los describía como «Plano original del Plan Regulador» bajo una
    # capa que el sitio llama «la única con efecto jurídico». Si ese sello se
    # cae, se le vuelve a atribuir a una propuesta un peso que no tiene.
    grupos = page.locator(".grupo-capas").count()
    if grupos >= 4:
        aud.ok(f"las capas están agrupadas por tipo de evidencia [{etq}]", f"{grupos} grupos")
    else:
        aud.falla(f"agrupación de capas [{etq}]", f"sólo {grupos} grupo(s)")
    sello = page.locator("#cap-planos").locator("xpath=..").locator(".sello")
    if sello.count() and "anteproyecto" in sello.inner_text().lower():
        aud.ok(f"los planos se declaran anteproyecto en la leyenda [{etq}]")
    else:
        aud.falla(f"sello de tramitación [{etq}]",
                  "la capa de planos no dice que son anteproyectos")
    # La capa DERIVADA existe y va achurada, no rellena. Es lo que impide que
    # una geometría que construimos nosotros desde una figura impresa se lea
    # como el vectorial oficial. Y el inventario la anuncia por comuna: si el
    # archivo no estuviera publicado, el sitio prometería evidencia invisible.
    if page.evaluate("() => !!estado.laminas"):
        n = page.evaluate("() => estado.laminas.features.length")
        aud.ok(f"las láminas vectorizadas están publicadas [{etq}]", f"{n} polígonos")
        guiones = page.evaluate(
            "() => estado.mapa.getLayer('lam-line') && "
            "estado.mapa.getPaintProperty('lam-line','line-dasharray')")
        if guiones:
            aud.ok(f"la capa derivada se dibuja achurada [{etq}]")
        else:
            aud.falla(f"simbología de la capa derivada [{etq}]",
                      "se dibuja igual que la normativa; se leería como "
                      "instrumento legal sin serlo")
    else:
        aud.falla(f"láminas vectorizadas [{etq}]",
                  "el inventario las cuenta por comuna pero no están publicadas: "
                  "el sitio promete evidencia que no se puede ver")

    # --- La capa derivada tiene que llegar al VEREDICTO, no sólo al mapa -----
    #
    # Hasta el 7-sep-2026 estas comprobaciones no existían y por eso la
    # auditoría daba 273/273 mientras el visor respondía «no cae dentro de un
    # área de riesgo» a un punto dentro del AR-2a del plan regulador vigente de
    # Angol. Es el mismo error que se cometió con la capa B: agregar una capa
    # sin agregarle comprobaciones (REGLAS §4.1). La regla vale para lo que la
    # capa PROMETE —que el veredicto la use—, no para que el archivo exista.
    if page.evaluate("() => !!estado.laminas"):
        dentro = page.evaluate("""() => {
            for (const f of estado.laminas.features) {
              const g = f.geometry;
              if (!g || g.type !== 'Polygon') continue;
              // Punto interior de verdad: el centroide de un polígono cóncavo
              // puede caer fuera, así que se comprueba con el mismo ray-casting
              // que usa el veredicto.
              const anillo = g.coordinates[0];
              let sx = 0, sy = 0;
              for (const [x, y] of anillo) { sx += x; sy += y; }
              const c = [sx / anillo.length, sy / anillo.length];
              if (poligonosQueContienen(c[0], c[1], estado.laminas).length) return c;
            }
            return null;
        }""")
        if dentro:
            page.evaluate("([lon,lat]) => consultar(lon, lat, 'Auditoría lámina')", dentro)
            page.wait_for_timeout(700)
            titular = page.locator("#respuesta .veredicto h2").inner_text().lower()
            if "sin registros" in titular:
                aud.falla(f"la capa derivada entra al veredicto [{etq}]",
                          "dentro de una zona vectorizada del documento comunal el "
                          f"visor responde «{titular}»")
            else:
                aud.ok(f"la capa derivada entra al veredicto [{etq}]", titular[:60])
            page.evaluate("() => irAPestana('detalle', false)")
            page.wait_for_timeout(300)
            ficha = page.locator("#detalle-ficha").inner_text()
            if "A · DERIVADO" in ficha and "derivado" in ficha.lower():
                aud.ok(f"la ficha muestra la capa derivada y su sello [{etq}]")
            else:
                aud.falla(f"bloque de la capa derivada [{etq}]",
                          "el veredicto la usa pero la ficha no la explica ni "
                          "dice que el trazado es nuestro (REGLAS §1.5)")
            # Y el borde tiene que declarar su incertidumbre en metros.
            if "m de" in ficha and "incertidumbre" in ficha.lower():
                aud.ok(f"la capa derivada declara la incertidumbre del borde [{etq}]")
            else:
                aud.falla(f"incertidumbre del borde [{etq}]",
                          "la mancha se muestra sin decir cuánto puede moverse su borde")
        else:
            aud.falla(f"punto interior de una lámina [{etq}]",
                      "no se encontró ninguno: la comprobación no puede correr")

    # --- El texto que se reenvía tiene que llevar la advertencia -------------
    #
    # La ficha se comparte por WhatsApp y ahí «sin registros» queda solo. La
    # advertencia estaba en pantalla y no en el texto, por leer un campo que no
    # existía: en pantalla se veía bien y nadie lo notó durante semanas.
    page.evaluate("() => consultar(-72.7, -38.75, 'Auditoría texto compartido')")
    page.wait_for_timeout(700)
    nivel = page.evaluate("() => estado.ultimo && estado.ultimo.res.nivel")
    if nivel == "sindato":
        txt = page.evaluate("() => textoFicha()")
        if "no significa que acá no se inunde" in txt.lower():
            aud.ok(f"el texto compartido lleva la advertencia de «sin registros» [{etq}]")
        else:
            aud.falla(f"advertencia en el texto compartido [{etq}]",
                      "«sin registros» se reenvía sin el aviso de que no significa "
                      "que no se inunde: es la lectura al revés que el sitio "
                      "entero se esfuerza en evitar")
    else:
        aud.falla(f"punto sin registros para probar el texto [{etq}]",
                  f"el punto de control dio «{nivel}»; la comprobación no corre")
    # Se devuelve el estado que este bloque encontró (REGLAS §4.3): si queda
    # abierta la pestaña de detalle, el bloque siguiente no alcanza el buscador
    # ni las casillas de capas y falla por una razón que no es la suya.
    page.evaluate("() => irAPestana('respuesta', false)")
    page.wait_for_timeout(200)

    auditar_lo_que_dice_el_veredicto(page, aud, etq)

    for cid in ["cap-areas", "cap-derivadas", "cap-planos", "cap-puntos",
                "cap-camp", "cap-jrc", "cap-sar", "cap-gore"]:
        el = page.locator(f"#{cid}")
        if el.count() == 0:
            aud.falla(f"control #{cid} [{etq}]", "no existe en el DOM")
            continue
        try:
            # click() de Playwright falla si el elemento está tapado: es
            # exactamente la comprobación que se quiere.
            el.click(timeout=3000)
            el.click(timeout=3000)   # devolverlo a su estado
            aud.ok(f"control #{cid} clicable [{etq}]")
        except Exception as exc:
            aud.falla(f"control #{cid} [{etq}]",
                      f"no se puede hacer clic: {str(exc).splitlines()[0][:110]}")

    # --------------------------------------------------------- sugerencias
    #
    # Las sugerencias de comuna salen de datos ya cargados, así que tienen que
    # aparecer aunque no haya red: es justamente la condición en que este visor
    # se usa. Se prueban SIN depender de Nominatim.
    page.fill("#q", "temu")
    page.wait_for_timeout(350)
    sug = page.locator("#sugerencias li")
    if sug.count() > 0:
        aud.ok(f"sugerencias al escribir [{etq}]", f"{sug.count()} opciones")
        # navegación por teclado
        page.focus("#q")
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(120)
        if page.locator("#sugerencias li.activa").count() == 1:
            aud.ok(f"sugerencias navegables con teclado [{etq}]")
        else:
            aud.falla(f"sugerencias con teclado [{etq}]",
                      "ArrowDown no marca ninguna opción", gravedad="media")
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        if page.locator("#sugerencias").evaluate("e => e.classList.contains('oculto')"):
            aud.ok(f"Escape cierra las sugerencias [{etq}]")
        else:
            aud.falla(f"Escape no cierra las sugerencias [{etq}]", "", gravedad="baja")
    else:
        aud.falla(f"sugerencias [{etq}]",
                  "escribir «temu» no ofrece ninguna comuna, y eso no depende de la red")
    page.fill("#q", "")
    page.wait_for_timeout(150)

    # ------------------------------------------------------ búsqueda + ficha
    #
    # El punto se elige DENTRO de la huella de un plano georreferenciado, para
    # que la ficha ejercite también el botón "ver el plano sobre el mapa". Elegir
    # el centroide de un área de riesgo cualquiera dejaba ese camino sin probar
    # y producía un falso hallazgo.
    p = page.evaluate("""() => {
        const pl = estado.planos[0];
        const [w, s, e, n] = pl.bounds_wgs84;
        return [(w + e) / 2, (s + n) / 2];
    }""")
    page.evaluate("([lon,lat]) => consultar(lon, lat, 'Auditoría')", p)
    page.wait_for_timeout(900)

    # La evidencia completa está en la segunda pestaña; hay que abrirla para
    # poder leerla, igual que una persona.
    page.evaluate("() => irAPestana('detalle', false)")
    page.wait_for_timeout(200)
    ficha = page.locator("#detalle-ficha")
    if ficha.is_visible():
        aud.ok(f"ficha de respuesta [{etq}]")
        # Se compara en minúsculas: los encabezados llevan text-transform:
        # uppercase, así que el texto renderizado no coincide con el del código.
        texto = ficha.inner_text().lower()
        for imprescindible in ["fuente:", "año:", "plan regulador",
                               "senapred", "modelo global", "observado"]:
            if imprescindible in texto:
                aud.ok(f"ficha declara «{imprescindible}» [{etq}]")
            else:
                aud.falla(f"ficha sin «{imprescindible}» [{etq}]",
                          "cada capa debe aparecer con su fuente y su año",
                          gravedad="alta")
        page.screenshot(path=str(CAPTURAS / f"02_ficha_{etq}.png"))

    else:
        aud.falla(f"ficha de respuesta [{etq}]", "no se mostró tras consultar un punto")

    # -------------------------------- capa A: qué dice sobre el efecto legal
    #
    # «No prohíbe construir, condiciona» no es un matiz de redacción: es lo que dice
    # la OGUC 2.1.17, que permite autorizar proyectos en área de riesgo con estudio
    # fundado de un profesional especialista y obras de mitigación. Un visor que
    # deje entender que el área de riesgo prohíbe estaría informando mal sobre el
    # efecto de una norma, que es el peor error que puede cometer.
    #
    # Va aparte porque sólo se puede comprobar sobre un punto que CAIGA dentro de un
    # área de riesgo, y el punto de prueba general no cae. Comprobarlo en el bloque
    # general daba un hallazgo falso que acusaba al visor de un error de la prueba.
    if page.evaluate("() => !!(estado.areasRiesgo && estado.areasRiesgo.features.length)"):
        centro_ar = page.evaluate("""() => {
            const g = estado.areasRiesgo.features[0].geometry;
            const anillo = g.type === 'MultiPolygon' ? g.coordinates[0][0]
                                                     : g.coordinates[0];
            let x = 0, y = 0;
            for (const [a, b] of anillo) { x += a; y += b; }
            return [x / anillo.length, y / anillo.length];
        }""")
        page.evaluate("([lon,lat]) => consultar(lon, lat, 'Auditoría área de riesgo')",
                      centro_ar)
        page.wait_for_timeout(900)
        t = page.locator("#detalle-ficha").inner_text().lower()
        if "no prohíbe construir" in t:
            aud.ok(f"la ficha explica que el área de riesgo condiciona, no prohíbe [{etq}]")
        else:
            aud.falla(f"efecto legal mal explicado [{etq}]",
                      "la ficha de un punto dentro de área de riesgo no dice que la "
                      "OGUC 2.1.17 permite construir con estudio fundado y mitigación")

    # Encender y apagar todo de una vez: comparar «lo que dice la norma» contra
    # «lo que se midió» es el gesto más útil del visor y a mano son siete toques.
    page.evaluate("() => irAPestana('respuesta', false)")
    page.evaluate("() => document.querySelector('details.capas-plegable').open = true")
    page.wait_for_timeout(200)
    page.locator("#btn-capas-todas").click(timeout=3000)
    page.wait_for_timeout(400)
    prendidas = page.evaluate(
        "() => ['cap-areas','cap-derivadas','cap-planos','cap-sar','cap-gore',"
        "'cap-jrc','cap-puntos','cap-camp']"
        ".filter(i => document.getElementById(i).checked).length")
    if prendidas == 8:
        aud.ok(f"«encender todo» prende las 8 capas [{etq}]")
    else:
        aud.falla(f"encender todo [{etq}]", f"quedaron {prendidas} de 8")
    page.locator("#btn-capas-ninguna").click(timeout=3000)
    page.wait_for_timeout(400)
    apagadas = page.evaluate(
        "() => ['cap-areas','cap-derivadas','cap-planos','cap-sar','cap-gore',"
        "'cap-jrc','cap-puntos','cap-camp']"
        ".filter(i => !document.getElementById(i).checked).length")
    if apagadas == 8:
        aud.ok(f"«apagar todo» apaga las 8 capas [{etq}]")
    else:
        aud.falla(f"apagar todo [{etq}]", f"quedaron {8 - apagadas} encendidas")
    # Restaurar el estado inicial por ESTADO, no por clic.
    #
    # Restaurar clicando dependía de que las casillas siguieran visibles y
    # alcanzables en ese momento, y no siempre lo están: el bloque anterior
    # cambia de pestaña y despliega paneles. Un clic que se cae acá tumba la
    # auditoría entera por un detalle de limpieza, no por un defecto del visor.
    page.evaluate("""
        () => { for (const [id, v] of [['cap-areas', true], ['cap-puntos', true]]) {
            const el = document.getElementById(id);
            if (el && el.checked !== v) { el.checked = v;
                el.dispatchEvent(new Event('change')); } } }
    """)
    page.wait_for_timeout(200)

    # ------------------------------------------- los dos mapas base
    #
    # Los bloques anteriores dejan abierta la pestaña de detalle. Cada bloque
    # deja el estado que necesita en vez de heredarlo: si no, el orden de las
    # comprobaciones cambia el resultado y la auditoría se vuelve frágil.
    page.evaluate("() => irAPestana('respuesta', false)")
    page.evaluate("() => document.querySelector('details.capas-plegable').open = true")
    page.wait_for_timeout(200)
    #
    # El satelital existe para ver el suelo real bajo la mancha. Se comprueba
    # que el cambio ocurra en el MAPA —visibilidad de la capa ráster— y no sólo
    # que el control se marque, que es lo que un botón roto también hace.
    vis = page.evaluate(
        "() => ({osm: estado.mapa.getLayoutProperty('osm','visibility'),"
        " sat: estado.mapa.getLayoutProperty('sat','visibility')})")
    if vis["osm"] == "visible" and vis["sat"] == "none":
        aud.ok(f"parte con el mapa base de calles [{etq}]")
    else:
        aud.falla(f"mapa base inicial [{etq}]", f"visibilidad inesperada: {vis}")

    page.locator("#base-satelite").click(timeout=3000)
    page.wait_for_timeout(300)
    vis = page.evaluate(
        "() => ({osm: estado.mapa.getLayoutProperty('osm','visibility'),"
        " sat: estado.mapa.getLayoutProperty('sat','visibility'),"
        " clase: document.body.classList.contains('base-satelite')})")
    if vis["sat"] == "visible" and vis["osm"] == "none":
        aud.ok(f"cambia a imagen satelital [{etq}]")
    else:
        aud.falla(f"cambio a satelital [{etq}]", f"visibilidad inesperada: {vis}")
    if vis["clase"]:
        aud.ok(f"marca el cuerpo para aclarar la escala sobre la imagen [{etq}]")
    else:
        aud.falla(f"contraste sobre satelital [{etq}]",
                  "falta la clase base-satelite; escala y atribución quedan ilegibles")

    # Las capas de datos tienen que seguir por ENCIMA del nuevo base: si se
    # perdieran al cambiar de fondo, el visor dejaría de responder justo cuando
    # alguien quiere mirar el terreno.
    capas_ahora = page.evaluate("() => estado.mapa.getStyle().layers.map(l => l.id)")
    faltan = [c for c in ("pc-circ", "ar-fill") if c not in capas_ahora]
    if not faltan:
        aud.ok(f"las capas de datos sobreviven al cambio de base [{etq}]")
    else:
        aud.falla(f"capas tras cambiar de base [{etq}]", f"desaparecieron: {faltan}")

    page.locator("#base-calles").click(timeout=3000)
    page.wait_for_timeout(200)

    # --------------------------------------- el prototipo está acotado
    #
    # Dos afirmaciones distintas y las dos importan:
    #   1. no se puede salir de la región desplazando el mapa;
    #   2. si igual llega una coordenada de afuera —GPS de otra región, enlace
    #      compartido, consola—, la respuesta dice «no sé», no «sin registros».
    # La segunda es la que hace daño si se rompe: una ficha vacía sobre Santiago
    # se lee como que Santiago no se inunda.
    lim = page.evaluate("() => estado.mapa.getMaxBounds() && "
                        "estado.mapa.getMaxBounds().toArray()")
    if lim:
        aud.ok(f"el mapa no deja salir de la región [{etq}] — "
               f"{lim[0][0]:.1f}…{lim[1][0]:.1f} lon")
    else:
        aud.falla(f"el mapa se puede desplazar fuera de la región [{etq}]",
                  "sin maxBounds se puede llegar a cualquier punto del país y "
                  "tocarlo, y ahí el visor responde por una región que no cubre")

    # Santiago: bien lejos del bbox, y el caso que de verdad va a ocurrir.
    page.evaluate("() => consultar(-70.65, -33.44, 'Auditoría fuera de alcance')")
    # Esperar el CONTENIDO, no un tiempo fijo. Con `wait_for_timeout` la
    # comprobación siguiente alcanzaba a leer la ficha anterior y el resultado
    # cambiaba entre corridas: una prueba intermitente esconde más de lo que
    # descubre.
    page.wait_for_function(
        "() => document.querySelector('#respuesta').innerText"
        ".toLowerCase().includes('fuera del alcance')", timeout=5000)
    t_fuera = page.locator("#respuesta").inner_text().lower()
    if "fuera del alcance" in t_fuera:
        aud.ok(f"un punto fuera de la región se declara fuera de alcance [{etq}]")
    else:
        aud.falla(f"punto fuera de la región no se declara [{etq}]",
                  f"la ficha de un punto en Santiago dice: {t_fuera[:120]!r}")
    if "no dice nada sobre el riesgo de ese lugar" in t_fuera:
        aud.ok(f"fuera de alcance NO se confunde con ausencia de riesgo [{etq}]")
    else:
        aud.falla(f"fuera de alcance se puede leer como «sin riesgo» [{etq}]",
                  "la respuesta para un punto de otra región no aclara que la "
                  "falta de dato no dice nada sobre su riesgo")

    # Se vuelve a un punto de la región: las comprobaciones que siguen operan
    # sobre la ficha, y quedarían mirando la de fuera de alcance.
    page.evaluate("() => consultar(-72.5904, -38.7359, 'Auditoría Temuco')")
    page.wait_for_function(
        "() => !document.querySelector('#respuesta').innerText"
        ".toLowerCase().includes('fuera del alcance')", timeout=5000)

    # ------------------------------------- el descargo de cómo leer un mapa
    #
    # Va comprobado, y no por formalismo. Es el texto que evita las dos lecturas
    # que hacen daño de verdad: creer que un mapa de amenaza pronostica la
    # próxima inundación, y creer que quedar del lado de afuera del borde
    # significa estar a salvo. Si alguien lo acorta «para que no asuste», esto
    # tiene que caerse.
    afirmaciones = {
        "no es un pronóstico": "predice la próxima inundación",
        "los métodos no son comparables": "no son comparables entre sí",
        "el estudio fundado tiene otro peso": "estudio fundado de riesgo",
        "el borde es lo más incierto": "mira la mancha, no su borde",
        "un mapa envejece": "un mapa envejece",
    }
    # Vive en la pestaña de detalle: oculta, `inner_text()` devuelve vacío y la
    # comprobación se acusaría a sí misma.
    page.evaluate("() => irAPestana('detalle', false)")
    page.wait_for_timeout(200)
    t_leer = page.locator("#como-leer").inner_text().lower()
    for nombre, aguja in afirmaciones.items():
        if aguja in t_leer:
            aud.ok(f"descargo dice que {nombre} [{etq}]")
        else:
            aud.falla(f"descargo incompleto: falta que {nombre} [{etq}]",
                      f"«{aguja}» no aparece en la sección «Cómo leer un mapa de "
                      "inundación»")

    # Y el cierre de la ficha, que es donde la gente sí lee: no sirve de nada que
    # el descargo esté al fondo de la página si la respuesta no lo menciona.
    t_ficha = page.locator("#detalle-ficha").inner_text().lower()
    if "mira la mancha, no su borde" in t_ficha:
        aud.ok(f"la ficha cierra recordando que el borde es lo incierto [{etq}]")
    else:
        aud.falla(f"la ficha no lleva el cierre del descargo [{etq}]",
                  "la respuesta termina sin decir que ninguno de estos mapas es un "
                  "pronóstico ni que el borde es lo más incierto")

    # ------------------------------------------- capa B en sus TRES estados
    #
    # La capa B es la única que puede decir «el agua llegó hasta acá», y por eso
    # es la que más daño hace si miente. Sus tres estados son afirmaciones
    # distintas y hay que ejercitarlos por separado:
    #   1. dentro de la huella          -> vio agua, con fecha
    #   2. observado y sin agua         -> miró y no vio, CON las limitaciones
    #   3. fuera de la cobertura        -> no miró: no observado ≠ no inundado
    # El estado 3 es el que sostiene la regla 5 del proyecto, y es justo el que
    # un visor descuidado convierte en un silencio que se lee como «acá no pasa
    # nada».
    if page.evaluate("() => !!(estado.sar && estado.sar.features.length)"):
        centro = page.evaluate("""() => {
            const anillo = estado.sar.features[0].geometry.coordinates[0];
            let x = 0, y = 0;
            for (const [a, b] of anillo) { x += a; y += b; }
            return [x / anillo.length, y / anillo.length];
        }""")
        page.evaluate("([lon,lat]) => consultar(lon, lat, 'Auditoría huella')", centro)
        page.wait_for_timeout(900)
        t = page.locator("#respuesta").inner_text().lower()
        if "el agua llegó" in t or "detectó agua" in t:
            aud.ok(f"capa B declara agua observada [{etq}]")
        else:
            aud.falla(f"capa B dentro de la huella [{etq}]",
                      "se consultó el centro de un polígono de huella y la ficha "
                      "no afirma que se observó agua")
        # Una huella sin fecha no sirve para nada: es la propiedad que la
        # distingue de un modelo.
        if any(m in t for m in ["agosto", "2026-08", "de 2026"]):
            aud.ok(f"la huella declara su fecha de pasada [{etq}]")
        else:
            aud.falla(f"huella sin fecha [{etq}]",
                      "la capa observada tiene que decir CUÁNDO pasó el satélite")
        page.screenshot(path=str(CAPTURAS / f"02b_ficha_sar_{etq}.png"))
    else:
        aud.falla(f"capa B ausente [{etq}]",
                  "no se cargó data/sar/huella-observada.geojson", gravedad="media")

    if page.evaluate("() => !!estado.sarCobertura"):
        # Un punto lejos del área observada: mar adentro no sirve porque el
        # visor podría no responder, así que se usa el extremo nororiental de
        # la región, donde ningún track del evento alcanzó.
        page.evaluate("([lon,lat]) => consultar(lon, lat, 'Auditoría sin cobertura')",
                      [-71.0, -37.5])
        page.wait_for_timeout(900)
        page.evaluate("() => irAPestana('detalle', false)")
        t = page.locator("#detalle-ficha").inner_text().lower()
        if "no pasó" in t or "no observado" in t or "no miró" in t:
            aud.ok(f"capa B distingue «no observado» de «no inundado» [{etq}]")
        else:
            aud.falla(f"capa B fuera de cobertura [{etq}]",
                      "un punto que el satélite no miró tiene que decirlo; el "
                      "silencio se lee como ausencia de riesgo")

    # Devolver la ficha al punto del plano. Las comprobaciones que siguen dan por
    # hecho que la consulta vigente es ésa, y dejarla en otra hacía fallar el
    # botón del plano — un hallazgo de la propia prueba, no del visor, que es
    # exactamente el error que la regla 10 del proyecto manda evitar.
    page.evaluate("([lon,lat]) => consultar(lon, lat, 'Auditoría')", p)
    page.wait_for_timeout(900)

    # ------------------------------------------------ plano sobre el mapa
    page.evaluate("() => irAPestana('detalle', false)")
    page.wait_for_timeout(200)
    btn = page.locator("#btn-plano")
    if btn.count():
        try:
            btn.click(timeout=4000)
            # Por contenido, no por tiempo (REGLAS §4.4): en móvil el fitBounds
            # y la carga de teselas a veces pasaban de los 3,5 s fijos.
            try:
                page.wait_for_function(
                    "() => estado.mapa.getStyle().layers.some(l => l.id.startsWith('plano-'))",
                    timeout=12000)
            except Exception:
                pass   # se informa abajo como falla, con su mensaje
            capas2 = page.evaluate("() => estado.mapa.getStyle().layers.map(l => l.id)")
            planos = [c for c in capas2 if c.startswith("plano-")]
            if planos:
                aud.ok(f"plano se agrega al mapa [{etq}]", f"{len(planos)} capa(s)")
                page.screenshot(path=str(CAPTURAS / f"03_plano_{etq}.png"))
            else:
                aud.falla(f"plano sobre el mapa [{etq}]",
                          "se pulsó el botón y no se agregó ninguna capa de imagen")
        except Exception as exc:
            aud.falla(f"botón ver plano [{etq}]", str(exc).splitlines()[0][:110])
    else:
        aud.falla(f"botón ver plano [{etq}]",
                  "no apareció aunque el punto cae dentro de un plano",
                  gravedad="media")

    # ------------------------------------- TODAS las imágenes de plano cargan
    #
    # Se comprueban las 23, no una. Probar sólo `planos[0]` dejó pasar durante
    # toda una ronda que los 14 planos de comunas con tilde devolvían 404: el
    # primero de la lista era Galvarino, sin tilde. Una capa de imagen que no
    # carga no da error — se ve vacía.
    faltantes = page.evaluate("""async () => {
        const malos = [];
        for (const p of (estado.planos || [])) {
            const r = await fetch('data/planos/' + encodeURIComponent(p.archivo),
                                  { method: 'HEAD' });
            if (!r.ok) malos.push(p.archivo + ' → HTTP ' + r.status);
        }
        return { total: (estado.planos || []).length, malos };
    }""")
    if faltantes["malos"]:
        aud.falla(f"imágenes de plano [{etq}]",
                  f"{len(faltantes['malos'])} de {faltantes['total']} no cargan: "
                  + "; ".join(faltantes["malos"][:3]))
    else:
        aud.ok(f"las {faltantes['total']} imágenes de plano cargan [{etq}]")

    # ------------------------------------------------------------ catálogo
    page.goto(f"{base}/documentos.html", wait_until="networkidle")
    page.wait_for_timeout(1200)
    n = page.locator("details.comuna").count()
    if n > 0:
        aud.ok(f"catálogo lista comunas [{etq}]", f"{n} comunas")
        page.fill("#q", "temuco")
        page.wait_for_timeout(400)
        if page.locator("details.comuna").count() >= 1:
            aud.ok(f"filtro del catálogo [{etq}]")
        else:
            aud.falla(f"filtro del catálogo [{etq}]", "buscar 'temuco' no devuelve nada")
        page.screenshot(path=str(CAPTURAS / f"04_catalogo_{etq}.png"), full_page=False)
    else:
        aud.falla(f"catálogo [{etq}]", "no renderizó ninguna comuna")

    # Texto roto por valores ausentes: "undefined", "null", o frases que quedan
    # cortadas cuando se concatena un dato que no existe ("... ambiental el ·").
    page.locator("details.comuna").first.evaluate("e => e.open = true")
    page.wait_for_timeout(250)
    visible = page.locator("main").inner_text()
    sucios = [m for m in ["undefined", "null", "NaN", " el ·", " el\n", "· ·"]
              if m in visible]
    if sucios:
        aud.falla(f"texto con huecos [{etq}]",
                  f"se muestran valores ausentes o frases cortadas: {sucios}",
                  gravedad="media")
    else:
        aud.ok(f"sin texto roto por datos ausentes [{etq}]")

    # ---------------------------------------------------- layout y errores
    desborde = page.evaluate(
        "() => document.body.scrollWidth > window.innerWidth + 1 "
        "? document.body.scrollWidth : 0")
    if desborde:
        aud.falla(f"layout [{etq}]",
                  f"la página desborda horizontalmente ({desborde}px > {'375' if movil else '1280'})")
    else:
        aud.ok(f"sin desborde horizontal [{etq}]")

    # ---------------------------------------------------------- contraste
    page.goto(f"{base}/index.html", wait_until="networkidle")
    page.wait_for_timeout(1200)
    pares = page.evaluate("""() => {
        const sel = ['body', '.cifra-txt', '.incert', '.eyebrow', '.chip',
                     '.capas-titulo', '.fila-comuna .cr', '.sub'];
        return sel.map(s => { const el = document.querySelector(s); if (!el) return null;
          const cs = getComputedStyle(el);
          let fondo = cs.backgroundColor, n = el;
          while (fondo === 'rgba(0, 0, 0, 0)' && n.parentElement) {
            n = n.parentElement; fondo = getComputedStyle(n).backgroundColor; }
          return { sel: s, texto: cs.color, fondo,
                   px: parseFloat(cs.fontSize), peso: cs.fontWeight };
        }).filter(Boolean);
    }""")
    for p in pares:
        # WCAG AA: 4.5:1 para texto normal, 3:1 para texto grande (>=18.66px
        # normal o >=24px). Se aplica el umbral que corresponda.
        grande = p["px"] >= 24 or (p["px"] >= 18.66 and int(p["peso"]) >= 700)
        minimo = 3.0 if grande else 4.5
        c = contraste(p["fondo"], p["texto"])
        if c >= minimo:
            aud.ok(f"contraste {p['sel']} [{etq}]", f"{c:.1f}:1")
        else:
            aud.falla(f"contraste {p['sel']} [{etq}]",
                      f"{c:.1f}:1, bajo el mínimo AA de {minimo}:1 "
                      f"({p['px']:.0f}px) — texto difícil de leer")

    if errores_js:
        aud.falla(f"errores de JavaScript [{etq}]", "; ".join(errores_js[:3]))
    else:
        aud.ok(f"sin errores de JavaScript [{etq}]")

    # Los tiles que se cancelan al mover el mapa (ERR_ABORTED sobre
    # tile.openstreetmap.org) son comportamiento normal de MapLibre, no un fallo:
    # aborta las peticiones de teselas que dejaron de ser visibles.
    reales = [f for f in fallos_red
              if "favicon" not in f.lower() and "ERR_ABORTED" not in f]
    if reales:
        aud.falla(f"recursos que fallan [{etq}]", "; ".join(sorted(set(reales))[:4]),
                  gravedad="media")
    else:
        aud.ok(f"todos los recursos cargan [{etq}]")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="auditar un servidor ya levantado")
    ap.add_argument("--ver", action="store_true", help="mostrar la ventana del navegador")
    ap.add_argument("--solo", choices=["escritorio", "movil"])
    a = ap.parse_args()

    httpd = None
    if a.url:
        base = a.url.rstrip("/")
    else:
        base, httpd = servir(WEB)
        print(f"servidor de auditoría en {base}")

    aud = Auditoria()
    try:
        with sync_playwright() as pw:
            navegador = pw.chromium.launch(headless=not a.ver)
            perfiles = []
            if a.solo != "movil":
                perfiles.append(({"viewport": {"width": 1280, "height": 860}}, False))
                # El tema oscuro es la mitad del diseño y hasta ahora no se
                # estaba mirando nunca: se audita como un perfil más.
                perfiles.append(({"viewport": {"width": 1280, "height": 860},
                                  "color_scheme": "dark"}, False))
            if a.solo != "escritorio":
                perfiles.append(({"viewport": {"width": 375, "height": 812},
                                  "is_mobile": True, "has_touch": True,
                                  "device_scale_factor": 2}, True))
            for kwargs, movil in perfiles:
                oscuro = kwargs.get("color_scheme") == "dark"
                print(f"\n--- {'MÓVIL' if movil else 'ESCRITORIO'}"
                      f"{' OSCURO' if oscuro else ''} ---")
                ctx = navegador.new_context(**kwargs)
                page = ctx.new_page()
                try:
                    auditar(page, aud, base, movil, oscuro)
                finally:
                    ctx.close()
            navegador.close()
    finally:
        if httpd:
            httpd.shutdown()

    (CAPTURAS / "hallazgos.json").write_text(
        json.dumps({"hallazgos": aud.hallazgos, "ok": aud.pasos},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    n = aud.resumen()
    print(f"\ncapturas en {CAPTURAS}")
    sys.exit(1 if n else 0)


if __name__ == "__main__":
    main()
