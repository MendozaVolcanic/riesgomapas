"""vB: por qué falta parte del AR-2a oficial de Angol en nuestras láminas vectorizadas.

Verificación del hallazgo F-200 (frente B, 2026-11-15). No modifica nada del proyecto.

QUÉ MIDE
    G = AR-2a de GeoIDE capa 29 (descarga propia, EPSG:32718 nativo).
    N = nuestros AR-2a publicados en web/data/laminas/vectorizadas.geojson.
    Cobertura de G por N, el faltante G-N en piezas, y para cada pieza la DENSIDAD
    de marcas triangulares de AR-2a que la propia lámina tiene dibujadas en ese
    lugar, comparada con la densidad dentro de G∩N. Con eso separa tres causas:
      (a) la lámina sí achura ahí y el vectorizador lo perdió (densidad alta,
          comparable a la de G∩N);
      (b) la lámina no achura ahí: el plano de la lámina y la capa de GeoIDE son
          versiones distintas, o la lámina usa otra trama (densidad ~0);
      (c) error de georreferencia: el faltante es una franja pegada a N y una
          traslación pequeña lo recupera (se mide la traslación óptima).
    También mide qué parte de G cae fuera de la huella útil de ambas láminas.

LAS DOS PREGUNTAS DEL INSTRUMENTO
    (1) Si el fenómeno estuviera completamente roto (el vectorizador perdiera
        zonas achuradas), ¿la prueba fallaría? Sí: --control borra de N el
        polígono más grande y exige que el instrumento lo clasifique como (a),
        con densidad de marcas comparable a la de G∩N.
    (2) Si el instrumento estuviera muerto (no detectara marcas, o la
        transformación píxel->UTM estuviera mal), ¿el resultado se vería
        distinto? Sí: la densidad de marcas en G∩N tiene que salir alta; si
        sale ~0 el instrumento no ve la trama y se aborta. --control además
        inyecta en G un polígono falso lejos de cualquier achurado y exige que
        salga como (b).

Uso:
    python tools/auditoria/vB_angol_porque_falta.py [--control] [--png DIR]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import yaml
from pyproj import Transformer
from shapely.geometry import Point, Polygon, shape, box
from shapely.ops import transform as sh_transform, unary_union
from shapely import affinity

RAIZ = Path(__file__).resolve().parents[2]
G_JSON = RAIZ / "data/raw/geoide_minvu_araucania_verif/capa29_todo_32718.json"
N_GEOJSON = RAIZ / "web/data/laminas/vectorizadas.geojson"
CFG = RAIZ / "config/laminas.yaml"
IDS = ["angol-prc-ar2a-lamina1", "angol-prc-ar2a-lamina2"]


def cargar_modulo18():
    sys.path.insert(0, str(RAIZ / "scripts"))
    spec = importlib.util.spec_from_file_location("v18", RAIZ / "scripts/18_vectorizar_laminas.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def esri_a_shapely(geom):
    # Anillos ESRI: horario = exterior, antihorario = hueco.
    ext, hue = [], []
    for r in geom["rings"]:
        p = Polygon(r)
        (ext if not p.exterior.is_ccw else hue).append(p)
    g = unary_union(ext)
    for h in hue:
        g = g.difference(h)
    return g if g.is_valid else g.buffer(0)


def cargar_G(zona="AR-2a"):
    d = json.load(open(G_JSON, encoding="utf-8"))
    gs = [esri_a_shapely(f["geometry"]) for f in d["features"] if f["attributes"]["ZONA"] == zona]
    return gs


def cargar_N():
    d = json.load(open(N_GEOJSON, encoding="utf-8"))
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32718", always_xy=True)
    out = []
    for f in d["features"]:
        p = f["properties"]
        if p.get("clase") == "AR-2a" and p.get("comuna") == "ANGOL":
            g = sh_transform(tr.transform, shape(f["geometry"]))
            out.append((p.get("origen_lamina"), g if g.is_valid else g.buffer(0), p.get("hectareas")))
    return out


def marcas_y_huella(m18, cfg):
    """Marcas triangulares AR-2a de la lámina (en UTM 32718) y huella útil."""
    import cv2
    pdf = m18.DATA_RAW / cfg["pdf"]
    im = m18.imagenes_de(pdf, cfg["pagina"])[cfg.get("imagen", 0)]
    if cfg.get("rotar"):
        im = im.rotate(cfg["rotar"], expand=True)
    a = np.array(im).astype(int)
    sol, s, rot, rmse, _ = m18.afin_por_vertices(cfg)
    a_, b_, tx, ty = sol
    H, W = a.shape[:2]
    exc = m18.cajas_a_excluir(cfg, W, H)
    clase = cfg["clases"][0]
    g = cv2.cvtColor(a.astype("uint8"), cv2.COLOR_RGB2GRAY)
    fondo = cv2.medianBlur(g, 21)
    osc = ((fondo.astype("int16") - g.astype("int16")) > clase.get("contraste_minimo", 28)).astype("uint8")
    n, lab, st, cent = cv2.connectedComponentsWithStats(osc, 8)
    amin, amax = clase["marca_area"]; lmin, lmax = clase["marca_lado"]
    ar, an, al = st[1:, cv2.CC_STAT_AREA], st[1:, cv2.CC_STAT_WIDTH], st[1:, cv2.CC_STAT_HEIGHT]
    sel = (ar >= amin) & (ar <= amax) & (an >= lmin) & (an <= lmax) & (al >= lmin) & (al <= lmax)
    pts = cent[1:][sel]
    pts = np.array([p for p in pts if not exc[int(p[1]), int(p[0])]])
    E = a_ * pts[:, 0] + b_ * pts[:, 1] + tx
    N = b_ * pts[:, 0] - a_ * pts[:, 1] + ty
    def px2utm(x, y):
        return (a_ * x + b_ * y + tx, b_ * x - a_ * y + ty)
    huella = Polygon([px2utm(0, 0), px2utm(W, 0), px2utm(W, H), px2utm(0, H)])
    # Restar las zonas excluidas (cajas / excluir_x) de la huella.
    cajas = list(cfg.get("excluir_cajas") or [])
    if cfg.get("excluir_x"):
        cajas.append([int(cfg["excluir_x"]), 0, W, H])
    for x0, y0, x1, y1 in cajas:
        huella = huella.difference(Polygon([px2utm(x0, y0), px2utm(x1, y0), px2utm(x1, y1), px2utm(x0, y1)]))
    return np.column_stack([E, N]), huella, im, sol, rmse


def densidad(pts_xy, geom):
    """Marcas por hectárea dentro de geom (prefiltro por bbox)."""
    if geom.is_empty or geom.area == 0:
        return 0.0, 0
    x0, y0, x1, y1 = geom.bounds
    m = (pts_xy[:, 0] >= x0) & (pts_xy[:, 0] <= x1) & (pts_xy[:, 1] >= y0) & (pts_xy[:, 1] <= y1)
    from shapely import contains_xy
    k = int(contains_xy(geom, pts_xy[m, 0], pts_xy[m, 1]).sum()) if m.any() else 0
    return k / (geom.area / 1e4), k


def piezas(g):
    if g.is_empty:
        return []
    return list(g.geoms) if hasattr(g, "geoms") else [g]


def analizar(Gs, Nlist, pts, huellas, etiqueta, umbral_a=0.5, out=print):
    G = unary_union(Gs)
    N = unary_union([g for _, g, _ in Nlist])
    suma_G = sum(g.area for g in Gs)
    out(f"[{etiqueta}] G: {len(Gs)} features, suma {suma_G/1e4:.2f} ha, disuelto {G.area/1e4:.2f} ha "
        f"(solape interno {(suma_G-G.area)/1e4:.2f} ha)")
    out(f"[{etiqueta}] N: {len(Nlist)} polígonos, disuelto {N.area/1e4:.2f} ha; "
        f"suma campo hectareas {sum(h for *_, h in Nlist):.2f} ha")
    inter = G.intersection(N)
    falta = G.difference(N)
    sobra = N.difference(G)
    out(f"[{etiqueta}] G∩N {inter.area/1e4:.2f} ha | cobertura de G {inter.area/G.area:.3f} | "
        f"G-N {falta.area/1e4:.2f} ha | N-G {sobra.area/1e4:.2f} ha | IoU {inter.area/G.union(N).area:.3f}")
    hu = unary_union(huellas)
    fuera = falta.difference(hu)
    out(f"[{etiqueta}] G fuera de la huella útil de ambas láminas: {G.difference(hu).area/1e4:.2f} ha; "
        f"de G-N, fuera de huella: {fuera.area/1e4:.2f} ha")
    d_ref, k_ref = densidad(pts, inter)
    d_fondo, _ = densidad(pts, hu.difference(G.union(N)).intersection(G.union(N).buffer(300)))
    out(f"[{etiqueta}] densidad de marcas AR-2a en G∩N: {d_ref:.0f} /ha ({k_ref} marcas); "
        f"en un anillo de 300 m fuera de G∪N: {d_fondo:.0f} /ha")
    if d_ref < 50:
        raise SystemExit("instrumento muerto: no ve la trama dentro de G∩N")
    ps = [p for p in piezas(falta)]
    grandes = [p for p in ps if p.area >= 2000]
    out(f"[{etiqueta}] G-N en {len(ps)} piezas; >=2000 m2: {len(grandes)} piezas, "
        f"{sum(p.area for p in grandes)/1e4:.2f} ha; <2000 m2: {len(ps)-len(grandes)} piezas, "
        f"{sum(p.area for p in ps if p.area < 2000)/1e4:.2f} ha")
    # Clasificar por densidad relativa a G∩N, y por si es franja de borde.
    clases = {"a_achurado_perdido": 0.0, "b_sin_achurado": 0.0, "intermedia": 0.0, "fuera_huella": 0.0}
    filas = []
    for p in grandes:
        pin = p.intersection(hu)
        if pin.area < 0.5 * p.area:
            clases["fuera_huella"] += p.area
            cl = "fuera_huella"; d = float("nan")
        else:
            d, _ = densidad(pts, pin)
            r = d / d_ref
            cl = "a_achurado_perdido" if r >= umbral_a else ("b_sin_achurado" if r < 0.15 else "intermedia")
            clases[cl] += p.area
        # Ancho medio de la pieza (área / medio perímetro) y distancia a N.
        ancho = 2 * p.area / p.length
        filas.append((p.area, cl, d, ancho, p.distance(N), p.representative_point()))
    filas.sort(key=lambda t: -t[0])
    out(f"[{etiqueta}] piezas >=2000 m2 por causa (ha): " +
        ", ".join(f"{k} {v/1e4:.2f}" for k, v in clases.items()))
    out(f"[{etiqueta}] 12 piezas mayores: área ha | causa | marcas/ha | ancho medio m | dist a N m | punto")
    for a, cl, d, an, dn, pt in filas[:12]:
        out(f"    {a/1e4:6.2f} | {cl:20s} | {d:6.0f} | {an:6.1f} | {dn:6.1f} | {pt.x:.0f},{pt.y:.0f}")
    # Corrimiento: traslación óptima en grilla de 2 m dentro de ±20 m.
    mejor = (0, 0, inter.area / G.union(N).area)
    for dx in range(-20, 21, 2):
        for dy in range(-20, 21, 2):
            Nt = affinity.translate(N, dx, dy)
            iou = G.intersection(Nt).area / G.union(Nt).area
            if iou > mejor[2]:
                mejor = (dx, dy, iou)
    Nt = affinity.translate(N, mejor[0], mejor[1])
    out(f"[{etiqueta}] traslación óptima ({mejor[0]},{mejor[1]}) m -> IoU {mejor[2]:.3f}; "
        f"G-N tras trasladar {G.difference(Nt).area/1e4:.2f} ha")
    for b in (5, 10, 15, 25):
        out(f"[{etiqueta}] G-N después de engordar N {b} m: {G.difference(N.buffer(b)).area/1e4:.2f} ha")
    return clases, filas, d_ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--png", default=None)
    args = ap.parse_args()
    m18 = cargar_modulo18()
    cfgs = {c["id"]: c for c in yaml.safe_load(open(CFG, encoding="utf-8"))["laminas"] if c.get("id") in IDS}
    pts_all, huellas, ims = [], [], {}
    for i in IDS:
        pts, hu, im, sol, rmse = marcas_y_huella(m18, cfgs[i])
        print(f"{i}: {len(pts)} marcas AR-2a en la hoja, huella útil {hu.area/1e4:.0f} ha, RMSE {rmse:.2f} m")
        pts_all.append(pts); huellas.append(hu); ims[i] = (im, sol)
    pts = np.vstack(pts_all)
    Gs = cargar_G("AR-2a")
    Nlist = cargar_N()
    clases, filas, d_ref = analizar(Gs, Nlist, pts, huellas, "real")

    G2b = unary_union(cargar_G("AR-2b"))
    d2b, k2b = densidad(pts, G2b)
    N = unary_union([g for _, g, _ in Nlist])
    print(f"[AR-2b] {G2b.area/1e4:.2f} ha; dentro de huella {G2b.intersection(unary_union(huellas)).area/1e4:.2f} ha; "
          f"cubierto por N {G2b.intersection(N).area/G2b.area:.3f}; marcas AR-2a/ha dentro: {d2b:.0f} ({k2b})")

    if args.png:
        dibujar(ims, filas, Gs, N, Path(args.png))

    if args.control:
        print("== CONTROL ==")
        # (1) borrar el polígono N más grande: debe aparecer como (a).
        idx = max(range(len(Nlist)), key=lambda k: Nlist[k][1].area)
        borrado = Nlist[idx][1]
        N_mal = [x for k, x in enumerate(Nlist) if k != idx]
        # (2) inyectar en G un cuadrado de 2 ha en la huella, a >300 m de G∪N.
        hu = unary_union(huellas)
        lejos = hu.difference(unary_union(Gs).union(N).buffer(400)).buffer(-80)
        c = lejos.representative_point()
        falso = box(c.x - 70, c.y - 70, c.x + 70, c.y + 70)
        cl, fl, _ = analizar(Gs + [falso], N_mal, pts, huellas, "control")
        ok1 = any(abs(a - borrado.intersection(unary_union(Gs)).area) < 0.3 * borrado.area and c_ == "a_achurado_perdido"
                  for a, c_, *_ in fl) or cl["a_achurado_perdido"] - clases["a_achurado_perdido"] > 0.5 * borrado.intersection(unary_union(Gs)).area
        # La pieza inyectada se busca por posición: el total por clase no sirve
        # porque d_ref cambia al borrar N y otras piezas cruzan el umbral.
        ok2 = any(c_ == "b_sin_achurado" and abs(a - falso.area) < 0.1 * falso.area
                  and pt.distance(falso) < 1 for a, c_, d, an, dn, pt in fl)
        print(f"CONTROL borrado {borrado.area/1e4:.2f} ha -> clasificado (a): {'OK' if ok1 else 'FALLA'}")
        print(f"CONTROL falso {falso.area/1e4:.2f} ha en {c.x:.0f},{c.y:.0f} -> clasificado (b): {'OK' if ok2 else 'FALLA'}")
        if not (ok1 and ok2):
            sys.exit(1)


def dibujar(ims, filas, Gs, N, carpeta):
    """Recortes de la lámina en las 6 piezas mayores: G en rojo, N en azul."""
    from PIL import ImageDraw
    carpeta.mkdir(parents=True, exist_ok=True)
    G = unary_union(Gs)
    for k, (a, cl, d, an, dn, pt) in enumerate(filas[:6]):
        for lid, (im, sol) in ims.items():
            a_, b_, tx, ty = sol
            M = np.array([[a_, b_], [b_, -a_]])
            Mi = np.linalg.inv(M)
            x, y = Mi @ np.array([pt.x - tx, pt.y - ty])
            if not (0 <= x < im.width and 0 <= y < im.height):
                continue
            r = 450
            x0, y0 = int(max(0, x - r)), int(max(0, y - r))
            crop = im.crop((x0, y0, int(min(im.width, x + r)), int(min(im.height, y + r)))).convert("RGB")
            dr = ImageDraw.Draw(crop)
            def a_px(geom, color):
                for p in piezas(geom):
                    if p.geom_type != "Polygon":
                        continue
                    for ring in [p.exterior] + list(p.interiors):
                        xy = [tuple(Mi @ np.array([e - tx, n - ty]) - np.array([x0, y0])) for e, n in ring.coords]
                        dr.line(xy, fill=color, width=3)
            ventana = box(pt.x - 500, pt.y - 500, pt.x + 500, pt.y + 500)
            a_px(G.intersection(ventana), (255, 0, 0))
            a_px(N.intersection(ventana), (0, 0, 255))
            crop.save(carpeta / f"pieza{k+1}_{lid}_{a/1e4:.1f}ha_{cl}.png")


if __name__ == "__main__":
    main()
