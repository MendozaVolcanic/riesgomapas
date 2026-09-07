#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lamina_sintetica.py — control positivo y negativo del vectorizador de láminas.

POR QUÉ. Ningún IoU medido sobre una lámina real cuenta si no sabemos que el
pipeline recupera una geometría CONOCIDA en la posición CONOCIDA. Esta prueba
fabrica una lámina con clases y coordenadas fijadas de antemano, la mete en un
PDF, y la pasa por `procesar()` de `scripts/18_vectorizar_laminas.py` —el código
real, importado como módulo, con `DATA_RAW` y `SALIDA` redirigidos a
`tools/auditoria/salida_sintetica/` para no tocar `config/` ni `data/`—.

LAS DOS PREGUNTAS DEL INSTRUMENTO
  1. Si el vectorizador estuviera roto (afín invertida, clases confundidas,
     apertura que se come todo), el IoU contra la geometría conocida sería < 0,9
     o el desplazamiento > 1 px: la prueba FALLA.
  2. Si el instrumento estuviera muerto (el PDF no se lee, `procesar` devuelve
     None), el resultado es «SIN POLÍGONOS» en el control positivo, que se
     imprime distinto de un OK. El control negativo exige además 0 polígonos
     sobre una lámina sin clases: un instrumento que da 0 siempre reprueba el
     positivo.

QUÉ FABRICA (escala 5 m/px, EPSG:32718, grilla x en px 200→E 700000 y
px 1000→E 704000, y en px 150→N 5815000):
  · «Alto»  — rectángulo E 700500..701500 × N 5813000..5814000 con un hueco
              interior de 200 m de lado (prueba anillos interiores).
  · «Alto»  — franja LEGÍTIMA pero delgada (3 px = 15 m de ancho, 400 m de
              largo) pegada al rectángulo: mide cuánto se come la apertura.
  · «Alto»  — línea de RÍO de 2 px que cruza la hoja en diagonal, mismo color:
              debe desaparecer (control del río↔«Alto»).
  · «Medio» — círculo de radio 300 m centrado en E 702500 N 5812500.
  · Caja de leyenda con los dos colores (como en las láminas reales) en la
    franja inferior derecha, para ver si se vectoriza la leyenda.
  · Fondo blanco, retícula gris, marco negro, texto negro.

CONTROLES
  positivo   — la lámina de arriba → IoU por clase contra la geometría conocida,
               desplazamiento del centroide, conteo de polígonos, ¿sobrevivió la
               franja de 3 px?, ¿desapareció el río?, ¿se vectorizó la leyenda?
  positivo_jpeg — la misma lámina pasada por JPEG calidad 80 (las figuras de
               los PDF suelen venir comprimidas): mide la robustez de la
               tolerancia de color.
  negativo   — la misma hoja SIN ninguna clase (sólo retícula, río y leyenda
               vacía) → se exige 0 polígonos / `procesar` devuelve None.
  guardian   — la lámina positiva con un rótulo de grilla que la manda fuera de
               la región (E 900000) → se exige SystemExit.

Uso:  python tools/auditoria/lamina_sintetica.py
Salida: tools/auditoria/salida_sintetica/{*.pdf,*.png,*.geojson} y el veredicto por
stdout. Código de salida 0 si todos los controles pasan, 1 si alguno falla.
"""
from __future__ import annotations

import importlib.util
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = Path(__file__).resolve().parent / "salida_sintetica"
SALIDA.mkdir(exist_ok=True)

sys.path.insert(0, str(RAIZ / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "vectorizar", RAIZ / "scripts" / "18_vectorizar_laminas.py")
vec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vec)
# Redirección: el script real lee DATA_RAW / cfg["pdf"] y escribe en SALIDA.
vec.DATA_RAW = SALIDA
vec.SALIDA = SALIDA

from comun import cargar_config  # noqa: E402

# ------------------------------------------------------------- la lámina

M_PX = 5.0
W, H = 1200, 900
X0_PX, X0_E = 200, 700000.0
X1_PX, X1_E = 1000, 704000.0
Y0_PX, Y0_N = 150, 5815000.0
ALTO = (4, 78, 163)
MEDIO = (0, 114, 255)
GRIS = (150, 150, 150)


def px(e: float, n: float) -> tuple[float, float]:
    return X0_PX + (e - X0_E) / M_PX, Y0_PX + (Y0_N - n) / M_PX


def geometria_conocida():
    """Las figuras, en metros UTM, como shapely (la verdad de la prueba)."""
    from shapely.geometry import Point, Polygon, box
    rect = box(700500, 5813000, 701500, 5814000)
    hueco = box(700900, 5813400, 701100, 5813600)
    alto = rect.difference(hueco)
    franja = box(701500, 5813500, 701900, 5813515)       # 400 m × 15 m (3 px)
    medio = Point(702500, 5812500).buffer(300, 64)
    return {"Alto": alto, "Alto_franja": franja, "Medio": medio}


def dibujar(con_clases: bool = True) -> Image.Image:
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    # retícula gris continua (como la detecta lineas_de_grilla) y marco negro
    for x in (X0_PX, 600, X1_PX):
        d.line([(x, 0), (x, H)], fill=GRIS, width=1)
    for y in (Y0_PX, 450, 750):
        d.line([(0, y), (W, y)], fill=GRIS, width=1)
    d.rectangle([2, 2, W - 3, H - 3], outline=(0, 0, 0), width=2)
    d.text((X0_PX + 4, 6), "700000", fill=(0, 0, 0))
    d.text((X1_PX + 4, 6), "704000", fill=(0, 0, 0))
    d.text((6, Y0_PX + 4), "5815000", fill=(0, 0, 0))
    if con_clases:
        g = geometria_conocida()
        # rectángulo con hueco: se dibuja el exterior y se «borra» el hueco
        ext = [px(*c) for c in g["Alto"].exterior.coords]
        d.polygon(ext, fill=ALTO)
        for interior in g["Alto"].interiors:
            d.polygon([px(*c) for c in interior.coords], fill=(255, 255, 255))
        d.polygon([px(*c) for c in g["Alto_franja"].exterior.coords], fill=ALTO)
        d.polygon([px(*c) for c in g["Medio"].exterior.coords], fill=MEDIO)
        # caja de leyenda, abajo a la derecha, con muestras de los dos colores
        d.rectangle([900, 780, 1180, 880], fill=(255, 255, 255), outline=(0, 0, 0))
        d.rectangle([915, 795, 945, 815], fill=ALTO)
        d.text((955, 798), "Alto", fill=(0, 0, 0))
        d.rectangle([915, 835, 945, 855], fill=MEDIO)
        d.text((955, 838), "Medio", fill=(0, 0, 0))
    # río: línea de 2 px del MISMO azul que «Alto», cruzando la hoja
    d.line([(150, 850), (1100, 100)], fill=ALTO, width=2)
    return im


def a_pdf(im: Image.Image, destino: Path, jpeg: int | None = None) -> None:
    """PDF con la imagen incrustada (sin pérdida, o JPEG de la calidad pedida)."""
    import fitz
    buf = io.BytesIO()
    if jpeg:
        im.save(buf, "JPEG", quality=jpeg)
    else:
        im.save(buf, "PNG")
    doc = fitz.open()
    page = doc.new_page(width=im.width, height=im.height)
    page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(str(destino))
    doc.close()


def cfg_base(id_: str, pdf: str) -> dict:
    return {
        "id": id_, "comuna": "ANGOL", "pdf": pdf, "pagina": 1, "imagen": 0,
        "titulo": "lámina sintética de control", "fuente": "sintética (auditoría)",
        "url": "", "anio_estudio": 2026, "metodo_original": "ninguno: figura fabricada",
        "escala_impresa": "1:sintética", "epsg": 32718,
        "grilla": {"x": [[X0_PX, X0_E], [X1_PX, X1_E]], "y": [[Y0_PX, Y0_N]]},
        "clases": [{"nombre": "Alto", "rgb": list(ALTO)},
                   {"nombre": "Medio", "rgb": list(MEDIO)}],
        "tolerancia_color": 45, "ancho_minimo_px": 4, "area_minima_m2": 2000,
    }


# ---------------------------------------------------------------- medición

def medir(geojson: Path, conocida: dict) -> dict:
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform as sh_transform, unary_union
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32718", always_xy=True)
    d = json.loads(geojson.read_text(encoding="utf-8"))
    por_clase: dict[str, list] = {}
    for f in d["features"]:
        g = sh_transform(tr.transform, shape(f["geometry"]))
        por_clase.setdefault(f["properties"]["clase"], []).append(g)
    out = {"n_poligonos": {k: len(v) for k, v in por_clase.items()}}
    # La caja de leyenda de la hoja (900..1180 × 780..880 px) en metros: lo que
    # caiga ahí no es territorio. Se mide aparte y se excluye del IoU.
    from shapely.geometry import box
    e0, n0 = X0_E + (900 - X0_PX) * M_PX, Y0_N - (880 - Y0_PX) * M_PX
    e1, n1 = X0_E + (1180 - X0_PX) * M_PX, Y0_N - (780 - Y0_PX) * M_PX
    caja = box(e0, n0, e1, n1)
    out["n_poligonos_en_leyenda"] = {
        k: sum(1 for g in v if g.intersects(caja)) for k, v in por_clase.items()}
    verdad_alto = unary_union([conocida["Alto"], conocida["Alto_franja"]])
    for clase, verdad in (("Alto", conocida["Alto"]), ("Medio", conocida["Medio"])):
        rec = unary_union([g for g in por_clase.get(clase, []) if not g.intersects(caja)])
        inter = rec.intersection(verdad).area
        union = rec.union(verdad).area
        out[f"iou_{clase}"] = round(inter / union, 4) if union else 0.0
        out[f"iou_{clase}_con_franja"] = (
            round(rec.intersection(verdad_alto).area / rec.union(verdad_alto).area, 4)
            if clase == "Alto" and not rec.is_empty else None)
        if not rec.is_empty:
            cx, cy = rec.centroid.x, rec.centroid.y
            vx, vy = verdad.centroid.x, verdad.centroid.y
            out[f"desplazamiento_{clase}_m"] = round(math.hypot(cx - vx, cy - vy), 2)
            out[f"area_{clase}_ha"] = round(rec.area / 1e4, 2)
            out[f"area_verdad_{clase}_ha"] = round(verdad.area / 1e4, 2)
            out[f"hausdorff_{clase}_m"] = round(rec.hausdorff_distance(verdad), 1)
    # ¿sobrevivió la franja de 3 px? (área recuperada dentro de la franja)
    rec_alto = unary_union(por_clase.get("Alto", []))
    fr = conocida["Alto_franja"]
    out["franja_15m_recuperada_pct"] = round(
        100 * rec_alto.intersection(fr).area / fr.area, 1) if not rec_alto.is_empty else 0.0
    # ¿se vectorizó la leyenda? (algo de «Alto»/«Medio» en la caja 900..1180 × 780..880)
    todo = unary_union([g for v in por_clase.values() for g in v])
    out["leyenda_vectorizada_m2"] = round(todo.intersection(caja).area, 0) if not todo.is_empty else 0
    # ¿algo del río fuera de las figuras conocidas? (área recuperada lejos de la verdad)
    lejos = todo.difference(unary_union([conocida["Alto"], conocida["Alto_franja"],
                                         conocida["Medio"]]).buffer(2 * M_PX))
    out["falso_positivo_fuera_de_verdad_m2"] = round(lejos.area - todo.intersection(caja).area, 0)
    out["anillos_interiores_Alto"] = sum(len(g.interiors) for g in por_clase.get("Alto", []))
    return out


def correr(nombre: str, im: Image.Image, jpeg: int | None, region: dict,
           grilla_x=None) -> dict | None:
    pdf = SALIDA / f"{nombre}.pdf"
    im.save(SALIDA / f"{nombre}.png")
    a_pdf(im, pdf, jpeg)
    cfg = cfg_base(f"sintetica-{nombre}", pdf.name)
    if grilla_x:
        cfg["grilla"]["x"] = grilla_x
    print(f"\n=== {nombre} ===")
    return vec.procesar(cfg, region)


def main() -> int:
    region = cargar_config()["region"]
    conocida = geometria_conocida()
    fallas = []
    veredictos = {}

    # --- control positivo, sin pérdida
    r = correr("positivo", dibujar(True), None, region)
    if r is None:
        fallas.append("positivo: procesar() devolvió None — SIN POLÍGONOS")
    else:
        m = medir(SALIDA / "sintetica-positivo.geojson", conocida)
        veredictos["positivo"] = m
        print(json.dumps(m, ensure_ascii=False, indent=1))
        if m["iou_Alto"] < 0.9 or m["iou_Medio"] < 0.9:
            fallas.append(f"positivo: IoU bajo (Alto {m['iou_Alto']}, Medio {m['iou_Medio']})")
        # El desplazamiento se juzga sobre «Medio» (círculo sin franja pegada) y
        # sobre la distancia de Hausdorff de «Alto» sin la franja: la franja de
        # 3 px mueve el centroide de la unión sin mover el rectángulo.
        # Tolerancia: 1,5 px de centroide y 3 px de Hausdorff. Dibujar un círculo
        # en una retícula de píxeles y simplificarlo a medio píxel ya cuesta ~1 px.
        if m["desplazamiento_Medio_m"] > 1.5 * M_PX or m["hausdorff_Medio_m"] > 3 * M_PX:
            fallas.append(f"positivo: «Medio» desplazado {m['desplazamiento_Medio_m']} m "
                          f"/ Hausdorff {m['hausdorff_Medio_m']} m (> 1 px / 3 px)")
        if m["iou_Alto_con_franja"] < 0.9:
            fallas.append("positivo: «Alto» con franja IoU < 0,9")
        if m["falso_positivo_fuera_de_verdad_m2"] > 2000:
            fallas.append(f"positivo: {m['falso_positivo_fuera_de_verdad_m2']} m² fuera de la verdad (¿río?)")
        if m["anillos_interiores_Alto"] < 1:
            fallas.append("positivo: el hueco interior no se recuperó")

    # --- control positivo con JPEG
    r = correr("positivo_jpeg80", dibujar(True), 80, region)
    if r is None:
        fallas.append("positivo_jpeg80: SIN POLÍGONOS")
    else:
        m = medir(SALIDA / "sintetica-positivo_jpeg80.geojson", conocida)
        veredictos["positivo_jpeg80"] = m
        print(json.dumps(m, ensure_ascii=False, indent=1))
        if m["iou_Alto"] < 0.9 or m["iou_Medio"] < 0.9:
            fallas.append(f"positivo_jpeg80: IoU bajo (Alto {m['iou_Alto']}, Medio {m['iou_Medio']})")

    # --- control negativo: sin clases (queda retícula + río + marco)
    r = correr("negativo", dibujar(False), None, region)
    if r is not None:
        n = sum(c["poligonos"] for c in r["resumen"])
        veredictos["negativo"] = r["resumen"]
        fallas.append(f"negativo: se obtuvieron {n} polígonos de una lámina sin clases")
    else:
        veredictos["negativo"] = "0 polígonos (procesar devolvió None)"
        print("negativo: 0 polígonos — OK")

    # --- guardián de región: rótulo que manda la lámina a E 900000 (fuera)
    try:
        correr("guardian", dibujar(True), None, region,
               grilla_x=[[X0_PX, 900000.0], [X1_PX, 904000.0]])
        fallas.append("guardian: NO se cayó con la lámina fuera de la región")
        veredictos["guardian"] = "no se cayó"
    except SystemExit as e:
        veredictos["guardian"] = f"SystemExit OK: {str(e)[:120]}"
        print(f"guardian: SystemExit — OK ({str(e)[:100]}…)")

    (SALIDA / "veredictos.json").write_text(
        json.dumps(veredictos, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== VEREDICTO ===")
    if fallas:
        for f in fallas:
            print("FALLA:", f)
        return 1
    print("todos los controles pasan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
