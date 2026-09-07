"""Segunda tanda del verificador: 103, 104 en 'sindato', 107, 110, 116, 117,
118, 214/223 (sin red) y 106 (geocodificador). Sólo lee.
"""
import json
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8795"
TEMUCO_CENTRO = (-72.5904, -38.7359)      # Plaza Aníbal Pinto, Temuco
LEJOS = (-71.60, -38.20)                  # cordillera, sin registros cerca
CARAHUE_AR = (-73.142903, -38.702816)


def txt(page, sel):
    el = page.query_selector(sel)
    return (el.inner_text() if el else "").strip()


def consultar(page, lon, lat, etq):
    page.evaluate(f"() => consultar({lon}, {lat}, {json.dumps(etq)})")
    page.wait_for_timeout(700)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errores = []
    page.on("pageerror", lambda e: errores.append(str(e)))
    page.goto(f"{BASE}/index.html", wait_until="networkidle")
    page.wait_for_function("() => !!window.estado && !!estado.puntos", timeout=30000)

    print("### 103/604 — comuna atribuida en el centro de Temuco")
    consultar(page, *TEMUCO_CENTRO, "Plaza de Temuco")
    d = txt(page, "#detalle-ficha")
    i = d.find("Con qué cuenta")
    print("  ", d[i:i+90].replace("\n", " "))
    print("  comunaDe ->", page.evaluate(
        f"() => {{const c = comunaDe(evaluar({TEMUCO_CENTRO[0]},{TEMUCO_CENTRO[1]}),"
        f"{TEMUCO_CENTRO[0]},{TEMUCO_CENTRO[1]}); return c && [c.comuna, c._km];}}"))
    print("  Temuco en estado-comunas ->", page.evaluate(
        "() => { const t = estado.estadoComunas.find(c=>c.comuna==='Temuco');"
        "return [t.puntos_inundacion, t.poligonos_area_riesgo, t.le_falta]; }"))

    print("\n### 107 — línea de atribución cuando el punto NO cae en un área")
    j = d.find("Fuente:")
    print("  ", d[j:j+150].replace("\n", " "))
    print("  features[0] de la capa:", page.evaluate(
        "() => { const p = estado.areasRiesgo.features[0].properties;"
        "return [p.comuna, p.anio, p.anio_fuente]; }"))

    print("\n### 104/202 — texto compartido de un punto SIN registros")
    consultar(page, *LEJOS, "Cordillera")
    print("  veredicto:", txt(page, "#respuesta h2"))
    print("  nivel:", page.evaluate("() => estado.ultimo.res.nivel"),
          "· estado.ultimo.nivel:", page.evaluate("() => String(estado.ultimo.nivel)"))
    t = page.evaluate("() => textoFicha()")
    print("  ¿el texto compartido trae el 'OJO:'?", "OJO:" in t)
    print("  texto completo:\n" + "\n".join("    " + x for x in t.splitlines()))

    print("\n### 110 — elegir la comuna ANGOL en las sugerencias")
    page.evaluate("() => zoomComuna(estado.comunas.comunas.find(c=>c.comuna==='ANGOL'))")
    page.wait_for_timeout(700)
    print("  veredicto:", txt(page, "#respuesta h2"))
    print("  dirección:", txt(page, "#respuesta .direccion"))
    print("  por qué  :", txt(page, "#respuesta .por-que"))

    print("\n### 602 — ¿la ficha de un punto nombra alguna vez la capa derivada?")
    print("  ocurrencias de 'AR-2a' en la ficha:", txt(page, "#detalle-ficha").count("AR-2a"))
    print("  ocurrencias de 'vectorizamos' (bloque comuna):",
          txt(page, "#detalle-ficha").count("vectorizamos"))

    print("\n### 116 — mensaje de #estado pegado tras cambiar de acción")
    page.evaluate("() => { elEstado().textContent = 'Mostrando 3 de 7 planos; acerca más para el resto.'; }")
    consultar(page, *CARAHUE_AR, "Carahue")
    print("  #estado tras una consulta nueva:", repr(txt(page, "#estado")))
    page.evaluate("() => { elEstado().textContent = 'No hay planos de plan regulador en esta zona.'; }")
    page.evaluate("() => document.getElementById('cap-jrc').click()")
    page.wait_for_timeout(300)
    print("  #estado tras encender la capa JRC:", repr(txt(page, "#estado")))

    print("\n### 117 — clic sobre el polígono de área de riesgo")
    r = page.evaluate("""() => new Promise(res => {
      const m = estado.mapa;
      m.jumpTo({center: [-73.142903, -38.702816], zoom: 15});
      m.once('idle', () => {
        document.querySelector('#respuesta').innerHTML = '';
        const p = m.project([-73.142903, -38.702816]);
        const hit = m.queryRenderedFeatures(p, {layers: ['ar-fill']}).length;
        m.fire('click', {lngLat: {lng: -73.142903, lat: -38.702816}, point: p,
                         originalEvent: new MouseEvent('click')});
        setTimeout(() => res({
          featuresBajoElDedo: hit,
          popupsAbiertos: document.querySelectorAll('.maplibregl-popup').length,
          respuestaRepintada: document.querySelector('#respuesta').innerText.slice(0, 60)
        }), 900);
      });
    })""")
    print("  ", r)

    print("\n### 214/223 — sin red")
    page.wait_for_timeout(1200)
    print("  service worker:", page.evaluate(
        "() => navigator.serviceWorker.controller ? 'activo' : 'sin controlador'"))
    ctx.set_offline(True)
    for etq, u in [("PNG de plano", "data/planos/04_Anteproyecto-Planos_PRC_Vilcun_p001.png"),
                   ("tesela Esri", "https://server.arcgisonline.com/ArcGIS/rest/services/"
                                   "World_Imagery/MapServer/tile/12/2400/1300"),
                   ("json inexistente", "data/no-existe.json")]:
        r = page.evaluate("""async (u) => {
          try { const r = await fetch(u); const t = await r.clone().text().catch(()=> '');
            return {ok: r.ok, status: r.status, tipo: r.headers.get('content-type'),
                    empieza: t.slice(0, 48)}; }
          catch (e) { return {error: String(e)}; }
        }""", u)
        print(f"  {etq} ->", r)
    ctx.set_offline(False)

    print("\n### 106/217 — geocodificador")
    r = page.evaluate("""async () => {
      try {
        const h = await geocodificar('Balmaceda 500, Temuco');
        return h;
      } catch (e) { return {error: String(e)}; }
    }""")
    print("  geocodificar('Balmaceda 500, Temuco') ->", r)

    print("\n### 111 — ¿responde la URL de ordenanza?")
    print("  polígonos con ordenanza_url:", page.evaluate(
        "() => estado.areasRiesgo.features.filter(f=>f.properties.ordenanza_url).length"))
    print("  URL:", page.evaluate(
        "() => [...new Set(estado.areasRiesgo.features.map(f=>f.properties.ordenanza_url)"
        ".filter(Boolean))]"))
    print("  ordenanza_url_vigente:", page.evaluate(
        "() => estado.areasRiesgo.features.filter(f=>f.properties.ordenanza_url_vigente).length"))

    print("\n### errores de JavaScript:", errores)
    b.close()
