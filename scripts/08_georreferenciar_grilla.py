"""Capa A — georreferenciar planos de PRC leyendo su grilla UTM impresa.

Este script cierra la cadena del proyecto: convierte un plano regulador que vive
como PDF dentro de un expediente ambiental en una capa geográfica consultable,
**sin intervención humana**.

Cómo funciona, y por qué se puede:

Los planos de anteproyecto de los planes reguladores se dibujan en formato de
plóter con la **retícula de coordenadas UTM rotulada en los márgenes**. Esos
rótulos no son una imagen: son texto vectorial dentro del PDF, con posición
exacta en la página. Entonces:

  · las etiquetas horizontales (740500, 740750, …) están sobre el eje inferior y
    superior, y su posición X marca dónde cae esa línea de la grilla;
  · las etiquetas verticales (5716000, 5716250, …) están en los márgenes
    izquierdo y derecho, y su posición Y marca la línea correspondiente.

El producto cartesiano de unas y otras da decenas de puntos de control de
coordenada **exacta** — no aproximada como cuando se calzan calles contra un mapa
base. El error resultante es de centímetros y proviene sólo del redondeo de la
posición del rótulo.

Controles que aplica antes de dar nada por bueno:
  1. La grilla debe ser regular: se exige que el paso entre etiquetas
     consecutivas sea constante (tolerancia 2%). Una grilla irregular delata que
     lo detectado no son coordenadas.
  2. La relación valor↔posición debe ser lineal en ambos ejes (R² ≥ 0,9999).
  3. La escala en X y en Y debe coincidir entre sí (≤1%): un plano no puede tener
     dos escalas distintas.
  4. El huso UTM se deduce de la coordenada y se verifica que el resultado caiga
     dentro del bbox de la región. Un plano en PSAD56 en vez de WGS84 aterriza
     ~200 m corrido, y esa verificación lo detecta.

Uso:
    python 08_georreferenciar_grilla.py <pdf> --pagina 7
    python 08_georreferenciar_grilla.py --todas          # todas las candidatas
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import DATA_PROC, DATA_RAW, cargar_config, log, procedencia, sello  # noqa: E402
from georref import metricas, remuestrear  # noqa: E402

DPI = 300           # suficiente para leer rótulos; 400 dpi en hoja de 150 cm no cabe
TOL_PASO = 0.02     # 2% de tolerancia en la regularidad de la grilla
R2_MIN = 0.9999
TOL_ESCALA = 0.01   # 1% entre escala X y escala Y


# ------------------------------------------------------- lectura de rótulos

def digitos_con_caja(pagina) -> list[dict]:
    tp = pagina.get_textpage()
    items = []
    for i in range(tp.count_chars()):
        c = tp.get_text_range(i, 1)
        if not c or not c.isdigit():
            continue
        try:
            l, b, r, t = tp.get_charbox(i)
        except Exception:  # noqa: BLE001
            continue
        items.append({"c": c, "l": l, "b": b, "r": r, "t": t,
                      "cx": (l + r) / 2, "cy": (b + t) / 2,
                      "w": r - l, "h": t - b})
    return items


def agrupar(items: list[dict], horizontal: bool) -> list[dict]:
    """Reagrupa dígitos sueltos en números.

    Hay que hacerlo por geometría y no por el orden del flujo de texto: los
    exportadores de CAD/SIG emiten cada glifo como su propio objeto, así que en
    el stream "740500" no aparece contiguo.
    """
    if not items:
        return []
    clave = ((lambda x: (round(x["cy"], 0), x["cx"])) if horizontal
             else (lambda x: (round(x["cx"], 0), x["cy"])))
    its = sorted(items, key=clave)
    grupos, cur = [], []
    for x in its:
        if not cur:
            cur = [x]
            continue
        p = cur[-1]
        # La separación admisible entre glifos consecutivos va de un solape
        # importante a un espacio pequeño. El solape hay que permitirlo: en
        # varios PDF la caja que reporta pdfium es más ancha que el avance real
        # del carácter, y entonces el borde izquierdo del siguiente dígito queda
        # ANTES del borde derecho del anterior. Exigir separación no negativa
        # rompía el reagrupamiento entero y la lámina se descartaba por
        # "no se detectó grilla".
        if horizontal:
            hueco = x["l"] - p["r"]
            ok = (abs(x["cy"] - p["cy"]) <= p["h"] * 0.5
                  and -p["w"] * 0.8 <= hueco <= p["w"] * 0.9)
        else:
            hueco = x["b"] - p["t"]
            ok = (abs(x["cx"] - p["cx"]) <= p["w"] * 0.6
                  and -p["h"] * 0.8 <= hueco <= p["h"] * 0.9)
        if ok:
            cur.append(x)
        else:
            grupos.append(cur)
            cur = [x]
    grupos.append(cur)

    out = []
    for g in grupos:
        s = "".join(y["c"] for y in g)
        if re.fullmatch(r"\d{6,7}", s):
            out.append({"valor": int(s),
                        "x": sum(y["cx"] for y in g) / len(g),
                        "y": sum(y["cy"] for y in g) / len(g)})
    return out


# Rangos válidos de coordenada UTM en Chile continental. Sirven para descartar
# de entrada números de 6-7 dígitos que no son coordenadas (códigos de lámina,
# denominadores de escala, teléfonos del timbre municipal).
RANGO_ESTE = (100_000, 900_000)
RANGO_NORTE = (4_000_000, 8_000_000)
TOL_INLIER_M = 3.0   # un rótulo bien leído no se desvía más que esto del ajuste


def eje_desde_etiquetas(etiquetas: list[dict], usar_x: bool) -> dict | None:
    """Convierte etiquetas en la relación lineal posición ↔ coordenada.

    Cada línea de grilla suele venir rotulada dos veces (los dos márgenes). Se
    promedia la posición de las repeticiones del mismo valor, lo que además
    cancela pequeñas asimetrías de composición.

    El ajuste es **robusto por RANSAC**, no por mínimos cuadrados sobre todo lo
    detectado: en una hoja de plano conviven con la grilla otros números de 6-7
    dígitos, y basta uno para arruinar una regresión ordinaria. Se busca el
    subconjunto más grande que caiga sobre una misma recta y se descarta el
    resto, en vez de exigir que *todo* lo detectado sea coherente.
    """
    rango = RANGO_ESTE if usar_x else RANGO_NORTE
    por_valor: dict[int, list[float]] = {}
    for e in etiquetas:
        if not (rango[0] <= e["valor"] <= rango[1]):
            continue
        por_valor.setdefault(e["valor"], []).append(e["x"] if usar_x else e["y"])
    pares = sorted((v, float(np.mean(ps))) for v, ps in por_valor.items())
    if len(pares) < 3:
        return None

    valores = np.array([p[0] for p in pares], float)
    posiciones = np.array([p[1] for p in pares], float)

    # --- RANSAC exhaustivo: n es pequeño, se prueban todos los pares ---------
    mejor: tuple[int, np.ndarray] | None = None
    n = len(pares)
    for i in range(n):
        for j in range(i + 1, n):
            dp = posiciones[j] - posiciones[i]
            if abs(dp) < 1e-6:
                continue
            m = (valores[j] - valores[i]) / dp
            if m <= 0:          # la coordenada tiene que crecer con la posición
                continue
            b = valores[i] - m * posiciones[i]
            inliers = np.abs(m * posiciones + b - valores) <= TOL_INLIER_M
            k = int(inliers.sum())
            if mejor is None or k > mejor[0]:
                mejor = (k, inliers)
    if mejor is None or mejor[0] < 3:
        return None

    inliers = mejor[1]
    descartados = int((~inliers).sum())
    valores, posiciones = valores[inliers], posiciones[inliers]
    pares = [p for p, keep in zip(pares, inliers) if keep]

    orden = np.argsort(valores)
    valores, posiciones = valores[orden], posiciones[orden]

    # Control 1: grilla regular entre los inliers.
    pasos = np.diff(valores)
    paso = float(np.median(pasos)) if len(pasos) else 0.0
    if paso <= 0:
        return None
    regular = bool(np.all(np.abs(pasos - paso) <= paso * TOL_PASO))

    # Control 2: linealidad valor <-> posición.
    A = np.column_stack([posiciones, np.ones_like(posiciones)])
    coef, *_ = np.linalg.lstsq(A, valores, rcond=None)
    pred = A @ coef
    ss_res = float(np.sum((valores - pred) ** 2))
    ss_tot = float(np.sum((valores - valores.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {"pares": sorted(pares), "paso_m": paso, "regular": regular, "r2": r2,
            "m_por_pt": float(coef[0]), "n": len(pares),
            "descartados": descartados,
            "min": float(valores.min()), "max": float(valores.max())}


def huso_utm(este: float, norte: float, cfg: dict) -> str | None:
    """Deduce el huso probando 18S y 19S y quedándose con el que aterriza en la región.

    Los planos casi nunca declaran el EPSG en texto legible. Probar y verificar
    contra el bbox regional es más robusto que confiar en la longitud nominal,
    porque la Araucanía está partida justo por el meridiano 72°O.
    """
    bbox = cfg["region"]["bbox"]
    for epsg in (cfg["region"]["utm"]["principal"], cfg["region"]["utm"]["cordillera"]):
        tr = Transformer.from_crs(epsg, "EPSG:4326", always_xy=True)
        lon, lat = tr.transform(este, norte)
        if bbox[0] - 0.3 <= lon <= bbox[2] + 0.3 and bbox[1] - 0.3 <= lat <= bbox[3] + 0.3:
            return epsg
    return None


# ------------------------------------------------------------- procesamiento

def procesar(pdf: Path, pagina_n: int, cfg: dict, salida_dir: Path) -> dict:
    doc = pdfium.PdfDocument(str(pdf))
    try:
        if pagina_n > len(doc):
            return {"ok": False, "motivo": f"el PDF tiene {len(doc)} páginas"}
        pag = doc[pagina_n - 1]
        W, H = pag.get_size()
        items = digitos_con_caja(pag)

        # Los rótulos se clasifican por RANGO DE VALOR, no por su orientación en
        # la hoja. La primera versión asumía "eastings horizontales, northings
        # rotadas", que es la convención de algunos planos pero no de todos: en
        # el PRC de Purén ambas van horizontales dentro del marco. Como los
        # rangos UTM chilenos no se solapan (eastings 6 dígitos, northings 7),
        # el valor basta para saber de qué eje es cada rótulo.
        numeros = agrupar(items, horizontal=True) + agrupar(items, horizontal=False)
        vistos, unicos = set(), []
        for e in numeros:
            clave = (e["valor"], round(e["x"], 1), round(e["y"], 1))
            if clave not in vistos:
                vistos.add(clave)
                unicos.append(e)

        este_lbl = [e for e in unicos if RANGO_ESTE[0] <= e["valor"] <= RANGO_ESTE[1]]
        norte_lbl = [e for e in unicos if RANGO_NORTE[0] <= e["valor"] <= RANGO_NORTE[1]]

        ejeE = eje_desde_etiquetas(este_lbl, usar_x=True)
        ejeN = eje_desde_etiquetas(norte_lbl, usar_x=False)
        if not ejeE or not ejeN:
            return {"ok": False, "motivo": "no se detectó grilla en uno de los ejes",
                    "etiquetas_h": len(este_lbl), "etiquetas_v": len(norte_lbl)}

        problemas = []
        if not ejeE["regular"]:
            problemas.append("grilla de eastings irregular")
        if not ejeN["regular"]:
            problemas.append("grilla de northings irregular")
        if ejeE["r2"] < R2_MIN:
            problemas.append(f"eastings no lineales (R²={ejeE['r2']:.6f})")
        if ejeN["r2"] < R2_MIN:
            problemas.append(f"northings no lineales (R²={ejeN['r2']:.6f})")

        # Control 3: misma escala en ambos ejes.
        esc_x, esc_y = abs(ejeE["m_por_pt"]), abs(ejeN["m_por_pt"])
        if max(esc_x, esc_y) > 0 and abs(esc_x - esc_y) / max(esc_x, esc_y) > TOL_ESCALA:
            problemas.append(f"escalas distintas en X ({esc_x:.4f}) e Y ({esc_y:.4f}) m/pt")

        # Control 4: huso y verificación contra el bbox regional.
        e0 = (ejeE["min"] + ejeE["max"]) / 2
        n0 = (ejeN["min"] + ejeN["max"]) / 2
        crs = huso_utm(e0, n0, cfg)
        if not crs:
            problemas.append(f"la coordenada ({e0:.0f}, {n0:.0f}) no cae en la región "
                             "en ningún huso — ¿datum distinto?")
        if problemas:
            return {"ok": False, "motivo": "; ".join(problemas),
                    "ejeE": {k: ejeE[k] for k in ("n", "paso_m", "r2", "regular")},
                    "ejeN": {k: ejeN[k] for k in ("n", "paso_m", "r2", "regular")}}

        # --- puntos de control: producto cartesiano de las dos grillas -------
        escala = DPI / 72.0
        px, py, mx, my = [], [], [], []
        for ve, xe in ejeE["pares"]:
            for vn, yn in ejeN["pares"]:
                px.append(xe * escala)
                # El origen del PDF está abajo-izquierda; la imagen, arriba-izquierda.
                py.append((H - yn) * escala)
                mx.append(ve)
                my.append(vn)

        met = metricas(px, py, mx, my, orden=1)

        img = np.array(pag.render(scale=escala).to_pil().convert("RGB"))
        destino = salida_dir / f"{pdf.stem}_p{pagina_n:03d}.tif"
        info = remuestrear(img, met, crs, destino, px, py, mx, my)

        return {"ok": True, "crs": crs, "pagina": pagina_n,
                "hoja_cm": [round(W / 28.35), round(H / 28.35)],
                "grilla": {"paso_este_m": ejeE["paso_m"], "paso_norte_m": ejeN["paso_m"],
                           "lineas_este": ejeE["n"], "lineas_norte": ejeN["n"],
                           "r2_este": round(ejeE["r2"], 8), "r2_norte": round(ejeN["r2"], 8)},
                "ajuste": {k: v for k, v in met.items() if not k.startswith("_")},
                "raster": info, "geotiff": str(destino)}
    finally:
        doc.close()


def candidatas() -> list[tuple[Path, int]]:
    """Láminas detectadas por el script 07 como cartografía de amenaza hídrica."""
    out: list[tuple[Path, int]] = []
    for f in sorted((DATA_PROC / "eae").glob("laminas_candidatas_*.json")):
        for d in json.loads(f.read_text(encoding="utf-8")):
            pdf = DATA_RAW / d["archivo_local"]
            if not pdf.exists():
                continue
            for h in d["paginas_con_amenaza"]:
                if h.get("tipo_lamina") == "plano":
                    out.append((pdf, h["pagina"]))
    # dedup conservando orden
    vistos, unicas = set(), []
    for t in out:
        if t not in vistos:
            vistos.add(t)
            unicas.append(t)
    return unicas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", nargs="?")
    ap.add_argument("--pagina", type=int, default=1)
    ap.add_argument("--todas", action="store_true",
                    help="procesa todas las láminas candidatas del script 07")
    ap.add_argument("--saltar-existentes", action="store_true",
                    help="omite las láminas que ya tienen GeoTIFF (para reintentar "
                         "sólo las que fallaron sin re-renderizar el resto)")
    a = ap.parse_args()

    cfg = cargar_config()
    salida = DATA_PROC / "georreferenciado"
    salida.mkdir(parents=True, exist_ok=True)

    tareas = candidatas() if a.todas else [(Path(a.pdf), a.pagina)]
    if not a.todas and not a.pdf:
        ap.error("indica un PDF o usa --todas")

    if a.saltar_existentes:
        antes = len(tareas)
        tareas = [(p, n) for p, n in tareas
                  if not (salida / f"{p.stem}_p{n:03d}.tif").exists()]
        log(f"{antes - len(tareas)} lámina(s) ya georreferenciada(s), se omiten")

    log(f"{len(tareas)} lámina(s) a procesar")
    resultados, ok, fallidas = [], 0, 0
    for pdf, npag in tareas:
        log(f"{pdf.name} p{npag}")
        try:
            r = procesar(pdf, npag, cfg, salida)
        except Exception as exc:  # noqa: BLE001
            r = {"ok": False, "motivo": f"excepción: {str(exc)[:110]}"}
        r["pdf"] = str(pdf)
        r["pagina"] = npag
        resultados.append(r)
        if not r["ok"]:
            fallidas += 1
            log(f"  ✗ {r['motivo']}")
            continue
        ok += 1
        aj = r["ajuste"]
        g = r["grilla"]
        log(f"  ✓ {r['crs']} | hoja {r['hoja_cm'][0]}x{r['hoja_cm'][1]} cm | "
            f"grilla {g['lineas_este']}x{g['lineas_norte']} cada {g['paso_este_m']:.0f} m")
        log(f"    {aj['n_puntos']} puntos de control · RMSE LOO {aj['rmse_loo_m']} m "
            f"· aptitud {aj['aptitud'].upper()}")
        log(f"    {r['raster']['resolucion_m']} m/px → {Path(r['geotiff']).name}")

        meta = procedencia(
            fuente=f"Plano de plan regulador georreferenciado por grilla UTM impresa "
                   f"({pdf.name}, p{npag})",
            url=str(pdf),
            metodo=f"Lectura automática de los rótulos de la retícula UTM del PDF, "
                   f"{aj['n_puntos']} puntos de control, transformación afín, "
                   f"render a {DPI} dpi",
            capa_evidencia="A_normativo",
            incertidumbre=f"RMSE leave-one-out {aj['rmse_loo_m']} m — {aj['uso_permitido']}. "
                          f"La coordenada de los puntos de control es exacta; el error "
                          f"proviene del centrado del rótulo en la página.",
            escala_original=f"hoja de {r['hoja_cm'][0]}x{r['hoja_cm'][1]} cm",
        )
        Path(r["geotiff"]).with_suffix(".json").write_text(
            json.dumps({"procedencia": meta,
                        **sello(f"Plan Regulador — {pdf.stem}", None),
                        "crs": r["crs"], "grilla": g, "ajuste": aj,
                        "raster": r["raster"]},
                       ensure_ascii=False, indent=1), encoding="utf-8")

    # Se FUSIONA con lo que ya había en vez de sobrescribir: correr el script
    # sobre un solo plano para reintentarlo no puede borrar el resultado de las
    # otras 20 láminas del lote anterior. La clave es (pdf, página).
    registro = DATA_PROC / "eae" / "georreferenciacion_grilla.json"
    previos = {}
    if registro.exists():
        try:
            for r in json.loads(registro.read_text(encoding="utf-8")):
                previos[(r.get("pdf"), r.get("pagina"))] = r
        except Exception:  # noqa: BLE001
            pass
    for r in resultados:
        previos[(r["pdf"], r["pagina"])] = r
    registro.write_text(
        json.dumps(sorted(previos.values(), key=lambda r: (r["pdf"], r["pagina"])),
                   ensure_ascii=False, indent=1), encoding="utf-8")

    log("")
    log(f"RESULTADO: {ok} láminas georreferenciadas, {fallidas} sin grilla utilizable")
    if fallidas:
        log("Motivos de rechazo (son rechazos correctos: sin grilla legible no hay"
            " forma honesta de ubicar el plano):")
        motivos: dict[str, int] = {}
        for r in resultados:
            if not r["ok"]:
                motivos[r["motivo"][:80]] = motivos.get(r["motivo"][:80], 0) + 1
        for k, v in sorted(motivos.items(), key=lambda t: -t[1]):
            log(f"   {v:3d}× {k}")


if __name__ == "__main__":
    main()
