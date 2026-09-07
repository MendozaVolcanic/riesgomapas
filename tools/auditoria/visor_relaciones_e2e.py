"""Mide en navegador real cinco relaciones del visor que el código correcto
línea a línea no muestra (auditoría 2026-09-06, frente 2, patrones 1/2/4/5).

Levanta `web/` en http://127.0.0.1:8792 (puerto fijado por el orquestador) y
ejecuta, con Chromium headless:

  M1  Punto DENTRO de una lámina vectorizada AR-2a (PRC Angol, efecto legal
      declarado en el dato) → ¿la ficha lo dice o dice «no cae dentro»?
      Control positivo: punto dentro de un área MINVU → la ficha dice «cae dentro».
  M2  Punto donde se solapan dos hojas de plano (Pucón v3 y v4) → ¿qué plano
      muestra la ficha? Control: cuántos planos cubren el punto según el visor.
  M3  Punto SIN DATO → ¿el texto que se comparte (textoFicha) lleva la
      advertencia «OJO: que no haya registro NO significa…»?
      Control: `res.nivel` del punto es 'sindato' y la PANTALLA sí muestra el
      aviso-fuerte.
  M4  Escribir «Angol», elegir la sugerencia de comuna, esperar 2 s → ¿la lista
      de sugerencias vuelve a abrirse sola? Control: justo tras elegir está oculta.
  M5  Punto dentro de un área MINVU con datos EAE → ¿la ficha dice a la vez
      «Año: NNNN» y «El año del plan regulador no está declarado…»?
  M6  Comuna Temuco → ¿el bloque de comuna dice «No detectamos vacíos» y qué
      fenómeno declara su único polígono?

Preguntas del instrumento:
  (1) Si lo medido estuviera roto, ¿fallaría? Sí: cada medida imprime el texto
      crudo que lee y una decisión explícita; los controles positivos prueban
      que la lectura de la ficha funciona.
  (2) Si el instrumento estuviera muerto, ¿se vería distinto? Sí: sin mapa o
      sin datos las evaluaciones lanzan y el script termina con traza.

Uso:  python tools/auditoria/visor_relaciones_e2e.py
No modifica nada del repositorio.
"""
from __future__ import annotations

import http.server
import io
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
WEB = RAIZ / "web"
PUERTO = 8792


def servir():
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(WEB), **k)

        def log_message(self, *a):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PUERTO), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


JS_PUNTO_DENTRO = """
([fc, filtro]) => {
  // Primer polígono que cumpla el filtro cuyo centroide del anillo exterior
  // caiga dentro de sí mismo (evita centroides fuera en formas cóncavas).
  const feats = fc.features;
  for (let i = 0; i < feats.length; i++) {
    const f = feats[i];
    if (filtro && !Object.entries(filtro).every(([k, v]) => f.properties[k] === v)) continue;
    const g = f.geometry;
    const anillo = g.type === 'MultiPolygon' ? g.coordinates[0][0] : g.coordinates[0];
    let x = 0, y = 0;
    for (const [a, b] of anillo) { x += a; y += b; }
    x /= anillo.length; y /= anillo.length;
    if (dentroAnillo(x, y, anillo)) return { i, lon: x, lat: y, props: f.properties };
  }
  return null;
}
"""


def main():
    httpd = servir()
    base = f"http://127.0.0.1:{PUERTO}"
    print(f"servidor: {base}")
    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=True)
        page = nav.new_page(viewport={"width": 1280, "height": 900})
        errores = []
        page.on("pageerror", lambda e: errores.append(str(e)))
        page.goto(f"{base}/index.html", wait_until="networkidle")
        page.wait_for_function("() => window.estado && estado.puntos && estado.laminas")
        n = page.evaluate("() => ({puntos: estado.puntos.features.length, laminas: estado.laminas.features.length, areas: estado.areasRiesgo.features.length, planos: estado.planos.length})")
        print("datos cargados:", n)

        def consultar(lon, lat, etq):
            page.evaluate("([lon, lat, e]) => consultar(lon, lat, e)", [lon, lat, etq])
            page.wait_for_function(
                "(e) => document.querySelector('#respuesta').innerText.includes(e)", arg=etq, timeout=8000)
            page.evaluate("() => irAPestana('detalle', false)")
            return (page.locator("#respuesta").inner_text(),
                    page.locator("#detalle-ficha").inner_text())

        # ---------------------------------------------------------------- M1
        print("\n== M1 lámina vectorizada AR-2a (Angol) ==")
        p = page.evaluate(JS_PUNTO_DENTRO, [page.evaluate("() => estado.laminas"), {"clase": "AR-2a"}])
        print("  punto:", round(p["lon"], 5), round(p["lat"], 5), "| props:",
              {k: p["props"][k] for k in ("clase", "comuna", "anio", "fuente")})
        print("  efecto_legal declarado:", (p["props"].get("efecto_legal") or "")[:90])
        resp, ficha = consultar(p["lon"], p["lat"], "M1 lamina AR-2a")
        nivel = page.evaluate("() => estado.ultimo.res.nivel")
        print("  res.nivel =", nivel)
        print("  respuesta corta:", resp.replace("\n", " | ")[:300])
        pr = ficha.lower()
        print("  ficha dice «no cae dentro de un área de riesgo»:", "no cae dentro de un área de riesgo" in pr)
        print("  ficha menciona 'lámina' o 'vectoriz' o 'AR-2a':",
              any(s in pr for s in ("lámina", "lamina", "vectoriz", "ar-2a")))
        print("  ficha menciona 'derivad':", "derivad" in pr)
        # control positivo: punto dentro de un área MINVU
        c = page.evaluate(JS_PUNTO_DENTRO, [page.evaluate("() => estado.areasRiesgo"), None])
        resp_c, ficha_c = consultar(c["lon"], c["lat"], "M1 control MINVU")
        print("  CONTROL área MINVU:", c["props"]["comuna"], c["props"]["clasificacion"],
              "| ficha dice «cae dentro de»:", "cae dentro de" in ficha_c.lower(),
              "| nivel:", page.evaluate("() => estado.ultimo.res.nivel"))

        # ---------------------------------------------------------------- M2
        print("\n== M2 planos solapados (Pucón v3 / v4) ==")
        info = page.evaluate("""() => {
          const v4 = estado.planos.find(p => p.archivo.includes('Pucon_v4.pdf_p001'));
          const [w, s, e, n] = v4.bounds_wgs84;
          const lon = (w + e) / 2, lat = (s + n) / 2;
          return { lon, lat, cubren: planosQueCubren(lon, lat).map(p => p.archivo),
                   orden: estado.planos.map(p => p.archivo).filter(a => a.includes('Pucon')) };
        }""")
        print("  orden en indice.json (Pucón):", info["orden"])
        print("  planos que cubren el centro de v4 p001:", info["cubren"])
        resp, ficha = consultar(info["lon"], info["lat"], "M2 pucon")
        import re
        # El encabezado se renderiza con text-transform: uppercase, así que se
        # busca sin distinguir mayúsculas y se imprimen las 4 líneas siguientes.
        lineas = ficha.splitlines()
        idx = next((k for k, l in enumerate(lineas) if "plano de tu comuna" in l.lower()), None)
        print("  bloque del plano en la ficha:",
              [l.strip() for l in lineas[idx:idx + 5]] if idx is not None else "(sin bloque de plano)")
        print("  la ficha menciona 'v4':", "v4" in ficha.lower(), "| menciona 'v3':", "v3" in ficha.lower())
        print("  res.planos según el visor:", page.evaluate("() => estado.ultimo.res.planos.map(p => p.archivo)"))

        # ---------------------------------------------------------------- M3
        print("\n== M3 punto SIN DATO y texto compartido ==")
        # buscar un punto sindato: rejilla gruesa dentro del bbox
        sd = page.evaluate("""() => {
          for (let lat = -37.4; lat > -39.6; lat -= 0.05)
            for (let lon = -73.6; lon < -71.0; lon += 0.05) {
              const r = evaluar(lon, lat);
              if (r.nivel === 'sindato') return { lon, lat };
            }
          return null;
        }""")
        resp, ficha = consultar(sd["lon"], sd["lat"], "M3 sindato")
        nivel = page.evaluate("() => estado.ultimo.res.nivel")
        texto = page.evaluate("() => textoFicha()")
        print("  punto:", sd, "| res.nivel =", nivel)
        print("  pantalla muestra .aviso-fuerte:", page.locator("#respuesta .aviso-fuerte").count())
        print("  textoFicha() contiene 'OJO':", "OJO" in texto)
        print("  textoFicha() contiene 'no significa que acá no se inunde':", "no significa que acá no se inunde" in texto)
        print("  estado.ultimo.nivel =", page.evaluate("() => estado.ultimo.nivel"))
        print("  --- textoFicha() crudo ---\n" + texto + "\n  --- fin ---")

        # ---------------------------------------------------------------- M4
        print("\n== M4 sugerencias tras elegir una comuna ==")
        page.evaluate("() => irAPestana('respuesta', false)")
        page.fill("#q", "")
        page.type("#q", "Angol")
        page.wait_for_function("() => document.querySelectorAll('#sugerencias li').length > 0", timeout=3000)
        page.locator("#sugerencias li").first.click()
        oculta_al_elegir = page.evaluate("() => document.querySelector('#sugerencias').classList.contains('oculto')")
        page.wait_for_timeout(2500)
        oculta_2s = page.evaluate("() => document.querySelector('#sugerencias').classList.contains('oculto')")
        items = page.evaluate("() => [...document.querySelectorAll('#sugerencias li')].map(l => l.innerText.split('\\n')[0])")
        print("  oculta justo al elegir (CONTROL):", oculta_al_elegir)
        print("  oculta 2,5 s después:", oculta_2s, "| items visibles:", items)
        print("  campo #q vale:", page.evaluate("() => document.querySelector('#q').value"))

        # ---------------------------------------------------------------- M5
        print("\n== M5 año del área MINVU: dos frases en la misma ficha ==")
        e = page.evaluate(JS_PUNTO_DENTRO, [page.evaluate("() => estado.areasRiesgo"),
                                            {"anio": "2009", "comuna": "Temuco"}])
        if not e:
            e = page.evaluate("""() => {
              const fc = estado.areasRiesgo; const f = fc.features.find(x => x.properties.eae_fecha_ingreso && x.properties.anio !== 'no declarado por la fuente');
              const i = fc.features.indexOf(f); const g = f.geometry;
              const an = g.type === 'MultiPolygon' ? g.coordinates[0][0] : g.coordinates[0];
              let x=0,y=0; for (const [a,b] of an){x+=a;y+=b;} return {i, lon:x/an.length, lat:y/an.length, props:f.properties};
            }""")
        resp, ficha = consultar(e["lon"], e["lat"], "M5 eae")
        fl = ficha
        m_anio = re.search(r"Año:\s*(\S+)", fl)
        print("  polígono:", e["props"]["comuna"], "| anio:", e["props"]["anio"],
              "| anio_fuente:", e["props"].get("anio_fuente"), "| eae:", e["props"].get("eae_fecha_ingreso"))
        print("  ficha muestra «Año: …»:", m_anio.group(0) if m_anio else None)
        print("  ficha dice «no está declarado en la capa publicada por MINVU»:",
              "no está declarado en la capa publicada por minvu" in fl.lower())
        print("  ficha menciona 'Atlas' o 'CIGIDEN':", any(s in fl for s in ("Atlas", "CIGIDEN")))

        # ---------------------------------------------------------------- M6
        print("\n== M6 Temuco: inventario ==")
        t = page.evaluate("""() => {
          const fs = estado.areasRiesgo.features.filter(f => f.properties.comuna === 'Temuco');
          return fs.map(f => ({clas: f.properties.clasificacion, tipo: f.properties.tipo_hidrico}));
        }""")
        print("  polígonos MINVU de Temuco:", t)
        ec = page.evaluate("() => estado.estadoComunas.find(c => c.comuna === 'Temuco')")
        print("  estado-comunas Temuco: le_falta =", ec["le_falta"], "| poligonos_area_riesgo =", ec["poligonos_area_riesgo"])
        print("  textoComuna(Temuco) dice «No detectamos vacíos»:",
              "No detectamos vacíos" in page.evaluate("(c) => textoComuna(c)", ec))

        print("\nerrores JS durante la corrida:", errores or "ninguno")
        nav.close()
    httpd.shutdown()


if __name__ == "__main__":
    main()
