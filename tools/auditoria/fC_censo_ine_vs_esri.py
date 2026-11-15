#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fC_censo_ine_vs_esri.py: compara la cartografía censal 2024 del INE (GPKG oficial,
R09) contra la copia de Esri Chile que usa el proyecto
(data/processed/censo/censo-2024-araucania.geojson).

Pregunta: ¿son las mismas unidades, con la misma geometría y la misma gente? Y si no,
¿dónde difieren?

Qué compara
  - unidades por tipo (manzana, entidad, aldea) y emparejamiento por MANZENT;
  - población y los ocho campos de vulnerabilidad, unidad por unidad;
  - población por comuna (CUT);
  - geometría de cada par: diferencia simétrica / área, y distancia de Hausdorff, en
    EPSG:32719;
  - geometrías inválidas en cada fuente.

El GPKG del INE es dato NO confiable: se lee como datos con pyogrio, no se ejecuta nada
de él. Correr con `python -I` desde fuera de su carpeta.

LAS DOS PREGUNTAS DEL INSTRUMENTO
  1. Si las fuentes difirieran, ¿lo vería? --control toma una copia de las manzanas del
     INE, le suma 1 persona a una, corre 5 m otra, y borra una tercera; exige que la
     comparación reporte exactamente 1 diferencia de población, 1 geometría con
     Hausdorff entre 4 y 6 m, y 1 unidad sin pareja.
  2. Si el instrumento estuviera muerto (no emparejara nada), ¿se vería distinto? Sí:
     imprime cuántas unidades emparejó; el control exige que empareje todas menos la
     borrada.

Uso:  python -I tools/auditoria/fC_censo_ine_vs_esri.py RUTA_GPKG [--control]
"""
from __future__ import annotations

import io
import json
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

warnings.simplefilter("ignore")
RAIZ = Path(__file__).resolve().parents[2]
CENSO = RAIZ / "data" / "processed" / "censo" / "censo-2024-araucania.geojson"
SALIDA = RAIZ / "docs" / "auditorias" / "2026-11-15" / "frente-C"
CRS_M = 32719
CAMPOS = ["n_per", "n_fuente_agua_rio", "n_viv_hacinadas", "n_edad_60_mas", "n_edad_0_5",
          "n_discapacidad", "n_mat_paredes_precarios", "n_tipo_viv_mediagua",
          "n_distrib_agua_acarreo"]


def comparar(esri: gpd.GeoDataFrame, ine: gpd.GeoDataFrame, etiqueta: str) -> dict:
    """Empareja por MANZENT y compara atributos y geometría."""
    e = esri.copy()
    i = ine.copy()
    e["MANZENT"] = pd.to_numeric(e["MANZENT"]).astype("int64")
    i["MANZENT"] = pd.to_numeric(i["MANZENT"]).astype("int64")
    m = e.merge(i, on="MANZENT", suffixes=("_e", "_i"))
    r = {"tipo": etiqueta, "esri": len(e), "ine": len(i), "emparejadas": len(m),
         "solo_esri": int((~e["MANZENT"].isin(i["MANZENT"])).sum()),
         "solo_ine": int((~i["MANZENT"].isin(e["MANZENT"])).sum()),
         "manzent_dup_esri": int(e["MANZENT"].duplicated().sum()),
         "manzent_dup_ine": int(i["MANZENT"].duplicated().sum())}
    for c in CAMPOS:
        d = (m[f"{c}_e"].astype(float) - m[f"{c}_i"].astype(float)).abs()
        r[f"difieren_{c}"] = int((d > 0).sum())
    ge = gpd.GeoSeries(m["geometry_e"], crs=e.crs).to_crs(CRS_M).values
    gi = gpd.GeoSeries(m["geometry_i"], crs=i.crs).to_crs(CRS_M).values
    ge = shapely.make_valid(ge)
    gi = shapely.make_valid(gi)
    sym = shapely.area(shapely.symmetric_difference(ge, gi))
    rel = sym / np.maximum(shapely.area(gi), 1e-9)
    hd = shapely.hausdorff_distance(ge, gi)
    r["hausdorff_m_p50"] = round(float(np.median(hd)), 4) if len(hd) else None
    r["hausdorff_m_p99"] = round(float(np.percentile(hd, 99)), 4) if len(hd) else None
    r["hausdorff_m_max"] = round(float(hd.max()), 4) if len(hd) else None
    r["geom_hausdorff_mayor_1m"] = int((hd > 1).sum())
    r["geom_difsim_rel_max"] = round(float(rel.max()), 6) if len(rel) else None
    r["geom_difsim_rel_mayor_1pct"] = int((rel > 0.01).sum())
    r["vertices_esri"] = int(shapely.get_num_coordinates(ge).sum())
    r["vertices_ine"] = int(shapely.get_num_coordinates(gi).sum())
    r["_hd"] = hd
    return r


def control(ruta: Path) -> int:
    ine = gpd.read_file(ruta, layer="Manzanas_CPV24").to_crs(4326).iloc[:500].copy()
    mod = ine.copy()
    mod.loc[mod.index[10], "n_per"] = mod.loc[mod.index[10], "n_per"] + 1
    g = gpd.GeoSeries([mod.geometry.iloc[20]], crs=4326).to_crs(CRS_M)
    g = g.translate(xoff=5.0).to_crs(4326)
    mod.loc[mod.index[20], "geometry"] = g.iloc[0]
    mod = mod.drop(mod.index[30])
    r = comparar(mod, ine, "control")
    ok = (r["difieren_n_per"] == 1 and r["geom_hausdorff_mayor_1m"] == 1
          and 4 <= r["hausdorff_m_max"] <= 6 and r["solo_ine"] == 1 and r["emparejadas"] == 499)
    print({k: v for k, v in r.items() if k != "_hd"})
    print("CONTROL:", "OK" if ok else "FALLA")
    return 0 if ok else 2


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ruta = Path(args[0])
    if "--control" in sys.argv:
        sys.exit(control(ruta))

    esri = gpd.read_file(CENSO)
    capas = {"manzana_urbana": "Manzanas_CPV24", "entidad_rural": "Entidades_CPV24"}
    filas = []
    for tipo, capa in capas.items():
        ine = gpd.read_file(ruta, layer=capa)
        r = comparar(esri[esri["unidad_censal"] == tipo], ine, tipo)
        r.pop("_hd")
        r["invalidas_esri"] = int((~esri[esri["unidad_censal"] == tipo].is_valid).sum())
        r["invalidas_ine"] = int((~ine.is_valid).sum())
        filas.append(r)
        print({k: v for k, v in r.items()})

    # aldeas: el geojson no trae MANZENT para ellas; se emparejan por punto representativo
    ea = esri[esri["unidad_censal"] == "aldea"].to_crs(CRS_M)
    ia = gpd.read_file(ruta, layer="Aldeas_CPV24").to_crs(CRS_M)
    rp = gpd.GeoDataFrame(ea[["n_per"]], geometry=ea.representative_point(), crs=CRS_M)
    j = gpd.sjoin(rp, ia[["n_per", "geometry"]].rename(columns={"n_per": "n_per_ine"}), predicate="within")
    hd = shapely.hausdorff_distance(ea.loc[j.index].geometry.values,
                                    ia.loc[j["index_right"]].geometry.values)
    ra = {"tipo": "aldea", "esri": len(ea), "ine": len(ia), "emparejadas": len(j),
          "difieren_n_per": int((j["n_per"] != j["n_per_ine"]).sum()),
          "hausdorff_m_max": round(float(hd.max()), 4),
          "invalidas_esri": int((~ea.is_valid).sum()), "invalidas_ine": int((~ia.is_valid).sum())}
    filas.append(ra)
    print(ra)

    # por comuna
    ine_all = pd.concat([gpd.read_file(ruta, layer=l, read_geometry=False)[["CUT", "n_per"]].assign(capa=l)
                         for l in ("Manzanas_CPV24", "Entidades_CPV24")])
    pe = esri[esri["unidad_censal"] != "aldea"].groupby("CUT")["n_per"].sum()
    pi = ine_all.groupby(pd.to_numeric(ine_all["CUT"]))["n_per"].sum()
    com = pd.DataFrame({"esri_sin_aldeas": pe, "ine_manzanas_mas_entidades": pi})
    com["esri_con_aldeas_como_esta"] = esri.groupby("CUT")["n_per"].sum()
    com["dif_sin_aldeas"] = com["esri_sin_aldeas"] - com["ine_manzanas_mas_entidades"]
    com["dif_como_esta"] = com["esri_con_aldeas_como_esta"] - com["ine_manzanas_mas_entidades"]
    nom = esri.drop_duplicates("CUT").set_index("CUT")["NOM_COMUNA"]
    com.insert(0, "comuna", nom)
    com.to_csv(SALIDA / "ine_vs_esri_por_comuna.csv", encoding="utf-8")
    print(com.sum(numeric_only=True).to_dict())
    print("comunas con diferencia sin aldeas:", int((com["dif_sin_aldeas"] != 0).sum()),
          "| con aldeas como está:", int((com["dif_como_esta"] != 0).sum()))
    print(com[com["dif_como_esta"] != 0][["comuna", "dif_como_esta"]].to_string())
    pd.DataFrame(filas).to_csv(SALIDA / "ine_vs_esri_unidades.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
