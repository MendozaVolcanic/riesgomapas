"""¿Qué tan cerca de cambiar de nivel queda un punto consultado en el visor?

Mide la sensibilidad de la regla de decisión de web/app.js (RADIOS = 300 / 500 /
1500 m, en metros por haversine) frente a un error de posición pequeño: el que
mete un geocodificador (decenas de metros) o un dedo en el celular.

Reimplementa la regla de `evaluar()` (app.js:333-378) SÓLO en su parte por
distancia a puntos críticos (capas A/B se ignoran: acá interesa el radio). Toma
una malla de puntos de prueba de 25 m alrededor de cada punto crítico (hasta
1.700 m) y para cada uno calcula el nivel; después mueve el punto 10, 25 y 50 m
en cuatro direcciones y cuenta cuántos cambian de nivel.

Las dos preguntas del instrumento:
 (1) Si la regla fuese completamente insensible a la posición (p. ej. todos los
     puntos a nivel fijo), la fracción que cambia sería 0 y se vería. Si fuese
     hipersensible (todo cambia con 10 m), se vería como ~100 %.
 (2) Si el instrumento estuviera muerto —malla vacía, distancia siempre 0—, el
     control positivo `--control` falla: pone un único punto crítico y una malla
     conocida, y exige que la fracción de cambio a 50 m sea > 0 y que el nivel a
     0 m sea 'alto' y a 2.000 m 'sindato'.

Uso:
    python tools/auditoria/sensibilidad_radios_veredicto.py
    python tools/auditoria/sensibilidad_radios_veredicto.py --control
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
PUNTOS = RAIZ / "web" / "data" / "puntos-criticos-inundacion.geojson"

RADIOS = {"cercano": 300.0, "medio": 500.0, "contexto": 1500.0}   # app.js:17
R_TIERRA = 6371000.0                                              # app.js:136


def haversine_m(lat1, lon1, lat2, lon2):
    """Copia literal de distancia() de app.js:135-143, vectorizada."""
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return 2 * R_TIERRA * np.arcsin(np.sqrt(a))


def nivel(lon, lat, plon, plat, grave):
    """Regla de app.js:342-378 sin capas A/B. Devuelve 0=sindato 1=bajo 2=medio 3=alto."""
    d = haversine_m(lat, lon, plat, plon)
    cerca = d <= RADIOS["contexto"]
    en_cercano = d <= RADIOS["cercano"]
    en_medio = d <= RADIOS["medio"]
    if (en_cercano & grave).any() or en_cercano.sum() >= 3:
        return 3
    if en_medio.any():
        return 2
    if cerca.any():
        return 1
    return 0


def desplazar(lon, lat, dx_m, dy_m):
    dlat = dy_m / 111_320.0
    dlon = dx_m / (111_320.0 * math.cos(math.radians(lat)))
    return lon + dlon, lat + dlat


def correr(plon, plat, grave, paso_m=25.0, alcance_m=1700.0, semilla=1):
    # Malla de prueba alrededor de cada punto crítico (se deduplica por celda).
    celdas = set()
    n_pasos = int(alcance_m // paso_m)
    for lo, la in zip(plon, plat):
        for i in range(-n_pasos, n_pasos + 1):
            for j in range(-n_pasos, n_pasos + 1):
                if math.hypot(i, j) * paso_m > alcance_m:
                    continue
                x, y = desplazar(lo, la, i * paso_m, j * paso_m)
                celdas.add((round(x, 5), round(y, 5)))
    pts = np.array(sorted(celdas))
    rng = np.random.default_rng(semilla)
    if len(pts) > 60_000:
        pts = pts[rng.choice(len(pts), 60_000, replace=False)]

    base = np.array([nivel(x, y, plon, plat, grave) for x, y in pts])
    salida = {"puntos_prueba": int(len(pts)),
              "niveles_base": {k: int((base == v).sum())
                               for k, v in (("sindato", 0), ("bajo", 1), ("medio", 2), ("alto", 3))}}
    for desp in (10.0, 25.0, 50.0):
        cambia = np.zeros(len(pts), bool)
        for dx, dy in ((desp, 0), (-desp, 0), (0, desp), (0, -desp)):
            niv = np.array([nivel(*desplazar(x, y, dx, dy), plon, plat, grave) for x, y in pts])
            cambia |= niv != base
        salida[f"cambia_con_{int(desp)}_m"] = {
            "n": int(cambia.sum()), "pct": round(100.0 * cambia.mean(), 1),
            "de_los_no_sindato_pct": round(
                100.0 * cambia[base > 0].mean(), 1) if (base > 0).any() else None,
        }
    # Distancia al punto crítico más cercano desde cada punto de prueba, para ver
    # cuántos quedan en la franja ±25 m de cada umbral.
    dmin = np.array([haversine_m(y, x, plat, plon).min() for x, y in pts])
    salida["en_franja_25m_de_un_umbral"] = {
        str(int(r)): int(((dmin > r - 25) & (dmin <= r + 25)).sum())
        for r in RADIOS.values()}
    return salida


def main() -> None:
    if "--control" in sys.argv:
        plon = np.array([-72.6]); plat = np.array([-38.75]); grave = np.array([True])
        assert nivel(-72.6, -38.75, plon, plat, grave) == 3, "a 0 m debe ser alto"
        x, y = desplazar(-72.6, -38.75, 2000, 0)
        assert nivel(x, y, plon, plat, grave) == 0, "a 2.000 m debe ser sindato"
        x, y = desplazar(-72.6, -38.75, 305, 0)
        assert nivel(x, y, plon, plat, grave) == 2, "a 305 m de un punto grave debe ser medio"
        r = correr(plon, plat, grave, paso_m=50.0, alcance_m=1700.0)
        assert r["cambia_con_50_m"]["n"] > 0, "el control debería ver cambios a 50 m"
        print("CONTROL POSITIVO OK:", json.dumps(r, ensure_ascii=False))
        return

    fc = json.loads(PUNTOS.read_text(encoding="utf-8"))
    feats = [f for f in fc["features"] if f.get("geometry")]
    plon = np.array([f["geometry"]["coordinates"][0] for f in feats], float)
    plat = np.array([f["geometry"]["coordinates"][1] for f in feats], float)
    grave = np.array([f["properties"].get("nivel") in ("Muy Alto", "Alto") for f in feats])
    print(f"puntos críticos: {len(feats)} ({int(grave.sum())} graves)")
    r = correr(plon, plat, grave)
    print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
