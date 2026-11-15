"""fB_geoide_descarga.py: descarga cruda de las 38 capas de GeoIDE PRC_Araucania.

LAS DOS PREGUNTAS DEL INSTRUMENTO
(1) Si la paginacion estuviera rota (cortara en la primera pagina), la descarga
    lo diria?  Si: se compara lo descargado contra returnCountOnly de cada capa y
    contra maxRecordCount; --control baja con pageSize=7 (fuerza muchas paginas) y
    exige que el total sea identico al de pageSize grande, y que
    exceededTransferLimit sea la unica senal de continuar.
(2) Si el instrumento estuviera muerto (no descargara nada), el resultado se veria
    distinto?  Si: el conteo descargado 0 != conteo del servicio.

Pagina SOLO con exceededTransferLimit (no con "vino menos de lo pedido").
Una peticion a la vez, pausa 0,5 s. Geometria en EPSG:32719 (outSR).
Uso: python fB_geoide_descarga.py [--control]
"""
import json, sys, time, urllib.request, urllib.parse, pathlib, datetime

BASE = "https://geoide.minvu.cl/server/rest/services/IPT/PRC_Araucania/FeatureServer"
RAW = pathlib.Path(r"C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\data\raw\geoide_minvu_araucania")


def get(url, params):
    time.sleep(0.5)
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + "?" + q, headers={"User-Agent": "riesgomapas-auditoria/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        hdr_date = r.headers.get("Date")
        data = json.loads(r.read().decode("utf-8"))
    if "error" in data:
        raise RuntimeError(f"{url} {params}: {data['error']}")
    return data, hdr_date


def descargar(layer, page_size=None):
    meta, d0 = get(f"{BASE}/{layer}", {"f": "json"})
    cnt, _ = get(f"{BASE}/{layer}/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})
    n_serv = cnt["count"]
    ps = page_size or meta.get("maxRecordCount", 1000)
    feats, offset, paginas = [], 0, 0
    # el objectIdField se usa para ordenar y que offset sea estable
    oid = meta.get("objectIdFieldName") or "OBJECTID"
    while True:
        d, _ = get(f"{BASE}/{layer}/query", {
            "where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": 32719,
            "resultOffset": offset, "resultRecordCount": ps, "orderByFields": oid, "f": "json"})
        paginas += 1
        fs = d.get("features", [])
        feats += fs
        offset += len(fs)
        if not d.get("exceededTransferLimit"):
            break
        if not fs:
            raise RuntimeError("exceededTransferLimit sin features: bucle")
    return meta, n_serv, feats, paginas, d0


if __name__ == "__main__":
    control = "--control" in sys.argv
    if control:
        # capa 29 (Angol riesgo, 81): con pageSize 7 debe dar las mismas 81 y mismos OBJECTID
        m, n, f_small, p_small, _ = descargar(29, page_size=7)
        m, n2, f_big, p_big, _ = descargar(29)
        ids_s = sorted(x["attributes"][m.get("objectIdFieldName", "OBJECTID")] for x in f_small)
        ids_b = sorted(x["attributes"][m.get("objectIdFieldName", "OBJECTID")] for x in f_big)
        print("CONTROL paginacion capa 29: servicio", n, "| pageSize7:", len(f_small), "en", p_small, "paginas | grande:", len(f_big), "en", p_big, "paginas | ids iguales:", ids_s == ids_b)
        # defecto fabricado: truncar a la primera pagina de 7 -> la medida debe verlo
        trunc = f_small[:7]
        print("CONTROL defecto (truncado a 1 pagina):", len(trunc), "!=", n, "->", "DETECTADO" if len(trunc) != n else "NO DETECTADO")
        sys.exit(0 if (len(f_small) == n == len(f_big) and ids_s == ids_b and len(trunc) != n and p_small > 1) else 1)
    RAW.mkdir(parents=True, exist_ok=True)
    resumen = []
    for layer in range(38):
        meta, n_serv, feats, paginas, fecha = descargar(layer)
        out = {"layer": layer, "name": meta["name"], "serverDate": fecha, "countServicio": n_serv,
               "geometryType": meta.get("geometryType"), "fields": meta.get("fields"),
               "maxRecordCount": meta.get("maxRecordCount"), "features": feats}
        (RAW / f"capa_{layer:02d}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        ok = len(feats) == n_serv
        print(f"{layer:2d} {meta['name']:45s} servicio={n_serv:6d} bajados={len(feats):6d} paginas={paginas} {'OK' if ok else 'DISCREPA'}", flush=True)
        resumen.append((layer, meta["name"], n_serv, len(feats)))
    print("fin", datetime.datetime.utcnow().isoformat())
