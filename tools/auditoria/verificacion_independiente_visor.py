"""Instrumento del VERIFICADOR (auditoría 2026-09-06, contexto limpio).

Mide tres cosas sobre las que hay hallazgos provisionales, con código propio y
sin leer los informes de los auditores:

  A. ¿La regla de pertenencia del visor (ray casting par-impar, `dentroAnillo`)
     da la misma respuesta que shapely sobre geometrías inválidas? Se
     reimplementa la función del frontend tal cual está en web/app.js:145-169.
  B. ¿Cuántas posiciones cambian de veredicto al moverse 50 m? (precisión GPS)
  C. ¿Qué tan cerca del borde de un polígono de evidencia quedan los puntos que
     el visor declara «sin registros»?

No modifica nada. Sólo lee web/data/.
"""
import json, math, random, sys
from pathlib import Path
from shapely.geometry import shape, Point
from shapely.validation import make_valid

W = Path(__file__).resolve().parents[2] / "web" / "data"
random.seed(20260906)


def cargar(p):
    try:
        return json.load(open(W / p, encoding="utf-8"))
    except Exception:
        return None


# --- réplica exacta de web/app.js:145-169 -----------------------------------
def dentro_anillo(lon, lat, anillo):
    dentro = False
    j = len(anillo) - 1
    for i in range(len(anillo)):
        xi, yi = anillo[i][0], anillo[i][1]
        xj, yj = anillo[j][0], anillo[j][1]
        if (yi > lat) != (yj > lat) and lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def contiene_visor(lon, lat, feat):
    g = feat["geometry"]
    polis = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    for poli in polis:
        if dentro_anillo(lon, lat, poli[0]) and not any(
                dentro_anillo(lon, lat, h) for h in poli[1:]):
            return True
    return False


def bbox(geom):
    xs, ys = [], []
    def rec(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for x in c: rec(x)
    rec(geom["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def A_ray_vs_shapely():
    print("=== A. ray casting del visor vs shapely (make_valid) ===")
    for nom, ruta in [("gore", "gore/amenaza-inundacion.geojson"),
                      ("sar", "sar/huella-observada.geojson"),
                      ("cobertura-sar", "sar/cobertura-sar.geojson"),
                      ("areas-riesgo", "areas-riesgo-inundacion.geojson"),
                      ("laminas", "laminas/vectorizadas.geojson"),
                      ("jrc", "jrc/rp100.geojson")]:
        fc = cargar(ruta)
        if not fc:
            print(f"  {nom}: SIN DATO (no se pudo leer)"); continue
        disc = 0; probados = 0; invalidos = 0; ej = []
        for f in fc["features"]:
            g = shape(f["geometry"])
            if not g.is_valid:
                invalidos += 1
            gv = make_valid(g)
            w, s, e, n = bbox(f["geometry"])
            for _ in range(40):
                lon = random.uniform(w, e); lat = random.uniform(s, n)
                a = contiene_visor(lon, lat, f)
                b = gv.contains(Point(lon, lat))
                probados += 1
                if a != b:
                    disc += 1
                    if len(ej) < 3: ej.append((round(lon, 5), round(lat, 5), a, b))
        print(f"  {nom}: features={len(fc['features'])} invalidos={invalidos} "
              f"puntos={probados} discrepancias={disc} ({100*disc/max(probados,1):.3f} %)")
        if ej: print(f"      ejemplos (lon,lat,visor,shapely): {ej}")


RADIOS = dict(cercano=300, medio=500, contexto=1500)


def distancia(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1); dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))


def evaluar(lon, lat, D):
    cerca = []
    for f in D["puntos"]["features"]:
        flon, flat = f["geometry"]["coordinates"]
        d = distancia(lat, lon, flat, flon)
        if d <= RADIOS["contexto"]: cerca.append((f, d))
    en = lambda r: [c for c in cerca if c[1] <= r]
    graves = [c for c in en(RADIOS["cercano"]) if c[0]["properties"].get("nivel") in ("Muy Alto", "Alto")]
    sar = any(contiene_visor(lon, lat, f) for f in D["sar"]["features"]) if D["sar"] else False
    areas = any(contiene_visor(lon, lat, f) for f in D["areas"]["features"]) if D["areas"] else False
    if sar: return "alto"
    if areas: return "alto"
    if graves or len(en(RADIOS["cercano"])) >= 3: return "alto"
    if en(RADIOS["medio"]): return "medio"
    if cerca: return "bajo"
    return "sindato"


def B_gps(D, n=400, salto=50):
    print(f"=== B. cambio de veredicto al moverse {salto} m (n={n} posiciones) ===")
    pts = D["puntos"]["features"]
    cambios = 0; pares = 0; ejs = []
    for _ in range(n):
        f = random.choice(pts)
        blon, blat = f["geometry"]["coordinates"]
        # posición sembrada en un anillo de hasta 1200 m del punto crítico
        r = random.uniform(0, 1200); th = random.uniform(0, 2*math.pi)
        dlat = (r*math.sin(th))/111320
        dlon = (r*math.cos(th))/(111320*math.cos(math.radians(blat)))
        lon, lat = blon+dlon, blat+dlat
        v0 = evaluar(lon, lat, D)
        th2 = random.uniform(0, 2*math.pi)
        dlat2 = (salto*math.sin(th2))/111320
        dlon2 = (salto*math.cos(th2))/(111320*math.cos(math.radians(lat)))
        v1 = evaluar(lon+dlon2, lat+dlat2, D)
        pares += 1
        if v0 != v1:
            cambios += 1
            if len(ejs) < 4: ejs.append((round(lon,5), round(lat,5), v0, v1))
    print(f"  {cambios}/{pares} = {100*cambios/pares:.1f} % cambia de veredicto")
    print(f"  ejemplos: {ejs}")


def C_borde(D, n=300):
    print("=== C. distancia al borde más cercano de evidencia, para 'sindato' ===")
    capas = [("areas", D["areas"]), ("laminas", D["laminas"]), ("gore", D["gore"])]
    geoms = {}
    for nom, fc in capas:
        if fc: geoms[nom] = [make_valid(shape(f["geometry"])) for f in fc["features"]]
    cerca_borde = 0; mirados = 0; ejs = []
    pts = D["puntos"]["features"]
    for _ in range(n):
        f = random.choice(pts)
        blon, blat = f["geometry"]["coordinates"]
        r = random.uniform(1500, 6000); th = random.uniform(0, 2*math.pi)
        lat = blat + (r*math.sin(th))/111320
        lon = blon + (r*math.cos(th))/(111320*math.cos(math.radians(blat)))
        if evaluar(lon, lat, D) != "sindato": continue
        mirados += 1
        p = Point(lon, lat)
        dmin = min((g.exterior.distance(p) if g.geom_type == "Polygon" else g.distance(p))
                   for gs in geoms.values() for g in gs if g.distance(p) < 0.05) if any(
                   g.distance(p) < 0.05 for gs in geoms.values() for g in gs) else None
        if dmin is not None:
            m = dmin * 111320
            if m < 100:
                cerca_borde += 1
                if len(ejs) < 4: ejs.append((round(lon,5), round(lat,5), round(m,1)))
    print(f"  posiciones 'sindato' evaluadas: {mirados}; a <100 m de un polígono "
          f"de evidencia: {cerca_borde}")
    print(f"  ejemplos (lon,lat,metros al polígono): {ejs}")


if __name__ == "__main__":
    D = {"puntos": cargar("puntos-criticos-inundacion.geojson"),
         "sar": cargar("sar/huella-observada.geojson"),
         "areas": cargar("areas-riesgo-inundacion.geojson"),
         "laminas": cargar("laminas/vectorizadas.geojson"),
         "gore": cargar("gore/amenaza-inundacion.geojson")}
    que = sys.argv[1] if len(sys.argv) > 1 else "abc"
    if "a" in que: A_ray_vs_shapely()
    if "b" in que: B_gps(D)
    if "c" in que: C_borde(D)
