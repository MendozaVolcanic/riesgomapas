"""Campamentos dentro de áreas de riesgo por inundación.

Qué agrega: hasta acá el visor respondía "este terreno está en un área de riesgo".
Esta capa responde la pregunta que sigue y que es la que importa —**cuánta gente
vive ahí**— sin que tengamos que estimarla nosotros: MINVU publica el Catastro
Nacional de Campamentos con el número de hogares de cada uno y si cae dentro de
un área de riesgo del instrumento de planificación.

En La Araucanía son 15 campamentos en área de riesgo por inundación, con 537
hogares, casi todos en Temuco.

Un cuidado que no es menor: esto identifica asentamientos de familias en
situación de vulnerabilidad. Se publica lo que MINVU ya publica —nombre, comuna,
número de hogares, tipo de riesgo— y nada más. No se agrega ningún dato que
permita identificar personas, ni se cruza con otras fuentes para enriquecer el
perfil de esos hogares.

Fuente: services3.arcgis.com/cTnMkBRk4HWkUCRo — `Campamentos_AR_2024/3`
Salida: data/processed/campamentos_araucania.geojson
        web/data/campamentos-inundacion.geojson
"""
from __future__ import annotations

import collections
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    DATA_PROC,
    WEB_DATA,
    consultar_capa_arcgis,
    escribir_geojson,
    log,
    procedencia,
    sello,
)

CAPA = ("https://services3.arcgis.com/cTnMkBRk4HWkUCRo/arcgis/rest/services"
        "/Campamentos_AR_2024/FeatureServer/3")

CLAVES_HIDRICAS = ("INUND", "INDUND", "ANEGAM", "TSUNAMI")  # el dato trae la errata


def norm(t) -> str:
    return unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().upper()


def es_hidrico(tipo) -> bool:
    return any(k in norm(tipo) for k in CLAVES_HIDRICAS)


def anillos_a_geojson(geom: dict) -> dict | None:
    """Mismo criterio que en el script 06: el signo del área separa exteriores
    de huecos, porque GeoJSON no comparte la convención de orientación ArcGIS."""
    anillos = (geom or {}).get("rings") or []
    if not anillos:
        return None

    def area(a):
        return sum((a[i][0] * a[i + 1][1] - a[i + 1][0] * a[i][1])
                   for i in range(len(a) - 1)) / 2.0

    ext, huecos = [], []
    for a in anillos:
        if len(a) < 4:
            continue
        (ext if area(a) < 0 else huecos).append([[float(x), float(y)] for x, y, *_ in a])
    if not ext:
        ext = [[[float(x), float(y)] for x, y, *_ in a] for a in anillos if len(a) >= 4]
        huecos = []
    if not ext:
        return None
    polis = [[e] for e in ext]
    for h in huecos:
        polis[0].append(h)
    return ({"type": "Polygon", "coordinates": polis[0]} if len(polis) == 1
            else {"type": "MultiPolygon", "coordinates": polis})


def anio_catastro(valor) -> str | None:
    """`AN_CAT` viene como 'CATASTRO_2022'. Se extrae el año, y si viene en
    blanco se deja que `sello()` lo declare como no informado."""
    d = "".join(c for c in str(valor or "") if c.isdigit())
    return d if len(d) == 4 else None


def main() -> None:
    log("catastro de campamentos MINVU")
    feats_raw = consultar_capa_arcgis(CAPA, where="REGION LIKE '%raucan%'", campos="*")
    log(f"  {len(feats_raw)} campamentos en La Araucanía")

    feats = []
    for x in feats_raw:
        a = x.get("attributes", {})
        g = anillos_a_geojson(x.get("geometry"))
        if not g:
            continue
        hogares = int(a.get("N_HOG") or 0)
        tipo = (a.get("TIP_AR_IPT") or "").strip()
        feats.append({
            "type": "Feature",
            "geometry": g,
            "properties": {
                "nombre": (a.get("NOMBRE") or "").strip() or None,
                "comuna": (a.get("COMUNA") or "").strip() or None,
                "hogares": hogares,
                "hectareas": round(float(a.get("HECTAREAS") or 0), 2),
                "en_area_riesgo": bool(a.get("AR_IPT")),
                "tipo_riesgo": tipo or None,
                "es_inundacion": es_hidrico(tipo),
                "levantado_por": (a.get("FUENTE") or "").strip() or None,
                **sello("MINVU — Catastro Nacional de Campamentos",
                        anio_catastro(a.get("AN_CAT"))),
            },
        })

    meta = procedencia(
        fuente="MINVU — Catastro Nacional de Campamentos, con marca de área de "
               "riesgo del instrumento de planificación territorial",
        url=CAPA,
        metodo="Descarga vía ArcGIS REST filtrada a La Araucanía. El cruce con el "
               "área de riesgo lo hace MINVU en origen (campos AR_IPT y "
               "TIP_AR_IPT); acá no se recalcula.",
        capa_evidencia="D_operacional",
        incertidumbre="El año de catastro cambia por campamento (2019 o 2022) y en "
                      "algunos no está informado. Un campamento puede haberse "
                      "erradicado o crecido desde entonces. El número de hogares "
                      "es el del levantamiento, no un dato actual.",
    )

    escribir_geojson(feats, DATA_PROC / "campamentos_araucania.geojson", meta)
    inund = [f for f in feats if f["properties"]["es_inundacion"]]
    escribir_geojson(inund, WEB_DATA / "campamentos-inundacion.geojson", meta)

    hog_total = sum(f["properties"]["hogares"] for f in feats)
    hog_inund = sum(f["properties"]["hogares"] for f in inund)
    log("")
    log(f"TOTAL: {len(feats)} campamentos, {hog_total} hogares")
    log(f"  en área de riesgo por inundación: {len(inund)} campamentos, "
        f"{hog_inund} hogares")
    log("")
    log("Por comuna (sólo los de riesgo por inundación):")
    por = collections.Counter()
    hog = collections.Counter()
    for f in inund:
        p = f["properties"]
        por[p["comuna"]] += 1
        hog[p["comuna"]] += p["hogares"]
    for c, n in por.most_common():
        log(f"  {n:3d} campamentos · {hog[c]:4d} hogares · {c}")
    log("")
    log("Los de mayor población:")
    for f in sorted(inund, key=lambda f: -f["properties"]["hogares"])[:8]:
        p = f["properties"]
        log(f"  {p['hogares']:4d} hogares · {p['comuna']:16s} {str(p['nombre'])[:38]:40s} "
            f"({p['anio']})")


if __name__ == "__main__":
    main()
