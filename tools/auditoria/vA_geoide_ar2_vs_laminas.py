"""vA_geoide_ar2_vs_laminas.py : F-103, ¿cuánto del AR-2a / AR-2b que GeoIDE publica
para Angol queda fuera de lo que el visor dibuja y usa en el veredicto?

POR QUÉ. El visor dice que Angol no tiene vectorial oficial y usa sólo sus
láminas derivadas (clase AR-2a, 54 polígonos). GeoIDE publica los polígonos
(10 AR-2a, 11 AR-2b). Si el visor los reproduce bien, el área de GeoIDE que
queda fuera de las láminas derivadas es ~0; AR-2b no existe en las láminas.

LAS DOS PREGUNTAS DEL INSTRUMENTO
 1. Si las láminas no reprodujeran GeoIDE, ¿lo vería? Sí: mide fracción de área
    de GeoIDE fuera de las láminas. CONTROL: la fracción de GeoIDE AR-2a contra
    sí misma (union de AR-2a) debe dar 0 % fuera; y contra un conjunto vacío,
    100 %. Si no, el detector está roto.
 2. Si el servicio no respondiera, lanza error (no imprime 0 %).
Uso: python -I tools/auditoria/vA_geoide_ar2_vs_laminas.py RUTA_GEOJSON_DE_GEOIDE
  (descargar antes: .../FeatureServer/29/query?where=1%3D1&outFields=*&outSR=4326&f=geojson)
"""
import json
import sys
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import unary_union, transform

RAIZ = Path(__file__).resolve().parents[2]
g = json.load(open(sys.argv[1], encoding="utf-8"))
if not g.get("features"):
    sys.exit("SIN DATO: el GeoJSON de GeoIDE vino vacío")
lam = json.load(open(RAIZ / "web/data/laminas/vectorizadas.geojson", encoding="utf-8"))
to_m = Transformer.from_crs(4326, 32718, always_xy=True).transform


def geo(zonas):
    return unary_union([transform(to_m, shape(f["geometry"]).buffer(0)) for f in g["features"]
                        if f["properties"].get("ZONA") in zonas])


def lam_u(clases):
    return unary_union([transform(to_m, shape(f["geometry"]).buffer(0)) for f in lam["features"]
                        if f["properties"]["comuna"] == "ANGOL" and f["properties"]["clase"] in clases])


for zonas in (["AR-2a"], ["AR-2b"], ["AR-2a", "AR-2b"]):
    a = geo(zonas)
    b = lam_u(["AR-2a"])
    fuera = a.difference(b).area
    print(f"GeoIDE {zonas}: {a.area / 1e4:.2f} ha; fuera de las láminas AR-2a del visor: {fuera / 1e4:.2f} ha ({100 * fuera / a.area:.1f} %)")
a = geo(["AR-2a"])
print(f"CONTROL AR-2a contra sí misma: {100 * a.difference(a).area / a.area:.1f} % fuera (debe ser 0); contra vacío: {100 * a.difference(lam_u(['__nada__'])).area / a.area:.1f} % (debe ser 100)")
b10 = lam_u(["AR-2a"]).buffer(10)
print(f"AR-2a GeoIDE fuera de las láminas ENSANCHADAS 10 m (descuenta el error de borde ~8 m): {a.difference(b10).area / 1e4:.2f} ha ({100 * a.difference(b10).area / a.area:.1f} %)")
print(f"visor AR-2a: {lam_u(['AR-2a']).area / 1e4:.2f} ha")
