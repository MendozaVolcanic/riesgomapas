# -*- coding: utf-8 -*-
"""vC_aldeas_doble_conteo.py: verifica F-300 de forma independiente (sin importar fC_).
Preguntas: (1) si las aldeas NO duplicaran a otras unidades, ¿fallaría? Sí: --control fabrica una
aldea que repite a dos manzanas y otra que no, y exige que solo la primera se marque.
(2) si el instrumento estuviera muerto (no cruzara nada), ¿se vería distinto? Sí: el control
exige 1 aldea duplicada y 1 no; con instrumento muerto daría 0 y 0.
Mide, por aldea, la población de las unidades NO aldea cuya geometría (intersección) cubre el
polígono de la aldea, por dos criterios: punto representativo dentro, y área solapada."""
import sys
from pathlib import Path
import geopandas as gpd, pandas as pd
from shapely.geometry import box
R = Path(__file__).resolve().parents[2]

def medir(g):
    g = g.to_crs(32719)
    ald = g[g.unidad_censal == 'aldea']; otr = g[g.unidad_censal != 'aldea'].copy()
    otr['rp'] = otr.geometry.representative_point()
    rows = []
    for i, a in ald.iterrows():
        dentro = otr[otr.rp.within(a.geometry)]
        inter = otr[otr.intersects(a.geometry)]
        solap = inter.geometry.intersection(a.geometry).area.sum() / a.geometry.area if a.geometry.area else 0
        rows.append(dict(MANZENT=a.MANZENT, n=a.n_per, suma_rp=dentro.n_per.sum(), n_rp=len(dentro),
                         tipos=','.join(sorted(dentro.unidad_censal.unique())), frac_cubierta_por_otras=round(solap, 3),
                         area_ha=round(a.geometry.area/1e4, 1)))
    return pd.DataFrame(rows)

def control():
    g = gpd.GeoDataFrame({'MANZENT': ['a', 'b', 'A1', 'A2'], 'n_per': [10, 5, 15, 7],
        'unidad_censal': ['manzana_urbana', 'manzana_urbana', 'aldea', 'aldea']},
        geometry=[box(-72, -38, -71.999, -37.999), box(-71.999, -38, -71.998, -37.999),
                  box(-72, -38, -71.998, -37.999), box(-71.5, -38, -71.499, -37.999)], crs=4326)
    d = medir(g); dup = (d.n == d.suma_rp).sum()
    assert dup == 1 and d.loc[d.MANZENT == 'A2', 'suma_rp'].iloc[0] == 0, d
    print('control OK: 1 aldea duplicada detectada, 1 no')

if __name__ == '__main__':
    if '--control' in sys.argv: control(); sys.exit()
    g = gpd.read_file(R / 'data/processed/censo/censo-2024-araucania.geojson')
    d = medir(g)
    d['igual'] = d.n == d.suma_rp
    pd.set_option('display.width', 250); pd.set_option('display.max_rows', 100)
    print(d.to_string())
    print('aldeas', len(d), 'con suma exacta', int(d.igual.sum()), 'pob aldeas', int(d.n.sum()), 'pob suma_rp', int(d.suma_rp.sum()))
    print('tipos de unidades dentro:', d.tipos.value_counts().to_dict())
    tot = g.n_per.sum(); sin = g[g.unidad_censal != 'aldea'].n_per.sum()
    print('total con aldeas', int(tot), 'sin aldeas', int(sin), 'diferencia', int(tot - sin))
