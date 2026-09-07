# Auditoría 2026-09-06 — Frente 3: magnitudes, umbrales y unidades

Rama `visor-simple-y-laminas-vectorizadas`, commit `b293aad`. IDs provisionales 301…
Todo número de este informe sale de un comando corrido en esta sesión; la salida
cruda va pegada al lado. Lo que no se midió está marcado SIN DATO.

Nota de método: la carpeta `docs/auditorias/2026-09-06/` **no existía** al empezar
(`ls docs` la omitía); se creó sólo para este archivo. Los instrumentos nuevos
quedaron en `tools/auditoria/` y cada uno lleva en su docstring las dos preguntas
del instrumento y un control positivo (`--control` o aserción interna).

## Instrumentos usados

| Instrumento | Qué mide | Control positivo |
|---|---|---|
| `tools/auditoria/censo_magnitudes.tsv` (ya existía) | 288 constantes en 28 archivos | ya pasado por quien lo escribió |
| `tools/auditoria/sensibilidad_radios_veredicto.py` | cuántos puntos consultados cambian de nivel al moverse 10/25/50 m con la regla de `app.js:333-378` | `--control`: 1 punto grave → alto a 0 m, medio a 305 m, sindato a 2 km, y >0 cambios a 50 m. **PASÓ** |
| `tools/auditoria/distribucion_areas_vs_area_minima.py` | distribución de áreas (reproyectadas a UTM) de los polígonos vectorizados frente a `area_minima_m2` | `--control`: cuadrado de 100×100 m → 9.985 m² (±1 %). **PASÓ** |
| `tools/auditoria/control_alcance_regional_laminas.py` | a partir de qué corrimiento la comprobación de `18:399-405` rechaza una lámina | aserción: corrimiento de 400 km → RECHAZA. **PASÓ** |
| `tools/auditoria/sensibilidad_ancho_minimo_laminas.py` | hectáreas y polígonos por clase variando `ancho_minimo_px`, `tolerancia_color`, `area_minima_m2` sobre la misma imagen del PDF | reproducir con los valores declarados los ha ya publicados. **PASÓ** (Angol 188,0/20,5 ha; Catripulli 93,8/715,3 ha idénticos) |
| `tools/auditoria/loo_por_linea_grilla.py` | RMSE leave-one-out por punto vs por línea de grilla, y el error sistemático que ningún LOO ve | aserción: una línea corrida 3 m sube el LOO por línea de 0,22 a 1,07 m. **PASÓ** |
| `tools/auditoria/coherencia_laminas_vs_gore_senapred.py` | si las láminas aterrizaron donde dice evidencia independiente (GORE 2016, SENAPRED), y cuánto empeora al correrlas | aserción: correr 5 km cambia la coincidencia >10 puntos. **PASÓ** |

Pregunta (1) de cada instrumento — «si el fenómeno estuviera roto, ¿fallaría?» — y
pregunta (2) — «si el instrumento estuviera muerto, ¿se vería distinto?» — están
respondidas en cada docstring; acá se resumen: en todos los casos se produjo el
fenómeno a propósito (punto corrido, línea corrida, mancha corrida, cuadrado
conocido) y la medida lo vio antes de aceptar ningún cero.

---

## 1. Tabla censo — constantes que mandan

Sólo las que deciden algo (las `-8` de `encoding='utf-8'`, `/1024`, `/72.0`,
`28.35` pt/cm y fechas quedan fuera; ver VERIFICADO LIMPIO). «Rango real» es el
que midieron los instrumentos o el que se lee de los datos publicados.

### 1.1 Visor (`web/app.js`, `web/sw.js`)

| archivo:línea | constante | unidad | qué decide | rango real chico / medio / grande | veredicto |
|---|---|---|---|---|---|
| app.js:17 | `RADIOS = {300, 500, 1500}` | metros (haversine, app.js:135-143, R=6.371.000 m) | nivel ALTO/MEDIO/BAJO/SIN DATO | distancia al punto crítico más cercano: 60.000 posiciones de prueba; 14,1 % cambian de nivel con 50 m; 2,9 % con 10 m | ver H-304 |
| app.js:366 | `>= 3` | conteo de puntos a ≤300 m | ALTO sin punto grave | — | OK, coherente con cabecera app.js:6-10 |
| app.js:31 | `bbox [-73.70,-39.65,-70.90,-37.35]` | grados | fuera de alcance | idéntico a `config/araucania.yaml:9` y a `tests/auditoria_datos.py:359` | OK |
| app.js:34 | `margenGrados 0.30` | grados | límites de paneo | no amplía alcance (app.js:37-40 usa bbox pelado) | OK |
| app.js:187 | `ZOOM_MIN_PLANO = 11` | nivel de zoom Leaflet/MapLibre | cargar imagen del plano | — | OK (comentario 183-186 justifica) |
| app.js:188 | `MAX_PLANOS_SIMULTANEOS = 6` | conteo | planos cargados | 23 planos publicados | OK |
| app.js:416 | `Math.round(dmin/100)/10` | m → km con 1 decimal | distancia a la comuna atribuida | — | OK |
| app.js:579 | «500 metros» | texto fijo | frase del porqué | — | H-318 (duplica RADIOS.medio) |
| app.js:780 | `Math.abs(p.caida_db)` | dB (umbral, no medida) | frase «el eco cayó X dB» | caida_db = −3,0 fijo en `araucania.yaml:158` | H-309 |
| app.js:858 | `p.rmse_loo_m` | metros (RMSE LOO del ajuste) | «error de ubicación» del plano | 0,02 … 1,81 m en los 24 planos | H-306 |
| app.js:1323-1332 | `enableHighAccuracy`, `timeout 12000` | ms | geolocalización | `pos.coords.accuracy` no se lee ni se muestra | H-305 |
| app.js:1140, 1160 | `slice(0,4)`, `limit=5` | conteo | sugerencias | — | OK |
| app.js:1247 | `450` | ms | debounce Nominatim | política ≤1 req/s | OK |
| app.js:1502-1504 | 0.72 / −0.35 / −0.08 | adimensional | tono del mapa base en oscuro | — | cosmético, OK |
| sw.js:16 | `VERSION 'riesgomapas-v21'` | — | invalidar cachés | — | no tocado |
| sw.js:82-90 | caché de teselas | bytes | sin tope de tamaño ni de edad | — | H-316 |

### 1.2 Vectorización de láminas (`scripts/18_vectorizar_laminas.py`, `config/laminas.yaml`)

| archivo:línea | constante | unidad | qué decide | rango real | veredicto |
|---|---|---|---|---|---|
| 18:347, 354; laminas.yaml:62, 105 | `tolerancia_color` 45 / 40 | distancia **euclídea** en RGB (`np.linalg.norm(axis=2)`), estricta `<` | píxel pertenece a una clase | Angol: tol 25→138 ha, 45→188, 90→286 (Alto). Catripulli «media»: tol 40→715 ha, 55→730, **70→3.332 ha** | H-303 |
| 18:328, 359-360; laminas.yaml:68, 106 | `ancho_minimo_px` 4 | píxeles de la figura → **31,0 m** en Angol (7,74 m/px), **21,3 m** en Catripulli (5,34 m/px) | borra rasgos más delgados que eso | Angol Alto 214→188 ha (−12 %), Medio 27,7→20,5 (−26 %) entre ancho 0 y 4 | H-302 |
| 18:329, 488; laminas.yaml:70, 107, 156 | `area_minima_m2` 2000 | m² en UTM (después de `transform`, antes de 4326) | descarta polígonos chicos | Angol: 17 de 98 polígonos en [2.000, 3.000) m²; Catripulli 5/39; plano 4/26 | H-311 |
| 18:329 vs 18:488 | omisión 0 vs 2000 | m² | valor si el YAML no lo declara | ambos YAML lo declaran | H-320 |
| 18:123 | `<25`, `<210` | niveles RGB 0-255 | píxel «neutro» (retícula) | — | sólo `--inspeccionar`/`--censo`; OK |
| 18:129-133 | `0.55`, `8`, `14` | fracción del alto/ancho; px; conteo | picos de retícula | — | sólo inspección; OK |
| 18:138, 139 | `.05/.75`, `.05/.62` | fracción de la imagen | franja donde buscar retícula | — | sólo inspección; OK |
| 18:163 | `0.01` | fracción (1 %) entre escala X e Y | aborta si difieren | **no se ejerce**: Angol y Catripulli tienen UNA ancla en Y (laminas.yaml:56, 101) → rama 18:171-179 | H-301 |
| 18:399-405, 523-525; araucania.yaml:9 | bbox regional, **margen 0** | grados | «aterrizó donde vive la comuna» | pasa hasta **20 km** de corrimiento en las 3 láminas; 5 km (un dígito del rótulo Y) PASA | H-301 |
| 18:244; laminas.yaml:152 | `contraste_minimo` 28 | niveles de gris (fondo mediana 21 px − píxel) | marca del achurado | — | SIN DATO (sensibilidad no medida) |
| 18:247-248; laminas.yaml:150-151 | `marca_area [8,45]`, `marca_lado [4,11]` | px² y px a 150 dpi (0,8486 m/px) | tamaño de marca AR-2a | 22.786 marcas detectadas (geojson) | SIN DATO |
| 18:256, 264, 266; laminas.yaml:153-155 | `celda_px` 8, `ventana_celdas` 5, `densidad_minima` 8 | 8 px = **6,8 m**; ventana 5 celdas = **34 m**; 8 marcas por ventana | dónde hay achurado | polígonos con borde cuantizado a 6,8 m y suavizado con kernels de 5×5 celdas (34 m) y 3×3 (20 m) (18:267-268) | H-307 |
| 18:289, 496 | `0.5` | medio píxel / media celda (m) | tolerancia `simplify` | 3,9 m Angol · 2,7 m Catripulli · 3,4 m plano | OK, declarado 18:288 |
| 18:476; laminas.yaml:142 | `rmse_maximo_m` 15 | metros | aborta el plano | RMSE 4,94 m con 3 vértices (2 grados de libertad, 18:473) | H-308 |
| 18:471 | `dpi` omisión 150 | dpi | sólo el log de escala impresa | — | OK |
| 18:609 | `paso < 60` | px | descarta retícula falsa en `--censo` | — | OK |
| 18:653 | `500`, `400` | px | imagen mínima para censo | — | OK |
| laminas.yaml:184-191 | comentario huérfano | — | — | tras «❌ RECHAZADA» sigue un párrafo que presenta la misma lámina como «la única cartografía…» | H-321 |

### 1.3 Georreferenciación por grilla (`scripts/08_georreferenciar_grilla.py`, `scripts/georref.py`)

| archivo:línea | constante | unidad | qué decide | rango real | veredicto |
|---|---|---|---|---|---|
| georref.py:20-21 | `UMBRAL_PREDIAL 10`, `UMBRAL_MANZANA 25` | metros de RMSE LOO | aptitud predial/manzana/contexto | 24 planos: LOO 0,02…1,81 m, todos «predial» | H-306 |
| 08:59 | `DPI 300` | dpi | render → `resolucion_m` | 0,212…0,773 m/px publicados | OK |
| 08:60, 200 | `TOL_PASO 0.02` | fracción del paso **en metros de los rótulos** (no en posición) | «grilla irregular» | Purén rechazado con r²=0,9999998 (`georreferenciacion_grilla.json`) | H-313 SOSPECHA |
| 08:61 | `R2_MIN 0.9999` | adimensional | linealidad | 0,99999998 … 1,0 publicados | OK |
| 08:62, 278 | `TOL_ESCALA 0.01` | fracción entre m/pt X e Y | «escalas distintas» | Vilcún p3 rechazado (0,3448 vs 0,6236) — correcto | OK |
| 08:139, 180 | `TOL_INLIER_M 3.0` | **metros de mapa** contra posiciones en pt | inlier RANSAC | 1 pt = 1,76 m en Traiguén (1:5.000); a 1:20.000 sería 7 m/pt → 3 m < 1 pt | H-314 SOSPECHA |
| 08:137-138 | `RANGO_ESTE (100k,900k)`, `RANGO_NORTE (4M,8M)` | metros UTM | descarta números que no son coordenadas | — | OK |
| 08:127 | `\d{6,7}` | dígitos | agrupar rótulos | — | OK |
| 08:111-116 | `0.5`, `0.8`, `0.9`, `0.6` | fracciones del alto/ancho de glifo (pt) | unir dígitos | — | OK (misma unidad ambos lados) |
| 08:227 | `± 0.3` | grados (~33 km) | huso 18/19 contra bbox | vs. margen **0** en 18:400 | H-315 (inconsistencia) |
| 08:293-304 | producto cartesiano E×N | puntos | 42 «puntos» de 13 mediciones | LOO por punto 0,19 m vs por línea 0,22 m (Traiguén) | OK: no infla (ver §3) |
| georref.py:105 | `MAX_PIXELES_SALIDA 60e6` | px | engruesa resolución | — | OK |

### 1.4 Capa B — SAR (`scripts/14_sar_huella_observada.py`, `scripts/sar.py`, `config/araucania.yaml:137-220`)

| archivo:línea | constante | unidad | qué decide | rango real | veredicto |
|---|---|---|---|---|---|
| araucania.yaml:148; 14:722-724 | `resolucion_grados 0.00045` | grados → 50 m lat × 39 m lon (a −39°) | rejilla de salida | `indice.json` publica `resolucion_m: 50` (14:887 usa sólo latitud) | OK, declarado |
| araucania.yaml:158; sar.py:293 | `caida_db −3.0` | dB (diferencia) | criterio 2 | — | OK; H-309 es cómo lo muestra el visor |
| araucania.yaml:170-173; sar.py:151-176; 14:521-524 | `percentil_agua 50`, `[−22, −13]`, respaldo −16 | dB σ⁰ | umbral de oscuridad | tracks: −20,11 / −21,99 / **−22,0 (crudo −24,34, acotado)** | OK; H-319 (docstring/omisión dicen p90) |
| araucania.yaml:177, 178, 182 | `estabilidad_pre_db 3.5`, `min_pre 3`, `max_pre 4` | dB; conteo de pasadas | criterio 4 y referencia | 4 fechas de referencia en los 3 tracks | OK |
| araucania.yaml:186 | `permanente_db −18.0` | dB | agua permanente | — | OK |
| araucania.yaml:190; 14:740-741 | `min_pixeles_agrupados 5` | píxeles → m² con `area_pixel_m2` a la **latitud media de la rejilla** | speckle | polígono medido a su propia latitud (sar.py:333); diferencia cos(−37,35°)/cos(−39,65°) = 3 % | OK (declarado «≈1 ha») |
| araucania.yaml:209, 210, 220; sar.py:243-249 | pendiente ≤ 5°, altitud ≤ 1.200 m, > 0,5 m | grados; metros | terreno apto | descartados por terreno: 167.529 / 8.216 / 447.443 px | OK |
| sar.py:49, 202-203; 14:642-643, 724, 870, 887 | `111_320` m/grado | m/grado lat; lon corregido por cos(lat) | pendiente, áreas, radios | — | OK: mismo valor en los dos módulos |
| 14:617, 682-683 | `radios_m (0, 300, 1000)` | metros → celdas (`ceil(r/m_por_px)`) | verificación | — | OK (unidad convertida) |
| 14:590 | `(d*d)//4` | fracción de bloque 32×32 | cobertura | — | OK |
| 14:598 | `5e6` | m² (5 km²) | descarta borde de cobertura | — | OK |
| 14:154 | `> 5000` | ítems STAC | corta paginación | — | OK |
| 14:482 | `con_dato < 0.5` | fracción | aborta sin DEM | — | OK |
| sar.py:173 | `< 100` | píxeles | usa respaldo | 40.958…259.249 px reales | OK |
| sar.py:371 | `decimales 6` | grados (~0,1 m) | redondeo | — | OK |

### 1.5 Descargas, paginación y límites (`comun.py`, 01, 06, 13, 15, 19, 05, 07, 12, 03, 20, 02, 17, 10, 11)

| archivo:línea | constante | unidad | qué decide | veredicto |
|---|---|---|---|---|
| comun.py:159, 172-175, 203, 206 | `pagina 2000`, `maxRecordCount`, `exceededTransferLimit`, tope 500.000 | registros | paginación ArcGIS | OK: se acota al tope del servicio, se para por bandera, no por «vino menos» |
| 15:102, 142, 145 | `PAGINA 1000`, `exceededTransferLimit`, tope 60.000 | registros | GORE | OK |
| 15:108 | `DECIMALES 5` | grados (~1 m) | redondeo | OK frente a 35 m/px |
| 01:154 | lon −76…−66, lat −56…−17 | grados | descarta coordenada corrupta | OK (Chile continental) |
| 01:257 | `n >= 3` | temporadas | «crónico» | OK, declarado en app.js |
| 01:51 | `SERIE_REFERENCIA 2026` | año | serie publicada | OK |
| 02:61 | `UMBRAL_M 0.25` | metros de profundidad | píxel JRC inundado | OK |
| 13:45 | claves `INUND/INDUND/ANEGAM/TSUNAMI` | texto | campamento hídrico | OK (incluye anegamiento; distinto criterio que araucania.yaml:84-86) — ver H-317 |
| 05:42-43, 162 | `ID_MAX 700`, `PAUSA 0.35 s`, `vacias >= 25` | ids; s; conteo | rango EAE | OK |
| 07:127-130 | `AREA_PLOTER 1e6 pt²`, `OBJETOS_MIN 200`, `FRAC_IMAGEN 0.18`, `TEXTO_MAX 1500` | pt²; conteo; fracción; caracteres | es lámina | SIN DATO (no medido) |
| 07:292-294 | `--max-mb 80`, `--limite 40` | MB; PDFs | corte de proceso | avisa en log 07:328-329; OK |
| 12:45-48 | `PAUSA 0.7 s`, `PROFUNDIDAD 2`, `MAX_PAGINAS 60`, `TIEMPO_MAX 40 s` | s; niveles; páginas; s | cosecha | OK |
| 03:36, 119, 164 | `DPI 400`, `< 1800` caracteres, `25` candidatas | dpi; chars; conteo | render de láminas | OK (03:165-167 avisa) |
| 20:137 | `m = 0.15` grados | «~15 km» | margen del paquete | 0,15° = 16,7 km lat / 13 km lon: el comentario es aproximado, OK |
| 17:64, 176 | `SITIOS_NACIONALES 252`, horizonte 2035-2065 | conteo; años | control de fuente | OK |
| 10:39-40, 119-124 | `ANCHO_MAX 2600 px`, `900 KB`, alfa 28/120/255 en RGB>240/>215 | px; KB; niveles | PNG del plano | OK, cosmético |
| 11:36, 53, 65, 118 | `ZOOM_MAX 17`, `1.6`, `160` teselas, alfa `0.85` | zoom; factor; conteo; fracción | verificación visual | OK (11:117 «misma opacidad que el visor»: SIN DATO, no comparado con style.css) |

---

## 2. Hallazgos (ordenados por gravedad)

### 301 — La única comprobación que protege un rótulo Y mal tecleado deja pasar corrimientos de hasta 20 km
- ARCHIVO:LÍNEA — `scripts/18_vectorizar_laminas.py:399-405` y `:523-525`; `config/laminas.yaml:14-17`, `:52-56`, `:99-101`; `config/araucania.yaml:9`
- QUÉ PASA — `laminas.yaml:16-17` promete que «una coordenada mal tecleada mueve la mancha cientos de metros y esas dos comprobaciones la cachan». Para Angol-2013 y Catripulli la primera comprobación (escala X vs Y, 18:163) **no se ejecuta** porque el eje Y tiene una sola ancla (rama 18:171-179). Queda sólo la segunda: que la geometría caiga en un bbox de 244 × 256 km con margen cero. Un norte tecleado con un dígito menos (5.815.000 → 5.810.000: 5 km) pasa.
- CÓMO SE VE — la mancha entera de una comuna dibujada kilómetros al norte o al sur de donde la lámina la pone, y el visor diciendo «no cae dentro» a quien sí está dentro (y viceversa), sin ninguna alarma del pipeline.
- CÓMO REPRODUCIRLO — `python tools/auditoria/control_alcance_regional_laminas.py`
- SALIDA CRUDA —
  ```
  [angol-peligro-inundacion-2013] lon -72.740..-72.665 · lat -37.837..-37.779
      5 km: N=PASA  S=PASA  E=PASA  O=PASA
     20 km: N=PASA  S=PASA  E=PASA  O=PASA
     50 km: N=RECHAZA  S=PASA  E=PASA  O=PASA
    → un norte mal tecleado en 5.000 m (un dígito) queda: PASA
  [curarrehue-catripulli-inundacion-2025] ...
     20 km: N=PASA  S=PASA  E=PASA  O=PASA
    → un norte mal tecleado en 5.000 m (un dígito) queda: PASA
  ```
- ¿Está corrida HOY? Se midió con evidencia independiente (`tools/auditoria/coherencia_laminas_vs_gore_senapred.py`): las tres láminas coinciden con el modelo GORE en 72,9 % / 87,6 % / 88,7 % de su área y correrlas 2-5 km lo baja a 0-50 %. No hay indicio de corrimiento grueso; el hallazgo es que **la defensa declarada no existe**, no que el dato esté mal. Matiz: Catripulli corrida +1 km al norte sube a 98,4 % (de 88,7 %) y Angol-2013 corrida +1 km al este queda igual (72,1 %); con un modelo de 35 m eso no alcanza para afirmar un corrimiento de 1 km, pero tampoco lo descarta → SIN DATO a esa escala.
  ```
  [curarrehue-catripulli-inundacion-2025] CURARREHUE · 809 ha
    corrida 0 km (+0,+0): dentro del GORE  88.7 %
    corrida 1 km (+0,+1): dentro del GORE  98.4 %
    corrida 5 km (+0,-5): dentro del GORE   0.0 %
  ```
- CONFIANZA — CONFIRMADO (líneas leídas; instrumento con control positivo)
- GRAVEDAD — 4 (una persona decide mal si el día que alguien reescriba un rótulo nadie lo nota; hoy el dato parece bien ubicado)

### 302 — `ancho_minimo_px: 4` no es un criterio físico: son 31 m en Angol y 21 m en Catripulli, y borra el 26 % de la clase «Medio» de Angol
- ARCHIVO:LÍNEA — `scripts/18_vectorizar_laminas.py:328, 357-360`; `config/laminas.yaml:64-68, 106`
- QUÉ PASA — la apertura morfológica con elipse de 4×4 px elimina cualquier rasgo más angosto que 4 píxeles **de la figura**, y el píxel vale 7,74 m en una lámina y 5,34 m en la otra. Lo que se declara como «sacar la red hídrica» borra también franjas inundables reales de menos de 31 m (una calle con sus dos veredas). Entre ancho 0 y 4 la clase Alto de Angol pierde 26 ha (−12 %) y Medio 7 ha (−26 %); la curva es continua, no hay un valor «natural».
- CÓMO SE VE — una casa en una franja inundable angosta pegada al río recibe «no cae dentro de la lámina», y el borde de toda la mancha entra ~15 m hacia adentro (medio kernel).
- CÓMO REPRODUCIRLO — `python tools/auditoria/sensibilidad_ancho_minimo_laminas.py`
- SALIDA CRUDA —
  ```
  [angol-peligro-inundacion-2013] 1266×1021 px · 7.740 m/px · declarado tol=45 ancho=4px (31.0 m)
   ancho=0 px (  0.0 m): Alto  103 pol    214.1 ha · Medio   43 pol     27.7 ha
   ancho=2 px ( 15.5 m): Alto   93 pol    206.8 ha · Medio   38 pol     25.9 ha
   ancho=4 px ( 31.0 m): Alto   70 pol    188.0 ha · Medio   28 pol     20.5 ha
   ancho=8 px ( 61.9 m): Alto   49 pol    149.4 ha · Medio   11 pol     10.2 ha
  [curarrehue-catripulli-inundacion-2025] 1338×946 px · 5.337 m/px · declarado tol=40 ancho=4px (21.3 m)
   ancho=0 px (  0.0 m): Susceptibilidad alta   10 pol     96.3 ha · Susceptibilidad media   19 pol    724.2 ha
   ancho=4 px ( 21.3 m): Susceptibilidad alta   12 pol     93.8 ha · Susceptibilidad media   27 pol    715.3 ha
  ```
  El metadato publicado dice `descartado_por_grosor_pct: 19.7` (Alto) y `34.6` (Medio) en píxeles (`data/processed/laminas/angol-peligro-inundacion-2013.geojson`, leído con python en esta sesión).
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 4

### 303 — `tolerancia_color` de Catripulli está a 15 unidades de un acantilado: a 70 la clase «media» pasa de 715 a 3.332 ha
- ARCHIVO:LÍNEA — `scripts/18_vectorizar_laminas.py:347-354`; `config/laminas.yaml:104-105`
- QUÉ PASA — la distancia es euclídea en RGB (`np.linalg.norm(a − rgb, axis=2)`, 18:347) y estricta (`dmin < tol`, 18:354). El celeste de «Susceptibilidad media» `[191,231,255]` está cerca de tonos claros del fondo de la lámina: subiendo la tolerancia de 40 a 70 el área se multiplica por 4,7. El valor actual está del lado bueno, pero nada en el pipeline avisa si alguien lo «relaja un poco». En Angol la respuesta es continua (138 → 286 ha entre tol 25 y 90), o sea que el valor 45 también mueve ±25 % de las hectáreas.
- CÓMO SE VE — con un ajuste de 30 unidades el pueblo entero de Catripulli quedaría dentro de «susceptibilidad media».
- CÓMO REPRODUCIRLO — mismo comando que 302
- SALIDA CRUDA —
  ```
   tol= 40: Susceptibilidad alta   12 pol     93.8 ha · Susceptibilidad media   27 pol    715.3 ha
   tol= 55: Susceptibilidad alta    9 pol    101.2 ha · Susceptibilidad media   24 pol    730.2 ha
   tol= 70: Susceptibilidad alta    6 pol    106.5 ha · Susceptibilidad media   25 pol   3331.6 ha
  (Angol) tol= 25: Alto 59 pol 137.9 ha · tol= 45: Alto 70 pol 188.0 ha · tol= 90: Alto 114 pol 285.6 ha
  ```
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 3 (hoy bien; frágil sin guardia)

### 304 — Con la regla de radios, el 14 % de las posiciones cambia de veredicto al moverse 50 m, y el visor no muestra ni usa la precisión del GPS
- ARCHIVO:LÍNEA — `web/app.js:17, 333-378` (regla); `web/app.js:1321-1332` (geolocalización sin `accuracy`)
- QUÉ PASA — `RADIOS` está en metros y `distancia()` es haversine en metros: **no hay mezcla de unidades**. El problema es la magnitud: sobre 60.000 posiciones de prueba a ≤1,7 km de puntos críticos, el 2,9 % cambia de nivel con un corrimiento de 10 m, el 7,0 % con 25 m y el 14,1 % con 50 m. Un geocodificador de calle o un GPS de computador erran eso o más; `getCurrentPosition` entrega `pos.coords.accuracy` y app.js:1323 lo descarta.
- CÓMO SE VE — la misma casa sale «Hay registros de inundación cerca» (MEDIO) o «a cierta distancia» (BAJO) según de qué esquina la ubicó el buscador.
- CÓMO REPRODUCIRLO — `python tools/auditoria/sensibilidad_radios_veredicto.py`
- SALIDA CRUDA —
  ```
  puntos críticos: 440 (279 graves)
  "puntos_prueba": 60000,
  "niveles_base": {"sindato": 6702, "bajo": 41182, "medio": 8501, "alto": 3615},
  "cambia_con_10_m": {"n": 1763, "pct": 2.9, "de_los_no_sindato_pct": 2.7},
  "cambia_con_25_m": {"n": 4212, "pct": 7.0, "de_los_no_sindato_pct": 6.4},
  "cambia_con_50_m": {"n": 8438, "pct": 14.1, "de_los_no_sindato_pct": 12.9},
  "en_franja_25m_de_un_umbral": {"300": 1486, "500": 1829, "1500": 1803}
  ```
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 3 (la regla está bien declarada en app.js:6-10; falta decirle a la persona con cuánto error la ubicaron)

### 305 — (fusionado en 304) `pos.coords.accuracy` ignorado
- Se deja el ID reservado; el verificador decide si va aparte. ARCHIVO:LÍNEA `web/app.js:1323`. CONFIRMADO (línea leída). GRAVEDAD 3.

### 306 — «error de ubicación 0,19 m» es la precisión del ajuste, no la exactitud del plano; un corrimiento de 1 pt en todos los rótulos vale 1,77 m y ningún LOO lo ve
- ARCHIVO:LÍNEA — `web/app.js:857-858`, `web/catalogo.js:46`; `scripts/georref.py:20-21, 49-54, 76-87`; `scripts/08_georreferenciar_grilla.py:293-304`
- QUÉ PASA — el número que ve la persona es el RMSE leave-one-out del ajuste afín sobre las posiciones de los rótulos de la grilla (0,02…1,81 m en los 24 planos). Mide qué tan recta es la grilla del PDF, no dónde está el dibujo respecto del terreno: el trazado del plano a 1:5.000 tiene su propio error (0,2 mm de papel = 1 m) y un corrimiento común de los rótulos respecto de sus líneas es invisible para el LOO. Se verificó además que el producto cartesiano de 08:293-304 **no infla** el LOO (por punto 0,19 m vs por línea 0,22 m), así que el número es honesto para lo que mide; lo que está mal es cómo se presenta.
- CÓMO SE VE — «error de ubicación 0.19 m» al lado de un plano de anteproyecto; una persona lee que el borde de la zona de riesgo está bien a 20 cm.
- CÓMO REPRODUCIRLO — `python tools/auditoria/loo_por_linea_grilla.py "data/raw/eae/traiguen/04_Anteproyecto-Plano_Actualizacion_PRC_Traiguén.pdf.pdf" 1`
- SALIDA CRUDA —
  ```
  7 líneas E × 6 líneas N = 42 «puntos» (mediciones independientes: 13)
  escala: 1.763 m por pt de PDF → 1 pt de corrimiento de rótulo = 1.76 m
  RMSE ajuste 0.17 m · LOO por punto 0.19 m · aptitud «predial» (umbral predial < 10 m, georref.py:20)
  LOO por LÍNEA: RMSE 0.22 m · máx 0.32 m
  control: una línea E corrida 3 m → LOO por línea 1.07 m
  si TODOS los rótulos E están 1 pt corridos respecto de su línea: error sistemático 1.77 m, invisible para el LOO
  ```
  Los 24 planos (`data/processed/georreferenciado/*.json`, leídos en esta sesión): LOO mín 0,02 m (Pitrufquén, 9 puntos), máx 1,81 m (Pucón v3 p2), todos «predial».
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 3

### 307 — El borde del AR-2a del plano de Angol está cuantizado a celdas de 6,8 m y suavizado con ventanas de 34 m, y la incertidumbre publicada sólo menciona el RMSE de 4,9 m
- ARCHIVO:LÍNEA — `scripts/18_vectorizar_laminas.py:256-268, 487, 496, 539-544`; `config/laminas.yaml:153-155`
- QUÉ PASA — la máscara se construye sobre una grilla de `celda_px` = 8 px = 8 × 0,8486 = **6,8 m**, la densidad se evalúa en ventanas de 5 celdas (**34 m**) y luego se cierra con kernel 5×5 celdas (34 m) y se abre con 3×3 (20 m). El polígono final hereda ese borde (transform `T` con `a_·cel`, 18:487). El texto de incertidumbre (18:539-544) dice «RMSE 4,9 m» y «hereda el grosor del achurado», sin la magnitud de 7-34 m del borde.
- CÓMO SE VE — el límite del área de riesgo con efecto legal puede estar hasta ~17 m (media ventana) más adentro o afuera que la línea del plano; para un predio de 15 m de frente es la diferencia entre «cae» y «no cae».
- CÓMO REPRODUCIRLO — aritmética sobre `laminas.yaml:120, 153-155` y `metros_por_pixel: 0.8486` del geojson publicado: 8 × 0,8486 = 6,79; 5 × 6,79 = 33,9.
- SALIDA CRUDA — `angol-prc-ar2a-lamina1 26 {'rmse_m': 4.94, 'metros_por_pixel': 0.8486, ...}`
- CONFIANZA — CONFIRMADO (líneas leídas); la magnitud del corrimiento real del borde es SIN DATO (no se midió contra el plano)
- GRAVEDAD — 3

### 308 — El RMSE del plano se calcula con 3 vértices (2 grados de libertad), sin leave-one-out, y con tope 15 m mientras el resto del proyecto exige < 10 m para «predial»
- ARCHIVO:LÍNEA — `scripts/18_vectorizar_laminas.py:203-218, 472-480`; `config/laminas.yaml:138-142`; `scripts/georref.py:20`
- QUÉ PASA — el ajuste de semejanza (4 parámetros) con 3 vértices deja 2 g.d.l.; el propio log lo dice (18:473). No pasa por `georref.metricas`, así que no recibe ni LOO ni categoría de aptitud, y el tope de rechazo es 15 m (`rmse_maximo_m`), o sea que un plano con RMSE 12 m se publicaría como capa normativa sin la etiqueta «manzana» que `georref.clasificar` le pondría.
- CÓMO SE VE — no se ve: la ficha del área vectorizada no muestra aptitud. Es una regla de calidad («ningún producto georreferenciado sale sin su RMSE leave-one-out y su categoría», georref.py:6-7) que este producto no cumple.
- CÓMO REPRODUCIRLO — leer las líneas citadas; `rmse_m: 4.94` en el geojson.
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 3

### 309 — La ficha SAR dice «el eco del radar cayó 3 dB» mostrando el umbral, no lo medido
- ARCHIVO:LÍNEA — `web/app.js:776-783`; `scripts/14_sar_huella_observada.py:800-801`
- QUÉ PASA — `p.caida_db` es `float(cfg_sar["caida_db"])` = −3,0 fijo (`araucania.yaml:158`) copiado a cada polígono; el visor lo presenta como la caída observada. La caída real de cada píxel no se publica. `umbral_agua_db` sí se presenta correctamente como umbral («quedó bajo −20,1 dB»).
- CÓMO SE VE — todos los polígonos de la región «cayeron 3 dB», que es falso: cayeron ≥ 3 dB.
- CÓMO REPRODUCIRLO — `python -c "import json,collections;h=json.load(open('web/data/sar/huella-observada.geojson',encoding='utf-8'));print(collections.Counter(f['properties'].get('caida_db') for f in h['features']))"`
- SALIDA CRUDA — `huella features 1075 caida_db: Counter({-3.0: 1075})` — los 1.075 polígonos llevan exactamente el mismo valor, que es la constante de `araucania.yaml:158`.
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 2

### 310 — Las láminas derivadas se etiquetan `capa_evidencia: A_normativo` aunque el texto diga «no tiene efecto legal»
- ARCHIVO:LÍNEA — `scripts/18_vectorizar_laminas.py:421, 538`; `scripts/19_estado_comunas.py:156`
- QUÉ PASA — la etiqueta de capa es la misma que la del vectorial MINVU. El visor las mantiene aparte (`estado.laminas` ≠ `estado.areasRiesgo`, app.js:63, 106, 348, 1549-1565), así que **no** entran al veredicto; pero cualquier consumidor del GeoJSON que filtre por `capa_evidencia` las mezcla.
- CÓMO SE VE — en el visor, no se ve. En el dato publicado, sí.
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 2

### 311 — `area_minima_m2 = 2000` deja 17 de 98 polígonos de Angol a menos de 1.000 m² de desaparecer
- ARCHIVO:LÍNEA — `scripts/18_vectorizar_laminas.py:286, 494`; `config/laminas.yaml:69-70, 107, 156`
- QUÉ PASA — el umbral se aplica en UTM (m²) después del transform, **antes** de reproyectar a 4326: unidades correctas. La magnitud es arbitraria: 2.000 m² son 33 px en Angol, 70 px en Catripulli y 2.777 px en el plano (0,85 m/px), tres criterios de tamaño-en-figura distintos con el mismo número. El 17 % de los polígonos de Angol está en [2.000, 3.000) m²; el efecto en hectáreas es chico (191,7 ha con 0 → 188,0 con 2.000).
- CÓMO SE VE — un patio inundable de 1.900 m² no aparece; uno de 2.100 sí.
- CÓMO REPRODUCIRLO — `python tools/auditoria/distribucion_areas_vs_area_minima.py`
- SALIDA CRUDA —
  ```
  [angol-peligro-inundacion-2013]  n=98  m/px=7.74
    área m²: min 2037 · p10 2516 · mediana 7189 · p90 41665 · max 319482
    bajo el umbral (2000 m²): 0
    en [2000, 3000) m²: 17  · en [2000, 4000): 26  · ≤ 1 ha: 56
    umbral en píxeles: 33 px de 7.74 m
  [angol-prc-ar2a-lamina1]  n=26  ... umbral en píxeles: 2777 px de 0.8486 m
  [curarrehue-catripulli-inundacion-2025]  n=39  ... en [2000, 3000) m²: 5 · umbral en píxeles: 70 px de 5.337 m
  ```
  (verifica también que ningún polígono publicado está bajo el umbral y que `hectareas` declarado coincide con el área recalculada: diferencia máx 50 m² = redondeo a 0,01 ha.)
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 2

### 312 — Hay dos definiciones distintas de «inundación» entre capas: SENAPRED excluye anegamiento, campamentos lo incluye
- ARCHIVO:LÍNEA — `config/araucania.yaml:84-92` (excluye «Colapso colectores…» y «Anegamiento de caminos»); `scripts/13_campamentos_riesgo.py:45, 52-53` (`ANEGAM` cuenta como hídrico); `web/data/areas-riesgo-inundacion.geojson` (feature 0: `clasificacion: ANEGAMIENTO`, `es_inundacion: True`, leído en esta sesión)
- QUÉ PASA — el proyecto argumenta largo (araucania.yaml:57-83) que anegamiento urbano no es inundación fluvial y lo saca de los puntos críticos; pero el área normativa de Temuco «ARRI restricción Inundación Anegamiento» y los campamentos con `ANEGAM` entran al veredicto como inundación (app.js:348, 363-365 manda con nivel alto). No es un error de unidades; es un umbral semántico aplicado de forma distinta según la capa.
- CÓMO SE VE — un punto en el ARRI de Temuco recibe «Estás en un área de riesgo por inundación» con la misma fuerza que uno en un área fluvial; el sello `tipo_hidrico` (app.js:689-692) lo matiza recién en la pestaña de detalle.
- SALIDA CRUDA — `areas A por tipo_hidrico: Counter({'fluvial': 57, 'anegamiento': 3, 'litoral': 2, 'napa_freatica': 1})` (63 polígonos publicados; 6 no son fluviales y todos entran a `poligonosQueContienen` en app.js:348 con el mismo peso).
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 2

### 313 — `TOL_PASO` se aplica al paso de los VALORES de los rótulos: un rótulo no leído convierte una grilla perfecta en «irregular» — SOSPECHA
- ARCHIVO:LÍNEA — `scripts/08_georreferenciar_grilla.py:60, 195-200`
- QUÉ PASA — `pasos = np.diff(valores)` son diferencias entre coordenadas UTM de rótulos consecutivos detectados; si falta uno, aparece un paso de 2.000 junto a pasos de 1.000 y `regular` es False aunque la linealidad sea perfecta. Purén se rechazó exactamente así: `r2 = 0,9999998` y «grilla de eastings irregular».
- CÓMO SE VE — Purén queda sin plano georreferenciado (pérdida de cobertura, conservadora).
- SALIDA CRUDA — `False | PRC-P-09208-01-Puren-GIS_31_mayo.pdf p 1 | grilla de eastings irregular | ejeE {'n': 6, 'paso_m': 1000.0, 'r2': 0.9999998298478207, 'regular': False}`
- CONFIANZA — SOSPECHA (no se abrió el PDF de Purén para confirmar que la causa es un rótulo faltante)
- GRAVEDAD — 2

### 314 — `TOL_INLIER_M = 3 m` es fijo en metros de mapa mientras la posición de los rótulos se mide en pt: a escalas chicas es menos de un punto tipográfico — SOSPECHA
- ARCHIVO:LÍNEA — `scripts/08_georreferenciar_grilla.py:139, 180`
- QUÉ PASA — en Traiguén 1 pt = 1,76 m (medido arriba). Un plano a 1:20.000 tendría 7 m/pt: un rótulo centrado 0,5 pt distinto de sus vecinos ya es outlier, y con < 3 inliers el eje se descarta (08:184). Los 24 planos publicados son todos de paso 250-500 m, o sea escalas grandes; el riesgo es de falso rechazo en planos de escala chica.
- CONFIANZA — SOSPECHA (no hay un plano rechazado por esta causa en `georreferenciacion_grilla.json`; los 15 «no se detectó grilla» no traen diagnóstico)
- GRAVEDAD — 2

### 315 — Dos márgenes distintos para la misma pregunta «¿cae en la región?»: 0,3° en el script 08 y 0 en el 18
- ARCHIVO:LÍNEA — `scripts/08_georreferenciar_grilla.py:227` (`± 0.3`, ~33 km); `scripts/18_vectorizar_laminas.py:400, 524` (sin margen); `tests/auditoria_datos.py:360` (`TOL = 0.01`)
- QUÉ PASA — tres tolerancias para el mismo bbox. Con margen 0, una lámina legítima de Lonquimay o Renaico pegada al borde regional se rechazaría; con 0,3°, un huso equivocado que caiga 30 km fuera se aceptaría.
- CONFIANZA — CONFIRMADO (líneas leídas); no hay caso real afectado → efecto SIN DATO
- GRAVEDAD — 2

### 316 — La caché de teselas del service worker no tiene tope de tamaño ni de edad
- ARCHIVO:LÍNEA — `web/sw.js:82-90`
- QUÉ PASA — cada tesela navegada se guarda (`c.put`) y sólo se borra al cambiar `VERSION`. No hay número que mande: crece sin límite hasta que el navegador desaloje el origen completo, incluida la caché de la app.
- CÓMO SE VE — en un celular con poco espacio, el navegador puede borrar toda la caché del sitio justo cuando se necesita sin señal.
- CONFIANZA — CONFIRMADO (líneas leídas); comportamiento del desalojo SIN DATO
- GRAVEDAD — 2

### 317 — `min_pixeles_agrupados` se convierte a m² con la latitud media de la rejilla regional
- ARCHIVO:LÍNEA — `scripts/14_sar_huella_observada.py:740-741`; `scripts/sar.py:390-394`
- QUÉ PASA — un solo `area_min` para toda la región; el píxel mide 3 % más en el norte que en el sur (cos −37,35° / cos −39,65°). Cinco píxeles en Renaico son 5,1 «píxeles de referencia»; en Loncoche 4,9. Efecto real: manchas de 5 px justo al sur del centro podrían caer. Magnitud despreciable frente al «≈1 ha» declarado.
- CONFIANZA — CONFIRMADO (aritmética sobre líneas leídas)
- GRAVEDAD — 1

### 318 — «a menos de 500 metros» escrito a mano en el texto del porqué
- ARCHIVO:LÍNEA — `web/app.js:578-579` vs `RADIOS.medio` en `app.js:17`
- QUÉ PASA — hoy coinciden; si alguien cambia `RADIOS` la frase miente.
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 1

### 319 — `umbral_agua()` declara percentil 90 por omisión y en su docstring; el proyecto usa 50
- ARCHIVO:LÍNEA — `scripts/sar.py:157, 165-166` vs `config/araucania.yaml:162-170` y `scripts/14_sar_huella_observada.py:524`
- QUÉ PASA — el script 14 pasa el valor del YAML (verificado en 14:524), así que el resultado publicado usa p50. Pero quien lea `sar.py` o use la función suelta obtiene p90, que el propio YAML documenta como «multiplicaba por tres el área detectada».
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 1

### 320 — `area_minima_m2` tiene omisión 0 en `procesar` y 2000 en `procesar_plano`
- ARCHIVO:LÍNEA — `scripts/18_vectorizar_laminas.py:329` vs `:488`
- QUÉ PASA — las tres láminas lo declaran, así que hoy no manda. Una lámina nueva sin el campo publicaría motas de 60 m² en un caso y no en el otro.
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 1

### 321 — Comentario huérfano en `laminas.yaml` que vuelve a presentar la lámina rechazada como «la única cartografía que alcanza a Ercilla y Los Sauces»
- ARCHIVO:LÍNEA — `config/laminas.yaml:184-191` (tras el bloque «❌ RECHAZADA» de :158-182)
- QUÉ PASA — el archivo termina a mitad de un párrafo que describe una lámina DGA de «43,8 m/píxel» sin entrada `- id:`. No manda nada (es comentario), pero contradice lo que dice diez líneas más arriba.
- CONFIANZA — CONFIRMADO
- GRAVEDAD — 1

---

## 3. SIN DATO (lo que no se midió)

- Sensibilidad de `contraste_minimo`, `marca_area`, `marca_lado`, `celda_px`, `ventana_celdas`, `densidad_minima` del plano AR-2a (18:244-268): no se corrió `mascara_por_trama` con variantes. El corrimiento real del borde vectorizado respecto de la línea del plano tampoco.
- Umbrales del detector de láminas (07:127-130) y del clasificador de páginas (03:119): no hay medida de falsos positivos/negativos.
- Causa concreta del rechazo de Purén (H-313) y existencia de planos rechazados por `TOL_INLIER_M` (H-314): los 15 «no se detectó grilla» no traen diagnóstico.
- Comportamiento del desalojo de caché en Android con poco espacio (H-316).
- Si `0.85` de 11:118 coincide con la opacidad real del visor en `style.css`.
- El corrimiento ≤ 1 km de Catripulli/Angol-2013 sugerido por la coherencia con el GORE (§H-301): el modelo de 35 m no permite afirmarlo ni descartarlo.

---

## 4. VERIFICADO LIMPIO

Lo que se miró y está sano; no hace falta volver a mirarlo por unidades o magnitud.

- **Sin mezcla grados/metros en el visor**: `RADIOS` (m) se compara sólo con `distancia()` haversine (m) en app.js:337-344, 409; `dentroAnillo`/`poligonosQueContienen` operan en lon/lat contra geometría en lon/lat (app.js:145-169); `planosQueCubren` compara lon/lat con `bounds_wgs84` (app.js:176-181). `R = 6371000` (app.js:136). Instrumento `sensibilidad_radios_veredicto.py --control`: 0 m → alto, 305 m → medio, 2.000 m → sindato.
- **El bbox regional es uno solo**: `[-73.70, -39.65, -70.90, -37.35]` idéntico en `config/araucania.yaml:9`, `web/app.js:31` y `tests/auditoria_datos.py:359` (leídos los tres). `dentroDeRegion` usa el bbox pelado (app.js:37-40); `margenGrados` sólo afecta paneo (app.js:43-47).
- **Filtro de área de las láminas en la unidad correcta**: `g.area < area_min` se evalúa sobre geometría en UTM (transform `Affine` en metros, 18:323-324) antes de `sh_transform` a 4326 (18:376). Ningún polígono publicado está bajo 2.000 m²; `hectareas` declarado coincide con el área recalculada (diferencia máx 50 m², redondeo a 0,01 ha). Salida cruda en H-311.
- **La vectorización se reproduce exactamente**: con los valores declarados, `sensibilidad_ancho_minimo_laminas.py` reproduce 70/188,0 ha y 28/20,5 ha (Angol) y 12/93,8 ha y 27/715,3 ha (Catripulli), iguales al `resumen_por_clase` publicado.
- **Escala X vs Y (`0.01`) funciona cuando tiene con qué**: rechazó Vilcún p3 con 0,3448 vs 0,6236 m/pt (`georreferenciacion_grilla.json`). Que no se ejerza en Angol/Catripulli es H-301, no un defecto del umbral.
- **El LOO del script 08 no está inflado por el producto cartesiano**: por punto 0,19 m, por línea 0,22 m, máx 0,32 m (Traiguén); el control (línea corrida 3 m → 1,07 m) demuestra que el instrumento ve el fenómeno.
- **Las tres láminas aterrizan donde dice evidencia independiente**: 72,9 % / 87,6 % / 88,7 % del área dentro del modelo GORE 2016; correrlas 5 km baja eso a 0-50 % en 11 de 12 direcciones (`coherencia_laminas_vs_gore_senapred.py`).
- **Paginación ArcGIS**: `comun.py:172-175` acota la página al `maxRecordCount` del servicio; la parada es `exceededTransferLimit` (comun.py:203; 15:142), con cortafuegos 500.000 / 60.000; un `error` con HTTP 200 revienta (comun.py:196-200; 15:136-139).
- **SAR, unidades coherentes**: `111_320` m/grado es el mismo valor en `sar.py:49` y en `14:642, 724, 870, 887`; la longitud se corrige por cos(lat) donde corresponde (sar.py:203, 393; 14:643); radios de verificación en metros convertidos a celdas con `ceil` (14:682-683); el umbral de agua se acota a [−22, −13] dB y el track 164A muestra el acotado funcionando (crudo −24,34 → −22,0, `indice.json`); `resolucion_m: 50` publicado coincide con 0,00045° × 111.320.
- **JRC**: `UMBRAL_M = 0.25` es profundidad en metros del producto (02:58-61); `ANIO_PUBLICACION 2016` sale del `Last-Modified` del servidor (02:52-55).
- **SENAPRED**: filtro de coordenadas en grados de Chile continental (01:154); `cronico = n >= 3` temporadas (01:257) y app.js lo presenta como «se repite temporada tras temporada» (app.js:580-581), sin número inventado.
- **Redondeos publicados**: GORE a 5 decimales (~1 m, 15:104-108) para un dato de 35 m; SAR a 6 (~0,1 m, sar.py:371) para 40-50 m; `_km` del visor a 0,1 km (app.js:416). Ninguno pierde precisión real.
- **Límites de proceso avisan**: `--limite 40` del script 07 escribe cuántos quedaron (07:327-330); `25` candidatas del 03 avisa (03:165-167); `ID_MAX 700` con 536 fichas reales (05:42).
- **Comentario «~15 km» de 20:137** es correcto como orden de magnitud (0,15° = 16,7 km en latitud, 13 km en longitud a −38,5°).
- **Las 130 constantes `8`/`-8`, `/1024`, `/72.0`, `28.35`, `1e6`, fechas y años del censo** son codificación UTF-8, conversión pt↔cm, KB/MB y literales de URL: no deciden nada geográfico (revisadas en `censo_magnitudes.tsv` y en el contexto de cada línea citada arriba).
