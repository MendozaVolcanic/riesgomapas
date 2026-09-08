"""Capa A (normativa) — áreas de riesgo de los Planes Reguladores, en vectorial.

Este es el hallazgo que cambia el proyecto. El supuesto de partida era que las
áreas de riesgo de los planes reguladores sólo existían como imagen dentro de
PDFs. Es cierto para el *estudio* que las fundamenta, pero **no** para el
polígono normativo: MINVU publica la zonificación de riesgo de los PRC de todo
Chile como servicio ArcGIS abierto, en vectorial y sin autenticación.

    services3.arcgis.com/cTnMkBRk4HWkUCRo
      · prc_riesgo_nacional_visor_P/0   "Área Riesgo PRC"  — 3.765 polígonos país
      · prc_riesgo_nacional_visor_P/1   "Área Riesgo PRI"  — 21.392 polígonos país
      · 09_PRC_La_Araucania             — 42 capas, PRC comuna por comuna

Se usa la capa 0. La 1 —las áreas de riesgo de los planes reguladores
INTERcomunales— se consultó el 8-sep-2026 y en toda La Araucanía tiene **dos**
polígonos, los dos de REMOCION EN MASA y los dos en Cautín (Villarrica-Pucón).
Para inundación en esta región no aporta nada. Queda anotado para que no haya
que volver a preguntárselo: 21.392 registros a escala país invitan a suponer
que falta media capa.

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

Requiere: nada del pipeline para la capa misma — opcional: 05_eae_documentos.py
        (data/processed/eae/araucania.json, sólo para agregar la fecha del
        procedimiento EAE; si no está, sigue corriendo sin esa fecha)
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
    anillos_a_geojson,
    DATA_PROC,
    WEB_DATA,
    cargar_config,
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

# Qué clasificaciones son de amenaza hídrica, y de qué TIPO.
#
# La lista es explícita porque el campo viene con erratas de origen ("REMOSION"),
# combinaciones y espacios sobrantes: cualquier heurística silenciosa acá
# clasifica mal un polígono con efecto legal.
#
# ⚠️ Y se separa el tipo, no sólo si es hídrica o no. El proyecto argumenta en
# todas partes que **inundación fluvial y anegamiento por drenaje son fenómenos
# distintos** —otra física, otra mitigación, otro servicio responsable— y lo
# demuestra con datos: los puntos de colector no muestran ninguna señal contra la
# huella satelital (×1,0, azar puro) mientras los de desborde dan ×2,1. Aun así,
# esta capa los publicaba juntos bajo el titular «área de riesgo por inundación»:
# 3 polígonos de anegamiento, 1 de afloramiento de napas y 2 de inundación
# litoral —que es marejada o tsunami, ni siquiera es fluvial— entre los 63.
#
# Se conservan todos, porque son áreas de riesgo reales y con efecto legal, pero
# cada uno dice QUÉ fenómeno declara y el visor deja de llamarlos a todos
# inundación.
TIPO_HIDRICO = {
    "INUND LITORAL": "litoral",      # va primero: contiene "INUND" y NO es fluvial
    "INUND": "fluvial",
    "QUEBRAD": "fluvial",            # activación de quebrada: agua que sale de un cauce
    "CANAL": "fluvial",              # un canal es un cauce, artificial pero cauce
    "ANEGAM": "anegamiento",         # drenaje insuficiente, no desborde
    "NAPAS": "napa_freatica",        # afloramiento, tampoco es desborde
}


def norm(t: str | None) -> str:
    return unicodedata.normalize("NFKD", (t or "")).encode("ascii", "ignore").decode().upper()


def tipo_hidrico(clasificacion: str | None) -> str | None:
    """Devuelve el fenómeno hídrico declarado, o None si no es hídrico.

    El orden del diccionario importa: «INUNDACION LITORAL» contiene «INUND» y
    NO es inundación fluvial, así que se comprueba antes.
    """
    n = norm(clasificacion)
    for clave, tipo in TIPO_HIDRICO.items():
        if all(parte in n for parte in clave.split()):
            return tipo
    return None


def es_hidrica(clasificacion: str | None) -> bool:
    return tipo_hidrico(clasificacion) is not None


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
            # Qué fenómeno hídrico declara el instrumento. Es la diferencia entre
            # «el río se sale» y «el colector no da abasto»: otra física, otra
            # mitigación y otro servicio responsable.
            "tipo_hidrico": tipo_hidrico(cls),
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
                if not f["properties"].get("tipo_hidrico"):
                    f["properties"]["tipo_hidrico"] = tipo_hidrico(nom)
        out.extend(conv)
        log(f"  capa {capa['id']:2d} '{nom[:48]}': {len(conv)} polígonos")
    return out


def centroide(geom: dict) -> tuple[float, float]:
    """Centroide aproximado por promedio de vértices del primer anillo exterior.

    Se descarta el vértice de cierre —el que repite al primero— antes de
    promediar. Sin eso el resultado depende de POR DÓNDE empieza el anillo: el
    mismo polígono publicado por dos servicios con distinto vértice inicial
    repite un punto distinto, el promedio cambia en el quinto decimal y la clave
    de deduplicación deja de coincidir. Así se colaron dos copias exactas de un
    área de 10,2 ha en Collipulli (mismos 229 vértices), y el visor decía «cae
    dentro de 2 áreas de riesgo» donde hay una.
    """
    c = geom["coordinates"]
    anillo = c[0] if geom["type"] == "Polygon" else c[0][0]
    if len(anillo) > 1 and anillo[0] == anillo[-1]:
        anillo = anillo[:-1]
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
        # El número de vértices también se cuenta sin el de cierre, por lo mismo.
        n_vert = len(anillo) - (1 if len(anillo) > 1 and anillo[0] == anillo[-1] else 0)
        clave = (norm(f["properties"]["comuna"]), centroide(g), n_vert)
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
    cfg = cargar_config()
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
        fecha_dato="consulta al servicio de MINVU; el año de cada instrumento va "
                   "por polígono en el campo `anio`",
    )

    # Nombre de comuna canónico. Ver `correcciones_nombre_comuna` en
    # config/araucania.yaml: el nombre es la llave de todos los cruces, y una
    # discrepancia no da error sino un cruce vacío.
    oficiales = {norm(c): c.title() for prov in cfg["provincias"].values() for c in prov}
    correcciones = {norm(k): v for k, v in
                    (cfg.get("correcciones_nombre_comuna") or {}).items()}
    corregidos, sin_clasificar = 0, set()
    for f in feats:
        bruto = (f["properties"].get("comuna") or "").strip()
        clave = norm(bruto)
        if clave in correcciones:
            f["properties"]["comuna_fuente"] = bruto
            f["properties"]["comuna"] = correcciones[clave]
            corregidos += 1
        elif clave in oficiales:
            pass                      # ya coincide con una comuna de la región
        elif bruto:
            sin_clasificar.add(bruto)
    if sin_clasificar:
        raise SystemExit(
            "el servicio del MINVU trae nombres de comuna que no son ninguna "
            f"comuna de La Araucanía ni están en `correcciones_nombre_comuna`: "
            f"{sorted(sin_clasificar)}. Revísalos y agrégalos a "
            "config/araucania.yaml — si se dejan pasar, esa comuna queda sin "
            "cruzar contra SENAPRED, el censo y el catálogo, y el síntoma es mudo.")
    log(f"  nombre de comuna corregido en {corregidos} polígono(s); la ortografía "
        f"original queda en `comuna_fuente`")

    # Año del instrumento vigente por comuna. MINVU no lo publica en la capa —el
    # campo venía «no declarado por la fuente» en los 124 polígonos—, y sin él no
    # se puede decir lo más útil de esta capa: que el área de riesgo que rige tu
    # terreno la dibujó un plan de hace medio siglo.
    #
    # La fuente es el catastro nacional del Atlas del Riesgo de Desastre (Vicuña y
    # Guzmán, CIGIDEN / IEUT-UC, 2025), que sí lo levantó comuna por comuna. Se
    # atribuye explícitamente porque es dato de terceros, y sólo cubre las comunas
    # que el Atlas lista: las que faltan siguen diciendo «no declarado».
    anios = cfg.get("anio_instrumento_comuna") or {}
    puestos = 0
    for f in feats:
        # Se busca por el nombre oficial Y por el que traía la fuente. El
        # renombre ocurre antes que esto —«Puerto Saavedra» pasa a «Saavedra»—
        # y el catastro del Atlas usa el nombre largo, así que buscar sólo por
        # el corregido dejaba a esa comuna sin año, indistinguible de una que
        # el Atlas de verdad no cubre.
        a = (anios.get((f["properties"].get("comuna") or "").strip())
             or anios.get((f["properties"].get("comuna_fuente") or "").strip()))
        if a:
            f["properties"]["anio"] = a
            f["properties"]["anio_fuente"] = ("Atlas del Riesgo de Desastre, "
                                              "Vicuña y Guzmán, CIGIDEN/IEUT-UC 2025")
            puestos += 1
    log(f"  año del instrumento asignado a {puestos} de {len(feats)} polígonos "
        f"({len(anios)} comunas con año conocido)")

    escribir_geojson(feats, DATA_PROC / "areas_riesgo_prc_araucania.geojson", meta)

    # Se publican TODOS los hídricos, pero cada uno diciendo qué fenómeno es.
    #
    # No se filtra a sólo fluvial porque un área de riesgo por anegamiento es un
    # área de riesgo real, con efecto legal, y quien consulta su terreno la tiene
    # que ver. Lo que no puede pasar es que se llamen todas «inundación»: el
    # visor usa `tipo_hidrico` para titular cada una por lo que declara.
    inund = [f for f in feats if f["properties"]["es_inundacion"]]
    sin_tipo = [f for f in inund if not f["properties"].get("tipo_hidrico")]
    if sin_tipo:
        raise SystemExit(
            f"{len(sin_tipo)} polígono(s) marcados como hídricos sin fenómeno "
            f"clasificado: {sorted({f['properties'].get('clasificacion') for f in sin_tipo})}. "
            "Agrégalos a TIPO_HIDRICO. Publicarlos sin tipo los haría aparecer "
            "como inundación fluvial, que es la mezcla que este proyecto existe "
            "para no hacer.")
    escribir_geojson(inund, WEB_DATA / "areas-riesgo-inundacion.geojson", meta)
    por_tipo = collections.Counter(f["properties"]["tipo_hidrico"] for f in inund)
    log(f"  publicados por fenómeno: {dict(por_tipo)}")

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
