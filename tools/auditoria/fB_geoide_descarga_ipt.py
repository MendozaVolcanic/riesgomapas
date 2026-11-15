"""fB_geoide_descarga_ipt.py: baja de GeoIDE (a) IPT/IPT_AREA_RIESGO capa 0 (PRC_Area_de_Riesgo, agregado
nacional del propio GeoIDE) filtrada a La Araucania y (b) IPT/PRI_Araucania capa 3 (PRI Villarrica-Pucon).

LAS DOS PREGUNTAS DEL INSTRUMENTO
(1) Si el filtro regional o la paginacion estuvieran rotos, se veria?  --control pide la misma consulta
    con pageSize 40 (varias paginas) y con pageSize 2000, exige mismos OBJECTID, y compara contra
    returnCountOnly (249 el 15-nov); ademas pide REG='ZZZ' y exige 0 (un filtro que no filtra
    devolveria 249 o todo el pais).
(2) Si el instrumento estuviera muerto (0 descargado), el resultado se veria distinto?  Si: 0 != 249.
Pagina SOLO con exceededTransferLimit. Geometria en EPSG:32718 (zona UTM de Angol). Pausa 0,5 s.
"""
import json, sys, time, urllib.request, urllib.parse, pathlib

R = "https://geoide.minvu.cl/server/rest/services/"
RAW = pathlib.Path(r"C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\data\raw\geoide_minvu_araucania")


def g(p, **kw):
    time.sleep(0.5)
    kw["f"] = "json"
    u = R + urllib.parse.quote(p) + "?" + urllib.parse.urlencode(kw)
    d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "riesgomapas-auditoria/1.0"}), timeout=120).read())
    if "error" in d:
        raise RuntimeError(str(d["error"]))
    return d


def bajar(path, where, ps, sr=32718):
    n = g(path + "/query", where=where, returnCountOnly="true")["count"]
    out, off = [], 0
    while True:
        d = g(path + "/query", where=where, outFields="*", returnGeometry="true", outSR=sr,
              resultOffset=off, resultRecordCount=ps, orderByFields="OBJECTID", **{})
        out += d.get("features", [])
        off += len(d.get("features", []))
        if not d.get("exceededTransferLimit"):
            break
        if not d.get("features"):
            raise RuntimeError("bucle")
    return n, out


if __name__ == "__main__":
    P0 = "IPT/IPT_AREA_RIESGO/FeatureServer/0"
    W = "REG like '%Araucan%'"
    if "--control" in sys.argv:
        n, a = bajar(P0, W, 40)
        n2, b = bajar(P0, W, 2000)
        ia = sorted(x["attributes"]["OBJECTID"] for x in a)
        ib = sorted(x["attributes"]["OBJECTID"] for x in b)
        c1 = (len(a) == n == len(b) and ia == ib)
        print("CONTROL paginacion: servicio", n, "| pageSize40:", len(a), "| pageSize2000:", len(b), "| ids iguales:", ia == ib, "OK" if c1 else "FALLA")
        z, zz = bajar(P0, "REG = 'ZZZ'", 2000)
        c2 = z == 0 and len(zz) == 0
        print("CONTROL filtro REG='ZZZ': servicio", z, "bajados", len(zz), "OK" if c2 else "FALLA")
        c3 = len(a[:40]) != n
        print("CONTROL defecto (solo 1a pagina de 40):", len(a[:40]), "!=", n, "DETECTADO" if c3 else "NO")
        sys.exit(0 if c1 and c2 and c3 else 1)
    n, feats = bajar(P0, W, 2000)
    d0 = g(P0)
    (RAW / "ipt_area_riesgo_L0_araucania_wkid32718.json").write_text(json.dumps({"layer": P0, "where": W, "countServicio": n, "outSR": 32718,
        "fields": d0["fields"], "features": feats}, ensure_ascii=False), encoding="utf-8")
    print("IPT_AREA_RIESGO/0 Araucania: servicio", n, "bajados", len(feats), "OK" if n == len(feats) else "DISCREPA")
    P3 = "IPT/PRI_Araucan\u00eda/FeatureServer/3"
    n, feats = bajar(P3, "1=1", 2000)
    d3 = g(P3)
    (RAW / "pri_araucania_L3_villarrica_pucon_wkid32718.json").write_text(json.dumps({"layer": P3, "countServicio": n, "outSR": 32718,
        "fields": d3["fields"], "features": feats}, ensure_ascii=False), encoding="utf-8")
    print("PRI_Araucania/3: servicio", n, "bajados", len(feats), "OK" if n == len(feats) else "DISCREPA")
