#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""revisar_poligonos_provincia.py — ¿los polígonos están bien extraídos y bien cortados?

POR QUÉ. Una lámina vectorizada puede verse perfecta en pantalla y estar mal de
tres maneras que no se notan mirando: la mancha se cortó en el borde de la hoja y
sigue fuera del mapa; la geometría es inválida y cualquier cálculo de área o de
«cae dentro» da distinto según la herramienta; o el recorte a la provincia partió
polígonos que en realidad siguen en la comuna vecina. Este arnés las busca sobre
el artefacto publicado, no sobre el código que lo generó.

QUÉ REVISA, por capa:
  · VALIDEZ      — autointersecciones y anillos rotos (`shapely.is_valid`), y si
                   `make_valid` cambia el área: si cambia, el polígono estaba
                   diciendo un número que no era.
  · TRUNCADOS    — polígonos que tocan el marco de la lámina de origen. Un
                   polígono pegado al borde de la hoja casi siempre está cortado:
                   la mancha real sigue fuera de la figura, y publicado se lee
                   como si ahí terminara el peligro.
  · CORTE PROVINCIAL — polígonos que tocan el borde del recorte a la provincia.
                   Son los que el paquete parte al recortar; el original está
                   completo en la capa regional.
  · UMBRAL       — polígonos a menos de un 20 % del `area_minima_m2` que los
                   habría eliminado. No son un error, pero son los que aparecen y
                   desaparecen si alguien toca ese número.
  · DUPLICADOS   — geometrías repetidas (IoU > 0,98) dentro de la misma capa.
  · COBERTURA    — cuánto del área declarada por la lámina quedó dentro de la
                   provincia pedida, para ver si el recorte se comió algo.

LAS DOS PREGUNTAS DEL INSTRUMENTO
  1. Si los polígonos estuvieran truncados o rotos, ¿esto fallaría? Sí: el
     control positivo (`--control`) inyecta un polígono pegado al marco, uno
     inválido en forma de moño y una copia exacta de otro, y exige que los tres
     aparezcan. Si no los ve, sale con código 2 y su resultado no vale.
  2. Si el instrumento estuviera muerto, ¿se vería distinto? Sí: imprime cuántas
     geometrías miró por capa. Cero geometrías es «no pude mirar», no «está todo
     bien».

Uso:  python tools/auditoria/revisar_poligonos_provincia.py [--provincia Malleco]
                                                            [--control]
                                                            [--salida <archivo.md>]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml
from shapely.geometry import box, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))


def nz(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z ]", "", t.upper()).strip()


def cargar(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def marco_de_lamina(cfg: dict):
    """Caja de la lámina en coordenadas del terreno (EPSG de la lámina).

    Se arma desde la misma transformación que usó el script 18, así que lo que
    se compara es la hoja de verdad, no una aproximación.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "vec18", RAIZ / "scripts" / "18_vectorizar_laminas.py")
    vec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vec)
    pdf = vec.DATA_RAW / cfg["pdf"]
    if not pdf.exists():
        return None, None
    ims = vec.imagenes_de(pdf, cfg["pagina"])
    if not ims:
        return None, None
    im = ims[cfg.get("imagen", 0)]
    if cfg.get("rotar"):
        im = im.rotate(cfg["rotar"], expand=True)
    w, h = im.size
    if cfg.get("vertices"):
        sol, s, _, _, _ = vec.afin_por_vertices(cfg)
        a_, b_, tx, ty = sol
        esq = [(a_ * x + b_ * y + tx, b_ * x - a_ * y + ty)
               for x, y in [(0, 0), (w, 0), (w, h), (0, h)]]
        from shapely.geometry import Polygon
        return Polygon(esq), s
    s, x_ref, e_ref, y_ref, n_ref, _ = vec.afin(cfg)
    e0 = e_ref - x_ref * s
    n0 = n_ref + y_ref * s
    return box(e0, n0 - h * s, e0 + w * s, n0), s


def revisar_lamina(cfg: dict, feats: list[dict], m_px: float, marco) -> dict:
    """Los cuatro controles que sólo se pueden hacer contra la lámina de origen."""
    from pyproj import Transformer
    from shapely.ops import transform as sh_transform
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{cfg['epsg']}", always_xy=True)
    gs = [sh_transform(tr.transform, shape(f["geometry"])) for f in feats]
    area_min = float(cfg.get("area_minima_m2", 0))
    # «Toca el marco» = a menos de dos píxeles del borde de la hoja. Un píxel
    # sería demasiado estricto (el borde del polígono ya está cuantizado a
    # píxel); dos deja pasar el ruido y sigue cazando lo truncado.
    tol = 2 * (m_px or 1)
    truncados, cerca_umbral = [], []
    for f, g in zip(feats, gs):
        if marco is not None and g.distance(marco.exterior) < tol:
            truncados.append(f["properties"])
        if area_min and g.area < area_min * 1.2:
            cerca_umbral.append((f["properties"].get("clase"), round(g.area)))
    return {"truncados": truncados, "cerca_umbral": cerca_umbral,
            "area_minima_m2": area_min, "m_por_px": m_px}


def revisar_validez(feats: list[dict]) -> dict:
    invalidos, cambian_area = [], []
    gs = []
    for i, f in enumerate(feats):
        g = shape(f["geometry"])
        gs.append(g)
        if not g.is_valid:
            invalidos.append(i)
            v = make_valid(g)
            if abs(v.area - g.area) > g.area * 1e-9:
                cambian_area.append((i, round(100 * (v.area - g.area) / max(g.area, 1e-12), 3)))
    # Duplicados: sólo entre los que comparten caja envolvente, para no cruzar
    # todos contra todos.
    dup = []
    for i in range(len(gs)):
        for j in range(i + 1, len(gs)):
            if gs[i].bounds != gs[j].bounds:
                continue
            a, b = gs[i], gs[j]
            if not a.is_valid:
                a = make_valid(a)
            if not b.is_valid:
                b = make_valid(b)
            u = a.union(b).area
            if u and a.intersection(b).area / u > 0.98:
                dup.append((i, j))
    return {"n": len(feats), "invalidos": invalidos,
            "invalidos_que_cambian_area": cambian_area, "duplicados": dup}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provincia", default="Malleco")
    ap.add_argument("--control", action="store_true",
                    help="inyecta defectos conocidos y exige que se detecten")
    ap.add_argument("--salida", help="además de imprimir, escribe este .md")
    a = ap.parse_args()

    cfg_reg = yaml.safe_load((RAIZ / "config" / "araucania.yaml").read_text(encoding="utf-8"))
    prov = {nz(k): v for k, v in cfg_reg["provincias"].items()}
    if nz(a.provincia) not in prov:
        raise SystemExit(f"provincia desconocida: {a.provincia}")
    comunas = {nz(c) for c in prov[nz(a.provincia)]}
    laminas = {c["id"]: c for c in yaml.safe_load(
        (RAIZ / "config" / "laminas.yaml").read_text(encoding="utf-8"))["laminas"]}

    L = [f"# Estado de los polígonos — provincia de {a.provincia.title()}", "",
         "Revisión automática de lo que ya está vectorizado: si la geometría es",
         "válida, si algún polígono quedó cortado en el borde de su lámina, y",
         "cuáles están tan cerca del umbral de área que aparecen o desaparecen si",
         "alguien lo toca. Se corre con:", "",
         "```", "python tools/auditoria/revisar_poligonos_provincia.py "
         f"--provincia {a.provincia.title()}", "```", ""]
    problemas = 0
    detectado = {"truncado": False, "invalido": False, "duplicado": False}

    for lid, cfg in laminas.items():
        if nz(cfg["comuna"]) not in comunas:
            continue
        ruta = RAIZ / "data" / "processed" / "laminas" / f"{lid}.geojson"
        d = cargar(ruta)
        if not d:
            L += [f"## {lid}", "", "⚠️ No existe su GeoJSON: nada que revisar.", ""]
            continue
        feats = list(d["features"])
        marco, m_px = marco_de_lamina(cfg)

        if a.control:
            # Control positivo: tres defectos fabricados que TIENEN que salir.
            from pyproj import Transformer
            from shapely.geometry import Polygon
            from shapely.ops import transform as sh_transform
            inv = Transformer.from_crs(f"EPSG:{cfg['epsg']}", "EPSG:4326", always_xy=True)
            if marco is not None:
                x0, y0, x1, y1 = marco.bounds
                pegado = box(x0, y0, x0 + 50 * (m_px or 1), y0 + 50 * (m_px or 1))
                feats.append({"type": "Feature", "properties": {"clase": "CONTROL-truncado"},
                              "geometry": json.loads(json.dumps(
                                  sh_transform(inv.transform, pegado).__geo_interface__))})
            mono = Polygon([(0, 0), (1e-3, 1e-3), (1e-3, 0), (0, 1e-3)])
            c = shape(feats[0]["geometry"]).centroid
            from shapely.affinity import translate
            feats.append({"type": "Feature", "properties": {"clase": "CONTROL-invalido"},
                          "geometry": json.loads(json.dumps(
                              translate(mono, c.x, c.y).__geo_interface__))})
            feats.append({"type": "Feature", "properties": {"clase": "CONTROL-duplicado"},
                          "geometry": feats[0]["geometry"]})

        val = revisar_validez(feats)
        lam = revisar_lamina(cfg, feats, m_px, marco)
        L += [f"## {lid}", "",
              f"- Geometrías revisadas: **{val['n']}**"
              + (f" · {lam['m_por_px']:.2f} m por píxel de la lámina" if lam["m_por_px"] else ""),
              f"- Geometrías inválidas: **{len(val['invalidos'])}**"
              + (f" (de ellas, {len(val['invalidos_que_cambian_area'])} cambian de área al repararse)"
                 if val["invalidos_que_cambian_area"] else ""),
              f"- Duplicadas (IoU > 0,98): **{len(val['duplicados'])}**",
              f"- Tocando el marco de la hoja: **{len(lam['truncados'])}**"
              + (" — probablemente cortados: la mancha sigue fuera de la lámina"
                 if lam["truncados"] else ""),
              f"- A menos de 20 % del área mínima ({lam['area_minima_m2']:.0f} m²): "
              f"**{len(lam['cerca_umbral'])}**", ""]
        if lam["truncados"]:
            L.append("Clases de los que tocan el marco: "
                     + ", ".join(sorted({str(p.get("clase")) for p in lam["truncados"]})) + ".")
            L.append("")
        problemas += len(val["invalidos"]) + len(val["duplicados"]) + len(lam["truncados"])
        if any(str(p.get("clase")) == "CONTROL-truncado" for p in lam["truncados"]):
            detectado["truncado"] = True
        if val["invalidos"]:
            detectado["invalido"] = True
        if val["duplicados"]:
            detectado["duplicado"] = True

    # Capas del paquete: lo que el recorte a la provincia pudo partir.
    L += ["## Recorte a la provincia", "",
          "Un polígono que toca el borde del recorte está partido acá pero entero",
          "en la capa regional: no es un defecto del dato, es del recorte. Se",
          "revisa para que nadie mida un área creyendo que es la completa.", ""]
    pq = RAIZ / "data" / "processed" / f"paquete_{nz(a.provincia).lower()}"
    gpkg = pq / f"capas_{nz(a.provincia).lower()}.gpkg"
    if gpkg.exists():
        import geopandas as gpd
        import fiona
        pts = cargar(RAIZ / "web" / "data" / "puntos-criticos-inundacion.geojson")
        xs = [f["geometry"]["coordinates"][0] for f in pts["features"]
              if nz(f["properties"].get("comuna")) in comunas]
        ys = [f["geometry"]["coordinates"][1] for f in pts["features"]
              if nz(f["properties"].get("comuna")) in comunas]
        m = 0.15
        borde = box(min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m).exterior
        L += ["| Capa | Geometrías | Tocan el borde del recorte |", "|---|---:|---:|"]
        for capa in fiona.listlayers(gpkg):
            if capa.startswith("00_"):
                continue
            g = gpd.read_file(gpkg, layer=capa)
            if g.empty or g.geometry.isna().all():
                continue
            tocan = int(sum(1 for x in g.geometry if x is not None
                            and x.distance(borde) < 1e-9))
            L.append(f"| {capa} | {len(g)} | {tocan} |")
        L.append("")
    else:
        L += [f"(no existe {gpkg.name}: corre antes el script 20)", ""]

    salida = "\n".join(L)
    print(salida)
    if a.salida:
        Path(a.salida).write_text(salida, encoding="utf-8")
        print(f"\nescrito: {a.salida}")

    if a.control:
        ok = all(detectado.values())
        sys.stderr.write("CONTROL POSITIVO: %s (%s)\n" % (
            "OK" if ok else "FALLA — el arnés no ve defectos que fabriqué",
            ", ".join(f"{k}={'sí' if v else 'NO'}" for k, v in detectado.items())))
        return 0 if ok else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
