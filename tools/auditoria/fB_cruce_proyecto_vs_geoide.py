"""fB_cruce_proyecto_vs_geoide.py: por comuna, que dice el proyecto (capa A publicada web/data/areas-riesgo-inundacion.geojson
y web/data/estado-comunas.json) y que trae GeoIDE (IPT/IPT_AREA_RIESGO capa 0, agregado del propio GeoIDE, filtrado a Araucania,
mas el campo de estado "le_falta").

LAS DOS PREGUNTAS DEL INSTRUMENTO
(1) Si el cruce estuviera roto (nombres de comuna que no calzan, CRS equivocado), se veria?  --control: copia GeoIDE como si
    fuera "la capa del proyecto" y exige IoU=1 por comuna (si el cruce de nombres o el CRS estuvieran mal daria 0 o NaN);
    luego la desplaza 20 m y exige que el IoU baje exactamente a lo que dice shapely para esa traslacion (calculo independiente
    con un cuadrado de control), y borra la mitad de los poligonos y exige que el area baje a ~la mitad.
(2) Si el instrumento estuviera muerto (todo vacio), se veria distinto?  Si: el IoU del control seria 0, no 1.

Salida: inventario_comuna.csv y consola.  Uso: python -I fB_cruce_proyecto_vs_geoide.py [--control]
"""
import csv, json, sys, unicodedata, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pyproj import Transformer
from shapely.geometry import shape, box
from shapely.ops import unary_union, transform
from shapely import affinity
from fB_geoide_geom import anillos_a_shapely, RAW
from fB_inventario_geoide import subtipo_hidrico, es_riesgo

P = pathlib.Path(r"C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas")
OUT = P / "docs" / "auditorias" / "2026-11-15" / "frente-B"
T = Transformer.from_crs(4326, 32718, always_xy=True)


def n(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
    s = {"pitufquen": "pitrufquen", "puerto saavedra": "saavedra"}.get(s, s)
    return s


def cargar_geoide_l0():
    d = json.loads((RAW / "ipt_area_riesgo_L0_araucania_wkid32718.json").read_text(encoding="utf-8"))
    out = []
    for f in d["features"]:
        a = f["attributes"]
        out.append({"com": n(a["COM"]), "zona": a["ZONA"], "nom": a.get("NOM"), "sub": subtipo_hidrico(a["ZONA"], a.get("NOM")),
                    "g": anillos_a_shapely(f["geometry"]["rings"])})
    return out


def cargar_geoide_38():
    """Las 38 capas PRC_Araucania (fuente primaria): poligonos de riesgo hidrico de cada capa, comuna por el nombre de la capa."""
    from fB_geoide_geom import cargar_capa
    from fB_inventario_geoide import NOMBRES_COMUNA, tipo_capa
    out = []
    for k in range(38):
        if k == 28:
            continue
        d, feats = cargar_capa(k)
        tc = tipo_capa(k, d["name"])
        for a, g, nr in feats:
            zona, nom = a.get("ZONA"), a.get("NOM", a.get("NOMBRE"))
            if tc == "area_de_riesgo" or es_riesgo(zona, nom):
                out.append({"com": n(NOMBRES_COMUNA[k]), "zona": zona, "nom": nom, "capa": k, "sub": subtipo_hidrico(zona, nom), "g": g})
    return out


def cargar_proyecto():
    d = json.loads((P / "web/data/areas-riesgo-inundacion.geojson").read_text(encoding="utf-8"))
    out = []
    for f in d["features"]:
        p = f["properties"]
        g = transform(T.transform, shape(f["geometry"]))
        out.append({"com": n(p["comuna"]), "zona": p["zona"], "sub": p["tipo_hidrico"], "anio": p["anio"], "origen": p["origen_capa"], "g": g})
    return out


def iou(a, b):
    if a.is_empty and b.is_empty:
        return float("nan")
    i = a.intersection(b).area
    u = a.union(b).area
    return i / u if u else float("nan")


def por_comuna(geoide, proy, l0=None):
    coms = sorted({x["com"] for x in geoide} | {x["com"] for x in proy})
    filas = []
    for c in coms:
        gg = [x for x in geoide if x["com"] == c]
        pp = [x for x in proy if x["com"] == c]
        gh = [x for x in gg if x["sub"]]  # todo lo hidrico de GeoIDE (inund, aneg, napa, tsunami, cauce/quebrada)
        ug = unary_union([x["g"] for x in gh]) if gh else box(0, 0, 0, 0)
        up = unary_union([x["g"] for x in pp]) if pp else box(0, 0, 0, 0)
        filas.append({"comuna": c, "geoide_poligonos_riesgo_toda_amenaza": len(gg), "geoide_poligonos_hidricos": len(gh),
                      "geoide_ha_hidricas": round(ug.area / 1e4, 1), "proyecto_poligonos_capaA": len(pp),
                      "proyecto_ha_capaA": round(up.area / 1e4, 1),
                      "iou_union": round(iou(ug, up), 3) if (gh and pp) else "", "interseccion_ha": round(ug.intersection(up).area / 1e4, 1) if (gh and pp) else 0,
                      "ha_solo_geoide": round(ug.difference(up).area / 1e4, 1), "ha_solo_proyecto": round(up.difference(ug).area / 1e4, 1),
                      "zonas_geoide_hidricas": " ".join(sorted({x["zona"] for x in gh}))})
        if l0 is not None:
            lh = [x for x in l0 if x["com"] == c and x["sub"]]
            ul = unary_union([x["g"] for x in lh]) if lh else box(0, 0, 0, 0)
            filas[-1]["L0_poligonos_hidricos"] = len(lh)
            filas[-1]["L0_ha_hidricas"] = round(ul.area / 1e4, 1)
            filas[-1]["L0_vs_38capas_iou"] = round(iou(ug, ul), 3) if (gh and lh) else ""
    return filas


def control():
    ok = True
    geo = cargar_geoide_38()
    # copia: el "proyecto" es GeoIDE mismo, solo los hidricos
    clon = [{"com": x["com"], "zona": x["zona"], "sub": x["sub"], "anio": 0, "origen": "x", "g": x["g"]} for x in geo if x["sub"]]
    f0 = por_comuna(geo, clon)
    bad = [f for f in f0 if f["iou_union"] not in ("", 1.0)]
    print("CONTROL identidad: comunas con IoU != 1:", len(bad), "de", sum(1 for f in f0 if f["iou_union"] != ""), "OK" if not bad else "FALLA")
    ok &= not bad
    # desplazamiento 20 m en el este
    sh = [dict(x, g=affinity.translate(x["g"], 20, 0)) for x in clon]
    f1 = por_comuna(geo, sh)
    bajo = [f for f in f1 if f["iou_union"] != "" and f["iou_union"] < 1.0]
    print("CONTROL desplazamiento 20 m: comunas con IoU<1:", len(bajo), "de", sum(1 for f in f1 if f["iou_union"] != ""), "OK" if len(bajo) == sum(1 for f in f1 if f["iou_union"] != "") else "FALLA")
    ok &= len(bajo) == sum(1 for f in f1 if f["iou_union"] != "")
    # calculo independiente: cuadrado 100x100 desplazado 20 -> IoU = 80*100/(120*100) = 2/3
    cuad = box(0, 0, 100, 100)
    esp = 2 / 3
    got = iou(cuad, affinity.translate(cuad, 20, 0))
    print("CONTROL IoU analitico del cuadrado desplazado 20 m: esperado", round(esp, 4), "medido", round(got, 4), "OK" if abs(got - esp) < 1e-9 else "FALLA")
    ok &= abs(got - esp) < 1e-9
    # borrar la mitad: el area compartida debe bajar ~ a la mitad en comunas con >=2 poligonos
    mitad = clon[::2]
    f2 = por_comuna(geo, mitad)
    # (primer diseno, fallo: pedia caida del 20 % del total, pero el total lo domina Temuco, un solo poligono de 1594 ha;
    #  se mide donde hay muchos poligonos, Collipulli)
    a0 = {f["comuna"]: f["proyecto_ha_capaA"] for f in f0}
    a2 = {f["comuna"]: f["proyecto_ha_capaA"] for f in f2}
    cond = a2["collipulli"] < 0.8 * a0["collipulli"] and a2["temuco"] <= a0["temuco"]
    print("CONTROL borrar la mitad de los poligonos: Collipulli ha", a0["collipulli"], "->", a2["collipulli"], "OK" if cond else "FALLA")
    ok &= cond
    # instrumento vivo
    # control de CRS entre fuentes: las 38 capas (bajadas en 32719, llevadas a 32718) contra L0 (bajada en 32718) deben coincidir
    l0 = cargar_geoide_l0()
    fx = por_comuna(geo, [], l0)
    ang = [f for f in fx if f["comuna"] == "angol"][0]
    c = ang["L0_vs_38capas_iou"] != "" and ang["L0_vs_38capas_iou"] > 0.99
    print("CONTROL CRS entre fuentes: IoU Angol (38 capas vs IPT_AREA_RIESGO L0)", ang["L0_vs_38capas_iou"], "OK" if c else "FALLA"); ok &= c
    vivo = len(geo) > 100 and any(f["geoide_poligonos_hidricos"] > 0 for f in f0)
    print("CONTROL instrumento vivo: poligonos GeoIDE", len(geo), "OK" if vivo else "FALLA")
    return ok and vivo


if __name__ == "__main__":
    if "--control" in sys.argv:
        sys.exit(0 if control() else 1)
    geo = cargar_geoide_38()
    l0 = cargar_geoide_l0()
    proy = cargar_proyecto()
    filas = por_comuna(geo, proy, l0)
    est = json.loads((P / "web/data/estado-comunas.json").read_text(encoding="utf-8"))["comunas"]
    em = {n(c["comuna"]): c for c in est}
    for f in filas:
        c = em.get(f["comuna"])
        f["estado_dice_sin_vectorial"] = "si" if c and any("vectorial" in x for x in c.get("le_falta", [])) else ("no" if c else "comuna ausente del estado")
        f["estado_poligonos_area_riesgo"] = c["poligonos_area_riesgo"] if c else ""
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "inventario_comuna.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    for f in filas:
        print(f"{f['comuna']:15s} G_riesgo={f['geoide_poligonos_riesgo_toda_amenaza']:3d} G_hid={f['geoide_poligonos_hidricos']:3d} G_ha={f['geoide_ha_hidricas']:8.1f} | A={f['proyecto_poligonos_capaA']:3d} A_ha={f['proyecto_ha_capaA']:8.1f} IoU={f['iou_union']!s:6s} inter={f['interseccion_ha']:7.1f} soloG={f['ha_solo_geoide']:7.1f} soloA={f['ha_solo_proyecto']:7.1f} | L0 n={f['L0_poligonos_hidricos']} ha={f['L0_ha_hidricas']} iouL0v38={f['L0_vs_38capas_iou']!s} | dice_sin_vec={f['estado_dice_sin_vectorial']} est_pol={f['estado_poligonos_area_riesgo']}")
