"""¿A dónde escribe `scripts/14_sar_huella_observada.py` cuando corre con
`--bbox`? (auditoría 2026-09-06, familia F-12, sitio 4 de 4)

`--bbox` existe para "probar rápido" sobre un recorte del área de trabajo. Antes
del arreglo, el bloque final del script escribía SIEMPRE en `web/data/sar/`
—la ruta que consume el visor—, así que correr una prueba sobre un recorte
sobrescribía la capa B publicada con la huella de esa fracción, sin ningún
error que lo delatara.

No se puede reproducir el script completo acá: `main()` necesita red (catálogo
STAC de Microsoft Planetary Computer, DEM Copernicus GLO-30) y decenas de
minutos por track, que es exactamente lo que `--bbox` existe para evitar. En
vez de eso, este instrumento EXTRAE el bloque real que decide `salida` —el
texto tal cual vive en el archivo, no una copia a mano que podría desincronizarse—
y lo ejecuta con `args.bbox` puesto y sin poner, contra un `WEB_DATA` de prueba.
Si mañana alguien vuelve a escribir `salida = WEB_DATA / "sar"` a secas, este
instrumento dejaría de encontrar el bloque y fallaría con AssertionError, no en
silencio.

Uso: python tools/auditoria/script14_bbox_no_pisa_publicado.py
"""
from __future__ import annotations

import argparse
import re
import textwrap
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FUENTE = RAIZ / "scripts" / "14_sar_huella_observada.py"


def extraer_bloque() -> str:
    texto = FUENTE.read_text(encoding="utf-8")
    m = re.search(
        r"    if args\.bbox:\n(?:.*\n)*?"
        r"    escribir_geojson\(cobertura_feats, salida / \"cobertura-sar\.geojson\", meta\)\n",
        texto,
    )
    assert m, ("no se encontró el bloque que decide `salida` en "
               f"{FUENTE.name} — el archivo cambió y este instrumento hay que "
               "actualizarlo, no ignorarlo.")
    return textwrap.dedent(m.group(0))


def correr(bbox) -> tuple[str, list[str]]:
    escritos: list[str] = []
    logs: list[str] = []

    def escribir_geojson(feats, destino, meta):
        escritos.append(str(destino))

    ns = {
        "args": argparse.Namespace(bbox=bbox),
        "WEB_DATA": Path("WEB_DATA"),
        "log": logs.append,
        "escribir_geojson": escribir_geojson,
        "huella_feats": [],
        "cobertura_feats": [],
        "meta": {},
    }
    exec(extraer_bloque(), ns)  # noqa: S102 — bloque leído del propio repo, no de red
    return str(ns["salida"]), logs


def main() -> None:
    sin_bbox, _ = correr(None)
    con_bbox, logs = correr([-72.7, -38.8, -72.5, -38.6])

    print("sin --bbox  → salida =", sin_bbox)
    print("con --bbox  → salida =", con_bbox)
    for l in logs:
        print("  " + l)

    assert sin_bbox == "WEB_DATA\\sar" or sin_bbox == "WEB_DATA/sar", sin_bbox
    assert "sar_prueba_bbox" in con_bbox, con_bbox
    assert con_bbox != sin_bbox, "con --bbox tiene que escribir a otra ruta"
    print("\nOK: --bbox nunca resuelve a la misma ruta que la corrida normal.")


if __name__ == "__main__":
    main()
