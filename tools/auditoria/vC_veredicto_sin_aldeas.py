# -*- coding: utf-8 -*-
"""vC_veredicto_sin_aldeas.py: cuanto cambian las cifras de personas de fA_veredicto_censo.js al quitar
las 33 aldeas que duplican a sus manzanas. Usa el MISMO .js (evaluar() real de web/app.js), sin tocar fA_.
Preguntas: (1) si el doble conteo no existiera, ¿el resultado seria igual con y sin aldeas? Si: el control
interno exige que con aldeas el total sea 1.021.433 y sin ellas 1.003.546 (diferencia 17.887 exacta) y que
la suma de 'personas por nivel' coincida con el total evaluado. (2) si el instrumento estuviera muerto
(.js no evaluara), ¿se veria distinto? Si: el .js termina con error si evalua menos puntos que los entregados.
Sin GeoIDE (no esta disponible como GeoJSON local): las categorias D6/D7 no se miden aqui.
Uso: python vC_veredicto_sin_aldeas.py DIR_SALIDA"""
import json, subprocess, sys
from pathlib import Path
import numpy as np, rasterio, yaml
from shapely.geometry import shape
R = Path(__file__).resolve().parents[2]
JS = R / 'tools/auditoria/fA_veredicto_censo.js'
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
cfg = yaml.safe_load(open(R / 'config/araucania.yaml', encoding='utf-8'))['sar']
d = json.load(open(R / 'data/processed/censo/censo-2024-araucania.geojson', encoding='utf-8'))
pts = []
for f in d['features']:
    g = shape(f['geometry'])
    if g.is_empty: continue
    rp = g.representative_point(); p = f['properties']
    pts.append({'lon': rp.x, 'lat': rp.y, 'n': int(p.get('n_per') or 0), 'comuna': p.get('NOM_COMUNA'), 'u': p.get('unidad_censal'), 'rio': int(p.get('n_fuente_agua_rio') or 0)})
with rasterio.open(R / 'data/processed/sar/2026-07-30_sistema_frontal/terreno.tif') as r:
    vals = list(r.sample([(p['lon'], p['lat']) for p in pts]))
for p, v in zip(pts, vals):
    dem, pend = float(v[0]), float(v[1])
    p['apto'] = bool(np.isfinite(dem) and np.isfinite(pend) and pend <= cfg['pendiente_max_grados'] and dem <= cfg['altitud_max_m'] and dem > cfg['altitud_min_m'])
con = pts; sin = [p for p in pts if p['u'] != 'aldea']
assert sum(p['n'] for p in con) == 1021433 and sum(p['n'] for p in sin) == 1003546 and sum(p['n'] for p in con) - sum(p['n'] for p in sin) == 17887
for nombre, lista in (('con_aldeas', con), ('sin_aldeas', sin)):
    f = out / f'{nombre}.json'; f.write_text(json.dumps(lista), encoding='utf-8')
    r = subprocess.run(['node', str(JS), str(f)], capture_output=True, text=True, encoding='utf-8')
    (out / f'{nombre}.txt').write_text(r.stdout + r.stderr, encoding='utf-8')
    print('=====', nombre, 'rc', r.returncode); print(r.stdout[:2500]); print(r.stderr[:500])
