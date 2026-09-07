"""Reproducción en navegador real de los síntomas del visor (verificador,
auditoría 2026-09-06). Sólo lee; no cambia nada del sitio.

Levantar antes:  python -m http.server 8795 --directory web
"""
import json, sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8795"
ANGOL_AR2A = (-72.6867, -37.784993)      # dentro del AR-2a vigente del PRC de Angol
TEMUCO_ANEG = (-72.609107, -38.713381)   # polígono MINVU de ANEGAMIENTO
TOLTEN_LITORAL = (-73.196158, -39.395615)
MAR = (-73.65, -38.9)                    # océano, dentro del bbox de la región


def txt(page, sel):
    el = page.query_selector(sel)
    return (el.inner_text() if el else "").strip()


def consultar(page, lon, lat, etq):
    page.evaluate(f"() => consultar({lon}, {lat}, {json.dumps(etq)})")
    page.wait_for_timeout(700)


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        errores = []
        page.on("pageerror", lambda e: errores.append(str(e)))
        page.goto(f"{BASE}/index.html", wait_until="networkidle")
        page.wait_for_function("() => !!window.estado && !!estado.puntos", timeout=30000)

        print("### 102 — botón Buscar")
        page.fill("#q", "Balmaceda 500, Temuco")
        page.evaluate("() => cerrarSugerencias()")
        antes = txt(page, "#respuesta") + "|" + txt(page, "#estado")
        page.click("#btn-buscar")
        page.wait_for_timeout(2500)
        despues = txt(page, "#respuesta") + "|" + txt(page, "#estado")
        print("  antes :", antes[:120].replace("\n", " / "))
        print("  después:", despues[:120].replace("\n", " / "))
        print("  ¿cambió algo?", antes != despues)
        print("  listeners registrados en #btn-buscar:",
              page.evaluate("() => { const s=document.getElementById('btn-buscar');"
                            "return s.outerHTML; }"))

        print("\n### 209 — la lista de sugerencias vuelve a abrirse sola")
        page.fill("#q", "")
        page.click("#q")
        page.type("#q", "angol", delay=40)
        page.wait_for_timeout(200)
        vis1 = page.evaluate("() => !document.getElementById('sugerencias').classList.contains('oculto')")
        page.evaluate("() => SUG.items[0] && SUG.items[0].accion()")
        page.wait_for_timeout(150)
        vis2 = page.evaluate("() => !document.getElementById('sugerencias').classList.contains('oculto')")
        page.wait_for_timeout(1600)
        vis3 = page.evaluate("() => !document.getElementById('sugerencias').classList.contains('oculto')")
        n3 = page.evaluate("() => document.querySelectorAll('#sugerencias li').length")
        print(f"  visible al escribir={vis1} · tras elegir={vis2} · 1,6 s después={vis3} (items={n3})")

        print("\n### 601/602 — punto dentro del AR-2a VIGENTE del PRC de Angol (capa derivada)")
        consultar(page, *ANGOL_AR2A, "AR-2a Angol")
        print("  veredicto:", txt(page, "#respuesta h2"))
        print("  por qué  :", txt(page, "#respuesta .por-que"))
        d = txt(page, "#detalle-ficha")
        i = d.find("Plan Regulador Comunal")
        print("  bloque A :", d[i:i+320].replace("\n", " "))
        print("  ¿la ficha nombra la lámina/derivada?",
              any(w in d for w in ["AR-2a", "vectorizamos", "lámina", "derivad"]))
        print("  ¿el punto está dentro de una lámina, según el propio visor?",
              page.evaluate(f"() => poligonosQueContienen({ANGOL_AR2A[0]}, {ANGOL_AR2A[1]}, estado.laminas).length"))
        print("  clase GORE en ese punto:",
              page.evaluate(f"() => poligonosQueContienen({ANGOL_AR2A[0]}, {ANGOL_AR2A[1]}, estado.gore).map(f=>f.properties.clase)"))

        print("\n### 104/202 — el texto compartido en 'sindato'")
        print("  nivel del último resultado:", page.evaluate("() => estado.ultimo.res.nivel"),
              "· estado.ultimo.nivel =", page.evaluate("() => String(estado.ultimo.nivel)"))
        t = page.evaluate("() => textoFicha()")
        print("  ¿el texto trae el 'OJO: ... NO significa que acá no se inunde'?", "OJO:" in t)
        print("  cola del texto:", " / ".join(t.splitlines()[-4:]))

        print("\n### 105 — polígono de ANEGAMIENTO titulado como inundación")
        consultar(page, *TEMUCO_ANEG, "Temuco anegamiento")
        print("  veredicto:", txt(page, "#respuesta h2"))
        print("  por qué  :", txt(page, "#respuesta .por-que"))
        d = txt(page, "#detalle-ficha")
        print("  ¿aparece el sello 'anegamiento, no desborde' en el detalle?",
              "anegamiento, no desborde" in d)
        print("\n  y el litoral (Toltén):")
        consultar(page, *TOLTEN_LITORAL, "Toltén litoral")
        print("  veredicto:", txt(page, "#respuesta h2"))
        print("  por qué  :", txt(page, "#respuesta .por-que"))

        print("\n### 113 — punto en el océano, dentro del bbox de la región")
        consultar(page, *MAR, "mar")
        print("  veredicto:", txt(page, "#respuesta h2"))
        print("  aviso    :", txt(page, "#respuesta .aviso-fuerte"))
        d = txt(page, "#detalle-ficha")
        i = d.find("Con qué cuenta")
        print("  bloque comuna:", d[i:i+200].replace("\n", " ") if i >= 0 else "(no hay)")

        print("\n### 107 — año de la atribución cuando el punto NO cae en un área")
        i = d.find("Plan Regulador Comunal")
        print("  ", d[i:i+430].replace("\n", " "))

        print("\n### 110 — elegir una comuna en las sugerencias")
        page.evaluate("() => zoomComuna(estado.comunas.comunas.find(c=>c.comuna==='Angol'))")
        page.wait_for_timeout(600)
        print("  veredicto:", txt(page, "#respuesta h2"))
        print("  dirección:", txt(page, "#respuesta .direccion"))

        print("\n### 117 — clic sobre un polígono de área de riesgo")
        n_click = page.evaluate("""() => {
          const m = estado.mapa; let popup=0, consulta=0;
          const orig = window.consultar; window.consultar = (...a) => { consulta++; return orig(...a); };
          return new Promise(res => {
            m.jumpTo({center: [-73.142903, -38.702816], zoom: 15});
            m.once('idle', () => {
              const p = m.project([-73.142903, -38.702816]);
              const hit = m.queryRenderedFeatures(p, {layers:['ar-fill']}).length;
              m.fire('click', {lngLat: {lng:-73.142903, lat:-38.702816}, point: p,
                               originalEvent: new MouseEvent('click')});
              setTimeout(() => res({hit, popups: document.querySelectorAll('.maplibregl-popup').length}), 800);
            });
          });
        }""")
        print("  ", n_click, "· veredicto tras el clic:", txt(page, "#respuesta h2"))

        print("\n### 116 — mensajes de #estado que se quedan pegados")
        page.evaluate("() => { elEstado().textContent = 'Mostrando 3 de 7 planos; acerca más para el resto.'; }")
        consultar(page, *TEMUCO_ANEG, "otra consulta")
        print("  #estado después de una consulta nueva:", repr(txt(page, "#estado")))

        print("\n### 214 — sin red, un recurso que no está en caché")
        page.wait_for_timeout(1500)
        sw = page.evaluate("() => navigator.serviceWorker.controller ? 'activo' : 'sin controlador'")
        print("  service worker:", sw)
        ctx.set_offline(True)
        r = page.evaluate("""async () => {
          try {
            const r = await fetch('data/planos/04_Anteproyecto-Planos_PRC_Vilcun_p001.png');
            const t = await r.clone().text().catch(()=> '');
            return {ok: r.ok, status: r.status, tipo: r.headers.get('content-type'),
                    empiezaCon: t.slice(0, 60)};
          } catch (e) { return {error: String(e)}; }
        }""")
        print("  PNG de plano sin red ->", r)
        r2 = page.evaluate("""async () => {
          try {
            const r = await fetch('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/12/2400/1300');
            const t = await r.clone().text().catch(()=> '');
            return {ok: r.ok, status: r.status, tipo: r.headers.get('content-type'), empiezaCon: t.slice(0,60)};
          } catch (e) { return {error: String(e)}; }
        }""")
        print("  tesela Esri sin red ->", r2)
        ctx.set_offline(False)

        print("\n### errores de JavaScript en toda la sesión:", errores)
        b.close()


main()
