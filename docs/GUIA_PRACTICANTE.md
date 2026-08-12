# Guía de la práctica — qué hay, qué haces y cómo se evalúa

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
| **B · Observado** | Hasta dónde llegó el agua, con fecha de pasada satelital | 5.776 ha, agosto 2026 |
| **C · Modelado** | Qué dice un modelo que *podría* pasar, y cada cuánto | global ~1 km + regional ~35 m |
| **D · Operacional** | Dónde reportó problemas el municipio | 440 puntos fluviales |

**Tu pregunta.**

> ¿El área de riesgo por inundación que declara el plan regulador coincide con la
> llanura de inundación real del río? ¿Y esa coincidencia mejora en los planes más
> nuevos?

Como hipótesis: **la concordancia mejora con la modernidad del instrumento.** Hay
59 años para probarla, de Puerto Saavedra (1964) a Renaico (2023). **Se puede
perder, y perderla también es resultado.**

**Por qué es geología.** La llanura de inundación es una forma del terreno que
construyó el río depositando sedimento: se lee en terrazas, paleocauces y quiebres
de pendiente. El polígono de un plan antiguo, en cambio, suele ser una faja de
ancho fijo siguiendo el cauce — un retiro fijado por norma, no una modelación.
Comparar ambos es geomorfología fluvial aplicada, y no está hecho.

⚠️ Pero **no todos los planes son fajas**: el Estudio Fundado de Riesgos de Temuco
tiene terrazas y períodos de retorno. Tu hipótesis ya tiene un contraejemplo, así
que vas a **medir**, no a confirmar lo que ya creías.

| Días | Fase | Qué sale de ahí |
|---|---|---|
| 1–5 | **Fase 1 — Carahue completa** | Un resultado entero de punta a punta. Sabes que el método funciona |
| 6–14 | **Fase 2 —** ensanchar y caracterizar | Las otras comunas, el año de cada instrumento, los expedientes muertos |
| 15–20 | **Fase 3 —** cerrar | Población expuesta, informe y charla |

**Por qué Carahue primero y sola.** Tu resultado —la llanura contra el polígono
normativo— es lo único irreemplazable de la práctica. Si va al final y depende de
que todo lo anterior salga a tiempo, cualquier atraso se lo come. Así que lo haces
**primero, en una sola comuna, de principio a fin**. Al día 5 tienes un resultado
completo; los quince restantes son repetir algo que ya probaste.

**Qué entregas:** productos, no cambios en la plataforma (ver «Qué entregas»).
**Cómo se evalúa:** informe ≤10 páginas, charla de 3 minutos, evaluación del
supervisor. Aprobado o reprobado.

**Qué NO hacer:** rehacer lo ya georreferenciado · modelar inundaciones (exige
hidráulica, no se defiende en 20 días) · depender de una solicitud por
transparencia, cuyo plazo legal vence **después** de que termine tu práctica.

---

## 2. Alcance: qué cuenta como inundación

Nos interesa la **inundación fluvial**: agua que se sale de un cauce —río, estero,
quebrada, canal— y ocupa terreno normalmente seco.

**No** nos interesa el **anegamiento urbano por drenaje insuficiente**: un colector
que colapsa, un paso bajo nivel que se llena. Suena parecido y es otro fenómeno,
con otra física y otro servicio responsable.

No es una distinción de vocabulario, y se puede medir. Contrastando los puntos
críticos de SENAPRED contra la huella satelital, con el mismo método:

| Grupo de puntos | Enriquecimiento sobre el azar |
|---|---:|
| Desborde de cauce y quebradas | ×2,1 |
| Colectores y anegamiento de caminos | **×1,0** — azar puro |

Los de drenaje **no muestran ninguna señal**, y es lo que predice la física: el
radar ve agua libre sobre terreno abierto, no un colector bajo una calle.

---

## 3. Qué recibes

| Qué | Dónde | Detalle |
|---|---|---|
| Áreas de riesgo de planes reguladores | `data/processed/areas_riesgo_prc_araucania.geojson` | 124 polígonos, 13 comunas |
| Puntos críticos fluviales (SENAPRED) | `web/data/puntos-criticos-inundacion.geojson` | 440, de ellos 211 crónicos |
| Huella de inundación por satélite | `web/data/sar/huella-observada.geojson` | 5.776 ha, agosto 2026 |
| Amenaza modelada global (JRC, Comisión Europea) | `data/processed/jrc/` | 6 escenarios, ~1 km |
| Amenaza modelada regional (Gobierno Regional, 2016) | `data/processed/gore/` | 2.539 polígonos, ~35 m |
| Unidades geomorfológicas | `data/processed/gore/` | 586 polígonos, mismo estudio |
| Planos de PRC georreferenciados | `data/processed/georreferenciado/` | 24 georreferenciados, 20 publicados, error < 2 m |
| Catálogo de documentos | `web/data/catalogo-documentos.json` | 354 documentos, 224 láminas |
| Expedientes de planificación (registro EAE) | `data/processed/eae/araucania.json` | 30 procedimientos con su estado |

**Sobre el período de retorno**, que es lo que más se malentiende: «100 años» **no**
significa que la crecida ocurra cada 100 años, sino que **cada año tiene un 1 % de
probabilidad**. Y «~1 km de resolución» significa una sola respuesta por cada
cuadrado de un kilómetro: sirve para ver dónde hay valles inundables, **no para
saber si una casa está dentro**.

**Sobre el código: no tienes que programar en este repositorio ni modificar el
visor.** Tu práctica es entregar productos y datos; nosotros integramos después lo
que sirva. Los scripts están como referencia. Para leer: `README.md` y
`docs/INVENTARIO_FUENTES.md`.

**Lo que reconstruyes tú es una sola cosa**, y es la que sostiene tu conclusión: la
llanura de inundación. Todo lo demás lo heredas. Cómo se hace está en la fase 1.

---

## 4. Las tres fases

### Fase 1 — Carahue completa, de punta a punta (días 1 a 5)

Una sola comuna, la cadena entera. Al día 5 tienes un resultado y sabes que el
método funciona.

**Carahue tiene los tres términos de la comparación**, y es la única que los tiene
juntos: plan regulador de **1989** (37 años), **31 polígonos** de área de riesgo, y
**795,7 ha** de huella satelital observada en el temporal de agosto — la mayor de la
región, confirmada por prensa con más de 4.500 personas aisladas.

1. **Verifica antes de agregar.** Toma una cifra que ya publicamos y compruébala
   contra la fuente, por el camino que prefieras. Decimos 124 polígonos en 13
   comunas: ¿es así? Si calza, entendiste el dato. **Si no calza, encontraste un
   problema nuestro**, y eso vale más que cualquier tarea asignada.
2. **Escribe tu predicción**, antes de calcular nada. *«Predigo que los planes
   antiguos van a quedarse cortos respecto de la llanura real.»* Con el resultado a
   la vista es facilísimo convencerse de que uno lo esperaba, y eso no es
   investigación. En la defensa te deja decir **«predije esto y obtuve esto otro»**.
3. **Cura los polígonos de Carahue**: separa inundación de lo que no lo es, y anota
   cada decisión.
4. **Interpreta el terreno tú primero.** Sobre el modelo de sombras, dibuja las
   terrazas, los paleocauces y el quiebre de la llanura — **antes** de calcular nada.
5. **Calcula la llanura** por altura sobre el cauce más próximo (**HAND**, *Height
   Above Nearest Drainage*). No partes en blanco:
   `Valles/scripts/06_watershed_pysheds.py` ya resuelve lo más engorroso con
   **pysheds**, que está instalado: acondicionar el modelo de elevación —rellenar
   depresiones y planicies— y calcular la dirección de flujo por el método **D8**.
   Te falta agregar acumulación de flujo, umbralizarla para definir los cauces, y
   calcular la diferencia de cota contra el cauce receptor. Eso último **es** el HAND.
6. **Compara y mide dos números**: qué fracción de la llanura real cubre el área
   declarada, y qué fracción del área declarada cae fuera de la llanura. Significan
   cosas opuestas — **repórtalos por separado, nunca sumados**.

Si tu interpretación a mano y el cálculo coinciden, tu criterio sirve. Si no
coinciden, tienes que averiguar cuál de los dos está equivocado: es la mejor
pregunta que te puede tocar.

**Lleva un cuaderno corrido desde el día 1**, una entrada diaria de tres líneas. De
ahí salen después los archivos, y sobre todo las **dificultades encontradas**, que
el reglamento te pide y que nadie recuerda al final si no las fue anotando.

---

### Fase 2 — Ensanchar y caracterizar (días 6 a 14)

Ahora repites lo probado sobre las demás comunas, y en paralelo levantas el
contexto que le da sentido.

#### Las otras comunas

Elegidas por medición, no por intuición:

| Comuna | Huella satelital | Polígonos normativos | Plan | Por qué está |
|---|---:|---:|---:|---|
| **Collipulli** | **0 ha** | **66** | 2009 | Más de la mitad de la capa regional y **nada de agua observada**, con 65 % de la comuna mirada |
| **Angol** | 7,7 ha | **0** | 2022 | El caso urbano, donde el método falla (más abajo) |
| Nueva Imperial | 202,4 ha | 1 | — | Caso intermedio |

Collipulli es el contraste que más enseña: o el instrumento sobredibuja, o el
evento no llegó ahí. **Cualquiera de las dos respuestas es un resultado.** Angol no
tiene polígonos normativos, así que ahí no hay comparación posible hasta que
resuelvas su discrepancia.

#### Curaduría de toda la capa

La capa de áreas de riesgo mezcla cosas que no son comparables: 48 polígonos de
inundación conviven con 52 de remoción en masa, 8 de quebradas, 3 de canales y uno
de resguardo de línea de alta tensión.

1. **Separar por tipo de amenaza** y construir una **tabla de homologación** con una
   fila por valor original. El Atlas de CIGIDEN encontró **102 nombres distintos** de
   área de inundación a escala nacional: la tabla es el activo.
2. **Separar los dos regímenes jurídicos**, que no son lo mismo: «área de riesgo»
   condiciona y «zona no edificable» prohíbe (ver «El área de riesgo condiciona, no
   prohíbe», más adelante).
3. **Resolver la discrepancia de Angol**: el Atlas lo mapea con zonas inundables
   extensas y su plan figura aprobado, pero **nuestra capa no tiene ni un polígono**.
   Averigua quién está incompleto.
4. **Corregir errores heredados**, empezando por la comuna escrita `Pitufquén`. Cada
   corrección se registra; el dato crudo no se edita nunca.

#### La edad y el fundamento de cada instrumento

Una ficha por comuna: año del instrumento, antigüedad, número y tipo de áreas de
riesgo, si la memoria incluye Estudio de Riesgos, escala, si declara metodología.

Los años ya los tenemos: Puerto Saavedra **1964**, Pitrufquén 1984, Carahue 1989,
Traiguén 1991, Villarrica 1992, Collipulli 2009, Temuco 2010, Gorbea y Toltén 2012,
Angol 2022, Renaico 2023. Puerto Saavedra ordena su territorio con un instrumento de
**1964**: la reconstrucción posterior al terremoto y tsunami de 1960.

**Y revisa los expedientes que murieron.** Cinco procedimientos terminaron en
abandono y sus documentos quedaron públicos igual:

| Instrumento | Ingreso | Documentos |
|---|---|---:|
| **PRC Temuco** | 08-09-2017 | 7 |
| PRC Collipulli | 30-08-2016 | 16 |
| PRC Victoria | 16-06-2015 | 8 |
| PRC Lonquimay | 23-10-2015 | 3 |
| PRC Temuco – Terreno Amanecer | 13-08-2015 | 3 |

Temuco ordena el argumento: la capital regional inició la actualización en 2017, el
proceso se abandonó, y sigue rigiendo el plan de 2010. **Si el estudio del expediente
abandonado se parece más a la llanura real que la norma vigente, demostraste que el
conocimiento existía y no llegó a ser norma.** Es prueba directa de tu hipótesis.

#### Georreferenciar lo que nunca fue vectorial

Esto es trabajo de relleno para cuando algo esté bloqueado — **no dejes que
desplace la fase 1 ni el informe**. Pero es valioso: MINVU publica las áreas de
riesgo de instrumentos **vigentes**, así que un plan que no se aprobó no aparece ahí
y **no va a aparecer nunca**. Georreferenciarlo no duplica nada: **crea el único
vectorial que va a existir de ese territorio**.

**17 de los 30 procedimientos están en comunas sin ningún vectorial**, y 15 ya tienen
sus láminas localizadas:

| Comuna | Estado del procedimiento | Láminas |
|---|---|---:|
| **Teodoro Schmidt** | Informe Ambiental Complementario | **37** |
| Vilcún | Informe Ambiental Complementario | 14 |
| Curarrehue | Inicio EAE | 14 |
| **Galvarino** | Cuarto Informe Ambiental, desde **2013** | 10 |
| Purén | Informe Ambiental Corregido | 9 |
| Saavedra | Tercer Informe Ambiental | 8 |
| Lonquimay | Complementario, y otro abandonado | 7 |

**Galvarino es tu ejemplo resuelto.** Entró a evaluación el 24-07-2013 y trece años
después sigue en «Cuarto Informe Ambiental». No tiene ni un polígono en MINVU, y sus
planos **ya están georreferenciados** en `data/processed/georreferenciado/`, con
error de 11 centímetros. Estúdialos antes de atacar los que faltan — y fíjate en el
plano mismo: **los tres recuadros de aprobación están en blanco**. Es la prueba
visual de que el plan nunca se aprobó, en el propio documento.

**Método.** Corre `08_georreferenciar_grilla.py` sobre las láminas: donde la retícula
UTM sea texto vectorial, el plano se ubica solo. Donde esté rasterizada —le pasó a 25
planos— hay que poner puntos de control a mano en QGIS, que es donde aprendes la
técnica de verdad.

⚠️ **Cada plano lleva su RMSE y su clasificación de aptitud** (ver glosario al final).
Tres planos correctos valen más que diez mal ubicados: uno mal georreferenciado
publicado como bueno es peor que no tenerlo.

#### El caso Angol: cuándo el método falla, y por qué

Tenlo claro desde temprano, porque es el límite más importante de la capa satelital
que vas a usar — y no es el que uno esperaría.

En **Angol**, el estero Rehue se desbordó la **madrugada del domingo 2 de agosto**.
SENAPRED ordenó evacuar a las 2 AM, el agua superó **1,5 m dentro de las casas** en
Villa La Arboleda y Santa Teresita, y 60 personas fueron rescatadas en bote.

**Las dos pasadas satelitales sobre Angol fueron el 3 de agosto.** Un día después.
Cubrieron la comuna al 100 % y la señal no cayó: −0,01 dB de caída mediana. Nuestra
capa registra **7,7 ha** donde ocurrió una de las peores inundaciones de la región.

El instrumento no se equivocó: el 3 de agosto, en Angol, no había lámina de agua.
**El agua subió y bajó antes de que pasara el satélite.**

Compáralo con Carahue, 795,7 ha: una llanura agrícola inundada se queda días; un
estero urbano drena en horas. El sesgo de esta capa **no es del sensor, es del
tiempo**: ve bien la inundación lenta y extensa, y pierde sistemáticamente la
crecida rápida — que es justamente la que mata gente.

Es una limitación que se puede afirmar con fecha y hora, y eso la hace mucho más
defendible que decir «el radar no ve bien las ciudades». Úsala así.

---

### Fase 3 — Cerrar (días 15 a 20)

**Población.** Censo 2024 por manzana: 17.107 unidades en la región, 1.021.433
personas, con variables de vulnerabilidad además del conteo (hacinamiento,
materialidad precaria, hogares con adultos mayores, agua desde río). La pregunta que
cierra tu argumento: **cuánta gente vive en llanura inundable que el instrumento no
reconoce.**

⚠️ Tres cosas que cuestan medio día si se descubren tarde:
- **Reproyecta a UTM (EPSG:32718/32719) antes de medir superficies.** En grados el
  número no significa nada.
- El servicio del Censo 2024 es un **espejo de Esri Chile**, no del INE: contrasta un
  par de totales comunales antes de publicar.
- En el Censo 2017 del INE, `REGION=9` devuelve **cero filas sin error** porque el
  campo es texto; hay que usar `REGION LIKE '%RAUCAN%'`. Cero filas sin mensaje es el
  modo de falla más peligroso que existe.

Y la regla que no se negocia: **agregado por manzana, nunca por persona.**

**Tu guía de dónde buscar cartografía de inundación.** No la hagas como una
investigación aparte: **es el registro de la búsqueda que ya hiciste** en la fase 2.
Anota sobre la marcha qué buscaste, dónde estaba, qué no encontraste y a quién habría
que pedírselo. Al día 15 la tienes casi escrita.

Es un producto por derecho propio —**el catastro no existe en ninguna parte**— y su
premisa es que la cartografía no vive sólo en los planes reguladores.

*Punto de partida verificado, para que veas el patrón*: los Planes Maestros de Aguas
Lluvias los hace la Dirección de Obras Hidráulicas para ciudades de más de 50 mil
habitantes. La página oficial (`doh.mop.gob.cl/planes-maestros/`) lista sólo **PM–07
Temuco y Padre Las Casas**… pero el repositorio DIRPLAN del MOP tiene además **Angol
(2018)** y **Villarrica (2016)**, que la página oficial no muestra. Comprobado: los
tres descargan y son PDF válidos. Fíjate en dos cosas: el catálogo oficial estaba
incompleto, y el PM–07 cubre **Padre Las Casas**, la comuna con más puntos críticos
crónicos de la región y de la que no tenemos ni un documento.

*Lo que te toca: encontrar el resto.*

| Familia | Quién la elabora | Por qué interesa |
|---|---|---|
| Planes Maestros de Aguas Lluvias | MOP – DOH | ✅ confirmado; falta ver qué traen adentro |
| Planes de manejo de cauces | MOP – DOH | Definen fajas y obras sobre los ríos |
| Planes de Reducción del Riesgo y de emergencia | SENAPRED (Ley 21.364) | La ley manda usar los Mapas de Amenaza al planificar |
| **PROT, Informe Componente Amenazas Naturales** | Gobierno Regional | De ahí salió el modelo de 2016 que usaste. **Nadie sabe cómo se hizo** |
| Mapas de Amenaza de Inundación | DGA | El estándar formal; hoy cubre un solo río del país |
| Planes de acción climática | Municipios y GORE (Ley 21.455) | Pueden traer cartografía |
| **Estudios Fundados de Riesgo de los PRC** | Consultoras, vía municipio | La veta más rica: el de Temuco tiene modelación con períodos de retorno |
| PLADECO y otros | Municipios | A veces aparece ahí lo que falta en el resto |

Para cada una: qué es, quién la hace, si trae cartografía, dónde se consulta, en qué
formato y qué instancias hay en La Araucanía. Más una sección de qué pedir por Ley
20.285 y a quién.

Tres reglas de método, que valen para toda tu carrera:
- **Verifica abriendo el archivo, no viendo el registro en un catálogo.** Un catálogo
  desactualizado es la causa habitual de concluir «el dato no existe»: nos pasó con
  MINVU, y acaba de pasar con los planes maestros.
- **Marca cada afirmación**: ✅ lo abriste · 🔎 lo viste referenciado · ⚠️ no lo pudiste
  confirmar.
- Prueba los **repositorios de transparencia activa**: suelen tener informes que no
  están en ningún portal de datos.

**Si encuentras una familia que no está en esa tabla, ése es el mejor resultado
posible.**

**Informe y presentación.** El informe no supera 10 páginas. La charla son 3 minutos:
alcanza para **una pregunta, un método y un número**. Ensáyala cronometrada más de
una vez.

---

## 5. Qué entregas

Tu práctica se mide por productos, no por commits. Todo son archivos que nos pasas:

| Producto | Formato | Bloque |
|---|---|---|
| Tabla de homologación de tipos de área de riesgo | CSV | A |
| Registro de correcciones y discrepancias | CSV | A |
| Ficha de caracterización por comuna | CSV | B |
| Ficha de instrumentos abandonados o detenidos | CSV o texto | B |
| Planos georreferenciados sin equivalente vectorial | GeoTIFF + puntos de control + RMSE | B2 |
| Áreas de riesgo digitalizadas de esos planos | GeoJSON o shapefile | B2 |
| **Llanura de inundación (HAND)** | ráster + polígonos | C |
| Tu interpretación geomorfológica | mapas + una página | C |
| Tabla de concordancia por comuna | CSV | C |
| Cifras de población expuesta | CSV por comuna | D |
| **Guía de dónde buscar cartografía** | documento | D |
| **Informe** ≤10 páginas · **presentación** 3 min | — | — |

Dos condiciones de entrega, y son las que hacen que un dato sirva o no:

- **Cada archivo lleva su fuente, su año y su método** al lado o en sus columnas.
  Un GeoJSON sin procedencia es inservible a los seis meses aunque los números
  estén perfectos.
- **Di en qué sistema de referencia está**, y si mediste superficies, en qué
  proyección. Es el error más común y el más silencioso.

---

## 6. El área de riesgo condiciona, no prohíbe

Es un error frecuente y si lo cometes en tu informe se nota:

> *«Para autorizar proyectos a emplazarse en áreas de riesgo, se requerirá que se
> acompañe a la respectiva solicitud de permiso de edificación **un estudio
> fundado, elaborado por profesional especialista** y aprobado por el organismo
> competente, que determine las acciones que deberán ejecutarse para su utilización
> […] Este tipo de proyectos **podrá recibirse** parcial o totalmente en la medida
> que se hubieren ejecutado las acciones indicadas.»*
> — OGUC, art. 2.1.17

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

**Si el tiempo se acorta** —va a pasar, la georreferenciación es lo menos
predecible— el orden de sacrificio está decidido de antemano para que no improvises
bajo presión: **nunca** se recortan el informe, la presentación ni el bloque C; se
recorta primero el cruce con población; se acota B2 a 3 o 4 planos bien hechos; y la
guía de fuentes puede quedar en borrador.

---

## 12. Glosario

**Vectorial y ráster.** Las dos formas de guardar un mapa. **Vectorial** son formas
con coordenadas —puntos, líneas, polígonos— y se puede consultar («¿este punto está
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
