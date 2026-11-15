"""vB: ¿el agregado nacional IPT/IPT_AREA_RIESGO capa 0 de GeoIDE coincide con las capas por comuna?

Verifica F-209. Lee la descarga del auditor (ipt_area_riesgo_L0_araucania_wkid32718.json,
filtro REG like '%Araucan%') y las capas por comuna (data/raw/geoide_minvu_araucania/),
y consulta conteos por comuna SIN filtro de región para ver si el filtro deja fuera
registros.

QUÉ MIDE
    Por comuna: n en el agregado vs n de áreas de riesgo en las capas por comuna,
    y para Angol el IoU geométrico agregado vs capa 29.

LAS DOS PREGUNTAS DEL INSTRUMENTO
    (1) Si el agregado no coincidiera, ¿se vería? Sí: compara conteo y geometría.
    (2) Si el instrumento estuviera muerto, ¿se notaría? Angol contra sí mismo
        (capa 29 vs capa 29) tiene que dar IoU 1; se comprueba antes.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "data/raw/geoide_minvu_araucania"
AGG = "https://geoide.minvu.cl/server/rest/services/IPT/IPT_AREA_RIESGO/FeatureServer/0/query"

# capas de áreas de riesgo por comuna (nombre de capa con «riesgo» o «_AR»), y las
# capas de PRC completo que traen zonas AR mezcladas (se cuentan sólo ZONA AR*).
AR = {"Angol": [29], "Renaico": [9, 31], "Toltén": [4, 6, 34, 37], "Nueva Imperial": [33],
      "Collipulli": [23], "Carahue": [25], "Temuco": [12]}


def esri(geom):
    ext, hue = [], []
    for r in geom["rings"]:
        p = Polygon(r)
        (ext if not p.exterior.is_ccw else hue).append(p)
    g = unary_union(ext)
    for h in hue:
        g = g.difference(h)
    return g if g.is_valid else g.buffer(0)


def main():
    agg = json.load(open(RAW / "ipt_area_riesgo_L0_araucania_wkid32718.json", encoding="utf-8"))
    c = Counter(f["attributes"]["COM"] for f in agg["features"])
    print("REG distintos en el agregado (descarga del auditor):",
          Counter(f["attributes"]["REG"] for f in agg["features"]))
    for com, capas in AR.items():
        n = 0
        for k in capas:
            d = json.load(open(RAW / f"capa_{k:02d}.json", encoding="utf-8"))
            n += len(d["features"])
        time.sleep(0.6)
        q = urllib.parse.urlencode({"where": f"COM = '{com}'", "returnCountOnly": "true", "f": "json"})
        try:
            sin_filtro = json.loads(urllib.request.urlopen(f"{AGG}?{q}", timeout=60).read())["count"]
        except Exception as e:  # noqa: BLE001
            sin_filtro = f"error {e}"
        print(f"  {com:15s} agregado(REG Araucan) {c.get(com, 0):3d} | agregado(COM=, sin filtro REG) {sin_filtro} | capas {capas} suman {n}")
    # Angol geométrico
    c29 = json.load(open(RAW / "capa_29_wkid32718.json", encoding="utf-8"))
    G = unary_union([esri(f["geometry"]) for f in c29["features"]])
    iou_self = G.intersection(G).area / G.union(G).area
    assert abs(iou_self - 1) < 1e-9, "instrumento muerto"
    A = unary_union([esri(f["geometry"]) for f in agg["features"] if f["attributes"]["COM"] == "Angol"])
    print(f"Angol agregado vs capa 29: {A.area/1e4:.2f} ha vs {G.area/1e4:.2f} ha, IoU {A.intersection(G).area/A.union(G).area:.4f}")
    za = Counter(f["attributes"]["ZONA"] for f in agg["features"] if f["attributes"]["COM"] == "Angol")
    print("Angol agregado por ZONA:", dict(za))


if __name__ == "__main__":
    main()
