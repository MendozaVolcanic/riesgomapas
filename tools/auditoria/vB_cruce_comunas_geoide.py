"""vB: Nueva Imperial, Renaico y Toltén, GeoIDE contra la capa A MINVU publicada.

Verifica F-203, F-204 y F-205 (frente B, 2026-11-15). Descarga propia (una
petición a la vez, 0,6 s de pausa, paginación por exceededTransferLimit) a
data/raw/geoide_minvu_araucania_verif/. No toca nada del proyecto.

QUÉ MIDE
    Para cada capa de GeoIDE: features por ZONA/NOM, área en EPSG:32718 (las
    tres comunas están al oeste de 72° O, huso 18S), P_DO / N_DOC / T_DO, y
    cuánto de esa área cubre el polígono que el visor publica para la comuna
    (web/data/areas-riesgo-inundacion.geojson), y al revés.

LAS DOS PREGUNTAS DEL INSTRUMENTO
    (1) Si el visor ya tuviera esos polígonos, ¿la prueba lo vería? Sí: mide
        cobertura geométrica, no conteo; --control inyecta en «nuestra» capa
        las geometrías de GeoIDE de Toltén y exige cobertura >= 0,99.
    (2) Si el instrumento estuviera muerto (proyección o lectura mal), ¿se
        vería distinto? Sí: el polígono de Renaico Tijeral que ya tenemos tiene
        que solaparse con la capa 9 (Tijeral); si da 0 la proyección está mal.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform as sh_transform, unary_union

RAIZ = Path(__file__).resolve().parents[2]
DEST = RAIZ / "data/raw/geoide_minvu_araucania_verif"
BASE = "https://geoide.minvu.cl/server/rest/services/IPT/PRC_Araucania/FeatureServer"
CAPAS = {9: "Renaico", 31: "Renaico", 33: "Nueva Imperial", 34: "Toltén", 37: "Toltén"}
PUB = RAIZ / "web/data/areas-riesgo-inundacion.geojson"


def get(url, params):
    u = url + "?" + urllib.parse.urlencode(params)
    time.sleep(0.6)
    with urllib.request.urlopen(u, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def descargar(n):
    f = DEST / f"capa{n}_32718.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    meta = get(f"{BASE}/{n}", {"f": "json"})
    cnt = get(f"{BASE}/{n}/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    feats, off = [], 0
    while True:
        r = get(f"{BASE}/{n}/query", {"where": "1=1", "outFields": "*", "outSR": 32718, "f": "json",
                                       "resultOffset": off, "resultRecordCount": meta.get("maxRecordCount", 1000)})
        if "error" in r:
            raise SystemExit(f"capa {n}: {r['error']}")
        feats += r["features"]
        if not r["features"] or not r.get("exceededTransferLimit"):
            break
        off += len(r["features"])
    d = {"capa": n, "nombre": meta.get("name"), "descripcion": meta.get("description"),
         "count_servicio": cnt, "features": feats, "fecha": time.strftime("%Y-%m-%d %H:%M")}
    if len(feats) != cnt:
        raise SystemExit(f"capa {n}: {len(feats)} features vs count {cnt}")
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def esri(geom):
    ext, hue = [], []
    for r in geom["rings"]:
        p = Polygon(r)
        (ext if not p.exterior.is_ccw else hue).append(p)
    g = unary_union(ext)
    for h in hue:
        g = g.difference(h)
    return g if g.is_valid else g.buffer(0)


def main():
    control = "--control" in sys.argv
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32718", always_xy=True)
    pub = json.load(open(PUB, encoding="utf-8"))
    nuestros = defaultdict(list)
    for f in pub["features"]:
        p = f["properties"]
        g = sh_transform(tr.transform, shape(f["geometry"]))
        nuestros[p["comuna"]].append((p.get("sector"), p.get("zona"), p.get("anio"), g if g.is_valid else g.buffer(0)))
    for com in ("Renaico", "Nueva Imperial", "Toltén"):
        print(f"visor {com}: " + "; ".join(f"{s}/{z}/año {a}/{g.area/1e4:.2f} ha" for s, z, a, g in nuestros[com]))
    geo = {}
    for n, com in CAPAS.items():
        d = descargar(n)
        print(f"\n== capa {n} {d['nombre']} ({d['count_servicio']} features, descarga {d['fecha']}) ==")
        porz = defaultdict(lambda: [0, 0.0])
        docs = set()
        gs = []
        for f in d["features"]:
            a = f["attributes"]
            g = esri(f["geometry"])
            k = (a.get("ZONA"), a.get("NOM"))
            porz[k][0] += 1; porz[k][1] += g.area
            docs.add((a.get("T_DO"), a.get("N_DOC"), a.get("P_DO"), a.get("LOC")))
            gs.append((k, g))
        for k, (c, ar) in sorted(porz.items(), key=lambda t: -t[1][1]):
            print(f"  {c:3d} x {str(k[0]):8s} {str(k[1])[:70]:70s} {ar/1e4:8.2f} ha")
        print(f"  documentos (T_DO, N_DOC, P_DO, LOC): {sorted(docs, key=str)}")
        geo[n] = gs
    # Cruce: área hídrica de GeoIDE (por texto de NOM) contra nuestra capa.
    HID = ("INUND", "ANEG", "NAPA", "TSUN", "CAUCE", "RIO", "RÍO", "ESTERO", "CANAL", "HUMED")
    def es_hid(k):
        t = f"{k[0]} {k[1]}".upper()
        return any(h in t for h in HID)
    print("\n== Cruce geométrico (EPSG:32718) ==")
    for com, ns in (("Renaico", (9, 31)), ("Nueva Imperial", (33,)), ("Toltén", (34, 37))):
        N = unary_union([g for *_, g in nuestros[com]]) if nuestros[com] else Polygon()
        for n in ns:
            H = unary_union([g for k, g in geo[n] if es_hid(k)])
            T = unary_union([g for k, g in geo[n]])
            if H.is_empty:
                print(f"  {com} capa {n}: sin features hídricas por texto"); continue
            print(f"  {com} capa {n}: hídrico GeoIDE {H.area/1e4:.2f} ha ({sum(1 for k,_ in geo[n] if es_hid(k))} feats); "
                  f"cubierto por el visor {H.intersection(N).area/H.area:.3f}; "
                  f"visor dentro de esta capa (cualquier zona) {N.intersection(T).area/max(N.area,1):.3f}; "
                  f"distancia visor-capa {N.distance(T):.0f} m")
        if com == "Renaico":
            cov9 = N.intersection(unary_union([g for _, g in geo[9]])).area
            print(f"  chequeo vivo: visor Renaico ∩ capa 9 = {cov9/1e4:.2f} ha")
            if cov9 == 0:
                sys.exit("instrumento muerto: Tijeral no se solapa con la capa 9")
    if control:
        Ht = unary_union([g for n in (34, 37) for k, g in geo[n] if es_hid(k)])
        N = unary_union([g for *_, g in nuestros["Toltén"]] + [Ht])
        cov = Ht.intersection(N).area / Ht.area
        print(f"\nCONTROL Toltén con GeoIDE inyectado: cobertura {cov:.3f} -> {'OK' if cov >= 0.99 else 'FALLA'}")
        if cov < 0.99:
            sys.exit(1)


if __name__ == "__main__":
    main()
