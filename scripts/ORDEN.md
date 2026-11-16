# Orden real de ejecución

> ⚠️ **El número del script no es el orden.** Del 01 al 10 coincide; del 11 en
> adelante el número es la fecha en que se escribió, no su lugar en la cadena.
>
> Correr `01…20` en orden numérico **produce un catálogo vacío**: el 09 lee
> salidas del 07 y del 08, y el 07 lee las del 12.

| # | Script | Qué hace | Requiere |
|---|---|---|---|
| 12 | `12_cosechar_municipios.py` | los sitios municipales → data/raw/documentos/ | — |
| 03 | `03_descargar_documentos.py` | documentos del registro EAE → data/raw/ | — |
| 05 | `05_eae_documentos.py` | índice nacional EAE → processed/eae/araucania.json | 03 |
| 07 | `07_buscar_laminas_riesgo.py` | abre los PDF y localiza las láminas | 05 + los PDF de 03; 12 opcional |
| 08 | `08_georreferenciar_grilla.py` | planos con retícula vectorial → GeoTIFF | 07 |
| 10 | `10_exportar_superposiciones.py` | publica los planos al visor | 08 |
| 01 | `01_senapred_puntos_criticos.py` | capa D + índice de comunas | — |
| 06 | `06_areas_riesgo_prc.py` | capa A: áreas de riesgo del MINVU (hídricas desde GeoIDE) | — (05 opcional: fecha EAE) |
| 13 | `13_campamentos_riesgo.py` | campamentos dentro de área de riesgo | — (MINVU entrega el cruce hecho) |
| 02 | `02_jrc_amenaza_modelada.py` | capa C global | — |
| 15 | `15_gore_amenaza.py` | capa C regional a 35 m | — |
| 14 | `14_sar_huella_observada.py` | capa B: huella por Sentinel-1 | 01 (para verificar) |
| 16 | `16_censo_2024.py` | población por manzana y entidad | — |
| 17 | `17_arclim_desbordes.py` | sitios de desborde de ARClim | — |
| 18 | `18_vectorizar_laminas.py` | láminas impresas → polígonos | 07 |
| 09 | `09_exportar_catalogo.py` | catálogo público de documentos | 05, 07, 08 |
| 11 | `11_verificar_superposicion.py` | control visual de los planos | 10 |
| 19 | `19_estado_comunas.py` | inventario del vacío + publica los derivados | 01,06,09,10,16,18 |
| 20 | `20_paquete_practicante.py` | paquete por provincia para QGIS | 19; opcionales 01,02,06,13,14,15,17,18 |
| 21 | `21_poblacion_expuesta.py` | gente dentro de cada capa A, por comuna, con su rango | 06,16,18,19 |
| 22 | `22_inventario_visor.py` | qué tiene el visor: capas, comunas y peso legal | 19 |
| 04 | `04_georreferenciar.py` | planos a mano, con .points de QGIS | cuando 08 rechaza uno |

> La columna «Requiere» se verificó contra el código el 7-sep-2026 y cinco filas
> estaban mal: 13 no lee la salida de 06, 09 se cae sin 05, 07 también necesita
> los PDF de 03, y 20 usa más capas de las que decía. Cada script declara ahora
> lo mismo en su propio docstring (`Requiere:`), y una prueba lo exige — así esta
> tabla deja de ser la única fuente y se puede contrastar.

## Camino corto

Para regenerar sólo lo que el visor consume, sin volver a descargar los 2,8 GB
de documentos:

```bash
python scripts/01_senapred_puntos_criticos.py
python scripts/06_areas_riesgo_prc.py
python scripts/13_campamentos_riesgo.py
python scripts/19_estado_comunas.py
python scripts/21_poblacion_expuesta.py
python scripts/22_inventario_visor.py
```

## Lo que se rompe al clonar limpio

`data/raw/` no está versionado, así que los scripts que lo leen no encuentran
nada. En particular **10_exportar_superposiciones.py corre sin error y deja el
índice de planos vacío**, borrando los 17 MB publicados: falla muda, la peor
clase. Antes de correrlo en un clon nuevo hay que correr 03, 12, 07 y 08.

El visor **sí funciona** en un clon limpio (`python -m http.server 8788
--directory web`): todo lo que consume está versionado.
