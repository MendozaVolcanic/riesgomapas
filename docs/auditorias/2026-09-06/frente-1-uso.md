# Auditoría 2026-09-06 · Frente 1 — POR USO: promesa → supuesto → control

Rama `visor-simple-y-laminas-vectorizadas`, árbol limpio al empezar (HEAD `b293aad`).
Visor servido con servidor propio en `http://127.0.0.1:8791` (mismo `SimpleHTTPRequestHandler`
que usa la e2e) y ejercitado con Playwright/Chromium, esperando siempre por contenido
(`wait_for_function`), salvo en dos pruebas de **ausencia** que se declaran abajo.

Instrumentos escritos en esta sesión (quedan en `tools/auditoria/`, con las dos preguntas del
instrumento en su docstring):

| Instrumento | Qué mide | Salida cruda |
|---|---|---|
| `tools/auditoria/inventario_propiedades_veredicto.py` | qué campos trae cada GeoJSON que `app.js` lee | stdout (pegado abajo donde se cita) |
| `tools/auditoria/uso_veredicto_por_punto.py` | veredicto, ficha y texto compartido para 9 puntos; geolocalización; buscador con y sin red; capas; clic en el mapa; cifras | `tools/auditoria/evidencia_uso/0N_*.txt` + `.png`, `resultados.json`, `corrida_arnes.log` |
| `tools/auditoria/uso_sin_senal.py` | qué llega a la ficha sin red, contenido de la caché del SW, satélite y catálogo sin red | `tools/auditoria/evidencia_uso/resultados_offline.json`, `15_offline_*.png/.txt` |
| `tools/auditoria/enlaces_publicados_responden.py` | código HTTP de «Ver ordenanza» y de una muestra del catálogo | stdout (pegado abajo) |

Las pruebas del proyecto (63 pytest · 151 datos · 273 e2e) **no se volvieron a correr**; se leyeron
para saber qué cubren. Lo que la e2e NO mira y acá sí: el texto que se comparte, la capa derivada
dentro del veredicto, el botón «Buscar», la comuna que atribuye el inventario, el buscador con
número de casa, el modo sin señal de punta a punta, los enlaces externos.

---

## 1. Tabla promesa → supuesto → control, por acción visible

| # | Acción / etiqueta | Qué promete | Qué supone | Control si el supuesto falla | Qué se ve si se rompe | Estado |
|---|---|---|---|---|---|---|
| 1 | Campo «Escribe tu dirección…» + **Enter** | ubicar la dirección en La Araucanía | red + Nominatim + que OSM tenga esa calle y ese número | mensaje en `#estado` («No se pudo buscar… Prueba tocando el mapa» / «No se encontró…») | ok sin red (medido) · **con red devuelve la calle aunque el número no exista, sin avisarlo** | H-106 |
| 2 | Botón **«Buscar»** (`index.html:55`) | lo mismo que Enter | que exista un manejador de clic | ninguno | **no hace nada, sin mensaje** | H-102 |
| 3 | Sugerencias al escribir (comunas / direcciones) | comunas al instante y sin señal; direcciones con red | comunas: `indice-comunas.json` cargado; direcciones: Nominatim | direcciones fallidas se callan (`app.js:1177`) | ok: sin red salen comunas (medido) | limpio / H-108 |
| 4 | Elegir una **comuna** sugerida | «responde, no sólo mueve el mapa» | que el centro del bbox de sus puntos críticos represente algo | ninguno | veredicto de nivel para un punto que nadie eligió | H-110 |
| 5 | «Usar mi ubicación actual» | consultar donde estoy | permiso + GPS + estar en la región | mensajes: fuera de región / denegado / sin API | ok (medido); mensaje de denegación en inglés | H-118 |
| 6 | Tocar el mapa | consultar ese punto | mapa WebGL vivo; punto dentro del bbox | fuera de bbox → «Fuera del alcance»; sin WebGL → aviso | ok (medido) · sobre un polígono MINVU abre popup **y** consulta a la vez | H-117 |
| 7 | **Veredicto** (título, nivel, color, «por qué») | decir qué dicen las fuentes de ese punto | que TODAS las capas publicadas entren a `evaluar()` | ninguno | **la capa derivada no entra: sobre la mancha de Angol dice «no cae dentro»** | H-101 |
| 8 | Bloque «Plan Regulador Comunal A · NORMATIVO» | polígono MINVU + fuente + año | polígono con `anio` | «no declarado por la fuente» cuando el campo lo dice | **sin polígono, muestra el año del primer polígono de la capa (otra comuna)** | H-107 |
| 9 | Título «área de riesgo por inundación» | inundación fluvial (alcance declarado del sitio) | `tipo_hidrico === 'fluvial'` | el sello «anegamiento, no desborde» sólo en la pestaña de detalle | **respuesta corta llama «inundación» a un polígono de anegamiento / litoral / napa** | H-105 |
| 10 | Bloque «Huella observada B» (3 estados) | vio agua / miró y no vio / no pasó | `sar`, `cobertura-sar`, `indice.json` | los 3 textos existen y se ven (medidos en 01, 07) | limpio | — |
| 11 | Bloque «Con qué cuenta [comuna] · INVENTARIO» | inventario de **tu** comuna | que el punto crítico más cercano sea de tu comuna | «el nombre va en grande» (comentario `app.js:402-404`) | **Temuco (292 mil hab., 0 puntos críticos) sale como Padre Las Casas** | H-103 |
| 12 | «Compartir» / «Compartir esta ficha» | «dice exactamente lo mismo que la pantalla» | `estado.ultimo.res.nivel` | — | **en «sin registros» el texto compartido pierde el «OJO: no significa que no se inunde»** | H-104 |
| 13 | «Compartir el estado de la comuna» / «Pedirle el mapa a la autoridad» | texto Ley 20.285 al portapapeles | clipboard/share; comuna correcta (ver 11) | «No se pudo copiar automáticamente» | hereda H-103 | — |
| 14 | «Ver ordenanza» (capa A) | abrir la ordenanza | que `ordenanza_url` responda | ninguno | **404** | H-111 |
| 15 | Pestañas «¿Se inunda?» / «Detalle y fuentes» | ficha corta / evidencia completa | — | foco y `hash` | ok (medido en cada consulta) | limpio |
| 16 | Casillas de capas (8) + «Encender/Apagar todo» | dibujar la capa | que la capa exista en el estilo | SAR, derivadas y planos avisan si falta; JRC/GORE/campamentos/puntos/áreas callan | con los datos actuales las 8 se dibujan (medido) | H-116 (mensajes pegados) |
| 17 | «Satélite, color real» | imagen satelital | red a Esri; **no se cachea** | ninguno | sin señal: mapa en blanco, sin mensaje | H-112 |
| 18 | Cifras de portada, `#sello-datos`, `#nota-sar` | contadas del dato | — | — | ok: 440 · 211 · 63 en 12 · 20 · 5.776 · 537 (medido) | limpio |
| 19 | Modo sin señal (PWA) | «funciona sin señal» | SW instalado y precaché completo | «Cargando…» / «No se pudieron cargar» | **todas las capas llegan sin red** (medido, ver VERIFICADO) | limpio |
| 20 | Modo oscuro / celular | contraste y layout | — | — | cubierto por e2e (3 perfiles); no medido acá | SIN DATO |
| 21 | «Imprimir o guardar como PDF» | ficha con fuentes en papel | `@media print` (`style.css:627`) | — | no medido el PDF real | SIN DATO |
| 22 | Catálogo `documentos.html`: enlace al PDF `#page=N` | «enlace directo al PDF oficial» | `d.url` absoluta y viva | ninguno | **38 documentos con URL vacía: el enlace recarga la página** | H-109 |
| 23 | Pie: «no se guarda tu dirección… la búsqueda ocurre en tu dispositivo» | privacidad §7.5 | — | — | el sitio no guarda nada (verificado), **pero la dirección viaja a Nominatim, letra a letra** | H-108 |

---

## 2. Hallazgos (ordenados por gravedad; IDs provisionales 101…)

### H-101 · La capa derivada (láminas vectorizadas) no entra al veredicto ni a la ficha
- **ARCHIVO:LÍNEA** — `web/app.js:333-386` (`evaluar`: devuelve `areas, sar, coberturaSar, planos, campamentos, enMancha, gore`; **nunca `estado.laminas`**); `web/app.js:657-960` (`render`: bloques A, B, plano, D, C, campamentos, comuna — **ningún bloque para `laminas`**); `web/app.js:1549-1565` (la capa sólo existe como dibujo del mapa, apagada por omisión, `index.html:111`).
- **QUÉ PASA** — El proyecto vectorizó 163 polígonos (Angol 124, Curarrehue 39) y los publica y precachea, pero el veredicto los ignora por completo. Un punto dentro de la mancha «Alto · inundación · 2013» de Angol recibe «Registros de inundación a cierta distancia» (nivel bajo) y la pestaña de detalle dice que **no cae dentro** de un área de riesgo.
- **CÓMO SE VE** — Quien consulta un sitio en Angol lee: *«Este punto no cae dentro de un área de riesgo por inundación declarada en el plan regulador»* y ninguna palabra sobre la lámina que el propio Estudio de Riesgo de Angol dibujó ahí. La única pista es una línea del inventario: «124 polígono(s) que convertimos nosotros desde una lámina impresa», sin decir que **este** punto cae en uno. En pantalla no aparece «derivado» ni la fuente ni el año 2013 de esa lámina.
- **CÓMO REPRODUCIRLO** — `python tools/auditoria/uso_veredicto_por_punto.py`; leer `tools/auditoria/evidencia_uso/02_angol_lamina_vectorizada.txt`. El punto se elige en el navegador con la misma `poligonosQueContienen` del visor: dentro de una lámina y fuera del vectorial MINVU.
- **SALIDA CRUDA**
  ```
  lámina elegida: [-72.69849822363237, -37.77912806273094, 'Alto', 'inundación', '2013']
  --- 02_angol_lamina_vectorizada: nivel=veredicto v-bajo comuna=['Angol', 0.8] eval={"nivel": "bajo", "titulo": "Registros de inundación a cierta distancia", "areas": 0, "sar": 0, "cerca": 1, "gore": 1, "enMancha": false, "lam": 1, "areasTipo": []}
  (ficha) Plan Regulador Comunal A · NORMATIVO Este punto no cae dentro de un área de riesgo por inundación declarada en el plan regulador.
  grep -c -i "lámina|lamina|derivad|vectoriz" 02_angol_lamina_vectorizada.txt → 6, todas en la etiqueta del punto o en el inventario de comuna; ninguna en el veredicto ni en un bloque de evidencia.
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **5**. Es exactamente el caso del preámbulo: «no cae dentro» leído sobre una mancha que sí existe.

### H-102 · El botón «Buscar» no hace nada
- **ARCHIVO:LÍNEA** — `web/index.html:55` (`<button id="btn-buscar">`); `web/app.js:1900-1942` (`enlazarInterfaz`: enlaza `#btn-ubicacion` en 1924, Enter en 1934-1939, **no hay `#btn-buscar`**); único uso en `app.js:1300` (sólo lo deshabilita mientras busca). Quitado en el commit `2ab0ccf` (25-ago-2026), que al mover el enlace a `enlazarInterfaz` no lo volvió a poner.
- **QUÉ PASA** — El control principal del visor no tiene manejador de clic. Sólo Enter dispara `buscar()`.
- **CÓMO SE VE** — Escribes la dirección, tocas «Buscar», y no pasa nada: ni «Buscando…», ni resultado, ni error. En celular (sin tecla Enter evidente; el teclado dice «buscar», `enterkeyhint`) el botón es lo primero que se toca.
- **CÓMO REPRODUCIRLO** — `grep -n "btn-buscar" web/app.js` → sólo la línea 1300. En el arnés: paso 11a escribe, clica el botón y espera 2,5 s (prueba de ausencia, tiempo acotado a propósito); control positivo: el paso 11 hace lo mismo con Enter y sí consulta.
- **SALIDA CRUDA**
  ```
  $ grep -n "btn-buscar\|buscar()" web/app.js
  1297:async function buscar() {
  1300:  const btn = $('#btn-buscar');
  1938:      else { cerrarSugerencias(); buscar(); }
  $ git log --oneline -S"btn-buscar').addEventListener" -- web/app.js
  2ab0ccf Que el visor responda antes de tener los datos, y que suelte lo que carga
  b9de7c3 Visor abierto de exposición a inundaciones para La Araucanía
  --- 11a botón Buscar: {'estado': 'Estás fuera de La Araucanía: …', 'peticiones_nominatim': 1, 'peticiones_de_buscar_limit1': 0, 'peticiones_de_sugerencias_limit5': 1}
  --- 11 buscar (Enter): {'estado': 'No se pudo buscar (Failed to fetch). Prueba tocando el mapa.', 'peticiones': 2}
  ```
  (`limit=1` es la petición de `buscar()`; `limit=5` la de las sugerencias: el clic no generó ninguna de `buscar()`.)
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **4**. No produce un dato equivocado, pero deja fuera a quien no sabe que hay que apretar Enter; y la e2e sólo comprueba que el botón es «clicable», no que haga algo.

### H-103 · El inventario de comuna se atribuye por el punto crítico más cercano: Temuco sale como «Padre Las Casas»
- **ARCHIVO:LÍNEA** — `web/app.js:393-417` (`comunaDe`: comuna del punto crítico más cercano, a cualquier distancia); `web/data/estado-comunas.json` (Temuco: `"puntos_inundacion": 0`).
- **QUÉ PASA** — Temuco no tiene puntos críticos de inundación en el dato (0 de 440), así que **cualquier** consulta en Temuco hereda la comuna del punto vecino más cercano. En la Plaza de Armas resuelve «Padre Las Casas» a 1,6 km. El bloque «Con qué cuenta…», el texto compartido de la comuna y la solicitud Ley 20.285 salen a nombre de la comuna equivocada — y con su inventario: Padre Las Casas «no publica ningún documento», Temuco tiene 16 documentos, 18 láminas y 1 polígono MINVU.
- **CÓMO SE VE** — Quien busca en Temuco lee «Con qué cuenta Padre Las Casas · 80.384 habitantes» y «No encontramos nada consultable para esta comuna»; y si «pide el mapa a la autoridad», la carta va por Padre Las Casas.
- **CÓMO REPRODUCIRLO** — arnés, puntos 04 (Temuco plaza) y 08 (polígono MINVU de Temuco, comuna `Temuco` en el dato).
- **SALIDA CRUDA**
  ```
  --- 04_temuco_plaza: nivel=veredicto v-sindato comuna=['Padre Las Casas', 1.6] …
  04_temuco_plaza.txt:76:    Con qué cuenta Padre Las Casas INVENTARIO
  04_temuco_plaza.txt:80:      80.384 habitantes (Censo 2024)
  área no fluvial elegida: [-72.6165…, -38.7588…, 'anegamiento', 'Temuco']
  --- 08_area_no_fluvial: … comuna=['Padre Las Casas', 1.5] …
  estado-comunas.json → {"comuna": "Temuco", … "puntos_inundacion": 0, "documentos": 16, "laminas_localizadas": 18, "poligonos_area_riesgo": 1 …}
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **4**. La capital regional entera hereda el inventario de otra comuna. El comentario del código lo admite «cerca de un deslinde»; acá no es un deslinde, es toda la ciudad.

### H-104 · El texto que se comparte en «Sin registros» pierde el «OJO: no significa que no se inunde»
- **ARCHIVO:LÍNEA** — `web/app.js:1089` (`if (estado.ultimo && estado.ultimo.nivel === 'sindato')`) contra `web/app.js:975` (`estado.ultimo = { res, etiqueta, lon, lat }` — el nivel está en `estado.ultimo.res.nivel`, no en `estado.ultimo.nivel`).
- **QUÉ PASA** — La condición nunca es verdadera. El párrafo de §7.1 que el comentario de la línea 1086-1088 dice que «viaja en el texto compartido» no viaja.
- **CÓMO SE VE** — El WhatsApp reenviado dice «SIN REGISTROS EN LAS FUENTES CONSULTADAS … Sin puntos críticos registrados en 1,5 km» y nada más. En pantalla sí está la aclaración (`app.js:604-608`); en el texto que se reenvía, no.
- **CÓMO REPRODUCIRLO** — arnés, punto 07; leer la sección `textoFicha()` de `07_sin_dato_nororiente.txt`.
- **SALIDA CRUDA**
  ```
  === textoFicha() (lo que se comparte) ===
  SIN REGISTROS EN LAS FUENTES CONSULTADAS
  Ubicación: Auditoría sin dato

  El satélite no pasó por acá en la ventana del evento.
    No observado NO es lo mismo que no inundado.

  Sin puntos críticos registrados en 1,5 km.

  Esto NO es información oficial ni un pronóstico.
  En emergencia: SENAPRED y tu municipio.
  ```
  (no aparece la línea «OJO: que no haya registro NO significa…» de `app.js:1090-1091`).
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **4**. Es la regla 7.1 en el canal donde el texto queda solo, sin pantalla que lo matice.

### H-105 · Un polígono de anegamiento, litoral o napa sale titulado «área de riesgo por inundación» en la respuesta corta
- **ARCHIVO:LÍNEA** — `web/app.js:363-365` (título) y `571-573` (`porQue`: «declaró esta zona área de riesgo por inundación»); el sello «anegamiento, no desborde» sólo se pinta en la pestaña de detalle (`app.js:689-692`). Datos: `areas-riesgo-inundacion.geojson` trae `tipo_hidrico` = fluvial 57 · anegamiento 3 · litoral 2 · napa_freatica 1.
- **QUÉ PASA** — El sitio declara (README «Qué cuenta como inundación», REGLAS 1.4) que anegamiento por drenaje **no** es su alcance; la respuesta corta, que es lo que la mayoría lee, lo llama inundación igual. El fenómeno se corrige sólo a un toque de distancia.
- **CÓMO SE VE** — En la zona ARRI de Temuco: «⚠️ Estás en un área de riesgo por inundación del plan regulador … Es la única fuente con efecto legal». Nada dice «anegamiento» hasta abrir «Detalle y fuentes».
- **CÓMO REPRODUCIRLO** — arnés, punto 08 (centroide del primer polígono no fluvial).
- **SALIDA CRUDA**
  ```
  valores tipo_hidrico: [('fluvial', 57), ('anegamiento', 3), ('litoral', 2), ('napa_freatica', 1)]
  === #respuesta === (08)
  ⚠️ Estás en un área de riesgo por inundación del plan regulador
  📍 Auditoría área no fluvial
  El plan regulador de tu comuna declaró esta zona área de riesgo por inundación. Es la única fuente con efecto legal.
  (detalle, línea 26): …por el plan regulador:ANEGAMIENTO anegamiento, no desborde (zona ARRI)…
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **3**. Son 6 de 63 polígonos; el efecto legal es real, el fenómeno nombrado no.

### H-106 · «Balmaceda 500, Temuco» devuelve la avenida entera, sin decir que el número no se encontró
- **ARCHIVO:LÍNEA** — `web/app.js:1114-1126` (`geocodificar`: toma `j[0]` sin mirar `addresstype`/`category`); `app.js:1305` sólo distingue «no encontró» de «encontró».
- **QUÉ PASA** — Nominatim, cuando no tiene el número, devuelve la calle (`addresstype: road`). El visor consulta el punto representativo de la calle y lo presenta como respuesta a la dirección escrita. Avenida Balmaceda cruza Temuco de lado a lado; el veredicto de «un punto» de ella no es el veredicto del 500.
- **CÓMO SE VE** — Escribes «Balmaceda 500, Temuco», lees «📍 Avenida Balmaceda, Villa Ñielol, Centro, Temuco…» y un veredicto. Sólo alguien que se fije en que el «500» desapareció de la etiqueta sabe que le respondieron otra cosa.
- **CÓMO REPRODUCIRLO** — arnés, paso 11 con red; y `curl` directo a Nominatim con la misma URL que arma el visor.
- **SALIDA CRUDA**
  ```
  $ curl … "…&limit=1&countrycodes=cl&…&bounded=1&q=Balmaceda%20500%2C%20Temuco"
  [{"osm_type": "way", "category": "highway", "type": "secondary", "addresstype": "road",
    "display_name": "Avenida Balmaceda, Centro, Temuco, …", "lat": "-38.7327346", "lon": "-72.5924760"}]
  --- 11 buscar con red: '❔ Sin registros en las fuentes consultadas  📍 Avenida Balmaceda, Villa Ñielol, Centro, Temuco, Provincia de Cautín, Regi…'
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **3**. Es el flujo principal (dirección → veredicto) y la persona no tiene cómo saber que el punto no es su casa.

### H-107 · Sin polígono MINVU, el bloque A muestra el «Año» del primer polígono de la capa (de otra comuna)
- **ARCHIVO:LÍNEA** — `web/app.js:720` (`atribucion(estado.areasRiesgo, res.areas[0] || estado.areasRiesgo?.features[0])`) con `app.js:649` (`p.anio || proc.fecha_dato || 'año no declarado'`).
- **QUÉ PASA** — Cuando el punto no cae en ningún polígono, la atribución se calcula con `features[0]`, que trae su propio `anio` (2010). Ese año se imprime como «Año: 2010» debajo de «Este punto no cae dentro…» en Angol, Padre Las Casas, y cualquier comuna sin polígono. No es el año de nada que tenga que ver con ese punto.
- **CÓMO SE VE** — «Fuente: MINVU — … · Año: 2010» en una comuna cuyo plan es de 2022 (Angol) o que no tiene polígono (Padre Las Casas).
- **CÓMO REPRODUCIRLO** — arnés, puntos 02 y 03; grep «Año:» en la sección `#detalle-ficha`.
- **SALIDA CRUDA**
  ```
  02_angol_lamina_vectorizada.txt: …Fuente: MINVU — áreas de riesgo de instrumentos de planificación territorial (Art. 2.1.17 OGUC) · Año: 2010 · datos obtenidos 2026-08-30…
  valores anio (areas-riesgo): [('2009', 36), ('1989', 9), ('2012', 5), ('no declarado por la fuente', 4), ('1984', 4), ('1992', 2), ('2010', 1), ('2023', 1), ('1991', 1)]
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **3**. Es la regla 1.1 («nunca inventar un año») aplicada al revés: el año existe, pero es de otro polígono.

### H-108 · El pie dice «la búsqueda ocurre en tu dispositivo»; la dirección viaja a Nominatim, y sus fragmentos también
- **ARCHIVO:LÍNEA** — `web/index.html:301-303` («la búsqueda y la consulta ocurren en tu dispositivo, no se guarda tu dirección…»); `web/app.js:1117-1121` (la dirección completa va en la URL a `nominatim.openstreetmap.org`); `web/app.js:1153-1165` (desde 4 caracteres, cada pausa de 450 ms manda lo escrito). Las teselas (`app.js:1411`, `1418`) revelan además la zona que se mira a OSM/Esri.
- **QUÉ PASA** — El sitio no guarda nada (verificado: no hay analítica, cookies ni beacons; `localStorage` sólo guarda el mapa base). Pero «la búsqueda ocurre en tu dispositivo» es falso para la búsqueda por dirección: la dirección exacta —dato personal según la propia nota de §7.5— la recibe un tercero, y la política de Nominatim la registra.
- **CÓMO SE VE** — Nada; por eso es una etiqueta que miente y no un bug visible.
- **CÓMO REPRODUCIRLO** — `grep -n -E "fetch\(|sendBeacon|analytics|cookie|localStorage" web/*.js` y el contador de peticiones del arnés (paso 11a: 1 petición `limit=5` sólo por escribir).
- **SALIDA CRUDA**
  ```
  web/app.js:1121:  const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
  web/app.js:1165:    const r = await fetch(url, { signal: SUG.aborto.signal });
  web/app.js:1443:    const v = localStorage.getItem('riesgomapas.base');
  (sin gtag / analytics / cookie / sendBeacon / XMLHttpRequest en web/)
  --- 11a: 'peticiones_de_sugerencias_limit5': 1  (sin haber apretado nada)
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **3**. No decide mal a nadie, pero contradice una promesa escrita en el pie y en REGLAS 7.5.

### H-109 · Catálogo: 38 documentos con URL vacía; el enlace «directo al PDF» recarga la página
- **ARCHIVO:LÍNEA** — `web/catalogo.js:64` (`href="${esc(d.url)}"`) y `:40` (`href="${esc(urlDoc)}#page=${l.pagina}"`); `web/data/catalogo-documentos.json`.
- **QUÉ PASA** — 38 documentos (Collipulli 17, Curarrehue 14, Purén 3, Saavedra 2, Carahue 2) tienen `url: ""`. `href=""` navega a la misma página; `href="#page=13"` no abre nada. Uno de ellos tiene lámina: la **Memoria Explicativa de Purén, octubre 2025**, que el README destaca como estudio nuevo.
- **CÓMO SE VE** — En `documentos.html`, tocar el título o «pág. N →» de esos documentos vuelve al índice.
- **CÓMO REPRODUCIRLO** — `python tools/auditoria/enlaces_publicados_responden.py` (hosts) y el conteo de abajo.
- **SALIDA CRUDA**
  ```
  38 docs sin URL absoluta; con láminas: 1
     ('Purén', '', 'MEMORIA-EXPLICATIVA-PUREN_OCTUBRE-2025.pdf', 1)
  comunas afectadas: Counter({'Collipulli': 17, 'Curarrehue': 14, 'Purén': 3, 'Saavedra': 2, 'Carahue': 2})
  ## hosts del catálogo: {'eae.mma.gob.cl': 214, … '': 38, …}
  muestra de 12 documentos con lámina y URL absoluta: los 12 → 200 application/pdf
  ```
- **CONFIANZA** — CONFIRMADO (no se clicó en el navegador; se lee del dato y de la plantilla).
- **GRAVEDAD** — **3** para el de Purén (promesa rota sobre cartografía real); 2 para el resto.

### H-110 · Elegir una comuna en las sugerencias produce un veredicto de nivel para un punto que nadie eligió
- **ARCHIVO:LÍNEA** — `web/app.js:1871-1892` (`zoomComuna`: consulta el centro del bbox de los puntos críticos de la comuna).
- **QUÉ PASA** — La intención documentada es «responder, no sólo mover el mapa». Pero la respuesta es un veredicto por radios (300/500/1500 m) sobre el centro geométrico de los puntos, que en Angol cae a 909 m del registro más cercano y da nivel «bajo» con ícono ℹ️. Ese nivel no describe a la comuna ni a ninguna casa.
- **CÓMO SE VE** — Escribes «Angol», eliges la comuna, y lees «ℹ️ Registros de inundación a cierta distancia · El registro más cercano de inundación está a 909 metros». Angol tiene 14 puntos críticos, 3 crónicos, un estudio de riesgo con 124 polígonos vectorizados, y el Rehue entró 1,5 m en las casas el 2-ago-2026 (texto del propio visor, `app.js:813-819`).
- **CÓMO REPRODUCIRLO** — arnés, paso 09.
- **SALIDA CRUDA**
  ```
  --- 09 sugerencia comuna: ℹ️ | Registros de inundación a cierta distancia |  | 📍 ANGOL (centro de los registros de la comuna) |  | El registro más cercano de inundación está a 909 metros. | …
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **3**. La etiqueta «centro de los registros» es honesta; el ícono y el nivel no lo son para una comuna.

### H-111 · «Ver ordenanza» lleva a un 404
- **ARCHIVO:LÍNEA** — `web/app.js:697-699`; dato: 9 de 63 polígonos traen `ordenanza_url`, una sola URL distinta.
- **QUÉ PASA** — `http://www.observatoriourbano.cl/Ipt/cehu_resultado_decreto.asp?r=9&c=29&i=25` responde 404 (el README §«fecha» decía 410; hoy es 404). El enlace se muestra igual.
- **CÓMO SE VE** — Un enlace «Ver ordenanza» en la ficha de la capa con efecto legal que termina en «página no encontrada».
- **CÓMO REPRODUCIRLO** — `python tools/auditoria/enlaces_publicados_responden.py`.
- **SALIDA CRUDA**
  ```
  control senapred.cl -> 200 text/html
  ## ordenanza_url en areas-riesgo: 1 distintas
     404 text/html http://www.observatoriourbano.cl/Ipt/cehu_resultado_decreto.asp?r=9&c=29&i=25
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **2**.

### H-112 · «Satélite, color real» sin señal queda mudo; y el SW responde `index.html` a lo que no tiene
- **ARCHIVO:LÍNEA** — `web/sw.js:82` (sólo `tile.openstreetmap.org` se cachea); `web/sw.js:106` (`c.match(req) || c.match('index.html')` para cualquier otra petición fallida, incluidas teselas de Esri y PNG de planos).
- **QUÉ PASA** — Sin red, elegir «Satélite» deja el mapa en blanco sin ningún mensaje (14 teselas de Esri fallidas en la prueba); las capas de datos se dibujan sobre nada. Y para cualquier recurso no precacheado (teselas de Esri, `data/planos/*.png`), el SW devuelve el HTML del índice como si fuera la imagen.
- **CÓMO SE VE** — Mapa blanco al elegir satélite sin señal; el control «Ver el plano sobre el mapa» sin señal diría «Plano cargado» sobre una capa vacía (esto último es SOSPECHA: no se probó el plano sin red).
- **CÓMO REPRODUCIRLO** — `python tools/auditoria/uso_sin_senal.py` (`teselas_fallidas_satelite`, captura `15_offline_satelite.png`).
- **SALIDA CRUDA**
  ```
  CACHÉ: … ["riesgomapas-v21-tiles", ["https://tile.openstreetmap.org/9/150/315.png", … 4 teselas]]
  buscar: … | teselas sat fallidas: 14 | catálogo: 25 comunas · 354 documentos · 224 láminas …
  ```
- **CONFIANZA** — CONFIRMADO lo del satélite; SOSPECHA lo del plano sin red.
- **GRAVEDAD** — **2**.

### H-113 · Un punto en el mar recibe «Sin registros… en comunas con poca capacidad técnica municipal es lo esperable»
- **ARCHIVO:LÍNEA** — `web/app.js:29-40` (`REGION.bbox` incluye océano hasta −73,70); `app.js:604-608` (texto de «sin dato»); `comunaDe` atribuye Saavedra a 16,2 km.
- **QUÉ PASA** — Dentro del bbox no hay distinción tierra/mar. Un clic en el Pacífico obtiene el veredicto «sin dato» completo, con el inventario de Saavedra.
- **CÓMO SE VE** — Curiosidad más que daño; pero el texto «En comunas con poca capacidad técnica municipal es lo esperable» sobre el mar es un texto que no sabe dónde está.
- **CÓMO REPRODUCIRLO** — arnés, punto 05.
- **SALIDA CRUDA**
  ```
  --- 05_mar_frente_a_saavedra: nivel=veredicto v-sindato comuna=['Saavedra', 16.2] eval={"nivel": "sindato", … "cerca": 0 …}
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **2**.

### H-114 · `vectorizadas.geojson` no lleva `estado_tramite` (REGLAS 1.5) y «derivado» sólo se lee en la leyenda de capas
- **ARCHIVO:LÍNEA** — `web/data/laminas/vectorizadas.geojson` (claves: `amenaza, anio, clase, comuna, escala_original, fuente, hectareas, metodo_original, origen_lamina`); `web/index.html:111-113` (sello «derivado» en la casilla) y `:118-124` (nota). Nada en `app.js` escribe «derivado» para un punto.
- **QUÉ PASA** — La regla 1.5 exige que el peso legal «vaya escrito en el dato (`estado_tramite`) y visible en pantalla con texto». En el dato no está (163/163); en pantalla sólo está en el panel de capas, plegado por omisión, no en el veredicto (ver H-101). Tampoco se publica el RMSE ni la aptitud (`predial/manzana/contexto`) por polígono, así que el visor no podría «difuminar» los de aptitud `contexto` aunque quisiera.
- **CÓMO SE VE** — Con la capa encendida se ve un achurado ámbar; sin abrir el plegable no hay texto que diga que es derivado, ni de qué año, ni con cuánto error.
- **CÓMO REPRODUCIRLO** — `python tools/auditoria/inventario_propiedades_veredicto.py`.
- **SALIDA CRUDA**
  ```
  ## laminas/vectorizadas.geojson: 163 features
     estado_tramite   ausente/vacío en 163/163
     rmse_loo_m       ausente/vacío en 163/163
     aptitud          ausente/vacío en 163/163
     claves de properties del 1er feature: ['amenaza', 'anio', 'clase', 'comuna', 'escala_original', 'fuente', 'hectareas', 'metodo_original', 'origen_lamina']
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **2** por sí solo (se vuelve parte del 5 de H-101 cuando la capa entre al veredicto).

### H-115 · Palabras de §7.2 presentes en `web/`
- **ARCHIVO:LÍNEA** — `web/index.html:278` («…SENAPRED para la alerta»); «pronóstico/pronósticos» negado en `index.html:75, 138, 222` y `app.js:554, 955, 1093`. No hay «aviso» (sólo la clase CSS `aviso-fuerte`, `app.js:605, 860`, `style.css:562`) ni «evacuación».
- **QUÉ PASA** — La regla dice «nunca». Todas las apariciones son negaciones («no es un pronóstico») o atribución a SENAPRED; ninguna afirma un pronóstico ni una alerta.
- **CÓMO SE VE** — No cambia la decisión de nadie. Se reporta porque la regla es literal y el verificador decide.
- **SALIDA CRUDA** — `grep -n -i -E "pron|evacua|alert" web/index.html web/app.js web/catalogo.js web/documentos.html web/manifest.json` (7 líneas, listadas arriba).
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **1**.

### H-116 · Mensajes de `#estado` que se quedan pegados a acciones que no son la suya
- **ARCHIVO:LÍNEA** — `#estado` es un único `<p>` (`index.html:60`) que escriben ~20 sitios de `app.js`; nadie lo limpia al cambiar de acción salvo algunas capas.
- **QUÉ PASA** — «Estás fuera de La Araucanía…» sigue en pantalla mientras se escribe una dirección; «No se encontró esa dirección…» sigue mientras se encienden capas; al encender «Campamentos» aparece «No hay planos de plan regulador en esta zona» (viene del `moveend` de planos).
- **CÓMO SE VE** — Un mensaje de error que no corresponde a lo que acabas de hacer.
- **SALIDA CRUDA**
  ```
  --- 11a botón Buscar: {'estado': 'Estás fuera de La Araucanía: este prototipo sólo cubre esa región.' …}
  --- 12 capas: {"cap-areas": {"vis": ["visible"], "estado": "No se encontró esa dirección en La Araucanía."}, … "cap-camp": {"vis": ["visible"], "estado": "No hay planos de plan regulador en esta zona."}}
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **1**.

### H-117 · Tocar un polígono MINVU abre el popup y además dispara la consulta completa
- **ARCHIVO:LÍNEA** — `web/app.js:1576-1588` (popup de `ar-fill`) y `app.js:1678-1683` (clic general: sólo excluye `pc-circ` y `huellas-fill`).
- **QUÉ PASA** — Dos respuestas a un toque. Dicen lo mismo (medido), así que no contradicen; pero el popup tapa parte del mapa mientras la página salta a la ficha.
- **SALIDA CRUDA**
  ```
  --- 13 clic área: {"popup": "INUNDACION\nPlan Regulador de Collipulli · zona ZR-2\n…Año: 2009\n×", "respuesta": "⚠️\nEstás en un área de riesgo por inundación del plan regulador\n\n📍 Punto seleccionado (-37.9613, -72.4377)…"}
  ```
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **1**.

### H-118 · Geolocalización denegada: el mensaje viene en inglés
- **ARCHIVO:LÍNEA** — `web/app.js:1331` (`err.message` del navegador se pega tal cual).
- **SALIDA CRUDA** — `--- 10 geo denegada: No se pudo obtener la ubicación (User denied Geolocation).`
- **CONFIANZA** — CONFIRMADO.
- **GRAVEDAD** — **1**.

---

## 3. SIN DATO (no medido; no es OK ni FALLA)

- **Celular y modo oscuro** más allá de lo que cubre la e2e (contraste, desbordes, controles clicables): no se consultó ningún punto en perfil móvil ni oscuro en esta sesión.
- **Impresión real** («Imprimir o guardar como PDF»): sólo se leyó que existe `@media print` en `style.css:627`; no se generó un PDF.
- **«Ver el plano sobre el mapa» sin señal**: no probado (ver H-112, parte SOSPECHA).
- **Nominatim bajo su política de uso** (bloqueo por tráfico): no se midió; una sola consulta directa respondió 200.
- **Compartir por `navigator.share`**: en Chromium sin `share` se cae al portapapeles; no se probó el diálogo nativo del celular.
- **Los 9 enlaces de catálogo por comuna municipal** (`munipuren.cl`, `angol.cl`, etc.) fuera de la muestra de 12: no se abrieron uno a uno.

---

## 4. VERIFICADO LIMPIO

Qué se miró y está sano, con el comando o la línea que lo respalda:

- **Control positivo del veredicto (capa A)**: centroide de un polígono fluvial de Collipulli → «Estás en un área de riesgo por inundación del plan regulador», nivel `v-alto`, `areas: 1`, `areasTipo: ["fluvial"]`; ficha con clasificación, zona, usos prohibidos, «no prohíbe construir, condiciona», fuente y año 2009 (`01_collipulli_area_minvu.txt`; `corrida_arnes.log` línea `--- 01_…`).
- **Punto fuera de la región**: Santiago por consulta y por geolocalización → «Fuera del alcance de este prototipo», `v-fuera`, «Eso no dice nada sobre el riesgo de ese lugar»; `estado.ultimo = null` (no hay ficha que compartir) (`06_santiago_fuera.txt`; `--- 10 geo: … Estás fuera de La Araucanía`).
- **Comuna sin cartografía (Padre Las Casas)**: veredicto por puntos críticos (4 a ≤1,5 km, nivel alto), bloque «Con qué cuenta Padre Las Casas» con «Esto no dice si tu casa se inunda», «Qué falta» con tres vacíos, y botones de compartir y de solicitud (`03_padre_las_casas.txt`).
- **«Ausencia de dato no es ausencia de riesgo» en pantalla**: en «sin dato» (`app.js:604-608`, visto en 05 y 07), en capa A sin polígono (`app.js:714-718`), en capa B sin cobertura (`app.js:830-833`, visto en 07: «No observado no es lo mismo que no inundado»), en capa D (`app.js:894-896`), en el bloque de comuna y en «Qué es y qué no es esto» (`index.html:255-257`). El único canal donde falta es el texto compartido de «sin dato» (H-104).
- **Capa B en sus tres estados**: «no pasó por acá» (07), «sí miró… y no detectó agua» los días 3 y 4 de agosto de 2026 (01, también en el texto compartido); el estado «vio agua» lo cubre la e2e (`tests/auditoria_e2e.py:760-797`) y no se repitió.
- **Modo sin señal, de punta a punta**: con el SW instalado y sin red, recargar el visor carga **todas** las capas (`puntos, areas, laminas, gore, jrc, sar, cob, sarIndice, camp: true; planos: 20; estadoComunas: 32`), el veredicto de Collipulli sigue diciendo «área de riesgo», las sugerencias de comuna funcionan, el buscador falla de forma visible («No se pudo buscar (Failed to fetch). Prueba tocando el mapa.») y el catálogo abre («25 comunas · 354 documentos · 224 láminas») — `resultados_offline.json`, salida `SIN RED flags: {… todas true …}`. Nota honesta: la primera versión de esa prueba leyó los flags **a mitad de carga** y acusó falsamente 8 capas ausentes; se corrigió esperando a que `#estado` deje de decir «Cargando…». El precaché lista 22 recursos (`CACHÉ: … riesgomapas-v21-app …`).
- **Sin errores de JavaScript** en toda la corrida (`--- errores JS: []`).
- **Nada se registra del usuario**: sin `analytics`, `gtag`, `cookie`, `sendBeacon`, `XMLHttpRequest` ni `console.log` en `web/`; `localStorage` sólo guarda `riesgomapas.base` (`app.js:1443, 1456`); `vendor/maplibre-gl.js` sólo contiene URLs de licencia y del namespace SVG (`grep -o "https?://…" | sort | uniq -c`). Lo que sí sale del dispositivo está en H-108.
- **Cifras de portada y sello calculadas del dato**: «440 · 211 crónicos · 63 áreas en 12 comunas · 20 planos · 5.776 ha · 537 hogares en 15 campamentos» y «440 puntos críticos de origen hídrico · temporada 2026 · datos generados 2026-08-12» coinciden con los conteos del inventario (`--- 14 cifras`; `inventario_propiedades_veredicto.py`: 440, 63, 15 features, `hectareas: 5776.0`, 20 planos).
- **Campos que la ficha lee existen en el dato** (ausentes 0/N): `nivel, comuna, causa, fuente, anio, cronico, temporadas_registrado` en puntos; `clasificacion, comuna, zona, usos_prohibidos, fuente, anio, tipo_hidrico` en áreas; `fecha_observacion, evento, hectareas, track, fechas_referencia, caida_db, umbral_agua_db` en SAR; `clase` en GORE; `titulo, estado_tramite, estado_tramite_nota, puntos_control, rmse_loo_m, resolucion_m_px, bounds_wgs84, archivo` en los 20 planos; `le_falta` es lista en 32/32 comunas. No hay texto «undefined» posible por esos campos.
- **Las 8 casillas de capas dibujan su capa** con los datos actuales (`--- 12 capas: … "visible" …`), y «Encender/Apagar todo» lo cubre la e2e.
- **Geolocalización**: dentro de la región consulta «Tu ubicación actual»; fuera avisa antes de responder; denegada avisa (`--- 10 geo …`).
- **Buscador sin red** falla de forma visible y sugiere el mapa (`--- 11 buscar: 'No se pudo buscar (Failed to fetch). Prueba tocando el mapa.'`); dirección de Santiago → «No se encontró esa dirección en La Araucanía.» (bbox + `bounded=1`).
- **Enlaces del catálogo con URL absoluta**: 12 de 12 muestreados con lámina responden `200 application/pdf` (`enlaces_publicados_responden.py`).
- **Planos**: los 20 se declaran «Anteproyecto» en el dato y el sello va en el encabezado del bloque (`app.js:849-853`); el aviso de zoom y el tope de 6 planos existen (`app.js:279-299`).
