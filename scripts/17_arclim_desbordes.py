"""Capa C — ARClim: inundación por desborde de ríos (MMA).

Por qué importa para este proyecto: es la única fuente encontrada que dice algo
sobre desborde de cauce en comunas donde **no existe ningún documento**. Cinco de
las siete comunas sin un solo PDF —incluida Padre Las Casas, el vacío más grave
de la región— tienen sitio en ARClim. No reemplaza un estudio local, pero deja de
ser un hueco absoluto.

Qué es: el Atlas de Riesgos Climáticos del Ministerio del Medio Ambiente publica
una cadena de impacto «Inundaciones por Desbordes de Ríos», elaborada por la
Facultad de Ciencias Físicas y Matemáticas de la Universidad de Chile y
actualizada en 2022 por MMA / Naciones Unidas / Centro de Cambio Global UC. Son
**252 sitios de análisis en centros poblados de todo Chile**, 46 de ellos en La
Araucanía, cada uno con río asociado y con índices de amenaza, exposición,
vulnerabilidad y riesgo para períodos de retorno de 25, 50 y 100 años, en
condición presente y proyectada a 2035-2065.

QUÉ NO ES, y hay que decirlo antes que cualquier cifra
-------------------------------------------------------
**No es una mancha de inundación.** Es un punto por localidad con un índice
adimensional entre 0 y 1. No dice hasta dónde llega el agua, así que no puede
responder «¿se inunda mi casa?». Entra como capa C —modelado— y a escala de
localidad, no de predio.

**El índice de amenaza PRESENTE no mide amenaza.** Verificado sobre los 252
sitios del país: `ind_amenaza_t25_presente` vale 0,4 en todos; `t50` vale 0,6 en
todos; `t100` vale 0,8 en todos. Es una recodificación del período de retorno,
constante en el territorio: no distingue Temuco de Lonquimay. Publicarlo como si
midiera peligro local sería inventar una diferencia que el dato no tiene, así que
este script **lo excluye de la salida** y deja constancia del motivo.

Lo que sí varía —y por tanto sí informa— es la amenaza **futura** (el cambio
proyectado por clima), la exposición, la vulnerabilidad y el riesgo resultante.

El script se cae si la fuente cambia de tamaño o si la constante deja de serlo:
un pipeline que publica en silencio números distintos de los documentados es peor
que uno que falla.

Requiere: nada (baja del ArcGIS de ARClim/MMA)
Salida: data/processed/arclim/desbordes-araucania.geojson
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    DATA_PROC, cargar_config, escribir_geojson, get_json, log, procedencia,
)

BASE = "https://arclim.mma.gob.cl"
# Ojo: la documentación de ARClim escribe estas rutas CON barra final y así
# devuelven 404. Van sin barra.
URL_VISTA = f"{BASE}/atlas/view/desbordes_rios_cbit/"
CAPA = "sitios_desbordes"

# Cifras publicadas por la fuente. Si no cuadran, la fuente cambió y hay que
# revisarla a mano antes de volver a publicar.
SITIOS_NACIONALES = 252

# Los índices que son constantes nacionales: no miden amenaza local, sólo
# recodifican el período de retorno. Se excluyen de la salida.
CONSTANTES_ESPERADAS = {
    "ind_amenaza_t25_presente": 0.4,
    "ind_amenaza_t50_presente": 0.6,
    "ind_amenaza_t100_presente": 0.8,
}

PREFIJO = "hidro_desbordes_"


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z]", "", t.upper())


def atributos_de_la_vista() -> list[str]:
    """Lee la configuración embebida en la página del atlas.

    ARClim no expone un endpoint que liste los atributos de una cadena de
    impacto; los deja en un `var config = {...}` dentro del HTML de la vista.
    Se leen de ahí en vez de escribirlos a mano para que, si la fuente agrega
    un indicador, aparezca solo.
    """
    from comun import get_bytes

    html = get_bytes(URL_VISTA).decode("utf-8", "replace")
    i = html.find("var config = ")
    if i < 0:
        raise SystemExit(
            "ARClim cambió el formato de la vista: no está el bloque `var config`. "
            f"Revisar a mano {URL_VISTA}")
    cfg, _ = json.JSONDecoder().raw_decode(html[i + len("var config = "):])
    ats = sorted({a["attr_id"] for a in cfg["attributes"]
                  if a["feature_id"] == CAPA and a["attr_id"].startswith(PREFIJO)})
    log(f"  la vista «{cfg['name']}» declara {len(ats)} atributos sobre {CAPA}")
    return ats


def main() -> None:
    cfg = cargar_config()
    comunas = {norm(c) for prov in cfg["provincias"].values() for c in prov}

    log("ARClim — cadena de impacto «Inundaciones por Desbordes de Ríos»")
    ats = atributos_de_la_vista()

    url = (f"{BASE}/api/datos/{CAPA}/geojson"
           f"?attributes={urllib.parse.quote(','.join(ats))}")
    resp = get_json(url)
    if "data" not in resp:
        raise SystemExit(f"respuesta inesperada de ARClim: {str(resp)[:200]}")
    feats = resp["data"]["features"]
    log(f"  {len(feats)} sitios de desborde en Chile")

    if len(feats) != SITIOS_NACIONALES:
        raise SystemExit(
            f"ARClim entregó {len(feats)} sitios y este pipeline está verificado "
            f"contra {SITIOS_NACIONALES}. La fuente cambió: revisar {URL_VISTA} "
            "antes de publicar nada.")

    # --- verificación de la constante -------------------------------------
    # No es una formalidad: si mañana ARClim hiciera variar la amenaza presente,
    # excluirla sin avisar nos haría tirar el dato bueno.
    for campo, esperado in CONSTANTES_ESPERADAS.items():
        vals = {f["properties"].get(PREFIJO + campo) for f in feats}
        if vals != {esperado}:
            raise SystemExit(
                f"«{campo}» ya NO es la constante {esperado} en los {len(feats)} "
                f"sitios del país (ahora toma {sorted(v for v in vals if v is not None)[:6]}). "
                "Eso cambia el diagnóstico: dejaría de ser una recodificación del "
                "período de retorno y podría ser un dato útil. Revisar a mano y "
                "actualizar la docstring de este script antes de seguir.")
    log(f"  verificado: {len(CONSTANTES_ESPERADAS)} índices de amenaza presente son "
        "constantes nacionales — se excluyen de la salida")

    descartados = {PREFIJO + c for c in CONSTANTES_ESPERADAS}

    salida = []
    for f in feats:
        p = f["properties"]
        if norm(p.get(PREFIJO + "nombre_comuna")) not in comunas:
            continue
        props = {k[len(PREFIJO):]: v for k, v in p.items()
                 if k.startswith(PREFIJO) and k not in descartados}
        # Las nueve columnas de estación fluviométrica vienen casi todas vacías;
        # se guarda sólo la lista de las que sí trae, que es lo trazable.
        est = [props.pop(f"estacion_{i}") for i in range(1, 10)]
        props["estaciones_dga"] = [e for e in est if e]
        props["fuente"] = "ARClim (MMA)"
        props["anio"] = "2022"
        salida.append({"type": "Feature", "geometry": f["geometry"],
                       "properties": props})

    log(f"  {len(salida)} sitios en La Araucanía, "
        f"{len({s['properties']['nombre_comuna'] for s in salida})} comunas")

    meta = procedencia(
        fuente="ARClim — Atlas de Riesgos Climáticos, Ministerio del Medio Ambiente. "
               "Cadena de impacto «Inundaciones por Desbordes de Ríos» (Ricchetti, "
               "Mendoza y Jerez, FCFM U. de Chile; actualizada 2022 por MMA / "
               "Naciones Unidas / Centro de Cambio Global UC)",
        url=URL_VISTA,
        metodo="descarga de la API pública de ARClim (/api/datos/sitios_desbordes/"
               "geojson) y filtro por comuna de La Araucanía. Se EXCLUYEN los "
               "índices de amenaza presente (t25/t50/t100) por ser constantes "
               "nacionales de 0,4/0,6/0,8: recodifican el período de retorno y no "
               "distinguen una localidad de otra.",
        capa_evidencia="C_modelado",
        incertidumbre="Índice adimensional 0-1 por localidad, NO una superficie "
                      "inundable. No permite decir si un predio se inunda. La "
                      "amenaza futura corresponde al horizonte 2035-2065.",
        escala_original="puntual, un sitio por centro poblado",
        fecha_dato="2022",
    )
    escribir_geojson(salida, DATA_PROC / "arclim" / "desbordes-araucania.geojson", meta)

    faltan = sorted(comunas - {norm(s["properties"]["nombre_comuna"]) for s in salida})
    if faltan:
        log(f"  sin sitio ARClim ({len(faltan)}): {', '.join(faltan)}")


if __name__ == "__main__":
    main()
