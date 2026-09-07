# Frente 6 — El veredicto geométrico del visor: ray-casting adversarial y la contradicción del borde

Auditoría del 2026-09-06 · rama `visor-simple-y-laminas-vectorizadas` · commit `b293aad` · IDs provisionales 601–608.

**Límite respetado:** no se tocó `scripts/`, `web/`, `tests/`, `config/`, `data/` ni docs existentes. Instrumentos nuevos, todos en `tools/auditoria/`:

| Instrumento | Qué mide |
|---|---|
| `tools/auditoria/raycasting_adversarial.js` | Extrae por regex `distancia`, `dentroAnillo`, `poligonosQueContienen`, `dentroDeMancha` de `web/app.js` (imprime línea y SHA-1 de cada una), las evalúa en un `vm` aislado y responde qué features contienen cada punto. `--autocontrol` corre un cuadrado con punto adentro/afuera. |
| `tools/auditoria/raycasting_vs_shapely.py` | Casos adversariales sintéticos + un punto en cada hueco real de cada capa + barrido aleatorio con semilla sobre la caja de cada capa; compara veredicto por veredicto contra shapely `contains`/`covers` (geometrías inválidas pasan por `make_valid` una sola vez). |
| `tools/auditoria/fraccion_cerca_del_borde.py` | Grilla de 20 m sobre las manzanas urbanas del Censo 2024 de cada comuna; distancia UTM al borde de polígono más cercano de cada capa; fracción de puntos y de población a <10/25/50 m. `--control` desplaza las capas 10 km. |
| `tools/auditoria/veredicto_en_pantalla.py` | Playwright sobre el visor servido en 8793: llama `consultar(lon, lat)` como hace `tests/auditoria_e2e.py` y extrae título, «por qué» y frases clave de la ficha. |

**Por qué extracción por regex y no `vm` con `document`/`window` falsos:** `web/app.js` termina con `inicio()` (línea 1980 aprox., leída con `tail`), que toca `fetch`, `navigator`, el DOM y MapLibre. Cualquier stub faltante revienta, o peor, deja funciones a medias sin error. Con la extracción el arnés muere con código 2 si no encuentra las cuatro funciones y publica el SHA-1 de lo que evaluó, así que se puede comprobar contra el archivo.

## 0. Las dos preguntas del instrumento (respondidas con corridas, no con intención)

**Arnés Node.** (1) Si el ray-casting estuviera roto, ¿falla? Sí. Copia de `app.js` con `dentroAnillo` anulada (`if (false && ...)`): control positivo `ok: false`, exit 1. (2) Si el instrumento estuviera muerto, ¿se ve distinto? Sí. Copia con la función renombrada: `NO SE PUDIERON EXTRAER: dentroAnillo`, exit 2. Salida cruda:

```
$ node tools/auditoria/raycasting_adversarial.js --autocontrol
 "funciones": [ {"nombre":"distancia","linea":135,"sha1":"eca3226829a2"},
   {"nombre":"dentroAnillo","linea":145,"sha1":"430a210ae1ca"},
   {"nombre":"poligonosQueContienen","linea":156,"sha1":"2fafc3bb2f9b"},
   {"nombre":"dentroDeMancha","linea":171,"sha1":"0a7f4f5d9ee2"} ]
 "control_positivo": {"punto":[-72.65,-37.75],"contiene":[0],"ok":true}
 "control_negativo": {"punto":[-72.5,-37.75],"contiene":[],"ok":true}
 "distancia_1grado_lat_m": 111194.92664455874
exit=0
$ node ... --autocontrol --app <copia con dentroAnillo anulada>
 "control_positivo": {..."contiene":[],"ok":false}   exit_roto=1
$ node ... --autocontrol --app <copia sin dentroAnillo>
NO SE PUDIERON EXTRAER: dentroAnillo de ...   exit_sin=2
```

**Comparador shapely.** Contra la copia rota ve el fenómeno: `TOTAL puntos evaluados: 2508   discrepancias visor↔shapely: 497` (n=200). Contra el visor real, 0 (sección 1). El cero es un cero medido, no un cero de instrumento mudo.

**Fracción cerca del borde.** Control con capas desplazadas 10 km: todas las celdas caen a 0,0 % salvo Temuco/GORE (0,9 %), porque a 10 km al este siguen habiendo polígonos GORE (la capa cubre toda la región). Con las capas reales las cifras suben a las de la sección 2. El instrumento aborta (`INSTRUMENTO MUERTO`) si una comuna no tiene manzanas: pasó en la primera corrida por usar `manzana` en vez de `manzana_urbana`, que es el valor real de `unidad_censal`.

**Veredicto en pantalla.** Aborta si `#respuesta` queda oculta o `estado.ultimo` no se llena. En la primera corrida se acusó a sí mismo: después de abrir la pestaña «detalle», `#respuesta` queda oculta. Corregido volviendo a `irAPestana('respuesta')` antes de cada consulta. Lo anoto porque es exactamente la trampa descrita en la memoria del proyecto (auditoría que se acusa a sí misma).

## 1. Ray-casting adversarial: 13 308 puntos, 0 discrepancias

Comando y resumen crudo (semilla declarada `20260906`, n = 2000 por capa; mitad uniforme en la caja de la capa, mitad a ±20 m de un vértice):

```
$ python tools/auditoria/raycasting_vs_shapely.py --n 2000 --semilla 20260906
huecos_reales:A_normativo        puntos=    2 en_borde_exacto=0 discrepancias=0
huecos_reales:A_derivada         puntos=  113 en_borde_exacto=0 discrepancias=0
huecos_reales:C_gore             puntos=  741 en_borde_exacto=0 discrepancias=0
huecos_reales:C_jrc_rp100        puntos=    7 en_borde_exacto=0 discrepancias=0
huecos_reales:B_sar_huella       puntos=  409 en_borde_exacto=11 discrepancias=0
barrido:A_normativo              puntos= 2000 en_borde_exacto=0 discrepancias=0
barrido:A_derivada               puntos= 2000 en_borde_exacto=0 discrepancias=0
barrido:C_gore                   puntos= 2000 en_borde_exacto=0 discrepancias=0
barrido:C_jrc_rp100              puntos= 2000 en_borde_exacto=0 discrepancias=0
barrido:B_sar_huella             puntos= 2000 en_borde_exacto=0 discrepancias=0
barrido:D_campamentos            puntos= 2000 en_borde_exacto=0 discrepancias=0
TOTAL puntos evaluados: 13308   discrepancias visor↔shapely: 0
real 0m19.251s
```

Inventario geométrico de las capas publicadas (medido con shapely en esta sesión; el encargo decía 17 huecos en las láminas, medí 113):

```
areas-riesgo-inundacion.geojson  features 63 {MultiPolygon:7, Polygon:56} anillos_ext 86 huecos 2   ext_horario 86   invalidos 0
laminas/vectorizadas.geojson     features 163 {Polygon:163}               anillos_ext 163 huecos 113 ext_horario 0  invalidos 0
gore/amenaza-inundacion.geojson  features 2539 {Polygon:2539}             anillos_ext 2539 huecos 741 ext_horario 2539 invalidos 198 (Ring Self-intersection)
jrc/rp100.geojson                features 52 {Polygon:52}                 huecos 7   ext_horario 0  invalidos 0
sar/huella-observada.geojson     features 1075 {Polygon:1075}             huecos 409 ext_horario 0  invalidos 585
campamentos-inundacion.geojson   features 15 {Polygon:15}                 huecos 0   ext_horario 15 invalidos 0
```

### Tabla de casos adversariales (caso · esperado · visor · shapely · veredicto)

Cuadrado sintético `[-72.70,-37.80]–[-72.60,-37.70]`, lat de referencia −38°: 1 m = 8,99e-6° lat, 1,141e-5° lon. Salida cruda del comparador:

| caso | punto [lon, lat] | esperado | visor | shapely contains | shapely covers | veredicto |
|---|---|---|---|---|---|---|
| control_positivo | [-72.65, -37.75] | [0] | [0] | [0] | [0] | OK |
| control_negativo | [-72.55, -37.75] | [] | [] | [] | [] | OK |
| vertice_exacto | [-72.7, -37.8] | borde | [0] | [] | [0] | borde:indefinido |
| vertice_exacto | [-72.6, -37.7] | borde | [] | [] | [0] | borde:indefinido |
| arista_horizontal | [-72.65, -37.8] | borde | [0] | [] | [0] | borde:indefinido |
| arista_horizontal | [-72.65, -37.7] | borde | [] | [] | [0] | borde:indefinido |
| arista_vertical | [-72.7, -37.75] | borde | [0] | [] | [0] | borde:indefinido |
| arista_vertical | [-72.6, -37.75] | borde | [] | [] | [0] | borde:indefinido |
| borde_1m_dentro | [-72.6999886, -37.75] | [0] | [0] | [0] | [0] | OK |
| borde_1m_dentro | [-72.65, -37.799991] | [0] | [0] | [0] | [0] | OK |
| borde_1m_fuera | [-72.7000114, -37.75] | [] | [] | [] | [] | OK |
| borde_1m_fuera | [-72.65, -37.800009] | [] | [] | [] | [] | OK |
| borde_3m_dentro | [-72.6999658, -37.75] | [0] | [0] | [0] | [0] | OK |
| borde_3m_dentro | [-72.65, -37.799973] | [0] | [0] | [0] | [0] | OK |
| borde_3m_fuera | [-72.7000342, -37.75] | [] | [] | [] | [] | OK |
| borde_3m_fuera | [-72.65, -37.800027] | [] | [] | [] | [] | OK |
| borde_10m_dentro | [-72.6998859, -37.75] | [0] | [0] | [0] | [0] | OK |
| borde_10m_dentro | [-72.65, -37.7999101] | [0] | [0] | [0] | [0] | OK |
| borde_10m_fuera | [-72.7001141, -37.75] | [] | [] | [] | [] | OK |
| borde_10m_fuera | [-72.65, -37.8000899] | [] | [] | [] | [] | OK |
| exterior_horario | [-72.65, -37.75] | [0] | [0] | [0] | [0] | OK |
| exterior_horario | [-72.55, -37.75] | [] | [] | [] | [] | OK |
| hueco_antihorario | [-72.65, -37.75] | [] | [] | [] | [] | OK |
| hueco_antihorario | [-72.62, -37.75] | [0] | [0] | [0] | [0] | OK |
| hueco_horario | [-72.65, -37.75] | [] | [] | [] | [] | OK |
| hueco_horario | [-72.62, -37.75] | [0] | [0] | [0] | [0] | OK |
| hueco_borde_1m_dentro_del_hueco | [-72.6599886, -37.75] | [] | [] | [] | [] | OK |
| hueco_borde_1m_fuera_del_hueco | [-72.6600114, -37.75] | [0] | [0] | [0] | [0] | OK |
| multipolygon_segunda_parte | [-72.45, -37.75] | [0] | [0] | [0] | [0] | OK |
| multipolygon_segunda_parte | [-72.55, -37.75] | [] | [] | [] | [] | OK |
| mono_autointerseccion | [-72.68, -37.75] | shapely | [0] | [0] | [0] | OK |
| mono_autointerseccion | [-72.62, -37.75] | shapely | [0] | [0] | [0] | OK |
| mono_autointerseccion | [-72.65, -37.72] | shapely | [] | [] | [] | OK |
| mono_autointerseccion | [-72.65, -37.78] | shapely | [] | [] | [] | OK |
| anillo_abierto | [-72.65, -37.75] | [0] | [0] | [0] | [0] | OK |
| dos_features_solapadas | [-72.65, -37.75] | [0, 1] | [0, 1] | [0, 1] | [0, 1] | OK |

Lectura: el ray-casting de `web/app.js:145-169` es correcto e independiente de la orientación de los anillos; excluye huecos de cualquier orientación; devuelve todas las features solapadas; en el «moño» coincide con shapely (`make_valid`, que lo parte en dos triángulos). En el borde exacto se comporta como intervalo semiabierto: oeste y sur cuentan como adentro, este y norte como afuera. Es indefinido por diseño y no importa a la persona (un borde exacto es un evento de medida cero), pero se documenta.

### Los cinco puntos en el navegador (arnés = shapely = pantalla)

Servidor `python -m http.server 8793 --directory web`; capas cargadas en el navegador `{"areas":true,"laminas":true,"gore":true,"jrc":true,"sar":true}`. Los índices de feature que da el arnés coinciden uno a uno con shapely (`A [[18],[],[],[],[]]  L [[],[],[],[0],[]]  G [[652],[652],[256],[256],[2]]`) y con `estado.ultimo.res` en pantalla:

| # | punto [lon, lat] | shapely | pantalla: nivel · título |
|---|---|---|---|
| 1 | [-72.438268, -37.961368] dentro de ZR-5 Collipulli, a 36 m del borde | areas [18], gore [652] | alto · «Estás en un área de riesgo por inundación del plan regulador» |
| 2 | [-72.438013, -37.962213] **3,8 m fuera** de esa misma área | areas [], gore [652] MAXIMA | **sindato** · «Sin registros en las fuentes consultadas» |
| 3 | [-72.696550, -37.781779] dentro de un hueco de lámina «Alto» Angol | laminas [], gore [256] | bajo · «Registros de inundación a cierta distancia» |
| 4 | [-72.698477, -37.779165] dentro de lámina «Alto» Angol 2013, sin área normativa | laminas [0], gore [256] | bajo · «Registros de inundación a cierta distancia» |
| 5 | [-73.086720, -38.681020] dentro de GORE MAXIMA | gore [2] | sindato · «Sin registros en las fuentes consultadas» |

## 2. La contradicción del borde

**¿Existe banda «cerca del borde»?** No, para ninguna capa poligonal. `web/app.js:357-378` compone `nivel`/`titulo` sólo con `sar.length`, `areas.length` y los puntos críticos (`graves`, `en(RADIOS.cercano)`, `en(RADIOS.medio)`, `cerca.length`). `RADIOS` (`web/app.js:17`, `{cercano:300, medio:500, contexto:1500}`) se usa únicamente contra `estado.puntos.features` (líneas 335-344, 575, 665, 872, 891). `grep -n -i "borde\|buffer\|distancia("` sobre `app.js` no encuentra ninguna distancia a polígono: las únicas llamadas a `distancia` son a puntos críticos (337, 409). El veredicto sobre polígonos es binario `poligonosQueContienen(...).length`.

**Qué fracción de la zona urbana queda en la franja.** Grilla de 20 m dentro de `manzana_urbana`/`aldea` del Censo 2024, ponderada por `n_per`. Cajas: Angol y Catripulli = caja de la lámina vectorizada de esa comuna; Collipulli y Temuco = caja de sus áreas normativas. Salida cruda de `python tools/auditoria/fraccion_cerca_del_borde.py --paso 20`:

| comuna | capa | polígonos en caja | puntos grilla | población | <10 m pts | <10 m pob | <25 m pts | <25 m pob | <50 m pts | <50 m pob |
|---|---|---|---|---|---|---|---|---|---|---|
| Angol | A_normativo | 0 | 31371 | 48148 | SIN DATO | | | | | |
| Angol | A_derivada | 124 | 31371 | 48148 | 5.5 % | 3.0 % | 11.0 % | 6.4 % | 17.2 % | 11.3 % |
| Angol | C_gore | 40 | 31371 | 48148 | 4.7 % | 4.3 % | 11.3 % | 10.3 % | 21.9 % | 19.8 % |
| Angol | C_jrc_rp100 | 0 | 31371 | 48148 | SIN DATO | | | | | |
| Collipulli | A_normativo | 36 | 8867 | 17640 | 2.2 % | 0.6 % | 4.8 % | 1.3 % | 8.9 % | 2.7 % |
| Collipulli | A_derivada | 0 | 8867 | 17640 | SIN DATO | | | | | |
| Collipulli | C_gore | 42 | 8867 | 17640 | 1.7 % | 0.5 % | 4.2 % | 1.2 % | 7.8 % | 2.5 % |
| Collipulli | C_jrc_rp100 | 0 | 8867 | 17640 | SIN DATO | | | | | |
| Temuco | A_normativo | 1 | 116570 | 271968 | 1.1 % | 0.5 % | 2.6 % | 1.3 % | 5.0 % | 3.1 % |
| Temuco | A_derivada | 0 | 116570 | 271968 | SIN DATO | | | | | |
| Temuco | C_gore | 31 | 116570 | 271968 | 1.8 % | 1.2 % | 4.4 % | 3.1 % | 8.7 % | 6.5 % |
| Temuco | C_jrc_rp100 | 0 | 116570 | 271968 | SIN DATO | | | | | |
| Catripulli (Curarrehue) | A_normativo | 0 | 5428 | 942 | SIN DATO | | | | | |
| Catripulli (Curarrehue) | A_derivada | 39 | 5428 | 942 | 37.7 % | 37.0 % | 69.7 % | 68.7 % | 91.0 % | 91.2 % |
| Catripulli (Curarrehue) | C_gore | 15 | 5428 | 942 | 2.2 % | 1.8 % | 5.6 % | 4.5 % | 11.0 % | 9.2 % |
| Catripulli (Curarrehue) | C_jrc_rp100 | 0 | 5428 | 942 | SIN DATO | | | | | |

Los SIN DATO del JRC son reales, no del instrumento: la unión de `rp100.geojson` no toca ninguna de las cuatro cajas (`Angol dist km aprox: 7.7 · Collipulli 16.7 · Temuco 1.9 · Catripulli 82.4`). Angol y Catripulli no tienen área normativa MINVU; Collipulli y Temuco no tienen lámina.

Incertidumbre del dato, leída de `data/processed/laminas/*.geojson` → `procedencia`: Angol peligro 2013 `metros_por_pixel: 7.74` («±7.7 m»); Angol PRC AR-2a `rmse_m: 4.94`, `metros_por_pixel: 0.8486`; Catripulli 2025 `metros_por_pixel: 5.337` («±5.3 m»). Para el GORE la ficha misma dice «~35 m» (`web/app.js:925`). Con eso: en Angol, el 5,5 % de la zona urbana (3 % de la gente) está a menos de 10 m del borde de la lámina, es decir, a poco más de un píxel de la figura de origen; en Catripulli es el 37,7 % de los puntos y el 37 % de la población (942 personas en la caja) a <10 m y el 91 % a <50 m, porque las manchas de susceptibilidad son muchas y chicas y la aldea está entera sobre ellas. Para el GORE (píxel de 35 m) la franja «dentro del error» es <50 m: 21,9 % de Angol urbano, 19,8 % de su gente.

## 3. Orden y prioridad

Leído en `web/app.js:357-378` y `render` (`676-960`):

- `nivel` y `titulo`: SAR (358) > área normativa (363) > puntos críticos (366-374) > sindato (375). **GORE, JRC y láminas derivadas no participan del veredicto** aunque se calculan (384-385) o ni siquiera se calculan (láminas: `estado.laminas` aparece sólo en carga 106, inventario 435-436, capa de mapa 1549-1565 y casilla 1700-1709; nunca en `evaluar`).
- Si un punto cae en área normativa Y en GORE Y en lámina: el título es el de la normativa (365), el «por qué» (571) también; la ficha muestra primero el bloque A (677), luego B (743), plano (836), D (868), C con JRC y después GORE (900-931), campamentos (939). La lámina no aparece en la ficha del punto: la única palabra «lámina» en pantalla viene del inventario de la comuna (`bloqueComuna`, 435-436: «11 lámina(s) de cartografía localizadas dentro de 41 documento(s)» y 446-448: «124 polígono(s) que convertimos nosotros»), que es un conteo por comuna, no un veredicto sobre el punto.
- La etiqueta «derivado» con texto existe sólo en el panel de capas (`web/index.html:111-113` y su nota 121-124). En la ficha: `ficha menciona 'derivad': False` para los cinco puntos, incluido el punto 4 que está dentro de una lámina.

## Hallazgos (ordenados por gravedad)

### 601 — El «por qué» afirma que ninguna fuente registra inundación mientras el GORE del mismo punto dice «máxima»
- `web/app.js:375-377` (rama `sindato`), `web/app.js:587` (`porQue`), `web/app.js:384-385` (GORE y JRC se calculan pero no entran en `nivel`).
- QUÉ PASA — `evaluar` deja `nivel='sindato'` y `porQue` devuelve «Ninguna de las fuentes consultadas registra inundación en este punto» cuando no hay SAR, área normativa ni punto crítico a 1500 m, aunque el modelo regional (`res.gore`) o el global (`res.enMancha`) sí lo marquen. La misma ficha, tres bloques más abajo, dice «clasifica este punto como amenaza de inundación máxima» (920).
- CÓMO SE VE — Punto 5 (GORE MAXIMA) y punto 2 (3,8 m fuera de un área normativa, GORE MAXIMA): titular «❔ Sin registros en las fuentes consultadas», «Ninguna de las fuentes consultadas registra inundación en este punto», y en la ficha «El modelo regional del Gobierno Regional clasifica este punto como amenaza de inundación máxima». Quien lee el titular y comparte por WhatsApp (`compartir`, 1098, usa `textoFicha`) se lleva «sin registros».
- CÓMO REPRODUCIRLO — `python -m http.server 8793 --directory web`; `python tools/auditoria/veredicto_en_pantalla.py cinco.json` con `{"5":{"lonlat":[-73.08672046357616,-38.681020000000004]}}`.
- SALIDA CRUDA — `=== 5_gore_maxima  nivel=sindato  res={"areas":0,"gore":1,...}  TÍTULO: Sin registros en las fuentes consultadas  POR QUÉ: Ninguna de las fuentes consultadas registra inundación en este punto.  FICHA: El modelo regional del Gobierno Regional clasifica este punto como amenaza de inundación máxima.`
- CONFIANZA — CONFIRMADO.
- GRAVEDAD — 5. El titular contradice la evidencia que el propio visor tiene en la mano; el resumen que se comparte es el titular.

### 602 — La capa A derivada (163 polígonos de láminas vectorizadas) no participa del veredicto ni aparece en la ficha del punto
- `web/app.js:333-386` (`evaluar` no consulta `estado.laminas`), `web/app.js:676-960` (`render` no tiene bloque de láminas); `estado.laminas` sólo en 63, 102-107, 435-436, 1549-1565, 1700-1709 (grep `laminas|derivad|DERIVAD`).
- QUÉ PASA — Se publica una capa con 124 polígonos en Angol (clases Alto/Medio/AR-2a del estudio de riesgo PRC 2013) y 39 en Catripulli, se dibuja en el mapa como «derivado», pero `evaluar` nunca pregunta si el punto cae dentro. La ficha responde «Este punto no cae dentro de un área de riesgo por inundación declarada en el plan regulador» (712) y el titular baja a los puntos críticos.
- CÓMO SE VE — Punto 4, dentro de un polígono «Alto» del «Estudio de Riesgo, Actualización Plan Regulador Comunal de Angol, 2013»: «ℹ️ Registros de inundación a cierta distancia», «El registro más cercano de inundación está a 782 metros». Nada dice que el estudio de riesgo del PRC de su comuna pintó su terreno como peligro alto; la única mención es el inventario comunal («124 polígono(s) que convertimos nosotros»). Y en Angol es la ÚNICA capa fina: no hay área normativa MINVU (`A_normativo: 0 polígonos en caja`).
- CÓMO REPRODUCIRLO — mismo instrumento, punto `[-72.69847679298667,-37.7791652004678]`; arnés: `L [[],[],[],[0],[]]` (feature 0 de `vectorizadas.geojson` lo contiene); shapely `shapely_laminas: [0]`.
- SALIDA CRUDA — `=== 4_dentro_lamina_derivada_sin_normativa  nivel=bajo  res={"areas":0,"gore":1,"enMancha":false,"sar":0,"laminas_en_res":false}  TÍTULO: Registros de inundación a cierta distancia  FICHA: Este punto no cae dentro de un área de riesgo por inundación declarada en el plan regulador.  ficha menciona 'derivad': False`
- CONFIANZA — CONFIRMADO.
- GRAVEDAD — 5. Es el caso del encargo: la persona en Angol lee «no cae dentro» sobre un terreno que el estudio de riesgo del PRC marcó como alto, porque el visor calla la única capa que lo sabe.

### 603 — El veredicto sobre polígonos es binario y no existe banda de borde; a 3,8 m del borde el visor dice «sin registros»
- `web/app.js:357-378`, `web/app.js:17` (`RADIOS` sólo para puntos críticos: usos en 338, 343, 366, 369, 575, 665, 872, 891), `web/app.js:712-713`, `web/index.html:232-235`, `web/app.js:962-963` (la frase «Mira la mancha, no su borde» cierra en 963).
- QUÉ PASA — El sitio le pide a la gente «Mira la mancha, no su borde… esa diferencia suele ser más chica que el error del propio mapa» y luego decide con `poligonosQueContienen().length` sin ninguna tolerancia. No hay `distancia` a polígono en todo `app.js`.
- CÓMO SE VE — Punto 2, a 3,8 m fuera de ZR-5 de Collipulli (36 m más al norte está el punto 1, que sí «Estás en un área de riesgo»): «❔ Sin registros en las fuentes consultadas» y «Este punto no cae dentro de un área de riesgo por inundación declarada en el plan regulador». La fracción de zona urbana en esa franja está en la tabla de §2: en Catripulli el 37,7 % de los puntos urbanos y el 37,0 % de la población están a <10 m de un borde de lámina cuyo píxel es de 5,3 m; en Angol, 5,5 % / 3,0 % a <10 m con píxel de 7,7 m y 21,9 % / 19,8 % a <50 m del GORE de 35 m.
- CÓMO REPRODUCIRLO — `python tools/auditoria/fraccion_cerca_del_borde.py --paso 20` y `veredicto_en_pantalla.py` con el punto 2.
- SALIDA CRUDA — ver tabla §2 y `=== 2_3m_fuera_area_normativa  nivel=sindato ... FICHA: Este punto no cae dentro de un área de riesgo`.
- CONFIANZA — CONFIRMADO (código y medida). La cifra «una persona a 3 m del borde» es un caso construido a propósito, no un reclamo real: SOSPECHA de que ocurra en la práctica con la frecuencia que dice la tabla, porque la tabla mide superficie urbana, no consultas.
- GRAVEDAD — 4. La contradicción no es del ray-casting (que es exacto) sino del contrato: el dato tiene ±5-35 m y el veredicto se entrega a 0 m.

### 604 — La comuna del bloque «Con qué cuenta» se resuelve por el punto crítico más cercano y contradice al área normativa de la misma ficha
- `web/app.js:393-417` (`comunaDe`; el comentario 402-404 admite el problema), `web/app.js:435-448` (`bloqueComuna`).
- QUÉ PASA — El punto 1 está dentro de un área ZR-5 cuya propiedad `comuna` es «Collipulli»; `comunaDe` devuelve «Ercilla» porque el punto crítico más cercano (5,7 km) es de Ercilla. El bloque dice de Ercilla «no tiene su área de riesgo por inundación en el vectorial público del MINVU» debajo de «Este punto cae dentro de 1 área de riesgo declarada por el plan regulador».
- CÓMO SE VE — Ficha del punto 1: titular «Estás en un área de riesgo…», y más abajo «Qué falta: no tiene su área de riesgo por inundación en el vectorial público del MINVU … Compartir el estado de Ercilla».
- CÓMO REPRODUCIRLO — `page.evaluate("() => comunaDe(estado.ultimo.res, estado.ultimo.lon, estado.ultimo.lat)")` tras consultar `[-72.43826796279558,-37.9613683661807]`.
- SALIDA CRUDA — `== 1_dentro_area_normativa comunaDe= {'comuna': 'Ercilla', '_km': 5.7, 'laminas': 0} area.comuna= ['Collipulli']`.
- CONFIANZA — CONFIRMADO.
- GRAVEDAD — 3. No cambia el veredicto, pero la ficha se contradice a sí misma y manda a pedir por Ley 20.285 un mapa a la municipalidad equivocada. Cuando `res.areas` trae `comuna`, esa es la fuente que debería mandar.

### 605 — El barrido no probó la capa de cobertura SAR ni las capas JRC distintas de rp100
- `tools/auditoria/raycasting_vs_shapely.py` (`CAPAS`), `web/app.js:355` (`coberturaSar`), `web/app.js:85` (sólo `rp100`).
- QUÉ PASA — `cobertura-sar.geojson` (115 polígonos, 405 huecos, 59 inválidos) decide «el satélite miró y no vio agua» y no se incluyó en el barrido; `rp10/20/50/200/500` no las carga el visor (85), así que no era necesario.
- CÓMO SE VE — nada en pantalla; es un límite de esta auditoría.
- CONFIANZA — CONFIRMADO como omisión. Resultado para esa capa: **SIN DATO**. Dado que la misma función pasó 13 308 puntos sobre capas con la misma clase de defectos (huecos, autointersecciones), SOSPECHA de que sea igual de exacta, sin medirlo.
- GRAVEDAD — 2.

### 606 — 198 polígonos del GORE y 585 de la huella SAR son inválidos (autointersección de anillo); el visor y shapely coinciden sólo tras `make_valid`
- `web/data/gore/amenaza-inundacion.geojson`, `web/data/sar/huella-observada.geojson`, `web/data/sar/cobertura-sar.geojson`.
- QUÉ PASA — `explain_validity`: `Ring Self-intersection` ×198 en GORE; 585/1075 huellas SAR y 59/115 coberturas inválidas (conteo con `is_valid`; razón detallada sólo medida en GORE). El ray-casting responde igual que shapely sobre la versión reparada (0 discrepancias en 2741 puntos de huecos y barrido sobre GORE+SAR), pero cualquier herramienta que use `contains` sin reparar (un script de auditoría, un SIG) puede responder distinto al visor en esos polígonos.
- CÓMO REPRODUCIRLO — script de inventario de §1 (`shape(g).is_valid`, `explain_validity`).
- SALIDA CRUDA — `gore ... invalidos 198` · `invalidez: Counter({'Ring Self-intersection': 198})` · `sar\huella-observada.geojson ... invalidos 585` · `cobertura-sar.geojson ... invalidos 59`.
- CONFIANZA — CONFIRMADO el conteo; SOSPECHA de que exista algún punto donde el veredicto dependa de la reparación (el barrido no lo encontró).
- GRAVEDAD — 2. Deuda del dato, no del veredicto, mientras nadie compare con otra herramienta.

### 607 — El borde exacto es semiabierto (oeste/sur adentro, este/norte afuera)
- `web/app.js:149-150`.
- QUÉ PASA — Un punto exactamente sobre el vértice o arista oeste/sur cuenta como adentro; sobre la este/norte, afuera. Es la convención estándar del algoritmo y sólo afecta a coordenadas exactamente coincidentes.
- SALIDA CRUDA — filas `vertice_exacto`, `arista_horizontal`, `arista_vertical` de la tabla §1.
- CONFIANZA — CONFIRMADO. GRAVEDAD — 1. Cosmético para una persona; relevante sólo para quien escriba tests con vértices exactos.

### 608 — El encargo decía 17 huecos en las láminas; hay 113
- `web/data/laminas/vectorizadas.geojson`.
- QUÉ PASA — Dato del encargo desactualizado o de otra versión de la capa. Se midieron 113 anillos interiores en 163 polígonos y se puso un punto en cada uno (todos coinciden con shapely).
- SALIDA CRUDA — `laminas/vectorizadas.geojson features 163 ... huecos 113`; `huecos_reales:A_derivada puntos= 113 discrepancias=0`.
- CONFIANZA — CONFIRMADO. GRAVEDAD — 1. Para quien orquesta: no dar por sentado el inventario de la capa entre auditorías.

## SIN DATO (no medido, no es FALLA ni OK)

- `cobertura-sar.geojson` en el barrido (605).
- Veredicto por la caja de búsqueda con «lat, lon»: no se probó; se usó `consultar(lon, lat)` como hace `tests/auditoria_e2e.py:532`. Si el geocodificador mueve el punto, eso no se vio.
- Frecuencia real con la que la gente consulta puntos en la franja de borde (la tabla mide superficie urbana, no consultas).
- Puntos en la franja de borde de la huella SAR y de campamentos (no estaban en el encargo de §2).

## VERIFICADO LIMPIO

- **`dentroAnillo` / `poligonosQueContienen` / `dentroDeMancha` (`web/app.js:145-173`)**: 13 308 puntos, 0 discrepancias contra shapely; MultiPolygon segunda parte OK; huecos horarios y antihorarios excluidos; exterior horario (las 86 áreas MINVU y los 2539 GORE lo son) OK; anillo abierto OK; features solapadas devuelve ambas; moño coincide con `make_valid`. No hace falta volver a mirar el ray-casting: el defecto está en qué capas se le preguntan y en qué se hace con la respuesta, no en la respuesta.
- **`distancia` (`web/app.js:135-143`)**: 1° de latitud = 111 194,93 m (`distancia_1grado_lat_m`), coherente con R = 6371 km.
- **Extracción del arnés**: SHA-1 `430a210ae1ca` (`dentroAnillo`, línea 145) y `2fafc3bb2f9b` (`poligonosQueContienen`, 156) sobre `web/app.js` del commit `b293aad`.
- **Arnés = shapely = pantalla** para los 5 puntos: índices de features idénticos en las tres vías (`A [[18],[],[],[],[]] L [[],[],[],[0],[]] G [[652],[652],[256],[256],[2]]`; `estado.ultimo.res.areas/gore` coinciden).
- **Prioridad SAR > normativa > puntos** (`web/app.js:358-374`) se cumple tal como está escrita y como dice el comentario 349-353; el punto 1 muestra el bloque A primero y el GORE dentro del bloque C después, en el orden que describe `render`.
- **Semántica de huecos en datos reales**: 2 (MINVU) + 113 (láminas) + 741 (GORE) + 7 (JRC) + 409 (SAR): un punto representativo en cada uno, ninguno reportado como «dentro» por el visor.
- **Región**: `dentroDeRegion` (`web/app.js:37-40`) no interfiere con los 5 puntos (todos dentro del bbox).
- **Sin residuos**: `git status --short` al cierre muestra sólo `tools/` y `docs/auditorias/` (más `docs/_prompts/PREAMBULO-AUDITOR.md`, que no es de este frente); el `casos_raycasting.casos.json` que mi script dejó en la raíz se borró y el defecto se cambió al directorio temporal. Servidor 8793 apagado (`taskkill` PID 33364).
