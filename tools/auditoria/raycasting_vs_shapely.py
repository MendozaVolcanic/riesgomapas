"""Compara el ray-casting del visor (vía raycasting_adversarial.js) contra shapely.

Qué mide: veredicto por veredicto, si `poligonosQueContienen` de web/app.js
responde lo mismo que shapely para (a) casos adversariales sintéticos,
(b) puntos dentro de los huecos reales de las capas publicadas, y (c) un
barrido aleatorio con semilla fija sobre la caja de cada capa publicada.

Las dos preguntas del instrumento:
 (1) Si el ray-casting estuviera roto, ¿esto falla?  Sí: cada caso trae su
     esperado y la comparación contra shapely es punto a punto; una copia
     adulterada de app.js (--app) hace saltar las discrepancias.
 (2) Si el instrumento estuviera muerto, ¿se vería distinto?  Sí: el arnés de
     Node muere con código 2 si no extrae las funciones, y este script aborta si
     el conteo de veredictos no coincide con el de puntos enviados.

Semántica: el visor dice "dentro" si el punto está en el anillo exterior y en
ningún hueco. shapely `contains` excluye el borde y `covers` lo incluye. Un
punto EXACTAMENTE en el borde es indefinido por diseño en ray-casting; se
reporta como discrepancia sólo si el visor contradice a `contains` Y a `covers`
a la vez (es decir, si el punto no está en el borde y aun así difieren).

Uso:
    python tools/auditoria/raycasting_vs_shapely.py [--n 2000] [--semilla 20260906] [--app web/app.js]
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

from shapely.geometry import Point, Polygon, shape
from shapely.validation import make_valid

RAIZ = Path(__file__).resolve().parents[2]
ARNES = RAIZ / "tools" / "auditoria" / "raycasting_adversarial.js"
LAT_REF = -38.0
M_LAT = 1 / 111_195.0                      # grados de latitud por metro (esfera R=6371 km)
import math
M_LON = 1 / (111_195.0 * math.cos(math.radians(LAT_REF)))

CAPAS = {
    "A_normativo": "web/data/areas-riesgo-inundacion.geojson",
    "A_derivada": "web/data/laminas/vectorizadas.geojson",
    "C_gore": "web/data/gore/amenaza-inundacion.geojson",
    "C_jrc_rp100": "web/data/jrc/rp100.geojson",
    "B_sar_huella": "web/data/sar/huella-observada.geojson",
    "D_campamentos": "web/data/campamentos-inundacion.geojson",
}


def fc(*geoms):
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {"i": i}, "geometry": g}
                         for i, g in enumerate(geoms)]}


def poly(ext, holes=()):
    return {"type": "Polygon", "coordinates": [list(map(list, ext))] + [list(map(list, h)) for h in holes]}


def casos_sinteticos():
    """Cada caso: id, fc, puntos, esperado (lista de índices por punto, o None = borde/indefinido)."""
    x0, y0, x1, y1 = -72.70, -37.80, -72.60, -37.70          # cuadrado ~8,8 km x 11 km
    ccw = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    cw = list(reversed(ccw))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    casos = []

    def caso(id_, fcol, puntos, esperado):
        casos.append({"id": id_, "fc": fcol, "puntos": puntos, "esperado": esperado})

    caso("control_positivo", fc(poly(ccw)), [[cx, cy]], [[0]])
    caso("control_negativo", fc(poly(ccw)), [[x1 + 0.05, cy]], [[]])
    caso("vertice_exacto", fc(poly(ccw)), [[x0, y0], [x1, y1]], [None, None])
    caso("arista_horizontal", fc(poly(ccw)), [[cx, y0], [cx, y1]], [None, None])
    caso("arista_vertical", fc(poly(ccw)), [[x0, cy], [x1, cy]], [None, None])
    for m in (1, 3, 10):
        caso(f"borde_{m}m_dentro", fc(poly(ccw)),
             [[x0 + m * M_LON, cy], [cx, y0 + m * M_LAT]], [[0], [0]])
        caso(f"borde_{m}m_fuera", fc(poly(ccw)),
             [[x0 - m * M_LON, cy], [cx, y0 - m * M_LAT]], [[], []])
    caso("exterior_horario", fc(poly(cw)), [[cx, cy], [x1 + 0.05, cy]], [[0], []])
    hole = [(cx - 0.01, cy - 0.01), (cx + 0.01, cy - 0.01), (cx + 0.01, cy + 0.01), (cx - 0.01, cy + 0.01), (cx - 0.01, cy - 0.01)]
    caso("hueco_antihorario", fc(poly(ccw, [hole])), [[cx, cy], [cx + 0.03, cy]], [[], [0]])
    caso("hueco_horario", fc(poly(ccw, [list(reversed(hole))])), [[cx, cy], [cx + 0.03, cy]], [[], [0]])
    caso("hueco_borde_1m_dentro_del_hueco", fc(poly(ccw, [hole])),
         [[cx - 0.01 + 1 * M_LON, cy]], [[]])
    caso("hueco_borde_1m_fuera_del_hueco", fc(poly(ccw, [hole])),
         [[cx - 0.01 - 1 * M_LON, cy]], [[0]])
    segunda = [(x1 + 0.1, y0), (x1 + 0.2, y0), (x1 + 0.2, y1), (x1 + 0.1, y1), (x1 + 0.1, y0)]
    mp = {"type": "MultiPolygon", "coordinates": [poly(ccw)["coordinates"], poly(segunda)["coordinates"]]}
    caso("multipolygon_segunda_parte", fc(mp), [[x1 + 0.15, cy], [x1 + 0.05, cy]], [[0], []])
    # moño (bow-tie): anillo autointersectado. shapely lo declara inválido.
    mono = [(x0, y0), (x1, y1), (x1, y0), (x0, y1), (x0, y0)]
    caso("mono_autointerseccion", fc(poly(mono)),
         [[x0 + 0.02, cy], [x1 - 0.02, cy], [cx, cy + 0.03], [cx, cy - 0.03]],
         "shapely")                                   # sin esperado a priori: se contrasta
    # polígono degenerado: anillo abierto (sin repetir el primer vértice)
    caso("anillo_abierto", fc({"type": "Polygon", "coordinates": [[list(p) for p in ccw[:-1]]]}),
         [[cx, cy]], [[0]])
    # dos features que se solapan: ¿devuelve ambos?
    caso("dos_features_solapadas", fc(poly(ccw), poly(ccw)), [[cx, cy]], [[0, 1]])
    return casos


def cargar(rel):
    return json.loads((RAIZ / rel).read_text(encoding="utf-8"))


from shapely.strtree import STRtree


class Indice:
    """Geometrías validadas UNA vez (make_valid sobre las inválidas) + STRtree.
    Sin esto, GORE (2539 polígonos, 198 inválidos) y SAR (1075, 585 inválidos)
    tardaban horas: make_valid se llamaba por punto y por polígono."""

    def __init__(self, fcol):
        self.gs = []
        for f in fcol["features"]:
            g = shape(f["geometry"]) if f.get("geometry") else None
            if g is not None and not g.is_valid:
                g = make_valid(g)
            self.gs.append(g)
        self.validos = [(i, g) for i, g in enumerate(self.gs) if g is not None]
        self.tree = STRtree([g for _, g in self.validos])

    def indices(self, pt, modo):
        out = []
        for k in self.tree.query(pt):
            i, g = self.validos[k]
            if (g.covers(pt) if modo == "covers" else g.contains(pt)):
                out.append(i)
        return sorted(out)


def geoms(fcol):
    return Indice(fcol)


def shapely_indices(pt, idx, modo):
    return idx.indices(pt, modo)


def casos_huecos_reales():
    """Un punto en el punto representativo de CADA hueco real de cada capa."""
    casos = []
    for nombre, rel in CAPAS.items():
        fcol = cargar(rel)
        puntos, esperado, meta = [], [], []
        for i, f in enumerate(fcol["features"]):
            g = f.get("geometry")
            if not g:
                continue
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            for po in polys:
                for h in po[1:]:
                    hp = Polygon(h)
                    if hp.is_empty or hp.area == 0:
                        continue
                    p = hp.representative_point()
                    puntos.append([p.x, p.y])
                    esperado.append("shapely")
                    meta.append(i)
        if puntos:
            casos.append({"id": f"huecos_reales:{nombre}", "fc": fcol, "puntos": puntos,
                          "esperado": "shapely", "feature_del_hueco": meta})
    return casos


def casos_barrido(n, semilla):
    casos = []
    for nombre, rel in CAPAS.items():
        fcol = cargar(rel)
        gs = [shape(f["geometry"]) for f in fcol["features"] if f.get("geometry")]
        minx = min(g.bounds[0] for g in gs); miny = min(g.bounds[1] for g in gs)
        maxx = max(g.bounds[2] for g in gs); maxy = max(g.bounds[3] for g in gs)
        rnd = random.Random(f"{semilla}:{nombre}")
        # mitad uniforme en la caja, mitad "pegada" a un borde (±0..20 m de un vértice)
        puntos = []
        for _ in range(n // 2):
            puntos.append([rnd.uniform(minx, maxx), rnd.uniform(miny, maxy)])
        verts = []
        for g in gs:
            polys = g.geoms if g.geom_type == "MultiPolygon" else [g]
            for p in polys:
                verts.extend(p.exterior.coords[::7])
        for _ in range(n - n // 2):
            vx, vy = rnd.choice(verts)
            d = rnd.uniform(-20, 20)
            puntos.append([vx + d * M_LON, vy + rnd.uniform(-20, 20) * M_LAT])
        casos.append({"id": f"barrido:{nombre}", "fc": fcol, "puntos": puntos, "esperado": "shapely"})
    return casos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--semilla", type=int, default=20260906)
    ap.add_argument("--app", default=None)
    ap.add_argument("--salida-json", default=None)
    a = ap.parse_args()

    casos = casos_sinteticos() + casos_huecos_reales() + casos_barrido(a.n, a.semilla)
    import tempfile
    tmp = Path(a.salida_json).with_suffix(".casos.json") if a.salida_json \
        else Path(tempfile.gettempdir()) / "raycasting_casos.json"
    tmp.write_text(json.dumps({"casos": [{k: c[k] for k in ("id", "fc", "puntos")} for c in casos]}),
                   encoding="utf-8")
    cmd = ["node", str(ARNES), "--casos", str(tmp)] + (["--app", a.app] if a.app else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ARNES MURIÓ:", r.returncode, r.stderr)
        sys.exit(2)
    salida = json.loads(r.stdout)
    print("extracción:", json.dumps(salida["extraccion"]))
    res = {x["id"]: x["contiene"] for x in salida["resultados"]}

    total = 0
    discrepancias = []
    filas = []
    for c in casos:
        vis = res[c["id"]]
        if len(vis) != len(c["puntos"]):
            print("INSTRUMENTO MUERTO: conteo de veredictos ≠ puntos en", c["id"]); sys.exit(2)
        gs = geoms(c["fc"])
        n_disc = 0
        n_borde = 0
        for k, (lon, lat) in enumerate(c["puntos"]):
            total += 1
            pt = Point(lon, lat)
            sc = shapely_indices(pt, gs, "contains")
            sv = shapely_indices(pt, gs, "covers")
            v = sorted(vis[k])
            esperado = c["esperado"] if c["esperado"] == "shapely" else c["esperado"][k]
            en_borde = sc != sv
            if en_borde:
                n_borde += 1
            coincide = (v == sorted(sc)) or (v == sorted(sv))
            if esperado not in ("shapely", None):
                coincide = coincide and v == sorted(esperado)
            if not coincide:
                n_disc += 1
                discrepancias.append({"caso": c["id"], "punto": [lon, lat], "visor": v,
                                      "shapely_contains": sc, "shapely_covers": sv,
                                      "esperado": esperado})
            if not c["id"].startswith(("barrido", "huecos_reales")):
                filas.append((c["id"], [round(lon, 7), round(lat, 7)],
                              "borde" if esperado is None else esperado, v, sc, sv,
                              "borde:indefinido" if en_borde else ("OK" if coincide else "DISCREPA")))
        if c["id"].startswith(("barrido", "huecos_reales")):
            print(f"{c['id']:32s} puntos={len(c['puntos']):5d} en_borde_exacto={n_borde} discrepancias={n_disc}")

    print("\n| caso | punto [lon, lat] | esperado | visor | shapely contains | shapely covers | veredicto |")
    print("|---|---|---|---|---|---|---|")
    for f in filas:
        print("| " + " | ".join(str(x) for x in f) + " |")
    print(f"\nTOTAL puntos evaluados: {total}   discrepancias visor↔shapely: {len(discrepancias)}")
    for d in discrepancias[:60]:
        print("  DISCREPA", json.dumps(d))
    if a.salida_json:
        Path(a.salida_json).write_text(json.dumps({"total": total, "discrepancias": discrepancias,
                                                   "extraccion": salida["extraccion"]}, indent=1),
                                       encoding="utf-8")


if __name__ == "__main__":
    main()
