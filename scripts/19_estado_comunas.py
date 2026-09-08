"""El inventario del vacío: qué tiene y qué le falta a cada comuna.

Por qué existe, y por qué es probablemente lo más útil del proyecto:

El visor responde «¿se inunda acá?». Esta capa responde otra pregunta, que es la
que puede mover a una institución: **¿con qué cuenta esta comuna para saberlo?**

Un mapa de riesgo asusta o tranquiliza, y compartirlo tiene costo — el veredicto
de un punto puede leerse como una promesa sobre una casa. En cambio, «mi comuna
no tiene ningún mapa de inundación en formato consultable» es un hecho
verificable que no predice nada, no compite con SENAPRED y pone la presión
exactamente donde corresponde. Ver docs/DIFUSION.md §0b.

Cruza todo lo que el proyecto reunió y, para cada una de las 32 comunas, deja
dicho qué existe y qué no:

  · gente expuesta        — Censo 2024
  · dónde ya se inundó    — puntos críticos de SENAPRED, y cuáles son crónicos
  · qué dice la norma     — si el área de riesgo está en el vectorial del MINVU
  · qué documentos hay    — del registro EAE y de los sitios municipales
  · si hay cartografía    — láminas localizadas dentro de esos documentos
  · si alguien la ubicó   — planos georreferenciados y láminas vectorizadas

⚠️ La regla del proyecto vale doble acá: **ausencia de dato no es ausencia de
riesgo**. Que una comuna aparezca sin cartografía NO significa que no se inunde;
significa que nadie levantó el mapa. Es justamente lo que se quiere mostrar.

Requiere: 01_senapred_puntos_criticos.py (web/data/indice-comunas.json),
        06_areas_riesgo_prc.py (web/data/areas-riesgo-inundacion.geojson),
        10_exportar_superposiciones.py (web/data/planos/indice.json, que a su
        vez necesita 08) y 09_exportar_catalogo.py (web/data/catalogo-documentos.json)
        — las cuatro son obligatorias, ver requerido() más abajo. Opcional:
        16_censo_2024.py (población) y 18_vectorizar_laminas.py (data/processed/laminas/*.geojson).
Salida: web/data/estado-comunas.json
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    DATA_PROC, WEB_DATA, cargar_config, log, procedencia, sello,
)


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", t.lower())


def _redondear(geom, n: int):
    """Recorta la precisión de las coordenadas.

    Cuatro decimales son ~11 m: de sobra para decidir en qué comuna cae un
    punto, y baja el archivo a una fracción. Esto viaja en una PWA que tiene que
    instalarse por datos móviles, así que cada kilobyte se paga.
    """
    def rec(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], n), round(c[1], n)]
        return [rec(x) for x in c]
    return {**geom, "coordinates": rec(geom["coordinates"])}


def cargar(ruta: Path):
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"{ruta} no se puede leer ({type(exc).__name__}: {exc})")


def requerido(ruta: Path, script: str):
    """Como `cargar()`, pero para una entrada que scripts/ORDEN.md declara en
    el `Requiere:` de este script.

    La diferencia con el censo (que sí puede faltar de verdad) es que estas
    cuatro SIEMPRE existen si el pipeline corrió hasta acá: si faltan, no es
    que el dato no exista, es que este paso corrió fuera de orden. Publicar
    igual —con `or {"comunas": []}`— es lo que hacía la auditoría de
    2026-09-06 (familia F-12): 32 comunas saliendo con «no publica ningún
    documento» o «0 puntos críticos» cuando en realidad el archivo nunca se
    generó. Eso es un resultado FALSO, no uno ausente (REGLAS §2), y en esta
    capa en particular —el inventario del vacío— es el peor lugar posible
    para mentir: es exactamente el archivo que el sitio muestra como «acá no
    hay nada».
    """
    d = cargar(ruta)
    if d is None:
        raise SystemExit(
            f"no existe {ruta}.\n"
            "Este inventario lo declara como entrada requerida (scripts/ORDEN.md): "
            "sin él, el resultado por comuna sería falso, no ausente. Corre antes:\n"
            f"    python scripts/{script}")
    return d


def main() -> None:
    cfg = cargar_config()
    comunas = [c for prov in cfg["provincias"].values() for c in prov]
    log(f"{len(comunas)} comunas de La Araucanía")

    # --- gente, del Censo 2024 (si está descargado) --------------------------
    #
    # El GeoJSON del censo son 73 MB y queda fuera del repositorio, así que esto
    # puede correr sin él. Cuando falta, la población va en None y el visor lo
    # dice — no se inventa ni se rellena con una cifra de otro año.
    poblacion: dict[str, dict] = {}
    censo = DATA_PROC / "censo" / "censo-2024-araucania.geojson"
    if censo.exists():
        d = cargar(censo)
        for f in d["features"]:
            p = f["properties"]
            k = norm(p.get("NOM_COMUNA"))
            e = poblacion.setdefault(k, {"personas": 0, "viv_hacinadas": 0,
                                         "agua_de_rio": 0, "mayores_60": 0})
            e["personas"] += int(p.get("n_per") or 0)
            e["viv_hacinadas"] += int(p.get("n_viv_hacinadas") or 0)
            e["agua_de_rio"] += int(p.get("n_fuente_agua_rio") or 0)
            e["mayores_60"] += int(p.get("n_edad_60_mas") or 0)
        log(f"  censo 2024: {len(poblacion)} comunas, "
            f"{sum(v['personas'] for v in poblacion.values()):,} personas")
    else:
        log("  censo 2024 no descargado — la población irá como «no disponible»")

    # --- lo que ya se publica ------------------------------------------------
    # Las cuatro llamadas siguientes usan requerido(), no cargar(): están en el
    # Requiere: de este script (01, 06, 10, 09 respectivamente) y su ausencia
    # produciría un inventario falso, no uno incompleto. Ver requerido() arriba.
    idx = requerido(WEB_DATA / "indice-comunas.json", "01_senapred_puntos_criticos.py")
    puntos = {norm(c["comuna"]): c for c in idx["comunas"]}

    areas = requerido(WEB_DATA / "areas-riesgo-inundacion.geojson", "06_areas_riesgo_prc.py")
    con_area = Counter(norm(f["properties"].get("comuna")) for f in areas["features"])

    planos = requerido(WEB_DATA / "planos" / "indice.json",
                       "10_exportar_superposiciones.py (que a su vez necesita 08)").get("planos", [])
    # El estado de tramitación importa: un anteproyecto no rige sobre nadie.
    planos_por_comuna: dict[str, Counter] = {}
    for p in planos:
        k = norm(p.get("titulo"))
        for c in comunas:
            if norm(c) and norm(c) in k:
                planos_por_comuna.setdefault(norm(c), Counter())[
                    p.get("estado_tramite") or "No declarado"] += 1

    catalogo = requerido(WEB_DATA / "catalogo-documentos.json", "09_exportar_catalogo.py")
    docs = {}
    for c in catalogo["comunas"]:
        k = norm(c.get("comuna") or c.get("nombre"))
        dd = c.get("documentos", [])
        docs[k] = {"documentos": len(dd),
                   "laminas": sum(len(x.get("laminas") or []) for x in dd)}

    # Láminas que nosotros convertimos en geometría (capa A derivada).
    #
    # Y se PUBLICAN, no sólo se cuentan. El bloque de comuna anunciaba «N
    # polígonos que convertimos nosotros» y esos polígonos no estaban en
    # web/data/: prometer evidencia que no se puede ver es peor que no
    # mencionarla. Van a un archivo aparte y con su propio sello, porque son
    # producto DERIVADO y no pueden mezclarse con el vectorial del MINVU, que sí
    # tiene efecto legal.
    vect: dict[str, int] = {}
    derivados = []
    for f in sorted((DATA_PROC / "laminas").glob("*.geojson")):
        d = cargar(f)
        for ft in (d or {}).get("features", []):
            k2 = norm(ft["properties"].get("comuna"))
            vect[k2] = vect.get(k2, 0) + 1
            derivados.append({**ft, "properties": {**ft["properties"],
                                                   "origen_lamina": f.stem}})
    if derivados:
        (WEB_DATA / "laminas").mkdir(exist_ok=True)
        (WEB_DATA / "laminas" / "vectorizadas.geojson").write_text(json.dumps({
            "procedencia": procedencia(
                fuente="Láminas de peligro publicadas en documentos oficiales, "
                       "vectorizadas por el proyecto",
                # No hay una URL única para la capa: cada lámina viene de un
                # documento distinto. La de cada polígono va en su propio campo
                # `url`, que es donde sirve.
                url="cada polígono trae la URL de su documento en el campo `url`",
                metodo="Georreferenciación desde la retícula UTM impresa o desde "
                       "los vértices rotulados del plano, y clasificación de las "
                       "clases de la leyenda por color o por trama. Cada polígono "
                       "lleva su propia `incertidumbre_borde_m`: el tamaño del "
                       "píxel de la figura, o el RMSE del ajuste más media celda "
                       "del achurado en el caso de un plano.",
                capa_evidencia="A_derivado",
                # El descargo distingue el CONTENIDO del TRAZADO. Decir de todo
                # el archivo «no tiene efecto legal» era cómodo y falso al revés:
                # 26 de estos polígonos son el área AR-2a del plan regulador
                # VIGENTE de Angol, la única evidencia normativa que existe para
                # esa comuna, y quedaban subvendidos junto a un estudio de 2013.
                # Lo derivado es dónde dibujamos el borde, no lo que la norma dice.
                incertidumbre="PRODUCTO DERIVADO: el trazado y la ubicación los "
                              "construimos nosotros desde una lámina impresa; el "
                              "organismo NO publica esta geometría. El contenido "
                              "es del instrumento o estudio de origen, con su año "
                              "y su método, y su peso legal es el que ese "
                              "instrumento tenga: los polígonos que traen el campo "
                              "`efecto_legal` vienen de un plan regulador vigente "
                              "y ese efecto rige; los demás son levantamientos de "
                              "riesgo sin efecto normativo propio. En ningún caso "
                              "el borde es el del vectorial oficial del MINVU: "
                              "cada polígono declara su `incertidumbre_borde_m`.",
                fecha_dato="según la lámina de origen"),
            "type": "FeatureCollection", "features": derivados},
            ensure_ascii=False), encoding="utf-8")
        log(f"  láminas vectorizadas publicadas: {len(derivados)} polígonos "
            f"→ web/data/laminas/vectorizadas.geojson")


    # --- armar la ficha por comuna ------------------------------------------
    salida = []
    for c in sorted(comunas):
        k = norm(c)
        pc = puntos.get(k, {})
        pl = planos_por_comuna.get(k, Counter())
        dc = docs.get(k, {"documentos": 0, "laminas": 0})
        pob = poblacion.get(k)

        # Los tres huecos que importan, cada uno con su frase. Se calculan acá y
        # no en el navegador para que el texto que se comparte y el que se ve
        # sean literalmente el mismo.
        faltas = []
        if not con_area.get(k):
            faltas.append("no tiene su área de riesgo por inundación en el "
                          "vectorial público del MINVU")
        if not dc["laminas"]:
            faltas.append("no le encontramos ninguna lámina de cartografía de "
                          "inundación en documentos públicos")
        if not dc["documentos"]:
            faltas.append("no publica ningún documento de planificación "
                          "territorial que hayamos podido cosechar")

        salida.append({
            "comuna": c.title(),
            "slug": re.sub(r"[^a-z0-9]+", "-", norm(c)).strip("-"),
            "personas": (pob or {}).get("personas"),
            "mayores_60": (pob or {}).get("mayores_60"),
            "viviendas_hacinadas": (pob or {}).get("viv_hacinadas"),
            "hogares_agua_de_rio": (pob or {}).get("agua_de_rio"),
            "puntos_inundacion": pc.get("puntos_inundacion", 0),
            "puntos_cronicos": pc.get("cronicos", 0),
            "poligonos_area_riesgo": con_area.get(k, 0),
            "documentos": dc["documentos"],
            "laminas_localizadas": dc["laminas"],
            "planos_georreferenciados": sum(pl.values()),
            "planos_por_estado": dict(pl),
            "poligonos_vectorizados_por_nosotros": vect.get(k, 0),
            "le_falta": faltas,
        })

    # ⚠️ NO se generan límites comunales acá, y vale explicar por qué se
    # intentó y se descartó: disolver las unidades del Censo 2024 por comuna NO
    # da el límite comunal, da la **huella poblada**. Sale lleno de huecos, pesa
    # 1,3 MB y un punto en zona despoblada —que en esta región es casi todo—
    # cae fuera de todos los polígonos. Peor que no tenerlo.
    #
    # El visor resuelve la comuna por el punto crítico de SENAPRED más cercano,
    # sin límite de distancia, y **muestra el nombre de la comuna en grande**
    # para que un error de atribución cerca de un deslinde sea visible al tiro.
    # Para reemplazarlo bien haría falta el límite administrativo oficial (BCN o
    # IDE Chile), no una derivación del censo.

    meta = procedencia(
        fuente="Cruce de todas las fuentes reunidas por el proyecto",
        url="",
        metodo="Para cada comuna se cuenta qué existe: población del Censo 2024, "
               "puntos críticos de SENAPRED, polígonos de área de riesgo del "
               "vectorial del MINVU, documentos y láminas del catálogo, planos "
               "georreferenciados y polígonos vectorizados por el proyecto.",
        capa_evidencia="inventario",
        incertidumbre="Es un inventario de LO QUE ENCONTRAMOS, no de lo que "
                      "existe. Que una comuna aparezca sin cartografía significa "
                      "que no la hallamos en fuentes públicas consultables, no "
                      "que no se inunde ni que el municipio no la tenga en papel. "
                      "AUSENCIA DE DATO NO ES AUSENCIA DE RIESGO.",
        fecha_dato="cruce al día de la corrida",
    )
    destino = WEB_DATA / "estado-comunas.json"
    destino.write_text(json.dumps({"procedencia": meta, **sello("varias", None),
                                   "comunas": salida},
                                  ensure_ascii=False, indent=1), encoding="utf-8")

    sin_area = [x for x in salida if not x["poligonos_area_riesgo"]]
    sin_lam = [x for x in salida if not x["laminas_localizadas"]]
    sin_doc = [x for x in salida if not x["documentos"]]
    log("")
    log(f"RESULTADO → {destino.relative_to(destino.parent.parent.parent)}")
    log(f"  {len(sin_area)} de {len(salida)} comunas SIN área de riesgo en el vectorial")
    log(f"  {len(sin_lam)} sin ninguna lámina de cartografía localizada")
    log(f"  {len(sin_doc)} sin ningún documento de planificación")
    log("")
    log("Las que más gente tienen entre las que no tienen nada consultable:")
    peor = sorted([x for x in salida if not x["poligonos_area_riesgo"]
                   and not x["laminas_localizadas"]],
                  key=lambda x: -(x["personas"] or 0))
    for x in peor[:8]:
        pob = f"{x['personas']:>7,}" if x["personas"] else "      ?"
        log(f"   {x['comuna'][:18]:20s} {pob} hab · "
            f"{x['puntos_inundacion']:>3} puntos ({x['puntos_cronicos']} crónicos)")


if __name__ == "__main__":
    main()
