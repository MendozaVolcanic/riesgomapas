# Cómo hacer que esto llegue a la gente

> Levantamiento: 25-ago-2026. Cada afirmación indica si se **verificó contra una
> fuente** o si es **inferencia**. La distinción importa: publicar información de
> riesgo apoyándose en una suposición es el mismo error que el proyecto combate
> en los datos.

El visor no está publicado. Hoy corre en `localhost` y depende de dos servicios
cuyas políticas de uso **no admiten** lo que este visor hace. Este documento
reúne lo que hay que resolver para publicarlo y lo que sabemos de cómo se
difunde algo así en Chile.

---

## 0. La conclusión en una frase

**El producto no es el mapa: es el vacío que el mapa documenta.** Web primero,
PWA instalable, teselas propias — pero lo que hay que hacer circular no es un
visor bonito, es un hecho incómodo y verificable, comuna por comuna.

## 0b. Para qué queremos que llegue

Esto no busca prestigio ni usuarios. Busca que **la institución que corresponde
—DGA/MOP para la amenaza, MINVU para el instrumento, SENAPRED para la alerta—
se haga cargo y construya la versión oficial**.

Eso cambia todo lo demás, y conviene tenerlo escrito porque es contraintuitivo:

- **El éxito es volverse innecesario.** Si en dos años existe un visor oficial de
  inundación y éste se puede apagar, ganamos. Conviene **decirlo en el propio
  sitio**: desarma de entrada la lectura de «un particular compitiendo con el
  Estado», que es el principal riesgo reputacional del proyecto, y convierte
  cada visita en un argumento a favor de la política pública en vez de en un
  reemplazo de ella.
- **Las visitas no mueven a una institución.** Lo que la mueve es un vacío
  documentado que alguien tenga que responder por escrito.
- **El activo más fuerte no es el visor, es el inventario.** Saber que 19 de 32
  comunas no tienen su área de riesgo en el vectorial del MINVU, o que Padre Las
  Casas tiene 76.000 habitantes, 38 puntos críticos crónicos y **cero documentos
  de planificación**, es más accionable que cualquier mapa.
- **Y el visor es la prueba de que se puede.** Dos personas, sin presupuesto,
  con datos públicos. Ese es exactamente el argumento que un servicio necesita
  para justificar internamente que vale la pena hacerlo bien.

### La palanca real: la Ley de Transparencia

Más eficaz que la prensa, y mucho más barata. La **Ley 20.285** obliga a
responder por escrito en 20 días hábiles. Una solicitud bien hecha tiene dos
salidas y las dos sirven:

- **«Sí lo tenemos»** → se pide el dato y el visor mejora.
- **«No lo tenemos»** → queda **documentado oficialmente** que el vacío existe,
  con timbre y fecha. Eso es lo que se le muestra a un medio, a un concejo
  municipal o a un parlamentario, y ya no es opinión de dos geólogos.

Solicitudes concretas que vale la pena hacer, una por organismo:

| A quién | Qué preguntar |
|---|---|
| **DGA / MOP** | Qué cuencas tienen Mapa de Amenaza de Inundación aprobado; si hay alguno en curso para La Araucanía; cuál es el plan de cobertura nacional |
| **MINVU (SEREMI Araucanía)** | Por qué el servicio vectorial de áreas de riesgo no incluye a Angol, teniendo PRC vigente con AR-2a graficada en la lámina PRC 09201-1 |
| **SENAPRED** | Si existe una capa nacional de amenaza de inundación fluvial y, si no, quién debería producirla |
| **Municipios sin documentos** | El Estudio Fundado de Riesgos de su PRC (los 7 que no publican nada) |

> ⚠️ **Ojo con quién firma.** Una solicitud de transparencia de un funcionario
> público a otro servicio, sobre una materia sectorial, puede leerse como
> gestión institucional aunque se haga a título personal. Conviene que la firme
> quien no tenga ese conflicto, o hacerla explícitamente como ciudadano y sin
> mencionar el cargo en ninguna parte.

### El gancho compartible, y por qué éste sí es honesto

La lección de Gopletos era que lo compartible fue la **identidad**, no la
utilidad. Acá la identidad es la comuna, y hay un hecho que se comparte solo:

> **«En mi comuna no hay ningún mapa de inundación.»**

Compartir eso **no asusta a nadie hacia una mala decisión**, no predice nada, no
compite con SENAPRED y pone la presión exactamente donde corresponde. Es lo
contrario de compartir un veredicto de riesgo sobre una casa, que es lo que no
hay que hacer nunca.

Por eso la unidad compartible del sitio debe ser la **ficha de estado de la
comuna** —qué hay y qué falta— y no la ficha de un punto.

---

## 1. El caso que se citó: Gopletos

Un buscador de completos que se volvió viral en Chile en abril-mayo de 2026.
Vale estudiarlo porque resolvió el mismo problema de partida —darse a conocer sin
presupuesto— y porque **la mitad de sus lecciones no aplican**, y esa mitad es la
más importante.

**Verificado** (notas de 24horas y T13):

- Lo hizo **Lunatic Motion**, una empresa chilena. No fue un aficionado suelto.
- Lanzó **gopletos.cl el 22-abr-2026**, y partió **como web**. Las tiendas
  quedaron para «próximamente»: la web fue el vehículo de entrada.
- Formato: **mapa interactivo + buscador por comuna**, geolocalización, ficha con
  dirección y horario, calificación y comentarios.
- Ancló el lanzamiento a **una fecha**: el 24 de mayo, Día del Completo.
- Pasó de «más de dos mil» usuarios (T13, 2-may) a «más de seis mil» (24horas)
  durante la ventana de cobertura.

**Inferencia**: el motor no fue la tecnología ni las redes, fue **tres notas de
prensa nacional en dos días**. La viralidad fue mediática, no orgánica. Y lo
compartible fue la **identidad**, no la utilidad: un completo es afecto nacional,
y la gente lo compartió por pertenencia.

### Lo que sí aplica

1. **Web primero, tienda nunca o mucho después.** Un enlace se pega en WhatsApp;
   una app hay que instalarla.
2. **Anclar el lanzamiento a una fecha, no a un evento.** Sirve el inicio del
   Plan Invierno. **Nunca una emergencia en curso.**
3. **A la prensa la gatilla un ángulo, no un producto.** Acá el ángulo es el
   vacío: Chile no tiene capa nacional de inundación, y Padre Las Casas —76.000
   habitantes, 38 puntos críticos crónicos, el máximo de la región— no tiene ni
   un documento.
4. **Buscar por dirección** es lo que vuelve personal un dato agregado.

### Lo que NO aplica, y por qué

- **Nada de gracia ni de meme.** Lo que hace compartible un completo hace
  desconfiable un mapa de riesgo.
- **Nada de aporte abierto sin curatoría.** Una reseña mala cuesta un mal
  completo; un polígono mal dibujado cuesta una casa comprada.
- **No perseguir el peak.** El tráfico de emergencia llega cuando la gente ya
  está mojada y no puede actuar. **El objetivo es que lo consulten en marzo, no
  en julio.**
- **Las visitas no son la métrica.** El éxito es que una junta de vecinos o una
  Dirección de Obras lo use, no seis mil visitas.

---

## 2. PWA o tienda

**Android 66,2 % contra iOS 33,8 %** en Chile (StatCounter, jul-2026 ✅). Dos de
cada tres usuarios tienen instalación de primera clase.

| Vía | Costo | Fricción real |
|---|---|---|
| **PWA** | 0 | Android instala solo; iOS exige Compartir → Agregar a inicio, a mano |
| Google Play (TWA) | USD 25 una vez | **12 testers reales durante 14 días seguidos** antes de producción ✅ |
| App Store | **USD 99 al año** | La exención de tarifa **excluye explícitamente a personas naturales** ✅; el nombre legal queda visible; los envoltorios se rechazan por la regla 4.2.2 ✅ |

**Dato que cambia el diseño**: en iOS la purga a 7 días borra `localStorage`,
IndexedDB y Cache API — **salvo si el sitio está en la pantalla de inicio**, que
queda con persistencia heurística ✅. Para un mapa que debe funcionar sin señal,
instalar **no es cosmético**: es la diferencia entre tener los datos o no
tenerlos cuando se corta la conexión. Hay que decírselo al usuario de iOS.

---

## 3. Lo que hoy impide publicar

Las dos dependencias externas prohíben justamente lo que el visor hace:

- **Nominatim** ✅ — máximo 1 petición por segundo, y **prohíbe explícitamente el
  autocompletado**. El buscador con sugerencias lo incumple.
- **Teselas de OSM** ✅ — prohíben prefetch y uso offline. La PWA lo incumple.
- **Esri World Imagery** — el satelital que se agregó tampoco admite tráfico de
  producción.

### La salida, sin costo

**Teselas: PMTiles propio.** Un archivo único servido estáticamente con
peticiones `Range`. La Araucanía a zoom 14 son unos **30-60 MB** (inferencia,
anclada en planeta = 120 GB ✅). Cero dependencias, cero costo, y **es lo único
que hace legítimo el modo sin señal**. Alternativa hosteada: **OpenFreeMap**, sin
clave, sin límite y con uso comercial permitido ✅ — pero es proyecto de una
persona y sin SLA.

**Direcciones: índice propio.** **OpenAddresses sí tiene Chile**, cobertura
nacional, atribuida al INE y sin *share-alike* ✅.

> ⚠️ **Y un hallazgo que cambia el diseño del buscador**: en La Araucanía hay
> 158.000 direcciones con número en OSM, pero **el 53 % está en la comuna de
> Temuco** (medido por Overpass, 25-ago-2026 ✅). Fuera de Temuco y Padre Las
> Casas la numeración es esquelética. **Buscar por localidad tiene que funcionar
> mejor que buscar por calle**, porque para la mayoría de la región la calle con
> número no existe en ningún índice.

El IDE Chile **no** sirve: su geocodificación delega en HERE ✅, así que no es
reutilizable por terceros.

---

## 4. A quién contactar

Todos verificados salvo donde se indica.

**La alianza natural: Kimün-Ko (UFRO)** ✅ — Observatorio de Recursos Hídricos de
La Araucanía; ya emite alertas y análisis de sistemas frontales y desbordes del
Trancura. Entrada por FICA UFRO. Ya estaba anotado en el inventario como
«contacto en terreno sin explorar»: es el momento.

**Radios** — UFRO Radio 89.3 (`ufroradio@ufrontera.cl`) es la mejor puerta:
medio universitario, sin costo, y conecta con Kimün-Ko. También Bío-Bío Temuco
88.1 (`internet@laradio.cl`) y las locales de Villarrica, Pucón, Lautaro y Angol.
Formato que les sirve: **cápsula de audio de 2 minutos lista para emitir**.

**Prensa regional** — El Austral de Temuco admite carta al director de 1.000
caracteres (`cartasdirector@australtemuco.cl`); Araucanía Diario
(`prensa@araucaniadiario.cl`); Araucanía Noticias
(`prensa@araucanianoticias.cl`). Formato: **una plana + tres capturas**.

**Municipios** — un tercero no integra el COGRID comunal; la vía real es que lo
lleve la Dirección de Emergencia comunal o SENAPRED regional. **AMRA** agrupa a
las 32 comunas. La puerta a las juntas de vecinos es la **DIDECO**, que por ley
asesora a las organizaciones comunitarias ✅.

**Rural** — los **comités de Agua Potable Rural** (Ley 20.998) son una red densa
en la región y llegan donde no llega el celular. Formato: **ficha imprimible A4 y
mapa impreso por sector**.

---

## 5. Lo legal, para un funcionario público

> ⚠️ Esto **no es asesoría legal**. La redacción final del aviso legal necesita
> abogado, o al menos un pronunciamiento de la jefatura, que es la vía barata de
> blindaje.

**La buena noticia, y es estructural**: la **inundación fluvial no es competencia
de SERNAGEOMIN** ✅. El DL 3.525 le entrega los peligros *geológicos*; las
crecidas son **DGA/MOP** y **SENAPRED** ✅. Por eso no se activa el gatillo del
art. 56 de la LOC 18.575, que prohíbe las actividades particulares sobre
«materias específicas o casos concretos que deban ser analizados, informados o
resueltos» por el organismo.

Condiciones que hay que cumplir, y que el proyecto ya cumple:

1. Fuera de la jornada de trabajo ✅ (art. 56 lo exige literalmente).
2. Con medios propios.
3. **Sin invocar el cargo ni marca institucional** — ya es la regla del proyecto.
4. Sin usar información no pública del Servicio.

**Palabras prohibidas en todo el sitio y en toda la difusión**: «alerta»,
«aviso», «pronóstico», «zona de evacuación». El **SAE es facultad exclusiva de
SENAPRED** ✅. Tampoco usar sus colores ni sus logos.

**Ley 21.719 de datos personales, vigente el 1-dic-2026** ✅: la geolocalización
es dato personal, con multas de hasta 20.000 UTM. El visor queda **fuera del
ámbito** si la consulta ocurre entera en el navegador y no se registra nada — sin
analytics, sin cookies, sin formularios, sin logs de dirección ni coordenada. Ya
es así; **conviene dejarlo escrito en el sitio** antes de esa fecha.

Sobre los descargos: sirven para fijar el estándar de diligencia y desmentir que
sea una alerta oficial, pero **no son escudo absoluto** ✅ — la doctrina chilena
anula las cláusulas que exoneran por culpa grave. La mitigación real es la que ya
hace el proyecto: **citar fuente y fecha de cada capa, mostrar la incertidumbre,
no dar veredictos por predio y no usar verbos de pronóstico.**

---

## 6. Orden sugerido

1. **PMTiles de La Araucanía + índice de direcciones propio.** Sin esto no se
   puede publicar: hoy se incumplen dos políticas de uso.
2. **Buscador por localidad**, no sólo por calle — el 53 % de las direcciones de
   la región están en una sola comuna.
3. **Aviso de privacidad** explícito, antes del 1-dic-2026.
4. **Hablar con Kimün-Ko** antes de cualquier difusión: valida y da respaldo.
5. **Lanzar anclado al Plan Invierno**, con el ángulo del vacío, nunca durante
   una emergencia.
