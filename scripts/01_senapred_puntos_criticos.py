"""Capa D (operacional) — Puntos Críticos del Programa Invierno de SENAPRED.

Qué es: el registro oficial, comuna por comuna, de los lugares donde el municipio
y los servicios sectoriales saben que se producen anegamientos, desbordes y
colapsos de colectores. Es el único dataset nacional, público y machine-readable
que dice DÓNDE SE INUNDA CHILE.

Por qué importa más que un modelo: no es una predicción, es memoria institucional.
Un punto que aparece año tras año en el registro es un problema crónico, no una
probabilidad.

Fuente: https://services5.arcgis.com/i7S5PSnIJAUcWvSE/arcgis/rest/services/
Salida: data/processed/senapred_*.geojson + web/data/puntos-criticos/<comuna>.geojson
"""
from __future__ import annotations

import collections
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    DATA_PROC,
    DATA_RAW,
    WEB_DATA,
    cargar_config,
    consultar_capa_arcgis,
    escribir_geojson,
    get_json,
    log,
    procedencia,
    sello,
    slug,
)

ORG = "https://services5.arcgis.com/i7S5PSnIJAUcWvSE/arcgis/rest/services"

# Series disponibles en el org de SENAPRED. La temporada actual es la de
# referencia; las anteriores sirven para detectar puntos CRÓNICOS (los que se
# repiten). Si una serie cambia de esquema o desaparece, se salta sin romper.
SERIES = {
    2026: f"{ORG}/compilado_INV_2026/FeatureServer/0",
    2022: f"{ORG}/Puntos_Críticos_Programa_Invierno_2022/FeatureServer/0",
    2021: f"{ORG}/Puntos_Críticos_Programa_Invierno_2021/FeatureServer/0",
    2020: f"{ORG}/Puntos_Críticos_Programa_Invierno_2020/FeatureServer/0",
}

SERIE_REFERENCIA = 2026

# Los nombres de campo cambian entre temporadas (y vienen truncados a 10
# caracteres por haber pasado por shapefile). Se resuelven por prefijo.
ALIAS = {
    "region": ("región", "region"),
    "provincia": ("provincia",),
    "comuna": ("comuna",),
    "sector": ("sector", "nombre_del", "lugar"),
    "causa": ("causa", "tipo_de_ev", "amenaza"),
    "nivel": ("nivel_de_r", "nivel", "riesgo"),
    "responsable": ("si_la_resp", "responsab", "servicio"),
    "solucion": ("la_soluci", "tipo_de_so", "solucion"),
    "acciones_prev": ("acciones_p",),
    "acciones_sol": ("acciones_s",),
}


def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def mapear_campos(campos_disponibles: list[str]) -> dict[str, str]:
    """Resuelve el nombre real de cada campo lógico para una serie dada."""
    mapa: dict[str, str] = {}
    normalizados = {_norm(c): c for c in campos_disponibles}
    for logico, prefijos in ALIAS.items():
        for pref in prefijos:
            p = _norm(pref)
            hit = next((real for n, real in normalizados.items() if n.startswith(p)), None)
            if hit:
                mapa[logico] = hit
                break
    return mapa


def descargar_serie(anio: int, url: str) -> tuple[list[dict], dict[str, str]] | None:
    log(f"serie {anio}: {url.split('/services/')[1].split('/')[0]}")
    try:
        info = get_json(url, {"f": "json"})
        campos = [f["name"] for f in info.get("fields", [])]
        if not campos:
            log(f"  serie {anio} sin campos — se salta")
            return None
        mapa = mapear_campos(campos)
        faltan = {"region", "comuna"} - set(mapa)
        if faltan:
            log(f"  serie {anio} sin campos clave {faltan} — se salta")
            return None
        feats = consultar_capa_arcgis(url, campos=",".join(mapa.values()))
        log(f"  {len(feats)} registros nacionales")
        return feats, mapa
    except Exception as exc:  # noqa: BLE001
        log(f"  serie {anio} no disponible: {exc}")
        return None


def es_araucania(valor: str | None) -> bool:
    """La región viene como nombre en la serie 2026 y como código DPA ('09') en
    las series 2020-2022. Hay que aceptar ambas o el histórico sale vacío."""
    if not valor:
        return False
    v = str(valor).strip()
    return "araucan" in _norm(v) or v.zfill(2) == "09"


def tabla_comunas() -> dict[str, str]:
    """Diccionario código CUT -> nombre de comuna, desde la capa oficial de SENAPRED.

    Una minoría de registros trae el código DPA en el campo `comuna` en vez del
    nombre (12 de 1374 en la temporada 2026). Sin resolverlos aparecen shards
    llamados `09211.geojson` que ningún usuario puede encontrar.
    """
    url = f"{ORG}/DPA_COMUNAS_2023/FeatureServer/0"
    try:
        feats = consultar_capa_arcgis(url, campos="cut_com,comuna", geometria=False)
    except Exception as exc:  # noqa: BLE001
        log(f"  no se pudo cargar la tabla DPA de comunas: {exc}")
        return {}
    tabla = {}
    for f in feats:
        a = f.get("attributes", {})
        cut, nom = a.get("cut_com"), a.get("comuna")
        if cut and nom:
            tabla[str(cut).strip().zfill(5)] = nom.strip()
    log(f"  tabla DPA: {len(tabla)} comunas")
    return tabla


def a_feature(attrs: dict, mapa: dict[str, str], geom: dict | None, anio: int,
              causas_inund: set[str]) -> dict | None:
    g = geom or {}
    lon, lat = g.get("x"), g.get("y")
    if lon is None or lat is None:
        # Algunas series traen la coordenada sólo en atributos.
        lon = attrs.get("Longitud")
        lat = attrs.get("Latitud")
    if lon is None or lat is None:
        return None
    try:
        lon, lat = float(lon), float(lat)
    except (TypeError, ValueError):
        return None
    if not (-76 < lon < -66 and -56 < lat < -17):
        return None  # fuera de Chile: coordenada corrupta

    def v(k: str):
        real = mapa.get(k)
        val = attrs.get(real) if real else None
        return val.strip() if isinstance(val, str) else val

    causa = v("causa")
    props = {
        # `anio` es la temporada del Programa Invierno a la que pertenece el
        # registro, no la fecha del evento. Va pegado al punto para que al
        # mezclarse con otras capas en el mapa siga sabiéndose de cuándo es.
        **sello("SENAPRED — Puntos Críticos, Programa Invierno", anio),
        "region": v("region"),
        "provincia": v("provincia"),
        "comuna": v("comuna"),
        "sector": v("sector"),
        "causa": causa,
        "nivel": v("nivel"),
        "responsable": v("responsable"),
        "solucion": v("solucion"),
        "acciones_prev": v("acciones_prev"),
        "acciones_sol": v("acciones_sol"),
        # Clasificación propia: ¿esta causa es de origen hídrico?
        # Regla explícita, no heurística — la lista vive en config/araucania.yaml.
        "es_inundacion": causa in causas_inund if causa else False,
    }
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
        "properties": props,
    }


def clave_cronica(f: dict) -> tuple:
    """Identidad aproximada de un punto para detectar reincidencia entre años.

    No hay ID estable entre temporadas. Se usa comuna + sector normalizado; si el
    sector falta, se cae a una grilla de ~1 km sobre la coordenada.
    """
    p = f["properties"]
    sector = _norm(p.get("sector") or "")
    if sector:
        return (_norm(p.get("comuna") or ""), sector)
    lon, lat = f["geometry"]["coordinates"]
    return (_norm(p.get("comuna") or ""), round(lon, 2), round(lat, 2))


def main() -> None:
    cfg = cargar_config()
    causas_inund = set(cfg["causas_inundacion"])

    todas: dict[int, list[dict]] = {}
    for anio, url in SERIES.items():
        res = descargar_serie(anio, url)
        if not res:
            continue
        feats_raw, mapa = res
        conv = []
        for ft in feats_raw:
            f = a_feature(ft.get("attributes", {}), mapa, ft.get("geometry"),
                          anio, causas_inund)
            if f and es_araucania(f["properties"]["region"]):
                conv.append(f)
        todas[anio] = conv
        log(f"  Araucanía {anio}: {len(conv)} puntos")

    if SERIE_REFERENCIA not in todas:
        raise SystemExit(f"la serie de referencia {SERIE_REFERENCIA} no se pudo descargar")

    # --- Normalizar comunas que vienen como código DPA ----------------------
    dpa = tabla_comunas()
    resueltos = sin_resolver = 0
    for feats in todas.values():
        for f in feats:
            c = (f["properties"].get("comuna") or "").strip()
            if c.isdigit():
                nom = dpa.get(c.zfill(5))
                if nom:
                    # La tabla DPA devuelve "Angol"; SENAPRED usa "ANGOL". Sin
                    # unificar la caja quedan dos comunas distintas para el mismo
                    # territorio y sus shards colisionan al escribirse, perdiendo
                    # puntos en silencio.
                    f["properties"]["comuna"] = nom.upper()
                    f["properties"]["comuna_origen"] = "resuelta desde código DPA"
                    resueltos += 1
                else:
                    sin_resolver += 1
    if resueltos or sin_resolver:
        log(f"  comunas por código DPA: {resueltos} resueltas, {sin_resolver} sin resolver")

    actual = todas[SERIE_REFERENCIA]

    # --- Reincidencia: cuántas temporadas aparece cada punto -----------------
    conteo = collections.Counter()
    for anio, feats in todas.items():
        for k in {clave_cronica(f) for f in feats}:
            conteo[k] += 1
    for f in actual:
        n = conteo[clave_cronica(f)]
        f["properties"]["temporadas_registrado"] = n
        # Un punto en 3+ temporadas es estructural, no circunstancial.
        f["properties"]["cronico"] = n >= 3

    meta = procedencia(
        fuente="SENAPRED — Puntos Críticos, Programa Invierno",
        url=SERIES[SERIE_REFERENCIA],
        metodo="Descarga directa vía ArcGIS REST, filtro por región, clasificación "
               "de causa según config/araucania.yaml, reincidencia contra series "
               f"{sorted(todas)}. Se cuentan como inundación sólo las causas de "
               "origen FLUVIAL —desborde de cauce y activación de quebradas—; el "
               "anegamiento urbano por drenaje insuficiente queda fuera de alcance "
               "por ser otro fenómeno.",
        capa_evidencia="D_operacional",
        incertidumbre="Puntos, no polígonos. Reflejan lo que el municipio reportó: "
                      "hay sesgo hacia comunas con más capacidad técnica. La "
                      "ausencia de puntos NO significa ausencia de riesgo. Los "
                      "puntos de drenaje urbano se conservan en el dato con su "
                      "etiqueta, pero no cuentan como inundación.",
        fecha_dato=f"temporada {SERIE_REFERENCIA}",
    )

    escribir_geojson(actual, DATA_PROC / "senapred_puntos_criticos_araucania.geojson", meta)

    solo_inund = [f for f in actual if f["properties"]["es_inundacion"]]
    escribir_geojson(solo_inund, WEB_DATA / "puntos-criticos-inundacion.geojson", meta)

    # Qué quedó dentro y qué fuera, con nombre y apellido. El alcance del
    # proyecto es una decisión, no un residuo de una lista incompleta, así que
    # tiene que verse en cada corrida.
    fuera = cfg.get("causas_fuera_de_alcance", {})
    conteo = collections.Counter(f["properties"]["causa"] for f in actual)
    log(f"  alcance FLUVIAL: {len(solo_inund):,} de {len(actual):,} puntos")
    for causa in cfg["causas_inundacion"]:
        if conteo.get(causa):
            log(f"    ✓ {conteo[causa]:4d}  {causa}")
    for causa, motivo in fuera.items():
        if conteo.get(causa):
            log(f"    ✗ {conteo[causa]:4d}  {causa} — {motivo}")
    sin_clasificar = set(conteo) - set(cfg["causas_inundacion"]) - set(fuera) - {None, ""}
    if sin_clasificar:
        # Una causa nueva en la fuente que nadie clasificó se iría en silencio al
        # grupo «no es inundación». Mejor que grite.
        raise SystemExit(f"causas sin clasificar en config/araucania.yaml: {sorted(sin_clasificar)}")

    # --- Shards por comuna para el frontend offline -------------------------
    por_comuna: dict[str, list[dict]] = collections.defaultdict(list)
    for f in actual:
        por_comuna[f["properties"]["comuna"] or "SIN-COMUNA"].append(f)

    # Cortafuegos: dos comunas distintas que produzcan el mismo nombre de archivo
    # se sobrescriben una a otra sin error. Preferimos fallar ruidosamente.
    colisiones = collections.Counter(slug(c) for c in por_comuna)
    repetidos = {s: [c for c in por_comuna if slug(c) == s]
                 for s, n in colisiones.items() if n > 1}
    if repetidos:
        raise SystemExit(f"nombres de comuna que colisionan al shardear: {repetidos}")

    dir_shards = WEB_DATA / "puntos-criticos"
    dir_shards.mkdir(parents=True, exist_ok=True)
    indice = []
    for comuna, feats in sorted(por_comuna.items()):
        s = slug(comuna)
        escribir_geojson(feats, dir_shards / f"{s}.geojson", meta)
        inund = [f for f in feats if f["properties"]["es_inundacion"]]
        graves = [f for f in inund if f["properties"]["nivel"] in ("Muy Alto", "Alto")]
        indice.append({
            "comuna": comuna,
            "slug": s,
            "puntos_total": len(feats),
            "puntos_inundacion": len(inund),
            "inundacion_riesgo_alto": len(graves),
            "cronicos": sum(1 for f in inund if f["properties"]["cronico"]),
            "causas": dict(collections.Counter(
                f["properties"]["causa"] for f in inund).most_common()),
        })

    # Prioridad del prototipo: comunas ordenadas por puntos de inundación de
    # nivel alto/muy alto. Es el proxy más defendible que tenemos sin población.
    indice.sort(key=lambda d: (-d["inundacion_riesgo_alto"], -d["puntos_inundacion"]))
    (WEB_DATA / "indice-comunas.json").write_text(
        json.dumps({"procedencia": meta, "comunas": indice}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    # --- Resumen a consola --------------------------------------------------
    log("")
    log(f"TOTAL Araucanía {SERIE_REFERENCIA}: {len(actual)} puntos críticos")
    log(f"  de origen hídrico (inundación): {len(solo_inund)}")
    log(f"  crónicos (3+ temporadas): {sum(1 for f in solo_inund if f['properties']['cronico'])}")
    log("")
    log("Comunas prioritarias (por puntos de inundación de riesgo Alto/Muy Alto):")
    for d in indice[:15]:
        log(f"  {d['inundacion_riesgo_alto']:3d} alto | {d['puntos_inundacion']:3d} inund "
            f"| {d['cronicos']:3d} crón | {d['comuna']}")

    # Crudo para trazabilidad
    (DATA_RAW / "senapred").mkdir(parents=True, exist_ok=True)
    for anio, feats in todas.items():
        (DATA_RAW / "senapred" / f"araucania_{anio}.json").write_text(
            json.dumps(feats, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
