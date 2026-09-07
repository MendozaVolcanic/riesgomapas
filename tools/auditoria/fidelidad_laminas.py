#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fidelidad_laminas.py — ¿los polígonos publicados reproducen lo que la lámina muestra?

POR QUÉ. Los GeoJSON de `data/processed/laminas/` se produjeron una vez y nadie los
volvió a poner sobre su lámina. Esta prueba re-renderiza cada polígono publicado sobre
la imagen de origen (la misma que extrae el script 18) y mide, POR CLASE:

  · IoU publicado ↔ máscara de color cruda (todo píxel a menos de `tolerancia_color`
    del color de leyenda, ANTES de la apertura morfológica): cuánto de lo que la
    lámina pinta con ese color quedó publicado.
  · IoU publicado ↔ máscara limpia (después de la apertura): valida que esta réplica
    reproduce el pipeline (debe ser ≈1; si no, la réplica no vale y todo lo demás
    tampoco).
  · IoU publicado ↔ clasificador INDEPENDIENTE (k-means sobre los colores de la
    imagen, k=10, asignando al centro más cercano a cada color de leyenda): un
    segundo instrumento que no comparte la tolerancia RGB.
  · Qué se comió la apertura: los píxeles crudos que no sobrevivieron se separan en
    (a) FRANJA — componentes pegadas a un polígono publicado (borde legítimo delgado)
    y (b) LÍNEA — componentes aisladas y alargadas (red hídrica u otro trazo). Es la
    confusión río↔«Alto» cuantificada en hectáreas.
  · Polígonos publicados en la zona de LEYENDA de la hoja (franja inferior), con su
    tamaño en hectáreas.
  · Para el plano AR-2a (clasificado por trama, no por color): fracción de las marcas
    de achurado detectadas que caen dentro de los polígonos publicados (recall de
    marcas) y densidad de marcas fuera de ellos.

Deja en tools/auditoria/evidencia_laminas/ los PNG de superposición (contorno
publicado sobre la lámina) para la cola de validación en campo.

LAS DOS PREGUNTAS DEL INSTRUMENTO
  1. Si los polígonos estuvieran corridos o fueran de otra clase, el IoU contra la
     máscara de color caería (control: desplazar el GeoJSON 5 px y ver que cae).
  2. Si el instrumento estuviera muerto (rasterización vacía), el IoU sería 0 con
     máscara no vacía; se imprime el número de píxeles de cada máscara para verlo.

Uso:  python tools/auditoria/fidelidad_laminas.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[2]
EVID = Path(__file__).resolve().parent / "evidencia_laminas"
EVID.mkdir(exist_ok=True)
sys.path.insert(0, str(RAIZ / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "vectorizar", RAIZ / "scripts" / "18_vectorizar_laminas.py")
vec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vec)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    u = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / u) if u else 0.0


def rasterizar(geoms, transform, shape_hw):
    from rasterio.features import rasterize
    if not geoms:
        return np.zeros(shape_hw, bool)
    return rasterize([(g, 1) for g in geoms], out_shape=shape_hw,
                     transform=transform, fill=0, dtype="uint8").astype(bool)


def publicados(lid: str, epsg: int):
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform as sh_transform
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    d = json.loads((RAIZ / "data/processed/laminas" / f"{lid}.geojson").read_text(encoding="utf-8"))
    out = {}
    for f in d["features"]:
        out.setdefault(f["properties"]["clase"], []).append(
            (sh_transform(tr.transform, shape(f["geometry"])), f["properties"]))
    return out


def kmeans_mask(a: np.ndarray, rgb_clases: list, k: int = 10):
    """Clasificador independiente: k-means sobre una muestra, luego asignación."""
    h, w, _ = a.shape
    flat = a.reshape(-1, 3).astype(np.float32)
    rng = np.random.default_rng(7)
    muestra = flat[rng.choice(len(flat), min(200_000, len(flat)), replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, _, centros = cv2.kmeans(muestra, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    # etiqueta de cada píxel: centro más cercano
    d = ((flat[:, None, :] - centros[None, :, :]) ** 2).sum(2)
    lab = d.argmin(1).reshape(h, w)
    masks = []
    for rgb in rgb_clases:
        dc = ((centros - np.array(rgb, np.float32)) ** 2).sum(1)
        j = int(dc.argmin())
        masks.append((lab == j, float(np.sqrt(dc[j])), centros[j].round(0).tolist()))
    return masks


def analizar_color(cfg: dict) -> dict:
    from affine import Affine
    lid = cfg["id"]
    ims = vec.imagenes_de(vec.DATA_RAW / cfg["pdf"], cfg["pagina"])
    im = ims[cfg.get("imagen", 0)]
    a = np.array(im).astype(int)
    h, w, _ = a.shape
    s, x_ref, e_ref, y_ref, n_ref, _ = vec.afin(cfg)
    T = Affine(s, 0, e_ref - x_ref * s, 0, -s, n_ref + y_ref * s)
    tol = cfg.get("tolerancia_color", 45)
    ancho = int(cfg.get("ancho_minimo_px", 4))
    pub = publicados(lid, cfg["epsg"])
    dists = [np.linalg.norm(a - np.array(c["rgb"]), axis=2) for c in cfg["clases"]]
    apilado = np.stack(dists)
    ganador, dmin = apilado.argmin(0), apilado.min(0)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ancho, ancho))
    km = kmeans_mask(a, [c["rgb"] for c in cfg["clases"]])

    res = {"lamina": lid, "imagen_px": [w, h], "m_por_px": round(s, 3), "clases": {}}
    overlay = im.copy()
    dr = ImageDraw.Draw(overlay)
    colores = [(255, 0, 0), (255, 140, 0), (0, 200, 0)]
    for i, clase in enumerate(cfg["clases"]):
        nombre = clase["nombre"]
        cruda = (ganador == i) & (dmin < tol)
        limpia = cv2.morphologyEx(cruda.astype("uint8"), cv2.MORPH_OPEN, k).astype(bool)
        geoms = [g for g, _ in pub.get(nombre, [])]
        rast = rasterizar(geoms, T, (h, w))
        # control 1: el mismo GeoJSON corrido 5 px debe bajar el IoU
        Tc = Affine(s, 0, e_ref - (x_ref + 5) * s, 0, -s, n_ref + y_ref * s)
        rast_corrido = rasterizar(geoms, Tc, (h, w))
        # lo que se comió la apertura: franja (toca lo publicado) vs línea (aislada)
        comido = cruda & ~limpia
        n_lab, lab, st, _ = cv2.connectedComponentsWithStats(comido.astype("uint8"), 8)
        dil = cv2.dilate(rast.astype("uint8"), np.ones((3, 3), "uint8")).astype(bool)
        franja_px = linea_px = 0
        comp_linea = []
        for j in range(1, n_lab):
            comp = lab == j
            area = int(st[j, cv2.CC_STAT_AREA])
            if np.logical_and(comp, dil).any():
                franja_px += area
            else:
                linea_px += area
                bw, bh = int(st[j, cv2.CC_STAT_WIDTH]), int(st[j, cv2.CC_STAT_HEIGHT])
                comp_linea.append((area, max(bw, bh)))
        # leyenda: polígonos publicados cuyo centroide cae en la franja inferior (y > 0,75·h)
        leyenda = []
        for g, p in pub.get(nombre, []):
            cx, cy = g.centroid.x, g.centroid.y
            px_, py_ = x_ref + (cx - e_ref) / s, y_ref + (n_ref - cy) / s
            if py_ > 0.75 * h:
                leyenda.append({"px": [round(px_), round(py_)], "ha": p["hectareas"]})
        kmask, kdist, kcentro = km[i]
        res["clases"][nombre] = {
            "poligonos_publicados": len(geoms),
            "px_publicados": int(rast.sum()), "px_cruda": int(cruda.sum()),
            "px_limpia": int(limpia.sum()),
            "iou_publicado_vs_limpia (réplica del pipeline, debe ser ~1)": round(iou(rast, limpia), 4),
            "iou_publicado_vs_cruda (fidelidad al color de la lámina)": round(iou(rast, cruda), 4),
            "iou_publicado_vs_kmeans (clasificador independiente)": round(iou(rast, kmask), 4),
            "kmeans_centro_rgb": kcentro, "kmeans_dist_al_color_leyenda": round(kdist, 1),
            "control_corrido_5px_iou_vs_cruda": round(iou(rast_corrido, cruda), 4),
            "comido_por_apertura_ha": round((cruda.sum() - limpia.sum()) * s * s / 1e4, 2),
            "  de eso, FRANJA pegada a lo publicado_ha": round(franja_px * s * s / 1e4, 2),
            "  de eso, LÍNEA aislada (río u otro trazo)_ha": round(linea_px * s * s / 1e4, 2),
            "  componentes de línea (n, la más larga en px)": [len(comp_linea), max((l for _, l in comp_linea), default=0)],
            "publicados_en_zona_de_leyenda": leyenda,
        }
        # contorno de lo publicado sobre la lámina
        cont, _ = cv2.findContours(rast.astype("uint8"), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in cont:
            pts = [tuple(p[0]) for p in c]
            if len(pts) > 2:
                dr.line(pts + [pts[0]], fill=colores[i % 3], width=2)
    overlay.save(EVID / f"{lid}_publicado_sobre_lamina.png")
    # recorte de la zona de leyenda con contornos
    overlay.crop((0, int(0.75 * h), w, h)).save(EVID / f"{lid}_zona_leyenda.png")
    return res


def analizar_trama(cfg: dict) -> dict:
    """AR-2a: recall de marcas de achurado dentro de lo publicado."""
    from affine import Affine
    from shapely.geometry import Point
    from shapely.prepared import prep
    from shapely.ops import unary_union
    lid = cfg["id"]
    ims = vec.imagenes_de(vec.DATA_RAW / cfg["pdf"], cfg["pagina"])
    im = ims[cfg.get("imagen", 0)]
    if cfg.get("rotar"):
        im = im.rotate(cfg["rotar"], expand=True)
    a = np.array(im).astype(int)
    h, w, _ = a.shape
    sol, s, rot, rmse, resid = vec.afin_por_vertices(cfg)
    a_, b_, tx, ty = sol
    clase = cfg["clases"][0]
    # réplica de la detección de marcas (mismos umbrales que el script)
    g = cv2.cvtColor(a.astype("uint8"), cv2.COLOR_RGB2GRAY)
    fondo = cv2.medianBlur(g, 21)
    osc = ((fondo.astype("int16") - g.astype("int16")) > clase.get("contraste_minimo", 28)).astype("uint8")
    n, lab, st, cent = cv2.connectedComponentsWithStats(osc, 8)
    amin, amax = clase.get("marca_area", [8, 45])
    lmin, lmax = clase.get("marca_lado", [4, 11])
    ar, an, al = st[1:, cv2.CC_STAT_AREA], st[1:, cv2.CC_STAT_WIDTH], st[1:, cv2.CC_STAT_HEIGHT]
    sel = ((ar >= amin) & (ar <= amax) & (an >= lmin) & (an <= lmax) & (al >= lmin) & (al <= lmax))
    marcas = cent[1:][sel]
    ex = cfg.get("excluir_x")
    if ex:
        marcas = marcas[marcas[:, 0] < ex]
    pub = publicados(lid, cfg["epsg"])
    geoms = [gg for gg, _ in pub.get(clase["nombre"], [])]
    union = prep(unary_union(geoms))
    dentro = 0
    for x, y in marcas:
        E = a_ * x + b_ * y + tx
        N = b_ * x - a_ * y + ty
        if union.contains(Point(E, N)):
            dentro += 1
    total = len(marcas)
    area_pub = sum(gg.area for gg in geoms)
    # densidad de marcas fuera: marcas/ha fuera vs dentro
    area_hoja = (ex or w) * h * s * s
    res = {"lamina": lid, "rmse_m_recalculado": round(rmse, 2), "residuos_m": [(n_, round(d, 2)) for n_, d in resid],
           "m_por_px": round(s, 4), "rotacion_deg": round(rot, 3),
           "marcas_del_tamaño_buscado": int(total), "marcas_dentro_de_lo_publicado": int(dentro),
           "recall_marcas_pct": round(100 * dentro / total, 1) if total else None,
           "densidad_dentro_marcas_por_ha": round(dentro / (area_pub / 1e4), 1) if area_pub else None,
           "densidad_fuera_marcas_por_ha": round((total - dentro) / ((area_hoja - area_pub) / 1e4), 2),
           "grados_de_libertad_del_ajuste": 2 * len(cfg["vertices"]) - 4}
    # overlay a escala reducida (el pliego es enorme)
    esc = 0.25
    small = im.resize((int(w * esc), int(h * esc)))
    dr = ImageDraw.Draw(small)
    for gg in geoms:
        # UTM → px inversa de la semejanza
        det = a_ * a_ + b_ * b_
        pts = []
        for E, N in gg.exterior.coords:
            dx, dy = E - tx, N - ty
            x = (a_ * dx + b_ * dy) / det
            y = (b_ * dx - a_ * dy) / det
            pts.append((x * esc, y * esc))
        dr.line(pts + [pts[0]], fill=(255, 0, 0), width=2)
    for x, y in marcas[::10]:
        dr.point((x * esc, y * esc), fill=(0, 200, 0))
    small.save(EVID / f"{lid}_publicado_sobre_plano_x025.png")
    return res


def main():
    cfgs = yaml.safe_load((RAIZ / "config/laminas.yaml").read_text(encoding="utf-8"))["laminas"]
    out = []
    for cfg in cfgs:
        r = analizar_trama(cfg) if cfg.get("vertices") else analizar_color(cfg)
        out.append(r)
        print(json.dumps(r, ensure_ascii=False, indent=1))
    (EVID / "fidelidad.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
