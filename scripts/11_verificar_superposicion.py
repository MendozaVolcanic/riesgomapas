"""Control de calidad: componer un plano georreferenciado sobre el mapa base.

Para qué sirve: el RMSE de la grilla mide la coherencia interna del ajuste, no
que el plano esté sobre el lugar correcto del mundo. La prueba definitiva es
mirar si las calles dibujadas en el plano caen sobre las calles del mapa base.

Este script hace exactamente lo que hace el visor —tomar el PNG y colocarlo por
sus cuatro esquinas en Web Mercator— pero fuera del navegador, de modo que el
resultado se pueda revisar y archivar sin depender de que haya una pantalla.

Uso:
    python 11_verificar_superposicion.py                    # el primer plano
    python 11_verificar_superposicion.py Vilcún_p007        # por nombre
    python 11_verificar_superposicion.py --todos

Requiere: 10_exportar_superposiciones.py (web/data/planos/indice.json)
Salida: data/processed/verificacion/verif_<plano>.jpg
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import DATA_PROC, WEB_DATA, _CTX, UA, log  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
TAM_TESELA = 256
ZOOM_MAX = 17


def lonlat_a_tile(lon: float, lat: float, z: int) -> tuple[float, float]:
    n = 2.0 ** z
    x = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n
    return x, y


def elegir_zoom(bounds: list[float], ancho_objetivo: int = 1800) -> int:
    """Zoom cuyo mosaico se acerque al ancho pedido, sin pasarse de ZOOM_MAX."""
    w, s, e, n = bounds
    for z in range(ZOOM_MAX, 5, -1):
        x0, _ = lonlat_a_tile(w, n, z)
        x1, _ = lonlat_a_tile(e, s, z)
        if (x1 - x0) * TAM_TESELA <= ancho_objetivo * 1.6:
            return z
    return 12


def mosaico_osm(bounds: list[float], z: int) -> tuple[Image.Image, tuple[float, float, float, float]]:
    """Descarga las teselas que cubren el bbox y devuelve el mosaico y su bbox real."""
    w, s, e, n = bounds
    x0f, y0f = lonlat_a_tile(w, n, z)
    x1f, y1f = lonlat_a_tile(e, s, z)
    x0, y0, x1, y1 = int(x0f), int(y0f), int(x1f), int(y1f)
    cols, filas = x1 - x0 + 1, y1 - y0 + 1
    if cols * filas > 160:
        raise SystemExit(f"el mosaico pediría {cols * filas} teselas: baja el zoom")

    img = Image.new("RGB", (cols * TAM_TESELA, filas * TAM_TESELA), (235, 235, 235))
    fallidas = 0
    for i, x in enumerate(range(x0, x1 + 1)):
        for j, y in enumerate(range(y0, y1 + 1)):
            url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, context=_CTX, timeout=45) as r:
                    t = Image.open(r).convert("RGB")
                img.paste(t, (i * TAM_TESELA, j * TAM_TESELA))
            except Exception:  # noqa: BLE001
                fallidas += 1
            # Política de uso de OSM: sin ráfagas. Es una verificación puntual,
            # no un scraper.
            time.sleep(0.12)
    if fallidas:
        log(f"    {fallidas} teselas no se pudieron descargar")
    # bbox geográfico exacto del mosaico completo
    def tile_a_lonlat(xt, yt):
        nn = 2.0 ** z
        lon = xt / nn * 360.0 - 180.0
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yt / nn))))
        return lon, lat
    lon_izq, lat_arr = tile_a_lonlat(x0, y0)
    lon_der, lat_aba = tile_a_lonlat(x1 + 1, y1 + 1)
    return img, (lon_izq, lat_aba, lon_der, lat_arr)


def componer(plano: dict, destino_dir: Path) -> Path | None:
    png = WEB_DATA / "planos" / plano["archivo"]
    if not png.exists():
        log(f"  falta {png.name}")
        return None
    bounds = plano["bounds_wgs84"]
    z = elegir_zoom(bounds)
    log(f"  {plano['titulo'][:56]} — zoom {z}")
    base, bb = mosaico_osm(bounds, z)

    # Posición del plano dentro del mosaico, en píxeles. Se hace en el espacio
    # de teselas (que es Web Mercator), igual que MapLibre.
    x0f, y0f = lonlat_a_tile(bb[0], bb[3], z)
    xw, yn = lonlat_a_tile(bounds[0], bounds[3], z)
    xe, ys = lonlat_a_tile(bounds[2], bounds[1], z)
    izq = round((xw - x0f) * TAM_TESELA)
    arr = round((yn - y0f) * TAM_TESELA)
    ancho = max(1, round((xe - xw) * TAM_TESELA))
    alto = max(1, round((ys - yn) * TAM_TESELA))

    capa = Image.open(png).convert("RGBA").resize((ancho, alto), Image.LANCZOS)
    # Misma opacidad que usa el visor, para que lo que se revisa sea lo que se ve.
    alfa = capa.split()[3].point(lambda v: int(v * 0.85))
    capa.putalpha(alfa)

    salida = base.convert("RGBA")
    salida.alpha_composite(capa, (izq, arr))

    destino_dir.mkdir(parents=True, exist_ok=True)
    ruta = destino_dir / f"verif_{Path(plano['archivo']).stem}.jpg"
    salida.convert("RGB").save(ruta, quality=82)
    log(f"    → {ruta.name} ({salida.size[0]}x{salida.size[1]} px)")
    return ruta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("filtro", nargs="?", help="parte del nombre del plano")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--salida", default=None)
    a = ap.parse_args()

    idx = WEB_DATA / "planos" / "indice.json"
    if not idx.exists():
        raise SystemExit("falta web/data/planos/indice.json — corre el script 10")
    planos = json.loads(idx.read_text(encoding="utf-8"))["planos"]

    if a.filtro:
        planos = [p for p in planos if a.filtro.lower() in p["archivo"].lower()]
    if not a.todos:
        planos = planos[:1]
    if not planos:
        raise SystemExit("ningún plano coincide con el filtro")

    destino = Path(a.salida) if a.salida else DATA_PROC / "verificacion"
    log(f"{len(planos)} plano(s) a verificar contra el mapa base de OpenStreetMap")
    for p in planos:
        componer(p, destino)
    log("")
    log("Revisar a ojo: las calles del plano deben caer sobre las calles del mapa")
    log("base. Si están corridas, el problema es la georreferenciación, no el visor.")


if __name__ == "__main__":
    main()
