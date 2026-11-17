"""Capa A desde GeoIDE del MINVU (familias 1 y 2 de la auditoría del 15-nov-2026).

Qué se exige y por qué:

- Angol tiene su área de riesgo hídrica publicada en vectorial por el MINVU
  (GeoIDE, Resolución 40 del 14-10-2022: 10 AR-2a inundables y 11 AR-2b de
  anegamiento). El visor decía que no y mostraba sólo nuestra lámina, que cubre
  el 72 % del AR-2a y nada del AR-2b (F-200, F-201, F-103).
- Nueva Imperial, Renaico y Toltén tenían versiones viejas o incompletas
  (F-203, F-204, F-205).
- El tipo de fenómeno sale de una tabla explícita, no del texto por heurística:
  «napa freática» contiene «inundable» y no es desborde; «tsunami» tampoco.
- Una zona con texto hídrico que la tabla no conoce tiene que botar el script,
  no colarse ni perderse en silencio.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
m06 = importlib.import_module("06_areas_riesgo_prc")
WEB = RAIZ / "web" / "data"


def _cuadrado(x0, y0, d=0.001):
    # anillo exterior en sentido horario, como lo entrega ArcGIS
    return {"rings": [[[x0, y0], [x0, y0 + d], [x0 + d, y0 + d], [x0 + d, y0], [x0, y0]]]}


def _feat(zona, nom, x0=-72.7, **extra):
    return {"attributes": {"ZONA": zona, "NOM": nom, **extra}, "geometry": _cuadrado(x0, -37.8)}


def test_tipo_sale_de_la_tabla_y_no_del_texto():
    t = m06.tipo_geoide
    assert t("PRC_Tolten_Nueva_Tolten_Area_de_riesgo", "AR2",
             "Zona potencialmente inundable por napa freática") == "napa_freatica"
    assert t("PRC_Tolten_Queule_Area_de_riesgo", "AR-3",
             "Área de Riesgo Zona de Inundación por Tsuanami") == "litoral"
    assert t("PRC_Nueva_Imperial_AR", "AR-2",
             "AR-2 Área de riesgo Zona Potencialmente Inundable por anegamiento") == "anegamiento"
    assert t("PRC_Angol_Area_de_riesgo", "AR-2b", "Áreas de Riesgo por Anegamiento") == "anegamiento"
    assert t("PRC_Angol_Area_de_riesgo", "AR-2a",
             "Áreas de Riesgo Inundables o Potencialmente Inundables") == "fluvial"
    # remoción en masa: no es hídrica
    assert t("PRC_Angol_Area_de_riesgo", "AR-1a", "Áreas de Riesgo de Deslizamientos") is None


def test_zona_hidrica_desconocida_bota_el_script():
    capas = [("PRC_Angol_Area_de_riesgo", [
        _feat("AR-2a", "Áreas de Riesgo Inundables o Potencialmente Inundables"),
        _feat("AR-2b", "Áreas de Riesgo por Anegamiento"),
        _feat("AR-9", "Zona inundable por un fenómeno nuevo"),
    ])]
    with pytest.raises(SystemExit, match="AR-9"):
        m06.seleccionar_geoide(capas)


def test_zona_de_la_tabla_que_desaparece_bota_el_script():
    capas = [("PRC_Angol_Area_de_riesgo", [
        _feat("AR-2a", "Áreas de Riesgo Inundables o Potencialmente Inundables"),
    ])]
    with pytest.raises(SystemExit, match="AR-2B"):
        m06.seleccionar_geoide(capas)


def test_seleccion_lleva_comuna_tipo_y_documento():
    capas = [("PRC_Angol_Area_de_riesgo", [
        _feat("AR-2a", "Áreas de Riesgo Inundables o Potencialmente Inundables",
              T_DO="Resolución", N_DOC="40", P_DO="14/10/2022"),
        _feat("AR-2b", "Áreas de Riesgo por Anegamiento", x0=-72.6),
        _feat("AR-1a", "Áreas de Riesgo de Deslizamientos", x0=-72.5),
    ])]
    out = m06.seleccionar_geoide(capas)
    assert len(out) == 2
    p = out[0]["properties"]
    assert p["comuna"] == "Angol" and p["tipo_hidrico"] == "fluvial"
    assert p["es_inundacion"] is True
    assert p["anio"] == "2022"
    assert "Resolución 40" in p["instrumento"]


def test_reemplazo_exige_que_geoide_cubra_lo_que_habia():
    viejo = {"type": "Feature", "geometry": None, "properties": {
        "comuna": "Angol", "zona": "AR-7", "es_inundacion": True}}
    nuevo = {"type": "Feature", "geometry": None, "properties": {
        "comuna": "Angol", "zona": "AR-2a", "es_inundacion": True}}
    with pytest.raises(SystemExit, match="AR-7"):
        m06.reemplazar_por_geoide([viejo], [nuevo])


def test_reemplazo_conserva_lo_no_hidrico_y_comunas_sin_geoide():
    rem = {"type": "Feature", "geometry": None, "properties": {
        "comuna": "Angol", "zona": "AR-1a", "es_inundacion": False}}
    otra = {"type": "Feature", "geometry": None, "properties": {
        "comuna": "Pucón", "zona": "ZR-9", "es_inundacion": True}}
    vieja = {"type": "Feature", "geometry": None, "properties": {
        "comuna": "Angol", "zona": "AR-2a", "es_inundacion": True, "origen_capa": "PRC nacional"}}
    nuevo = {"type": "Feature", "geometry": None, "properties": {
        "comuna": "Angol", "zona": "AR-2a", "es_inundacion": True, "origen_capa": "GeoIDE"}}
    quedan, reemplazadas = m06.reemplazar_por_geoide([rem, otra, vieja], [nuevo])
    assert rem in quedan and otra in quedan and nuevo in quedan
    assert vieja not in quedan and vieja in reemplazadas


# --- lo publicado ---------------------------------------------------------

def _publicado():
    return json.loads((WEB / "areas-riesgo-inundacion.geojson").read_text(encoding="utf-8"))


def test_angol_publicado_desde_geoide():
    fs = [f for f in _publicado()["features"] if f["properties"]["comuna"] == "Angol"]
    tipos = sorted(f["properties"]["tipo_hidrico"] for f in fs)
    assert tipos.count("fluvial") == 10 and tipos.count("anegamiento") == 11


def test_comunas_actualizadas_desde_geoide():
    fs = _publicado()["features"]
    n = lambda c: sum(1 for f in fs if f["properties"]["comuna"] == c)  # noqa: E731
    assert n("Renaico") == 20          # 19 AR-1 del pueblo + Tijeral (F-204)
    assert n("Toltén") == 21           # Queule, Villa O'Higgins, Nueva Toltén, Villa Boldos (F-205)
    assert n("Nueva Imperial") == 9    # Resolución 111/2025 (F-203)


def test_anio_por_poligono():
    fs = _publicado()["features"]
    anio = {(f["properties"]["comuna"], f["properties"].get("instrumento")): f["properties"]["anio"]
            for f in fs}
    # GeoIDE trae la fecha del Diario Oficial y gana sobre el catastro del Atlas
    assert anio[("Angol", "Resolución 40 del 14/10/2022")] == "2022"
    assert anio[("Toltén", "Resolución 38 del 08/05/2026")] == "2026"
    # sin fecha en GeoIDE, el Atlas; «Puerto Saavedra» en el Atlas es Saavedra
    assert {f["properties"]["anio"] for f in fs if f["properties"]["comuna"] == "Saavedra"} == {1964}


def test_lamina_de_angol_queda_de_respaldo_y_no_se_publica():
    vect = json.loads((WEB / "laminas" / "vectorizadas.geojson").read_text(encoding="utf-8"))
    origen = {f["properties"]["origen_lamina"] for f in vect["features"]}
    assert not any(o.startswith("angol-prc-ar2a") for o in origen)
    # el estudio de 2013 no es el plan regulador: sigue publicado
    assert "angol-peligro-inundacion-2013" in origen
    # y el respaldo sigue en disco, trazable
    assert (RAIZ / "data" / "processed" / "laminas" / "angol-prc-ar2a-lamina1.geojson").exists()


def test_inventario_de_angol_ya_no_dice_sin_vectorial():
    est = json.loads((WEB / "estado-comunas.json").read_text(encoding="utf-8"))
    filas = est["comunas"] if isinstance(est, dict) else est
    angol = next(c for c in filas if c["comuna"] == "Angol")
    assert angol["poligonos_area_riesgo"] == 21


def test_geoide_se_rotula_como_interpretacion_referencial():
    """El MINVU declara su capa PRC_Araucania «Interpretación de los planos
    oficiales de los PRC» con licencia «Información referencial» (medido el
    16-nov-2026). El contenido es normativo, pero el trazado es la
    digitalización del MINVU, no el plano con efecto legal. Publicarlo sin
    decirlo deja creer que el borde dibujado es el legal."""
    fs = [f for f in _publicado()["features"]
          if str(f["properties"].get("origen_capa", "")).startswith("GeoIDE")]
    assert fs
    assert all("referencial" in f["properties"]["fuente"] for f in fs)
    app = (RAIZ / "web" / "app.js").read_text(encoding="utf-8")
    assert "información referencial" in app and "origen_capa" in app


def test_comunas_con_plan_en_geoide_sin_area_hidrica():
    """Victoria y Freire tienen su plan en GeoIDE sin área de riesgo por
    inundación (17-nov-2026). La solicitud no puede decir que «no está
    disponible»: está publicado y no la trae."""
    assert m06.comunas_con_prc_en_geoide(["PRC_Victoria", "Limite_Urbano"]) == ["Victoria"]
    with pytest.raises(SystemExit):
        m06.comunas_con_prc_en_geoide(["PRC_Cunco"])
    est = {c["comuna"]: c for c in
           json.loads((WEB / "estado-comunas.json").read_text(encoding="utf-8"))["comunas"]}
    assert est["Victoria"]["prc_en_geoide"] and not est["Victoria"]["poligonos_area_riesgo"]
    assert not est["Cunco"]["prc_en_geoide"]
    app = (RAIZ / "web" / "app.js").read_text(encoding="utf-8")
    assert "c.prc_en_geoide" in app
