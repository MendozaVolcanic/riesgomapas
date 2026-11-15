"""vB: ¿el faltante del AR-2a de Angol es achurado sobre fondo oscuro que el vectorizador no ve?

Complementa vB_angol_porque_falta.py. Hipótesis que nace de mirar los recortes: la
lámina SÍ achura AR-2a sobre las zonas Z-1 (rojo oscuro) y Z-5 (café), pero el
detector de marcas exige que el triángulo sea `contraste_minimo` (28 niveles de
gris) más oscuro que su vecindad, y sobre un fondo oscuro eso no se cumple.

QUÉ MIDE
    1. Luminancia del fondo (mediana 21 px, la misma que usa el vectorizador) en
       puntos cada 3 m dentro de G∩N y dentro de G-N.
    2. Densidad de marcas con contraste_minimo 28 (el de producción) y con 14, en
       G∩N, en G-N con fondo claro, en G-N con fondo oscuro, y en un anillo de
       300 m fuera de G∪N (ruido).
    3. Cuánto se solapan en GeoIDE el AR-2a y el AR-2b (¿la lámina rotula AR-2b
       un corredor que GeoIDE codifica AR-2a?).

LAS DOS PREGUNTAS DEL INSTRUMENTO
    (1) Si la hipótesis fuera falsa (G-N sin achurado), ¿se notaría? Sí: con
        contraste 14 la densidad en G-N oscuro seguiría cerca del anillo de
        ruido; --control lo comprueba inyectando un cuadrado de G en fondo
        oscuro SIN achurado (zona Z-1 lejos de AR) y exige densidad de ruido.
    (2) Si el instrumento estuviera muerto, ¿se vería distinto? La densidad en
        G∩N con contraste 28 tiene que reproducir la de vB_angol_porque_falta
        (149/ha); si no, se aborta.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml
from shapely import contains_xy
from shapely.geometry import box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vB_angol_porque_falta as base  # noqa: E402


def marcas(a, clase, contraste, exc):
    import cv2
    g = cv2.cvtColor(a.astype("uint8"), cv2.COLOR_RGB2GRAY)
    fondo = cv2.medianBlur(g, 21)
    osc = ((fondo.astype("int16") - g.astype("int16")) > contraste).astype("uint8")
    n, lab, st, cent = cv2.connectedComponentsWithStats(osc, 8)
    amin, amax = clase["marca_area"]; lmin, lmax = clase["marca_lado"]
    ar, an, al = st[1:, 2 + 2], st[1:, 2], st[1:, 3]
    sel = (ar >= amin) & (ar <= amax) & (an >= lmin) & (an <= lmax) & (al >= lmin) & (al <= lmax)
    p = cent[1:][sel]
    return np.array([q for q in p if not exc[int(q[1]), int(q[0])]]), fondo


def main():
    control = "--control" in sys.argv
    m18 = base.cargar_modulo18()
    cfgs = {c["id"]: c for c in yaml.safe_load(open(base.CFG, encoding="utf-8"))["laminas"] if c.get("id") in base.IDS}
    G = unary_union(base.cargar_G("AR-2a"))
    G2b = unary_union(base.cargar_G("AR-2b"))
    N = unary_union([g for _, g, _ in base.cargar_N()])
    print(f"GeoIDE AR-2a ∩ AR-2b: {G.intersection(G2b).area/1e4:.2f} ha de {G2b.area/1e4:.2f} ha de AR-2b")
    print(f"AR-2b a menos de 5 m de AR-2a: {G2b.intersection(G.buffer(5)).area/1e4:.2f} ha")
    falta = G.difference(N)
    inter = G.intersection(N)
    filas = {}
    for lid in base.IDS:
        cfg = cfgs[lid]
        im = m18.imagenes_de(m18.DATA_RAW / cfg["pdf"], cfg["pagina"])[cfg.get("imagen", 0)]
        if cfg.get("rotar"):
            im = im.rotate(cfg["rotar"], expand=True)
        a = np.array(im).astype(int)
        H, W = a.shape[:2]
        exc = m18.cajas_a_excluir(cfg, W, H)
        sol, *_ = m18.afin_por_vertices(cfg)
        a_, b_, tx, ty = sol
        M = np.array([[a_, b_], [b_, -a_]]); Mi = np.linalg.inv(M)
        hu = base.marcas_y_huella(m18, cfg)[1]
        # grilla de 3 m en la huella
        x0, y0, x1, y1 = hu.bounds
        xs, ys = np.meshgrid(np.arange(x0, x1, 3.0), np.arange(y0, y1, 3.0))
        xs, ys = xs.ravel(), ys.ravel()
        k = contains_xy(hu, xs, ys); xs, ys = xs[k], ys[k]
        px = Mi @ np.vstack([xs - tx, ys - ty])
        ix, iy = np.clip(px[0].astype(int), 0, W - 1), np.clip(px[1].astype(int), 0, H - 1)
        res = {}
        for c in (28, 14):
            pts, fondo = marcas(a, cfg["clases"][0], c, exc)
            E = a_ * pts[:, 0] + b_ * pts[:, 1] + tx
            Nn = b_ * pts[:, 0] - a_ * pts[:, 1] + ty
            res[c] = (np.column_stack([E, Nn]), fondo)
        fondo = res[28][1]
        lum = fondo[iy, ix]
        en_inter = contains_xy(inter, xs, ys)
        en_falta = contains_xy(falta, xs, ys)
        filas[lid] = dict(xs=xs, ys=ys, lum=lum, en_inter=en_inter, en_falta=en_falta, res=res, hu=hu)
        print(f"\n== {lid} ==")
        for nom, m in (("G∩N", en_inter), ("G-N", en_falta)):
            if m.sum():
                q = np.percentile(lum[m], [10, 50, 90])
                print(f"  fondo gris en {nom}: p10/p50/p90 = {q[0]:.0f}/{q[1]:.0f}/{q[2]:.0f} (n={m.sum()})")
        UMBRAL = 150
        print(f"  G-N con fondo oscuro (<{UMBRAL}): {(en_falta & (lum < UMBRAL)).sum()*9/1e4:.2f} ha de {en_falta.sum()*9/1e4:.2f} ha")
        print(f"  G∩N con fondo oscuro (<{UMBRAL}): {(en_inter & (lum < UMBRAL)).sum()*9/1e4:.2f} ha de {en_inter.sum()*9/1e4:.2f} ha")
        anillo = hu.intersection(G.union(N).buffer(300)).difference(G.union(N).buffer(30))
        for c in (28, 14):
            pts = res[c][0]
            def dens(mask_pts_area):
                return mask_pts_area
            def d_geom(geom):
                k = contains_xy(geom, pts[:, 0], pts[:, 1]).sum()
                return k / (geom.area / 1e4) if geom.area else float("nan")
            # densidad por fondo: contar marcas en celdas de 3 m clasificadas
            def d_celdas(mascara):
                if mascara.sum() == 0:
                    return float("nan")
                sub = box(0, 0, 0, 0)
                # marca -> celda de grilla más cercana
                from scipy.spatial import cKDTree
                t = cKDTree(np.column_stack([xs[mascara], ys[mascara]]))
                dd, _ = t.query(pts, distance_upper_bound=2.2)
                return np.isfinite(dd).sum() / (mascara.sum() * 9 / 1e4)
            print(f"  contraste {c}: marcas/ha G∩N {d_celdas(en_inter):.0f} | G-N claro {d_celdas(en_falta & (lum >= UMBRAL)):.0f}"
                  f" | G-N oscuro {d_celdas(en_falta & (lum < UMBRAL)):.0f} | anillo ruido {d_geom(anillo):.0f}"
                  f" | anillo ruido oscuro {d_celdas(contains_xy(anillo, xs, ys) & (lum < UMBRAL)):.0f}")
        if lid == base.IDS[0]:
            pts = res[28][0]
            k = contains_xy(inter, pts[:, 0], pts[:, 1]).sum()
            print(f"  (chequeo vivo: {k} marcas c28 en G∩N de esta lámina)")
            if k < 1000:
                sys.exit("instrumento muerto")

    # Descomposición de G-N sin doble conteo entre láminas (la lámina 2 sólo
    # aporta los puntos que no caen en la huella de la lámina 1).
    print("\n== Descomposición de G-N (celdas de 3 m) ==")
    N10 = N.buffer(10)
    tot = {"borde<=10m": 0, "oscuro>10m": 0, "claro>10m_en_AR2b": 0, "claro>10m_resto": 0}
    hu1 = filas[base.IDS[0]]["hu"]
    for j, lid in enumerate(base.IDS):
        f = filas[lid]
        m = f["en_falta"].copy()
        if j == 1:
            m &= ~contains_xy(hu1, f["xs"], f["ys"])
        cerca = contains_xy(N10, f["xs"], f["ys"])
        en2b = contains_xy(G2b, f["xs"], f["ys"])
        osc = f["lum"] < 150
        tot["borde<=10m"] += (m & cerca).sum()
        tot["oscuro>10m"] += (m & ~cerca & osc).sum()
        tot["claro>10m_en_AR2b"] += (m & ~cerca & ~osc & en2b).sum()
        tot["claro>10m_resto"] += (m & ~cerca & ~osc & ~en2b).sum()
    for k, v in tot.items():
        print(f"  {k:20s} {v*9/1e4:6.2f} ha")
    print(f"  total {sum(tot.values())*9/1e4:.2f} ha (G-N exacto {falta.area/1e4:.2f} ha)")

    if control:
        print("\n== CONTROL: cuadrado de fondo oscuro sin AR, lejos de G∪N ==")
        f = filas[base.IDS[0]]
        oscuro = f["lum"] < 150
        lejos = ~contains_xy(G.union(N).union(G2b).buffer(150), f["xs"], f["ys"])
        cand = np.where(oscuro & lejos)[0]
        # tomar el punto oscuro lejano cuyo vecindario de 60 m sea mayormente oscuro
        from scipy.spatial import cKDTree
        t = cKDTree(np.column_stack([f["xs"], f["ys"]]))
        mejor = None
        for i in cand[:: max(1, len(cand) // 400)]:
            vec = t.query_ball_point([f["xs"][i], f["ys"][i]], 40)
            fr = oscuro[vec].mean()
            if mejor is None or fr > mejor[1]:
                mejor = (i, fr)
        i = mejor[0]
        cx, cy = f["xs"][i], f["ys"][i]
        sq = box(cx - 40, cy - 40, cx + 40, cy + 40)
        for c in (28, 14):
            pts = f["res"][c][0]
            k = contains_xy(sq, pts[:, 0], pts[:, 1]).sum()
            print(f"  contraste {c}: cuadrado oscuro sin AR en {cx:.0f},{cy:.0f} (fracción oscura {mejor[1]:.2f}): {k/(sq.area/1e4):.0f} marcas/ha")


if __name__ == "__main__":
    main()
