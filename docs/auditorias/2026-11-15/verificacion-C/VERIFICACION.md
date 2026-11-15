# Verificación frente C (censo y población expuesta)

Registro previo a abrir el informe del auditor (2026-11-15 09:32 hora local, `date` de esta sesión):
- sha256 frente-C/INFORME.md   = 27b0c98c922e0c9f30033a45b3117f374e8c46df6af93ae10b8061b3669cdc28
- sha256 frente-C/hallazgos.csv = 6dbc4342167c0b6d5e0adb9ee8e2f10fe1b428f9278ff644118bba94e4385b57
(salida cruda de `sha256sum` corrida antes de leer ambos archivos)

## Caminos de ruptura, escritos antes de abrir el informe

F-300 (aldeas duplicadas): (a) las aldeas no se solapan con entidades rurales sino que son rurales distintas; (b) el solape se mide por centroide/IDs y no por geometría; (c) las 17.887 personas están dentro de las manzanas-entidades solo en parte; (d) el visor no suma capas, usa otro campo; (e) "19 comunas" cuenta comunas con aldea, no comunas donde el visor realmente infla; (f) app.js:618/701 no usa n_per de aldeas; (g) la copia local de data está atrasada.
F-301 (borde): el delta se calcula con buffer del error en un CRS en grados; el campo incertidumbre_borde_m no es el RMSE de borde sino otra cosa; el buffer se aplica también hacia adentro; el disuelto cambia el resultado.
F-302 (84 % anegamiento Temuco): ¿el tipo es campo real o inferido?; la ha es de un solo polígono mal etiquetado; REGLAS.md no obliga a separar tipos.
F-303/304: el 0 a 24.315 depende de criterio (centroide vs intersecta vs reparto); la proporción rural se calcula con TIPO inferido por capa; la base de reparto usa área en grados.
F-305: porcentaje de región se calcula sobre bbox o sobre área sin la mar; mancha publicada puede incluir lagos.
F-306: JRC rp10 vs rp500 usa los mismos archivos copiados, o las manzanas son grandes.
F-307: se suman dos veces entre archivos, no dentro de uno; disuelto 5.094 con distinto CRS.
F-308: el campo agua de río cuenta viviendas y el rótulo dice hogares; ¿el INE lo define como hogares?
F-309: TIPO_MZ puede existir ya en CAMPOS u otro; ESPERADO sí puede ver la duplicación.
F-310: set_precision con grid en grados vs metros; "34 m" confunde unidades; 209 inválidas pueden ser preexistentes.
F-311: el total 1.021.433 puede estar etiquetado como suma de tres capas (correcto como suma bruta); 12.381/4.726 pueden salir de otro corte.
F-312: procedencia puede ser INE por cadena (el original es Esri/INE republicado); D_operacional puede ser decisión justificada.
F-313: invalidez medida con shapely vs. otro validador.
Cruce fA_veredicto_censo.py:76: la línea quizá no pondera por n_per; quizá ya excluye aldeas.
INE = Esri: emparejar por MANZENT puede ocultar duplicados de clave; "cero diferencias" puede ser de campos que se copian; la geometría puede diferir por simplificación solo en parte.

## Resultado (comparado con el informe del auditor solo despues de escribir lo anterior)

El sha256 de INFORME.md y hallazgos.csv, recalculado a las 09:53 antes de abrirlos, es el mismo de arriba.

| id | veredicto | gravedad verificador |
|---|---|---|
| F-300 | CONFIRMADO | 3 |
| F-301 | CONFIRMADO EN PARTE | 3 |
| F-302 | CONFIRMADO | 3 |
| F-303 | CONFIRMADO | 2 |
| F-304 | CONFIRMADO EN PARTE | 3 |
| F-305 | CONFIRMADO | 2 |
| F-306 | CONFIRMADO | 2 |
| F-307 | CONFIRMADO | 2 |
| F-308 | CONFIRMADO | 2 |
| F-309 | CONFIRMADO | 2 |
| F-310 | CONFIRMADO EN PARTE | 2 |
| F-311 | CONFIRMADO | 1 |
| F-312 | CONFIRMADO EN PARTE | 1 |
| F-313 | CONFIRMADO | 1 |
| fA_veredicto_censo.py:76 | CONFIRMADO | 3 |
| INE = Esri | CONFIRMADO | 3 |

Detalle y comando de cada uno en `veredictos.csv`. Salidas crudas en `salidas/`. Instrumentos propios
(todos con `--control` salvo el que corre el .js): `tools/auditoria/vC_aldeas_doble_conteo.py`,
`vC_reparto_independiente.py`, `vC_ine_vs_esri.py`, `vC_veredicto_sin_aldeas.py`.

### Lo que cambia respecto al auditor
- **F-300** se sostiene al 100 %: 33 de 33 aldeas son la suma exacta de 505 manzanas TIPO_MZ Aldea (17.887). Bajo la gravedad de 4 a 3: infla un conteo de inventario ("habitantes"), no cambia un veredicto de inundacion.
- **F-301**: el -25/+27 % de AR-2a usa el error maximo (8,3 m) para todos los poligonos. Con el error de cada lamina (4,6 y 8,3 m) sale -16/+17 %. El del estudio 2013 (-40/+43 %) se reproduce exacto.
- **F-304**: cierto para el radar (99 % rural). Falso para Curarrehue como "entidades rurales": 265 de 579 (46 %) vienen de entidades, el resto de manzanas de aldea que el auditor cuenta como rurales por AREA_C.
- **F-310**: 215 invalidas tras el redondeo (208 nuevas), no 209.
- **F-312**: la procedencia publicada ya dice "INE, servicio de Esri Chile" y "espejo de Esri Chile"; solo la linea 27 del docstring contradice la 26.
- **F-311**: 12.381 y 4.726 si salen del archivo por `AREA_C`; lo erroneo es el rotulo ("entidades rurales" incluye 505 manzanas y 33 aldeas).

### Afirmacion cruzada con el frente A (fA_veredicto_censo.py:76)
Confirmada y medida con el mismo .js, con y sin aldeas (`salidas/con_aldeas.txt`, `salidas/sin_aldeas.txt`):
personas evaluadas 1.021.433 vs 1.003.546; nivel alto 74.788 vs 70.843 (-5,3 %); A normativo 20.494 vs 18.955 (-7,5 %);
D puntos alto 47.767 vs 45.361; D4 (GORE maxima callada) 71.877 vs 70.237. D1, D2, D3, A derivado y B observado no cambian. No se midieron D6 y D7 (no hay GeoIDE como GeoJSON local).

### INE = Esri
Se sostiene, con una precision: 17.074 unidades empareja por MANZENT (las 33 aldeas no traen MANZENT y se emparejan por punto y n_per, 33 de 33). 0 diferencias en 17 campos, hausdorff max 0,729 m. La recomendacion de cambiar de fuente no cambia ningun numero; la ventaja real es que el INE publica TIPO_MZ y el archivo fijo. La capa Aldeas del INE tambien duplica: hay que excluirla igual.

### Hallazgos nuevos
- **F-380 (2)**: `unidad_censal = manzana_urbana` contiene 505 manzanas rurales de aldea (AREA_C Rural), asi que filtrar por `unidad_censal` (lo que aconseja la procedencia) y por `AREA_C` clasifican distinto urbano y rural (Curarrehue 46 % vs 100 % rural).
- **F-381 (1)**: el resumen del informe dice "17.107 por MANZENT, ocho campos"; son 17.074 por MANZENT y 17 campos comparados por mi.

### VERIFICADO LIMPIO
- `fC_poblacion_expuesta.py --control` pasa y la corrida completa reproduce byte a byte `resumen_por_capa.csv` y `expuesta_A_derivado_angol_prc_ar2a.csv` (`cmp`).
- `fC_tamano_publicable.py --control` pasa.
- Mi reparto independiente (sin importar fC_) da AR-2a 4.943, estudio 2013 726 y 1.290, Curarrehue 579, anegamiento 16.889: identicos al auditor.
- Totales comunales: estado-comunas.json suma 1.021.433 y coincide comuna por comuna con el censo con aldeas.
- Sin dato: no se verifico si alguna suma agregada "A normativo junto" se publica (F-302); no se midio D6/D7; no se abrio el visor en navegador.
- Nota: las corridas de los instrumentos fC_ reescribieron `frente-C/resumen_por_capa.csv`, los `expuesta_*.csv` y `tamano_publicable.csv`; de los `expuesta_*.csv` solo se comparo con `cmp` el de AR-2a (identico), junto con resumen_por_capa.csv; tamano_publicable.csv no se comparo.
