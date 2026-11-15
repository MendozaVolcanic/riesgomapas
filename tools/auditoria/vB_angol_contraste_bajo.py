"""vB: ¿cuánto del AR-2a oficial de Angol recupera el MISMO vectorizador con contraste más bajo?

No modifica el proyecto: llama a mascara_por_trama de scripts/18 con una copia de
la configuración de clase y polygoniza en memoria, igual que procesar_plano.

QUÉ MIDE
    Cobertura de G (AR-2a GeoIDE) y área fuera de G (N-G, falsos positivos
    respecto del oficial) para contraste_minimo 28 (producción), 20, 14 y 10.

LAS DOS PREGUNTAS DEL INSTRUMENTO
    (1) Si bajar el contraste no recuperara nada (el faltante no fuera trama
        sobre fondo oscuro), la cobertura no subiría: la prueba lo mostraría.
    (2) Si el instrumento estuviera muerto, con contraste 28 no reproduciría
        el N publicado. Se exige que con 28 la cobertura de G quede a menos de
        0,02 de la del N publicado (0,722) y el área a menos de 5 %.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np
import yaml
from shapely.geometry import shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vB_angol_porque_falta as base  # noqa: E402


def main():
    from affine import Affine
    from rasterio.features import shapes
    m18 = base.cargar_modulo18()
    cfgs = {c["id"]: c for c in yaml.safe_load(open(base.CFG, encoding="utf-8"))["laminas"] if c.get("id") in base.IDS}
    G = unary_union(base.cargar_G("AR-2a"))
    G2b = unary_union(base.cargar_G("AR-2b"))
    Npub = unary_union([g for _, g, _ in base.cargar_N()])
    ims = {}
    for lid in base.IDS:
        cfg = cfgs[lid]
        im = m18.imagenes_de(m18.DATA_RAW / cfg["pdf"], cfg["pagina"])[cfg.get("imagen", 0)]
        if cfg.get("rotar"):
            im = im.rotate(cfg["rotar"], expand=True)
        ims[lid] = np.array(im).astype(int)
    for c in (28, 20, 14, 10):
        gs = []
        for lid in base.IDS:
            cfg = cfgs[lid]; a = ims[lid]
            clase = copy.deepcopy(cfg["clases"][0]); clase["contraste_minimo"] = c
            sol, s, *_ = m18.afin_por_vertices(cfg)
            a_, b_, tx, ty = sol
            m, cel, _, _ = m18.mascara_por_trama(a, clase, s, m18.cajas_a_excluir(cfg, a.shape[1], a.shape[0]))
            T = Affine(a_ * cel, b_ * cel, tx, b_ * cel, -a_ * cel, ty)
            for geom, val in shapes(m, mask=m.astype(bool), transform=T):
                g = shape(geom)
                g = g if g.is_valid else g.buffer(0)
                if g.area >= float(cfg.get("area_minima_m2", 2000)):
                    gs.append(g)
        N = unary_union(gs)
        cov = G.intersection(N).area / G.area
        print(f"contraste {c:2d}: N {N.area/1e4:6.2f} ha | cobertura de G {cov:.3f} | G-N {G.difference(N).area/1e4:5.2f} ha"
              f" | N-G {N.difference(G).area/1e4:5.2f} ha | N-G fuera de AR-2b {N.difference(G).difference(G2b).area/1e4:5.2f} ha"
              f" | IoU {G.intersection(N).area/G.union(N).area:.3f} | G-N con N+10 m {G.difference(N.buffer(10)).area/1e4:5.2f} ha")
        if c == 28:
            cov_pub = G.intersection(Npub).area / G.area
            if abs(cov - cov_pub) > 0.02 or abs(N.area - Npub.area) / Npub.area > 0.05:
                sys.exit(f"instrumento no reproduce el publicado: {cov:.3f} vs {cov_pub:.3f}")


if __name__ == "__main__":
    main()
