"""¿Los polígonos SAR inválidos (anillos que se tocan a sí mismos) hacen que el
punto-en-polígono del visor responda al revés?

Se porta `dentroAnillo`/`poligonosQueContienen` de web/app.js a Python tal
cual, y para cada polígono publicado en web/data/sar/huella-observada.geojson
se evalúa en una grilla de puntos (centros de píxel de la rejilla SAR, más los
puntos desplazados un cuarto de píxel) contra shapely.make_valid().contains().

Preguntas del instrumento: (1) si el ray-casting fallara en vértices
compartidos, habría desacuerdos con shapely y se listan; (2) si el instrumento
estuviera muerto, el control positivo (una pajarita, donde el ray-casting y el
área firmada difieren por construcción) no daría el desacuerdo esperado.
Sólo lee.
"""
import io, json, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
from shapely.geometry import shape, Point, Polygon
from shapely.validation import make_valid

def dentro_anillo(lon, lat, anillo):
    dentro = False
    j = len(anillo) - 1
    for i in range(len(anillo)):
        xi, yi = anillo[i]; xj, yj = anillo[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            dentro = not dentro
        j = i
    return dentro

def contiene(lon, lat, geom):
    polis = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return any(dentro_anillo(lon, lat, p[0]) and not any(dentro_anillo(lon, lat, h) for h in p[1:]) for p in polis)

# control positivo: pajarita — shapely make_valid la parte en dos triángulos; el
# ray-casting even-odd también debe decir "dentro" en cada lóbulo.
paj = {"type": "Polygon", "coordinates": [[(0,0),(2,2),(2,0),(0,2),(0,0)]]}
mv = make_valid(shape(paj))
ok = contiene(0.5,1.0,paj) == mv.contains(Point(0.5,1.0)) == True and contiene(0.9,0.05,paj) is False and not mv.contains(Point(0.9,0.05))
print("control pajarita: lóbulo dentro en ambos =", contiene(0.5,1.0,paj), mv.contains(Point(0.5,1.0)), "; punto fuera de ambos lóbulos (0,9, 0,05) =", not contiene(0.9,0.05,paj), not mv.contains(Point(0.9,0.05)), "→", "OK" if ok else "FALLÓ")
if not ok: sys.exit(2)

H = json.load(open("web/data/sar/huella-observada.geojson", encoding="utf-8"))["features"]
res = 0.00045; x0, y0 = -73.7, -37.35
desac = 0; evaluados = 0; polis_con_desac = []
for i, f in enumerate(H):
    g = shape(f["geometry"])
    if g.is_valid: continue
    gv = make_valid(g)
    b = g.bounds
    c0, c1 = int((b[0]-x0)/res)-1, int((b[2]-x0)/res)+2
    r0, r1 = int((y0-b[3])/res)-1, int((y0-b[1])/res)+2
    n_d = 0
    for r in range(r0, r1):
        for c in range(c0, c1):
            for dx, dy in ((0.5,0.5),(0.25,0.25),(0.75,0.75),(0.25,0.75)):
                lon = x0 + (c+dx)*res; lat = y0 - (r+dy)*res
                a = contiene(lon, lat, f["geometry"]); s = gv.contains(Point(lon, lat))
                evaluados += 1
                if a != s: n_d += 1
    if n_d: polis_con_desac.append((i, n_d)); desac += n_d
print(f"polígonos inválidos evaluados: {sum(1 for f in H if not shape(f['geometry']).is_valid)} · puntos evaluados: {evaluados:,} · desacuerdos visor↔shapely: {desac} en {len(polis_con_desac)} polígonos")
print("primeros:", polis_con_desac[:10])
