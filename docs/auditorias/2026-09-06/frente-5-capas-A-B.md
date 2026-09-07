# Frente 5 — Capa A oficial (MINVU) y Capa B (Sentinel-1), medidas sobre el artefacto

Fecha: 2026-09-06 · Rama: `visor-simple-y-laminas-vectorizadas` · IDs provisionales 501–512.

Regla aplicada: todo lo que afirma algo sobre un artefacto se midió sobre el
artefacto (`data/processed/…`, `web/data/…`), no sobre el código. El código se
leyó sólo para saber qué prometió. Nada de `data/`, `web/`, `scripts/`, `tests/`,
`config/` fue modificado. La carpeta `docs/auditorias/2026-09-06/` no existía
(`ls` inicial: *No such file or directory*); se creó sólo para este archivo.

## Instrumentos (en `tools/auditoria/`, commiteables hoy)

| Instrumento | Qué mide | (1) Si el fenómeno estuviera roto, ¿falla? | (2) Si el instrumento estuviera muerto, ¿se ve distinto? |
|---|---|---|---|
| `capa_a_duplicados_y_filtro.py` | IoU entre pares, filtro hídrico, años, validez, sobre los 124 y los 63 | Sí: IoU sobre geometría, vocabulario hídrico independiente de `TIPO_HIDRICO`, `shapely.is_valid` | Sí: controles positivos (par idéntico → IoU 1,000; par desplazado → 0,333; «pajarita» → inválida) fallan y sale con código 2 |
| `capa_b_donde_caen.py` | Altitud, pendiente y distancia al mar de cada polígono de la huella, muestreando **todos** los píxeles interiores del DEM; enriquecimiento SENAPRED | Sí: un polígono sintético en el Llaima y otro en el mar se meten al mismo flujo y se exige contarlos | Sí: `CONTROL FALLÓ` + código 2; un control negativo (huella corrida 20 km) debe dar ≈ ×1 |
| `capa_b_ray_casting_vs_shapely.py` | Si los polígonos SAR inválidos hacen que el punto-en-polígono del visor responda al revés | Sí: compara el `dentroAnillo` de `web/app.js:145-153` portado literal contra `make_valid().contains()` en 377.052 puntos | Sí: control con pajarita (dentro en cada lóbulo, fuera en (0,9, 0,05)); la primera versión del control estaba mal (probaba el nudo, que es borde) y se corrigió |

Salidas crudas de cada corrida: pegadas abajo, sección por sección.

---

## PARTE 1 — Capa A oficial

Universo `data/processed/areas_riesgo_prc_araucania.geojson`: 124 polígonos.
Publicado `web/data/areas-riesgo-inundacion.geojson`: 63. Controles: OK.

```
controles positivos: IoU idéntico=1.000  IoU desplazado=0.333  pajarita válida=False  → OK
universo: 124 · publicados: 63
```

### P1 — ¿Por qué Collipulli tiene 36 de 63?

**Respuesta: son 35 geometrías distintas más 1 duplicado exacto.** Collipulli
es la única comuna cuyo PRC (2009) zonificó la amenaza hídrica polígono por
polígono y pequeño (mediana ~2 ha): 27 vienen del servicio nacional (25
`INUNDACION` + 2 `ANEGAMIENTO`) y 9 del regional `PRC Riesgo Collipulli` (8
`ZR-5 Franja de Restricción por Quebradas` + 1 `ZR-2`). No es inflación por
duplicación masiva: en 36 polígonos hay **un** par con IoU 1,000.

```
publicados por comuna: {'Collipulli': 36, 'Carahue': 9, 'Pitrufquén': 4, 'Toltén': 4, 'Loncoche': 2, 'Villarrica': 2, 'Temuco': 1, 'Nueva Imperial': 1, 'Saavedra': 1, 'Renaico': 1, 'Traiguén': 1, 'Gorbea': 1}

IoU > 0,5 entre pares publicados (todas las comunas):
  IoU=1.000  #20 Collipulli | PRC nacional | ZR-2 | ZR-2 Área de Riesgo por Inundación   <->   #62 PRC Riesgo Collipulli | ZR-2 | ZR-2 Área de Riesgo por Inundación

solapes parciales con intersección > 10 % del menor (todas las comunas):
  60.2% del menor  #18 Collipulli ZR-5 (2.0 ha, PRC Riesgo Collipulli)  <->  #32 ZR-2 (1.1 ha, PRC nacional)
  100.0% del menor  #20 Collipulli ZR-2 (10.2 ha, PRC nacional)  <->  #62 ZR-2 (10.2 ha, PRC Riesgo Collipulli)
  11.6% del menor  #23 Collipulli ZR-2 (2.1 ha, PRC nacional)  <->  #24 ZR-1 (2.7 ha, PRC nacional)
  100.0% del menor  #53 Toltén AR-1 (19.9 ha, PRC nacional)  <->  #54 AR-3 (68.7 ha, PRC nacional)
  100.0% del menor  #54 Toltén AR-3 (68.7 ha, PRC nacional)  <->  #55 AR-2 (0.2 ha, PRC nacional)
  total pares con solape parcial: 5

  origen_capa: {'PRC Riesgo Collipulli': 9, 'PRC nacional': 27}
  zona: {'ZR-5': 8, 'ZR-2': 26, 'ZR-1': 2}
  clasificacion: {'ZR-5 Área y/o Franja de Restricción por Quebradas': 8, 'INUNDACION': 25, 'ANEGAMIENTO': 2, 'ZR-2 Área de Riesgo por Inundación': 1}
  área total Collipulli publicada: 122.4 ha
  geometrías byte-idénticas repetidas: 0
  en el universo Collipulli tiene 66; por origen×es_inundacion: {('PRC nacional', False): 24, ('PRC Riesgo Collipulli', True): 9, ('PRC nacional', True): 27, ('PRC Riesgo Collipulli', False): 6}
```

Por qué el deduplicador de `scripts/06_areas_riesgo_prc.py:202-236` no atrapó
el par #20/#62: la clave es `(comuna, centroide redondeado a 5 decimales, nº de
vértices)`. Los dos tienen 229 vértices, pero el anillo empieza en un vértice
distinto y el centroide por promedio de vértices redondea distinto en el 5º
decimal:

```
20 Polygon nvert 229 centroide -72.42995 -37.94556 primer [-72.4312524849546, -37.9432403843605] ...
62 Polygon nvert 229 centroide -72.42994 -37.94559 primer [-72.4297186256007, -37.948072946114] ...
```

En el universo de 124, con IoU > 0,9 el único par es ese mismo (#58/#118):

```
pares IoU>0,9 en el universo de 124 (nacional vs regional):
  IoU=1.000 #58 Collipulli ZR-2 [PRC nacional] cls=INUNDACION inund=True  <->  #118 ZR-2 [PRC Riesgo Collipulli] cls=ZR-2 Área de Riesgo por Inunda inund=True
```

### P2 — ¿El filtro conservó y descartó las clases correctas?

Tabla cruzada sobre los 124:

```
    52  es_inund=False  tipo=None            REMOSION EN MASA
    48  es_inund=True   tipo=fluvial         INUNDACION
     8  es_inund=True   tipo=fluvial         ZR-5 Área y/o Franja de Restricción por Quebradas
     3  es_inund=True   tipo=anegamiento     ANEGAMIENTO
     3  es_inund=False  tipo=None            ZR-3 Área en torno a Canales
     3  es_inund=False  tipo=None            ZR-6 Área de Resguardo Línea de Alta Tensión
     2  es_inund=True   tipo=litoral         INUNDACION LITORAL
     1  es_inund=True   tipo=napa_freatica   AFLORAMIENTO NAPAS FREATICAS
     1  es_inund=False  tipo=None            ANTROPICO
     1  es_inund=False  tipo=None            PENDIENTES
     1  es_inund=False  tipo=None            PENDIENTES/REMOSION EN MASA
     1  es_inund=True   tipo=fluvial         ZR-2 Área de Riesgo por Inundación
```

Descartados (61): 57 sin vocabulario hídrico (52 remoción en masa, 2
pendientes, 1 antrópico, 3 línea de alta tensión — lista completa en la salida
del instrumento) y **4 con vocabulario hídrico**:

```
  Collipulli       ZR-5     ZR-5 Área y/o Franja de Restricción por Quebradas  | REMOSION EN MASA | ['QUEBRAD']
  Collipulli       ZR-3     ZR-3 Área en torno a Canales                       | ZR-3 Área en torno a Canales | ['CANAL']
  Collipulli       ZR-3     ZR-3 Área en torno a Canales                       | ZR-3 Área en torno a Canales | ['CANAL']
  Collipulli       ZR-3     ZR-3 Área en torno a Canales                       | ZR-3 Área en torno a Canales | ['CANAL']
  → 4 descartados con vocabulario hídrico
Publicados SIN vocabulario hídrico (entraron sin serlo):
  → 0
tipo_hidrico entre los 63 publicados: {'anegamiento': 3, 'fluvial': 57, 'litoral': 2, 'napa_freatica': 1}
es_inundacion entre los 63 publicados: {True: 63}
geometrías es_inundacion en universo: 63 · publicadas: 63 · sólo en universo: 0 · sólo en publicado: 0
```

Lectura: ningún polígono entró sin ser hídrico; `tipo_hidrico` no tiene `null`
(REGLAS §1.4 se cumple en el dato: 57 fluvial / 3 anegamiento / 2 litoral / 1
napa). Los cuatro descartados con vocabulario hídrico son dos problemas
distintos, ver hallazgos 501 y 510. El ZR-5 nacional descartado (0,91 ha,
`REMOSION EN MASA`) **no intersecta** ninguno de los 8 ZR-5 regionales
publicados como `fluvial`: es un noveno polígono de la misma zona del plan,
clasificado al revés que sus ocho hermanos.

```
ZR-5 nacional: [(114, 0.91, False)]
ZR-5 regional: [(48, 2.0), (63, 1.02), (71, 0.95), (75, 4.99), (88, 0.96), (89, 4.03), (90, 1.49), (100, 4.97)]
(sin intersecciones)
```

### P3 — Los 5 polígonos sin año

```
universo: 5 sin año
  comuna='Loncoche' comuna_fuente=None anio='no declarado por la fuente' anio_fuente=None zona=ZR-2B ... es_inund=True origen=PRC nacional
  comuna='Loncoche' comuna_fuente=None anio='no declarado por la fuente' anio_fuente=None zona=ZR-2A ... es_inund=True origen=PRC nacional
  comuna='Nueva Imperial' comuna_fuente=None anio='no declarado por la fuente' anio_fuente=None zona=ZR-1 ... es_inund=True origen=PRC nacional
  comuna='Pucón' comuna_fuente=None anio='no declarado por la fuente' anio_fuente=None zona=ZR-6 ... es_inund=False origen=PRC nacional
  comuna='Saavedra' comuna_fuente='Puerto Saavedra' anio='no declarado por la fuente' anio_fuente=None zona=Inundable restringida nombre=Sin información es_inund=True origen=PRC nacional
publicados: 4 sin año   (los mismos menos Pucón)
anio_fuente en universo: {'Atlas del Riesgo de Desastre, ': 119, 'None': 5}
```

Los 5 **no** vienen del Atlas de CIGIDEN (`anio_fuente=None`); los 119 con año
sí (todos del Atlas: MINVU no publica año en ninguno). Loncoche, Nueva Imperial
y Pucón no están en `config/araucania.yaml:229-241`. **Saavedra sí está**, como
`"Puerto Saavedra": 1964` (`config/araucania.yaml:235`), pero el script
renombra la comuna a «Saavedra» (`config/araucania.yaml:263`
`"Puerto Saavedra": "Saavedra"`, aplicado en `scripts/06_areas_riesgo_prc.py:317`)
**antes** de buscar el año con el nombre corregido
(`scripts/06_areas_riesgo_prc.py:345`). Hallazgo 504.

### P4 — Validez geométrica de los 63 publicados

```
inválidos: 0
área < 100 m²: 0 []
exteriores en sentido horario (RFC 7946 pide antihorario): 63 polígonos
huecos en sentido antihorario (RFC 7946 pide horario): 2 polígonos
total anillos interiores en publicados: 2
áreas ha: min=0.173 p50=3.35 max=1596.6 suma=2171.3
inválidos en universo (124): 1
  #1 Temuco ARP es_inund=False: Ring Self-intersection[-72.5049378170171 -38.6620175593733]
```

El visor sí evalúa huecos (`web/app.js:164-165`:
`dentroAnillo(lon, lat, poli[0]) && !poli.slice(1).some(...)`), y el
ray-casting even-odd es indiferente a la orientación, así que la orientación
invertida no cambia respuestas (hallazgo 511, cosmético).

---

## PARTE 2 — Capa B (huella Sentinel-1)

Artefactos: `web/data/sar/huella-observada.geojson` (1.075 polígonos),
`cobertura-sar.geojson` (115), `indice.json`; DEM
`data/processed/sar/2026-07-30_sistema_frontal/terreno.tif` (2 bandas: elevación
y pendiente, 6223×5112 px, EPSG:4326, sin NaN). Umbrales del script
(`config/araucania.yaml` bloque `sar`, `indice.json.procedencia.metodo`):
pendiente ≤ 5°, altura entre 0,5 y 1.200 m.

Máscara de mar usada para «distancia a la costa»: píxeles del DEM a exactamente
0 m y al oeste de −72,5° (2.941.665 px). Control: Temuco queda a 55,7 km del
mar (esperable ~55–70 km).

```
terreno.tif 6223×5112 px · 39.2×50.1 m/px · elev nan=0
píxeles de mar (0 m exacto y lon < −72,5°): 2,941,665
control: distancia al mar en Temuco (−72,60 −38,74) = 55.7 km (esperado ~60-70 km)
huella publicada: 1075 polígonos; por track: {'83D': 350, '156D': 298, '164A': 427}
píxeles rasterizados con algún polígono: 29,809
polígonos sin píxel ni centroide dentro del DEM (SIN DATO): 0
controles positivos: Llaima alt_med=2584 m (>1200 → contado), mar alt_med=0.0 m dist=0 m → OK
```

### Dónde caen las detecciones, por órbita

```
track     n       ha | alt p5/p50/p95 (m) | pend p50/p95 (°) | dist mar p5/p50 (km) | %área>1000m %área>1200m %área<0,5m %área<1km mar %área pend>5°
156D    298   1537.8 |      1/    25/    90 |   0.3/  2.1 |    0.3/  38.8 |     0.00      0.00      0.00      12.00       0.00
164A    427   2620.1 |      1/    22/   135 |   0.4/  2.3 |    0.2/  30.7 |     0.00      0.00      0.00      18.11       0.00
83D     350   1621.1 |      4/   133/   728 |   0.3/  2.7 |    2.1/  69.3 |     1.62      0.00      0.00       1.98       0.00
TODOS  1075   5779.0 |      1/    37/   324 |   0.3/  2.5 |    0.3/  40.5 |     0.46      0.00      0.00      11.96       0.00

  alt_med > 1200 m                       0 polígonos        0.0 ha  tracks={}
  alt_med > 1000 m                      13 polígonos       26.3 ha  tracks={'83D': 13}
      #233 83D 4.7 ha alt=1036m pend=0.8° mar=176.5km (-71.1184,-39.1272)
      #230 83D 3.1 ha alt=1036m pend=0.9° mar=176.5km (-71.1207,-39.1242)
      #225 83D 2.5 ha alt=1042m pend=3.6° mar=175.1km (-71.1369,-39.1226)
      #41 83D 2.2 ha alt=1182m pend=3.9° mar=156.6km (-71.5148,-38.2956)
      #113 83D 2.0 ha alt=1116m pend=0.6° mar=141.2km (-71.6179,-38.6361)
      #142 83D 2.0 ha alt=1150m pend=0.0° mar=178.6km (-71.1305,-38.8989)
  alt_max > 1200 m (algún píxel)         0 polígonos        0.0 ha  tracks={}
  alt_med < 0,5 m                        0 polígonos        0.0 ha  tracks={}
  alt_min <= 0 m (algún píxel)           0 polígonos        0.0 ha  tracks={}
  dist al mar < 1 km                   142 polígonos      691.2 ha  tracks={'83D': 14, '156D': 37, '164A': 91}
      #958 164A 96.4 ha alt=1m pend=0.2° mar=0.1km (-73.3493,-38.7179)
      #979 164A 67.0 ha alt=1m pend=0.2° mar=0.2km (-73.3704,-38.7437)
      #614 156D 29.0 ha alt=1m pend=0.4° mar=0.3km (-73.3695,-38.7430)
      #583 156D 22.9 ha alt=1m pend=0.4° mar=0.1km (-73.3531,-38.7159)
      #589 156D 20.8 ha alt=1m pend=0.2° mar=0.5km (-73.3457,-38.7189)
      #978 164A 16.1 ha alt=1m pend=0.1° mar=0.2km (-73.3473,-38.7435)
  pend_med > 5°                          0 polígonos        0.0 ha  tracks={}
  pend_max > 5° (algún píxel)            0 polígonos        0.0 ha  tracks={}
  muestreado sólo en centroide           7 polígonos       12.5 ha  tracks={'156D': 7}
```

**La máscara de terreno sí llegó al artefacto publicado**: ningún píxel interior
de ningún polígono supera 1.200 m ni 5° ni baja de 0,5 m, y los controles
sintéticos demuestran que el instrumento los habría contado. Nota de
instrumento: los «7 muestreados sólo en centroide» no son defecto del dato:
`rasterize` sobrescribe con el último polígono, y esos 7 de 156D están
completamente cubiertos por polígonos de 164A (es el solape entre órbitas del
hallazgo 505); el fallback al centroide los midió igual.

Separando el océano abierto (componente de 0 m conectada al borde oeste del
DEM) de lagunas costeras a 0 m:

```
componentes de 0 m: 369; océano (tocan borde oeste): 1 comp, 2,939,256 px; lagunas/estuarios a 0 m no conectados: 2,409 px
huella a <1 km del OCÉANO abierto: 118 polígonos, 657.9 ha (11.4% del área); a <1 km de laguna/estuario a 0 m (y no del océano): 62.0 ha (1.1%)
  #958 164A 96.4 ha  dist océano=0 m  (-73.3493,-38.7179)
  #979 164A 67.0 ha  dist océano=0 m  (-73.3704,-38.7437)
  #614 156D 29.0 ha  dist océano=128 m  (-73.3695,-38.7430)
  #583 156D 22.9 ha  dist océano=0 m  (-73.3531,-38.7159)
```

Esas coordenadas (−73,35, −38,72 / −73,37, −38,74) están en la ribera norte del
estuario del río Imperial, entre Puerto Saavedra y Nehuentúe. En el GLO-30 el
estuario está a 0 m y conectado al mar, así que «pegado al océano» ahí significa
«pegado al estuario». Los polígonos están a 1 m (pasan el corte de 0,5 m). Si es
inundación fluvial del Imperial o llanura mareal, **SIN DATO** (hallazgo 507).

### Área por franja de longitud (la prueba de agosto: la nieve caía en −71,4…−71,0)

```
  156D: [-73.6) 24.0%  [-73.2) 69.9%  [-72.8)  5.5%  [-72.4)  0.6%  [-72.0)  0.1%
  164A: [-73.6) 23.4%  [-73.2) 67.5%  [-72.8)  7.7%  [-72.4)  0.6%  [-72.0)  0.9%
  83D: [-73.6)  0.5%  [-73.2) 38.6%  [-72.8)  6.2%  [-72.4) 29.5%  [-72.0) 13.9%  [-71.6) 10.1%  [-71.2)  1.2%
```

La franja cordillerana −71,2…−70,8 tiene 1,2 % del área de 83D y 0 % de las
otras dos; el 74,7 % de agosto no está. 83D es la única órbita que mira el
interior; 156D y 164A son casi enteramente la depresión costera (Imperial,
Cholchol, Carahue).

### Los 10 polígonos más grandes

Comuna = la del punto SENAPRED más cercano (no hay límites comunales en disco;
el censo son manzanas): **aproximada**, con la distancia al punto al lado.

```
  # 863 164A   110.6 ha  alt p50=   21 m (min 15 / max 25)  pend p50=0.4°  mar= 34.5 km  (-72.8878,-38.5384)  comuna≈CHOL CHOL (punto a 2.4 km)
  # 958 164A    96.4 ha  alt p50=    1 m (min 1 / max 2)  pend p50=0.2°  mar=  0.1 km  (-73.3493,-38.7179)  comuna≈CARAHUE (punto a 1.5 km)
  # 951 164A    91.5 ha  alt p50=    4 m (min 2 / max 6)  pend p50=0.3°  mar=  8.9 km  (-73.1250,-38.7182)  comuna≈CARAHUE (punto a 0.2 km)
  #  92 83D    77.8 ha  alt p50=   28 m (min 19 / max 34)  pend p50=0.9°  mar= 34.7 km  (-72.8868,-38.5414)  comuna≈CHOL CHOL (punto a 2.9 km)
  # 799 164A    71.9 ha  alt p50=   55 m (min 53 / max 57)  pend p50=0.2°  mar= 46.9 km  (-72.9007,-38.1271)  comuna≈LUMACO (punto a 1.0 km)
  #  34 83D    69.8 ha  alt p50=  724 m (min 715 / max 743)  pend p50=1.5°  mar=158.9 km  (-71.5326,-38.1683)  comuna≈CURACAUTÍN (punto a 18.5 km)
  # 317 83D    68.2 ha  alt p50=  213 m (min 213 / max 213)  pend p50=0.0°  mar= 98.2 km  (-72.0134,-39.2732)  comuna≈PUCÓN (punto a 2.4 km)
  # 979 164A    67.0 ha  alt p50=    1 m (min 1 / max 3)  pend p50=0.2°  mar=  0.2 km  (-73.3704,-38.7437)  comuna≈SAAVEDRA (punto a 1.6 km)
  # 428 156D    62.5 ha  alt p50=   65 m (min 64 / max 67)  pend p50=0.2°  mar= 42.0 km  (-72.9663,-38.0344)  comuna≈PURÉN (punto a 1.6 km)
  # 550 156D    62.4 ha  alt p50=   21 m (min 15 / max 23)  pend p50=0.5°  mar= 34.5 km  (-72.8900,-38.5388)  comuna≈CHOL CHOL (punto a 2.6 km)
```

#863, #92 y #550 son **la misma mancha de Cholchol vista por las tres órbitas**
(mismo centroide a ±300 m). #317 a 213 m con p50=min=max es un cuerpo de agua
plano (lago Villarrica está a 213 m): agua nueva sobre la orilla de un lago que
subió, plausible. #34 (70 ha a 724 m, pendiente 1,5°, a 18,5 km del punto
SENAPRED más cercano) es lo único de esta lista que podría ser nieve húmeda o
una vega andina: **SIN DATO** (hallazgo 508).

### Consistencia índice ↔ archivo

```
indice 83D: poligonos=350 km2=16.21  |  archivo: n=350 km2=16.21
indice 156D: poligonos=298 km2=15.37  |  archivo: n=298 km2=15.38
indice 164A: poligonos=427 km2=26.18  |  archivo: n=427 km2=26.20
hectareas declarada vs medida (UTM19): desvío relativo p50=0.1% max=0.6%; suma declarada=5776.4 suma medida=5779.0
área mínima publicada: 0.982 ha (min_pixeles_agrupados=5 → ≈ 0.98 ha)
```

### Solape entre órbitas y validez

```
solape entre órbitas: 302 pares, 400 polígonos implicados; suma áreas=5779 ha, unión=5084 ha, doble conteo=695 ha (12.0%)
polígonos cuyo punto representativo cae dentro de N polígonos de la huella: {1: 926, 2: 145, 3: 4}
huella inválidos: 585   (Ring Self-intersection / Interior is disconnected)
cobertura inválidos: 59
huella con anillos interiores: 182
```

Ray-casting del visor contra shapely sobre los 585 inválidos:

```
control pajarita: lóbulo dentro en ambos = True True ; punto fuera de ambos lóbulos (0,9, 0,05) = True True → OK
polígonos inválidos evaluados: 585 · puntos evaluados: 377,052 · desacuerdos visor↔shapely: 0 en 0 polígonos
```

### Reproducción del ×2,8

Lo que el proyecto cita (`README.md:176-187`, `REGLAS.md:46`,
`docs/PROXIMA_SESION.md:130`): 55/371 puntos fluviales de SENAPRED a 300 m
contra 390/7.420 al azar → ×2,8; ×3,0 a 0 m; ×2,0 a 1 km.

Lo que da sobre la **huella publicada** (polígonos, buffer euclídeo en UTM 19S,
azar uniforme dentro de `cobertura-sar.geojson`, semilla 20260809, 20 puntos
de azar por punto observado, igual que el script):

```
es_inundacion=True (data/processed, 1374 pts): 440 puntos, 406 dentro de la cobertura SAR; 8120 al azar
  radio   SENAPRED           azar               enriquecimiento
      0 m     4/406 (  1.0 %)     27/8120 (  0.3 %)  ×2.96
    300 m    15/406 (  3.7 %)    154/8120 (  1.9 %)  ×1.95
   1000 m    52/406 ( 12.8 %)    475/8120 (  5.8 %)  ×2.19

web/data/puntos-criticos-inundacion.geojson (lo que usa el script 14): (idéntico: mismos 440 puntos)
  control negativo (huella desplazada 20 km al este, 300 m): 5/406 vs 88/8120 → ×1.14 (esperado ≈ ×1)
```

**No se reproduce a 300 m: ×1,95, no ×2,8.** Las dos tasas difieren: 3,7 % de
puntos SENAPRED con huella publicada a 300 m contra el 14,8 % citado. Por qué
puede diferir, en orden de peso:

1. **El script no mide lo publicado.** `scripts/14_sar_huella_observada.py:909`
   llama `verificar(agua_union, cobertura_union, rejilla)` con la máscara raster
   cruda acumulada en `:813` (`agua_union |= res["agua"]`), **antes** del filtro
   de 5 píxeles de `vectorizar` (`:566`). Los píxeles detectados suman
   12.651 + 9.734 + 16.513 = 38.898 (`indice.json`), y los publicados
   rasterizan a 29.809: un 23 % de lo detectado son grupos < 5 px que no se
   publican pero sí cuentan en el ×2,8. Un punto crítico es una alcantarilla o
   un puente: justo el tipo de sitio donde el radar deja 2–4 píxeles sueltos.
2. La ventana del script es cuadrada (`_hay_agua_cerca`, `:607-613`,
   `ceil(300/50)=6` filas × `ceil(300/39)=8` columnas → ±300 × ±312 m) contra
   mi círculo de 300 m; afecta a los dos grupos por igual y no explica una
   diferencia de 4×.
3. La cobertura publicada es más gruesa que la raster (bloques con ≥ 25 %
   observado, `:590`): 406 puntos «dentro» contra 371. Eso baja mi tasa
   observada como mucho de 3,7 % a 4,0 %.

A 0 m sí coincide (×2,96 ≈ ×3,0) y el control negativo da ×1,14, así que el
instrumento distingue señal de nada. Hallazgo 503.

---

## HALLAZGOS (peor primero)

### 501 — Ocho polígonos de Collipulli publicados como «inundación fluvial» que MINVU clasifica como remoción en masa
- ARCHIVO:LÍNEA: `scripts/06_areas_riesgo_prc.py:78` (`"QUEBRAD": "fluvial"`), `:114-115` (precedencia `CLASIFICACION_RIESGOS` > `NOMBRE`); dato: `web/data/areas-riesgo-inundacion.geojson` #18, #25, #28, #29, #42, #43, #44, #51.
- QUÉ PASA: la zona ZR-5 «Área y/o Franja de Restricción por Quebradas» del PRC de Collipulli existe 9 veces en el universo. Las 8 del servicio regional (sin campo de clasificación) se clasificaron por el nombre → `fluvial` y se publican; la novena, del servicio nacional, trae `CLASIFICACION_RIESGOS = REMOSION EN MASA` y se descarta. La misma zona del mismo plan dice dos cosas según de qué servidor vino.
- CÓMO SE VE: en 8 franjas de quebrada de Collipulli (19,4 ha en total) el visor dice «área de riesgo declarada» con fenómeno «fluvial», cuando el clasificador oficial del MINVU para ZR-5 dice remoción en masa. Una persona lee «se inunda» donde el instrumento habla de derrumbe de ladera de quebrada (o de ambos: no se puede saber desde el dato).
- CÓMO REPRODUCIRLO: `python tools/auditoria/capa_a_duplicados_y_filtro.py` → sección P2 y bloque «ZR-5 nacional / regional».
- SALIDA CRUDA: `8 es_inund=True tipo=fluvial ZR-5 Área y/o Franja de Restricción por Quebradas` y `Collipulli ZR-5 ... | REMOSION EN MASA | ['QUEBRAD']` (descartado); `ZR-5 nacional: [(114, 0.91, False)]`, sin intersección con los 8 regionales.
- CONFIANZA: CONFIRMADO la inconsistencia. SOSPECHA cuál de las dos clasificaciones es la correcta para ZR-5 (haría falta la ordenanza del PRC Collipulli 2009, que el enlace `ordenanza_url` no entrega: 410).
- GRAVEDAD: 3.

### 502 — Duplicado exacto en Collipulli: el visor dice «cae dentro de 2 áreas» donde hay una
- ARCHIVO:LÍNEA: `scripts/06_areas_riesgo_prc.py:218` (clave `(comuna, centroide 5 decimales, nº vértices)`), `:193-199` (`centroide` por promedio de vértices); dato: `web/data/areas-riesgo-inundacion.geojson` #20 y #62; efecto en `web/app.js:679-680`.
- QUÉ PASA: #20 (PRC nacional) y #62 (PRC Riesgo Collipulli) son el mismo polígono ZR-2 de 10,22 ha (IoU 1,000). Los 229 vértices son los mismos pero el anillo empieza en otro vértice y el centroide redondea distinto en el 5º decimal (−37,94556 vs −37,94559, ~3 m), así que la clave exacta no los junta. El docstring de `deduplicar` promete exactamente lo contrario («La geometría es idéntica entre capas, así que no hace falta tolerancia», `:210`).
- CÓMO SE VE: para cualquier punto dentro de esas 10 ha, el visor escribe «Este punto cae dentro de **2** áreas de riesgo declaradas» y lista dos ZR-2 iguales; el relleno translúcido se dibuja doble y parece más severo. Es el síntoma que el propio script dice evitar (`:204-207`).
- CÓMO REPRODUCIRLO: instrumento de 501, sección P1, «IoU > 0,5».
- SALIDA CRUDA: `IoU=1.000  #20 Collipulli | PRC nacional | ZR-2 ... <-> #62 PRC Riesgo Collipulli | ZR-2`; centroides arriba.
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 3.

### 503 — El ×2,8 de verificación no se mide sobre la capa publicada; sobre ella da ×1,95
- ARCHIVO:LÍNEA: `scripts/14_sar_huella_observada.py:909` (`verificar(agua_union, ...)`), `:813` (`agua_union |= res["agua"]`, máscara previa a `vectorizar`), `:566` (filtro `area < area_min_m2` sólo al vectorizar); citas: `README.md:176-187`, `REGLAS.md:46`, `docs/PROXIMA_SESION.md:130`.
- QUÉ PASA: la cifra que respalda públicamente la capa B se calculó sobre la máscara raster con los grupos < 5 px incluidos (23 % de los píxeles detectados), no sobre `huella-observada.geojson`. Sobre lo que ve una persona, a 300 m es ×1,95 (15/406 vs 154/8.120), no ×2,8 (55/371 vs 390/7.420).
- CÓMO SE VE: el README dice «×2,8, ~8 σ» de una capa que, tal como se publica, da ×2. No cambia lo que el visor dibuja; cambia cuánto se puede confiar en él, y ése es el número que el proyecto usa para justificar la capa entera.
- CÓMO REPRODUCIRLO: `python tools/auditoria/capa_b_donde_caen.py` → sección «Enriquecimiento».
- SALIDA CRUDA: tabla de arriba; control negativo ×1,14.
- CONFIANZA: CONFIRMADO que el script mide la máscara y no el artefacto (líneas leídas) y CONFIRMADO el ×1,95 sobre el artefacto. SOSPECHA que la diferencia se deba enteramente a los grupos < 5 px: no reconstruí la máscara raster (habría que correr el script, que descarga escenas).
- GRAVEDAD: 3.

### 504 — «Puerto Saavedra» tiene año en la config y el polígono publicado sale «no declarado»
- ARCHIVO:LÍNEA: `scripts/06_areas_riesgo_prc.py:317` (renombra a «Saavedra») y `:345` (busca el año con el nombre ya renombrado); `config/araucania.yaml:235` (`"Puerto Saavedra": 1964`) y `:263` (`"Puerto Saavedra": "Saavedra"`); dato: `web/data/areas-riesgo-inundacion.geojson`, único polígono con `comuna='Saavedra'`.
- QUÉ PASA: el diccionario de años está indexado por el nombre que trae la fuente y la búsqueda se hace con el nombre canónico. El año 1964 (reconstrucción post-terremoto 1960, el plan más viejo de la región) está en la config y nunca llega al dato.
- CÓMO SE VE: quien consulta la zona «Inundable restringida» de Puerto Saavedra no ve que el área de riesgo que rige su terreno la dibujó un plan de hace 62 años, que es justo lo que `:333-336` dice que es «lo más útil de esta capa». Los otros 3 publicados sin año (Loncoche ×2, Nueva Imperial) no están en la config: ése es el hallazgo medio ya conocido de `tests/auditoria_datos.py:194-200`.
- CÓMO REPRODUCIRLO: instrumento de 501, sección P3.
- SALIDA CRUDA: `comuna='Saavedra' comuna_fuente='Puerto Saavedra' anio='no declarado por la fuente' anio_fuente=None`.
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 2.

### 505 — 695 ha (12 %) de la huella se cuentan dos o tres veces entre órbitas; el visor muestra sólo la primera mancha
- ARCHIVO:LÍNEA: `web/data/sar/indice.json` (`"hectareas": 5776.0`, suma por track), `scripts/14_sar_huella_observada.py:893` (`"hectareas": round(area_total * 100, 0)`), `web/app.js:1832` (`haObservadas` desde ese resumen), `web/app.js:745-756` (`res.sar[0]` y su `hectareas`).
- QUÉ PASA: las tres órbitas se solapan (302 pares, 400 polígonos): la unión es 5.084 ha, la suma 5.779. 149 polígonos tienen su punto representativo dentro de 2 o 3 polígonos. El visor, al caer dentro, describe sólo `res.sar[0]` («la mancha que contiene este punto mide X ha»), que depende del orden del archivo.
- CÓMO SE VE: «5.776 hectáreas observadas» en pantalla es 14 % más que el área real con agua. En Cholchol (#863/#92/#550, la misma mancha en tres órbitas) la persona ve una sola fecha y un solo tamaño, y no que el agua se vio el 3 y el 4 de agosto.
- CÓMO REPRODUCIRLO: bloque «solape entre órbitas» de `capa_b_donde_caen.py` (sección extra corrida inline, pegada arriba).
- SALIDA CRUDA: `suma áreas=5779 ha, unión=5084 ha, doble conteo=695 ha (12.0%)`; `{1: 926, 2: 145, 3: 4}`.
- CONFIANZA: CONFIRMADO el doble conteo; SOSPECHA que el visor muestre la cifra 5.776 tal cual (leí la línea que la toma del índice, no la pantalla).
- GRAVEDAD: 2.

### 506 — 585 de 1.075 polígonos de la huella y 59 de 115 de la cobertura son geométricamente inválidos
- ARCHIVO:LÍNEA: `web/data/sar/huella-observada.geojson`, `web/data/sar/cobertura-sar.geojson`; origen: `scripts/14_sar_huella_observada.py:561-562` (`shapes(..., connectivity=8)`: dos píxeles unidos sólo por la esquina producen un anillo que se toca a sí mismo).
- QUÉ PASA: `Ring Self-intersection` / `Interior is disconnected`. **No** invierte la respuesta del visor: el ray-casting portado de `web/app.js:145-153` coincide con `make_valid().contains()` en 377.052 puntos (0 desacuerdos). Sí rompe a quien cargue el GeoJSON en QGIS/PostGIS/shapely para operaciones de solape (`intersection` sobre inválidos lanza `TopologyException`; en mi corrida hubo que usarlos con cuidado).
- CÓMO SE VE: para la persona en el visor, nada medible. Para un municipio o un perito que baje la capa, «geometría inválida» al primer cruce.
- CÓMO REPRODUCIRLO: `python tools/auditoria/capa_b_ray_casting_vs_shapely.py`.
- SALIDA CRUDA: `huella inválidos: 585`, `cobertura inválidos: 59`, `desacuerdos visor↔shapely: 0 en 0 polígonos`.
- CONFIANZA: CONFIRMADO. Cómo los pinta MapLibre (earcut sobre anillos auto-tangentes): SIN DATO.
- GRAVEDAD: 2.

### 507 — 658 ha (11,4 %) de la huella están a 1 m de altitud pegadas al estuario del Imperial; el artefacto no distingue marea de inundación
- ARCHIVO:LÍNEA: `web/data/sar/huella-observada.geojson` #958, #979, #614, #583, #589, #978 y 112 más; `web/data/sar/indice.json` `procedencia.incertidumbre` (no menciona estuario ni marea; habla de nieve, dosel, urbano y viento).
- QUÉ PASA: el corte de 0,5 m descartó el océano abierto (0 polígonos ≤ 0 m), pero la llanura entre Puerto Saavedra y Nehuentúe está a 1 m y a 0–400 m del agua a 0 m del GLO-30. Ahí el radar ve la misma firma si el Imperial se desbordó (evento real de esa semana) o si la marea o el viento cambió la lámina del estuario entre pasadas.
- CÓMO SE VE: el 11 % del área «observada» de la capa está en un sitio donde la capa no puede saber qué vio, y la ficha de incertidumbre no lo dice.
- CÓMO REPRODUCIRLO: bloque «océano abierto vs lagunas» (pegado arriba).
- SALIDA CRUDA: `huella a <1 km del OCÉANO abierto: 118 polígonos, 657.9 ha (11.4% del área)`; todos con `alt=1m`.
- CONFIANZA: CONFIRMADO dónde están y a qué altura. Si es marea o inundación: SIN DATO.
- GRAVEDAD: 2 (SOSPECHA de falso positivo, no probado).

### 508 — 83D: 13 polígonos entre 1.000 y 1.200 m y una mancha de 70 ha a 724 m sin punto SENAPRED en 18 km
- ARCHIVO:LÍNEA: `web/data/sar/huella-observada.geojson` #34 (−71,5326, −38,1683), #233, #230, #225, #41, #113, #142.
- QUÉ PASA: pasan el umbral de 1.200 m (el script lo puso alto a propósito, `scripts/sar.py:225-227`) pero están donde en agosto hay nieve. #34 es plano (1,5°), 715–743 m, y no hay ningún punto crítico a menos de 18,5 km.
- CÓMO SE VE: si es nieve, una persona en el valle alto de Curacautín/Lonquimay lee «el radar detectó agua justo en este punto» sobre un nevado derritiéndose.
- CÓMO REPRODUCIRLO: `capa_b_donde_caen.py`, «alt_med > 1000 m» y «10 más grandes».
- SALIDA CRUDA: `alt_med > 1000 m 13 polígonos 26.3 ha tracks={'83D': 13}`; `#34 83D 69.8 ha alt p50=724 m ... comuna≈CURACAUTÍN (punto a 18.5 km)`.
- CONFIANZA: SOSPECHA. No hay forma de decidirlo con lo que hay en disco.
- GRAVEDAD: 2.

### 509 — Toltén: AR-1 (19,9 ha) y AR-2 (0,2 ha) están 100 % contenidos en AR-3 (68,7 ha)
- ARCHIVO:LÍNEA: `web/data/areas-riesgo-inundacion.geojson` #53, #54, #55.
- QUÉ PASA: anidamiento total. Puede ser legítimo (niveles de restricción distintos dentro de una misma área) o el mismo error de fuente que 502 con otra zona.
- CÓMO SE VE: «cae dentro de 2 áreas de riesgo declaradas» en todo Toltén AR-1 y AR-2.
- SALIDA CRUDA: `100.0% del menor #53 Toltén AR-1 (19.9 ha) <-> #54 AR-3 (68.7 ha)`; `100.0% del menor #54 Toltén AR-3 <-> #55 AR-2 (0.2 ha)`.
- CONFIANZA: CONFIRMADO el anidamiento; SOSPECHA que sea un defecto.
- GRAVEDAD: 1.

### 510 — Tres «ZR-3 Área en torno a Canales» de Collipulli quedaron fuera del filtro hídrico
- ARCHIVO:LÍNEA: `scripts/06_areas_riesgo_prc.py:75-81` (`TIPO_HIDRICO` no tiene «CANAL»); universo, 3 polígonos.
- QUÉ PASA: la faja de resguardo de un canal de riego es un área de riesgo cuyo fenómeno es agua (desborde del canal), y el filtro la trata como no hídrica. Es decisión de criterio, no bug: se lista porque el encargo pide todo lo que tenga vocabulario hídrico y quedó fuera.
- SALIDA CRUDA: `3 es_inund=False tipo=None ZR-3 Área en torno a Canales`.
- CONFIANZA: CONFIRMADO que están fuera; SOSPECHA que deban entrar.
- GRAVEDAD: 1.

### 511 — Orientación de anillos al revés de RFC 7946 en los 63 publicados
- ARCHIVO:LÍNEA: `web/data/areas-riesgo-inundacion.geojson` (63 exteriores horarios, 2 huecos antihorarios); `scripts/06_areas_riesgo_prc.py:293` dice «respetando el signo del área para los huecos» (convención ArcGIS, que es la inversa de GeoJSON).
- QUÉ PASA: sin efecto en el visor (even-odd) ni en shapely; algún consumidor estricto (lectores que usan la orientación para decidir hueco/exterior) lo puede leer al revés.
- SALIDA CRUDA: `exteriores en sentido horario: 63 polígonos`, `huecos en sentido antihorario: 2 polígonos`.
- CONFIANZA: CONFIRMADO. GRAVEDAD: 1.

### 512 — Un polígono inválido en el universo (no publicado)
- ARCHIVO:LÍNEA: `data/processed/areas_riesgo_prc_araucania.geojson` #1, Temuco ARP «Restricción por Pendiente».
- SALIDA CRUDA: `#1 Temuco ARP es_inund=False: Ring Self-intersection[-72.5049378170171 -38.6620175593733]`.
- CONFIANZA: CONFIRMADO. GRAVEDAD: 1 (no llega al visor).

---

## SIN DATO (no medido, no es FALLA ni OK)

- Si ZR-5 de Collipulli es fluvial, remoción o ambos (501): requiere la ordenanza del PRC.
- Si el ×2,8 se recupera exactamente sobre la máscara raster con grupos < 5 px (503): no regeneré la máscara (implica descargar escenas y tocar la caché).
- Si las 658 ha del estuario del Imperial son marea o desborde (507) y si #34 y los 13 polígonos > 1.000 m son nieve (508).
- Cómo pinta MapLibre los 585 polígonos auto-tangentes (506): no se abrió navegador.
- Comuna real de cada polígono SAR: no hay límites comunales en disco; se usó el punto SENAPRED más cercano, con la distancia declarada.
- Si el número «5.776 ha» aparece literalmente en pantalla (505): leí `web/app.js:1832`, no la página renderizada.

## VERIFICADO LIMPIO

- **La máscara de terreno sí se aplicó al artefacto publicado.** 0 de 1.075 polígonos con algún píxel > 1.200 m, 0 con pendiente > 5°, 0 con algún píxel ≤ 0 m ni mediana < 0,5 m; el 74,7 % cordillerano de agosto no está (1,2 % del área de 83D en −71,2…−70,8; 0 % en 156D/164A). Controles sintéticos Llaima (2.584 m) y mar (0 m, 0 m de distancia) contados. `capa_b_donde_caen.py`.
- **El filtro hídrico no dejó entrar nada no hídrico**: 0 publicados sin vocabulario hídrico; `es_inundacion=True` en los 63; `tipo_hidrico` sin `null` (57/3/2/1); el publicado es exactamente el subconjunto `es_inundacion` del universo (0 sólo en uno u otro). Cumple REGLAS §1.4 en el dato.
- **Los 63 publicados son geométricamente válidos**, sin áreas ~0 (mín 0,173 ha), y el visor evalúa huecos (`web/app.js:164-165`).
- **119 de 124 polígonos tienen año, todos atribuidos al Atlas** (`anio_fuente`); ninguno de los 5 sin año se atribuye a una fuente que no lo tenga.
- **Índice ↔ archivo SAR consistentes**: 350/298/427 polígonos y 16,21/15,37/26,18 km² coinciden; `hectareas` declaradas por polígono coinciden con el área medida en UTM 19 (desvío p50 0,1 %, máx 0,6 %); área mínima 0,982 ha = 5 píxeles, como promete la config.
- **Los polígonos SAR inválidos no invierten la respuesta del visor**: 0 desacuerdos en 377.052 puntos entre el `dentroAnillo` portado y shapely. `capa_b_ray_casting_vs_shapely.py`.
- **La huella tiene señal contra SENAPRED**: ×2,96 a 0 m, ×2,19 a 1 km, y el control negativo (huella corrida 20 km) da ×1,14. Lo que está mal es la cifra citada a 300 m, no que la capa no sirva.
- **`terreno.tif` está sano**: sin NaN, 6223×5112, elevación −8 a 3.742 m, pendiente máx 73,8°, mar a 0 m exacto (2,94 M px), Temuco a 55,7 km del mar.
- **Deduplicación nacional/regional**: en el universo de 124 sólo sobrevive el par de 502; los otros duplicados que el script dice haber atrapado (`deduplicar`) no reaparecen (0 pares adicionales con IoU > 0,9).
