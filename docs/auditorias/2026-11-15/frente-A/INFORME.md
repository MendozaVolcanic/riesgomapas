# Auditoría frente A: la lógica del veredicto del visor

- **Hora del servidor**: inicio 2026-11-15 08:11:40 (-0300), informe cerrado 2026-11-15 ~08:50 (-0300), según `date` en esta sesión.
- **Commit**: `ef2f534` en la rama `visor-simple-y-laminas-vectorizadas` (árbol limpio al empezar).
- **Modelo**: Claude Opus 5.5 (`claude-opus-5-5`), como subagente auditor.
- **Rango de IDs provisionales**: F-100 a F-120. Los IDs finales los pone el verificador.
- **Instrumentos nuevos** (todos en `tools/auditoria/`, prefijo `fA_`, cada uno con sus dos preguntas en el encabezado y con control): `fA_harness_evaluar.js`, `fA_veredicto_censo.py` + `fA_veredicto_censo.js`, `fA_texto_compartido.js`, `fA_detalle_sin_banda.js`, `fA_zoom_comuna.js`, `fA_precision_arrastrada.js`.
- **Salidas crudas** de cada instrumento en `docs/auditorias/2026-11-15/frente-A/salidas/`.

**Cómo se midió.** `fA_harness_evaluar.js` carga el `web/app.js` REAL en Node con los datos REALES de `web/data/`; sólo se reemplazan el DOM (por un objeto que absorbe todo) y `fetch` (por lectura de disco). Así se mide el visor y no una copia de su regla. Su control (`--control`) reproduce el caso F-01 de la auditoría anterior: `CONTROL Angol AR-2a derivado: alto | Estás en un área de riesgo por inundación del plan regulador | laminas 2 OK`.

**Qué NO miré.**
- No abrí el visor en un navegador real para estos hallazgos (salvo la corrida completa de `tests/auditoria_e2e.py`); todo lo demás es el código real ejecutado en Node. Lo que depende del dibujo en pantalla (colores, apilado) lo leí en el código, no lo vi.
- No medí la geometría de GeoIDE contra nuestras láminas (IoU, desplazamiento): es del frente B. Sólo bajé la capa 29 (Angol) para saber qué le dice el visor a la gente que vive dentro.
- No medí población expuesta a inundación: es del frente C. Uso el censo sólo para contar a cuántas personas les toca cada defecto, con el **punto representativo** de cada unidad censal (la persona se cuenta entera donde cae ese punto). Son órdenes de magnitud del alcance del defecto, no cifras de exposición.
- No revisé Collipulli, Renaico ni Curarrehue en GeoIDE; el texto del visor afirma lo de Angol **y** Curarrehue, y sólo verifiqué Angol.
- No verifiqué en campo ni contra ortofoto ningún borde.
- No miré el modo sin red ni el service worker.

---

## En una pantalla

1. El veredicto consulta las siete capas, pero la **banda de borde se explica sólo en el resumen**: la pestaña de detalle, la que se imprime como PDF «para mostrárselo a quien te vende el terreno», dice «no cae dentro» bajo un titular de borde en **532 de 532** casos medidos (F-100).
2. **Elegir tu comuna da «Sin registros en las fuentes consultadas» en 22 de 30 comunas** que suman 335 registros (Pucón con 26, Teodoro Schmidt con 32): el visor responde sobre el centro de una caja que nadie eligió (F-101).
3. El **texto que se reenvía no nombra la capa que decidió** cuando decide la lámina derivada, el modelo, el borde o el campamento: sale el titular en mayúsculas sin fuente ni año (F-102).
4. **Angol sí tiene vectorial oficial** (GeoIDE, 81 polígonos, Resolución 40 del 14/10/2022) y el visor afirma lo contrario en cinco lugares, incluida la solicitud por Ley 20.285; ~1.335 personas viven dentro de un área hídrica de GeoIDE donde el visor no muestra ninguna capa A (F-103).
5. El nivel único (alto, medio, bajo, sin dato) **sigue resumiendo capas distintas en un color**, y donde manda el registro D el modelo regional queda callado en el resumen para ~71.900 personas con amenaza máxima; además el «sí miró» del satélite alcanza a ~131.500 personas en terreno que el propio método excluye (F-104, F-109, F-110).

---

## Hallazgos (ordenados por gravedad, lo peor primero)

### F-100 · El detalle imprimible contradice al titular de borde y no explica la banda
- **ARCHIVO:LÍNEA**: `web/app.js:752-758` (la explicación de la banda vive sólo en `porQue`, que usa `resumen`), `web/app.js:870-886` y `:931-949` (`render` no lee `res.borde`), `web/index.html:193-197` («Imprimir o guardar como PDF ... mostrárselo a quien te vende el terreno»).
- **QUÉ PASA**: cuando el titular es «Estás justo en el borde de un área marcada como inundable», la pestaña de detalle repite el titular y debajo, en el bloque A, dice «Este punto no cae dentro de un área de riesgo por inundación declarada en el plan regulador», sin la distancia ni la incertidumbre. `grep -n "res\.borde" web/app.js` sólo encuentra la línea 752 (en `porQue`).
- **CÓMO SE VE**: el PDF que la persona lleva a la Dirección de Obras o al vendedor tiene un titular de borde y una frase negativa debajo; el vendedor lee la frase negativa.
- **CÓMO REPRODUCIRLO**: `node tools/auditoria/fA_detalle_sin_banda.js`
- **SALIDA CRUDA**:
  ```
  CONTROL (dentro de derivado, el detalle trae «±»): OK
  puntos con titular de borde: 532
    detalle SIN explicación de la banda: 532
    ... y además con «Este punto no cae dentro de un área de riesgo»: 532
    ejemplo: {"lon":-72.620737,"lat":-38.761129,"d":0.5,"capa":"normativa","titulo":"Estás justo en el borde de un área marcada como inundable"}
  ```
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 4.

### F-101 · Elegir una comuna responde «Sin registros» en 22 de 30 comunas con registros
- **ARCHIVO:LÍNEA**: `web/app.js:2252-2273` (`zoomComuna` consulta el centro de la caja envolvente de los puntos y lo etiqueta «(centro de los registros de la comuna)»); la prueba que lo cubre sólo mira que aparezca el nombre: `tests/auditoria_e2e.py:346-355` (`if "angol" in t and len(t) > 60`).
- **QUÉ PASA**: el centro de la caja es un punto que nadie eligió y suele caer lejos de todo registro. El veredicto se calcula ahí con los mismos titulares que para una casa.
- **CÓMO SE VE**: quien escribe «Pucón» y elige la comuna lee «SIN REGISTROS EN LAS FUENTES CONSULTADAS» para una comuna con 26 puntos críticos; Curarrehue (18, de ellos 17 crónicos según `estado-comunas.json`) igual.
- **CÓMO REPRODUCIRLO**: `node tools/auditoria/fA_zoom_comuna.js`
- **SALIDA CRUDA** (extracto):
  ```
  TEODORO SCHMIDT    puntos= 32  a1,5km= 0  sindato Sin registros en las fuentes consultadas
  PUCÓN              puntos= 26  a1,5km= 0  sindato Sin registros en las fuentes consultadas
  FREIRE             puntos= 26  a1,5km= 0  sindato Sin registros en las fuentes consultadas
  CURARREHUE         puntos= 18  a1,5km= 0  sindato Sin registros en las fuentes consultadas
  COLLIPULLI         puntos= 10  a1,5km= 0  sindato Sin registros en las fuentes consultadas
  comunas con registros: 30; titular «sin dato» al elegir la comuna: 22 (335 registros en esas comunas)
  CONTROL (punto crítico más cercano al centro no es «sin dato»): OK
  ```
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 4.

### F-102 · El texto que se reenvía no nombra la evidencia que decidió el titular
- **ARCHIVO:LÍNEA**: `web/app.js:1327-1384` (`textoFicha` sólo escribe capa B, capa A del MINVU y puntos D; no escribe láminas derivadas, banda de borde, GORE, JRC ni campamentos).
- **QUÉ PASA**: cuando decide la capa A derivada, el modelo, la banda o el punto está en un campamento, el texto compartido lleva el titular en mayúsculas y ninguna línea que lo respalde. En el caso derivado, la única evidencia que viaja es «El satélite miró este punto ... y no detectó agua», que se lee al revés del titular.
- **CÓMO SE VE**: por WhatsApp llega «ESTÁS EN UN ÁREA DE RIESGO POR INUNDACIÓN DEL PLAN REGULADOR» sin decir qué plan, de qué año, ni que el trazado es nuestro.
- **CÓMO REPRODUCIRLO**: `node tools/auditoria/fA_texto_compartido.js`
- **SALIDA CRUDA** (extracto):
  ```
  FALTA   A derivado AR-2a (efecto legal) @ -72.69911, -37.78179
        ESTÁS EN UN ÁREA DE RIESGO POR INUNDACIÓN DEL PLAN REGULADOR
        El satélite miró este punto el 3 de agosto de 2026 y no detectó agua.
        Puntos críticos registrados cerca:
        • 801 m - Inundación por desborde de cauce (riesgo Alto)
  FALTA   A derivado clase Medio (estudio 2013) @ -72.69639, -37.79894
  FALTA   GORE máxima sin puntos (modelo) @ -73.08786, -38.68423
  FALTA   Campamento en área de riesgo @ -72.61253, -38.75646
  NOMBRA  CONTROL + B observado @ -72.12303, -37.45710
  NOMBRA  CONTROL + A MINVU @ -72.62005, -38.76051
  controles positivos OK
  ```
  (en la salida real el separador de la línea del punto crítico es un guion largo; aquí se transcribió con guion simple por la regla de estilo).
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 4.

### F-103 · El visor afirma que Angol no tiene vectorial oficial, y GeoIDE lo publica
- **ARCHIVO:LÍNEA**: textos que ve la persona: `web/app.js:939-941` («no está en el vectorial que publica el MINVU ... el organismo todavía no la publica en formato consultable»), `web/app.js:748` («Ese documento existe sólo en papel»), `web/app.js:1008-1011` («esa cartografía existe sólo como figura impresa ... no es el borde del vectorial oficial del MINVU»), `web/index.html:120-123` («el organismo publicó esa cartografía sólo como figura impresa»), `web/data/estado-comunas.json` (Angol, `le_falta`: «no tiene su área de riesgo por inundación en el vectorial público del MINVU»), y la solicitud Ley 20.285 `web/app.js:677-683`, que con `poligonos_area_riesgo: 0` le pregunta al MINVU «por qué razón dicha cartografía no se encuentra disponible en el servicio público». Comentarios con la misma premisa: `web/app.js:449-451`, `:860`, `:952`, `:972-973`.
- **QUÉ PASA**: la capa `PRC_Angol_Area_de_riesgo` (GeoIDE, `IPT/PRC_Araucania/FeatureServer/29`) tiene 81 polígonos, 21 hídricos (10 AR-2a inundable, 11 AR-2b anegamiento), todos con `T_DO` Resolución, `N_DOC` 40, `P_DO` 14/10/2022. El visor no los consulta y dice que no existen. Quien vive dentro de un AR-2a de GeoIDE que nuestras tres láminas no cubren recibe, en el bloque A, «no cae dentro de un área de riesgo ... declarada en el plan regulador».
- **CÓMO SE VE**: un vecino de Angol fuera de las láminas pero dentro del AR-2a oficial lee «Registros de inundación a cierta distancia» (nivel bajo) y «no cae dentro». La solicitud por transparencia que el visor redacta parte de una premisa falsa.
- **CÓMO REPRODUCIRLO**: bajar la capa (GET público, sin credenciales) `https://geoide.minvu.cl/server/rest/services/IPT/PRC_Araucania/FeatureServer/29/query?where=1%3D1&outFields=*&outSR=4326&f=geojson&resultRecordCount=2000` a una carpeta propia, y luego `python tools/auditoria/fA_veredicto_censo.py --geoide RUTA_GEOJSON --salida RUTA_TEMPORAL.json`.
- **SALIDA CRUDA**:
  ```
  81 None None
  Counter({('AR-1c', ..., 'Resolución', '40', '14/10/2022'): 38, ('AR-1b', ...): 18, ('AR-2b', 'Áreas de Riesgo por Anegamiento', 'Resolución', '40', '14/10/2022'): 11, ('AR-2a', 'Áreas de Riesgo Inundables o Potencialmente Inundables', 'Resolución', '40', '14/10/2022'): 10, ('AR-1a', ...): 4})
  GeoIDE Angol: 81 polígonos, hídricos 21 (AR-2a 10, AR-2b 11)
  D6 dentro de AR hídrica GeoIDE Angol, sin capa A en el visor: 1.335 / 23 / 1  [Angol 1.335]
     ejemplo: {"lon":-72.69149,"lat":-37.81476,"n":258,"comuna":"Angol","titulo":"Registros de inundación a cierta distancia","nivel":"bajo"}
  D6a ... y es AR-2a inundable: 1.154 / 17 / 1  [Angol 1.154]
  ```
  (formato: personas / unidades censales / personas con agua de río; los «...» son nombres de zona que abrevié; el `None None` es `exceededTransferLimit` y `properties`, o sea, no hubo truncamiento).
- **CONFIANZA**: CONFIRMADO (textos leídos, capa bajada y contada en esta sesión). Las 1.335 personas son con punto representativo: orden de magnitud.
- **GRAVEDAD**: 4.

### F-104 · El nivel único resume capas distintas en un solo color
- **ARCHIVO:LÍNEA**: `web/app.js:471-522` (todas las ramas escriben el mismo `nivel`), `web/app.js:790` y `:882` (`v-${res.nivel}` es la única clase de color), `web/app.js:817` (un ícono por nivel).
- **QUÉ PASA**: `alto` sale de cinco fuentes distintas: agua observada (B), área legal del MINVU (A), plano legal derivado (A derivado), estudio sin efecto legal de clase Alto **o Medio** (A derivado, ver F-107) y uno o más registros municipales graves a 300 m (D). `medio` mezcla la banda de borde (incertidumbre geométrica de A o B) con «registro a menos de 500 m» (D). El titular sí distingue; el color y el ícono, que es lo que se lee primero y lo único que se ve de lejos, no. REGLAS §1.3 prohíbe la capa síntesis y el nivel funciona como una.
- **CÓMO SE VE**: un estudio de 2013 sin hidráulica, de clase «Medio», y agua medida por radar, se pintan con el mismo rojo y el mismo ⚠️.
- **CÓMO REPRODUCIRLO**: leer las ramas; el reparto de personas por rama: `python tools/auditoria/fA_veredicto_censo.py --geoide ... --salida ...`.
- **SALIDA CRUDA**:
  ```
  PERSONAS POR NIVEL: {"bajo":230746,"medio":121027,"alto":74788,"sindato":594872}
  POR CAPA QUE DECIDE (personas / unidades):
    D puntos (alto)            47.767 / 895
    A normativo MINVU          20.494 / 324
    A derivado                  6.038 / 69
    banda de borde              5.597 / 64
    B observado                   489 / 8
  ```
  De las 74.788 personas con nivel `alto`, 47.767 lo reciben por registros municipales a 300 m y no por estar dentro de ninguna mancha.
- **CONFIANZA**: CONFIRMADO (código leído, reparto corrido). **GRAVEDAD**: 3.

### F-105 · La banda de borde le gana a los registros graves y rebaja alto a medio
- **ARCHIVO:LÍNEA**: `web/app.js:496-503` (la rama `else if (borde)` va antes que `graves.length >= 1 || en(RADIOS.cercano).length >= 3`).
- **QUÉ PASA**: un punto a menos de 2 × incertidumbre del borde de un área, y con un registro Alto o Muy Alto a 300 m, recibe `medio` «Estás justo en el borde» en vez de `alto` «Tu sector tiene registro de inundaciones»; el «por qué» deja de mencionar los registros.
- **CÓMO SE VE**: estar cerca de un borde **baja** el nivel que daría estar lejos de él.
- **CÓMO REPRODUCIRLO**: `node tools/auditoria/fA_veredicto_censo.js --control` (caso sintético) y la corrida del censo.
- **SALIDA CRUDA**:
  ```
    OK    D1 detectado
  D1 borde rebaja alto->medio: 272 / 7 / 0  [Villarrica 96, Traiguén 84, Angol 55, Loncoche 37]
     ejemplo: {"lon":-72.66807,"lat":-38.25632,"n":84,"comuna":"Traiguén","titulo":"Estás justo en el borde de un área marcada como inundable","nivel":"medio"}
  ```
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 3 (pocas personas, pero el sentido del error es el malo).

### F-106 · La precisión del GPS se arrastra a una dirección elegida en las sugerencias
- **ARCHIVO:LÍNEA**: `web/app.js:1466-1469` (la acción de la sugerencia llama `consultar` sin poner `estado.precisionPos = null`), igual `web/app.js:2272` (`zoomComuna`); sí lo resetean `:1595` (`buscar`) y `:2024` (toque en el mapa).
- **QUÉ PASA**: tras «mi ubicación» con ±65 m, elegir una dirección sugerida ensancha la banda con ese GPS y el «por qué» dice «tu ubicación ±65 m» de una dirección escrita.
- **CÓMO SE VE**: la misma dirección da «Estás justo en el borde» o «Sin registros...» según si antes se tocó «mi ubicación».
- **CÓMO REPRODUCIRLO**: `node tools/auditoria/fA_precision_arrastrada.js` (ejecuta `sugerenciasDirecciones` y su `accion` reales con un Nominatim falso).
- **SALIDA CRUDA**:
  ```
  punto de prueba: -73.134459, -38.701075 (Carahue), borde MINVU a 30.0 m
  RUTA sugerencia tras GPS: precisionPos=65 nivel=medio titulo="Estás justo en el borde de un área marcada como inundable"
     «por qué» menciona «tu ubicación ±65 m»: true
  RUTA buscar() tras GPS:    precisionPos=null nivel=sindato titulo="Sin registros observados ni norma, pero un modelo sí marca este punto"
  DEFECTO CONFIRMADO: la misma dirección da «borde» por sugerencia y no por buscar(); la precisión del GPS se arrastró.
  ```
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 3.

### F-107 · Una clase «Medio» de un estudio sin efecto legal sube a nivel alto
- **ARCHIVO:LÍNEA**: `web/app.js:488-495` (cualquier polígono derivado deja `nivel = 'alto'`, sin mirar `clase`).
- **QUÉ PASA**: Angol 2013 «Medio» (29 polígonos) y Curarrehue «Susceptibilidad media» (18) dan el mismo nivel que la huella observada. El estudio distingue dos clases y el veredicto borra la distinción. En pantalla el «por qué» dice «marcó esta zona como medio» bajo un titular rojo.
- **CÓMO SE VE**: alto y medio del documento comunal se ven idénticos en el titular y el color.
- **CÓMO REPRODUCIRLO**: corrida del censo; conteo de clases con el script inline de la sesión (`clase`, `incertidumbre_borde_m` por comuna).
- **SALIDA CRUDA**:
  ```
  ('ANGOL', 'Medio', 7.7, False, 'derivado', '2013') 29
  ('CURARREHUE', 'Susceptibilidad media', 5.3, False, 'derivado', '2025') 18
  D2 clase media -> nivel alto: 773 / 12 / 72  [Curarrehue 662, Angol 111]
  ```
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 3.

### F-108 · Campamentos: capa dibujada que no entra al veredicto
- **ARCHIVO:LÍNEA**: `web/app.js:527` (se calcula y se devuelve), `web/app.js:471-522` (ninguna rama lo usa), `web/app.js:1218-1231` (el detalle sí dice «Este punto está dentro del campamento ... en área de riesgo por inundación»).
- **QUÉ PASA**: es la única de las ocho casillas (`CASILLAS_CAPAS`, `web/app.js:273-274`) que no influye ni en el nivel ni en el titular ni en el «por qué». Dentro de un campamento que el catastro marca en área de riesgo, el titular puede ser «Sin registros en las fuentes consultadas».
- **CÓMO SE VE**: Temuco, campamento La Ribera: resumen «Sin registros», detalle «dentro del campamento ... 33 hogares en área de riesgo por inundación».
- **CÓMO REPRODUCIRLO**: corrida del censo.
- **SALIDA CRUDA**:
  ```
  D3 campamento en AR sin nivel alto: 341 / 4 / 0  [Temuco 320, Collipulli 21]
  D3b campamento en AR con «sin registros»: 124 / 2 / 0  [Temuco 103, Collipulli 21]
     ejemplo: {"lon":-72.61139,"lat":-38.7172,"n":103,"comuna":"Temuco","titulo":"Sin registros en las fuentes consultadas","nivel":"sindato"}
  ```
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 3.

### F-109 · «El satélite sí miró este punto» en terreno que el método excluye
- **ARCHIVO:LÍNEA**: `scripts/14_sar_huella_observada.py:109` (`DECIMACION_COBERTURA = 32`) y `:594` (un bloque cuenta como observado si **un cuarto** de sus píxeles lo fue); `web/app.js:1070-1077` («El satélite sí miró este punto ... y no detectó agua»). La máscara de terreno es `scripts/sar.py:248-254` (pendiente ≤ 5°, 0,5 m < altura ≤ 1.200 m).
- **QUÉ PASA**: la cobertura publicada es un contorno de bloques de 32 × 0,00045° (~1,3 a 1,6 km). Dentro de él hay terreno con pendiente > 5° donde el método nunca habría marcado agua. Ahí el visor dice «sí miró y no detectó agua»; el dato dice «no podía ver».
- **CÓMO SE VE**: quien vive en una terraza o ladera dentro de la cobertura lee que el satélite miró su punto.
- **CÓMO REPRODUCIRLO**: corrida del censo (muestrea `terreno.tif` con la misma regla que `terreno_apto`).
- **SALIDA CRUDA**:
  ```
  terreno apto (pendiente ≤ 5.0°, 0.5 < altura ≤ 1200.0 m): 14279 de 17107 puntos
  D5 «sí miró» en terreno que el radar excluye: 131.520 / 1793 / 4.326  [Temuco 32.869, Padre Las Casas 11.490, Villarrica 10.838, Carahue 9.105]
  ```
- **CONFIANZA**: CONFIRMADO el mecanismo; la cifra es SOSPECHA de magnitud: el punto representativo cae en un píxel de 40 × 50 m y la pendiente de un píxel urbano puede no ser la de la casa. **GRAVEDAD**: 3.

### F-110 · El modelo regional queda callado en el resumen cuando hay un registro lejano
- **ARCHIVO:LÍNEA**: `web/app.js:501-509` (las ramas D van antes de `gore.length || enMancha`, `:510`), `web/app.js:759-770` (`porQue` igual).
- **QUÉ PASA**: la decisión D-3(b) de la auditoría de septiembre («el titular deja de decir sin registros cuando el modelo dice máxima») se aplicó sólo cuando no hay ningún registro a 1,5 km. Con un registro a 501-1.500 m, el titular es «Registros de inundación a cierta distancia» y el «por qué» habla sólo de esa distancia, aunque el punto esté en amenaza máxima del GORE.
- **CÓMO SE VE**: la persona lee «el registro más cercano está a 1.200 metros» y nada del modelo, salvo que abra el detalle.
- **CÓMO REPRODUCIRLO**: corrida del censo.
- **SALIDA CRUDA**:
  ```
  D4 GORE máxima callada en el resumen: 71.877 / 978 / 299  [Pitrufquén 10.053, Angol 9.872, Freire 6.173, Nueva Imperial 5.813]
     ejemplo: {"lon":-72.69831,"lat":-37.78934,"n":1499,"comuna":"Angol","titulo":"Registros de inundación a cierta distancia","nivel":"bajo"}
  ```
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 3.

### F-111 · El año del AR-2a de Angol se muestra como «2026» y el instrumento es de 2022
- **ARCHIVO:LÍNEA**: `web/data/laminas/vectorizadas.geojson` (54 polígonos AR-2a con `anio: "2026"`), `web/app.js:862` y `:1012` (`atribucion` imprime `Año: ${p.anio}` sin calificar).
- **QUÉ PASA**: el commit `4d66776` aclaró en el paquete que 2026 es el año de la ordenanza, pero el visor imprime «Año: 2026» a secas. GeoIDE declara el instrumento como Resolución 40 del 14/10/2022.
- **CÓMO SE VE**: «Fuente: Plan Regulador Comunal de Angol ... · Año: 2026».
- **CÓMO REPRODUCIRLO**: `renderDetalle` del arnés en (-72.69911, -37.78179).
- **SALIDA CRUDA**:
  ```
  -72.69911 -37.78179 laminas AR-2a/2026/8.3
      Plan Regulador Comunal de Angol, Plano de Zonificación y Vialidad lámina PRC 09201-1, ... ordenanza local actualizada a marzo de 2026  |  2026
  ```
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 3.

### F-112 · La banda de borde de la capa B usa 10 m y el dato declara ~40 × 50 m
- **ARCHIVO:LÍNEA**: `web/app.js:202` y `:214-217` (sin `incertidumbre_borde_m`, se usa `BORDE_MINIMO_M = 10`), `web/app.js:460-467` (la capa `observada` entra a la banda con 2 × 10 m); `config/araucania.yaml:150-156` (rejilla de 0,00045°, «≈40 × 50 m»); procedencia de `web/data/sar/huella-observada.geojson`: «Resolución de salida ~50 m: no apto para decisión predial». Además `web/app.js:1027-1028` dice «detectó agua **justo** en este punto».
- **QUÉ PASA**: la banda subestima la incertidumbre del borde del radar unas 2 a 2,5 veces, y el texto afirma una precisión de punto que el dato niega.
- **CÓMO SE VE**: a 25 m de una huella de 50 m de píxel, «Sin registros»; dentro, «el agua llegó hasta acá».
- **CÓMO REPRODUCIRLO**: leer las líneas citadas; conteo de `incertidumbre_borde_m` en la capa SAR: `Counter({None: 1075})`.
- **SALIDA CRUDA**: `Counter({None: 1075})` (los 1.075 polígonos SAR no declaran incertidumbre de borde).
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 3.

### F-113 · Vuelve la mitad de F-07: el texto compartido recorta a 3 puntos sin decir cuántos hay
- **ARCHIVO:LÍNEA**: `web/app.js:1360-1369`.
- **QUÉ PASA**: se listan los 3 más cercanos y no se dice el total.
- **CÓMO REPRODUCIRLO**: `node tools/auditoria/fA_texto_compartido.js`
- **SALIDA CRUDA**:
  ```
  punto con más registros a 1,5 km: -71.942799, -39.278511
  RECORTE: puntos a ≤1500 m = 15; líneas «•» de puntos en el texto = 3; ¿dice el total? false
  ```
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 2.

### F-114 · Con dos láminas superpuestas, la atribución y la incertidumbre salen de la primera
- **ARCHIVO:LÍNEA**: `web/app.js:1010-1012` (usa `res.laminas[0]`), `web/app.js:493-495` (el titular lo decide `some(efecto_legal)`).
- **QUÉ PASA**: en (-72.6867, -37.78499) el titular lo decide el AR-2a legal (±8,3 m, ordenanza 2026), pero el bloque dice «±7,7 m» y la fuente y año del estudio de 2013. Una sola atribución para dos fuentes distintas.
- **SALIDA CRUDA**:
  ```
  -72.6867 -37.78499 laminas Alto/2013/7.7 ; AR-2a/2026/8.3
     El borde tiene ±7,7 m de incertidumbre, y no es el borde del vectorial oficial del MINVU.
      Estudio de Riesgo, Actualización Plan Regulador Comunal de Angol, I. Municipalidad de Angol, septiembre de 2013  |  2013
  ```
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 2.

### F-115 · El JRC dice «fuera de la mancha» sin decir que no modela cuencas pequeñas
- **ARCHIVO:LÍNEA**: `web/app.js:1182-1191`; la procedencia de `web/data/jrc/rp100.geojson` sí lo declara: «No modela drenaje urbano ni cuencas pequeñas».
- **QUÉ PASA**: «queda fuera» en un estero que el modelo no representa es «nadie modeló aquí», no «no se inunda». La ficha menciona la resolución y el drenaje urbano, no las cuencas pequeñas.
- **CONFIANZA**: CONFIRMADO (lectura). **GRAVEDAD**: 2.

### F-116 · La banda sólo existe por fuera
- **ARCHIVO:LÍNEA**: `web/app.js:459` (sólo se busca borde si no está dentro de nada).
- **QUÉ PASA**: a 1 m por dentro de un polígono derivado de ±8,3 m, «Estás en un área de riesgo» sin matiz; a 1 m por fuera, «Estás justo en el borde». La incertidumbre es simétrica y la respuesta no. Para un lote donde el área legal condiciona el permiso, también importa estar dudosamente dentro.
- **CONFIANZA**: CONFIRMADO (lectura). **GRAVEDAD**: 2.

### F-117 · El tope de búsqueda de borde trunca bandas mayores de 10 m (latente)
- **ARCHIVO:LÍNEA**: `web/app.js:464-466`: `tope = BORDE_MINIMO_M * 2 + precision`, pero la condición usa `incertidumbreBorde(b.f) * 2 + precision`.
- **QUÉ PASA**: hoy la mayor incertidumbre declarada es 8,3 m, así que no se activa. Cualquier capa futura con más de 10 m (por ejemplo, si la capa B declara sus ~50 m, como pide F-112) quedaría recortada a 20 m sin aviso.
- **SALIDA CRUDA**: valores de `incertidumbre_borde_m` en láminas: 7.7, 8.3, 4.6, 5.3.
- **CONFIANZA**: CONFIRMADO (lectura). **GRAVEDAD**: 1 hoy, 3 si se arregla F-112 sin esto.

### F-118 · El comentario «REGLA DE DECISIÓN» describe sólo los puntos
- **ARCHIVO:LÍNEA**: `web/app.js:3-14`.
- **QUÉ PASA**: la regla escrita en cabecera omite B, A, A derivado, banda y modelo. Quien lea el código para saber «exactamente por qué lo dijo» lee una regla vieja.
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 1.

### F-119 · «amenaza maxima» sin tilde en el resumen
- **ARCHIVO:LÍNEA**: `web/app.js:774` y `:777-778` (`String(clase).toLowerCase()`), contra `:1201`, que sí traduce a «máxima».
- **SALIDA CRUDA**: `por qué (pantalla): ... el modelo regional de 2016 lo clasifica como amenaza maxima.`
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 1.

### F-120 · Detalles de rotulado
- `web/index.html:148-153`: «Campamentos en área de riesgo» va bajo «Lo que reportó el municipio», pero la fuente es el Catastro Nacional de Campamentos del MINVU (procedencia de `campamentos-inundacion.geojson`).
- El mar dentro del recuadro de la región recibe veredicto: (-73.6, -38.8), frente a Saavedra, sale `sindato | Sin registros en las fuentes consultadas` (salida del control del arnés) en vez de «fuera de alcance».
- **CONFIANZA**: CONFIRMADO. **GRAVEDAD**: 1.

---

## Propuestas de mejora de la lógica (PROPUESTA, no defecto)

1. **Separar el color del nivel por tipo de evidencia.** En vez de un nivel síntesis, un titular con hasta tres renglones fijos: «La norma dice», «Se midió», «El municipio registró», cada uno con su propio estado (dentro, en el borde, fuera, sin cobertura). Resuelve F-104 y F-107 sin inventar equivalencias.
2. **Cuatro estados por capa, no dos**: dentro, borde, fuera **con cobertura**, y **sin cobertura** (nadie midió aquí). La capa A derivada necesita su huella de cobertura (la extensión de cada lámina) para poder decir «fuera de la lámina» en vez de «no cae dentro»; la capa B necesita la cobertura a resolución del dato (sin bloques de 32 px) o al menos la máscara de terreno recortada.
3. **Banda simétrica** (dentro y fuera) y con la incertidumbre declarada por la capa, incluida la capa B (~50 m) y el MINVU cuando se sepa.
4. **Elegir una comuna no debería producir un veredicto de punto**: debería abrir el bloque «Con qué cuenta» de la comuna, que es lo que el propio código (`web/app.js:582-588`) dice que es la unidad que se comparte.
5. **GeoIDE como capa A normativa**, separada de la derivada y de la del servicio nacional, con su `P_DO` como año del instrumento. Donde GeoIDE y la lámina derivada coinciden, la derivada pasa a ser verificación, no evidencia.
6. **Censo por manzana en la ficha, no en el nivel.** Agregar «en tu manzana viven N personas; X sacan agua del río» como inventario (categoría `inventario`/D), sin que cambie el veredicto. Lo que sí cambia la lógica es el **reparto por área** para decir cuánta gente de la comuna vive dentro de cada capa, publicado siempre como rango (memoria del proyecto: 4 % a 55 % en Angol según el criterio).
7. **`textoFicha` derivado de las mismas ramas que `porQue`**: una línea por capa que decidió o que contradice, para que el texto compartido no pueda quedarse atrás del titular (F-102).

---

## SEGUIMIENTOS

- **Curarrehue en GeoIDE** (frente B): el visor afirma que Curarrehue tampoco tiene vectorial (`web/app.js:449-451`, `:972-973`, `estado-comunas.json`). No lo verifiqué.
- **Collipulli y Renaico**: el traspaso dice 68 y 20 polígonos en GeoIDE contra 38 y 1 en el visor. No medí qué le dice el visor a quien vive en los que faltan; el mismo `fA_veredicto_censo.py --geoide` sirve con esas capas.
- **Prueba ciega en e2e**: `tests/auditoria_e2e.py:346-355` da OK a «elegir una comuna entrega ficha» con sólo ver el nombre; no mira el titular (F-101).
- **e2e con 1 falla fuera de mi eje**: `[ALTA] plano sobre el mapa [móvil]: se pulsó el botón y no se agregó ninguna capa de imagen` (284 OK, 1 hallazgo; salida en `salidas/auditoria_e2e.txt`). Corrí una sola vez: no sé si es intermitente. Nota: esa corrida escribió capturas en `data/processed/auditoria/`, que es el comportamiento normal del test.
- **F-109 con reparto por píxel**: repetir D5 con la fracción de la manzana apta, no con el punto representativo.
- **Cola de campo**: un punto de D6 (-72.69149, -37.81476, Angol, 258 personas) para comprobar sobre el plano oficial que está dentro del AR-2a de GeoIDE y fuera de nuestras láminas.

## VERIFICADO LIMPIO

- **Las siete capas de evidencia se consultan** (vara: `web/app.js:437-454` calcula `areas`, `sar`, `coberturaSar`, `laminas`, `gore`, `enMancha`; `:527` campamentos). F-01 de septiembre no volvió: el control del arnés da `alto | Estás en un área de riesgo por inundación del plan regulador | laminas 2 OK`.
- **El «sin registros» con modelo dice que hay modelo** cuando no hay registros a 1,5 km (vara: titular `Sin registros observados ni norma, pero un modelo sí marca este punto` en `fA_texto_compartido.js`; 210.093 personas en esa rama según el censo). Lo que falta es el caso con registro lejano (F-110).
- **El texto compartido lleva el «OJO» en sin dato** (vara: F-07 de septiembre; en la salida de `fA_texto_compartido.js` el caso GORE trae «OJO: que no haya registro NO significa que acá no se inunde»).
- **Fuera de la región no hay veredicto** (vara: `web/app.js:1556` llama `renderFuera` antes de `evaluar`).
- **La capa B distingue «vio agua», «miró y no vio», «no miró» y «no hay capa»** (vara: `web/app.js:1024-1120`, cuatro ramas escritas). Lo que falla es el alcance de «miró» (F-109), no la existencia de los casos.
- **GORE: ningún MAXIMA queda tapado por un MEDIA anterior** (vara: `tools/auditoria/solape_gore_y_extension_jrc.py`, `MAXIMA con punto representativo dentro de un MEDIA: 0`, con su control artificial `(1, 1)`).
- **JRC: el recorte llega al este de la región** (misma corrida: `¿el recorte llega al este del bbox (−70,90)? True`; el agua modelada termina en lon −71,65 porque el modelo no ve más, no porque falte recorte).
- **El fenómeno se nombra en el titular** para anegamiento, napa y litoral (vara: control positivo A MINVU de `fA_texto_compartido.js`: `Estás en un área de riesgo por anegamiento del plan regulador`).
- **Pruebas del repo**: `python -m pytest tests/ -q` dio `64 passed in 19.11s`.

## SIN DATO

- **Cobertura del GORE**: no medí la unión de sus clases contra el contorno regional. La memoria del proyecto dice que cubre la región (3,16 M ha), pero no lo comprobé en esta sesión, así que no puedo afirmar que «no clasifica este punto en sus dos categorías más altas» (`web/app.js:1202-1203`) sea siempre «se modeló y salió bajo» y no a veces «no se modeló».
- **Exactitud del borde del MINVU**: el visor le asume 10 m (`web/app.js:198-202`, declarado como elección propia). No hay dato de la fuente para contrastarlo.
- **Precisión GPS real en celulares de la región** (C-11 de septiembre): sigue sin medir.
- **Población por reparto de área para cada defecto**: todas las cifras de personas de este informe son con punto representativo.
