"""Auditoría de la capa B (huella Sentinel-1 publicada): dónde caen las detecciones.

Las dos preguntas del instrumento:
 (1) Si la huella publicada tuviera nieve húmeda (cordillera) u océano (0 m,
     pegado a la costa), ¿esta prueba lo vería?  Sí: se muestrea el DEM
     Copernicus GLO-30 (terreno.tif, bandas elevación y pendiente) en TODOS los
     píxeles interiores de cada polígono, no sólo en el centroide, y la distancia
     a la costa se calcula desde el propio DEM (píxeles a exactamente 0 m al
     oeste de −72,5° = mar).  Antes de contar nada se meten dos polígonos
     sintéticos —uno en el volcán Llaima, otro en el mar frente a Puerto
     Saavedra— y el script exige contarlos como «sobre 1.200 m» y «a 0 m / < 1 km
     del mar»; si no, imprime CONTROL FALLÓ y sale con código 2.
 (2) Si el instrumento estuviera muerto (DEM ilegible, rasterización vacía),
     ¿se vería distinto?  Sí: los controles fallarían y los polígonos sin píxel
     interior se cuentan y se listan aparte como SIN DATO, no como 0.

Sólo lee. No escribe en data/ ni web/.
Uso:  python tools/auditoria/capa_b_donde_caen.py
"""
from __future__ import annotations

import collections
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import rasterize
from scipy import ndimage
from shapely.geometry import shape, Polygon, Point
from shapely.ops import transform as sh_transform
from shapely.strtree import STRtree

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
HUELLA = RAIZ / "web/data/sar/huella-observada.geojson"
COBERTURA = RAIZ / "web/data/sar/cobertura-sar.geojson"
INDICE = RAIZ / "web/data/sar/indice.json"
TERRENO = RAIZ / "data/processed/sar/2026-07-30_sistema_frontal/terreno.tif"
SENAPRED = RAIZ / "data/processed/senapred_puntos_criticos_araucania.geojson"

ALT_MAX, ALT_MIN, PEND_MAX = 1200.0, 0.5, 5.0     # config/araucania.yaml, bloque sar
_T = Transformer.from_crs("EPSG:4326", "EPSG:32719", always_xy=True)


def a_utm(g):
    return sh_transform(_T.transform, g)


def main():
    with rasterio.open(TERRENO) as f:
        elev = f.read(1)
        pend = f.read(2)
        tr = f.transform
        res = f.res[0]
    alto, ancho = elev.shape
    lat_media = (tr.f + tr.f + tr.e * alto) / 2
    m_px_y = res * 111_320.0
    m_px_x = m_px_y * math.cos(math.radians(lat_media))
    print(f"terreno.tif {ancho}×{alto} px · {m_px_x:.1f}×{m_px_y:.1f} m/px · "
          f"elev nan={int(np.isnan(elev).sum())}")

    # Máscara de mar: exactamente 0 m y al oeste de −72,5° (los lagos andinos no
    # están a 0 m; el único 0 exacto masivo del GLO-30 es el océano).
    cols = np.arange(ancho)
    lon_col = tr.c + (cols + 0.5) * tr.a
    mar = (elev == 0) & (lon_col[None, :] < -72.5)
    print(f"píxeles de mar (0 m exacto y lon < −72,5°): {int(mar.sum()):,}")
    # distancia euclídea al mar en píxeles, escalada a metros (anisotropía x/y)
    dist_px = ndimage.distance_transform_edt(~mar, sampling=(m_px_y, m_px_x))
    print(f"control: distancia al mar en Temuco (−72,60 −38,74) = "
          f"{dist_px[int((tr.f - (-38.74)) / res), int((-72.60 - tr.c) / res)] / 1000:.1f} km "
          f"(esperado ~60-70 km)")

    huella = json.loads(HUELLA.read_text(encoding="utf-8"))["features"]
    print(f"huella publicada: {len(huella)} polígonos; por track:",
          dict(collections.Counter(f["properties"]["track"] for f in huella)))

    # --- controles positivos sintéticos --------------------------------------
    llaima = Polygon([(-71.74, -38.70), (-71.72, -38.70), (-71.72, -38.68), (-71.74, -38.68)])
    mar_sint = Polygon([(-73.50, -38.80), (-73.48, -38.80), (-73.48, -38.78), (-73.50, -38.78)])
    sinteticos = [
        {"type": "Feature", "geometry": llaima.__geo_interface__,
         "properties": {"track": "CONTROL", "hectareas": 0, "nombre": "sintético Llaima"}},
        {"type": "Feature", "geometry": mar_sint.__geo_interface__,
         "properties": {"track": "CONTROL", "hectareas": 0, "nombre": "sintético mar"}},
    ]
    todos = huella + sinteticos

    # Rasterizar cada polígono con su índice+1 (all_touched=False: sólo píxeles
    # cuyo centro cae dentro; los polígonos vienen de esta misma rejilla).
    idx = rasterize(((shape(f["geometry"]), i + 1) for i, f in enumerate(todos)),
                    out_shape=(alto, ancho), transform=tr, fill=0, dtype="int32",
                    all_touched=False)
    print(f"píxeles rasterizados con algún polígono: {int((idx > 0).sum()):,}")

    filas = []
    sin_pixel = []
    for i, f in enumerate(todos):
        m = idx == (i + 1)
        n = int(m.sum())
        g = shape(f["geometry"])
        if n == 0:
            # polígono más chico que un píxel centrado: muestrear en el centroide
            c = g.centroid
            r, cc = int((tr.f - c.y) / res), int((c.x - tr.c) / res)
            if not (0 <= r < alto and 0 <= cc < ancho):
                sin_pixel.append(i); continue
            e, s, d = elev[r, cc:cc + 1], pend[r, cc:cc + 1], dist_px[r, cc:cc + 1]
            fuente = "centroide"
        else:
            e, s, d = elev[m], pend[m], dist_px[m]
            fuente = "interior"
        ha = a_utm(g).area / 1e4
        filas.append({
            "i": i, "track": f["properties"]["track"], "ha": ha,
            "ha_decl": f["properties"].get("hectareas"), "npx": n, "fuente": fuente,
            "alt_med": float(np.nanmedian(e)), "alt_max": float(np.nanmax(e)),
            "alt_min": float(np.nanmin(e)),
            "pend_med": float(np.nanmedian(s)), "pend_max": float(np.nanmax(s)),
            "dist_mar_m": float(np.nanmin(d)),
            "frac_px_alt_gt1200": float((e > ALT_MAX).mean()),
            "frac_px_alt_gt1000": float((e > 1000).mean()),
            "frac_px_alt_lt05": float((e < ALT_MIN).mean()),
            "frac_px_pend_gt5": float((s > PEND_MAX).mean()),
            "lon": g.centroid.x, "lat": g.centroid.y, "geom": g,
        })
    print(f"polígonos sin píxel ni centroide dentro del DEM (SIN DATO): {len(sin_pixel)}")

    # --- verificar controles -------------------------------------------------
    ok = True
    ctl = {r["i"]: r for r in filas if r["track"] == "CONTROL"}
    c_ll = ctl.get(len(huella)); c_mar = ctl.get(len(huella) + 1)
    if not c_ll or c_ll["alt_med"] <= ALT_MAX:
        print("CONTROL FALLÓ: el polígono sintético en el Llaima no sale sobre 1.200 m", c_ll and c_ll["alt_med"]); ok = False
    if not c_mar or c_mar["alt_med"] != 0.0 or c_mar["dist_mar_m"] > 1000:
        print("CONTROL FALLÓ: el polígono sintético en el mar no sale a 0 m / < 1 km", c_mar and (c_mar["alt_med"], c_mar["dist_mar_m"])); ok = False
    print(f"controles positivos: Llaima alt_med={c_ll['alt_med']:.0f} m (>{ALT_MAX:.0f} → contado), "
          f"mar alt_med={c_mar['alt_med']:.1f} m dist={c_mar['dist_mar_m']:.0f} m → {'OK' if ok else 'FALLÓ'}")
    if not ok:
        sys.exit(2)
    filas = [r for r in filas if r["track"] != "CONTROL"]

    # --- tablas por órbita ---------------------------------------------------
    def pct(xs, q):
        return float(np.percentile(xs, q)) if len(xs) else float("nan")

    print("\n=== Distribución por órbita (mediana de píxeles interiores por polígono) ===")
    print(f"{'track':<6}{'n':>5}{'ha':>9} | alt p5/p50/p95 (m) | pend p50/p95 (°) | dist mar p5/p50 (km) | "
          f"%área>1000m %área>1200m %área<0,5m %área<1km mar %área pend>5°")
    for tk in sorted({r["track"] for r in filas}) + ["TODOS"]:
        rs = [r for r in filas if tk == "TODOS" or r["track"] == tk]
        A = sum(r["ha"] for r in rs)
        alts = [r["alt_med"] for r in rs]; pen = [r["pend_med"] for r in rs]
        dm = [r["dist_mar_m"] / 1000 for r in rs]
        a1000 = sum(r["ha"] for r in rs if r["alt_med"] > 1000) / A * 100
        a1200 = sum(r["ha"] for r in rs if r["alt_med"] > ALT_MAX) / A * 100
        a05 = sum(r["ha"] for r in rs if r["alt_med"] < ALT_MIN) / A * 100
        akm = sum(r["ha"] for r in rs if r["dist_mar_m"] < 1000) / A * 100
        ap5 = sum(r["ha"] for r in rs if r["pend_med"] > PEND_MAX) / A * 100
        print(f"{tk:<6}{len(rs):>5}{A:>9.1f} | {pct(alts,5):6.0f}/{pct(alts,50):6.0f}/{pct(alts,95):6.0f} | "
              f"{pct(pen,50):5.1f}/{pct(pen,95):5.1f} | {pct(dm,5):6.1f}/{pct(dm,50):6.1f} | "
              f"{a1000:8.2f} {a1200:9.2f} {a05:9.2f} {akm:10.2f} {ap5:10.2f}")

    print("\n=== Conteos absolutos sobre los 1.075 (mediana del polígono) ===")
    for nombre, cond in (("alt_med > 1200 m", lambda r: r["alt_med"] > ALT_MAX),
                         ("alt_med > 1000 m", lambda r: r["alt_med"] > 1000),
                         ("alt_max > 1200 m (algún píxel)", lambda r: r["alt_max"] > ALT_MAX),
                         ("alt_med < 0,5 m", lambda r: r["alt_med"] < ALT_MIN),
                         ("alt_min <= 0 m (algún píxel)", lambda r: r["alt_min"] <= 0),
                         ("dist al mar < 1 km", lambda r: r["dist_mar_m"] < 1000),
                         ("pend_med > 5°", lambda r: r["pend_med"] > PEND_MAX),
                         ("pend_max > 5° (algún píxel)", lambda r: r["pend_max"] > PEND_MAX),
                         ("muestreado sólo en centroide", lambda r: r["fuente"] == "centroide")):
        sel = [r for r in filas if cond(r)]
        print(f"  {nombre:<34} {len(sel):5d} polígonos  {sum(r['ha'] for r in sel):9.1f} ha  "
              f"tracks={dict(collections.Counter(r['track'] for r in sel))}")
        for r in sorted(sel, key=lambda r: -r["ha"])[:6]:
            print(f"      #{r['i']} {r['track']} {r['ha']:.1f} ha alt={r['alt_med']:.0f}m "
                  f"pend={r['pend_med']:.1f}° mar={r['dist_mar_m']/1000:.1f}km ({r['lon']:.4f},{r['lat']:.4f})")

    # Área declarada vs medida
    dif = [abs(r["ha"] - float(r["ha_decl"])) / max(r["ha"], 1e-9) for r in filas]
    print(f"\nhectareas declarada vs medida (UTM19): desvío relativo p50={np.median(dif)*100:.1f}% "
          f"max={max(dif)*100:.1f}%; suma declarada={sum(float(r['ha_decl']) for r in filas):.1f} "
          f"suma medida={sum(r['ha'] for r in filas):.1f}")
    ha_min = min(r["ha"] for r in filas)
    print(f"área mínima publicada: {ha_min:.3f} ha (min_pixeles_agrupados=5 → ≈ {5*m_px_x*m_px_y/1e4:.2f} ha)")

    # --- 10 más grandes con comuna aproximada --------------------------------
    sen = json.loads(SENAPRED.read_text(encoding="utf-8"))["features"]
    pts = [Point(f["geometry"]["coordinates"]) for f in sen]
    arbol = STRtree(pts)
    print("\n=== 10 polígonos más grandes (comuna = la del punto SENAPRED más cercano, APROX) ===")
    for r in sorted(filas, key=lambda r: -r["ha"])[:10]:
        j = arbol.nearest(r["geom"].centroid)
        com = sen[j]["properties"]["comuna"]
        dkm = a_utm(r["geom"].centroid).distance(a_utm(pts[j])) / 1000
        print(f"  #{r['i']:4d} {r['track']} {r['ha']:7.1f} ha  alt p50={r['alt_med']:5.0f} m "
              f"(min {r['alt_min']:.0f} / max {r['alt_max']:.0f})  pend p50={r['pend_med']:.1f}°  "
              f"mar={r['dist_mar_m']/1000:5.1f} km  ({r['lon']:.4f},{r['lat']:.4f})  "
              f"comuna≈{com} (punto a {dkm:.1f} km)")

    # --- dónde caen: histograma por franja de longitud (la prueba de agosto) ---
    print("\n=== Área por franja de longitud (0,4°) — la nieve de agosto caía en −71,4…−71,0 ===")
    for tk in sorted({r["track"] for r in filas}):
        rs = [r for r in filas if r["track"] == tk]
        h = collections.Counter()
        for r in rs:
            h[math.floor(r["lon"] / 0.4) * 0.4] += r["ha"]
        A = sum(h.values())
        print(f"  {tk}: " + "  ".join(f"[{k:.1f}) {v/A*100:4.1f}%" for k, v in sorted(h.items())))

    # --- cobertura vs índice -------------------------------------------------
    idxj = json.loads(INDICE.read_text(encoding="utf-8"))
    for t in idxj["tracks"]:
        n = sum(1 for r in filas if r["track"] == t["track"])
        A = sum(r["ha"] for r in filas if r["track"] == t["track"]) / 100
        print(f"indice {t['track']}: poligonos={t['poligonos']} km2={t['km2']}  |  archivo: n={n} km2={A:.2f}")

    # --- reproducir el ×2,8 --------------------------------------------------
    print("\n=== Enriquecimiento SENAPRED vs huella PUBLICADA (polígonos, no máscara) ===")
    cob = json.loads(COBERTURA.read_text(encoding="utf-8"))["features"]
    cob_utm = [a_utm(shape(f["geometry"])) for f in cob]
    cob_arbol = STRtree(cob_utm)
    hue_utm = [a_utm(r["geom"]) for r in filas]
    hue_arbol = STRtree(hue_utm)

    def en_cobertura(p):
        return any(cob_utm[k].contains(p) for k in cob_arbol.query(p))

    def agua_cerca(p, radio):
        b = p.buffer(radio) if radio > 0 else p
        return any(hue_utm[k].intersects(b) for k in hue_arbol.query(b))

    for etiqueta, sel in (("es_inundacion=True (data/processed, 1374 pts)",
                           [f for f in sen if f["properties"].get("es_inundacion")]),
                          ("web/data/puntos-criticos-inundacion.geojson (lo que usa el script 14)",
                           json.loads((RAIZ / "web/data/puntos-criticos-inundacion.geojson")
                                      .read_text(encoding="utf-8"))["features"])):
        obs = [a_utm(Point(f["geometry"]["coordinates"])) for f in sel]
        obs = [p for p in obs if en_cobertura(p)]
        rng = np.random.default_rng(20260809)
        # azar uniforme dentro de la cobertura (muestreo por rechazo en el bbox)
        xs = [g.bounds for g in cob_utm]
        x0, y0 = min(b[0] for b in xs), min(b[1] for b in xs)
        x1, y1 = max(b[2] for b in xs), max(b[3] for b in xs)
        azar, objetivo, intentos = [], len(obs) * 20, 0
        while len(azar) < objetivo and intentos < 5_000_000:
            intentos += 1
            p = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
            if en_cobertura(p):
                azar.append(p)
        print(f"\n{etiqueta}: {len(sel)} puntos, {len(obs)} dentro de la cobertura SAR; "
              f"{len(azar)} al azar")
        print("  radio   SENAPRED           azar               enriquecimiento")
        for radio in (0, 300, 1000):
            a = sum(agua_cerca(p, radio) for p in obs)
            b = sum(agua_cerca(p, radio) for p in azar)
            po, pa = 100 * a / max(1, len(obs)), 100 * b / max(1, len(azar))
            print(f"  {radio:>5} m  {a:4d}/{len(obs)} ({po:5.1f} %)  {b:5d}/{len(azar)} ({pa:5.1f} %)  "
                  f"×{po / pa if pa else float('nan'):.2f}")
        # control: barajar la huella (desplazarla 20 km al este) debe dar ≈ ×1
        if etiqueta.startswith("web"):
            from shapely.affinity import translate
            hue_desp = [translate(g, xoff=20_000) for g in hue_utm]
            arb2 = STRtree(hue_desp)
            def agua2(p, radio):
                b = p.buffer(radio); return any(hue_desp[k].intersects(b) for k in arb2.query(b))
            a = sum(agua2(p, 300) for p in obs); b = sum(agua2(p, 300) for p in azar)
            po, pa = 100 * a / len(obs), 100 * b / len(azar)
            print(f"  control negativo (huella desplazada 20 km al este, 300 m): "
                  f"{a}/{len(obs)} vs {b}/{len(azar)} → ×{po/pa if pa else float('nan'):.2f} (esperado ≈ ×1)")


if __name__ == "__main__":
    main()
