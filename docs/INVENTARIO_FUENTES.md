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

**Resultado: 24 planos georreferenciados automáticamente** (`scripts/08_…`), con
RMSE leave-one-out mayoritariamente bajo 0,20 m (20 se publican; 4 resultaron ser
copias exactas del mismo plano):

| Comuna | Planos | RMSE | Resolución |
|---|---:|---|---|
| Vilcún | 5 | 0,02 – 0,09 m | 0,21 m/px |
| Teodoro Schmidt | 6 | 0,15 – 0,20 m | 0,42 m/px |
| Pitrufquén | 4 | 0,03 – 0,04 m | 0,42 m/px |
| Pucón | 4 | 1,31 – 1,81 m | 0,77 m/px |
| Galvarino | 3 | 0,11 m | 0,42 m/px |
| Traiguén | 2 | 0,19 m | 0,42 – 0,51 m/px |

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


## 2b. Los dos repositorios del MOP que faltaban (30-ago-2026) ✅ verificado

**Corrección a §6b.** Ahí se anotó «DOH publica casi nada» tras mirar
`doh.mop.gob.cl`. Era cierto de ese CMS y **falso del MOP**: el acervo vive en
dos repositorios DSpace con API abierta que nadie había interrogado. Es el mismo
error de razonamiento que con Sentinel-1 — se anotó una propiedad del *sitio*
como si fuera del *organismo*.

| Repositorio | API | Acceso |
|---|---|---|
| **«Kimen», DIRPLAN** | `repositoriodirplan.mop.gob.cl/biblioteca/server/api` | abierta, sin credenciales |
| **Catálogo Documental DGA** (SNIA/PIA) | `snia.mop.gob.cl/PIA/server/api` | **403 a curl pelado; 200 con User-Agent de navegador + `Referer: https://snia.mop.gob.cl/PIA/`** |

> **Regla que queda, y ya van tres veces**: un 403 o un 500 no significa
> «cerrado». Antes de anotar una fuente como caída hay que reintentar con
> encabezados de navegador real. Pasó con el GORE, con el SEIA y ahora con la
> DGA.

### El hallazgo que más rinde: SIT N°449 (DGA, 2019)

**Álbum de planos del Sistema de Alerta Temprana de crecidas del Biobío**,
febrero 2019. Ficha:
`repositoriodirplan.mop.gob.cl/biblioteca/items/067efa9d-01d0-4060-abaf-78308fbd20c8`
· PDF de 23,8 MB, verificado leyendo bytes.

La lámina **5432-PLA-012, «Mapa Inundación Subcuenca Ríos Malleco y Vergara»**
(página 13) trae **retícula UTM impresa y rotulada** —150000/175000/200000 E,
5775000–5825000 N—, declara **UTM 19S WGS84** y su leyenda distingue «Zonas de
Riesgo de Inundación» de «Zonas de Riesgo de Inundación Plan Maestro».

### ❌ …y NO sirve. Verificado el 30-ago-2026.

Prometía ser la única cartografía que alcanzara a Ercilla y Los Sauces. Se
vectorizó y **se descartó**. Vale la pena contar cómo se descubrió, porque el
error era convincente:

Se georreferenció **bien**: escala verificada en ambos ejes con 0,09 % de
diferencia, y al superponer los puntos críticos de SENAPRED caen **exactos**
sobre Renaico, Angol, Los Sauces, Collipulli y Ercilla. La posición no era el
problema.

El problema es qué mapea. Las «Zonas de Riesgo de Inundación» que dibuja están
**todas en el corredor del Biobío**, entre Nacimiento y Negrete, fuera de La
Araucanía. Dentro de la subcuenca Malleco–Vergara —el polígono rosado, donde
están todas nuestras comunas— **no hay ni un solo polígono de riesgo**: la
subcuenca aparece como marco de contexto, no como área mapeada.

Las tres comprobaciones, por si alguien quiere rehacerlas:

| Prueba | Resultado |
|---|---|
| Puntos SENAPRED de Malleco a ≤300 m | **0 de 77**; el más cercano a 504 m, la mayoría entre 4 y 16 km |
| Intersección con el modelo GORE 2016 en el mismo marco | **11 ha de 10.887 = 0,1 %** |
| ¿Es un corrimiento? | No: desplazarla hasta 3 km en cualquier dirección no mejora la coincidencia |

> **La lección, y es reutilizable**: el título de una lámina nombra su **marco**,
> no necesariamente lo que mapea. «Mapa Inundación Subcuenca Ríos Malleco y
> Vergara» describe la hoja, no su contenido. Antes de invertir en
> georreferenciar hay que mirar **dónde caen las clases de la leyenda**, no hasta
> dónde llega la hoja.

Queda en `config/laminas.yaml` como bloque comentado con el detalle, para que
nadie la reintente.

⚠️ Otras dos salvedades verificadas: la página **no tiene capa de texto** (0
caracteres, 1.490 trazos vectoriales), así que hubo que rasterizarla —para eso se
agregó el modo `renderizar:` al script 18—; y la leyenda declara como fuente al
**Gobierno Regional del Biobío**, o sea es recopilación, no modelación nueva.

### Plan Maestro de Aguas Lluvias de Angol (2018) — con hidráulica de verdad

`repositoriodirplan.mop.gob.cl/biblioteca/items/ae38d1ec-…` · 14 MB. Es sólo el
**Resumen Ejecutivo**, pero trae caudales de crecida T=2…100 para el Picoiquén y
el Rehue, 92 puntos de inundación, y modelación **SWMM + Iber 2D**.

Eso importa mucho: **es más reciente y con hidráulica** que el Estudio de Riesgo
de 2013 que el proyecto ya vectorizó, que era álgebra de mapas sin caudales. Las
manchas están en el informe final, que **no está publicado** — candidato directo
a solicitud por Ley 20.285.

En La Araucanía sólo existen plan maestro de Angol y el diagnóstico de Villarrica
(2016). **Victoria, Traiguén y Collipulli no tienen.**

### Los PEGH existen y NO sirven para esto

Planes Estratégicos de Gestión Hídrica en Cuencas, descargables sin
credenciales: **Imperial 2021-07** (309 pp) y **Biobío 2021-08** (284 pp). Se
contaron sus figuras: 120 y 187 respectivamente, y **ninguna** lleva
«inundación», «crecida», «amenaza» ni «riesgo» en el título. Queda anotado para
no volver a mirarlos.

### El GORE reparte los expedientes de PRC por Google Drive

Ya **no responde 403** con encabezados de navegador. No publica el PROT ni el
informe metodológico del modelo 2016 —que sigue siendo el pendiente—, pero
reparte los **expedientes completos de Plan Regulador en una carpeta pública de
Google Drive** que incluye las 11 comunas de Malleco:
`drive.google.com/…/1eVpc0vrpnMFJjbgHbzgvC-4_V5yrry2Q`. Verificado bajando el
`Estudio_Riesgo.pdf` de Angol.

**Es la vía para Ercilla y Los Sauces**, que hoy no tienen ningún documento.

### SEIA: se automatiza, y responde

`POST seia.sea.gob.cl/busqueda/buscarProyectoResumenAction.php` con
`selectRegion=9` devuelve **214 expedientes** en las 11 comunas de Malleco. Los
anexos se bajan sin login: por ejemplo el «Anexo 01 Hidráulica» de la extracción
de áridos Piedras Negras, Renaico (expediente 2145188301),
`seia.sea.gob.cl/archivos/2019/12/11/01_Hidraulica.rar`, responde 200.
🔎 Que ese anexo traiga mancha de inundación **no está verificado**: no se abrió.

### Sin hallazgo

- **Tesis**: no hay modelación hidráulica 2D en Malleco. La UdeC tiene hidrología
  del Vergara (2024, 2025) — caudales, no manchas.
  ⚠️ `repositoriodigital.ufro.cl` **ya no existe**; el vivo es `repositorio.ufro.cl`.
- **Servicios OGC**: `ide.mop.gob.cl`, `geoportal.dga.mop.gob.cl` e `ide.cl` no
  exponen GeoServer (404).
- **CDA47 de la DGA** (1986): narra desbordes en Victoria, Traiguén y el camino
  Lumaco–Purén, pero sus planos son de Carahue y Nueva Imperial.

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

### 4.3 ARClim — inundación por desborde de ríos (MMA) ✅ verificado

> Estaba anotado en §7 como «referencia secundaria». Era un error de
> clasificación del mismo tipo que los de §1.2 y §5b: se archivó como atlas
> divulgativo algo que expone una **API pública documentada**. Consumido por
> `scripts/17_arclim_desbordes.py`.

- Vista: https://arclim.mma.gob.cl/atlas/view/desbordes_rios_cbit/
- API: `https://arclim.mma.gob.cl/api/datos/sitios_desbordes/geojson?attributes=…`
  Sin autenticación. ⚠️ La documentación escribe las rutas **con barra final** y
  así devuelven 404; van **sin** barra. El listado de capas es `/api/capas`.
- Los atributos de cada cadena de impacto no salen por API: están en un
  `var config = {…}` embebido en el HTML de la vista.
- Autoría: Ricchetti, Mendoza y Jerez (FCFM, U. de Chile), actualizada en 2022
  por MMA / Naciones Unidas / Centro de Cambio Global UC.

**252 sitios de análisis en centros poblados de Chile, 46 en La Araucanía**,
cubriendo **26 de las 32 comunas**. Cada sitio trae río principal, estaciones
fluviométricas DGA asociadas, e índices de amenaza, exposición, vulnerabilidad y
riesgo para T=25, 50 y 100 años, en presente y proyectado a 2035-2065.

**Por qué vale**: cubre **cinco de las siete comunas que no tienen ni un
documento** —Cholchol, Loncoche, Los Sauces, Melipeuco y **Padre Las Casas**, el
vacío más grave de la región— y las cinco que tenían documentos sin cartografía.
Quedan sin cubrir Curarrehue, Ercilla, Perquenco, Pucón, Purén y Saavedra.

⚠️ **No es una mancha de inundación**: es un punto por localidad con un índice
adimensional. No responde «¿se inunda mi casa?». Capa C, escala de localidad.

⚠️ **El índice de amenaza PRESENTE no mide amenaza.** Verificado sobre los 252
sitios del país: `t25` vale 0,4 en todos, `t50` 0,6 en todos, `t100` 0,8 en
todos. Es una recodificación del período de retorno, constante en el territorio:
no distingue Temuco de Lonquimay. El script **lo excluye de la salida** y se cae
si alguna vez deja de ser constante —porque entonces sí sería un dato útil y
excluirlo en silencio nos haría tirarlo. Lo que sí varía es la amenaza **futura**,
la exposición, la vulnerabilidad y el riesgo.

### 4.4 Elevación 🔎

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

**5.082 ha** de huella observada sobre 17.382 km² mirados. Por órbita: 16,2 km²
(83 desc.), 15,4 (156 desc.) y 26,2 (164 asc.). Tres geometrías, dos plataformas y
dos fechas convergiendo en el mismo orden de magnitud.

Las tres órbitas **se solapan**, así que el total no es su suma —57,8 km²— sino su
unión: 50,8. Las 6,9 km² de diferencia son territorio que la misma agua ocupa en
dos y hasta tres pasadas.

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

## 6a. Fuentes que existen y quedan fuera por decisión (15-nov-2026)

| Fuente | Qué es | Por qué queda fuera |
|---|---|---|
| **GeoIDE MINVU, `Informacion_Regional/Ar_Araucania`** (`https://geoide.minvu.cl/server/rest/services/Informacion_Regional/Ar_Araucania/MapServer`) | Inundación por **tsunami** (inferido: tiempos de arribo en clases de 5 min, velocidades sobre 10 m/s, franja solo litoral; la descripción del servicio está vacía). Tres capas: profundidad (Bajo < 0,5 m, Medio 0,5 a 2 m, Alto > 2 m), tiempos de arribo, velocidad. Anónimo, EPSG:32718. Cubre Carahue, Saavedra, Teodoro Schmidt y Toltén (F-208, F-280). | riesgomapas es fluvial. Decisión de Nicolás del 15-nov-2026: «No por ahora, anotar». Si entra algún día, va como capa aparte (otro fenómeno, REGLAS §1.4), nunca dentro del veredicto fluvial. |

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
| **SEIA — `seia.sea.gob.cl`** | Estudios de impacto ambiental con anexos de inundación | Daba **500** en agosto; al 24-ago-2026 **responde 200**, así que el descarte caducó. Sigue siendo enorme y sin filtro por tipo de amenaza: es un proyecto aparte, no un barrido. |
| **Registro global de ArcGIS Online** | Capas de inundación publicadas y olvidadas por municipios o consultoras, como pasó con la capa del MINVU | Barridas 26 consultas (por texto y por `bbox` de la región; ojo: `bbox` es **parámetro propio**, dentro de `q` devuelve 0 sin error) → 443 ítems, **34 pertinentes y ninguno útil**: son trabajos de estudiantes de INACAP e IPLACEX sobre incendios y volcanes. El ítem «RIESGOS DE INUNDACIÓN» es de un colegio. **No volver a barrer**: si aparece algo institucional será por el org de su servicio, no por el buscador global. |
| **`OSIG_GEOLOGIA_O` (org ArcGIS de SERNAGEOMIN)** | Capa de inundación propia | 47 ítems: hidrogeología, geotermia, geoquímica y peligro volcánico del Villarrica. **Ninguno de inundación** — confirma por segunda vía lo de §2.2. |
| **`sitemap.xml` de los 32 municipios** | Enumerar el sitio entero en vez de rastrear a profundidad 2 | **Cero documentos.** WordPress no lista los adjuntos en el sitemap, sólo entradas y páginas. La API de medios (`/wp-json/wp/v2/media`) sigue siendo la única vía que rinde. |
| **`datos.gob.cl` (CKAN)** | Catálogo nacional de datos abiertos | La API responde 200, pero busca «inundación OR araucanía OR riesgo» y devuelve **2 resultados** en todo el país. El catálogo está prácticamente vacío. |

## 6bis. La misma amenaza bajo tres marcos legales ✅ verificado 24-ago-2026

El hallazgo de método de esta pasada, y el que más rinde a futuro. Un municipio
chileno publica cartografía de la misma amenaza bajo **tres leyes distintas**,
con vocabularios que no comparten ni una palabra:

| Marco | Instrumento | Vigencia |
|---|---|---|
| Ley General de Urbanismo | Estudio Fundado de Riesgos del plan regulador | histórico |
| **Ley 21.364 (2021)** | **Plan Comunal para la Reducción del Riesgo de Desastres**, plan de emergencia comunal | 2024-2026 |
| **Ley 21.455 (2022)** | **Plan de Acción Comunal de Cambio Climático (PACCC)** | 2025-2026 |

El cosechador `12_cosechar_municipios.py` sólo tenía el vocabulario del primero
—`riesgo`, `prc`, `zonificacion`, `estudio fundado`— y **pasaba por encima de los
otros dos sin verlos**. No es que los municipios no publicaran: es que el barrido
no preguntaba por esos nombres.

Al agregar las tres familias aparecieron **40 documentos nuevos** en 11 comunas,
casi todos **posteriores al registro EAE**. El índice de láminas municipales pasó
de 140 a **173 documentos** y de 70 a **80 láminas candidatas**:

- **Curarrehue — el mejor hallazgo.** Su `Decreto-Exento-1802-30-12-2025-Aprueba-PLAN-RRD.pdf`
  trae en p71-73 la **«Zonificación de áreas inundables en la localidad de
  Catripulli»**: susceptibilidad alta y media de inundación, y riesgo alto y
  medio sobre edificaciones, equipamiento y caminos, con los ríos Trancura y
  Cavisañi y el estero Santa Rosa. Tiene **grilla UTM impresa y rotulada**
  (264000-270000 E), así que es georreferenciable con
  `08_georreferenciar_grilla.py`. Procede del levantamiento de riesgos de la
  actualización del PRC — es decir, el estudio del plan regulador **llegó antes
  por la vía del plan de desastres que por la del registro EAE**. Su PACCC
  (Decreto 950, julio-2025) aporta 2 láminas más.
- **Lautaro** — `PLAN-COMUNAL-PARA-LA-RRD-FINAL.pdf` (2024) y plan de emergencia.
  Verificado página a página: es texto y tablas, **sin cartografía**. El escáner
  acertó al no declarar láminas.
- **Collipulli** — PACCC aprobado por Decreto N°1752 de julio-2025, más
  `15.-y-16.-Mapa-de-Vulnerabilidad-fusionado.pdf`: dos láminas **A3 con grilla
  UTM SIRGAS 18S impresa y rotulada**, georreferenciables con
  `08_georreferenciar_grilla.py`. Contenido: índice de vulnerabilidad social
  SoVI 2017 y catastro de campamentos 2022-2023 — **no es amenaza de
  inundación**, sirve como exposición.
- **Lonquimay** — Plan de Cambio Climático comunal, junio-2025, con lámina.
- **Renaico** — el PLADECO trae 2 láminas y saca a la comuna de la lista de «sin
  cartografía». **Villarrica** y **Lonquimay** también ganan cartografía.
- **Saavedra** — dos planes de emergencia comunal y el PLADECO.
- PLADECO recientes de Purén, Freire, Temuco, Villarrica y Collipulli.

> **La lección que queda**: el estudio de riesgo de una comuna puede llegar antes
> por el plan de desastres o por el de cambio climático que por el registro
> ambiental, porque esos instrumentos **citan y reproducen** el levantamiento del
> plan regulador mientras el expediente EAE todavía está en trámite. Buscar por
> un solo marco legal deja fuera la copia más accesible del mismo mapa.

⚠️ **Punto ciego del escáner de láminas, confirmado.** `07_buscar_laminas_riesgo.py`
exige vocabulario hídrico **en la capa de texto** de la página. La lámina de
Collipulli es un PDF aparte, de 2 páginas, con el texto convertido a trazos: cero
caracteres extraíbles. El escáner no la ve, y es justo el formato más valioso —la
cartografía de verdad, en tamaño de plano. Una lámina publicada como PDF separado
sin capa de texto es invisible para el índice.

⚠️ **Ruido propio de este vocabulario.** «emergencia», «adaptación» y
«vulnerabilidad» traen compras de vehículos, bases de concurso para jefaturas de
protección civil y el Ingreso Familiar de Emergencia. Se descartan por nombre en
`RUIDO_NOMBRE` antes de gastar la descarga.

## 6c. Estado de cobertura por comuna (24-ago-2026)

De las 32 comunas de La Araucanía:

- **21 tienen al menos una lámina cartográfica** localizada (Renaico se sumó al
  agregar el vocabulario de §6bis).
- **4 tienen documentos pero sin cartografía detectada**: Carahue (2 doc),
  Lautaro (7, incluido su plan de RRD — verificado sin mapas), Curacautín (3),
  Victoria (4).
- **7 no tienen ningún documento**: Cholchol, Loncoche, Melipeuco,
  **Padre Las Casas**, Perquenco, Ercilla, Los Sauces.
  De ésas, **ARClim (§4.3) cubre cinco** con un sitio de desborde de río:
  Cholchol, Loncoche, Los Sauces, Melipeuco y **Padre Las Casas**. Siguen sin
  ninguna fuente **Ercilla y Perquenco**.

> ⚠️ **Padre Las Casas es el vacío más grave**: 76.000 habitantes, 54 puntos
> críticos de inundación y **38 crónicos** —el máximo de la región—, y cero
> documentos. Su sitio no expone API de WordPress ni buscador útil, y su PRC
> **no ha pasado por el registro EAE**: rige desde 1984, de cuando era un barrio
> de Temuco. En marzo de 2025 se anunció que tendrá su primer plan regulador
> propio. Mientras tanto, la única vía sería pedirlo directamente al municipio.

## 7. Referencias secundarias

- ~~ARClim (MMA)~~ → **promovido a §4.3**: no era una referencia secundaria, tiene
  API pública y ya está consumido. Quedan sin explotar sus otras dos cadenas de
  impacto de inundación: `asentamientos_inundaciones` e `inundaciones_urbanas`
  (esta última **fuera del alcance** del proyecto, que es inundación fluvial).
- IDE MMA, centro de descargas: https://ide.mma.gob.cl/centro-de-descargas
- Geoportal de Chile (IDE Chile): https://geoportal.cl/geoportal/catalog
- Kimün-Ko (UFRO, Temuco) — plataforma local de alertas hidrometeorológicas;
  el sitio tiene enlaces rotos apuntando a `localhost:1313`, no se pudo leer.
  Contacto potencial en terreno.
- Visor Chile Preparado (SENAPRED): https://www.visorchilepreparado.cl/ —
  app ArcGIS Web AppBuilder, ítem `5062b40cc3e347c8b11fd8b20a639a88`.
  Cubre solo volcánico, tsunami e incendio forestal. Sin inundación.
