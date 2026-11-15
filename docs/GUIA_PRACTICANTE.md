# Guía de la práctica: qué hay, qué haces y cómo se evalúa

> Práctica **CITI-295**, Geología UACh, alojada por **Fundación Pewenkem**.
> 20 días, >160 horas. Léela entera antes del día 1.

---

## 1. En una página

**El proyecto.** Un visor abierto que responde «¿se inunda donde vivo?» para La
Araucanía, reuniendo información pública hoy dispersa en PDFs:
`mendozavolcanic.github.io/riesgomapas`. Su idea rectora es que **la evidencia no
se fusiona en un número único**: se muestran cuatro capas separadas, cada una con
su fuente, su año y su error declarado.

| Capa | Qué responde | Estado |
|---|---|---|
| **A · Normativo** | Qué declaró el plan regulador. Única con efecto legal | 124 polígonos, 13 comunas |
| **B · Observado** | Hasta dónde llegó el agua, con fecha de pasada satelital | 5.082 ha, agosto 2026 |
| **C · Modelado** | Qué dice un modelo que *podría* pasar, y cada cuánto | global ~1 km + regional ~35 m |
| **D · Operacional** | Dónde reportó problemas el municipio | 440 puntos fluviales |

### Tus tres objetivos

Son los que se te evalúan. Todo lo demás en esta guía existe para servirlos.

> **1.** Crear una base de datos georreferenciada de áreas de riesgo geológico urbano.
>
> **2.** Cruzarla con bases demográficas y de infraestructura, y generar un análisis
> de riesgo.
>
> **3.** Comparar los polígonos de riesgo mapeados para Angol con la inundación
> ocurrida el domingo 2 de agosto.

Y esto es lo que ya está y lo que falta de cada uno. Léelo con atención, porque
**ninguno de los tres está resuelto, y no les falta lo mismo**:

| Objetivo | Qué existe hoy | Qué te toca a ti |
|---|---|---|
| **1 · Base de datos** | 124 polígonos en 13 de 32 comunas | Curarla, fecharla, y **crear la que no existe** en las otras 19 |
| **2 · Cruce y análisis** | Nada. Ni población ni infraestructura | Construir las dos capas y recién ahí cruzar |
| **3 · Angol** | **Cero polígonos** y una huella satelital que no sirve | Levantar los polígonos del plan y reconstruir la inundación |

**El orden en que los vas a hacer no es 1, 2, 3.** Empiezas por el **3**, que es el
más acotado y el que te da un resultado defendible en la primera semana. Después el
**1**, que es repetir a escala regional la técnica que ya aprendiste en Angol. Y el
**2** al final, porque necesita la base del 1 terminada.

| Días | Fase | Objetivo | Qué sale de ahí |
|---|---|---|---|
| 1-6 | **Angol de punta a punta** | **3** | Un resultado completo, y sabes que el método funciona |
| 7-14 | **La base de datos regional** | **1** | La capa curada, fechada y ampliada a comunas sin cartografía |
| 15-20 | **Cruce, análisis y cierre** | **2** | Población e infraestructura expuestas, informe y charla |

### Por qué Angol primero, y por qué es el mejor caso

Porque ahí hay una pregunta con respuesta, y no es la que uno esperaría.

El plan regulador de Angol es de **2022**: el segundo más nuevo de la región. Pero
su **Estudio de Riesgo es de septiembre de 2013**, y lo tienes en disco. Es decir: el
instrumento parece moderno y su evidencia tiene **trece años más** que el plan que la
usa, y **trece años menos** que la inundación que tiene que explicar.

Y el método con que delimitó esas zonas está declarado en el propio estudio:
**álgebra de mapas con pesos** sobre variables morfométricas (morfología, pendiente,
cobertura vegetal) más terreno. **Sin modelación hidráulica, sin caudales y sin
períodos de retorno.** El estudio incluso recomienda, en sus conclusiones, hacer el
estudio hidromorfométrico de microcuencas que nunca se hizo.

El **domingo 2 de agosto de 2026**, de madrugada, el estero Rehue se desbordó. El
agua superó **1,5 m dentro de las casas** en Villa La Arboleda y Santa Teresita,
SENAPRED ordenó evacuar a las 2 AM y 60 personas salieron en bote.

> **Tu pregunta del objetivo 3:** ¿la zona que ese estudio dibujó en 2013 contuvo el
> agua de 2026?

Cualquiera de las dos respuestas es un resultado publicable, y la pregunta se
sostiene sola en tres minutos de defensa.

⚠️ **Una corrección de fecha que conviene fijar ahora.** El objetivo, tal como está
escrito, dice «domingo 2 de julio». El 2 de julio de 2026 fue **jueves**; el domingo
2 fue el de **agosto**, y es la fecha de todo lo documentado: la evacuación, el
rescate en bote, las pasadas satelitales. Trabajas sobre **el 2 de agosto de 2026**.

### Si te alcanza el tiempo, una segunda pregunta

Angol es un caso. Si la base de datos del objetivo 1 queda lista con holgura, se
puede preguntar lo mismo a escala regional:

> **La concordancia entre el área de riesgo declarada y la llanura de inundación
> real, ¿mejora en los planes más nuevos?**

Hay 59 años de rango, de Puerto Saavedra (1964) a Renaico (2023). **Es opcional**:
no la persigas si el objetivo 2 va atrasado. Y ojo, porque Angol ya la complica:
un plan de 2022 apoyado en un estudio de 2013 dice que **la fecha del plan no es la
fecha de su evidencia**, y ésa es una advertencia metodológica que vale por sí sola.

**Por qué todo esto es geología.** La llanura de inundación es una forma del terreno
que construyó el río depositando sedimento: se lee en terrazas, paleocauces y
quiebres de pendiente. De hecho el propio estudio de Angol lo dice, sitúa el
peligro medio «en áreas de paleocauces» donde la red de drenaje fue modificada.
Verificar eso en el terreno y contra el agua real es geomorfología fluvial aplicada,
y no está hecho.

**Qué entregas:** productos, no cambios en la plataforma (ver «Qué entregas»).
**Cómo se evalúa:** informe ≤10 páginas, charla de 3 minutos, evaluación del
supervisor. Aprobado o reprobado.

**Qué NO hacer:** rehacer lo que ya está georreferenciado · modelar inundaciones
(exige hidráulica, no se defiende en 20 días) · depender de una solicitud por
transparencia, cuyo plazo legal vence **después** de que termine tu práctica.

---

## 2. Alcance: qué cuenta, y por qué no es lo mismo en cada objetivo

Acá hay una asimetría que tienes que tener clara, porque si la pasas por alto vas a
construir mal la base de datos.

**El objetivo 1 dice «riesgo geológico», que es más ancho que inundación.** La capa
que recibes lo confirma:

| Clasificación en la capa | Polígonos |
|---|---:|
| Remoción en masa | **52** |
| Inundación | 48 |
| Área o franja de restricción por quebradas | 8 |
| Anegamiento | 3 |
| Área en torno a canales | 3 |
| Resguardo de línea de alta tensión | 3 |
| Inundación litoral | 2 |
| Antrópico | 1 |

**La base de datos del objetivo 1 los lleva todos**, cada uno etiquetado por tipo de
amenaza. La remoción en masa es riesgo geológico tanto como la inundación, y son 52
polígonos: dejarlos fuera mutilaría el objetivo. La línea de alta tensión, en cambio,
**no es riesgo geológico**: se conserva en la base con su etiqueta, pero no entra en
el análisis.

**Los objetivos 2 y 3 sí se centran en inundación fluvial**, y por una razón
práctica: es donde tenemos el evento observado y la capa satelital para contrastar.
Nadie te va a pedir una remoción en masa medida con radar.

**Qué es inundación fluvial**: agua que se sale de un cauce (río, estero, quebrada,
canal) y ocupa terreno normalmente seco. **No** lo es el **anegamiento urbano por
drenaje insuficiente**: un colector que colapsa, un paso bajo nivel que se llena.
Suena parecido y es otro fenómeno, con otra física y otro servicio responsable.

No es una distinción de vocabulario, y se puede medir. Contrastando los puntos
críticos de SENAPRED contra la huella satelital, con el mismo método para los dos
grupos:

| Grupo de puntos | Enriquecimiento sobre el azar |
|---|---:|
| Desborde de cauce y quebradas | ×2,1 |
| Colectores y anegamiento de caminos | **×1,0**: azar puro |

Los de drenaje **no muestran ninguna señal**, y es lo que predice la física: el
radar ve agua libre sobre terreno abierto, no un colector bajo una calle.

---

## 3. Qué recibes

| Qué | Dónde | Detalle |
|---|---|---|
| Áreas de riesgo de planes reguladores | `data/processed/areas_riesgo_prc_araucania.geojson` | 124 polígonos, 13 comunas, con año |
| **Estudio de Riesgo del PRC de Angol** | `data/raw/documentos/angol/Estudio_Riesgo.pdf` | **64 páginas, septiembre 2013** |
| Documentos del PRC de Angol | `data/raw/documentos/angol/` | 24 archivos: planos, ordenanza, memoria |
| Puntos críticos fluviales (SENAPRED) | `web/data/puntos-criticos-inundacion.geojson` | 440, de ellos 211 crónicos · Angol: 50 |
| Huella de inundación por satélite | `web/data/sar/huella-observada.geojson` | 5.082 ha, agosto 2026 |
| Amenaza modelada global (JRC, Comisión Europea) | `data/processed/jrc/` | 6 escenarios, ~1 km |
| Amenaza modelada regional (Gobierno Regional, 2016) | `data/processed/gore/` | 2.539 polígonos, ~35 m |
| Unidades geomorfológicas | `data/processed/gore/` | 586 polígonos, mismo estudio |
| Planos de PRC georreferenciados | `data/processed/georreferenciado/` | 24 georreferenciados, 20 publicados, error < 2 m |
| Catálogo de documentos | `web/data/catalogo-documentos.json` | 354 documentos, 224 láminas |
| Expedientes de planificación (registro EAE) | `data/processed/eae/araucania.json` | 30 procedimientos con su estado |

⚠️ **Lo que NO recibes, y necesitas para el objetivo 2:** no hay ninguna capa de
población ni de infraestructura en el proyecto. Ni una. Construirlas es parte de tu
trabajo, y está en la fase 3 con las fuentes indicadas.

**Sobre el período de retorno**, que es lo que más se malentiende: «100 años» **no**
significa que la crecida ocurra cada 100 años, sino que **cada año tiene un 1 % de
probabilidad**. Y «~1 km de resolución» significa una sola respuesta por cada
cuadrado de un kilómetro: sirve para ver dónde hay valles inundables, **no para
saber si una casa está dentro**.

**Sobre el código: no tienes que programar en este repositorio ni modificar el
visor.** Tu práctica es entregar productos y datos; nosotros integramos después lo
que sirva. Los scripts están como referencia. Para leer: `README.md` y
`docs/INVENTARIO_FUENTES.md`.

---

## 4. Las tres fases

### Fase 1: Angol de punta a punta (días 1 a 6) · objetivo 3

Una sola comuna, la cadena entera. Al día 6 tienes un resultado completo y sabes
que el método funciona.

Tienes que producir **los dos términos de la comparación**, porque ninguno de los
dos está listo. Ése es el trabajo.

#### 1. Verifica antes de agregar (medio día)

Toma una cifra que ya publicamos y compruébala contra la fuente, por el camino que
prefieras. Decimos 124 polígonos en 13 comunas: ¿es así? Si calza, entendiste el
dato. **Si no calza, encontraste un problema nuestro**, y eso vale más que cualquier
tarea asignada.

Y **escribe tu predicción antes de calcular nada**. *«Predigo que la zona de 2013
va a quedarse corta respecto del agua de 2026.»* Con el resultado a la vista es
facilísimo convencerse de que uno lo esperaba, y eso no es investigación. En la
defensa te deja decir **«predije esto y obtuve esto otro»**.

#### 2. El primer término: los polígonos que Angol declaró

**Angol no tiene ni un polígono en la capa que recibes.** El plan está aprobado
desde 2022 y el vectorial nacional de MINVU no lo trae, nuestra capa va por detrás
de las aprobaciones, y ésa es una advertencia que ya publicamos en el visor.

Así que los polígonos hay que **levantarlos del plan mismo**. Tienes todo:

- `Estudio_Riesgo.pdf`: 64 páginas, con la metodología, las clases de peligro y las
  figuras de los rásteres de inundación, anegamiento y remoción en masa.
- `Plano_Zonificacion_Vialidad-PRC_09201-1.pdf` y `-2.pdf`: la zonificación, donde
  las áreas de riesgo aparecen como zonas `ZR-n`.
- `Ordenanza_Local_actualizada_MARZO_2026.pdf`: qué se prohíbe y qué se condiciona
  en cada una de esas zonas.

**El método ya está resuelto y probado.** Corre `08_georreferenciar_grilla.py` sobre
las láminas: donde la retícula UTM sea texto vectorial, el plano se ubica solo.
Donde esté rasterizada hay que poner puntos de control a mano en QGIS. Antes de
empezar, estudia el caso de **Galvarino** en `data/processed/georreferenciado/`, que
está resuelto con **11 centímetros** de error.

⚠️ **Cada plano lleva su RMSE y su clasificación de aptitud** (ver el glosario al
final). Un plano mal georreferenciado publicado como bueno es peor que no tenerlo.

#### 3. El segundo término: la inundación que realmente ocurrió

Acá está la trampa del objetivo 3, y es importante que la entiendas antes de perder
dos días: **no puedes tomar la inundación de nuestra capa satelital.**

Las dos pasadas de satélite sobre Angol fueron el **3 de agosto**, un día después.
Cubrieron la comuna al 100 % y la señal no cayó: **−0,01 dB** de caída mediana.
Nuestra capa registra **7,7 ha** donde ocurrió una de las peores inundaciones de la
región. Compáralo con Carahue, que registra **795,7 ha**.

El instrumento no se equivocó: el 3 de agosto, en Angol, ya no había lámina de agua.
Una llanura agrícola inundada se queda días; un estero urbano drena en horas. **El
sesgo de esta capa no es del sensor, es del tiempo**: ve bien la inundación lenta y
extensa, y pierde sistemáticamente la crecida rápida, que es justamente la que mata
gente.

Poder afirmar eso con fecha y hora, y no como una vaguedad sobre el radar y las
ciudades, ya es un resultado de tu práctica. **Escríbelo.**

Entonces la inundación se reconstruye con **evidencia documental y de terreno**, que
es trabajo de geólogo:

- **Los 50 puntos críticos de SENAPRED en Angol**, que ya tienes en
  `web/data/puntos-criticos/angol.geojson`.
- **Los sectores nombrados en los reportes**: Villa La Arboleda, Santa Teresita.
  Ubícalos y delimítalos.
- **Marcas de agua**, si vas a terreno: línea de barro en muros, restos en cercos.
  Es la evidencia más fuerte que puedes conseguir y tiene cota.
- **Registros municipales y de SENAPRED**: fichas de damnificados por dirección,
  decreto de emergencia, actas.
- **Prensa y redes con fotos georreferenciables**, tratadas con cuidado: sirven para
  ubicar, no para medir.

Cada fuente entra con su tipo de evidencia y su incertidumbre declarada. **No las
fusiones en un polígono único**: es exactamente lo que el proyecto no hace.

#### 4. Interpreta el terreno tú, antes de comparar

Sobre el modelo de sombras, dibuja las terrazas del Malleco y del Rehue, los
paleocauces y el quiebre de la llanura, **antes** de mirar el resultado de 2013.

Después calcula la llanura por altura sobre el cauce más próximo (**HAND**, *Height
Above Nearest Drainage*). No partes en blanco:
`Valles/scripts/06_watershed_pysheds.py` ya resuelve lo más engorroso con
**pysheds**, que está instalado: acondicionar el modelo de elevación (rellenar
depresiones y planicies) y calcular la dirección de flujo por el método **D8**. Te
falta agregar acumulación de flujo, umbralizarla para definir los cauces, y calcular
la diferencia de cota contra el cauce receptor. Eso último **es** el HAND.

#### 5. Compara, y mide dos números

Entre la zona declarada en 2013 y la inundación reconstruida de 2026:

- qué fracción del agua real cayó **fuera** de la zona declarada;
- qué fracción de la zona declarada **no** se inundó.

Significan cosas opuestas, **repórtalos por separado, nunca sumados**. El primero
mide lo que el instrumento no vio; el segundo, cuánto se pasó de precavido, que no
es un error.

Y una comparación más, que es regalada y muy elocuente: el estudio de Angol clasificó
el peligro en **mínima / media / máxima**, exactamente el mismo esquema cualitativo
que el modelo regional del Gobierno Regional de 2016 que ya tienes cargado. **Dos
estudios independientes, con la misma limitación**: clases sin significado físico, que
no se pueden traducir a un período de retorno.

**Lleva un cuaderno corrido desde el día 1**, una entrada diaria de tres líneas. De
ahí salen después los archivos, y sobre todo las **dificultades encontradas**, que
el reglamento te pide y que nadie recuerda al final si no las fue anotando.

---

### Fase 2: La base de datos regional (días 7 a 14) · objetivo 1

Ahora repites a escala regional lo que ya probaste en Angol, y construyes la base de
datos que es el objetivo 1.

#### Curar lo que existe

La capa mezcla cosas que no son comparables (ver el alcance, más arriba). Lo que hay
que hacer con ella:

1. **Etiquetar por tipo de amenaza** y construir una **tabla de homologación** con
   una fila por valor original. El Atlas de CIGIDEN encontró **102 nombres distintos**
   de área de inundación a escala nacional: la tabla es el activo.
2. **Separar los dos regímenes jurídicos**, que no son lo mismo: «área de riesgo»
   condiciona y «zona no edificable» prohíbe (ver «El área de riesgo condiciona, no
   prohíbe», más adelante).
3. **Corregir errores heredados**, empezando por la comuna escrita `Pitufquén`. Cada
   corrección se registra; el dato crudo no se edita nunca.
4. **Cerrar los 5 polígonos sin año**: Loncoche (dos sectores), Nueva Imperial, Pucón
   y Saavedra (Puerto Saavedra) no están en el Atlas, así que su año hay que sacarlo
   del decreto.

Los años de los demás ya los tenemos: Puerto Saavedra **1964**, Pitrufquén 1984,
Carahue 1989, Traiguén 1991, Villarrica 1992, Collipulli 2009, Temuco 2010, Gorbea y
Toltén 2012, Angol 2022, Renaico 2023. Puerto Saavedra ordena su territorio con un
instrumento de **1964**: la reconstrucción posterior al terremoto y tsunami de 1960.

⚠️ **Y guárdate la lección de Angol**: el año del plan no es el año de su evidencia.
Para cada comuna, si el expediente tiene Estudio de Riesgos, anota **las dos fechas**.
Es una columna de la base de datos y probablemente sea tu hallazgo más citable.

#### Crear la que no existe

Ésta es la parte del objetivo 1 que nadie más ha hecho. **19 de las 32 comunas no
tienen ningún vectorial de áreas de riesgo**, y MINVU sólo publica instrumentos
**vigentes**, así que un plan que no se aprobó no aparece ahí y **no va a aparecer
nunca**. Georreferenciarlo no duplica nada: **crea el único vectorial que va a
existir de ese territorio**.

17 de los 30 procedimientos están en comunas sin vectorial, y 15 ya tienen sus
láminas localizadas:

| Comuna | Estado del procedimiento | Láminas |
|---|---|---:|
| **Teodoro Schmidt** | Informe Ambiental Complementario | **37** |
| Vilcún | Informe Ambiental Complementario | 14 |
| Curarrehue | Inicio EAE | 14 |
| **Galvarino** | Cuarto Informe Ambiental, desde **2013** | 10 |
| Purén | Informe Ambiental Corregido | 9 |
| Saavedra | Tercer Informe Ambiental | 8 |
| Lonquimay | Complementario, y otro abandonado | 7 |

Galvarino entró a evaluación el 24-07-2013 y trece años después sigue en «Cuarto
Informe Ambiental». Fíjate en el plano mismo: **los tres recuadros de aprobación
están en blanco**. Es la prueba visual de que el plan nunca se aprobó, en el propio
documento.

⚠️ **Tres planos correctos valen más que diez mal ubicados.** Si el tiempo aprieta,
haz menos y declara bien el error de cada uno.

#### Los expedientes que murieron

Cinco procedimientos terminaron en abandono y sus documentos quedaron públicos igual:

| Instrumento | Ingreso | Documentos |
|---|---|---:|
| **PRC Temuco** | 08-09-2017 | 7 |
| PRC Collipulli | 30-08-2016 | 16 |
| PRC Victoria | 16-06-2015 | 8 |
| PRC Lonquimay | 23-10-2015 | 3 |
| PRC Temuco, Terreno Amanecer | 13-08-2015 | 3 |

Temuco ordena el argumento: la capital regional inició la actualización en 2017, el
proceso se abandonó, y sigue rigiendo el plan de 2010. **Si el estudio del expediente
abandonado se parece más a la llanura real que la norma vigente, demostraste que el
conocimiento existía y no llegó a ser norma.**

#### Comunas de contraste, si te alcanza

Elegidas por medición, no por intuición:

| Comuna | Huella satelital | Polígonos | Plan | Por qué |
|---|---:|---:|---:|---|
| **Carahue** | **795,7 ha** | 31 | 1989 | La mayor huella de la región y plan antiguo |
| **Collipulli** | **0 ha** | **66** | 2009 | Media capa regional y **nada de agua observada** |
| Nueva Imperial | 202,4 ha | 1 | - | Caso intermedio |

Collipulli es el contraste que más enseña: o el instrumento sobredibuja, o el evento
no llegó ahí. **Cualquiera de las dos respuestas es un resultado.**

---

### Fase 3: Cruce, análisis y cierre (días 15 a 20) · objetivo 2

El objetivo 2 pide cruzar la base con **demografía e infraestructura**. Ojo: **esas
dos capas no existen en el proyecto**, así que la fase empieza construyéndolas. Es
descarga y limpieza, no investigación, pero hay que presupuestarla.

#### Población

**Sí, el censo viene georreferenciado**: son polígonos, no una tabla que haya que
unir por código. Servicio *Microdatos Censo 2024* de Esri Chile, verificado:

```
https://services.arcgis.com/r7t1P5pnkoOLRdhr/arcgis/rest/services/Microdatos_Censo_2024/FeatureServer
```

⚠️ **Pero la región no está en una sola capa, y ahí está la trampa.** Son tres
unidades geográficas distintas que hay que unir para cubrir el territorio:

| Capa | Qué es | Polígonos en R09 | Población |
|---:|---|---:|---:|
| **0** | Manzanas (urbanas) | 12.886 | 691.173 |
| **1** | Manzanas-entidades (rurales) | 4.188 | 312.373 |
| **2** | Aldeas | 33 | 17.887 |
| | **Total** | **17.107** | **1.021.433** |

Las capas 3 y 4 (zonas censales y distritos) son **agregaciones de las anteriores**:
si las sumas cuentas la misma gente dos veces.

⚠️ **Y no mezcles urbano con rural sin decirlo.** En Angol, una manzana urbana típica
mide ~116 × 119 m con 39 personas; una entidad rural mide ~543 × 770 m con 7. Son
**treinta veces más superficie con la quinta parte de la gente**. Si calculas densidad
sobre las dos juntas sin distinguirlas, el resultado no significa nada. Angol tiene
737 manzanas urbanas y 94 entidades rurales.

**Lo demás que conviene saber antes de descargar:**

- **216 campos**, con variables de vulnerabilidad además del conteo: hacinamiento,
  materialidad precaria, hogares con adultos mayores, agua desde río, tramos de edad,
  población inmigrante. El campo de población es `n_per`.
- **El sistema de referencia es SIRGAS 2000 geográfico (EPSG:4674)**, o sea grados.
  Reproyecta a UTM antes de medir cualquier superficie.
- Filtras con `COD_REGION = 9`, que **es un campo numérico** y funciona directo. (No
  lo confundas con el servicio del Censo 2017 del INE, donde el campo equivalente es
  texto y `=9` devuelve cero filas sin dar error.)
- `maxRecordCount` es **2.000**, así que hay que paginar. QGIS trae conector ArcGIS
  nativo y lo hace solo.

#### Infraestructura

Ésta hay que armarla desde cero. Lo que importa para inundación, en orden de
utilidad:

| Capa | Dónde | Por qué importa |
|---|---|---|
| Establecimientos educacionales | MINEDUC, directorio oficial con coordenadas | Alta ocupación diurna, y son albergue en emergencia |
| Establecimientos de salud | DEIS / MINSAL | No pueden quedar aislados |
| Red vial y puentes | MOP, Vialidad; IDE Chile | El corte de acceso es el impacto más frecuente |
| Agua potable rural (APR) | SISS / DOH | Su captación se contamina con la crecida |
| Bomberos y cuarteles | ONEMI / SENAPRED | Capacidad de respuesta |
| Cualquier vacío | OpenStreetMap | Cobertura desigual: declárala |

⚠️ **Verifica abriendo el archivo, no viendo el registro en un catálogo.** Un catálogo
desactualizado es la causa habitual de concluir «el dato no existe».

#### El análisis

La pregunta que cierra tu argumento: **cuánta gente, y cuánta infraestructura
crítica, está en llanura inundable que el instrumento no reconoce.** Eso es
exposición, y se cuenta cruzando cada capa contra la base del objetivo 1 y contra la
llanura que calculaste.

⚠️ Cuatro cosas que cuestan medio día si se descubren tarde:
- **Reproyecta a UTM (EPSG:32718/32719) antes de medir superficies.** En grados el
  número no significa nada.
- El servicio del Censo 2024 es un **espejo de Esri Chile**, no del INE: contrasta un
  par de totales comunales antes de publicar.
- En el Censo **2017** del INE, `REGION=9` devuelve **cero filas sin error** porque el
  campo es texto; hay que usar `REGION LIKE '%RAUCAN%'`. Cero filas sin mensaje es el
  modo de falla más peligroso que existe. (En el servicio de 2024 el campo sí es
  numérico, comprobado.)
- **Exposición no es riesgo.** Contar gente dentro de un polígono es exposición.
  Llamarlo riesgo exige además vulnerabilidad y capacidad de respuesta. Di lo que
  mediste.

Y la regla que no se negocia: **agregado por manzana, nunca por persona.**

#### La guía de dónde buscar cartografía

No la hagas como una investigación aparte: **es el registro de la búsqueda que ya
hiciste** en las fases 1 y 2. Anota sobre la marcha qué buscaste, dónde estaba, qué
no encontraste y a quién habría que pedírselo.

Es un producto por derecho propio (**el catastro no existe en ninguna parte**) y su
premisa es que la cartografía no vive sólo en los planes reguladores.

*Punto de partida verificado, para que veas el patrón*: los Planes Maestros de Aguas
Lluvias los hace la Dirección de Obras Hidráulicas para ciudades de más de 50 mil
habitantes. La página oficial lista sólo **PM-07 Temuco y Padre Las Casas**… pero el
repositorio DIRPLAN del MOP tiene además **Angol (2018)** y **Villarrica (2016)**, que
la página oficial no muestra. Comprobado: los tres descargan y son PDF válidos.

⚠️ **El de Angol te sirve directamente para el objetivo 3**: es un estudio de drenaje
de la misma ciudad, cinco años posterior al Estudio de Riesgo que estás evaluando.

| Familia | Quién la elabora | Por qué interesa |
|---|---|---|
| Planes Maestros de Aguas Lluvias | MOP, DOH | ✅ confirmado, incluido Angol 2018 |
| Planes de manejo de cauces | MOP, DOH | Definen fajas y obras sobre los ríos |
| Planes de Reducción del Riesgo y de emergencia | SENAPRED (Ley 21.364) | La ley manda usar los Mapas de Amenaza al planificar |
| **PROT, Informe Componente Amenazas Naturales** | Gobierno Regional | De ahí salió el modelo de 2016. **Nadie sabe cómo se hizo** |
| Mapas de Amenaza de Inundación | DGA | El estándar formal; hoy cubre un solo río del país |
| Planes de acción climática | Municipios y GORE (Ley 21.455) | Pueden traer cartografía |
| **Estudios Fundados de Riesgo de los PRC** | Consultoras, vía municipio | La veta más rica: es donde estaba el de Angol |
| PLADECO y otros | Municipios | A veces aparece ahí lo que falta en el resto |

Para cada una: qué es, quién la hace, si trae cartografía, dónde se consulta, en qué
formato y qué instancias hay en La Araucanía. Más una sección de qué pedir por Ley
20.285 y a quién. **Marca cada afirmación**: ✅ lo abriste · 🔎 lo viste referenciado ·
⚠️ no lo pudiste confirmar.

**Si encuentras una familia que no está en esa tabla, ése es el mejor resultado
posible.**

#### Informe y presentación

El informe no supera 10 páginas. La charla son 3 minutos: alcanza para **una
pregunta, un método y un número**, y la pregunta es Angol. Ensáyala cronometrada
más de una vez.

---

## 5. Qué entregas

Tu práctica se mide por productos, no por commits. Todo son archivos que nos pasas,
y cada uno está amarrado al objetivo que sirve:

| Producto | Formato | Objetivo |
|---|---|---|
| **Áreas de riesgo de Angol, digitalizadas del plan** | GeoJSON o shapefile | **3** |
| **Inundación de Angol reconstruida**, por tipo de evidencia | GeoJSON + tabla de fuentes | **3** |
| Planos de Angol georreferenciados | GeoTIFF + puntos de control + RMSE | **3** |
| Tu interpretación geomorfológica de Angol | mapas + una página | **3** |
| **Llanura de inundación (HAND)** | ráster + polígonos | **3** |
| **Tabla de concordancia**: agua fuera de zona, zona sin agua | CSV | **3** |
| Base de datos de áreas de riesgo geológico, curada y fechada | GeoJSON + diccionario de campos | **1** |
| Tabla de homologación de tipos de área de riesgo | CSV | **1** |
| Registro de correcciones y discrepancias | CSV | **1** |
| Ficha por comuna: año del plan **y año de su estudio** | CSV | **1** |
| Ficha de instrumentos abandonados o detenidos | CSV o texto | **1** |
| Planos de otras comunas, georreferenciados y digitalizados | GeoTIFF + GeoJSON + RMSE | **1** |
| Capa de población por manzana | GeoJSON o CSV con clave | **2** |
| Capa de infraestructura crítica | GeoJSON | **2** |
| **Análisis de exposición** por comuna | CSV + una página de lectura | **2** |
| **Guía de dónde buscar cartografía** | documento | **2** |
| **Informe** ≤10 páginas · **presentación** 3 min | - | los tres |

Tres condiciones de entrega, y son las que hacen que un dato sirva o no:

- **Cada archivo lleva su fuente, su año y su método** al lado o en sus columnas.
  Un GeoJSON sin procedencia es inservible a los seis meses aunque los números
  estén perfectos.
- **Di en qué sistema de referencia está**, y si mediste superficies, en qué
  proyección. Es el error más común y el más silencioso.
- **Cada capa de evidencia se entrega separada.** No fusiones el agua observada con
  la modelada ni con la declarada: el proyecto entero se sostiene en no hacer eso.

⚠️ **Si el tiempo aprieta, esto se recorta en este orden**: primero las comunas extra
del objetivo 1 (con tres planos bien hechos basta), después la guía de fuentes, que
puede quedar en borrador. **Nunca se recorta Angol ni el informe.**

---

## 6. El área de riesgo condiciona, no prohíbe

Es un error frecuente y si lo cometes en tu informe se nota:

> *«Para autorizar proyectos a emplazarse en áreas de riesgo, se requerirá que se
> acompañe a la respectiva solicitud de permiso de edificación **un estudio
> fundado, elaborado por profesional especialista** y aprobado por el organismo
> competente, que determine las acciones que deberán ejecutarse para su utilización
> […] Este tipo de proyectos **podrá recibirse** parcial o totalmente en la medida
> que se hubieren ejecutado las acciones indicadas.»*
>, OGUC, art. 2.1.17

1. Se puede construir, con estudio de especialista y obras de mitigación
   ejecutadas. Distinto es una **«zona no edificable»**, que sí prohíbe y protege
   infraestructura peligrosa (alta tensión, embalses).
2. **Ese «profesional especialista» es, en inundación, un geólogo o un ingeniero
   hidráulico.** Es el puesto que vas a ocupar: esta práctica no te muestra el
   sistema desde afuera, te muestra dónde vas a trabajar dentro de él.
3. Un plan comunal puede incluso **reducir** un área de riesgo intercomunal con un
   estudio de mayor detalle.

---

## 7. Cómo se evalúa

| Pieza | Formato | Ojo con |
|---|---|---|
| **Informe de actividades** | máximo 10 páginas | Objetivos, contexto, actividades, logros **y dificultades encontradas** |
| **Presentación oral** | 3 min + 2 de preguntas | Es cortísimo. Ensáyala cronometrada |
| **Evaluación del supervisor** | formulario confidencial | Responsabilidad, calidad, relaciones, **iniciativa**, **versatilidad**, confiabilidad |

⚠️ **Estructura el informe por tus tres objetivos.** Es lo que la comisión va a
buscar, y te ahorra tener que inventar un orden. Para cada uno: qué encontraste ya
hecho, qué hiciste tú, qué te salió y qué quedó pendiente.

El informe te pide **analizar tu desempeño y relacionarlo con el rol del geólogo
profesional**. Tienes material: vas a trabajar en la frontera entre geología,
planificación territorial y derecho urbano, que es donde se ejerce esta parte de la
profesión.

⚠️ **Distingue explícitamente qué recibiste y qué hiciste tú.** No es burocracia: es
atribución, y es práctica profesional.

**Antes del día 1:**

- [ ] **Enviar la ficha de inscripción.** Activa tu seguro estudiantil.
- [ ] Confirmar quién firma como supervisor. El formulario lo envía esa persona a
      `egeologia@uach.cl` y `karenmoreno@uach.cl`; es **tu responsabilidad**
      hacérselo llegar.
- [ ] Dejar el computador listo: Python 3.12, QGIS y `requirements.txt`.
- [ ] **Cuéntanos qué manejas** y qué te gustaría aprender. No para evaluarte: para
      repartir el trabajo y calibrar los plazos, que hoy son una estimación.

---

## 8. Sobre usar inteligencia artificial

Vas a usarla y está bien. Pero conviene saber dónde ayuda y dónde te hunde.

**Ayuda mucho** con el código de fontanería: paginar un servicio de datos,
reproyectar, intersecar geometrías, calcular superficies, armar el HAND. Es tedioso
más que difícil. Aprovéchalo sin culpa.

**No cambia nada** el tiempo de descarga, leer un expediente de 22 documentos, poner
puntos de control a ojo, interpretar geomorfología, escribir diez páginas ni ensayar
tres minutos.

**Te puede hundir en la verificación.** Un asistente escribe código geoespacial
razonable que entrega números confiadamente equivocados, y **todas las trampas del
(ver el índice) son trampas en las que cae**: medir superficies en grados, un filtro numérico
sobre campo de texto que devuelve cero filas, una paginación que se corta antes, una
consulta que responde «200 OK» con un error adentro. Ninguna revienta: te entrega un
número, está mal, y no tienes cómo saberlo si no lo verificas contra algo
independiente.

**El límite:** la IA puede escribir el código; **la lectura del terreno y el
argumento tienen que ser tuyos.** Si el asistente interpreta la geomorfología por
ti, llegas a los 5 minutos de preguntas sin nada que defender.

El programa no dice nada sobre IA. Al no haber regla, el criterio honesto es el
mismo que para lo que heredas: **declara qué hiciste con asistencia y qué no.**

---

## 9. Reglas que no se negocian

1. **`data/raw/` no se modifica nunca.** Sólo se generan derivados.
2. **Todo dato publicado lleva fuente y año.** Y el año **no se inventa**: si la
   fuente no lo declara, se escribe «no declarado por la fuente».
3. **Las capas no se fusionan.**
4. **La ausencia de dato no es ausencia de riesgo.** Que una comuna no tenga
   polígono significa que nadie lo declaró, no que no se inunde.
5. **Verificar antes de declarar algo listo**: comando → resultado → verificación
   contra algo independiente.
6. **Si un resultado te parece inverosímil, mira dónde está antes de creerle.** Una
   capa de este proyecto declaró 1.252 km² inundados y resultó ser nieve de
   cordillera y mar. No se descubrió mirando el total, sino la distribución
   espacial.

**Límite ético.** Predio sí, persona nunca: sin nombres de propietarios, vendedores
ni titulares, y cifras agregadas por comuna y por año. **Ninguna afirmación de
ilegalidad**: construir en área de riesgo con el estudio correspondiente **es
legal**, y el punto no es acusar sino mostrar que la información existe y no llega a
quien decide. Y esto **no es información oficial del Estado**.

---

## 10. Trampas ya pagadas

- **Proyecta a UTM antes de medir superficies** (EPSG:32718/32719 acá).
- **Los códigos de comuna engañan**: Pucón es **09115**; 09107 es Gorbea.
- **En servicios ArcGIS**, la condición de parada de la paginación es la bandera
  `exceededTransferLimit`, **nunca** «vino menos de lo que pedí».
- **Un campo mal escrito en `outFields` devuelve HTTP 200 con un objeto `error`**,
  no un fallo. Leído con default `[]`, una capa completa desaparece en silencio.
- **Un filtro numérico sobre campo de texto devuelve cero filas sin error.**
- **Antes de dar una fuente por bloqueada, prueba los espejos y lee bytes reales.**
  La capa B estuvo marcada como «requiere cuenta de Copernicus»: era propiedad de un
  proveedor, no del dato.
- **Una caché se valida, no se supone.** Un archivo puede existir y estar truncado.

---

## 11. Ritmo y ayuda

La asignatura tiene **0 horas de docencia directa**: el riesgo real es que te
pierdas solo dos semanas.

- **Reunión corta cada 2 o 3 días.** Llevar preguntas sirve tanto como resultados.
- **Si algo te tiene atascado más de medio día, pregunta.** Es el 3 % de tu práctica.
- **Escribe el informe desde el día 1.** Lo que más se olvida son las dificultades
  encontradas, que el reglamento pide explícitamente.

**Si el tiempo se acorta** (va a pasar, la georreferenciación es lo menos
predecible) el orden de sacrificio está decidido de antemano para que no improvises
bajo presión: **nunca** se recortan el informe, la presentación ni el objetivo 3 (Angol); se
recorta primero el cruce con población; se acota B2 a 3 o 4 planos bien hechos; y la
guía de fuentes puede quedar en borrador.

---

## 12. Glosario

**Vectorial y ráster.** Las dos formas de guardar un mapa. **Vectorial** son formas
con coordenadas (puntos, líneas, polígonos) y se puede consultar («¿este punto está
dentro de este polígono?»). **Ráster** es una grilla de celdas con un valor cada
una, como una foto. Importa acá: un plano escaneado es una imagen sin coordenadas y
no se puede consultar. «No existe en vectorial» significa que sólo existe como
imagen o PDF.

**Georreferenciar.** Darle coordenadas del mundo real a una imagen que no las tiene.

**RMSE** (error cuadrático medio). Cuánto se equivoca en promedio una
georreferenciación, en metros. **Leave-one-out** es la forma honesta de medirlo: se
saca un punto de control, se calcula la transformación con los demás, y se mide
cuánto falla en el que se sacó. Sin eso reportas el error sobre los mismos datos con
los que te ajustaste, que **siempre sale mejor de lo que es**.

**EPSG.** El catálogo de códigos de sistemas de referencia. `EPSG:4326` son grados;
`EPSG:32718` y `32719` son metros UTM, que es lo que sirve para medir superficies
acá.

**DEM.** Modelo de elevación digital: grilla con la altura del terreno. El nuestro,
Copernicus GLO-30, tiene celdas de 30 m.

**Modelo de sombras** (*hillshade*). Imagen calculada del DEM que simula luz
rasante. Es la forma habitual de **ver** terrazas, paleocauces y escarpes que en el
dato de altura crudo no se distinguen.

**HAND.** *Height Above Nearest Drainage*: altura de cada punto sobre el cauce que
lo recibe. Separa la llanura inundable del terreno alto.

**D8.** El método más simple de dirección de flujo: cada celda del DEM manda toda su
agua a la de mayor pendiente entre sus 8 vecinas.

**Período de retorno.** 100 años **no** es «cada 100 años»: es 1 % de probabilidad
cada año.

**Enriquecimiento.** Cuántas veces más frecuente es algo dentro de una zona que por
azar. Si el 15 % de los puntos reales cae en una capa que ocupa el 5 % del
territorio, el enriquecimiento es ×3. Un valor cercano a ×1 significa que la capa
**no distingue nada**.

**Manzana censal.** La unidad territorial más chica que publica el censo; en zona
urbana, literalmente una manzana.

**IPT.** Instrumento de Planificación Territorial. Los que importan: **PRC** (Plan
Regulador Comunal, sólo dentro del límite urbano) y **PRI** (Intercomunal, que
abarca varias comunas y alcanza el área rural).

**LGUC y OGUC.** La Ley General de Urbanismo y Construcciones y su Ordenanza
General. El art. **2.1.17 de la OGUC** define las áreas de riesgo (ver «El área de riesgo condiciona, no prohíbe»).

**EAE.** Evaluación Ambiental Estratégica: el procedimiento por el que pasa todo
plan regulador antes de aprobarse. Su registro público es la razón por la que
tenemos los expedientes, incluidos los de planes que nunca se aprobaron.

**Ley 20.285.** Ley de transparencia: permite pedir documentos a cualquier organismo
del Estado. Respuesta en 20 días hábiles, prorrogable por 10.

**Instituciones.** **MINVU** Vivienda y Urbanismo · **MOP** Obras Públicas · **DOH**
Dirección de Obras Hidráulicas (MOP) · **DGA** Dirección General de Aguas (MOP) ·
**SENAPRED** Servicio Nacional de Prevención y Respuesta ante Desastres, ex ONEMI ·
**GORE** Gobierno Regional · **INE** Instituto Nacional de Estadísticas · **JRC**
centro de investigación de la Comisión Europea · **CIGIDEN** centro de investigación
de riesgo de desastres de la Universidad Católica.
