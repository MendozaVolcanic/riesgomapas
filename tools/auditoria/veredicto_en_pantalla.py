"""Lee en un navegador real lo que el visor responde para una lista de puntos.

Qué mide: para cada [lon, lat] llama a `consultar(lon, lat, etiqueta)` (igual que
tests/auditoria_e2e.py) sobre el visor servido en --base y extrae el título del
veredicto (#respuesta h2), la frase «por qué», y las oraciones de la ficha de
detalle sobre plan regulador, láminas derivadas y modelo regional. Sirve para
contrastar el veredicto en pantalla con lo que dan el arnés de Node y shapely.

Las dos preguntas del instrumento:
 (1) Si el visor respondiera mal, ¿esto lo mostraría?  Sí: imprime el texto
     literal en pantalla y quien compara lo hace contra el veredicto esperado.
 (2) Si el instrumento estuviera muerto, ¿se vería distinto?  Sí: aborta si
     `#respuesta` sigue oculto o `estado.ultimo` no se llenó tras consultar.

Uso: python tools/auditoria/veredicto_en_pantalla.py puntos.json [--base http://127.0.0.1:8793]
     puntos.json: {"nombre": {"lonlat": [lon, lat]}, ...}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def frases(texto, *claves):
    out = []
    for oracion in re.split(r"(?<=[.!?])\s+", " ".join(texto.split())):
        if any(k in oracion.lower() for k in claves):
            out.append(oracion.strip())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puntos")
    ap.add_argument("--base", default="http://127.0.0.1:8793")
    a = ap.parse_args()
    puntos = json.loads(Path(a.puntos).read_text(encoding="utf-8"))
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(f"{a.base}/index.html", wait_until="networkidle")
        page.wait_for_function("() => estado.puntos && estado.areasRiesgo", timeout=30000)
        cargadas = page.evaluate("() => ({areas: !!estado.areasRiesgo, laminas: !!estado.laminas, "
                                 "gore: !!estado.gore, jrc: !!estado.jrc, sar: !!estado.sar})")
        print("capas cargadas en el navegador:", json.dumps(cargadas))
        for nombre, v in puntos.items():
            lon, lat = v["lonlat"]
            # Volver a la pestaña de respuesta: si quedó abierta la de detalle,
            # #respuesta está oculta y la guardia de abajo se acusaría a sí misma.
            page.evaluate("() => irAPestana('respuesta', false)")
            page.evaluate("([lon,lat]) => consultar(lon, lat, 'Auditoría')", [lon, lat])
            page.wait_for_timeout(700)
            if page.locator("#respuesta").is_hidden() or not page.evaluate("() => !!estado.ultimo"):
                print("INSTRUMENTO MUERTO: sin respuesta para", nombre); sys.exit(2)
            titulo = page.locator("#respuesta h2").inner_text()
            porque = page.locator("#respuesta .por-que").inner_text()
            nivel = page.evaluate("() => estado.ultimo.res.nivel")
            n = page.evaluate("() => ({areas: estado.ultimo.res.areas.length, gore: estado.ultimo.res.gore.length,"
                              " enMancha: estado.ultimo.res.enMancha, sar: estado.ultimo.res.sar.length,"
                              " laminas_en_res: 'laminas' in estado.ultimo.res})")
            page.evaluate("() => irAPestana('detalle', false)")
            page.wait_for_timeout(200)
            ficha = page.locator("#detalle-ficha").inner_text()
            print(f"\n=== {nombre}  [{lon:.6f}, {lat:.6f}]")
            print(f"  nivel={nivel}  res={json.dumps(n)}")
            print(f"  TÍTULO: {titulo}")
            print(f"  POR QUÉ: {' '.join(porque.split())}")
            for fr in frases(ficha, "este punto cae", "este punto no cae", "este punto queda",
                             "gobierno regional clasifica", "clasifica este punto", "lámina", "derivad"):
                print(f"  FICHA: {fr}")
            print(f"  ficha menciona 'derivad': {'derivad' in ficha.lower()} · 'lámina': {'lámina' in ficha.lower()}")
        b.close()


if __name__ == "__main__":
    main()
