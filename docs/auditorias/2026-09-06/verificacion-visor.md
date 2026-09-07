# Verificación independiente del visor — 2026-09-06

Verificador con contexto limpio. **No leí ningún informe de los auditores**: recibí
sólo ID provisional, título y `archivo:línea`. Cada veredicto de acá abajo está
anclado a una línea que leí o a la salida cruda de un comando que corrí en esta
sesión.

**Instrumentos que escribí** (no tocan nada del sitio, sólo leen):

- `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas\tools\auditoria\verificacion_independiente_visor.py`
  — réplica del ray casting del frontend contra shapely, sensibilidad del veredicto
  al ruido del GPS, distancia al borde de la evidencia.
- `...\tools\auditoria\verificacion_navegador_visor.py`, `..._visor2.py`, `..._visor3.py`
  — reproducción en Chromium real sobre `python -m http.server 8795 --directory web`.

Convención de caminos que enumero en cada familia: **(a)** búsqueda por dirección
escrita, **(b)** Enter sin elegir sugerencia, **(c)** clic/toque en el mapa,
**(d)** «usar mi ubicación», **(e)** elegir una comuna (sugerencia o tabla de
portada), **(f)** tocar un polígono dibujado, **(g)** el texto que se reenvía por
WhatsApp, **(h)** sin red, **(i)** en celular.

---

## Tabla resumen

| ID | Familia | Grav. | Absorbe | Veredicto |
|---|---|---|---|---|
| **V-01** | El veredicto sólo mira cuatro de las siete capas que el visor dibuja | 5 | 101, 201, 601, 602 | CONFIRMADO |
| **V-02** | El texto que se reenvía pierde la advertencia y recorta la evidencia | 4 | 104, 202, 210 | CONFIRMADO |
| **V-03** | Anegamiento, marejada y napa se titulan «área de riesgo por inundación» | 4 | 105 | CONFIRMADO |
| **V-04** | El veredicto es binario, sin banda de borde, y se mueve con el ruido del GPS | 4 | 603, 304, 305, 607 | PARCIAL |
| **V-05** | Sin red el service worker responde `index.html`, y el visor lo da por cargado | 4 | 112, 214, 223, 213, 316 | CONFIRMADO |
| **V-06** | «Con qué cuenta» nombra la comuna equivocada y declara vacíos inexistentes | 4 | 103, 604, 204, 113 | CONFIRMADO |
| **V-07** | El botón «Buscar» no está enlazado a nada | 4 | 102 | CONFIRMADO |
| **V-08** | El año se firma como MINVU, sale del Atlas CIGIDEN, y si no hay polígono es el de otra comuna | 3 | 107, 205 | CONFIRMADO |
| **V-09** | Un número de calle inexistente devuelve la avenida entera sin avisar | 3 | 106, 217 | CONFIRMADO |
| **V-10** | Elegir una comuna produce un veredicto para un punto que nadie eligió | 3 | 110 | CONFIRMADO |
| **V-11** | El umbral configurado se muestra como si fuera lo medido | 3 | 309 | CONFIRMADO |
| **V-12** | El «error de ubicación» del plano es la precisión del ajuste, no la exactitud | 3 | 306 | CONFIRMADO |
| **V-13** | Enlaces que no llevan a ninguna parte | 3 | 111, 109 | CONFIRMADO |
| **V-14** | Un toque sobre el polígono dispara dos respuestas a la vez | 3 | 117 | CONFIRMADO |
| **V-15** | La capa derivada no declara peso legal y mezcla vigente con estudio | 3 | 114 | CONFIRMADO |
| **V-16** | El pie promete que la búsqueda ocurre en el dispositivo | 2 | 108 | CONFIRMADO |
| **V-17** | Mensajes de `#estado` pegados a acciones que no son la suya | 2 | 116 | CONFIRMADO |
| **V-18** | La espera al estilo del mapa llegó a dos casillas de ocho | 2 | 211, 212 | CONFIRMADO |
| **V-19** | La lista de sugerencias se reabre sola después de elegir | 2 | 209 | CONFIRMADO |
| **V-20** | Geometría inválida en tres capas | 2 | 606 | PARCIAL |
| **V-21** | La prueba e2e y el barrido no cubren lo que se agregó | 2 | 218, 605 | CONFIRMADO |
| **V-22** | Dos hojas de plano cubren el mismo punto y se muestra una | 2 | 206 | CONFIRMADO |
| **V-23** | 113 anillos interiores en las láminas vectorizadas | 2 | 608 | PARCIAL / SIN DATO |
| **V-24** | Geolocalización denegada: el mensaje viene en inglés | 1 | 118 | CONFIRMADO |
| **V-25** | Deuda menor de código | 1 | 222, 318 | CONFIRMADO |
| **V-26** | Palabras prohibidas por §7.2 en `web/` | 1 | 115 | **REFUTADO** |

Hallazgos propios: **V-N01 … V-N05** (al final).

Recuento: **26 familias** · 22 CONFIRMADAS · 1 REFUTADA · 2 PARCIALES · 1
PARCIAL-con-parte-SIN-DATO.

---

## V-01 · El veredicto sólo mira cuatro de las siete capas (GRAVEDAD 5) — CONFIRMADO

Absorbe **101, 201, 601, 602**.

**Archivo:línea** — `web/app.js:333-386` (`evaluar`), `web/app.js:657-1039` (`render`),
`web/app.js:1549-1565` (la capa `lam` sí se dibuja), `web/app.js:106` (`estado.laminas`
se carga).

`evaluar` calcula `gore` y `enMancha` (JRC) pero el `nivel` sólo puede salir de
`sar`, `areas` y los puntos críticos (líneas 357-378). `estado.laminas` no se
consulta **en ninguna parte** de `evaluar` ni de `render`: sólo existe para
pintarse en el mapa.

**Caminos**: se reproduce en (a), (b), (c), (d), (e), (g) y (i) — todos los caminos
de consulta, porque el defecto está en la función de decisión, no en la entrada.
Con y sin red da igual.

**Reproducción** — punto dentro del polígono AR-2a más grande de Angol
(-72.6867, -37.784993), que en `vectorizadas.geojson` trae
`"efecto_legal": "Zona restringida al desarrollo urbano. Los predios afectados
deben cumplir el artículo 2.1.17 de la OGUC…"` y `"anio": "2026"`:

```
### 601/602 — punto dentro del AR-2a VIGENTE del PRC de Angol (capa derivada)
  veredicto: Hay registros de inundación cerca
  por qué  : Hay 1 punto donde el municipio reportó inundación a menos de 500 metros.
  bloque A : Plan Regulador Comunal A · NORMATIVO
             Este punto no cae dentro de un área de riesgo por inundación
             declarada en el plan regulador.
  ¿el punto está dentro de una lámina, según el propio visor? 2
  clase GORE en ese punto: ['MAXIMA']
  ocurrencias de 'AR-2a' en la ficha: 0
```

Es decir: el visor **tiene** el polígono del plan regulador vigente de Angol y
**tiene** la clase máxima del modelo regional para ese mismo punto, y aun así le
imprime a la persona «este punto no cae dentro de un área de riesgo por
inundación declarada en el plan regulador». Angol no aparece en
`areas-riesgo-inundacion.geojson` (12 comunas, ninguna es Angol), así que para esa
comuna la única evidencia normativa que el proyecto tiene es justamente la que el
veredicto ignora.

```
$ python … origen_lamina
Counter({'angol-peligro-inundacion-2013': 98,
         'curarrehue-catripulli-inundacion-2025': 39,
         'angol-prc-ar2a-lamina1': 26})
$ comunas de areas-riesgo-inundacion.geojson
Counter({'Collipulli': 36, 'Carahue': 9, 'Pitrufquén': 4, 'Toltén': 4,
         'Loncoche': 2, 'Villarrica': 2, 'Temuco': 1, 'Nueva Imperial': 1,
         'Saavedra': 1, 'Renaico': 1, 'Traiguén': 1, 'Gorbea': 1})
```

Lo mismo vale para el GORE: el punto está en clase `MAXIMA` del modelo de ~35 m y
en el camino (g) el texto compartido no lo menciona nunca (`textoFicha`, 1043-1096,
sólo arma SAR, áreas y puntos críticos). La rama `sindato` de `porQue`
(`app.js:587`) llega a afirmar «ninguna de las fuentes consultadas registra
inundación en este punto» con el GORE diciendo lo contrario en la misma ficha.

---

## V-02 · El texto que se reenvía pierde la advertencia (GRAVEDAD 4) — CONFIRMADO

Absorbe **104, 202, 210**.

**Archivo:línea** — `web/app.js:1089` (`estado.ultimo.nivel`) contra `web/app.js:975`
(`estado.ultimo = { res, etiqueta, lon, lat }` — el nivel vive en `res.nivel`);
`web/app.js:1076-1085` (corte a 3 puntos) contra `web/app.js:871` (la pantalla dice
el total).

**Caminos**: (g) es el único camino donde se ve, pero se alcanza desde (a)-(f) e (i);
el botón «Compartir» está tanto en la respuesta corta (`app.js:611`) como en la
ficha (`app.js:967`).

**Reproducción** — punto sin registros (-71.60, -38.20):

```
  veredicto: Sin registros en las fuentes consultadas
  nivel: sindato · estado.ultimo.nivel: undefined
  ¿el texto compartido trae el 'OJO:'? False
  texto completo:
    SIN REGISTROS EN LAS FUENTES CONSULTADAS
    Ubicación: Cordillera
    El satélite no pasó por acá en la ventana del evento.
      No observado NO es lo mismo que no inundado.
    Sin puntos críticos registrados en 1,5 km.
    Esto NO es información oficial ni un pronóstico.
    En emergencia: SENAPRED y tu municipio.
```

`estado.ultimo.nivel` es `undefined` **siempre**, así que la condición de la línea
1089 nunca se cumple: la advertencia que el código dice explícitamente que tiene
que viajar por WhatsApp no viaja nunca. El titular en mayúsculas «SIN REGISTROS EN
LAS FUENTES CONSULTADAS» se reenvía solo.

Y el recorte (210), medido en el punto con más vecinos de la región:

```
  punto con más vecinos: [[-71.942799, -39.278511], 15]
  pantalla dice: 'Hay 15 puntos críticos registrados a menos de 1500 m'
  texto compartido:
    Puntos críticos registrados cerca:
    • 0 m — Inundación por desborde de cauce (riesgo Muy Alto)
    • 27 m — Inundación por desborde de cauce (riesgo Alto)
    • 65 m — Inundación por desborde de cauce (riesgo Muy Alto)
```

15 en pantalla, 3 en el texto, y el texto no dice que son 3 de 15.

---

## V-03 · Anegamiento, marejada y napa se titulan «inundación» (GRAVEDAD 4) — CONFIRMADO

Absorbe **105**.

**Archivo:línea** — `web/app.js:363-365` (titular), `web/app.js:571-573` (`porQue`),
contra `web/app.js:689-692` (el sello `FENOMENO` sólo se pinta en la pestaña de detalle).

**Caminos**: (a)-(f), (i). En (g) el texto compartido tampoco distingue
(`app.js:1069-1074` imprime `clasificacion` cruda, que sí dice ANEGAMIENTO — ese
camino se salva).

**Datos**: de los 63 polígonos, 6 no son fluviales
(`Counter({'fluvial': 57, 'anegamiento': 3, 'litoral': 2, 'napa_freatica': 1})`).

**Reproducción** — polígono ANEGAMIENTO de Temuco (-72.609107, -38.713381) y
polígono INUNDACION LITORAL de Toltén (-73.196158, -39.395615):

```
  veredicto: Estás en un área de riesgo por inundación del plan regulador
  por qué  : El plan regulador de tu comuna declaró esta zona área de riesgo
             por inundación. Es la única fuente con efecto legal.
  ¿aparece el sello 'anegamiento, no desborde' en el detalle? True

  y el litoral (Toltén):
  veredicto: Estás en un área de riesgo por inundación del plan regulador
```

El caso del litoral es el peor: una marejada se le presenta a la persona como
inundación fluvial en la respuesta corta, que es la que la mayoría lee. El detalle
lo corrige, pero el detalle está a un toque de distancia y el titular ya se leyó.

---

## V-04 · Veredicto binario, sin banda de borde, movido por el GPS (GRAVEDAD 4) — PARCIAL

Absorbe **603, 304, 305, 607**.

**Archivo:línea** — `web/app.js:357-378` (el veredicto), `web/app.js:17` (`RADIOS`,
sólo para puntos críticos), `web/app.js:145-153` (`dentroAnillo`, borde semiabierto),
`web/app.js:1321-1333` (`ubicarme` descarta `pos.coords.accuracy`),
`web/app.js:960-964` («Mira la mancha, no su borde», al final de la ficha).

**Caminos**: (c) y (d) son los que importan — «mi ubicación» trae un error de
decenas de metros en celular y el visor ni lo muestra ni lo usa. (a)/(b) heredan
además el error del geocodificador (ver V-09).

**Qué CONFIRMO**: `pos.coords.accuracy` está disponible en el mismo objeto
`pos.coords` del que la línea 1323 saca `longitude` y `latitude`, y no se lee
en ninguna parte (`grep accuracy web/app.js` → sin resultados). El borde es
semiabierto por la comparación estricta `lon <` y `(yi > lat) !== (yj > lat)`
de la línea 149-150. Y el salto de veredicto existe y es material:

```
=== C. distancia al borde más cercano de evidencia, para 'sindato' ===
  posiciones 'sindato' evaluadas: 235; a <100 m de un polígono de evidencia: 15
  ejemplos (lon,lat,metros al polígono):
    [(-72.68915, -38.27417, 91.7), (-72.96175, -38.09703, 9.1),
     (-73.00769, -38.76179, 96.3), (-72.20001, -38.94962, 16.4)]
```

Una posición a **9,1 m** del borde de un polígono de evidencia recibe «Sin
registros en las fuentes consultadas».

**Qué es PARCIAL**: no reproduzco el 14 % del hallazgo 304. Con mi diseño de
muestreo (400 posiciones sembradas a 0–1200 m de un punto crítico, salto de 50 m
en dirección aleatoria, semilla 20260906) mido:

```
=== B. cambio de veredicto al moverse 50 m (n=400 posiciones) ===
  21/400 = 5.2 % cambia de veredicto
  ejemplos: [(-71.73387, -39.34341, 'alto', 'medio'),
             (-73.16484, -39.26772, 'medio', 'alto'),
             (-72.97024, -38.75589, 'bajo', 'alto'),
             (-73.36498, -38.75656, 'medio', 'alto')]
```

El fenómeno está CONFIRMADO; la cifra concreta depende del diseño de muestreo y
yo mido 5,2 %, no 14 %. **305 no va aparte**: es el mismo defecto raíz.

---

## V-05 · Sin red, el service worker responde `index.html` (GRAVEDAD 4) — CONFIRMADO

Absorbe **112, 214, 223, 213, 316**.

**Archivo:línea** — `web/sw.js:82` (sólo `tile.openstreetmap.org` va a `CACHE_TILES`),
`web/sw.js:104-108` (`c.match(req) || c.match('index.html')`), `web/sw.js:16-18` y
`:64-70` (`activate` borra todo lo que no empiece por `VERSION`, incluidas las teselas),
`web/app.js:1034-1036` (el botón declara el plano cargado).

**Caminos**: (h) sobre todo, combinado con (c)/(f) — tocar la huella de un plano o
el botón «Ver el plano sobre el mapa» estando sin señal, que es exactamente el
escenario para el que el proyecto existe.

**Reproducción real** — cargué el visor, esperé al service worker y **apagué el
servidor** (la emulación offline de Playwright no llega al service worker; el primer
intento dio falsos «200 OK» y lo descarto como no medido):

```
  service worker: activo
  servidor apagado: True
  PNG de plano (no precacheado) -> {'ok': True, 'status': 200, 'tipo': 'text/html',
     'empieza': '<!doctype html>\r\n<html lang="es">\r\n<head>\r\n<meta charset="ut'}
  índice de planos (precacheado) -> {'ok': True, 'status': 200, 'tipo': 'application/json', …}
  json inexistente -> {'ok': True, 'status': 200, 'tipo': 'text/html', …}

  ¿qué pasa si se pide un plano estando sin red? (mostrarPlano)
   {'devolvio': True, 'estado': '', 'capaEnMapa': True}
```

Un PNG de plano se sirve como el HTML del sitio con **200 OK**, `mostrarPlano`
devuelve `true`, la capa queda agregada al mapa y el botón escribe **«Plano cargado
sobre el mapa»** — mientras la persona no ve ningún plano. Es literalmente el modo
de fallar que el comentario de `app.js:220-223` dice querer evitar.

Y el reparto de cachés (223 + 213 + 316), medido después de cambiar a satélite y
panear:

```
CACHES: {'riesgomapas-v21-app':   {'entradas': 34, 'esri': 12, 'osm': 0},
         'riesgomapas-v21-tiles': {'entradas': 2,  'esri': 0,  'osm': 2}}
base guardada en localStorage: satelite
#estado tras elegir satélite: ''
```

Las 12 teselas de Esri viven en la caché de la **app**, no en la de teselas. De ahí
salen tres consecuencias encadenadas: (1) `CACHE_APP` crece sin tope con imágenes
satelitales; (2) subir `VERSION` —obligatorio por §7.4 en cada cambio del frontend—
borra las dos cachés, o sea el mapa base offline se vacía en cada publicación;
(3) ninguna de las dos tiene tope de tamaño ni de edad, así que bajo presión de
almacenamiento el navegador puede desalojar el origen entero y llevarse el armazón
offline, que es el requisito de diseño número uno del proyecto. Además la base
satelital se recuerda en `localStorage` y al elegirla el visor no dice nada
(`aplicarBase`, 1448-1464, no escribe en `#estado`): sin señal, quien la dejó
activa abre un mapa en blanco y mudo.

---

## V-06 · «Con qué cuenta» nombra la comuna equivocada (GRAVEDAD 4) — CONFIRMADO

Absorbe **103, 604, 204, 113**.

**Archivo:línea** — `web/app.js:393-417` (`comunaDe`, punto crítico más cercano a
cualquier distancia), `web/app.js:958` (se llama con el resultado),
`web/app.js:426-480` (`bloqueComuna`), `scripts/19_estado_comunas.py:183-185`
(`if not con_area.get(k)`), `web/app.js:29-40` (el bbox incluye océano hasta −73,70).

**Caminos**: (a)-(f), (i); en (g) el bloque de comuna es además **la unidad que el
proyecto quiere que se comparta** (`app.js:419-424`), así que el error se propaga.

**Reproducción 1 — Plaza Aníbal Pinto, Temuco** (-72.5904, -38.7359):

```
   Con qué cuenta Padre Las Casas INVENTARIO
  comunaDe -> ['Padre Las Casas', 1.6]
  Temuco en estado-comunas -> [0, 1, []]
```

La capital regional recibe el inventario de la comuna vecina. Y su propia ficha
(`puntos_inundacion: 0`, `poligonos_area_riesgo: 1`, `le_falta: []`) haría decir al
visor «No detectamos vacíos en las fuentes que revisamos» (`app.js:466`) para
Temuco, cuyo único polígono MINVU es de **ANEGAMIENTO**, no de desborde: el script
19 cuenta cualquier polígono del archivo como «tiene su área de riesgo por
inundación». Temuco y Victoria (0 puntos críticos cada una) además **nunca** pueden
ser resueltas por `comunaDe`: no hay ningún punto propio que la devuelva.

**Reproducción 2 — un punto en el océano** dentro del bbox (-73.65, -38.9):

```
  veredicto: Sin registros en las fuentes consultadas
  aviso    : Que no haya registro no significa que acá no se inunde. Significa que
             nadie lo ha levantado. En comunas con poca capacidad técnica municipal
             es lo esperable.
  bloque comuna: Con qué cuenta Saavedra INVENTARIO … 13.228 habitantes
```

---

## V-07 · El botón «Buscar» no está enlazado (GRAVEDAD 4) — CONFIRMADO

Absorbe **102**.

**Archivo:línea** — `web/index.html:55` (`<button id="btn-buscar" type="button">Buscar</button>`),
`web/app.js:1900-1942` (`enlazarInterfaz` enlaza `#btn-ubicacion` en 1924 y el Enter
en 1934-1939; **no hay ningún `#btn-buscar`**), único uso en `app.js:1300-1311`
(sólo para deshabilitarlo dentro de `buscar()`).

**Caminos**: (a) escritorio con mouse → muerto. (b) Enter → funciona. (i) celular
con el teclado virtual en modo «search» (`enterkeyhint="search"`) → funciona, porque
dispara Enter. O sea: el camino que falla es el del dedo o el mouse sobre el botón
más visible de la página.

**Reproducción** (escritorio y celular 375×812 con toque):

```
### 102 — botón Buscar
  antes : |
  después: |
  ¿cambió algo? False
  listeners registrados en #btn-buscar: <button id="btn-buscar" type="button">Buscar</button>

--- 102 en celular (tap en Buscar)
  #estado: '' | #respuesta vacía: True
```

Ni siquiera aparece «Buscando la dirección…»: el clic no llega a ninguna parte.

---

## V-08 · El año se firma como MINVU y viene de otra parte (GRAVEDAD 3) — CONFIRMADO

Absorbe **107, 205**.

**Archivo:línea** — `web/app.js:720`
(`atribucion(estado.areasRiesgo, res.areas[0] || estado.areasRiesgo?.features[0])`),
`web/app.js:645-655` (`atribucion`), `scripts/06_areas_riesgo_prc.py:342-350`.

El script escribe `anio` desde `config/araucania.yaml → anio_instrumento_comuna` y
deja `anio_fuente = "Atlas del Riesgo de Desastre, Vicuña y Guzmán, CIGIDEN/IEUT-UC
2025"`; 59 de 63 polígonos lo llevan. `atribucion` imprime `fuente` (MINVU) y `anio`
(CIGIDEN) en la misma línea, sin nombrar nunca `anio_fuente`.

**Caminos**: (a)-(f), (i), con y sin red.

**Reproducción** — punto que NO cae en ningún área:

```
   Fuente: MINVU — áreas de riesgo de instrumentos de planificación territorial
   (Art. 2.1.17 OGUC) · Año: 2010 · datos obtenidos 2026-08-30
  features[0] de la capa: ['Temuco', 2010, 'Atlas del Riesgo de Desastre, Vicuña y
   Guzmán, CIGIDEN/IEUT-UC 2025']
```

El «Año: 2010» que se le muestra a alguien de Curarrehue es el del polígono de
Temuco, que es el primero del archivo. Y cuando sí cae dentro de un área, la ficha
imprime «Año: 2009» y cinco líneas más abajo «El año del plan regulador no está
declarado en la capa publicada por MINVU» (`app.js:725-730`): 53 de los 63 polígonos
cumplen las dos condiciones a la vez.

---

## V-09 · El número de calle inexistente devuelve la avenida entera (GRAVEDAD 3) — CONFIRMADO

Absorbe **106, 217**.

**Archivo:línea** — `web/app.js:1114-1126` (`geocodificar`: `limit=1`, `return j[0]`
sin mirar `addresstype`/`category`), `web/app.js:1297-1313` (`buscar` sólo distingue
«no encontró» de «encontró»), `web/app.js:1934-1939` (Enter sin sugerencia marcada
entra por acá).

**Caminos**: (b) es el camino real (V-07 mata el botón). (i) también, por el teclado
virtual. Sin red no aplica: Nominatim no se cachea (`sw.js:80`).

**Reproducción**:

```
  geocodificar('Balmaceda 500, Temuco') ->
    {'lon': -72.5998406, 'lat': -38.7312969,
     'etiqueta': 'Avenida Balmaceda, Villa Ñielol, Centro, Temuco, Provincia de
                  Cautín, Región de la Araucanía, 4800996, Chile'}
```

El «500» desapareció y la etiqueta que se pinta en la ficha (`📍 …`) y viaja en el
texto compartido dice «Avenida Balmaceda» a secas. La persona cree que consultó su
casa y consultó un punto arbitrario del eje de la avenida.

---

## V-10 · Elegir una comuna produce un veredicto para un punto que nadie eligió (GRAVEDAD 3) — CONFIRMADO

Absorbe **110**.

**Archivo:línea** — `web/app.js:1871-1892` (`zoomComuna` calcula el centro del bbox de
los puntos críticos de la comuna y llama a `consultar`), llamado desde
`app.js:1145` (sugerencias) y desde `app.js:1805` (**tabla de comunas de la portada**
— dos caminos, no uno).

**Caminos**: (e) por sugerencia y (e) por la tabla de portada.

**Reproducción**:

```
### 110 — elegir la comuna ANGOL en las sugerencias
  veredicto: Registros de inundación a cierta distancia
  dirección: 📍 ANGOL (centro de los registros de la comuna)
  por qué  : El registro más cercano de inundación está a 909 metros.
```

La etiqueta avisa entre paréntesis, pero el veredicto con ícono y color es un
veredicto de nivel sobre una coordenada que la persona no pidió, y es compartible
con el mismo botón que cualquier otro.

---

## V-11 · El umbral configurado se muestra como si fuera lo medido (GRAVEDAD 3) — CONFIRMADO

Absorbe **309**.

**Archivo:línea** — `web/app.js:776-783` («el eco del radar cayó
{Math.abs(p.caida_db)} dB»), `scripts/14_sar_huella_observada.py:800-801`
(`"caida_db": float(cfg_sar["caida_db"])`), `config/araucania.yaml:158`
(`caida_db: -3.0`).

**Datos**: los 1075 polígonos de la huella traen exactamente el mismo valor.

```
SAR n: 1075 caida_db: Counter({-3.0: 1075}) umbral: Counter({-22.0: 725, -20.1: 350})
```

**Caminos**: (a)-(f), (g) no (el texto compartido no lo incluye).

La frase de pantalla es la evidencia más fuerte que ofrece el visor y está redactada
como una medición del píxel consultado («el eco del radar **cayó** 3 dB»), cuando es
el umbral de decisión que se le impuso al detector. El `umbral_agua_db` sí varía por
pasada (−22,0 / −20,1) y ése sí es un valor calculado.

---

## V-12 · El «error de ubicación» del plano es la precisión del ajuste (GRAVEDAD 3) — CONFIRMADO

Absorbe **306**.

**Archivo:línea** — `web/app.js:856-859` («error de ubicación {rmse_loo_m} m»),
`web/catalogo.js:46` (idem en el catálogo), `scripts/georref.py:49-54` (`clasificar`:
<10 m = «apto para consulta a nivel de predio»), `scripts/georref.py:58-87`
(`metricas`: el leave-one-out saca un punto de control y **reajusta**).

**Mecanismo, verificado leyendo el código**: los puntos de control son los rótulos de
la retícula UTM impresa. El LOO mide el residual de un rótulo contra el ajuste de
los demás rótulos. Un corrimiento sistemático que afecte a **todos** los rótulos por
igual —el offset del renderizado del texto respecto de la línea de grilla— lo absorbe
el término de traslación del ajuste y **no deja residual**: el LOO no puede verlo por
construcción. Los 20 planos publicados están clasificados «predial»:

```
aptitud: Counter({'predial': 20})
rmse: [0.19, 0.11, 0.03, 0.04, 0.03, 0.04, 1.61, 1.81, 1.31, 1.52, 0.17, 0.18, …]
```

**Magnitud, calculada por mí**: `scripts/08_georreferenciar_grilla.py:59` fija
`DPI = 300`, y `resolucion_m_px` va de 0,212 a 0,773 m/px. Un corrimiento de 1 punto
tipográfico = 1/72 pulgada = 4,17 px a 300 dpi = **0,9 a 3,2 m en el terreno**, entre
5 y 30 veces el «error de ubicación» que la ficha declara (0,19 m en el ejemplo de
Traiguén). El número mostrado no es una cota de la exactitud del plano y sirve de
base a la clasificación «apto para consulta a nivel de predio», que es justo la
decisión que este visor quiere apoyar.

---

## V-13 · Enlaces que no llevan a ninguna parte (GRAVEDAD 3) — CONFIRMADO

Absorbe **111, 109**.

**Archivo:línea** — `web/app.js:697-699` (`Ver ordenanza`), `web/catalogo.js:64`
(`href="${esc(d.url)}"`) y `web/catalogo.js:40` (`href="${esc(urlDoc)}#page=${l.pagina}"`).

**111** — 9 de los 63 polígonos (los de Collipulli) traen `ordenanza_url`, todos la
misma, y ninguno tiene `ordenanza_url_vigente: true`:

```
  polígonos con ordenanza_url: 9
  URL: ['http://www.observatoriourbano.cl/Ipt/cehu_resultado_decreto.asp?r=9&c=29&i=25']
  ordenanza_url_vigente: 0

$ curl -sL …
final=404 url=https://observatoriourbano.cl/Ipt/cehu_resultado_decreto.asp?r=9&c=29&i=25
<title>404 — OBSERVATORIOURBANO.CL</title>
```

**109** — 38 documentos de 354 tienen `url` vacía; en `documentos.html` eso produce
`href=""`, que recarga la página, y una lámina cuelga de un documento sin URL, con lo
que el enlace «pág. N →» queda como `#page=60` sobre la propia página del catálogo:

```
  docs totales: 354 sin url: 38 laminas colgando de docs sin url: 1
  {'total': 579, 'vacios': 39,
   'ejemplos': [['', '', 'http://localhost:8795/documentos.html'],
                ['#page=60', '', 'http://localhost:8795/documentos.html#page=60'], …]}
```

---

## V-14 · Un toque sobre el polígono dispara dos respuestas (GRAVEDAD 3) — CONFIRMADO

Absorbe **117**.

**Archivo:línea** — `web/app.js:1576-1588` (popup de `ar-fill`), `web/app.js:1602-1610`
(popup de `camp-fill`), `web/app.js:1678-1683` (el clic general excluye sólo `pc-circ`
y `huellas-fill`).

**Caminos**: (f) en escritorio y celular. `camp-fill` tiene el mismo problema y no
estaba en el hallazgo: son dos capas, no una.

**Reproducción** sobre un polígono de Carahue:

```
{'featuresBajoElDedo': 1, 'popupsAbiertos': 1,
 'respuestaRepintada': '⚠️\nEstás en un área de riesgo por inundación del plan regula'}
```

Un toque abre el globo **y** repinta la ficha completa desplazando lo que la persona
estaba leyendo. En celular el globo tapa además el punto que se tocó.

---

## V-15 · La capa derivada no declara su peso legal (GRAVEDAD 3) — CONFIRMADO

Absorbe **114**.

**Archivo:línea** — `web/data/laminas/vectorizadas.geojson`,
`web/index.html:111-113` (el sello «derivado» sólo en la casilla de capas),
`REGLAS.md §1.5` («Va escrito en el dato (`estado_tramite`) y visible en pantalla con
texto, no sólo color»).

```
keys: {'clase': 163, 'comuna': 163, 'amenaza': 163, 'fuente': 163, 'anio': 163,
       'metodo_original': 137, 'escala_original': 163, 'hectareas': 163,
       'origen_lamina': 163, 'descripcion': 26, 'efecto_legal': 26}
```

Ningún feature trae `estado_tramite`. Y hay algo peor que el campo faltante, que
anoto como hallazgo propio en **V-N01**: los 26 polígonos con `efecto_legal` son del
PRC **vigente** de Angol y el `procedencia.incertidumbre` del archivo declara en
bloque «PRODUCTO DERIVADO … NO tiene el efecto legal del vectorial del MINVU» para
los 163.

---

## V-16 · El pie promete privacidad que el código no cumple (GRAVEDAD 2) — CONFIRMADO

Absorbe **108**.

**Archivo:línea** — `web/index.html:301-303` («Este sitio no registra nada: la
búsqueda y la consulta ocurren en tu dispositivo, no se guarda tu dirección ni tu
ubicación»), contra `web/app.js:1117-1121` (`geocodificar` pone la dirección completa
en la URL a `nominatim.openstreetmap.org`) y `web/app.js:1160-1163`
(`sugerenciasDirecciones` manda **cada fragmento** mientras se escribe, cada 450 ms).

**Caminos**: (a), (b) y sobre todo el autocompletado, que se dispara con sólo
enfocar el campo (`app.js:1928`). No hay red → no sale nada (`sw.js:80` no cachea).

La consulta de riesgo sí ocurre en el dispositivo. La **búsqueda** no: la dirección
y sus prefijos van a un tercero con IP y user-agent. La frase del pie es más
absoluta que la realidad, y `REGLAS.md §7.5` la respalda invocando la Ley 21.719.
No es que el sitio guarde nada; es que promete algo que no controla.

---

## V-17 · Mensajes de `#estado` pegados (GRAVEDAD 2) — CONFIRMADO

Absorbe **116**. `web/index.html:60` es un único `<p>` que escriben ~20 sitios de
`app.js` y casi nadie limpia.

```
  #estado tras una consulta nueva: 'Mostrando 3 de 7 planos; acerca más para el resto.'
  #estado tras encender la capa JRC: 'No hay planos de plan regulador en esta zona.'
```

Es un `role="status" aria-live="polite"`: quien usa lector de pantalla escucha un
mensaje viejo como si fuera la respuesta a lo que acaba de hacer.

---

## V-18 · La espera al estilo llegó a dos casillas de ocho (GRAVEDAD 2) — CONFIRMADO

Absorbe **211, 212**. `#cap-sar` (`app.js:1735-1739`) y `#cap-planos`
(`app.js:1760-1770`) esperan al `idle` del estilo; `alternar()` (`app.js:1693-1697`)
y los manejadores de `#cap-derivadas`, `#cap-camp` y `#cap-areas` sólo comprueban
`m.getLayer(capa)` y, si aún no existe, **no hacen nada y no dicen nada**: la casilla
queda marcada y la capa apagada. `#btn-capas-todas` (`app.js:1922`) dispara las ocho
de una vez, que es cuando más probable es. Y `actualizarPlanos` (`app.js:277`)
conserva la guarda `!m.isStyleLoaded()` que `ocultarPlanos` documenta en 244-251 como
la causa de una limpieza que se saltaba entera y en silencio.

---

## V-19 · La lista de sugerencias se reabre sola (GRAVEDAD 2) — CONFIRMADO

Absorbe **209**. `cerrarSugerencias` (`app.js:1219-1227`) no hace
`clearTimeout(SUG.timer)`, y el temporizador de 450 ms de `pedirSugerencias`
(`app.js:1243-1247`) repinta si `$('#q').value === texto` — condición que se cumple
siempre al elegir una **comuna**, porque esa rama no cambia el valor del campo
(sí lo cambia la rama de dirección, `app.js:1173`).

```
  visible al escribir=True · tras elegir=False · 1,6 s después=True (items=2)
```

En celular la lista vuelve a taparle la respuesta que acaba de pedir.

---

## V-20 · Geometría inválida en tres capas (GRAVEDAD 2) — PARCIAL

Absorbe **606**. Confirmo la invalidez y **refuto que cambie lo que se le dice a la
persona**, al menos en 160.280 puntos de prueba.

```
gore:        n=2539 invalidos=198  ej=[(0, 'Ring Self-intersection[-73.09633 -38.64726]')]
sar:         n=1075 invalidos=585  ej=[(3, 'Interior is disconnected[-72.4931 -37.6659]')]
cobertura:   n=115  invalidos=59
areas: 0 · laminas: 0 · jrc: 0 · campamentos: 0

=== A. ray casting del visor vs shapely (make_valid) ===
  gore:          puntos=101560 discrepancias=0 (0.000 %)
  sar:           puntos=43000  discrepancias=0 (0.000 %)
  cobertura-sar: puntos=4600   discrepancias=0 (0.000 %)
  areas-riesgo:  puntos=2520   discrepancias=0 (0.000 %)
  laminas:       puntos=6520   discrepancias=0 (0.000 %)
  jrc:           puntos=2080   discrepancias=0 (0.000 %)
```

Reimplementé `dentroAnillo`/`poligonosQueContienen` tal cual están en
`web/app.js:145-169` y las comparé contra `shapely.make_valid(...).contains`. Cero
discrepancias. La invalidez es real y le rompe la vida a cualquier consumidor
downstream que no llame a `make_valid` —incluidos los propios instrumentos de
auditoría—, pero el veredicto que ve la persona no cambia por eso.

---

## V-21 · La e2e y el barrido no cubren lo que se agregó (GRAVEDAD 2) — CONFIRMADO

Absorbe **218, 605**.

`tests/auditoria_e2e.py:137-139` espera `osm, pc-circ, ar-fill, huellas-fill,
camp-fill, sar-fill, sar-line, gore-fill`: no `jrc-fill` ni `lam-fill`. En todo el
archivo no aparece `textoFicha` ni ninguna consulta dentro de una lámina
(`grep textoFicha\|lam-fill\|jrc-fill tests/auditoria_e2e.py` → sólo dos
coincidencias, ambas de `estado.laminas` en 457-458, que comprueban que el archivo
existe y que el borde va punteado). Por eso los 273 OK de hoy conviven con V-01 y
V-02 sin verlos.

`tools/auditoria/raycasting_vs_shapely.py:44-51` define `CAPAS` con seis entradas y
**no incluye `sar/cobertura-sar.geojson`** (59 de 115 features inválidos) ni ninguna
capa JRC distinta de `rp100`. La cobertura SAR es la que decide la frase «el
satélite sí miró este punto y no detectó agua», que es una afirmación fuerte.

---

## V-22 · Dos hojas cubren el mismo punto y se muestra una (GRAVEDAD 2) — CONFIRMADO

Absorbe **206**. `web/app.js:844-845` (`const p = res.planos[0]`) con el encabezado
singular «El plano de tu comuna» en 851, mientras `planosQueCubren`
(`app.js:176-181`) devuelve todas las que cubren el punto.

```
PLANOS n= 20 · pares de hojas que se traslapan: 12
   ('04_Anteproyecto-Plano_Actualizacion_PRC_Traiguen.pdf_p001.png',
    '04_Anteproyecto_Planos_PRC_Traiguen.pdf_p001.png')
   ('04_Anteproyecto-Planos_PRC_Pitrufquen_2_p001.png',
    '04_Anteproyecto-Planos_PRC_Pitrufquen_p001.png')
   ('04_Anteproyecto-Planos_PRC_Pucon_v3.pdf_p001.png',
    '04_Anteproyecto-Planos_PRC_Pucon_v4.pdf_p001.png')  …
```

Son versiones distintas del mismo anteproyecto (Pucón v3 y v4, Traiguén en dos
archivos). El visor muestra la primera por orden alfabético del glob, sin decir que
hay otra ni cuál es más nueva.

---

## V-23 · 113 anillos interiores en las láminas (GRAVEDAD 2) — PARCIAL / SIN DATO

Absorbe **608**. Confirmo la medición y **no puedo verificar el encargo**: la cifra
«17» vive en el pedido que se le hizo a quien vectorizó, y no la encuentro en ningún
documento del repo fuera de `docs/auditorias/`, que no debo abrir.

```
poligonos: 163  anillos interiores (huecos): 113
```

Lo medible: hay 113 huecos, todos los polígonos son geométricamente válidos, y un
hueco mal puesto es un «no cae dentro» para alguien que sí está dentro. Que sean 113
y no 17 es una diferencia de un factor 6,6 respecto de lo que el hallazgo dice que
se encargó; si el encargo decía 17, alguien tiene que mirar los 96 restantes uno por
uno. Queda **SIN DATO** el contraste con el encargo.

---

## V-24 · Geolocalización denegada, en inglés (GRAVEDAD 1) — CONFIRMADO

Absorbe **118**. `web/app.js:1331` pega `err.message` del navegador tal cual.

```
  #estado: 'No se pudo obtener la ubicación (User denied Geolocation).'
  idioma de la página: es
```

---

## V-25 · Deuda menor de código (GRAVEDAD 1) — CONFIRMADO

Absorbe **222, 318**.

- **222**: `web/app.js:49-64` declara 12 claves; `areasRiesgo` (89), `planos` (95) y
  `campamentos` (114) se crean al vuelo. Todas las lecturas están guardadas, así que
  hoy no rompe nada; es legibilidad.
- **318**: `web/app.js:578-579` escribe «a menos de 500 metros» a mano mientras el
  filtro usa `RADIOS.medio` (`app.js:17`). Hoy coinciden. El día que alguien cambie
  el radio, la frase queda mintiendo sin que ninguna prueba lo note.

---

## V-26 · Palabras prohibidas por §7.2 — **REFUTADO** (GRAVEDAD 1)

Absorbe **115**. `REGLAS.md §7.2` dice «Nunca las palabras "alerta", "aviso",
"pronóstico" ni "zona de evacuación"». Busqué las cuatro en todo `web/`:

```
$ grep -n -i alerta web/index.html web/app.js web/catalogo.js web/documentos.html
web/index.html:278:       la alerta.</p>
$ grep -n -i pron web/index.html web/app.js
web/index.html:75:     y <strong>no es un pronóstico</strong>. Es un proyecto abierto y personal.
web/index.html:138:        <span class="grupo-nota">escenarios, no pronósticos</span></p>
web/index.html:222:       un pronóstico: es la conclusión de un estudio, con su fecha y su método.</p>
web/app.js:554:    'No es información oficial ni un pronóstico.');
web/app.js:955:     ninguna de ellas es un pronóstico, y que el borde de la mancha es justo
web/app.js:1093:  l.push('', 'Esto NO es información oficial ni un pronóstico.',
$ grep -n -i evacu web/index.html web/app.js
(sin resultados)
$ grep -n -i aviso …
web/app.js:605, 860  →  ambos son la clase CSS `aviso-fuerte`
```

**Las seis apariciones de «pronóstico» son negaciones** («no es un pronóstico»,
«escenarios, no pronósticos»), que es precisamente lo que la regla persigue; y
«alerta» aparece una vez, atribuyéndole a SENAPRED la competencia que la regla
protege («la DGA para la amenaza, el MINVU para el instrumento, SENAPRED para la
alerta»). Borrarlas empeoraría el sitio. La regla, leída al pie de la letra, es más
ancha que su propósito. **REFUTADO** como defecto; si acaso, lo que hay que corregir
es el texto de la regla, no el del visor.

---

# Hallazgos propios del verificador

## V-N01 · El archivo «derivado» mezcla el PRC vigente de Angol con un estudio de 2013 (GRAVEDAD 4)

`web/data/laminas/vectorizadas.geojson`. Los 163 polígonos comparten un único
`procedencia.incertidumbre`: «PRODUCTO DERIVADO … NO tiene el efecto legal del
vectorial del MINVU». Pero 26 de ellos son del **plan regulador vigente**:

```
origen_lamina: Counter({'angol-peligro-inundacion-2013': 98,
                        'curarrehue-catripulli-inundacion-2025': 39,
                        'angol-prc-ar2a-lamina1': 26})
ejemplo con efecto_legal:
 {"clase": "AR-2a",
  "descripcion": "Áreas de Riesgo Inundables o Potencialmente Inundables",
  "fuente": "Plan Regulador Comunal de Angol, Plano de Zonificación y Vialidad
             lámina PRC 09201-1, aprobado por la SEREMI de Vivienda y Urbanismo…",
  "anio": "2026",
  "efecto_legal": "Zona restringida al desarrollo urbano. Los predios afectados
                   deben cumplir el artículo 2.1.17 de la OGUC…"}
```

El contenido de esos 26 **sí** tiene efecto legal (lo nuestro es el trazado, no la
norma). Meterlos bajo el descargo general y sin `estado_tramite` hace lo contrario
de lo que §1.5 busca: en vez de sobrevender un anteproyecto, **subvende** la única
evidencia normativa que existe para Angol. Junto con V-01, el resultado es que a un
vecino de Angol parado dentro de un AR-2a el visor le dice que no está en ninguna
área de riesgo declarada.

## V-N02 · «Plano cargado sobre el mapa» cuando no se cargó nada (GRAVEDAD 3)

Medido en V-05: sin red, `mostrarPlano` (`app.js:209-233`) devuelve `true` y el botón
escribe «Plano cargado sobre el mapa» (`app.js:1035`) porque el service worker le
entregó `index.html` con 200 OK en vez del PNG. La persona ve el mapa sin plano y un
botón que le dice que sí está.

## V-N03 · El veredicto fantasma de comuna tiene dos puertas, no una (GRAVEDAD 2)

`zoomComuna` se llama desde las sugerencias (`app.js:1145`) **y desde la tabla de
comunas de la portada** (`app.js:1805`). El hallazgo 110 apuntaba sólo a la primera.
La tabla de portada es el elemento más visible de la página de inicio.

## V-N04 · Temuco y Victoria no pueden ver nunca su propio inventario (GRAVEDAD 2)

`comunaDe` resuelve por el punto crítico más cercano. En `indice-comunas.json`,
Temuco y Victoria tienen `puntos_inundacion: 0`, así que **ninguna consulta** puede
devolverlas: el bloque «Con qué cuenta» de la capital regional siempre será el de
otra comuna. Medido: Plaza de Temuco → Padre Las Casas a 1,6 km.

## V-N05 · La base satelital recordada deja el mapa mudo sin señal (GRAVEDAD 2)

`aplicarBase` (`app.js:1448-1464`) guarda la preferencia en `localStorage` y no
escribe nada en `#estado`. Medido: `base guardada en localStorage: satelite` y
`#estado tras elegir satélite: ''`. Combinado con `sw.js:82` (sólo OSM va a la caché
de teselas), quien dejó la vista satelital abre el visor durante un corte y recibe un
lienzo vacío sin ninguna explicación. Es el escenario para el que existe el proyecto.

---

# Verificado limpio

Cosas que revisé a propósito y que **no** tienen defecto que reportar:

- **El ray casting del frontend** (`app.js:145-169`) coincide con shapely en 160.280
  puntos de prueba sobre las seis capas de polígonos, incluidas las 842 features
  inválidas. La regla par-impar con exclusión de anillos interiores está bien
  implementada (ver salida cruda en V-20).
- **`fechaLarga`** (`app.js:311-316`) parsea a mano en vez de con `new Date`, así que
  no corre el día hacia atrás por UTC. Devuelve `null` en vez de inventar año.
- **`esc()`** (`app.js:635-638`) escapa `& < > " '` y está aplicada en todos los
  `innerHTML` que interpolan propiedades del dato, incluidos los popups
  (1576-1588, 1602-1610, 1631-1644). No encontré ninguna interpolación sin escapar de
  contenido que venga del GeoJSON.
- **`dentroDeRegion` y `renderFuera`** (`app.js:37-40`, `1261`, `1270-1295`): un punto
  fuera del bbox no recibe «sin riesgo» sino «este sitio no tiene nada que decir», y
  `estado.ultimo = null` impide compartir una ficha vacía. Bien resuelto.
- **`ocultarPlanos`** (`app.js:235-261`): libera fuente y capa en vez de ocultarlas, y
  reintenta en `idle`. El comentario explica por qué no lleva la guarda de estilo y
  es correcto.
- **`renderCifras`** (`app.js:1812-1848`): las cifras de portada se calculan del dato
  cargado, no están escritas a mano, y la de hogares se omite si es cero.
- **Errores de JavaScript**: cero `pageerror` en las tres sesiones de navegador
  (`### errores de JavaScript: []`), salvo el que provoqué yo pasándole a `zoomComuna`
  una comuna inexistente.
- **`sugerenciasDirecciones`** (`app.js:1153-1178`) aborta la petición anterior con
  `AbortController`, así que escribir rápido no deja ganar a una respuesta vieja.
- **§7.3** (autoría y «que deje de hacer falta») está cumplida en `index.html:274-280`
  y en el pie.
