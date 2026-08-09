# Inventario de fuentes — mapas de inundación en Chile

> Levantamiento: 6-ago-2026. Estado de verificación indicado por fuente.
> `✅ verificado` = se consultó el endpoint/archivo directamente en esta sesión.
> `🔎 referencia` = proviene de búsqueda web, falta confirmar contra la fuente.

## 0. Conclusión del levantamiento

**No existe una capa nacional de amenaza de inundación en Chile.** Existe un
mosaico de siete familias de información con coberturas, formatos y estatus
legal distintos. El diagnóstico inicial del proyecto era correcto en lo esencial
(la mayoría está en PDF de planes reguladores), pero incompleto en dos puntos
que cambian el diseño del producto:

1. **Sí hay un dataset nacional, público y machine-readable de dónde se inunda**:
   los *Puntos Críticos* del Programa Invierno de SENAPRED (15.799 puntos, ArcGIS
   REST abierto). Nadie lo está usando como capa de riesgo ciudadana.
2. **Sí hay un raster global de amenaza con períodos de retorno** que cubre Chile
   completo con licencia libre (JRC GloFAS v2.1, ~90 m). No reemplaza un estudio
   local, pero da línea base continua donde no hay nada.

Lo que falta y hay que construir es la **capa observada**: dónde llegó el agua de
verdad, derivada de SAR. Eso no lo tiene ningún visor chileno.

---

## 1. Amenaza normativa (tiene efecto legal)

### 1.1 DGA — Mapas de Amenaza de Inundación (MAI) ✅ verificado

- URL: https://dga.mop.gob.cl/mapas-de-amenaza-de-inundacion/
- Es el instrumento formal, aprobado por resolución, con modelación hidráulica.
- **Cobertura al 6-ago-2026: una sola cuenca.** Río Mataquito, Región del Maule
  (Res. DGA Exenta N°5199 de 2025).
- Formatos publicados: PDF (6 láminas por sector), **GDB, SHP y KMZ**, más metadatos,
  todo en un ZIP.
- **La Araucanía no aparece** — ni Cautín, ni Imperial, ni Toltén, ni Temuco.

> Implicancia: el estándar de oro existe y es descargable, pero cubre <1% del país.
> Sirve como *plantilla de esquema de atributos* para lo que construyamos.

### 1.2 Áreas de riesgo de Planes Reguladores — SÍ existen en vectorial ✅ verificado

> ⚠️ **Corrección al levantamiento inicial.** La primera pasada concluyó que no
> había capa nacional de áreas de riesgo. Era falso, y el motivo del error vale
> más que el dato: el registro de `datos.gob.cl` apunta a
> `geoportal.cl/ArcGIS/rest/services/MinisteriodeViviendayUrbanismo/...`, que
> **está caído (404)**. MINVU migró a otra organización ArcGIS y nadie actualizó
> el catálogo. Un catálogo oficial obsoleto es la razón habitual de concluir que
> "el dato no existe".

**Organización viva de MINVU**: `services3.arcgis.com/cTnMkBRk4HWkUCRo`
(1.310 servicios publicados; se llega a ella desde el `orgId` embebido en
https://ide.minvu.cl/).

| Servicio | Contenido | Registros |
|---|---|---|
| `prc_riesgo_nacional_visor_P/0` | **Área Riesgo PRC — nacional** | **3.765 polígonos** |
| `prc_riesgo_nacional_visor_P/1` | Área Riesgo PRI — nacional | 21.392 polígonos |
| `Riesgos_IPT/1` | Misma capa PRC, versión 22-03-2022 | 4.624 |
| `09_PRC_La_Araucania` | 42 capas: PRC comuna por comuna de la región | — |

**La Araucanía: 212 polígonos de área de riesgo, 63 de ellos por amenaza hídrica**
(tras deduplicar entre la capa nacional y la regional, que publican los mismos
polígonos para Collipulli y Carahue).

Distribución de los polígonos de inundación: Collipulli 36, Carahue 9,
Pitrufquén 4, Toltén 4, Loncoche 2, Villarrica 2, y 1 cada uno en Temuco,
Nueva Imperial, Puerto Saavedra, Renaico, Traiguén y Gorbea.

Clasificaciones presentes: `INUNDACION`, `ANEGAMIENTO`, `INUNDACION LITORAL`,
`AFLORAMIENTO NAPAS FREATICAS`, `ZR-2 Área de Riesgo por Inundación`,
`ZR-5 Área y/o Franja de Restricción por Quebradas`, `ZR-1 Área de Riesgo por
Anegamiento`.

Campo clave para el ciudadano: **`UPROH`/`UPROM` (usos prohibidos)**, que dice
textualmente qué no se puede construir en ese terreno, más `URL` con enlace a la
ordenanza en observatoriourbano.cl.

**Límite honesto de esta capa**: sólo cubre comunas con PRC que haya zonificado el
riesgo, y sólo dentro del límite urbano. 12 comunas de 32 en la región. La
ausencia de polígono no significa ausencia de riesgo.

⚠️ **Trampa de consulta**: pedir `outFields` con un campo que esa capa no tiene
(p. ej. `UPROH` donde el campo es `UPROM`) devuelve **HTTP 200 con un objeto
`error`**, no un fallo. Leer `features` con default `[]` convierte eso en "capa
vacía" y hace desaparecer 89 polígonos sin que nadie se entere.

Portales relacionados (menos útiles de lo que aparentan):
- https://instrumentosdeplanificacion.minvu.cl/ — publica ordenanzas (PDF) y
  planos (JPG), no los estudios de riesgo. El filtro por comuna no cambia el
  resultado servidor-side.
- https://ide.minvu.cl/ — ArcGIS Hub, útil sólo para descubrir el `orgId`.

### 1.2b Evaluación Ambiental Estratégica — la llave del expediente completo ✅ verificado

**Todo Plan Regulador Comunal de Chile debe pasar por Evaluación Ambiental
Estratégica**, y el Ministerio del Medio Ambiente publica cada procedimiento con
sus documentos adjuntos, sin autenticación. Es un único portal que da acceso a
los expedientes de planificación territorial de todo el país.

- Tabla nacional: https://eae.mma.gob.cl/reporte-general — **524 procedimientos**
- Ficha con adjuntos: `https://eae.mma.gob.cl/file/<id>` (ids 1–536)
- Los PDF viven en `https://eae.mma.gob.cl/storage/documents/<nombre>.pdf`

No hay buscador de texto ni índice de documentos: por eso
`scripts/05_eae_documentos.py` construye el índice que falta.

**Resultado del rastreo (6-ago-2026): 5.991 documentos públicos a nivel nacional.
La Araucanía: 30 procedimientos, 411 documentos, 25 comunas cubiertas.**

Tipología de los adjuntos, y qué sirve para cartografía:

| Patrón de nombre | Qué es | Valor cartográfico |
|---|---|---|
| `04_Anteproyecto-Planos_*` | **Láminas del anteproyecto** | Alto — es cartografía pura |
| `04_Anteproyecto_*` | Memoria explicativa | Medio — figuras de riesgo |
| `02_*_IA_*` | Informe Ambiental | Medio — capítulo de riesgos |
| `01_Ingreso_*`, `03_Rpt_*` | Trámite administrativo | Nulo |

⚠️ **Sólo 1 de los 411 documentos tiene "riesgo" en el nombre del archivo**
(`04_Anteproyecto-Estrudio-Riesgos_PRC_Purén_VF.pdf`, con la errata incluida).
Filtrar por nombre de archivo hace perder casi todo: la cartografía de inundación
está *adentro* de documentos que se llaman "Anteproyecto". Por eso
`scripts/07_buscar_laminas_riesgo.py` abre los PDF y busca página por página.

**Resultado del escaneo de los 34 documentos `*Planos*` de La Araucanía:
31 láminas cartográficas con contenido de amenaza hídrica, en 15 documentos.**

| Comuna | Láminas | Documento |
|---|---:|---|
| Vilcún | 6 | `04_Anteproyecto-Planos_PRC_Vilcún.pdf` |
| Collipulli | 3 | `04_Anteproyecto-Completo-Planos_PRC_Collipulli` |
| Teodoro Schmidt | 3 + 3 | dos versiones del anteproyecto |
| Pitrufquén | 2 + 2 | dos versiones |
| Pucón | 2 + 2 | versiones v3 y v4 |
| Purén | 2 | `04_Anteproyecto-Planos_PRC_Purén_VF` |
| Galvarino | 1 ×3 | tres versiones |
| Villarrica–Pucón (PRI) | 1 ×2 | |
| Traiguén | 1 | |

⚠️ **Dos tipos de lámina, y un detector que sólo veía una.** El primer intento
buscó "página con imagen y poco texto" y encontró **cero**. El motivo: los planos
de anteproyecto son **hojas de plóter vectoriales** (Vilcún: 150×60 cm, 5.018
trazos vectoriales, 6.000 caracteres de rótulos). Tienen *mucho* texto, que es
justo lo contrario del criterio. Hay que distinguir:

- **Plano de plóter**: superficie > 1.000.000 pt² (A4 son ~501.000) y ≥200
  objetos (trazos + rótulos + imágenes). El texto no discrimina.
- **Lámina rasterizada** dentro de un informe carta: ≤1.000.000 pt², <1.500
  caracteres y una **imagen que cubra ≥18% de la hoja**. Es el caso del catastro
  de anegamientos de Temuco (54% de la hoja).

⚠️ **El falso positivo que hay que evitar**: pedir sólo "hay una imagen" marca como
lámina cualquier página de texto, porque **el logo de la consultora está en el pie
de todas las hojas**. Exigir fracción de superficie lo elimina. Verificado: sin ese
filtro, la p86 del Estudio Fundado de Riesgos de Temuco —prosa sobre obras en el
canal Gibbs— se publicaba como si fuera un mapa.

✅ **Hallazgo que abarata la georreferenciación**: los planos de plóter traen la
**grilla de coordenadas UTM rotulada en los márgenes**, y en muchos casos esos
rótulos son **texto vectorial con posición exacta** dentro del PDF, no una imagen.
Cada cruce de grilla es entonces un punto de control de coordenada exacta.

**Resultado: 23 planos georreferenciados automáticamente** (`scripts/08_…`), con
RMSE leave-one-out mayoritariamente bajo 0,20 m:

| Comuna | Planos | RMSE | Resolución |
|---|---:|---|---|
| Vilcún | 5 | 0,02 – 0,09 m | 0,21 m/px |
| Teodoro Schmidt | 6 | 0,15 – 0,20 m | 0,42 m/px |
| Pitrufquén | 4 | 0,03 – 0,04 m | 0,42 m/px |
| Pucón | 4 | 1,31 – 1,81 m | 0,77 m/px |
| Galvarino | 3 | 0,11 m | 0,42 m/px |
| Traiguén | 1 | 0,19 m | 0,42 m/px |

Verificación independiente sobre Vilcún: la hoja aterriza en −38,667 / −72,216
(la localidad), 4,00 × 1,50 km, y los puntos críticos de SENAPRED —dataset que no
participó en la georreferenciación— caen sobre las calles y el cauce dibujados.

⚠️ **Dónde falla, y por qué el rechazo es correcto.** 8 de 31 láminas se
descartaron. La causa verificada en el PRC de Purén: **los rótulos de la grilla
están vectorizados**, no son texto. El PDF trae 490 objetos de texto y 50.177
trazos, y en su capa de texto los únicos números son `1976`, `1992` y `2026`
(referencias legales). El plano sí muestra la grilla al renderizarlo —se leen
5791000, 5790500, 5790000— pero es dibujo, no texto.
→ Camino pendiente para recuperarlos: **OCR sobre los márgenes renderizados**.

⚠️ **Tipos de objeto de pdfium**: `1 = TEXTO`, `2 = TRAZO`, `3 = IMAGEN`. Es fácil
invertir 1 y 2 y sacar conclusiones equivocadas sobre la composición de una página.

### 1.3 Estudios Fundados de Riesgo (anexos de los PRC)

Documento clave para Temuco, verificado descargable ✅:

- `Cap9-5-Estudio-Fundado-Riesgos.pdf` — https://www.temuco.cl/wp-content/uploads/2022/04/Cap9-5-Estudio-Fundado-Riesgos.pdf
- `Cap9-2-Estudio-Aguas-Lluvias.pdf` — https://www.temuco.cl/wp-content/uploads/2022/04/Cap9-2-Estudio-Aguas-Lluvias.pdf

Son PDF con cartografía rasterizada. **Este es el caso típico** que hay que
georreferenciar. En el de Temuco, la **página 13 del Estudio de Aguas Lluvias** es
la *"Figura N°1: Catastro de Anegamientos Estacionales, año 2015"* — el plano de
la ciudad con los tramos de calle anegados marcados en rojo. Exactamente el tipo
de información que existe, es pública y no llega a nadie.

Otros estudios de riesgo hallados directamente en sitios municipales, todos
verificados descargables y ya incorporados al pipeline (`scripts/03_…`) ✅:

| Comuna | Documento | URL |
|---|---|---|
| Pucón | Estudio Fundado de Riesgos y Protección Ambiental | https://www.sustentapucon.cl/wp-content/uploads/2022/02/Estudio_Fundado_Riesgos_Proteccion_Ambiental-3.pdf |
| Teodoro Schmidt | Estudio de Riesgos PRC (E5) | https://muniteodoro.cl/portal/wp-content/uploads/2023/05/Estudio-Riesgos-PRCTS-E5.pdf |
| Purén | Anteproyecto — Estudio de Riesgos | vía EAE (`04_Anteproyecto-Estrudio-Riesgos_PRC_Purén_VF.pdf`) |
| Collipulli | PRC completo | https://municipalidadcollipulli.cl/wp-content/uploads/2022/07/PRC-1.pdf |

### 1.3b Barrido automático de los 32 sitios municipales ✅ verificado

`scripts/12_cosechar_municipios.py` automatiza esta vía. Dos hallazgos que la
hacen viable:

**1. Los dominios se adivinan.** Las municipalidades chilenas usan un puñado de
patrones (`municipalidad<comuna>.cl`, `muni<comuna>.cl`, `<comuna>.cl`,
`m<comuna>.cl`…). Probándolos y verificando cuál responde HTML se descubrieron
**31 de 32** dominios sin buscar a mano. El único que falló fue Lonquimay
(`mlonquimay.cl`, patrón que quedó agregado).

**2. Son WordPress y exponen su biblioteca de medios.**
`/wp-json/wp/v2/media?search=<término>` permite **buscar directamente entre los
archivos subidos**. Es mucho más efectivo que rastrear enlaces y más considerado
con el sitio: una docena de consultas a la API en vez de sesenta descargas de
páginas.

> ⚠️ El rastreo por enlaces a profundidad 2 devolvía **cero en Temuco**, que sí
> publica sus estudios. Con la API pasó a 12 documentos. Si un municipio parece no
> publicar nada, probar la API antes de concluirlo.
>
> ⚠️ **No usar `media_type=application`** en esa consulta: descarta resultados
> válidos porque no todos los sitios clasifican así los PDF. Filtrar por la
> extensión de la URL.

**Resultado: 92 documentos de 7 comunas** (Purén 36, Angol 24, Temuco 10,
Curarrehue 9, Villarrica 5, Collipulli 4, Saavedra 4).

**Las otras 25 comunas genuinamente no publican estos documentos.** Verificado
consultando su biblioteca de medios: en Galvarino los únicos aciertos de "riesgo"
son afiches de prevención de riesgos laborales; en Cunco no hay ninguno. Para
ellas el registro EAE es la única vía.

⚠️ **Ruido a filtrar**: buscar "ordenanza" a secas trae la de tenencia de mascotas
y la de medio ambiente (50 MB). Palabras como *ordenanza*, *memoria*, *decreto* y
*plano* sólo cuentan acompañadas de algo que las ate a planificación territorial.

Patrón replicable si se hace a mano: buscar `<municipio>.cl` + "estudio fundado de
riesgos" / "actualización PRC". Pero el camino sistemático para el resto del país
es EAE (§1.2b), porque no depende de que cada municipio mantenga su sitio.

**Las dos vías son complementarias, no redundantes**: el municipio publica el
*Estudio Fundado de Riesgos* —el estudio que fundamenta la zonificación, con el
análisis de amenaza detallado— mientras que el registro EAE publica el expediente
del procedimiento (anteproyecto, planos, informes ambientales). Láminas de
inundación encontradas por la vía municipal: Teodoro Schmidt 7, Temuco 7 (5 en el
Estudio de Aguas Lluvias + 2 en el Estudio Fundado de Riesgos), Pucón 2.

Contenido de riesgo de inundación ya identificado en los anteproyectos 🔎:
- **Angol**: zona de riesgo asociada al río Malleco en su confluencia con el
  Vergara, y en el puente N°1 donde se unen el Picoiquén y el Rehue.
- **Traiguén**: el río pasó de ser límite de la ciudad original a cauce inmerso
  en ella; amenaza caracterizada como mediana-alta.

---

## 2. Estudios de ingeniería (sin efecto normativo, alta calidad técnica)

### 2.1 DOH — Planes Maestros de Evacuación y Drenaje de Aguas Lluvias

- Repositorio: https://doh.mop.gob.cl/ y https://repositoriodirplan.mop.gob.cl/
- Plan Maestro Temuco–Padre Las Casas aprobado por **D.S. MOP N°1941, 31-oct-2002** 🔎
  (norma en BCN: https://www.bcn.cl/leychile/Navegar?idNorma=206896)
- Existe actualización posterior del Plan Maestro de Temuco 🔎
  (https://adaptaclima.org/wp-content/uploads/2024/01/Digital_LIBRO-PLAN-MAESTRO-1.pdf)
- Formato: PDF. Definen red primaria, zonas de anegamiento y obras. Cubren ~50 ciudades.

### 2.2 SERNAGEOMIN — Geología para el Ordenamiento Territorial

- `Geología para el ordenamiento territorial: área de Temuco, Región de La Araucanía`,
  2007, Serie Geología Ambiental, esc. 1:100.000 🔎
  (tienda digital: https://tiendadigital.sernageomin.cl/es/ — ítem 2852)
- Incluye lámina de *peligros geológicos y problemas de obras civiles*.
- **Confirmado por inspección del org ArcGIS de SERNAGEOMIN** ✅: 208 servicios
  publicados, ninguno es una capa nacional de inundación. Lo temático disponible es
  remociones en masa (`Catálogo_de_eventos_de_RM_nacional`, `REMOCIONES_EN_MASA_SNGM_2005`,
  `Peligros_Geológicos_de_Flujos_Cuencas_Alta_Cordillera`), peligro volcánico y minería.
  → El supuesto inicial "SERNAGEOMIN solo tiene remociones" es **correcto**.

---

## 3. Capa operacional — el hallazgo principal ✅ verificado

### SENAPRED — Puntos Críticos, Programa Invierno

- Endpoint abierto, sin autenticación:
  `https://services5.arcgis.com/i7S5PSnIJAUcWvSE/arcgis/rest/services/compilado_INV_2026/FeatureServer/0`
- **15.799 puntos a nivel nacional**, temporada 2026.
- Series anteriores disponibles: `Registro_Puntos_Críticos` (2020, 2021, 2022),
  `compilado_invierno`, `compilado_estival`.

Esquema de atributos:

| Campo | Contenido |
|---|---|
| `Región` / `Provincia` / `Comuna` / `Sector` | localización administrativa |
| `Causa_del_` | tipología del evento (11 categorías) |
| `Nivel_de_R` | Muy Alto / Alto / Medio / Bajo / Solucionado |
| `Acciones_P`, `Acciones_S` | acciones preventivas y de solución |
| `La_soluci`, `Si_la_resp` | quién es responsable (DOH, Vialidad, municipio…) |
| `Tipo_de_So` | tipo de solución |
| `Longitud`, `Latitud` | WGS84 |

**La Araucanía: 1.374 puntos críticos** (6ª región del país). Desglose por causa:

| n | Causa |
|---:|---|
| 434 | Inundación por desborde de cauce |
| 278 | Colapso colectores de aguas lluvia / alcantarillados |
| 191 | Anegamiento de caminos / pasos a desnivel |
| 113 | Acumulación de nieve |
| 111 | Deslizamiento / derrumbe / rodado / caída |
| 86 | Interrupción de caminos |
| 62 | Subsidencia / licuefacción / socavamiento / erosión |
| 37 | Congelamiento de caminos |
| 35 | Daño o pérdida en infraestructura |
| 21 | Flujos de barro/detritos (aluvión) |
| 6 | Activación de quebradas |

Nivel de riesgo en Araucanía: **292 Muy Alto**, 472 Alto, 415 Medio, 183 Bajo,
12 solucionados.

Top comunas: Purén (106), Temuco (72), Curarrehue (71), Saavedra (69),
Padre Las Casas (68), Nueva Imperial (65), Ercilla (65), Curacautín (59),
Villarrica (58), Carahue (55), Pucón (54), Teodoro Schmidt (54).

> ✅ Encoding: verificado byte a byte — el servicio entrega **UTF-8 válido**
> (`Regi\xc3\xb3n`). El mojibake que aparece al inspeccionar desde consola Windows es
> de la consola, no del dato: usar `PYTHONIOENCODING=utf-8`. No aplicar "reparación"
> de mojibake al ingerir, porque corrompería el texto correcto.

### Otras capas SENAPRED públicas ✅

Del mismo org (`geoportalonemi`, 426 ítems): `Amenaza_por_Tsunami_2024`,
`AMENAZA_VOLCÁNICA_2024`, `Amenaza_por_Incendio_Forestal`, `Servicios_2024`
(salud/bomberos/educación/carabineros), `VIAS_EVAC`, `PE_VOLCÁNES_CHPREP`,
`OBRAS_MINVU_MOP`, `viviendas_afectadas`, `Inunda_R_Minas` (Río de las Minas,
Punta Arenas — única capa de inundación puntual).

> El proyecto `Valles/` ya tiene los scripts `08_descargar_senapred.py` y
> `09_sharding_senapred.py` que consumen este mismo org — **reutilizar, no reescribir**.

---

## 4. Amenaza modelada global (línea base continua)

### 4.1 JRC Global River Flood Hazard Maps v2.1 🔎

- Google Earth Engine: `JRC/CEMS_GLOFAS/FloodHazard/v2_1`
- JRC Data Catalogue: https://data.jrc.ec.europa.eu/collection/id-0069
- 7 períodos de retorno: 10, 20, 50, 75, 100, 200, 500 años. Resolución ~90 m.
- Modelos LISFLOOD (hidrología) + LISFLOOD-FP (hidrodinámica).
- **Licencia CC BY 4.0** — redistribución permitida con atribución.
- Limitación conocida: subestima cuencas pequeñas y no modela drenaje urbano.

### 4.2 Google Flood Hub 🔎

- Chile cubierto desde 2023 (pronóstico fluvial hasta 7 días).
- Julio 2026: se sumó pronóstico de **inundación urbana repentina a 24 h**
  (metodología Groundsource).
- Gratuito, sin registro. Existe API de Flood Forecasting de Google.

### 4.3 Elevación 🔎

- IDE Chile publica **DEM ALOS PALSAR 12,5 m** por región, descarga directa:
  https://ide.cl/descarga/capas.html
- No hay cobertura LiDAR nacional. LiDAR existe solo en zonas prioritarias.
- Alternativas globales: Copernicus GLO-30, FABDEM (DEM corregido por vegetación
  y edificios — relevante porque SRTM/ALOS sobrestiman altura bajo dosel en la
  Araucanía y arruinan el cálculo hidrológico).

---

## 5. Tiempo real

- **DGA HIDROlínea / Sistema Hidrométrico en Línea** 🔎 — 1.330 estaciones
  transmitiendo, dato horario. Fluviométricas (caudal, nivel, temperatura del agua),
  meteorológicas, nivométricas. https://snia.mop.gob.cl/dgasat/pages/dgasat_param/dgasat_param.jsp?param=1
- **Sentinel-1 SAR** — huella observada de inundación. Ver §5b: **no requiere
  cuenta**, contra lo que se había anotado.

## 5b. Sentinel-1 sin ninguna credencial ✅ verificado

> ⚠️ **Corrección al levantamiento inicial**, del mismo tipo que la de §1.2 y por
> el mismo motivo de fondo. La primera pasada anotó la capa B como «bloqueada por
> credenciales de Copernicus Data Space». Era cierto de CDSE y **falso del dato**:
> se registró «requiere credenciales» como una propiedad del *producto* cuando era
> una propiedad de *un proveedor*. El mismo Sentinel-1 se distribuye por varios
> espejos con políticas de acceso distintas.

Las tres piezas, todas verificadas leyendo bytes reales el 9-ago-2026:

| Pieza | Endpoint | Autenticación |
|---|---|---|
| Catálogo | `planetarycomputer.microsoft.com/api/stac/v1/search` | ninguna |
| Catálogo alternativo | `catalogue.dataspace.copernicus.eu/odata/v1/Products` | ninguna para consultar; OAuth **sólo para descargar** |
| Firma de acceso | `planetarycomputer.microsoft.com/api/sas/v1/token/sentinel1euwest/s1-grd` | ninguna |
| Píxeles | `sentinel1euwest.blob.core.windows.net/s1-grd/…/measurement/iw-vv.tiff` | el token SAS anterior |

**Los assets son COG**: un `Range: bytes=…` devuelve una ventana espacial sin
bajar la escena de ~1 GB. Medido: 1.739 × 1.305 px en 6,6 s.

✅ **Y está la anotación SAFE completa en el mismo contenedor**, que es lo que
permite calibrar de verdad en vez de trabajar con cuentas de sensor sin unidad:

```
…/annotation/calibration/calibration-iw-vv.xml    tabla sigmaNought  (1,0 MB)
…/annotation/iw-vv.xml                            anotación del producto
…/annotation/calibration/noise-iw-vv.xml          tabla de ruido térmico
```

**Validación de la cadena completa** (DN → σ⁰ → dB), medida sobre el lago
Villarrica el 4-ago-2026, que es agua indiscutible:

| Superficie | σ⁰ VV |
|---|---:|
| Lago Villarrica, centro | **−24,7 dB** |
| Tierra vegetada alrededor | **−9,4 dB** |

Quince decibeles de separación, y los dos valores caen donde la física dice que
tienen que caer. Si la calibración estuviera mal, el agua no aterrizaría en −25.

⚠️ **Trampas verificadas de esta vía**:

1. **El token SAS caduca en ~1 hora.** Hay que re-firmar *dentro* del bucle de
   proceso. Firmar una sola vez al principio hace que una corrida larga muera a
   mitad con un 403 que se lee como «no tengo permiso» cuando es «se me venció».
2. **El GRD viene en geometría de radar, no proyectado**: `crs` es `None` y trae
   **210 puntos de control**. Hay que reproyectar con ellos.
3. **`WarpedVRT` con rejilla de destino explícita ignora los GCPs y devuelve un
   arreglo de ceros, sin error.** Es el fallo silencioso más peligroso de todo
   esto: parece que la escena no cubre el área. Hay que usar
   `rasterio.warp.reproject(..., gcps=…, src_crs=…)`, que sí los honra.
4. **Al leer decimado hay que escalar los GCPs** por el mismo factor, o la escena
   aterriza corrida por ese factor.
5. **El `bbox` de un item del STAC es el rectángulo envolvente de una huella
   rotada**: que un punto caiga dentro del bbox no significa que la escena lo
   cubra. Costó una validación que salió «sin datos» sin ser un error.
6. **La colección `sentinel-1-rtc`, ya corregida por terreno, SÍ exige cuenta.**
   Con GRD la geocodificación corre por cuenta de uno.

> **Regla general que queda**: antes de anotar un dataset como bloqueado por
> credenciales, recorrer los espejos —CDSE, Planetary Computer, AWS Open Data,
> ASF— y probar una **lectura real de bytes**, no la existencia del registro.

### Pasadas disponibles sobre el evento del 30-jul al 4-ago-2026

Emparejar por **órbita relativa idéntica**, no por fecha: dos pasadas de
geometría de vista distinta difieren en retrodispersión por el terreno, no por el
agua. Tres tracks tienen pasada posterior al evento y referencia suficiente:

| Track | Plataforma | Posterior | Pasadas de referencia previas |
|---|---|---|---|
| 156 descendente | S1C | 3-ago | 22-jul, 10-jul, 28-jun (+ S1D 28-jul, 16-jul…) |
| 164 ascendente | S1C | 3-ago | 22-jul, 10-jul, 28-jun (+ S1D 28-jul, 16-jul…) |
| 83 descendente | S1D | 4-ago | 23-jul, 11-jul, 29-jun, 17-jun, 5-jun |

Varias pasadas previas permiten usar la **mediana** como referencia en vez de una
sola imagen, que es lo que evita confundir suelo mojado con inundación, y una
**desviación** que descarta superficies que ya venían variando solas.

### Resultado y los dos falsos positivos que hay que conocer

**5.776 ha** de huella observada sobre 17.382 km² mirados: 16,2 km² (órbita 83
desc.), 15,4 (156 desc.) y 26,2 (164 asc.). Tres geometrías, dos plataformas y dos
fechas convergiendo en el mismo orden de magnitud.

⚠️ **Nieve húmeda.** En banda C la nieve mojada absorbe casi toda la señal y es
**radiométricamente indistinguible del agua**. Sin filtro geomorfológico aportaba
el 74,7 % de las detecciones de este evento (tasa 8,9 % en la franja cordillerana
contra 0,1–1 % en el resto).

⚠️ **El océano.** Su rugosidad cambia con el viento entre pasadas. Una pasada que
lo encuentra liso lo ve caer >5 dB respecto de referencias que lo encontraron
picado, y eso cumple todos los criterios de «apareció agua». Aportaba 871 de los
903 km² que declaraba una órbita. En el DEM Copernicus el mar vale exactamente 0 m.

Los dos se descartan con **Copernicus GLO-30** (`copernicus-dem-30m.s3.amazonaws.com`),
que es COG público sin credenciales, con tiles de 1°×1° **nombrados por su esquina
suroeste**. Criterio aplicado: pendiente ≤ 5°, altura entre 0,5 y 1.200 m.

⚠️ **El umbral de agua se deriva del agua permanente CONTINENTAL, y por la
mediana, no por el percentil 90.** La cola brillante del agua permanente (p90
−15,8 dB contra p50 −20,1) es agua con viento, no píxeles de borde: erosionar la
máscara tres veces no la mueve. Calibrar contra el mar tampoco sirve: es mucho más
liso que una inundación sobre potrero, y produce un umbral que la huella real no
alcanza a cumplir.

---

## 6. Contexto: la emergencia en curso 🔎

Entre el 30-jul y el 4-ago-2026 un sistema frontal dejó en La Araucanía
**~14.569 personas afectadas**, ~4.800 aisladas, 275 damnificadas, 2.183 viviendas
con daño menor y 19 rutas cortadas. Desbordes en ríos Imperial, Cholchol, Cautín
y Toltén (estero Huilío). Comunas más golpeadas: Temuco, Nueva Imperial, Galvarino,
Pitrufquén, Traiguén, Lumaco, Angol, Victoria, Carahue, Toltén, Teodoro Schmidt.

> Esto da un **evento de validación reciente y bien documentado** para derivar la
> huella SAR y contrastarla contra los puntos críticos de SENAPRED.

---

## 6b. Fuentes sondeadas que NO rinden (para no volver a intentarlas)

Documentarlas ahorra la próxima sesión. Todas fueron verificadas, no descartadas
por suposición.

| Fuente | Qué se esperaba | Qué hay realmente |
|---|---|---|
| **DOH — `doh.mop.gob.cl`** | Los ~50 Planes Maestros de Aguas Lluvias | El sitio es WordPress pero **casi no publica**: su sitemap tiene 33 URLs y el tipo de contenido `document` contiene **1 solo registro** ("Consejo consultivo"). Los PDF de planes maestros existen sueltos bajo `/uploads/sites/8/…` pero no hay índice que los enumere. Habría que descubrirlos por búsqueda web uno a uno. |
| **Centro de Documentación MINVU — `catalogo.minvu.cl`** | Repositorio nacional de planes reguladores | Es un catálogo **bibliotecario** (Koha) con **597 registros** de "plan regulador", incluido el PRC de Padre Las Casas. Describe documentos **físicos**: no adjunta archivos y no expone OAI-PMH. Sirve para saber **qué existe**, no para obtenerlo. |
| **`repositoriodigital.minvu.cl`** | Versión digital del anterior | El dominio **no resuelve** (DNS). |
| **Tienda digital SERNAGEOMIN** | *Geología para el Ordenamiento Territorial: área de Temuco* (2007), que incluye el Mapa 5 de peligros geológicos a 1:100.000 | `tiendadigital.sernageomin.cl` **no resuelve** (DNS). La publicación existe y está citada; hay que conseguirla por otra vía. |
| **GORE Araucanía** | Estudios regionales | Responde **403** a peticiones automatizadas. |
| **SEIA — `seia.sea.gob.cl`** | Estudios de impacto ambiental con anexos de inundación | Responde **500**. Además es enorme y sin filtro por tipo de amenaza; requeriría un proyecto aparte. |

## 6c. Estado de cobertura por comuna (ago-2026)

De las 32 comunas de La Araucanía:

- **20 tienen al menos una lámina cartográfica** localizada.
- **5 tienen documentos pero sin cartografía detectada**: Carahue (2 doc),
  Lautaro (5), Curacautín (3), Renaico (10), Victoria (4).
- **7 no tienen ningún documento**: Cholchol, Loncoche, Melipeuco,
  **Padre Las Casas**, Perquenco, Ercilla, Los Sauces.

> ⚠️ **Padre Las Casas es el vacío más grave**: 76.000 habitantes, 54 puntos
> críticos de inundación y **38 crónicos** —el máximo de la región—, y cero
> documentos. Su sitio no expone API de WordPress ni buscador útil, y su PRC
> **no ha pasado por el registro EAE**: rige desde 1984, de cuando era un barrio
> de Temuco. En marzo de 2025 se anunció que tendrá su primer plan regulador
> propio. Mientras tanto, la única vía sería pedirlo directamente al municipio.

## 7. Referencias secundarias

- ARClim (MMA) — atlas de riesgos climáticos, incluye desbordes de ríos e
  inundaciones urbanas a escala comunal: https://arclim.mma.gob.cl/
- IDE MMA, centro de descargas: https://ide.mma.gob.cl/centro-de-descargas
- Geoportal de Chile (IDE Chile): https://geoportal.cl/geoportal/catalog
- Kimün-Ko (UFRO, Temuco) — plataforma local de alertas hidrometeorológicas;
  el sitio tiene enlaces rotos apuntando a `localhost:1313`, no se pudo leer.
  Contacto potencial en terreno.
- Visor Chile Preparado (SENAPRED): https://www.visorchilepreparado.cl/ —
  app ArcGIS Web AppBuilder, ítem `5062b40cc3e347c8b11fd8b20a639a88`.
  Cubre solo volcánico, tsunami e incendio forestal. Sin inundación.
