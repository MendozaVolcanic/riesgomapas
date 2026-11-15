# Frente B: GeoIDE del MINVU contra lo que riesgomapas ya tiene

- Hora del servidor (cabecera HTTP Date): Sun, 15 Nov 2026 11:12:32 GMT. Descarga de las 38 capas terminada 11:15:32 UTC.
- Commit del repo auditado: `ef2f534` (rama `visor-simple-y-laminas-vectorizadas`).
- Modelo: Sonnet 5.5. Rango de IDs: F-200 a F-214.
- Carpeta: `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\docs\auditorias\2026-11-15\frente-B\`
- Descargas crudas: `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\data\raw\geoide_minvu_araucania\` (38 capas `capa_NN.json`, `capa_29_wkid32718.json`, `ipt_area_riesgo_L0_araucania_wkid32718.json`, `pri_araucania_L3_...json`, `barrido_servicios.json`).
- Instrumentos (todos con `--control`, sin commitear): `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\tools\auditoria\fB_*.py`.

**Qué NO miré.** Las 13 carpetas de GeoIDE que exigen token (no hay forma anónima de listarlas, F-210). El contenido de las capas MapServer de `Informacion_Regional/Ar_Araucania` más allá de conteos, extensión y muestra de 3 filas. Los vectoriales de las otras 13 regiones. Nada contra el terreno (ortofoto, predios): todo es geometría contra geometría, así que no sé cuál de las dos está bien ubicada, solo cuánto difieren. No toqué `web/`, `scripts/`, `tests/`, `config/`, ni `docs/` existentes. No hice commit.

## En una pantalla

1. GeoIDE trae Angol con 81 polígonos de riesgo, 21 hídricos (AR-2a 10 con 282,2 ha, AR-2b anegamiento 11 con 15,6 ha); el proyecto sigue diciendo 0 y su capa derivada no tiene el AR-2b (F-201).
2. Nuestros 54 AR-2a derivados caen 90,5 % dentro del AR-2a oficial pero cubren solo 72 % de él (225 contra 282 ha, IoU 0,671); el resto son 70 ha en 61 piezas grandes, no un corrimiento: la mejor traslación es (-4, -3) m y sube el IoU solo a 0,680 (F-200).
3. El IoU de 0,20 queda explicado: es plan AR-2a contra estudio de peligro 2013, dos fuentes distintas; con la geometría oficial da 0,189 (nuestra 0,202), así que no era un defecto del vectorizador (F-202).
4. Faltan en la capa A publicada: Nueva Imperial (nuestro polígono es una versión vieja, IoU 0,10 contra la Resolución 111 de 2025), Renaico (el pueblo entero, 16 ha) y Toltén (Nueva Toltén y Villa Boldos, 21,9 ha) (F-203, F-204, F-205).
5. GeoIDE no resuelve los años faltantes: solo Nueva Imperial trae fecha y es de otra versión; además existe un servicio regional de inundación costera sin uso (F-208) y el agregado `IPT/IPT_AREA_RIESGO` capa 0 sí incluye Angol (F-209).

## Parte 1: inventario de GeoIDE

Tabla completa por capa: `inventario_geoide.csv` (38 filas). Cruce por comuna contra el proyecto: `inventario_comuna.csv`. Salidas crudas: `salida_cruce_comuna.txt`.

Servicio `IPT/PRC_Araucania/FeatureServer`: 38 capas, `maxRecordCount` 2000, ninguna se acerca al límite (la mayor es Temuco con 1788), todas bajaron en una página y el conteo bajado igual al `returnCountOnly` en las 38 (salida de `fB_geoide_descarga.py`, ejemplo `29 PRC_Angol_Area_de_riesgo servicio= 81 bajados= 81 paginas=1 OK`). El servicio es nativo en EPSG:32718.

Hay tres tipos de capa: 11 capas de área de riesgo propias (sufijo `Area_de_riesgo` o `_AR`), capas de zonificación que llevan zonas de riesgo mezcladas (Pitrufquén R1-A, Traiguén ZR1, Gorbea AR1, Carahue Z-R9/Z-R10, Saavedra «Inundable restringida», Villarrica ZR-4/ZR-9, Temuco ZE7), y `Limite_Urbano` (28).

Hídricos por comuna (clasificación propia sobre ZONA y NOM; polígonos, no anillos):

| Comuna | Polígonos hídricos GeoIDE | ha | Proyecto (capa A) | ha | Lectura |
|---|---:|---:|---:|---:|---|
| Angol | 21 (10 inund., 11 aneg.) | 288,6 | 0 | 0 | proyecto dice sin vectorial (F-201) |
| Carahue | 8 (+2 ZR-1a/1b que mi clasificador omite) | 104,3 | 9 | 107,3 | coincide (IoU 0,971) |
| Collipulli | 41 | 111,9 | 38 | 143,1 | coincide; los 32 ha extra son ZR-3 «en torno a canales», que mi clasificador omite pero GeoIDE tiene idéntico (F-211) |
| Gorbea | 1 | 10,8 | 1 | 10,8 | IoU 1,0 |
| Loncoche | 0 reconocibles (2 zonas ZR-2A/ZR-2B sin texto) | 0 | 2 | 19,1 | GeoIDE no dice que sean hídricas: SIN DATO |
| Nueva Imperial | 9 | 154,7 | 1 | 18,3 | IoU 0,101 (F-203) |
| Pitrufquén | 4 | 77,6 | 4 | 77,6 | IoU 1,0 |
| Renaico | 20 | 23,8 | 1 | 7,8 | IoU 0,329 (F-204) |
| Saavedra | 1 | 46,3 | 1 | 46,3 | IoU 1,0 |
| Temuco | 2 | 1595,7 | 1 | 1594,3 | IoU 0,999 |
| Toltén | 21 (incluye 3 litorales y napas) | 99,2 | 4 | 77,3 | IoU 0,779 (F-205) |
| Traiguén | 1 | 55,7 | 1 | 55,7 | IoU 1,0 |
| Villarrica | 2 | 10,9 | 2 | 10,9 | IoU 1,0 |
| Pucón, Victoria | 0 | 0 | 0 | 0 | solo hay zonas de protección (Pucón ZR-6 «Zona ZR-6» sin texto; Victoria ZR-1 vertientes y cursos de agua) |

Comunas donde el proyecto dice no tener vectorial y GeoIDE sí lo tiene: Angol (el único caso). Para las demás comunas con `le_falta` de vectorial (Cholchol, Cunco, Curacautín, Curarrehue, Ercilla, Freire, Galvarino, Lautaro, Lonquimay, Los Sauces, Lumaco, Melipeuco, Padre Las Casas, Perquenco, Pucón, Purén, Teodoro Schmidt, Vilcún, Victoria) GeoIDE no trae ningún polígono hídrico: o no tienen capa en las 38 (Cholchol, Cunco, Ercilla, Galvarino, Los Sauces, Lumaco, Melipeuco, Perquenco, Purén, Teodoro Schmidt, Vilcún) o su capa es solo zonificación (Curacautín, Freire, Lautaro, Lonquimay, Padre Las Casas, Victoria, Pucón). Lo verificado es la lista de capas y sus ZONA/NOM; no que no se inunden. Curarrehue no aparece entre las 38 capas.

Datos del instrumento (T_DO, N_DOC, P_DO). Solo 11 de las 37 capas de zonas los traen (16, 27, 29 a 37). Angol: Resolución 40, 14/10/2022 (81 de 81 y 890 de 890). Renaico: Resolución 90, 18/02/2023. Nueva Imperial: Resolución 111, 26/07/2025 (capas 16 y 33). Toltén Nueva Toltén y Boldos: Resolución 38, 08/05/2026. Las demás comunas no traen ningún campo de instrumento (F-207: el significado de `P_DO` tampoco está documentado).

Los cuatro polígonos sin año (F-206): en la capa publicada son tres (Loncoche ZR-2A, ZR-2B, Nueva Imperial ZR-1); Pucón ZR-6 está en `data/processed/areas_riesgo_prc_araucania.geojson` con `es_inundacion` falso, así que no se publica. GeoIDE no trae fecha para Loncoche ni Pucón. Para Nueva Imperial trae 26/07/2025, pero esa fecha corresponde a nueve polígonos AR-1/AR-2 que no son nuestro ZR-1: no se puede asignar a nuestro polígono sin decidir antes que es la misma versión (IoU 0,10 dice que no).

Otros servicios (barrido de `/server/rest/services`, 22 carpetas, 135 servicios listados, `barrido_servicios.json`):
- `IPT/IPT_AREA_RIESGO` capa 0 `PRC_Area_de_Riesgo`: agregado nacional del propio GeoIDE. Filtrado a Araucanía da 249 polígonos y **incluye Angol**; contra las 38 capas el IoU por comuna es 1,0 (F-209).
- `IPT/IPT_AREA_RIESGO` capa 2 `PRI_Areas_de_Riesgo`: 2 polígonos en Araucanía, solo remoción en masa. `IPT/PRI_Araucanía` capa 3 (PRI Villarrica-Pucón, 16): solo aluviones y deslizamientos, nada hídrico.
- `Informacion_Regional/Ar_Araucania` (MapServer): profundidad de inundación, tiempos de arribo y velocidad, extensión lon -73,50 a -73,07, lat -39,41 a -38,60, comunas Carahue y Saavedra (F-208, SOSPECHA de que es inundación por tsunami).
- `Inventario_de_Humedales` (MapServer, 2020): humedales con COMUNA. Contexto, no amenaza.
- 13 carpetas bloqueadas por token (F-210).

## Parte 2: Angol, geometría contra geometría

Todo en EPSG:32718. GeoIDE bajado también con `outSR=32718` para no pasar por 32719. Salida completa: `salida_angol_geometria.txt`, `salida_angol_residuo.txt`, `angol_geometria.json`.

Qué se comparó. GeoIDE `ZONA = AR-2a`, «Áreas de Riesgo Inundables o Potencialmente Inundables»: 10 features, 15 anillos, 282,21 ha. Nuestros 54 polígonos AR-2a (lámina 1: 26, incertidumbre declarada 8,3 m; lámina 2: 28, incertidumbre 4,6 m): 225,22 ha. **Representan lo mismo**: misma zona del plan, mismo nombre de clase, y 90,5 % de nuestra área cae dentro del AR-2a oficial. No es otra versión ni otra zona (otra clase: solo 0,7 % cae en AR-2b, 4,5 % en AR-1b, 1,3 % en AR-1c, 6,2 % fuera de todo).

| Medida | Resultado |
|---|---|
| IoU global | 0,671 (intersección 203,84 ha) |
| Nuestra área dentro de GeoIDE / GeoIDE cubierta por nosotros | 0,905 / 0,722 |
| Distancia entre centroides | 68,0 m (efecto del área faltante, no de corrimiento) |
| Traslación que maximiza el IoU (global) | (-4, -3) m, IoU 0,680 |
| Lámina 1 (n=26): IoU, mejor traslación | 0,634; (-9, +3) m, IoU 0,658 |
| Lámina 2 (n=28): IoU, mejor traslación | 0,645; (-1, -8) m, IoU 0,661 |
| Fracción de la diferencia que cabe en la incertidumbre declarada | 0,38 con u=8,3 m global; lámina 1 con 8,3 m: 0,28; lámina 2 con 4,6 m: 0,25 (sube a 0,40/0,41 con 2u y 0,45/0,51 con 3u) |

Lectura (F-200). Un corrimiento no explica la diferencia: la mejor traslación global es de 5 m y mejora el IoU en 0,009. La incertidumbre declarada tampoco la explica: solo 38 % de la diferencia queda a 8,3 m o menos del borde de la otra geometría. Lo que falta es área: GeoIDE tiene 78,4 ha que no están en la nuestra, de ellas 69,8 ha en 61 piezas mayores de 2000 m2 (la mayor 11,1 ha) y 8,3 ha en 385 piezas chicas; 33 % de lo faltante está a 8,3 m o menos del borde de lo nuestro, 56 % a 25 m o menos. Por feature de GeoIDE: el grande (OBJECTID 67, 171,4 ha) lo cubrimos 66,9 % con 32 de nuestros polígonos; los dos más pequeños (OBJECTID 6 y 7, 0,15 y 0,24 ha) 0 %; el 53 (2,3 ha) 18 %. Tres de nuestros polígonos (30.003, 3.088 y 15.890 m2) no tocan el AR-2a oficial, a 249, 164 y 51 m. Además nuestro exceso sobre GeoIDE es 21,4 ha, de ellas 11,8 ha a 8,3 m o menos del borde oficial (compatible con incertidumbre de borde).

Consecuencia para quien decide: una parcela dentro del AR-2a oficial pero en una de esas piezas faltantes recibe «no cae en área de riesgo del plan regulador» desde nuestra capa derivada. Ese es el error de la clase que más importa (falso negativo).

Qué explica el IoU de 0,20 (F-202). Es el que la configuración (`config/laminas.yaml:136-141`) cita contra el estudio de peligro 2013 (96 polígonos Alto y Medio, 213,1 ha). Reproducido: nuestro AR-2a contra Alto+Medio 0,202; **el AR-2a oficial de GeoIDE contra el mismo estudio 0,189**; contra Alto solo 0,172 (nuestro) y 0,152 (oficial). Que la geometría oficial dé lo mismo prueba que el 0,20 mide la distancia entre dos productos distintos (un estudio morfométrico de 2013 sin hidráulica y el plan regulador de 2022), no un error de vectorización ni de color.

Límites de esta medición. Las métricas por polígono (IoU con el feature de mayor solape, Hausdorff, p95 de borde) comparan un fragmento nuestro contra un feature oficial entero y salen sin sentido (IoU mediano 0,014, Hausdorff mediano 3503 m, F-212): no las uso como evidencia. La métrica válida por polígono es la fracción dentro del AR-2a (mediana 0,913; 48 de 54 con 50 % o más; 30 con 90 % o más). No sé cuál de las dos geometrías está mejor ubicada respecto del terreno.

## Hallazgos

Ver `hallazgos.csv` (columnas id, titulo, archivo_linea, confianza, gravedad, eje, comando_reproduccion, salida_cruda). Orden por gravedad:

| ID | Gravedad | Confianza | Título |
|---|---:|---|---|
| F-200 | 4 | CONFIRMADO | Los 54 AR-2a derivados cubren 72 % del AR-2a oficial de Angol; faltan 78 ha en piezas grandes |
| F-201 | 4 | CONFIRMADO | Angol tiene vectorial oficial (21 hídricos, incl. AR-2b anegamiento) y el proyecto declara 0 |
| F-203 | 4 | CONFIRMADO | Nueva Imperial: polígono sin año de versión vieja; GeoIDE trae 154,7 ha, Resolución 111 de 2025 |
| F-204 | 4 | CONFIRMADO | Renaico: falta el pueblo (19 AR-1, 16 ha) |
| F-205 | 3 | CONFIRMADO | Toltén: faltan Nueva Toltén y Villa Boldos (21,9 ha) |
| F-208 | 3 | SOSPECHA | MapServer regional de inundación costera sin uso |
| F-209 | 3 | CONFIRMADO | El agregado `IPT_AREA_RIESGO` capa 0 de GeoIDE sí trae Angol |
| F-202 | 2 | CONFIRMADO | El IoU de 0,20 es plan contra estudio 2013, no un defecto |
| F-206 | 2 | CONFIRMADO | Los «cuatro sin año» son tres; GeoIDE no los resuelve |
| F-207 | 2 | SOSPECHA | `P_DO` no está documentado; valores basura |
| F-210 | 2 | CONFIRMADO | 13 carpetas con token, indistinguibles de una inexistente |
| F-211 a F-214 | 1 | CONFIRMADO | Límites de mi propio instrumento y cosméticos (ZR-3 y «causes», métrica por polígono, CRS, campo hectáreas) |

## SEGUIMIENTOS (para quien orquesta, no los hice)

1. Decidir si la capa A de Angol pasa a ser el vectorial oficial de GeoIDE (capa 29 o `IPT_AREA_RIESGO/0`) y la derivada se degrada a validación. Mantener separadas ambas (REGLAS 1.3).
2. Cambiar la fuente nacional de la capa A de `services3.arcgis.com/.../prc_riesgo_nacional_visor_P` a `IPT/IPT_AREA_RIESGO/FeatureServer/0`, y rehacer Renaico, Nueva Imperial y Toltén (F-203 a F-205). Medir antes de tocar: es hipótesis hasta que lo repita quien arregla.
3. Incluir el AR-2b (anegamiento) de Angol; hoy solo existe la clase AR-2a (`config/laminas.yaml:169`).
4. Mirar por qué el detector de achurado pierde 70 ha en piezas grandes (no es el corrimiento): densidad mínima, ventana, o calles/edificación sobre el achurado.
5. Confirmar con el MINVU qué significa `P_DO` antes de publicarlo como «año del instrumento».
6. Evaluar `Informacion_Regional/Ar_Araucania` como capa C (modelada) de inundación costera, separada de la fluvial (REGLAS 1.4). Verificar si es tsunami.
7. Pedir a Nicolás si tiene acceso para listar las carpetas con token (PEGIR_2025, Suelo, Urbano).

## VERIFICADO LIMPIO (contra qué vara)

- Paginación y descarga: las 38 capas, conteo bajado = `returnCountOnly` (salida en `fB_geoide_descarga.py`); `--control` con pageSize 7: 81 en 12 páginas contra 81 en 1, ids iguales, y el defecto «solo primera página» da 7 distinto de 81 (detectado). Misma prueba en `fB_geoide_descarga_ipt.py` (249 con pageSize 40 y 2000; filtro `REG='ZZZ'` da 0).
- Cifras del traspaso: Angol capa 29 = 81 polígonos, `T_DO` Resolución, `N_DOC` 40, `P_DO` 14/10/2022 (81 de 81); Collipulli capa 23 = 68; Renaico capa 31 = 20. Coinciden con `docs/PROXIMA_SESION.md` sección 2. «Lo que teníamos»: Collipulli 38, Renaico 1, Angol 0 (confirmado en la capa publicada y en `estado-comunas.json`).
- Coincidencia exacta con GeoIDE (IoU 1,0, cruce por comuna): Gorbea, Pitrufquén, Saavedra, Traiguén, Villarrica; Temuco 0,999; Carahue 0,971 y Collipulli 0,771 solo por mi clasificador (F-211), con el mismo dato en ambas.
- Las 38 capas coinciden con `IPT_AREA_RIESGO/0` (IoU 1,0 por comuna), así que no hay dos versiones del dato dentro de GeoIDE.
- Controles de los cuatro instrumentos de medición corridos y en verde: clasificador (positivos, negativos, mutación borrando 3 polígonos 21 a 18, NOM vaciado 21 a 0), cruce por comuna (identidad IoU 1, corrimiento 20 m IoU menor en 12 de 12 comunas, cuadrado analítico 0,6667 medido 0,6667, mitad de polígonos Collipulli 112 a 55,8 ha, y control de CRS entre fuentes), Angol (identidad, corrimiento (20,-10) recuperado como (-20,+10) con IoU óptimo 1,0, corrimiento 3 m con explicada 1,0, mitad de polígonos cobertura 1,0 a 0,192) y descomposición del residuo (3 huecos de 2700 m2 recuperados, franja, identidad).
- Dos controles fallaron en su primer diseño y se corrigieron (se dejó anotado en los scripts): «borrar la mitad» medido sobre el total (lo domina Temuco) y la descomposición de residuo con distancia Hausdorff simétrica y una franja que borraba brazos enteros.

## SIN DATO

- Cuál geometría está mejor ubicada respecto del terreno (no se comparó contra ortofoto ni predios).
- Qué contienen las 13 carpetas con token.
- Si `Ar_Araucania` es tsunami (descripción vacía; es inferencia por «tiempos de arribo» y la extensión costera).
- Qué significa `P_DO` y si 14/10/2022 es fecha de resolución o de publicación.
- Si GeoIDE es más nuevo, igual o más viejo que el servicio `services3` que usamos para el resto de las comunas (no se midió fecha de edición: el servicio no la expone, `lastEditDate` None en la capa 29).
- Loncoche ZR-2A y ZR-2B: GeoIDE no declara fenómeno (nombre «Zona ZR-2A»), así que no corrobora que sean inundación.
