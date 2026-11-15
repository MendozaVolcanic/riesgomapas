# Auditoría del 15-nov-2026: síntesis

Tres frentes disjuntos en paralelo y un verificador con contexto limpio por frente, de
otro modelo que el auditor (A y C los auditó Opus y los verificó Sonnet; B al revés). Cada
verificador escribió sus caminos de ruptura antes de abrir el informe que verificaba.

| Frente | Informe | Verificación | Hallazgos | Refutados |
|---|---|---|---:|---:|
| A, lógica del veredicto | `frente-A/INFORME.md` | `verificacion-A/VERIFICACION.md` | 21 + 2 del verificador | 0 |
| B, GeoIDE del MINVU | `frente-B/INFORME.md` | `verificacion-B/VERIFICACION.md` | 15 + 3 del verificador | 0 |
| C, población expuesta | `frente-C/INFORME.md` | `verificacion-C/VERIFICACION.md` | 14 + 2 del verificador | 0 |

**Los IDs provisionales quedan como finales.** Solo hay un duplicado: F-180 (verificador A)
se funde en F-200 y F-201. La gravedad que manda es la del verificador.

## En una pantalla

1. **La capa derivada de Angol es una copia degradada de un vectorial oficial que existe.**
   GeoIDE publica el AR-2a de la Resolución 40/2022; nuestras láminas cubren el 72 % y no
   traen el AR-2b. La causa es el vectorizador, no la georreferencia ni otra versión del
   plan. Y el visor le dice a la gente que ese vectorial no existe.
2. **La capa A está incompleta o vieja en Nueva Imperial, Renaico y Toltén**, y GeoIDE
   trae lo que falta.
3. **El veredicto tiene cuatro defectos de comunicación serios**: elegir comuna responde
   sobre un punto que nadie eligió, el detalle contradice al titular de borde, el texto que
   se reenvía no dice qué capa decidió, y la banda de borde baja un registro grave.
4. **El censo cuenta dos veces a 17.887 personas** (las aldeas), y la población expuesta
   depende más del criterio de cruce que de la capa.
5. **Nada de esto toca la regla de no fusionar capas**: ningún hallazgo encontró un
   promedio entre capas; F-104 (nivel único) se verificó como decisión de diseño.

## Hallazgos por familia (para planificar arreglos, uno por familia)

Gravedad del verificador. CEP = confirmado en parte.

### Familia 1: Angol, reemplazar la lámina vectorizada por el vectorial oficial

| ID | Gravedad | Veredicto | Qué |
|---|---:|---|---|
| F-200 (+F-180) | 4 | CEP | Faltan 78,4 ha del AR-2a oficial (69,8 en 61 piezas grandes); IoU 0,671, la mejor traslación lo sube a 0,680 |
| F-282 | 4 | nuevo | Causa: el umbral de contraste no ve el achurado sobre fondo oscuro (Z-1, Z-5, canal Pochochingue), 23,6 ha; bajarlo agrega 122,9 ha falsas |
| F-201 | 4 | confirmado | Angol tiene 21 polígonos hídricos oficiales (10 AR-2a, 11 AR-2b); el AR-2b no está en nuestra capa |
| F-103 | 4 | confirmado | Cinco textos del visor, incluida la solicitud por Ley 20.285, afirman que Angol no tiene vectorial |
| F-281 | 2 | nuevo | 9,26 de las 15,64 ha de AR-2b están dibujadas encima del AR-2a: no sumarlas al importar |
| F-111 | 2 | CEP | «Año: 2026» es la ordenanza; la fecha del instrumento es 14-10-2022 (Diario Oficial) |
| F-202 | 1 | confirmado | El IoU de 0,20 abierto desde septiembre era plan contra estudio de 2013, no un defecto |
| F-214 | 1 | otra causa | Las dos láminas se solapan 2,34 ha entre sí |

Decisión que abre: la capa oficial pasa a ser «A normativo» de Angol y la vectorizada
queda como respaldo trazable, o se retira. SIN DATO: si las Enmiendas II de 2026
cambiaron las áreas de riesgo.

### Familia 2: capa A normativa incompleta o desactualizada

| ID | Gravedad | Veredicto | Qué |
|---|---:|---|---|
| F-203 | 4 | CEP | Nueva Imperial: nuestro ZR-1 es versión vieja; GeoIDE trae la Resolución 111/2025 |
| F-204 | 4 | confirmado | Renaico: faltan 19 AR-1 inundables del pueblo (16,0 ha), Resolución 90/2023 |
| F-205 | 3 | confirmado | Toltén: faltan Nueva Toltén y Villa Boldos (21,9 ha), Resolución 38/2026 |
| F-209 | 3 | CEP | `IPT/IPT_AREA_RIESGO/0` es un agregado que sí trae Angol, pero difiere de las capas por comuna en Collipulli, Carahue y Temuco |
| F-206 | 2 | confirmado | Los «cuatro sin año» son tres en lo publicado; GeoIDE da fecha para uno, de otra versión |
| F-207 | 2 | CEP | `P_DO` es la fecha del Diario Oficial en Angol; los valores basura están en `DO` de la capa 28 |
| F-210, F-211, F-212, F-213 | 1 | | Carpetas con token, clasificador de cauces, métricas por polígono, EPSG 32719 vs 32718 |

### Familia 3: lo que el veredicto le dice a la persona

| ID | Gravedad | Veredicto | Qué |
|---|---:|---|---|
| F-101 | 4 | confirmado | Elegir comuna da «Sin registros» en 22 de 30 comunas con registros |
| F-100 | 3 | CEP | La pestaña de detalle dice «no cae dentro» bajo el titular de borde; lo impreso sí trae el resumen |
| F-102 | 3 | confirmado | El texto reenviado no nombra la capa que decidió |
| F-105 | 3 | confirmado | La banda de borde rebaja alto a medio (mismo punto: medio a 0 m, alto a 60 m) |
| F-106 | 3 | confirmado | La precisión del GPS se arrastra a una dirección elegida |
| F-108 | 3 | diseño | Los campamentos no entran al veredicto (Wenehuen, 37 hogares, titular «Sin registros») |
| F-109 | 3 | confirmado | «El satélite sí miró» en terreno que el método excluye (32,3 % de la cobertura) |
| F-110 | 3 | confirmado | El modelo GORE queda callado si hay un registro a 501-1.500 m |
| F-104 | 2 | diseño | Nivel único en un color; sesga a la prudencia |
| F-107 | 2 | diseño | «Medio» de un estudio sin efecto legal sube a alto |
| F-112, F-113, F-114, F-115 | 2 | confirmado | Banda B de 10 m sobre píxel de ~50 m; texto recorta a 3 puntos; dos láminas superpuestas; JRC sin cuencas pequeñas |
| F-116 a F-120, F-181 | 1 | confirmado | Menores |
| F-280 | 3 | nuevo | El servicio de tsunami también cubre Teodoro Schmidt |
| F-208 | 3 | CEP | Hay un servicio de tsunami en GeoIDE para cuatro comunas costeras; fuera del alcance fluvial, decisión |

### Familia 4: el censo

| ID | Gravedad | Veredicto | Qué |
|---|---:|---|---|
| F-300 | 3 | confirmado | 33 aldeas = 505 manzanas «Aldea»: 17.887 personas dos veces; 19 comunas infladas en el visor |
| cruce A/C | 3 | confirmado | `fA_veredicto_censo.py:76` hereda el doble conteo: nivel alto 74.788 baja a 70.843 sin aldeas |
| INE = Esri | 3 | confirmado | Mismo dato en 17 campos (17.074 por MANZENT, 33 por punto); el GPKG del INE conviene como fuente fija |
| F-309 | 2 | confirmado | El script 16 no baja `TIPO_MZ` y su control no puede ver la duplicación |
| F-380 | 2 | nuevo | `unidad_censal = manzana_urbana` incluye 505 manzanas rurales: Curarrehue sale 46 % o 100 % rural según el campo |
| F-308 | 2 | confirmado | `hogares_agua_de_rio` publica viviendas con rótulo de hogares |
| F-311, F-312, F-313, F-381 | 1 | | Totales repetidos en documentos, rótulo de procedencia, 7 geometrías inválidas, cifra del informe |

### Familia 5: población expuesta, el método

| ID | Gravedad | Veredicto | Qué |
|---|---:|---|---|
| F-301 | 3 | CEP | El error de borde mueve el reparto del AR-2a de Angol -16/+17 % (con el error de cada lámina) y el estudio 2013 -40/+43 % |
| F-302 | 3 | confirmado | El A normativo junto mezcla fenómenos: 84 % de su gente es un anegamiento de Temuco |
| F-304 | 3 | CEP | En el radar el reparto es 99 % rural (densidad pareja no sirve); en Curarrehue 46 % |
| F-303, F-305, F-306, F-307 | 2 | confirmado | Hasta 50 veces entre criterios; GORE pone 20 a 40 % de la región; JRC no distingue períodos; traslapes internos |
| F-310 | 2 | CEP | Redondear coordenadas no es inocuo (set_precision mueve 34 m; 208 inválidas nuevas) |

## Lo que no se miró

El visor en navegador después de los hallazgos; la impresión real en papel (F-100 se
verificó leyendo el CSS); las carpetas de GeoIDE con token; qué parte del terreno no apto
de F-109 es mar y cuál ladera; la comparación uno a uno con el practicante (no tenemos sus
polígonos).
