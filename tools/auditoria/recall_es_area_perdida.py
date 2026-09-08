#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""El recall del vectorizador es bajo. ¿Significa que falta mancha?

Las dos preguntas del instrumento
---------------------------------
1. ¿Qué mide? Dónde caen las marcas del achurado que NO quedaron dentro de un
   polígono publicado: si se agrupan con la densidad del achurado real —una
   mancha entera sin capturar— o si están dispersas —texto, símbolos, tramas de
   otras zonas, y el borde donde el achurado se desvanece—.
2. ¿Cómo sabría que se equivoca? Con `--control`, que borra a propósito el
   polígono publicado más grande y exige que aparezcan celdas de densidad plena
   fuera. Si no las ve, no sabría reconocer una mancha perdida ni cuando la hay.

Por qué existe
--------------
`fidelidad_laminas.py` reporta un recall de 68–76 % en las láminas del PRC de
Angol, y un recall así se lee como «falta un cuarto del área». No es lo mismo.
El detector cuenta manchitas oscuras del tamaño del achurado, y a esa definición
también responden las letras de un rótulo, los símbolos del plano y las tramas
de zonas que no son AR-2a. Un recall bajo puede ser eso, o puede ser una mancha
entera que el vectorizador no vio, y **son cosas opuestas**: la primera no se
arregla, la segunda es un defecto grave.

Lo que separa una de otra es la densidad. El achurado impreso tiene una densidad
característica; el ruido, no. Una mancha AR-2a sin capturar aparecería como un
grupo de celdas con densidad de achurado pleno fuera de lo publicado.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tools" / "auditoria"))

CELDA_PX = 100          # ~85 m de lado a la escala de estas láminas


def marcas_de(cfg: dict, vec, cv2) -> tuple[np.ndarray, tuple]:
    """Réplica del detector de marcas de `fidelidad_laminas`, con su ajuste."""
    im = vec.imagenes_de(vec.DATA_RAW / cfg["pdf"], cfg["pagina"])[cfg.get("imagen", 0)]
    if cfg.get("rotar"):
        im = im.rotate(cfg["rotar"], expand=True)
    a = np.array(im).astype(int)
    clase = cfg["clases"][0]
    g = cv2.cvtColor(a.astype("uint8"), cv2.COLOR_RGB2GRAY)
    osc = ((cv2.medianBlur(g, 21).astype("int16") - g.astype("int16"))
           > clase.get("contraste_minimo", 28)).astype("uint8")
    _, _, st, cent = cv2.connectedComponentsWithStats(osc, 8)
    amin, amax = clase.get("marca_area", [8, 45])
    lmin, lmax = clase.get("marca_lado", [4, 11])
    ar = st[1:, cv2.CC_STAT_AREA]
    an, al = st[1:, cv2.CC_STAT_WIDTH], st[1:, cv2.CC_STAT_HEIGHT]
    m = cent[1:][(ar >= amin) & (ar <= amax) & (an >= lmin) & (an <= lmax)
                 & (al >= lmin) & (al <= lmax)]
    ex = cfg.get("excluir_x")
    if ex is not None:
        m = m[m[:, 0] < ex]
    return m, vec.afin_por_vertices(cfg)[0]


def por_celda(pts: np.ndarray) -> np.ndarray:
    c = (pts // CELDA_PX).astype(int)
    _, n = np.unique(c[:, 0] * 100000 + c[:, 1], return_counts=True)
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--laminas", nargs="*",
                    default=["angol-prc-ar2a-lamina1", "angol-prc-ar2a-lamina2"])
    ap.add_argument("--control", action="store_true",
                    help="borra el polígono publicado mayor y exige detectarlo")
    a = ap.parse_args()

    warnings.filterwarnings("ignore")
    import importlib

    import cv2
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from shapely.prepared import prep
    vec = importlib.import_module("18_vectorizar_laminas")
    fid = importlib.import_module("fidelidad_laminas")

    lam = {c["id"]: c for c in yaml.safe_load(
        (RAIZ / "config" / "laminas.yaml").read_text(encoding="utf-8"))["laminas"]}

    sospechosas_total = 0
    for lid in a.laminas:
        cfg = lam[lid]
        marcas, (a_, b_, tx, ty) = marcas_de(cfg, vec, cv2)
        geoms = [g for g, _ in fid.publicados(lid, cfg["epsg"]).get(
            cfg["clases"][0]["nombre"], [])]
        if a.control:
            # Se quita la mancha más grande: sus marcas TIENEN que aparecer
            # fuera, y con densidad de achurado pleno.
            geoms = sorted(geoms, key=lambda g: g.area)[:-1]
        U = prep(unary_union(geoms))
        dentro = np.array([U.contains(Point(a_ * x + b_ * y + tx, b_ * x - a_ * y + ty))
                           for x, y in marcas])
        nd, nf = por_celda(marcas[dentro]), por_celda(marcas[~dentro])
        p90 = int(np.percentile(nd, 90))
        sospechosas = int((nf >= p90).sum())
        sospechosas_total += sospechosas
        print(f"{lid}")
        print(f"   marcas: {len(marcas)} · {int(dentro.sum())} dentro · "
              f"{int((~dentro).sum())} fuera "
              f"(recall {100 * dentro.mean():.1f} %)")
        print(f"   densidad del achurado capturado: mediana {int(np.median(nd))}"
              f"/celda, p90 {p90}, máx {nd.max()}")
        print(f"   densidad de lo que queda fuera : mediana {int(np.median(nf))}"
              f"/celda, máx {nf.max()}")
        print(f"   celdas fuera con densidad de achurado pleno (≥ {p90}): "
              f"**{sospechosas}**\n")

    if a.control:
        ok = sospechosas_total > 0
        sys.stderr.write("CONTROL POSITIVO: %s\n" % (
            f"OK — ve {sospechosas_total} celda(s) plenas al borrar una mancha"
            if ok else "FALLA — no reconoce una mancha perdida ni cuando la hay"))
        return 0 if ok else 2

    if sospechosas_total:
        print(f"❌ {sospechosas_total} celda(s) con achurado denso fuera de lo "
              "publicado: hay mancha sin capturar, mírala en la lámina")
        return 2
    print("✅ nada de lo que queda fuera alcanza la densidad del achurado: el "
          "recall bajo es ruido disperso y borde, no área perdida")
    return 0


if __name__ == "__main__":
    sys.exit(main())
