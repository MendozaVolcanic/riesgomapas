# Auditoría 2026-09-06 — Frente 2: por relación

Rama `visor-simple-y-laminas-vectorizadas`, commit `b293aad`, árbol limpio. Auditor: Claude (Fable 5.1), sesión del 6-sep-2026. IDs provisionales 201–224; los finales los pone el verificador.

Qué es esto: un censo **por patrón**, no por archivo, de los defectos que viven entre dos piezas correctas. Cada sección declara el comando con que se buscó, pega su salida cruda y lista los hallazgos en el formato del preámbulo. No se modificó nada de `scripts/`, `web/`, `tests/`, `config/`, `data/` ni `docs/` existentes. Los instrumentos nuevos quedaron en `tools/auditoria/`:

| Instrumento | Qué mide |
|---|---|
| `tools/auditoria/campos_visor_vs_datos.py` | qué `properties.X` lee `web/app.js` contra las claves reales de cada `web/data/*` (patrón 1) |
| `tools/auditoria/visor_relaciones_e2e.py` | seis relaciones del visor en Chromium real, servido en `127.0.0.1:8792` (patrones 1, 2, 4, 5) |
| `tools/auditoria/script19_entradas_ausentes.py` | qué escribe el script 19 cuando le falta una entrada, sobre una copia en el scratchpad (patrón 6) |
| `tools/auditoria/solape_gore_y_extension_jrc.py` | anidamiento MAXIMA-dentro-de-MEDIA en el GORE y extensión real del ráster JRC (patrones 2, 5) |

Cada instrumento lleva en su docstring las dos preguntas (¿fallaría si lo medido estuviera roto? ¿se vería distinto si el instrumento estuviera muerto?) y un control positivo. Los cuatro controles pasaron: `__control_inexistente → FALTA 0/440`; punto dentro de área MINVU → «cae dentro de»; par artificial MEDIA/MAXIMA → `(1, 1)`; E0 del script 19 reproduce el publicado salvo los cuatro campos del censo, que la copia no incluía.

Las tres pruebas del proyecto (63 pytest · 151 datos · 273 navegador) no se volvieron a correr; se leyeron enteras para saber qué cubren (`tests/test_scripts.py`, `tests/auditoria_datos.py`, `tests/auditoria_e2e.py`).

---

## Resumen ordenado por gravedad

| ID | Grav. | Título | Archivo:línea |
|---|---|---|---|
| 201 | 5 | Las láminas vectorizadas se dibujan pero no entran al veredicto ni a la ficha | `web/app.js:333-386`, `:1549-1565` |
| 202 | 4 | El texto que se comparte pierde la advertencia de «sin registros» por leer un campo que no existe | `web/app.js:1089` |
| 203 | 4 | El script 19 con una entrada ausente publica un inventario falso, sin error | `scripts/19_estado_comunas.py:103,109,119` |
| 204 | 3 | «No detectamos vacíos» para Temuco, cuyo único polígono MINVU es de anegamiento | `scripts/19_estado_comunas.py:183-185` · `web/app.js:466,546` |
| 205 | 3 | El año del área MINVU viene del Atlas CIGIDEN y la ficha lo firma como MINVU, y en la misma ficha dice que no está declarado | `web/app.js:645-655,725-731` · `scripts/06_areas_riesgo_prc.py:342-350` |
| 206 | 3 | Dos hojas de plano cubren el mismo punto y la ficha muestra sólo la primera (Pucón v3 tapa a v4) | `web/app.js:844-845` |
| 207 | 3 | `--bbox` del script 14 sobrescribe la capa B publicada con un recorte de prueba | `scripts/14_sar_huella_observada.py:702-703,717,877-879` |
| 208 | 3 | La capa derivada se publica con `capa_evidencia = A_normativo` | `scripts/19_estado_comunas.py:156` · `scripts/18_vectorizar_laminas.py:421,538` · `scripts/comun.py:290-292` |
| 209 | 2 | La lista de sugerencias vuelve a abrirse sola 450 ms después de elegir una comuna | `web/app.js:1219-1227,1243-1247` |
| 210 | 2 | El texto compartido recorta a 3 puntos críticos sin decir cuántos hay | `web/app.js:1076-1085` |
| 211 | 2 | El arreglo «esperar al estilo» llegó a dos casillas de ocho | `web/app.js:1693-1697` vs `:1735-1739` |
| 212 | 2 | El arreglo de `ocultarPlanos` (sin guarda `isStyleLoaded`) no llegó a `actualizarPlanos` | `web/app.js:244-251` vs `:277` |
| 213 | 2 | Subir `VERSION` borra también la caché de teselas: lo que «ya miraste» se pierde en cada publicación | `web/sw.js:16-18,63-66` |
| 214 | 2 | Sin red, un dato o un PNG que no está en caché se sirve como `index.html` | `web/sw.js:104-106` |
| 215 | 2 | Ningún script declara `Requiere:` (REGLAS §6.1) y la prueba sólo exige `Salida:` | `scripts/*.py` · `tests/test_scripts.py:50-64` |
| 216 | 2 | Tres referencias a `docs/REGLAS.md`, que no existe, y «son doce» reglas que son 32 encabezados | `scripts/07_buscar_laminas_riesgo.py:27` · `scripts/20_paquete_practicante.py:393,404` |
| 217 | 2 | Enter sin elegir sugerencia geocodifica con `limit=1` y toma el primer resultado sin avisar | `web/app.js:1117-1125` |
| 218 | 2 | La e2e no mira `jrc-fill` ni `lam-fill`, y nunca consulta un punto dentro de una lámina ni lee el texto compartido | `tests/auditoria_e2e.py:138-139,457-472` |
| 219 | 2 | Otros dos scripts con la forma «entrada opcional ausente → salida más chica sin aviso» | `scripts/09_exportar_catalogo.py:126-127` · `scripts/20_paquete_practicante.py:235` |
| 220 | 1 | Cinco GeoJSON del JRC publicados sin lector, y la auditoría de datos es ciega a `jrc/` | `web/data/jrc/rp{10,20,50,200,500}.geojson` · `tests/auditoria_datos.py:274` |
| 221 | 1 | Campos escritos que nadie lee (censo por comuna, `ordenanza_url_vigente`, `solucion`…) | ver §1 |
| 222 | 1 | `estado` no declara `areasRiesgo`, `planos`, `campamentos` | `web/app.js:49-64` |
| 223 | 1 | Las teselas de Esri pasan por la caché de la app, no por la de teselas | `web/sw.js:83-93` |
| 224 | SIN DATO | `comunaDe` atribuye por el punto crítico más cercano sin cota de distancia; `_km` se calcula y no se muestra | `web/app.js:393-417` |

---

## Patrón 1 — El bug vive entre dos piezas correctas

**Comando declarado**: `python tools/auditoria/campos_visor_vs_datos.py` (transcribe a mano cada `properties.X` con su línea y lo compara con las claves reales; el bloque de tokens verifica que la transcripción no dejó nada afuera).

Salida cruda (recortada a lo que importa; la completa está al correrlo):

```
-- Tokens de app.js que NO están en la tabla transcrita (deben ser ruido):
   d: líneas [342, 575, 665]  f: [344, 577, 663, 665]  fecha_dato: [130]  generado: [130]  i: [1662]
## puntos-criticos-inundacion.geojson  n=440
   lee responsable  app.js:[665, 1639]  -> PARCIAL presente 440/440, nulos/vacíos 109
   lee sector       app.js:[877, 1636]  -> PARCIAL presente 440/440, nulos/vacíos 15
   lee __control_inexistente  app.js:[0]  -> FALTA presente 0/440
   claves que el archivo trae y el visor NO lee (6): ['region', 'provincia', 'solucion', 'acciones_prev', 'acciones_sol', 'es_inundacion']
## areas-riesgo-inundacion.geojson  n=63
   lee ordenanza_url      -> PARCIAL 63/63, nulos 54
   lee eae_fecha_ingreso  -> PARCIAL presente 54/63
   claves que el archivo trae y el visor NO lee (8): ['sector', 'nombre', 'usos_permitidos', 'ordenanza_url_vigente', 'es_inundacion', 'origen_capa', 'anio_fuente', 'comuna_fuente']
## laminas/vectorizadas.geojson  n=163  procedencia.capa='A_normativo'
   claves que el archivo trae y el visor NO lee (11): ['clase', 'comuna', 'amenaza', 'fuente', 'anio', 'metodo_original', 'escala_original', 'hectareas', 'origen_lamina', 'descripcion', 'efecto_legal']
## estado-comunas.json [comunas] n=32
   claves que el archivo trae y el visor NO lee (4): ['slug', 'mayores_60', 'viviendas_hacinadas', 'hogares_agua_de_rio']
```

Todo campo que el visor lee existe en su archivo; los PARCIAL tienen guarda en el código (`filter(Boolean)` en 666, `p.sector ?` en 877, `if (p.ordenanza_url)` en 697, `filter(eae_fecha_ingreso)` en 722). El problema está al revés: **lo que se produce y nadie consume**.

Distribución de valores (comando: script `vals.py` del scratchpad, salida cruda):

```
LAMINAS n= 163
  clase: {'Alto': 70, 'Medio': 28, 'Susceptibilidad media': 27, 'AR-2a': 26, 'Susceptibilidad alta': 12}
  efecto_legal: {'None': 137, 'Zona restringida al desarrollo urbano. Los predios afectados deben cumplir el artículo 2.1.17 de la OGUC; ...': 26}
  fuente: {'Estudio de Riesgo, Actualización PRC Angol, sept 2013': 98, 'Levantamiento de riesgos ... Curarrehue ... Decreto Exento N°1802 del 30-12-2025': 39, 'Plan Regulador Comunal de Angol, Plano de Zonificación y Vialidad lámina PRC 09201-1, aprobado por la SEREMI ...; ordenanza local actualizada a marzo de 2026': 26}
AREAS n= 63
  anio: {'2009': 36, '1989': 9, '2012': 5, 'no declarado por la fuente': 4, '1984': 4, '1992': 2, '2010': 1, '2023': 1, '1991': 1}
  anio_fuente: {'Atlas del Riesgo de Desastre, Vicuña y Guzmán, CIGIDEN/IEUT-UC 2025': 59, 'None': 4}
PLANOS n= 20 · estado_tramite: {'Anteproyecto': 20}
  pares de planos con hojas solapadas: 12
    ('..._PRC_Pucon_v3.pdf_p001.png', '..._PRC_Pucon_v4.pdf_p001.png')  [y 11 más]
```

### 201 — Las láminas vectorizadas se dibujan pero no entran al veredicto ni a la ficha
- ARCHIVO:LÍNEA — `web/app.js:333-386` (`evaluar`: consulta `areasRiesgo` en 348, `sar` en 354, `sarCobertura` en 355, `campamentos` 383, `jrc` 384, `gore` 385; **nunca `estado.laminas`**). `web/app.js:1549-1565` las dibuja. `web/app.js:657-970` (`render`) no tiene bloque para ellas. Productor: `scripts/19_estado_comunas.py:135-167`.
- QUÉ PASA — El script 19 publica 163 polígonos (26 son la zona AR-2a del PRC de Angol, con `efecto_legal` declarado y fuente «aprobado por la SEREMI»), el visor los carga y los pinta, y `evaluar()` no los consulta. El único lugar donde la ficha los nombra es el inventario de la comuna («124 polígono(s) que convertimos nosotros»), que por diseño «no dice si tu casa se inunda».
- CÓMO SE VE — Una persona toca un punto dentro de la mancha achurada de Angol y lee «Registros de inundación a cierta distancia» (nivel BAJO) y, en la ficha, «Este punto no cae dentro de un área de riesgo por inundación declarada en el plan regulador». Está dentro de una zona restringida al desarrollo urbano del PRC vigente.
- CÓMO REPRODUCIRLO — `python tools/auditoria/visor_relaciones_e2e.py`, medida M1.
- SALIDA CRUDA —
  ```
  == M1 lámina vectorizada AR-2a (Angol) ==
    punto: -72.69874 -37.78127 | props: {'clase': 'AR-2a', 'comuna': 'ANGOL', 'anio': '2026', 'fuente': 'Plan Regulador Comunal de Angol, Plano de Zonificación y Vialidad lámina PRC 09201-1, aprobado por la SEREMI ...'}
    efecto_legal declarado: Zona restringida al desarrollo urbano. Los predios afectados deben cumplir el artículo 2.1
    res.nivel = bajo
    respuesta corta: ... ℹ️ | Registros de inundación a cierta distancia | ... El registro más cercano de inundación está a | 767 metros.
    ficha dice «no cae dentro de un área de riesgo»: True
    ficha menciona 'derivad': False
    CONTROL área MINVU: Temuco ANEGAMIENTO | ficha dice «cae dentro de»: True | nivel: alto
  ```
- CONFIANZA — CONFIRMADO (código leído + medido en navegador con control positivo).
- GRAVEDAD — 5.

### 205 — El año del área MINVU viene del Atlas CIGIDEN, la ficha lo firma como MINVU y a la vez dice que no está declarado
- ARCHIVO:LÍNEA — `scripts/06_areas_riesgo_prc.py:342-350` escribe `anio` desde `config` y `anio_fuente = "Atlas del Riesgo de Desastre, Vicuña y Guzmán, CIGIDEN/IEUT-UC 2025"`. `web/app.js:645-655` (`atribucion`) imprime «Fuente: {fuente} · Año: {anio}» y **nunca lee `anio_fuente`** (instrumento: «claves que el visor NO lee: … 'anio_fuente'»). `web/app.js:725-731` imprime, para los 54 polígonos con EAE, «El año del plan regulador no está declarado en la capa publicada por MINVU».
- QUÉ PASA — Dos frases escritas en momentos distintos: la de 725 es anterior a que el 06 empezara a rellenar el año desde el Atlas; la atribución no distingue de dónde salió el año.
- CÓMO SE VE — En la misma ficha: «Fuente: MINVU — áreas de riesgo … · Año: 2010» y tres líneas más abajo «El año del plan regulador no está declarado en la capa publicada por MINVU». Y el año, que es de un tercero, queda firmado por el MINVU.
- CÓMO REPRODUCIRLO — medida M5 del arnés.
- SALIDA CRUDA —
  ```
  == M5 == polígono: Temuco | anio: 2010 | anio_fuente: Atlas del Riesgo de Desastre, Vicuña y Guzmán, CIGIDEN/IEUT-UC 2025 | eae: 22/07/2025
    ficha muestra «Año: …»: Año: 2010
    ficha dice «no está declarado en la capa publicada por MINVU»: True
    ficha menciona 'Atlas' o 'CIGIDEN': False
  ```
- CONFIANZA — CONFIRMADO. GRAVEDAD — 3.

### 206 — Dos hojas de plano cubren el mismo punto y la ficha muestra sólo la primera
- ARCHIVO:LÍNEA — `web/app.js:844-845` (`if (res.planos.length) { const p = res.planos[0];`), encabezado singular «El plano de tu comuna» en 851. Índice: `scripts/10_exportar_superposiciones.py:186` (`sorted(origen.glob("*.tif"))` → v3 antes que v4).
- QUÉ PASA — 12 pares de hojas se solapan; en Pucón coexisten dos versiones del anteproyecto (v3 y v4) y la ficha muestra siempre la v3.
- CÓMO SE VE — Quien consulta Pucón ve «04 Anteproyecto-Planos PRC Pucon v3 p001» y el botón carga ese plano; la v4, que existe y cubre el mismo punto, no aparece.
- CÓMO REPRODUCIRLO — medida M2 del arnés.
- SALIDA CRUDA —
  ```
  planos que cubren el centro de v4 p001: ['..._Pucon_v3.pdf_p001.png', '..._Pucon_v4.pdf_p001.png']
  bloque del plano en la ficha: ['EL PLANO DE TU COMUNA', 'ANTEPROYECTO', '', 'Tenemos el plano ...']
  la ficha menciona 'v4': False | menciona 'v3': True
  res.planos según el visor: ['..._Pucon_v3.pdf_p001.png', '..._Pucon_v4.pdf_p001.png']
  ```
- CONFIANZA — CONFIRMADO. GRAVEDAD — 3.

### 208 — La capa derivada se publica con `capa_evidencia = A_normativo`
- ARCHIVO:LÍNEA — `scripts/19_estado_comunas.py:156` y `scripts/18_vectorizar_laminas.py:421,538` escriben `capa_evidencia="A_normativo"`; `scripts/comun.py:290-292` sólo admite `A_normativo | B_observado | C_modelado | D_operacional | inventario`; el docstring de `scripts/18_vectorizar_laminas.py:41-43` dice que «la capa se etiqueta `A_derivado`». Salida del instrumento: `laminas/vectorizadas.geojson … capa='A_normativo'`.
- QUÉ PASA — El sello que «el frontend usa para no mezclar evidencia legal con modelo» (comun.py:280-281) dice *normativo* para lo que el propio sitio rotula *derivado*. Quien consuma el GeoJSON fuera del visor (paquete del practicante, script 20; terceros) lee que es instrumento normativo.
- CÓMO SE VE — En `web/data/laminas/vectorizadas.geojson` y en el GPKG del practicante, `procedencia.capa_evidencia: "A_normativo"` junto a `incertidumbre: "NO tiene el efecto legal del vectorial del MINVU"`.
- CÓMO REPRODUCIRLO — `grep -n capa_evidencia scripts/18_vectorizar_laminas.py scripts/19_estado_comunas.py scripts/comun.py`.
- SALIDA CRUDA — `scripts/18_vectorizar_laminas.py:421: capa_evidencia="A_normativo"` · `:538: capa_evidencia="A_normativo"` · `scripts/comun.py:290: assert capa_evidencia in ("A_normativo", "B_observado", "C_modelado", "D_operacional", "inventario")`.
- CONFIANZA — CONFIRMADO. GRAVEDAD — 3.

### 220 — Cinco GeoJSON del JRC publicados sin lector; la auditoría de datos es ciega a `jrc/`
- ARCHIVO:LÍNEA — `web/data/jrc/rp{10,20,50,200,500}.geojson` (≈208 KB); `web/app.js:85` y `web/sw.js:45` sólo nombran `rp100`; `tests/auditoria_datos.py:274` salta `jrc/` en la búsqueda de huérfanos.
- SALIDA CRUDA — `grep -rn -o -E "rp[0-9]+\.geojson" web/*.js web/*.html web/sw.js | sort | uniq -c` → `1 web/app.js:85:rp100.geojson · 2 web/sw.js:45:rp100.geojson`.
- CONFIANZA — CONFIRMADO. GRAVEDAD — 1.

### 221 — Campos escritos que nadie lee
- ARCHIVO:LÍNEA — salida del instrumento, bloques «claves que el archivo trae y el visor NO lee»: `estado-comunas.json` → `mayores_60, viviendas_hacinadas, hogares_agua_de_rio` (escritos en `19:197-199`); `areas-riesgo` → `ordenanza_url_vigente, usos_permitidos, anio_fuente, comuna_fuente`; puntos críticos → `solucion, acciones_prev, acciones_sol`; SAR huella → `tipo`; planos → `aptitud, fuente, anio, procedencia_metodo`.
- QUÉ PASA — No es un defecto por sí mismo (§6.3 acepta publicar más de lo que el visor usa), pero `anio_fuente` (→ 205) y `efecto_legal` (→ 201) son los dos casos donde el campo no leído es justamente el que cambia la lectura.
- CONFIANZA — CONFIRMADO. GRAVEDAD — 1.

---

## Patrón 2 — Un dato sin inicializar no falla: miente

**Comandos declarados**: lectura completa de `web/app.js:49-131` (objeto `estado` y `cargarDatos`) y de todos los `estado.X` que se leen antes o fuera de `cargarDatos`; en scripts, `grep -n -E 'or \{|or \[\]|\.get\([^)]*, *(0|""|\[\])' scripts/19_estado_comunas.py scripts/20_paquete_practicante.py scripts/09_exportar_catalogo.py` y lectura de las funciones. Medidas M3 y M6 del arnés; `solape_gore_y_extension_jrc.py`.

### 202 — El texto compartido pierde la advertencia de «sin registros» por leer un campo que no existe
- ARCHIVO:LÍNEA — `web/app.js:1089` (`if (estado.ultimo && estado.ultimo.nivel === 'sindato')`); `estado.ultimo` se asigna en `:975` como `{ res, etiqueta, lon, lat }` — el nivel vive en `estado.ultimo.res.nivel`.
- QUÉ PASA — `estado.ultimo.nivel` es siempre `undefined`, así que las dos líneas «OJO: que no haya registro NO significa que acá no se inunde» (1090-1091) no viajan nunca. El comentario de 1086-1088 explica que existen precisamente porque la ficha «se reenvía por WhatsApp y ahí “sin registros” queda solo».
- CÓMO SE VE — En pantalla el aviso fuerte aparece (`.aviso-fuerte`, 604-608). En el texto que se comparte o se copia, no: «SIN REGISTROS EN LAS FUENTES CONSULTADAS … Sin puntos críticos registrados en 1,5 km. Esto NO es información oficial ni un pronóstico.»
- CÓMO REPRODUCIRLO — medida M3 del arnés (busca un punto con `res.nivel === 'sindato'` en rejilla y llama `textoFicha()`).
- SALIDA CRUDA —
  ```
  punto: {'lon': -73.6, 'lat': -37.4} | res.nivel = sindato
  pantalla muestra .aviso-fuerte: 1
  textoFicha() contiene 'OJO': False
  textoFicha() contiene 'no significa que acá no se inunde': False
  estado.ultimo.nivel = None
  --- textoFicha() crudo ---
  SIN REGISTROS EN LAS FUENTES CONSULTADAS
  Ubicación: M3 sindato
  El satélite miró este punto el 3 de agosto de 2026 y no detectó agua.
    Ojo: el radar no ve agua bajo bosque cerrado ni en zona urbana densa,
    y es la foto del instante de la pasada, no el máximo del evento.
  Sin puntos críticos registrados en 1,5 km.
  Esto NO es información oficial ni un pronóstico.
  En emergencia: SENAPRED y tu municipio.
  ```
- CONFIANZA — CONFIRMADO. GRAVEDAD — 4.

### 204 — «No detectamos vacíos» para Temuco, cuyo único polígono MINVU es de anegamiento
- ARCHIVO:LÍNEA — `scripts/19_estado_comunas.py:183-185` (`if not con_area.get(k): faltas.append("no tiene su área de riesgo por inundación …")`) cuenta **cualquier** polígono de `areas-riesgo-inundacion.geojson`, que por `06:356-362` incluye anegamiento, napa y litoral. `web/app.js:466` («No detectamos vacíos en las fuentes que revisamos.») y `:546` (mismo texto en `textoComuna`, el que se reenvía).
- QUÉ PASA — Un valor por omisión plausible: «tiene área de riesgo» se rellena con un polígono de otro fenómeno. Nueve comunas quedan con `le_falta` vacío; Temuco (la más poblada) con un solo polígono, y ese polígono es ANEGAMIENTO, no inundación fluvial — la distinción que REGLAS §1.4 dice que hay que hacer.
- CÓMO SE VE — El bloque «Con qué cuenta Temuco» y el texto que se comparte por WhatsApp dicen «No detectamos vacíos en las fuentes que revisamos.» La solicitud Ley 20.285 (`textoSolicitud`, 494-532) para Temuco sale sin ninguna viñeta de «lo que falta».
- CÓMO REPRODUCIRLO — medida M6 del arnés; `vals.py` → `ESTADO-COMUNAS: le_falta vacío en: [('Collipulli', 36, …), ('Gorbea', 1, …), ('Nueva Imperial', 1, …), ('Pitrufquen', 4, …), ('Saavedra', 1, …), ('Temuco', 1, 18, 0, 0), ('Tolten', 4, …), ('Traiguen', 1, …), ('Villarrica', 2, …)]`.
- SALIDA CRUDA —
  ```
  polígonos MINVU de Temuco: [{'clas': 'ANEGAMIENTO', 'tipo': 'anegamiento'}]
  estado-comunas Temuco: le_falta = [] | poligonos_area_riesgo = 1
  textoComuna(Temuco) dice «No detectamos vacíos»: True
  ```
- CONFIANZA — CONFIRMADO. GRAVEDAD — 3.

### 222 — `estado` no declara `areasRiesgo`, `planos`, `campamentos`
- ARCHIVO:LÍNEA — `web/app.js:49-64` declara 12 claves; `areasRiesgo` (89), `planos` (95) y `campamentos` (114) se crean al vuelo en `cargarDatos`. Todas las lecturas están guardadas (`estado.planos || []` en 177, 196, 253, 267; `estado.areasRiesgo?.` en 720, 1817; `estado.campamentos?.` en 1818) y `consultar` exige `estado.puntos` (1254).
- CONFIANZA — CONFIRMADO (cosmético; no encontré un camino que lea antes del fetch sin guarda). GRAVEDAD — 1.

**Medido y limpio en este patrón** — GORE: «MAXIMA con punto representativo dentro de un MEDIA: 0» (control artificial `(1, 1)`), así que `res.gore[0]` (918) no puede degradar una clase máxima a media. JRC: el ráster recortado cubre el bbox completo (`lon [-73.700, -70.900]`) y «columna más al este con agua → lon ≈ −71.654»; que el este de la región «quede fuera de la mancha» (905) es del modelo, no de un recorte corto. `atribucion()` (649) tiene el fallback `p.anio || proc.fecha_dato`, pero ningún archivo publicado deja `anio` vacío en sus features (todos 100 % presentes en el instrumento), así que hoy no se dispara.

---

## Patrón 3 — La lista de clientes que se desactualiza

**Comandos declarados y salida cruda**:

```
$ grep -n 'add_argument(' scripts/*.py            # filtros
07: --prioridad --comuna --max-mb --limite(default=40) --solo-listar
08: pdf --pagina --todas --saltar-existentes
12: --comuna --redescubrir --solo-listar --max-mb
14: --evento --bbox --forzar --conservar-fechas --verificar
18: --id --inspeccionar --pagina --censo
20: --provincia --salida
$ for f in scripts/*.py; do grep -c '^Salida:' $f; grep -c '^Requiere:' $f; done
   Salida=1 en los 20 numerados · Requiere=0 en los 20 numerados
$ grep -n -i "requiere" scripts/*.py
scripts/02_jrc_amenaza_modelada.py:18:   distribuye vía Google Earth Engine, que requiere cuenta. Ver README.
$ grep -n 'procedencia(' scripts/*.py   # 17 llamadas en 01,02,04,06,08,09,10,13,14,15,16,17,18(x2),19(x2)
$ python …/crs.py   # 46 GeoJSON: crs=None (RFC 7946), todos dentro del bbox salvo 4 cifras de redondeo en lat −39,650
$ grep -n -E "lam-fill|lam-line|jrc-fill|laminas" tests/auditoria_e2e.py
457: if page.evaluate("() => !!estado.laminas")   461-462: getLayer('lam-line') … line-dasharray
```

Invariante por invariante:

| Invariante | Quiénes deben cumplirla | Quiénes no |
|---|---|---|
| Todo producto publicado en `web/data/` pasa por `comun.procedencia()` | 01, 02, 06, 09, 10, 13, 14, 15, 19 | ninguno (todos los `web/data/*` traen `procedencia` con las 8 claves; instrumento §1) |
| Todo script declara `Salida:` y `Requiere:` (REGLAS §6.1) | 20 scripts | **`Requiere:` 0/20** → 215 |
| Todo script con filtro fusiona su índice (§3) | 07 (`--comuna`, `--limite`), 12 (`--comuna`), 18 (`--id`), 14 (`--evento`, `--bbox`) | 07 fusiona (`07:390 fusionado`), 12 fusiona (`12:392-404`), 18 escribe un archivo por `id` (`18:436,550`) → seguro; **14 con `--bbox` sobrescribe** → 207 |
| Toda capa del visor tiene comprobaciones en la e2e (§4.1) | osm, sat, jrc-fill, gore-fill, sar-fill/line, lam-fill/line, ar-fill/line, camp-fill/line, pc-circ, huellas-fill/line | **`jrc-fill` y `lam-fill` no están en la lista de 138-139**; `lam-line` sólo por `getLayer` (461); ningún bloque consulta un punto dentro de una lámina → 218 |
| Todo `web/data/*.geojson` en EPSG:4326 (§6.2) | 46 archivos | ninguno (salida de `crs.py`) |

### 207 — `--bbox` del script 14 sobrescribe la capa B publicada con un recorte de prueba
- ARCHIVO:LÍNEA — `scripts/14_sar_huella_observada.py:702-703` («recorta el área de trabajo (para probar rápido)»), `:717` (`bbox = args.bbox or cfg["region"]["bbox"]`), `:877-879` (`escribir_geojson(huella_feats, salida / "huella-observada.geojson", meta)` y cobertura, sin fusionar ni cambiar de destino), `:900` (índice).
- QUÉ PASA — Es la forma exacta de REGLAS §3: un filtro que escribe el índice entero. Una corrida de prueba sobre Angol publica una huella y una **cobertura** que sólo cubren Angol.
- CÓMO SE VE — Para el resto de la región la ficha pasaría a decir «El satélite no pasó por acá … en la ventana del evento» (825-829) sobre lugares que sí se observaron; la cifra de portada (1832) y la nota del control (1862-1868) cambiarían solas.
- CÓMO REPRODUCIRLO — lectura de las líneas citadas; no se corrió el script (baja escenas de Planetary Computer).
- CONFIANZA — CONFIRMADO por lectura del flujo, no ejecutado. GRAVEDAD — 3.

### 215 — Ningún script declara `Requiere:` y la prueba sólo exige `Salida:`
- ARCHIVO:LÍNEA — REGLAS §6.1 («Cada script declara en su docstring **`Requiere:`** además de `Salida:`»); `tests/test_scripts.py:50-64` sólo busca `Salida:`; salida cruda arriba: `Requiere=0` en 20/20.
- CÓMO SE VE — El grafo de dependencias vive sólo en `scripts/ORDEN.md`, escrito a mano; el commit `a6c08f1` dice que dos pruebas nuevas «exigen … que cada uno diga qué produce», pero la mitad de la regla (qué necesita) no tiene prueba ni cumplimiento.
- CONFIANZA — CONFIRMADO. GRAVEDAD — 2.

### 216 — Tres referencias a `docs/REGLAS.md`, que no existe
- ARCHIVO:LÍNEA — `scripts/07_buscar_laminas_riesgo.py:27`, `scripts/20_paquete_practicante.py:393,404` (van al `LEEME.md` que recibe el practicante: `data/processed/paquete_malleco/LEEME.md:37,48`). El archivo real es `REGLAS.md` en la raíz. El mismo commit `a6c08f1` cuenta que «se borró» el `docs/REGLAS.md` duplicado. Además `20:393` dice «Son doce» y `grep -c -E '^##+ ' REGLAS.md` → `32`.
- SALIDA CRUDA — `grep -rn "docs/REGLAS" --include=*.py --include=*.md .` → 5 líneas (las 3 citadas + 2 en el LEEME generado).
- CONFIANZA — CONFIRMADO. GRAVEDAD — 2.

---

## Patrón 4 — Apagar ≠ limpiar; borrar ≠ ocultar

**Comandos declarados**: `grep -n "isStyleLoaded" web/app.js`; lectura de `web/sw.js` completo; lectura de `cerrarSugerencias`/`pedirSugerencias` (1219-1248), `consultar`/`render`/`renderFuera` (1250-1295, 657-1039), `ocultarPlanos`/`actualizarPlanos` (235-300) y los ocho manejadores de casilla (1693-1780); medida M4 del arnés.

```
$ grep -n "isStyleLoaded" web/app.js
211:  if (!m || !m.isStyleLoaded()) return false;
244:  // ⚠️ NO se pone `isStyleLoaded()` como guardián.
277:  if (!m || !casilla || !casilla.checked || !m.isStyleLoaded()) return;
1493:    if (capasPuestas || !m.isStyleLoaded()) return;
1735:    if (!m.isStyleLoaded()) {
1760:    if (!m.isStyleLoaded()) {
```

### 209 — La lista de sugerencias vuelve a abrirse sola después de elegir una comuna
- ARCHIVO:LÍNEA — `web/app.js:1243-1247` arma `SUG.timer` (450 ms) y al vencer repinta `[...sugerenciasLocales(texto), ...dirs]` si `$('#q').value === texto`; `cerrarSugerencias` (1219-1227) borra items y DOM pero **no hace `clearTimeout(SUG.timer)`**; elegir una comuna (`accion`, 1145) no cambia el valor del campo.
- QUÉ PASA — Apagar la lista no limpia el temporizador. El caso comuna es el que se rompe (el caso dirección reescribe `#q` en 1173 y por eso sobrevive al chequeo de 1245). Sin red también pasa: `dirs` queda `[]` pero las locales bastan para repintar.
- CÓMO SE VE — Escribes «Angol», tocas la sugerencia, el mapa viaja y la ficha aparece; medio segundo después la lista de sugerencias se despliega otra vez encima del buscador.
- CÓMO REPRODUCIRLO — medida M4 del arnés.
- SALIDA CRUDA —
  ```
  oculta justo al elegir (CONTROL): True
  oculta 2,5 s después: False | items visibles: ['◧', '⌖']
  campo #q vale: Angol
  ```
- CONFIANZA — CONFIRMADO. GRAVEDAD — 2.

### 211 — El arreglo «esperar al estilo» llegó a dos casillas de ocho
- ARCHIVO:LÍNEA — `#cap-sar` (1735-1739) y `#cap-planos` (1760-1770) hacen `if (!m.isStyleLoaded()) { … m.once('idle', …) }` con el comentario «Pedirle al usuario que reintente es trasladarle un problema nuestro». `alternar` (1693-1697, usada por `cap-puntos`, `cap-jrc`, `cap-gore`), `cap-derivadas` (1700-1709), `cap-camp` (1743-1749) y `cap-areas` (1774-1780) hacen `if (m.getLayer(capa))` y, si la capa aún no existe, no hacen nada y la casilla queda marcada.
- CÓMO SE VE — Quien marca «Modelo regional» mientras el estilo carga (3G, gama baja) ve la casilla marcada y ninguna mancha, sin mensaje. El comentario de 1713-1715 describe exactamente ese síntoma como la razón del arreglo en `cap-sar`.
- CÓMO REPRODUCIRLO — no medido (requiere sincronizar el clic con el estado del estilo).
- CONFIANZA — SOSPECHA (asimetría confirmada por lectura; el síntoma no se produjo). GRAVEDAD — 2.

### 212 — El arreglo de `ocultarPlanos` no llegó a `actualizarPlanos`
- ARCHIVO:LÍNEA — `web/app.js:244-251` explica por qué se quitó la guarda `isStyleLoaded()` de `ocultarPlanos` (con ella «la limpieza se saltaba ENTERA y en silencio»). `actualizarPlanos` (`:277`) conserva `!m.isStyleLoaded()` y `return` sin reintento; se llama desde cada `moveend` (1674).
- CÓMO SE VE — Un paneo cuyo `moveend` cae mientras el estilo está ocupado (p. ej. justo después de cargar una imagen, el caso que 246 describe) no carga los planos de la vista nueva hasta el siguiente movimiento.
- CONFIANZA — SOSPECHA (lectura; no reproducido). GRAVEDAD — 2.

### 213 — Subir `VERSION` borra también la caché de teselas
- ARCHIVO:LÍNEA — `web/sw.js:16-18` (`CACHE_TILES = \`${VERSION}-tiles\``), `:63-66` (`activate` borra todo lo que no empiece por `VERSION`). REGLAS §7.4 obliga a subir `VERSION` «en cada cambio del frontend»; `sw.js:11-12` promete que «la comuna que ya miraste queda disponible».
- CÓMO SE VE — Cada publicación (van 21) deja a quien tenía el sitio instalado sin ninguna tesela guardada: la próxima vez sin señal el mapa base sale en blanco aunque los datos sí estén.
- CONFIANZA — CONFIRMADO por lectura (el borrado es literal); efecto no medido offline. GRAVEDAD — 2.

### 214 — Sin red, un dato o PNG que no está en caché se sirve como `index.html`
- ARCHIVO:LÍNEA — `web/sw.js:104-106` (`const hit = await c.match(req) || await c.match('index.html'); if (hit) return hit;`) aplica a **todo** lo que no sea Nominatim ni OSM, incluidos `data/planos/*.png` (que no se precachean) y los GeoJSON opcionales.
- CÓMO SE VE — Offline, «Ver el plano sobre el mapa» de un plano nunca visto recibe HTML como imagen: capa vacía, sin error — el «peor modo de fallar» que `app.js:220-223` describe. Un GeoJSON opcional recibido como HTML cae en el `catch` de `cargarDatos` y se lee como «capa no disponible en esta instalación».
- CONFIANZA — SOSPECHA (lectura; no medido con red cortada). GRAVEDAD — 2.

### 223 — Las teselas de Esri pasan por la caché de la app
- ARCHIVO:LÍNEA — `web/sw.js:83` sólo desvía `tile.openstreetmap.org` a `CACHE_TILES`; `server.arcgisonline.com` cae en la rama de la app (`cache: 'no-cache'`, `c.put` en `CACHE_APP`).
- CONFIANZA — CONFIRMADO por lectura. GRAVEDAD — 1.

**Limpio en este patrón** — `ponerMarcador` quita el marcador anterior (1466-1471); una consulta nueva reemplaza `innerHTML` de `#respuesta` (613) y `#detalle-ficha` (971), y `renderFuera` limpia ambos y pone `estado.ultimo = null` (1272-1294); `sugerenciasDirecciones` aborta el fetch anterior (1158-1159); `activate` del SW sí borra cachés de versiones viejas (63-66); `ocultarPlanos` libera capa y fuente (256-257) y la e2e lo mide con planos realmente cargados (310-334). En la corrida del arnés: «errores JS durante la corrida: ninguno».

---

## Patrón 5 — El clamp que se come el rango

**Comando declarado**: `grep -n -E 'slice\(|Math\.(min|max)|limit=|maxZoom|minZoom|MAX_|\.first|\[0\]' web/app.js` (leído sobre el archivo completo). Lista completa de recortes y su veredicto:

| Línea | Recorte | ¿Se dice? |
|---|---|---|
| 295-299 | `enVista.slice(0, MAX_PLANOS_SIMULTANEOS)` | sí: «Mostrando N de M planos» |
| 662, 871-872 | `res.cerca.slice(0, 5)` en la ficha | sí: «Hay N puntos … Los más cercanos:» |
| 1076-1085 | `res.cerca.slice(0, 3)` en el texto compartido | **no** → 210 |
| 845 | `res.planos[0]` | **no** → 206 |
| 360, 567, 746 | `res.sar[0]` | no, pero la huella es una sola capa con misma fecha por track (1075 features, 2 fechas); el orden sólo elige la fecha mostrada |
| 918 | `res.gore[0]` | no; medido: 0 anidamientos (limpio) |
| 939 | `res.campamentos[0]` | no; 15 polígonos, no medido si se solapan (SIN DATO, gravedad baja) |
| 1117 | `limit=1` en `geocodificar` | **no** → 217 |
| 1140 | `.slice(0, 4)` comunas sugeridas | no, es una lista de sugerencias (aceptable) |
| 1787 | `.slice(0, 12)` tabla de comunas | el título dice «Comunas con más registros» (aceptable) |
| 1880 | `maxZoom: 13` al centrar comuna | aceptable |
| `catalogo.js:43` | `terminos.slice(0, 3)` | no (cosmético) |

### 210 — El texto compartido recorta a 3 puntos críticos sin decir cuántos hay
- ARCHIVO:LÍNEA — `web/app.js:1076-1085`: «Puntos críticos registrados cerca:» + 3 viñetas; la pantalla (871) sí dice «Hay N puntos críticos registrados a menos de 1500 m».
- CÓMO SE VE — Un sector con 9 puntos crónicos se reenvía por WhatsApp como si tuviera 3.
- CONFIANZA — CONFIRMADO por lectura. GRAVEDAD — 2.

### 217 — Enter sin elegir sugerencia geocodifica con `limit=1`
- ARCHIVO:LÍNEA — `web/app.js:1117-1125` (`limit=1`, `return j[0]`), disparado desde `buscar()` (1297-1313) al pulsar Enter sin marcar sugerencia (1938).
- CÓMO SE VE — «Los Sauces 100» existe en varias comunas; el visor responde por el primero que devuelva Nominatim y la etiqueta es lo único que lo delata.
- CONFIANZA — CONFIRMADO por lectura. GRAVEDAD — 2.

---

## Patrón 6 — Un arreglo que cubre un camino de dos

**Comandos declarados**: `git log --stat -8`, `git show a6c08f1 -- scripts/`; para cada arreglo, grep de la forma en los demás caminos; `tools/auditoria/script19_entradas_ausentes.py`.

| Commit | Arreglo | Caminos que debían recibirlo | Recibido |
|---|---|---|---|
| `a6c08f1` | 10: entrada ausente → `SystemExit`, no reescribir el índice | 19 (lee 6 salidas), 09 (lee 07/08/muni), 20 (lee 7 capas), 13, 15 | **19 no** → 203; 09 y 20 parcial → 219; 13 y 15 se caen solos (13: consulta ArcGIS y `escribir_geojson` de lo que llega; 15: no leído a fondo, SIN DATO) |
| `a6c08f1` | `Salida:` en 04/07/08/11 + prueba | `Requiere:` en los 20 (REGLAS §6.1) | **no** → 215 |
| `a6c08f1` | borrar `docs/REGLAS.md` duplicado | referencias en 07:27, 20:393, 20:404 | **no** → 216 |
| `af47b56` | descartar la lámina DGA | `config/laminas.yaml`, `web/data/laminas` | sí: `origen_lamina` tiene 3 valores y ninguno es DGA (vals.py) |
| `3cb34ad` | `estado_tramite` en planos + sello en la leyenda | ficha (849-861), leyenda (index 114-116), e2e (447-452) | sí en pantalla; el texto compartido no menciona planos (no aplica) |
| `d4625db` | restaurar shards por comuna | 01 los escribe (319-341), auditoría de datos los suma (152-163) | sí |
| (anterior) | `ocultarPlanos` sin guarda `isStyleLoaded` | `actualizarPlanos` | **no** → 212 |
| (anterior) | `cap-sar` espera `idle` si el estilo no está | las otras 6 casillas | **no** → 211 |
| (anterior) | aviso «sin registros ≠ no se inunda» en pantalla y en el texto compartido | `resumen()` y `textoFicha()` | pantalla sí; texto **no** por el campo inexistente → 202 |

### 203 — El script 19 con una entrada ausente publica un inventario falso, sin error
- ARCHIVO:LÍNEA — `scripts/19_estado_comunas.py:103` (`idx = cargar(…indice-comunas.json) or {"comunas": []}`), `:106` (áreas `or {"features": []}`), `:109` (planos `or {}`), `:119` (catálogo `or {"comunas": []}`), `:238-241` escribe `web/data/estado-comunas.json` sin condición. Es la forma que `a6c08f1` arregló en el 10 («corría entero sin error y reescribía … VACÍO»), y REGLAS §2 la nombra: «Un índice previo ilegible es motivo para parar». Acá el índice no ilegible sino **ausente** se trata como «todo en cero».
- QUÉ PASA — Sin `catalogo-documentos.json` las 32 comunas reciben «no publica ningún documento de planificación territorial» y «no le encontramos ninguna lámina»; sin `indice-comunas.json` las 32 quedan con 0 puntos críticos. Se escribe y se publica; el visor, el texto compartido y la solicitud Ley 20.285 lo reproducen tal cual.
- CÓMO SE VE — Angol (41 documentos, 11 láminas) diría «no publica ningún documento … no le encontramos ninguna lámina», y esa frase iría en una solicitud formal al MINVU con timbre y fecha.
- CÓMO REPRODUCIRLO — `SCRATCH=%TEMP% python tools/auditoria/script19_entradas_ausentes.py` (corre sobre una copia; el repositorio no se toca).
- SALIDA CRUDA —
  ```
  PUBLICADO : 32 comunas · puntos_inundacion total=440 · documentos total=354 · con le_falta vacío=9
  E0 completo: 32 comunas · puntos_inundacion total=440 · documentos total=354 · con le_falta vacío=9
    (E0 difiere del publicado sólo en personas/mayores_60/viviendas_hacinadas/hogares_agua_de_rio: la copia no lleva el censo)
  E1 sin catálogo: 32 comunas · puntos_inundacion total=440 · documentos total=0 · con le_falta vacío=0 · frases le_falta=Counter({'no le encontramos ninguna lámina …': 32, 'no publica ningún documento …': 32, 'no tiene su área de riesgo …': 20})
  E2 sin índice de comunas: 32 comunas · puntos_inundacion total=0 · documentos total=354 …
    E1 escribió estado-comunas.json: True
    E1 Angol: {'comuna': 'Angol', 'documentos': 0, 'laminas_localizadas': 0, 'le_falta': [las tres frases]}
  ```
- CONFIANZA — CONFIRMADO. GRAVEDAD — 4.

### 219 — Otros dos scripts con la forma «entrada opcional ausente → salida más chica sin aviso»
- ARCHIVO:LÍNEA — `scripts/09_exportar_catalogo.py:126-127` (`if muni.exists():` sin `else`/log: el catálogo sale sin los documentos municipales y sin decirlo); `scripts/20_paquete_practicante.py:235` (`cargar(…estado-comunas.json) or {"comunas": []}` → tareas sin estado). El 20 en `:128-134` sí se cae si faltan los puntos.
- CONFIANZA — CONFIRMADO por lectura; no ejecutados. GRAVEDAD — 2.

---

## Patrón 7 — El observable equivocado

**Comando declarado**: lectura completa de `tests/test_scripts.py` (64), `tests/auditoria_datos.py` (408) y `tests/auditoria_e2e.py` (1006); `grep -n -E "lam-fill|lam-line|jrc-fill|laminas" tests/auditoria_e2e.py`.

### 218 — La e2e no mira `jrc-fill` ni `lam-fill`, y nunca consulta dentro de una lámina ni lee el texto compartido
- ARCHIVO:LÍNEA — `tests/auditoria_e2e.py:138-139` (lista de capas esperadas: osm, pc-circ, ar-fill, huellas-fill, camp-fill, sar-fill, sar-line, gore-fill); `:457-472` comprueba que las láminas **están cargadas y punteadas**, no que la ficha las use; ningún bloque llama `textoFicha()` (grep: 0 apariciones); `:569-587` consulta dentro de un área MINVU pero ninguna dentro de una lámina.
- QUÉ PASA — Es REGLAS §4.1 al pie de la letra: la capa derivada tiene comprobaciones de que existe, no de que sirve. 201 y 202 pasan en verde por esto. El 273/273 de hoy no los ve.
- CONFIANZA — CONFIRMADO. GRAVEDAD — 2.

Otros observables revisados y **aceptados**: `auditoria_datos.py:274` salta `jrc/` (→ 220, gravedad 1); los clics dobles de 474-488 miden clicabilidad, que es lo que declaran; la prueba de fuga (310-334) sí acerca a zoom 13 antes de medir y falla si `con == 0` (§4.2 cumplida); `esperar_mapa` (99-106) espera por contenido; la de «sin cobertura» usa `[-71.0, -37.5]` y la cobertura llega a lon −70,906 (crs.py), así que el punto está fuera de cobertura sólo si ningún polígono lo contiene — pasó, pero es frágil ante un track nuevo (nota, no hallazgo).

---

## Patrón 8 — Constantes calibradas para ESTA instalación

**Comando declarado**: `grep -n -E 'C:\\\\|C:/|/Users/|nmend|%TEMP%|TEMP\b|localhost|127\.0\.0\.1|:87[0-9][0-9]|:88[0-9][0-9]|8792|dpi\s*=|DPI|Program Files|Anaconda|\.exe|Escritorio|OneDrive|HOME|USERPROFILE|tesseract|gdal_|chrome|msedge' scripts/*.py tests/*.py web/*.js web/*.html config/*` y `grep -n -E 'C:|/Users|OneDrive|Escritorio|localhost|\.exe' config/*`.

Salida cruda: en `scripts/` sólo `03:36 DPI = 400`, `08:59 DPI = 300`, sus usos, y `18:34` («el binario de tesseract no está instalado»); en `tests/` sólo `auditoria_e2e.py:14` (doc), `:46,61,63` (servidor propio en `127.0.0.1` y puerto libre) y `spec.loader.exec_module`; en `web/` sólo el regex de fecha (`app.js:312`); en `config/` nada. `comun.py:35` deriva `WEB_DATA` de `RAIZ`, y `RAIZ` de `__file__`.

**Sin hallazgos.** Los `DPI` son parámetros del render de PDF, no de esta máquina. La única dependencia de instalación es de diseño y está escrita: `18:33-36` decide declarar los rótulos a mano *porque* tesseract no está instalado acá; si otro computador lo tuviera, el script no lo usaría igual (no es un bug, es una decisión documentada).

---

## SIN DATO

- **224** — `comunaDe` (`web/app.js:393-417`) atribuye la comuna por el punto crítico más cercano sin cota; calcula `_km` (416) y no lo muestra. Cuántos puntos de la región quedarían atribuidos a la comuna vecina no se puede medir sin el límite administrativo, que el proyecto no tiene (lo dice 219-221 del script 19).
- Solape de los 15 campamentos entre sí (`res.campamentos[0]`, 939): no medido.
- `scripts/15_gore_amenaza.py` y `13` frente al patrón 6: 13 leído entero (se cae si ArcGIS no responde); 15 no leído a fondo.
- Comportamiento real del service worker sin red (213, 214): sólo lectura.
- 211 y 212: la asimetría está en el código; el síntoma no se produjo.

---

## VERIFICADO LIMPIO

Lo que se miró y está sano, con lo que lo respalda:

1. **Todo campo que el visor lee existe en su archivo** — `tools/auditoria/campos_visor_vs_datos.py`: 0 FALTA reales (el único FALTA es el control positivo), y los 6 PARCIAL tienen guarda en `app.js:666, 697, 722, 877` (leídas).
2. **Todo producto de `web/data/` lleva `procedencia` con las 8 claves** (`capa_evidencia, escala_original, fecha_dato, fuente, generado, incertidumbre, metodo, url`) — salida del mismo instrumento, 9 archivos; y `procedencia()` valida la capa con `assert` (`comun.py:290`).
3. **EPSG:4326 y dentro de la región en los 46 GeoJSON** — `crs.py`: `crs=None`, todos `lon ⊂ [−73,70, −70,90]`, `lat ⊂ [−39,65, −37,35]` (los cuatro `False` son −39,650 exacto contra −39,65 por redondeo).
4. **GORE sin anidamiento MAXIMA-en-MEDIA** — «MAXIMA con punto representativo dentro de un MEDIA: 0», control artificial `(1, 1)`.
5. **JRC recortado al bbox entero** — ráster `lon [−73,700, −70,900]`, 336×276 px; el agua termina en −71,654 por el modelo, no por el recorte.
6. **El arreglo del script 10 está** — `10:187-195` se cae con instrucción y no reescribe el índice.
7. **07 y 12 fusionan sus índices; 18 escribe un archivo por lámina** — `07:390` (`fusionado`), `12:392-404` (`previos[r["url"]] = r`), `18:436,550` (`SALIDA / f"{cfg['id']}.geojson"`).
8. **La lámina de la DGA no está publicada** — `origen_lamina`: `angol-peligro-inundacion-2013 98 · curarrehue-catripulli-inundacion-2025 39 · angol-prc-ar2a-lamina1 26`.
9. **Los 20 planos dicen `Anteproyecto` y la ficha lo pone en el encabezado** — `estado_tramite: {'Anteproyecto': 20}`; medida M2: `['EL PLANO DE TU COMUNA', 'ANTEPROYECTO', …]`.
10. **Área MINVU → veredicto ALTO y «cae dentro de»** — control de M1: `Temuco ANEGAMIENTO | cae dentro de: True | nivel: alto`; y el fenómeno no fluvial se rotula aparte (`app.js:689-692`).
11. **Punto sin dato → aviso fuerte en pantalla** — M3: `.aviso-fuerte: 1` (lo que falla es sólo el texto compartido, 202).
12. **Consulta nueva limpia la anterior** — marcador (1466-1471), `#respuesta` (613), `#detalle-ficha` (971), `renderFuera` (1272-1294) y `estado.ultimo = null`; fetch de sugerencias abortable (1158-1159); 0 errores JS en toda la corrida del arnés.
13. **El service worker borra las cachés de versiones anteriores** — `sw.js:63-66`.
14. **Ninguna ruta, puerto ni nombre de máquina en el código** — patrón 8, grep con salida vacía salvo `DPI`.
15. **`scripts/ORDEN.md` nombra los 20 scripts y cada uno declara `Salida:`** — `test_scripts.py:30-64` (leído) y grep `^Salida:` = 1 en 20/20.
16. **La e2e mide la fuga de planos con planos realmente cargados** — `auditoria_e2e.py:310-334` (`if con == 0: falla`).
17. **`textoSolicitud` y `textoComuna` se generan desde el mismo `le_falta` que la pantalla** — `app.js:463-466, 525, 542-546` y `19:182-191`; lo que está mal es el contenido de `le_falta` (204), no la relación pantalla/texto.
