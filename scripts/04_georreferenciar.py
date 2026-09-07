"""Capa A (normativa) — georreferenciar una lámina con puntos de control a mano.

El problema: los mapas de inundación con valor legal en Chile están dibujados
dentro de PDFs. Para poder consultarlos hay que darles coordenadas.

De dónde sacar los puntos de control, en orden de preferencia:

  1. **La grilla UTM impresa en la lámina.** Los planos de anteproyecto de los PRC
     traen la retícula rotulada en los márgenes. Para esos, usar
     `08_georreferenciar_grilla.py`, que la lee sola y no necesita intervención.
  2. **Rasgos identificables** contra una base (cruces de calles, esquinas de
     manzana, puentes). Es lo único posible cuando la lámina es una figura
     rasterizada dentro de un informe, sin grilla — como el catastro de
     anegamientos de Temuco. Para ese caso es este script.

Lo que aporta, en ambos casos, es el rigor alrededor del ajuste: RMSE
leave-one-out y clasificación de aptitud de uso. Ver `georref.py`.

     RMSE LOO < 10 m   → apto para consulta a nivel de predio
     10 a 25 m         → referencial a nivel de manzana
     > 25 m            → sólo contexto; el frontend debe difuminarlo

Sin esa clasificación el producto no sale. Un polígono de área de riesgo mal
ubicado puede afectar el valor de un terreno o un permiso de edificación.

Uso:
    python 04_georreferenciar.py --plantilla salida.json
    python 04_georreferenciar.py lamina.png puntos.json --crs EPSG:32718 --orden 1

`puntos.json` también acepta el formato `.points` que exporta el Georreferenciador
de QGIS, que es como se van a producir los GCP en la práctica.

Requiere: nada por código — la lámina PNG y los puntos de control se pasan
        como argumentos. En la práctica, la lámina viene de
        03_descargar_documentos.py o 07_buscar_laminas_riesgo.py, y los puntos
        de control se arman a mano (o se exportan desde QGIS): es el camino
        para cuando 08_georreferenciar_grilla.py rechaza una lámina.
Salida: data/processed/georreferenciado/<lamina>.tif + su .json de procedencia
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import DATA_PROC, log, procedencia  # noqa: E402
from georref import (  # noqa: E402,F401  (se reexportan para los tests)
    UMBRAL_MANZANA,
    UMBRAL_PREDIAL,
    ajustar,
    aplicar,
    clasificar,
    metricas,
    min_puntos,
    remuestrear,
)

Image.MAX_IMAGE_PIXELS = None


def leer_puntos(ruta: Path):
    """Lee GCP desde JSON propio o desde un .points del Georreferenciador de QGIS.

    QGIS escribe `sourceY` como fila negativa (crece hacia abajo desde el borde
    superior, pero con signo invertido). Este código trabaja con origen
    arriba-izquierda e Y positivo hacia abajo, así que basta tomar el valor
    absoluto. Si no se corrige, la lámina sale espejada verticalmente y —lo
    peligroso— el RMSE puede salir igual de bajo: el error es silencioso.
    """
    txt = ruta.read_text(encoding="utf-8-sig")
    if ruta.suffix.lower() == ".points" or txt.lstrip().startswith("#CRS"):
        filas = list(csv.DictReader(
            [l for l in txt.splitlines() if not l.startswith("#")]))
        px = np.array([float(f["sourceX"]) for f in filas])
        py = np.array([float(f["sourceY"]) for f in filas])
        mx = np.array([float(f["mapX"]) for f in filas])
        my = np.array([float(f["mapY"]) for f in filas])
        return px, np.abs(py), mx, my, True
    d = json.loads(txt)
    p = d["puntos"]
    return (np.array([q["pixel_x"] for q in p], float),
            np.array([q["pixel_y"] for q in p], float),
            np.array([q["lon"] for q in p], float),
            np.array([q["lat"] for q in p], float),
            False)


PLANTILLA = {
    "lamina": "data/raw/laminas/temuco/estudio_aguas_lluvias_p013.png",
    "documento": "Estudio de Aguas Lluvias, diagnóstico PRC Temuco (2022). "
                 "Figura N°1: Catastro de Anegamientos Estacionales, año 2015.",
    "url_fuente": "https://www.temuco.cl/wp-content/uploads/2022/04/Cap9-2-Estudio-Aguas-Lluvias.pdf",
    "escala_original": "sin escala gráfica declarada — verificar",
    "crs_puntos": "EPSG:4326",
    "_ayuda": [
        "pixel_x / pixel_y: posición en la PNG, origen arriba-izquierda.",
        "lon / lat: coordenada real del mismo rasgo, en grados decimales.",
        "Elegir rasgos que no se muevan: cruces de calles, esquinas de manzana,",
        "puentes. NO usar árboles, vehículos ni bordes de la hoja.",
        "Mínimo 8 puntos bien repartidos, incluyendo los bordes del mapa.",
        "Nunca alinearlos todos sobre un mismo eje: el ajuste queda indeterminado.",
    ],
    "puntos": [
        {"nombre": "ejemplo — reemplazar", "pixel_x": 0, "pixel_y": 0,
         "lon": -72.5900, "lat": -38.7350},
    ],
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lamina", nargs="?", help="PNG de la lámina")
    ap.add_argument("puntos", nargs="?", help="GCP en .json o .points de QGIS")
    ap.add_argument("--crs", default="EPSG:32718",
                    help="CRS proyectado de salida (Araucanía: 32718 o 32719)")
    ap.add_argument("--orden", type=int, default=1, choices=[1, 2])
    ap.add_argument("--plantilla", metavar="RUTA",
                    help="escribe un archivo de puntos de ejemplo y termina")
    a = ap.parse_args()

    if a.plantilla:
        Path(a.plantilla).write_text(
            json.dumps(PLANTILLA, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"plantilla escrita en {a.plantilla}")
        return

    if not a.lamina or not a.puntos:
        ap.error("hacen falta la lámina y el archivo de puntos "
                 "(o usa --plantilla para empezar)")

    lamina, ruta_pts = Path(a.lamina), Path(a.puntos)
    px, py, gx, gy, ya_proyectado = leer_puntos(ruta_pts)
    log(f"{lamina.name}: {len(px)} puntos de control, polinomio orden {a.orden}")

    # Los GCP en JSON vienen en lon/lat; hay que llevarlos al CRS proyectado
    # antes de ajustar, porque el RMSE tiene que estar en metros.
    if ya_proyectado:
        mx, my = gx, gy
    else:
        tr = Transformer.from_crs("EPSG:4326", a.crs, always_xy=True)
        mx, my = tr.transform(gx, gy)
        mx, my = np.asarray(mx), np.asarray(my)

    met = metricas(px, py, mx, my, a.orden)
    log(f"  RMSE ajuste        : {met['rmse_m']} m")
    log(f"  RMSE leave-one-out : {met['rmse_loo_m']} m   <- el que vale")
    log(f"  peor residual      : {met['residual_max_m']} m (punto #{met['peor_punto']})")
    log(f"  aptitud            : {met['aptitud'].upper()} — {met['uso_permitido']}")
    if met["aptitud"] == "contexto":
        log("  ⚠️ error demasiado alto. Revisa el peor punto antes de publicar esto.")

    destino = DATA_PROC / "georreferenciado" / f"{lamina.stem}.tif"
    img = np.array(Image.open(lamina).convert("RGB"))
    info = remuestrear(img, met, a.crs, destino, px, py, mx, my)
    log(f"  GeoTIFF: {destino.name} — {info['ancho']}x{info['alto']} px, "
        f"{info['resolucion_m']} m/px")

    meta = procedencia(
        fuente=f"Lámina georreferenciada desde {lamina.name}",
        url=str(ruta_pts),
        metodo=f"Polinomio orden {a.orden} ajustado sobre {met['n_puntos']} puntos "
               f"de control, remuestreo vecino más cercano",
        capa_evidencia="A_normativo",
        incertidumbre=f"RMSE leave-one-out {met['rmse_loo_m']} m — {met['uso_permitido']}",
    )
    reporte = {"procedencia": meta,
               "ajuste": {k: v for k, v in met.items() if not k.startswith("_")},
               "raster": info, "crs": a.crs}
    destino.with_suffix(".json").write_text(
        json.dumps(reporte, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"  reporte: {destino.with_suffix('.json').name}")


if __name__ == "__main__":
    main()
