"""¿Las láminas vectorizadas aterrizaron donde dice el resto de la evidencia?

Complemento de control_alcance_regional_laminas.py: aquél muestra que la
comprobación del script 18 no ve un corrimiento de kilómetros; éste mide, con
datos que NO participaron en la vectorización, si la mancha publicada está donde
tiene que estar. Dos contrastes:
  · fracción del área de cada lámina que cae dentro de la amenaza modelada del
    GORE 2016 (web/data/gore/amenaza-inundacion.geojson);
  · distancia de los puntos críticos SENAPRED de la misma comuna a la mancha.

Y el mismo cálculo con la lámina corrida 1, 2 y 5 km, para ver cuánto baja: si
la posición real fuera equivocada, un corrimiento la MEJORARÍA en vez de
empeorarla.

Las dos preguntas del instrumento:
 (1) Si la lámina estuviera corrida, la coincidencia con el GORE sería baja y
     algún corrimiento la subiría; se vería en la tabla.
 (2) Si el instrumento estuviera muerto (intersección siempre 0 o siempre 1),
     la fila de 5 km no diferiría de la de 0 km. Se exige que 5 km cambie la
     fracción en más de 10 puntos, si no aborta.

Uso:
    python tools/auditoria/coherencia_laminas_vs_gore_senapred.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape, Point
from shapely.ops import transform as sh_transform, unary_union

RAIZ = Path(__file__).resolve().parents[2]
WEB = RAIZ / "web" / "data"
EPSG = {"ANGOL": 32718, "CURARREHUE": 32719}


def a_utm(geom, epsg):
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    return sh_transform(tr.transform, geom)


def main() -> None:
    vect = json.loads((WEB / "laminas" / "vectorizadas.geojson").read_text(encoding="utf-8"))
    gore = json.loads((WEB / "gore" / "amenaza-inundacion.geojson").read_text(encoding="utf-8"))
    puntos = json.loads((WEB / "puntos-criticos-inundacion.geojson").read_text(encoding="utf-8"))

    por_lamina: dict[str, list] = {}
    for f in vect["features"]:
        por_lamina.setdefault(f["properties"]["origen_lamina"], []).append(f)

    for lam, feats in por_lamina.items():
        comuna = feats[0]["properties"]["comuna"]
        epsg = EPSG[comuna]
        mancha = unary_union([a_utm(shape(f["geometry"]), epsg) for f in feats])
        bb = mancha.buffer(6000).bounds
        gore_u = unary_union([
            a_utm(shape(f["geometry"]), epsg) for f in gore["features"]
            if f.get("geometry")]).buffer(0)
        gore_u = gore_u.intersection(
            shape({"type": "Polygon", "coordinates": [[
                [bb[0], bb[1]], [bb[2], bb[1]], [bb[2], bb[3]], [bb[0], bb[3]], [bb[0], bb[1]]]]}))
        pts = [a_utm(Point(f["geometry"]["coordinates"]), epsg) for f in puntos["features"]
               if f["properties"].get("comuna", "").upper() == comuna]
        print(f"\n[{lam}] {comuna} · {mancha.area / 1e4:.0f} ha · {len(pts)} puntos SENAPRED de la comuna")
        filas = []
        base = None
        for km in (0, 1, 2, 5):
            for dx, dy in (((0, 0),) if km == 0 else ((km, 0), (-km, 0), (0, km), (0, -km))):
                from shapely.affinity import translate
                m = translate(mancha, dx * 1000, dy * 1000)
                frac = m.intersection(gore_u).area / m.area if not gore_u.is_empty else float("nan")
                d = sorted(p.distance(m) for p in pts)
                cerca300 = sum(1 for x in d if x <= 300)
                fila = (f"  corrida {km} km ({dx:+},{dy:+}): dentro del GORE {100 * frac:5.1f} % · "
                        f"puntos SENAPRED a ≤300 m: {cerca300}/{len(pts)} · mediana dist {d[len(d)//2] if d else float('nan'):.0f} m")
                filas.append(fila)
                if km == 0:
                    base = frac
                if km == 5 and base == base:
                    assert abs(frac - base) > 0.10 or gore_u.is_empty, \
                        "CONTROL FALLIDO: correr 5 km no cambia la coincidencia; el instrumento no mide"
        print("\n".join(filas))


if __name__ == "__main__":
    main()
