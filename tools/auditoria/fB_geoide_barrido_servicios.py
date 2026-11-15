"""fB_geoide_barrido_servicios.py: barre geoide.minvu.cl/server/rest/services (raiz y carpetas) y marca los
servicios cuyo nombre o capas hablan de riesgo, inundacion, La Araucania, humedales, cauces, amenaza.

LAS DOS PREGUNTAS DEL INSTRUMENTO
(1) Si el barrido estuviera roto (no entrara a las carpetas, o el filtro no reconociera "riesgo"),
    fallaria?  --control: (a) aplica el filtro a una lista sintetica con positivos y negativos;
    (b) exige que el barrido real encuentre IPT/IPT_AREA_RIESGO y IPT/PRC_Araucania, que se
    sabe que existen; (c) lo corre con una carpeta ficticia y exige error y 0 servicios de ella sin caerse
    (descubierto al correrlo: el servidor responde igual, Token Required, a una carpeta
    inexistente que a una protegida, asi que una carpeta protegida es indistinguible de una vacia).
(2) Si el instrumento estuviera muerto (devolviera lista vacia), el resultado se veria distinto?
    Si: el control (b) falla con lista vacia.

Escribe barrido_servicios.json en data/raw/geoide_minvu_araucania (crudo) y un resumen en consola.
Una peticion a la vez, 0,5 s de pausa.
"""
import json, sys, time, re, urllib.request, urllib.parse, unicodedata, pathlib

ROOT = "https://geoide.minvu.cl/server/rest/services"
RAW = pathlib.Path(r"C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\data\raw\geoide_minvu_araucania")
RE_REL = re.compile(r"riesgo|inunda|araucan|humedal|cauce|amenaza|peligro|anegam|tsunami|remocion|sismic|volcan|pegir|senapred|hidro|fluvial|rio|lago", re.I)


def norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


def relevante(texto):
    return bool(RE_REL.search(norm(texto)))


def get(path):
    time.sleep(0.5)
    url = ROOT + path + ("&" if "?" in path else "?") + "f=json"
    req = urllib.request.Request(url, headers={"User-Agent": "riesgomapas-auditoria/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def barrer(carpetas_extra=()):
    raiz = get("")
    out = {"carpetas": raiz.get("folders", []), "servicios": []}
    for s in raiz.get("services", []):
        out["servicios"].append({"nombre": s["name"], "tipo": s["type"], "carpeta": ""})
    for c in list(raiz.get("folders", [])) + list(carpetas_extra):
        d = get("/" + urllib.parse.quote(c))
        if "error" in d:
            out.setdefault("errores", []).append({"carpeta": c, "error": d["error"]})
            continue
        for s in d.get("services", []):
            out["servicios"].append({"nombre": s["name"], "tipo": s["type"], "carpeta": c})
    return out


def detalle_featureserver(nombre):
    d = get("/" + urllib.parse.quote(nombre) + "/FeatureServer")
    if "error" in d:
        d = get("/" + urllib.parse.quote(nombre) + "/MapServer")
    return d


if __name__ == "__main__":
    if "--control" in sys.argv:
        ok = True
        sint = [("IPT/IPT_AREA_RIESGO", True), ("Hosted/Inundaciones_2024", True), ("Subsidios/DS49", False),
                ("Obras_Urbanas/Parques", False), ("Informacion_Regional/Araucania_x", True), ("Otros/Humedales", True)]
        for n, esp in sint:
            got = relevante(n)
            print("CONTROL filtro", n, "esperado", esp, "medido", got, "OK" if got == esp else "FALLA")
            ok &= got == esp
        r = barrer(carpetas_extra=("CarpetaQueNoExiste_xyz",))
        nombres = {s["nombre"] for s in r["servicios"]}
        b = {"IPT/IPT_AREA_RIESGO", "IPT/PRC_Araucania"} <= nombres
        print("CONTROL barrido encuentra IPT_AREA_RIESGO y PRC_Araucania:", b, "| servicios totales:", len(nombres), "| carpetas:", len(r["carpetas"]))
        errs = {e["carpeta"]: e["error"] for e in r.get("errores", [])}
        c = "CarpetaQueNoExiste_xyz" in errs and not any(s["carpeta"] == "CarpetaQueNoExiste_xyz" for s in r["servicios"])
        print("CONTROL carpeta ficticia da error y 0 servicios:", c, "| ojo: su error es", errs.get("CarpetaQueNoExiste_xyz"), "| carpetas reales con el mismo error:", sorted(k for k, v in errs.items() if v == errs.get("CarpetaQueNoExiste_xyz") and k != "CarpetaQueNoExiste_xyz"))
        sys.exit(0 if ok and b and c else 1)
    r = barrer()
    RAW.mkdir(parents=True, exist_ok=True)
    rel = [s for s in r["servicios"] if s["tipo"] == "FeatureServer" and relevante(s["nombre"])]
    # detalle de capas de los FeatureServer relevantes, y de todos los de IPT para ver nombres de capa
    detalles = {}
    for s in r["servicios"]:
        if s["tipo"] != "FeatureServer":
            continue
        if relevante(s["nombre"]) or s["carpeta"] in ("IPT",):
            d = detalle_featureserver(s["nombre"])
            detalles[s["nombre"]] = {"capas": [(l["id"], l["name"]) for l in d.get("layers", [])] + [("T%d" % t["id"], t["name"]) for t in d.get("tables", [])], "error": d.get("error"), "wkid": (d.get("spatialReference") or {}).get("wkid")}
    r["detalles"] = detalles
    (RAW / "barrido_servicios.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print("carpetas", len(r["carpetas"]), "servicios", len(r["servicios"]), "errores", r.get("errores"))
    for c in [""] + r["carpetas"]:
        ss = sorted({s["nombre"] for s in r["servicios"] if s["carpeta"] == c})
        print(f"[{c or 'raiz'}] {len(ss)}:", ", ".join(ss))
