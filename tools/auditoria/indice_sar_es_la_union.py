#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""¿El total que publica el índice SAR es la unión de la huella, o su suma?

Las dos preguntas del instrumento
---------------------------------
1. ¿Qué mide? El área que `web/data/sar/indice.json` declara como observada,
   contra la que se obtiene disolviendo la huella publicada a su lado.
2. ¿Cómo sabría que se equivoca? Con `--control`, que reinyecta la suma por
   track en el índice en memoria y exige que el instrumento la rechace. Si el
   control pasa en verde, el instrumento no está comparando nada.

Por qué existe
--------------
Sentinel-1 cubre La Araucanía desde tres órbitas relativas que se solapan. El
agua que cae en el solape aparece en la huella de cada una, y sumar las tres
la cuenta dos y hasta tres veces. `scripts/14` ya calcula la unión desde el
6-sep-2026, pero el índice que está publicado se generó antes y sólo se
regenera bajando los rásters otra vez. La huella, en cambio, ya está en disco:
el total se puede recalcular sin descargar nada.

Con `--escribir` corrige el campo en el índice, **fusionando**: lee el archivo
de disco, cambia sólo `resumen.km2` y `resumen.hectareas`, y deja el resto
intacto. El disco es la fuente de verdad, no lo que este script recuerde.

Salida: 0 si el índice ya declara la unión, 2 si no.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import sar  # noqa: E402

TOLERANCIA_KM2 = 0.5          # medio km² sobre ~50: ruido de reproyección


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="web/data/sar")
    ap.add_argument("--escribir", action="store_true",
                    help="corrige el índice en disco (fusionando, no reescribiendo)")
    ap.add_argument("--control", action="store_true",
                    help="inyecta la suma por track y exige que se detecte")
    a = ap.parse_args()

    base = RAIZ / a.dir
    indice = json.loads((base / "indice.json").read_text(encoding="utf-8"))
    huella = json.loads((base / "huella-observada.geojson").read_text(encoding="utf-8"))

    union = sar.area_union_km2(huella["features"])
    suma_tracks = sum(d["km2"] for d in indice.get("tracks", []))
    declarado = float(indice["resumen"]["km2"])

    if a.control:
        # Control positivo: si el índice declarara la suma por track, esto
        # TIENE que salir en rojo. Sin este paso, un instrumento que siempre
        # dice «está bien» pasaría por bueno.
        declarado = suma_tracks

    print(f"huella publicada : {len(huella['features'])} polígonos")
    print(f"unión            : {union:8.2f} km²  ({union * 100:,.0f} ha)")
    print(f"suma por track   : {suma_tracks:8.2f} km²  ({suma_tracks * 100:,.0f} ha)")
    print(f"índice declara   : {declarado:8.2f} km²  ({declarado * 100:,.0f} ha)")

    calza = abs(declarado - union) <= TOLERANCIA_KM2
    if a.control:
        ok = not calza
        sys.stderr.write("CONTROL POSITIVO: %s\n" % (
            "OK — rechaza la suma por track" if ok
            else "FALLA — acepta la suma como si fuera la unión"))
        return 0 if ok else 2

    if calza:
        print("\n✅ el índice declara la unión")
        return 0

    exceso = declarado - union
    print(f"\n❌ el índice declara {exceso:+.2f} km² de más "
          f"({100 * exceso / max(declarado, 1e-9):.0f} % del total): "
          "es territorio contado dos y tres veces por el solape entre órbitas")
    if a.escribir:
        # Fusión, no reescritura: se lee de disco y se toca un campo.
        vivo = json.loads((base / "indice.json").read_text(encoding="utf-8"))
        vivo["resumen"]["km2"] = round(union, 2)
        vivo["resumen"]["hectareas"] = round(union * 100, 0)
        vivo["resumen"]["total_es"] = (
            "unión de la huella; la suma por track cuenta dos y tres veces "
            "el territorio donde se solapan las órbitas")
        (base / "indice.json").write_text(
            json.dumps(vivo, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"corregido en disco: {base / 'indice.json'}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
