"""Utilidades compartidas de fB_*: ArcGIS JSON -> shapely (anillos con signo), lectura raw."""
import json, pathlib
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union, transform
from pyproj import Transformer

# las capas se bajaron en EPSG:32719 (lo pedido); toda medida de este frente va en 32718, la zona UTM de Angol y de
# la mayor parte de La Araucania. Mezclar ambas hizo que un primer cruce diera IoU 0 en todas las comunas.
T19_18 = Transformer.from_crs(32719, 32718, always_xy=True)

RAW = pathlib.Path(r"C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\data\raw\geoide_minvu_araucania")


def anillos_a_shapely(rings):
    """Convencion ArcGIS: exterior en sentido horario (area con signo negativa en
    el plano), huecos antihorario. Cada hueco se resta del exterior que lo contiene."""
    ext, hue = [], []
    for r in rings:
        if len(r) < 4:
            continue
        p = Polygon(r)
        a2 = sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1))
        (ext if a2 < 0 else hue).append(p.buffer(0) if not p.is_valid else p)
    if not ext and hue:   # defensa: orientacion invertida en toda la capa
        ext, hue = hue, []
    res = []
    for e in ext:
        h = [x for x in hue if e.contains(x.representative_point())]
        res.append(e.difference(unary_union(h)) if h else e)
    return unary_union(res) if res else Polygon()


def cargar_capa(n, sufijo="", a32718=True):
    d = json.loads((RAW / f"capa_{n:02d}{sufijo}.json").read_text(encoding="utf-8"))
    out = []
    for f in d["features"]:
        g = f.get("geometry")
        if g is None:
            geom = None
        elif "rings" in g:
            geom = anillos_a_shapely(g["rings"])
        elif "paths" in g:
            geom = unary_union([LineString(p) for p in g["paths"]])
        else:
            geom = None
        if geom is not None and a32718 and sufijo == "":
            geom = transform(T19_18.transform, geom)
        out.append((f["attributes"], geom, (len(g.get("rings", [])) if g else 0)))
    return d, out
