import json,sys,io,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import explain_validity
R=Path(__file__).resolve().parents[2]
h=json.loads((R/"web/data/sar/huella-observada.geojson").read_text(encoding="utf-8"))
c=json.loads((R/"web/data/sar/cobertura-sar.geojson").read_text(encoding="utf-8"))
idx=json.loads((R/"web/data/sar/indice.json").read_text(encoding="utf-8"))
import math
def area_m2(g):
    # equal-area aprox: proyeccion cilindrica equivalente local
    from pyproj import Geod
    geod=Geod(ellps="WGS84")
    return abs(geod.geometry_area_perimeter(g)[0])
F=h["features"]
print("huella features:",len(F),"cobertura:",len(c["features"]))
print("indice resumen:",idx["resumen"])
inv=[i for i,f in enumerate(F) if not shape(f["geometry"]).is_valid]
invc=[i for i,f in enumerate(c["features"]) if not shape(f["geometry"]).is_valid]
print(f"[506] huella invalidos={len(inv)}/{len(F)}  cobertura invalidos={len(invc)}/{len(c['features'])}")
if inv: print("     ejemplo:",inv[0],explain_validity(shape(F[inv[0]]['geometry'])))
sumprop=sum(f["properties"]["hectareas"] for f in F)
print(f"[505] suma de la propiedad 'hectareas' de los poligonos = {sumprop:,.1f} ha")
print(f"      indice.resumen.hectareas = {idx['resumen']['hectareas']:,.1f} ha (suma por track)")
geos=[shape(f["geometry"]).buffer(0) for f in F]
u=unary_union(geos)
ua=area_m2(u)/1e4
print(f"      UNION geodesica de los 1075 poligonos = {ua:,.1f} ha")
print(f"      solape entre tracks = {sumprop-ua:,.1f} ha ({100*(sumprop-ua)/sumprop:.1f} % de la suma)")
print("      por track:",collections.Counter(f["properties"].get("track") for f in F))
# area por track union
for t in sorted({f["properties"].get("track") for f in F}):
    gs=[geos[i] for i,f in enumerate(F) if f["properties"].get("track")==t]
    print(f"        {t}: {len(gs)} pol, suma prop {sum(f['properties']['hectareas'] for f in F if f['properties'].get('track')==t):,.1f} ha, union {area_m2(unary_union(gs))/1e4:,.1f} ha")
