"""Capa C (modelada) — mapas globales de amenaza de inundación fluvial del JRC.

Qué es: modelación hidrodinámica global (LISFLOOD + LISFLOOD-FP) de la mancha de
inundación para distintos períodos de retorno. Licencia CC BY 4.0.

Por qué se incluye: es la única fuente con cobertura continua sobre TODA la
Araucanía. Donde no hay estudio local ni huella observada, esto es lo que hay.

⚠️ LIMITACIÓN CENTRAL, que el frontend debe mostrar siempre:
   Esta versión global (`floodMapGL_*`) tiene resolución de 30 arcosegundos,
   ~1 km en latitudes medias. Un píxel cubre varias manzanas. NO sirve para
   decidir si una casa concreta se inunda, y no modela drenaje urbano — es
   decir, es ciega a los 278 puntos de "colapso de colectores" que SENAPRED
   registra en la región. Se publica como contexto regional, nunca como
   respuesta predial.

   La versión de 90 m (JRC/CEMS_GLOFAS/FloodHazard/v2_1) existe pero sólo se
   distribuye vía Google Earth Engine, que requiere cuenta. Ver README.

Fuente: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FLOODS/GlobalMaps/
Salida: data/processed/jrc/araucania_rp<N>.tif  (+ GeoJSON de contorno para el web)
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    DATA_PROC,
    DATA_RAW,
    WEB_DATA,
    cargar_config,
    cargar_config as _cfg,  # noqa: F401
    descargar,
    escribir_geojson,
    log,
    procedencia,
    sello,
)

BASE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/FLOODS/GlobalMaps"
PERIODOS = [10, 20, 50, 100, 200, 500]

# Año de publicación del dataset, tomado del `Last-Modified` de los propios
# archivos del servidor del JRC (22-nov-2016), no de una estimación. Importa
# mostrarlo: un modelo de 2016 no incorpora las obras fluviales ni los cambios de
# uso de suelo de la última década.
ANIO_PUBLICACION = 2016

# Umbral de profundidad para considerar "inundado". El producto entrega
# profundidad en metros; por debajo de 25 cm el valor está dentro del ruido del
# modelo a esta resolución y genera manchas espurias.
UMBRAL_M = 0.25


def recortar(tif_global: Path, bbox: list[float], destino: Path) -> Path | None:
    """Lee sólo la ventana de la región. No carga el ráster global en memoria."""
    with rasterio.open(tif_global) as src:
        try:
            win = from_bounds(*bbox, transform=src.transform)
        except Exception as exc:  # noqa: BLE001
            log(f"  bbox fuera del ráster: {exc}")
            return None
        datos = src.read(1, window=win)
        perfil = src.profile.copy()
        perfil.update(
            height=datos.shape[0],
            width=datos.shape[1],
            transform=src.window_transform(win),
            compress="deflate",
            tiled=True,
        )
    if datos.size == 0:
        log("  ventana vacía")
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(destino, "w", **perfil) as dst:
        dst.write(datos, 1)
    log(f"  recorte: {destino.name} — {datos.shape[1]}x{datos.shape[0]} px")
    return destino


def contorno_geojson(tif: Path, meta: dict, destino: Path, props_feature: dict) -> None:
    """Vectoriza la mancha inundada a polígonos para servirla en el mapa web."""
    with rasterio.open(tif) as src:
        arr = src.read(1)
        nodata = src.nodata
        mask = np.isfinite(arr) & (arr > UMBRAL_M)
        if nodata is not None:
            mask &= arr != nodata
        if not mask.any():
            log(f"  {tif.name}: sin píxeles sobre {UMBRAL_M} m")
            escribir_geojson([], destino, meta)
            return

        feats = []
        for geom, val in shapes(mask.astype("uint8"), mask=mask, transform=src.transform):
            if val != 1:
                continue
            feats.append({"type": "Feature", "geometry": geom,
                          "properties": dict(props_feature)})
    escribir_geojson(feats, destino, meta)


def main() -> None:
    cfg = cargar_config()
    bbox = cfg["region"]["bbox"]
    destino_raw = DATA_RAW / "jrc"
    destino_raw.mkdir(parents=True, exist_ok=True)

    periodos = [int(a) for a in sys.argv[1:]] or PERIODOS

    for rp in periodos:
        log(f"período de retorno {rp} años")
        zip_local = destino_raw / f"floodMapGL_rp{rp}y.zip"
        try:
            descargar(f"{BASE}/floodMapGL_rp{rp}y.zip", zip_local)
        except Exception as exc:  # noqa: BLE001
            log(f"  no se pudo descargar: {exc}")
            continue

        with zipfile.ZipFile(zip_local) as z:
            tifs = [n for n in z.namelist() if n.lower().endswith(".tif")]
            if not tifs:
                log(f"  el zip no trae .tif: {z.namelist()[:5]}")
                continue
            extraido = destino_raw / tifs[0]
            if not extraido.exists():
                z.extract(tifs[0], destino_raw)

        rec = recortar(extraido, bbox, DATA_PROC / "jrc" / f"araucania_rp{rp}.tif")
        if not rec:
            continue

        meta = procedencia(
            fuente=f"JRC Global River Flood Hazard Map — período de retorno {rp} años",
            url=f"{BASE}/floodMapGL_rp{rp}y.zip",
            metodo=f"Recorte al bbox de La Araucanía y vectorización de píxeles con "
                   f"profundidad > {UMBRAL_M} m",
            capa_evidencia="C_modelado",
            incertidumbre="Resolución ~1 km (30 arcsec): un píxel cubre varias manzanas. "
                          "No modela drenaje urbano ni cuencas pequeñas. Referencial "
                          "a escala regional; NO apto para decisión predial.",
            escala_original="30 arcosegundos (~1 km)",
            fecha_dato=f"JRC GlobalMaps v1, publicado {ANIO_PUBLICACION}",
        )
        contorno_geojson(rec, meta, WEB_DATA / "jrc" / f"rp{rp}.geojson",
                         {**sello(f"JRC (Comisión Europea) — Global River Flood "
                                  f"Hazard Map, retorno {rp} años", ANIO_PUBLICACION),
                          "periodo_retorno_anios": rp})

    log("listo")


if __name__ == "__main__":
    main()
