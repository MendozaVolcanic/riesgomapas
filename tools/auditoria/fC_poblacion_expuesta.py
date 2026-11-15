#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fC_poblacion_expuesta.py: cuánta gente del Censo 2024 cae dentro de cada mancha de
evidencia, con los cuatro criterios de cruce, capa por capa y comuna por comuna.

Frente C de la auditoría del 15-nov-2026. NO publica nada al visor: escribe tablas en
docs/auditorias/2026-11-15/frente-C/.

QUÉ HACE
  1. Lee el censo (data/processed/censo/censo-2024-araucania.geojson) y quita las 33
     aldeas de la capa 2 SOLO si se comprueba, aldea por aldea, que su población es la
     suma exacta de las manzanas de la capa 0 cuyo punto representativo cae dentro.
     Si alguna no cuadra, se cae (dato incoherente, REGLAS.md §2).
  2. Para cada capa de evidencia (A normativo, A derivado, B observado, C modelado),
     por separado y nunca unidas entre sí, disuelve los polígonos de esa capa (o
     subcapa) para que un traslape interno no cuente dos veces a la misma gente.
  3. Cruza cada unidad censal con la mancha disuelta, en EPSG:32719 (metros):
       dentro    unidad con >= 99,99 % de su área dentro (cota inferior)
       punto     el representative_point() de la unidad cae dentro (no el centroide)
       reparto   n * (área dentro / área de la unidad): supone gente homogénea
       cualquier la unidad comparte área > 0 con la mancha (cota superior)
     y aplica los mismos cuatro criterios a los campos de vulnerabilidad.
  4. Para las subcapas del A derivado, que declaran `incertidumbre_borde_m`, repite el
     reparto con la mancha encogida y engordada en ese error, para ver cuánto mueve el
     borde la cifra.

LAS DOS PREGUNTAS DEL INSTRUMENTO
  1. Si el cruce estuviera completamente roto (fracción mal calculada, traslapes
     contados dos veces, aldeas duplicadas), ¿esta prueba fallaría? Sí: --control
     fabrica una manzana de población conocida mitad dentro, otra 70 % dentro, una
     mancha duplicada sobre sí misma y una aldea que repite a sus manzanas, y exige los
     valores exactos. Además exige que el cruce SIN disolver dé un número distinto
     (si diera igual, el control no estaría viendo el traslape).
  2. Si el instrumento estuviera muerto (no leyera la capa, o el cruce devolviera
     siempre cero), ¿el resultado se vería distinto? Sí: --control también exige que
     las desigualdades dentro <= reparto <= cualquier y punto <= cualquier se cumplan
     en los datos reales Y que al menos una capa real tenga reparto > 0; y que la
     mancha trasladada 100 km mar adentro dé cero exacto.

Uso:
  python tools/auditoria/fC_poblacion_expuesta.py --control
  python tools/auditoria/fC_poblacion_expuesta.py            # corre y escribe tablas
  python tools/auditoria/fC_poblacion_expuesta.py --con-aldeas   # muestra el doble conteo
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import box
from shapely import affinity

RAIZ = Path(__file__).resolve().parents[2]
CENSO = RAIZ / "data" / "processed" / "censo" / "censo-2024-araucania.geojson"
SALIDA = RAIZ / "docs" / "auditorias" / "2026-11-15" / "frente-C"
CRS_M = 32719
UMBRAL_DENTRO = 0.9999

CAMPOS_V = [
    "n_fuente_agua_rio", "n_viv_hacinadas", "n_edad_60_mas", "n_edad_0_5",
    "n_discapacidad", "n_mat_paredes_precarios", "n_tipo_viv_mediagua",
    "n_distrib_agua_acarreo",
]
CRITERIOS = ["dentro", "punto", "reparto", "cualquier"]

W = "web/data/"
CAPAS = [
    # (capa de evidencia, subcapa, archivo, filtro, campo de error de borde)
    ("A_normativo", "todas", W + "areas-riesgo-inundacion.geojson", None, None),
    ("A_normativo", "fluvial", W + "areas-riesgo-inundacion.geojson",
     lambda g: g["tipo_hidrico"] == "fluvial", None),
] + [
    # REGLAS.md §1.4: fenómeno distinto, cifra distinta. Una fila por tipo_hidrico.
    ("A_normativo", t, W + "areas-riesgo-inundacion.geojson",
     (lambda t: lambda g: g["tipo_hidrico"] == t)(t), None)
    for t in ("anegamiento", "litoral", "napa_freatica")
] + [
    ("A_derivado", "angol_estudio_2013_alto_medio", W + "laminas/vectorizadas.geojson",
     lambda g: g["origen_lamina"] == "angol-peligro-inundacion-2013", "incertidumbre_borde_m"),
    ("A_derivado", "angol_estudio_2013_alto", W + "laminas/vectorizadas.geojson",
     lambda g: (g["origen_lamina"] == "angol-peligro-inundacion-2013") & (g["clase"] == "Alto"),
     "incertidumbre_borde_m"),
    ("A_derivado", "angol_prc_ar2a", W + "laminas/vectorizadas.geojson",
     lambda g: g["origen_lamina"].str.startswith("angol-prc-ar2a"), "incertidumbre_borde_m"),
    ("A_derivado", "curarrehue_2025", W + "laminas/vectorizadas.geojson",
     lambda g: g["origen_lamina"] == "curarrehue-catripulli-inundacion-2025",
     "incertidumbre_borde_m"),
    ("A_derivado", "todas_disueltas", W + "laminas/vectorizadas.geojson", None, None),
    ("B_observado", "sar_2026_08", W + "sar/huella-observada.geojson", None, None),
    ("C_modelado", "gore_maxima", W + "gore/amenaza-inundacion.geojson",
     lambda g: g["clase"] == "MAXIMA", None),
    ("C_modelado", "gore_media_o_maxima", W + "gore/amenaza-inundacion.geojson", None, None),
] + [
    ("C_modelado", f"jrc_rp{rp}", W + f"jrc/rp{rp}.geojson", None, None)
    for rp in (10, 20, 50, 100, 200, 500)
]


# ----------------------------------------------------------------------- censo
def preparar_censo(g: gpd.GeoDataFrame, con_aldeas: bool = False) -> tuple[gpd.GeoDataFrame, dict]:
    """Proyecta, valida geometrías y quita las aldeas duplicadas tras comprobarlo."""
    g = g.to_crs(CRS_M).copy()
    g["geometry"] = shapely.make_valid(g.geometry.values)
    g = g[~g.geometry.is_empty].copy()
    info = {"unidades_entrada": len(g), "personas_entrada": int(g["n_per"].sum())}
    ald = g[g["unidad_censal"] == "aldea"]
    mz = g[g["unidad_censal"] == "manzana_urbana"]
    if len(ald):
        rp = gpd.GeoDataFrame({"n_per": mz["n_per"].values},
                              geometry=mz.geometry.representative_point().values, crs=CRS_M)
        j = gpd.sjoin(rp, ald[["geometry"]], predicate="within")
        suma = j.groupby("index_right")["n_per"].sum().reindex(ald.index, fill_value=0)
        dif = (suma - ald["n_per"]).abs()
        info["aldeas"] = len(ald)
        info["aldeas_que_cuadran"] = int((dif == 0).sum())
        info["personas_aldeas"] = int(ald["n_per"].sum())
        info["personas_manzanas_dentro_de_aldeas"] = int(suma.sum())
        if not con_aldeas:
            if (dif != 0).any():
                raise SystemExit(
                    f"{int((dif != 0).sum())} aldeas NO son la suma de sus manzanas: no se "
                    "puede decidir cuál capa duplicar o quitar. Revisa el censo.")
            g = g[g["unidad_censal"] != "aldea"].copy()
    g["area_u"] = g.geometry.area
    g = g[g["area_u"] > 0].copy()
    g["rural"] = g["AREA_C"].astype(str).str.lower().eq("rural")
    info["unidades_usadas"] = len(g)
    info["personas_usadas"] = int(g["n_per"].sum())
    return g.reset_index(drop=True), info


# ---------------------------------------------------------------------- mancha
def disolver(geoms) -> shapely.Geometry:
    v = shapely.make_valid(np.asarray(geoms))
    # make_valid puede devolver colecciones con líneas; nos quedamos con lo areal
    polys = []
    for x in shapely.get_parts(v):
        if x.geom_type in ("Polygon", "MultiPolygon"):
            polys.append(x)
        elif x.geom_type == "GeometryCollection":
            polys += [p for p in shapely.get_parts(x) if p.geom_type in ("Polygon", "MultiPolygon")]
    if not polys:
        return shapely.Polygon()
    return shapely.make_valid(shapely.union_all(polys))


def fracciones(u: gpd.GeoDataFrame, H, disuelta: bool = True, crudas=None) -> pd.DataFrame:
    """Por unidad: área dentro / área, y si su punto representativo cae dentro.

    disuelta=False (sólo para el control) suma el área contra cada polígono crudo
    sin disolver: así cuenta dos veces lo que se traslapa, que es el error a cazar.
    """
    out = pd.DataFrame({"a_in": np.zeros(len(u)), "rep_in": np.zeros(len(u), bool)})
    if H.is_empty:
        return out
    if disuelta:
        partes = gpd.GeoDataFrame(geometry=list(shapely.get_parts(H)), crs=CRS_M)
    else:
        partes = gpd.GeoDataFrame(geometry=list(crudas), crs=CRS_M)
    tree = shapely.STRtree(partes.geometry.values)
    iu, ip = tree.query(u.geometry.values, predicate="intersects")
    if len(iu):
        a = shapely.area(shapely.intersection(u.geometry.values[iu], partes.geometry.values[ip]))
        out["a_in"] = np.bincount(iu, weights=a, minlength=len(u))
    shapely.prepare(H)
    rp = u.geometry.representative_point().values
    out["rep_in"] = shapely.contains(H, rp)
    return out


def criterios(u: gpd.GeoDataFrame, fr: pd.DataFrame) -> pd.DataFrame:
    frac = np.clip(fr["a_in"].values / u["area_u"].values, 0, None)
    pesos = pd.DataFrame({
        "dentro": (frac >= UMBRAL_DENTRO).astype(float),
        "punto": fr["rep_in"].values.astype(float),
        "reparto": np.minimum(frac, 1.0),
        "cualquier": (fr["a_in"].values > 0).astype(float),
    })
    pesos["frac_cruda"] = frac
    return pesos


def agregar(u: gpd.GeoDataFrame, pesos: pd.DataFrame, por: str = "NOM_COMUNA") -> pd.DataFrame:
    filas = []
    for comuna, idx in u.groupby(por).groups.items():
        sub = u.loc[idx]
        p = pesos.loc[idx]
        if p["cualquier"].sum() == 0:
            continue
        f = {"comuna": comuna, "personas_comuna": int(sub["n_per"].sum()),
             "unidades_tocadas": int(p["cualquier"].sum()),
             "unidades_rurales_tocadas": int((p["cualquier"] * sub["rural"]).sum())}
        for c in CRITERIOS:
            f[f"personas_{c}"] = float((sub["n_per"] * p[c]).sum())
        f["personas_reparto_rural"] = float((sub["n_per"] * p["reparto"] * sub["rural"]).sum())
        f["pct_reparto"] = 100 * f["personas_reparto"] / f["personas_comuna"] if f["personas_comuna"] else np.nan
        for v in CAMPOS_V:
            f[f"{v}_comuna"] = int(sub[v].sum())
            for c in CRITERIOS:
                f[f"{v}_{c}"] = float((sub[v] * p[c]).sum())
        filas.append(f)
    df = pd.DataFrame(filas)
    if len(df):
        tot = {k: df[k].sum() for k in df.columns if k != "comuna"}
        tot["comuna"] = "TOTAL (comunas tocadas)"
        tot["pct_reparto"] = 100 * tot["personas_reparto"] / tot["personas_comuna"]
        df = pd.concat([df.sort_values("personas_reparto", ascending=False), pd.DataFrame([tot])],
                       ignore_index=True)
    return df


def leer_capa(arch: str, filtro) -> gpd.GeoDataFrame:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        c = gpd.read_file(RAIZ / arch)
    if filtro is not None:
        c = c[filtro(c)]
    return c


# ----------------------------------------------------------------------- control
def control() -> int:
    ok = True
    log = []

    def exige(nombre, obtenido, esperado, tol=1e-6):
        nonlocal ok
        bien = abs(obtenido - esperado) <= tol
        ok &= bien
        log.append(f"  {'OK   ' if bien else 'FALLA'} {nombre}: obtenido {obtenido:.4f}, esperado {esperado}")
        return bien

    x0, y0 = 700000.0, 5800000.0   # en UTM 19S, dentro de la región
    U = [box(x0, y0, x0 + 100, y0 + 100),               # U1 mitad dentro
         box(x0 + 300, y0, x0 + 400, y0 + 100),         # U2 entera dentro
         box(x0 + 1000, y0, x0 + 1100, y0 + 100),       # U3 fuera
         box(x0 + 500, y0, x0 + 600, y0 + 100)]         # U4 70 % dentro
    u = gpd.GeoDataFrame({"NOM_COMUNA": ["Sintetica"] * 4, "n_per": [1000, 1000, 1000, 1000],
                          "AREA_C": ["Urbano"] * 4, "unidad_censal": ["manzana_urbana"] * 4,
                          **{v: [10, 10, 10, 10] for v in CAMPOS_V}}, geometry=U, crs=CRS_M)
    u["area_u"] = u.geometry.area
    u["rural"] = False
    crudas = [box(x0 + 50, y0 - 50, x0 + 200, y0 + 150),     # cubre mitad de U1
              box(x0 + 250, y0 - 50, x0 + 450, y0 + 150),    # cubre U2
              box(x0 + 250, y0 - 50, x0 + 450, y0 + 150),    # DUPLICADO exacto sobre U2
              box(x0 + 50, y0 - 50, x0 + 120, y0 + 150),     # traslape parcial sobre U1
              box(x0 + 530, y0 - 50, x0 + 700, y0 + 150)]    # 70 % de U4
    H = disolver(crudas)
    p = criterios(u, fracciones(u, H))
    per = {c: (u["n_per"] * p[c]).values for c in CRITERIOS}
    log.append("Control 1: manzanas sintéticas de 1.000 personas, mancha con traslapes")
    exige("U1 mitad dentro, reparto", per["reparto"][0], 500)
    exige("U1 mitad dentro, dentro", per["dentro"][0], 0)
    exige("U1 mitad dentro, cualquier", per["cualquier"][0], 1000)
    exige("U2 entera dentro (mancha duplicada encima), reparto", per["reparto"][1], 1000)
    exige("U2 entera dentro, dentro", per["dentro"][1], 1000)
    exige("U2 entera dentro, punto", per["punto"][1], 1000)
    exige("U3 fuera, cualquier", per["cualquier"][2], 0)
    exige("U4 70 % dentro, reparto", per["reparto"][3], 700)
    exige("U4 70 % dentro, punto (centro adentro)", per["punto"][3], 1000)
    exige("U4 70 % dentro, dentro", per["dentro"][3], 0)
    exige("campo vulnerabilidad U1 reparto (10 viviendas)", (u["n_fuente_agua_rio"] * p["reparto"]).values[0], 5)

    log.append("Control 2: sin disolver, el traslape tiene que inflar la cifra (si no, el control es ciego)")
    pn = criterios(u, fracciones(u, H, disuelta=False, crudas=crudas))
    tot_naive = float((u["n_per"] * pn["frac_cruda"]).sum())
    tot_bien = float(per["reparto"].sum())
    log.append(f"  sin disolver (fracción cruda sin tope) = {tot_naive:.1f}; disuelta = {tot_bien:.1f}; esperado 2200")
    exige("disuelta total reparto", tot_bien, 2200)
    if tot_naive <= tot_bien + 1:
        ok = False
        log.append("  FALLA: sin disolver dio lo mismo, el control no ve el traslape")
    else:
        log.append("  OK    sin disolver infla la cifra: el control sí ve el doble conteo")

    log.append("Control 3: aldea que repite a sus dos manzanas (30 + 20 = 50)")
    m1 = box(x0, y0 + 1000, x0 + 100, y0 + 1100)
    m2 = box(x0 + 100, y0 + 1000, x0 + 200, y0 + 1100)
    base = {"NOM_COMUNA": "Sintetica", "AREA_C": "Rural", **{v: 0 for v in CAMPOS_V}}
    cg = gpd.GeoDataFrame([{**base, "n_per": 30, "unidad_censal": "manzana_urbana"},
                           {**base, "n_per": 20, "unidad_censal": "manzana_urbana"},
                           {**base, "n_per": 50, "unidad_censal": "aldea"}],
                          geometry=[m1, m2, box(x0 - 5, y0 + 995, x0 + 205, y0 + 1105)], crs=CRS_M)
    cg4326 = cg.to_crs(4326)
    limpio, info = preparar_censo(cg4326)
    exige("población tras quitar la aldea duplicada", limpio["n_per"].sum(), 50)
    exige("población si NO se quita (debe duplicar)", preparar_censo(cg4326, con_aldeas=True)[0]["n_per"].sum(), 100)
    cg_mal = cg4326.copy()
    cg_mal.loc[2, "n_per"] = 60
    try:
        preparar_censo(cg_mal)
        ok = False
        log.append("  FALLA: una aldea que no cuadra (60 != 50) no detuvo el instrumento")
    except SystemExit:
        log.append("  OK    una aldea que no cuadra (60 != 50) detiene el instrumento")

    log.append("Control 4: datos reales")
    g, info = preparar_censo(gpd.read_file(CENSO))
    log.append(f"  censo: {info}")
    exige("aldeas que cuadran con sus manzanas", info.get("aldeas_que_cuadran", -1), info.get("aldeas", -2))
    alguna = False
    for capa, sub, arch, filtro, _ in CAPAS:
        c = leer_capa(arch, filtro).to_crs(CRS_M)
        Hr = disolver(c.geometry.values)
        p = criterios(g, fracciones(g, Hr))
        tot = {k: float((g["n_per"] * p[k]).sum()) for k in CRITERIOS}
        orden = (tot["dentro"] * UMBRAL_DENTRO <= tot["reparto"] + 1e-6
                 and tot["reparto"] <= tot["cualquier"] + 1e-6
                 and tot["punto"] <= tot["cualquier"] + 1e-6)
        # por unidad, no sólo en total
        orden_u = bool(((p["dentro"] * UMBRAL_DENTRO <= p["reparto"] + 1e-9)
                        & (p["reparto"] <= p["cualquier"]) & (p["punto"] <= p["cualquier"])).all())
        ok &= orden and orden_u
        alguna |= tot["reparto"] > 0
        log.append(f"  {'OK   ' if orden and orden_u else 'FALLA'} {capa}/{sub}: dentro {tot['dentro']:.0f} <= reparto {tot['reparto']:.0f} <= cualquier {tot['cualquier']:.0f}; punto {tot['punto']:.0f}")
        if sub == "angol_prc_ar2a":
            lejos = affinity.translate(Hr, xoff=-100000)
            pz = criterios(g, fracciones(g, lejos))
            exige("mancha AR-2a de Angol trasladada 100 km al mar: cualquier", float((g["n_per"] * pz["cualquier"]).sum()), 0)
    if not alguna:
        ok = False
        log.append("  FALLA: ninguna capa real tiene gente expuesta: instrumento muerto")
    print("\n".join(log))
    print("CONTROL:", "OK" if ok else "FALLA")
    return 0 if ok else 2


# -------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--con-aldeas", action="store_true",
                    help="no quita las aldeas duplicadas (para medir el doble conteo)")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if a.control:
        sys.exit(control())

    g, info = preparar_censo(gpd.read_file(CENSO), con_aldeas=a.con_aldeas)
    print("censo:", info)
    SALIDA.mkdir(parents=True, exist_ok=True)
    sufijo = "_con_aldeas" if a.con_aldeas else ""
    resumen = []
    for capa, sub, arch, filtro, campo_borde in CAPAS:
        c = leer_capa(arch, filtro).to_crs(CRS_M)
        H = disolver(c.geometry.values)
        area_cruda = float(shapely.area(shapely.make_valid(c.geometry.values)).sum())
        p = criterios(g, fracciones(g, H))
        df = agregar(g, p)
        nombre = f"expuesta_{capa}_{sub}{sufijo}.csv"
        if not a.con_aldeas:
            df.to_csv(SALIDA / nombre, index=False, float_format="%.1f", encoding="utf-8")
        tot = {k: float((g["n_per"] * p[k]).sum()) for k in CRITERIOS}
        fila = {"capa": capa, "subcapa": sub, "poligonos": len(c),
                "ha_suma_poligonos": round(area_cruda / 1e4, 1),
                "ha_disuelta": round(H.area / 1e4, 1),
                "comunas_tocadas": int((df["comuna"] != "TOTAL (comunas tocadas)").sum()) if len(df) else 0,
                **{f"personas_{k}": round(v, 1) for k, v in tot.items()},
                "personas_reparto_rural": round(float((g["n_per"] * p["reparto"] * g["rural"]).sum()), 1)}
        for v in CAMPOS_V:
            fila[f"{v}_reparto"] = round(float((g[v] * p["reparto"]).sum()), 1)
            fila[f"{v}_min"] = round(float((g[v] * p["dentro"]).sum()), 1)
            fila[f"{v}_max"] = round(float((g[v] * p["cualquier"]).sum()), 1)
        if campo_borde:
            e = float(pd.to_numeric(c[campo_borde], errors="coerce").max())
            for signo, nom in ((-1, "encogida"), (1, "engordada")):
                Hb = shapely.make_valid(shapely.buffer(H, signo * e))
                pb = criterios(g, fracciones(g, Hb))
                fila[f"reparto_borde_{nom}_{e:g}m"] = round(float((g["n_per"] * pb["reparto"]).sum()), 1)
        resumen.append(fila)
        print(f"{capa:12} {sub:32} ha={fila['ha_disuelta']:>9} dentro={tot['dentro']:>8.0f} punto={tot['punto']:>8.0f} "
              f"reparto={tot['reparto']:>9.1f} cualquier={tot['cualquier']:>8.0f}")
    r = pd.DataFrame(resumen)
    r.to_csv(SALIDA / f"resumen_por_capa{sufijo}.csv", index=False, encoding="utf-8")
    print("escrito:", SALIDA / f"resumen_por_capa{sufijo}.csv")


if __name__ == "__main__":
    main()
