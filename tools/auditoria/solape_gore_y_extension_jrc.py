"""Dos mediciones sobre las capas C que el visor resume con «el primero que
contiene el punto» (auditoría 2026-09-06, frente 2, patrones 2 y 5).

A. GORE (web/data/gore/amenaza-inundacion.geojson): el visor muestra
   `res.gore[0].properties.clase` (web/app.js:918). Si un polígono MAXIMA está
   contenido en uno MEDIA y el MEDIA va ANTES en el archivo, la ficha dice
   «media» para un punto de amenaza máxima. Se cuenta cuántos MAXIMA tienen su
   punto representativo dentro de algún MEDIA, y en cuántos de ésos el MEDIA
   aparece primero en el orden del archivo.
   Control: se construye a mano un par (MEDIA grande antes, MAXIMA chica
   dentro) y se verifica que el conteo lo ve.

B. JRC (data/processed/jrc/araucania_rp100.tif, si existe localmente): el
   contorno publicado llega sólo hasta lon −71,650 mientras la región llega a
   −70,90. Se mira si el ráster recortado cubre el bbox entero y hasta dónde hay
   píxeles > 0,25 m; así se sabe si el este de la región «queda fuera de la
   mancha» porque el modelo no ve agua ahí o porque el recorte no llegó.

Preguntas del instrumento: (1) si hubiera anidamiento y el orden fuera el malo,
el conteo sería > 0 (el control artificial lo demuestra); (2) si shapely o
rasterio no cargaran, el script termina con traza, no con ceros.

Uso:  python tools/auditoria/solape_gore_y_extension_jrc.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, shape
from shapely.strtree import STRtree

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]


def contar_anidados(feats):
    geoms = [shape(f["geometry"]) for f in feats]
    clases = [f["properties"]["clase"] for f in feats]
    media_idx = [i for i, c in enumerate(clases) if c == "MEDIA"]
    arbol = STRtree([geoms[i] for i in media_idx])
    anidados, media_primero = 0, 0
    ejemplos = []
    for i, c in enumerate(clases):
        if c != "MAXIMA":
            continue
        rp = geoms[i].representative_point()
        for j in arbol.query(rp):
            jj = media_idx[int(j)]
            if geoms[jj].contains(rp):
                anidados += 1
                if jj < i:
                    media_primero += 1
                    if len(ejemplos) < 3:
                        ejemplos.append((i, jj, (round(rp.x, 4), round(rp.y, 4))))
                break
    return anidados, media_primero, ejemplos


def main():
    d = json.loads((RAIZ / "web/data/gore/amenaza-inundacion.geojson").read_text(encoding="utf-8"))
    feats = d["features"]
    print(f"A. GORE: {len(feats)} polígonos; orden en archivo: primeros 5 =",
          [f["properties"]["clase"] for f in feats[:5]], "| primer MAXIMA en índice",
          next(i for i, f in enumerate(feats) if f["properties"]["clase"] == "MAXIMA"))
    a, mp, ej = contar_anidados(feats)
    print(f"   MAXIMA con punto representativo dentro de un MEDIA: {a}")
    print(f"   de ésos, el MEDIA va ANTES en el archivo (la ficha diría «media»): {mp}")
    print(f"   ejemplos (idx_maxima, idx_media, punto): {ej}")
    # control positivo
    ctrl = [{"geometry": Polygon([(0, 0), (10, 0), (10, 10), (0, 10)]).__geo_interface__, "properties": {"clase": "MEDIA"}},
            {"geometry": Polygon([(4, 4), (6, 4), (6, 6), (4, 6)]).__geo_interface__, "properties": {"clase": "MAXIMA"}}]
    print("   CONTROL artificial (MEDIA antes, MAXIMA dentro) →", contar_anidados(ctrl)[:2], "(esperado (1, 1))")

    tif = RAIZ / "data/processed/jrc/araucania_rp100.tif"
    print(f"\nB. JRC: {tif} existe={tif.exists()}")
    if tif.exists():
        import rasterio
        with rasterio.open(tif) as src:
            b = src.bounds
            arr = src.read(1)
            print(f"   extensión del recorte: lon [{b.left:.3f}, {b.right:.3f}] lat [{b.bottom:.3f}, {b.top:.3f}]  "
                  f"px={src.width}x{src.height} nodata={src.nodata}")
            mask = np.isfinite(arr) & (arr > 0.25)
            if src.nodata is not None:
                mask &= arr != src.nodata
            cols = np.where(mask.any(axis=0))[0]
            lon_max = src.xy(0, cols.max())[0] if cols.size else None
            print(f"   píxeles >0,25 m: {int(mask.sum())}; columna más al este con agua → lon ≈ {lon_max}")
            print(f"   ¿el recorte llega al este del bbox (−70,90)? {b.right >= -70.91}")
    pub = json.loads((RAIZ / "web/data/jrc/rp100.geojson").read_text(encoding="utf-8"))
    xs = [x for f in pub["features"] for ring in f["geometry"]["coordinates"] for x, _ in ring]
    print(f"   publicado rp100.geojson: lon máx = {max(xs):.3f}")


if __name__ == "__main__":
    main()
