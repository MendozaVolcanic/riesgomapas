#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fC_tamano_publicable.py: cuánto pesaría publicar la población por manzana para el
visor offline, en varias formas. Mide, no decide.

Variantes (todas con el censo SIN las 33 aldeas duplicadas, ver fC_poblacion_expuesta):
  V0  el geojson del censo tal como está en data/processed
  V1  todas las unidades, sólo campos útiles (MANZENT, comuna, unidad, n_per y los ocho
      de vulnerabilidad), coordenadas redondeadas a 5 decimales
  V2  sólo las unidades que tocan alguna mancha de ALGUNA capa (la unión sirve sólo para
      elegir qué manzanas viajan; cada cruce se sigue haciendo capa por capa), mismos
      campos y redondeo. Se mide también sin GORE ni JRC, que son las capas que más
      unidades arrastran.
  V3  las piezas de manzana recortadas a cada mancha, un archivo por capa (las capas no
      se fusionan), con la fracción de área y la gente repartida de cada pieza
  V4  la tabla precalculada por capa y comuna (los CSV de este frente)
Cada una se mide en bytes crudos y con gzip -9.

LAS DOS PREGUNTAS DEL INSTRUMENTO
  1. Si la medida estuviera rota (gzip que no comprime, redondeo que mueve la geometría
     más de lo declarado), ¿se notaría? --control comprime y descomprime cada salida y
     exige igualdad byte a byte; mide el corrimiento máximo del redondeo a 5 decimales
     en metros y exige que sea < 1 m; y exige que V0 medido coincida con os.stat.
  2. Si el instrumento estuviera muerto (archivos vacíos), ¿se vería distinto? Sí: el
     control exige que V1 contenga exactamente las 17.074 unidades y 1.003.546 personas.

Uso:  python tools/auditoria/fC_tamano_publicable.py [--control]
"""
from __future__ import annotations

import gzip
import io
import json
import os
import sys
import tempfile
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

warnings.simplefilter("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fC_poblacion_expuesta as X  # noqa: E402

CAMPOS = ["MANZENT", "NOM_COMUNA", "unidad_censal", "n_per"] + X.CAMPOS_V


def medir(datos: bytes) -> tuple[int, int, bool]:
    z = gzip.compress(datos, compresslevel=9)
    return len(datos), len(z), gzip.decompress(z) == datos


def redondear(geoms, dec: int = 5):
    """Redondeo simple de cada vértice. NO usa set_precision: ése preserva topología a
    costa de mover vértices hasta decenas de metros en manzanas angostas (medido)."""
    return shapely.transform(np.asarray(geoms), lambda xy: np.round(xy, dec))


def a_geojson(g: gpd.GeoDataFrame, dec: int = 5) -> bytes:
    g = g.to_crs(4326).copy()
    g["geometry"] = redondear(g.geometry.values, dec)
    return g.to_json(drop_id=True, na="drop").encode("utf-8")


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    control = "--control" in sys.argv
    ok = True
    filas = []

    crudo = X.CENSO.read_bytes()
    b, z, rt = medir(crudo)
    filas.append(("V0 geojson del censo tal cual", 17107, b, z))
    if control:
        ok &= (b == os.stat(X.CENSO).st_size) and rt

    g, info = X.preparar_censo(gpd.read_file(X.CENSO))
    g = g.copy()
    for c in ["n_per"] + X.CAMPOS_V:
        g[c] = g[c].astype(int)
    v1 = g[CAMPOS + ["geometry"]]
    d1 = a_geojson(v1)
    b, z, rt = medir(d1)
    filas.append(("V1 todas las unidades, campos útiles, 5 decimales", len(v1), b, z))
    if control:
        ok &= rt and len(v1) == 17074 and int(v1["n_per"].sum()) == 1003546
        orig = v1.to_crs(4326).geometry.values
        o_m = gpd.GeoSeries(orig, crs=4326).to_crs(X.CRS_M).values
        for nom, red in (("redondeo simple", redondear(orig)),
                         ("set_precision", shapely.set_precision(orig, 1e-5))):
            r_m = gpd.GeoSeries(red, crs=4326).to_crs(X.CRS_M).values
            hd = shapely.hausdorff_distance(o_m, r_m)
            da = np.abs(shapely.area(r_m) - shapely.area(o_m)) / shapely.area(o_m)
            peor = int(np.nanargmax(hd))
            print(f"{nom} a 5 decimales: corrimiento máximo {np.nanmax(hd):.3f} m "
                  f"(MANZENT {v1['MANZENT'].iloc[peor]}, {v1['NOM_COMUNA'].iloc[peor]}), p99 {np.nanpercentile(hd, 99):.3f} m, "
                  f"cambio de área máx {100 * np.nanmax(da):.3f} %, inválidas {int((~shapely.is_valid(red)).sum())}, "
                  f"vacías {int(shapely.is_empty(red).sum())}")
            if nom == "redondeo simple":
                ok &= np.nanmax(hd) < 1.0

    toca_todas = np.zeros(len(g), bool)
    toca_finas = np.zeros(len(g), bool)
    piezas_bytes = piezas_gz = 0
    n_piezas = 0
    vistas = set()
    for capa, sub, arch, filtro, _ in X.CAPAS:
        if sub in ("todas_disueltas",):
            continue
        c = X.leer_capa(arch, filtro).to_crs(X.CRS_M)
        H = X.disolver(c.geometry.values)
        fr = X.fracciones(g, H)
        t = fr["a_in"].values > 0
        toca_todas |= t
        if not sub.startswith(("gore", "jrc")):
            toca_finas |= t
        # V3: piezas recortadas, una capa a la vez; sin repetir la misma mancha
        clave = (arch, sub)
        if clave in vistas:
            continue
        vistas.add(clave)
        idx = np.where(t)[0]
        if len(idx) == 0:
            continue
        pz = gpd.GeoDataFrame(g.iloc[idx][["MANZENT", "NOM_COMUNA", "unidad_censal"]].copy(),
                              geometry=shapely.intersection(g.geometry.values[idx], H), crs=X.CRS_M)
        f = fr["a_in"].values[idx] / g["area_u"].values[idx]
        pz["frac"] = np.round(np.minimum(f, 1), 4)
        for col in ["n_per"] + X.CAMPOS_V:
            pz[col + "_rep"] = np.round(g[col].values[idx] * pz["frac"].values, 1)
        d = a_geojson(pz)
        b3, z3, rt3 = medir(d)
        ok &= rt3 if control else True
        piezas_bytes += b3
        piezas_gz += z3
        n_piezas += len(pz)
        filas.append((f"   V3 pieza {capa}/{sub}", len(pz), b3, z3))

    for nom, m in (("V2 unidades que tocan alguna mancha (todas las capas)", toca_todas),
                   ("V2b unidades que tocan alguna mancha sin GORE ni JRC", toca_finas)):
        d = a_geojson(v1[m])
        b, z, rt = medir(d)
        ok &= rt if control else True
        filas.append((nom, int(m.sum()), b, z))
    filas.append(("V3 piezas recortadas, suma de todos los archivos por capa", n_piezas, piezas_bytes, piezas_gz))

    tablas = sorted(X.SALIDA.glob("expuesta_*.csv"))
    tb = b"".join(p.read_bytes() for p in tablas)
    b, z, rt = medir(tb)
    filas.append((f"V4 tablas precalculadas por capa y comuna ({len(tablas)} CSV)", len(tablas), b, z))

    df = pd.DataFrame(filas, columns=["variante", "elementos", "bytes", "bytes_gzip9"])
    df["MB"] = (df["bytes"] / 1e6).round(2)
    df["MB_gzip"] = (df["bytes_gzip9"] / 1e6).round(3)
    print(df.to_string(index=False))
    df.to_csv(X.SALIDA / "tamano_publicable.csv", index=False, encoding="utf-8")
    print("escrito:", X.SALIDA / "tamano_publicable.csv")
    if control:
        print("CONTROL:", "OK" if ok else "FALLA")
        sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
