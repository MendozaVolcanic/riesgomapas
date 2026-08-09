"""Núcleo de georreferenciación: ajuste polinómico, error y remuestreo.

Compartido por `04_georreferenciar.py` (puntos de control puestos a mano) y
`08_georreferenciar_grilla.py` (puntos leídos de la grilla UTM impresa).

La regla del proyecto está acá: ningún producto georreferenciado sale sin su
RMSE leave-one-out y su categoría de aptitud de uso.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import Affine

Image.MAX_IMAGE_PIXELS = None  # las láminas a 400 dpi superan el tope por defecto

UMBRAL_PREDIAL = 10.0
UMBRAL_MANZANA = 25.0


def _terminos(x: np.ndarray, y: np.ndarray, orden: int) -> np.ndarray:
    if orden == 1:
        return np.column_stack([np.ones_like(x), x, y])
    if orden == 2:
        return np.column_stack([np.ones_like(x), x, y, x * y, x ** 2, y ** 2])
    raise ValueError("orden debe ser 1 o 2")


def min_puntos(orden: int) -> int:
    return {1: 3, 2: 6}[orden]


def ajustar(px, py, mx, my, orden: int):
    """Ajusta píxel -> coordenada de mapa. Devuelve coeficientes para X e Y."""
    A = _terminos(np.asarray(px, float), np.asarray(py, float), orden)
    cx, *_ = np.linalg.lstsq(A, np.asarray(mx, float), rcond=None)
    cy, *_ = np.linalg.lstsq(A, np.asarray(my, float), rcond=None)
    return cx, cy


def aplicar(px, py, cx, cy, orden: int):
    A = _terminos(np.asarray(px, float), np.asarray(py, float), orden)
    return A @ cx, A @ cy


def clasificar(rmse_loo: float) -> tuple[str, str]:
    if not np.isnan(rmse_loo) and rmse_loo < UMBRAL_PREDIAL:
        return "predial", "apto para consulta a nivel de predio"
    if not np.isnan(rmse_loo) and rmse_loo < UMBRAL_MANZANA:
        return "manzana", "referencial a nivel de manzana"
    return "contexto", "sólo contexto: no usar para decisiones sobre un predio"


def metricas(px, py, mx, my, orden: int) -> dict:
    """Ajuste + residuales + RMSE leave-one-out + aptitud de uso.

    El leave-one-out es el que vale: mide el error en un punto que el modelo NO
    usó para ajustarse. El RMSE del ajuste reparte el error entre todos los
    puntos y disimula un punto de control mal puesto.
    """
    px, py = np.asarray(px, float), np.asarray(py, float)
    mx, my = np.asarray(mx, float), np.asarray(my, float)
    n = len(px)
    if n < min_puntos(orden):
        raise SystemExit(
            f"orden {orden} necesita al menos {min_puntos(orden)} puntos, hay {n}")

    cx, cy = ajustar(px, py, mx, my, orden)
    ex, ey = aplicar(px, py, cx, cy, orden)
    res = np.hypot(ex - mx, ey - my)
    rmse = float(np.sqrt(np.mean(res ** 2)))

    loo = []
    if n > min_puntos(orden):
        for i in range(n):
            m = np.ones(n, bool)
            m[i] = False
            try:
                bx, by = ajustar(px[m], py[m], mx[m], my[m], orden)
            except np.linalg.LinAlgError:
                continue
            qx, qy = aplicar(px[i:i + 1], py[i:i + 1], bx, by, orden)
            loo.append(float(np.hypot(qx[0] - mx[i], qy[0] - my[i])))
    rmse_loo = float(np.sqrt(np.mean(np.square(loo)))) if loo else float("nan")
    aptitud, uso = clasificar(rmse_loo)

    return {
        "orden": orden, "n_puntos": n,
        "rmse_m": round(rmse, 2), "rmse_loo_m": round(rmse_loo, 2),
        "residual_max_m": round(float(res.max()), 2),
        "residuales_m": [round(float(r), 2) for r in res],
        "peor_punto": int(np.argmax(res)),
        "aptitud": aptitud, "uso_permitido": uso,
        "_cx": cx.tolist(), "_cy": cy.tolist(),
    }


# Techo de píxeles de salida. Una hoja de plóter grande a 300 dpi puede pedir una
# grilla de 200 millones de píxeles: son ~4,5 GB sólo para el arreglo RGB, y el
# proceso muere. Cuando se supera, se engruesa la resolución en vez de fallar —
# perder resolución es aceptable, perder la lámina entera no.
MAX_PIXELES_SALIDA = 60_000_000


def remuestrear(img: np.ndarray, met: dict, crs_destino: str, salida: Path,
                px, py, mx, my, resolucion: float | None = None) -> dict:
    """Lleva la imagen a una grilla regular en el CRS proyectado.

    Se invierte el polinomio ajustando la transformación contraria (mapa->píxel)
    con los mismos puntos de control, en vez de invertir analíticamente: así
    funciona igual para orden 1 y 2.
    """
    alto, ancho = img.shape[:2]
    orden = met["orden"]
    cx, cy = np.array(met["_cx"]), np.array(met["_cy"])

    ex = np.array([0, ancho, 0, ancho], float)
    ey = np.array([0, 0, alto, alto], float)
    gx, gy = aplicar(ex, ey, cx, cy, orden)
    minx, maxx, miny, maxy = gx.min(), gx.max(), gy.min(), gy.max()

    res = resolucion or max((maxx - minx) / ancho, (maxy - miny) / alto)
    n_col = int(np.ceil((maxx - minx) / res))
    n_fil = int(np.ceil((maxy - miny) / res))

    if n_col * n_fil > MAX_PIXELES_SALIDA:
        factor = float(np.sqrt(n_col * n_fil / MAX_PIXELES_SALIDA))
        res *= factor
        n_col = int(np.ceil((maxx - minx) / res))
        n_fil = int(np.ceil((maxy - miny) / res))

    transform = Affine(res, 0, minx, 0, -res, maxy)

    ix, iy = ajustar(mx, my, px, py, orden)
    col = np.arange(n_col) + 0.5
    fil = np.arange(n_fil) + 0.5
    MX = np.broadcast_to(minx + col[None, :] * res, (n_fil, n_col)).ravel()
    MY = np.broadcast_to(maxy - fil[:, None] * res, (n_fil, n_col)).ravel()
    PXf, PYf = aplicar(MX, MY, ix, iy, orden)

    cc = np.rint(PXf).astype(int)
    rr = np.rint(PYf).astype(int)
    dentro = (cc >= 0) & (cc < ancho) & (rr >= 0) & (rr < alto)

    plano = np.zeros((n_fil * n_col, 3), dtype="uint8")
    plano[dentro] = img[rr[dentro], cc[dentro]]
    bandas = plano.reshape(n_fil, n_col, 3).transpose(2, 0, 1)
    alfa = (dentro.reshape(n_fil, n_col) * 255).astype("uint8")

    salida.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        salida, "w", driver="GTiff", height=n_fil, width=n_col, count=4,
        dtype="uint8", crs=crs_destino, transform=transform,
        compress="deflate", tiled=True, photometric="RGB",
    ) as dst:
        dst.write(bandas, indexes=[1, 2, 3])
        dst.write(alfa, 4)
        dst.colorinterp = [
            rasterio.enums.ColorInterp.red, rasterio.enums.ColorInterp.green,
            rasterio.enums.ColorInterp.blue, rasterio.enums.ColorInterp.alpha,
        ]
    return {"ancho": n_col, "alto": n_fil, "resolucion_m": round(float(res), 3),
            "extension": [float(minx), float(miny), float(maxx), float(maxy)]}
