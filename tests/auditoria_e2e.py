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

    # ------------------------------------- lo que arregló la auditoría
    #
    # Cuatro fallas que no daban error y se manifestaban como «el sitio no hace
    # nada» o «acá no hay dato». Cada una con su comprobación, porque un arreglo
    # sin prueba se deshace solo en el siguiente cambio.

    # (a) Los planos se LIBERAN al apagarlos, no se ocultan: cada uno es una
    #     textura de ~870 KB en memoria de video y se acumulaban al panear.
    page.evaluate("() => irAPestana('respuesta', false)")
    page.evaluate("() => document.querySelector('details.capas-plegable').open = true")
    page.wait_for_timeout(200)
    # Hay que ACERCARSE primero: los planos sólo se cargan desde zoom 11, así que
    # comprobar la liberación a escala regional pasaría sin haber cargado ninguno
    # —«0 capas → 0 capas»— y no probaría nada.
    page.evaluate("() => { const p = estado.planos && estado.planos[0]; "
                  "if (!p) return; const b = p.bounds_wgs84; "
                  "estado.mapa.jumpTo({center: [(b[0]+b[2])/2, (b[1]+b[3])/2], "
                  "zoom: 13}); }")
    page.wait_for_timeout(600)
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
    for cid in ["cap-areas", "cap-planos", "cap-puntos", "cap-camp", "cap-jrc",
                "cap-sar", "cap-gore"]:
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
        "() => ['cap-areas','cap-planos','cap-sar','cap-gore','cap-jrc','cap-puntos',"
        "'cap-camp'].filter(i => document.getElementById(i).checked).length")
    if prendidas == 7:
        aud.ok(f"«encender todo» prende las 7 capas [{etq}]")
    else:
        aud.falla(f"encender todo [{etq}]", f"quedaron {prendidas} de 7")
    page.locator("#btn-capas-ninguna").click(timeout=3000)
    page.wait_for_timeout(400)
    apagadas = page.evaluate(
        "() => ['cap-areas','cap-planos','cap-sar','cap-gore','cap-jrc','cap-puntos',"
        "'cap-camp'].filter(i => !document.getElementById(i).checked).length")
    if apagadas == 7:
        aud.ok(f"«apagar todo» apaga las 7 capas [{etq}]")
    else:
        aud.falla(f"apagar todo [{etq}]", f"quedaron {7 - apagadas} encendidas")
    page.locator("#cap-areas").click(timeout=3000)
    page.locator("#cap-puntos").click(timeout=3000)   # volver al estado inicial

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
            page.wait_for_timeout(3500)
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
