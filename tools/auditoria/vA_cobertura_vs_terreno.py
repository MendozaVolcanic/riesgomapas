"""vA_cobertura_vs_terreno.py : F-109, ¿«el satélite sí miró este punto» en terreno
que el método excluye?

POR QUÉ. La cobertura publicada (web/data/sar/cobertura-sar.geojson) se decima
en bloques de 32 px y un bloque cuenta como observado si >= 1/4 de sus píxeles
lo fue (scripts/14_sar_huella_observada.py). El visor lee esa capa para decir
«el satélite sí miró este punto y no detectó agua». Pero un píxel sólo cuenta
como observado si el terreno es apto (pendiente <= 5°, 0,5 m <= altitud <=
1200 m, config/araucania.yaml). Esta sonda toma puntos al azar DENTRO de los
polígonos publicados de cobertura y mide en cuántos el terreno es no apto.

LAS DOS PREGUNTAS DEL INSTRUMENTO
 1. Si la cobertura publicada fuera exacta (sólo terreno apto), ¿lo vería? Sí:
    daría ~0 % no apto. CONTROL: se mide también el % no apto sobre puntos al
    azar de TODO el recuadro del DEM (fuera de cobertura); si el detector está
    bien, ahí tiene que dar mucho más alto que dentro.
 2. Si el instrumento estuviera muerto (terreno.tif ilegible), lanza error, no
    imprime 0 %.
Uso: python -I tools/auditoria/vA_cobertura_vs_terreno.py
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
import rasterio
from shapely.geometry import shape, Point
from shapely.prepared import prep
from shapely.ops import unary_union

RAIZ = Path(__file__).resolve().parents[2]
terreno = RAIZ / "data/processed/sar/2026-07-30_sistema_frontal/terreno.tif"
cob = json.load(open(RAIZ / "web/data/sar/cobertura-sar.geojson", encoding="utf-8"))
geoms = [shape(f["geometry"]) for f in cob["features"]]
u = unary_union(geoms)
print("polígonos de cobertura:", len(geoms), "| área bbox:", [round(x, 3) for x in u.bounds])

random.seed(1)
with rasterio.open(terreno) as src:
    dem, pend = src.read(1), src.read(2)
    print("terreno.tif:", src.crs, src.shape, "bounds", [round(x, 3) for x in src.bounds])
    if src.crs.to_epsg() != 4326:
        sys.exit("CRS inesperado, la sonda asume EPSG:4326")

    def apto_en(lon, lat):
        r, c = src.index(lon, lat)
        if not (0 <= r < src.height and 0 <= c < src.width):
            return None
        d, p = dem[r, c], pend[r, c]
        return bool(np.isfinite(d) and np.isfinite(p) and p <= 5.0 and 0.5 <= d <= 1200.0)

    def muestrea(region, n):
        w, s, e, nn = region.bounds
        pr = prep(region)
        out = []
        tries = 0
        while len(out) < n and tries < n * 200:
            tries += 1
            lon, lat = random.uniform(w, e), random.uniform(s, nn)
            if pr.contains(Point(lon, lat)):
                a = apto_en(lon, lat)
                if a is not None:
                    out.append(a)
        return out

    dentro = muestrea(u, 20000)
    from shapely.geometry import box
    fuera = muestrea(box(*src.bounds).difference(u), 20000)

print(f"puntos DENTRO de la cobertura publicada: {len(dentro)}; terreno NO apto: {len(dentro) - sum(dentro)} ({100 * (1 - np.mean(dentro)):.1f} %)")
if fuera:
    print(f"CONTROL puntos FUERA de la cobertura (mismo DEM): {len(fuera)}; NO apto: {100 * (1 - np.mean(fuera)):.1f} %")
else:
    print("CONTROL: SIN DATO (no hay recuadro fuera de la cobertura)")
