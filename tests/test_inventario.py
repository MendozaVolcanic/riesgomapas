"""Inventario del visor: qué tenemos, de cuántas comunas, y con qué peso legal.

Qué se exige y por qué:

- Nicolás pidió (16-nov-2026) una sección que diga en pocas líneas qué hay en el
  visor: cuántos mapas o estudios oficiales y de cuántas comunas, cuántos sin aprobar.
  Una portada que exagera el peso legal de lo que muestra es peor que no tenerla, así
  que el estado de tramitación sale del dato y nunca se supone: un documento con un
  estado que no conocemos va a «sin estado declarado», no al grupo más parecido.
- Las capas no se fusionan (REGLAS §1): el inventario cuenta cada una por separado y
  una comuna puede aparecer en varias. «Sin cartografía» es sólo la comuna que no
  aparece en ninguna de las cartográficas.
- Cada plano georreferenciado tiene que quedar atribuido a una comuna. Hasta el
  16-nov tres planos de Teodoro Schmidt se perdían porque el archivo fuente dice
  «Schimdt», y la comuna figuraba con 1 plano de 4.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
m22 = importlib.import_module("22_inventario_visor")
WEB = RAIZ / "web" / "data"


def _j(p):
    return json.loads((WEB / p).read_text(encoding="utf-8"))


def test_cada_plano_queda_atribuido_a_una_comuna():
    planos = _j("planos/indice.json")["planos"]
    comunas = _j("estado-comunas.json")["comunas"]
    atribuidos = sum(c["planos_georreferenciados"] for c in comunas)
    assert atribuidos == len(planos), (
        f"{len(planos)} planos publicados y {atribuidos} atribuidos a una comuna")
    ts = next(c for c in comunas if c["comuna"] == "Teodoro Schmidt")
    assert ts["planos_georreferenciados"] == 4


def test_estado_desconocido_no_se_adivina():
    assert m22.grupo_de_estado("Resolución de Aprobación del Instrumento") == "aprobado"
    assert m22.grupo_de_estado("Cuarto Informe Ambiental") == "en_tramite"
    assert m22.grupo_de_estado("publicado por el municipio") == "municipal"
    # Control: un estado inventado no puede caer en un grupo con peso legal.
    assert m22.grupo_de_estado("Resolución de Algo Nuevo") == "sin_estado"
    assert m22.grupo_de_estado(None) == "sin_estado"


def test_sin_cartografia_es_la_comuna_que_no_aparece_en_ninguna():
    comunas = [
        {"comuna": "A", "poligonos_area_riesgo": 3, "poligonos_vectorizados_por_nosotros": 0,
         "planos_georreferenciados": 0, "laminas_localizadas": 0},
        {"comuna": "B", "poligonos_area_riesgo": 0, "poligonos_vectorizados_por_nosotros": 0,
         "planos_georreferenciados": 0, "laminas_localizadas": 2},
        {"comuna": "C", "poligonos_area_riesgo": 0, "poligonos_vectorizados_por_nosotros": 0,
         "planos_georreferenciados": 0, "laminas_localizadas": 0},
    ]
    assert m22.sin_cartografia(comunas) == ["C"]


def test_inventario_publicado_cuadra_con_los_datos():
    inv = _j("inventario.json")
    assert inv["procedencia"]["capa_evidencia"] == "inventario"
    comunas = _j("estado-comunas.json")["comunas"]
    assert inv["total_comunas"] == len(comunas)

    areas = _j("areas-riesgo-inundacion.geojson")["features"]
    n = inv["normativo"]
    assert n["poligonos"] == len(areas)
    assert n["comunas"] == len({f["properties"]["comuna"] for f in areas})
    con_res = {f["properties"]["comuna"] for f in areas if f["properties"].get("instrumento")}
    assert {x["comuna"] for x in n["con_resolucion"]} == con_res
    assert len(n["con_resolucion"]) + len(n["sin_resolucion_declarada"]) == n["comunas"]

    docs = [d for c in _j("catalogo-documentos.json")["comunas"] for d in c["documentos"]]
    d = inv["documentos"]
    assert d["documentos"] == len(docs)
    assert sum(g["documentos"] for g in d["por_estado"]) == len(docs)

    planos = _j("planos/indice.json")["planos"]
    assert inv["planos"]["planos"] == len(planos)

    # Ninguna comuna sin cartografía puede tener polígonos, planos ni láminas.
    porcomuna = {m22._sin_tildes(c["comuna"]): c for c in comunas}
    for nombre in inv["sin_cartografia"]:
        c = porcomuna[m22._sin_tildes(nombre)]
        assert not (c["poligonos_area_riesgo"] or c["planos_georreferenciados"]
                    or c["laminas_localizadas"] or c["poligonos_vectorizados_por_nosotros"])


def test_inventario_sin_guiones_largos():
    texto = (WEB / "inventario.json").read_text(encoding="utf-8")
    assert "\u2014" not in texto and "\u2013" not in texto


def test_nombre_con_tilde_si_otra_capa_lo_trae():
    assert m22.con_tildes("Curacautin", {"Curacautín", "Angol"}) == "Curacautín"
    # Control: no se fuerza un nombre distinto aunque se parezca.
    assert m22.con_tildes("Cholchol", {"Chol Chol"}) == "Cholchol"
