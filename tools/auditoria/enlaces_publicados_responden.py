"""¿Los enlaces que el visor y el catálogo le dan a la persona responden?
(1) Si todos estuvieran muertos, ¿fallaría?  Sí: imprime el código HTTP de cada
    uno; un 404/410 se ve.  (2) Si el instrumento estuviera muerto, ¿se vería
    distinto?  Sí: no habría códigos, habría excepción. Control: senapred.cl.
Uso: python tools/auditoria/enlaces_publicados_responden.py
"""
import io, json, random, sys
from pathlib import Path
import requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = Path(__file__).resolve().parents[2] / 'web' / 'data'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) riesgomapas-auditoria'}

def estado(url):
    try:
        r = requests.get(url, headers=UA, timeout=20, stream=True, allow_redirects=True)
        ct = r.headers.get('Content-Type', '')
        r.close()
        return f'{r.status_code} {ct[:40]}'
    except Exception as e:
        return f'ERROR {type(e).__name__}'

print('control senapred.cl ->', estado('https://senapred.cl'))
ar = json.loads((W / 'areas-riesgo-inundacion.geojson').read_text(encoding='utf-8'))
urls = sorted({f['properties'].get('ordenanza_url') for f in ar['features'] if f['properties'].get('ordenanza_url')})
print(f'## ordenanza_url en areas-riesgo: {len(urls)} distintas')
for u in urls: print('  ', estado(u), u[:110])
cat = json.loads((W / 'catalogo-documentos.json').read_text(encoding='utf-8'))
docs = [(c['comuna'], d) for c in cat['comunas'] for d in c['documentos']]
con_lam = [(c, d) for c, d in docs if d.get('laminas')]
random.seed(20260906)
muestra = random.sample(con_lam, min(12, len(con_lam)))
print(f'## catálogo: {len(docs)} documentos, {len(con_lam)} con láminas; muestra de {len(muestra)} con lámina')
for c, d in muestra: print('  ', estado(d['url']), c, '|', d['url'][:100])
hosts = {}
for c, d in docs:
    h = d['url'].split('/')[2] if '://' in d['url'] else d['url'][:30]
    hosts[h] = hosts.get(h, 0) + 1
print('## hosts del catálogo:', hosts)
