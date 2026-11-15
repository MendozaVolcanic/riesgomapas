"""fB_angol_residuo_vs_geoide.py: descompone lo que GeoIDE AR-2a tiene y nuestros 54 AR-2a no (G menos N), y lo que tenemos
y GeoIDE no (N menos G), para decir DE QUE ESTA HECHA la diferencia: huecos interiores, franjas de borde, o piezas lejanas.

LAS DOS PREGUNTAS DEL INSTRUMENTO
(1) Si la descomposicion estuviera rota, fallaria?  --control: N := G menos 3 huecos cuadrados de 30x30 m puestos adentro
    de G y menos una franja de 6 m pegada al borde de un lado; la medida debe reportar >=3 huecos interiores de ~900 m2
    y que el resto cae en franja de borde <= 8 m.
(2) Si el instrumento estuviera muerto (todo cero), se veria distinto?  Si: el control da 0 huecos.

Categorias de G\\N por pieza conexa: 'hueco' (la pieza no toca el borde exterior de G), 'borde<=u' (todos sus puntos a <= u m del borde
de N), 'chica' (< 2000 m2, el area_minima_m2 de config/laminas.yaml), 'otra'.
"""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from shapely.geometry import box
from shapely.ops import unary_union
from shapely import affinity
from fB_angol_geometria_vs_geoide import geoide_angol, laminas


def dmax_a(p, N):
    """distancia maxima de los puntos del borde de p a N (dirigida: p hacia N, no simetrica)."""
    from shapely import segmentize
    from shapely.geometry import Point
    b = segmentize(p.exterior, 2.0)
    return max(N.distance(Point(c)) for c in b.coords)


def descomponer(N, G, u=8.3, amin=2000.0):
    piezas = G.difference(N)
    piezas = list(piezas.geoms) if hasattr(piezas, "geoms") else ([piezas] if not piezas.is_empty else [])
    cat = {"hueco_interior": [0, 0.0], "franja_borde": [0, 0.0], "pieza_chica": [0, 0.0], "otra": [0, 0.0]}
    Nb = N.boundary
    Gb = G.boundary
    for p in piezas:
        a = p.area
        if p.exterior.distance(Gb) > 0.5:
            k = "hueco_interior"
        elif a < amin:
            k = "pieza_chica"
        elif dmax_a(p, N) <= u + 0.5:
            k = "franja_borde"
        else:
            k = "otra"
        cat[k][0] += 1
        cat[k][1] += a
    return cat, len(piezas)


def control():
    G = unary_union([x[2] for x in geoide_angol() if x[0] == "AR-2a" and x[2].area > 1e5])
    core = G.buffer(-60)
    big = max(core.geoms, key=lambda q: q.area) if hasattr(core, "geoms") else core
    c = big.representative_point()
    cand = [box(c.x + dx, c.y + dy, c.x + dx + 30, c.y + dy + 30) for dx in (-60, 0, 60) for dy in (-60, 0, 60)]
    huecos = [h for h in cand if G.buffer(-20).contains(h)][:3]
    assert len(huecos) == 3, "no se pudieron colocar 3 huecos interiores"
    print("huecos colocados:", len(huecos))
    N = G.difference(unary_union(huecos))
    cat, n = descomponer(N, G)
    ok = cat["hueco_interior"][0] >= 3 and abs(cat["hueco_interior"][1] - 2700) < 400
    print("CONTROL 3 huecos de 30x30 (2700 m2): hueco_interior =", cat["hueco_interior"], "OK" if ok else "FALLA")
    # franja: se le quita a G una banda vertical de 6 m en el borde occidental de su caja (pieza pegada al borde de G y a <= 6 m de N)
    x0, y0, x1, y1 = G.bounds
    N2 = G.difference(box(x0 - 1, y0 - 1, x0 + 6, y1 + 1))
    cat2, n2 = descomponer(N2, G, amin=1.0)
    ok2 = cat2["franja_borde"][1] > 0.8 * (G.area - N2.area)
    print("CONTROL franja de 6 m: franja_borde ha =", round(cat2["franja_borde"][1] / 1e4, 2), "de", round((G.area - N2.area) / 1e4, 2), "ha", "OK" if ok2 else "FALLA")
    cat0, n0 = descomponer(G, G)
    ok3 = n0 == 0
    print("CONTROL identidad: piezas", n0, "OK" if ok3 else "FALLA")
    return ok and ok2 and ok3


if __name__ == "__main__":
    if "--control" in sys.argv:
        sys.exit(0 if control() else 1)
    g = geoide_angol()
    G = unary_union([x[2] for x in g if x[0] == "AR-2a"])
    N = unary_union([x[4] for x in laminas() if x[0] == "AR-2a"])
    for u in (4.6, 8.3):
        cat, n = descomponer(N, G, u)
        print(f"G menos N (u={u}): {n} piezas, total {G.difference(N).area / 1e4:.2f} ha")
        for k, (m, a) in cat.items():
            print(f"   {k:15s} {m:4d} piezas {a / 1e4:7.2f} ha")
    d2 = N.difference(G)
    print(f"N menos G: {d2.area / 1e4:.2f} ha; a <=8,3 m de G: {d2.intersection(G.buffer(8.3)).area / 1e4:.2f} ha; a <=25 m: {d2.intersection(G.buffer(25)).area / 1e4:.2f} ha")
    # G\N: distribucion de area por distancia al borde de N
    gm = G.difference(N)
    for r in (4.6, 8.3, 16.6, 25, 50):
        print(f"   G menos N dentro de {r} m de N: {gm.intersection(N.buffer(r)).area / gm.area:.2f}")
    # cuantas piezas de G\N son grandes
    ps = list(gm.geoms) if hasattr(gm, "geoms") else [gm]
    ps.sort(key=lambda p: -p.area)
    print("   10 piezas mayores (ha):", [round(p.area / 1e4, 2) for p in ps[:10]], "| n piezas:", len(ps), "| ha en piezas <2000 m2:", round(sum(p.area for p in ps if p.area < 2000) / 1e4, 2))
