# Práctica profesional — base de datos de riesgo geológico urbano y contraste con la inundación de agosto de 2026

> Plan para **CITI-295 Práctica Profesional (a)**, Geología, Instituto de Ciencias
> de la Tierra, Universidad Austral de Chile. Institución de acogida: **Fundación
> Pewenkem**. Duración: 20 días, >160 h de trabajo autónomo.
>
> Estado: **propuesta**. Las fuentes están verificadas; el reparto de días es una
> estimación y hay que ajustarla al estudiante real.
>
> 📄 **Este documento es para quienes diseñan y supervisan la práctica**: argumenta
> las decisiones, lo descartado y por qué. El documento que se le entrega **a él**
> es [`GUIA_PRACTICANTE.md`](GUIA_PRACTICANTE.md), que dice qué hay, qué tiene que
> hacer y cómo se evalúa, sin la discusión de diseño.

---

## En una página

**Los objetivos ya están definidos.** Este plan no los propone: los sirve.

> **1.** Crear una base de datos georreferenciada de áreas de riesgo geológico urbano.
>
> **2.** Cruzarla con bases demográficas y de infraestructura, y generar un análisis
> de riesgo.
>
> **3.** Comparar los polígonos de riesgo mapeados para Angol con la inundación
> ocurrida el domingo 2 de agosto.

**Qué se propone.** Una práctica de 20 días alojada por Fundación Pewenkem, que
**entrega productos y datos** al proyecto en vez de intervenir la plataforma.

**La decisión de diseño central: el orden de ejecución no es 1, 2, 3, sino 3, 1, 2.**
El objetivo 3 es el más acotado, es el único que produce una afirmación defendible en
tres minutos, y **no depende de los otros dos**. Ponerlo primero significa que al día
6 hay un resultado completo; ponerlo al final significa que cualquier atraso en la
base de datos se lo come. El objetivo 1 después, porque Angol enseña la técnica que
el 1 necesita a escala. Y el 2 al final, porque es el único que sí depende del 1.

| Días | Fase | Objetivo |
|---|---|---|
| 1–6 | Angol de punta a punta | **3** |
| 7–14 | La base de datos regional | **1** |
| 15–20 | Cruce, análisis y cierre | **2** |

### Los cuatro hallazgos que definen el plan

Todos verificados leyendo la fuente, no el catálogo. Los tres primeros son
obstáculos que hay que presupuestar; el cuarto es el resultado que la práctica puede
alcanzar.

**1. Angol no tiene ni un polígono en nuestra capa, así que el objetivo 3 empieza
creando su propio objeto de estudio.** El plan está aprobado desde 2022 y el
vectorial nacional de MINVU no lo trae: nuestra capa va por detrás de las
aprobaciones. Los polígonos hay que levantarlos del plan mismo, georreferenciando
sus láminas. Esto convierte la georreferenciación —que en la versión anterior de
este plan era relleno opcional— en **tarea central y de ruta crítica**.

**2. La huella satelital no sirve para Angol, y hay que decírselo antes de que pierda
dos días.** Las dos pasadas fueron el 3 de agosto, un día después del evento;
cubrieron la comuna al 100 % y la señal no cayó (−0,01 dB). La capa registra **7,7 ha**
donde hubo 1,5 m de agua dentro de las casas, contra 795,7 ha en Carahue. El
instrumento no falló: el agua ya había drenado. La inundación de Angol hay que
reconstruirla con evidencia documental y de terreno, que es trabajo de geólogo y no
de clic sobre un ráster.

**3. Las capas del objetivo 2 no existen: no hay ninguna de población ni de
infraestructura en el proyecto.** El objetivo dice «cruzar», pero la fase empieza
construyendo los dos términos. Es descarga y limpieza, no investigación, y por eso
está al final — pero hay que presupuestarla o el objetivo 2 queda en nada.

**4. El plan de Angol es de 2022 y su Estudio de Riesgo es de septiembre de 2013.**
Está en disco, son 64 páginas, y declara su método: **álgebra de mapas con pesos**
sobre variables morfométricas —morfología, pendiente, cobertura vegetal— más terreno.
Sin modelación hidráulica, sin caudales y sin períodos de retorno. En sus propias
conclusiones recomienda hacer el estudio hidromorfométrico de microcuencas que nunca
se hizo. Y clasifica el peligro en **mínima / media / máxima**, el mismo esquema
cualitativo del modelo regional de 2016.

Ese cuarto hallazgo es el que le da a la práctica una tesis en vez de un inventario:

> **La fecha de un plan regulador no es la fecha de su evidencia.** Angol aparenta ser
> el segundo instrumento más moderno de la región, y la cartografía que rige su
> territorio se hizo trece años antes de la inundación que tenía que anticipar.

Es una advertencia metodológica que se generaliza a toda la base de datos del
objetivo 1 —y por eso ésta lleva **dos columnas de año**, la del plan y la de su
estudio— y es defendible en tres minutos.

### Alcance: geológico es más ancho que inundación

El objetivo 1 dice «riesgo geológico», no «inundación». La base de datos, por lo
tanto, lleva **también los 52 polígonos de remoción en masa** que hoy quedan fuera del
visor, etiquetados por tipo de amenaza. Los objetivos 2 y 3 sí se centran en
inundación fluvial, porque es donde hay evento observado y capa satelital con que
contrastar. La distinción va explícita en la guía del estudiante.

### Una corrección de fecha

El objetivo 3 dice «domingo 2 de julio». El 2 de julio de 2026 fue **jueves**; el
domingo 2 fue el de **agosto**, y es la fecha de todo lo documentado — la evacuación
de las 2 AM, el rescate en bote, las pasadas satelitales del día 3. Conviene
corregirlo en la ficha antes de que llegue al informe.

### Lo que se descarta, y por qué

Rehacer los planos ya georreferenciados. Pedir polígonos a CIGIDEN, porque su fuente
es la misma nuestra. Modelar inundaciones, que exige hidráulica. Y depender de una
solicitud por transparencia, cuyo plazo legal vence después de terminada la práctica.

### Lo que hay que decidir antes del día 1

Enviar la ficha de inscripción, que activa su seguro. Definir quién firma como
supervisor. Y preguntarle su nivel técnico en vez de suponerlo: **este plan carga más
SIG que la versión anterior**, porque georreferenciar dejó de ser opcional.

---

## 1. Las dos decisiones de diseño

**Por qué el eje de la defensa es Angol.** No es una preferencia: es el formato. La
defensa son **3 minutos y 5 de preguntas**, y ahí no se defiende un inventario sino
una afirmación. De los tres objetivos, el 1 y el 2 producen productos —una base de
datos, un análisis de exposición— que son valiosos y no se defienden en tres minutos.
El 3 produce una pregunta con respuesta:

> **¿La zona de riesgo que Angol dibujó en 2013 contuvo el agua de 2026?**

Se puede perder, y perderla es igual de publicable. Y tiene la virtud de que el
estudiante **no puede confirmarla sin medir**, porque el estudio de 2013 no es una
faja de ancho fijo: es una zonificación con base geomorfológica declarada, que sitúa
el peligro medio en paleocauces. Está mejor hecha de lo que uno esperaría, y eso
obliga a comparar en serio.

**Si sobra tiempo**, la pregunta regional —¿la concordancia mejora con la modernidad
del instrumento?— queda como línea secundaria, con 59 años de rango entre Puerto
Saavedra (1964) y Renaico (2023). Está explícitamente marcada como opcional en la
guía, para que no desplace al objetivo 2.

**Qué reconstruye y qué hereda.** Partir de cero desperdicia la práctica; heredarlo
todo lo convierte en alguien que aprieta botones. La regla intermedia:

> **Reconstruye desde cero exactamente aquello de lo que depende su conclusión, y
> hereda todo lo demás.**

En este plan eso son **tres piezas**, todas en el objetivo 3: los polígonos de Angol
(georreferenciando), la inundación real de Angol (evidencia documental y de terreno)
y la llanura geomorfológica (interpretación propia más HAND). Más dos mecanismos: un
**día 0 de reproducción** —verificar una cifra ya publicada; si no calza, encontró un
problema nuestro— y la regla de **verificar todo dato heredado en al menos un número**.

Y un argumento que le sirve para el informe: **en un trabajo nadie parte de cero**.
Llegar a un proyecto andando, entenderlo, encontrarle errores y agregarle una pieza
es lo que hace un geólogo junior en su primer empleo. Condición única: **el informe
debe distinguir qué recibió y qué hizo**.

**La práctica no interviene la plataforma.** Entrega productos y datos; nosotros
integramos después. Eso lo libera de entender nuestro código para poder aportar, y
nos libera de revisar cambios de alguien que está aprendiendo sobre un sitio ya
publicado.

---

## 2. Lo que NO debe hacer, y por qué

Esto importa tanto como la lista de tareas. Son 160 horas: lo que se hace mal cuesta
el doble, porque además desplaza a lo que sí valía.

**No georreferenciar planos de instrumentos ya aprobados que ya están en vectorial.**
Sus áreas de riesgo se descargan del servicio nacional de MINVU, y hay 24 planos ya
georreferenciados con error bajo 2 m.

⚠️ **Angol es la excepción, y es central.** Su plan está aprobado y MINVU **no** lo
trae, así que ahí georreferenciar no duplica nada: es la única forma de obtener el
objeto que el objetivo 3 manda comparar. Lo mismo vale para las 19 comunas sin
vectorial del objetivo 1.

**No tomar la huella satelital como «la inundación de Angol».** Es el error que este
plan más quiere prevenir, porque es invisible: la capa existe, se abre, tiene
polígonos y da un número. El número es 7,7 ha y es correcto — sólo que mide el día
equivocado.

**No pedir los polígonos a CIGIDEN.** La intuición era razonable —si publicaron el
Atlas, deben tener los archivos— pero la verificación la desmiente: sus polígonos
salen de las mismas áreas de riesgo de MINVU que ya tenemos. Sí vale escribirles, pero
por otra cosa (§4).

**No hacer proyecciones de inundación.** Requiere modelación hidrológica e hidráulica,
forzantes climáticas y calibración. No es defendible en 20 días sin formación en
hidráulica, y un resultado mal hecho sobre dónde se inunda una ciudad es peor que no
tener resultado. Lo que sí se puede: **usar** los períodos de retorno del JRC ya
cargados, como término de comparación, declarando su resolución de ~1 km.

**No confundir exposición con riesgo en el objetivo 2.** Contar población dentro de un
polígono es exposición. Llamarlo riesgo exige además vulnerabilidad y capacidad de
respuesta. El objetivo dice «análisis de riesgo»; lo honesto es entregar exposición
bien medida y decir explícitamente qué le falta para ser riesgo.

**No depender de una solicitud por Ley de Transparencia.** Puede presentarla —y
conviene que aprenda a hacerlo— pero el plazo legal es de **20 días hábiles,
prorrogable por 10**. Una solicitud ingresada el día 1 vence **después** de que
termine la práctica. Se ingresa como legado para el proyecto, jamás como insumo de su
informe.

---

## 3. El plan, en tres fases

Estimación sobre 20 días de 8 h. Los productos están amarrados desde el día 1 a los
dos entregables que evalúa la asignatura: **informe de ≤10 páginas** y **presentación
oral de 3 minutos**. El detalle operativo está en
[`GUIA_PRACTICANTE.md`](GUIA_PRACTICANTE.md), que es el documento que él lee; acá sólo
el reparto y lo que no va en el suyo.

| Días | Fase | Objetivo | Producto principal |
|---|---|---|---|
| 1–6 | **Angol** | **3** | Polígonos digitalizados del plan, inundación reconstruida, llanura HAND, tabla de concordancia |
| 7–14 | **Base de datos** | **1** | Capa curada con tipo de amenaza y **dos columnas de año**; cartografía nueva de comunas sin vectorial |
| 15–20 | **Cruce y cierre** | **2** | Capas de población e infraestructura, análisis de exposición, guía de fuentes, informe y charla |

**El plan está lleno, y hay que decirlo.** La georreferenciación es la actividad de
duración menos predecible —depende de si cada retícula es texto vectorial o dibujo, y
eso no se sabe hasta correrla— y ahora está en la ruta crítica del objetivo 3. Orden
de sacrificio acordado de antemano, para no improvisar bajo presión el día 15:

1. **Nunca se recorta**: el objetivo 3 completo, el informe y la charla. Son la
   evaluación y son la geología.
2. **Se recorta primero** la ampliación del objetivo 1 a comunas nuevas. Tres planos
   bien hechos con su RMSE declarado valen más que diez mal ubicados, y la base
   curada de las 13 comunas existentes ya cumple el objetivo.
3. **Se acota** el objetivo 2 a población, dejando infraestructura en las dos o tres
   capas de mayor impacto (educación, salud, vialidad).
4. La guía de fuentes puede quedar en borrador y terminarse después de la práctica.

**Media jornada aparte, antes de la fase 2**: leer el régimen normativo real. El área
de riesgo **no prohíbe, condiciona** (OGUC 2.1.17: se autoriza con estudio fundado de
profesional especialista y obras de mitigación ejecutadas), y eso obliga a separar en
la base de datos los dos regímenes que hoy tenemos mezclados —«área de riesgo» y
«zona no edificable»—, que son estatutos jurídicos distintos.

⚠️ Límite heredado y no negociable: **predio sí, persona nunca**, y ninguna afirmación
de ilegalidad — construir ahí con el estudio correspondiente es legal, y ése es el
punto.

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
| Censo 2024, polígonos | ✅ | 17.107 unidades en R09 repartidas en **3 capas**, 1.021.433 personas, 216 campos |
| Censo 2017 por manzana (INE) | ✅ | 9.224 manzanas + 4.166 entidades, ojo con `REGION` texto |
| DEM Copernicus GLO-30 | ✅ | anónimo, ya integrado al pipeline |
| Huella Sentinel-1 (capa B) | ✅ | 5.776 ha, evento ago-2026, 3 órbitas |
| Puntos críticos SENAPRED | ✅ | 440 fluviales en la región (1.374 en total) |
| Catálogo EAE + municipios | ✅ | 354 documentos, 224 láminas localizadas |
| **Riesgo de inundación GORE Araucanía 2016** | ✅ | **7.203 polígonos, ~35 m** — ver «El modelo regional del Gobierno Regional» |
| Riesgo de anegamiento / remoción / volcánico GORE | ✅ | 4.491 / 10.108 / 240 polígonos |
| Áreas de riesgo IPT de CIGIDEN | ✅ | 3.402 polígonos nacionales, sólo consulta |
| **Estudio de Riesgo del PRC de Angol** | ✅ | **64 páginas, sept-2013**, álgebra de mapas, sin hidráulica |
| Documentos del PRC de Angol (planos, ordenanza, memoria) | ✅ | 24 archivos en disco |
| **Censo 2024, polígonos** (Esri Chile, `Microdatos_Censo_2024`) | ✅ | **Georreferenciado**: 3 capas — 12.886 manzanas + 4.188 entidades rurales + 33 aldeas = 17.107 · 1.021.433 personas · 216 campos · EPSG:4674 · **no está descargado** |
| **Infraestructura crítica (educación, salud, vialidad, APR)** | ❌ | **No existe ninguna capa.** Construirla es el objetivo 2 |
| Cartas geológicas 1:100.000 | ❓ | **sin verificar** — establecerlo es tarea de la fase 1 |

Los ❓, ⚠️ y ❌ están declarados a propósito: no comprometemos la práctica de una
persona sobre un supuesto.

### 5b. El modelo regional del Gobierno Regional, 2016

El Gobierno Regional modeló la amenaza de inundación de toda la región en 2016 para
el *Informe Componente Amenazas Naturales* del PROT. Está público —republicado por
CIGIDEN— y **ya lo ingesta `scripts/15_gore_amenaza.py`**.

Es un ráster clasificado convertido a polígonos (los campos `gridcode` y `count_`
son su firma), de **~35 m**. Validado contra los puntos críticos fluviales de
SENAPRED, que no participaron en su elaboración:

| Clase | Puntos reales dentro | Del territorio | Enriquecimiento |
|---|---:|---:|---:|
| NULA | 5,5 % | 27,1 % | **×0,2** |
| MÍNIMA | 38,0 % | 37,4 % | ×1,0 |
| MEDIA | 18,0 % | 6,1 % | ×2,9 |
| MÁXIMA | 39,5 % | 8,2 % | **×4,8** |

Gradiente monótono: donde el modelo dice «nula» los desbordes reales son cinco
veces más raros que el azar, y el 39,5 % de ellos cae en MÁXIMA, que ocupa el 8,2 %
del territorio. `MÍNIMA` es azar puro y no se publica.

Tres límites que hay que declarar siempre: las clases **no tienen significado
físico** (no son períodos de retorno, a diferencia del JRC); **el PROT nunca se
aprobó** —entró a evaluación en 2013 y no tiene resolución de término—; y **no
declara licencia**, así que antes de publicarlo hay que preguntarle al GORE. El
informe metodológico no está en ningún canal del Gobierno Regional: **no sabemos
cómo se construyó**, y pedirlo por Ley 20.285 es tarea pendiente.

El mismo estudio publica **unidades geomorfológicas** (586 polígonos), material
directo para la pregunta del practicante.

---

## 5c. Cuánto cuesta dejar cada fuente utilizable

⚠️ **Estas horas suponen trabajo manual, sin asistencia de IA.** Es un supuesto que
conviene declarar porque cambia el cuadro (ver «Qué cambia si trabaja con IA»). Estimación de referencia para
dimensionar el plan; **ajustarla cuando se conozca su nivel real**, que no hay que
dar por supuesto en ninguna dirección.

| Fuente | Horas hasta tenerla en QGIS |
|---|---:|
| Censo 2024 (QGIS trae conector ArcGIS nativo y pagina solo) | 1–2 |
| Áreas de riesgo MINVU / CIGIDEN (mismo camino) | 1–2 |
| Modelo GORE 2016 | 1–2 |
| Censo 2017 del INE (+ truco del `LIKE`) | 2–3 |
| Huella Sentinel-1 y JRC (ya son archivos del proyecto) | <1 |
| HAND desde el DEM | **se le entrega calculado** |
| **Georreferenciar los planos de Angol** (ruta crítica del objetivo 3) | **4–12**, según si la retícula es vectorial |
| **Infraestructura crítica** (educación, salud, vialidad, APR) | 4–6, y es construcción desde cero |
| Reconstruir la inundación de Angol desde documentos | 6–10, irreducible: es lectura y terreno |

Lo que **no** entra por costo: descargar y recortar grillas globales de población
(WorldPop, GHS-POP), que existen y funcionan pero no agregan nada sobre el Censo
2024 a nivel manzana.

---

## 5d. Qué cambia si trabaja con IA

Las horas de la tabla anterior suponen trabajo manual. Si usa un asistente —y lo más probable es
que lo use— el reparto cambia, pero **no de forma pareja**, y ahí está lo
interesante.

**Se desploma** (de horas a minutos): el código de fontanería. Paginar un servicio
ArcGIS, reproyectar, intersecar geometrías, calcular superficies, implementar HAND
sobre pysheds. Nada de eso es difícil, sólo es tedioso, y es exactamente lo que un
asistente hace bien.

**No cambia nada**: el tiempo de descarga; leer un expediente de 22 documentos;
poner puntos de control a ojo sobre una retícula escaneada; **interpretar la
geomorfología**; escribir diez páginas; ensayar tres minutos.

**Empeora**: la verificación. Un asistente produce código geoespacial verosímil que
entrega números confiadamente equivocados, y **cae en todas las trampas de esa lista**: medir superficies en grados, un filtro
numérico sobre un campo de texto que devuelve cero filas sin error, la paginación
de ArcGIS que se corta antes, un `outFields` inválido que responde HTTP 200 con un
objeto `error`. Ninguna de ésas levanta una excepción. El asistente entrega un
número y el número está mal.

**Consecuencia para el plan: el tiempo que se libera no se usa para agregar
tareas.** Se usa para interpretar y para verificar, que es donde está el valor y
donde la IA no reemplaza a nadie.

Y una línea que conviene dejar dicha desde el día 1: **la IA puede escribir el
código; la lectura del terreno y el argumento tienen que ser suyos.** Si el
asistente interpreta la geomorfología por él, se queda sin nada que defender en los
5 minutos de preguntas — y ahí es donde una práctica se vacía por dentro.

El programa de CITI-295 **no dice nada sobre uso de IA** (lo revisamos). Al no haber
regla, el criterio honesto es el mismo que ya rige para lo heredado: **que el
informe declare qué hizo con asistencia y qué no.** Eso es atribución, y no le resta
mérito a nada.

---

## 6. Cómo se defiende esto como geología

Frente a la comisión, el mapeo con el perfil de egreso de la carrera:

| Competencia del programa | Dónde se cumple |
|---|---|
| Identificar y caracterizar procesos geológicos a distintas escalas de tiempo y espacio | Llanura de inundación como forma construida por el río; terrazas y paleocauces |
| Abordar críticamente problemas de la profesión | Decidir qué fuentes son comparables entre sí y cuáles no, por escala y por naturaleza del dato |
| Dominar tecnologías aplicables | DEM, SIG, teledetección radar |
| Recoger, procesar, modelar, interpretar y presentar datos | HAND, contraste multicapa, cuantificación de concordancia |
| Integrar información de calidad y origen heterogéneos | Reconstruir la inundación de Angol desde documentos, terreno y prensa, cada fuente con su incertidumbre |
| Aspectos éticos y legales, compromiso social | Datos personales agregados; el instrumento que no declara el riesgo |
| Comunicar eficazmente | Informe de 10 páginas y charla de 3 minutos |

Y conviene tener presente que el programa **no restringe el ámbito de la práctica**.
Al contrario: *«trabajo en equipo inter y multidisciplinario»* está en el perfil de
egreso, y **«versatilidad» es uno de los seis criterios** que califica el
supervisor. Cruzar hacia planificación territorial, derecho urbano y datos públicos
no es una concesión: es parte de lo que se evalúa.

La frase que ordena la defensa: **no se trata de dibujar mapas, sino de decidir si el
mapa que rige es geológicamente correcto — y de comprobarlo contra el agua que
efectivamente pasó.**

---

## 7. Riesgos del plan, y qué hacer con cada uno

| Riesgo | Mitigación |
|---|---|
| **No conocemos su nivel de SIG ni de programación, y no hay que suponerlo** | Preguntárselo antes del día 1. El plan funciona en los dos escenarios: curar y caracterizar la base de datos no requiere código, y si maneja SIG y programa, el cálculo de la llanura se le entrega completo en vez de precalculado. **Ojo: este plan carga más SIG que la versión anterior**, porque georreferenciar Angol dejó de ser opcional |
| **La georreferenciación de Angol se atasca** — está en ruta crítica del objetivo 3 | Es el riesgo número uno de este plan. Mitigación: atacarla el día 2, no el día 5, y tener Galvarino como caso resuelto de referencia. Si la retícula está rasterizada en todos los planos, se digitaliza sobre ortofoto con error declarado |
| **Toma la huella satelital como la inundación de Angol** | Advertido en su guía con el número (7,7 ha) y la explicación física. Verificarlo en la primera reunión |
| Se atasca en el cálculo de la llanura | La base de datos del objetivo 1 y el análisis del 2 ya constituyen práctica aprobable |
| La zona de 2013 resulta acertada y contuvo el agua | Es un resultado igual de bueno, y más interesante: querría decir que el álgebra de mapas funcionó donde no había hidráulica |
| **El objetivo 2 queda sin tiempo** porque hay que construir sus capas desde cero | Está último a propósito y su orden de recorte está acordado (§3). Población sola ya lo cumple parcialmente |
| La comisión objeta que es geografía | El mapeo con el perfil de egreso está en «Cómo se defiende esto como geología», preparado desde el día 1 |
| Se entusiasma y quiere modelar inundaciones | Cortarlo temprano y con argumento, no con autoridad (§2) |
| **Sale a demostrar que «los planes están mal»** | La pregunta de Angol se puede perder, y perderla también es resultado. Y el estudio de 2013 está mejor hecho de lo que uno esperaría: eso lo obliga a medir |
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

1. **Las áreas de riesgo de Angol**, que hoy son un hueco en el mapa de la comuna con
   el peor evento urbano del temporal.
2. **El caso Angol documentado**: un plan de 2022 cuya cartografía es de 2013, y un
   estudio que recomendó el análisis hidráulico que nunca se hizo. Es material para la
   ficha del visor y para la discusión pública.
3. **Base de datos curada** de riesgo geológico urbano, separada por tipo de amenaza,
   con tabla de homologación y **dos columnas de año** —la del plan y la de su
   estudio—, que es una distinción que hoy nadie hace.
4. **Cartografía vectorial que no existe en ninguna otra parte**, digitalizada desde
   planos de instrumentos no aprobados. El Estado sólo publica lo vigente.
5. **Población e infraestructura expuestas**, que es la pregunta que la gente hace
   después de «¿se inunda acá?». Hoy el visor no puede responderla: no tiene ninguna
   de las dos capas.
6. **Una capa de llanura geomorfológica**, evidencia de naturaleza distinta a las
   cuatro actuales, que encaja en la arquitectura sin fusionarse con ninguna.
7. **El registro de instrumentos abandonados o detenidos**, que abre una línea nueva:
   dónde existe conocimiento técnico público que nunca alcanzó fuerza legal.
8. **La guía de fuentes**, publicable por la fundación con autoría del estudiante.
9. **Una advertencia sobre nuestra propia fuente**: el vectorial de MINVU va por detrás
   de las aprobaciones —Angol 2022 está aprobado y no aparece—, así que la ausencia de
   polígono en el visor no significa ausencia de área de riesgo. Es la regla 5 del
   proyecto.
