"""Cuánta gente del Censo 2024 vive dentro de cada mapa de inundación, por comuna.

Por qué existe. El inventario de comuna (script 19) dice cuánta gente tiene la
comuna, pero no cuánta vive **dentro** de la mancha. Ésa era la brecha de lógica
central del visor (familia 5 de la auditoría del 15-nov-2026), y es lo mismo que el
practicante calculó para Malleco en su informe del 13-nov.

Por qué un rango y no un número. La manzana censal no sabe dónde está cada casa: si
la mancha corta una manzana, no hay forma de saber cuántos de sus habitantes quedan
dentro. Se publican los cuatro criterios de cruce, que acotan la respuesta:

  dentro     sólo manzanas enteramente dentro (>= 99,99 % del área): cota inferior
  punto      la manzana cuenta entera si su punto representativo cae dentro
  reparto    habitantes por la fracción de área dentro: supone gente repartida pareja
  cualquier  cualquier manzana que la mancha toque: cota superior

En el AR-2a de Angol la cota inferior y la superior se separaban 50 veces (F-303).
El reparto es la cifra central, nunca la única.

Qué se cruza y qué no:

- Sólo capa A: el área de riesgo normativa (MINVU) y la derivada (láminas que
  vectorizamos). Son los mapas que una autoridad firmó; las capas B y C miden otra
  cosa y quedan para después.
- El A normativo va por fenómeno (fluvial, anegamiento, litoral, napa freática): juntos,
  el 84 % de la gente era un anegamiento de Temuco y la cifra hablaba de otra cosa
  (F-302). Las capas nunca se fusionan entre sí (REGLAS §1).
- El A derivado va por documento, y además con la mancha encogida y engordada en su
  error de borde declarado, porque moverlo cambia el reparto un cuarto o más (F-301).
- Dentro de cada capa se disuelven los polígonos antes de cruzar, para que un
  traslape no cuente dos veces a la misma gente.
- Se publica la fracción del reparto que cae en entidades rurales: ahí la gente no
  está repartida pareja (una entidad rural es un polígono grande con casas en un
  rincón) y el reparto pierde sentido (F-304).

El censo es `data/processed/censo/censo-2024-araucania.geojson` del script 16, que ya
no trae las aldeas contadas dos veces (F-300). Si apareciera una unidad «aldea», este
script se cae en vez de sumarla.

El cálculo se contrasta en `tests/test_poblacion_expuesta.py` con
`tools/auditoria/vC_reparto_independiente.py`, que reparte por otro camino.

Requiere: 16_censo_2024.py, 06_areas_riesgo_prc.py, 18_vectorizar_laminas.py y
19_estado_comunas.py (que decide qué láminas se publican).
Salida: web/data/poblacion-expuesta.json (unos 20 kB, va offline en el visor).
"""
from __future__ import annotations

import json
import warnings
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely

from comun import RAIZ, log, procedencia

CENSO = RAIZ / "data" / "processed" / "censo" / "censo-2024-araucania.geojson"
CAPA_A = RAIZ / "web" / "data" / "areas-riesgo-inundacion.geojson"
LAMINAS = RAIZ / "web" / "data" / "laminas" / "vectorizadas.geojson"
SALIDA = RAIZ / "web" / "data" / "poblacion-expuesta.json"

# Metros. La región cruza el meridiano 72 O, borde entre los husos 18 y 19; el
# reparto es un cociente de áreas y el borde se mueve unos metros, así que la
# deformación del huso (bajo 0,1 %) no cambia ninguna cifra publicada.
CRS_M = 32719
UMBRAL_DENTRO = 0.9999
CRITERIOS = ("dentro", "punto", "reparto", "cualquier")

# Campos de vulnerabilidad que se publican, con su unidad: el INE cuenta la fuente
# de agua por vivienda, no por hogar (F-308).
CAMPOS_V = {
    "n_fuente_agua_rio": "viviendas que sacan agua de río, vertiente u otra fuente natural",
    "n_edad_60_mas": "personas de 60 años o más",
    "n_edad_0_5": "niños de 0 a 5 años",
    "n_discapacidad": "personas con discapacidad",
}

NOMBRE_FENOMENO = {
    "fluvial": "Área de riesgo por inundación de río o estero del plan regulador",
    "anegamiento": "Área de riesgo por anegamiento del plan regulador",
    "litoral": "Área de riesgo por inundación litoral del plan regulador",
    "napa_freatica": "Área de riesgo por napa freática alta del plan regulador",
}


# ------------------------------------------------------------------ cálculo
def preparar_unidades(g: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Proyecta a metros, repara geometrías y marca las unidades rurales."""
    g = g.to_crs(CRS_M).copy()
    g["geometry"] = shapely.make_valid(g.geometry.values)
    g = g[~g.geometry.is_empty].copy()
    g["area_u"] = g.geometry.area
    g = g[g["area_u"] > 0].copy()
    g["rural"] = g["AREA_C"].astype(str).str.upper().eq("RURAL")
    return g.reset_index(drop=True)


def disolver(geoms) -> shapely.Geometry:
    """Une los polígonos de una capa en una sola mancha, sin líneas sueltas."""
    polys = []
    for x in shapely.get_parts(shapely.make_valid(np.asarray(list(geoms), dtype=object))):
        if x.geom_type in ("Polygon", "MultiPolygon"):
            polys.append(x)
        elif x.geom_type == "GeometryCollection":
            polys += [p for p in shapely.get_parts(x)
                      if p.geom_type in ("Polygon", "MultiPolygon")]
    if not polys:
        return shapely.Polygon()
    return shapely.make_valid(shapely.union_all(polys))


def cruzar(u: gpd.GeoDataFrame, geoms, campos=()) -> dict:
    """Por comuna: personas con cada criterio, reparto rural y campos de vulnerabilidad.

    `u` viene de `preparar_unidades`; `geoms` son los polígonos de UNA capa en
    CRS_M, que se disuelven aquí. Sólo devuelve comunas que la mancha toca.
    """
    H = disolver(geoms)
    n = len(u)
    a_in = np.zeros(n)
    if not H.is_empty:
        partes = np.asarray(list(shapely.get_parts(H)), dtype=object)
        iu, ip = shapely.STRtree(partes).query(u.geometry.values, predicate="intersects")
        if len(iu):
            a = shapely.area(shapely.intersection(u.geometry.values[iu], partes[ip]))
            a_in = np.bincount(iu, weights=a, minlength=n)
        shapely.prepare(H)
        rep_in = shapely.contains(H, u.geometry.representative_point().values)
    else:
        rep_in = np.zeros(n, bool)
    frac = np.clip(a_in / u["area_u"].values, 0, 1)
    pesos = {
        "dentro": (frac >= UMBRAL_DENTRO).astype(float),
        "punto": np.asarray(rep_in, float),
        "reparto": frac,
        "cualquier": (a_in > 0).astype(float),
    }
    out = {}
    tocadas = pesos["cualquier"] > 0
    for comuna in sorted(set(u.loc[tocadas, "NOM_COMUNA"])):
        m = (u["NOM_COMUNA"] == comuna).values
        per = u.loc[m, "n_per"].values
        r = {c: float((per * pesos[c][m]).sum()) for c in CRITERIOS}
        r["reparto_rural"] = float((per * pesos["reparto"][m] * u.loc[m, "rural"].values).sum())
        r["personas_comuna"] = int(per.sum())
        r["campos"] = {v: {c: float((u.loc[m, v].values * pesos[c][m]).sum()) for c in CRITERIOS}
                       for v in campos}
        out[comuna] = r
    return out


# ----------------------------------------------------------------- publicar
def _bloque_comuna(r: dict, borde: tuple[dict, dict] | None, comuna: str) -> dict:
    rep = r["reparto"]
    b = {
        "personas": {c: int(round(r[c])) for c in CRITERIOS},
        "personas_comuna": r["personas_comuna"],
        "fraccion_rural": round(r["reparto_rural"] / rep, 2) if rep > 0 else 0.0,
        "vulnerabilidad": {v: {c: int(round(x[c])) for c in CRITERIOS}
                           for v, x in r["campos"].items()},
    }
    if borde is not None:
        menos, mas = borde
        lo = menos.get(comuna, {}).get("reparto", 0.0)
        hi = mas.get(comuna, {}).get("reparto", 0.0)
        b["reparto_con_borde"] = [int(round(min(lo, rep))), int(round(max(hi, rep)))]
    return b


def _leer(p: Path) -> gpd.GeoDataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return gpd.read_file(p)


def main() -> None:
    cen = _leer(CENSO)
    if (cen["unidad_censal"] == "aldea").any():
        raise SystemExit("El censo trae unidades «aldea»: se contarían dos veces (F-300). "
                         "Corre de nuevo scripts/16_censo_2024.py.")
    u = preparar_unidades(cen)
    campos = tuple(CAMPOS_V)
    log(f"censo: {len(u)} unidades, {int(u['n_per'].sum())} personas")

    capas = []

    a = _leer(CAPA_A)
    proc_a = json.loads(CAPA_A.read_text(encoding="utf-8"))["procedencia"]
    a = a[a["es_inundacion"].astype(bool)].to_crs(CRS_M)
    desconocidos = set(a["tipo_hidrico"]) - set(NOMBRE_FENOMENO)
    if desconocidos:
        raise SystemExit(f"tipo_hidrico sin nombre para el visor: {sorted(desconocidos)}")
    for tipo in sorted(set(a["tipo_hidrico"])):
        sel = a[a["tipo_hidrico"] == tipo]
        res = cruzar(u, sel.geometry.values, campos)
        capas.append({
            "capa_evidencia": "A_normativo",
            "subcapa": tipo,
            "nombre": NOMBRE_FENOMENO[tipo],
            "poligonos": int(len(sel)),
            "comunas": {c: _bloque_comuna(r, None, c) for c, r in res.items()},
            "procedencia": procedencia(
                fuente=f"{proc_a['fuente']}, cruzada con el Censo 2024 (INE)",
                url=proc_a["url"],
                metodo="Polígonos del fenómeno disueltos y cruzados con manzanas y "
                       "entidades rurales del censo con cuatro criterios (ver script 21).",
                capa_evidencia="A_normativo",
                incertidumbre="El rango entre el criterio «dentro» y «cualquier» es la "
                              "incertidumbre del cruce: el censo no ubica las casas dentro "
                              "de la manzana.",
            ),
        })
        log(f"A_normativo {tipo}: {len(res)} comunas, reparto "
            f"{sum(r['reparto'] for r in res.values()):.0f}")

    v = _leer(LAMINAS)
    proc_v = json.loads(LAMINAS.read_text(encoding="utf-8"))["procedencia"]
    v = v.to_crs(CRS_M)
    for origen in sorted(set(v["origen_lamina"])):
        sel = v[v["origen_lamina"] == origen]
        err = sel["incertidumbre_borde_m"].astype(float)
        if (err <= 0).any() or err.isna().any():
            raise SystemExit(f"{origen}: polígonos sin error de borde declarado (REGLAS §2)")
        res = cruzar(u, sel.geometry.values, campos)
        menos = cruzar(u, sel.geometry.buffer(-err).values)
        mas = cruzar(u, sel.geometry.buffer(err).values)
        p0 = sel.iloc[0]
        anio = str(int(p0["anio"]))
        fuente = p0["fuente"] if anio in str(p0["fuente"]) else f"{p0['fuente']} ({anio})"
        capas.append({
            "capa_evidencia": "A_derivado",
            "subcapa": origen,
            "nombre": f"{fuente}, clases {', '.join(sorted(set(sel['clase'])))}",
            "poligonos": int(len(sel)),
            "incertidumbre_borde_m": float(err.max()),
            "comunas": {c: _bloque_comuna(r, (menos, mas), c) for c, r in res.items()},
            "procedencia": procedencia(
                fuente=f"{p0['fuente']}, vectorizada por el proyecto, cruzada con el "
                       "Censo 2024 (INE)",
                url=str(p0["url"]),
                metodo="Igual que el A normativo, y además el reparto repetido con la "
                       "mancha encogida y engordada en su error de borde declarado.",
                capa_evidencia="A_derivado",
                incertidumbre=f"{proc_v['incertidumbre']} Error de borde: "
                              f"{float(err.min()):g} a {float(err.max()):g} m.",
            ),
        })
        log(f"A_derivado {origen}: {len(res)} comunas, reparto "
            f"{sum(r['reparto'] for r in res.values()):.0f}")

    salida = {
        "generado": date.today().isoformat(),
        "censo": {
            "fuente": "Censo 2024, INE: manzanas y entidades rurales, sin aldeas",
            "personas_region": int(u["n_per"].sum()),
            "unidades": int(len(u)),
        },
        "criterios": {
            "dentro": "sólo manzanas enteramente dentro (cota inferior)",
            "punto": "la manzana cuenta entera si su punto representativo cae dentro",
            "reparto": "habitantes por la fracción de área dentro (cifra central)",
            "cualquier": "cualquier manzana que la mancha toque (cota superior)",
        },
        "campos_vulnerabilidad": CAMPOS_V,
        "capas": capas,
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
    log(f"escrito {SALIDA} ({SALIDA.stat().st_size / 1024:.1f} kB)")


if __name__ == "__main__":
    main()
