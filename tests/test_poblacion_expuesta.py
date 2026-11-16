"""Población expuesta por comuna (familia 5 de la auditoría del 15-nov-2026).

Qué se exige y por qué:

- La cifra depende más del criterio de cruce que de la capa: en el AR-2a de Angol
  iba de 429 personas (manzana entera dentro) a 22.113 (cualquier toque). Un solo
  número no es defendible, así que se publican los cuatro criterios y el visor
  muestra el rango (F-303).
- Cada capa de evidencia se cruza sola, y el A normativo además por fenómeno: junto,
  el 84 % de su gente era un anegamiento de Temuco (F-302, REGLAS §1).
- En el A derivado el borde trazado tiene un error declarado en metros, y moverlo
  cambia el reparto un cuarto o más: se publica el reparto con la mancha encogida y
  engordada en ese error (F-301).
- Donde la gente expuesta está sobre todo en entidades rurales, el supuesto de
  densidad pareja no se sostiene: se publica la fracción rural para avisarlo (F-304).
- El cálculo se contrasta con `tools/auditoria/vC_reparto_independiente.py`, que
  calcula el reparto por otro camino y sin importar este script.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tools" / "auditoria"))
m21 = importlib.import_module("21_poblacion_expuesta")
SALIDA = RAIZ / "web" / "data" / "poblacion-expuesta.json"
CRITERIOS = ("dentro", "punto", "reparto", "cualquier")


def _salida():
    return json.loads(SALIDA.read_text(encoding="utf-8"))


def test_cruce_sintetico_da_los_valores_exactos():
    """30 % dentro (mancha duplicada), entera dentro, fuera y 70 % dentro."""
    u = gpd.GeoDataFrame(
        {"NOM_COMUNA": ["X"] * 4, "n_per": [1000, 1000, 1000, 1000],
         "AREA_C": ["URBANO", "URBANO", "URBANO", "RURAL"]},
        geometry=[box(0, 0, 100, 100), box(300, 0, 400, 100),
                  box(1000, 0, 1100, 100), box(500, 0, 600, 100)], crs=32719)
    mancha = [box(-50, -50, 30, 150), box(-50, -50, 30, 150),   # duplicada: no cuenta doble
              box(290, -10, 410, 110), box(530, -10, 620, 110)]
    r = m21.cruzar(m21.preparar_unidades(u), mancha)["X"]
    assert r["dentro"] == pytest.approx(1000)       # sólo U2
    assert r["punto"] == pytest.approx(2000)        # U2 y U4; el centro de U1 queda fuera
    assert r["reparto"] == pytest.approx(300 + 1000 + 700)
    assert r["cualquier"] == pytest.approx(3000)
    assert r["reparto_rural"] == pytest.approx(700)


def test_publica_por_capa_y_fenomeno_sin_fusionar():
    d = _salida()
    capas = {(b["capa_evidencia"], b["subcapa"]) for b in d["capas"]}
    assert ("A_normativo", "fluvial") in capas
    assert ("A_normativo", "anegamiento") in capas
    # F-302: nunca una fila con todos los fenómenos normativos juntos
    assert not any(s in ("todas", "todos") for _, s in capas)
    assert {c for c, _ in capas} <= {"A_normativo", "A_derivado"}
    for b in d["capas"]:
        assert b["procedencia"]["capa_evidencia"] == b["capa_evidencia"]


def test_rango_ordenado_en_cada_comuna():
    d = _salida()
    n = 0
    for b in d["capas"]:
        for c, v in b["comunas"].items():
            p = v["personas"]
            assert p["dentro"] <= p["punto"] <= p["cualquier"], (b["subcapa"], c)
            assert p["dentro"] <= p["reparto"] <= p["cualquier"], (b["subcapa"], c)
            assert 0 <= v["fraccion_rural"] <= 1
            n += 1
    assert n > 10


def test_a_derivado_trae_el_reparto_con_el_borde_movido():
    d = _salida()
    der = [b for b in d["capas"] if b["capa_evidencia"] == "A_derivado"]
    assert der, "no hay capa A derivado publicada"
    for b in der:
        assert b["incertidumbre_borde_m"] > 0
        for c, v in b["comunas"].items():
            lo, hi = v["reparto_con_borde"]
            assert lo <= v["personas"]["reparto"] <= hi, (b["subcapa"], c)


def test_reparto_coincide_con_el_verificador_independiente():
    import vC_reparto_independiente as vC
    cen = gpd.read_file(RAIZ / "data/processed/censo/censo-2024-araucania.geojson")
    cen = cen[cen.unidad_censal != "aldea"].to_crs(32719)
    a = gpd.read_file(RAIZ / "web/data/areas-riesgo-inundacion.geojson").to_crs(32719)
    d = {(b["capa_evidencia"], b["subcapa"]): b for b in _salida()["capas"]}
    for tipo in ("fluvial", "anegamiento"):
        esperado = vC.reparto(cen, a[a.tipo_hidrico == tipo].geometry.union_all())
        obtenido = sum(v["personas"]["reparto"]
                       for v in d[("A_normativo", tipo)]["comunas"].values())
        # el publicado va redondeado a la persona, comuna por comuna
        assert obtenido == pytest.approx(esperado, abs=len(d[("A_normativo", tipo)]["comunas"]))


def test_censo_sin_doble_conteo():
    d = _salida()
    assert d["censo"]["personas_region"] == 1003546


def test_visor_carga_y_guarda_offline_el_archivo():
    app = (RAIZ / "web" / "app.js").read_text(encoding="utf-8")
    sw = (RAIZ / "web" / "sw.js").read_text(encoding="utf-8")
    assert "data/poblacion-expuesta.json" in app
    assert "data/poblacion-expuesta.json" in sw
