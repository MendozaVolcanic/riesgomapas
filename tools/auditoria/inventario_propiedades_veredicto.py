"""Inventario de las propiedades que el veredicto del visor lee de cada GeoJSON.

Preguntas del instrumento:
 (1) Si un campo que app.js lee faltara en TODOS los features, ¿fallaría?  Sí:
     imprime el conteo de features sin ese campo; un 100 % es visible.
 (2) Si el instrumento estuviera muerto, ¿se vería distinto?  Sí: no imprimiría
     nada o reventaría; los conteos se calculan, no se asumen.
Uso: python tools/auditoria/inventario_propiedades_veredicto.py
"""
import io, json, sys
from collections import Counter
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = Path(__file__).resolve().parents[2] / 'web' / 'data'

def carga(rel):
    p = W / rel
    if not p.exists():
        print(f'## {rel}: NO EXISTE'); return None
    return json.loads(p.read_text(encoding='utf-8'))

def fc(rel, campos, valores=()):
    d = carga(rel)
    if d is None: return None
    fs = d.get('features', [])
    print(f'## {rel}: {len(fs)} features · procedencia={json.dumps(d.get("procedencia"), ensure_ascii=False)[:300]}')
    for c in campos:
        falt = sum(1 for f in fs if f.get('properties', {}).get(c) in (None, ''))
        print(f'   {c:26s} ausente/vacío en {falt}/{len(fs)}')
    for c in valores:
        print(f'   valores {c}: {Counter(str(f["properties"].get(c)) for f in fs).most_common(12)}')
    return d

fc('puntos-criticos-inundacion.geojson',
   ['nivel','comuna','causa','fuente','anio','cronico','responsable','sector','temporadas_registrado'],
   ['nivel','comuna'])
ar = fc('areas-riesgo-inundacion.geojson',
   ['clasificacion','comuna','zona','usos_prohibidos','ordenanza_url','fuente','anio','tipo_hidrico','estado_tramite','eae_fecha_ingreso'],
   ['tipo_hidrico','comuna','estado_tramite','anio','fuente'])
lam = fc('laminas/vectorizadas.geojson',
   ['fuente','anio','comuna','estado_tramite','clasificacion','tipo_hidrico','rmse_loo_m','aptitud'],
   ['comuna','estado_tramite','aptitud','anio','fuente'])
if lam:
    print('   claves de properties del 1er feature:', sorted(lam['features'][0]['properties'].keys()))
fc('campamentos-inundacion.geojson', ['nombre','hogares','comuna','tipo_riesgo','fuente','anio'], ['tipo_riesgo','anio'])
fc('jrc/rp100.geojson', ['fuente','anio'], [])
fc('gore/amenaza-inundacion.geojson', ['clase','fuente','anio'], ['clase'])
fc('sar/huella-observada.geojson', ['fecha_observacion','evento','hectareas','track','fuente','anio','fechas_referencia','caida_db','umbral_agua_db'], [])
fc('sar/cobertura-sar.geojson', ['fecha_observacion','fuente','anio'], ['fecha_observacion'])
si = carga('sar/indice.json'); print('## sar/indice.json evento=', json.dumps(si.get('evento'), ensure_ascii=False)[:200], 'resumen=', json.dumps(si.get('resumen'), ensure_ascii=False)[:200])
pl = carga('planos/indice.json')['planos']
print(f'## planos/indice.json: {len(pl)} planos')
for c in ['titulo','estado_tramite','estado_tramite_nota','puntos_control','rmse_loo_m','resolucion_m_px','bounds_wgs84','archivo']:
    print(f'   {c:22s} ausente en {sum(1 for p in pl if p.get(c) in (None, ""))}/{len(pl)}')
print('   estado_tramite:', Counter(p.get('estado_tramite') for p in pl))
ec = carga('estado-comunas.json')['comunas']
print(f'## estado-comunas.json: {len(ec)} comunas')
for c in ['comuna','personas','puntos_inundacion','puntos_cronicos','le_falta','documentos','laminas_localizadas','poligonos_area_riesgo','poligonos_vectorizados_por_nosotros','planos_georreferenciados']:
    print(f'   {c:38s} ausente en {sum(1 for x in ec if x.get(c) is None)}/{len(ec)}')
print('   le_falta no-lista:', sum(1 for x in ec if not isinstance(x.get('le_falta'), list)))
print('   comunas:', sorted(x['comuna'] for x in ec))
for x in ec:
    if x['comuna'] in ('Padre Las Casas','Angol','Collipulli','Temuco'):
        print('   ', json.dumps(x, ensure_ascii=False)[:600])
ic = carga('indice-comunas.json')
print('## indice-comunas.json claves:', list(ic.keys()), '· n comunas', len(ic.get('comunas', [])), '· 1a:', json.dumps(ic['comunas'][0], ensure_ascii=False)[:300])
