"""Población expuesta — Censo 2024 por unidad censal, para La Araucanía.

Qué es: el conteo oficial de personas y viviendas, ya georreferenciado como
polígonos. Responde la pregunta que la gente hace después de «¿se inunda acá?»,
que es «¿cuánta gente vive ahí?».

LO QUE HAY QUE SABER ANTES DE USARLO, y es la razón de que este script exista en
vez de una descarga a mano:

1. La región NO está en una sola capa. Son tres unidades geográficas distintas
   —manzanas urbanas, entidades rurales y aldeas— y hay que unir las tres para
   cubrir el territorio. Las capas 3 y 4 del servicio (zonas censales, distritos)
   son AGREGACIONES de éstas: sumarlas cuenta la misma gente dos veces.

2. Urbano y rural no son comparables en superficie. En Angol una manzana urbana
   mide ~116x119 m con 39 personas; una entidad rural ~543x770 m con 7. Treinta
   veces el área con un quinto de la gente. Por eso cada polígono sale etiquetado
   con `unidad_censal`: calcular densidad sobre la mezcla no significa nada.

3. El servicio almacena en EPSG:4674 (SIRGAS 2000). Este script pide `outSR=4326`,
   así que la salida es WGS84 — grados igual. La superficie se calcula
   reproyectando a UTM 18S/19S, nunca sobre los grados.

Límite del proyecto, no negociable: agregado por unidad censal, NUNCA por persona.

Fuente: Microdatos Censo 2024, servicio de Esri Chile (espejo, no del INE).
Salida: data/processed/censo/censo-2024-araucania.geojson
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    DATA_PROC,
    anillos_a_geojson,
    consultar_capa_arcgis,
    get_json,
    escribir_geojson,
    log,
    procedencia,
    sello,
)

SERVICIO = (
    "https://services.arcgis.com/r7t1P5pnkoOLRdhr/arcgis/rest/services"
    "/Microdatos_Censo_2024/FeatureServer"
)
REGION = 9

# Las tres capas que juntas cubren el territorio. Las capas 3 y 4 del servicio son
# agregaciones de éstas y NO se descargan: sumarlas duplicaría la población.
CAPAS = {
    0: "manzana_urbana",
    1: "entidad_rural",
    2: "aldea",
}

# Control de integridad: verificado contra el servicio el 2026-08-14. Si el servicio
# se actualiza estos números cambian, y queremos enterarnos en vez de publicar en
# silencio un total distinto del que dicen nuestros documentos.
ESPERADO = {
    "manzana_urbana": (12_886, 691_173),
    "entidad_rural": (4_188, 312_373),
    "aldea": (33, 17_887),
}

# De los 216 campos nos quedamos con los que sirven para exposición a inundación.
# Traer los 216 hace un archivo inmanejable y la mayoría son de otras preguntas.
CAMPOS = [
    # identificación territorial
    "COD_REGION", "COD_PROVINCIA", "CUT", "NOM_REGION", "NOM_PROVINCIA", "NOM_COMUNA",
    "COD_MANZANA", "MANZENT", "AREA_C",
    # conteo
    "n_per", "n_hombres", "n_mujeres",
    # grupos que condicionan la evacuación
    "n_edad_0_5", "n_edad_60_mas", "n_discapacidad",
    # vulnerabilidad de la vivienda
    "n_viv_hacinadas", "n_mat_paredes_precarios", "n_mat_techo_precarios",
    "n_tipo_viv_mediagua", "n_hog_allegados", "n_jefatura_mujer",
    # agua: relevante porque la crecida contamina la captación
    "n_fuente_agua_publica", "n_fuente_agua_pozo", "n_fuente_agua_camion",
    "n_fuente_agua_rio", "n_distrib_agua_acarreo",
]


def campos_de(capa_url: str) -> list[str]:
    """Los campos pedidos que esa capa realmente tiene.

    Las tres capas NO comparten esquema: pedirle a la de entidades rurales un campo
    que sólo existe en la de manzanas hace que ArcGIS rechace la consulta entera con
    `'outFields' parameter is invalid`, y se pierde la capa completa. Se intersecta
    contra el esquema real y se informa lo que falta, en vez de suponerlo.
    """
    reales = {f["name"] for f in get_json(capa_url, {"f": "json"}).get("fields", [])}
    hay = [c for c in CAMPOS if c in reales]
    faltan = [c for c in CAMPOS if c not in reales]
    if faltan:
        log(f"   sin estos campos en esta capa: {', '.join(faltan)}")
    if "n_per" not in hay:
        raise SystemExit(f"{capa_url} no tiene `n_per`: sin población no sirve.")
    return hay


def main() -> None:
    todas: list[dict] = []
    resumen: list[tuple[str, int, int]] = []

    for capa_id, unidad in CAPAS.items():
        log(f"capa {capa_id} — {unidad}")
        crudos = consultar_capa_arcgis(
            f"{SERVICIO}/{capa_id}",
            where=f"COD_REGION={REGION}",
            campos=",".join(campos_de(f"{SERVICIO}/{capa_id}")),
        )

        feats = []
        for x in crudos:
            g = anillos_a_geojson(x.get("geometry"))
            if g is None:          # sin geometría no sirve para cruzar con nada
                continue
            feats.append({"type": "Feature", "geometry": g,
                          "properties": dict(x.get("attributes") or {})})

        if len(feats) != len(crudos):
            log(f"   {len(crudos) - len(feats)} sin geometría, descartados")
        poblacion = sum(int(f["properties"].get("n_per") or 0) for f in feats)

        esp_n, esp_p = ESPERADO[unidad]
        if (len(feats), poblacion) != (esp_n, esp_p):
            raise SystemExit(
                f"El servicio cambió para «{unidad}»: llegaron {len(feats)} polígonos "
                f"y {poblacion} personas, se esperaban {esp_n} y {esp_p}.\n"
                "No se publica nada. Revisa la fuente y actualiza ESPERADO y los "
                "documentos que citan estas cifras (docs/GUIA_PRACTICANTE.md)."
            )

        # La etiqueta va pegada a cada feature: en cuanto se filtra o se mezcla en un
        # mapa, saber si un polígono es urbano o rural deja de ser opcional.
        for f in feats:
            f["properties"]["unidad_censal"] = unidad
            f["properties"].update(sello("Censo 2024 (INE, vía Esri Chile)", 2024))

        todas.extend(feats)
        resumen.append((unidad, len(feats), poblacion))
        log(f"   {len(feats):>6} polígonos · {poblacion:>9,} personas")

    destino = DATA_PROC / "censo" / "censo-2024-araucania.geojson"
    destino.parent.mkdir(parents=True, exist_ok=True)
    escribir_geojson(
        todas,
        destino,
        meta=procedencia(
            fuente="Censo de Población y Vivienda 2024 (INE), servicio de Esri Chile",
            url=SERVICIO,
            metodo=(
                "Descarga paginada de las capas 0 (manzanas urbanas), 1 (entidades "
                "rurales) y 2 (aldeas) filtradas por COD_REGION=9, reproyectadas a "
                "EPSG:4326 por el servicio, unidas y "
                "etiquetadas con `unidad_censal`. Las capas 3 y 4 son agregaciones "
                "de éstas y se omiten a propósito para no duplicar población."
            ),
            capa_evidencia="D_operacional",
            incertidumbre=(
                "Espejo de Esri Chile, no del INE: contrastar totales comunales antes "
                "de publicar. Urbano y rural NO son comparables en superficie, filtrar "
                "por `unidad_censal` antes de calcular densidad."
            ),
            escala_original="unidad censal (manzana, entidad o aldea)",
            fecha_dato="2024",
        ),
    )

    total_n = sum(n for _, n, _ in resumen)
    total_p = sum(p for _, _, p in resumen)
    log("")
    for unidad, n, p in resumen:
        log(f"  {unidad:16} {n:>6} polígonos  {p:>9,} personas")
    log(f"  {'TOTAL':16} {total_n:>6} polígonos  {total_p:>9,} personas")
    log(f"\n{destino} · {destino.stat().st_size / 1e6:.1f} MB")
    log("Salida en EPSG:4326 (grados). Reproyecta a UTM antes de medir áreas.")


if __name__ == "__main__":
    main()
