"""507/508/503: altitud de la huella publicada y enriquecimiento sobre la CAPA PUBLICADA."""
import json,sys,io,math,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
from pathlib import Path
import numpy as np, rasterio
from shapely.geometry import shape, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
R=Path(__file__).resolve().parents[2]
H=json.loads((R/"web/data/sar/huella-observada.geojson").read_text(encoding="utf-8"))["features"]
C=json.loads((R/"web/data/sar/cobertura-sar.geojson").read_text(encoding="utf-8"))["features"]
P=json.loads((R/"web/data/puntos-criticos-inundacion.geojson").read_text(encoding="utf-8"))["features"]
ds=rasterio.open(R/"data/processed/sar/2026-07-30_sistema_frontal/terreno.tif")
dem=ds.read(1); pend=ds.read(2)
geos=[shape(f["geometry"]).buffer(0) for f in H]
cent=[g.representative_point() for g in geos]
def alt(pt):
    r,c=ds.index(pt.x,pt.y)
    if 0<=r<ds.height and 0<=c<ds.width: return float(dem[r,c]), float(pend[r,c])
    return float("nan"),float("nan")
alts=[alt(p) for p in cent]
ha=[f["properties"]["hectareas"] for f in H]
print("=== [507/508] altitud del punto representativo de cada polígono de la huella ===")
bins=[(-5,2),(2,5),(5,20),(20,100),(100,300),(300,700),(700,1000),(1000,1300)]
for lo,hi in bins:
    sel=[i for i,(a,_) in enumerate(alts) if not math.isnan(a) and lo<=a<hi]
    print(f"  {lo:>5}–{hi:<5} m : {len(sel):>4} pol · {sum(ha[i] for i in sel):8.1f} ha")
nan=[i for i,(a,_) in enumerate(alts) if math.isnan(a)]
print("  sin DEM:",len(nan))
b1=[i for i,(a,_) in enumerate(alts) if not math.isnan(a) and a<=2]
print(f"\n[507] polígonos con altitud ≤ 2 m: {len(b1)} · {sum(ha[i] for i in b1):.1f} ha "
      f"({100*sum(ha[i] for i in b1)/sum(ha):.1f} % de la huella)")
print("      tracks:",collections.Counter(H[i]['properties'].get('track') for i in b1))
print("      lon/lat extremos:", min(cent[i].x for i in b1),max(cent[i].x for i in b1),
      min(cent[i].y for i in b1),max(cent[i].y for i in b1))
alto=[i for i,(a,_) in enumerate(alts) if not math.isnan(a) and a>=1000]
print(f"\n[508] polígonos con altitud ≥ 1000 m: {len(alto)} · {sum(ha[i] for i in alto):.1f} ha")
for i in sorted(alto,key=lambda i:-ha[i])[:15]:
    print(f"   #{i} {H[i]['properties'].get('track')} alt={alts[i][0]:.0f} m pend={alts[i][1]:.1f}° {ha[i]:.1f} ha en ({cent[i].x:.4f},{cent[i].y:.4f})")
alto7=[i for i,(a,_) in enumerate(alts) if not math.isnan(a) and a>=700]
print(f"  ≥700 m: {len(alto7)} pol · {sum(ha[i] for i in alto7):.1f} ha")

print("\n=== [503] enriquecimiento SOBRE LA CAPA PUBLICADA ===")
cob=unary_union([shape(f["geometry"]).buffer(0) for f in C])
tree=STRtree(geos)
pts=[Point(*f["geometry"]["coordinates"]) for f in P]
obs=[p for p in pts if cob.contains(p)]
print(f"  puntos SENAPRED hídricos dentro de la cobertura: {len(obs)} de {len(pts)}")
rng=np.random.default_rng(20260906)
o,s,e,n=cob.bounds
azar=[]
while len(azar)<len(obs)*20:
    x=rng.uniform(o,e); y=rng.uniform(s,n); q=Point(x,y)
    if cob.contains(q): azar.append(q)
def cerca(p,r_m):
    dlat=r_m/111320.0; dlon=dlat/math.cos(math.radians(p.y))
    from shapely.geometry import box
    bb=box(p.x-dlon,p.y-dlat,p.x+dlon,p.y+dlat)
    for j in tree.query(bb):
        g=geos[j]
        d=g.distance(p)
        if d*111320.0<=r_m*1.0:  # aprox; se refina abajo
            # distancia real en metros aproximada con factor de latitud
            import shapely.ops as so
            return True
    return False
print("  radio    SENAPRED        azar           enriquecimiento")
for r in (100,200,300,500,1000):
    a=sum(1 for p in obs if cerca(p,r)); b=sum(1 for p in azar if cerca(p,r))
    po=100*a/len(obs); pa=100*b/len(azar)
    print(f"  {r:>5} m  {a:>4}/{len(obs)} ({po:5.2f} %)  {b:>5}/{len(azar)} ({pa:5.2f} %)  "
          + (f"×{po/pa:.2f}" if pa>0 else "(azar 0)"))
frac=100*sum(g.area for g in geos)/cob.area
print(f"  la huella cubre el {frac:.2f} % del área de cobertura publicada")
