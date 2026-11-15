# Verificación del frente B (GeoIDE MINVU vs proyecto)

Verificador con contexto limpio, 2026-11-15, repo en commit c9ac59f.

Registro previo a abrir el informe del auditor (09:45:30 -0300):

```
1f30eed81e495604588c7d581cef67010a691f7dbc7609f293e2687878e20653 *docs/auditorias/2026-11-15/frente-B/INFORME.md
011c275c0407d3f3093e19cbdf2b657e3ca20d6e5e1752786e5ea34979f4af05 *docs/auditorias/2026-11-15/frente-B/hallazgos.csv
```

## 1. Caminos de ruptura, escritos antes de releer nada

F-200 (72 % de cobertura, faltan 78 ha en 61 piezas, no es corrimiento)
- La capa 29 no es Angol o mezcla Angol con otra comuna (filtro por comuna mal hecho).
- El filtro de clase toma AR-2a de nuestra capa pero en GeoIDE incluye AR-2b o AR-1 (otro universo).
- Proyección: se intersecta 32718 con 32719 o con grados, y la diferencia es de sistema, no de dato.
- El 72 % es área de intersección sobre GeoIDE, pero se calcula sin disolver: polígonos superpuestos en GeoIDE cuentan doble.
- 78 ha vs 70 ha: una es diferencia bruta y otra con buffer; o una incluye fragmentos menores a un umbral.
- "No es corrimiento" se afirma sin medir el desplazamiento óptimo (un corrimiento de 10 a 20 m en zonas angostas también deja residuo).
- La descarga de GeoIDE está truncada (exceededTransferLimit) y faltan polígonos, o al revés, sobra.
- Nuestra capa publicada no es la que lee el script (lee data/processed u otra versión).

F-201 (Angol: 21 hídricos, 10 AR-2a y 11 AR-2b; el proyecto declara 0)
- El "0" de estado-comunas.json se refiere a otra cosa (capa A MINVU vectorial, no la derivada), y entonces es correcto en su propio sentido.
- AR-2b "anegamiento" puede no ser inundación fluvial sino remoción u otra cosa; el clasificador por texto lo mete mal.
- El conteo 10 + 11 depende de multipartes vs partes.
- config/laminas.yaml:169 ya no dice lo que el auditor cita.
- El AR-2b sí está en nuestra capa con otro código de clase.

F-202 (IoU 0,20 es entre fuentes distintas)
- La comparación con geometría oficial usa la misma referencia que la comparación original, y el 0,189 no prueba nada sobre la causa.
- config/laminas.yaml:136-141 no documenta la fuente que se cita.
- El IoU de 0,20 original se calculó contra otra cosa que el auditor no identifica bien.

F-203, F-204, F-205 (Nueva Imperial, Renaico, Toltén desactualizados o incompletos)
- Los polígonos de GeoIDE son otra zona (ZR no hídrica, por ejemplo área verde) que el clasificador cuenta como hídrica.
- Los polígonos "faltantes" sí están en nuestra capa con otro nombre de comuna o localidad.
- Las hectáreas se calculan en grados o en zona UTM equivocada.
- La resolución y fecha salen de un campo que no es fecha de aprobación (ver F-207).
- La capa 31, 9, 34, 37, 33 no corresponden a esas comunas.
- Nuestro polígono "viejo" coincide geométricamente con GeoIDE y la diferencia es solo de atributos.

F-206 (cuatro sin año son tres)
- PROXIMA_SESION.md:121 no dice "cuatro".
- Pucón ZR-6 sí está en la capa publicada como inundación.
- data/processed y web/data difieren por diseño.

F-207 (P_DO no documentado)
- GeoIDE sí documenta P_DO en el metadato del servicio (alias del campo).

F-208 (MapServer regional costero)
- El servicio no existe o pide token.
- Es tsunami, no inundación fluvial; o es otro tema (borde costero administrativo).

F-209 (IPT_AREA_RIESGO capa 0 coincide con las 38 capas)
- "Coincide" sin comparar geometrías, solo conteos.
- La consulta filtró por región mal y trae otras regiones.

F-210 (13 de 22 carpetas token)
- Conteo sobre una lista distinta; carpetas que responden error por otro motivo.

F-211 a F-214 (instrumentos y aritmética)
- F-211: la expresión regular sí incluye canal o cauce.
- F-213: el inflado depende de la latitud; 0,14 % puede ser otro factor.
- F-214: hectareas suma de otro filtro; geometría en otra proyección.

Duplicado F-180 (vA): 49,12 ha con buffer de 10 m vs 78/70 ha sin buffer; la diferencia puede ser buffer, denominador o versión de capa.

Abrí INFORME.md y hallazgos.csv recién a las 09:58:27, después de medir F-200 a F-206 y F-208 a F-210. A esa hora el sha256 de INFORME.md seguía siendo `1f30eed8...0653`.

## 2. Instrumentos nuevos (todos con sus dos preguntas en el encabezado)

| Instrumento | Mide | Control |
|---|---|---|
| `tools/auditoria/vB_angol_porque_falta.py` | cobertura de G (AR-2a GeoIDE) por N (nuestros AR-2a), piezas de G-N, densidad de marcas de la lámina en cada pieza, traslación óptima, recortes PNG | `--control`: borra el N más grande (tiene que salir «achurado perdido») e inyecta en G un cuadrado sin trama (tiene que salir «sin achurado»). Ambos OK |
| `tools/auditoria/vB_angol_fondo_oscuro.py` | luminancia del fondo de la lámina en G∩N y G-N, densidad de marcas con contraste 28 y 14, descomposición de G-N | `--control`: cuadrado de fondo oscuro sin AR, 0 marcas/ha con ambos contrastes |
| `tools/auditoria/vB_angol_contraste_bajo.py` | lo que recupera el MISMO vectorizador bajando `contraste_minimo` | se aborta si con 28 no reproduce el N publicado (lo reproduce: 0,722) |
| `tools/auditoria/vB_cruce_comunas_geoide.py` | Renaico, Nueva Imperial, Toltén: GeoIDE (descarga propia) contra la capa A publicada | `--control`: inyecta GeoIDE de Toltén en nuestra capa, cobertura 1,000 OK; chequeo vivo Tijeral ∩ capa 9 = 7,84 ha |
| `tools/auditoria/vB_ipt_agregado_vs_capas.py` | agregado IPT_AREA_RIESGO/0 contra capas por comuna | Angol contra sí mismo IoU 1 |

Las salidas crudas están en esta carpeta (`salida_vB_*.txt`), y los recortes de la lámina en `recortes_angol/` (rojo = AR-2a GeoIDE, azul = nuestro AR-2a). Mis descargas están en `data/raw/geoide_minvu_araucania_verif/`: la capa 29 completa en 32718 (81 features, count del servicio 81, sin `exceededTransferLimit`), las capas 9, 31, 33, 34 y 37, el MapServer Ar_Araucania y el barrido de carpetas.

## 3. La pregunta central: por qué faltan hectáreas del AR-2a de Angol

Salida cruda (`salida_vB_angol_porque_falta.txt`, `salida_vB_angol_fondo_oscuro.txt`):

```
[real] G: 10 features, suma 282.21 ha, disuelto 282.21 ha (solape interno 0.00 ha)
[real] N: 54 polígonos, disuelto 225.22 ha; suma campo hectareas 227.57 ha
[real] G∩N 203.84 ha | cobertura de G 0.722 | G-N 78.37 ha | N-G 21.38 ha | IoU 0.671
[real] G fuera de la huella útil de ambas láminas: 0.00 ha; de G-N, fuera de huella: 0.00 ha
[real] densidad de marcas AR-2a en G∩N: 149 /ha (30438 marcas); en un anillo de 300 m fuera de G∪N: 5 /ha
[real] G-N en 448 piezas; >=2000 m2: 61 piezas, 69.83 ha; <2000 m2: 387 piezas, 8.54 ha
[real] traslación óptima (-4,-4) m -> IoU 0.680; G-N tras trasladar 76.86 ha
[real] G-N después de engordar N 10 m: 49.12 ha
== angol-prc-ar2a-lamina1 ==
  contraste 28: marcas/ha G∩N 157 | G-N claro 32 | G-N oscuro 22 | anillo ruido 3 | anillo ruido oscuro 2
  contraste 14: marcas/ha G∩N 148 | G-N claro 25 | G-N oscuro 86 | anillo ruido 8 | anillo ruido oscuro 5
== angol-prc-ar2a-lamina2 ==
  contraste 28: marcas/ha G∩N 128 | G-N claro 39 | G-N oscuro 21 | anillo ruido 5 | anillo ruido oscuro 2
  contraste 14: marcas/ha G∩N 104 | G-N claro 26 | G-N oscuro 91 | anillo ruido 7 | anillo ruido oscuro 6
== Descomposición de G-N (celdas de 3 m) ==
  borde<=10m            29.14 ha
  oscuro>10m            23.56 ha
  claro>10m_en_AR2b      2.27 ha
  claro>10m_resto       23.41 ha
  total 78.38 ha (G-N exacto 78.37 ha)
```

Lectura, separando las tres causas que pidió el orquestador:

- **(c) Error de georreferencia: descartado.** La mejor traslación es (-4,-4) m y sube el IoU de 0,671 a 0,680; el faltante solo baja de 78,37 a 76,86 ha. Nada de G cae fuera de la huella de las láminas.
- **(a) El vectorizador no vio la trama: es la causa principal.** En los recortes `recortes_angol/pieza1..6` se ve que la lámina SÍ achura AR-2a sobre las zonas oscuras Z-1 (rojo, centro de Angol, corredor del canal Pochochingue, pieza 1 de 11,1 ha) y Z-5 (café, piezas 2, 3 y 4), y que el contorno rojo de GeoIDE sigue ese achurado. El detector exige que el triángulo sea 28 niveles de gris más oscuro que su vecindad (`scripts/18_vectorizar_laminas.py`, `mascara_por_trama`), y sobre fondo oscuro no lo es. Al bajar el contraste a 14, la densidad en G-N oscuro sube de 21-22 a 86-91 marcas/ha, contra 5-6 de ruido sobre fondo oscuro sin AR. Son 23,6 ha a más de 10 m de lo nuestro. Bajar el contraste para toda la lámina NO lo arregla: con 14 la cobertura cae a 0,689 y aparecen 122,9 ha fuera del oficial (`salida_vB_angol_contraste_bajo.txt`).
- **Borde: 29,1 ha** de lo faltante están a 10 m o menos de nuestro polígono. Es más ancho que la incertidumbre declarada (4,6 y 8,3 m).
- **Resto: 23,4 ha** sobre fondo claro a más de 10 m, con 25-39 marcas/ha (contra 104-157 dentro y 3-5 de ruido): achurado ralo o pisado por otra trama (el rayado del AR-1a, calles). En la pieza 5 se ve el AR-2a cruzado con el rayado del AR-1a. El detalle fino queda SIN DATO.
- **(b) Versiones distintas del plan: sin evidencia para la geometría AR-2a.** El contorno de GeoIDE calza con el achurado de la lámina en los seis recortes. GeoIDE es la Resolución 40, publicada en el Diario Oficial el 14/10/2022 (`data/raw/documentos/angol/PRC_Publicación Diario Oficial.pdf`, página 1: «(Resolución) Núm. 40.- Temuco, 6 de junio de 2022», «Viernes 14 de Octubre de 2022»). Lo único con aire de versión distinta es de codificación: la lámina rotula AR-2b corredores que GeoIDE dibuja dentro del AR-2a (9,26 de las 15,64 ha de AR-2b están encima del AR-2a; ver F-281). Si las Enmiendas II de 2026 cambiaron áreas de riesgo es SIN DATO.

**Conclusión para decidir:** nuestra capa derivada de Angol es una copia degradada del mismo plano que GeoIDE ya publica en vectorial con sus atributos legales, y además le falta el AR-2b. La evidencia respalda reemplazarla por la oficial. Eso lo decide quien orquesta.

## 4. Veredictos

### F-200 | CONFIRMADO EN PARTE | gravedad 4
Las cifras se reproducen con descarga propia: cobertura 0,722, G-N 78,37 ha, 61 piezas de 2000 m2 o más con 69,83 ha, y 387 piezas chicas con 8,54 ha. **78 contra 70:** el faltante total es 78,4 ha, y 69,8 ha de ese total están en las 61 piezas grandes. El título junta las dos cifras y está mal escrito («78 ha en 61 piezas»). «No es corrimiento» se sostiene (traslación óptima de 4 m, +0,009 de IoU). Lo que no se sostiene es leerlo como «no es borde»: 29,1 ha (37 %) están a 10 m o menos de lo nuestro. La causa medida está en la sección 3 y en F-282.
**Fusión con F-180 (verificador A):** es el mismo G y el mismo N. Las 49,12 ha de F-180 son el G-N después de engordar N 10 m (mi salida: `G-N después de engordar N 10 m: 49.12 ha`), y 49,12 / 282,21 = 17,4 %. El 89,9 % del AR-2b de F-180 es sin buffer: mi salida da «cubierto por N 0.101». Las tres cifras (78,4, 69,8 y 49,1 ha) son el mismo faltante medido de tres maneras.

### F-201 | CONFIRMADO | gravedad 4
En `web/data/estado-comunas.json`, Angol figura con `"poligonos_area_riesgo": 0` y con el `le_falta` «no tiene su área de riesgo por inundación en el vectorial público del MINVU». La frase sale de `scripts/19_estado_comunas.py:234-235`. El proyecto consulta el ArcGIS Online del MINVU (`scripts/06_areas_riesgo_prc.py:64`, `services3.arcgis.com/cTnMkBRk4HWkUCRo`), que no trae Angol; GeoIDE, también del MINVU, sí: la capa 29 tiene 10 AR-2a «Inundables o Potencialmente Inundables» y 11 AR-2b «por Anegamiento», Resolución 40, P_DO 14/10/2022 (descarga propia). La frase que se muestra al público es falsa. `config/laminas.yaml` declara una sola clase, AR-2a, en las dos láminas (líneas 168-169 y el bloque de la lámina 2), así que el AR-2b no está: lo nuestro lo cubre en 10,1 % (salida `[AR-2b] 15.64 ha ... cubierto por N 0.101`). Anegamiento es amenaza hídrica, así que pertenece a la capa.

### F-202 | CONFIRMADO | gravedad 1
Reproducido: `estudio2013 Alto+Medio 213.1 ha; IoU N vs E 0.202; IoU G vs E 0.189`. El IoU de 0,20 mide la distancia entre el plan y el estudio de 2013, no un defecto del vectorizador. El comentario está en `config/laminas.yaml:147` y `:207`, no en 136-141. Ese comentario ya lo usa solo para decir que el año no se deduce, así que es coherente con esto: baja a 1.

### F-203 | CONFIRMADO EN PARTE | gravedad 4
Salida: `Nueva Imperial capa 33: hídrico GeoIDE 154.71 ha (9 feats); cubierto por el visor 0.102; visor dentro de esta capa (cualquier zona) 0.868`, Resolución 111, 26/07/2025. Confirmado: el visor publica 18,25 ha (ZR-1, sin año) y GeoIDE trae 154,7 ha de áreas hídricas vigentes, así que el 90 % del área inundable oficial no está en el visor. Tres matices. (1) Los 154,7 ha incluyen la localidad Villa Almagro (LOC en la capa). (2) Que ZR-1 sea «una versión vieja» del mismo plan es una inferencia razonable (otra nomenclatura, EAE de 2011, 87 % dentro de la capa nueva), pero no está demostrada. (3) GeoIDE codifica un polígono de 94,10 ha con ZONA «AR-2» y NOM «AR-1 ... inundables»: los atributos se contradicen en el origen.

### F-204 | CONFIRMADO | gravedad 4
Salida: capa 31 `19 x AR - 1 Zonas inundables o potencialmente inundables 15.97 ha`, Resolución 90, 18/02/2023; `cubierto por el visor 0.000; distancia visor-capa 6076 m`. El visor solo tiene Tijeral AR-1 (7,84 ha, idéntico a la capa 9). El AR-2 de Tijeral (8,10 ha, NOM vacío en GeoIDE) es remoción en masa según `data/processed/areas_riesgo_prc_araucania.geojson`; está bien que no se publique.

### F-205 | CONFIRMADO | gravedad 3
Salida: capa 34 Nueva Toltén, 6 features y 13,34 ha; capa 37 Villa Los Boldos, 11 features y 8,57 ha. En total, 17 polígonos y 21,91 ha, Resolución 38, 08/05/2026, cobertura del visor 0,000. Incluyen napa freática y cercanía a río.

### F-206 | CONFIRMADO | gravedad 2
Lo que el traspaso llama «cuatro polígonos sin año» está en `docs/PROXIMA_SESION.md:121` (y repetido en la 248). En la capa publicada hay 3 sin año (Loncoche ZR-2B, Loncoche ZR-2A y Nueva Imperial ZR-1). En processed son 4; el cuarto es Pucón ZR-6, REMOSION EN MASA, `es_inundacion False`. En GeoIDE, P_DO solo aparece en Nueva Imperial; Loncoche (capa 18) y Pucón (capa 0) no lo traen. Y la fecha de Nueva Imperial es del plan nuevo, así que no le pone fecha a nuestro ZR-1.

### F-207 | CONFIRMADO EN PARTE | gravedad 2
Sin documentar: confirmado (`description ''`, alias igual al nombre, `capa29_meta.json`). Que P_DO sea la fecha de publicación ya no es solo SOSPECHA en Angol: la Resolución 40 es del 6/6/2022 y salió en el Diario Oficial el 14/10/2022, que es el P_DO. Para las otras comunas no lo verifiqué. «Varios valores son basura» es falso en la ubicación citada: en la capa 29 los 81 P_DO son `14/10/2022`. La basura está en el campo `DO` de la capa 28 Limite_Urbano: `(' ', 55), ('Municipalidad de Loncoche', 1), ('11-04-1995', 1)`.

### F-208 | CONFIRMADO EN PARTE | gravedad 3
El servicio existe, es anónimo y está en EPSG:32718. Tiene tres capas: profundidad (Bajo < 0,5 m, Medio 0,5-2 m, Alto > 2 m), tiempos de arribo en clases de 5 min y velocidad (de «menor a 1» a «mayor a 10»). Su extensión es solo costera (E 630-666 km). La capa 0 trae **cuatro** comunas, no tres: Carahue, Saavedra, Teodoro Schmidt y Toltén. Es **tsunami**, no inundación fluvial: tiempos de arribo desde un origen, velocidades sobre 10 m/s y una franja solo litoral. Sigue siendo inferencia, porque el servicio no trae descripción (SOSPECHA fuerte). Va como capa C litoral, separada. Las capas 1 y 2 tienen más de 2000 registros (`exceededTransferLimit True`), y de ellas bajé solo la primera página de atributos.

### F-209 | CONFIRMADO EN PARTE | gravedad 3
Angol en el agregado es idéntico a la capa 29: `IoU 1.0000`, 81 features, mismas ZONA. Renaico da 22 = 22, Toltén 21 = 21 y Nueva Imperial 10 = 10. Pero **no coincide con todas**: Collipulli trae 64 contra 68 de la capa 23, Carahue 31 contra 15 de la capa 25, y Temuco 3 contra 24 de la capa 12. El filtro `REG like '%Araucan%'` no pierde nada: los conteos por COM sin filtro dan lo mismo.

### F-210 | CONFIRMADO | gravedad 1
Barrido propio: de 22 carpetas, 13 responden `error 499 Token Required` (`barrido_carpetas_verif.json`). Las que interesan (IPT, Informacion_Regional) son anónimas.

### F-211 | CONFIRMADO EN PARTE | gravedad 1
En `tools/auditoria/fB_inventario_geoide.py:32`, `RE_CAUCE` sí trae «cauce» y «quebrada», pero no «canal», «estero» ni «río». Collipulli ZR-3 se llama «ZR-3 Área en torno a Canales» (capa 23) y por eso queda fuera. «No reconoce cauces» es falso; «no reconoce canales» es cierto.

### F-212 | CONFIRMADO | gravedad 1
Releí `frente-B/salida_angol_geometria.txt`: 32 de nuestros polígonos tocan el OBJECTID 67 (171,42 ha), con mediana de IoU por polígono 0,014 y Hausdorff de 3503 m. Son métricas de fragmento contra entero y no significan nada. No lo volví a correr.

### F-213 | CONFIRMADO EN PARTE | gravedad 1
Las 81 features en 32719 (`capa_29.json`) suman 591,60 ha, y en 32718, 590,64 ha: razón 1,00161 (0,16 % sobre la suma de las 81; el auditor da 0,14 % sobre las hídricas). El IoU 0 del primer cruce es historia del auditor: SIN DATO, aunque es lo esperable al mezclar husos. Además, `capa_29.json` no guarda `outSR` ni `spatialReference`, así que el archivo no dice en qué sistema está.

### F-214 | CONFIRMADO, con otra causa | gravedad 1
`N: 54 polígonos, disuelto 225.22 ha; suma campo hectareas 227.57 ha`. Pero la suma de las áreas de geometría polígono por polígono es 227,56 ha, y el campo difiere de su geometría en 0,0002 ha de media. El campo no está mal: **nuestros AR-2a se solapan entre sí 2,34 ha** (las dos láminas se pisan). Cualquier suma por polígono, por ejemplo en el paquete del practicante, cuenta dos veces esas 2,3 ha.

## 5. Hallazgos propios

- **F-280 | Ar_Araucania cubre también Teodoro Schmidt | gravedad 3 | CONFIRMADO.** El MapServer de tsunami trae Teodoro Schmidt (3 de las 12 features de la capa 0). El frente B la pone entre las comunas sin ningún polígono hídrico en GeoIDE (INFORME.md:47). Es el mismo servicio de F-208, y este hallazgo corrige su lista.
- **F-281 | En GeoIDE el AR-2b de Angol está encima del AR-2a | gravedad 2 | CONFIRMADO.** `GeoIDE AR-2a ∩ AR-2b: 9.26 ha de 15.64 ha`. La lámina rotula AR-2b corredores (canal Pochochingue, Av. Los Confines) que GeoIDE dibuja dentro del AR-2a. Si se importa la oficial, las dos capas no se suman: la suma de las 81 features es 590,64 ha y la unión 567,70 ha.
- **F-282 | El vectorizador no ve el achurado AR-2a sobre zonas oscuras (Z-1, Z-5) | gravedad 4 | CONFIRMADO.** Es la causa principal de F-200 (sección 3): 23,6 ha a más de 10 m de lo nuestro. Incluye el corredor del canal Pochochingue por el centro de Angol (Z-1), donde el visor responde «fuera de área de riesgo» y el plan dice AR-2a. Cambiar `contraste_minimo` para toda la lámina no lo resuelve: con 14 la cobertura baja a 0,689 y salen 122,9 ha falsas.

## 6. VERIFICADO LIMPIO

- Descarga de la capa 29: 81 features = `returnCountOnly` 81, sin `exceededTransferLimit`, nativa en 32718 (`capa29_meta.json`, `capa29_count.json`).
- El AR-2a de GeoIDE no se solapa consigo mismo (`solape interno 0.00 ha`): el 72 % no está inflado por doble conteo.
- Todo G cae dentro de la huella útil de las dos láminas (`G fuera de la huella útil de ambas láminas: 0.00 ha`): no falta ningún pliego.
- El filtro de región del agregado IPT no pierde registros (conteos por COM iguales con y sin filtro).
- Tijeral AR-1 del visor = capa 9 AR-1 (7,84 ha, solape total).
- Las capas 9, 31, 33, 34 y 37 se bajaron completas (count = features, chequeado en el script).
- Las carpetas IPT e Informacion_Regional de GeoIDE responden sin token.

## 7. Pendiente (no me toca decidirlo)

- Reemplazar la capa A derivada de Angol por la oficial de GeoIDE (AR-2a + AR-2b), o corregir el detector. La evidencia apunta a lo primero.
- Corregir la frase de `le_falta` de Angol y sumar Renaico, Nueva Imperial y Toltén desde GeoIDE.
- Saber si las Enmiendas II (2026) del PRC de Angol tocaron las áreas de riesgo: SIN DATO.
