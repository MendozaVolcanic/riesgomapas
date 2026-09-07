"""Compara los campos que web/app.js LEE con las claves que los archivos de
web/data/ REALMENTE traen (auditoría 2026-09-06, frente 2, patrón 1).

Preguntas del instrumento:
  (1) Si el visor leyera un campo que ningún archivo trae, ¿esto lo ve?
      Sí: aparece como FALTA con cobertura 0/N.
  (2) Si el instrumento estuviera muerto (no cargó los archivos), ¿se vería
      distinto? Sí: cada archivo imprime n>0 y sus claves; un archivo no leído
      aparece con ERROR.
Control positivo: se agrega a mano un campo inventado ('__control_inexistente')
en la tabla de lecturas de `puntos` para verificar que se reporta como FALTA.

Uso:  python tools/auditoria/campos_visor_vs_datos.py
Sale por stdout. No modifica nada.
"""
import collections
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "web" / "app.js"

# Qué lee el visor de cada archivo. Transcrito a mano desde web/app.js con el
# número de línea donde se lee (versión de la rama visor-simple-y-laminas-
# vectorizadas, commit b293aad). El bloque de abajo verifica que la
# transcripción cubra todos los tokens `properties.X` / `p.X` del archivo.
LECTURAS = {
    "puntos-criticos-inundacion.geojson": {
        "nivel": [344, 876, 1080, 1637], "comuna": [410, 1638, 1873],
        "cronico": [577, 663, 878, 1815], "responsable": [665, 1639],
        "causa": [875, 1080, 1637], "sector": [877, 1636],
        "temporadas_registrado": [878], "fuente": [1082, 1641],
        "anio": [1082, 1642],
        "__control_inexistente": [0],   # control positivo: DEBE salir FALTA
    },
    "areas-riesgo-inundacion.geojson": {
        "clasificacion": [684, 1072, 1579], "tipo_hidrico": [689],
        "zona": [693, 1581], "usos_prohibidos": [694, 1582],
        "ordenanza_url": [697], "eae_fecha_ingreso": [722],
        "eae_procedimiento": [727], "eae_estado": [729],
        "fuente": [648, 1073, 1586], "anio": [649, 1073, 1586],
        "comuna": [1580, 1817],
    },
    "sar/huella-observada.geojson": {
        "fecha_observacion": [360, 567, 747, 1050], "evento": [750, 1052],
        "hectareas": [756], "track": [761], "direccion": [764],
        "orbita_relativa": [767], "plataforma": [772],
        "fechas_referencia": [775], "caida_db": [776], "umbral_agua_db": [776],
        "fuente": [1053], "anio": [1054],
    },
    "sar/cobertura-sar.geojson": {"fecha_observacion": [321]},
    "gore/amenaza-inundacion.geojson": {"clase": [918, 1524]},
    "campamentos-inundacion.geojson": {
        "nombre": [942, 1605], "hogares": [943, 1606, 1819],
        "tipo_riesgo": [945, 1607], "anio": [947, 1609], "fuente": [1609],
        "comuna": [1606],
    },
    "laminas/vectorizadas.geojson": {},   # el visor NO lee ningún campo
    "jrc/rp100.geojson": {},              # sólo geometría
}
LECTURAS_JSON = {
    "planos/indice.json": ("planos", {
        "bounds_wgs84": [178, 197, 217], "titulo": [201, 856],
        "rmse_loo_m": [201, 858], "archivo": [201, 212, 224],
        "estado_tramite": [849, 853], "estado_tramite_nota": [861],
        "puntos_control": [857], "resolucion_m_px": [858],
    }),
    "estado-comunas.json": ("comunas", {
        "comuna": [415, 451], "poligonos_area_riesgo": [431, 495],
        "laminas_localizadas": [435], "documentos": [437],
        "planos_georreferenciados": [439], "planos_por_estado": [440],
        "poligonos_vectorizados_por_nosotros": [445], "personas": [455, 538],
        "puntos_inundacion": [456, 539], "puntos_cronicos": [457, 540],
        "le_falta": [463, 525, 542],
    }),
    "indice-comunas.json": ("comunas", {
        "comuna": [1139, 1873], "puntos_inundacion": [1144, 1787],
        "inundacion_riesgo_alto": [1788], "cronicos": [1798],
    }),
}


def claves_fc(ruta):
    d = json.loads(ruta.read_text(encoding="utf-8"))
    feats = d["features"]
    cnt, nulos = collections.Counter(), collections.Counter()
    for f in feats:
        for k, v in (f.get("properties") or {}).items():
            cnt[k] += 1
            if v is None or v == "":
                nulos[k] += 1
    return d, feats, cnt, nulos


def main():
    print(f"app.js: {APP} ({sum(1 for _ in APP.open(encoding='utf-8'))} líneas)")
    js = APP.read_text(encoding="utf-8")
    tokens = collections.defaultdict(set)
    for n, linea in enumerate(js.splitlines(), 1):
        for m in re.finditer(r"properties\??\.(\w+)|\bp\.(\w+)|\bc\.(\w+)", linea):
            t = m.group(1) or m.group(2) or m.group(3)
            tokens[t].add(n)
    conocidos = set()
    for tabla in LECTURAS.values():
        conocidos |= set(tabla)
    for _, tabla in LECTURAS_JSON.values():
        conocidos |= set(tabla)
    print("\n-- Tokens `properties.X` / `p.X` / `c.X` de app.js que NO están en la "
          "tabla transcrita (deben ser ruido: p.fecha_dato, p.generado, c.d, c.f...):")
    for t in sorted(tokens):
        if t not in conocidos:
            print(f"   {t}: líneas {sorted(tokens[t])[:8]}")

    print("\n== GEOJSON ==")
    for rel, tabla in LECTURAS.items():
        ruta = RAIZ / "web" / "data" / rel
        try:
            d, feats, cnt, nulos = claves_fc(ruta)
        except Exception as e:  # noqa: BLE001
            print(f"\n## {rel}: ERROR {e}")
            continue
        n = len(feats)
        proc = d.get("procedencia") or {}
        print(f"\n## {rel}  n={n}  procedencia.keys={sorted(proc)}")
        print(f"   procedencia.fuente={proc.get('fuente')!r} fecha_dato={proc.get('fecha_dato')!r} "
              f"capa={proc.get('capa') or proc.get('capa_evidencia')!r}")
        for k, lineas in tabla.items():
            c = cnt.get(k, 0)
            estado = "OK" if c == n and nulos[k] == 0 else ("PARCIAL" if c else "FALTA")
            print(f"   lee {k:<36} app.js:{lineas}  -> {estado} presente {c}/{n}, nulos/vacíos {nulos[k]}")
        sobran = [k for k in cnt if k not in tabla]
        print(f"   claves que el archivo trae y el visor NO lee ({len(sobran)}): {sobran}")

    print("\n== JSON ==")
    for rel, (lista, tabla) in LECTURAS_JSON.items():
        ruta = RAIZ / "web" / "data" / rel
        d = json.loads(ruta.read_text(encoding="utf-8"))
        items = d[lista]
        n = len(items)
        cnt, nulos = collections.Counter(), collections.Counter()
        for it in items:
            for k, v in it.items():
                cnt[k] += 1
                if v is None or v == "" or v == []:
                    nulos[k] += 1
        print(f"\n## {rel} [{lista}] n={n} top={sorted(k for k in d if k != lista)}")
        for k, lineas in tabla.items():
            c = cnt.get(k, 0)
            estado = "OK" if c == n and nulos[k] == 0 else ("PARCIAL" if c else "FALTA")
            print(f"   lee {k:<36} app.js:{lineas}  -> {estado} presente {c}/{n}, nulos/vacíos {nulos[k]}")
        sobran = [k for k in cnt if k not in tabla]
        print(f"   claves que el archivo trae y el visor NO lee ({len(sobran)}): {sobran}")

    # sar/indice.json: el visor lee evento.{nombre,fecha_inicio,fecha_fin} y
    # resumen.{hectareas,km2}
    si = json.loads((RAIZ / "web/data/sar/indice.json").read_text(encoding="utf-8"))
    print("\n## sar/indice.json top=", sorted(si))
    print("   evento=", json.dumps(si.get("evento"), ensure_ascii=False))
    print("   resumen=", json.dumps(si.get("resumen"), ensure_ascii=False))


if __name__ == "__main__":
    main()
