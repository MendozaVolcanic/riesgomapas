"""Población expuesta: Censo 2024 por unidad censal, para La Araucanía.

Qué es: el conteo oficial de personas y viviendas, ya georreferenciado como
polígonos. Responde la pregunta que la gente hace después de «¿se inunda acá?»,
que es «¿cuánta gente vive ahí?».

LO QUE HAY QUE SABER ANTES DE USARLO, y es la razón de que este script exista en
vez de una descarga a mano:

1. El territorio lo cubren DOS capas, no tres: manzanas y entidades rurales. La
   capa de aldeas parece una tercera unidad y no lo es: cada una de las 33 aldeas
   es la suma exacta de sus manzanas de tipo «ALDEA» (505 manzanas, 17.887
   personas), que ya vienen en la capa de manzanas. Hasta el 15-nov-2026 este
   script sumaba las tres y contaba a esa gente dos veces (F-300 de la auditoría
   de esa fecha): la región daba 1.021.433 en vez de 1.003.546. Las capas zonal,
   distrital, de localidades y de límite urbano también son agregaciones.

2. Urbano y rural no son comparables en superficie. En Angol una manzana urbana
   mide ~116x119 m con 39 personas; una entidad rural ~543x770 m con 7. Treinta
   veces el área con un quinto de la gente. Por eso cada polígono sale etiquetado
   con `unidad_censal`: `manzana_urbana`, `manzana_aldea` (rural, pero con forma
   de manzana) o `entidad_rural`. Calcular densidad sobre la mezcla no significa
   nada.

3. El GPKG viene en EPSG:4674 (SIRGAS 2000). La salida se reproyecta a EPSG:4326;
   entre los dos datums la diferencia es submétrica. La superficie se calcula
   reproyectando a UTM 18S/19S, nunca sobre los grados.

Límite del proyecto, no negociable: agregado por unidad censal, NUNCA por persona.

Fuente: Cartografía censal del Censo 2024, GPKG de la Región de La Araucanía
publicado por el INE (archivo fijo, verificado por sha256). Hasta el 15-nov-2026
se bajaba del servicio de Esri Chile, que es el mismo dato (17 campos, cero
diferencias, verificación C de esa fecha).
Requiere: nada (baja el GPKG del INE si no está en data/raw/censo_ine_2024_R09/)
Salida: data/processed/censo/censo-2024-araucania.geojson
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    DATA_PROC,
    DATA_RAW,
    descargar,
    escribir_geojson,
    log,
    procedencia,
    sello,
)

URL = ("https://storage.googleapis.com/bktdescargascenso2024/Cartografia/GPKG/"
       "Cartografia_censo2024_R09.zip")
DIR_RAW = DATA_RAW / "censo_ine_2024_R09"
ZIP = DIR_RAW / "Cartografia_censo2024_R09.zip"
GPKG = DIR_RAW / "Cartografia_censo2024_R09.gpkg"
# Bajados el 15-nov-2026. Si el INE publica otra versión el hash cambia y el
# script se detiene: queremos enterarnos antes de publicar otro total.
SHA256_GPKG = "3c6f0eed77f09641b23ad5a73018177449a9ba84efd974f7128b268ffd101ce5"

CAPA_MANZANAS = "Manzanas_CPV24"
CAPA_ENTIDADES = "Entidades_CPV24"
CAPA_ALDEAS = "Aldeas_CPV24"     # se lee sólo para comprobar que duplica

# Control de integridad por unidad: (polígonos, personas). Verificado contra el
# GPKG del INE el 15-nov-2026.
ESPERADO = {
    "manzana_urbana": (12_381, 673_286),
    "manzana_aldea": (505, 17_887),
    "entidad_rural": (4_188, 312_373),
}

# De los ~210 campos nos quedamos con los que sirven para exposición a inundación.
# Los nombres de comuna, provincia y región se renombran a los del esquema que ya
# consumen los scripts siguientes (NOM_COMUNA, etc.).
RENOMBRE = {"COMUNA": "NOM_COMUNA", "PROVINCIA": "NOM_PROVINCIA", "REGION": "NOM_REGION"}
CAMPOS = [
    # identificación territorial
    "COD_REGION", "COD_PROVINCIA", "CUT", "REGION", "PROVINCIA", "COMUNA",
    "COD_MANZANA", "MANZENT", "ID_ENTIDAD", "ENTIDAD", "AREA_C", "TIPO_MZ",
    # conteo
    "n_per", "n_hombres", "n_mujeres",
    # grupos que condicionan la evacuación
    "n_edad_0_5", "n_edad_60_mas", "n_discapacidad",
    # vulnerabilidad de la vivienda
    "n_viv_hacinadas", "n_mat_paredes_precarios", "n_mat_techo_precarios",
    "n_tipo_viv_mediagua", "n_hog_allegados", "n_jefatura_mujer",
    # agua: relevante porque la crecida contamina la captación. Ojo: el INE
    # cuenta VIVIENDAS en estos campos, no hogares (F-308).
    "n_fuente_agua_publica", "n_fuente_agua_pozo", "n_fuente_agua_camion",
    "n_fuente_agua_rio", "n_distrib_agua_acarreo",
]


def _n(v) -> int:
    return int(v or 0)


def unidades_censales(manzanas: list[dict], entidades: list[dict],
                      aldeas: list[dict]) -> list[dict]:
    """Las unidades que cubren el territorio una sola vez, rotuladas.

    Recibe los atributos de las tres capas (con o sin geometría, se devuelven los
    mismos objetos) y devuelve manzanas más entidades, sin las aldeas. Antes de
    omitir las aldeas comprueba que cada una sea exactamente la suma de sus
    manzanas «ALDEA»: si no lo fuera, omitirlas perdería gente, y eso es dato
    incoherente que detiene el script (REGLAS §2), no algo que se arregla solo.
    """
    por_aldea: dict = {}
    for m in manzanas:
        if m.get("TIPO_MZ") == "ALDEA":
            por_aldea[m.get("ID_ENTIDAD")] = por_aldea.get(m.get("ID_ENTIDAD"), 0) + _n(m["n_per"])
    malas = [(a.get("ENTIDAD"), _n(a["n_per"]), por_aldea.get(a.get("ID_ENTIDAD"), 0))
             for a in aldeas if _n(a["n_per"]) != por_aldea.get(a.get("ID_ENTIDAD"), 0)]
    if malas:
        raise SystemExit(
            "Hay aldeas que NO son la suma de sus manzanas «ALDEA» (aldea, n_per, "
            f"suma de manzanas): {malas[:5]}.\nOmitir la capa de aldeas perdería "
            "gente. Revisa la versión del censo antes de seguir.")
    if len(por_aldea) != len(aldeas):
        raise SystemExit(
            f"{len(por_aldea)} entidades con manzanas «ALDEA» y {len(aldeas)} aldeas: "
            "la relación entre capas cambió. Revisa la versión del censo.")

    salida = []
    for m in manzanas:
        tipo = m.get("TIPO_MZ")
        if tipo not in ("URBANO", "ALDEA"):
            raise SystemExit(f"TIPO_MZ desconocido en una manzana: {tipo!r}")
        m["unidad_censal"] = "manzana_aldea" if tipo == "ALDEA" else "manzana_urbana"
        salida.append(m)
    for e in entidades:
        e["unidad_censal"] = "entidad_rural"
        salida.append(e)
    return salida


def _gpkg() -> Path:
    if not GPKG.exists():
        descargar(URL, ZIP)
        with zipfile.ZipFile(ZIP) as z:
            nombre = next(n for n in z.namelist() if n.endswith(".gpkg"))
            GPKG.write_bytes(z.read(nombre))
    h = hashlib.sha256(GPKG.read_bytes()).hexdigest()
    if h != SHA256_GPKG:
        raise SystemExit(
            f"{GPKG.name} tiene sha256 {h}, se esperaba {SHA256_GPKG}.\n"
            "El INE publicó otra versión o el archivo está truncado. No se publica "
            "nada: revisa la fuente y actualiza SHA256_GPKG, ESPERADO y los "
            "documentos que citan estas cifras.")
    return GPKG


def _features(capa: str, campos: list[str] | None) -> list[dict]:
    import geopandas as gpd

    g = gpd.read_file(_gpkg(), layer=capa)
    if campos is not None:
        g = g[[c for c in campos if c in g.columns] + ["geometry"]]
    g = g.to_crs(4326)
    feats = json.loads(g.to_json(drop_id=True))["features"]
    # Los conteos vienen como float en el GPKG; a enteros, sin perder nada.
    for f in feats:
        p = f["properties"]
        for k, v in list(p.items()):
            if isinstance(v, float) and v.is_integer() and (k.startswith("n_") or
                                                            k in ("CUT", "MANZENT", "ID_ENTIDAD")):
                p[k] = int(v)
    return [f for f in feats if f.get("geometry")]


def main() -> None:
    log(f"GPKG del INE: {_gpkg()}")
    manzanas = _features(CAPA_MANZANAS, CAMPOS)
    entidades = _features(CAPA_ENTIDADES, CAMPOS)
    aldeas = _features(CAPA_ALDEAS, ["ID_ENTIDAD", "ENTIDAD", "n_per"])
    log(f"  {len(manzanas)} manzanas, {len(entidades)} entidades, "
        f"{len(aldeas)} aldeas (sólo para comprobar)")

    props = unidades_censales([f["properties"] for f in manzanas],
                              [f["properties"] for f in entidades],
                              [f["properties"] for f in aldeas])
    log(f"  las {len(aldeas)} aldeas son la suma exacta de sus manzanas: se omiten")
    todas = manzanas + entidades
    assert len(props) == len(todas)

    resumen = []
    for unidad, (esp_n, esp_p) in ESPERADO.items():
        sel = [f for f in todas if f["properties"]["unidad_censal"] == unidad]
        pob = sum(_n(f["properties"]["n_per"]) for f in sel)
        if (len(sel), pob) != (esp_n, esp_p):
            raise SystemExit(
                f"El censo cambió para «{unidad}»: {len(sel)} polígonos y {pob} "
                f"personas, se esperaban {esp_n} y {esp_p}.\nNo se publica nada. "
                "Revisa la fuente y actualiza ESPERADO y los documentos que citan "
                "estas cifras (docs/GUIA_PRACTICANTE.md).")
        resumen.append((unidad, len(sel), pob))

    for f in todas:
        p = f["properties"]
        for viejo, nuevo in RENOMBRE.items():
            if viejo in p:
                p[nuevo] = p.pop(viejo)
        p.update(sello("Censo 2024 (INE)", 2024))

    destino = DATA_PROC / "censo" / "censo-2024-araucania.geojson"
    escribir_geojson(
        todas,
        destino,
        meta=procedencia(
            fuente="Censo de Población y Vivienda 2024 (INE), cartografía censal GPKG R09",
            url=URL,
            metodo=(
                "Lectura de las capas Manzanas_CPV24 y Entidades_CPV24 del GPKG del "
                "INE (sha256 verificado), reproyectadas de EPSG:4674 a EPSG:4326 y "
                "etiquetadas con `unidad_censal` (manzana_urbana, manzana_aldea, "
                "entidad_rural) según TIPO_MZ. La capa Aldeas_CPV24 se omite porque "
                "cada aldea es la suma exacta de sus manzanas «ALDEA»; el script lo "
                "comprueba antes de omitirla. Las capas zonal, distrital, de "
                "localidades y de límite urbano son agregaciones y no se usan."
            ),
            capa_evidencia="D_operacional",
            incertidumbre=(
                "Conteo censal oficial, sin error de muestreo. Urbano y rural NO son "
                "comparables en superficie: filtrar por `unidad_censal` antes de "
                "calcular densidad. Los campos n_fuente_agua_* cuentan viviendas, "
                "no hogares."
            ),
            escala_original="unidad censal (manzana o entidad rural)",
            fecha_dato="2024",
        ),
    )

    log("")
    for unidad, n, p in resumen:
        log(f"  {unidad:16} {n:>6} polígonos  {p:>9,} personas")
    log(f"  {'TOTAL':16} {sum(r[1] for r in resumen):>6} polígonos  "
        f"{sum(r[2] for r in resumen):>9,} personas")
    log(f"\n{destino} · {destino.stat().st_size / 1e6:.1f} MB")
    log("Salida en EPSG:4326 (grados). Reproyecta a UTM antes de medir áreas.")


if __name__ == "__main__":
    main()
