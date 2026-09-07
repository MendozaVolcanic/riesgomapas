"""Verificador independiente de la capa A publicada (areas-riesgo-inundacion.geojson)."""
import json, collections, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
from shapely.geometry import shape
R = Path(__file__).resolve().parents[2]
pub = json.loads((R/"web/data/areas-riesgo-inundacion.geojson").read_text(encoding="utf-8"))
uni = json.loads((R/"data/processed/areas_riesgo_prc_araucania.geojson").read_text(encoding="utf-8"))
F = pub["features"]
print(f"publicados={len(F)}  universo={len(uni['features'])}")
print("meta.capa_evidencia =", pub.get("procedencia",{}).get("capa_evidencia"))

# --- 501: QUEBRAD -> fluvial vs clasificacion MINVU
print("\n[501] tipo_hidrico=fluvial cuyo texto de clasificacion NO dice INUND:")
n=0
for i,f in enumerate(F):
    p=f["properties"]
    if p.get("tipo_hidrico")=="fluvial" and "INUND" not in (p.get("clasificacion") or "").upper():
        n+=1
        print(f"  #{i} {p.get('comuna')} clas={p.get('clasificacion')!r} nombre={p.get('nombre')!r} zona={p.get('zona')!r}")
print(f"  total={n}")

# --- 502: duplicados exactos por WKT
print("\n[502] duplicados por geometria identica (WKT exacto):")
wkt=collections.defaultdict(list)
for i,f in enumerate(F): wkt[shape(f["geometry"]).wkt].append(i)
d=[v for v in wkt.values() if len(v)>1]
for v in d:
    for i in v:
        p=F[i]["properties"]; print(f"  #{i} {p.get('comuna')} {p.get('clasificacion')!r} nombre={p.get('nombre')!r} tipo={p.get('tipo_hidrico')}")
    print("  ---")
print(f"  grupos duplicados={len(d)}")

# --- 504: anio
print("\n[504] polígonos sin anio:")
sin=[(i,F[i]['properties'].get('comuna')) for i in range(len(F)) if not F[i]['properties'].get('anio')]
print(" ", collections.Counter(c for _,c in sin), "total", len(sin))
print("  Saavedra publicados:", sum(1 for f in F if f['properties'].get('comuna')=='Saavedra'),
      "con anio:", sum(1 for f in F if f['properties'].get('comuna')=='Saavedra' and f['properties'].get('anio')))
print("  comuna_fuente de esos:", {f['properties'].get('comuna_fuente') for f in F if f['properties'].get('comuna')=='Saavedra'})
print("  universo sin anio:", collections.Counter(f['properties'].get('comuna') for f in uni['features'] if not f['properties'].get('anio')))

# --- 509: contencion Tolten
print("\n[509] contencion entre poligonos publicados (mismo comuna):")
geos=[shape(f["geometry"]).buffer(0) for f in F]
for i in range(len(F)):
    for j in range(len(F)):
        if i==j: continue
        if F[i]['properties'].get('comuna')!=F[j]['properties'].get('comuna'): continue
        gi,gj=geos[i],geos[j]
        if gi.area==0: continue
        inter=gi.intersection(gj).area
        if inter/gi.area > 0.98:
            print(f"  #{i} ({F[i]['properties'].get('comuna')} {F[i]['properties'].get('zona')!r} {F[i]['properties'].get('hectareas') if 'hectareas' in F[i]['properties'] else ''}) contenido {100*inter/gi.area:.1f}% en #{j} ({F[j]['properties'].get('zona')!r})")

# --- 511: orientacion de anillos RFC7946
print("\n[511] orientacion de anillos:")
def signed(ring):
    s=0
    for k in range(len(ring)-1):
        x1,y1=ring[k][:2]; x2,y2=ring[k+1][:2]; s+=(x2-x1)*(y2+y1)
    return s
ext_cw=ext_ccw=hole_cw=hole_ccw=0
for f in F:
    g=f["geometry"]; polys=[g["coordinates"]] if g["type"]=="Polygon" else g["coordinates"]
    for poly in polys:
        for r_i,ring in enumerate(poly):
            s=signed(ring)
            if r_i==0:
                if s>0: ext_cw+=1
                else: ext_ccw+=1
            else:
                if s>0: hole_cw+=1
                else: hole_ccw+=1
print(f"  exteriores horarios(cw)={ext_cw} antihorarios(ccw)={ext_ccw}; huecos cw={hole_cw} ccw={hole_ccw}")
print("  RFC7946 exige exterior CCW y hueco CW")

# --- 512 / validez
print("\n[512] validez geometrica:")
from shapely.validation import explain_validity
inv_pub=[(i,explain_validity(shape(f['geometry']))) for i,f in enumerate(F) if not shape(f['geometry']).is_valid]
print("  publicados invalidos:", len(inv_pub), inv_pub[:5])
inv_uni=[(i,F and uni['features'][i]['properties'].get('comuna'),uni['features'][i]['properties'].get('clasificacion'),explain_validity(shape(uni['features'][i]['geometry']))) for i in range(len(uni['features'])) if not shape(uni['features'][i]['geometry']).is_valid]
print("  universo invalidos:", len(inv_uni))
for r in inv_uni[:5]: print("   ", r)

# --- 510: CANAL fuera del filtro hidrico
print("\n[510] universo: clasificaciones con CANAL / AGUA / RIO / ESTERO no publicadas:")
pubset={shape(f['geometry']).wkt for f in F}
for i,f in enumerate(uni['features']):
    p=f['properties']; txt=((p.get('clasificacion') or '')+' '+(p.get('nombre') or '')+' '+(p.get('zona') or '')).upper()
    if any(k in txt for k in ("CANAL","ESTERO","RIO ","RÍO","CAUCE","AGUA","LAGUNA","BORDE")):
        marca = "PUB" if shape(f['geometry']).wkt in pubset else "no-pub"
        print(f"  {marca} #{i} {p.get('comuna')} clas={p.get('clasificacion')!r} nombre={p.get('nombre')!r} tipo={p.get('tipo_hidrico')}")

# --- tipos publicados
print("\n[titulares] tipo_hidrico publicado:", collections.Counter(f['properties'].get('tipo_hidrico') for f in F))
print("[401] estado_tramite presente?:", sum(1 for f in F if 'estado_tramite' in f['properties']), "de", len(F))
print("     claves de properties:", sorted(F[0]['properties'].keys()))
