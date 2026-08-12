# Práctica profesional — curaduría y contraste geomorfológico de las áreas de riesgo por inundación

> Propuesta de plan para **CITI-295 Práctica Profesional (a)**, Geología, Instituto
> de Ciencias de la Tierra, Universidad Austral de Chile. Institución de acogida:
> **Fundación Pewenkem**. Duración: 20 días, >160 h de trabajo autónomo.
>
> Estado: **propuesta**. Las fuentes están verificadas (§5); el reparto de días es
> una estimación y hay que ajustarla al estudiante real.

---

## 1. El eje de la práctica, y por qué no es una cuestión de reglamento

Surgió temprano la duda de si esto es geología o geografía. Conviene separar dos
cosas que se confunden.

**Lo primero es factual: el programa no restringe el ámbito, y premia lo
contrario.** El perfil de egreso incluye textualmente *«participar proactivamente
en la organización de trabajo en equipo inter y multidisciplinario»*; el objetivo
declarado de la asignatura es *«introducir al estudiante en su futura vida
laboral»*; y entre los seis criterios que evalúa el supervisor está,
literalmente, **«versatilidad»**. Una práctica de planificación territorial no
sólo es admisible: es de las que el instrumento de evaluación recompensa. Y el
argumento de fondo es correcto —el mundo laboral pide profesionales que crucen la
frontera de la geología dura, y esta práctica es exactamente ese cruce.

**Lo segundo no es de reglamento sino de formato.** La defensa son **3 minutos de
exposición y 5 de preguntas**. En ese formato no se defiende un inventario: se
defiende una afirmación. Por eso conviene que el estudiante tenga **una pregunta
propia**, con método y resultado, y que esa pregunta sea de su disciplina — no
para cumplir una norma, sino para tener algo que sostener cuando la comisión
pregunte. Todo lo demás —curaduría, población, manual— es el trabajo que le da
valor a la fundación y al visor, y no compite con eso.

La pregunta propuesta:

> **¿El polígono que el plan regulador declara como «área de riesgo por
> inundación» corresponde a la llanura de inundación real del río? ¿Y esa
> correspondencia mejora en los instrumentos más nuevos?**

La segunda mitad es la que la convierte en investigación. Formulada como hipótesis:

> **H — La concordancia entre el área de riesgo declarada y la llanura de
> inundación geomorfológica mejora con la modernidad del instrumento.**

Es razonable esperar que los planes recientes incorporen estudios de riesgo con
base geológica y los antiguos no, y hay **59 años de rango** para ponerlo a
prueba: de Puerto Saavedra (1964) a Renaico (2023). Lo importante es que la
hipótesis **se puede perder**: si se cumple, el resultado es que el sistema mejora
y hay que acelerar las actualizaciones; si no se cumple, es un resultado distinto
e igual de publicable. Un estudiante que puede perder su hipótesis está
investigando, no llenando una plantilla.

Por qué la pregunta tiene sentido: miren cualquier plano de área de riesgo
antiguo. Las zonas inundables son **cintas de
ancho aproximadamente constante siguiendo los cauces**. Eso no es la salida de una
modelación hidráulica: es un **retiro de faja**, una distancia fijada por norma. La
llanura de inundación real, en cambio, es una **forma del terreno**: la construyó
el propio río depositando sedimento, y se reconoce por su morfología —terrazas,
paleocauces, meandros abandonados, quiebres de pendiente— y por su posición
topográfica respecto del cauce actual.

Comparar una cosa con la otra es geomorfología fluvial aplicada. Y tiene
consecuencia directa: donde la faja normativa es más angosta que la llanura, hay
terreno que se inunda y que el instrumento no declara.

⚠️ Y una prevención contra la conclusión fácil: **no todos los planes son fajas**.
Es esperable que los más recientes vengan de un estudio de riesgos con base
geológica. Salir a demostrar que «los planes están mal» sería confirmar un
prejuicio; la gracia del diseño es que la vejez del instrumento es una **variable
que se mide**, no un supuesto.

---

## 1b. ¿Desde cero, o desde lo ya construido?

La pregunta es real: se le está entregando mucho hecho —catálogos, descargas, la
huella satelital, los planos georreferenciados— y hay dos formas de arruinar la
práctica con eso.

**Partir de cero la desperdicia.** Veinte días rehaciendo lo que ya existe produce
una versión peor de algo que ya está, y ningún resultado nuevo.

**Heredarlo todo lo convierte en alguien que aprieta botones.** En los 5 minutos de
preguntas de la comisión, eso se nota de inmediato.

La regla intermedia:

> **Reconstruye desde cero exactamente una pieza: aquella de la que depende su
> conclusión. Hereda todo lo demás.**

Su afirmación es sobre la llanura geomorfológica frente al polígono normativo.
Entonces eso lo hace él: para al menos una comuna, **dibuja las terrazas, los
paleocauces y el quiebre de la llanura sobre el modelo de sombras ANTES de ver el
HAND calculado**, y recién después compara su interpretación con el resultado
automático. Si coinciden, aprendió que su criterio sirve. Si no coinciden, tiene
que averiguar cuál de los dos está equivocado — y ésa es la mejor pregunta que le
puede tocar.

Dos mecanismos que conviene agregar:

1. **Día 0 de reproducción** (media jornada). Correr un script del proyecto de punta
   a punta y **verificar un número ya publicado**. Si lo reproduce, entendió el
   pipeline. Si no lo reproduce, encontró un problema nuestro, y eso vale más que
   cualquier tarea asignada.
2. **Todo dato heredado se verifica en al menos un número.** Es la cultura del
   proyecto, y le da criterio propio en vez de confianza ciega.

Y un argumento que sirve para su informe: **en un trabajo nadie parte de cero.** El
informe le pide relacionar lo hecho con *«el rol del geólogo profesional»*. Llegar a
un proyecto andando, entenderlo, encontrarle errores y agregarle una pieza es
exactamente lo que hace un geólogo junior en su primer empleo — una simulación más
honesta que un ejercicio de laboratorio.

⚠️ Condición única: **el informe debe distinguir explícitamente qué recibió y qué
hizo él.** Eso también es práctica profesional.

---

## 2. Lo que NO debe hacer, y por qué

Esto importa tanto como la lista de tareas. Son 160 horas: lo que se hace mal
cuesta el doble, porque además desplaza a lo que sí valía.

**No georreferenciar planos de instrumentos ya aprobados.** Sus áreas de riesgo
existen en vectorial abierto en el servicio nacional de MINVU, y hay 24 planos ya
georreferenciados con error bajo 2 m. Rehacerlos sería reconstruir a mano un dato
que se descarga.

⚠️ **Pero sí georreferenciar los planos que no tienen equivalente vectorial** — y
ésa es una tarea de producción, no un ejercicio. Ver §3.2b: son 15 comunas.

**No pedir los polígonos a CIGIDEN.** La intuición era razonable —si publicaron el
Atlas, deben tener los archivos— pero la verificación la desmiente: sus polígonos
salen de las mismas áreas de riesgo de MINVU que ya tenemos. Sí vale escribirles,
pero por otra cosa (§4).

**No hacer proyecciones de inundación.** Requiere modelación hidrológica e
hidráulica, forzantes climáticas y calibración. No es defendible en 20 días sin
formación en hidráulica, y un resultado mal hecho sobre dónde se inunda una ciudad
es peor que no tener resultado. Lo que sí se puede: **usar** los períodos de
retorno del JRC que ya están cargados, como término de comparación, declarando su
resolución de ~1 km.

**No depender de una solicitud por Ley de Transparencia.** Puede presentarla —y
conviene que aprenda a hacerlo— pero el plazo legal de respuesta es de **20 días
hábiles, prorrogable por 10 más**. Una solicitud ingresada el día 1 vence **después**
de que termine la práctica. Se ingresa como legado para el proyecto, jamás como
insumo de su informe.

**No usar el Mapa Geológico de Chile como capa de comparación.** Tiene 564
polígonos en toda la región: es 1:1.000.000 y el área de riesgo se dibuja a
1:5.000. La llanura se deriva del DEM.

---

## 3. El plan, en cinco bloques

Estimación sobre 20 días de 8 h. Los productos están amarrados desde el día 1 a
los dos entregables que evalúa la asignatura: **informe de ≤10 páginas** y
**presentación oral de 3 minutos**.

**El plan está lleno, y hay que decirlo.** Cinco bloques en 20 días no dejan
holgura, y la georreferenciación (§3.2b) es la actividad de duración menos
predecible: depende de si cada retícula es texto vectorial o dibujo, y eso no se
sabe hasta correrla. Orden de sacrificio acordado de antemano, para no improvisar
bajo presión el día 15:

1. **Nunca se recorta**: el informe, la charla y el bloque C. Son la evaluación y
   son la geología.
2. **Se recorta primero** el cruce con población (§3.4.1). Es valioso para el visor
   pero es el que menos aporta a su defensa.
3. **Se acota** el bloque B2 a 3 o 4 planos bien hechos con su RMSE declarado. Diez
   planos mal ubicados valen menos que tres correctos.
4. El manual (§3.4.2) puede quedar en borrador y terminarse después de la práctica.

### 3.1 Bloque A — Curaduría (días 1 a 4)

El trabajo que resuelve la queja concreta: *los mapas no se entienden y están
mezclados con polígonos que no son de inundación*. Y no es impresión: en la capa
regional conviven 48 polígonos de inundación con 52 de remoción en masa, 8 de
quebradas, 3 de canales y hasta **uno de resguardo de línea de alta tensión**.

1. **Separar por tipo de amenaza.** Existe el campo `es_inundacion`, pero la
   clasificación de origen tiene 12 formas distintas de decir lo mismo. Construir
   una **tabla de homologación** explícita, documentada, con una fila por valor
   original. El Atlas de CIGIDEN encontró **102 nombres distintos de área de
   inundación a escala nacional** (y 53 de remoción en masa): la tabla es el
   activo, no el subproducto. Están en las **notas al pie 16 y 17, páginas 22-24**
   del PDF, y son texto extraíble. ⚠️ Trampa verificada: los nombres se separan con
   `;` pero varios contienen `;` internos, así que un corte ingenuo da 111 y no 102.
   El Atlas los homologa a las categorías del **art. 2.1.17 de la OGUC**, de las
   cuales reporta tres con contenido —inundables (72 áreas, 239.797 ha), avalanchas
   y aluviones (48, 22.108 ha), actividad humana (9, 12.197 ha)— y una **vacía en
   todo el país**: la volcánica. La leyenda de sus mapas muestra además incendio
   forestal, que no es categoría de la OGUC.
2. **Resolver la discrepancia de Angol.** El Atlas mapea Angol (PRC 2022) con
   zonas inundables extensas; nuestra capa no tiene **ni un polígono** de Angol.
   Al revés, nosotros tenemos Loncoche, Nueva Imperial y Pucón que el Atlas no
   lista. Alguien está incompleto. Resolverlo consultando el servicio de MINVU y
   la ordenanza vigente. **Es la primera victoria del estudiante y llega el día 2.**
3. **Corregir errores de dato heredados de la fuente**, empezando por la comuna que
   viene escrita `Pitufquén` (falta la r). Cada corrección se registra; no se
   edita el dato crudo.

> Producto: capa de inundación curada + `homologacion_areas_riesgo.csv` + registro
> de correcciones.

### 3.2 Bloque B — Caracterización de los instrumentos (días 5 a 6)

Aquí entra la idea del *instrumento de caracterización*: medir la profundidad y la
vigencia de lo que cada comuna declara.

Una ficha por comuna con, como mínimo: año del instrumento vigente, antigüedad,
número y tipo de áreas de riesgo, si la memoria incluye Estudio de Riesgos, escala
de la cartografía, si declara metodología, si declara período de retorno, y si
existe enlace a la ordenanza.

Buena parte del insumo ya está: **354 documentos y 224 láminas catalogadas** con
enlace a la página exacta del PDF, y el índice de 5.991 documentos del registro
EAE. El estudiante lee y caracteriza; no tiene que salir a buscar.

El año lo aporta el Atlas de CIGIDEN, y es un dato que hoy **no tenemos**: nuestro
campo `anio` dice *«no declarado por la fuente»* en los 124 polígonos.

| Comuna | Año | Antigüedad |
|---|---:|---:|
| Puerto Saavedra | **1964** | **62 años** |
| Pitrufquén | 1984 | 42 |
| Carahue | 1989 | 37 |
| Traiguén | 1991 | 35 |
| Villarrica | 1992 | 34 |
| Collipulli | 2009 | 17 |
| Temuco | 2010 | 16 |
| Gorbea · Toltén | 2012 | 14 |
| Angol | 2022 | 4 |
| Renaico | 2023 | 3 |

Puerto Saavedra ordena su territorio con un instrumento de **1964**: la
reconstrucción posterior al terremoto y tsunami de 1960. Ese solo dato sostiene una
diapositiva.

#### El cementerio de instrumentos: lo que se estudió y nunca fue norma

Un plan regulador puede quedar sin aprobarse por razones políticas, comerciales o
administrativas, y su expediente **queda público igual**. Eso significa que puede
existir un estudio de riesgos moderno, con base geológica, **sin ninguna fuerza
legal**, mientras rige un plan mucho más antiguo.

No es hipotético. De los 30 procedimientos de La Araucanía en el registro EAE,
**cinco terminaron en «Resolución de Desistimiento o Abandono»**:

| Instrumento | Ingreso | Documentos en el expediente |
|---|---|---:|
| **PRC Temuco** | 08-09-2017 | 7 |
| PRC Collipulli | 30-08-2016 | **16** |
| PRC Victoria | 16-06-2015 | 8 |
| PRC Lonquimay (zona vivienda alta densidad) | 23-10-2015 | 3 |
| PRC Temuco – Terreno Amanecer | 13-08-2015 | 3 |

**Temuco es el caso que ordena el argumento.** La capital regional inició la
actualización de su plan en 2017, el proceso se abandonó, y sigue rigiendo el
instrumento de 2010. Collipulli —cuyos 66 polígonos son más de la mitad de la capa
regional— dejó 16 documentos de un proceso de 2016 que murió.

Esto abre la comparación más limpia de toda la práctica, y es **prueba directa de
la hipótesis H**: contrastar el estudio de riesgos del expediente abandonado de
Temuco (2017) contra el área de riesgo que efectivamente rige (2010) y contra la
llanura geomorfológica. Si el estudio abandonado se parece más a la llanura real
que la norma vigente, queda demostrado —para un caso— que **el conocimiento existía
y no llegó a ser norma**. Es una variante del «caso B» más incómoda que la
habitual: no es que nadie lo estudiara, es que el estudio no prosperó.

Tarea concreta: para los cinco expedientes, revisar los documentos ya descargados y
determinar si contienen Estudio de Riesgos y cartografía de amenaza. El catálogo ya
tiene el enlace a la página exacta de cada lámina.

> Producto: `caracterizacion_ipt_araucania.csv` + figura de antigüedad por comuna +
> ficha de los cinco instrumentos abandonados. Responde *«qué tan desactualizados
> están los mapas»*, y algo más: **por qué lo están**.

### 3.2b Bloque B2 — Georreferenciar lo que nunca fue vectorial (días 7 a 9)

Aquí se corrige la regla anterior. MINVU publica las áreas de riesgo de los
instrumentos **vigentes**; un plan que no se aprobó no aparece ahí y **no va a
aparecer nunca**. Su cartografía existe sólo como PDF dentro del expediente. Ésos
son los planos que vale la pena georreferenciar, porque el trabajo no duplica nada:
crea el único vectorial que va a existir de ese territorio.

El cruce entre el registro EAE y la capa de MINVU da la lista de objetivos:
**17 de los 30 procedimientos de la región están en comunas sin ningún vectorial de
áreas de riesgo, y 15 de ellos ya tienen láminas localizadas** por el escáner de
PDF, con enlace a la página exacta.

| Comuna | Estado del procedimiento | Docs | Láminas ubicadas |
|---|---|---:|---:|
| **Teodoro Schmidt** | Informe Ambiental Complementario | 21 | **37** |
| Vilcún | Informe Ambiental Complementario | 18 | 14 |
| Curarrehue | Inicio EAE | 3 | 14 |
| Angol | Aprobación del Instrumento ⚠️ | 8 | 11 |
| **Galvarino** | Cuarto Informe Ambiental, desde **2013** | 22 | 10 |
| Purén | Informe Ambiental Corregido | 22 | 9 |
| Saavedra | Tercer Informe Ambiental | 12 | 8 |
| Lonquimay | Complementario (+ otro abandonado) | 21 | 7 |
| Cunco · Freire · Lumaco | Término de EAE / Segundo Informe | 27/15/7 | 2 c/u |
| Curacautín · Victoria | Inicio EAE / Abandono | 9/8 | 0 |

**Galvarino es el caso que enseña.** Su PRC entró a evaluación el **24-07-2013** y
trece años después sigue en «Cuarto Informe Ambiental», con 22 documentos. La
comuna **no tiene ni un polígono** en MINVU. Y sin embargo **ya tenemos tres
versiones de su plano georreferenciadas** — sirve como ejemplo resuelto para
enseñarle el método antes de que ataque los que faltan.

⚠️ **Angol obliga a corregir algo nuestro.** Es el único procedimiento de la región
con «Resolución de Aprobación del Instrumento», coincide con el PRC 2022 que lista
el Atlas… y tampoco tiene polígonos en la capa nacional de MINVU. La conclusión no
es que el Atlas se equivoque: es que **el vectorial de MINVU va por detrás de las
aprobaciones**. Para un visor que se presenta como fuente, eso hay que declararlo.

Método: correr `08_georreferenciar_grilla.py` sobre las láminas de los objetivos.
Donde la retícula UTM sea texto vectorial, el plano se ubica solo. Donde esté
rasterizada —le pasó a 25 planos— el automático falla y hay que poner puntos de
control a mano en QGIS, que es donde aprende la técnica de verdad. **Cada plano
lleva su RMSE leave-one-out y su clasificación de aptitud**: un plano mal ubicado
publicado como bueno es peor que no tenerlo.

> Producto: N planos nuevos georreferenciados, con RMSE declarado, y las áreas de
> riesgo de instrumentos no aprobados digitalizadas donde la calidad lo permita.
> **Es dato que hoy no existe en ninguna parte.**

---

### 3.2c Qué permite realmente el área de riesgo, y quién construye ahí

Media jornada de lectura normativa que cambia el sentido de todo el resto, y que
conviene hacer **antes** del bloque C.

**Un área de riesgo no prohíbe construir. Condiciona.** El texto de la OGUC es
explícito, y la diferencia con las «zonas no edificables» es de régimen jurídico:

> *«Por "áreas de riesgo", se entenderán aquellos territorios en los cuales, previo
> estudio fundado, se limite determinado tipo de construcciones por razones de
> seguridad contra desastres naturales u otros semejantes, **que requieran para su
> utilización la incorporación de obras de ingeniería o de otra índole suficientes
> para subsanar o mitigar tales efectos**. Para autorizar proyectos a emplazarse en
> áreas de riesgo, se requerirá que se acompañe a la respectiva solicitud de permiso
> de edificación **un estudio fundado, elaborado por profesional especialista** y
> aprobado por el organismo competente, que determine las acciones que deberán
> ejecutarse para su utilización […] Este tipo de proyectos **podrá recibirse** parcial
> o totalmente en la medida que se hubieren ejecutado las acciones indicadas.»*
> — OGUC art. 2.1.17 ✅ verificado contra el texto vigente

Tres consecuencias que hay que sacar y decir:

1. **«Estás en área de riesgo» ≠ «no se puede construir».** Se puede, con estudio de
   un especialista y ejecutando obras de mitigación. Si el visor deja entender lo
   contrario, está informando mal. Las **«zonas no edificables»** sí son
   prohibición —«no son susceptibles de edificación», sólo actividades
   transitorias— y son otra cosa: fajas de protección de infraestructura peligrosa,
   torres de alta tensión, embalses.
   👉 Esto obliga a refinar el bloque A: hoy nuestra capa **mezcla los dos
   regímenes** (ahí está el «ZR-6 Área de Resguardo Línea de Alta Tensión»). No es
   un problema de prolijidad: son estatutos jurídicos distintos.
2. **El «profesional especialista» que firma ese estudio es el oficio del
   estudiante.** En inundación es un geólogo o un ingeniero hidráulico. La práctica
   deja de ser una mirada externa al sistema: le muestra el puesto que va a ocupar
   dentro de él.
3. **Un plan comunal puede reducir el área de riesgo.** La OGUC 2.1.7 N°2 h)
   permite que, «mediante estudios de mayor detalle, los planes reguladores
   comunales **precisen o disminuyan**» las áreas de riesgo intercomunales. Existe
   entonces un mecanismo legal para achicar la zona de restricción con un estudio,
   y verificar si se ha usado en la región es una pregunta legítima.

**Y la pregunta que se abre: ¿quién está construyendo o vendiendo ahí?** Con el
régimen entendido, el cruce se puede leer bien. Las fuentes ya están levantadas en
el proyecto hermano `exposicion/`:

| Fuente | Qué aporta | Estado |
|---|---|---|
| SEIA, punto representativo | 30.193 proyectos con fecha de presentación y de calificación | ✅ |
| Permisos de edificación INE | 163.487 permisos como puntos + 18.272 recepciones | ✅ |
| Límite urbano `LU_IPT_CHILE` | separa lo que el PRC alcanza de lo que no | ✅ |
| Subdivisiones DL 3.516 (loteos) del SAG | KML + rol + fecha… **no se publica** | ❌ vía Ley 20.285 |

Lo interesante no es sólo *cuántos* proyectos caen dentro, sino **si son
posteriores al instrumento que declara el riesgo**: eso distingue al que construyó
antes de que existiera la norma del que lo hizo después. Y si un proyecto está
dentro de un área de riesgo, por ley **debe existir un estudio fundado** — cuya
existencia es preguntable a la Dirección de Obras.

⚠️ Límite ético heredado de `exposicion/`, y no se negocia: **predio sí, persona
nunca**. Cifras agregadas por comuna y por año, sin nombres de titulares,
propietarios ni vendedores, y **ninguna afirmación de ilegalidad**: construir ahí
con el estudio correspondiente **es legal**, y ése es justamente el punto.

> Producto: media página del informe con el régimen explicado en lenguaje llano, y
> una tabla de proyectos y permisos dentro de áreas de riesgo por inundación,
> agregada por comuna y por año.

---

### 3.3 Bloque C — El núcleo geológico (días 10 a 14)

Cuatro comunas piloto, elegidas por contraste: **Temuco** (la mayor población),
**Carahue** (instrumento de 1989 sobre el río Imperial), **Collipulli** (66
polígonos, el más denso) y **Angol** (instrumento nuevo, 2022 — permite preguntar
si un plan reciente lo hace mejor).

Para cada una:

1. **Derivar la llanura de inundación geomorfológica** del DEM Copernicus GLO-30
   mediante altura sobre el cauce más próximo (HAND). El pipeline ya descarga y
   mosaica el DEM y calcula pendiente; hay que agregar el encauzamiento. **Esto se
   lo dejamos preparado**: el estudiante interpreta, no programa.
2. **Interpretar geomorfológicamente**: identificar sobre el modelo de sombras y
   los perfiles topográficos las terrazas fluviales, los paleocauces y los
   meandros abandonados. Esto es lectura de formas, y es su oficio.
3. **Contrastar cinco capas** de naturaleza epistémica distinta sobre el mismo
   territorio, sin fusionarlas nunca: faja normativa del PRC · llanura
   geomorfológica HAND · **modelo del GORE 2016 a 35 m** (§5b) · **huella observada
   por Sentinel-1** del temporal del 30-jul al 4-ago-2026 · puntos críticos de
   SENAPRED. Que digan cosas distintas **no es un problema a resolver promediando**:
   es el resultado.
4. **Medir dos números por comuna**: qué fracción de la llanura geomorfológica está
   cubierta por el área de riesgo declarada, y qué fracción del área declarada cae
   fuera de la llanura. Los dos errores tienen significados opuestos y hay que
   reportarlos por separado, nunca sumados.

> Producto: cuatro láminas comparativas + tabla de concordancia. Es el corazón del
> informe y de la charla.

### 3.4 Bloque D — Exposición y cierre (días 15 a 20)

1. **Cruce con población (Censo 2024).** Verificado consultando el servicio, con
   filtro `COD_REGION=9`:

   | Capa | Polígonos en R09 | Personas |
   |---|---:|---:|
   | Manzanas (urbano) | 12.886 | 691.173 |
   | Manzanas-entidades (rural) | 4.188 | 312.373 |
   | Aldeas | 33 | 17.887 |
   | **Unión de las tres** | **17.107** | **1.021.433** |

   Las tres capas son partición exhaustiva y el total cuadra con la población
   regional. Traen ~200 variables. La pregunta que cierra el argumento:
   **cuántas personas viven dentro de la llanura geomorfológica pero fuera del área
   de riesgo declarada** — es decir, en terreno inundable que el instrumento no
   reconoce.
   Variables que conviene mirar más allá del conteo, porque hablan de
   vulnerabilidad y no sólo de exposición: `n_viv_hacinadas`,
   `n_mat_paredes_precarios`, `n_hog_60`, `n_discapacidad`, `n_fuente_agua_rio`.
   ⚠️ Tres advertencias verificadas, y las tres cuestan medio día si se descubren
   tarde:
   - **Reproyectar a UTM (EPSG:32718/32719) antes de medir superficie intersectada.**
     Calcular áreas en grados no da un número con sentido. Es un error que este
     workspace ya cometió una vez.
   - El servicio del Censo 2024 es un **espejo de Esri Chile**, no un servidor
     `ine.gob.cl`. Atribuye al INE, pero conviene contrastar un par de totales
     comunales contra la publicación oficial antes de publicar nada.
   - Si se usa el Censo 2017 del servidor propio del INE, hay una **trampa de
     esquema**: el campo de región es texto, así que `REGION=9` devuelve **cero
     filas** sin error. Hay que consultar `REGION LIKE '%RAUCAN%'`. Cero filas sin
     mensaje de error es el modo de falla más peligroso de todos.

   Y la regla que no se negocia: **agregado por manzana, nunca por persona**, sin
   cruzar variables hasta un nivel que permita identificar a alguien.
2. **Manual de fuentes** (días 16-17). Guía pública y breve —10 páginas— de dónde
   está cada cosa y cómo pedir lo que no está: MINVU, registro EAE, SENAPRED,
   INE, sitios municipales, y cómo se presenta una solicitud por Ley 20.285 con
   sus plazos reales. Buena parte se puede destilar del inventario de fuentes ya
   escrito. **Es el producto más reutilizable y el que puede publicar la fundación.**
3. **Informe y charla** (días 18-20). El informe no supera 10 páginas por
   reglamento. La charla son **3 minutos**: alcanza para una pregunta, un método y
   un número. Conviene ensayarla cronometrada más de una vez.

---

## 4. Qué pedirle a CIGIDEN, y qué no

No hay que pedirles polígonos: su fuente es la misma nuestra. Sí vale escribir a
Magdalena Vicuña y Simón Guzmán (los correos están en la página de créditos del
Atlas) por dos cosas concretas:

- **El crosswalk nombre original ↔ polígono.** La lista de los 102 nombres está
  en el PDF, y sus servicios publican el campo de categoría OGUC, pero **el vínculo
  entre cada polígono y su denominación original se perdió al publicar**: el campo
  `Capa` trae el nombre del plan, no el del área de riesgo. Ese cruce es
  exactamente lo que no se puede reconstruir desde fuera.
- **Contraste de la discrepancia de Angol**, que es una observación útil para
  ellos, no sólo una petición nuestra.

Un correo que aporta un hallazgo se responde mucho más que uno que sólo pide.

---

## 5. Fuentes verificadas

Comprobadas leyendo el servicio, no el catálogo.

| Fuente | Estado | Detalle |
|---|---|---|
| Áreas de riesgo IPT (MINVU) | ✅ | 124 polígonos en la región, 63 hídricos |
| Censo 2024 por manzana | ✅ | 17.107 unidades en R09, 1.021.433 personas, ~200 variables |
| Censo 2017 por manzana (INE) | ✅ | 9.224 manzanas + 4.166 entidades, ojo con `REGION` texto |
| DEM Copernicus GLO-30 | ✅ | anónimo, ya integrado al pipeline |
| Huella Sentinel-1 (capa B) | ✅ | 5.776 ha, evento ago-2026, 3 órbitas |
| Puntos críticos SENAPRED | ✅ | 992 hídricos en la región |
| Catálogo EAE + municipios | ✅ | 354 documentos, 224 láminas localizadas |
| **Riesgo de inundación GORE Araucanía 2016** | ✅ | **7.203 polígonos, ~35 m** — ver §5b |
| Riesgo de anegamiento / remoción / volcánico GORE | ✅ | 4.491 / 10.108 / 240 polígonos |
| Áreas de riesgo IPT de CIGIDEN | ✅ | 3.402 polígonos nacionales, sólo consulta (§5b) |
| Mapa Geológico de Chile | ⚠️ | **1:1.000.000** — sólo contexto regional (§3) |
| Cartas geológicas 1:100.000 | ❓ | **sin verificar** — establecerlo es tarea del bloque C |

Los dos ❓ están declarados a propósito: no comprometemos la práctica de una
persona sobre un supuesto.

### 5b. El hallazgo que reordena el plan: existe un modelo regional a 35 m

Buscando los datos del Atlas apareció otra cosa, y es mejor. CIGIDEN **republica**
en su organización de ArcGIS cuatro capas regionales que **no son suyas**:

> *«Cobertura del riesgo de inundación para la Región de la Araucanía. Fecha de
> elaboración: 2 de mayo de 2016. Información adicional: Informe Componente
> Amenazas Naturales para la elaboración del **Plan Regional de Ordenamiento
> Territorial**. Fuente: **Gobierno Regional de la Araucanía**.»*

Es decir: **el Gobierno Regional modeló la amenaza de inundación de toda la región
en 2016** para su PROT, y ese modelo está público.

Qué es, técnicamente. Los campos `gridcode`, `count_` y `max_gridco` son la firma
de un **ráster clasificado convertido a polígonos**; del área y el conteo de celdas
se deduce un píxel de **~35 m**. Las clases son ordinales —`NULA` 1.963, `MINIMA`
3.845, `MEDIA` 943 polígonos— y cubren la región completa (3,16 millones de ha).

**Lo verificamos contra SENAPRED**, que no participó en su elaboración:

| | dentro de la clase MEDIA |
|---|---:|
| Puntos críticos hídricos de SENAPRED | 142 de 992 (**14,3 %**) |
| Puntos al azar en la misma envolvente | 205 de 8.000 (2,6 %) |

**Enriquecimiento ×5,6.** El modelo tiene habilidad real: no es ruido.

Y tiene dos límites que hay que declarar siempre. Primero, **las clases no
significan nada físico**: «MEDIA» no corresponde a ningún período de retorno, a
diferencia del JRC, que sí dice «100 años». Más resolución, menos
interpretabilidad — y es un canje que conviene que el estudiante entienda, porque
se repite en toda la geología aplicada. Segundo, **no declara licencia**, así que
antes de publicarlo en el visor hay que preguntar al GORE.

Esto le da al bloque C una quinta capa y una pregunta mucho mejor:

> El Gobierno Regional modeló esta amenaza en **2016**, a 35 m y con validación
> independiente. **¿Cuántos planes reguladores de la región la recogieron?**

Con los años del §4.2 la pregunta se responde: Angol (2022) y Renaico (2023) son
**posteriores** al modelo; los otros nueve son anteriores. Es exactamente la
distinción entre desfase no imputable y brecha señalable.

**Cómo se descarga.** Los servicios tienen `capabilities = Query` **sin `Extract`**:
no hay botón de descarga, pero la API sí entrega geometría con
`f=geojson&outSR=4326`, paginando con `resultOffset` y cortando por
`exceededTransferLimit`. Es el mismo patrón ya resuelto en `scripts/comun.py`.

---

## 5c. Cuánto cuesta dejar cada fuente utilizable

Estimación para alguien que sabe usar QGIS pero **no programa**. Es el dato que
decide qué entra al plan y qué no.

| Fuente | Horas hasta tenerla en QGIS |
|---|---:|
| Censo 2024 (QGIS trae conector ArcGIS nativo y pagina solo) | 1–2 |
| Áreas de riesgo MINVU / CIGIDEN (mismo camino) | 1–2 |
| Modelo GORE 2016 (§5b) | 1–2 |
| Censo 2017 del INE (+ truco del `LIKE`) | 2–3 |
| Huella Sentinel-1 y JRC (ya son archivos del proyecto) | <1 |
| HAND desde el DEM | **se le entrega calculado** |

Lo que **no** entra por costo: descargar y recortar grillas globales de población
(WorldPop, GHS-POP), que existen y funcionan pero no agregan nada sobre el Censo
2024 a nivel manzana.

---

## 6. Cómo se defiende esto como geología

Frente a la comisión, el mapeo con el perfil de egreso de la carrera:

| Competencia del programa | Dónde se cumple |
|---|---|
| Identificar y caracterizar procesos geológicos a distintas escalas de tiempo y espacio | Llanura de inundación como forma construida por el río; terrazas y paleocauces |
| Abordar críticamente problemas de la profesión | Rechazar la comparación 1:1.000.000 vs 1:5.000 por incompatibilidad de escala |
| Dominar tecnologías aplicables | DEM, SIG, teledetección radar |
| Recoger, procesar, modelar, interpretar y presentar datos | HAND, contraste multicapa, cuantificación de concordancia |
| Aspectos éticos y legales, compromiso social | Datos personales agregados; el instrumento que no declara el riesgo |
| Comunicar eficazmente | Informe de 10 páginas y charla de 3 minutos |

Y conviene tener presente que el programa **no restringe el ámbito de la práctica**.
Al contrario: *«trabajo en equipo inter y multidisciplinario»* está en el perfil de
egreso, y **«versatilidad» es uno de los seis criterios** que califica el
supervisor. Cruzar hacia planificación territorial, derecho urbano y datos públicos
no es una concesión: es parte de lo que se evalúa.

La frase que ordena la defensa: **no se trata de dibujar mapas, sino de decidir si
el mapa que rige es geológicamente correcto — y si eso ha ido mejorando con el
tiempo.**

---

## 7. Riesgos del plan, y qué hacer con cada uno

| Riesgo | Mitigación |
|---|---|
| El estudiante no maneja SIG ni programación | Bloques A y B no requieren código. El HAND se le entrega calculado; él interpreta |
| Se atasca en el bloque C | Los bloques A, B y el manual ya constituyen práctica aprobable por sí solos |
| La discrepancia de Angol resulta trivial | Igual es resultado: se documenta y se sigue |
| La comisión objeta que es geografía | §6, preparado desde el día 1, no improvisado al final |
| Se entusiasma y quiere modelar inundaciones | Cortarlo temprano y con argumento, no con autoridad (§2) |
| **Sale a demostrar que «los planes están mal»** | La hipótesis H se puede perder, y perderla también es resultado. La vejez del instrumento se mide, no se supone (§1) |
| Los expedientes abandonados no traen estudio de riesgos | Se documenta que no lo traen: la ausencia también responde la pregunta |

---

## 8. Antes del día 1

- [ ] **Enviar la ficha de inscripción por correo.** Activa el seguro estudiantil y
      va *inmediatamente antes* de iniciar la práctica. Sin esto el estudiante
      trabaja sin cobertura.
- [ ] Definir quién firma como **supervisor** en Fundación Pewenkem: es quien
      completa el formulario confidencial de evaluación y lo envía a
      `egeologia@uach.cl` y `karenmoreno@uach.cl`. Se evalúa responsabilidad,
      calidad del trabajo, relaciones en el trabajo, iniciativa, versatilidad y
      confiabilidad — conviene que sea alguien que lo vea trabajar.
- [ ] Acordar una **reunión breve cada 2 o 3 días**. Con 0 horas de docencia
      directa, el riesgo real de esta asignatura es que el estudiante se pierda
      solo durante dos semanas.
- [ ] Confirmar qué computador y qué software usará, y dejar el entorno instalado
      **antes** del día 1. Un día perdido en instalar es un 5 % de la práctica.

---

## 9. Qué gana el visor

Que no sea trabajo escolar que termina en un cajón:

1. **Capa A curada**, separada por tipo de amenaza y con tabla de homologación
   documentada.
2. **El año del instrumento** en cada polígono, que hoy no tenemos. Permite decir
   en la ficha del visor: *«esta área de riesgo la declaró un plan de 1964»*.
3. **Una capa nueva de llanura geomorfológica**, que es evidencia de naturaleza
   distinta a las cuatro actuales y encaja en la arquitectura sin fusionarse con
   ninguna.
4. **La cifra de población expuesta**, que es la pregunta que la gente hace después
   de «¿se inunda acá?».
5. **El manual de fuentes**, publicable por la fundación con autoría del estudiante.
6. **El registro de instrumentos abandonados o detenidos**, que abre una línea
   nueva: dónde existe conocimiento técnico público que nunca alcanzó fuerza legal.
7. **Cartografía vectorial que no existe en ninguna otra parte**, digitalizada
   desde planos de instrumentos no aprobados (§3.2b). Es el aporte que ningún
   servicio del Estado publica, porque el Estado sólo publica lo vigente.
8. **Una advertencia sobre nuestra propia fuente**: el vectorial de MINVU va por
   detrás de las aprobaciones —Angol 2022 está aprobado y no aparece—, así que la
   ausencia de polígono en el visor no significa ausencia de área de riesgo. Eso
   hay que declararlo en la ficha, y es exactamente la regla 5 del proyecto.
