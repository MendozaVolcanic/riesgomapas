"""¿El RMSE «leave-one-out» de los planos georreferenciados por grilla mide algo?

scripts/08_georreferenciar_grilla.py:293-304 arma los puntos de control como el
PRODUCTO CARTESIANO de las líneas de eastings por las de northings: con 7 y 6
líneas salen 42 «puntos», pero sólo hay 13 mediciones independientes (la
posición de cada línea). Al dejar fuera un punto (georref.py:76-87), su columna
y su fila siguen dentro del ajuste a través de los otros puntos, así que el
leave-one-out no deja nada fuera de verdad. Ese número («error de ubicación
0,19 m») es el que ve la persona en web/app.js:858.

Este instrumento vuelve a leer los rótulos de un PDF con las funciones del
script 08, reconstruye los puntos y calcula tres cosas:
  · RMSE LOO por punto (lo que publica el proyecto);
  · RMSE LOO por LÍNEA: se deja fuera una línea entera de la grilla (todos los
    puntos que la usan) y se predice su posición;
  · el error que introduce un corrimiento sistemático de 1 pt (0,35 mm) en la
    posición de TODOS los rótulos de un eje, que ningún LOO puede ver porque no
    hay dato independiente: eso es lo que vale la «exactitud» de un rótulo.

Las dos preguntas del instrumento:
 (1) Si el LOO por punto fuese honesto, coincidiría con el LOO por línea. Si el
     producto cartesiano lo infla, el LOO por línea saldrá mayor.
 (2) Control interno: al desplazar a propósito UNA línea 3 m, el LOO por línea
     debe subir de forma visible; si no sube, el instrumento está muerto y aborta.

Uso:
    python tools/auditoria/loo_por_linea_grilla.py <pdf> [pagina]
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from georref import ajustar, aplicar, metricas  # noqa: E402

spec = importlib.util.spec_from_file_location("s08", RAIZ / "scripts" / "08_georreferenciar_grilla.py")
s08 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s08)


def puntos_de(pdf: Path, pagina: int):
    doc = pdfium.PdfDocument(str(pdf))
    pag = doc[pagina - 1]
    W, H = pag.get_size()
    items = s08.digitos_con_caja(pag)
    numeros = s08.agrupar(items, True) + s08.agrupar(items, False)
    este = [e for e in numeros if s08.RANGO_ESTE[0] <= e["valor"] <= s08.RANGO_ESTE[1]]
    norte = [e for e in numeros if s08.RANGO_NORTE[0] <= e["valor"] <= s08.RANGO_NORTE[1]]
    ejeE, ejeN = s08.eje_desde_etiquetas(este, True), s08.eje_desde_etiquetas(norte, False)
    doc.close()
    if not ejeE or not ejeN:
        raise SystemExit("no se detectó grilla")
    esc = s08.DPI / 72.0
    return ejeE["pares"], ejeN["pares"], H, esc


def loo_por_linea(paresE, paresN, H, esc):
    def armar(pE, pN):
        px, py, mx, my = [], [], [], []
        for ve, xe in pE:
            for vn, yn in pN:
                px.append(xe * esc); py.append((H - yn) * esc); mx.append(ve); my.append(vn)
        return map(np.array, (px, py, mx, my))
    errores = []
    for i in range(len(paresE)):
        resto = paresE[:i] + paresE[i + 1:]
        px, py, mx, my = armar(resto, paresN)
        cx, cy = ajustar(px, py, mx, my, 1)
        qx, qy, qmx, qmy = armar([paresE[i]], paresN)
        ex, ey = aplicar(qx, qy, cx, cy, 1)
        errores.extend(np.hypot(ex - qmx, ey - qmy))
    for j in range(len(paresN)):
        resto = paresN[:j] + paresN[j + 1:]
        px, py, mx, my = armar(paresE, resto)
        cx, cy = ajustar(px, py, mx, my, 1)
        qx, qy, qmx, qmy = armar(paresE, [paresN[j]])
        ex, ey = aplicar(qx, qy, cx, cy, 1)
        errores.extend(np.hypot(ex - qmx, ey - qmy))
    return float(np.sqrt(np.mean(np.square(errores)))), float(np.max(errores))


def main() -> None:
    pdf = Path(sys.argv[1])
    pagina = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    paresE, paresN, H, esc = puntos_de(pdf, pagina)
    px, py, mx, my = [], [], [], []
    for ve, xe in paresE:
        for vn, yn in paresN:
            px.append(xe * esc); py.append((H - yn) * esc); mx.append(ve); my.append(vn)
    met = metricas(px, py, mx, my, 1)
    m_por_pt = abs((paresE[-1][0] - paresE[0][0]) / (paresE[-1][1] - paresE[0][1]))
    print(f"{pdf.name} p{pagina}: {len(paresE)} líneas E × {len(paresN)} líneas N = "
          f"{len(px)} «puntos» (mediciones independientes: {len(paresE) + len(paresN)})")
    print(f"  escala: {m_por_pt:.3f} m por pt de PDF → 1 pt de corrimiento de rótulo = {m_por_pt:.2f} m")
    print(f"  RMSE ajuste {met['rmse_m']} m · LOO por punto {met['rmse_loo_m']} m · "
          f"aptitud «{met['aptitud']}» (umbral predial < 10 m, georref.py:20)")
    r, mx_ = loo_por_linea(paresE, paresN, H, esc)
    print(f"  LOO por LÍNEA: RMSE {r:.2f} m · máx {mx_:.2f} m")
    # Control: mover una línea E 3 m (en pt) y ver que el LOO por línea lo nota.
    dpt = 3.0 / m_por_pt
    alterado = [(v, p + (dpt if k == 0 else 0)) for k, (v, p) in enumerate(paresE)]
    r2, _ = loo_por_linea(alterado, paresN, H, esc)
    print(f"  control: una línea E corrida 3 m → LOO por línea {r2:.2f} m")
    assert r2 > r + 0.5, "CONTROL FALLIDO: el LOO por línea no ve una línea corrida 3 m"
    # Corrimiento sistemático de todos los rótulos de un eje (no lo ve ningún LOO).
    todos = [(v, p + 1.0) for v, p in paresE]
    px2 = [xe * esc for ve, xe in todos for vn, yn in paresN]
    cx, cy = ajustar(px2, py, mx, my, 1)
    ex, ey = aplicar(px, py, cx, cy, 1)
    print(f"  si TODOS los rótulos E están 1 pt corridos respecto de su línea: "
          f"error sistemático {np.hypot(ex - mx, ey - my).mean():.2f} m, invisible para el LOO")


if __name__ == "__main__":
    main()
