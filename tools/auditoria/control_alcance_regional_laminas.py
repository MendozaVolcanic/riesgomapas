"""¿La verificación de «alcance regional» del script 18 cacha un rótulo mal tecleado?

config/laminas.yaml (líneas 14-17) promete que una coordenada mal tecleada
«mueve la mancha cientos de metros y esas dos comprobaciones la cachan». La
segunda comprobación es scripts/18_vectorizar_laminas.py:399-405 (y 523-525):
exige que TODO el resultado caiga dentro del bbox de la región
(config/araucania.yaml:9), sin margen. Este instrumento aplica exactamente esa
condición a la geometría ya publicada, desplazada a propósito, y reporta a
partir de qué corrimiento la comprobación empieza a fallar.

Para Angol y Catripulli el eje Y tiene UNA sola ancla (laminas.yaml:56 y 101),
así que la única defensa contra un norte mal tecleado es esta comprobación.

Las dos preguntas del instrumento:
 (1) Si la comprobación fuese perfecta (rechazara cualquier corrimiento de
     cientos de metros), la tabla mostraría RECHAZA desde 0,5 km. Si no sirve,
     mostrará PASA hasta decenas de kilómetros.
 (2) Si el instrumento estuviera muerto, el control interno falla: un
     corrimiento de 400 km TIENE que ser rechazado; si no lo es, se aborta.

Uso:
    python tools/auditoria/control_alcance_regional_laminas.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
LAMINAS = RAIZ / "data" / "processed" / "laminas"


def coords(geom):
    def rec(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for x in c:
                yield from rec(x)
    return list(rec(geom["coordinates"]))


def pasa_bbox(xs, ys, bbox) -> bool:
    o, su, e, n = bbox
    return o <= min(xs) and max(xs) <= e and su <= min(ys) and max(ys) <= n   # 18:400


def main() -> None:
    bbox = yaml.safe_load((RAIZ / "config" / "araucania.yaml").read_text(encoding="utf-8"))["region"]["bbox"]
    print(f"bbox regional: {bbox}  (ancho {(bbox[2]-bbox[0])*111.32*math.cos(math.radians(-38.5)):.0f} km "
          f"× alto {(bbox[3]-bbox[1])*111.32:.0f} km)")
    for f in sorted(LAMINAS.glob("*.geojson")):
        d = json.loads(f.read_text(encoding="utf-8"))
        xs = [c[0] for ft in d["features"] for c in coords(ft["geometry"])]
        ys = [c[1] for ft in d["features"] for c in coords(ft["geometry"])]
        lat = (min(ys) + max(ys)) / 2
        print(f"\n[{f.stem}] lon {min(xs):.3f}..{max(xs):.3f} · lat {min(ys):.3f}..{max(ys):.3f}")
        assert pasa_bbox(xs, ys, bbox), "la geometría publicada debería pasar sin desplazar"
        control = pasa_bbox(xs, [y - 400 / 111.32 for y in ys], bbox)
        assert not control, "CONTROL FALLIDO: un corrimiento de 400 km al sur debería rechazarse"
        filas = []
        for km in (0.5, 1, 2, 5, 10, 20, 50, 100):
            dl = km / 111.32
            dlo = km / (111.32 * math.cos(math.radians(lat)))
            res = {
                "N": pasa_bbox(xs, [y + dl for y in ys], bbox),
                "S": pasa_bbox(xs, [y - dl for y in ys], bbox),
                "E": pasa_bbox([x + dlo for x in xs], ys, bbox),
                "O": pasa_bbox([x - dlo for x in xs], ys, bbox),
            }
            filas.append(f"  {km:>5} km: " + "  ".join(
                f"{k}={'PASA' if v else 'RECHAZA'}" for k, v in res.items()))
        print("\n".join(filas))
        # Corrimiento que provoca un error de UN dígito en el rótulo Y declarado
        # (p. ej. 5815000 → 5810000, o 5640000 → 5630000): 5 y 10 km.
        print("  → un norte mal tecleado en 5.000 m (un dígito) queda:",
              "PASA" if pasa_bbox(xs, [y - 5 / 111.32 for y in ys], bbox) else "RECHAZA")


if __name__ == "__main__":
    main()
