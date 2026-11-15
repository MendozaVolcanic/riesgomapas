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

Desde el 15-nov-2026 lo hídrico sale de GeoIDE (geoide.minvu.cl), otro servidor
del mismo ministerio con una capa por comuna, resolución y fecha: ver
ZONAS_GEOIDE más abajo. El agregado de services3 queda para lo no hídrico y para
las comunas que GeoIDE no cubra.

Requiere: nada del pipeline para la capa misma — opcional: 05_eae_documentos.py
        (data/processed/eae/araucania.json, sólo para agregar la fecha del
        procedimiento EAE; si no está, sigue corriendo sin esa fecha)
Salida: data/processed/areas_riesgo_prc_araucania.geojson
        data/processed/areas_riesgo_prc_reemplazadas_por_geoide.geojson (respaldo)
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


# ---------------------------------------------------------------------------
# GeoIDE del MINVU: la fuente que manda para lo hídrico desde el 15-nov-2026
# ---------------------------------------------------------------------------
#
# El MINVU publica los planes reguladores en DOS servidores, y hasta el 15-nov
# sólo usábamos el agregado de services3. GeoIDE (geoide.minvu.cl) trae una o más
# capas por comuna con la Resolución y la fecha del Diario Oficial, y trae a
# Angol, que el agregado no tiene: por eso creíamos que Angol no tenía vectorial
# y vectorizamos sus láminas a mano (auditoría 15-nov, familias 1 y 2). Lo
# encontró el practicante, que lo cita en su informe del 13-nov.
#
# Decisión de Nicolás (15-nov-2026): GeoIDE reemplaza. Para cada comuna que
# GeoIDE cubre, sus polígonos hídricos salen de GeoIDE y los del agregado
# quedan de respaldo en data/processed, no publicados. Lo no hídrico (remoción
# en masa) sigue saliendo del agregado: este cambio es sólo de inundación.

GEOIDE = "https://geoide.minvu.cl/server/rest/services/IPT/PRC_Araucania/FeatureServer"

# Comuna de cada capa de GeoIDE que aporta zonas hídricas. Explícito y no
# deducido del campo COM, que viene con la localidad («Puerto Saavedra»).
COMUNA_DE_CAPA = {
    "PRC_Angol_Area_de_riesgo": "Angol",
    "PRC_Carahue": "Carahue",
    "PRC_Collipulli_Area_de_riesgo": "Collipulli",
    "PRC_Collipulli": "Collipulli",
    "PRC_Gorbea": "Gorbea",
    "PRC_Loncoche": "Loncoche",
    "PRC_Nueva_Imperial_AR": "Nueva Imperial",
    "PRC_Pitrufquen": "Pitrufquén",
    "PRC_Puerto_Saavedra": "Saavedra",
    "PRC_Renaico_Area_de_riesgo": "Renaico",
    "PRC_Renaico_Tijeral_Area_de_riesgo": "Renaico",
    "PRC_Temuco_Areas_de_proteccion_y_riesgo": "Temuco",
    "PRC_Tolten_Queule_Area_de_riesgo": "Toltén",
    "PRC_Tolten_Villa_OHiggins_Area_de_riesgo": "Toltén",
    "PRC_Tolten_Nueva_Tolten_Area_de_riesgo": "Toltén",
    "PRC_Tolten_Villa_Boldos_Area_de_riesgo": "Toltén",
    "PRC_Traiguen": "Traiguén",
    "PRC_Villarrica": "Villarrica",
}

# Qué zonas de GeoIDE son área de riesgo hídrica y de qué fenómeno.
#
# La llave es (capa, ZONA, NOM) normalizados, y el tipo NO se deduce del texto:
# «zona potencialmente inundable por napa freática» contiene «inundable» y no es
# un desborde; «inundación por tsunami» tampoco. Una heurística sobre el texto
# clasificaba mal las dos. Cuando la fuente no trae texto (Loncoche ZR-2A y
# ZR-2B), el tipo es el que les da la capa nacional del MINVU en
# CLASIFICACION_RIESGOS, y así se declara.
ZONAS_GEOIDE: dict[tuple[str, str, str], tuple[str, str]] = {
    # (capa, ZONA, NOM): (tipo_hidrico, de dónde sale el tipo)
    ("PRC_Angol_Area_de_riesgo", "AR-2A", "AREAS DE RIESGO INUNDABLES O POTENCIALMENTE INUNDABLES"): ("fluvial", "NOM"),
    ("PRC_Angol_Area_de_riesgo", "AR-2B", "AREAS DE RIESGO POR ANEGAMIENTO"): ("anegamiento", "NOM"),
    ("PRC_Carahue", "Z-R10", "Z-R10 ZONA INUNDABLE O POTENCIALMENTE INUNDABLE POR QUEBRADAS"): ("fluvial", "NOM"),
    ("PRC_Carahue", "Z-R9", "Z-R9 ZONA INUNDABLE O POTENCIALMENTE INUNDABLE POR RIOS Y ESTEROS"): ("fluvial", "NOM"),
    ("PRC_Carahue", "ZR1A", "ZR1A AREAS INUNDABLES, ALVEOS O CURSOS DE AGUAS DE DOMINIO PUBLICO"): ("fluvial", "NOM"),
    ("PRC_Carahue", "ZR-1B", "ZR-1B ZONA DE CAUSES NATURALES DE CORRIENTES DISCONTINUAS FORMADAS POR AGUAS PLUVIALES"): ("fluvial", "capa nacional MINVU: INUNDACION"),
    ("PRC_Collipulli_Area_de_riesgo", "ZR-1", "ZR-1 AREA DE RIESGO POR ANEGAMIENTO"): ("anegamiento", "NOM"),
    ("PRC_Collipulli_Area_de_riesgo", "ZR-2", "ZR-2 AREA DE RIESGO POR INUNDACION"): ("fluvial", "NOM"),
    # un canal es un cauce, artificial pero cauce: misma decisión que TIPO_HIDRICO
    ("PRC_Collipulli_Area_de_riesgo", "ZR-3", "ZR-3 AREA EN TORNO A CANALES"): ("fluvial", "NOM"),
    ("PRC_Collipulli_Area_de_riesgo", "ZR-5", "ZR-5 AREA Y/O FRANJA DE RESTRICCION POR QUEBRADAS"): ("fluvial", "NOM"),
    # la capa general de Collipulli trae un ZR-2 y un ZR-5 más, que no se tocan
    # con los de la capa de riesgo (medido: IoU 0 contra todos)
    ("PRC_Collipulli", "ZR-2", "ZR-2 AREA DE RIESGO POR INUNDACION"): ("fluvial", "NOM"),
    ("PRC_Collipulli", "ZR-5", "ZR-5 AREA DE RESTRICCION POR QUEBRADAS"): ("fluvial", "NOM"),
    ("PRC_Gorbea", "AR1", "ZONA INUNDABLE O POTENCIALMENTE INUNDABLE"): ("fluvial", "NOM"),
    ("PRC_Loncoche", "ZR-2A", "ZONA ZR-2A"): ("fluvial", "capa nacional MINVU: INUNDACION"),
    ("PRC_Loncoche", "ZR-2B", "ZONA ZR-2B"): ("fluvial", "capa nacional MINVU: INUNDACION"),
    ("PRC_Nueva_Imperial_AR", "AR-1", "AR-1 AREA DE RIESGOS ZONAS INUNDABLES O POTENCIALMENTE INUNDABLES"): ("fluvial", "NOM"),
    # ⚠️ la fuente se contradice: ZONA dice AR-2 y NOM dice AR-1 (94 ha). Se
    # clasifica por NOM, que es el texto descriptivo, y queda anotado en el
    # polígono (`nota_fuente`).
    ("PRC_Nueva_Imperial_AR", "AR-2", "AR-1 AREA DE RIESGOS ZONAS INUNDABLES O POTENCIALMENTE INUNDABLES"): ("fluvial", "NOM; ZONA dice AR-2"),
    ("PRC_Nueva_Imperial_AR", "AR-2", "AR-2 AREA DE RIESGO ZONA POTENCIALMENTE INUNDABLE POR ANEGAMIENTO"): ("anegamiento", "NOM"),
    ("PRC_Pitrufquen", "R1-A", "AREA R1-A. ZONA INUNDABLE O POTENCIALMENTE INUNDABLE"): ("fluvial", "NOM"),
    ("PRC_Puerto_Saavedra", "INUNDABLE RESTRINGIDA", "SIN INFORMACION"): ("fluvial", "ZONA; capa nacional MINVU: INUNDACION"),
    ("PRC_Renaico_Area_de_riesgo", "AR - 1", "ZONAS INUNDABLES O POTENCIALMENTE INUNDABLES"): ("fluvial", "NOM"),
    ("PRC_Renaico_Tijeral_Area_de_riesgo", "AR-1", "AREA DE RIESGO DE INUNDACION"): ("fluvial", "NOM"),
    # «restricción inundación anegamiento»: la capa nacional lo clasifica ANEGAMIENTO
    ("PRC_Temuco_Areas_de_proteccion_y_riesgo", "ARRI", "ARRI RESTRICCION INUNDACION ANEGAMIENTO"): ("anegamiento", "capa nacional MINVU: ANEGAMIENTO"),
    ("PRC_Tolten_Queule_Area_de_riesgo", "AR-1", "AREA DE RIESGO ZONAS INUNDABLES O POTENCIALMENTE INUNDABLES"): ("fluvial", "NOM"),
    ("PRC_Tolten_Queule_Area_de_riesgo", "AR-2", "AREA DE RIESGO ZONAS POTENCIALMENTE INUNDABLES POR NAPAS FREATICAS"): ("napa_freatica", "NOM"),
    # tsunami: inundación litoral, ni fluvial ni de drenaje (la fuente escribe «Tsuanami»)
    ("PRC_Tolten_Queule_Area_de_riesgo", "AR-3", "AREA DE RIESGO ZONA DE INUNDACION POR TSUANAMI"): ("litoral", "NOM"),
    ("PRC_Tolten_Villa_OHiggins_Area_de_riesgo", "AR-3", "AREA DE RIESGO ZONA DE INUNDACION POR TSUNAMI"): ("litoral", "NOM"),
    ("PRC_Tolten_Nueva_Tolten_Area_de_riesgo", "AR1", "ZONA INUNDABLE POR CERCANIA A RIO"): ("fluvial", "NOM"),
    ("PRC_Tolten_Nueva_Tolten_Area_de_riesgo", "AR2", "ZONA POTENCIALMENTE INUNDABLE POR NAPA FREATICA"): ("napa_freatica", "NOM"),
    ("PRC_Tolten_Nueva_Tolten_Area_de_riesgo", "AR3", "ZONA POTENCIALMENTE INUNDABLE POR CERCANIA A RIO"): ("fluvial", "NOM"),
    ("PRC_Tolten_Nueva_Tolten_Area_de_riesgo", "AR4", "ZONA INUNDABLE POR NAPA FREATICA"): ("napa_freatica", "NOM"),
    ("PRC_Tolten_Villa_Boldos_Area_de_riesgo", "AR1", "ZONA INUNDABLE POR CERCANIA A RIO"): ("fluvial", "NOM"),
    ("PRC_Tolten_Villa_Boldos_Area_de_riesgo", "AR2", "ZONA POTENCIALMEBTE INUNDABLE POR NAPA FREATICA"): ("napa_freatica", "NOM"),
    ("PRC_Traiguen", "ZR1", "ZR1 ZONA DE RIESGO DE INUNDACION"): ("fluvial", "NOM"),
    ("PRC_Villarrica", "ZR-4", "AREAS INUNDABLES"): ("fluvial", "NOM"),
    ("PRC_Villarrica", "ZR-9", "ZONA ZR-9: ZONAINUNDABLE POR QUEBRADAS, CURSOS DE AGUA NO CANALIZADO"): ("fluvial", "NOM"),
}

# Zonas con texto que suena a agua y que NO se publican como área de riesgo
# hídrica. Son franjas de protección de cauces, lechos y riberas: zonificación
# urbana, no un área de riesgo del Art. 2.1.17 por inundación, y la capa
# nacional del MINVU tampoco las clasifica hídricas (eso lo comprueba
# reemplazar_por_geoide). Están listadas para que la exclusión sea una decisión
# visible y no un olvido: lo que no está en ninguna de las dos tablas bota el
# script. Temuco ARC (restricción canal) y ZE7 quedan como decisión pendiente.
EXCLUIDAS_GEOIDE: set[tuple[str, str, str]] = {
    ("PRC_Villarrica", "ZR-2", "ZONA ZR-2 DE PROTECCION VERTIENTE Y CURSOS NATURALES DE AGUA"),
    ("PRC_Villarrica", "ZR-3", "PROTECCION DE VERTIENTES Y CAUCES NATURALES DE AGUA"),
    ("PRC_Villarrica", "ZR-7", "ZONA ZR-7 DE PROTECCION DE LADERAS Y QUEBRADAS NATURALES"),
    ("PRC_Victoria", "ZR-1", "ZR-1; ZONA DE PROTECCION DE VERTIENTES Y CURSOS NATURALES DE AGUA"),
    ("PRC_Temuco", "ZE7", "ZE7 ZONA ESPECIAL RESTRICCION POR ANEGAMIENTO DE INUNDACION"),
    ("PRC_Temuco_Areas_de_proteccion_y_riesgo", "ARC", "ARC RESTRICCION CANAL"),
    ("PRC_Loncoche", "LECHO DE CAUCE NATURAL", "LECHO DE CAUCE NATURAL"),
    ("PRC_Loncoche", "ZR-1", "ZONA DE PROTECCION DE VERTIENTES Y CURSOS NATURALES DE AGUA"),
    ("PRC_Gorbea", "CURSO DE AGUA", "CURSO DE AGUA"),
    ("PRC_Freire_Quepe", "LECHO DE CAUCE NATURAL", "LECHO DE CAUCE NATURAL"),
    ("PRC_Collipulli", "ZAV-2", "ZAV-2 ZONA DE AREAS VERDES CANALES"),
    ("PRC_Collipulli", "ZP-2", "ZP-2 ZONA DE MANEJO DE CAUCE"),
    ("PRC_Carahue", "LECHO DE CAUCE", "LECHO DE CAUCE"),
    ("PRC_Carahue", "ZR1", "ZR1 ZONA DE PROTECCION DE ALVEOS O CURSOS NATURALES DE AGUA"),
    ("PRC_Tolten_Nueva_Tolten", "CURSO DE AGUA", ""),
    ("PRC_Tolten_Villa_Boldos", "CURSO AGUA", ""),
}

# Palabras que obligan a que una zona esté en una de las dos tablas.
PALABRAS_HIDRICAS = ("INUND", "ANEGA", "NAPA", "TSUNAMI", "TSUANAMI", "QUEBRAD",
                     "CANAL", "CAUCE", "CAUSE", "ALVEO", "CURSO", "VERTIENTE")

# Zonas del agregado que GeoIDE reemplaza por OTRA zona, no por la misma.
# Sin esta tabla, reemplazar_por_geoide exige que cada zona hídrica que había
# siga existiendo en GeoIDE.
ZONAS_SUPERADAS = {
    ("NUEVA IMPERIAL", "ZR-1"): "el PRC actualizado (Resolución 111 del 26-07-2025) "
                                "la reemplaza por las zonas AR-1 y AR-2",
}


def _k(s: str | None) -> str:
    return " ".join(norm(s).split())


def _k_zona(s: str | None) -> str:
    return norm(s).replace(" ", "")


def tipo_geoide(capa: str, zona: str | None, nom: str | None) -> str | None:
    """Fenómeno hídrico de una zona de GeoIDE según la tabla, o None."""
    v = ZONAS_GEOIDE.get((capa.strip(), _k(zona), _k(nom)))
    return v[0] if v else None


def seleccionar_geoide(capas: list[tuple[str, list[dict]]]) -> list[dict]:
    """Features ArcGIS de GeoIDE (en EPSG:4326) → polígonos hídricos GeoJSON.

    Se cae si aparece una zona con texto hídrico que ninguna tabla conoce, o si
    una zona de la tabla ya no está en su capa: las dos cosas significan que el
    MINVU cambió el plan y hay que mirarlo, no adivinarlo.
    """
    desconocidas, vistas = set(), set()
    capas_vistas = set()
    out = []
    for capa, feats in capas:
        capa = capa.strip()
        capas_vistas.add(capa)
        for x in feats:
            a = x.get("attributes", {})
            nom = a.get("NOM") or a.get("NOMBRE")
            llave = (capa, _k(a.get("ZONA")), _k(nom))
            if llave in ZONAS_GEOIDE:
                vistas.add(llave)
            elif llave not in EXCLUIDAS_GEOIDE:
                texto = llave[1] + " " + llave[2]
                if any(p in texto for p in PALABRAS_HIDRICAS):
                    desconocidas.add(llave)
                continue
            else:
                continue
            tipo, base = ZONAS_GEOIDE[llave]
            g = anillos_a_geojson(x.get("geometry") or {})
            if not g:
                continue
            doc = " ".join(str(a.get(c) or "").strip() for c in ("T_DO", "N_DOC")).strip()
            p_do = (a.get("P_DO") or "").strip()
            props = {
                "comuna": COMUNA_DE_CAPA[capa],
                "sector": (a.get("LOCALIDAD") or a.get("LOC") or a.get("SECTOR") or "").strip() or None,
                "zona": (a.get("ZONA") or "").strip() or None,
                "nombre": (nom or "").strip() or None,
                "clasificacion": (nom or "").strip() if base.startswith("NOM") else
                                 f"{(a.get('ZONA') or '').strip()} ({base})",
                "usos_prohibidos": (a.get("UPROH") or a.get("UPROM") or "").strip() or None,
                "usos_permitidos": (a.get("UPERM") or "").strip() or None,
                "ordenanza_url": None,
                "ordenanza_url_vigente": False,
                "es_inundacion": True,
                "tipo_hidrico": tipo,
                "tipo_hidrico_segun": base,
                "origen_capa": f"GeoIDE {capa}",
                "instrumento": (f"{doc} del {p_do}" if doc and p_do else doc or None),
                **sello("MINVU GeoIDE: áreas de riesgo del Plan Regulador Comunal "
                        "(Art. 2.1.17 OGUC)", p_do[-4:] if len(p_do) >= 4 else None),
            }
            if p_do:
                props["anio_fuente"] = "GeoIDE MINVU, fecha de publicación en el Diario Oficial (P_DO)"
            if "ZONA dice" in base:
                props["nota_fuente"] = ("la fuente se contradice: el campo ZONA dice "
                                        f"{props['zona']} y el nombre dice AR-1; se clasificó por el nombre")
            out.append({"type": "Feature", "geometry": g, "properties": props})
    faltan = {k for k in ZONAS_GEOIDE if k[0] in capas_vistas} - vistas
    if desconocidas or faltan:
        raise SystemExit(
            "GeoIDE cambió respecto de la tabla revisada a mano.\n"
            f"  zonas con texto hídrico que ninguna tabla conoce: {sorted(desconocidas)}\n"
            f"  zonas de ZONAS_GEOIDE que ya no están en su capa: {sorted(faltan)}\n"
            "Revisa cada una y agrégala a ZONAS_GEOIDE o a EXCLUIDAS_GEOIDE: "
            "clasificarla por parecido es poner un área con efecto legal donde no va.")
    return out


def desde_geoide() -> list[dict]:
    """Descarga TODAS las capas de GeoIDE de La Araucanía, no sólo las de la
    tabla: así una zona hídrica nueva en una capa que no mirábamos bota el
    script en vez de quedar fuera. outSR=4326 lo pide consultar_capa_arcgis;
    no se reproyecta a mano (la descarga de la auditoría venía en 32719 sin
    declararlo, y leída como 32718 daba 0 % de solape).
    """
    log("GeoIDE MINVU, servicio IPT/PRC_Araucania")
    info = get_json(GEOIDE, {"f": "json"})
    capas = []
    for capa in info.get("layers", []):
        feats = consultar_capa_arcgis(f"{GEOIDE}/{capa['id']}", campos="*")
        capas.append((capa["name"], feats))
    out = seleccionar_geoide(capas)
    log(f"  {len(capas)} capas, {len(out)} polígonos hídricos")
    return out


def reemplazar_por_geoide(agregado: list[dict], geoide: list[dict]) -> tuple[list[dict], list[dict]]:
    """Para cada comuna que GeoIDE cubre, sus hídricos del agregado se retiran.

    Devuelve (lo que queda + GeoIDE, lo retirado). Se cae si una zona hídrica
    del agregado no aparece en GeoIDE para esa comuna y no está en
    ZONAS_SUPERADAS: reemplazar no puede ser perder un área de riesgo.
    """
    cubiertas = {norm(f["properties"]["comuna"]) for f in geoide}
    zonas_geoide = {(norm(f["properties"]["comuna"]), _k_zona(f["properties"]["zona"]))
                    for f in geoide}
    quedan, retiradas, perdidas = [], [], set()
    for f in agregado:
        p = f["properties"]
        c = norm(p.get("comuna"))
        if p.get("es_inundacion") and c in cubiertas:
            retiradas.append(f)
            z = _k_zona(p.get("zona"))
            if (c, z) not in zonas_geoide and (c, z) not in ZONAS_SUPERADAS:
                perdidas.add((p.get("comuna"), p.get("zona")))
        else:
            quedan.append(f)
    if perdidas:
        raise SystemExit(
            f"zonas hídricas del agregado que GeoIDE no trae: {sorted(perdidas)}. "
            "O falta en ZONAS_GEOIDE, o el plan la cambió y va en ZONAS_SUPERADAS "
            "con su razón.")
    return quedan + geoide, retiradas


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
    # Primero se corrige el nombre de comuna del agregado (abajo se hace para
    # todos, pero el reemplazo cruza por comuna y «Puerto Saavedra» no calzaría
    # con «Saavedra»).
    _corr = {norm(k): v for k, v in (cfg.get("correcciones_nombre_comuna") or {}).items()}
    for f in feats:
        bruto = (f["properties"].get("comuna") or "").strip()
        if norm(bruto) in _corr:
            f["properties"]["comuna_fuente"] = bruto
            f["properties"]["comuna"] = _corr[norm(bruto)]
    feats, retiradas = reemplazar_por_geoide(feats, desde_geoide())
    for f in retiradas:
        f["properties"]["reemplazado_por"] = "GeoIDE MINVU (decisión 15-nov-2026)"
    log(f"  {len(retiradas)} polígonos hídricos del agregado quedan de respaldo, "
        "reemplazados por GeoIDE")

    eae = fechas_eae_por_comuna()
    for f in feats:
        info = eae.get(norm(f["properties"]["comuna"]))
        if info:
            f["properties"]["eae_procedimiento"] = info["procedimiento"]
            f["properties"]["eae_fecha_ingreso"] = info["fecha"]
            f["properties"]["eae_estado"] = info["estado"]

    meta = procedencia(
        fuente="MINVU — Áreas de riesgo de Instrumentos de Planificación Territorial",
        url=GEOIDE,
        metodo="Las áreas de riesgo hídricas salen de GeoIDE del MINVU "
               "(IPT/PRC_Araucania, una o más capas por comuna, con resolución y "
               "fecha del Diario Oficial), clasificadas por una tabla revisada a "
               "mano zona por zona. Para las comunas que GeoIDE no cubre, y para "
               "lo no hídrico, la capa nacional de áreas de riesgo PRC filtrada a "
               "La Araucanía más el servicio regional 09_PRC_La_Araucania. Cada "
               "polígono dice su capa de origen en `origen_capa`. Conversión de "
               "anillos ArcGIS a GeoJSON respetando el signo del área para los huecos.",
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
        # La fecha del Diario Oficial que trae GeoIDE es del instrumento mismo y
        # gana sobre el catastro: el Atlas daba 2012 a todo Toltén, y Nueva
        # Toltén y Villa Boldos son de la Resolución 38 de 2026.
        if f["properties"].get("anio_fuente"):
            continue
        # GeoIDE ya trae el nombre oficial («Saavedra») y no deja comuna_fuente,
        # así que también se prueban los nombres que la tabla de correcciones
        # asocia a esa comuna: sin esto Saavedra perdió su 1964.
        oficial = (f["properties"].get("comuna") or "").strip()
        a = (anios.get(oficial)
             or anios.get((f["properties"].get("comuna_fuente") or "").strip())
             or next((anios[k] for k, v in (cfg.get("correcciones_nombre_comuna") or {}).items()
                      if v == oficial and k in anios), None))
        if a:
            f["properties"]["anio"] = a
            f["properties"]["anio_fuente"] = ("Atlas del Riesgo de Desastre, "
                                              "Vicuña y Guzmán, CIGIDEN/IEUT-UC 2025")
            puestos += 1
    log(f"  año del instrumento asignado a {puestos} de {len(feats)} polígonos "
        f"({len(anios)} comunas con año conocido)")

    escribir_geojson(feats, DATA_PROC / "areas_riesgo_prc_araucania.geojson", meta)
    # El respaldo: lo que el agregado decía para las comunas que GeoIDE cubre.
    # No se publica, pero se guarda para poder comparar versiones.
    escribir_geojson(retiradas, DATA_PROC / "areas_riesgo_prc_reemplazadas_por_geoide.geojson",
                     {**meta, "metodo": "Polígonos hídricos del agregado nacional y regional "
                      "del MINVU retirados porque GeoIDE publica la misma comuna con "
                      "resolución y fecha; respaldo, no se publican."})

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
