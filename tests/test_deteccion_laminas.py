"""Verificación del detector de láminas cartográficas dentro de los informes.

Es la lógica que decide qué se publica en el catálogo público. Sus dos formas de
fallar tienen costos distintos y hay que probar ambas:

  · falso negativo → la lámina de inundación de una comuna queda sepultada, que
    es exactamente el problema que el proyecto intenta resolver;
  · falso positivo → se manda a un vecino a la página 86 de un informe donde no
    hay ningún mapa, y el catálogo pierde credibilidad.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

_spec = importlib.util.spec_from_file_location(
    "g7", RAIZ / "scripts" / "07_buscar_laminas_riesgo.py")
g7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g7)

CARTA = 792 * 612          # hoja tamaño carta apaisada, en pt²
PLOTER = 4535 * 1700       # hoja de plóter de 160 x 60 cm


def test_plano_de_ploter_se_detecta_pese_a_tener_mucho_texto():
    """Caso Vilcún: 150x60 cm, 5.018 trazos, 6.000 caracteres de rótulos.

    El criterio ingenuo "poco texto + una imagen" da CERO sobre estos planos.
    """
    assert g7.clasificar_lamina(area=PLOTER, caracteres=7022, n_img=188,
                                n_trazo=5270, n_texto=18470,
                                frac_img=0.01) == "plano"


def test_lamina_rasterizada_en_informe_carta():
    """Caso Temuco: catastro de anegamientos, imagen que ocupa media hoja."""
    assert g7.clasificar_lamina(area=CARTA, caracteres=321, n_img=1, n_trazo=0,
                                n_texto=40, frac_img=0.54) == "raster"


def test_logo_del_pie_de_pagina_no_convierte_texto_en_lamina():
    """El falso positivo real: página de texto con el logo de la consultora.

    Estaba marcando como 'lámina' páginas que sólo tienen prosa.
    """
    assert g7.clasificar_lamina(area=CARTA, caracteres=1317, n_img=1, n_trazo=2,
                                n_texto=300, frac_img=0.02) is None


def test_pagina_de_texto_sin_imagen_no_es_lamina():
    assert g7.clasificar_lamina(area=CARTA, caracteres=2800, n_img=0, n_trazo=0,
                                n_texto=400, frac_img=0.0) is None


def test_pagina_con_imagen_grande_pero_mucho_texto_no_es_lamina():
    """Una figura pequeña dentro de una página densa no es una lámina."""
    assert g7.clasificar_lamina(area=CARTA, caracteres=3200, n_img=1, n_trazo=0,
                                n_texto=500, frac_img=0.30) is None


def test_hoja_grande_pero_casi_vacia_no_es_plano():
    """Una portada en formato grande no es cartografía."""
    assert g7.clasificar_lamina(area=PLOTER, caracteres=120, n_img=1, n_trazo=3,
                                n_texto=20, frac_img=0.05) is None


def test_si_no_se_puede_medir_la_imagen_se_cae_al_criterio_laxo():
    """Antes que perder la lámina en silencio, se deja pasar para revisión.

    Cubre el caso de una versión de pypdfium2 sin el método de bounding box.
    """
    assert g7.clasificar_lamina(area=CARTA, caracteres=300, n_img=1, n_trazo=0,
                                n_texto=30, frac_img=0.0,
                                fallo_caja=True) == "raster"
    # pero con la caja medida y una imagen chica, sigue siendo un rechazo
    assert g7.clasificar_lamina(area=CARTA, caracteres=300, n_img=1, n_trazo=0,
                                n_texto=30, frac_img=0.02,
                                fallo_caja=False) is None


def test_caja_tolera_ambos_nombres_de_metodo():
    """pypdfium2 expone `get_bounds`; otras versiones usaron `get_pos`."""
    class ConBounds:
        def get_bounds(self):
            return (10.0, 20.0, 110.0, 220.0)

    class ConPos:
        def get_pos(self):
            return (1.0, 2.0, 3.0, 4.0)

    class SinNada:
        pass

    assert g7._caja(ConBounds()) == (10.0, 20.0, 110.0, 220.0)
    assert g7._caja(ConPos()) == (1.0, 2.0, 3.0, 4.0)
    assert g7._caja(SinNada()) is None
