"""Qué tiene el visor, en pocas líneas: cuántos mapas, de cuántas comunas y con qué peso.

Por qué existe. Nicolás lo pidió el 16-nov-2026: una sección que diga resumidamente
qué tenemos en el visor, cuántos mapas o estudios oficiales y de cuántas comunas, y
cuántos no están aprobados u oficializados. Sin eso, quien abre el visor no sabe si
la falta de mancha en su comuna es «no se inunda» o «nadie la ha mapeado».

Qué cuidado tiene:

- Se cuenta cada capa por separado (REGLAS §1). Una comuna puede estar en varias y
  las cuentas no se suman entre capas.
- El peso legal sale del dato y nunca se supone. La capa A viene de GeoIDE del MINVU;
  sólo algunas comunas traen en el dato la resolución publicada en el Diario Oficial,
  y las demás se informan como «sin resolución declarada en el dato», no como
  aprobadas ni como no aprobadas.
- Los documentos se agrupan por su estado en el registro de Evaluación Ambiental
  Estratégica. Un estado que este script no conoce va a «sin estado declarado»: nunca
  al grupo más parecido, porque equivocarse hacia «aprobado» es el error caro.
- «Sin cartografía» es sólo la comuna que no aparece en ninguna capa cartográfica
  (área de riesgo, trazado derivado, plano ubicado o lámina localizada).

Lee sólo lo que el visor ya publica en `web/data/`, así que el inventario describe
exactamente lo que una persona ve.

Requiere: 19_estado_comunas.py (y, a través de él, 01, 06, 09, 10, 13, 14, 15, 18).
Salida: web/data/inventario.json (unos 5 kB, va offline en el visor).
"""
from __future__ import annotations

import json
import unicodedata
from collections import Counter
from datetime import datetime, timezone

from comun import RAIZ, log, procedencia

WEB = RAIZ / "web" / "data"
SALIDA = WEB / "inventario.json"

# Estado en el registro EAE -> grupo. Lista cerrada a propósito (ver docstring).
GRUPOS = {
    "Resolución de Aprobación del Instrumento": "aprobado",
    "Resolución de Término de la EAE": "eae_terminada",
    "Inicio EAE": "en_tramite",
    "Informe Ambiental Corregido": "en_tramite",
    "Informe Ambiental Complementario": "en_tramite",
    "Segundo Informe Ambiental": "en_tramite",
    "Tercer Informe Ambiental": "en_tramite",
    "Cuarto Informe Ambiental": "en_tramite",
    "Resolución de Desistimiento o Abandono": "desistido",
    "publicado por el municipio": "municipal",
}
ROTULOS = {
    "aprobado": "de un plan con resolución de aprobación en el registro",
    "eae_terminada": "con la evaluación ambiental terminada; el registro no dice si el plan ya rige",
    "en_tramite": "de planes en tramitación, sin efecto legal todavía",
    "desistido": "de planes desistidos o abandonados",
    "municipal": "publicados por el municipio fuera del registro: estudios y planes de emergencia",
    "sin_estado": "sin estado declarado",
}


def grupo_de_estado(estado: str | None) -> str:
    return GRUPOS.get((estado or "").strip(), "sin_estado")


def sin_cartografia(comunas: list[dict]) -> list[str]:
    return [c["comuna"] for c in comunas
            if not (c.get("poligonos_area_riesgo") or c.get("poligonos_vectorizados_por_nosotros")
                    or c.get("planos_georreferenciados") or c.get("laminas_localizadas"))]


def _sin_tildes(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def con_tildes(nombre: str, conocidos: set[str]) -> str:
    """`estado-comunas.json` guarda los nombres sin tilde («Curacautin»). Si otra
    capa trae el mismo nombre con tilde, se usa ése; si no, queda como está."""
    for c in conocidos:
        if _sin_tildes(c) == _sin_tildes(nombre):
            return c
    return nombre


def _j(rel: str):
    return json.loads((WEB / rel).read_text(encoding="utf-8"))


def main() -> None:
    comunas = _j("estado-comunas.json")["comunas"]
    areas = _j("areas-riesgo-inundacion.geojson")["features"]
    laminas = _j("laminas/vectorizadas.geojson")["features"]
    planos = _j("planos/indice.json")["planos"]
    catalogo = _j("catalogo-documentos.json")["comunas"]
    puntos = _j("puntos-criticos-inundacion.geojson")["features"]
    camp = _j("campamentos-inundacion.geojson")["features"]
    gore = _j("gore/amenaza-inundacion.geojson")["features"]
    sar = _j("sar/indice.json")

    # A normativo: por comuna, con la resolución si el dato la trae.
    por_comuna: dict[str, dict] = {}
    for f in areas:
        p = f["properties"]
        d = por_comuna.setdefault(p["comuna"], {"comuna": p["comuna"], "poligonos": 0,
                                                "instrumento": None})
        d["poligonos"] += 1
        d["instrumento"] = d["instrumento"] or p.get("instrumento")
    normativo = {
        "poligonos": len(areas),
        "comunas": len(por_comuna),
        "con_resolucion": sorted((d for d in por_comuna.values() if d["instrumento"]),
                                 key=lambda d: d["comuna"]),
        "sin_resolucion_declarada": sorted(d["comuna"] for d in por_comuna.values()
                                           if not d["instrumento"]),
    }

    # A derivado: por documento de origen, con su año y su estado.
    docs_der: dict[str, dict] = {}
    for f in laminas:
        p = f["properties"]
        d = docs_der.setdefault(p["origen_lamina"], {
            "comuna": p["comuna"].title(), "fuente": p["fuente"], "anio": p.get("anio"),
            "estado_tramite": p.get("estado_tramite"), "poligonos": 0,
            "incertidumbre_borde_m": p.get("incertidumbre_borde_m")})
        d["poligonos"] += 1
    derivado = {"poligonos": len(laminas), "documentos": list(docs_der.values()),
                "comunas": len({d["comuna"] for d in docs_der.values()})}

    # Planos ubicados sobre el mapa, por estado de tramitación.
    por_estado_plano = Counter()
    for c in comunas:
        por_estado_plano.update(c.get("planos_por_estado") or {})
    planos_inv = {"planos": len(planos),
                  "comunas": sum(1 for c in comunas if c.get("planos_georreferenciados")),
                  "por_estado": dict(por_estado_plano)}

    # Documentos del catálogo, por estado en el registro EAE.
    grupos: dict[str, dict] = {}
    for c in catalogo:
        for d in c["documentos"]:
            g = grupo_de_estado(d.get("estado_eae"))
            x = grupos.setdefault(g, {"grupo": g, "rotulo": ROTULOS[g], "documentos": 0,
                                      "comunas": set()})
            x["documentos"] += 1
            x["comunas"].add(c["comuna"])
    orden = list(ROTULOS)
    por_estado = [dict(g, comunas=len(g["comunas"]))
                  for g in sorted(grupos.values(), key=lambda g: orden.index(g["grupo"]))]
    n_docs = sum(len(c["documentos"]) for c in catalogo)
    documentos = {
        "documentos": n_docs,
        "comunas": sum(1 for c in catalogo if c["documentos"]),
        "laminas": sum(len(d.get("laminas") or []) for c in catalogo for d in c["documentos"]),
        "comunas_con_lamina": sum(1 for c in catalogo
                                  if any(d.get("laminas") for d in c["documentos"])),
        "por_estado": por_estado,
    }

    nombres = ({f["properties"]["comuna"].title() for f in puntos}
               | {f["properties"]["comuna"] for f in areas})
    resumen_sar = sar.get("resumen") or {}
    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "procedencia": procedencia(
            fuente="Recuento de lo que el propio visor publica en web/data/",
            url="",
            metodo=("Cada capa se cuenta por separado. El peso legal de la capa A sale del "
                    "campo `instrumento` de GeoIDE; el de los documentos, de su estado en el "
                    "registro de Evaluación Ambiental Estratégica, con una lista cerrada."),
            capa_evidencia="inventario",
            incertidumbre=("Describe lo que tenemos, no el territorio: una comuna sin "
                           "cartografía no es una comuna que no se inunda."),
        ),
        "total_comunas": len(comunas),
        "normativo": normativo,
        "derivado": derivado,
        "planos": planos_inv,
        "documentos": documentos,
        "sin_cartografia": [con_tildes(c, nombres) for c in sin_cartografia(comunas)],
        "otras_capas": {
            "puntos_criticos": {"puntos": len(puntos),
                                "comunas": len({f["properties"]["comuna"] for f in puntos})},
            "campamentos": {"campamentos": len(camp),
                            "hogares": sum(f["properties"].get("hogares") or 0 for f in camp)},
            "sar": {"hectareas_con_agua": resumen_sar.get("hectareas"),
                    "km2_observados": resumen_sar.get("km2_observados"),
                    "evento": (sar.get("evento") or {}).get("nombre")},
            "gore": {"poligonos": len(gore)},
            "jrc": {"periodos_de_retorno": len(list((WEB / "jrc").glob("rp*.geojson")))},
        },
    }
    texto = json.dumps(salida, ensure_ascii=False, separators=(",", ":"))
    assert "\u2014" not in texto and "\u2013" not in texto, "guion largo en el inventario"
    SALIDA.write_text(texto, encoding="utf-8")
    log(f"inventario: {normativo['comunas']} comunas con área de riesgo "
        f"({len(normativo['con_resolucion'])} con resolución), {derivado['comunas']} con "
        f"trazado derivado, {planos_inv['comunas']} con planos, "
        f"{len(salida['sin_cartografia'])} sin cartografía -> {SALIDA}")


if __name__ == "__main__":
    main()
