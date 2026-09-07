"""Distribución de áreas de los polígonos publicados frente a `area_minima_m2`.

Pregunta: ¿cuántos polígonos de las láminas vectorizadas quedan justo por
encima del umbral de 2.000 m² (config/laminas.yaml), o sea, cuántos habrían
desaparecido con un umbral apenas distinto? Y de paso: cuánto mide el borde en
metros según `ancho_minimo_px` × m/px y `celda_px` × m/px, que es la magnitud
física real del criterio «demasiado delgado».

Área en m² calculada reproyectando a UTM (18S u 19S según la comuna), que es lo
que hace el propio script 18 antes de filtrar. También se reporta el área que
declara el campo `hectareas` del polígono, para verificar que coinciden.

Las dos preguntas del instrumento:
 (1) Si el filtro de área no funcionara (polígonos < 2.000 m² publicados), la
     cuenta «bajo el umbral» sería > 0 y se vería.
 (2) Si el instrumento estuviera muerto (reproyección mal hecha, área en grados),
     el control `--control` compara el área de un cuadrado conocido de 100 × 100 m
     y exige 10.000 m² ± 1 %.

Uso:
    python tools/auditoria/distribucion_areas_vs_area_minima.py [--control]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as sh_transform

RAIZ = Path(__file__).resolve().parents[2]
VECT = RAIZ / "web" / "data" / "laminas" / "vectorizadas.geojson"
LAMINAS = RAIZ / "data" / "processed" / "laminas"
AREA_MIN = 2000.0     # config/laminas.yaml líneas 70, 107, 156

EPSG = {"ANGOL": 32718, "CURARREHUE": 32719}
TR = {e: Transformer.from_crs("EPSG:4326", f"EPSG:{e}", always_xy=True) for e in EPSG.values()}


def area_m2(geom: dict, epsg: int) -> float:
    return sh_transform(TR[epsg].transform, shape(geom)).area


def main() -> None:
    if "--control" in sys.argv:
        lat, lon = -37.8, -72.7
        dlat = 100 / 111_320.0
        import math
        dlon = 100 / (111_320.0 * math.cos(math.radians(lat)))
        cuadro = {"type": "Polygon", "coordinates": [[
            [lon, lat], [lon + dlon, lat], [lon + dlon, lat + dlat], [lon, lat + dlat], [lon, lat]]]}
        a = area_m2(cuadro, 32718)
        assert abs(a - 10_000) / 10_000 < 0.01, a
        print(f"CONTROL POSITIVO OK: cuadrado 100×100 m → {a:.1f} m²")
        return

    fc = json.loads(VECT.read_text(encoding="utf-8"))
    por_lamina: dict[str, list[tuple[float, float]]] = {}
    for f in fc["features"]:
        p = f["properties"]
        a = area_m2(f["geometry"], EPSG[p["comuna"]])
        por_lamina.setdefault(p["origen_lamina"], []).append((a, p.get("hectareas", 0) * 10_000))

    print(f"{len(fc['features'])} polígonos en {VECT.relative_to(RAIZ)}")
    for lam, vals in por_lamina.items():
        a = np.array([v[0] for v in vals])
        decl = np.array([v[1] for v in vals])
        meta = json.loads((LAMINAS / f"{lam}.geojson").read_text(encoding="utf-8"))
        mpx = meta.get("procedencia", {}).get("metros_por_pixel") or meta.get("metros_por_pixel")
        print(f"\n[{lam}]  n={len(a)}  m/px={mpx}")
        print(f"  área m²: min {a.min():.0f} · p10 {np.percentile(a, 10):.0f} · mediana "
              f"{np.median(a):.0f} · p90 {np.percentile(a, 90):.0f} · max {a.max():.0f}")
        print(f"  bajo el umbral ({AREA_MIN:.0f} m²): {(a < AREA_MIN).sum()}")
        print(f"  en [2000, 3000) m²: {((a >= 2000) & (a < 3000)).sum()}  "
              f"· en [2000, 4000): {((a >= 2000) & (a < 4000)).sum()}  "
              f"· ≤ 1 ha: {(a <= 10_000).sum()}")
        print(f"  diferencia máx entre área recalculada y `hectareas` declarado: "
              f"{np.abs(a - decl).max():.0f} m²")
        if mpx:
            print(f"  umbral en píxeles: {AREA_MIN / mpx ** 2:.0f} px de {mpx} m")


if __name__ == "__main__":
    main()
