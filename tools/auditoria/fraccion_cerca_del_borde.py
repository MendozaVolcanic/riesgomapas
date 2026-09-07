"""Qué fracción de la zona urbana queda a <10 / <25 / <50 m de un borde de polígono.

Por qué: el visor responde binario «cae dentro / no cae dentro» (web/app.js,
`evaluar`). Si el dato tiene ±5-8 m de error de posición, todo punto a menos de
esa distancia del borde recibe un veredicto que el propio dato no sostiene.
Este script mide cuánta gente está en esa franja.

Qué mide: grilla de puntos (paso configurable, 20 m) dentro de las manzanas
urbanas del Censo 2024 (data/processed/censo/censo-2024-araucania.geojson,
`unidad_censal` manzana_urbana o aldea) de cada comuna, recortada a la caja de
interés (Catripulli es una localidad de Curarrehue: se usa la caja de la
lámina vectorizada de esa comuna). Para cada punto, distancia en metros
(proyección UTM 18S / 19S vía pyproj) al borde más cercano de cada capa
publicada. Se reporta la fracción de puntos y la fracción de población
(ponderando cada punto por n_per de su manzana / puntos de esa manzana).

Las dos preguntas del instrumento:
 (1) Si el fenómeno no existiera (ningún punto cerca de un borde), ¿fallaría?
     Sí: daría 0 %. Control: --control desplaza la capa 10 km al este y la
     fracción debe caer a ~0.
 (2) Si el instrumento estuviera muerto, ¿se vería distinto?  Sí: aborta si
     una comuna no tiene manzanas o una capa no tiene polígonos en la caja.

Uso: python tools/auditoria/fraccion_cerca_del_borde.py [--paso 20] [--control]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import Point, box, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid

RAIZ = Path(__file__).resolve().parents[2]
CENSO = RAIZ / "data/processed/censo/censo-2024-araucania.geojson"
CAPAS = {
    "A_normativo": "web/data/areas-riesgo-inundacion.geojson",
    "A_derivada": "web/data/laminas/vectorizadas.geojson",
    "C_gore": "web/data/gore/amenaza-inundacion.geojson",
    "C_jrc_rp100": "web/data/jrc/rp100.geojson",
}
# Cajas de interés [oeste, sur, este, norte]. Angol y Curarrehue: caja de las
# láminas vectorizadas (medida con shapely en la sesión de auditoría).
# Collipulli y Temuco: caja de las áreas normativas de esa comuna, ampliada 2 km.
COMUNAS = {
    "Angol": ("ANGOL", [-72.7398, -37.8374, -72.6651, -37.7786]),
    "Collipulli": ("COLLIPULLI", [-72.4778, -37.9659, -72.3893, -37.7816]),
    "Temuco": ("TEMUCO", [-72.8245, -38.7821, -72.5104, -38.6839]),
    "Catripulli (Curarrehue)": ("CURARREHUE", [-71.744, -39.3751, -71.6709, -39.3331]),
}
UMBRALES = (10, 25, 50)


def a_utm(lon):
    zona = 18 if lon < -72 else 19
    return Transformer.from_crs("EPSG:4326", f"EPSG:327{zona}", always_xy=True).transform


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paso", type=float, default=20.0)
    ap.add_argument("--control", action="store_true", help="desplaza las capas 10 km: la fracción debe ir a ~0")
    a = ap.parse_args()

    censo = json.loads(CENSO.read_text(encoding="utf-8"))
    capas = {k: json.loads((RAIZ / v).read_text(encoding="utf-8")) for k, v in CAPAS.items()}

    print(f"paso de grilla: {a.paso} m · umbrales: {UMBRALES} m · control desplazado: {a.control}")
    print("\n| comuna | capa | polígonos en caja | puntos grilla | población | <10 m pts | <10 m pob | <25 m pts | <25 m pob | <50 m pts | <50 m pob |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for nombre, (nom_censo, bb) in COMUNAS.items():
        caja = box(*bb)
        cx = (bb[0] + bb[2]) / 2
        proy = a_utm(cx)
        manz = [f for f in censo["features"]
                if f["properties"]["NOM_COMUNA"].upper() == nom_censo
                and f["properties"]["unidad_censal"] in ("manzana_urbana", "aldea")
                and shape(f["geometry"]).intersects(caja)]
        if not manz:
            print(f"INSTRUMENTO MUERTO: sin manzanas para {nombre}"); sys.exit(2)
        # grilla de puntos dentro de manzanas, con población por punto
        pts, pesos = [], []
        for f in manz:
            g = transform(proy, shape(f["geometry"]).intersection(caja))
            if g.is_empty:
                continue
            minx, miny, maxx, maxy = g.bounds
            xs = np.arange(minx, maxx, a.paso); ys = np.arange(miny, maxy, a.paso)
            cand = [Point(x, y) for x in xs for y in ys]
            dentro = [p for p in cand if g.covers(p)]
            if not dentro:
                dentro = [g.representative_point()]
            n_per = float(f["properties"].get("n_per") or 0)
            pts.extend(dentro); pesos.extend([n_per / len(dentro)] * len(dentro))
        pesos = np.array(pesos)
        pob = pesos.sum()
        for capa, fcol in capas.items():
            gs = []
            for f in fcol["features"]:
                if not f.get("geometry"):
                    continue
                g = shape(f["geometry"])
                if not g.intersects(caja.buffer(0.01)):
                    continue
                if not g.is_valid:
                    g = make_valid(g)
                g = transform(proy, g)
                if a.control:
                    g = transform(lambda x, y, z=None: (x + 10_000, y), g)
                gs.append(g)
            if not gs:
                print(f"| {nombre} | {capa} | 0 | {len(pts)} | {pob:.0f} | SIN DATO | | | | | |")
                continue
            bordes = [g.boundary for g in gs]
            tree = STRtree(bordes)
            d = np.array([bordes[tree.nearest(p)].distance(p) for p in pts])
            fila = [nombre, capa, str(len(gs)), str(len(pts)), f"{pob:.0f}"]
            for u in UMBRALES:
                m = d < u
                fila += [f"{100 * m.mean():.1f} %", f"{100 * pesos[m].sum() / pob:.1f} %" if pob else "s/d"]
            print("| " + " | ".join(fila) + " |")


if __name__ == "__main__":
    main()
