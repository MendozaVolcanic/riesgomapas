"""Verificación del núcleo de detección de agua en Sentinel-1.

Este módulo decide qué se pinta como «inundado» en un visor público. Sus errores
no se ven: producen una mancha plausible en el lugar equivocado, o dejan de
marcar una población anegada. Ninguna de las dos cosas levanta una excepción.

Por eso lo que se prueba acá no es que el código corra, sino que se sostengan
las propiedades físicas que el módulo declara en su docstring:

  · el agua permanente NO es inundación —el río estaba ahí antes—;
  · la sombra de radar, que es estática dentro de una misma órbita relativa,
    tiene que cancelarse sola en la diferencia pre/post;
  · una caída de 3 dB que deja al píxel en −7 dB es un cambio de cultivo, no
    una lámina de agua;
  · la calibración tiene que aterrizar en la fila correcta de la escena: un
    desfase de media celda corre toda la imagen sin que nada falle;
  · quitar vértices colineales aliviana el GeoJSON pero no puede mover un solo
    borde, porque el borde es el dato.
"""
from __future__ import annotations

import importlib.util
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

_spec = importlib.util.spec_from_file_location("sar", RAIZ / "scripts" / "sar.py")
sar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sar)


# =========================================================== ayudas de armado

def xml_calibracion(lineas, pixeles, sigma) -> bytes:
    """Reproduce el `calibration-iw-vv.xml` del anexo SAFE, en memoria.

    Mismo esqueleto que el real: raíz `<calibration>`, una
    `<calibrationVectorList>` y, dentro de cada `<calibrationVector>`, la línea
    suelta y las series de píxel y sigmaNought separadas por espacios.
    """
    vectores = []
    for linea, fila in zip(lineas, sigma):
        px = " ".join(repr(float(p)) for p in pixeles)
        sg = " ".join(repr(float(s)) for s in fila)
        vectores.append(
            "<calibrationVector>"
            f"<line>{linea}</line>"
            f'<pixel count="{len(pixeles)}">{px}</pixel>'
            f'<sigmaNought count="{len(fila)}">{sg}</sigmaNought>'
            "</calibrationVector>"
        )
    cuerpo = "".join(vectores)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<calibration><adsHeader><polarisation>VV</polarisation></adsHeader>"
        f'<calibrationVectorList count="{len(vectores)}">{cuerpo}</calibrationVectorList>'
        "</calibration>"
    ).encode("utf-8")


def anillo_rectangulo(x0, y0, x1, y1, intermedios):
    """Rectángulo cerrado con vértices colineales de más en cada lado.

    Es lo que devuelve `rasterio.features.shapes`: el contorno píxel a píxel,
    donde un borde recto de 200 píxeles sale con 200 vértices.
    """
    pts: list[list[float]] = []
    esquinas = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    for k in range(4):
        a, b = esquinas[k], esquinas[(k + 1) % 4]
        for i in range(intermedios + 1):
            t = i / (intermedios + 1)
            pts.append([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
    pts.append([x0, y0])
    return pts


def poligono(*anillos) -> dict:
    return {"type": "Polygon", "coordinates": [list(a) for a in anillos]}


# ===================================================== lectura de calibración

def test_lut_se_lee_con_las_formas_y_los_valores_del_producto():
    """La tabla es una rejilla (línea × píxel); si se traspone, la escena se cruza."""
    lineas = [0.0, 500.0, 1000.0]
    pixeles = [0.0, 250.0, 500.0, 750.0]
    sigma = [[100.0, 101.0, 102.0, 103.0],
             [200.0, 201.0, 202.0, 203.0],
             [300.0, 301.0, 302.0, 303.0]]

    ln, px, sg = sar.leer_lut_sigma_nought(xml_calibracion(lineas, pixeles, sigma))

    assert ln.shape == (3,) and px.shape == (4,)
    assert sg.shape == (3, 4), "sigma va (n_líneas, n_píxeles), no al revés"
    assert np.array_equal(ln, np.array(lineas))
    assert np.array_equal(px, np.array(pixeles))
    assert np.array_equal(sg, np.array(sigma))


def test_sin_lista_de_vectores_no_hay_calibracion_posible():
    """Sin tabla no se puede pasar de cuentas digitales a σ⁰: hay que parar."""
    xml = b"<calibration><adsHeader/></calibration>"
    with pytest.raises(ValueError):
        sar.leer_lut_sigma_nought(xml)


def test_lista_de_vectores_vacia_tambien_revienta():
    """Una lista presente pero vacía es igual de inservible que no tenerla."""
    xml = b'<calibration><calibrationVectorList count="0"></calibrationVectorList></calibration>'
    with pytest.raises(ValueError):
        sar.leer_lut_sigma_nought(xml)


def test_series_de_largo_distinto_se_rechazan():
    """Si sobran o faltan valores de sigmaNought, la tabla quedó truncada."""
    xml = (
        '<?xml version="1.0"?><calibration><calibrationVectorList count="1">'
        "<calibrationVector><line>0</line>"
        "<pixel>0 100 200 300</pixel>"
        "<sigmaNought>500.0 501.0 502.0</sigmaNought>"
        "</calibrationVector></calibrationVectorList></calibration>"
    ).encode("utf-8")
    with pytest.raises(ValueError):
        sar.leer_lut_sigma_nought(xml)


def test_rejilla_de_pixeles_que_cambia_entre_vectores_es_error_fatal():
    """Éste es el error caro: interpolar sobre ejes que no coinciden.

    Nada falla, nada queda en NaN: sale una calibración suave y creíble, aplicada
    a coordenadas equivocadas. Un resultado plausible y errado es peor que una
    excepción, así que el módulo tiene que negarse a seguir.
    """
    lineas = [0.0, 500.0]
    sigma = [[100.0, 101.0, 102.0], [200.0, 201.0, 202.0]]
    xml = xml_calibracion(lineas, [0.0, 250.0, 500.0], sigma).decode("utf-8")
    # Se cambia la rejilla de píxeles sólo del segundo vector.
    partes = xml.split("</calibrationVector>")
    partes[1] = partes[1].replace("0.0 250.0 500.0", "0.0 300.0 600.0", 1)
    with pytest.raises(ValueError):
        sar.leer_lut_sigma_nought("</calibrationVector>".join(partes).encode("utf-8"))


# ================================================= interpolación de la tabla

def test_una_lut_lineal_se_reproduce_exactamente():
    """La bilineal es exacta sobre funciones lineales: si no lo es, está mal armada.

    La tabla real varía suavemente con el rango, así que una interpolación que ni
    siquiera reproduce un plano introduce un sesgo de calibración que se arrastra
    hasta los decibeles y corre el umbral de agua.
    """
    lineas = np.array([0.0, 500.0, 1000.0, 1500.0])
    pixeles = np.array([0.0, 250.0, 500.0, 750.0, 1000.0])
    sigma = 300.0 + 0.02 * lineas[:, None] + 0.005 * pixeles[None, :]

    alto, ancho, factor = 8, 10, 100
    salida = sar.interpolar_lut(lineas, pixeles, sigma, alto, ancho, factor)

    gx = (np.arange(ancho) + 0.5) * factor
    gy = (np.arange(alto) + 0.5) * factor
    esperado = 300.0 + 0.02 * gy[:, None] + 0.005 * gx[None, :]
    assert salida.shape == (alto, ancho)
    assert np.allclose(salida, esperado, rtol=0, atol=1e-3), salida - esperado


def test_la_fila_i_cae_en_el_centro_de_la_celda_decimada():
    """Protege el `(i + 0,5) · factor`, que es dónde queda la escena en el mundo.

    Si alguien quita el `+ 0,5`, la calibración se muestrea en el borde de la
    celda y no en su centro: media celda de desfase. Si quita el `· factor`, la
    tabla se aplica como si no hubiera decimación y la escena queda corrida por
    completo. Ninguna de las dos cosas produce NaN ni error; sólo un mapa mal
    puesto. Con una LUT que vale exactamente el número de línea, la salida tiene
    que delatar el desfase.
    """
    lineas = np.array([0.0, 1000.0, 2000.0])
    pixeles = np.array([0.0, 1000.0])
    sigma = np.repeat(lineas[:, None], 2, axis=1)   # sigma = número de línea

    alto, factor = 6, 100
    salida = sar.interpolar_lut(lineas, pixeles, sigma, alto, 3, factor)

    esperado = (np.arange(alto) + 0.5) * factor
    assert np.allclose(salida[:, 0], esperado, rtol=0, atol=1e-2), salida[:, 0]
    assert np.allclose(salida[:, 2], esperado, rtol=0, atol=1e-2)


def test_la_columna_j_cae_en_el_centro_en_rango():
    """Lo mismo en el eje de rango: la columna j es el píxel (j + 0,5) · factor."""
    lineas = np.array([0.0, 1000.0])
    pixeles = np.array([0.0, 500.0, 1000.0])
    sigma = np.repeat(pixeles[None, :], 2, axis=0)  # sigma = número de píxel

    ancho, factor = 5, 40
    salida = sar.interpolar_lut(lineas, pixeles, sigma, 3, ancho, factor)

    esperado = (np.arange(ancho) + 0.5) * factor
    assert np.allclose(salida[0], esperado, rtol=0, atol=1e-2), salida[0]


def test_dimensiones_no_positivas_se_rechazan():
    """Una escena de alto o ancho cero es un producto roto, no un caso borde."""
    lineas = np.array([0.0, 100.0])
    pixeles = np.array([0.0, 100.0])
    sigma = np.ones((2, 2))
    with pytest.raises(ValueError):
        sar.interpolar_lut(lineas, pixeles, sigma, 0, 10, 4)
    with pytest.raises(ValueError):
        sar.interpolar_lut(lineas, pixeles, sigma, 10, -1, 4)


# ========================================================= cuentas → σ⁰ → dB

def test_sigma0_es_el_cuadrado_del_dn_sobre_el_cuadrado_de_la_lut():
    """σ⁰ = DN²/A². El cuadrado no es decorativo: el GRD guarda amplitud.

    Olvidarlo deja los decibeles a la mitad y con ello el contraste tierra-agua,
    que es todo lo que este pipeline mide.
    """
    dn = np.array([100.0, 500.0, 250.0])
    lut = np.array([10.0, 100.0, 250.0])
    got = sar.a_sigma0(dn, lut)
    assert np.allclose(got, [100.0, 25.0, 1.0])


def test_el_borde_de_la_escena_queda_en_cero_y_no_en_un_valor_cualquiera():
    """DN = 0 es «no hay dato», el relleno del recorte del GRD.

    Si se dejara entrar a la fórmula daría σ⁰ = 0 → −inf dB, es decir el píxel
    más oscuro posible: todo el borde de la escena se marcaría como agua.
    """
    dn = np.array([0.0, 100.0, 0.0])
    lut = np.array([10.0, 10.0, 0.0])
    got = sar.a_sigma0(dn, lut)
    assert got[0] == 0.0
    assert got[2] == 0.0, "una LUT nula tampoco puede dividir"
    assert got[1] == pytest.approx(100.0)


def test_sin_dato_va_a_nan_y_nunca_a_menos_infinito():
    """−inf dB contamina medianas, percentiles y umbrales; NaN se puede excluir.

    Todo el criterio de agua se apoya en percentiles y desviaciones sobre pilas
    de fechas. Un solo −inf arrastra al promedio de la pila entera.
    """
    lineal = np.array([1.0, 0.0, -3.0, np.nan, 100.0])
    got = sar.a_db(lineal)
    assert got[0] == pytest.approx(0.0)
    assert got[4] == pytest.approx(20.0)
    assert np.isnan(got[1]) and not np.isneginf(got[1])
    assert np.isnan(got[2]), "un σ⁰ negativo no tiene logaritmo"
    assert np.isnan(got[3])


# ================================================ umbral derivado de la escena

def agua_conocida(n_oscuros=180, n_claros=20, oscuro=-25.0, claro=-18.0, nan=0):
    """Pila de píxeles de agua permanente con percentil 90 calculable a mano."""
    vals = [oscuro] * n_oscuros + [claro] * n_claros + [np.nan] * nan
    post = np.array(vals, dtype=float)
    return post, np.ones(post.shape, dtype=bool)


def test_el_umbral_sale_del_agua_que_ya_se_sabe_que_es_agua():
    """El percentil 90 del agua permanente vista el mismo día y con la misma geometría.

    Es lo que evita importar un umbral de la literatura, que arrastra el sesgo de
    otro sensor y otro procesamiento. Con 180 píxeles a −25 dB y 20 a −18 dB el
    percentil 90 cae en −24,3 dB por interpolación lineal, sin ambigüedad.
    """
    post, perm = agua_conocida()
    aplicado, crudo, n = sar.umbral_agua(post, perm, minimo=-30.0, maximo=-10.0,
                                         respaldo=-18.0)
    assert crudo == pytest.approx(-24.3)
    assert aplicado == pytest.approx(-24.3), "dentro del rango no se toca"
    assert n == 200


def test_un_umbral_absurdamente_oscuro_se_acota_por_abajo():
    """Escena con poca agua permanente: el percentil puede dar un número imposible.

    Un umbral de −40 dB no marcaría ni el lago; acotarlo al mínimo mantiene el
    detector funcionando en vez de devolver una escena vacía y silenciosa.
    """
    post, perm = agua_conocida(oscuro=-40.0, claro=-40.0)
    aplicado, crudo, _ = sar.umbral_agua(post, perm, minimo=-30.0, maximo=-10.0,
                                         respaldo=-18.0)
    assert crudo == pytest.approx(-40.0)
    assert aplicado == pytest.approx(-30.0)


def test_un_umbral_demasiado_claro_se_acota_por_arriba():
    """Con oleaje el agua permanente se ilumina y el percentil sube.

    Sin tope, un umbral de −5 dB declararía agua medio campo. El máximo es la
    salvaguarda contra el día de viento.
    """
    post, perm = agua_conocida(oscuro=-5.0, claro=-5.0)
    aplicado, crudo, _ = sar.umbral_agua(post, perm, minimo=-30.0, maximo=-10.0,
                                         respaldo=-18.0)
    assert crudo == pytest.approx(-5.0)
    assert aplicado == pytest.approx(-10.0)


def test_con_poca_agua_permanente_se_usa_el_respaldo_y_se_declara():
    """Menos de 100 píxeles no sostienen un percentil: hay que decirlo, no fingirlo.

    Se devuelve NaN como valor crudo justamente para que quien lea el reporte no
    confunda «no se pudo calcular» con «se calculó y dio el respaldo».
    """
    post, perm = agua_conocida(n_oscuros=90, n_claros=9)
    aplicado, crudo, n = sar.umbral_agua(post, perm, minimo=-30.0, maximo=-10.0,
                                         respaldo=-18.5)
    assert aplicado == pytest.approx(-18.5)
    assert math.isnan(crudo)
    assert n == 99, "hay que informar cuántos píxeles había, no sólo que faltaban"


def test_los_pixeles_sin_dato_no_cuentan_como_soporte():
    """120 píxeles de agua permanente, 30 sin dato: el soporte real son 90."""
    post, perm = agua_conocida(n_oscuros=80, n_claros=10, nan=30)
    aplicado, crudo, n = sar.umbral_agua(post, perm, minimo=-30.0, maximo=-10.0,
                                         respaldo=-18.5)
    assert n == 90
    assert math.isnan(crudo) and aplicado == pytest.approx(-18.5)


# ==================================================== agua permanente y nueva

def test_agua_permanente_exige_oscuridad_y_estabilidad_a_la_vez():
    """Oscuro solo no basta; estable solo tampoco.

    Un lago con oleaje entre pasadas es agua, pero no es una referencia estable:
    tomarlo como agua permanente contaminaría el umbral de la escena. Y una
    superficie oscura que varía es sospechosa de otra cosa (cultivo, camino).
    """
    pre = np.array([-24.0, -24.0, -8.0, np.nan, -24.0, -18.0])
    desv = np.array([0.4, 3.0, 0.3, 0.5, np.nan, 1.5])
    got = sar.agua_permanente(pre, desv, umbral_db=-18.0, estabilidad_db=1.5)
    assert list(got) == [True, False, False, False, False, True]


# Caso de referencia que sí tiene que salir marcado: cae 13 dB, queda en −22 dB,
# referencia estable y diez pasadas previas. Va como control en cada prueba
# negativa, para que un `False` no pueda deberse a que la máscara salió vacía.
INUNDACION = (-22.0, -9.0, 0.5, 10, False)


def mascara(casos, **kw):
    """Corre el criterio sobre una lista de (post, pre_mediana, pre_desv, n_pre, permanente)."""
    params = dict(umbral_agua_db=-18.0, caida_db=-3.0, estabilidad_db=1.5, min_pre=4)
    params.update(kw)
    return sar.detectar_agua_nueva(
        post_db=np.array([c[0] for c in casos], dtype=float),
        pre_mediana_db=np.array([c[1] for c in casos], dtype=float),
        pre_desv_db=np.array([c[2] for c in casos], dtype=float),
        n_pre=np.array([c[3] for c in casos], dtype=int),
        permanente=np.array([c[4] for c in casos], dtype=bool),
        **params,
    )


def test_una_inundacion_de_verdad_se_detecta():
    """Suelo vegetado a −9 dB que amanece en −22 dB: eso es una lámina de agua."""
    assert list(mascara([INUNDACION])) == [True]


def test_el_agua_permanente_no_se_marca_como_inundacion():
    """El río estaba ahí antes. Marcarlo sería el error más vistoso del pipeline.

    Un mapa que dibuja el Cautín como inundación se desacredita en el primer
    vistazo de cualquier vecino, y con él todo el resto de la capa.
    """
    got = mascara([(-24.0, -24.0, 0.4, 10, True), INUNDACION])
    assert list(got) == [False, True]


def test_la_sombra_de_radar_se_cancela_sola():
    """Lo estático no cambia entre pasadas de la misma órbita relativa.

    La sombra detrás de un cerro y el asfalto liso son tan oscuros como el agua,
    pero lo eran también antes del evento. Por eso el criterio principal es el
    cambio y no la oscuridad: la geometría de vista se resta a sí misma.
    """
    got = mascara([(-20.0, -20.0, 0.3, 10, False), INUNDACION])
    assert list(got) == [False, True]


def test_una_caida_que_deja_al_pixel_en_menos_siete_db_no_es_agua():
    """Cae los 3 dB exigidos, pero −7 dB sigue siendo tierra.

    Es el cultivo que se cosecha entre pasadas. La oscuridad absoluta es el
    filtro que impide que un cambio agrícola se publique como inundación.
    """
    got = mascara([(-7.0, -4.0, 0.5, 10, False), INUNDACION])
    assert list(got) == [False, True]


def test_una_referencia_inestable_no_sostiene_ninguna_conclusion():
    """Un píxel que ya oscilaba 3 dB entre pasadas no permite leer una caída puntual.

    Con esa varianza, la «caída» puede ser sólo la próxima oscilación: la
    mediana pre-evento no describe un estado, describe un ruido.
    """
    got = mascara([(-22.0, -9.0, 3.0, 10, False), INUNDACION])
    assert list(got) == [False, True]


def test_sin_suficientes_pasadas_previas_no_hay_referencia():
    """Con dos imágenes previas no hay mediana que valga.

    Una sola pasada previa confunde suelo mojado por lluvia reciente con lámina
    de agua; la mediana necesita varias fechas para representar «cómo se ve este
    píxel normalmente».
    """
    got = mascara([(-22.0, -9.0, 0.5, 2, False), INUNDACION])
    assert list(got) == [False, True]


def test_los_huecos_sin_dato_no_se_detectan_ni_hacen_ruido():
    """NaN en cualquier entrada es «no sé», y «no sé» nunca es «inundado».

    Además la comparación no puede llenar el log de avisos de numpy: en una
    escena de millones de píxeles con borde de relleno, el aviso se repite hasta
    tapar cualquier mensaje que sí importe.
    """
    casos = [
        (np.nan, -9.0, 0.5, 10, False),   # sin post
        (-22.0, np.nan, 0.5, 10, False),  # sin mediana pre
        (-22.0, -9.0, np.nan, 10, False), # sin desviación pre
        INUNDACION,
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with np.errstate(all="warn"):
            got = mascara(casos)
    assert list(got) == [False, False, False, True]


# ============================================================ vectorización

def test_un_borde_recto_se_reduce_a_sus_esquinas():
    """Un rectángulo de 41 vértices tiene 4 esquinas; el resto es peso muerto.

    El GeoJSON de esta capa se descarga por una conexión mala y tiene que quedar
    en caché para servir sin señal. Cada vértice colineal es peso que no aporta
    ni un metro de información.
    """
    denso = anillo_rectangulo(-72.60, -38.76, -72.50, -38.74, intermedios=9)
    assert len(denso) == 41
    ligero = sar.quitar_colineales(denso)
    assert len(ligero) == 5, ligero
    assert ligero[0] == ligero[-1], "el anillo tiene que seguir cerrado"
    esquinas = {(-72.60, -38.76), (-72.50, -38.76), (-72.50, -38.74), (-72.60, -38.74)}
    assert {tuple(p) for p in ligero[:-1]} == esquinas


def test_quitar_colineales_no_mueve_la_geometria_ni_un_grado():
    """Ésta es la comprobación que importa: no es simplificación con tolerancia.

    Si la «optimización» deformara el polígono, el visor mostraría una superficie
    inundada distinta de la que se midió, y nadie lo notaría porque el mapa
    seguiría viéndose bien. El área en grados² es el invariante puro de la
    geometría y tiene que coincidir hasta el redondeo de punto flotante.
    """
    denso = anillo_rectangulo(-72.60, -38.76, -72.50, -38.74, intermedios=9)
    ligero = sar.quitar_colineales(denso)
    assert sar.area_anillo_grados(ligero) == pytest.approx(
        sar.area_anillo_grados(denso), rel=1e-9)


def test_el_area_en_metros_sobrevive_al_aligerado():
    """El área reportada en hectáreas —el número que se publica— no cambia.

    La tolerancia es 10⁻⁴ relativo y no cero por una razón concreta: la escala
    m²/grado² se evalúa en `lat_media`, que es el promedio de los vértices del
    anillo, y no su centroide. Al borrar vértices ese promedio se corre unos
    milésimos de grado y el coseno cambia en ~2·10⁻⁵ relativo. Es un sesgo mil
    veces menor que el propio error de la aproximación cilíndrica (~0,2 %), pero
    existe, y fijar `rel=0` haría fallar el test por la razón equivocada.
    """
    denso = anillo_rectangulo(-72.60, -38.76, -72.50, -38.74, intermedios=9)
    ligero = sar.quitar_colineales(denso)
    assert sar.area_poligono_m2(poligono(ligero)) == pytest.approx(
        sar.area_poligono_m2(poligono(denso)), rel=1e-4)


def test_una_geometria_sin_colineales_queda_intacta():
    """Sin nada que quitar, la función no puede inventar ni perder vértices."""
    triangulo = [[-72.6, -38.8], [-72.5, -38.8], [-72.55, -38.7], [-72.6, -38.8]]
    assert sar.quitar_colineales(triangulo) == triangulo


def test_un_anillo_degenerado_no_revienta():
    """`rasterio` entrega manchas de un píxel y restos de speckle.

    El vectorizador corre sobre miles de polígonos sin supervisión: un anillo de
    dos puntos, o uno enteramente colineal, tiene que devolverse tal cual en vez
    de tumbar la corrida completa.
    """
    assert sar.quitar_colineales([[0.0, 0.0], [1.0, 0.0]]) == [[0.0, 0.0], [1.0, 0.0]]
    degenerado = [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [0.0, 0.0]]
    assert sar.quitar_colineales(degenerado) == degenerado


def test_area_de_un_cuadrado_conocido_contra_el_elipsoide():
    """Un cuadrado de 0,01° a 38,75° S, comparado con la geodesia de verdad.

    La tolerancia es 0,5 % y está elegida así: la aproximación cilíndrica usa un
    radio esférico único (111.320 m/grado) mientras que en WGS84, a esta
    latitud, el arco de meridiano vale 111.011 m/grado y el de paralelo
    86.932 m/grado. La discrepancia estructural entre ambos modelos es de ~0,16 %
    acá, así que 0,5 % deja pasar la aproximación declarada pero atrapa cualquier
    error real de factor —un coseno olvidado serían 28 %, un grado en vez de
    metros, órdenes de magnitud—. Y 0,16 % es despreciable frente a la
    incertidumbre del propio píxel SAR, que es de decenas de metros.
    """
    m_por_grado_lat = 111_010.7   # arco de meridiano WGS84 a 38,75°
    m_por_grado_lon = 86_931.8    # arco de paralelo WGS84 a 38,75°
    esperada = (0.01 * m_por_grado_lat) * (0.01 * m_por_grado_lon)

    cuadrado = [[-72.60, -38.75], [-72.59, -38.75],
                [-72.59, -38.74], [-72.60, -38.74], [-72.60, -38.75]]
    assert sar.area_poligono_m2(poligono(cuadrado)) == pytest.approx(esperada, rel=5e-3)


def test_un_hueco_se_descuenta_del_area():
    """Un sector seco dentro de la mancha no es superficie inundada.

    Sumar el hueco infla las hectáreas reportadas, que es el número con el que se
    dimensiona una emergencia.
    """
    externo = [[-72.60, -38.75], [-72.58, -38.75],
               [-72.58, -38.73], [-72.60, -38.73], [-72.60, -38.75]]
    # Hueco de 0,01° × 0,01°: exactamente un cuarto del área externa.
    hueco = [[-72.595, -38.745], [-72.585, -38.745],
             [-72.585, -38.735], [-72.595, -38.735], [-72.595, -38.745]]

    llena = sar.area_poligono_m2(poligono(externo))
    con_hueco = sar.area_poligono_m2(poligono(externo, hueco))
    assert con_hueco == pytest.approx(llena * 0.75, rel=1e-9)
    assert con_hueco < llena


def test_redondear_conserva_los_anillos_cerrados():
    """Un anillo abierto es un GeoJSON inválido: no lo dibuja ningún visor."""
    externo = [[-72.6012345678, -38.7512345678], [-72.5812345678, -38.7512345678],
               [-72.5812345678, -38.7312345678], [-72.6012345678, -38.7312345678],
               [-72.6012345678, -38.7512345678]]
    got = sar.redondear(poligono(externo), decimales=4)
    assert got["type"] == "Polygon"
    assert got["coordinates"][0][0] == got["coordinates"][0][-1]
    assert got["coordinates"][0][0] == [-72.6012, -38.7512]


def test_aligerar_deja_un_geojson_valido_con_hueco_incluido():
    """Aligerar toca todos los anillos, y todos tienen que seguir cerrados.

    El hueco es un anillo más: si el aligerado lo dejara abierto, el polígono
    completo se caería del mapa sin ningún error a la vista.
    """
    externo = anillo_rectangulo(-72.60, -38.76, -72.50, -38.74, intermedios=5)
    hueco = anillo_rectangulo(-72.57, -38.755, -72.55, -38.745, intermedios=3)
    got = sar.aligerar(poligono(externo, hueco), decimales=6)

    assert got["type"] == "Polygon"
    assert len(got["coordinates"]) == 2
    for anillo in got["coordinates"]:
        assert anillo[0] == anillo[-1], "cada anillo tiene que cerrar"
        assert len(anillo) == 5, "cada rectángulo queda en sus cuatro esquinas"


def test_area_de_pixel_encoge_con_la_latitud():
    """Los meridianos convergen: el mismo paso en grados cubre menos metros al sur.

    De acá salen las hectáreas por píxel y el filtro de manchas mínimas; usar el
    área ecuatorial sobrestimaría la superficie inundada en La Araucanía.
    """
    ecuador = sar.area_pixel_m2(0.0004, 0.0)
    araucania = sar.area_pixel_m2(0.0004, -38.75)
    assert araucania < ecuador
    assert araucania / ecuador == pytest.approx(math.cos(math.radians(38.75)), rel=1e-9)
