# Auditoría profunda de riesgomapas — 6 de septiembre de 2026

Rama `visor-simple-y-laminas-vectorizadas`, árbol limpio al empezar (`b293aad`). Ejecutada según
`GUIA_MAESTRA_AUDITORIAS.md` y la guía de prompting de Fable 5.1, con el prompt de
`docs/_prompts/AUDITORIA-2026-09.md`.

**Cómo se hizo.** Siete frentes disjuntos en paralelo (uso · relación · magnitudes · documentación ·
capas A y B · ray-casting · polígonos), cada uno con el preámbulo anti-fabricación de
`docs/_prompts/PREAMBULO-AUDITOR.md` pegado entero y numeración provisional propia (101+ … 701+).
Los 93 hallazgos provisionales pasaron por dos **verificadores con contexto limpio** (Opus) que
recibieron sólo título y archivo:línea, releyeron, enumeraron caminos, re-corrieron los bancos,
refutaron tres, midieron distinto en tres y encontraron ocho propios. Sus informes son
`verificacion-visor.md` (familias V-xx) y `verificacion-pipeline.md` (familias P-xx); los de los
frentes, `frente-1…7-*.md`. Este documento funde todo en familias finales F-xx: un defecto raíz,
todos sus síntomas.

**Línea base de hoy, corrida en esta sesión antes de apoyarse en ella:**

| Prueba | Resultado |
|---|---|
| `python -m pytest tests -q` | 63 passed |
| `python tests/auditoria_datos.py` | 151 OK · 1 hallazgo medio (5 de 124 polígonos sin año) |
| `python tests/auditoria_e2e.py` | 273 OK · 0 hallazgos |

Los tres verdes son verdaderos y a la vez no miran nada de lo que sigue: la capa derivada, el
texto compartido, el modo sin red y las láminas contra su origen no tienen comprobación (F-20).

**Instrumentos nuevos**, todos en `tools/auditoria/` y commiteados hoy (34 scripts; la evidencia
pesada —PNG, PDF, GeoJSON regenerables— queda fuera del repositorio por la regla 6.4 y se
regenera corriéndolos). Los que responden la pregunta de los polígonos: `lamina_sintetica.py`,
`fidelidad_laminas.py`, `georref_independiente.py`, `raycasting_adversarial.js`,
`raycasting_vs_shapely.py`, `fraccion_cerca_del_borde.py`, `verif_702_apertura.py`,
`verif_703_color_rio.py`, `censo_magnitudes.py` (con control positivo).

---

## 1. Respuesta directa a las dos preguntas

### ¿Está todo en orden o hay algo que mejorar?

No está en orden. El sitio dibuja siete capas y **decide con cuatro**: los 163 polígonos que el
proyecto produjo desde láminas impresas —la única evidencia normativa que existe para Angol y
Curarrehue— se pintan en el mapa y nunca entran al veredicto ni a la ficha; el modelo regional del
GORE y el JRC se calculan y tampoco. Un vecino de Angol parado dentro del área AR-2a del plan
regulador **vigente** lee «este punto no cae dentro de un área de riesgo por inundación declarada
en el plan regulador». Alrededor de ese defecto raíz hay 21 familias más, seis de gravedad 4:
el texto que se reenvía por WhatsApp pierde la advertencia «no significa que acá no se inunde»;
el botón «Buscar» no hace nada desde el 25 de agosto; sin red el service worker entrega
`index.html` como si fuera un plano y el botón dice «Plano cargado»; el bloque «Con qué cuenta»
nombra la comuna equivocada (Temuco sale siempre como Padre Las Casas); anegamiento, marejada y
napa se titulan «área de riesgo por inundación»; y el veredicto es binario sin banda de borde
mientras el propio sitio pide «mira la mancha, no su borde».

### ¿Estamos reconociendo bien los polígonos?

**La forma y la posición, sí, dentro de un píxel; y lo sabemos porque una lámina de geometría
conocida pasó por el mismo `procesar()` del script 18 y volvió con IoU 0,956 («Alto») y 0,975
(«Medio»), el hueco interior conservado, el río de 2 px eliminado, 0 polígonos en el control
negativo y el guardián de región cayéndose como debe.** Las dos láminas de Angol,
georreferenciadas por métodos independientes (rótulos de retícula vs. vértices rotulados),
coinciden con corrimiento óptimo (0, 0) m; los cuatro puntos «Alto» de SENAPRED caen a 12-37 m
del «Alto» de 2013, y 4 de 6 puntos de Catripulli caen a 0 m de su mancha.

Lo que **no** está bien, medido sobre el artefacto:

| Medida (salida cruda en `frente-7-poligonos.md` y `verificacion-pipeline.md`) | Angol 2013 Alto | Angol 2013 Medio | Catripulli alta | Catripulli media | AR-2a plano |
|---|---|---|---|---|---|
| IoU publicado vs. máscara de color cruda de la lámina | 0,70 | 0,49 | 0,83 | 0,94 | — |
| IoU publicado vs. clasificador independiente (k-means) | 0,65 | 0,22 | 0,73 | 0,94 | — |
| Distancia del centro k-means al color de leyenda (RGB) | 13,8 | **54,1** (fuera de la tolerancia 45) | 17,5 | 1,9 | — |
| Área que se come la apertura de 4 px | 25 % | 42 % | 15 % | 6 % | — |
| Marcas de achurado dentro de lo publicado | — | — | — | — | 76 % (densidad ×52 dentro vs. fuera) |
| Corrimiento sistemático por núcleo par | +1 px E, +1 px S (7,7 m) | ídem | +1 px (5,3 m) | ídem | no aplica |
| Polígonos que son la caja de leyenda | 6,12 ha + 0,28 ha | 5,62 ha | 0,3 ha | 0,5 ha | 0 |
| Población a < 10 m de un borde derivado (grilla 20 m, Censo 2024) | 3,0 % | | **37,0 %** | | — |

Y la premisa que justifica la apertura («la red hídrica se dibuja en el mismo azul que Alto») es
falsa en Angol: el río va en azul marino (0, 8, 48), a distancia 135 del color «Alto»; de 9.056
píxeles de ese color en el cuerpo, **0** caen dentro de la tolerancia. Lo que la apertura elimina
son franjas legítimas de «Alto» a lo largo de esteros (35 ha aisladas + 26 ha de borde de 188
publicadas), y además, por el núcleo par, **agrega** 13-16 ha que nunca tuvieron el color.

Conclusión operativa: los polígonos sirven para lo que el proyecto quiere hacer con ellos, pero
hoy no deben publicarse como están. Antes: sacar la leyenda (F-03), corregir el núcleo y
re-medir el grosor mínimo (F-04), decir qué son (F-02) y recién entonces meterlos al veredicto
(F-01). Y el borde tiene que llevar su incertidumbre en pantalla (F-09), porque en Catripulli
una de cada tres personas vive a menos de 10 m de él.

---

## 2. Hallazgos confirmados, por familia

Gravedad 5 = una persona decide mal con este dato. Cada familia cita el archivo:línea de su raíz
y los IDs de verificación (V-/P-) y provisionales que absorbe; el detalle, los caminos y la salida
cruda están en los informes de verificación.

### F-01 · El veredicto decide con cuatro de las siete capas que dibuja — **5**
`web/app.js:333-386` (`evaluar` no consulta `estado.laminas`; calcula `gore` y `enMancha` pero
`nivel` sólo sale de `sar`, `areas` y puntos críticos), `web/app.js:657-1039` (`render` sin bloque
de láminas). Absorbe V-01, P-01, 101, 201, 601, 602. Reproducido por ambos verificadores en
(−72,6867, −37,78499), dentro del AR-2a mayor de Angol: 0 en capa A oficial, 0 SAR, 0 JRC, 2 en
láminas, y en pantalla «no cae dentro de un área de riesgo». Además el titular «Sin registros en
las fuentes consultadas» sale en puntos donde la misma ficha dice GORE «máxima» (601). Se
reproduce en todos los caminos de consulta, con y sin red.

### F-02 · La capa derivada no dice lo que es — **4**
`scripts/18_vectorizar_laminas.py:421,538` y `scripts/19_estado_comunas.py:156` sellan
`capa_evidencia="A_normativo"`; el docstring `:35` promete `A_derivado`, que `comun.py:290-292`
rechaza. Ningún polígono lleva `estado_tramite` (REGLAS §1.5) ni número de incertidumbre: el
RMSE 4,94 m vive en `data/processed/`, que no se publica, y la cuantización a celdas de 6,8 m y
ventanas de 34 m del AR-2a no se declara. Y los 26 polígonos AR-2a del PRC **vigente** quedan bajo
el mismo descargo «NO tiene efecto legal» que un estudio de 2013: subvende la única evidencia
normativa de Angol. Absorbe V-15, V-N01, P-03, P-04, 208, 310, 400, 401, 114, 307, 308.

### F-03 · Los cuadros de la leyenda están publicados como área de riesgo — **4 (5 en cuanto F-01 se arregle)**
`scripts/18_vectorizar_laminas.py:347-350` clasifica la hoja entera; `excluir_y` existe
(`:343-345`) y ninguna lámina lo declara. Angol: «Alto» 6,12 ha (371×170 m) en lon −72,70378 lat
−37,83436 y «Medio» 5,62 ha en −72,70369 / −37,83663, campo abierto a 2 km del punto crítico más
cercano; Catripulli: 0,3 y 0,5 ha en −71,683 / −39,374. Los recortes de la lámina muestran que
esos píxeles son los cuadros «Alto/Medio» y «Susceptibilidad Alta/Media» de la leyenda; la lámina
sintética lo reproduce. Absorbe P-05, 701.

### F-04 · El vectorizador no protege su posición ni declara su borde — **5 (por el guardián)**
- Guardián de región sin margen (`18:399-405`, `:523-525`): acepta corrimientos de **20 km** en las
  cuatro direcciones; es la única defensa de un rótulo mal tecleado porque las dos láminas de
  figura tienen una sola ancla vertical y la verificación cruzada de escala no corre. Tres
  respuestas distintas a «¿cae en la región?» en el repositorio (0,3° en el 08, 0 en el 18, 0,01 en
  la auditoría). P-02, 301, 315.
- Apertura con núcleo par 4×4 (`18:359-360`): corre toda la mancha +1 px E y +1 px S y agrega
  píxeles fuera de la clase. P-07, 702, 320.
- `ancho_minimo_px: 4` son 31 m en Angol y 21 m en Catripulli; se come 25 % de «Alto» y 42 % de
  «Medio» en Angol; la premisa del río es falsa. P-08, 302, 703.
- `tolerancia_color: 40` de Catripulli a 25-30 unidades de un acantilado ×4,4 en la clase «media»;
  el «Medio» de Angol tiene su centro real a 54 unidades del color declarado. P-21, 303.
- `area_minima_m2 = 2000` con 17 de 98 polígonos de Angol a menos de 1.000 m² de desaparecer;
  omisión 0 en `procesar` y 2000 en `procesar_plano`. P-22, 311.

### F-05 · La lámina 09201-2 de Angol existe y nadie la declara — **2 hoy, 4 cuando F-01 entre**
`config/laminas.yaml:114-124` vectoriza sólo la lámina 09201-1; el PDF de la 2 está en
`data/raw/documentos/angol/` y `grep "09201-2"` no devuelve nada en config, docs, scripts ni web.
Los tres puntos crónicos «Alto» de SENAPRED (N ≈ 5.812.200) quedan a 1,1-1,3 km del AR-2a
publicado y a 29-37 m del «Alto» de 2013: el sur del pueblo no tiene plano legal en el visor.
Contenido de la lámina 2: SIN DATO. P-23, 704.

### F-06 · Sin red, el service worker miente y el visor le cree — **4**
`web/sw.js:104-106` responde `index.html` a todo lo que no tiene; `mostrarPlano`
(`app.js:209-233`) devuelve `true` y el botón escribe «Plano cargado sobre el mapa» sin plano;
las teselas de Esri van a la caché de la app (`sw.js:82-83`), que se borra entera en cada
`VERSION` y no tiene tope; quien dejó la base satelital recordada abre el visor en un corte y
recibe un lienzo vacío sin explicación. Es el escenario para el que existe el proyecto. Absorbe
V-05, V-N02, V-N05, 112, 214, 223, 213, 316.

### F-07 · El texto que se reenvía pierde la advertencia y recorta la evidencia — **4**
`web/app.js:1089` lee `estado.ultimo.nivel`, que no existe (el nivel está en
`estado.ultimo.res.nivel`, `:975`): el «OJO: que no haya registro NO significa que acá no se
inunde» nunca viaja por WhatsApp en «sin registros»; el texto recorta a 3 puntos críticos sin
decir cuántos hay (`:1076-1085`). V-02, 104, 202, 210.

### F-08 · El fenómeno no se distingue donde la persona lee primero — **4**
`web/app.js:363-365, 571-573`: anegamiento, litoral y napa salen titulados «área de riesgo por
inundación» en el titular y el porqué; el sello «anegamiento, no desborde» sólo está en la
pestaña de detalle (`:689-692`). Y hay dos definiciones de «inundación» entre capas
(`config/araucania.yaml:84-92` excluye anegamiento; `13_campamentos_riesgo.py:45,52-53` lo
incluye). V-03, P-20, 105, 312. Contradice REGLAS §1.4.

### F-09 · Veredicto binario sin banda de borde, y el GPS sin su precisión — **4**
`web/app.js:357-378` y `:17` (`RADIOS` sólo para puntos críticos), `:1321-1333` (`accuracy`
descartado), contra `index.html:232` («Mira la mancha, no su borde»). A 3,8 m fuera de ZR-5
Collipulli y a 9,1 m de un polígono de evidencia: «Sin registros». 5,2 % de 400 posiciones cambia
de veredicto al moverse 50 m (el 14 % del auditor no se reprodujo). Población a < 10 m de un
borde: Catripulli 37,0 %, Angol derivada 3,0 %, Angol GORE 4,3 % (19,8 % a < 50 m). El borde es
semiabierto por diseño (`:149-150`). V-04, 603, 304, 305, 607.

### F-10 · «Con qué cuenta» nombra la comuna equivocada — **4**
`web/app.js:393-417` (`comunaDe` = comuna del punto crítico más cercano, a cualquier distancia):
Temuco y Victoria tienen 0 puntos y **nunca** pueden salir; la Plaza de Temuco sale «Padre Las
Casas»; un punto en el mar sale Saavedra a 16 km con «poca capacidad técnica municipal»; un
punto dentro de un área de Collipulli dice «Ercilla … no tiene su área de riesgo». Y «no
detectamos vacíos» para Temuco por su único polígono, que es de anegamiento
(`19_estado_comunas.py:183-185`). V-06, V-N04, 103, 604, 204, 113.

### F-11 · El botón «Buscar» no está enlazado a nada — **4**
`web/index.html:55` (`#btn-buscar`) sin manejador en `enlazarInterfaz` (`app.js:1900-1942`)
desde `2ab0ccf` (25-ago). Sólo Enter busca. V-07, 102.

### F-12 · Una entrada ausente produce una salida falsa, sin error — **4**
La misma forma que arregló `a6c08f1` en el script 10, en tres scripts más:
`19_estado_comunas.py:103,106,109,119` (`or {…}` vacío → 32 comunas «no publica ningún
documento» / 0 puntos críticos), `09_exportar_catalogo.py:126-127` (sin municipales y sin
decirlo), `20_paquete_practicante.py:235`; y `--bbox` del 14 sobrescribe la capa B publicada con
un recorte de prueba (`14:702-703, 717, 877-879`). Contradice REGLAS §2. P-06, P-19, 203, 219, 207.

### F-13 · El año se firma como MINVU, sale del Atlas, y a veces es de otra comuna — **3**
`06_areas_riesgo_prc.py:342-350` escribe `anio` desde la config con `anio_fuente = Atlas CIGIDEN`;
`app.js:645-655` lo imprime como MINVU y a la vez dice «no declarado»; sin polígono, `app.js:720`
muestra el año del primer polígono de la capa; «Puerto Saavedra» pierde su año por renombrar
antes de buscar (`06:317,345`); la guía del practicante dice 4 sin año y son 5. V-08, P-13, 107,
205, 504, 404.

### F-14 · Capa A oficial: lo que el filtro dejó pasar y lo que no — **3**
Duplicado geométrico exacto en Collipulli (#20/#62, 10,2 ha, mismos 229 vértices con distinto
vértice inicial; la clave de `06:218` no lo ve): «cae dentro de 2 áreas» donde hay una. Tres «ZR-3
Área en torno a Canales» fuera del filtro hídrico (`06:75-81`). Toltén AR-1 y AR-2 100 %
contenidos en AR-3. Anillos al revés de RFC 7946 en los 63. Collipulli tiene 36 de 63 porque su
PRC de 2009 zonificó en polígonos chicos (mediana ~2 ha): 27 del servicio nacional y 9 del
regional. P-11, P-15, P-16, P-17, 502, 510, 509, 511. (501 «MINVU los clasifica remoción en
masa» quedó **refutado**: 6 de 8 ZR-5 no tocan ningún polígono de remoción.)

### F-15 · Capa B: lo que suma, lo que no es válido y lo que no nombra — **3**
5.776 ha es la suma de tres órbitas: 695-702 ha se cuentan dos o tres veces. 585 de 1.075
polígonos de la huella y 59 de 115 de la cobertura son inválidos (`14:561-562`, conectividad 8);
el ray-casting del visor coincide con shapely igual. El ×2,8 se mide sobre la máscara ráster
previa al filtro de área (`14:909, 813, 566`), no sobre lo publicado; medido sobre lo publicado
da ×2,5-3,3 según el radio (el ×1,95 del auditor quedó **refutado**). 841 ha (14,6 %) a ≤ 2 m de
altitud en el estuario del Imperial y la incertidumbre publicada no contiene «marea» ni
«estuario»; 13 polígonos entre 1.000 y 1.200 m no violan ninguna regla declarada (la «mancha de
70 ha a 724 m» no se encontró: SIN DATO). La máscara de terreno sí llegó al artefacto: 0
polígonos > 1.200 m, 0 con pendiente > 5°. P-09, P-10, P-12, P-14, V-20, 505, 506, 503, 507,
508, 606.

### F-16 · Se muestra el parámetro como si fuera lo medido — **3**
`app.js:776-783` «el eco del radar cayó 3 dB» es el umbral, no la caída (1.075/1.075 iguales);
`app.js:857-858` «error de ubicación 0,19 m» es la precisión del ajuste, no la exactitud del
plano (un corrimiento de 1 pt en todos los rótulos vale 1,77 m y ningún leave-one-out lo ve). V-11,
V-12, 309, 306.

### F-17 · Geocodificación que responde otra cosa sin avisar — **3**
«Balmaceda 500, Temuco» devuelve la avenida entera (`app.js:1114-1126` toma `j[0]` sin mirar
`addresstype`); Enter sin sugerencia geocodifica con `limit=1`; elegir una comuna (sugerencias
**y** tabla de portada, `:1145` y `:1805`) produce un veredicto de nivel para el centro del bbox de
sus puntos críticos, que nadie eligió. V-09, V-10, V-N03, 106, 217, 110.

### F-18 · Enlaces que no llevan a ninguna parte — **3**
«Ver ordenanza» → 404 (`app.js:697-699`; 9 de 63 con URL, una sola distinta); 38 documentos del
catálogo con URL vacía y «directo al PDF» que recarga la página (`catalogo.js:40,64`). V-13, 111,
109.

### F-19 · Interacción: respuestas dobles, mensajes pegados, hojas tapadas — **2-3**
Tocar un polígono MINVU abre popup y dispara la consulta completa (`app.js:1576-1588`,
`1678-1683`); `#estado` es un solo `<p>` que ~20 sitios escriben y nadie limpia; las sugerencias
se reabren solas tras elegir (`:1243-1247`); la espera al estilo llegó a 2 casillas de 8; dos
hojas de plano cubren el mismo punto y se muestra `planos[0]` (Pucón v3 tapa a v4, `:844-845`);
geolocalización denegada en inglés (`:1331`). V-14, V-17, V-18, V-19, V-22, V-24.

### F-20 · Lo que las pruebas no miran — **2**
La e2e no mira `jrc-fill` ni `lam-fill`, nunca consulta dentro de una lámina ni lee el texto
compartido (`tests/auditoria_e2e.py:138-139, 457-472`); cinco GeoJSON del JRC publicados sin
lector y `auditoria_datos.py:274` exenta `jrc/` de la búsqueda de huérfanos; el barrido de
ray-casting no probó `cobertura-sar`; los propios instrumentos de auditoría se caen en Windows
por cp1252 si no se fija `PYTHONIOENCODING`. V-21, P-18, P-26, 218, 605, 220.

### F-21 · Documentación contra realidad — **2**
`docs/REGLAS.md` no existe y lo citan `07:27` y `20:393,404` (llega al `LEEME.md` del
practicante); ningún script declara `Requiere:` y `test_scripts.py:50-64` sólo exige `Salida:`;
«23 planos» en `app.js:185,190` y `PROPUESTA.md:39` cuando son 20; `laminas.yaml:184-191` resucita
la lámina rechazada de la DGA justo después del bloque «RECHAZADA»; `sar.py:157,165` declara
percentil 90 y el proyecto usa 50; el pie dice «la búsqueda ocurre en tu dispositivo» y la
dirección viaja a Nominatim letra a letra (`index.html:301-303`, `app.js:1117-1121`). P-24, P-25,
P-28, V-16, 215, 216, 403, 321, 402, 319, 108.

### F-22 · Menores — **1**
Campos escritos que nadie lee (`estado-comunas.json`: `mayores_60`, `viviendas_hacinadas`,
`hogares_agua_de_rio`; y las 11 propiedades de `vectorizadas.geojson`, ver F-01); `estado` no
declara tres claves; «500 metros» escrito a mano (`app.js:578` vs `RADIOS`); `area_pixel_m2` con la
latitud media (±1,6 %); `TOL_PASO` sobre el paso de los valores. P-27, P-29, P-30, V-25.

### Refutados y corregidos por los verificadores
- **115** «palabras de §7.2 en `web/`»: las seis apariciones de «pronóstico» son negaciones y la
  única «alerta» atribuye la facultad a SENAPRED. REFUTADO.
- **501** «MINVU clasifica los ZR-5 como remoción en masa»: 6 de 8 no tocan ningún polígono de
  remoción; «quebrada» = fluvial es coherente con `araucania.yaml:86-89`. REFUTADO.
- **314** «`TOL_INLIER_M` es sub-píxel»: 3,88-14,15 px en los 20 planos publicados. REFUTADO.
- **503** ×1,95 → ×2,5-3,3 medido sobre lo publicado (el defecto de método sí se confirma).
- **304** 14 % → 5,2 % con muestreo declarado (el defecto sí se confirma).
- **508** la mancha de 70 ha a 724 m no existe; sobre 700 m hay 28 polígonos, el mayor 4,7 ha.
- **608** «17 huecos» en el encargo eran 113 (contados sobre el artefacto).

---

## 3. VERIFICADO LIMPIO

Lo que se miró a propósito y está sano vale tanto como lo roto; nadie tiene que volver a mirarlo
hasta que cambie.

- **Las tres pruebas del proyecto** corren hoy y dan 63 / 151 / 273.
- **El ray-casting del visor** (`app.js:145-169`): 13.308 puntos adversariales y aleatorios
  (semilla 20260906) más 160.280 puntos del verificador sobre las seis capas, **0 discrepancias**
  con shapely, incluidas las 842 features inválidas; independiente de la orientación de anillos;
  excluye huecos; MultiPolygon correcto. El cero está validado: con `dentroAnillo` anulada el
  comparador ve 497 discrepancias en 2.508 puntos.
- **Georreferenciación de las tres láminas**: las dos de Angol coinciden entre sí con corrimiento
  óptimo (0, 0) m; SENAPRED a 12-37 m en Angol, 4 de 6 a 0 m en Catripulli; 66-87 % del área
  derivada cae en GORE MÁXIMA; RMSE 4,94 m del AR-2a reproducido (residuos 3,48 / 6,36 / 4,56 m).
- **Control positivo, negativo y guardián del vectorizador** con lámina sintética: pasan (§1).
- **Detección de trama AR-2a**: 154,9 marcas/ha dentro de lo publicado vs. 3,0 fuera (×52).
- **Filtro de la capa A**: 0 publicados sin vocabulario hídrico; `tipo_hidrico` sin `null` (57
  fluvial / 3 anegamiento / 2 litoral / 1 napa); 0 polígonos inválidos entre los 63.
- **Máscara de terreno de la capa B llegó al artefacto**: 0 polígonos > 1.200 m, 0 con
  pendiente > 5°, 0 a ≤ 0 m (controles sintéticos Llaima y mar contados).
- **Privacidad (§7.5)**: sin analítica, sin cookies, sin beacons; `esc()` aplicado en todos los
  `innerHTML` que interpolan dato; `AbortController` en las sugerencias.
- **Fuera de región**: «este sitio no tiene nada que decir», no «sin riesgo», y no se puede
  compartir una ficha vacía. **Modo sin señal** con las 10 capas de datos cargadas desde la caché.
- **Procedencia** en los 9 productos publicados; **EPSG:4326** en los 46 GeoJSON; **ninguna ruta,
  puerto ni máquina** atada a este computador; el arreglo del script 10 (`a6c08f1`) está; 07 y 12
  fusionan sus índices y 18 escribe por id; `fechaLarga` no corre el día por UTC; §7.3 (autoría y
  «dejar de hacer falta») cumplido; cifras de portada calculadas del dato.

---

## 4. Cola de validación en campo

ID · qué mirar · qué decide · qué desbloquea · de dónde sale.

| ID | Qué mirar | Qué decide | Qué desbloquea | Fuente |
|---|---|---|---|---|
| C-01 | Ortofoto o visita a lon −72,7038 lat −37,834 (Angol, 2 rectángulos de 6 ha) | Confirmar que es campo sin cauce: son la leyenda | F-03: `excluir_y` en las tres láminas y regenerar | 701 |
| C-02 | Esteros de los cerros al oeste de Angol que la lámina pinta «Alto» y no tienen polígono (`evidencia_laminas/angol2013_huerfanos_x05.png`) | Si son cauces con riesgo real, `ancho_minimo_px` baja a 0-2 y el río se excluye sólo por color | F-04 grosor | 703, 302 |
| C-03 | Abrir `Plano_Zonificacion_Vialidad-PRC_09201-2.pdf` y leer sus vértices | Si trae AR-2a al sur del pueblo, se vectoriza con 3+ vértices | F-05; paquete Malleco | 704 |
| C-04 | Catripulli, sector Casa de Lata y Correo Viejo: caminar el borde de la mancha «alta» con GPS | Si las casas están a < 10 m del borde, la banda de borde es obligatoria y ≥ 2 px | F-09 | 603, 705 |
| C-05 | Tabla de mareas de Puerto Saavedra 3-4 ago 2026 vs. las 841 ha a ≤ 2 m del estuario | Si coincide con pleamar, se etiqueta «posible marea» o se excluye la franja | F-15 | 507 |
| C-06 | Imagen óptica (Sentinel-2) del 3-4 ago sobre los 13 polígonos SAR a 1.000-1.200 m | Nieve → bajar `altitud_max_m`; agua → dejar | F-15 | 508 |
| C-07 | Ordenanza del PRC Collipulli 2009, artículo de ZR-5 «franja por quebradas» | Fluvial o remoción → `TIPO_HIDRICO` | F-14 | 501 (refutado en parte) |
| C-08 | Consulta al servicio nacional del MINVU: ¿publica los 9 polígonos del servicio regional de Collipulli con otra etiqueta? | Si sí, la deduplicación los tapó y hay que comparar etiquetas | F-14 | P-11 reserva |
| C-09 | `evidencia_laminas/angol-prc-ar2a-lamina1_publicado_sobre_plano_x025.png`: zonas achuradas sin contorno rojo | Si hay AR-2a perdida, ajustar `densidad_minima`/`ventana_celdas` | F-04 trama | 706 |
| C-10 | Muestrear a ojo el «Medio» del cuerpo de la lámina de Angol (¿hay hillshade que oscurece?) | Si el color real es (32,102,213), declarar ese en la leyenda o subir tolerancia con control | F-04 tolerancia | verificación P-21 |
| C-11 | Un celular real en Catripulli: `pos.coords.accuracy` típico | Fija el ancho mínimo de la banda de borde para «mi ubicación» | F-09 | 304 |
| C-12 | Sin red en un celular, con la base satelital recordada | Confirmar lienzo vacío sin mensaje | F-06 | V-N05 |
| C-13 | Villa La Arboleda / Santa Teresita / Los Ríos (Angol): ¿están dentro del límite urbano y con AR-2a en la lámina 2? | Decide si el sur de Angol tiene plano legal en el visor | F-05, F-01 | 704 |

---

## 5. Tabla de decisiones para el dueño

| # | Decisión | Opciones | Recomendación |
|---|---|---|---|
| D-1 | ¿La capa derivada entra al veredicto? | (a) entra como bloque propio «A · derivado» con texto y su incertidumbre; (b) sigue sólo dibujada y la ficha lo dice; (c) se retira del visor hasta arreglar F-02/F-03/F-04 | **(c) ahora, (a) después**: hoy dibuja leyendas y no dice qué es; meterla al veredicto así empeora. Orden: F-03 → F-04 (núcleo) → regenerar → F-02 → F-01. |
| D-2 | Etiqueta de la capa derivada | (a) nueva categoría `A_derivado` en `comun.procedencia()`; (b) seguir en `A_normativo` con `estado_tramite=derivado` por polígono | **(a) más `estado_tramite` por polígono**: los 26 AR-2a llevan `vigente` con «trazado derivado»; los 137 de estudio, `estudio`. Es lo que REGLAS §1.3/§1.5 ya prometen. |
| D-3 | ¿GORE y JRC entran al nivel? | (a) sí, como nivel «modelado»; (b) no, pero el titular deja de decir «sin registros» cuando el modelo dice máxima | **(b)**: las capas no se fusionan (§1.3); el titular pasa a «Sin registros normativos ni observados; el modelo regional lo clasifica MÁXIMA». |
| D-4 | Banda de borde | (a) veredicto sigue binario; (b) «a menos de N m del borde» por capa, N = 2 × max(píxel, RMSE) | **(b)**: 15 m Angol, 11 m Catripulli, 10 m AR-2a, 70 m GORE; y mostrar `accuracy` del GPS. |
| D-5 | Grosor mínimo y núcleo | (a) dejar 4×4; (b) núcleo impar 5×5; (c) `ancho` 0-2 y excluir el río sólo por color, con control sintético | **(c) en Angol y Catripulli**, medido con `fidelidad_laminas.py` antes y después; la sintética exige desplazamiento 0. |
| D-6 | Lámina 09201-2 | (a) vectorizar ahora; (b) declarar «cobertura parcial» en el dato | **(a)** antes del paquete de Malleco; mientras, (b). |
| D-7 | Guardián de posición | (a) exigir 2 anclas verticales; (b) portar `georref_independiente.py` al script 18 como control automático contra SENAPRED y GORE (falla si < 1 punto a ≤ 100 m o < 50 % en GORE MÁXIMA/MEDIA) | **(b)**: es el control que desenmascaró a la DGA, y no depende de que la lámina tenga rótulos. |
| D-8 | Capa B | (a) hectáreas por unión de órbitas; `make_valid` al escribir; nombrar marea/estuario en la incertidumbre; `verificar()` sobre lo publicado | **todo (a)**; C-05 decide si el estuario se excluye. |
| D-9 | Paquete de Malleco para el practicante | (a) entregar hoy el de `20_paquete_practicante.py`; (b) regenerar después de D-1…D-7 con un LEEME por capa (fuente, año, estado legal, incertidumbre) | **(b)**: hoy heredaría leyendas como polígonos, `A_normativo` en lo derivado y `docs/REGLAS.md` fantasma en su LEEME. |
| D-10 | Botón «Buscar», texto compartido, `comunaDe`, SW sin red | arreglos directos sin decisión de diseño | hacerlos en la primera tanda; cada uno con su comprobación nueva en la e2e (§4.1). |

---

## 6. Prompt para la sesión siguiente

Copiar entero desde la línea siguiente.

---

Vas a ejecutar el **ciclo de arreglo** de la auditoría del 6-sep-2026 de **riesgomapas**
(`C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas`, rama
`visor-simple-y-laminas-vectorizadas`). Lee primero, enteros: `docs/auditorias/2026-09-06/INFORME.md`
(familias F-01…F-22, cola de campo C-xx, decisiones D-xx), `REGLAS.md`, `scripts/ORDEN.md` y
`GUIA_MAESTRA_AUDITORIAS.md` §6 (de la auditoría al arreglo). Reconstruye el estado **desde el
sistema**: `git log --oneline -15`, `git status`, y corre las tres pruebas (63 / 151 con 1 medio /
273; la e2e tarda 12 min, lánzala en segundo plano). Un verde que no corriste hoy es SOSPECHA.

Por qué importa: un vecino de Angol parado dentro del AR-2a del plan regulador vigente hoy lee
«no cae dentro de un área de riesgo», y hay dos rectángulos de 6 ha de «peligro Alto» publicados
en un potrero porque son la leyenda de la hoja. Quien decide con esto firma una compraventa.

Las decisiones **están tomadas** (tabla D del informe, columna Recomendación), tarea por tarea:
D-1 (c)→(a), D-2 (a), D-3 (b), D-4 (b), D-5 (c), D-6 (a), D-7 (b), D-8 (a), D-9 (b), D-10 sí.
No esperes confirmación.

Orden, un commit por defecto, con su línea base roja antes del verde y la misma familia de
pruebas después: **1** F-03 (`excluir_y` en las tres láminas; la sintética debe dar
`n_poligonos_en_leyenda` 0) → **2** F-04 núcleo y grosor (D-5; `verif_702_apertura.py` debe dar
desplazamiento 0; `fidelidad_laminas.py` antes/después) → **3** regenerar las tres láminas y
re-correr `georref_independiente.py` → **4** F-02 (`A_derivado` + `estado_tramite`) → **5** F-05
(lámina 09201-2, C-03/C-13) → **6** F-01 con D-3 y D-4, más comprobaciones nuevas en
`tests/auditoria_e2e.py` (consultar dentro de una lámina, leer el texto compartido, mirar
`lam-fill` y `jrc-fill`) → **7** F-11, F-07, F-10, F-06 (arreglos directos, cada uno con su prueba) →
**8** F-12 (script 19/09/20/14: entrada ausente → `SystemExit`) → **9** F-15 y F-14 (D-8; duplicado
Collipulli; ZR-3) → **10** F-08, F-13, F-16, F-17, F-18 → **11** F-21 documentación → **12** subir
`VERSION` en `web/sw.js` una vez al final del frontend → **13** regenerar el **paquete de Malleco**
con `20_paquete_practicante.py` y verificar conteos por capa y comuna contra `web/data/`, con un
LEEME por capa (D-9): es la entrega al practicante.

Límites: no borres nada que un informe dé por muerto sin `grep` en `tests/`, `scripts/` y `docs/`;
no crees documentos sin `ls` previo de la raíz y de `docs/`; los instrumentos viven en
`tools/auditoria/` y se corren con `PYTHONIOENCODING=utf-8`; usa el modelo que corresponde a cada
tarea (Opus para decidir y verificar, Sonnet para lo mecánico; Fable sólo para censos semánticos
grandes). Español de Chile. Al cerrar: actualizar «Estado» en `docs/PROXIMA_SESION.md`, pegar los
ítems de campo que cada arreglo declare en la cola C-xx y comprobar con `grep` que existen, y
dejar el prompt de la siguiente sesión. Si se compacta el contexto, preserva: el orden 1-13, las
decisiones D-1…D-10 como tomadas, los tres números de las pruebas, y qué paso está en línea base /
cambiado / verificado.

Nadie contesta a mitad. Si algo te bloquea, toma la opción conservadora, anótala en la tabla de
decisiones y sigue; termina el ciclo completo aunque un paso quede en SIN DATO.

---

*Fin del prompt.*

**Pendiente del dueño, fuera del ciclo:** revisar el visor juntos con este informe abierto (los
puntos de reproducción están en cada familia), y entregar el paquete de Malleco al practicante
sólo después del paso 13.
