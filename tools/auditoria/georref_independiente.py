#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""georref_independiente.py — ¿las láminas vectorizadas aterrizan donde deben?

POR QUÉ. La georreferenciación de dos de las tres láminas sale de rótulos de grilla
tecleados a mano, con UNA sola línea vertical (sin verificación cruzada de escala).
El único control que no participó en la derivación son los puntos críticos de
SENAPRED (capa D) y el modelo del GORE (capa C). Fue ese control el que desenmascaró a
la lámina de la DGA (0 de 77 puntos a menos de 300 m).

QUÉ MIDE, por lámina y por clase:
  · distancia de cada punto crítico fluvial de la comuna (es_inundacion) al polígono
    publicado más cercano, y cuántos quedan a ≤ 0 / 50 / 100 / 300 m;
  · BARRIDO DE CORRIMIENTO: se desplaza la lámina entera en una grilla de
    ±300 m cada 25 m y se busca el desplazamiento que minimiza la distancia mediana
    de los puntos crónicos a la mancha. Si el mínimo está en (0, 0) ± 1 paso, la
    georreferenciación es consistente con la evidencia independiente; si está a
    100 m, hay un corrimiento sistemático que los puntos ven y el RMSE declarado no;
  · intersección con el modelo del GORE (35 m): fracción del área de cada clase que
    cae en ALTA / MEDIA / BAJA / fuera; y al revés, cuánto del GORE dentro de la caja
    de la lámina queda cubierto por ella;
  · consistencia entre las DOS láminas de Angol (estudio 2013 por color y plano PRC
    AR-2a por trama, georreferenciadas por métodos distintos): IoU y fracción de AR-2a
    dentro de Alto∪Medio.

LAS DOS PREGUNTAS DEL INSTRUMENTO
  1. Si la lámina estuviera 200 m corrida, el barrido lo mostraría con el mínimo lejos
     de (0,0) y los puntos a >100 m: control positivo incorporado — se corre el barrido
     también sobre la lámina desplazada artificialmente 150 m y se exige que el mínimo
     aparezca en −150 m.
  2. Si el instrumento estuviera muerto (sin puntos, sin polígonos), imprime n=0 y
     SIN DATO, no un cero.

Uso:  python tools/auditoria/georref_independiente.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml
from pyproj import Transformer
from shapely.affinity import translate
from shapely.geometry import shape
from shapely.ops import transform as sh_transform, unary_union
from shapely.strtree import STRtree

RAIZ = Path(__file__).resolve().parents[2]
EVID = Path(__file__).resolve().parent / "evidencia_laminas"
EVID.mkdir(exist_ok=True)


def cargar(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def a_utm(g, epsg):
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    return sh_transform(tr.transform, g)


def puntos_comuna(sen, comuna, epsg):
    out = []
    for f in sen["features"]:
        p = f["properties"]
        if p["comuna"] == comuna and p["es_inundacion"]:
            out.append((a_utm(shape(f["geometry"]), epsg), p["sector"], p["nivel"], p["cronico"]))
    return out


def dist_stats(pts, union):
    d = np.array([g.distance(union) for g, *_ in pts])
    return {"n": int(len(d)),
            "d_m": [round(x) for x in d],
            "sectores": [(s, n, round(x)) for (_, s, n, _), x in zip(pts, d)],
            "<=0": int((d <= 0).sum()), "<=50": int((d <= 50).sum()),
            "<=100": int((d <= 100).sum()), "<=300": int((d <= 300).sum()),
            "mediana_m": round(float(np.median(d))) if len(d) else None}


def barrido(pts, union, paso=25, alcance=400):
    """Devuelve (dx, dy, media) del corrimiento que minimiza la MEDIA de las distancias
    acotadas a 300 m. (La mediana se saturaba en 0 con 4 de 6 puntos dentro de la
    mancha y no distinguía corrimientos: el control positivo lo cazó.)"""
    mejor = None
    grilla = np.arange(-alcance, alcance + 1, paso)
    tabla = np.zeros((len(grilla), len(grilla)))
    for i, dx in enumerate(grilla):
        for j, dy in enumerate(grilla):
            u = translate(union, dx, dy)
            med = float(np.mean([min(g.distance(u), 300.0) for g, *_ in pts]))
            tabla[i, j] = med
            if mejor is None or med < mejor[2]:
                mejor = (int(dx), int(dy), round(med, 1))
    en_origen = float(tabla[len(grilla) // 2, len(grilla) // 2])
    return mejor, round(en_origen, 1)


def gore_cruce(lam_union, gore_feats, epsg):
    """Fracción del área de la lámina en cada clase del GORE."""
    res = {}
    bbox = lam_union.envelope
    tot = lam_union.area
    dentro_caja = []
    for f in gore_feats:
        g = f["geometry"]
        if not g.intersects(bbox):
            continue
        dentro_caja.append(f)
        cl = f["leyenda"]
        res[cl] = res.get(cl, 0.0) + lam_union.intersection(g).area
    fr = {k: round(100 * v / tot, 1) for k, v in res.items()}
    fr["fuera_del_modelo"] = round(100 - sum(fr.values()), 1)
    # cobertura inversa: del GORE ALTA dentro de la caja, cuánto cubre la lámina
    alta = unary_union([f["geometry"] for f in dentro_caja if f["leyenda"] in ("ALTA", "MAXIMA")])
    inv = round(100 * lam_union.intersection(alta).area / alta.area, 1) if not alta.is_empty else None
    return fr, inv, len(dentro_caja)


def main():
    cfgs = yaml.safe_load((RAIZ / "config/laminas.yaml").read_text(encoding="utf-8"))["laminas"]
    sen = cargar(RAIZ / "data/processed/senapred_puntos_criticos_araucania.geojson")
    gore_raw = cargar(RAIZ / "web/data/gore/amenaza-inundacion.geojson")
    informe = {}
    laminas_utm = {}
    for cfg in cfgs:
        lid, epsg = cfg["id"], cfg["epsg"]
        d = cargar(RAIZ / "data/processed/laminas" / f"{lid}.geojson")
        por_clase = {}
        for f in d["features"]:
            por_clase.setdefault(f["properties"]["clase"], []).append(a_utm(shape(f["geometry"]), epsg))
        union_total = unary_union([g for v in por_clase.values() for g in v])
        laminas_utm[lid] = (por_clase, union_total, epsg)
        pts = puntos_comuna(sen, cfg["comuna"], epsg)
        # sólo los puntos dentro de la caja de la lámina ampliada 2 km: los demás no la miran
        caja = union_total.envelope.buffer(2000)
        pts_caja = [p for p in pts if caja.contains(p[0])]
        r = {"comuna": cfg["comuna"], "epsg": epsg,
             "puntos_fluviales_comuna": len(pts), "puntos_en_caja_2km": len(pts_caja),
             "rmse_declarado_m": d["procedencia"].get("rmse_m", "no declarado"),
             "m_por_px": d["procedencia"].get("metros_por_pixel")}
        for cl, gs in por_clase.items():
            r[f"distancias_a_{cl}"] = dist_stats(pts_caja, unary_union(gs)) if pts_caja else "SIN DATO (0 puntos)"
        r["distancias_a_cualquier_clase"] = dist_stats(pts_caja, union_total) if pts_caja else "SIN DATO"
        if len(pts_caja) >= 3:
            cron = pts_caja
            mejor, en0 = barrido(cron, union_total)
            r["barrido_corrimiento"] = {"puntos_usados": len(cron), "distancias_acotadas_a_m": 300,
                                        "media_acotada_en_(0,0)_m": en0,
                                        "mejor_(dx,dy,media)": mejor,
                                        "paso_m": 25}
            # control positivo: lámina corrida 150 m al este → el mínimo debe salir en dx≈-150
            mejor_c, _ = barrido(cron, translate(union_total, 150, 0))
            r["barrido_control_positivo(+150E → espera dx≈-150)"] = mejor_c
        else:
            r["barrido_corrimiento"] = "SIN DATO (menos de 3 puntos)"
        # GORE
        gore_feats = [{"geometry": a_utm(shape(f["geometry"]), epsg), "leyenda": f["properties"].get("leyenda") or f["properties"].get("clase")}
                      for f in gore_raw["features"]
                      if shape(f["geometry"]).intersects(shape(json.loads(json.dumps(
                          sh_transform(Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True).transform,
                                       union_total.envelope.buffer(500)).__geo_interface__))))]
        if gore_feats:
            for cl, gs in por_clase.items():
                fr, inv, n = gore_cruce(unary_union(gs), gore_feats, epsg)
                r[f"gore_{cl}"] = {"fraccion_pct_por_clase_GORE": fr, "cobertura_de_GORE_MAXIMA_en_caja_pct": inv,
                                   "poligonos_gore_en_caja": n}
        else:
            r["gore"] = "SIN DATO (el modelo del GORE no cubre esta caja)"
        informe[lid] = r
        print(f"\n=== {lid} ===")
        print(json.dumps(r, ensure_ascii=False, indent=1))

    # consistencia entre las dos láminas de Angol
    if "angol-peligro-inundacion-2013" in laminas_utm and "angol-prc-ar2a-lamina1" in laminas_utm:
        pc13, u13, _ = laminas_utm["angol-peligro-inundacion-2013"]
        pcar, uar, _ = laminas_utm["angol-prc-ar2a-lamina1"]
        alto = unary_union(pc13.get("Alto", []))
        medio = unary_union(pc13.get("Medio", []))
        cons = {
            "AR-2a_ha": round(uar.area / 1e4, 1), "Alto2013_ha": round(alto.area / 1e4, 1),
            "Medio2013_ha": round(medio.area / 1e4, 1),
            "iou_AR2a_vs_Alto∪Medio": round(uar.intersection(u13).area / uar.union(u13).area, 3),
            "fraccion_AR2a_dentro_de_Alto_pct": round(100 * uar.intersection(alto).area / uar.area, 1),
            "fraccion_AR2a_dentro_de_Alto∪Medio_pct": round(100 * uar.intersection(u13).area / uar.area, 1),
            "fraccion_Alto_dentro_de_AR2a_pct": round(100 * alto.intersection(uar).area / alto.area, 1),
            "fraccion_Alto_dentro_de_caja_AR2a_que_cae_en_AR2a_pct": round(
                100 * alto.intersection(uar).area / alto.intersection(uar.envelope).area, 1)
                if not alto.intersection(uar.envelope).is_empty else None,
        }
        # barrido entre láminas: ¿qué corrimiento de AR-2a maximiza su intersección con Alto?
        mejor = None
        for dx in range(-400, 401, 20):
            for dy in range(-400, 401, 20):
                a_ = translate(uar, dx, dy).intersection(alto).area
                if mejor is None or a_ > mejor[3]:
                    mejor = (dx, dy, round(a_ / 1e4, 1), a_)
        mejor = mejor[:3]
        cons["interseccion_AR2a_Alto_sin_corrimiento_ha"] = round(uar.intersection(alto).area / 1e4, 1)
        cons["corrimiento_AR2a_que_maximiza_interseccion_con_Alto (dx,dy,ha)"] = mejor
        informe["consistencia_angol"] = cons
        print("\n=== consistencia entre las dos láminas de Angol ===")
        print(json.dumps(cons, ensure_ascii=False, indent=1))
    (EVID / "georref_independiente.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
