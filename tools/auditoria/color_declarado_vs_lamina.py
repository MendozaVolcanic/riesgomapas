#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""¿El color que declara la leyenda es el que la lámina usa en el mapa?

Las dos preguntas del instrumento
---------------------------------
1. ¿Qué mide? La distancia, en unidades RGB, entre el color declarado de cada
   clase en `config/laminas.yaml` y el color que domina la mancha de esa clase
   en el cuerpo de la lámina. Y, con esa distancia, cuánta superficie queda
   fuera de la tolerancia vigente: los píxeles que el vectorizador NO recoge.
2. ¿Cómo sabría que se equivoca? Con `--control`, que corre lo mismo contra un
   color desplazado a propósito y exige que el instrumento lo denuncie. Si el
   control pasa en verde, no está comparando nada.

Por qué existe
--------------
El cuadro de la leyenda se imprime plano. El mapa, no: puede llevar un
sombreado de relieve debajo que oscurece el mismo color, o una transparencia
sobre la base. Cuando eso pasa, un color muestreado del cuadrito y una
tolerancia estrecha dejan afuera parte de la mancha, y el polígono publicado
sale más chico que el impreso, sin que nada falle.

Esto NO decide. Mide para que la decisión se tome mirando un número: si el
color del cuerpo está lejos del declarado, hay que declarar el del cuerpo o
subir la tolerancia — pero eso se hace a sabiendas, no moviendo el umbral hasta
que el resultado quede bonito.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))


def dominante(pix: np.ndarray) -> tuple[int, int, int]:
    """Color más frecuente de un conjunto de píxeles, cuantizado de a 4.

    Cuantizado porque una imagen JPEG no repite un RGB exacto: el color de la
    mancha llega como una nube de valores cercanos, y la moda cruda elegiría un
    punto arbitrario de esa nube.
    """
    q = (pix // 4 * 4).astype(np.int32)
    claves, cuentas = np.unique(q[:, 0] * 65536 + q[:, 1] * 256 + q[:, 2],
                                return_counts=True)
    k = int(claves[int(np.argmax(cuentas))])
    return (k // 65536, (k // 256) % 256, k % 256)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lamina", default="angol-peligro-inundacion-2013")
    ap.add_argument("--control", action="store_true",
                    help="desplaza el color declarado y exige que se denuncie")
    a = ap.parse_args()

    import importlib
    v18 = importlib.import_module("18_vectorizar_laminas")

    laminas = {c["id"]: c for c in yaml.safe_load(
        (RAIZ / "config" / "laminas.yaml").read_text(encoding="utf-8"))["laminas"]}
    cfg = laminas[a.lamina]
    img = v18.imagenes_de(RAIZ / "data" / "raw" / cfg["pdf"], cfg["pagina"])[cfg["imagen"]]
    arr = np.asarray(img).astype(np.int32)

    # Fuera de la leyenda: el cuadrito es plano y sería el color declarado por
    # construcción. Lo que interesa es el color del MAPA.
    cuerpo = np.ones(arr.shape[:2], bool)
    for x0, y0, x1, y1 in cfg.get("excluir_cajas", []):
        cuerpo[y0:y1, x0:x1] = False

    tol = float(cfg["tolerancia_color"])
    declarados = []
    for clase in cfg["clases"]:
        d = np.array(clase["rgb"], dtype=np.int32)
        if a.control:
            d = np.clip(d + np.array([0, -60, 60], np.int32), 0, 255)
        declarados.append(d)

    # Distancia de cada píxel a cada clase, y a cuál queda más cerca. Sin este
    # paso, preguntar por «Medio» con un radio generoso devuelve la nube de
    # «Alto», que está a 99 unidades y es mucho más numerosa: una clase
    # contestaría por la otra.
    dists = np.stack([np.sqrt(((arr - d) ** 2).sum(2)) for d in declarados])
    duena = dists.argmin(0)

    salida, peor = [], 0.0
    for k, clase in enumerate(cfg["clases"]):
        decl = declarados[k]
        d = dists[k]
        # La nube de la clase: suya por cercanía, y dentro de un radio que
        # admite el sombreado del relieve sin llegar a la clase vecina.
        radio = min(tol * 2.5, float(min(
            (np.sqrt(((declarados[j] - decl) ** 2).sum()) / 2
             for j in range(len(declarados)) if j != k), default=tol * 2.5)))
        cerca = cuerpo & (duena == k) & (d < radio)
        if cerca.sum() < 200:
            # Que un color declarado no tenga mancha cerca en el mapa TAMBIÉN
            # es denunciarlo: no es que no se pueda medir, es que ese color no
            # está en la lámina.
            salida.append((clase["nombre"], None, None, 0, 0))
            peor = max(peor, 1.0)
            continue
        real = dominante(arr[cerca])
        dist = float(np.sqrt(((np.array(real) - decl) ** 2).sum()))
        dentro = int((cerca & (d < tol)).sum())
        fuera = int(cerca.sum() - dentro)
        salida.append((clase["nombre"], tuple(int(x) for x in decl), real,
                       dentro, fuera))
        peor = max(peor, dist - tol)

    print(f"lámina: {a.lamina}   tolerancia declarada: {tol:.0f}")
    print("(cada píxel se asigna a la clase declarada más cercana antes de "
          "muestrear,\n así que ninguna clase puede contestar por otra)")
    for nombre, decl, real, dentro, fuera in salida:
        if real is None:
            print(f"  {nombre:<8} ❌ ninguna mancha del color declarado en el mapa")
            continue
        dist = float(np.sqrt(((np.array(real) - np.array(decl)) ** 2).sum()))
        marca = "❌ fuera de tolerancia" if dist > tol else "✅ dentro"
        pct = 100 * fuera / max(dentro + fuera, 1)
        print(f"  {nombre:<8} declarado {decl}  en el mapa {real}  "
              f"distancia {dist:5.1f}  {marca}")
        print(f"           {dentro:,} px recogidos · {fuera:,} px de la misma "
              f"nube quedan fuera ({pct:.0f} %)")

    if a.control:
        ok = peor > 0
        sys.stderr.write("CONTROL POSITIVO: %s\n" % (
            "OK — denuncia el color desplazado" if ok
            else "FALLA — un color corrido 85 unidades le parece bien"))
        return 0 if ok else 2
    return 0 if peor <= 0 else 2


if __name__ == "__main__":
    sys.exit(main())
