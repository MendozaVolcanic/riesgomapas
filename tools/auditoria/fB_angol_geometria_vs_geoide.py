"""fB_angol_geometria_vs_geoide.py: geometria contra geometria entre los AR-2a de GeoIDE (PRC_Angol_Area_de_riesgo, capa 29)
y los 54 AR-2a que el proyecto derivo de las dos laminas del PRC de Angol (web/data/laminas/vectorizadas.geojson, clase AR-2a).
Todo en EPSG:32718 (la zona UTM de Angol; la capa 29 se bajo ademas con outSR=32718 para no pasar por 32719).

LAS DOS PREGUNTAS DEL INSTRUMENTO
(1) Si lo que mide (la coincidencia entre las dos geometrias) estuviera completamente roto, esta medicion fallaria?
    --control fabrica el defecto: toma los AR-2a de GeoIDE como si fueran "nuestra capa" y (a) identidad: IoU=1,
    traslacion optima (0,0), 100 % explicado; (b) la corre (20,-10) m: la traslacion optima debe salir (-20,+10) +-1 m,
    el IoU baja, y la fraccion "explicada por la incertidumbre de 8,3 m" debe ser baja; (c) la corre 3 m: la fraccion
    explicada debe ser ~1; (d) borra la mitad de los poligonos: la cobertura de GeoIDE debe bajar a ~la mitad.
(2) Si el instrumento estuviera muerto (devolviera siempre el mismo numero), el resultado se veria distinto?  Si: los
    controles (a)-(d) dan resultados distintos entre si.

Uso: python -I fB_angol_geometria_vs_geoide.py [--control] [--json salida.json]
"""
import json, sys, math, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import numpy as np
from pyproj import Transformer
from shapely.geometry import shape, Point, MultiPoint
from shapely.ops import unary_union, transform
from shapely import affinity, hausdorff_distance
from fB_geoide_geom import anillos_a_shapely, RAW

P = pathlib.Path(r"C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas")
T = Transformer.from_crs(4326, 32718, always_xy=True)


def geoide_angol():
    d = json.loads((RAW / "capa_29_wkid32718.json").read_text(encoding="utf-8"))
    return [(f["attributes"]["ZONA"], f["attributes"]["OBJECTID"], anillos_a_shapely(f["geometry"]["rings"])) for f in d["features"]]


def laminas():
    d = json.loads((P / "web/data/laminas/vectorizadas.geojson").read_text(encoding="utf-8"))
    out = []
    for f in d["features"]:
        p = f["properties"]
        out.append((p["clase"], p["origen_lamina"], p.get("incertidumbre_borde_m"), p.get("hectareas"), transform(T.transform, shape(f["geometry"]))))
    return out


def iou(a, b):
    u = a.union(b).area
    return a.intersection(b).area / u if u else float("nan")


def mejor_traslacion(n, g, rango=100, paso=5):
    """traslacion (dx,dy) de n que maximiza el IoU con g; busqueda gruesa y refinada. Devuelve (dx,dy,iou)."""
    mejor = (0, 0, iou(n, g))
    for dx in range(-rango, rango + 1, paso):
        for dy in range(-rango, rango + 1, paso):
            v = iou(affinity.translate(n, dx, dy), g)
            if v > mejor[2]:
                mejor = (dx, dy, v)
    cx, cy = mejor[0], mejor[1]
    for dx in np.arange(cx - paso, cx + paso + 0.01, 1.0):
        for dy in np.arange(cy - paso, cy + paso + 0.01, 1.0):
            v = iou(affinity.translate(n, float(dx), float(dy)), g)
            if v > mejor[2]:
                mejor = (float(dx), float(dy), v)
    return mejor


def fraccion_explicada(n, g, u):
    """Que fraccion del area de la diferencia simetrica N xor G cae a <= u metros del borde de la otra geometria
    (es decir, la que cabe en un corrimiento de borde de u metros)."""
    dif = n.symmetric_difference(g)
    if dif.area == 0:
        return 1.0
    banda = unary_union([g.boundary.buffer(u), n.boundary.buffer(u)])
    # lo que esta en N pero no en G debe estar cerca del borde de G; y viceversa
    d1 = n.difference(g).intersection(g.boundary.buffer(u))
    d2 = g.difference(n).intersection(n.boundary.buffer(u))
    return (d1.area + d2.area) / dif.area


def p95_borde(a, b, paso=2.0):
    """percentil 95 de la distancia de los puntos del borde de a al borde de b (m); y el maximo (aprox. Hausdorff)."""
    bd = a.boundary
    L = bd.length
    ds = []
    bb = b.boundary
    for s in np.arange(0, L, paso):
        ds.append(bb.distance(bd.interpolate(float(s))))
    ds = np.array(ds)
    return float(np.percentile(ds, 95)), float(ds.max())


def medir(n_polys, g2a, u_list):
    """n_polys: lista de (origen, u, geom). g2a: geometria union de AR-2a de GeoIDE."""
    N = unary_union([x[2] for x in n_polys])
    G = g2a
    r = {"area_N_ha": N.area / 1e4, "area_G_ha": G.area / 1e4, "iou": iou(N, G), "inter_ha": N.intersection(G).area / 1e4,
         "N_dentro_de_G": N.intersection(G).area / N.area if N.area else 0, "G_cubierto_por_N": N.intersection(G).area / G.area if G.area else 0}
    r["centroide_N"] = (N.centroid.x, N.centroid.y)
    r["centroide_G"] = (G.centroid.x, G.centroid.y)
    r["dist_centroides_m"] = N.centroid.distance(G.centroid)
    r["explicada"] = {str(u): fraccion_explicada(N, G, u) for u in u_list}
    return r


def control():
    ok = True
    g = geoide_angol()
    G = unary_union([x[2] for x in g if x[0] == "AR-2a"])
    polys = [x for x in g if x[0] == "AR-2a"]
    base = [("ctl", 8.3, x[2]) for x in polys]
    r0 = medir(base, G, [8.3])
    t0 = mejor_traslacion(unary_union([x[2] for x in base]), G, rango=30, paso=5)
    c = abs(r0["iou"] - 1) < 1e-9 and (t0[0], t0[1]) == (0, 0) and r0["explicada"]["8.3"] == 1.0
    print("CONTROL (a) identidad: IoU", round(r0["iou"], 6), "traslacion", t0[:2], "explicada", r0["explicada"]["8.3"], "OK" if c else "FALLA"); ok &= c
    sh = [("ctl", 8.3, affinity.translate(x[2], 20, -10)) for x in polys]
    Ns = unary_union([x[2] for x in sh])
    r1 = medir(sh, G, [8.3])
    t1 = mejor_traslacion(Ns, G, rango=40, paso=5)
    c = abs(t1[0] + 20) <= 1 and abs(t1[1] - 10) <= 1 and r1["iou"] < 0.9 and r1["explicada"]["8.3"] < 0.6 and t1[2] > r1["iou"]
    print("CONTROL (b) corrido (20,-10) m: IoU", round(r1["iou"], 3), "| traslacion optima", t1[:2], "(esperada -20,+10) IoU optimo", round(t1[2], 3), "| explicada u=8,3:", round(r1["explicada"]["8.3"], 3), "OK" if c else "FALLA"); ok &= c
    sh3 = [("ctl", 8.3, affinity.translate(x[2], 3, 0)) for x in polys]
    r3 = medir(sh3, G, [8.3])
    c = r3["explicada"]["8.3"] > 0.95
    print("CONTROL (c) corrido 3 m: IoU", round(r3["iou"], 3), "explicada u=8,3:", round(r3["explicada"]["8.3"], 3), "OK" if c else "FALLA"); ok &= c
    mit = base[::2]
    r2 = medir(mit, G, [8.3])
    c = r2["G_cubierto_por_N"] < 0.8 * r0["G_cubierto_por_N"]
    print("CONTROL (d) mitad de los poligonos: cobertura de GeoIDE", round(r0["G_cubierto_por_N"], 3), "->", round(r2["G_cubierto_por_N"], 3), "OK" if c else "FALLA"); ok &= c
    return ok


if __name__ == "__main__":
    if "--control" in sys.argv:
        sys.exit(0 if control() else 1)
    g = geoide_angol()
    L = laminas()
    res = {}
    por_zona = collections.defaultdict(list)
    for z, oid, geom in g:
        por_zona[z].append((oid, geom))
    Gz = {z: unary_union([x[1] for x in v]) for z, v in por_zona.items()}
    print("GeoIDE capa 29 por ZONA (features, ha):", {z: (len(v), round(Gz[z].area / 1e4, 1)) for z, v in por_zona.items()})
    ar2a = [(x[1], x[2], x[4]) for x in L if x[0] == "AR-2a"]
    print("Nuestros AR-2a:", len(ar2a), "poligonos; por lamina:", collections.Counter(x[0] for x in ar2a), "u:", sorted({x[1] for x in ar2a}))
    N = unary_union([x[2] for x in ar2a])
    res["N_ha_publicada_suma_campo_hectareas"] = sum((x[3] or 0) for x in L if x[0] == "AR-2a")
    res["N_ha_geometria"] = N.area / 1e4
    ref = {"AR-2a": Gz["AR-2a"], "AR-2b": Gz["AR-2b"], "AR-2a+2b": unary_union([Gz["AR-2a"], Gz["AR-2b"]]),
           "AR-1a+1b+1c": unary_union([Gz["AR-1a"], Gz["AR-1b"], Gz["AR-1c"]]), "todo AR (81)": unary_union(list(Gz.values()))}
    print("\n== Global: nuestra union de AR-2a contra cada referencia de GeoIDE ==")
    for k, G in ref.items():
        r = medir(ar2a, G, [4.6, 8.3, 16.6, 24.9])
        print(f"{k:14s} G={r['area_G_ha']:7.2f} ha N={r['area_N_ha']:7.2f} ha IoU={r['iou']:.3f} inter={r['inter_ha']:6.2f} ha | N dentro de G={r['N_dentro_de_G']:.3f} G cubierto por N={r['G_cubierto_por_N']:.3f} | dist centroides={r['dist_centroides_m']:.1f} m | explicada u=4,6/8,3/16,6/24,9: " + "/".join(f"{v:.2f}" for v in r['explicada'].values()))
        res["global_" + k] = r
    G2a = ref["AR-2a"]
    # fraccion de N en cada zona de GeoIDE (donde cae realmente)
    print("\n== Donde cae el area de nuestros AR-2a (fraccion de N) ==")
    for z in ("AR-2a", "AR-2b", "AR-1a", "AR-1b", "AR-1c"):
        print(f"  dentro de {z}: {N.intersection(Gz[z]).area / N.area:.3f}")
    allG = ref["todo AR (81)"]
    print(f"  fuera de todo AR de GeoIDE: {N.difference(allG).area / N.area:.3f}")
    # por lamina
    print("\n== Por lamina ==")
    for lam in ("angol-prc-ar2a-lamina1", "angol-prc-ar2a-lamina2"):
        sub = [x for x in ar2a if x[0] == lam]
        Nl = unary_union([x[2] for x in sub])
        # GeoIDE restringido a la caja de la lamina (para no penalizar a una lamina por lo que cubre la otra)
        caja = Nl.convex_hull.buffer(300)
        Gl = G2a.intersection(caja)
        u = sub[0][1]
        r = medir(sub, Gl, [u, 2 * u, 3 * u])
        t = mejor_traslacion(Nl, Gl, rango=100, paso=5)
        print(f"{lam}: n={len(sub)} u={u} m N={r['area_N_ha']:.2f} ha G(en su caja)={r['area_G_ha']:.2f} ha IoU={r['iou']:.3f} | traslacion que maximiza IoU: ({t[0]:.0f},{t[1]:.0f}) m IoU={t[2]:.3f} | explicada u,2u,3u: " + "/".join(f"{v:.2f}" for v in r['explicada'].values()))
        res["lamina_" + lam] = {"n": len(sub), "u": u, "iou": r["iou"], "traslacion": t, "area_N_ha": r["area_N_ha"], "area_G_ha": r["area_G_ha"], "explicada": r["explicada"]}
    t = mejor_traslacion(N, G2a, rango=100, paso=5)
    print(f"\nGlobal: traslacion que maximiza el IoU: ({t[0]:.0f},{t[1]:.0f}) m -> IoU {t[2]:.3f} (sin trasladar: {iou(N, G2a):.3f})")
    res["traslacion_global"] = t
    # por poligono nuestro
    print("\n== Por poligono nuestro (54) contra AR-2a de GeoIDE ==")
    filas = []
    for i, (lam, u, geom) in enumerate(ar2a):
        inter = geom.intersection(G2a).area
        frac = inter / geom.area
        # feature GeoIDE de mayor solape
        best = max(por_zona["AR-2a"], key=lambda x: geom.intersection(x[1]).area)
        gb = best[1]
        sol = geom.intersection(gb).area
        d_cen = geom.centroid.distance(gb.centroid) if sol > 0 else geom.distance(G2a)
        d_near = geom.distance(G2a)
        hd = hausdorff_distance(geom, gb, densify=0.05) if sol > 0 else float("nan")
        p95 = p95_borde(geom, gb)[0] if sol > 0 else float("nan")
        filas.append({"i": i, "lamina": lam.split("-")[-1], "u": u, "area_m2": geom.area, "dentro_AR2a": frac, "dist_a_AR2a_m": d_near,
                      "oid_gb": best[0] if sol > 0 else None, "iou_con_feature": iou(geom, gb) if sol > 0 else 0.0, "d_centroides_m": d_cen, "hausdorff_m": hd, "p95_borde_m": p95,
                      "dentro_AR2b": geom.intersection(Gz["AR-2b"]).area / geom.area,
                      "dentro_AR1": geom.intersection(unary_union([Gz["AR-1a"], Gz["AR-1b"], Gz["AR-1c"]])).area / geom.area})
    ninguno = [f for f in filas if f["dentro_AR2a"] == 0]
    print("poligonos con 0 % dentro de AR-2a:", len(ninguno), "de", len(filas))
    print("poligonos con >=50 % dentro de AR-2a:", sum(1 for f in filas if f["dentro_AR2a"] >= .5))
    print("poligonos con >=90 % dentro de AR-2a:", sum(1 for f in filas if f["dentro_AR2a"] >= .9))
    print("mediana fraccion dentro:", round(float(np.median([f["dentro_AR2a"] for f in filas])), 3))
    ct = [f for f in filas if f["oid_gb"] is not None]
    print("con solape (n=%d): mediana IoU con su feature:" % len(ct), round(float(np.median([f["iou_con_feature"] for f in ct])), 3) if ct else None,
          "| mediana dist centroides:", round(float(np.median([f["d_centroides_m"] for f in ct])), 1) if ct else None,
          "| mediana Hausdorff:", round(float(np.nanmedian([f["hausdorff_m"] for f in ct])), 1) if ct else None,
          "| mediana p95 borde:", round(float(np.nanmedian([f["p95_borde_m"] for f in ct])), 1) if ct else None)
    sin = [f for f in filas if f["oid_gb"] is None]
    print("sin ningun solape con AR-2a:", len(sin), "distancia mediana al AR-2a mas cercano:", round(float(np.median([f['dist_a_AR2a_m'] for f in sin])), 1) if sin else None)
    res["por_poligono"] = filas
    # por feature GeoIDE: cuanto de el cubren los nuestros
    print("\n== Por feature de GeoIDE AR-2a (10) ==")
    gf = []
    for oid, geom in por_zona["AR-2a"]:
        cub = N.intersection(geom).area / geom.area
        n_in = sum(1 for x in ar2a if x[2].intersects(geom))
        iu = iou(N.intersection(geom.buffer(100)), geom)
        gf.append({"oid": oid, "ha": geom.area / 1e4, "cubierto_por_N": cub, "n_nuestros_que_lo_tocan": n_in, "iou_local": iu})
        print(f"  OBJECTID {oid}: {geom.area/1e4:6.2f} ha, cubierto por N={cub:.3f}, nuestros que lo tocan={n_in}, IoU local={iu:.3f}")
    res["por_feature_geoide"] = gf
    # reproducir el IoU 0,20 del estudio 2013
    est = [x for x in L if x[0] in ("Alto", "Medio") and x[1] == "angol-peligro-inundacion-2013"]
    E_alto = unary_union([x[4] for x in est if x[0] == "Alto"])
    E_med = unary_union([x[4] for x in est if x[0] == "Medio"])
    E = unary_union([E_alto, E_med])
    print("\n== Contraste con el estudio de peligro 2013 (clasificador independiente, las manchas Alto/Medio) ==")
    print(f"estudio 2013: n={len(est)} union={E.area/1e4:.1f} ha (Alto {E_alto.area/1e4:.1f}, Medio {E_med.area/1e4:.1f})")
    for nombre, A in (("nuestros AR-2a", N), ("GeoIDE AR-2a", G2a), ("GeoIDE AR-2a+2b", ref["AR-2a+2b"])):
        for nm, E_ in (("Alto", E_alto), ("Medio", E_med), ("Alto+Medio", E)):
            print(f"  {nombre:16s} vs estudio2013 {nm:10s}: IoU={iou(A, E_):.3f}  A dentro de E={A.intersection(E_).area / A.area:.3f}  E cubierto por A={A.intersection(E_).area / E_.area:.3f}")
    res["estudio2013_ha"] = E.area / 1e4
    if "--json" in sys.argv:
        out = pathlib.Path(sys.argv[sys.argv.index("--json") + 1])
        out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
