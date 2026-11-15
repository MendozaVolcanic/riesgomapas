#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fA_veredicto_censo.py : qué le responde el visor a cada manzana del Censo 2024,
y a cuánta gente le toca cada defecto de la lógica del veredicto.

POR QUÉ. Un defecto de evaluar() pesa según a cuántas personas les cambia la
respuesta. Este script toma el punto representativo de cada una de las 17.107
unidades censales de La Araucanía (manzanas urbanas y entidades rurales), le
agrega dos rótulos que el visor NO conoce (si el terreno es apto para que el
radar vea agua, y si cae en un área de riesgo hídrica del PRC de Angol según
GeoIDE del MINVU) y se lo pasa a fA_veredicto_censo.js, que llama al evaluar()
REAL de web/app.js punto por punto.

LÍMITE DECLARADO. Se usa el punto representativo de cada unidad, no el reparto
por área: la persona se cuenta entera donde cae ese punto. Para manzanas
urbanas (cientos de metros) es aceptable; para entidades rurales extensas es
grueso. Las cifras son órdenes de magnitud de exposición al defecto, no
población expuesta a inundación.

LAS DOS PREGUNTAS DEL INSTRUMENTO
  1. Si el defecto no existiera, ¿la cuenta daría cero? Sí: cada categoría se
     define por la salida de evaluar() (nivel, titular, capas), no por una
     copia de la regla. --control fabrica cada defecto en un punto sintético y
     exige que la cuenta lo vea (lo hace el .js con --control).
  2. Si el instrumento estuviera muerto, ¿se vería distinto? Sí: el script
     termina con error si el censo no carga, si la suma de población no está en
     el orden de 1.000.000, o si el arnés no carga las capas.

Uso:
  python tools/auditoria/fA_veredicto_censo.py --geoide RUTA_GEOJSON_GEOIDE_CAPA29 \
         --salida RUTA_TEMPORAL.json
  python tools/auditoria/fA_veredicto_censo.py --control
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from shapely.geometry import shape
from shapely.strtree import STRtree
import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
CENSO = RAIZ / "data/processed/censo/censo-2024-araucania.geojson"
TERRENO = RAIZ / "data/processed/sar/2026-07-30_sistema_frontal/terreno.tif"
JS = Path(__file__).with_name("fA_veredicto_censo.js")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geoide", help="GeoJSON de PRC_Angol_Area_de_riesgo (GeoIDE capa 29)")
    ap.add_argument("--salida", help="JSON intermedio de puntos (fuera del repo)")
    ap.add_argument("--control", action="store_true")
    a = ap.parse_args()

    if a.control:
        return subprocess.call(["node", str(JS), "--control"])

    cfg = yaml.safe_load(open(RAIZ / "config/araucania.yaml", encoding="utf-8"))["sar"]
    d = json.load(open(CENSO, encoding="utf-8"))
    feats = d["features"]
    pts = []
    for f in feats:
        g = shape(f["geometry"])
        if g.is_empty:
            continue
        rp = g.representative_point()
        p = f["properties"]
        pts.append({"lon": rp.x, "lat": rp.y, "n": int(p.get("n_per") or 0),
                    "comuna": p.get("NOM_COMUNA"), "u": p.get("unidad_censal"),
                    "rio": int(p.get("n_fuente_agua_rio") or 0)})
    total = sum(p["n"] for p in pts)
    print(f"unidades censales: {len(pts)} · población sumada: {total}")
    if not (900_000 < total < 1_100_000):
        print("INSTRUMENTO MUERTO: la población no está en el orden esperado")
        return 2

    # Terreno apto para el radar (misma regla que scripts/sar.py terreno_apto).
    with rasterio.open(TERRENO) as r:
        vals = list(r.sample([(p["lon"], p["lat"]) for p in pts]))
    for p, v in zip(pts, vals):
        dem, pend = float(v[0]), float(v[1])
        p["apto"] = bool(np.isfinite(dem) and np.isfinite(pend)
                         and pend <= cfg["pendiente_max_grados"]
                         and dem <= cfg["altitud_max_m"] and dem > cfg["altitud_min_m"])
    print(f"terreno apto (pendiente ≤ {cfg['pendiente_max_grados']}°, "
          f"{cfg['altitud_min_m']} < altura ≤ {cfg['altitud_max_m']} m): "
          f"{sum(p['apto'] for p in pts)} de {len(pts)} puntos")

    # GeoIDE Angol: áreas de riesgo hídricas (AR-2a inundable, AR-2b anegamiento).
    if a.geoide:
        gj = json.load(open(a.geoide, encoding="utf-8"))
        geoms, zonas = [], []
        for f in gj["features"]:
            z = f["properties"].get("ZONA")
            if z in ("AR-2a", "AR-2b"):
                geoms.append(shape(f["geometry"]).buffer(0))
                zonas.append(z)
        print(f"GeoIDE Angol: {len(gj['features'])} polígonos, hídricos {len(geoms)} "
              f"(AR-2a {zonas.count('AR-2a')}, AR-2b {zonas.count('AR-2b')})")
        arbol = STRtree(geoms)
        from shapely.geometry import Point
        for p in pts:
            pt = Point(p["lon"], p["lat"])
            hits = [zonas[i] for i in arbol.query(pt) if geoms[i].contains(pt)]
            p["geoide"] = sorted(set(hits))

    salida = Path(a.salida)
    salida.write_text(json.dumps(pts), encoding="utf-8")
    print(f"puntos escritos en {salida}")
    return subprocess.call(["node", str(JS), str(salida)])


if __name__ == "__main__":
    sys.exit(main())
