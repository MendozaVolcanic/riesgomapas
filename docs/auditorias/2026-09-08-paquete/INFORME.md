# Auditoría del paquete Malleco para el practicante

**Fecha:** 2026-09-08
**Objeto auditado:** `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\data\processed\paquete_malleco\`
y su comprimido `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\data\processed\paquete_malleco.zip`
**Alcance:** entregable, no código. No se modificó ningún archivo del paquete ni del repositorio.

---

## Aviso previo: el paquete cambió a mitad de la auditoría

Al abrir la sesión, `LEEME.md` medía 12.125 bytes y existían `ESTADO_DE_LOS_POLIGONOS.md`
y `ESTADO_DE_LOS_POLIGONOS.docx` (salida de `find -printf "%10s %p"` del inicio de sesión).
A las **09:56:45** los archivos de texto fueron reescritos: `LEEME.md` quedó en 6.326 bytes
y los dos `ESTADO_DE_LOS_POLIGONOS.*` desaparecieron. El zip se regeneró a las 09:56:55.

```
zip mtime 2026-09-08 09:56:55 181774040
    14585 09:56:46  LEEME.docx
     6326 09:56:45  LEEME.md
ESTADO* en disco: []
ESTADO* en zip: []
entradas zip: 129
```

**Todo lo que sigue está medido contra el estado de las 09:56.** Verifiqué además que el zip
y la carpeta son byte a byte idénticos, salvo que el zip no lleva los `.md`:

```
ARCHIVOS QUE DIFIEREN entre zip y carpeta: 0
EN DISCO NO EN ZIP:  (los 13 .md)
EN ZIP NO EN DISCO:  (ninguno)
```

Dos defectos que estaban en la versión anterior **ya no existen** y no los reporto:
la referencia a `scripts/ORDEN.md` y la exigencia de devolver un `config/laminas.yaml`
(grep sobre los `.md` actuales: cero coincidencias de `ORDEN.md`, `yaml`, `scripts/`, `config/`).

---

# HALLAZGOS, ordenados por gravedad

## GRAVEDAD 5

### 1. TAREAS manda georreferenciar una lámina que el propio paquete ya vectorizó

**DÓNDE** — `TAREAS.md` línea 60 (y `TAREAS.docx`, mismo texto) contra
`2_laminas_por_georreferenciar/LEEME.md` líneas 35 y 61.

**QUÉ PASA** — La primera tarea del paquete («Georreferenciar y digitalizar las láminas que ya
tienen retícula») encabeza su lista con `documentos/angol/Estudio_Riesgo.pdf` página 30. Esa
página es exactamente la que produjo `1_cartografia_ya_vectorizada/angol-peligro-inundacion-2013/`
(96 polígonos). El LEEME de esa subcarpeta la marca `✅ ya vectorizado`, y en la misma página
la segunda tabla del mismo LEEME la vuelve a listar como pendiente.

**CÓMO LO SUFRE EL PRACTICANTE** — Es el primer ítem de la primera tarea. Empieza por ahí,
georreferencia y digitaliza un día entero, y produce una capa que ya existe y que además está
mejor hecha (7,74 m/px derivados de la retícula impresa). Nadie lo detecta hasta la entrega.

**CÓMO LO VERIFICASTE** —
```
TAREAS.md:60 - `documentos/angol/Estudio_Riesgo.pdf` página 30, imagen 0 — 1266x1021 px...
2_laminas_por_georreferenciar/LEEME.md:35 | Angol | Estudio_Riesgo.pdf | **30, 32, 34, 55, 56** | — | ✅ ya vectorizado → `1_cartografia_ya_vectorizada/angol-peligro-inundacion-2013/`
2_laminas_por_georreferenciar/LEEME.md:61 | Angol | Estudio_Riesgo.pdf | 30 | `angol/Estudio_Riesgo.pdf` |
```
y la capa `00_procedencia_de_cada_capa` del GeoPackage: *«Vectorización de la figura “Modelo
raster de peligro de inundación” (página 30 del PDF de origen)»*.

**GRAVEDAD 5**

---

### 2. El «✅ ya vectorizado» tapa cuatro láminas pendientes

**DÓNDE** — `2_laminas_por_georreferenciar/LEEME.md` línea 35.

**QUÉ PASA** — La fila declara láminas en las páginas **30, 32, 34, 55 y 56** y marca la fila
entera como `✅ ya vectorizado`. Sólo se vectorizó la página 30: la carpeta contiene un único
`lamina_pagina-30.jpg` y una sola capa de 96 polígonos, cuyo método declara «página 30».

**CÓMO LO SUFRE EL PRACTICANTE** — Salta la fila entera. Cuatro láminas con retícula detectada
—las más baratas de todo el paquete, según la propia TAREAS— quedan sin hacer y nadie las
reclama, porque el documento dice que están listas.

**CÓMO LO VERIFICASTE** — Contenido de la carpeta:
```
1_cartografia_ya_vectorizada\angol-peligro-inundacion-2013\lamina_pagina-30.jpg  (única .jpg)
DERIVADO_angol_peligro_inundacion_2013  n=96
```
y `TAREAS.md:61,63,64,65` listan las páginas 32, 34, 55 y 56 como retículas pendientes.

**GRAVEDAD 5**

---

### 3. El CSV de procedencia da hectáreas 13,5 % mayores que el GeoPackage

**DÓNDE** — `FUENTE_DE_CADA_POLIGONO.csv`, columna `hectareas`, las 2.285 filas.

**QUÉ PASA** — La superficie de cada polígono en el CSV está inflada por un factor constante
≈1,135 respecto de la geometría real y respecto del campo `hectareas` que trae el propio
GeoPackage. No es un redondeo: es sistemático y afecta a todas las capas.

**CÓMO LO SUFRE EL PRACTICANTE** — El CSV es lo único que abre en Excel para ordenar y filtrar,
y el LEEME lo presenta como «el detalle polígono por polígono». Cualquier superficie que cite
desde ahí —en un informe, en un correo, en una minuta— será un 13,5 % mayor que la que QGIS le
muestra en pantalla con el mismo polígono seleccionado. Y si lo nota, no tiene forma de saber
cuál de los dos números es el bueno.

**CÓMO LO VERIFICASTE** —
```
DERIVADO_angol_peligro_inundacion_2013: CSV_ha=241.96  gpkg_ha=213.13  real_UTM18S=213.11
DERIVADO_angol_prc_ar2a_lamina1:        CSV_ha=125.47  gpkg_ha=110.51  real_UTM18S=110.52
DERIVADO_angol_prc_ar2a_lamina2:        CSV_ha=132.88  gpkg_ha=117.06  real_UTM18S=117.04
amenaza_modelada_JRC_100a:              CSV_ha=30756.23  real_UTM18S=27171.80
areas_riesgo_PRC_MINVU:                 CSV_ha=239.20    real_UTM18S=210.18
```
Fila a fila en `DERIVADO_angol_prc_ar2a_lamina1` (csv / gpkg / real, en ha):
`0.78 0.69 0.687 · 3.41 3.00 3.000 · 0.59 0.52 0.521 · 1.66 1.46 1.461`.
El área real se midió reproyectando a EPSG:32718 con geopandas.

**GRAVEDAD 5**

---

## GRAVEDAD 4

### 4. Las 16 rutas de la tarea principal apuntan a una carpeta que no existe

**DÓNDE** — `TAREAS.md` líneas 60-79 (sección «1. Georreferenciar y digitalizar las láminas que
ya tienen retícula»). Idéntico en `TAREAS.docx`.

**QUÉ PASA** — Las 16 láminas con retícula se citan como `documentos/angol/…`,
`documentos/puren/…`, `documentos/renaico/…`. En el paquete no existe ninguna carpeta
`documentos/`: los PDF están en `2_laminas_por_georreferenciar/angol/`, `…/puren/`, `…/renaico/`.

**CÓMO LO SUFRE EL PRACTICANTE** — Abre el zip, busca `documentos\`, no está. Tiene que deducir
la equivalencia; hasta que la deduce, el documento más importante del paquete parece describir
otro paquete. Es recuperable, pero es 16 de 16 rutas y es lo primero que se abre.

**CÓMO LO VERIFICASTE** — Listado completo del paquete: las carpetas de primer nivel son
`1_cartografia_ya_vectorizada`, `2_laminas_por_georreferenciar`, `3_capas_en_shapefile`.
Y las 16 líneas de TAREAS con prefijo `documentos/` están pegadas en el hallazgo (grep sobre
`TAREAS.md` y sobre el texto extraído de `TAREAS.docx`, mismo resultado).

**GRAVEDAD 4**

---

### 5. Las imágenes de las láminas no traen georreferencia, y el LEEME manda superponerlas en QGIS

**DÓNDE** — `1_cartografia_ya_vectorizada/*/LEEME.md`, sección «Si encuentras un error»
(líneas 55 / 56 / 56).

**QUÉ PASA** — El texto dice: *«Abre `lamina_pagina-30.jpg` al lado de los polígonos en QGIS y
compáralos»*. Los `.jpg` viajan pelados: no hay `.jgw`, ni `.wld`, ni `.aux.xml`, ni un `.tif`
georreferenciado, ni el `.points` del ajuste.

**CÓMO LO SUFRE EL PRACTICANTE** — Carga el JPG en QGIS y aparece en coordenadas de píxel
(0,0)–(1741,−4000), a miles de kilómetros de los polígonos. Como el paquete le vende esa
comparación como el mecanismo para detectar errores de trazado —que es el control de calidad
de las tres capas que ya existen—, la única verificación que se le ofrece no se puede ejecutar,
y tendría que rehacer él mismo la georreferenciación para poder mirar.

**CÓMO LO VERIFICASTE** —
```
extensiones en el paquete: {'.gpkg':4, '.docx':12, '.md':12, '.csv':1, '.pdf':36,
                            '.jpg':3, '.geojson':3, '.cpg':14, '.dbf':14, '.prj':14,
                            '.shp':14, '.shx':14}
world files (.jgw/.wld/.aux.xml/.tif/.points): []
lamina_pagina-30.jpg (1225, 1585) RGB
lamina_pagina-1.jpg  (1741, 4000) RGB
lamina_pagina-1.jpg  (1737, 4000) RGB
```

**GRAVEDAD 4**

---

### 6. El LEEME promete `ESTADO_DE_LOS_POLIGONOS` y ese archivo ya no está en el paquete

**DÓNDE** — `LEEME.md` línea 29; también en `LEEME.docx` (que es lo que recibe el practicante).

**QUÉ PASA** — *«**`ESTADO_DE_LOS_POLIGONOS`** — la revisión que le hicimos a todo esto antes de
entregártelo. Te dice qué mirar con desconfianza.»* El archivo fue eliminado en la regeneración
de las 09:56 y no está ni en la carpeta ni en el zip.

**CÓMO LO SUFRE EL PRACTICANTE** — Lo busca porque el índice se lo ofrece como la lista de qué
desconfiar, y no lo encuentra. Con él se perdió, además, lo único que documentaba las geometrías
duplicadas y los polígonos partidos por el recorte (ver hallazgo 15). Sospecha, con razón, que el
zip le llegó incompleto.

**CÓMO LO VERIFICASTE** —
```
ESTADO* en disco: []
ESTADO* en zip: []
referencias a ESTADO_DE_LOS_POLIGONOS en los textos:
  LEEME.md:29  - **`ESTADO_DE_LOS_POLIGONOS`** — la revisión que le hicimos a todo esto antes
```
y en el texto extraído de `LEEME.docx`: *«ESTADO_DE_LOS_POLIGONOS — la revisión que le hicimos a
todo esto antes de entregártelo.»*

**GRAVEDAD 4**

---

### 7. No hay a quién preguntar, ni plazo, ni dónde dejar la entrega

**DÓNDE** — Todo el paquete.

**QUÉ PASA** — Tres documentos dicen «avísanos» y uno dice «pídenos una copia nueva», pero no hay
un nombre, un correo, un teléfono ni un canal en ninguna parte. Tampoco hay fecha de entrega ni
instrucción de dónde dejar el resultado (`COMO_TRABAJAR_EN_QGIS` dice **qué** entregar; nunca **a
quién** ni **dónde**).

**CÓMO LO SUFRE EL PRACTICANTE** — El paquete está diseñado explícitamente para alguien que
trabaja solo. Cuando algo se rompe —y con los hallazgos 1 a 6 se va a romper—, la instrucción del
propio paquete es «anótalo y sigue». Termina el trabajo con una lista de dudas y sin destinatario.

**CÓMO LO VERIFICASTE** — Búsqueda de `@|correo|mail|teléfono|contacto|pregunt|avísanos|escríbenos|
whatsapp|responsable del paquete` sobre los 12 `.md`. Únicas coincidencias:
```
1_cartografia_ya_vectorizada\angol-peligro-inundacion-2013\LEEME.md:55  ...avísanos con la coordenada
1_cartografia_ya_vectorizada\angol-prc-ar2a-lamina1\LEEME.md:56         ...avísanos con la coordenada
1_cartografia_ya_vectorizada\angol-prc-ar2a-lamina2\LEEME.md:56         ...avísanos con la coordenada
```
Ninguna aporta un destinatario.

**GRAVEDAD 4**

---

### 8. La tabla de campos que debe crear omite `url`, que es donde vive la procedencia

**DÓNDE** — `COMO_TRABAJAR_EN_QGIS.md` líneas 125-134, paso 7.2.

**QUÉ PASA** — La tabla dice: *«Crea estos campos, con estos nombres, para que calce con lo que ya
existe»*, y lista ocho: `clase, comuna, amenaza, fuente, anio, escala_original, estado_tramite,
incertidumbre_borde_m`. Las capas que ya existen tienen once o doce, e incluyen `url`, que es
justamente el campo que `FUENTE_DE_CADA_POLIGONO.md` señala como el que lleva el enlace del
documento («Ahí están las columnas `fuente`, `url`, `anio`…»), y `metodo_original` / `descripcion`
/ `efecto_legal` / `hectareas`.

**CÓMO LO SUFRE EL PRACTICANTE** — Sigue la instrucción al pie de la letra y entrega capas sin
`url`. No «calzan con lo que ya existe» y hay que reprocesarlas. El paquete además le exige
(«Reglas», «Lo que nunca hay que hacer») que todo lo que produzca lleve su procedencia, y le
quita el campo donde ponerla.

**CÓMO LO VERIFICASTE** — Columnas reales de las capas del paquete:
```
angol-peligro-inundacion-2013: ['clase','comuna','amenaza','fuente','url','anio',
  'metodo_original','escala_original','hectareas','estado_tramite','incertidumbre_borde_m','geometry']
angol-prc-ar2a-lamina1/2:      ['clase','descripcion','comuna','amenaza','fuente','url','anio',
  'efecto_legal','escala_original','hectareas','estado_tramite','incertidumbre_borde_m','geometry']
```
contra las 8 filas de la tabla de `COMO_TRABAJAR_EN_QGIS.md:127-134`.

**GRAVEDAD 4**

---

## GRAVEDAD 3

### 9. Renaico no aparece en la tabla principal de láminas, pese a que su PDF viaja

**DÓNDE** — `2_laminas_por_georreferenciar/LEEME.md`, tabla de las líneas 14-50, contra la línea 76
y contra `TAREAS.md:23,79`.

**QUÉ PASA** — La tabla que el propio LEEME presenta como «la que importa» tiene filas de Purén,
Traiguén, Angol, Lonquimay, Collipulli y Lumaco. Renaico no está. Pero `renaico/PLADECO-Renaico.pdf`
sí viaja (123 páginas), sí tiene retícula detectada en la página 8, y TAREAS le asigna
`Retículas 1`. En TAREAS, Renaico figura con `Láminas 0` y `Retículas 1`: una retícula sin lámina.

**CÓMO LO SUFRE EL PRACTICANTE** — Trabaja con la tabla principal y no ve Renaico. Si la cruza con
TAREAS, encuentra una comuna con 19 puntos críticos —el máximo de la provincia— cuya única lámina
sólo aparece en una tabla secundaria, sin indicar de qué es ni si sirve.

**CÓMO LO VERIFICASTE** —
```
comunas con carpeta en 2_laminas: ['angol','collipulli','lonquimay','lumaco','puren','renaico','traiguen']
  123  e007383c41  2_laminas_por_georreferenciar\renaico\PLADECO-Renaico.pdf
2_laminas.../LEEME.md:76 | Renaico | PLADECO-Renaico.pdf | 8 | `renaico/PLADECO-Renaico.pdf` |
TAREAS.md:23 | **Renaico** | 10,665 | 19 | 0 | 1 | 10 | 0 | 1 | 0 |
```
Ninguna fila con «Renaico» entre las líneas 14 y 50 del mismo archivo.

**GRAVEDAD 3**

---

### 10. `COMO_TRABAJAR_EN_QGIS` se contradice consigo mismo sobre los campos vacíos

**DÓNDE** — `COMO_TRABAJAR_EN_QGIS.md` línea 150 contra líneas 176-177.

**QUÉ PASA** —
- Línea 150: *«Abre la tabla de atributos y confirma que **ningún campo quedó vacío**.»*
- Línea 176: *«**No rellenar un campo que no sabes.** Va vacío o “no declarado”, nunca un valor
  plausible.»*

**CÓMO LO SUFRE EL PRACTICANTE** — En la lista de chequeo previa a la entrega se encuentra con que
tiene campos vacíos porque la lámina no declara la escala. Una regla le dice que eso está mal; la
otra, que está bien. La salida fácil —y la que el paquete entero existe para evitar— es rellenar
con algo plausible.

**CÓMO LO VERIFICASTE** — Ambas líneas leídas en el archivo actual (9.107 bytes, mtime 09:56:45),
citadas textualmente arriba.

**GRAVEDAD 3**

---

### 11. El mínimo de puntos de control cambia según el documento, y el propio paquete usó menos

**DÓNDE** — `COMO_TRABAJAR_EN_QGIS.md` líneas 67-70 · `LEEME.md` línea 98 ·
`1_cartografia_ya_vectorizada/angol-prc-ar2a-lamina1/LEEME.md` línea 36.

**QUÉ PASA** — La guía exige *«Cuatro o más»*. El glosario del LEEME dice que el RMSE *«con menos
de tres puntos de control no significa nada»*, es decir, fija el mínimo en tres. Y la lámina 1 del
PRC de Angol, que es el ejemplo modelo del paquete, se georreferenció con **3 vértices**.

**CÓMO LO SUFRE EL PRACTICANTE** — Con una lámina que sólo ofrece tres cruces legibles no sabe si
descartarla, entregarla marcada, o hacer lo mismo que hizo el paquete. Pierde tiempo decidiendo
una regla que el documento debería haber decidido por él.

**CÓMO LO VERIFICASTE** —
```
COMO_TRABAJAR_EN_QGIS.md:67  **Cuántos puntos.** Cuatro o más, **repartidos por toda la hoja**...
LEEME.md:98  | **RMSE** | ... Con menos de tres puntos de control no significa nada. |
lamina1/LEEME.md:36  ...ajuste de semejanza sobre 3 vértices del límite urbano ... RMSE 4.94 m
```

**GRAVEDAD 3**

---

### 12. Se le pide devolver `.tif` y `.points`, y el paquete no entrega ninguno de los suyos

**DÓNDE** — `COMO_TRABAJAR_EN_QGIS.md` líneas 158-168 («Qué entregar de vuelta»).

**QUÉ PASA** — La entrega exigida es «una carpeta por lámina, igual que las de
`1_cartografia_ya_vectorizada`» e incluye el `.tif` georreferenciado y el `.points`. Las carpetas
de `1_cartografia_ya_vectorizada` no contienen ni `.tif` ni `.points`: sólo PDF, JPG, GeoJSON,
GPKG y shapefile.

**CÓMO LO SUFRE EL PRACTICANTE** — El modelo que le mandan copiar no contiene dos de los cuatro
elementos que le piden. No tiene un ejemplo de cómo debe verse un `.points` bien hecho, y tampoco
puede auditar la georreferenciación de lo que ya existe (que es lo que TAREAS le pide: «No los
rehagas; revísalos»).

**CÓMO LO VERIFICASTE** — Mismo listado de extensiones del hallazgo 5: `.tif` y `.points` = 0
archivos en todo el paquete.

**GRAVEDAD 3**

---

### 13. Comunas con documentos declarados en TAREAS que no viajan en el paquete

**DÓNDE** — `TAREAS.md` líneas 15 y 16 (Curacautín `Docs 3`, Victoria `Docs 4`), y la columna
`Docs` completa.

**QUÉ PASA** — TAREAS declara 166 documentos sumando la columna; el paquete lleva 33 PDF en
`2_laminas_por_georreferenciar/` (Angol 7, Collipulli 3, Lonquimay 4, Lumaco 2, Purén 12,
Renaico 1, Traiguén 4). Curacautín y Victoria no tienen carpeta. Ningún texto explica que «Docs»
cuenta documentos catalogados en el repositorio y no documentos entregados.

**CÓMO LO SUFRE EL PRACTICANTE** — Lee «Victoria: 4 documentos» y los busca. No están, y no hay
nota que lo diga. Concluye que le llegó un zip incompleto, o pierde la tarde intentando
descargarlos sin saber de cuáles se trata.

**CÓMO LO VERIFICASTE** —
```
comunas con carpeta en 2_laminas: ['angol','collipulli','lonquimay','lumaco','puren','renaico','traiguen']
'.pdf': 36   (33 en 2_laminas + 3 documento_original.pdf en 1_cartografia)
TAREAS.md:15 | **Curacautin** | 18,949 | 9 | 4 | 0 | 3 | 0 | 0 | 0 |
TAREAS.md:16 | **Victoria**   | 36,073 | 0 | 0 | 0 | 4 | 0 | 0 | 0 |
```

**GRAVEDAD 3**

---

### 14. El campo `comuna` está vacío en 1.983 de las 2.285 filas del CSV, y con mayúsculas mezcladas

**DÓNDE** — `FUENTE_DE_CADA_POLIGONO.csv`, columna `comuna`.

**QUÉ PASA** — 87 % de las filas no tienen comuna. Y las que la tienen mezclan cajas y tildes:
`Collipulli` (39) junto a `COLLIPULLI` (10), `Renaico` (1) junto a `RENAICO` (19), `Traiguén` (1)
junto a `TRAIGUÉN` (8).

**CÓMO LO SUFRE EL PRACTICANTE** — Abre el CSV en Excel para filtrar por su comuna, que es el uso
que el LEEME le promete («se puede ordenar y filtrar»), y le salen 10 filas de Collipulli cuando
hay 49. Además, `COMO_TRABAJAR_EN_QGIS.md:128` le ordena escribir la comuna *«en mayúsculas, como
en las otras capas»*, y las otras capas no están todas en mayúsculas.

**CÓMO LO VERIFICASTE** —
```
CSV filas 2285 comuna vacia 1983 hectareas vacia 133
comuna
NaN 1983 · ANGOL 164 · Collipulli 39 · RENAICO 19 · LOS SAUCES 16 · LONQUIMAY 11 ·
COLLIPULLI 10 · ERCILLA 10 · PURÉN 10 · CURACAUTÍN 9 · TRAIGUÉN 8 · LUMACO 4 ·
Renaico 1 · Traiguén 1
```

**GRAVEDAD 3**

---

### 15. `cobertura_satelite` trae 15 geometrías exactamente duplicadas y ningún texto lo explica

**DÓNDE** — Capa `cobertura_satelite` de `capas_malleco.gpkg` y su shapefile en
`3_capas_en_shapefile/`.

**QUÉ PASA** — De 48 polígonos, 15 son duplicados exactos (mismo WKB). El documento que lo
declaraba —`ESTADO_DE_LOS_POLIGONOS`, que reportaba «Duplicadas: 16»— fue eliminado (hallazgo 6),
así que hoy no queda ningún texto en el paquete que lo mencione.

**CÓMO LO SUFRE EL PRACTICANTE** — Si usa la cobertura para responder «¿aquí el satélite miró?»
—que es el uso que le da `00_procedencia_de_cada_capa`— cuenta la misma pasada varias veces. Y si
mide superficie cubierta, la infla.

**CÓMO LO VERIFICASTE** —
```
cobertura_satelite    n=48  invalidas=0  dup_exactos=15
```
(hash MD5 del WKB de cada geometría, capa por capa; el resto de las capas dio `dup_exactos=0`).

**GRAVEDAD 3**

---

### 16. Un estudio de riesgo sin efecto legal queda clasificado en la capa «A», la normativa

**DÓNDE** — Capa `00_procedencia_de_cada_capa`, fila `DERIVADO_angol_peligro_inundacion_2013`,
campo `capa_evidencia = A_derivado`; contra
`1_cartografia_ya_vectorizada/angol-peligro-inundacion-2013/LEEME.md` línea 45.

**QUÉ PASA** — El LEEME de esa capa dice: *«Este documento es un **levantamiento de riesgo**, no
una norma»* y *«No tiene efecto legal: no es el vectorial del plan regulador»*. Aun así viaja bajo
la letra **A**, que la tabla del LEEME principal define como *«Lo que el plan regulador declaró
área de riesgo. Tiene efecto legal.»* Comparte letra con las dos láminas del PRC, que sí la tienen.

**CÓMO LO SUFRE EL PRACTICANTE** — Si agrupa o simboliza por `capa_evidencia` —que es lo que la
letra invita a hacer—, mete en el mismo saco un estudio cualitativo de 2013 sin efecto legal y el
plano vigente del plan regulador. Es exactamente la confusión que el LEEME dice que el proyecto
existe para evitar.

**CÓMO LO VERIFICASTE** —
```
capa: DERIVADO_angol_peligro_inundacion_2013
  capa_evidencia: A_derivado
LEEME.md:78 | **A · Normativo** | Lo que el plan regulador declaró área de riesgo. Tiene efecto legal.
lamina LEEME.md:45 Este documento es un **levantamiento de riesgo**, no una norma...
```
La tabla del LEEME sí distingue una fila `A · Derivado`, pero comparte la letra, y el valor real
del campo (`A_derivado`) es el mismo prefijo.

**GRAVEDAD 3**

---

### 17. Nombres de fuente cortados a media palabra en la tabla de procedencia

**DÓNDE** — `FUENTE_DE_CADA_POLIGONO.md` líneas 15-18 (y su `.docx`).

**QUÉ PASA** — La columna «Fuente» está truncada a ~110 caracteres, y el corte cae en mitad de la
palabra: `«…I. Municipalidad de Angol, septiembre de 201»`, `«…aprobado por la SEREMI d»`,
`«…Plan Regional de Ordenamiento Terri»`.

**CÓMO LO SUFRE EL PRACTICANTE** — Copia la cita para un informe y publica una fuente que termina
en «septiembre de 201»: el año, que es el dato que más importa en este proyecto, se pierde
justo en el corte. La cita completa existe en la tabla de atributos, pero nada en la página se lo
advierte.

**CÓMO LO VERIFICASTE** — Líneas 15, 16, 17 y 18 del archivo, citadas textualmente arriba.
Comparadas contra el campo `fuente` del GeoPackage, que sí está completo:
`«Estudio de Riesgo, Actualización Plan Regulador Comunal de Angol, I. Municipalidad de Angol,
septiembre de 2013»`.

**GRAVEDAD 3**

---

## GRAVEDAD 2

### 18. El orden de prioridad de TAREAS no se reproduce con el criterio que declara

**DÓNDE** — `TAREAS.md` líneas 3-5 y tabla de las líneas 14-24.

**QUÉ PASA** — El criterio declarado es *«comunas con gente y con registro de inundación, pero sin
ninguna cartografía consultable»*. Renaico, con **19 puntos críticos** —el máximo de la provincia—
y 10.665 habitantes, va en el puesto 10 de 11. Victoria, con **0 puntos críticos**, va tercera.

**CÓMO LO SUFRE EL PRACTICANTE** — Confía en el orden porque el documento le dice que está
ordenado por lo que más importa, y empieza por comunas sin ningún registro de inundación mientras
la de mayor registro queda al final.

**CÓMO LO VERIFICASTE** — Puntos por comuna medidos sobre `puntos_criticos_SENAPRED`:
```
RENAICO 19 · LOS SAUCES 16 · ANGOL 14 · LONQUIMAY 11 · COLLIPULLI 10 · ERCILLA 10 ·
PURÉN 10 · CURACAUTÍN 9 · TRAIGUÉN 8 · LUMACO 4   (Victoria: sin filas)
```
coinciden exactamente con la columna «Puntos» de TAREAS; el orden de las filas, no con el criterio.

**GRAVEDAD 2**

---

### 19. Cuatro de las nueve columnas de la tabla de TAREAS no están definidas

**DÓNDE** — `TAREAS.md` líneas 12 y 26-37.

**QUÉ PASA** — La sección «Cómo leer las columnas» explica `Área PRC`, `Láminas`, `Retículas` y
`Ya derivados`. No explica `Hab.`, `Puntos`, `Crónicos` ni `Docs`, que son cuatro de las nueve.

**CÓMO LO SUFRE EL PRACTICANTE** — Tiene que adivinar de qué año es la población, qué cuenta un
«punto» y a partir de cuántas temporadas algo es «crónico» (el umbral —tres temporadas— sólo
aparece dentro de `00_procedencia_de_cada_capa`, en el GeoPackage). `Docs`, además, es la columna
del hallazgo 13.

**CÓMO LO VERIFICASTE** — Encabezado de la tabla:
`| Comuna | Hab. | Puntos | Crónicos | Área PRC | Docs | Láminas | Retículas | Ya derivados |`
contra los cuatro viñetas de las líneas 28-37.

**GRAVEDAD 2**

---

### 20. La tabla de formatos del LEEME no lista `.pdf` ni `.jpg`

**DÓNDE** — `LEEME.md` líneas 47-53.

**QUÉ PASA** — La tabla «En qué formato está todo» lista `.gpkg`, `.shp`, `.geojson`, `.csv` y
`.docx`. El paquete lleva además 36 PDF y 3 JPG: 39 de los 141 archivos, y son los que el
practicante más va a abrir. La versión anterior del LEEME sí los listaba.

**CÓMO LO SUFRE EL PRACTICANTE** — Menor: sabe abrir un PDF. Pero la tabla se presenta como
inventario completo y no lo es.

**CÓMO LO VERIFICASTE** — Conteo de extensiones citado en el hallazgo 5: `'.pdf': 36, '.jpg': 3`,
contra las cinco filas de la tabla.

**GRAVEDAD 2**

---

### 21. Los nombres de comuna de TAREAS no llevan tilde; los de los datos, sí

**DÓNDE** — `TAREAS.md` líneas 15, 19, 20 (`Curacautin`, `Puren`, `Traiguen`) contra el campo
`comuna` de `puntos_criticos_SENAPRED` (`CURACAUTÍN`, `PURÉN`, `TRAIGUÉN`).

**QUÉ PASA** — El texto y el dato escriben distinto la misma comuna.

**CÓMO LO SUFRE EL PRACTICANTE** — Un filtro copiado del documento a la calculadora de campos de
QGIS devuelve cero registros y parece un error de datos.

**CÓMO LO VERIFICASTE** — Valores reales del campo, pegados en el hallazgo 18.

**GRAVEDAD 2**

---

### 22. Nombres de documento truncados a 52 caracteres en la tabla de láminas

**DÓNDE** — `2_laminas_por_georreferenciar/LEEME.md` líneas 16, 31, 32, 33, 34, 46.

**QUÉ PASA** — La columna «Documento» corta el nombre:
`04_Anteproyecto-Estrudio-Riesgos_PRC_Purén_VF.pdf.pd`,
`04_Anteproyecto-Memoria_Actualizacion_PRC_Traiguén.p`,
`04_Anteproyecto-Completo-Planos_PRC_Collipulli.pdf.p`.

**CÓMO LO SUFRE EL PRACTICANTE** — Poco: la columna «PDF en esta carpeta», dos celdas más allá,
trae la ruta completa. Molesta al buscar por nombre.

**CÓMO LO VERIFICASTE** — Líneas citadas del archivo, con los nombres reales del listado de PDF
(`04_Anteproyecto-Estrudio-Riesgos_PRC_Purén_VF.pdf.pdf`, etc.).

**GRAVEDAD 2**

---

### 23. `Estudio_Riesgo.pdf` viaja dos veces, idéntico, pese a que el LEEME dice que los repetidos ya están fuera

**DÓNDE** — `1_cartografia_ya_vectorizada/angol-peligro-inundacion-2013/documento_original.pdf` y
`2_laminas_por_georreferenciar/angol/Estudio_Riesgo.pdf`; `LEEME.md` líneas 41-42.

**QUÉ PASA** — Los dos archivos tienen el mismo MD5 (`e893f7201b`) y pesan 4,16 MB cada uno. El
LEEME afirma: *«Los documentos repetidos ya están fuera. […] se comparan por contenido y viaja
uno.»* La deduplicación funcionó dentro de `2_laminas` (cuatro filas marcadas `↩ mismo archivo`),
no entre carpetas.

**CÓMO LO SUFRE EL PRACTICANTE** — Puede vectorizar desde una copia y comparar contra la otra sin
darse cuenta de que es el mismo documento. La fila 35 del LEEME de láminas, además, dice
`✅ ya vectorizado` en la celda «PDF en esta carpeta» cuando el PDF sí está en esa carpeta.

**CÓMO LO VERIFICASTE** —
```
   64  e893f7201b  1_cartografia_ya_vectorizada\angol-peligro-inundacion-2013\documento_original.pdf
   64  e893f7201b  2_laminas_por_georreferenciar\angol\Estudio_Riesgo.pdf
```

**GRAVEDAD 2**

---

### 24. Los `.md` no viajan en el zip, pero un LEEME remite a un `.md`

**DÓNDE** — `1_cartografia_ya_vectorizada/angol-prc-ar2a-lamina1/shapefile/LEEME_shapefile.md`
línea 10 (y lamina2, misma línea).

**QUÉ PASA** — *«El texto completo está en `../poligonos.geojson` y en `../LEEME.md`.»* El zip
lleva sólo los `.docx`: los 13 `.md` quedan fuera.

**CÓMO LO SUFRE EL PRACTICANTE** — Busca `..\LEEME.md` y encuentra `..\LEEME.docx`. Trivial de
resolver, pero es una ruta que no existe en lo que recibe.

**CÓMO LO VERIFICASTE** —
```
md: []      (namelist del zip)
docx: [13 entradas]
EN DISCO NO EN ZIP: los 13 .md
```

**GRAVEDAD 2**

---

### 25. El SRC de trabajo que manda la guía no es el del resto del paquete, y nunca se dice en cuál entregar

**DÓNDE** — `COMO_TRABAJAR_EN_QGIS.md` línea 120 («SRC: el mismo huso UTM») contra `LEEME.md`
línea 55 («**Todo viene en EPSG:4326**»).

**QUÉ PASA** — La guía manda crear la capa nueva en UTM 18S o 19S. Las 11 capas del paquete están
en EPSG:4326, incluidas las tres derivadas que la guía pone como modelo. La sección «Qué entregar
de vuelta» no dice en qué SRC debe llegar el resultado.

**CÓMO LO SUFRE EL PRACTICANTE** — Entrega en UTM y no calza con nada de lo anterior sin
reproyectar, o reproyecta por su cuenta sin que nadie se lo haya pedido. No es un error de dato,
pero es una decisión que el paquete le deja a él sin decírselo.

**CÓMO LO VERIFICASTE** — CRS medido en las 11 capas del GeoPackage y en los 14 shapefiles: todos
`EPSG:4326`; los 14 `.prj` son un único WKT idéntico de WGS84.

**GRAVEDAD 2**

---

## GRAVEDAD 1

### 26. `campamentos.hectareas` no corresponde a su geometría

**DÓNDE** — Capa `campamentos` de `capas_malleco.gpkg`, campo `hectareas`.

**QUÉ PASA** — El campo declara 8,95 ha; el polígono mide 5,56 ha en UTM 18S (y 6,32 en el CSV,
que arrastra el factor del hallazgo 3). Tres números para un solo polígono.

**CÓMO LO SUFRE EL PRACTICANTE** — Es un único polígono y `00_procedencia_de_cada_capa` advierte
que el cruce lo hace MINVU en origen y «acá no se recalcula». Impacto bajo.

**CÓMO LO VERIFICASTE** —
```
campamentos  n=1  gpkg.hectareas=8.95  real32718=5.56  csv_ha=6.32
```

**GRAVEDAD 1**

---

### 27. «1 páginas»

**DÓNDE** — `1_cartografia_ya_vectorizada/angol-prc-ar2a-lamina1/LEEME.md` línea 8 y lamina2 línea 8.

**QUÉ PASA** — *«**Documento:** Plano_Zonificacion_Vialidad-PRC_09201-1.pdf (1 páginas)»*.
Concordancia de número. Verificado que el PDF tiene efectivamente 1 página.

**GRAVEDAD 1**

---

# SIN DATO — lo que no pude medir

- **Los menús de QGIS.** No hay QGIS instalado en esta sesión. No puedo confirmar que
  «Capa → Georreferenciador…», «Configuración de transformación», «Archivo → Guardar puntos GCP
  como…», «Vector → Herramientas de geometría → Comprobar validez» o
  «Complementos → QuickMapServices» estén donde el documento dice, ni en qué versión de QGIS 3.x.
  **Sí verifiqué lo verificable**: los códigos EPSG:32718 y EPSG:32719 son correctos para UTM 18S
  y 19S WGS84, y los rangos de Este de la tabla (`COMO_TRABAJAR_EN_QGIS.md:59-60`) son coherentes
  con la posición real de las comunas —Angol cae en 72,73°O–72,67°O, dentro del huso 18 (límite
  72°O), y Lonquimay al este de esa longitud, en el 19—. El bbox medido de los polígonos de Angol
  es −72,7399 a −72,6650 de longitud, −37,8302 a −37,7782 de latitud.
- **Los 375 polígonos reparados** (`LEEME.md:36`). No hay una copia previa a la reparación contra
  la cual medir. Lo que sí verifiqué: hoy las 11 capas tienen **0 geometrías inválidas**, que es
  consistente con la afirmación.
- **Las cifras de población** de la columna `Hab.` de TAREAS. No hay en el paquete ninguna capa
  ni tabla con población; no se puede contrastar sin salir del paquete.
- **Si las páginas 32, 34, 55 y 56 de `Estudio_Riesgo.pdf` traen realmente cartografía de
  inundación.** Verifiqué que las páginas existen (el PDF tiene 64) y que TAREAS las declara con
  retícula; no abrí las figuras.
- **Si los enlaces resuelven.** No hice peticiones de red. Los 14 URL de
  `FUENTE_DE_CADA_POLIGONO.md` y `00_procedencia_de_cada_capa` están bien formados, nada más.
- **Si la georreferenciación de las tres capas derivadas es correcta en terreno.** Sin el `.tif`
  ni el `.points` (hallazgo 12) no hay nada que auditar dentro del paquete.
- **El origen del factor 1,135 del hallazgo 3.** Verifiqué que existe y que es constante en todas
  las capas; no busqué el script que lo produce, porque la auditoría es del entregable.

---

# VERIFICADO LIMPIO

Todo lo siguiente se midió y **está bien**:

1. **Coherencia entre formatos.** Las 11 capas coinciden en número de geometrías entre
   `capas_malleco.gpkg` y los 11 shapefiles de `3_capas_en_shapefile/`, con el mismo número de
   columnas y el mismo CRS. Igual las tres carpetas de `1_cartografia_ya_vectorizada`:
   GeoJSON, GPKG y SHP dan 96/26/28 geometrías, la misma superficie (213,11 / 110,52 / 117,04 ha
   en UTM 18S) y el mismo juego de campos.
2. **Los shapefiles traen sus cinco archivos.** 14 `.shp`, 14 `.dbf`, 14 `.shx`, 14 `.prj`,
   14 `.cpg`. Ninguno cojo.
3. **El CRS declarado es el mismo en todo.** Los 14 `.prj` son un único WKT de WGS84 idéntico;
   las 11 capas del GeoPackage y los 3 GeoJSON son EPSG:4326.
4. **Validez geométrica.** 0 geometrías inválidas en las 11 capas, tal como el paquete promete.
5. **Los recuentos de polígonos cuadran en todas partes.** LEEME (96/26/28), los LEEME de cada
   subcarpeta, `FUENTE_DE_CADA_POLIGONO.md`, el CSV (96+26+28 filas), `00_procedencia_de_cada_capa`
   (campo `n_geometrias`) y las capas reales. `areas_riesgo_PRC_MINVU` 1+38+1 = 40 = real;
   `huella_observada_satelite` 342+115 = 457 = real; `cobertura_satelite` 27+21 = 48 = real.
6. **Las hectáreas de los LEEME y del GeoPackage son correctas.** 213,13 / 110,51 / 117,06
   declaradas contra 213,11 / 110,52 / 117,04 medidas en UTM 18S. El desglose por clase también:
   Alto 67 polígonos / 195,0 ha y Medio 29 / 18,1 ha. (El único que falla es el CSV, hallazgo 3.)
7. **Los 33 recuentos de páginas de PDF de `2_laminas_por_georreferenciar/LEEME.md` son exactos.**
   Verificados uno por uno con pypdfium2: 52, 57, 39, 113, 105, 39, 3, 82, 82, 66, 141, 82, 218,
   122, 133, 127, 36, 104, 2, 39, 36, 106, 1, 1, 1, 1, 1, 123, 157, 151, 57, 1. Ninguna página
   citada cae fuera del documento.
8. **«64 páginas» de `Estudio_Riesgo.pdf` y «1 páginas» de los dos planos: correcto.**
9. **La deduplicación dentro de `2_laminas` es real.** Las cuatro filas marcadas `↩ mismo archivo`
   (Plano-PRC-Caupolican-2024, Plano-PRC-Puren-2024,
   04_Anteproyecto_Memoria_Explicativa_PRC_Traiguén, 04_Anteproyecto_Planos_PRC_Traiguén) no
   viajan duplicadas: 33 PDF en disco, ningún par con el mismo MD5 dentro de esa carpeta.
10. **Los recuentos por comuna de TAREAS cuadran con los datos.** «Puntos» suma 111 y coincide
    comuna por comuna con `puntos_criticos_SENAPRED`; «Crónicos» suma 39 y coincide con el campo
    `cronico`; «Área PRC» (Collipulli 38, Renaico 1, Traiguén 1 = 40) coincide con
    `areas_riesgo_PRC_MINVU`; «Ya derivados» 150 = 96+26+28. Las 11 comunas de la provincia de
    Malleco están todas presentes.
11. **Las 16 retículas de TAREAS coinciden** con las 16 filas de la segunda tabla de
    `2_laminas_por_georreferenciar/LEEME.md` (Angol 6, Purén 9, Renaico 1).
12. **Los LEEME de shapefile dicen la verdad sobre el truncamiento.** Los nombres de campo
    acortados que declaran (`metodo_ori`, `escala_ori`, `estado_tra`, `incertidum`, `descripcio`,
    `efecto_leg`) son exactamente los que trae el `.dbf`. El LEEME de `3_capas_en_shapefile/`
    declara además los renombrados sin parecido (`ordenanz_1`, `ind_amen_1`…`ind_vuln_2`), que es
    la trampa que de verdad muerde y está bien documentada.
13. **`00_procedencia_de_cada_capa` existe, tiene 11 filas —una por capa— y ninguna está vacía**
    en los campos `fuente`, `url`, `metodo`, `incertidumbre` y `capa_evidencia`.
14. **Las capas derivadas no tienen ni un solo atributo nulo**: los 11-12 campos de las tres
    capas están completos en las 150 filas.
15. **El CSV es legible en Excel chileno.** Separador `;`, UTF-8 con BOM: abre directo con doble
    clic sin el paso de «Datos → Desde texto».
16. **Zip y carpeta son consistentes.** Ningún archivo del zip falta en disco ni difiere en
    contenido; la única diferencia son los 13 `.md`, que quedan fuera a propósito.
17. **El GeoPackage abre de una** con las 11 capas más la tabla sin geometría, tal como promete
    el LEEME («arrástralo a QGIS y aparecen todas»).

---

# LO QUE SOBRA

El dueño pidió simplificar. Esto es lo que se puede recortar sin perder ninguna instrucción.
Está medido sobre los `.md` actuales (post 09:56).

### A. La anécdota de la DGA, contada dos veces y en dos versiones distintas

- `COMO_TRABAJAR_EN_QGIS.md:17-20` — *«descartamos una que decía “Mapa Inundación Subcuenca Ríos
  Malleco y Vergara” y tenía todos sus polígonos de riesgo fuera de esa subcuenca»*
- `TAREAS.md:53-55` — *«Y una de la DGA que estaba perfectamente ubicada y no mapeaba ni un
  polígono de riesgo dentro de la zona que su título nombraba.»*

Es el mismo caso. **Sobra la de TAREAS entera**; en su lugar, una línea:
*«Antes de invertir tiempo en una lámina, aplica el paso 0 de `COMO_TRABAJAR_EN_QGIS`.»*

### B. El párrafo de Teodoro Schmidt

`TAREAS.md:50-53` — *«ya descartamos una de Teodoro Schmidt que resultó ser riesgo multiamenaza
“sin discriminar niveles de peligrosidad”»*. Teodoro Schmidt no es de Malleco y no aparece en
ninguna otra parte del paquete. La regla ya está dicha en `COMO_TRABAJAR_EN_QGIS.md:14-16`.
**Sobra entero.**

### C. La sección «Qué NO hacer» duplicada

`COMO_TRABAJAR_EN_QGIS.md:170-186` («Lo que nunca hay que hacer») ya absorbió las cinco reglas.
`TAREAS.md:105` remite a ella. **Correcto como está** — pero `TAREAS.md:89-90`
(*«Un polígono sin error declarado no se publica»*) y `COMO_TRABAJAR_EN_QGIS.md:112-113`
(la misma frase, literal) repiten la misma sentencia. **Sobra la de TAREAS.**

### D. Los tres bloques «Qué NO es» de los LEEME de lámina, idénticos palabra por palabra

`1_cartografia_ya_vectorizada/*/LEEME.md` líneas 48-52 (o 47-51): las mismas tres viñetas en las
tres carpetas, y una de ellas —*«No es una modelación hidráulica, **salvo que el método de arriba
lo diga**»*— es una plantilla que se contradice a sí misma según el caso. Los tres LEEME ya dicen
lo mismo en «Lo que la fuente advierte», tres párrafos más arriba. **Sobran los tres bloques**;
la advertencia ya está en el campo `incertidumbre` de cada polígono.

### E. Los dos LEEME de shapefile de lamina1 y lamina2 son el mismo archivo

`angol-prc-ar2a-lamina1/shapefile/LEEME_shapefile.md` y el de lamina2: **byte a byte idénticos**
(1.330 bytes cada uno, mismo contenido), y ambos declaran el mismo truncamiento. Sirven, pero el
párrafo «Si vas a citar o revisar la procedencia» repite lo que ya dice `LEEME.md:59-63`.
**Sobra ese párrafo en los tres LEEME de shapefile**; basta la lista de campos acortados, que es
lo único específico de cada capa.

### F. Explicaciones de más en la guía de QGIS

- `COMO_TRABAJAR_EN_QGIS.md:78` — la justificación de Polinomial 1 ocupa tres líneas
  (*«Los polinomios de grado 2 o 3 “arreglan” el error deformando la imagen, y el RMSE baja sin
  que la ubicación mejore»*). **Reemplazar por**: *«Polinomial 1. Los grados 2 y 3 bajan el RMSE
  deformando la imagen, sin mejorar la ubicación.»*
- `COMO_TRABAJAR_EN_QGIS.md:67-70` — la explicación de por qué dos puntos mienten está también en
  el glosario del LEEME (línea 98). **Dejar sólo una**, la de la guía.
- `COMO_TRABAJAR_EN_QGIS.md:31-32` — *«Mientras más resolución, mejor: cada píxel de la imagen es
  la unidad más fina que vas a poder dibujar después.»* **Sobra la explicación**; basta
  *«Exporta a la máxima resolución que ofrezca el lector.»*

### G. El aviso de la fecha del paquete

`LEEME.md:3-5` — *«si pasaron meses, pídenos una copia nueva antes de apoyarte en los conteos»*.
No hay a quién pedírsela (hallazgo 7). **O se le pone destinatario, o sobra.**

### H. Prosa de manual generado

- `LEEME.md:34` — *«No hace falta que arregles nada antes de empezar»*, seguido de una lista de
  tres cosas que el practicante nunca habría sabido que estaban rotas. **Sobra la frase de
  entrada**; la lista se sostiene sola bajo el título «Lo que ya viene resuelto».
- `2_laminas_por_georreferenciar/LEEME.md:10-11` — *«La columna “Lámina en la página” es la que
  importa: estos son informes de decenas o cientos de páginas y el mapa está en dos o tres.»*
  **Reemplazar por**: *«El mapa está en las páginas en negrita.»*
- `LEEME.md:71-74` — el párrafo *«No es burocracia…»* justifica por qué abrir
  `00_procedencia_de_cada_capa`. La tabla A/B/C/D que viene justo después dice lo mismo con
  ejemplos. **Sobra el párrafo.**
