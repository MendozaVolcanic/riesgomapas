"""fB_inventario_geoide.py: inventario por capa de GeoIDE PRC_Araucania.

LAS DOS PREGUNTAS DEL INSTRUMENTO
(1) Si la clasificacion hidrica estuviera rota (no reconociera "inundable", "anegamiento",
    "napa", "quebrada"...), el inventario fallaria?  Solo si se prueba: --control corre el
    clasificador sobre textos conocidos (positivos y negativos, con tilde y mayusculas) y
    sobre la capa 29 a la que se le quitan 3 poligonos hidricos o se le vacia el campo NOM:
    el conteo hidrico de Angol tiene que bajar exactamente en lo borrado, o caer a 0.
(2) Si el instrumento estuviera muerto (todo cero), se veria distinto?  Si: las capas
    area_de_riesgo de Angol/Collipulli deben dar 81/68 poligonos y hidricos > 0.

Salida: inventario_geoide.csv en la carpeta del frente B (una fila por capa).
Uso: python -I fB_inventario_geoide.py [--control]
"""
import csv, sys, re, unicodedata, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from fB_geoide_geom import cargar_capa

OUT = pathlib.Path(r"C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\docs\auditorias\2026-11-15\frente-B")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


# subtipos hidricos, en orden de prioridad. tsunami se separa: es otro fenomeno (REGLAS 1.4).
RE_TSUNAMI = re.compile(r"tsunami|tsuanami|maremoto")
RE_NAPA = re.compile(r"napa|freatic")
RE_ANEG = re.compile(r"anegam")
RE_INUND = re.compile(r"inundab|inundac|inundado")
RE_CAUCE = re.compile(r"cauce|quebrada|curso de agua|curso agua|cursos naturales|alveo|vertiente|lecho")
RE_RIESGO = re.compile(r"riesgo|propensa|propensas|avalancha|remocion|aluvion|deslizam|desprendim|flujos|restriccion|inundab|anegam|napa")


def subtipo_hidrico(zona, nom):
    t = norm(zona) + " | " + norm(nom)
    if RE_TSUNAMI.search(t):
        return "tsunami"
    if RE_NAPA.search(t):
        return "napa"
    if RE_ANEG.search(t):
        return "anegamiento"
    if RE_INUND.search(t):
        return "inundacion"
    if RE_CAUCE.search(t):
        return "cauce_quebrada"
    return ""


def es_riesgo(zona, nom):
    return bool(RE_RIESGO.search(norm(zona) + " | " + norm(nom)))


def campo(a, *ks):
    for k in ks:
        if k in a:
            return a[k]
    return None


# capa -> comuna, por el nombre de la capa
NOMBRES_COMUNA = {
    0: "Pucon", 1: "Villarrica", 2: "Victoria", 3: "Traiguen", 4: "Tolten", 5: "Tolten", 6: "Tolten", 7: "Tolten",
    8: "Saavedra", 9: "Renaico", 10: "Renaico", 11: "Temuco", 12: "Temuco", 13: "Temuco", 14: "Pitrufquen",
    15: "Padre Las Casas", 16: "Nueva Imperial", 17: "Lonquimay", 18: "Loncoche", 19: "Lautaro", 20: "Gorbea",
    21: "Freire", 22: "Curacautin", 23: "Collipulli", 24: "Collipulli", 25: "Carahue", 26: "Carahue", 27: "Angol",
    28: "(todas: limite urbano)", 29: "Angol", 30: "Renaico", 31: "Renaico", 32: "Renaico", 33: "Nueva Imperial",
    34: "Tolten", 35: "Tolten", 36: "Tolten", 37: "Tolten",
}


def tipo_capa(n, nombre):
    if n == 28:
        return "limite_urbano"
    if "Area_de_riesgo" in nombre or nombre.endswith("_AR") or "proteccion_y_riesgo" in nombre:
        return "area_de_riesgo"
    return "zonificacion"


def fila_capa(n, d, feats):
    nombre = d["name"]
    tc = tipo_capa(n, nombre)
    cnt = collections.Counter()
    ha = collections.defaultdict(float)
    zonas_h = collections.defaultdict(set)
    n_ris = 0
    for a, g, nr in feats:
        zona, nom = campo(a, "ZONA"), campo(a, "NOM", "NOMBRE")
        st = subtipo_hidrico(zona, nom)
        if tc == "area_de_riesgo" or es_riesgo(zona, nom):
            n_ris += 1
        if st:
            cnt[st] += 1
            ha[st] += (g.area / 1e4) if g is not None else 0.0
            zonas_h[st].add(f"{zona}")
    campos = [f["name"] for f in d["fields"]]
    tiene_inst = any(k in campos for k in ("T_DO", "T_DOC", "N_DOC", "N_DO", "P_DO", "DO"))

    def top(ks):
        c = collections.Counter(campo(a, *ks) for a, g, nr in feats)
        return "; ".join(f"{k!s}({v})" for k, v in c.most_common(4) if k not in (None, "", " "))
    ih = cnt["inundacion"] + cnt["anegamiento"] + cnt["napa"]
    return {
        "capa_id": n, "capa": nombre, "comuna": NOMBRES_COMUNA[n], "tipo_capa": tc,
        "geometria": d["geometryType"].replace("esriGeometry", ""),
        "n_features": len(feats), "n_anillos": sum(nr for a, g, nr in feats),
        "n_riesgo_cualquier_amenaza": n_ris,
        "n_inundacion": cnt["inundacion"], "n_anegamiento": cnt["anegamiento"], "n_napa": cnt["napa"],
        "n_tsunami": cnt["tsunami"], "n_cauce_quebrada": cnt["cauce_quebrada"],
        "n_hidricos_inund_aneg_napa": ih,
        "ha_inund_aneg_napa": round(ha["inundacion"] + ha["anegamiento"] + ha["napa"], 1),
        "zonas_inund_aneg_napa": " ".join(sorted(zonas_h["inundacion"] | zonas_h["anegamiento"] | zonas_h["napa"])),
        "zonas_cauce_quebrada": " ".join(sorted(zonas_h["cauce_quebrada"])),
        "tiene_campos_instrumento": "si" if tiene_inst else "no",
        "T_DO": top(("T_DO", "T_DOC")) if tiene_inst else "sin campo",
        "N_DOC": top(("N_DOC", "N_DO")) if tiene_inst else "sin campo",
        "P_DO": top(("P_DO", "DO")) if tiene_inst else "sin campo",
        "campos": " ".join(campos),
    }


def inventario():
    filas = []
    for n in range(38):
        d, feats = cargar_capa(n)
        filas.append(fila_capa(n, d, feats))
    return filas


def control():
    ok = True
    pos = [("AR-2a", "Áreas de Riesgo Inundables o Potencialmente Inundables", "inundacion"),
           ("AR-2b", "ÁREAS DE RIESGO POR ANEGAMIENTO", "anegamiento"),
           ("AR2", "Zona potencialmente inundable por napa freática", "napa"),
           ("AR-3", "Área de Riesgo Zona de Inundación por Tsuanami", "tsunami"),
           ("ZR-5", "ZR-5 Área y/o Franja de Restricción por Quebradas", "cauce_quebrada"),
           ("ZR1", "Zona de Protección de Álveos o Cursos Naturales de Agua", "cauce_quebrada")]
    neg = [("Z-3", "Residencial Mixta Densidad Media"), ("AR-1c", "Áreas de Riesgo de Desprendimientos"),
           ("AR-1b", "Áreas de Riesgo de Flujos"), ("ZAV", "Zona Área Verde"), ("ZM-5", "Zona Mixta Río Malleco")]
    for z, nm, esp in pos:
        got = subtipo_hidrico(z, nm)
        print(f"CONTROL positivo {z!r}: esperado {esp}, medido {got}", "OK" if got == esp else "FALLA")
        ok &= got == esp
    for z, nm in neg:
        got = subtipo_hidrico(z, nm)
        print(f"CONTROL negativo {z!r}: esperado vacio, medido {got!r}", "OK" if got == "" else "FALLA")
        ok &= got == ""
    d, feats = cargar_capa(29)
    base = fila_capa(29, d, feats)
    hid = [i for i, (a, g, nr) in enumerate(feats) if subtipo_hidrico(a.get("ZONA"), a.get("NOM"))]
    mut = [f for i, f in enumerate(feats) if i not in hid[:3]]
    m1 = fila_capa(29, d, mut)
    c1 = m1["n_hidricos_inund_aneg_napa"] == base["n_hidricos_inund_aneg_napa"] - 3
    print("CONTROL mutacion A: hidricos", base["n_hidricos_inund_aneg_napa"], "-> sin 3 poligonos", m1["n_hidricos_inund_aneg_napa"], "OK" if c1 else "FALLA")
    mut2 = [(dict(a, NOM=" ", ZONA="X"), g, nr) for a, g, nr in feats]
    m2 = fila_capa(29, d, mut2)
    c2 = m2["n_hidricos_inund_aneg_napa"] == 0
    print("CONTROL mutacion B: NOM y ZONA vaciados, hidricos", base["n_hidricos_inund_aneg_napa"], "->", m2["n_hidricos_inund_aneg_napa"], "OK" if c2 else "FALLA")
    inv = {x["capa_id"]: x for x in inventario()}
    c3 = inv[29]["n_features"] == 81 and inv[23]["n_features"] == 68 and inv[29]["n_hidricos_inund_aneg_napa"] > 0
    print("CONTROL instrumento vivo: capa29", inv[29]["n_features"], "capa23", inv[23]["n_features"], "hidricos capa29", inv[29]["n_hidricos_inund_aneg_napa"], "OK" if c3 else "FALLA")
    return ok and c1 and c2 and c3


if __name__ == "__main__":
    if "--control" in sys.argv:
        sys.exit(0 if control() else 1)
    filas = inventario()
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "inventario_geoide.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    for f in filas:
        print(f"{f['capa_id']:2d} {f['capa'][:40]:40s} {f['tipo_capa'][:8]:8s} n={f['n_features']:4d} ris={f['n_riesgo_cualquier_amenaza']:3d} inu={f['n_inundacion']:3d} ane={f['n_anegamiento']:3d} napa={f['n_napa']} tsu={f['n_tsunami']} cau={f['n_cauce_quebrada']:3d} ha={f['ha_inund_aneg_napa']:8.1f} inst={f['tiene_campos_instrumento']} {f['T_DO'][:12]}|{f['N_DOC'][:8]}|{f['P_DO'][:26]}")
