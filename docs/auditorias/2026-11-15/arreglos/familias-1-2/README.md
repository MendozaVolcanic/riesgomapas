# Familias 1 y 2: capa A hídrica desde GeoIDE, toda La Araucanía

Decisión de Nicolás (15-nov-2026): «GeoIDE reemplaza, lámina de respaldo», y luego
«Sí, toda la región». Las dos familias quedaron en un solo importador regional,
porque son el mismo servicio.

## Instrumento

`tools/auditoria/fB_cruce_proyecto_vs_geoide.py`, el mismo de la auditoría (tiene
`--control`). Compara por comuna la capa A publicada (`web/data/areas-riesgo-inundacion.geojson`)
contra el agregado `IPT_AREA_RIESGO` de GeoIDE, en EPSG:32718. Salidas:
`antes_cruce.txt` y `despues_cruce.txt`. El instrumento reescribe
`frente-B/inventario_comuna.csv`; se restauró con `git restore` para no tocar la
evidencia de la auditoría.

## Antes y después (G = GeoIDE hídrico, A = capa publicada)

| Comuna | Antes A | Antes IoU | Después A | Después IoU | Lectura |
|---|---:|---:|---:|---:|---|
| Angol | 0 | (sin capa) | 21 | 1,0 | F-200, F-201 cerrados |
| Nueva Imperial | 1 | 0,101 | 9 | 1,0 | F-203: Res. 111/2025 |
| Renaico | 1 | 0,329 | 20 | 1,0 | F-204: Res. 90/2023 |
| Toltén | 4 | 0,779 | 21 | 1,0 | F-205: Res. 38/2026 |
| Gorbea, Pitrufquén, Saavedra, Traiguén, Villarrica | | 1,0 | | 1,0 | sin cambio |
| Temuco | 1 | 0,999 | 1 | 0,999 | el 0,1 % es ARC «restricción canal», excluida a propósito |
| Carahue | 9 | 0,971 | 9 | 0,971 | ZR-1b (3,1 ha): el clasificador de la auditoría no la cuenta; la capa nacional del MINVU sí (INUNDACION) |
| Collipulli | 38 | 0,771 | 44 | 0,777 | ZR-3 «en torno a canales» (32 ha), incluida como hasta ahora; +6 ZR-5 y ZR-2 que GeoIDE trae y el agregado no |
| Loncoche | 2 | (G sin texto) | 2 | (G sin texto) | ZR-2A y ZR-2B: GeoIDE no dice qué son; la capa nacional dice INUNDACION y así se clasifican |

Lo que sigue difiriendo son **decisiones de clasificación visibles en
`ZONAS_GEOIDE` y `EXCLUIDAS_GEOIDE`** (script 06), no geometría. El huso quedó bien:
IoU 1,0 en las comunas que cambiaron, sin pasar por la trampa de EPSG:32719 (F-213).

Publicado: 65 polígonos hídricos antes, 136 después (fluvial 108, anegamiento 19,
napa freática 7, litoral 2). Los 65 del agregado quedan de respaldo en
`data/processed/areas_riesgo_prc_reemplazadas_por_geoide.geojson`.

## Guardas, rojas antes

`tests/test_capa_a_geoide.py`: 11 pruebas, las 10 primeras rojas antes de tocar el
código y la del año (Saavedra) roja después de la primera corrida, que la había
perdido. La tabla de zonas bota el script si aparece una zona con texto hídrico que no
conoce, si una zona de la tabla desaparece, o si el reemplazo pierde una zona que el
agregado tenía.

## Lámina de Angol

`angol-prc-ar2a-lamina1` y `-lamina2` (54 polígonos) quedan en `data/processed/laminas/`
y salen del visor (`laminas_de_respaldo` en `config/araucania.yaml`). El estudio de
2013 de Angol es otro documento y sigue publicado.

`angol_en_el_visor.png`: un punto dentro del AR-2a oficial, titular normativo y
«Instrumento: Resolución 40 del 14/10/2022» en el detalle.
