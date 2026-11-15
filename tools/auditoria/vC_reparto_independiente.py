# -*- coding: utf-8 -*-
"""vC_reparto_independiente.py: recalcula sin importar fC_ el reparto por area (F-301, F-302, F-303,
F-304) y la sensibilidad al borde.
Preguntas: (1) si el reparto estuviera roto (fraccion mal calculada), ¿fallaria? Si: --control exige
50 % y 70 % exactos en dos manzanas fabricadas y que una mancha duplicada no cambie el valor.
(2) si el instrumento estuviera muerto (devolviera 0), ¿se veria distinto? Si: el control exige 150 y
sin disolver sobre mancha duplicada exige 300 (distinto), y los datos reales no dan 0."""
import sys, warnings
from pathlib import Path
import geopandas as gpd, pandas as pd
from shapely.geometry import box
warnings.filterwarnings('ignore')
R = Path(__file__).resolve().parents[2]

def reparto(cen, mancha_geom, col='n_per'):
    m = gpd.GeoDataFrame(geometry=[mancha_geom], crs=cen.crs)
    cand = cen[cen.intersects(mancha_geom)].copy()
    if cand.empty: return 0.0
    inter = cand.geometry.intersection(mancha_geom).area
    return float((cand[col] * inter / cand.geometry.area).sum())

def control():
    cen = gpd.GeoDataFrame({'n_per': [100, 100]}, geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)], crs=32719)
    m1 = box(0, 0, 5, 10).union(box(10, 0, 17, 10))
    assert abs(reparto(cen, m1) - 120) < 1e-6
    m = gpd.GeoSeries([box(0, 0, 5, 10), box(0, 0, 5, 10)], crs=32719)
    assert abs(reparto(cen, m.union_all()) - 50) < 1e-6
    assert abs(sum(reparto(cen, g) for g in m) - 100) < 1e-6  # sin disolver duplica
    print('control OK')

def main():
    cen = gpd.read_file(R / 'data/processed/censo/censo-2024-araucania.geojson')
    n_ald = (cen.unidad_censal == 'aldea').sum()
    cen = cen[cen.unidad_censal != 'aldea'].to_crs(32719)
    pd.set_option('display.width', 250)
    # F-301
    v = gpd.read_file(R / 'web/data/laminas/vectorizadas.geojson').to_crs(32719)
    for nombre, sel in [('AR-2a', v[v.clase == 'AR-2a']), ('Alto', v[v.clase == 'Alto']),
                        ('Alto+Medio', v[v.clase.isin(['Alto', 'Medio'])]), ('Susc alta (Curarrehue)', v[v.clase == 'Susceptibilidad alta']),
                        ('Susc alta+media', v[v.clase.isin(['Susceptibilidad alta', 'Susceptibilidad media'])])]:
        base = reparto(cen, sel.geometry.union_all())
        mas = reparto(cen, sel.buffer(sel.incertidumbre_borde_m).union_all())
        menos = reparto(cen, sel.buffer(-sel.incertidumbre_borde_m).union_all())
        print(f'{nombre:24s} base {base:8.0f} -borde {menos:8.0f} ({(menos/base-1)*100:+.0f}%) +borde {mas:8.0f} ({(mas/base-1)*100:+.0f}%)  ha_disuelta {sel.geometry.union_all().area/1e4:.1f}  borde_m {sorted(sel.incertidumbre_borde_m.unique())}')
    # F-302
    a = gpd.read_file(R / 'web/data/areas-riesgo-inundacion.geojson').to_crs(32719)
    print('tipos', a.groupby('tipo_hidrico').size().to_dict(), 'es_inundacion', a.es_inundacion.value_counts().to_dict())
    tot = reparto(cen, a.geometry.union_all())
    print('A normativo todas reparto', round(tot))
    for t, s in a.groupby('tipo_hidrico'):
        print(f'  {t:14s} {reparto(cen, s.geometry.union_all()):8.0f}  ha {s.geometry.union_all().area/1e4:8.1f}')
    ane = a[a.tipo_hidrico == 'anegamiento']
    for c, s in ane.groupby('comuna'):
        print('  anegamiento', c, round(reparto(cen, s.geometry.union_all())), round(s.geometry.union_all().area/1e4, 1), 'n poligonos', len(s))
    print('aldeas excluidas del calculo:', n_ald)

if __name__ == '__main__':
    control() if '--control' in sys.argv else main()
