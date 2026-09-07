#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""veredicto_puntos_clave.py — qué responde el visor en los puntos que la auditoría
dejó marcados, en un navegador real.

POR QUÉ. La auditoría del 6-sep-2026 encontró que el veredicto decidía con cuatro
de las siete capas que el visor dibuja, y que a metros del borde respondía «sin
registros». Los arreglos de F-01, F-08, F-09, F-10 y D-3 sólo valen si se ven en
la pantalla: este arnés consulta una lista de puntos con coordenadas fijas y
compara el titular, el «por qué» y los bloques de evidencia contra lo que se
espera de cada uno.

LAS DOS PREGUNTAS DEL INSTRUMENTO
  1. Si el veredicto volviera a ignorar la capa derivada, los casos «derivada» y
     «AR-2a lámina 2» fallarían: exigen texto que sólo puede venir de esa capa.
  2. Si el instrumento estuviera muerto (la página no carga, `consultar` no
     existe), no habría titular que leer y el caso sale ROTO, no OK.
  Control negativo incluido: un punto en el mar, que no debe recibir veredicto
  de riesgo, y un punto en un potrero de Angol donde antes se publicaba la caja
  de leyenda.

Uso:  python tools/auditoria/veredicto_puntos_clave.py [--url http://127.0.0.1:8796]
      (si no se le pasa URL levanta su propio servidor)
Salida: una línea por caso y un veredicto final; código 1 si alguno falla.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# lon, lat, nombre, qué tiene que aparecer, qué NO puede aparecer
CASOS = [
    (-72.6867, -37.78499, "Angol · dentro del AR-2a de la lámina 1 del PRC",
     ["área de riesgo por inundación del plan regulador", "A · DERIVADO", "trazado derivado"],
     ["no cae dentro de un área de riesgo", "Sin registros en las fuentes consultadas"]),
    (-72.70378, -37.83436, "Angol · el potrero donde se publicaba la caja de leyenda",
     [], ["A · DERIVADO"]),
    (-71.68301, -39.37424, "Catripulli · donde estaba el cuadro de leyenda",
     [], ["A · DERIVADO"]),
    (-72.7, -38.75, "Punto rural cualquiera de la región", [], []),
]


def servidor(puerto: int):
    h = functools.partial(http.server.SimpleHTTPRequestHandler,
                          directory=str(RAIZ / "web"))
    socketserver.TCPServer.allow_reuse_address = True
    s = socketserver.TCPServer(("127.0.0.1", puerto), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


JS = """
async ([lon, lat]) => {
  await consultar(lon, lat, 'prueba');
  const q = (s) => (document.querySelector(s) || {}).textContent || '';
  return {
    titulo: q('#respuesta .veredicto h2').trim(),
    porque: q('#respuesta .por-que').trim(),
    nivel: (document.querySelector('#respuesta .veredicto') || {}).className || '',
    detalle: (document.querySelector('#detalle-ficha') || {}).textContent || '',
    comuna: q('#detalle-ficha h3'),
  };
}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--puerto", type=int, default=8796)
    a = ap.parse_args()
    srv = None
    url = a.url
    if not url:
        srv = servidor(a.puerto)
        url = f"http://127.0.0.1:{a.puerto}/"
    from playwright.sync_api import sync_playwright

    fallas, filas = [], []
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pag = nav.new_page(viewport={"width": 1280, "height": 900})
        errores = []
        pag.on("pageerror", lambda e: errores.append(str(e)))
        pag.goto(url, wait_until="networkidle")
        # Esperar por CONTENIDO, no por tiempo: las capas que el veredicto usa.
        pag.wait_for_function(
            "() => window.estado && estado.puntos && estado.areasRiesgo && estado.laminas",
            timeout=30000)
        for lon, lat, nombre, debe, no_debe in CASOS:
            r = pag.evaluate(JS, [lon, lat])
            texto = f"{r['titulo']} ||| {r['porque']} ||| {r['detalle']}"
            faltan = [x for x in debe if x.lower() not in texto.lower()]
            sobran = [x for x in no_debe if x.lower() in texto.lower()]
            ok = not faltan and not sobran
            filas.append((nombre, r["titulo"], r["nivel"], ok, faltan, sobran))
            if not ok:
                fallas.append(f"{nombre}: faltan {faltan} · sobran {sobran}")
        nav.close()
    if srv:
        srv.shutdown()

    for nombre, titulo, nivel, ok, faltan, sobran in filas:
        print(f"[{'OK ' if ok else 'FALLA'}] {nombre}")
        print(f"        titular: «{titulo}»  ({nivel})")
        if faltan:
            print(f"        NO apareció: {faltan}")
        if sobran:
            print(f"        apareció y no debía: {sobran}")
    if errores:
        print("errores de JavaScript:", errores[:3])
        fallas.append(f"{len(errores)} errores de JavaScript")
    print("\n=== VEREDICTO ===")
    if fallas:
        for f in fallas:
            print("FALLA:", f)
        return 1
    print(f"los {len(CASOS)} casos responden lo esperado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
