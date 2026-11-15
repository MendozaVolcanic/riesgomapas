# Verificación del frente A (F-100 a F-120)

Verificador con contexto limpio. Commit base ef2f534 más trabajo sin commitear. Todo lo medido sale de comandos corridos en esta sesión; las salidas crudas están en `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\docs\auditorias\2026-11-15\verificacion-A\salidas\`.

## Orden de trabajo (para que un tercero lo repita)

1. Leí `web/app.js`, `web/index.html`, `web/style.css`, `config/araucania.yaml` y `scripts/14_sar_huella_observada.py`.
2. Escribí los caminos de ruptura de los 21 hallazgos en `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\docs\auditorias\2026-11-15\verificacion-A\CAMINOS_DE_RUPTURA.md`.
   sha256 = `2cec31366dc2cb5a5e1d039ff280f22bf0bfbcc215a085de5244ad466a387635`, calculado el 2026-11-15 08:41:50 -0300, ANTES de abrir `INFORME.md` y `hallazgos.csv`.
3. Corrí mis propias sondas (abajo). Después abrí `INFORME.md` para comparar.

Instrumentos nuevos (todos en `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\tools\auditoria\`, con sus dos preguntas en el encabezado y un control positivo):

| Instrumento | Mide |
|---|---|
| `vA_sondas.js` (F100 F101 F102 F105 F106 F110 F114 F117 F120) | ejecuta `app.js` real con el arnés `fA_harness_evaluar.js` |
| `vA_cobertura_vs_terreno.py` | F-109, terreno no apto dentro de la cobertura SAR publicada |
| `vA_geoide_ar2_vs_laminas.py` | F-103, área AR-2a y AR-2b de GeoIDE fuera de las láminas del visor |
| `vA_campamentos_vs_titular.js` | F-108, titular en el centro de cada campamento |
| `vA_borde_no_monotono.js` | F-105, mismo punto a 0, 60 y 120 m de un borde |
| `vA_clases_laminas_a_nivel.js` | F-107, nivel por clase de lámina |

Uso el arnés del auditor (carga el `app.js` real), pero las sondas, los controles y las cifras son míos. No re-corrí `fA_veredicto_censo.*` (las cifras de personas por nivel y por capa quedan SIN DATO para mí) ni `fA_precision_arrastrada.js` ni `fA_texto_compartido.js`: reproduje los mismos fenómenos con sondas propias.

## Resultados

| id | veredicto | gravedad mía |
|---|---|---|
| F-100 | CONFIRMADO EN PARTE | 3 |
| F-101 | CONFIRMADO | 4 |
| F-102 | CONFIRMADO | 3 |
| F-103 | CONFIRMADO | 4 |
| F-104 | CONFIRMADO EN PARTE (decisión de diseño) | 2 |
| F-105 | CONFIRMADO | 3 |
| F-106 | CONFIRMADO | 3 |
| F-107 | CONFIRMADO (decisión de diseño discutible) | 2 |
| F-108 | CONFIRMADO (diseño, con contradicción concreta) | 3 |
| F-109 | CONFIRMADO | 3 |
| F-110 | CONFIRMADO | 3 |
| F-111 | CONFIRMADO EN PARTE | 2 |
| F-112 | CONFIRMADO | 2 |
| F-113 | CONFIRMADO | 2 |
| F-114 | CONFIRMADO | 2 |
| F-115 | CONFIRMADO | 2 |
| F-116 | CONFIRMADO (consecuencia de diseño, en el lado prudente) | 1 |
| F-117 | CONFIRMADO (latente) | 1 |
| F-118 | CONFIRMADO | 1 |
| F-119 | CONFIRMADO | 1 |
| F-120 | CONFIRMADO | 1 |

### F-100 CONFIRMADO EN PARTE, gravedad 3

Caminos que probé: que el detalle sí explique la banda (no); que `render` lea `res.borde` (`grep` y lectura: sólo `porQue` en `web/app.js:752`); que lo impreso no sea sólo el detalle (sí, aquí está la parte que no se sostiene).

- Verdadero: en 407 de 407 puntos con titular de borde, la pestaña de detalle no trae «metros del borde», «adentro y afuera» ni «±», y en los 407 dice «Este punto no cae dentro de un área de riesgo». Control positivo (dentro de una lámina el detalle sí trae «±»): OK.
- Matiz que el auditor no dice: lo que se imprime no es sólo el detalle. `web/style.css:633` (`[role="tabpanel"][hidden] { display: block !important; }`) y `web/index.html:41,78,179` ponen `#respuesta` (resumen, con `porQue`) dentro de `#panel-respuesta`, que en papel se muestra. En los 407 casos el resumen sí dice «adentro y afuera no se distinguen». O sea, el PDF lleva la explicación, pero en otro bloque, arriba del que se contradice. No lo probé imprimiendo en un navegador: es por lectura de CSS (SOSPECHA razonada).
- Queda: la contradicción interna de la pestaña de detalle, que es lo que alguien lee si copia sólo esa pestaña.

```
== F-100 ...
  puntos con titular de borde: 407; detalle sin explicar banda: 407; resumen (panel que TAMBIEN se imprime) explica la banda: 407; detalle dice "no cae dentro": 407
  CONTROL (dentro de lámina el detalle trae ±): OK
```
Comando: `node tools/auditoria/vA_sondas.js F100`.

### F-101 CONFIRMADO, gravedad 4

Camino probado: que el instrumento del auditor mida otra cosa que lo que hace el visor. Llamé al `zoomComuna` real y leí lo escrito en `#respuesta`. Salida: «comunas con registros: 30; titular "Sin registros" al elegirlas: 22» (Pucón 26 puntos, Curarrehue 18, Freire 26, Teodoro Schmidt 32). Hay 32 comunas en `estado-comunas.json`; 2 no tienen registros. Además la «sin registros observados ni norma, pero un modelo sí marca este punto» sale en otras 5 comunas. La prueba e2e que lo cubre sólo exige `"angol" in t and len(t) > 60` (`tests/auditoria_e2e.py:354`): leído.

Comando: `node tools/auditoria/vA_sondas.js F101`.

### F-102 CONFIRMADO, gravedad 3

Corrí `textoFicha()` real en dos puntos. Dentro del AR-2a de Angol (-72.6867, -37.78499) el texto trae el titular «ESTÁS EN UN ÁREA DE RIESGO POR INUNDACIÓN DEL PLAN REGULADOR», luego «El satélite miró este punto el 3 de agosto de 2026 y no detectó agua» y un punto crítico a 499 m; ni plano, ni año, ni «trazado derivado», ni ±. En un punto de borde, el titular es «ESTÁS JUSTO EN EL BORDE…» y el cuerpo no menciona borde, distancia ni incertidumbre. La gravedad es 3 y no 4 porque el titular sí lleva la conclusión correcta; lo que se pierde es el respaldo (REGLAS §1.5).

### F-103 CONFIRMADO, gravedad 4

Consulté GeoIDE (capa 29) tres veces: 81 polígonos de Angol, todos con `P_DO` 14/10/2022, `N_DOC` 40, `T_DO` Resolución. Por zona: AR-1a 4, AR-1b 18, AR-1c 38 (remoción en masa), AR-2a 10 (inundable), AR-2b 11 (anegamiento). Por tanto «81 polígonos de área de riesgo» es cierto, pero sólo 21 son de agua; el auditor lo dice bien (21 hídricos).

Caminos: que «el vectorial del MINVU» del visor sea otro servicio. Lo es: el visor usa `prc_riesgo_nacional_visor_P` (procedencia de `web/data/areas-riesgo-inundacion.geojson`), donde Angol tiene 0 polígonos; así que «no está en el vectorial que publica el MINVU» es verdad de esa capa nacional. Lo falso es lo que se dice al lado: «el organismo todavía no la publica en formato consultable» (`web/app.js:939-941`), «el organismo publicó esa cartografía sólo como figura impresa» (`web/index.html:120-123`) y, lo más serio, la solicitud de transparencia que el visor redacta (`web/app.js:677-683`) le pregunta al MINVU «por qué razón dicha cartografía no se encuentra disponible en el servicio público de datos territoriales», cuando GeoIDE la sirve.

Medición propia de cuánto de GeoIDE no está en lo que el visor usa (control OK: 0 % contra sí misma, 100 % contra vacío):

```
GeoIDE ['AR-2a']: 282.21 ha; fuera de las láminas AR-2a del visor: 78.37 ha (27.8 %)
GeoIDE ['AR-2b']: 15.64 ha; fuera de las láminas AR-2a del visor: 14.06 ha (89.9 %)
AR-2a GeoIDE fuera de las láminas ENSANCHADAS 10 m (descuenta el error de borde ~8 m): 49.12 ha (17.4 %)
visor AR-2a: 225.22 ha
```
Comando: `python -I tools/auditoria/vA_geoide_ar2_vs_laminas.py RUTA_GEOJSON` (GeoJSON bajado de `.../FeatureServer/29/query?where=1=1&outFields=ZONA,NOM,P_DO&outSR=4326&f=geojson`). Las «1.335 personas» del auditor: SIN DATO para mí (no re-corrí el censo). Ver F-180.

### F-104 CONFIRMADO EN PARTE, gravedad 2

Verdad por lectura: `web/app.js:471-522` deja `nivel = 'alto'` desde radar, área MINVU, lámina y registros graves, y `:790` y `:882` pintan con `v-${res.nivel}`. Pero el titular y la etiqueta A/B/C/D sí distinguen la fuente, y un semáforo único es una decisión de diseño legítima. Que REGLAS §1.3 prohíba una capa síntesis lo dice el auditor; yo no lo releí en REGLAS (sólo ubiqué la línea 31 con las cuatro clases), así que esa parte queda SOSPECHA.

### F-105 CONFIRMADO, gravedad 3

En 582 puntos con titular de borde, 50 tienen un registro grave o 3 o más a 300 m (alto sin la regla de borde). Control de no monotonía, el mismo punto desplazado:

```
0 m medio | Estás justo en el borde de un área marcada como inundable | borde 3 graves300 1
60 m alto | Tu sector tiene registro de inundaciones | borde null graves300 1
120 m alto | Tu sector tiene registro de inundaciones | borde null graves300 2
```
Acercarse al polígono baja el nivel. Comandos: `PASO=3 node tools/auditoria/vA_sondas.js F105` y `node tools/auditoria/vA_borde_no_monotono.js`. El `porQue` de borde no menciona los registros (leído en `web/app.js:752-758`).

### F-106 CONFIRMADO, gravedad 3

`precisionPos` sólo se asigna en `web/app.js:71, 1595, 1627, 2024`. La acción de la sugerencia (`:1466-1469`) y `zoomComuna` (`:2272`) llaman `consultar` sin resetearlo. Medido: `precisionPos antes=80 despues de consultar()=80`. Efecto: la banda se ensancha con el GPS y `porQue` afirma «tu ubicación ±N m» de una dirección escrita. Es además la vía por la que F-105 se activa más seguido. Comando: `node tools/auditoria/vA_sondas.js F106`.

### F-107 CONFIRMADO, gravedad 2 (decisión de diseño discutible)

`web/app.js:488-495` no mira `clase`. Medido: Curarrehue «Susceptibilidad media» (sin efecto legal) da `alto` con titular «Estás dentro de la zona que el estudio… marcó como inundable», y el `porQue` dice «marcó esta zona como susceptibilidad media». El sesgo es hacia la prudencia, y el titular distingue norma de estudio; por eso 2. Nota: el punto de prueba en «Medio» de Angol cayó en solape con el AR-2a (ver F-114), así que ese caso no es limpio; el de Curarrehue sí.

### F-108 CONFIRMADO, gravedad 3 (decisión de diseño con una contradicción concreta)

`evaluar` calcula `campamentos` (`web/app.js:527`) y ninguna rama lo usa. Medido sobre el centro de cada uno de los 15 campamentos: 15 caen dentro de su polígono y 1 (Comunidad Indígena Urbana Wenehuen, riesgo «Inundación», 37 hogares) recibe el titular «Sin registros en las fuentes consultadas»; el detalle de esa misma ficha dice que el punto está en un campamento con 37 hogares en área de riesgo por inundación. Que la capa D no suba el nivel puede ser deliberado (REGLAS: las capas no se fusionan); lo que no es deliberado es que el titular niegue lo que el detalle afirma. Comando: `node tools/auditoria/vA_campamentos_vs_titular.js`. No verifiqué qué dice REGLAS sobre campamentos (sólo la línea 31).

### F-109 CONFIRMADO, gravedad 3

Muestreo de 20.000 puntos al azar dentro de los polígonos publicados de cobertura, leyendo `terreno.tif` con la regla de config (pendiente <= 5°, 0,5 m a 1200 m):

```
puntos DENTRO de la cobertura publicada: 20000; terreno NO apto: 6457 (32.3 %)
CONTROL puntos FUERA de la cobertura (mismo DEM): 20000; NO apto: 95.2 %
```
Mecanismo leído: `scripts/14_sar_huella_observada.py:109` (`DECIMACION_COBERTURA = 32`) y `:594` (cuarta parte). Parte del terreno no apto dentro de la cobertura es mar o laguna (altitud < 0,5) o ladera; no separé las causas. `web/app.js:1075` dice «sí miró este punto». Comando: `python -I tools/auditoria/vA_cobertura_vs_terreno.py`. Es una cifra por área, no por personas (la del auditor es por personas y no la re-corrí).

### F-110 CONFIRMADO, gravedad 3

Sobre puntos a 700 a 1300 m de cada registro: 767 casos de nivel «bajo» con GORE o mancha JRC, y el `porQue` ahí habla sólo del registro más cercano; ejemplo con GORE «MAXIMA»: «El registro más cercano de inundación está a 899 metros.» (-73.123908, -38.70824819942508). Leído: `web/app.js:759-770` no consulta `res.gore`. Comando: `PASO=1 node tools/auditoria/vA_sondas.js F110`.

### F-111 CONFIRMADO EN PARTE, gravedad 2

Dato: los AR-2a de Angol traen `anio: '2026'` y `fuente` «…ordenanza local actualizada a marzo de 2026» (`web/data/laminas/vectorizadas.geojson`, leído). GeoIDE: `P_DO` 14/10/2022, Resolución 40, para los 10 AR-2a. `atribucion` imprime `Año: ${p.anio}` (`web/app.js:862-865`). Lo que se sostiene: el visor muestra «Año: 2026» sin calificar. Lo que no: el 2026 no es un error de dato sino el año de la ordenanza, y la línea de fuente justo al lado lo dice. Es ambigüedad de rotulado, no cifra falsa. Que el instrumento sea «de 2022» descansa en el `P_DO` de GeoIDE; no vi la resolución misma.

### F-112 CONFIRMADO, gravedad 2

`Counter` propio: 0 de 1075 polígonos SAR declaran `incertidumbre_borde_m` (la sonda F117 lo imprime: `sar: declaran=0`). Entonces `incertidumbreBorde` devuelve `BORDE_MINIMO_M = 10` (`web/app.js:214-217`), con un comentario que justifica 10 m por la escala de un plan regulador (`:198-201`), y `config/araucania.yaml:150-152` declara la rejilla «≈40 × 50 m». Subestimación de la banda confirmada por lectura de las tres líneas. Bajo a 2 porque el lado negativo ya viaja con el aviso de que el radar «es la foto del instante». La frase «justo en este punto» (`:1027-1028`) la leí.

### F-113 CONFIRMADO, gravedad 2

`web/app.js:1360` (`slice(0, 3)`) y `:1363-1366`: lista 3 y cita la fuente sólo de `cerca[0]`; no hay total. Leído; no lo re-corrí con el punto de 15 registros del auditor.

### F-114 CONFIRMADO, gravedad 2

3 combinaciones de láminas superpuestas, las 3 con incertidumbre y año distintos, por ejemplo `[["Alto","2013",7.7],["AR-2a","2026",8.3]]`. `web/app.js:1010-1012` y `:749` usan `laminas[0]` (el estudio de 2013 va primero en el archivo). Comando: `node tools/auditoria/vA_sondas.js F114`.

### F-115 CONFIRMADO, gravedad 2

`web/app.js:1182-1191` menciona resolución, drenaje urbano y modelo de 2016, no cuencas pequeñas. La limitación está declarada en `docs/INVENTARIO_FUENTES.md:491` («subestima cuencas pequeñas») y `docs/PROPUESTA.md:276` (cuencas < 500 km²), que leí por grep; la procedencia del GeoJSON del JRC no la abrí.

### F-116 CONFIRMADO, gravedad 1

`web/app.js:459` sólo busca borde si no hay polígono que contenga el punto. Es asimétrico, pero el error cae hacia el lado de más aviso (adentro dice «alto»), así que el daño de decisión es menor.

### F-117 CONFIRMADO (latente), gravedad 1

Salida: `laminas: declaran=174, max=8.3, >10: 0`; áreas MINVU, SAR y GORE no declaran. `tope = BORDE_MINIMO_M * 2 + precision` (`:464`) frente a `incertidumbreBorde(b.f) * 2 + precision` (`:466`): sólo muerde si una capa declara más de 10 m.

### F-118 CONFIRMADO, gravedad 1

`web/app.js:3-14` describe sólo puntos a 300, 500 y 1500 m.

### F-119 CONFIRMADO, gravedad 1

Los valores del GORE son `MAXIMA` y `MEDIA` (`Counter({'MEDIA': 1863, 'MAXIMA': 676})`); `web/app.js:774` hace `toLowerCase()` y `:777` lo imprime, mientras `:1201` sí traduce a «máxima».

### F-120 CONFIRMADO, gravedad 1

`web/index.html:148-153` pone «Campamentos en área de riesgo» bajo «Lo que reportó el municipio»; `web/app.js:1222` dice «el catastro nacional». Mar: `(-73.6,-38.5) dentroDeRegion=true -> sindato: Sin registros en las fuentes consultadas` y `(-73.69,-37.4)` igual (ejemplo mío, el auditor usó otra coordenada). Que ese punto sea océano lo sé por la geografía de la costa de la región, no por una capa del repo.

## Hallazgos propios nuevos (rango F-180 a F-199)

### F-180 El visor no usa buena parte del AR-2a y nada del AR-2b que GeoIDE publica para Angol (relacionado con F-103, probable duplicado con el frente B)
- ARCHIVO: `web/data/laminas/vectorizadas.geojson` (sólo clase AR-2a, `origen_lamina: angol-prc-ar2a-lamina1`); `web/app.js:452`.
- QUÉ PASA: aun descontando 10 m de error de borde, 49,12 ha (17,4 %) del AR-2a de GeoIDE quedan fuera de las láminas del visor, y el AR-2b (anegamiento, 11 polígonos, 15,64 ha) queda fuera en un 89,9 %. Quien está ahí recibe «no cae dentro de un área de riesgo» o un nivel por registros.
- SALIDA: la de F-103 arriba. Comando: `python -I tools/auditoria/vA_geoide_ar2_vs_laminas.py RUTA_GEOJSON`.
- CONFIANZA: CONFIRMADO para el área; SOSPECHA de causa (las láminas derivadas pueden cubrir una lámina distinta del plano o tener un desfase mayor que 10 m; no lo separé). GRAVEDAD 4. Si el frente B ya lo midió, fundir con su ID.

### F-181 «con 0 hogares en área de riesgo» en la ficha de un campamento
- ARCHIVO: `web/app.js:1222-1225`.
- QUÉ PASA: «Generación 2» trae `hogares = 0` y la frase sale «registra con 0 hogares en área de riesgo por inundación»: o el catastro no cuenta a nadie (y entonces no es un campamento en riesgo) o el dato no es un conteo.
- SALIDA: `Generación 2 | Inundación | 0 | dentro: true | alto | ...` (`vA_campamentos_vs_titular.txt`).
- CONFIANZA: CONFIRMADO. GRAVEDAD 1.

## VERIFICADO LIMPIO (qué miré y está sano)

- El arnés carga `app.js` y las 8 capas reales (`capas cargadas: [440,174,2539,1075,65,15]`) y el control del Angol AR-2a da «alto»: el instrumento no está muerto.
- Las sondas de F-100, F-109 y F-103 traen control positivo que pasa (`CONTROL ... OK`; 95,2 % no apto fuera de la cobertura; 0 %/100 % contra sí misma/vacío).
- `dentroDeRegion` sí desvía lo que cae fuera del recuadro a `renderFuera` (`web/app.js:1556`): el defecto de F-120 es el recuadro, no la función.
- Rama `sar` y rama `areas` van antes que `laminas` y que el borde en `evaluar` (`web/app.js:472-495`); lo que gana al borde es lo esperado, salvo los registros graves (F-105).
- El resumen de «sin dato» agrega su aclaración al texto compartido (`web/app.js:1377-1380`): leí que `estado.ultimo.res.nivel` es la ruta correcta.
- GeoIDE capa 29: el conteo 81 y la distribución por zona coinciden con lo que declara el auditor (`vA_geoide_capa29_zonas.txt`).

## SIN DATO

- Las cifras de personas por nivel y por capa (`fA_veredicto_censo`): no re-corridas.
- Comportamiento de impresión real en un navegador (F-100): sólo por CSS.
- Qué parte del terreno no apto de F-109 es mar o ladera.
- Si el desfase de F-180 es de las láminas derivadas o de otra lámina del plano.
- Contenido de REGLAS.md sobre campamentos y sobre la capa síntesis (sólo leí la línea que lista las cuatro clases).
