# Frente C: población expuesta espacial

| | |
|---|---|
| Hora del servidor al empezar | 2026-11-15T08:11:53-03:00 (`Get-Date`); informe escrito hacia las 08:50 |
| Commit | `ef2f534d6ef9ca46349966f33e47d61d87fcebad`, rama `visor-simple-y-laminas-vectorizadas` |
| Modelo | Claude Opus 5.5 (`claude-opus-5-5`), auditor del frente C |
| Rango de IDs | F-300 a F-399 (provisionales; los finales los pone el verificador) |
| Instrumentos | `tools/auditoria/fC_poblacion_expuesta.py`, `fC_censo_ine_vs_esri.py`, `fC_tamano_publicable.py`, los tres con `--control` |
| Salidas crudas | `docs/auditorias/2026-11-15/frente-C/salidas/` |

**Qué NO miré.** No abrí el visor ni su lógica de veredicto (frente A), ni el GeoIDE del
MINVU (frente B). No corrí `pytest` ni las auditorías e2e. No regeneré ninguna capa de
evidencia: crucé lo que está publicado en `web/data/` tal como está. No validé en terreno
ni contra imagen ninguna mancha. No tengo los polígonos del practicante, así que su cifra
sólo sirve de orden de magnitud. No miré la capa D (puntos críticos, son puntos, no
manchas) ni los campamentos. No medí cuánto pesa publicar con 6 decimales ni en teselas
vectoriales.

## En una pantalla

1. **El censo que usamos cuenta dos veces a 17.887 personas.** Las 33 aldeas de la capa 2 son la suma exacta de 505 manzanas «Aldea» de la capa 0; el total real es 1.003.546, no 1.021.433, y el visor ya muestra habitantes inflados en 19 comunas (Toltén 11.798 en vez de 9.995, +18 %).
2. **Las fuentes INE y Esri son el mismo dato**: mismas 17.107 unidades por MANZENT, cero diferencias en población y en los ocho campos, geometría a menos de 0,73 m. Recomiendo el GPKG del INE como fuente primaria (oficial, archivo fijo, una sola geometría inválida contra siete).
3. **El criterio de cruce manda más que la capa**: en la AR-2a de Angol la cifra va de 429 (manzana entera) a 22.113 (cualquier toque), y el reparto por área da 4.943; en el radar va de 0 a 24.315. Ningún número solo es defendible.
4. **El borde declarado del A derivado mueve el reparto un cuarto o más**: ±8,3 m en la AR-2a de Angol lleva 4.943 a 3.684 o 6.291; en el estudio 2013, 1.290 pasa a 776 o 1.851.
5. **Publicar por manzana offline cuesta entre 0,7 y 6,1 MB con gzip** según qué se recorte; la tabla precalculada por comuna, 15 kB. GORE y JRC arrastran el 89 % de las unidades.

## 1. El censo: qué contiene y cuánta gente hay de verdad

`data/processed/censo/censo-2024-araucania.geojson` tiene 17.107 polígonos en tres
`unidad_censal`, con los ocho campos pedidos presentes y sin nulos (salida de esta sesión):

```
aldea              33   17887
entidad_rural    4188  312373
manzana_urbana  12886  691173
total 1021433 nulls n_per 0
invalid 7 by {'entidad_rural': 6, 'manzana_urbana': 1}
n_fuente_agua_rio True 0 21510 ...   (los ocho campos: True, 0 nulos)
```

**Las aldeas están dos veces.** El GPKG del INE trae el campo `TIPO_MZ` en las manzanas, y
el servicio de Esri también, pero `scripts/16_censo_2024.py` no lo descarga:

```
INE Manzanas TIPO_MZ: {'URBANO': 12381, 'ALDEA': 505}  ->  {'ALDEA': 17887.0, 'URBANO': 673286.0}
Esri capa 0, en vivo hoy, agrupado por TIPO_MZ: Aldea n=505 p=17887 ; Urbano n=12381 p=673286
ESRI geojson: manzanas_urbanas que intersectan aldeas: 505 poblacion de esas manzanas: 17887
```

`fC_poblacion_expuesta.py` comprueba aldea por aldea, por punto representativo, que las 33
cuadran exacto con sus manzanas (`'aldeas_que_cuadran': 33, 'personas_manzanas_dentro_de_aldeas': 17887`).
El total que cuadra con el INE es urbano 673.286 (igual a `Limite_Urbano_CPV24` y
`Zonal_CPV24`) más rural 330.260 (igual a `Localidades_CPV24`), es decir **1.003.546**.
Todos los cruces de este informe usan manzanas más entidades, sin las 33 aldeas.

## 2. INE contra Esri

Salida de `fC_censo_ine_vs_esri.py` (control OK: detecta 1 persona sumada, 5,0 m de
corrimiento y 1 unidad borrada en una copia sintética):

| | Manzanas | Entidades | Aldeas |
|---|---:|---:|---:|
| Unidades Esri / INE | 12.886 / 12.886 | 4.188 / 4.188 | 33 / 33 |
| Emparejadas (MANZENT; aldeas por punto) | 12.886 | 4.188 | 33 |
| Difieren en `n_per` y en los 8 campos | 0 | 0 | 0 |
| Hausdorff mediana / máximo | 0,0001 m / 0,7286 m | 0,0001 m / 0,01 m | máx 0,0006 m |
| Geometrías inválidas Esri / INE | 1 / 1 | 6 / 0 | 0 / 0 |

Por comuna, sin aldeas, la diferencia es cero en las 32. Con el archivo tal como está,
19 comunas difieren (tabla `ine_vs_esri_por_comuna.csv`).

**Qué trae cada una.** Esri: un servicio vivo de 216 campos, paginado, cuya fecha de
edición (`lastEditDate` 2026-08-19) es posterior a nuestra descarga del 14-ago, aunque los
conteos de hoy son idénticos. INE: un archivo fijo (miembros del zip fechados 2025-12-15,
sha256 `da2b75d6...6015133`) con los mismos campos más diez capas: además de manzanas,
entidades y aldeas trae `Limite_Urbano_CPV24` (52), `Localidades_CPV24` (1.615), zonal,
distrital, comunal, provincial y regional, y un diccionario que **no** documenta las
unidades de los campos `n_*` (sólo las variables geográficas).

**Recomendación, con la evidencia de arriba**: usar el GPKG del INE como fuente primaria.
Es el mismo dato, es la fuente oficial, se puede fijar por sha256 en vez de depender de
un servicio que se edita, trae `TIPO_MZ` y los totales de control (límite urbano y
localidades) con los que se detecta el doble conteo, y entrega seis geometrías inválidas
menos. Esri queda como espejo para consultas puntuales. Pesa 42 MB el zip y 73 MB el GPKG.

## 3. Población expuesta, capa por capa

Cada capa se cruzó sola; dentro de cada una se disolvió antes de cruzar. Las tablas por
comuna están en `expuesta_<capa>_<subcapa>.csv` y el resumen en `resumen_por_capa.csv`.
Reparto y campos de vulnerabilidad en `resumen_por_capa.csv`. Cifras en personas, región
completa (1.003.546), salida de la corrida de esta sesión:

| Capa | Subcapa | ha | Dentro | Punto | Reparto | Cualquiera | % del reparto en entidades rurales |
|---|---|---:|---:|---:|---:|---:|---:|
| A normativo | todas | 2.172 | 10.232 | 19.408 | 20.179 | 48.376 | 9 |
| A normativo | fluvial | 514 | 378 | 2.963 | 2.708 | 15.860 | 8 |
| A normativo | anegamiento | 1.602 | 9.457 | 15.922 | 16.889 | 31.437 | 6 |
| A normativo | litoral | 78 | 397 | 644 | 701 | 1.769 | 100 |
| A normativo | napa freática | 0,2 | 0 | 0 | 0,3 | 283 | 100 |
| A derivado | Angol estudio 2013 (alto y medio) | 213 | 0 | 1.209 | 1.290 | 10.328 | 3 |
| A derivado | Angol estudio 2013 (alto) | 195 | 0 | 219 | 726 | 6.970 | 4 |
| A derivado | Angol PRC AR-2a | 226 | 429 | 4.983 | 4.943 | 22.113 | 0 |
| A derivado | Curarrehue 2025 | 819 | 0 | 644 | 579 | 2.243 | 100 |
| A derivado | todas disueltas | 1.185 | 429 | 5.738 | 5.673 | 24.433 | 11 |
| B observado | SAR ago-2026 | 5.084 | 0 | 773 | 873 | 24.315 | 99 |
| C modelado | GORE máxima | 313.908 | 95.102 | 204.571 | 204.888 | 352.178 | 38 |
| C modelado | GORE media o máxima | 558.742 | 254.035 | 401.131 | 400.312 | 562.079 | 31 |
| C modelado | JRC 10 años | 60.772 | 5.888 | 15.767 | 16.394 | 36.919 | 62 |
| C modelado | JRC 100 años | 67.637 | 6.612 | 17.103 | 17.773 | 38.499 | 62 |
| C modelado | JRC 500 años | 72.751 | 6.775 | 17.605 | 18.577 | 39.653 | 62 |

(JRC 20, 50 y 200 años en el CSV; quedan entre las filas mostradas.)

**Vulnerabilidad expuesta por reparto** (mismas unidades que el censo: personas para
edades y discapacidad; viviendas para agua, hacinamiento, paredes, mediagua y acarreo,
según el alias del servicio de Esri). Ejemplos con su rango mínimo a máximo:

- Viviendas con agua de río, vertiente u otra fuente natural: Curarrehue 75 (0 a 448); SAR 22 (0 a 1.475); AR-2a de Angol 1 (0 a 34); GORE máxima 2.158 (82 a 10.442).
- Mayores de 60 en la AR-2a de Angol: 876; niños de 0 a 5: 307; personas con discapacidad: 578; viviendas hacinadas: 84.
- Las demás capas y campos, con mínimo y máximo, en `resumen_por_capa.csv` y por comuna en cada `expuesta_*.csv`.

**Sensibilidad al borde** (sólo el A derivado declara `incertidumbre_borde_m`; se usó el
máximo de cada subcapa):

| Subcapa | Error | Reparto encogida | Reparto | Reparto engordada |
|---|---:|---:|---:|---:|
| Angol estudio 2013 (alto y medio) | 7,7 m | 776 | 1.290 | 1.851 |
| Angol estudio 2013 (alto) | 7,7 m | 480 | 726 | 994 |
| Angol PRC AR-2a | 8,3 m | 3.684 | 4.943 | 6.291 |
| Curarrehue 2025 | 5,3 m | 494 | 579 | 655 |

**Referencia del practicante, sólo como orden de magnitud.** Él midió Angol por reparto en
10.387 con sus propios polígonos de siete comunas (no los tenemos). Nuestro reparto en
Angol cae entre 5.094 (A derivado disuelto) y 15.866 (GORE máxima); la forma del rango es
la misma: punto y reparto casi iguales (4.983 y 4.943 en la AR-2a contra sus 10.674 y
10.387), «manzana entera» muy abajo (429 contra 2.175) y «cualquier toque» muy arriba
(22.113 contra 28.192). Su Malleco (14.158 de 125.584 habitantes de poblados) no se puede
contrastar: su denominador son habitantes de poblados de siete comunas que no sé cuáles
son, y el nuestro, 204.850 habitantes comunales de las once de Malleco. En nuestras capas A,
Malleco sólo tiene gente expuesta en Angol (A derivado), Collipulli, Renaico, Traiguén y
otras del A normativo (598 por reparto en total), y no se pueden sumar capas.

## 4. Tamaño de lo que habría que publicar (para decidir, no decidido)

Salida de `fC_tamano_publicable.py --control` (control OK: gzip ida y vuelta idéntico,
V0 igual a `os.stat`, V1 con 17.074 unidades y 1.003.546 personas):

| Variante | Elementos | MB | MB con gzip -9 |
|---|---:|---:|---:|
| V0 geojson del censo tal cual | 17.107 | 73,16 | 15,706 |
| V1 todas las unidades, campos útiles, 5 decimales | 17.074 | 44,96 | 6,110 |
| V2 unidades que tocan alguna mancha, todas las capas | 8.706 | 28,26 | 4,015 |
| V2b unidades que tocan alguna mancha, sin GORE ni JRC | 981 | 5,11 | 0,724 |
| V3 piezas recortadas, un archivo por capa, suma | 17.807 | 42,84 | 5,534 |
| V4 tablas precalculadas por capa y comuna (19 CSV) | 19 | 0,07 | 0,015 |

V3 por capa: A normativo todas 0,150 MB gzip, AR-2a de Angol 0,045, SAR 0,083, GORE
media o máxima 2,601, cada JRC cerca de 0,14. El redondeo a 5 decimales tiene un costo
medido que entra en la decisión (F-310).

## 5. Hallazgos

Ordenados por cuánto puede hacer decidir mal a una persona. El CSV con los mismos
hallazgos está en `hallazgos.csv`.

### F-300 El censo cuenta dos veces a la gente de las 33 aldeas, y el visor ya lo muestra

- ARCHIVO:LÍNEA: `scripts/16_censo_2024.py:54-60` (comentario y dict `CAPAS`: dice que las capas 3 y 4 son agregaciones, pero la 2 también lo es de la 0); `scripts/19_estado_comunas.py:119-127` (suma `n_per` de todas las unidades); `web/app.js:618` y `web/app.js:701` (muestran `c.personas`).
- QUÉ PASA: las 33 aldeas (capa 2) son exactamente la suma de 505 manzanas `TIPO_MZ = Aldea` de la capa 0, que el script baja como `manzana_urbana`. Se suman ambas.
- CÓMO SE VE: la ficha de comuna dice «11.798 habitantes (Censo 2024)» en Toltén cuando son 9.995 (+18 %); Teodoro Schmidt +8 %, Freire +7,2 %, Victoria y Curarrehue +6,1 %, 19 comunas en total. Y en cualquier cruce espacial, la gente de una aldea dentro de una mancha aparece dos veces: el reparto en Curarrehue pasa de 579 a 910 (+57 %) y el litoral de Toltén de 701 a 1.400.
- CÓMO REPRODUCIRLO: `python -I tools/auditoria/fC_censo_ine_vs_esri.py data/raw/censo_ine_2024_R09/Cartografia_censo2024_R09.gpkg` y `python tools/auditoria/fC_poblacion_expuesta.py --con-aldeas`.
- SALIDA CRUDA: `{'esri_sin_aldeas': 1003546.0, 'ine_manzanas_mas_entidades': 1003546.0, 'esri_con_aldeas_como_esta': 1021433.0, 'dif_sin_aldeas': 0.0, 'dif_como_esta': 17887.0}` · `comunas con diferencia sin aldeas: 0 | con aldeas como está: 19` · `Toltén 9995.0 publicado 11798 dif 1803.0 pct 18.0` · `publicado==esri_como_esta en todas: True 32` · con aldeas: `curarrehue_2025 ... reparto= 910.2`, sin aldeas `reparto= 579.4`.
- CONFIANZA: CONFIRMADO (tres fuentes: INE, servicio de Esri en vivo agrupado por `TIPO_MZ`, cruce espacial en el geojson).
- GRAVEDAD: 4.

### F-301 El error de borde declarado del A derivado mueve la cifra más que elegir entre reparto y punto

- ARCHIVO:LÍNEA: `web/data/laminas/vectorizadas.geojson` (campo `incertidumbre_borde_m`: 7.7, 8.3, 4.6, 5.3); medición en `tools/auditoria/fC_poblacion_expuesta.py` (bloque `campo_borde` de `main`).
- QUÉ PASA: encoger o engordar la mancha en su propio error declarado cambia el reparto en −25 % / +27 % (AR-2a de Angol) y −40 % / +43 % (estudio 2013). Entre reparto y punto la diferencia es menos de 1 % en la AR-2a.
- CÓMO SE VE: una cifra «4.943 personas en el área de riesgo de Angol» parece precisa, pero el mismo polígono dentro de su error da entre 3.684 y 6.291.
- CÓMO REPRODUCIRLO: `python tools/auditoria/fC_poblacion_expuesta.py`, columnas `reparto_borde_*` de `resumen_por_capa.csv`.
- SALIDA CRUDA: `angol_prc_ar2a ... reparto_borde_encogida_8.3m 3684.2  reparto_borde_engordada_8.3m 6290.9` (reparto 4942.9); `angol_estudio_2013_alto_medio ... 775.6 / 1850.7` (reparto 1290.3).
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 4.

### F-302 El A normativo junto mezcla fenómenos: el 84 % de su gente es un solo polígono de anegamiento en Temuco

- ARCHIVO:LÍNEA: `web/data/areas-riesgo-inundacion.geojson` (feature de Temuco, `clasificacion` ANEGAMIENTO, `tipo_hidrico` anegamiento, 1.596,6 ha); regla en `REGLAS.md:39-48` (§1.4).
- QUÉ PASA: cruzar «la capa A» entera da 20.179 por reparto; 16.889 de ellos son anegamiento (el polígono de Temuco aporta 16.780). Lo fluvial, que es el alcance del proyecto, son 2.708. La litoral (tsunami en Toltén, AR-3) suma 701.
- CÓMO SE VE: si se publica «20 mil personas en áreas de riesgo por inundación del plan regulador», ocho de cada diez están en un área de drenaje urbano, otro fenómeno con otra mitigación.
- CÓMO REPRODUCIRLO: `python tools/auditoria/fC_poblacion_expuesta.py`, filas `A_normativo` de `resumen_por_capa.csv`; Temuco en `expuesta_A_normativo_todas.csv`.
- SALIDA CRUDA: `A_normativo todas ... reparto= 20178.7` · `fluvial ... reparto= 2708.1` · `anegamiento ha= 1601.6 ... reparto= 16889.0` · `Temuco 290661 285 35 9457.0 15897.0 16780.3 26775.0 5.8` · `0 ANEGAMIENTO anegamiento ARRI ... 2010 [1596.6]`.
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 4.

### F-303 Entre criterios la cifra cambia hasta 50 veces, y en el radar va de 0 a 24.315

- ARCHIVO:LÍNEA: `docs/auditorias/2026-11-15/frente-C/resumen_por_capa.csv`.
- QUÉ PASA: «cualquier toque» dividido por «manzana entera» da 51,5 en la AR-2a de Angol y 42 en el A normativo fluvial; en el SAR, Curarrehue y el estudio 2013 «manzana entera» es cero. Un polígono de napa freática de 0,2 ha «expone» a 283 personas con cualquier toque y a 0,3 por reparto.
- CÓMO SE VE: quien lea un solo número no sabe si es la cota baja, la alta o el medio.
- CÓMO REPRODUCIRLO: la misma corrida.
- SALIDA CRUDA: `angol_prc_ar2a dentro 429 ... cualquier 22113 rango_x 51.5` · `sar_2026_08 0.0 773.0 873.4 24315.0` · `napa_freatica 0.2 ... 0.3 283.0`.
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 3.

### F-304 En el radar y en Curarrehue la cifra es casi entera un supuesto: gente repartida pareja en entidades rurales

- ARCHIVO:LÍNEA: `resumen_por_capa.csv` (columna `personas_reparto_rural`).
- QUÉ PASA: el 98,8 % del reparto del SAR y el 100 % del de Curarrehue y del litoral vienen de entidades rurales, donde la memoria del proyecto ya advierte que el supuesto de densidad pareja falla (la gente está en un caserío, no repartida en 40 ha).
- CÓMO SE VE: «873 personas en agua observada» puede ser 0 o varios cientos más según dónde estén las casas; el censo no lo dice.
- CÓMO REPRODUCIRLO: la misma corrida; `pct_rural` = `personas_reparto_rural / personas_reparto`.
- SALIDA CRUDA: `B_observado sar_2026_08 ... 873.4 24315.0 NaN 98.8` · `curarrehue_2025 ... 579.4 2243.0 NaN 100.0`.
- CONFIANZA: CONFIRMADO (la cifra); SOSPECHA (que el error sea grande en estos lugares: no lo medí, haría falta la ubicación de las viviendas).
- GRAVEDAD: 3.

### F-305 El modelo del GORE pone a 20 % o 40 % de la región «dentro»

- ARCHIVO:LÍNEA: `web/data/gore/amenaza-inundacion.geojson` (2.539 polígonos, `clase` MEDIA 1.863 y MAXIMA 676).
- QUÉ PASA: por reparto, 204.888 personas en clase máxima y 400.312 en media o máxima, sobre 1.003.546. Las clases son ordinales sin período de retorno (lo dice su propia procedencia). Es el número más grande del informe por un orden de magnitud y no se puede comparar con los otros.
- CÓMO SE VE: si una cifra por capa se muestra lado a lado, el GORE «gana» y se lee como el riesgo real; en Temuco son 50.896 y en Pitrufquén el 51 % de la comuna.
- CÓMO REPRODUCIRLO: la misma corrida, `expuesta_C_modelado_gore_maxima.csv`.
- SALIDA CRUDA: `gore_maxima ha= 313907.9 dentro= 95102 punto= 204571 reparto= 204888.1 cualquier= 352178` · `Pitrufquén 26848 239 65 8085.0 13322.0 13711.6 19638.0 51.1`.
- CONFIANZA: CONFIRMADO (cifra). Si el modelo sobreestima, no lo medí: SIN DATO.
- GRAVEDAD: 3.

### F-306 El JRC casi no distingue períodos de retorno a escala de manzana

- ARCHIVO:LÍNEA: `web/data/jrc/rp10.geojson` a `rp500.geojson`.
- QUÉ PASA: de 10 a 500 años el reparto sube de 16.394 a 18.577 (13 %) y siempre en las mismas 9 comunas; con píxel de ~1 km, un píxel cubre varias manzanas y el 62 % del reparto cae en entidades rurales.
- CÓMO SE VE: «la crecida de 500 años expone apenas un 13 % más que la de 10» es un artefacto de resolución, no hidrología.
- CÓMO REPRODUCIRLO: la misma corrida.
- SALIDA CRUDA: `jrc_rp10 ... reparto= 16394.3` · `jrc_rp500 ... reparto= 18577.0` · `comunas_tocadas 9 9 9 9 9 9`.
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 2.

### F-307 Las capas tienen traslapes internos que, sin disolver, cuentan dos veces

- ARCHIVO:LÍNEA: `web/data/sar/huella-observada.geojson`, `web/data/laminas/vectorizadas.geojson`, `web/data/areas-riesgo-inundacion.geojson`.
- QUÉ PASA: la suma de áreas de polígonos excede la mancha disuelta en 695 ha en el SAR (órbitas que se solapan), 76 ha en el A derivado y 24 ha en el A normativo. En Angol, sumar el estudio 2013 y la AR-2a da 6.233 personas; disueltas, 5.094: 1.139 personas contadas dos veces.
- CÓMO SE VE: cualquier cifra que se calcule polígono por polígono y se sume queda inflada.
- CÓMO REPRODUCIRLO: la misma corrida; `ha_suma_poligonos` contra `ha_disuelta`.
- SALIDA CRUDA: `B_observado sar_2026_08 1075 5779.0 5083.8` · `A_derivado todas_disueltas 174 1260.4 1184.5` · `A_normativo todas 65 2195.7 2172.1` · Angol `angol_estudio_2013_alto_medio 1290` + `angol_prc_ar2a 4943` contra `todas_disueltas 5094`.
- CONFIANZA: CONFIRMADO. El instrumento disuelve; el control 2 prueba que sin disolver da 3.700 en vez de 2.200.
- GRAVEDAD: 2.

### F-308 `hogares_agua_de_rio` son viviendas, no hogares

- ARCHIVO:LÍNEA: `scripts/19_estado_comunas.py:249`; `docs/PROXIMA_SESION.md:102` («495 hogares con agua de río»).
- QUÉ PASA: el servicio define `n_fuente_agua_rio` como «Viviendas con agua de río, vertiente u otra fuente natural». El campo publicado dice hogares. Un hogar no es una vivienda (hay allegados).
- CÓMO SE VE: hoy el visor no muestra ese campo (no aparece en `web/*.js`), pero el JSON publicado y el traspaso sí; quien lo cite subestima o sobreestima según el allegamiento.
- CÓMO REPRODUCIRLO: `curl "https://services.arcgis.com/r7t1P5pnkoOLRdhr/arcgis/rest/services/Microdatos_Censo_2024/FeatureServer/0?f=json"` y buscar el alias.
- SALIDA CRUDA: `n_fuente_agua_rio | Viviendas con agua de río, vertiente u otra fuente natural | esriFieldTypeDouble`.
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 2.

### F-309 El script 16 no baja `TIPO_MZ` y su control de totales no podía ver la duplicación

- ARCHIVO:LÍNEA: `scripts/16_censo_2024.py:73-87` (`CAMPOS` sin `TIPO_MZ`); `scripts/16_censo_2024.py:65-69` (`ESPERADO` compara conteos por capa, no que las capas sean disjuntas).
- QUÉ PASA: sin `TIPO_MZ` el archivo derivado no distingue una manzana de aldea de una urbana; la única pista es `AREA_C = Rural` en 505 «manzanas urbanas». El control de integridad pasaba con los números correctos de cada capa y la suma duplicada.
- CÓMO SE VE: la auditoría del 6-sep (`docs/auditorias/2026-09-06/frente-4-documentacion.md:76`) dio el total por bueno.
- CÓMO REPRODUCIRLO: ver el geojson: `ESRI: AREA_C de manzana_urbana: {'Urbano': 12381, 'Rural': 505}`.
- SALIDA CRUDA: la de arriba; y `'TIPO_MZ' ... alias 'Tipo de manzana'` en el servicio.
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 2.

### F-310 Redondear coordenadas para publicar no es inocuo

- ARCHIVO:LÍNEA: medición en `tools/auditoria/fC_tamano_publicable.py` (función `redondear` y bloque del control).
- QUÉ PASA: `shapely.set_precision` a 1e-5 grados movió una manzana de Temuco 34 m y cambió áreas hasta 83 %. El redondeo simple mueve como máximo 0,71 m, pero deja 209 geometrías inválidas y cambia más de 1 % el área de 2.340 unidades con 44.103 personas (las que cambian más de 5 % no tienen gente).
- CÓMO SE VE: si se publica con `set_precision`, una manzana puede aparecer corrida decenas de metros; con redondeo simple, la fracción dentro de la mancha de manzanas chicas cambia algunos puntos.
- CÓMO REPRODUCIRLO: `python tools/auditoria/fC_tamano_publicable.py --control`.
- SALIDA CRUDA: `redondeo simple a 5 decimales: corrimiento máximo 0.706 m ... cambio de área máx 54.373 %, inválidas 209` · `set_precision a 5 decimales: corrimiento máximo 34.222 m (MANZENT 9101171002018.0, Temuco) ... cambio de área máx 83.155 %` · `cambio de área > 1%: 2340 unidades, 44103 personas` · `cambio de área > 5%: 433 unidades, 0 personas`.
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 2.

### F-311 Los documentos repiten el total duplicado y el traspaso trae un desglose que no está en el archivo

- ARCHIVO:LÍNEA: `docs/PROXIMA_SESION.md:90-91` («12.381 manzanas urbanas y 4.726 entidades rurales», «1.021.433 personas»); `docs/GUIA_PRACTICANTE.md:426-429`; `docs/PRACTICA_PROFESIONAL.md:271` y `:282`; memoria `censo-2024-tres-capas-poligonos.md` (tabla con total 1.021.433).
- QUÉ PASA: 4.726 = 4.188 entidades + 505 manzanas de aldea + 33 aldeas: cuenta las aldeas dos veces dentro del «rural». El archivo etiqueta 12.886 como `manzana_urbana`.
- CÓMO SE VE: el practicante o un lector externo cita 1.021.433.
- CÓMO REPRODUCIRLO: `grep -n "1.021.433\|4.726" docs/*.md`.
- SALIDA CRUDA: `docs\PROXIMA_SESION.md:90:... **17.107 polígonos** (12.381 manzanas urbanas y 4.726` · `docs\GUIA_PRACTICANTE.md:429:| | **Total** | **17.107** | **1.021.433** |`.
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 1.

### F-312 Procedencia del censo mal rotulada

- ARCHIVO:LÍNEA: `scripts/16_censo_2024.py:27` («Requiere: nada (baja del servicio censal del INE)», pero baja de Esri); `scripts/16_censo_2024.py:166` (`capa_evidencia="D_operacional"`).
- QUÉ PASA: el censo no es evidencia operacional de inundación ni viene del INE en este script. Rotularlo D lo pone en la misma categoría que los puntos críticos de SENAPRED.
- CÓMO SE VE: en el `procedencia` del geojson: `"capa_evidencia":"D_operacional"`.
- CÓMO REPRODUCIRLO: `head -c 1500 data/processed/censo/censo-2024-araucania.geojson`.
- SALIDA CRUDA: `"capa_evidencia":"D_operacional","incertidumbre":"Espejo de Esri Chile, no del INE: ...`.
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 1.

### F-313 Siete geometrías inválidas en el censo de Esri

- ARCHIVO:LÍNEA: `data/processed/censo/censo-2024-araucania.geojson`.
- QUÉ PASA: 1 manzana y 6 entidades inválidas; en el GPKG del INE las mismas entidades son válidas (1 manzana inválida en ambos). El instrumento aplica `make_valid` antes de cruzar.
- CÓMO SE VE: un cruce sin `make_valid` puede caerse o dar áreas raras en esas siete unidades.
- CÓMO REPRODUCIRLO: `fC_censo_ine_vs_esri.py`, columnas `invalidas_*`.
- SALIDA CRUDA: `'invalidas_esri': 1, 'invalidas_ine': 1` (manzanas) · `'invalidas_esri': 6, 'invalidas_ine': 0` (entidades).
- CONFIANZA: CONFIRMADO.
- GRAVEDAD: 1.

## 6. SEGUIMIENTOS

1. **Frente A, `tools/auditoria/fA_veredicto_censo.py:76`**: pondera con `n_per` los 17.107 puntos representativos, aldeas incluidas, así que hereda el doble conteo de F-300 en las 19 comunas con aldeas. No lo toqué; que el verificador lo contraste.
2. Corregir F-300 en el origen (script 16 o cambio a la fuente INE) y regenerar `estado-comunas.json`; subir `VERSION` en `web/sw.js` si cambia lo que se ve. Es decisión del orquestador.
3. Si se publica exposición, publicarla **por subcapa y por fenómeno** (F-302), con las cuatro cifras y la banda de borde (F-301), y marcar la fracción que viene de entidades rurales (F-304).
4. Medir el tamaño con 6 decimales y con teselas vectoriales antes de decidir (no medido).
5. Para Curarrehue y el SAR, lo que falta para salir del supuesto de densidad pareja es la ubicación de las viviendas (por ejemplo, puntos de dirección del censo o edificaciones de OSM). No lo busqué.
6. Pedir al practicante su GeoPackage para comparar uno a uno (ya anotado en el traspaso).

## 7. VERIFICADO LIMPIO

Contra qué vara: cero diferencias, o desigualdades que tienen que cumplirse siempre.

- **INE y Esri traen la misma gente y la misma geometría**: 17.107 de 17.107 emparejadas, 0 diferencias en `n_per` y en los ocho campos, Hausdorff máximo 0,73 m (`salidas/fC_censo_ine_vs_esri.txt`). No hace falta volver a comparar fuentes salvo que una cambie.
- **Las 33 aldeas cuadran exacto con sus manzanas** (`'aldeas_que_cuadran': 33`), así que quitar la capa 2 no pierde a nadie.
- **Manzanas y entidades no se traslapan entre sí**: intersección total 3 m² en 242 piezas, ninguna sobre 100 m² (`manz x ent area m2 3 n pieces 242 pieces>100m2 0`, sobre el GPKG del INE). La suma manzanas más entidades es la población, sin dobles.
- **Los ocho campos de vulnerabilidad existen en las tres unidades, sin nulos**.
- **El cruce respeta dentro ≤ reparto ≤ cualquiera y punto ≤ cualquiera**, unidad por unidad, en las 19 subcapas reales (`salidas/fC_poblacion_expuesta_control.txt`).
- **La mancha del SAR disuelta mide 5.083,8 ha**, contra los 5.082 ha de la unión que declara el traspaso: 1,8 ha de diferencia, cuya causa no investigué (SOSPECHA: `make_valid` sobre los 585 polígonos inválidos).
- **La población por comuna publicada coincide con el geojson tal cual** en las 32 comunas (`publicado==esri_como_esta en todas: True 32`): el error de F-300 está en el dato, no en el script 19.

## 8. SIN DATO

- Unidades exactas de los campos `n_*` según el INE: su diccionario sólo documenta las variables geográficas. Usé el alias del servicio de Esri.
- Si las entidades rurales concentran su gente lejos o cerca de las manchas (F-304): requiere ubicación de viviendas.
- Si el modelo del GORE sobreestima o no: su informe metodológico no está publicado.
- Comparación uno a uno con el practicante: no tenemos sus polígonos.
- Peso con 6 decimales, con simplificación o en teselas vectoriales.
- Las capas no se validaron en terreno; este informe mide exposición potencial sobre lo publicado, no riesgo.
