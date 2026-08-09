"""Verificación del detector de grilla UTM impresa.

Por qué importa tener esto cubierto: el script 08 georreferencia planos sin que
nadie mire. Si la detección se equivoca, el resultado no falla — produce un mapa
de riesgo de inundación colocado en el lugar equivocado, con un RMSE bajísimo que
lo hace parecer excelente. El RMSE mide la coherencia interna de la grilla, no
que la grilla sea realmente una grilla.

De ahí que lo que se prueba acá sea sobre todo que el detector **rechace** lo que
debe rechazar.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

_spec = importlib.util.spec_from_file_location(
    "g8", RAIZ / "scripts" / "08_georreferenciar_grilla.py")
g8 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g8)


def etiquetas(valores, posiciones, usar_x=True):
    """Construye la lista que devolvería la lectura del PDF."""
    return [{"valor": v, "x": p if usar_x else 0.0, "y": 0.0 if usar_x else p}
            for v, p in zip(valores, posiciones)]


def grilla_ideal(v0=740500, paso=250, n=13, p0=352.8, escala=1.1336):
    """Grilla regular como la del plano de Vilcún: 250 m cada 283,4 pt."""
    vals = [v0 + paso * i for i in range(n)]
    pos = [p0 + (v - v0) * escala for v in vals]
    return vals, pos


def test_grilla_limpia_se_detecta_y_es_lineal():
    vals, pos = grilla_ideal()
    eje = g8.eje_desde_etiquetas(etiquetas(vals, pos), usar_x=True)
    assert eje is not None
    assert eje["n"] == len(vals)
    assert eje["regular"] is True
    assert eje["r2"] > 0.99999
    assert eje["paso_m"] == pytest.approx(250)
    assert eje["descartados"] == 0


def test_etiqueta_repetida_en_ambos_margenes_no_duplica_lineas():
    """Cada línea viene rotulada dos veces; deben promediarse, no contarse doble."""
    vals, pos = grilla_ideal(n=6)
    dobles = etiquetas(vals, pos) + etiquetas(vals, [p + 0.4 for p in pos])
    eje = g8.eje_desde_etiquetas(dobles, usar_x=True)
    assert eje["n"] == 6, "las repeticiones del mismo valor son una sola línea"


def test_numero_espurio_es_descartado_por_ransac():
    """Un número de 6-7 dígitos que no es coordenada no puede torcer el ajuste.

    Es el caso real que hizo fallar el primer intento sobre el plano de Vilcún.
    """
    vals, pos = grilla_ideal()
    conts = etiquetas(vals, pos) + etiquetas([145000], [800.0])
    eje = g8.eje_desde_etiquetas(conts, usar_x=True)
    assert eje["descartados"] >= 1
    assert eje["r2"] > 0.99999
    assert eje["paso_m"] == pytest.approx(250)


def test_valores_fuera_del_rango_chileno_se_filtran_antes():
    vals, pos = grilla_ideal()
    # 1.450.000 no puede ser una easting UTM en Chile
    conts = etiquetas(vals, pos) + etiquetas([1_450_000], [900.0])
    eje = g8.eje_desde_etiquetas(conts, usar_x=True)
    assert eje["max"] <= g8.RANGO_ESTE[1]


def test_northings_usan_su_propio_rango():
    vals, pos = grilla_ideal(v0=5_716_000, paso=250, n=5, p0=333.7)
    eje = g8.eje_desde_etiquetas(etiquetas(vals, pos, usar_x=False), usar_x=False)
    assert eje is not None and eje["n"] == 5
    # Una easting de 6 dígitos no debe colarse como northing
    mezcla = etiquetas(vals, pos, usar_x=False) + etiquetas([741000], [500.0], usar_x=False)
    eje2 = g8.eje_desde_etiquetas(mezcla, usar_x=False)
    assert eje2["min"] >= g8.RANGO_NORTE[0]


def test_ruido_sin_estructura_no_produce_grilla():
    """Números dispersos sin relación lineal no deben aceptarse como grilla."""
    vals = [712345, 733111, 750007, 799999, 601234]
    pos = [10.0, 900.0, 55.0, 400.0, 1200.0]
    eje = g8.eje_desde_etiquetas(etiquetas(vals, pos), usar_x=True)
    # O no detecta nada, o lo que detecta no es una grilla regular.
    assert eje is None or not eje["regular"] or eje["n"] < 3


def test_menos_de_tres_lineas_no_alcanza():
    eje = g8.eje_desde_etiquetas(etiquetas([740500, 740750], [100.0, 383.4]), usar_x=True)
    assert eje is None


def test_coordenada_decreciente_con_la_posicion_se_rechaza():
    """En ambos ejes la coordenada crece con la posición en el sistema del PDF.

    Una pendiente negativa significa que se emparejaron rótulos de otra cosa.
    """
    vals, pos = grilla_ideal(n=8)
    eje = g8.eje_desde_etiquetas(etiquetas(vals, list(reversed(pos))), usar_x=True)
    assert eje is None or not eje["regular"] or eje["r2"] < g8.R2_MIN


def test_huso_se_deduce_y_una_coordenada_ajena_se_rechaza():
    from comun import cargar_config
    cfg = cargar_config()
    # Vilcún: 741.000 E / 5.716.000 N cae en 18S dentro de La Araucanía
    assert g8.huso_utm(741_000, 5_716_000, cfg) == "EPSG:32718"
    # Coordenada del norte de Chile: no debe aterrizar en la región
    assert g8.huso_utm(400_000, 7_400_000, cfg) is None


def test_agrupar_reconstruye_numero_desde_glifos_sueltos():
    """El PDF emite cada dígito por separado; hay que reagrupar por geometría."""
    items = []
    x = 100.0
    for ch in "740500":
        items.append({"c": ch, "l": x, "b": 50.0, "r": x + 4.0, "t": 55.76,
                      "cx": x + 2.0, "cy": 52.88, "w": 4.0, "h": 5.76})
        x += 4.2
    got = g8.agrupar(items, horizontal=True)
    assert len(got) == 1 and got[0]["valor"] == 740500
