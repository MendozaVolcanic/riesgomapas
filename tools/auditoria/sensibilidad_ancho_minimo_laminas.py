"""Cuánto cambia la mancha vectorizada si se mueve `ancho_minimo_px` o `tolerancia_color`.

Repite la clasificación de scripts/18_vectorizar_laminas.py (procesar(): color
euclídeo en RGB → apertura morfológica con elipse de `ancho` px → polígonos →
filtro `area_minima_m2`) sobre la MISMA imagen del PDF, variando un parámetro a
la vez, y reporta hectáreas y número de polígonos por clase. No escribe nada en
data/: sólo mide.

La magnitud física del umbral: `ancho_minimo_px: 4` son 4 × 7,74 = 31 m en
Angol y 4 × 5,34 = 21 m en Catripulli. Una franja inundable más angosta que eso
desaparece del mapa aunque la lámina la pinte.

Las dos preguntas del instrumento:
 (1) Si el parámetro no mandara nada, las hectáreas serían idénticas en toda la
     fila y se vería. Si mandara demasiado, se vería el salto.
 (2) Si el instrumento estuviera muerto (imagen equivocada, máscara vacía), la
     fila con los valores declarados en config/laminas.yaml NO reproduciría las
     hectáreas que ya publica data/processed/laminas/<id>.geojson; se imprime
     esa comparación como control.

Uso:
    python tools/auditoria/sensibilidad_ancho_minimo_laminas.py [--id ID]
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

spec = importlib.util.spec_from_file_location("s18", RAIZ / "scripts" / "18_vectorizar_laminas.py")
s18 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s18)


def clasificar(a, cfg, transform, tol, ancho, area_min):
    import cv2
    dists = [np.linalg.norm(a - np.array(c["rgb"]), axis=2) for c in cfg["clases"]]
    apilado = np.stack(dists)
    ganador, dmin = apilado.argmin(0), apilado.min(0)
    out = []
    for i, clase in enumerate(cfg["clases"]):
        cruda = (ganador == i) & (dmin < tol)
        if ancho >= 1:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ancho, ancho))
            limpia = cv2.morphologyEx(cruda.astype("uint8"), cv2.MORPH_OPEN, k).astype(bool)
        else:
            limpia = cruda
        gs = s18.poligonos(limpia, transform, area_min)
        out.append((clase["nombre"], len(gs), sum(g.area for g in gs) / 10_000))
    return out


def main() -> None:
    from affine import Affine
    decl = yaml.safe_load((RAIZ / "config" / "laminas.yaml").read_text(encoding="utf-8"))["laminas"]
    quiero = sys.argv[sys.argv.index("--id") + 1] if "--id" in sys.argv else None
    for cfg in decl:
        if cfg.get("vertices") or (quiero and cfg["id"] != quiero):
            continue
        pdf = RAIZ / "data" / "raw" / cfg["pdf"]
        ims = s18.imagenes_de(pdf, cfg["pagina"])
        a = np.array(ims[cfg.get("imagen", 0)]).astype(int)
        s, x_ref, e_ref, y_ref, n_ref, _ = s18.afin(cfg)
        transform = Affine(s, 0, e_ref - x_ref * s, 0, -s, n_ref + y_ref * s)
        tol0 = cfg.get("tolerancia_color", 45)
        ancho0 = int(cfg.get("ancho_minimo_px", 4))
        amin0 = float(cfg.get("area_minima_m2", 0))
        pub = json.loads((RAIZ / "data" / "processed" / "laminas" / f"{cfg['id']}.geojson")
                         .read_text(encoding="utf-8"))
        resumen_pub = (pub.get("procedencia") or pub).get("resumen_por_clase")
        print(f"\n[{cfg['id']}] {a.shape[1]}×{a.shape[0]} px · {s:.3f} m/px · "
              f"declarado tol={tol0} ancho={ancho0}px ({ancho0 * s:.1f} m) area_min={amin0:.0f} m²")
        print(f"  publicado: {[(c['clase'], c['poligonos'], c['hectareas']) for c in resumen_pub]}")
        base = clasificar(a, cfg, transform, tol0, ancho0, amin0)
        print(f"  reproducido con los valores declarados (control): "
              f"{[(n, k, round(h, 1)) for n, k, h in base]}")

        print("  --- ancho_minimo_px (tol y área fijas) ---")
        for ancho in (0, 2, 3, 4, 5, 6, 8):
            r = clasificar(a, cfg, transform, tol0, ancho, amin0)
            print(f"   ancho={ancho} px ({ancho * s:5.1f} m): " + " · ".join(
                f"{n} {k:>4} pol {h:8.1f} ha" for n, k, h in r))
        print("  --- tolerancia_color (ancho y área fijos) ---")
        for tol in (25, 35, tol0, 55, 70, 90):
            r = clasificar(a, cfg, transform, tol, ancho0, amin0)
            print(f"   tol={tol:>3}: " + " · ".join(
                f"{n} {k:>4} pol {h:8.1f} ha" for n, k, h in r))
        print("  --- area_minima_m2 (tol y ancho fijos) ---")
        for amin in (0, 500, 1000, 2000, 4000, 10000):
            r = clasificar(a, cfg, transform, tol0, ancho0, amin)
            print(f"   area_min={amin:>5} m²: " + " · ".join(
                f"{n} {k:>4} pol {h:8.1f} ha" for n, k, h in r))


if __name__ == "__main__":
    main()
