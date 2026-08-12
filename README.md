# riesgomapas — ¿se inunda donde vivo?

Visor abierto de exposición a inundaciones. **Prototipo: Región de La Araucanía.**

Chile no tiene un mapa nacional de inundaciones. El Visor Chile Preparado cubre
volcanes, tsunami e incendios, pero no inundación — y no por descuido: no existe
la capa que mostraría. Lo que hay está repartido en PDFs de planes reguladores,
informes de la DOH y estudios comunales, casi siempre como imagen sin coordenadas.

Este proyecto reúne lo que sí es consultable, lo etiqueta por calidad de
evidencia, y construye lo que falta.

> ⚠️ **Esto no es información oficial del Estado.** Es un proyecto abierto y
> personal. No reemplaza al Plan Regulador de tu comuna ni a las instrucciones de
> SENAPRED durante una emergencia.

📄 [Inventario de fuentes](docs/INVENTARIO_FUENTES.md) · [Propuesta y arquitectura](docs/PROPUESTA.md) · [Cómo continuar](docs/PROXIMA_SESION.md)

---

## La idea en una frase

En vez de una capa binaria "estás dentro / estás fuera", el visor responde con
**todas las fuentes disponibles, cada una etiquetada por tipo de evidencia**, y
declara su error. Nunca las fusiona en un número único.

| Capa | Qué es | Estado |
|---|---|---|
| **A · Normativo** | Área de riesgo del Plan Regulador. Tiene efecto legal. | ✅ 63 polígonos de inundación, 12 comunas |
| **B · Observado** | Huella real de inundación por satélite, con fecha. | ✅ 5.776 ha, 3 órbitas, ago-2026 |
| **C · Modelado** | Qué dice un modelo que podría pasar, y cada cuánto. | ✅ 6 escenarios globales (JRC) + amenaza regional a 35 m |
| **D · Operacional** | Puntos críticos municipales, nivel de río, pronóstico. | ✅ 440 puntos fluviales, 4 temporadas |

## Qué funciona hoy

- **Áreas de riesgo del Plan Regulador en vectorial**: 212 polígonos de la región,
  **63 por amenaza hídrica**, con el texto legal de usos prohibidos y enlace a la
  ordenanza. Es la única capa con efecto jurídico, y resultó estar publicada como
  servicio ArcGIS abierto — no encerrada en PDFs, como suponíamos.
- **1.374 puntos críticos** de La Araucanía descargados de SENAPRED, de los
  cuales **440 son de inundación fluvial** —desborde de cauce y activación de
  quebradas— y **211 de ésos son crónicos** (aparecen en 3 o más temporadas del
  Programa Invierno: no son eventos aislados). El resto se conserva etiquetado
  pero no cuenta como inundación; ver «Qué cuenta como inundación» más abajo.
- **6 capas de amenaza modelada** del JRC recortadas a la región.
- **Índice de 5.991 documentos** de Evaluación Ambiental Estratégica de todo Chile
  (411 de La Araucanía, 25 comunas), con escáner que abre los PDF y localiza las
  páginas que contienen cartografía de inundación.
- **Barrido de los 32 sitios municipales**: los 32 dominios descubiertos solos y
  97 documentos cosechados por la API de medios de WordPress, incluidos estudios
  de riesgo de Purén (2025), Angol, Curarrehue y Lautaro que no están en el
  registro EAE.
- **Catálogo público navegable** (`documentos.html`): **354 documentos y 224
  láminas en 25 comunas**, con **enlace directo a la página del PDF donde está el
  mapa** (`....pdf#page=13`), no al documento de 300 páginas.
  **20 de las 32 comunas** tienen al menos una lámina localizada; los vacíos
  están documentados uno a uno en el inventario de fuentes.
- **24 planos de plan regulador georreferenciados automáticamente** (20 se
  publican; 4 resultaron ser copias exactas del mismo plano) desde su
  grilla UTM impresa, visibles como capa en el visor. Al activarla se dibujan los
  **recuadros** de las hojas disponibles; la imagen se carga sólo al acercarse
  (zoom ≥ 11) o al tocar un recuadro, con un tope de 6 simultáneas. El fondo de
  papel se publica casi transparente para que no tape el mapa base.
- **Campamentos en área de riesgo**: 15 campamentos con **537 hogares** dentro de
  área de riesgo por inundación (Temuco 460, Toltén 40, Collipulli 37). Responde
  la pregunta que sigue a «¿hay riesgo acá?»: cuánta gente vive ahí.
- **Buscador con sugerencias**: las comunas salen de datos ya cargados, así que
  aparecen al instante y **funcionan sin señal**; las direcciones llegan después.
- **Frontend estático** que responde por dirección, por ubicación GPS o tocando
  el mapa, con ficha compartible por WhatsApp y funcionamiento **sin señal**.
- **Georreferenciador** de láminas de PDF con RMSE leave-one-out y clasificación
  de aptitud de uso, verificado con transformaciones conocidas.

## Qué cuenta como inundación acá

El alcance es la **inundación fluvial**: agua que se sale de un cauce —río,
estero, quebrada, canal— y ocupa terreno que normalmente está seco.

**No** es alcance el **anegamiento urbano por drenaje insuficiente**: un colector
que colapsa, un paso bajo nivel que se llena. Suena parecido y es otro fenómeno,
con otra física, otra mitigación y otro servicio responsable — la Dirección de
Obras Hidráulicas y sus Planes Maestros de Aguas Lluvias.

La distinción no es de vocabulario: **mezclarlos diluye la evidencia**, y se puede
medir. Contrastando los puntos críticos de SENAPRED contra la huella satelital,
con el mismo método para los dos grupos:

| Grupo de puntos | Enriquecimiento sobre el azar |
|---|---:|
| Desborde de cauce y quebradas | **×2,1** |
| Colectores y anegamiento de caminos | **×1,0** — azar puro |

Los puntos de drenaje **no muestran ninguna señal**, y es lo que predice la
física: el radar ve una lámina de agua libre sobre terreno abierto y no ve un
colector colapsado bajo una calle. Contarlos juntos sólo agregaba ruido.

De los 1.374 puntos de SENAPRED en la región, **440 son fluviales**: 434 por
desborde de cauce y 6 por activación de quebradas. Los otros 934 se conservan en
`data/processed/` con su etiqueta —quien quiera estudiarlos puede— pero no cuentan
como inundación. La lista de causas dentro y fuera de alcance vive en
`config/araucania.yaml`, y **el pipeline se cae si la fuente trae una causa que
nadie clasificó**: al aplicar esta regla aparecieron cinco causas que se estaban
yendo en silencio al grupo equivocado.

Vale la pena notar que la fuente que usamos para la amenaza modelada regional —el
estudio del Gobierno Regional de 2016— **ya hacía esta distinción**: publica
«Amenaza de inundación» separada de «Riesgo de anegamiento». Los que las
mezclábamos éramos nosotros.

## Hasta dónde llegó el agua, de verdad

Las otras tres capas responden preguntas distintas de la que la gente hace. La A
dice qué declaró el plan regulador; la C, qué modeló alguien en 2016 a un
kilómetro de resolución; la D, dónde reportó problemas el municipio. Ninguna dice
**hasta dónde llegó el agua**. Esta sí, con fecha de pasada satelital verificable.

Un radar mide cuánta energía le devuelve el terreno. Una superficie rugosa a la
escala de 5,6 cm dispersa en todas direcciones y algo vuelve: el suelo vegetado
de la Araucanía marca −9 dB. Una lámina de agua quieta es un espejo a esa escala:
refleja casi todo hacia adelante y vuelve muy poco. Medido sobre el lago
Villarrica: **−24,7 dB**. Quince decibeles de diferencia, y ahí está la huella.

Pero «oscuro» no basta: también son oscuros el asfalto liso, la sombra detrás de
un cerro y el propio río. Por eso el criterio no es oscuridad sino **cambio
respecto de cómo se veía ese mismo píxel antes**, comparando sólo pasadas de la
**misma órbita relativa**. Esa elección hace la mitad del trabajo sola: la sombra
de radar y el relieve son estáticos y se cancelan, y el agua permanente es oscura
en las dos fechas, así que el río no se marca como inundación.

**Resultado sobre el sistema frontal del 30-jul al 4-ago-2026: 5.776 ha** de agua
observada, sobre 17.382 km² efectivamente mirados.

| Órbita | Plataforma | Pasada | Referencia | Huella |
|---|---|---|---|---:|
| 83 desc. | Sentinel-1D | 4-ago | 4 pasadas, 11-jul a 29-jul | 16,2 km² |
| 156 desc. | Sentinel-1C | 3-ago | 4 pasadas, 10-jul a 28-jul | 15,4 km² |
| 164 asc. | Sentinel-1C | 3-ago | 4 pasadas, 10-jul a 28-jul | 26,2 km² |

Que tres órbitas con geometría, hora y plataforma distintas converjan en el mismo
orden de magnitud es la señal de que se está midiendo algo real.

**Y se obtiene sin ninguna cuenta.** Estaba anotado como bloqueado por
credenciales de Copernicus Data Space, y era cierto de ese proveedor y falso del
dato: el catálogo STAC de Microsoft Planetary Computer y su firma SAS son
anónimos, los assets son COG —un `Range: bytes=…` trae una ventana en vez de la
escena de 1 GB— y en el mismo contenedor está la anotación SAFE completa, con la
tabla de calibración que permite llegar a σ⁰ físico. Ver §5b del inventario.

### Los dos falsos positivos que casi se publican

Ninguno de los dos se detecta mirando el número: los dos se detectaron mirando
**dónde** estaban las detecciones.

**Nieve húmeda.** La primera corrida declaró 1.252 km². El 74,7 % de las
detecciones caía en la franja cordillerana, con una tasa de 8,9 % contra 0,1–1 %
en el resto. No era agua: el frente cálido derritió la nieve andina, y en banda C
la nieve mojada absorbe casi toda la señal y se ve **exactamente igual de oscura
que una lámina de agua**. Ningún umbral radiométrico las separa. Lo que las
separa es la geomorfología: el agua se embalsa en terreno plano, la nieve se
acumula en altura y en pendiente.

**El mar.** Después de filtrar la nieve, una órbita seguía declarando 903 km². Sus
detecciones tenían altitud mediana **0 m** y el 98 % estaba a menos de 1 km de
agua permanente. Era el océano: liso en la pasada vespertina, picado por viento en
las referencias matinales. Radiométricamente «apareció agua», y es verdad que
apareció agua lisa — sólo que ahí el agua siempre estuvo. El mar aportaba **871
de esos 903 km²**.

Los dos se descartan con el DEM **Copernicus GLO-30**, que resultó ser accesible
igual que Sentinel-1: COG público, sin credenciales, leído por `Range`.

### Verificación independiente

Contra los puntos críticos de origen hídrico de SENAPRED, que no participaron en
ningún paso de la derivación, y contra puntos al azar sobre el mismo territorio
observado —porque una huella grande acierta por tamaño—:

| | dentro de 300 m de la huella |
|---|---:|
| Puntos fluviales de SENAPRED | 55 de 371 (14,8 %) |
| Puntos al azar, misma cobertura | 390 de 7.420 (5,3 %) |

**Enriquecimiento ×2,8**, con un exceso de ~8 σ. Sube a **×3,0** exigiendo
coincidencia exacta y baja a ×2,0 al ampliar el radio a 1 km, que es el
comportamiento esperable de una señal real.

Esta cifra era **×1,7** hasta que se depuró el alcance: los puntos de drenaje
urbano, que el radar no puede ver, estaban diluyendo la verificación de la propia
capa. El límite que queda en pie es otro: el radar **no ve agua bajo dosel cerrado
ni en zona urbana densa**.

### Lo que esta capa no puede decir

- Es una **foto del instante de la pasada**, no el máximo del evento. El agua que
  subió y bajó entre pasadas no existe para este método.
- **No ve agua bajo dosel cerrado** ni **en zona urbana densa** (el doble rebote
  pared-suelo mantiene alta la señal): subestima justo donde vive más gente.
- **No ve agua con viento**, que rugosiza la lámina.
- **No afirma nada en cordillera ni en ladera**: ahí la máscara de terreno la
  apaga, porque no puede distinguir agua de nieve.

## Los planos sepultados, georreferenciados solos

El plano de zonificación de un plan regulador —el que dibuja el área de riesgo por
inundación con efecto legal— vive como PDF dentro de un expediente ambiental que
nadie abre. Pero esos planos se dibujan en formato de plóter **con la retícula de
coordenadas UTM rotulada en los márgenes**, y esos rótulos no son una imagen: son
texto vectorial con posición exacta dentro del PDF.

Eso permite georreferenciarlos **sin intervención humana**: el producto cartesiano
de las líneas de la grilla da decenas de puntos de control de coordenada exacta.

**Resultado sobre La Araucanía: 24 planos georreferenciados automáticamente**,
todos con error de ubicación por debajo de 2 metros y la mayoría bajo 20 cm.

| Comuna | Planos | Error típico |
|---|---:|---|
| Vilcún | 5 | 0,02 – 0,09 m |
| Teodoro Schmidt | 6 | 0,15 – 0,20 m |
| Pitrufquén | 4 | 0,03 – 0,04 m |
| Pucón | 4 | 1,3 – 1,8 m |
| Galvarino | 3 | 0,11 m |
| Traiguén | 1 | 0,19 m |

De 49 láminas candidatas de tipo plano, 25 se rechazaron. **Ese rechazo es el comportamiento
correcto**: sin grilla legible no hay forma honesta de ubicar un plano, y
publicarlo mal ubicado sería peor que no publicarlo.

La causa está verificada: en el PRC de Purén los rótulos de la grilla **están
vectorizados**, no son texto. El plano los muestra al renderizarlo, pero la capa
de texto del PDF sólo contiene `1976`, `1992` y `2026`. Recuperar esos casos
requiere OCR sobre los márgenes renderizados — está pendiente.

Verificación independiente sobre Vilcún: el plano aterriza en −38,667 / −72,216
(la localidad), con huella de 4,00 × 1,50 km, y los puntos críticos que SENAPRED
registra ahí —un dataset que no participó en la georreferenciación— caen sobre las
calles y sobre el cauce dibujados en el plano.

## El hallazgo que reorientó el proyecto

La hipótesis de partida era que los mapas de inundación sólo existían como
imágenes dentro de informes. Es cierto para los **estudios** que fundamentan el
riesgo, pero no para el **polígono normativo**: MINVU publica las áreas de riesgo
de los planes reguladores de todo Chile en vectorial y abierto.

No se encontraba porque el catálogo oficial de datos.gob.cl apunta a un servidor
**caído desde hace tiempo** (`geoportal.cl/ArcGIS/...` responde 404). El servicio
vivo está en otra organización ArcGIS, sin que nadie actualizara el registro.

Y para lo que sí está sepultado en informes, la palanca es que **todo plan
regulador de Chile debe pasar por Evaluación Ambiental Estratégica**: un solo
portal público, sin autenticación, con los expedientes completos del país.

### Comunas con más puntos críticos de inundación de riesgo Alto/Muy Alto

| Comuna | Alto/Muy Alto | Inundación | Crónicos |
|---|---:|---:|---:|
| Purén | 39 | 64 | 17 |
| Pucón | 39 | 46 | 13 |
| Temuco | 37 | 72 | 2 |
| Saavedra | 34 | 48 | 22 |
| Teodoro Schmidt | 32 | 54 | 32 |
| Nueva Imperial | 32 | 45 | 16 |
| Renaico | 30 | 41 | 5 |
| Padre Las Casas | 29 | 54 | 38 |
| Curarrehue | 29 | 29 | 25 |

## Instalación y uso

```bash
pip install -r requirements.txt
```

```bash
python scripts/01_senapred_puntos_criticos.py
```

```bash
python scripts/02_jrc_amenaza_modelada.py
```

```bash
python scripts/06_areas_riesgo_prc.py
```

### Cosechar los sitios municipales

```bash
python scripts/12_cosechar_municipios.py
```

Descubre solo el dominio de cada municipalidad, consulta su biblioteca de medios
de WordPress y descarga los documentos de planificación. `--comuna ANGOL` acota a
una, `--solo-listar` muestra qué bajaría, `--max-mb` limita el tamaño.

### Encontrar los mapas sepultados en informes

Primero se construye el índice del registro de Evaluación Ambiental Estratégica
(rastrea 536 fichas, ~7 min; queda en caché):

```bash
python scripts/05_eae_documentos.py
```

Después se abren los PDF y se localizan las páginas con cartografía de inundación:

```bash
python scripts/07_buscar_laminas_riesgo.py --prioridad planos --max-mb 90
```

`--prioridad planos` va a las láminas del anteproyecto, que es cartografía pura.
`anteproyecto` e `ia` cubren memorias explicativas e informes ambientales, y
`municipales` los estudios de riesgo bajados directo de los sitios comunales por
el script 03. Con `--comuna Angol` se acota a una comuna, y `--solo-listar`
muestra qué se descargaría sin bajar nada.

Después, los planos que traen grilla UTM impresa se georreferencian solos:

```bash
python scripts/08_georreferenciar_grilla.py --todas
```

Y se publican como capa del visor y como catálogo navegable:

```bash
python scripts/10_exportar_superposiciones.py
```

```bash
python scripts/09_exportar_catalogo.py
```

La capa B se deriva aparte, porque es la única que baja píxeles de satélite:

```bash
python scripts/14_sar_huella_observada.py --verificar
```

`--bbox O S E N` acota el área para probar rápido, `--verificar` contrasta el
resultado contra los puntos críticos de SENAPRED y `--forzar` ignora la caché de
rásteres. La corrida completa tarda ~30 min y deja ~800 MB en `data/processed/`,
que es caché regenerable.

```bash
python -m http.server 8788 --directory web
```

Los scripts se corren en orden; cada uno es independiente y se puede repetir.
`data/raw/` pesa ~1,8 GB después de correr todo (son los PDF de los expedientes)
y está fuera de control de versiones: se regenera con los scripts.

### Georreferenciar una lámina

```bash
python scripts/03_descargar_documentos.py
```

Eso baja los PDFs y renderiza las láminas candidatas a 400 dpi en
`data/raw/laminas/`. Después hay que poner los puntos de control a mano — no hay
forma seria de automatizarlo:

```bash
python scripts/04_georreferenciar.py --plantilla mis_puntos.json
```

Se pueden llenar en el JSON o, mejor, picarlos en el Georreferenciador de QGIS y
exportar el `.points`, que el script lee directamente.

```bash
python scripts/04_georreferenciar.py data/raw/laminas/temuco/estudio_aguas_lluvias_p013.png mis_puntos.points --crs EPSG:32718
```

El script reporta el **RMSE leave-one-out** y clasifica el resultado:

| RMSE LOO | Aptitud | Uso |
|---|---|---|
| < 10 m | `predial` | consulta sobre una propiedad concreta |
| 10–25 m | `manzana` | referencial a nivel de manzana |
| > 25 m | `contexto` | sólo contexto; el frontend debe difuminarlo |

Se usa el leave-one-out y no el RMSE del ajuste porque el segundo reparte el
error entre todos los puntos y disimula un GCP mal picado. Hay un test que
comprueba exactamente eso.

### Tests

```bash
python -m pytest tests/ -q --ignore=tests/auditoria_e2e.py
```

### Auditoría funcional en navegador real

Los tests unitarios no ven la clase de bug que más daño hace en un visor:
controles tapados por otro elemento, capas que no se dibujan, texto roto por
datos ausentes, contraste ilegible, desbordes en celular. Para eso hay un arnés
que levanta Chromium, ejerce cada funcionalidad y deja capturas:

```bash
python tests/auditoria_e2e.py
```

Audita tres perfiles —escritorio claro, escritorio oscuro y celular— y comprueba,
entre otras cosas: que MapLibre cargue y **dibuje** (midiendo colores sobre una
captura del elemento, no con `readPixels`, que devuelve un lienzo vacío y da un
falso negativo); que cada control de capa acepte el clic (Playwright falla si el
elemento está tapado); que la ficha declare fuente y año de cada capa; que el
plano se agregue al mapa; que el contraste cumpla WCAG AA; y que no se muestren
`undefined` ni frases cortadas por un dato ausente.

Deja las capturas en `data/processed/auditoria/`.

```bash
python tests/auditoria_e2e.py --ver
```

muestra la ventana del navegador mientras corre.

## Estructura

```
riesgomapas/
├── config/araucania.yaml      # comunas, husos UTM, causas de inundación, eventos
├── scripts/
│   ├── comun.py               # descarga, paginación ArcGIS, procedencia
│   ├── 01_senapred_...py      # capa D — puntos críticos
│   ├── 02_jrc_...py           # capa C — amenaza modelada
│   ├── 03_descargar_docs.py   # capa A — PDFs municipales y láminas
│   ├── 04_georreferenciar.py  # capa A — GCP, RMSE, GeoTIFF
│   ├── georref.py             # núcleo: ajuste, RMSE leave-one-out, remuestreo
│   ├── 05_eae_documentos.py   # capa A — índice del registro EAE nacional
│   ├── 06_areas_riesgo_prc.py # capa A — polígonos normativos MINVU
│   ├── 07_buscar_laminas...py # capa A — dónde está el mapa dentro del informe
│   ├── 08_georreferenciar_grilla.py  # capa A — georref. auto por grilla UTM
│   ├── 09_exportar_catalogo.py       # catálogo público por comuna
│   ├── 10_exportar_superposiciones.py # planos como capa del visor
│   ├── sar.py                 # núcleo capa B: calibración, criterio, vectorizado
│   └── 14_sar_huella_...py    # capa B — huella observada Sentinel-1
├── web/                       # sitio estático + PWA offline
│   ├── index.html             # visor: respuesta por dirección o ubicación
│   └── documentos.html        # catálogo: dónde está el mapa de cada comuna
├── data/raw/                  # descargas crudas, nunca se editan
├── data/processed/            # derivados
└── docs/                      # inventario de fuentes y propuesta
```

## Reglas del proyecto

1. **Todo mapa que se muestra dice su fuente y su año.** No en la letra chica: en
   el mismo bloque que el dato, con el mismo peso visual. Un área de riesgo de un
   plan regulador de 1978 no significa lo mismo que una de 2022, y un modelo de
   2016 no conoce las obras fluviales posteriores.
   - El sello (`comun.sello()`) va **pegado a cada geometría**, no sólo a la
     cabecera del archivo: los features se filtran, se shardean y se mezclan en el
     mapa, y la atribución tiene que sobrevivir a eso.
   - **El año nunca se inventa.** Si la fuente no lo declara, se escribe
     literalmente «no declarado por la fuente», que es información, no un hueco.
     Es el caso de las áreas de riesgo de MINVU: la capa no trae campo de fecha y
     su enlace a la ordenanza responde 410.
2. **Todo producto declara su procedencia.** Fuente, método, capa de evidencia e
   incertidumbre. `comun.procedencia()` lo exige con un assert: si un producto no
   puede declarar a qué capa pertenece, no se publica.
3. **No fusionar capas en un índice único.** Mezclar evidencia legal con un
   modelo global de 1 km produce un número que parece preciso y no lo es.
4. **`data/raw/` no se modifica nunca.** Sólo derivados.
5. **Ausencia de dato ≠ ausencia de riesgo.** El frontend lo dice explícitamente.
6. **Tiene que funcionar sin señal.** Es el requisito de diseño principal: en una
   inundación se corta la luz y con ella la conexión.
7. **Ningún control puede quedarse mudo.** Si una capa no se puede mostrar —zoom
   insuficiente, nada en la vista, mapa todavía cargando— el visor lo dice y
   explica qué hacer. Un control que parece no funcionar mientras descarga 19 MB
   en silencio es el peor de los dos mundos, y fue un bug real de este proyecto.
8. **Los controles no van flotando sobre el mapa.** MapLibre pone los suyos
   (escala abajo a la izquierda, zoom arriba a la derecha) con `z-index: 2`, y
   una leyenda flotante termina tapada por ellos: las casillas de abajo quedaban
   invisibles y no aceptaban el clic. Van en un panel propio encima del mapa.
9. **Subir `VERSION` en `sw.js` en cada publicación.** El service worker tiene
   estrategia "red primero", pero sin `cache: 'no-cache'` el navegador le
   devolvía su propia copia vieja: después de corregir una hoja de estilos, el
   usuario seguía viendo la versión anterior y los controles parecían rotos.
10. **Antes de declarar algo arreglado, correr `tests/auditoria_e2e.py`.** Tres
    de los cuatro "bugs" del primer informe de auditoría eran bugs de la propia
    prueba. Una auditoría en la que no se confía es peor que no tenerla.
    Y **si la auditoría no mira la capa nueva, su 100 % no dice nada**: al
    integrar la capa B daba 108/108 sin comprobar ni una sola vez la capa recién
    construida.
11. **Antes de anotar una fuente como bloqueada por credenciales, recorrer los
    espejos y probar una lectura real de bytes.** La capa B estuvo dada por
    imposible por «requiere cuenta en Copernicus Data Space»: era una propiedad
    de un proveedor, no del dato. El mismo error, con otra forma, había hecho
    concluir que no existía capa nacional de áreas de riesgo.
12. **Un resultado inverosímil se investiga mirando DÓNDE está, no cuánto es.**
    Los dos falsos positivos grandes de la capa B —nieve húmeda y océano— eran
    invisibles en el total y evidentes en la distribución espacial.
13. **Una caché se valida, no se supone.** Con el disco lleno quedó un GeoTIFF
    truncado pero presente, y la corrida siguiente lo dio por bueno y reventó
    mucho después con un error que no se parecía en nada a su causa.

## Sistema visual

Anclado en el tema, no en una plantilla:

- **Color**: papel frío con sesgo azul-verde (`#e9eef0` claro / `#0e171b` oscuro)
  — un gris neutro puro se lee como no elegido. Acento *río* petróleo
  (`#0b6478` / `#4fc3dc`). La escala de amenaza es una **leyenda cartográfica**
  (granate, ámbar quemado, ocre, musgo) y se mantiene **separada del acento**,
  para que «esto es grave» nunca dependa del mismo tono que «esto es un enlace».
- **Tipografía**: pila del sistema, a propósito. Una fuente web rompería el
  funcionamiento sin señal y agrega descarga en una conexión mala, que es la
  condición del público objetivo. El carácter lo dan la escala, los pesos y los
  numerales tabulares.
- **Motivo propio**: el achurado diagonal con que los planes reguladores marcan
  las áreas de riesgo, usado sólo en el veredicto grave para que signifique algo.
- **Información antes que decoración**: la portada abre con las cifras del acervo
  —calculadas de los datos, nunca escritas a mano— y las comunas llevan barra de
  magnitud además del número, porque un panel se opera de un vistazo.
- Ambos temas se diseñan y **ambos se auditan**: el contraste se comprueba en
  claro y en oscuro, y en oscuro el mapa base se atenúa por capa
  (`raster-brightness-max`), no con un filtro CSS sobre el lienzo, que apagaría
  también los colores de amenaza.

## Pendientes

- **OCR de márgenes** para recuperar los planos cuya grilla está vectorizada
  (Purén, Collipulli, PRI Villarrica–Pucón). Son 8 láminas de 4 comunas.
- **Georreferenciar las figuras rasterizadas** de las memorias explicativas: 95 de
  las 144 láminas detectadas son figuras dentro de informes, sin grilla. Requieren
  puntos de control a mano (`scripts/04_georreferenciar.py`). La más valiosa es el
  Catastro de Anegamientos Estacionales de Temuco, por población afectada.
- **Servir los GeoJSON comprimidos**: la carga inicial son 1,9 MB en crudo pero
  397 KB con gzip. Hay que asegurarse de que el hosting lo aplique.

- **Capa B — más eventos.** El pipeline está hecho y es reutilizable: basta
  agregar el evento a `config/araucania.yaml`. Los candidatos naturales son jun-2023
  y jul-2006, que darían huellas comparables y permitirían ver qué sectores se
  repiten.
- **Corrección radiométrica por terreno de la capa B.** Hoy la ladera se descarta
  entera con la máscara de pendiente. Con un DEM ya descargado, aplicar corrección
  por ángulo local de incidencia recuperaría parte de ese territorio.
- **JRC v2.1 a 90 m** en vez de la versión global de 1 km. Sólo se distribuye por
  Google Earth Engine, que requiere cuenta.
- **Geocodificador propio**: hoy usa Nominatim, cuya política de uso no permite
  tráfico alto. Para producción hace falta uno propio o el de IDE Chile.
- **Tiles propios**: hoy usa el servidor de tiles de OSM, que tampoco está pensado
  para tráfico de producción. Migrar a PMTiles autoalojado.
- **Puntos de encuentro y vías de evacuación** de SENAPRED: ya están en el mismo
  org de ArcGIS y el proyecto `Valles/` tiene los scripts para bajarlos.
- **Contactar a Kimün-Ko (UFRO)** antes de escalar: trabajan en alertas
  hidrometeorológicas para la misma región.

## Fuentes y licencias

- SENAPRED — Puntos Críticos Programa Invierno (ArcGIS Online público).
- JRC / Comisión Europea — Global River Flood Hazard Maps, **CC BY 4.0**.
- Municipalidad de Temuco — Estudio Fundado de Riesgos y Estudio de Aguas Lluvias
  del PRC (2022).
- Copernicus / ESA — **Sentinel-1 GRD**, distribuido por Microsoft Planetary
  Computer. Datos Copernicus, uso libre con atribución.
- Copernicus / ESA — **DEM GLO-30**, vía AWS Open Data.
- OpenStreetMap — mapa base y geocodificación, **ODbL**.
