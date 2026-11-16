# Familia 5: población expuesta en el visor

Decisión de Nicolás (15-nov-2026): «Población al visor».

## Qué faltaba

El panel de la comuna decía cuánta gente tiene la comuna (Angol, 52.605), pero no
cuánta vive **dentro** de los mapas. La auditoría (frente C) midió el cruce con
`tools/auditoria/fC_poblacion_expuesta.py` y dejó cinco hallazgos de método:
el criterio de cruce cambia la cifra hasta 50 veces (F-303), el A normativo junto
mezcla fenómenos (F-302), el borde del A derivado mueve el reparto un cuarto o más
(F-301), en sectores rurales la densidad pareja no se sostiene (F-304), y los
traslapes internos cuentan dos veces (F-307).

## Qué se hizo

- `scripts/21_poblacion_expuesta.py` publica `web/data/poblacion-expuesta.json`
  (16,5 kB, va offline). Por cada capa A y comuna: los cuatro criterios (dentro,
  punto, reparto, cualquier), la fracción rural del reparto, cuatro campos de
  vulnerabilidad y, en el A derivado, el reparto con la mancha encogida y
  engordada en su error de borde. El A normativo va por fenómeno; nunca junto.
  Cada capa se disuelve antes de cruzar.
- El panel de la comuna muestra la cifra central redondeada («unas 6.600») y
  siempre el rango, avisa cuando la mayor parte es rural, y explica por qué es un
  rango. El texto que se comparte lleva lo mismo. Las capas no se suman.
- Sólo capa A. Las capas B (radar) y C (modelos) quedan para otra decisión: el
  GORE pone entre 20 y 40 % de la región dentro de su mancha (F-305) y publicarlo
  así pide otro texto.

## Medición

Antes: el visor no publicaba ninguna cifra de gente dentro de un mapa.

Después (`python scripts/21_poblacion_expuesta.py`, censo de 1.003.546 personas sin
aldeas):

| Capa | Comunas | Reparto | Ejemplo |
|---|---:|---:|---|
| A normativo fluvial | 13 | 12.874 | Angol unas 6.600 (926 a 25.098) |
| A normativo anegamiento | 6 | 17.284 | Temuco 16.780 (9.457 a 26.775) |
| A normativo litoral | 1 | 701 | Toltén, 100 % rural |
| A normativo napa freática | 1 | 45 | Toltén |
| A derivado Angol 2013 | 1 | 1.290 | borde ±7,7 m: 775 a 1.851 |
| A derivado Curarrehue 2025 | 2 | 579 | Curarrehue 542, Pucón 37 |

Los dos derivados coinciden con la auditoría del frente C (1.290 y 579). El fluvial
sube de 2.708 a 12.874 porque la capa A ya trae los polígonos de GeoIDE (familias 1
y 2): Angol pasó de 0 a 21 polígonos.

Contra el practicante: para Angol él da 10.387 por reparto, pero su base junta
inundación, anegamiento y remoción en masa. Nuestro fluvial (6.628) más anegamiento
(268), sumados sólo para comparar y sin descontar traslapes, da unas 6.900 sin
remoción. El orden de magnitud cuadra; la comparación fina pide sus
polígonos.

## Guardas, rojas antes

`tests/test_poblacion_expuesta.py`, 7 pruebas, rojas antes de existir el script:
caso sintético con valores exactos (30 %, 70 %, entera, fuera, mancha duplicada);
nada de «todas» en el A normativo; rango ordenado en cada comuna; borde que
envuelve al reparto; el reparto coincide con `vC_reparto_independiente.py`, que
calcula por otro camino; censo sin doble conteo; el visor carga y guarda offline
el archivo.
