"""Auditoría de la capa A (áreas de riesgo PRC del MINVU) medida sobre el dato.

Las dos preguntas del instrumento:
 (1) Si el artefacto estuviera roto (duplicados, filtro que deja fuera clases
     hídricas, polígonos inválidos), ¿esta prueba lo vería?  Sí: la IoU entre
     pares se calcula sobre la geometría y no sobre un identificador; el filtro
     se contrasta con vocabulario hídrico independiente del script; la validez
     la evalúa shapely.  Se comprueba con controles positivos sintéticos al
     inicio (par idéntico → IoU 1,0; «pajarita» → inválido).
 (2) Si el instrumento estuviera muerto, ¿se vería distinto?  Sí: los controles
     positivos imprimen CONTROL FALLÓ y el script sale con código 2.

Sólo lee. No escribe en data/ ni web/.
Uso:  python tools/auditoria/capa_a_duplicados_y_filtro.py
"""
from __future__ import annotations

import collections
import io
import json
import sys
import unicodedata
from itertools import combinations
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape, Polygon
from shapely.ops import transform as sh_transform
from shapely.validation import explain_validity

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
UNIVERSO = RAIZ / "data/processed/areas_riesgo_prc_araucania.geojson"
PUBLICADO = RAIZ / "web/data/areas-riesgo-inundacion.geojson"

# EPSG:4326 → UTM 19S (WGS84). La región va de −73,7 a −70,9; la zona 19 empieza
# en −72, así que la mitad oeste está fuera de zona pero la distorsión a 1,7°
# del meridiano central es < 0,1 % en área: sobra para IoU y hectáreas.
_T = Transformer.from_crs("EPSG:4326", "EPSG:32719", always_xy=True)


def a_utm(g):
    return sh_transform(_T.transform, g)


def norm(t):
    return unicodedata.normalize("NFKD", (t or "")).encode("ascii", "ignore").decode().upper()


VOCAB_HIDRICO = ["INUND", "ANEGA", "CAUCE", "QUEBRAD", "ESTERO", "RIO ", "RIO", "NAPA",
                 "LITORAL", "TSUNAMI", "MAREJ", "HIDR", "FLUVIAL", "DRENAJ", "LAGO", "CANAL"]


def vocab(p):
    txt = " ".join(norm(p.get(k)) for k in ("nombre", "clasificacion", "zona", "sector"))
    return sorted({v.strip() for v in VOCAB_HIDRICO if v in txt})


def cargar(p):
    d = json.loads(p.read_text(encoding="utf-8"))
    return d["features"]


def controles():
    ok = True
    a = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    b = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    iou = a.intersection(b).area / a.union(b).area
    if abs(iou - 1.0) > 1e-9:
        print("CONTROL FALLÓ: par idéntico no da IoU 1,0"); ok = False
    c = Polygon([(0.5, 0), (1.5, 0), (1.5, 1), (0.5, 1)])
    iou2 = a.intersection(c).area / a.union(c).area
    if abs(iou2 - 1 / 3) > 1e-9:
        print("CONTROL FALLÓ: par desplazado no da IoU 1/3"); ok = False
    pajarita = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
    if pajarita.is_valid:
        print("CONTROL FALLÓ: la pajarita salió válida"); ok = False
    print(f"controles positivos: IoU idéntico={iou:.3f}  IoU desplazado={iou2:.3f}  "
          f"pajarita válida={pajarita.is_valid}  → {'OK' if ok else 'FALLÓ'}")
    if not ok:
        sys.exit(2)


def main():
    controles()
    uni = cargar(UNIVERSO)
    pub = cargar(PUBLICADO)
    print(f"\nuniverso: {len(uni)} · publicados: {len(pub)}")

    # ------------------------------------------------------------ Pregunta 1
    print("\n=== P1. Collipulli: ¿36 geometrías distintas o duplicados? ===")
    por_comuna = collections.Counter(f["properties"]["comuna"] for f in pub)
    print("publicados por comuna:", dict(por_comuna.most_common()))
    geoms = [(i, f, a_utm(shape(f["geometry"]))) for i, f in enumerate(pub)]
    print("\nIoU > 0,5 entre pares publicados (todas las comunas):")
    pares_dup = []
    for (i, fi, gi), (j, fj, gj) in combinations(geoms, 2):
        if not gi.intersects(gj):
            continue
        inter = gi.intersection(gj).area
        if inter <= 0:
            continue
        iou = inter / gi.union(gj).area
        if iou > 0.5:
            pares_dup.append((iou, i, j))
    if not pares_dup:
        print("  ninguno")
    for iou, i, j in sorted(pares_dup, reverse=True):
        pi, pj = pub[i]["properties"], pub[j]["properties"]
        print(f"  IoU={iou:.3f}  #{i} {pi['comuna']} | {pi['origen_capa']} | {pi['zona']} "
              f"| {(pi['nombre'] or '')[:40]}   <->   #{j} {pj['origen_capa']} | {pj['zona']} "
              f"| {(pj['nombre'] or '')[:40]}")
    # Contención parcial (un polígono dentro de otro) también le dice al visor
    # «cae dentro de 2 áreas».
    print("\nsolapes parciales con intersección > 10 % del menor (todas las comunas):")
    n_sol = 0
    for (i, fi, gi), (j, fj, gj) in combinations(geoms, 2):
        if not gi.intersects(gj):
            continue
        inter = gi.intersection(gj).area
        menor = min(gi.area, gj.area)
        if menor > 0 and inter / menor > 0.10:
            n_sol += 1
            pi, pj = pub[i]["properties"], pub[j]["properties"]
            print(f"  {inter/menor:5.1%} del menor  #{i} {pi['comuna']} {pi['zona']} "
                  f"({gi.area/1e4:.1f} ha, {pi['origen_capa']})  <->  #{j} {pj['zona']} "
                  f"({gj.area/1e4:.1f} ha, {pj['origen_capa']})")
    print(f"  total pares con solape parcial: {n_sol}")

    print("\nCollipulli, los 36 publicados:")
    col = [(i, f, g) for i, f, g in geoms if f["properties"]["comuna"] == "Collipulli"]
    print(f"  {'#':>3} {'ha':>8} {'origen_capa':<26} {'zona':<8} {'sector':<14} nombre | clasificacion")
    for i, f, g in col:
        p = f["properties"]
        print(f"  {i:>3} {g.area/1e4:8.2f} {str(p['origen_capa'])[:26]:<26} {str(p['zona']):<8} "
              f"{str(p['sector'])[:14]:<14} {str(p['nombre'])[:45]} | {p['clasificacion']}")
    print("  origen_capa:", dict(collections.Counter(f["properties"]["origen_capa"] for _, f, _ in col)))
    print("  zona:", dict(collections.Counter(f["properties"]["zona"] for _, f, _ in col)))
    print("  clasificacion:", dict(collections.Counter(f["properties"]["clasificacion"] for _, f, _ in col)))
    print("  área total Collipulli publicada: %.1f ha" % (sum(g.area for _, _, g in col) / 1e4))
    # ¿Comparten vértices exactos (misma geometría con distinto centroide redondeado)?
    firmas = collections.Counter(json.dumps(f["geometry"]["coordinates"]) for _, f, _ in col)
    print("  geometrías byte-idénticas repetidas:", sum(v - 1 for v in firmas.values()))
    # En el universo (124), Collipulli por origen y es_inundacion
    uc = [f for f in uni if f["properties"]["comuna"] == "Collipulli"]
    print(f"  en el universo Collipulli tiene {len(uc)}; por origen×es_inundacion:",
          dict(collections.Counter((f["properties"]["origen_capa"], f["properties"]["es_inundacion"]) for f in uc)))

    # ------------------------------------------------------------ Pregunta 2
    print("\n=== P2. Filtro «inundación»: clasificacion × tipo_hidrico × es_inundacion (124) ===")
    tabla = collections.Counter(
        (f["properties"]["clasificacion"], f["properties"]["tipo_hidrico"],
         f["properties"]["es_inundacion"]) for f in uni)
    for (c, t, e), n in sorted(tabla.items(), key=lambda x: (-x[1], str(x[0]))):
        print(f"  {n:4d}  es_inund={str(e):<5}  tipo={str(t):<14}  {c}")
    desc = [f for f in uni if not f["properties"]["es_inundacion"]]
    print(f"\nDescartados: {len(desc)}. Con vocabulario hídrico en nombre/clasificacion/zona/sector:")
    n_v = 0
    for f in desc:
        p = f["properties"]
        v = vocab(p)
        if v:
            n_v += 1
            print(f"  {p['comuna']:<16} {str(p['zona']):<8} {str(p['nombre'])[:50]:<50} "
                  f"| {p['clasificacion']} | {v}")
    print(f"  → {n_v} descartados con vocabulario hídrico")
    print("\nDescartados sin vocabulario hídrico (comuna / zona / nombre / clasificacion):")
    for f in desc:
        p = f["properties"]
        if not vocab(p):
            print(f"  {p['comuna']:<16} {str(p['zona']):<8} {str(p['nombre'])[:50]:<50} | {p['clasificacion']}")
    print("\nPublicados SIN vocabulario hídrico (entraron sin serlo):")
    n_sin = 0
    for f in pub:
        p = f["properties"]
        if not vocab(p):
            n_sin += 1
            print(f"  {p['comuna']:<16} {str(p['zona']):<8} {str(p['nombre'])[:50]:<50} | {p['clasificacion']} | {p['origen_capa']}")
    print(f"  → {n_sin}")
    print("\ntipo_hidrico entre los 63 publicados:",
          dict(collections.Counter(f["properties"].get("tipo_hidrico") for f in pub)))
    print("es_inundacion entre los 63 publicados:",
          dict(collections.Counter(f["properties"].get("es_inundacion") for f in pub)))
    print("clasificacion entre los 63 publicados:",
          dict(collections.Counter(f["properties"].get("clasificacion") for f in pub)))
    # ¿el publicado es exactamente el subconjunto es_inundacion del universo?
    fu = {json.dumps(f["geometry"]["coordinates"]) for f in uni if f["properties"]["es_inundacion"]}
    fp = {json.dumps(f["geometry"]["coordinates"]) for f in pub}
    print(f"geometrías es_inundacion en universo: {len(fu)} · publicadas: {len(fp)} · "
          f"sólo en universo: {len(fu - fp)} · sólo en publicado: {len(fp - fu)}")

    # ------------------------------------------------------------ Pregunta 3
    print("\n=== P3. Polígonos sin año ===")
    for coleccion, nombre in ((uni, "universo"), (pub, "publicados")):
        sin = [f for f in coleccion if not f["properties"].get("anio")
               or "no declarado" in str(f["properties"].get("anio"))]
        print(f"{nombre}: {len(sin)} sin año")
        for f in sin:
            p = f["properties"]
            print(f"  comuna={p['comuna']!r} comuna_fuente={p.get('comuna_fuente')!r} "
                  f"anio={p.get('anio')!r} anio_fuente={p.get('anio_fuente')!r} "
                  f"zona={p['zona']} nombre={str(p['nombre'])[:40]} es_inund={p['es_inundacion']} "
                  f"origen={p['origen_capa']}")
    print("anio_fuente en universo:",
          dict(collections.Counter(str(f["properties"].get("anio_fuente"))[:30] for f in uni)))
    print("anio por comuna (publicados):",
          {c: sorted({str(f["properties"].get("anio")) for f in pub if f["properties"]["comuna"] == c})
           for c in sorted(por_comuna)})

    # ------------------------------------------------------------ Pregunta 4
    print("\n=== P4. Validez geométrica de los 63 publicados ===")
    inval, ceros, huecos_mal, ext_mal = [], [], [], []
    for i, f in enumerate(pub):
        g = shape(f["geometry"])
        if not g.is_valid:
            inval.append((i, explain_validity(g)))
        gu = a_utm(g)
        if gu.area < 100:                      # < 1 are
            ceros.append((i, gu.area))
        polys = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
        for pg in polys:
            if not pg.exterior.is_ccw:
                ext_mal.append(i)
            for r in pg.interiors:
                if r.is_ccw:
                    huecos_mal.append(i)
    print(f"inválidos: {len(inval)}")
    for i, e in inval:
        p = pub[i]["properties"]
        print(f"  #{i} {p['comuna']} {p['zona']} {str(p['nombre'])[:40]}: {e}")
    print(f"área < 100 m²: {len(ceros)}", ceros)
    print(f"exteriores en sentido horario (RFC 7946 pide antihorario): {len(set(ext_mal))} polígonos")
    print(f"huecos en sentido antihorario (RFC 7946 pide horario): {len(set(huecos_mal))} polígonos")
    n_huecos = sum(len(pg.interiors) for f in pub for pg in
                   (list(shape(f["geometry"]).geoms) if f["geometry"]["type"] == "MultiPolygon"
                    else [shape(f["geometry"])]))
    print(f"total anillos interiores en publicados: {n_huecos}")
    areas = sorted(a_utm(shape(f["geometry"])).area / 1e4 for f in pub)
    print(f"áreas ha: min={areas[0]:.3f} p50={areas[len(areas)//2]:.2f} max={areas[-1]:.1f} "
          f"suma={sum(areas):.1f}")
    # también el universo
    inval_u = [(i, explain_validity(shape(f["geometry"]))) for i, f in enumerate(uni)
               if not shape(f["geometry"]).is_valid]
    print(f"inválidos en universo (124): {len(inval_u)}")
    for i, e in inval_u:
        p = uni[i]["properties"]
        print(f"  #{i} {p['comuna']} {p['zona']} es_inund={p['es_inundacion']}: {e[:120]}")


if __name__ == "__main__":
    main()
