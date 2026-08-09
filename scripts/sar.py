"""Núcleo de la capa B — detección de agua en Sentinel-1 GRD.

Aquí vive la parte del pipeline SAR que se puede probar sin red: la lectura de
la tabla de calibración, la conversión a σ⁰, el criterio de agua y la
vectorización. El script `14_sar_huella_observada.py` es el que va a buscar los
datos y orquesta.

FÍSICA, QUE ES LO QUE HAY QUE ENTENDER ANTES QUE EL CÓDIGO
-----------------------------------------------------------
Un radar de apertura sintética ilumina el terreno de lado y mide cuánta energía
le vuelve. Una superficie rugosa a la escala de la longitud de onda (5,6 cm en
banda C) devuelve energía en todas direcciones, y algo llega de vuelta al
satélite: el suelo vegetado marca del orden de −9 dB. Una lámina de agua quieta
es un espejo a esa escala: refleja casi todo hacia adelante, lejos del sensor, y
vuelve muy poco. Medido sobre el lago Villarrica el 4-ago-2026: **−24,7 dB**,
quince decibeles bajo la tierra que lo rodea.

Esa diferencia es la que permite ver la inundación. Pero «oscuro» no basta:
también son oscuros el asfalto liso, la sombra de radar detrás de un cerro y el
propio río. Por eso el criterio no es oscuridad sino **cambio respecto de cómo
se veía ese mismo píxel antes**, con estas consecuencias:

  - La sombra de radar y el relieve son estáticos: si se comparan dos pasadas de
    la MISMA órbita relativa, la geometría de vista es la misma y la sombra se
    cancela sola. De ahí la regla de emparejar por órbita relativa y no por
    fecha: dos pasadas de geometría distinta difieren por el terreno, no por el
    agua.
  - El agua permanente es oscura en las dos fechas: no hay caída, no se marca.
  - Una superficie que ya venía variando entre pasadas (un cultivo que se
    cosecha, un lago con oleaje) no permite concluir nada de una caída puntual.
    Por eso se exige que la referencia pre-evento sea estable.

Lo que este método NO ve, y que hay que declarar siempre:
  - Agua bajo dosel cerrado: la copa devuelve la señal antes de llegar al suelo.
  - Agua en zona urbana densa: el doble rebote pared-suelo mantiene la
    retrodispersión alta aunque haya agua. Subestima justo donde vive la gente.
  - Agua con viento: el oleaje capilar rugosiza la superficie y la ilumina.
  - Agua que se retiró antes de la pasada: es una foto, no un máximo del evento.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np

# Radio de la Tierra usado para pasar grados a metros. No se busca precisión
# geodésica: es para reportar hectáreas y para filtrar manchas de speckle.
_M_POR_GRADO_LAT = 111_320.0


# --------------------------------------------------------------- calibración

def leer_lut_sigma_nought(xml: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extrae la tabla de calibración `sigmaNought` del anexo SAFE.

    El GRD se distribuye en cuentas digitales, no en unidades físicas. Para
    llegar a σ⁰ hace falta la tabla que el propio producto trae en
    `annotation/calibration/calibration-iw-vv.xml`, muestreada en una rejilla
    regular de (línea, píxel) sobre la escena en geometría de radar.

    Devuelve (líneas, píxeles, sigma) con sigma de forma (n_líneas, n_píxeles).
    """
    raiz = ET.fromstring(xml)
    lista = raiz.find("calibrationVectorList")
    if lista is None or len(lista) == 0:
        raise ValueError("el XML de calibración no trae calibrationVectorList")

    lineas: list[float] = []
    filas: list[np.ndarray] = []
    pixeles: np.ndarray | None = None
    for v in lista:
        # Un vector incompleto tiene que reventar como ValueError igual que el
        # resto de los rechazos de esta función, no como un AttributeError de
        # `None.text` que en el traceback parece un error de programación.
        campos = {}
        for nombre in ("line", "pixel", "sigmaNought"):
            nodo = v.find(nombre)
            if nodo is None or not (nodo.text or "").strip():
                raise ValueError(f"vector de calibración sin <{nombre}>")
            campos[nombre] = nodo.text
        lineas.append(float(campos["line"]))
        px = np.fromstring(campos["pixel"], sep=" ")
        sg = np.fromstring(campos["sigmaNought"], sep=" ")
        if sg.size != px.size:
            raise ValueError("sigmaNought y pixel tienen largos distintos")
        # La rejilla de píxeles es la misma en todos los vectores de un producto.
        # Si algún día deja de serlo, mejor reventar que interpolar sobre ejes
        # que no coinciden.
        if pixeles is None:
            pixeles = px
        elif not np.array_equal(px, pixeles):
            raise ValueError("la rejilla de píxeles cambia entre vectores de calibración")
        filas.append(sg)
    return np.asarray(lineas, float), pixeles, np.vstack(filas)


def interpolar_lut(
    lineas: np.ndarray,
    pixeles: np.ndarray,
    sigma: np.ndarray,
    alto: int,
    ancho: int,
    factor: int,
) -> np.ndarray:
    """Lleva la tabla de calibración a la rejilla decimada que se leyó.

    `factor` es la decimación con que se leyó la escena: la fila `i` del arreglo
    corresponde a la línea `(i + 0,5) · factor` del producto original. Se
    interpola bilinealmente y de forma separable, que es exacto sobre una
    rejilla regular y evita depender de scipy.
    """
    if alto <= 0 or ancho <= 0:
        raise ValueError("alto y ancho deben ser positivos")
    gx = (np.arange(ancho) + 0.5) * factor
    gy = (np.arange(alto) + 0.5) * factor

    # Primero a lo ancho (rango), manteniendo las líneas originales…
    parcial = np.empty((sigma.shape[0], ancho), dtype=np.float64)
    for i in range(sigma.shape[0]):
        parcial[i] = np.interp(gx, pixeles, sigma[i])
    # …después a lo alto (acimut).
    salida = np.empty((alto, ancho), dtype=np.float32)
    for j in range(ancho):
        salida[:, j] = np.interp(gy, lineas, parcial[:, j])
    return salida


def a_sigma0(dn: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Cuentas digitales → σ⁰ lineal. Los píxeles de borde (DN = 0) quedan en 0.

    σ⁰ = DN² / A², la fórmula del manual del producto. El cuadrado es porque el
    GRD guarda amplitud y σ⁰ es una potencia.
    """
    salida = np.zeros(dn.shape, dtype=np.float32)
    valido = (dn > 0) & (lut > 0)
    salida[valido] = (dn[valido].astype(np.float32) ** 2) / (lut[valido] ** 2)
    return salida


def a_db(lineal: np.ndarray) -> np.ndarray:
    """σ⁰ lineal → dB, con NaN donde no hay dato."""
    salida = np.full(lineal.shape, np.nan, dtype=np.float32)
    m = np.isfinite(lineal) & (lineal > 0)
    salida[m] = 10.0 * np.log10(lineal[m])
    return salida


# ------------------------------------------------------------------ criterio

def umbral_agua(
    post_db: np.ndarray,
    permanente: np.ndarray,
    minimo: float,
    maximo: float,
    respaldo: float,
    percentil: float = 90.0,
) -> tuple[float, float, int]:
    """Deriva el umbral de oscuridad del agua permanente de la propia escena.

    Un umbral fijo tomado de la literatura arrastra el sesgo de otro sensor,
    otra geometría y otro procesamiento. Acá hay una referencia mucho mejor a
    mano: el mar, los lagos y los ríos que ya estaban ahí antes del evento son
    agua indiscutible, vista por **el mismo sensor, la misma geometría y el
    mismo día** que la inundación que se quiere detectar. Se toma su percentil
    90 en la imagen post: «tan oscuro como el 90 % del agua que sé que es agua».

    Se acota a [mínimo, máximo] porque una escena con poca agua permanente, o con
    oleaje ese día, puede devolver un número absurdo. Devuelve el valor aplicado,
    el crudo antes de acotar y cuántos píxeles lo sustentan.
    """
    vals = post_db[permanente & np.isfinite(post_db)]
    if vals.size < 100:
        return respaldo, float("nan"), int(vals.size)
    crudo = float(np.percentile(vals, percentil))
    return float(min(max(crudo, minimo), maximo)), crudo, int(vals.size)


def agua_permanente(
    pre_mediana_db: np.ndarray,
    pre_desv_db: np.ndarray,
    umbral_db: float,
    estabilidad_db: float,
) -> np.ndarray:
    """Agua que ya estaba antes del evento: oscura y estable en la referencia."""
    return (
        np.isfinite(pre_mediana_db)
        & (pre_mediana_db <= umbral_db)
        & np.isfinite(pre_desv_db)
        & (pre_desv_db <= estabilidad_db)
    )


def pendiente_grados(dem: np.ndarray, res_grados: float, lat_media: float) -> np.ndarray:
    """Pendiente del terreno en grados, por diferencias centradas.

    Se calcula a la resolución de trabajo y no a la del DEM a propósito: lo que
    interesa es si el terreno es plano **a la escala a la que se está afirmando
    que hay agua**, no la rugosidad de 30 m. Un talud de 30 m dentro de una
    llanura de inundación no la vuelve inapta.
    """
    dy = res_grados * _M_POR_GRADO_LAT
    dx = dy * math.cos(math.radians(lat_media))
    gy, gx = np.gradient(dem.astype(np.float32), dy, dx)
    return np.degrees(np.arctan(np.hypot(gx, gy))).astype(np.float32)


def terreno_apto(
    dem: np.ndarray,
    pendiente: np.ndarray,
    pendiente_max: float,
    altitud_max: float,
    altitud_min: float = 0.0,
) -> np.ndarray:
    """Dónde es físicamente posible que se embalse agua de inundación.

    Es el filtro que separa inundación de **nieve húmeda**, que es el falso
    positivo clásico de este método: en banda C la nieve mojada absorbe casi toda
    la señal y se ve tan oscura como una lámina de agua, así que ningún umbral de
    brillo las distingue. Lo que las distingue es dónde están.

    Dos condiciones, las dos geomorfológicas:
      - **Pendiente baja**: el agua se embalsa en terreno plano. En ladera
        escurre y no deja huella a la hora de la pasada.
      - **Altura acotada**: la nieve de agosto vive en la cordillera. El tope se
        pone alto a propósito, para no borrar las inundaciones reales de los
        valles andinos poblados (Curarrehue, Melipeuco, Lonquimay).

    Y una tercera, `altitud_min`, que excluye **el mar**. No es un detalle
    técnico: sin ella el resultado lo domina el océano. La superficie del mar
    cambia de rugosidad con el viento entre dos pasadas, y una pasada que lo
    encuentra liso lo ve caer más de 5 dB respecto de referencias que lo
    encontraron picado. Eso cumple todos los criterios radiométricos de
    «apareció agua» — y es cierto que apareció agua lisa, sólo que ahí el agua
    siempre estuvo. Medido sobre este evento: el mar aportaba **871 de los 903
    km²** que declaraba la órbita 164A. En el DEM Copernicus el océano vale
    exactamente 0 m, así que basta exigir tierra sobre el nivel del mar.

    Donde no hay DEM el terreno se declara NO apto. Es la decisión conservadora:
    preferimos perder huella real antes que publicar como inundación algo que no
    pudimos descartar.
    """
    return (
        np.isfinite(dem)
        & np.isfinite(pendiente)
        & (pendiente <= pendiente_max)
        & (dem <= altitud_max)
        & (dem > altitud_min)
    )


def detectar_agua_nueva(
    post_db: np.ndarray,
    pre_mediana_db: np.ndarray,
    pre_desv_db: np.ndarray,
    n_pre: np.ndarray,
    umbral_agua_db: float,
    caida_db: float,
    estabilidad_db: float,
    min_pre: int,
    permanente: np.ndarray,
    terreno: np.ndarray | None = None,
) -> np.ndarray:
    """Los cuatro filtros que tienen que cumplirse a la vez.

    Ninguno sobra:
      1. `n_pre ≥ min_pre` — sin varias pasadas de referencia no hay mediana que
         valga; una sola imagen previa confunde suelo mojado con inundación.
      2. caída ≥ |caida_db| respecto de la mediana pre — es el criterio principal
         y el único inmune a sesgos de calibración, porque pre y post pasan por
         el mismo proceso y todo sesgo constante se cancela en la resta. Es
         también el que anula la sombra de radar y el relieve, que son estáticos
         dentro de una misma órbita relativa.
      3. oscuridad absoluta — impide marcar como agua una caída de 3 dB que deja
         al píxel todavía en −7 dB, que no es agua sino un cambio de cultivo.
      4. referencia estable — un píxel que ya oscilaba varios dB entre pasadas no
         sostiene ninguna conclusión a partir de una caída puntual.

    Y se descuenta el agua permanente: el río estaba ahí antes. Mostrarlo como
    inundación sería el error más fácil y más vistoso de este pipeline.

    `terreno` es la máscara de dónde puede embalsarse agua (ver `terreno_apto`).
    Es la que descarta la nieve húmeda de cordillera, que ninguno de los cuatro
    filtros anteriores distingue del agua porque **radiométricamente son lo
    mismo**. Se deja opcional para poder probar el criterio radiométrico solo.
    """
    with np.errstate(invalid="ignore"):
        m = (
            (n_pre >= min_pre)
            & np.isfinite(post_db)
            & np.isfinite(pre_mediana_db)
            & np.isfinite(pre_desv_db)
            & ((post_db - pre_mediana_db) <= caida_db)
            & (post_db <= umbral_agua_db)
            & (pre_desv_db <= estabilidad_db)
            & ~permanente
        )
    if terreno is not None:
        m &= terreno
    return m


# ------------------------------------------------------------- vectorización

def area_anillo_grados(anillo) -> float:
    """Área con signo de un anillo, en grados². Fórmula del cordón de zapato."""
    n = len(anillo)
    if n < 4:
        return 0.0
    s = 0.0
    for i in range(n - 1):
        x1, y1 = anillo[i][0], anillo[i][1]
        x2, y2 = anillo[i + 1][0], anillo[i + 1][1]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def area_poligono_m2(geom: dict) -> float:
    """Área de un polígono lon/lat en m², descontando huecos.

    Aproximación cilíndrica local: a estas latitudes y para manchas de hectáreas
    el error es despreciable frente a la incertidumbre del propio dato SAR.
    """
    anillos = geom["coordinates"]
    if not anillos or len(anillos[0]) < 4:
        return 0.0
    # Punto medio de la extensión en latitud, NO el promedio de los vértices: el
    # promedio depende de cuán densamente esté muestreado el contorno, y
    # `quitar_colineales` cambia exactamente eso. Con el promedio, aligerar la
    # geometría movía las hectáreas publicadas; con el punto medio, la invariante
    # «aligerar no cambia el área» se cumple de verdad.
    lats = [p[1] for p in anillos[0]]
    lat_media = (min(lats) + max(lats)) / 2.0
    escala = (_M_POR_GRADO_LAT ** 2) * math.cos(math.radians(lat_media))
    bruta = abs(area_anillo_grados(anillos[0]))
    huecos = sum(abs(area_anillo_grados(a)) for a in anillos[1:])
    return max(0.0, (bruta - huecos)) * escala


def quitar_colineales(anillo: list, tol: float = 1e-12) -> list:
    """Elimina vértices intermedios de tramos rectos.

    `rasterio.features.shapes` devuelve el contorno pixel a pixel: un borde recto
    de 200 píxeles sale con 200 vértices. Quitar los colineales **no cambia la
    geometría en absoluto** —no es simplificación con tolerancia— y suele bajar a
    la mitad el peso del GeoJSON, que en este proyecto se descarga por una
    conexión mala y tiene que quedar en caché para funcionar sin señal.
    """
    if len(anillo) < 4:
        return anillo
    cerrado = anillo[0] == anillo[-1]
    pts = anillo[:-1] if cerrado else list(anillo)
    if len(pts) < 3:
        return anillo

    salida: list = []
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i - 1]
        bx, by = pts[i]
        cx, cy = pts[(i + 1) % n]
        # Producto cruzado: si b está sobre el segmento a→c, no aporta nada.
        if abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) > tol:
            salida.append(pts[i])
    if len(salida) < 3:
        return anillo
    return salida + [salida[0]]


def redondear(geom: dict, decimales: int = 6) -> dict:
    """Redondea coordenadas. 6 decimales ≈ 0,1 m: sobra para un dato de 40 m."""
    return {
        "type": geom["type"],
        "coordinates": [
            [[round(x, decimales), round(y, decimales)] for x, y in anillo]
            for anillo in geom["coordinates"]
        ],
    }


def aligerar(geom: dict, decimales: int = 6) -> dict:
    """Quita vértices colineales y redondea, sin mover ningún borde real."""
    return redondear(
        {"type": geom["type"],
         "coordinates": [quitar_colineales(a) for a in geom["coordinates"]]},
        decimales,
    )


def area_pixel_m2(res_grados: float, lat: float) -> float:
    """Área nominal de un píxel de la rejilla de salida a una latitud dada."""
    alto = res_grados * _M_POR_GRADO_LAT
    ancho = res_grados * _M_POR_GRADO_LAT * math.cos(math.radians(lat))
    return alto * ancho
