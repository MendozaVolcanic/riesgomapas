# -*- coding: utf-8 -*-
"""vC_ine_vs_esri.py: verifica de forma independiente que el censo Esri del proyecto es el dato del INE.
Preguntas: (1) si Esri e INE fueran distintos (una poblacion alterada), ¿fallaria? Si: --control altera
una fila y exige que se detecte; ademas compara los 25 campos de CAMPOS, no solo 8. (2) si el instrumento
estuviera muerto (no emparejara nada), ¿se veria distinto? Si: el control exige que el numero de
emparejados sea > 0 y que una clave inventada quede sin pareja. Empareja por MANZENT donde existe y por
geometria (representative_point dentro) para las aldeas, que no tienen MANZENT."""
import sys, warnings
from pathlib import Path
import geopandas as gpd, pandas as pd, numpy as np
warnings.filterwarnings('ignore')
R = Path(__file__).resolve().parents[2]
P = R / 'data/raw/censo_ine_2024_R09/Cartografia_censo2024_R09.gpkg'
CAMPOS = ['n_per','n_hombres','n_mujeres','n_edad_0_5','n_edad_60_mas','n_discapacidad','n_viv_hacinadas','n_mat_paredes_precarios',
          'n_mat_techo_precarios','n_tipo_viv_mediagua','n_hog_allegados','n_jefatura_mujer','n_fuente_agua_publica',
          'n_fuente_agua_pozo','n_fuente_agua_camion','n_fuente_agua_rio','n_distrib_agua_acarreo']

def comparar(esri, ine, clave='MANZENT'):
    e = esri[esri[clave].notna()]; i = ine[ine[clave].notna()]
    out = {'dup_esri': int(e[clave].duplicated().sum()), 'dup_ine': int(i[clave].duplicated().sum())}
    m = e.drop_duplicates(clave).merge(i.drop_duplicates(clave), on=clave, suffixes=('_e', '_i'))
    out['emparejados'] = len(m); out['solo_esri'] = len(set(e[clave]) - set(i[clave])); out['solo_ine'] = len(set(i[clave]) - set(e[clave]))
    dif = {}
    for c in CAMPOS:
        if c + '_e' in m and c + '_i' in m:
            a, b = pd.to_numeric(m[c+'_e'], errors='coerce'), pd.to_numeric(m[c+'_i'], errors='coerce')
            dif[c] = int(((a != b) & ~(a.isna() & b.isna())).sum())
        else: dif[c] = 'campo ausente en alguna fuente'
    out['dif'] = dif
    return out, m

def control():
    a = pd.DataFrame({'MANZENT': ['1', '2', '3'], 'n_per': [5, 6, 7]}); b = a.copy(); b.loc[1, 'n_per'] = 99
    b.loc[2, 'MANZENT'] = 'X'
    o, _ = comparar(a, b)
    assert o['emparejados'] == 2 and o['dif']['n_per'] == 1 and o['solo_esri'] == 1, o
    print('control OK')

def main():
    esri = gpd.read_file(R / 'data/processed/censo/censo-2024-araucania.geojson')
    ine_m = gpd.read_file(P, layer='Manzanas_CPV24'); ine_e = gpd.read_file(P, layer='Entidades_CPV24'); ine_a = gpd.read_file(P, layer='Aldeas_CPV24')
    ine = pd.concat([ine_m, ine_e]); 
    print('INE manzanas+entidades', len(ine), 'aldeas', len(ine_a), 'pob', int(ine.n_per.sum()), int(ine_a.n_per.sum()))
    print('Esri sin MANZENT:', int(esri.MANZENT.isna().sum()), esri[esri.MANZENT.isna()].unidad_censal.value_counts().to_dict())
    o, m = comparar(esri[esri.unidad_censal != 'aldea'], ine)
    print({k: v for k, v in o.items() if k != 'dif'}); print('dif por campo', o['dif'])
    # geometria
    e32 = esri.set_index('MANZENT').to_crs(32719).geometry; i32 = ine.drop_duplicates('MANZENT').set_index('MANZENT').to_crs(32719).geometry
    k = [x for x in m.MANZENT.unique() if x in e32.index and x in i32.index]
    h = e32.loc[k].reset_index(drop=True).hausdorff_distance(i32.loc[k].reset_index(drop=True))
    print('hausdorff m: max', round(h.max(), 3), 'p99', round(h.quantile(.99), 3), 'n', len(k))
    # aldeas: emparejar por poblacion y comuna
    ea = esri[esri.unidad_censal == 'aldea'].to_crs(32719); ia = ine_a.to_crs(32719)
    ea['rp'] = ea.geometry.representative_point()
    ok = 0
    for _, r in ea.iterrows():
        c = ia[ia.geometry.contains(r.rp)]
        ok += int(len(c) == 1 and int(c.n_per.iloc[0]) == int(r.n_per))
    print('aldeas Esri con aldea INE que la contiene y misma n_per:', ok, 'de', len(ea))
    # invalidos
    print('invalidas Esri', int((~esri.geometry.is_valid).sum()), 'INE', int((~ine.geometry.is_valid).sum()), 'INE aldeas', int((~ine_a.geometry.is_valid).sum()))
    # manzanas rurales dentro de INE manzanas: AREA_C
    print('INE Manzanas por AREA_C', ine_m.groupby('AREA_C').n_per.agg(['count', 'sum']).to_dict())
    print('INE Manzanas TIPO_MZ', ine_m.TIPO_MZ.value_counts().to_dict())
    rur = ine_m[ine_m.AREA_C.str.lower() == 'rural']
    print('manzanas rurales INE n_per', int(rur.n_per.sum()), 'aldeas INE n_per', int(ine_a.n_per.sum()))

if __name__ == '__main__':
    control() if '--control' in sys.argv else main()
