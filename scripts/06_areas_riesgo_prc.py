"""Capa A (normativa) — áreas de riesgo de los Planes Reguladores, en vectorial.

Este es el hallazgo que cambia el proyecto. El supuesto de partida era que las
áreas de riesgo de los planes reguladores sólo existían como imagen dentro de
PDFs. Es cierto para el *estudio* que las fundamenta, pero **no** para el
polígono normativo: MINVU publica la zonificación de riesgo de los PRC de todo
Chile como servicio ArcGIS abierto, en vectorial y sin autenticación.

    services3.arcgis.com/cTnMkBRk4HWkUCRo
      · prc_riesgo_nacional_visor_P/0   "Área Riesgo PRC"  — 3.765 polígonos país
      · 09_PRC_La_Araucania             — 42 capas, PRC comuna por comuna

Ojo con lo que esto es y lo que no es: son las **áreas de riesgo del instrumento
normativo** (Art. 2.1.17 OGUC), es decir, dónde el plan regulador restringe o
prohíbe construir. Tienen efecto legal. No son una modelación hidráulica ni una
mancha de inundación calculada, y sólo existen dentro del límite urbano de las
comunas que tienen PRC actualizado.

El campo `UPROH` (usos prohibidos) es el que más le sirve a una persona: dice
literalmente qué no se puede hacer en ese terreno.

⚠️ Nota de descubrimiento: el registro de datos.gob.cl apunta a
`geoportal.cl/ArcGIS/...`, que está **caído (404)**. El servicio vivo es el de
arriba. Un catálogo oficial desactualizado es la razón habitual de concluir que
"el dato no existe".

Salida: data/processed/areas_riesgo_prc_araucania.geojson
        web/data/areas-riesgo-inundacion.geojson
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
    WEB_DATA,
    consultar_capa_arcgis,
    escribir_geojson,
    get_json,
    log,
    procedencia,
    sello,
)

ORG = "https://services3.arcgis.com/cTnMkBRk4HWkUCRo/arcgis/rest/services"
NACIONAL = f"{ORG}/prc_riesgo_nacional_visor_P/FeatureServer/0"
REGIONAL = f"{ORG}/09_PRC_La_Araucania/FeatureServer"

# Qué clasificaciones cuentan como amenaza hídrica. La lista es explícita porque
# el campo viene con erratas de origen ("REMOSION"), combinaciones y espacios
# sobrantes: cualquier heurística silenciosa acá clasifica mal un polígono con
# efecto legal.
CLAVES_HIDRICAS = ("INUND", "ANEGAM", "QUEBRAD", "NAPAS")


def norm(t: str | None) -> str:
    return unicodedata.normalize("NFKD", (t or "")).encode("ascii", "ignore").decode().upper()


def es_hidrica(clasificacion: str | None) -> bool:
    return any(k in norm(clasificacion) for k in CLAVES_HIDRICAS)


def anillos_a_geojson(geom: dict) -> dict | None:
    """ArcGIS entrega polígonos como lista de anillos con orientación implícita.

    Convención ArcGIS: anillo exterior en sentido horario, huecos en antihorario.
    GeoJSON no comparte esa regla, así que hay que separarlos por el signo del
    área firmada; si no, los huecos se dibujan como polígonos macizos y una zona
    excluida del área de riesgo aparece como incluida.
    """
    anillos = geom.get("rings") or []
    if not anillos:
        return None

    def area(a):
        return sum((a[i][0] * a[i + 1][1] - a[i + 1][0] * a[i][1])
                   for i in range(len(a) - 1)) / 2.0

    exteriores, huecos = [], []
    for a in anillos:
        if len(a) < 4:
            continue
        (exteriores if area(a) < 0 else huecos).append([[float(x), float(y)] for x, y, *_ in a])

    if not exteriores:  # todos dieron el mismo signo: tratarlos como exteriores
        exteriores = [[[float(x), float(y)] for x, y, *_ in a] for a in anillos if len(a) >= 4]
        huecos = []
    if not exteriores:
        return None

    polis = [[e] for e in exteriores]
    for h in huecos:                       # cada hueco al primer exterior disponible
        polis[0].append(h)
    if len(polis) == 1:
        return {"type": "Polygon", "coordinates": polis[0]}
    return {"type": "MultiPolygon", "coordinates": polis}


def a_feature(attrs: dict, geom: dict, origen: str) -> dict | None:
    g = anillos_a_geojson(geom or {})
    if not g:
        return None
    # La capa nacional trae `CLASIFICACION_RIESGOS`. Las capas regionales no, pero
    # su campo `NOMBRE` es explícito ("ZR-4 Área de Riesgo por Proceso de Remoción
    # en Masa"), mientras que `ZONA` sólo trae el código ("ZR-4"), inservible para
    # clasificar. El orden importa: una capa llamada "PRC Riesgo Collipulli"
    # contiene zonas de inundación Y de remoción mezcladas.
    cls = (attrs.get("CLASIFICACION_RIESGOS") or attrs.get("RIESGO")
           or attrs.get("NOMBRE") or attrs.get("ZONA"))
    return {
        "type": "Feature",
        "geometry": g,
        "properties": {
            "comuna": (attrs.get("COMUNA") or "").strip() or None,
            "sector": (attrs.get("SECTOR") or "").strip() or None,
            "zona": (attrs.get("ZONA") or "").strip() or None,
            "nombre": (attrs.get("NOMBRE") or "").strip() or None,
            "clasificacion": (cls or "").strip() or None,
            "usos_prohibidos": (attrs.get("UPROH") or attrs.get("UPROM") or "").strip() or None,
            "usos_permitidos": (attrs.get("UPERM") or "").strip() or None,
            # El campo URL de la capa apunta a observatoriourbano.cl, que responde
            # 410 Gone. Se conserva por trazabilidad pero se marca como caído para
            # que el frontend no lo ofrezca como enlace vivo.
            "ordenanza_url": (attrs.get("URL") or "").strip() or None,
            "ordenanza_url_vigente": False,
            "es_inundacion": es_hidrica(cls),
            "origen_capa": origen,
            **sello("MINVU — áreas de riesgo de instrumentos de planificación "
                    "territorial (Art. 2.1.17 OGUC)", None),
        },
    }


def desde_nacional() -> list[dict]:
    log("capa nacional de áreas de riesgo PRC")
    feats = consultar_capa_arcgis(
        NACIONAL, where="NOM_REGION LIKE '%RAUCAN%'",
        campos="COMUNA,SECTOR,ZONA,NOMBRE,UPERM,UPROH,CLASIFICACION_RIESGOS")
    out = [f for f in (a_feature(x.get("attributes", {}), x.get("geometry"), "PRC nacional")
                       for x in feats) if f]
    log(f"  {len(out)} polígonos en La Araucanía")
    return out


def desde_regional() -> list[dict]:
    """Capas de riesgo del servicio regional, que cubren comunas que la capa
    nacional no trae (Temuco anegamiento, Renaico, Toltén, Collipulli...)."""
    log("capas de riesgo del servicio regional 09_PRC_La_Araucania")
    try:
        info = get_json(REGIONAL, {"f": "json"})
    except Exception as exc:  # noqa: BLE001
        log(f"  no disponible: {exc}")
        return []
    out = []
    for capa in info.get("layers", []):
        nom = capa.get("name", "")
        n = norm(nom)
        if not ("RIESGO" in n or "INUNDAC" in n or "ANEGAM" in n):
            continue
        # `outFields=*` y no una lista: el esquema cambia entre capas (unas traen
        # UPROH, otras UPROM) y pedir un campo inexistente hace fallar la consulta
        # entera.
        try:
            feats = consultar_capa_arcgis(f"{REGIONAL}/{capa['id']}", campos="*")
        except Exception as exc:  # noqa: BLE001
            log(f"  capa {capa['id']} '{nom}' falló: {exc}")
            continue
        conv = [f for f in (a_feature(x.get("attributes", {}), x.get("geometry"), nom)
                            for x in feats) if f]
        # Si el nombre de la CAPA ya declara inundación, vale para todos sus
        # polígonos aunque el atributo no lo diga.
        if "INUNDAC" in n or "ANEGAM" in n:
            for f in conv:
                f["properties"]["es_inundacion"] = True
                f["properties"]["clasificacion"] = f["properties"]["clasificacion"] or nom
        out.extend(conv)
        log(f"  capa {capa['id']:2d} '{nom[:48]}': {len(conv)} polígonos")
    return out


def centroide(geom: dict) -> tuple[float, float]:
    """Centroide aproximado por promedio de vértices del primer anillo exterior."""
    c = geom["coordinates"]
    anillo = c[0] if geom["type"] == "Polygon" else c[0][0]
    xs = [p[0] for p in anillo]
    ys = [p[1] for p in anillo]
    return round(sum(xs) / len(xs), 5), round(sum(ys) / len(ys), 5)


def deduplicar(feats: list[dict]) -> list[dict]:
    """La capa nacional y la regional publican los MISMOS polígonos para varias
    comunas (Collipulli y Carahue sobre todo). Sin deduplicar, el conteo se
    infla y el mapa dibuja el área de riesgo dos veces, lo que además oscurece
    el relleno translúcido y hace parecer más severa una zona por un artefacto
    de procesamiento.

    Se identifica cada polígono por comuna + centroide + nº de vértices. La
    geometría es idéntica entre capas, así que no hace falta tolerancia.
    """
    vistos: dict[tuple, dict] = {}
    duplicados = 0
    for f in feats:
        g = f["geometry"]
        anillo = (g["coordinates"][0] if g["type"] == "Polygon"
                  else g["coordinates"][0][0])
        clave = (norm(f["properties"]["comuna"]), centroide(g), len(anillo))
        previo = vistos.get(clave)
        if previo is None:
            vistos[clave] = f
            continue
        duplicados += 1
        # Se conserva el que tenga clasificación explícita de amenaza; si ambos
        # la tienen, gana el que además marque inundación (más informativo).
        mejor = max((previo, f), key=lambda x: (
            bool(x["properties"]["es_inundacion"]),
            bool(x["properties"]["clasificacion"]),
            bool(x["properties"]["usos_prohibidos"]),
        ))
        mejor["properties"]["es_inundacion"] = (
            previo["properties"]["es_inundacion"] or f["properties"]["es_inundacion"])
        vistos[clave] = mejor
    if duplicados:
        log(f"  deduplicados: {duplicados} polígonos repetidos entre capas")
    return list(vistos.values())


def fechas_eae_por_comuna() -> dict[str, dict]:
    """Fecha del procedimiento EAE del PRC de cada comuna, si el índice existe.

    ⚠️ Esto NO es el año del plan regulador vigente. Es la fecha en que entró a
    Evaluación Ambiental Estratégica el procedimiento de elaboración o
    actualización. Se publica con esa etiqueta exacta y no como "año del plan",
    porque son cosas distintas y confundirlas induce a error sobre la vigencia.

    El año del instrumento no está declarado en ninguna de las fuentes
    verificadas: la capa MINVU no trae campo de fecha, y su enlace a la ordenanza
    en observatoriourbano.cl responde 410.
    """
    idx = DATA_PROC / "eae" / "araucania.json"
    if not idx.exists():
        log("  (sin índice EAE: corre el script 05 para agregar fecha de procedimiento)")
        return {}
    out: dict[str, dict] = {}
    for p in json.loads(idx.read_text(encoding="utf-8")):
        if (p.get("instrumento") or "").upper() != "PRC":
            continue
        for c in (p.get("comunas") or "").split(","):
            c = norm(c.strip())
            if not c:
                continue
            # Si hay varios procedimientos, se conserva el más reciente.
            prev = out.get(c)
            f = p.get("fecha_ingreso") or ""
            if not prev or f[-4:] > (prev["fecha"] or "")[-4:]:
                out[c] = {"fecha": f, "procedimiento": p.get("nombre"),
                          "estado": p.get("estado")}
    log(f"  fechas EAE disponibles para {len(out)} comunas")
    return out


def main() -> None:
    feats = deduplicar(desde_nacional() + desde_regional())
    if not feats:
        raise SystemExit("no se obtuvo ningún polígono — revisar los servicios MINVU")

    eae = fechas_eae_por_comuna()
    for f in feats:
        info = eae.get(norm(f["properties"]["comuna"]))
        if info:
            f["properties"]["eae_procedimiento"] = info["procedimiento"]
            f["properties"]["eae_fecha_ingreso"] = info["fecha"]
            f["properties"]["eae_estado"] = info["estado"]

    meta = procedencia(
        fuente="MINVU — Áreas de riesgo de Instrumentos de Planificación Territorial",
        url=NACIONAL,
        metodo="Descarga vía ArcGIS REST de la capa nacional de áreas de riesgo PRC "
               "filtrada a La Araucanía, más las capas de riesgo del servicio "
               "regional 09_PRC_La_Araucania. Conversión de anillos ArcGIS a "
               "GeoJSON respetando el signo del área para los huecos.",
        capa_evidencia="A_normativo",
        incertidumbre="Son áreas de riesgo del instrumento normativo (Art. 2.1.17 OGUC), "
                      "no una modelación hidráulica. Sólo existen dentro del límite "
                      "urbano de comunas con PRC que las haya definido: la ausencia de "
                      "polígono no significa ausencia de riesgo, significa que el plan "
                      "regulador no lo zonificó.",
        escala_original="escala del plan regulador respectivo (típicamente 1:5.000 a 1:20.000)",
    )

    escribir_geojson(feats, DATA_PROC / "areas_riesgo_prc_araucania.geojson", meta)
    inund = [f for f in feats if f["properties"]["es_inundacion"]]
    escribir_geojson(inund, WEB_DATA / "areas-riesgo-inundacion.geojson", meta)

    log("")
    log(f"TOTAL: {len(feats)} polígonos de área de riesgo")
    log(f"  de amenaza hídrica: {len(inund)}")
    log("")
    log("Por clasificación:")
    for k, v in collections.Counter(
            f["properties"]["clasificacion"] for f in feats).most_common(12):
        marca = "💧" if es_hidrica(k) else "  "
        log(f"  {marca} {v:4d}  {k}")
    log("")
    log("Comunas con área de riesgo por inundación:")
    for k, v in collections.Counter(
            f["properties"]["comuna"] for f in inund).most_common():
        log(f"   {v:4d}  {k}")


if __name__ == "__main__":
    main()
