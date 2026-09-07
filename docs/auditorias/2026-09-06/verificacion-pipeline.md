# Verificación con contexto limpio — pipeline, datos y documentación

**Fecha**: 2026-09-06 · **Rama**: `visor-simple-y-laminas-vectorizadas` · **Verificador**: sesión
independiente, sin lectura de los informes de los auditores.

Se recibieron 46 hallazgos provisionales como *ID + título + archivo:línea*. Cada veredicto de
abajo se apoya en una lectura o en un comando corrido **en esta sesión**, con la salida cruda
pegada. Lo que no se pudo medir dice SIN DATO, no FALLA.

Instrumentos nuevos escritos para verificar (todos en `tools/auditoria/`, ninguno toca `scripts/`,
`web/`, `config/`, `data/` ni `tests/`):
`verif_capaA.py`, `verif_capaB.py`, `verif_capaB2.py`, `verif_702_apertura.py`,
`verif_703_color_rio.py`.

Línea base: `python -m pytest tests -q` → `63 passed in 0.94s`.
`python tests/auditoria_datos.py` → `151 comprobaciones OK · 1 hallazgos (0 de gravedad alta)`.

---

## Tabla resumen

| ID | Familia | Gravedad | IDs absorbidos | Veredicto |
|---|---|---|---|---|
| **P-01** | La capa A-derivada se dibuja pero **no se consulta**: Angol y Curarrehue responden «sin registros» sobre su propio polígono | 5 | P-N01 (nuevo), 221 (parte) | CONFIRMADO |
| **P-02** | El guardián de alcance regional deja pasar corrimientos de hasta 20 km | 5 | 301, 315 | CONFIRMADO |
| **P-03** | Producto derivado publicado como `A_normativo`; el docstring nombra una etiqueta que el validador rechaza | 4 | 208, 310, 400 | CONFIRMADO |
| **P-04** | La incertidumbre que llega al visor no lleva **ningún** número de georreferenciación | 4 | 307, 308 | CONFIRMADO |
| **P-05** | Los cuadros de la leyenda se publican como área de riesgo | 4 | 701 | CONFIRMADO |
| **P-06** | Una entrada ausente produce un inventario falso, sin error ni aviso | 4 | 203, 219 | CONFIRMADO |
| **P-07** | Apertura con núcleo par: corre la mancha +1 px E y +1 px S y **agrega** píxeles que nunca fueron de la clase | 3 | 702, 320, P-N03 | CONFIRMADO |
| **P-08** | El grosor mínimo no es criterio físico y se come área legítima; la premisa del río es falsa | 3 | 302, 703 | CONFIRMADO |
| **P-09** | La capa B publica 5.776 ha sumando órbitas: 702 ha se cuentan dos o tres veces | 3 | 505 | CONFIRMADO |
| **P-10** | 585 de 1.075 polígonos de la huella y 59 de 115 de la cobertura son inválidos | 3 | 506, 512 | CONFIRMADO |
| **P-11** | Duplicado geométrico en Collipulli que la clave de deduplicación no ve | 3 | 502 | CONFIRMADO (reformulado) |
| **P-12** | La verificación contra SENAPRED no se mide sobre la capa publicada | 3 | 503 | PARCIAL (número refutado) |
| **P-13** | «Puerto Saavedra» pierde su año por el orden renombrar→buscar; la guía lo cuenta mal | 3 | 504, 404 | CONFIRMADO |
| **P-14** | Huella a nivel del mar en el estuario y a 1.000–1.200 m; la incertidumbre no nombra marea | 3 | 507, 508 | PARCIAL |
| **P-15** | Tres «ZR-3 Área en torno a Canales» fuera del filtro hídrico | 2 | 510 | CONFIRMADO |
| **P-16** | Toltén: AR-1 y AR-2 100 % contenidos en AR-3 | 2 | 509 | CONFIRMADO |
| **P-17** | Orientación de anillos al revés de RFC 7946 en los 63 publicados | 2 | 511 | CONFIRMADO |
| **P-18** | Cinco GeoJSON del JRC publicados sin lector, y la auditoría de datos exenta de mirarlos | 2 | 220 | CONFIRMADO |
| **P-19** | `--bbox` del script 14 sobrescribe la capa B publicada | 2 | 207 | CONFIRMADO |
| **P-20** | Dos definiciones de «inundación» entre capas | 2 | 312 | CONFIRMADO |
| **P-21** | `tolerancia_color` de Catripulli a 25–30 unidades de un acantilado ×4,4 | 2 | 303 | PARCIAL |
| **P-22** | `area_minima_m2 = 2000` con 17 de 98 polígonos de Angol a un paso de desaparecer | 2 | 311 | CONFIRMADO |
| **P-23** | La lámina 09201-2 existe y nadie la declara | 2 | 704 | CONFIRMADO (cobertura) / SIN DATO (contenido) |
| **P-24** | Documentación: `docs/REGLAS.md` fantasma, `Requiere:` que nadie declara, «23 planos» que son 20, `estado_tramite` que no está | 2 | 215, 216, 401, 403, P-N05 | CONFIRMADO |
| **P-25** | `laminas.yaml`: comentario huérfano que resucita la lámina rechazada | 2 | 321, 402 | CONFIRMADO |
| **P-26** | Los propios instrumentos de auditoría se caen en Windows por cp1252 | 2 | P-N02 (nuevo) | CONFIRMADO |
| **P-27** | Campos escritos que nadie lee | 1 | 221 (resto) | CONFIRMADO |
| **P-28** | Docstrings que mienten sobre su omisión (`percentil 90` vs 50) | 1 | 319 | CONFIRMADO |
| **P-29** | `area_pixel_m2` con la latitud media de la región: ±1,6 % | 1 | 317 | CONFIRMADO |
| **P-30** | `TOL_PASO` se aplica al paso de los VALORES de los rótulos | 1 | 313 | CONFIRMADO (sin impacto medido) |
| **—** | Ocho polígonos de Collipulli «que MINVU clasifica como remoción en masa» | — | 501 | **REFUTADO** |
| **—** | `TOL_INLIER_M = 3 m` es menos de un punto tipográfico | — | 314 | **REFUTADO** |
| **—** | Georreferenciación de las láminas | — | 705 | VERIFICADO LIMPIO |
| **—** | Trama AR-2a, 76 % de recall | — | 706 | VERIFICADO con reserva |

**30 familias** · 24 confirmadas · 3 parciales · 2 refutadas · 2 limpias · 0 sin dato.

---

## ¿Reconocemos bien los polígonos? — respuesta directa

**El reconocimiento del dibujo es bueno; el aterrizaje es bueno pero no está protegido; y el
polígono que sí reconocemos no llega a la respuesta que la persona lee.** Con un control positivo
sintético —geometría y coordenadas fijadas de antemano, pasadas por el `procesar()` real— el
vectorizador recupera IoU **0,956** para «Alto» y **0,975** para «Medio», con desplazamiento del
centroide de 5,2 a 15,2 m y un anillo interior conservado; el control negativo da 0 polígonos y el
guardián se cae como debe. Sobre las láminas reales, la clasificación por color es fiel en
Catripulli (IoU publicado vs. clasificador k-means independiente **0,937**, y el centro k-means cae
a **1,9 unidades RGB** del color declarado en la leyenda), pero es floja en Angol: **0,647** para
«Alto» y **0,220** para «Medio», con el centro k-means de «Medio» a **54,1 unidades** del color
declarado, o sea *fuera* de la `tolerancia_color: 45` que el propio archivo declara. En el plano
AR-2a —el único con efecto legal— el ajuste por vértices reproduce **RMSE 4,94 m** (residuos 3,48 /
6,36 / 4,56 m) y la trama se detecta con densidad de **154,9 marcas/ha dentro** de lo publicado
contra **3,0 marcas/ha fuera**: un contraste de ×52, que es evidencia sólida de que el achurado se
identifica donde está. Contra eso hay tres defectos que corren el borde: la apertura con núcleo par
(4×4) desplaza toda la mancha **+1 píxel al este y +1 al sur** —medido: un cuadrado de 40×40 px
entra en filas 20..59 y sale en filas 21..60— y además **agrega 2.227 píxeles = 13,3 ha en Angol
que nunca tuvieron el color de la clase**; el grosor mínimo de 4 px se come el **25,3 % de «Alto» y
el 42,1 % de «Medio»** en Angol sin que lo comido tenga forma de río (la componente conexa más
grande de lo eliminado mide 356 px con elongación 1,5, y su RGB medio está a **11,9 unidades** del
de los píxeles que sobreviven: es el mismo azul, es borde, no cauce); y el único guardián que
protege un rótulo mal tecleado **acepta corrimientos de hasta 20 km** en las cuatro direcciones.
Eso importa porque **el 37,7 % de la población de Catripulli vive a menos de 10 m de un borde
derivado** y el 91 % a menos de 50 m. Y sobre todo: los 163 polígonos que producimos **no entran en
la consulta por punto**. Un predio dentro del AR-2a mayor del PRC de Angol (−72,6867, −37,78499)
da 0 en la capa A oficial, 0 en la huella SAR, 0 en el JRC, y **2 en las láminas vectorizadas** —
que el visor dibuja pero nunca consulta.

---

## P-01 — La capa A-derivada se dibuja pero no se consulta (GRAVEDAD 5, CONFIRMADO)

**Archivo:línea** — `web/app.js:106` (se carga), `web/app.js:1549-1564` (se dibuja),
`web/app.js:375-385` (la función que responde la consulta y **no** la nombra),
`scripts/19_estado_comunas.py:135-166` (la publica).

**Caminos** — el único consumidor es `web/app.js`. `estado.laminas` aparece exactamente en 4
líneas: 106/107 (carga), 1549-1550 (capa de mapa), 1705 (mensaje de caché). El bloque de retorno de
`consultar()` enumera `areas`, `sar`, `coberturaSar`, `planos`, `campamentos`, `enMancha` (JRC) y
`gore`. **`laminas` no está.** Se reproduce en las tres láminas publicadas (163 polígonos: 98 Angol
figura, 26 Angol AR-2a, 39 Catripulli).

```
$ grep -n "estado.laminas" web/app.js
106:    estado.laminas = await cargarJSON('data/laminas/vectorizadas.geojson');
107:  } catch { estado.laminas = null; }
1549:    if (estado.laminas) {
1705:    if (e.target.checked && !estado.laminas) {
```

```
comunas en capa A publicada: ['Carahue','Collipulli','Gorbea','Loncoche','Nueva Imperial',
 'Pitrufquén','Renaico','Saavedra','Temuco','Toltén','Traiguén','Villarrica']
ANGOL en capa A: 0
CURARREHUE en capa A: 0

punto de prueba dentro del AR-2a mayor: -72.6867 -37.78499
  ¿cae en capa A oficial (areas-riesgo)? 0
  ¿cae en alguna lámina vectorizada? 2
  ¿cae en huella SAR? 0
  ¿cae en GORE? 1
  ¿cae en JRC rp100? 0
  punto crítico SENAPRED más cercano: 499 m
```

Angol es exactamente la comuna que motivó el script 18 —cero polígonos en el vectorial del MINVU— y
su AR-2a es el único polígono del corpus con `efecto_legal` (artículo 2.1.17 de la OGUC, tope de
14 m de altura). Ese texto está en el dato publicado y **nunca se muestra**: el instrumento
`campos_visor_vs_datos.py` lo dice completo.

```
## laminas/vectorizadas.geojson  n=163
   claves que el archivo trae y el visor NO lee (11): ['clase','comuna','amenaza','fuente','anio',
   'metodo_original','escala_original','hectareas','origen_lamina','descripcion','efecto_legal']
```

Es decir: de las 11 propiedades de la capa derivada, el visor lee **cero**. Quien consulta su
dirección en Angol ve una mancha ocre punteada y recibe «Sin registros en las fuentes consultadas»,
o —peor— la ficha del modelo regional del GORE a 35 m mientras el instrumento legal de su propia
comuna, a 0,85 m/píxel, no aparece.

---

## P-02 — El guardián de alcance regional deja pasar 20 km (GRAVEDAD 5, CONFIRMADO)

**Archivo:línea** — `scripts/18_vectorizar_laminas.py:399-405` (`procesar`) y `:523-525`
(`procesar_plano`); `config/laminas.yaml:14-17, 52-56, 99-101` (los rótulos declarados a mano);
`config/araucania.yaml:9` (el bbox).

**Caminos** — es la ÚNICA comprobación que protege un rótulo UTM mal tecleado en las láminas de
figura (`procesar`): la verificación de escala cruzada X/Y sólo aplica cuando hay ≥2 anclas
verticales, y **ninguna de las dos láminas de figura las tiene** (Angol y Catripulli declaran una
sola línea de norte, `laminas.yaml:52-56` y `:99-101`). Para el plano AR-2a hay además el RMSE.

Re-corrido de `tools/auditoria/control_alcance_regional_laminas.py`:

```
bbox regional: [-73.7, -39.65, -70.9, -37.35]  (ancho 244 km x alto 256 km)

[angol-peligro-inundacion-2013] lon -72.740..-72.665 · lat -37.837..-37.779
    0.5 km: N=PASA  S=PASA  E=PASA  O=PASA
      1 km: N=PASA  S=PASA  E=PASA  O=PASA
      2 km: N=PASA  S=PASA  E=PASA  O=PASA
      5 km: N=PASA  S=PASA  E=PASA  O=PASA
     10 km: N=PASA  S=PASA  E=PASA  O=PASA
     20 km: N=PASA  S=PASA  E=PASA  O=PASA
     50 km: N=RECHAZA  S=PASA  E=PASA  O=PASA
    100 km: N=RECHAZA  S=PASA  E=PASA  O=RECHAZA
```

Un dígito equivocado en el norte de Angol (5.815.000 → 5.825.000) mueve la mancha 10 km y el
pipeline la publica sin decir nada. Absorbe **315**: la misma pregunta —«¿cae en la región?»— tiene
tres respuestas distintas en el repositorio: `scripts/08_georreferenciar_grilla.py:227` usa
`± 0.3` (~33 km), `scripts/18:400,524` no usa margen, y `tests/auditoria_datos.py:360` usa
`TOL = 0.01`.

---

## P-03 — Producto derivado publicado como `A_normativo` (GRAVEDAD 4, CONFIRMADO)

**Archivo:línea** — `scripts/18_vectorizar_laminas.py:44` (docstring: «la capa se etiqueta
`A_derivado`»), `:421` y `:538` (el código escribe `A_normativo`),
`scripts/19_estado_comunas.py:156` (lo repite al publicar), `scripts/comun.py:290-292` (el `assert`
no admite `A_derivado`).

```
$ grep -n "A_derivado\|A_normativo" scripts/18_vectorizar_laminas.py scripts/19_estado_comunas.py scripts/comun.py
scripts/18_vectorizar_laminas.py:44:   la capa se etiqueta `A_derivado` — nunca se mezcla con el vectorial del MINVU,
scripts/18_vectorizar_laminas.py:421:        capa_evidencia="A_normativo",
scripts/18_vectorizar_laminas.py:538:        capa_evidencia="A_normativo",
scripts/19_estado_comunas.py:156:                capa_evidencia="A_normativo",
scripts/comun.py:290:    assert capa_evidencia in ("A_normativo", "B_observado", "C_modelado",
```

```
$ python -c "...web/data/laminas/vectorizadas.geojson..."
features 163
procedencia.capa_evidencia A_normativo
```

Los tres archivos de `data/processed/laminas/` también salen `A_normativo`. La etiqueta que se
publica es la de **más peso legal** para un producto cuyo propio texto dice «NO tiene el efecto
legal del vectorial del MINVU». El docstring propone la etiqueta correcta y el validador la
rechazaría: el defecto raíz es que el vocabulario de `comun.py:290` no tiene lugar para lo derivado.
Absorbe 208, 310 y 400: los tres describen este mismo defecto desde el script 18, el script 19 y el
docstring.

---

## P-04 — La incertidumbre publicada no lleva ningún número (GRAVEDAD 4, CONFIRMADO)

**Archivo:línea** — `scripts/19_estado_comunas.py:148-163` (arma un bloque genérico que **reemplaza**
las tres procedencias de origen); `scripts/18:256-268, 487, 496, 539-544` (celda y ventana);
`scripts/18:203-218, 472-480` (RMSE con 3 vértices); `config/laminas.yaml:138-142, 153-155`.

Lo que el script 18 sí escribe en `data/processed/laminas/angol-prc-ar2a-lamina1.geojson`:

```
procedencia keys: ['fuente','url','metodo','capa_evidencia','incertidumbre','escala_original',
                   'fecha_dato','generado','rmse_m','metros_por_pixel','resumen_por_clase']
rmse en procedencia? 4.94 0.8486
incert: ... la georreferenciación y la vectorización son nuestras, con RMSE 4.9 m.
```

Lo que llega a `web/data/laminas/vectorizadas.geojson`, que es lo único que el visor puede leer:

```
INCERTIDUMBRE: PRODUCTO DERIVADO: la geometría la construimos nosotros a partir de una lámina
impresa; el organismo NO la publica así. El contenido es del estudio original, con su año y su
método; la ubicación y el trazado son nuestros. NO tiene el efecto legal del vectorial del MINVU.
 contiene 'celda' : False
 contiene 'cuantiz' : False
 contiene 'ventana' : False
 contiene 'suaviz' : False
 contiene 'RMSE' : False
```

El `metodo` publicado dice «El RMSE de cada lámina está en su archivo de origen, en
`data/processed/laminas/`» — carpeta que **no se publica**: `ls web/data/laminas/` devuelve un solo
archivo. Además el bloque colapsa en una sola frase tres láminas de calidad muy distinta: una figura
de 7,74 m/píxel, otra de 5,34 m/píxel y un plano de 0,85 m/píxel con RMSE 4,94 m. Y no nombra lo
que efectivamente engorda el borde del AR-2a: la máscara se construye sobre celdas de
`celda_px: 8` × 0,8486 m/px = **6,79 m**, suavizadas con una ventana de `ventana_celdas: 5` =
**33,9 m** (`scripts/18:262-268` y `:487`). Absorbe 307 y 308.

Sobre 308 en particular, confirmo por lectura y por medición: el ajuste usa 3 vértices
(`config/laminas.yaml:143-146`), o sea 2·3−4 = **2 grados de libertad**, sin *leave-one-out*, y el
tope es `rmse_maximo_m: 15` mientras `scripts/georref.py:20` fija el criterio «predial» del resto
del proyecto. Los 20 planos del script 08 sí publican `rmse_loo_m` (0,02 a 1,81 m); el AR-2a no
publica ningún RMSE al visor.

---

## P-05 — Los cuadros de la leyenda se publican como área de riesgo (GRAVEDAD 4, CONFIRMADO)

**Archivo:línea** — `scripts/18_vectorizar_laminas.py:347-354` (la clasificación por color corre
sobre la hoja entera); `:343-345` (`excluir_y` existe) y `config/laminas.yaml` (ninguna lámina lo
declara; sólo el plano AR-2a declara `excluir_x: 6900`, `laminas.yaml:147`).

**Control positivo sintético** — `tools/auditoria/lamina_sintetica.py`, que fabrica una lámina con
una caja de leyenda como las reales y la pasa por el `procesar()` real:

```
=== positivo ===
    Alto      2 polígonos ·     99.2 ha
    Medio     2 polígonos ·     30.2 ha
 "n_poligonos": {"Alto": 2, "Medio": 2},
 "n_poligonos_en_leyenda": {"Alto": 1, "Medio": 1},
 "iou_Alto": 0.9558, "iou_Medio": 0.9745,
 "leyenda_vectorizada_m2": 32400.0
```

La mitad de los polígonos de cada clase son el cuadro de la leyenda. Sobre las láminas reales,
`fidelidad_laminas.py` lo localiza en píxeles y en hectáreas:

```
Angol  Alto : "publicados_en_zona_de_leyenda": [{px:[1027,782], ha:0.28}, {px:[588,866], ha:6.12}]
Angol  Medio: "publicados_en_zona_de_leyenda": [{px:[588,898], ha:5.62}]
Catripulli alta : [{px:[1081,895], ha:0.3}]
Catripulli media: [{px:[1081,908], ha:0.5}]
```

**12,8 ha** publicadas como área inundable que son la caja de la leyenda del propio documento,
georreferenciadas con la afín del mapa. En Angol caen sobre territorio real. Gravedad 4 y no 5
porque son manchas chicas y localizadas; sube a 5 si alguien consulta ahí.

---

## P-06 — Una entrada ausente publica un inventario falso, sin error (GRAVEDAD 4, CONFIRMADO)

**Archivo:línea** — `scripts/19_estado_comunas.py:65-71` (`cargar` devuelve `None` si el archivo no
existe) con `:103, 106, 109, 119` (`or {"comunas": []}` / `or {"features": []}`);
`scripts/09_exportar_catalogo.py:126-127` (`if muni.exists():` sin `else` ni log);
`scripts/20_paquete_practicante.py:235` (`cargar(...estado-comunas.json) or {"comunas": []}`).

Re-corrido del instrumento `script19_entradas_ausentes.py`:

```
PUBLICADO : 32 comunas · documentos total=354 · con le_falta vacío=9
E1 sin catálogo: 32 comunas · documentos total=0 · con le_falta vacío=0 ·
   frases le_falta=Counter({'no le encontramos ninguna lámina de cartografía de inundación en
   documentos públicos': 32, 'no publica ningún documento de planificación territorial que hayamos
   podido cosechar': 32, ...})
  E1 escribió estado-comunas.json: True
  E1 Angol: {'documentos': 0, 'laminas_localizadas': 0,
             'le_falta': ['no tiene su área de riesgo por inundación en el vectorial público del
             MINVU', 'no le encontramos ninguna lámina de cartografía de inundación en documentos
             públicos', 'no publica ningún documento de planificación territorial que hayamos
             podido cosechar']}
```

Con el catálogo ausente, el script **escribe igual** y afirma de las 32 comunas que no publican
ningún documento. De Angol —que tiene Estudio de Riesgo, PRC y ordenanza en `data/raw/documentos/
angol/`— publica una afirmación falsa, en la capa cuya razón de existir es distinguir «no hay dato»
de «no hay riesgo». Cero errores, cero avisos, código de salida 0. Absorbe 219, que es el mismo
patrón en los scripts 09 y 20.

---

## P-07 — Apertura con núcleo par: corre la mancha y agrega píxeles (GRAVEDAD 3, CONFIRMADO)

**Archivo:línea** — `scripts/18_vectorizar_laminas.py:359-360`
(`cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ancho, ancho))` con `ancho = 4`, seguido de
`MORPH_OPEN`); `config/laminas.yaml:64` (Angol) y `:105` (Catripulli), ambas con `ancho_minimo_px: 4`.

**Comprobación propia**, `tools/auditoria/verif_702_apertura.py` — un cuadrado sintético, sin PDF:

```
ancho=3  núcleo:            ancho=4  núcleo:
[[0 1 0]                    [[0 0 1 0]
 [1 1 1]                     [1 1 1 1]
 [0 1 0]]                    [1 1 1 1]
                             [1 1 1 1]]
  entrada  filas 20..59       entrada  filas 20..59 cols 20..59
  salida   filas 20..59       salida   filas 21..60 cols 21..60
  desplazamiento dy=+0.00 dx=+0.00     desplazamiento dy=+0.96 dx=+0.99

ancho=5: dy=+0.00 dx=+0.00        ancho=6: dy=+0.94 dx=+0.96
```

El elemento estructurante de lado par no tiene centro: OpenCV lo ancla arriba-izquierda y el
resultado de la apertura sale corrido **+1 fila (sur) y +1 columna (este)**. Con `ancho` impar el
desplazamiento es exactamente cero. A 7,74 m/px son **+7,7 m al este y +7,7 m al sur** en Angol; a
5,34 m/px, **+5,3 m** en Catripulli. Es un sesgo sistemático, no ruido, y no está declarado en
ninguna parte.

**Corolario nuevo (P-N03)**: como el núcleo es asimétrico, la apertura deja de ser anti-extensiva —
puede *añadir* píxeles que no estaban en la máscara cruda. Medido sobre la imagen real de Angol:

```
Alto   ancho=3: crudo= 39872 limpio= 35134 perdidos= 4738 (11.9%) NUEVOS=    0 = 0.0 ha | 210.5 ha
Alto   ancho=4: crudo= 39872 limpio= 31999 perdidos=10100 (25.3%) NUEVOS= 2227 = 13.3 ha | 191.7 ha
Alto   ancho=5: crudo= 39872 limpio= 30432 perdidos= 9440 (23.7%) NUEVOS=    0 = 0.0 ha | 182.3 ha
Medio  ancho=4: crudo=  5788 limpio=  3788 perdidos= 2437 (42.1%) NUEVOS=  437 = 2.6 ha |  22.7 ha
```

**15,9 ha publicadas en Angol no corresponden a ningún píxel del color de su clase en la lámina de
origen.** Sólo el valor par produce ese efecto.

Absorbe **320**: `area_minima_m2` tiene omisión `0` en `procesar` (`scripts/18:329`) y `2000` en
`procesar_plano` (`:488`). Es inconsistencia real; hoy no muerde porque las tres láminas lo declaran.

---

## P-08 — El grosor mínimo no es un criterio físico y la premisa del río es falsa (GRAVEDAD 3, CONFIRMADO)

**Archivo:línea** — `scripts/18_vectorizar_laminas.py:27-32` (docstring: «la red hídrica se dibuja
en el mismo azul que la clase Alto… se separa por grosor»), `:328, 357-360`;
`config/laminas.yaml:64-68, 106`.

`ancho_minimo_px: 4` es un número en píxeles, no en metros: son **30,96 m en Angol** (4 × 7,74) y
**21,3 m en Catripulli** (4 × 5,337). El mismo parámetro descarta rasgos de anchos físicos muy
distintos según la resolución de impresión del PDF, sin que ninguna de las dos cifras aparezca en
la configuración ni en la procedencia.

**La premisa del río, medida en la imagen de origen** (`data/raw/documentos/angol/Estudio_Riesgo.pdf`,
página 30, imagen 0, extraída con `imagenes_de()` del script 18), vía
`tools/auditoria/verif_703_color_rio.py`:

```
imagen de origen 1266x1021
px 'Alto' crudos=39872  tras apertura=31999  comidos=10100 (25.3 %)

componentes mayores de lo comido por la apertura (¿río o franja legítima?):
  area=  356 px  bbox 39x58   RGB medio=(17,73,170)  dist a ALTO=15.1  elongacion=1.5
  area=  154 px  bbox 27x110  RGB medio=(18,73,141)  dist a ALTO=26.9  elongacion=4.1
  area=  152 px  bbox 34x30   RGB medio=(19,73,167)  dist a ALTO=16.4  elongacion=1.1
  ... (las 8 mayores, ninguna supera 356 px)

RGB medio de los píxeles COMIDOS   = [ 20.  72. 154.]  (n=10100)
RGB medio de los píxeles QUE QUEDAN = [ 10.  76. 159.]  (n=31999)
  distancia entre esos dos centros = 11.9
```

No hay ninguna componente conexa con forma de red hídrica. La más grande de lo eliminado mide
356 px con elongación 1,5 —una mancha, no un cauce— y el color de lo eliminado está a **11,9
unidades RGB** del de lo conservado: es el mismo azul, es borde de polígono. `fidelidad_laminas.py`
lo confirma desde otro ángulo: lo que llama «línea aislada» son **733 componentes cuya mayor mide
58 px**, es decir speckle de antialiasing, no un río.

Consecuencia: la apertura **no separa río de mancha**; recorta el 25,3 % de «Alto» (47,2 ha) y el
42,1 % de «Medio» (12,0 ha) de la lámina de Angol, de los cuales `fidelidad_laminas.py` atribuye
**25,57 ha a franjas pegadas a lo publicado** — área legítima. El control sintético lo cuantifica:
la franja legítima de 15 m de ancho se recupera al **67,9 %** en la lámina limpia y al **3,7 %** si
la figura viene comprimida en JPEG 80, que es como vienen las figuras de los PDF reales.

---

## P-09 — La capa B suma órbitas y publica el total como si fuera área (GRAVEDAD 3, CONFIRMADO)

**Archivo:línea** — `scripts/14_sar_huella_observada.py:889-893` (`area_total = sum(d["km2"] for d
in diagnostico)` y `"hectareas": round(area_total * 100, 0)`); `web/data/sar/indice.json`
(`"hectareas": 5776.0`); `web/app.js:1832` lee ese resumen; `tests/auditoria_datos.py` valida la
cifra «5776» contra la documentación, o sea **valida la cifra equivocada contra sí misma**.

Medición propia con área geodésica (`pyproj.Geod`), `tools/auditoria/verif_capaB.py`:

```
huella features: 1075 cobertura: 115
indice resumen: {'tracks': 3, 'poligonos': 1075, 'km2': 57.76, 'hectareas': 5776.0, ...}
[505] suma de la propiedad 'hectareas' de los polígonos = 5,776.4 ha
      indice.resumen.hectareas = 5,776.0 ha (suma por track)
      UNION geodesica de los 1075 poligonos = 5,073.9 ha
      solape entre tracks = 702.5 ha (12.2 % de la suma)
        156D: 298 pol, suma prop 1,536.8 ha, union 1,534.3 ha
        164A: 427 pol, suma prop 2,618.4 ha, union 2,614.3 ha
        83D:  350 pol, suma prop 1,621.2 ha, union 1,618.9 ha
```

Dentro de cada órbita el solape es despreciable (2–4 ha): las **702,5 ha** son territorio visto por
dos o tres tracks distintos y contado dos o tres veces. El área realmente inundada según esta capa
es **5.074 ha**, un 12,2 % menos que la publicada. Y el visor, además, dibuja los polígonos
superpuestos, así que la persona ve una sola mancha donde el índice cuenta dos.

---

## P-10 — 585 de 1.075 polígonos de la huella son inválidos (GRAVEDAD 3, CONFIRMADO)

**Archivo:línea** — `scripts/14_sar_huella_observada.py:561-562`
(`shapes(..., connectivity=8)`: dos píxeles unidos sólo por la esquina producen un anillo que se
autointerseca en ese vértice); `web/data/sar/huella-observada.geojson`,
`web/data/sar/cobertura-sar.geojson`.

```
[506] huella invalidos=585/1075  cobertura invalidos=59/115
     ejemplo: 2 Ring Self-intersection[-72.3293 -37.5894]
```

Absorbe **512**, que es el mismo tipo de defecto en la capa A pero en el universo, no en lo
publicado:

```
[512] validez geometrica:
  publicados invalidos: 0 []
  universo invalidos: 1
    (1, 'Temuco', 'PENDIENTES', 'Ring Self-intersection[-72.5049378170171 -38.6620175593733]')
```

O sea: la capa A publicada está limpia (0 de 63) y el único inválido del universo no se publica
—es un polígono de pendientes, no hídrico—. La capa B, en cambio, publica el 54 % de sus polígonos
inválidos. El *ray casting* del visor sobrevive a eso (ver VERIFICADO LIMPIO), pero cualquier
consumidor externo que use `shapely`, PostGIS o QGIS obtiene errores o resultados distintos.

---

## P-11 — Duplicado geométrico que la clave de deduplicación no ve (GRAVEDAD 3, CONFIRMADO, reformulado)

**Archivo:línea** — `scripts/06_areas_riesgo_prc.py:193-199` (`centroide` por promedio de vértices,
redondeado a 5 decimales), `:206-218` (clave `(comuna, centroide, nº vértices)`; el docstring dice
«La geometría es idéntica entre capas, así que no hace falta tolerancia»).

El hallazgo provisional lo llamaba «duplicado exacto». **No lo es**, y por eso la deduplicación
falla. Mi prueba de igualdad WKT da 0 grupos; la prueba de contención mutua encuentra el par:

```
[502] duplicados por geometria identica (WKT exacto):
  grupos duplicados=0

[509] contencion entre poligonos publicados (mismo comuna):
  #20 (Collipulli 'ZR-2') contenido 100.0% en #62 ('ZR-2')
  #62 (Collipulli 'ZR-2') contenido 100.0% en #20 ('ZR-2')
```

En el universo son `#58` (capa nacional, `INUNDACION`) y `#118` (capa regional, `ZR-2 Área de
Riesgo por Inundación`):

```
  # 58 PRC nacional            INUNDACION  verts 229  area 1.0457495773525925e-05
  # 118 PRC Riesgo Collipulli  ZR-2 ...    verts 229  area 1.0457495727644857e-05
   centroide-avg (-72.42995, -37.94556) nvert 229
   centroide-avg (-72.42994, -37.94559) nvert 229
```

Mismo polígono, mismo número de vértices, áreas que difieren en la decimocuarta cifra: los dos
servicios de ArcGIS entregan las coordenadas con precisión distinta. El centroide promedio,
redondeado a 5 decimales, difiere en 1e-5 de longitud y 3e-5 de latitud, y la clave no coincide. La
premisa escrita en el docstring —«no hace falta tolerancia»— es la causa. Consecuencia para quien
consulta: el visor dice «cae dentro de 2 áreas de riesgo» donde hay una, y el relleno translúcido
se oscurece haciendo parecer más severa la zona.

---

## P-12 — La verificación no se mide sobre la capa publicada (GRAVEDAD 3, PARCIAL)

**Archivo:línea** — `scripts/14_sar_huella_observada.py:909` (`verificar(agua_union,
cobertura_union, rejilla)`), `:813` (`agua_union |= res["agua"]` — la máscara ráster, previa a
`vectorizar`), `:566` (el filtro `area < area_min_m2` sólo actúa al vectorizar).

**La parte estructural: CONFIRMADA por lectura.** `verificar()` recibe la unión de máscaras de
píxeles, no el GeoJSON publicado. Todo lo que el filtro de área elimina —los grupos bajo
`min_pixeles_agrupados` convertidos a m²— cuenta a favor del enriquecimiento y no está en el mapa.

**La parte numérica: REFUTADA.** El hallazgo afirmaba que sobre la capa publicada el
enriquecimiento cae a ×1,95. Lo medí yo, con los 1.075 polígonos publicados, los 440 puntos
críticos hídricos de SENAPRED y 20 puntos de control al azar por cada punto observado dentro de la
cobertura publicada (`tools/auditoria/verif_capaB2.py`):

```
=== [503] enriquecimiento SOBRE LA CAPA PUBLICADA ===
  puntos SENAPRED hídricos dentro de la cobertura: 406 de 440
  radio    SENAPRED        azar           enriquecimiento
    100 m     7/406 ( 1.72 %)     42/8120 ( 0.52 %)  ×3.33
    200 m    10/406 ( 2.46 %)     81/8120 ( 1.00 %)  ×2.47
    300 m    14/406 ( 3.45 %)    104/8120 ( 1.28 %)  ×2.69
    500 m    27/406 ( 6.65 %)    175/8120 ( 2.16 %)  ×3.09
   1000 m    50/406 (12.32 %)    356/8120 ( 4.38 %)  ×2.81
  la huella cubre el 0.25 % del área de cobertura publicada
```

Entre ×2,47 y ×3,33 según el radio, es decir del mismo orden que el ×2,8 declarado, no ×1,95. La
señal de la capa publicada **se sostiene**. Reserva metodológica honesta: mi cálculo de distancia
usa grados × 111.320 sin corregir por el coseno de la latitud, lo que ensancha el radio en
longitud ~29 % a −39°; el sesgo afecta por igual a los puntos SENAPRED y a los de control, así que
el cociente es comparable, pero los porcentajes absolutos no son directamente los del script.

Gravedad 3 y no 4: el defecto es de método de verificación —una cifra que se cita como validación
externa no se mide sobre lo que se publica—, no una capa mal publicada.

---

## P-13 — «Puerto Saavedra» pierde su año, y la guía lo cuenta mal (GRAVEDAD 3, CONFIRMADO)

**Archivo:línea** — `scripts/06_areas_riesgo_prc.py:313-318` (renombra por
`correcciones_nombre_comuna`), `:342-350` (busca el año con el nombre **ya renombrado**);
`config/araucania.yaml:235` (`"Puerto Saavedra": 1964`) y `:263`
(`"Puerto Saavedra": "Saavedra"`); `docs/GUIA_PRACTICANTE.md:332`.

```
$ python -c "...areas_riesgo_prc_araucania.geojson..."
Counter({'2009': 66, '1989': 31, '1984': 6, '2012': 6,
         'no declarado por la fuente': 5, '2010': 3, '1992': 3, '2023': 2, '1991': 2})
sin anio comunas: Counter({'Loncoche': 2, 'Nueva Imperial': 1, 'Pucón': 1, 'Saavedra': 1})
```

```
  Saavedra publicados: 1
  comuna_fuente de esos: {'Puerto Saavedra'}
```

El diccionario `anio_instrumento_comuna` tiene la llave `"Puerto Saavedra"`, pero cuando se
consulta, el campo `comuna` ya vale `"Saavedra"`. El año 1964 —la reconstrucción posterior al
terremoto de 1960, el dato más elocuente de toda la capa— existe en la configuración y no se
publica.

Absorbe **404**, que es el síntoma documental del mismo defecto:
`docs/GUIA_PRACTICANTE.md:332` dice «Cerrar los 4 polígonos sin año — Loncoche, Nueva Imperial y
Pucón», y unas líneas más abajo lista «Puerto Saavedra 1964» entre los que «ya tenemos». Son **5**,
y el quinto es justamente Saavedra. El practicante recibe una tarea que omite el caso que la
configuración ya resolvió.

---

## P-14 — Huella a nivel del mar y en cordillera (GRAVEDAD 3, PARCIAL)

**Archivo:línea** — `web/data/sar/huella-observada.geojson`; `web/data/sar/indice.json`
(`procedencia.incertidumbre`); `config/araucania.yaml:209-220`
(`pendiente_max_grados: 5.0`, `altitud_max_m: 1200.0`, `altitud_min_m: 0.5`).

Medido con el DEM que el propio pipeline dejó en caché
(`data/processed/sar/2026-07-30_sistema_frontal/terreno.tif`, GLO-30 remuestreado a la rejilla),
tomando el punto representativo de cada polígono (`tools/auditoria/verif_capaB2.py`):

```
=== [507/508] altitud del punto representativo de cada polígono de la huella ===
     -5–2     m :  181 pol ·    839.7 ha
      2–5     m :   98 pol ·    590.1 ha
      5–20    m :  130 pol ·    555.7 ha
     20–100   m :  407 pol ·   2505.1 ha
    100–300   m :  164 pol ·    779.5 ha
    300–700   m :   67 pol ·    319.9 ha
    700–1000  m :   15 pol ·    160.0 ha
   1000–1300  m :   13 pol ·     26.3 ha
  sin DEM: 0

[507] polígonos con altitud ≤ 2 m: 182 · 840.9 ha (14.6 % de la huella)
      tracks: Counter({'164A': 111, '156D': 57, '83D': 14})
      lon/lat extremos: -73.47185 -73.090025 -39.644775 -38.00475

[508] polígonos con altitud ≥ 1000 m: 13 · 26.3 ha
   #233 83D alt=1036 m pend=0.6° 4.7 ha en (-71.1199,-39.1277)
   #41  83D alt=1183 m pend=3.9° 2.2 ha en (-71.5148,-38.2957)
   #142 83D alt=1150 m pend=0.0° 1.9 ha en (-71.1307,-38.8991)
  ≥700 m: 28 pol · 186.4 ha
```

**Lo confirmado**: 840,9 ha (14,6 % de la huella) están a 2 m o menos de altitud, en la franja
costera entre −73,47 y −73,09 de longitud; y el texto de incertidumbre publicado no contiene las
palabras «estuario», «marea», «costa» ni «océano» —lo comprobé buscándolas una por una—. Habla de
nieve húmeda, dosel, urbano denso y viento, que son las trampas de tierra adentro. Una detección
por radar a nivel del mar en el estuario del Imperial puede ser la pleamar, y el pipeline no tiene
cómo distinguirla.

**Lo parcial**: (a) mis 840,9 ha / 14,6 % no coinciden con las 658 ha / 11,4 % del hallazgo, porque
el criterio de altitud no está definido en él; (b) los 13 polígonos sobre 1.000 m **no violan
ninguna regla declarada**: `altitud_max_m: 1200` los admite explícitamente. Es un riesgo residual
de nieve húmeda —en agosto, a 1.000–1.200 m en los Andes de 38–39°S— no un incumplimiento; (c) la
«mancha de 70 ha a 724 m» del hallazgo **no la encuentro**: el polígono más grande sobre 700 m es
de 4,7 ha y el total sobre 700 m es de 186,4 ha repartidas en 28 polígonos. Esa parte queda
**SIN DATO**.

---

## P-15 — Tres «ZR-3 Área en torno a Canales» fuera del filtro hídrico (GRAVEDAD 2, CONFIRMADO)

**Archivo:línea** — `scripts/06_areas_riesgo_prc.py:75-81` (`TIPO_HIDRICO` no tiene «CANAL»).

```
[510] universo: clasificaciones con CANAL / AGUA / RIO / ESTERO no publicadas:
  no-pub #117 Collipulli clas='ZR-3 Área en torno a Canales' tipo=None
  no-pub #120 Collipulli clas='ZR-3 Área en torno a Canales' tipo=None
  no-pub #122 Collipulli clas='ZR-3 Área en torno a Canales' tipo=None
```

Tres polígonos del PRC de Collipulli que el instrumento zonifica **en torno a canales** —agua
conducida que se desborda— quedan fuera de la capa publicada porque el diccionario no tiene la
clave. En el mismo barrido, cuatro polígonos de Carahue y Villarrica cuyo `NOMBRE` habla de ríos,
esteros y cauces sí entran, porque su `CLASIFICACION_RIESGOS` dice `INUNDACION`. El defecto raíz es
que la clasificación depende de un diccionario de subcadenas cerrado y ningún control avisa cuando
un texto con vocabulario hídrico cae fuera de él (a diferencia de lo que sí pasa con los nombres de
comuna, que hacen caer el script en `06:378-386`).

---

## P-16 — Toltén: AR-1 y AR-2 contenidos en AR-3 (GRAVEDAD 2, CONFIRMADO)

**Archivo:línea** — `web/data/areas-riesgo-inundacion.geojson` features #53, #54, #55.

```
  #53 (Toltén 'AR-1') contenido 100.0% en #54 ('AR-3')
  #55 (Toltén 'AR-2') contenido 100.0% en #54 ('AR-3')
```

Son tres zonas distintas del instrumento —AR-1, AR-2 y AR-3 tienen usos prohibidos distintos— pero
anidadas. El visor las cuenta como tres áreas superpuestas sin explicar la jerarquía. No es un
error de procesamiento: es lo que la fuente publica. La falla es de presentación, no de dato.

---

## P-17 — Orientación de anillos al revés de RFC 7946 (GRAVEDAD 2, CONFIRMADO)

**Archivo:línea** — `scripts/06_areas_riesgo_prc.py:293` («respetando el signo del área para los
huecos», que es la convención ArcGIS, inversa a la de GeoJSON).

```
[511] orientacion de anillos:
  exteriores horarios(cw)=86 antihorarios(ccw)=0; huecos cw=0 ccw=2
  RFC7946 exige exterior CCW y hueco CW
```

Los 63 features publicados suman 86 anillos exteriores, **todos** en sentido horario, y 2 huecos,
ambos antihorarios: exactamente al revés de lo que exige RFC 7946. Ningún consumidor razonable
falla por esto (`shapely` y el *ray casting* del visor ignoran la orientación), pero un cliente que
sí la respete —algunos renderizadores vectoriales y varias librerías de geometría esférica— dibuja
el complemento del polígono, o sea toda la región **menos** el área de riesgo. Gravedad 2 porque
hoy no muerde, pero es exactamente el tipo de defecto silencioso que muerde al primer reutilizador.

---

## P-18 — Cinco GeoJSON del JRC publicados sin lector y exentos de la auditoría (GRAVEDAD 2, CONFIRMADO)

**Archivo:línea** — `web/data/jrc/rp{10,20,50,200,500}.geojson`; `web/app.js:85` y `web/sw.js:45`
sólo nombran `rp100`; `tests/auditoria_datos.py:274` excluye `jrc/` de la búsqueda de huérfanos.

```
  rp10.geojson: 53 feats, 40 KB, RP=10      rp200.geojson: 47 feats, 39 KB, RP=200
  rp20.geojson: 54 feats, 41 KB, RP=20      rp500.geojson: 49 feats, 41 KB, RP=500
  rp50.geojson: 50 feats, 39 KB, RP=50      rp100.geojson: 52 feats, 40 KB, RP=100
  leidos por app.js: rp100.geojson
```

253 features y ~200 KB que se descargan al repositorio publicado y nadie consume. Lo agravante es
la exención: el comentario de `auditoria_datos.py:273` justifica el `continue` diciendo que «los
shards por comuna se cargan por nombre calculado, no literal», lo cual es cierto para
`puntos-criticos/` y `planos/` y **falso para `jrc/`**, donde `rp100.geojson` está escrito literal
en `app.js:85`. Por eso el paso 4 informa «sin archivos publicados huérfanos» estando ciego a la
única carpeta que sí los tiene.

---

## P-19 — `--bbox` sobrescribe la capa B publicada (GRAVEDAD 2, CONFIRMADO)

**Archivo:línea** — `scripts/14_sar_huella_observada.py:702-703` (la ayuda dice literalmente
«recorta el área de trabajo (para probar rápido)»), `:717` (`bbox = args.bbox or
cfg["region"]["bbox"]`), `:877-879`:

```
    salida = WEB_DATA / "sar"
    escribir_geojson(huella_feats, salida / "huella-observada.geojson", meta)
    escribir_geojson(cobertura_feats, salida / "cobertura-sar.geojson", meta)
```

No hay ninguna condición sobre `args.bbox`. Correr el script con la bandera que él mismo ofrece
«para probar rápido» reemplaza la capa publicada por el recorte de prueba, con su propia
`cobertura-sar.geojson` — así que el visor diría «acá no se miró» para todo el resto de la región y
la contradicción sería invisible para la auditoría de datos, cuyo control 1 sólo verifica que las
features caigan **dentro** del bbox regional.

---

## P-20 — Dos definiciones de «inundación» entre capas (GRAVEDAD 2, CONFIRMADO)

**Archivo:línea** — `config/araucania.yaml:86-95` (`causas_inundacion` son sólo «Inundación por
desborde de cauce» y «Activación de quebradas»; `causas_fuera_de_alcance` excluye explícitamente
«Colapso colectores…» y «Anegamiento de caminos…»); `scripts/13_campamentos_riesgo.py:45`:

```
CLAVES_HIDRICAS = ("INUND", "INDUND", "ANEGAM", "TSUNAMI")  # el dato trae la errata
```

La capa de campamentos cuenta como hídrico el **anegamiento** —que la capa D excluye por escrito— y
además el **tsunami**, que no es fluvial en ninguna definición del proyecto. La capa A, por su
parte, publica los cuatro fenómenos pero cada uno etiquetado:

```
[titulares] tipo_hidrico publicado: Counter({'fluvial': 57, 'anegamiento': 3, 'litoral': 2,
                                             'napa_freatica': 1})
```

O sea: tres criterios distintos conviven, y sólo la capa A declara cuál aplicó a cada polígono. El
proyecto argumenta en su propia documentación que desborde y anegamiento son fenómenos distintos;
la capa de campamentos los fusiona.

---

## P-21 — El acantilado de `tolerancia_color` en Catripulli (GRAVEDAD 2, PARCIAL)

**Archivo:línea** — `scripts/18_vectorizar_laminas.py:347-354`; `config/laminas.yaml:104-105`
(`tolerancia_color: 40`).

Barrido propio sobre la imagen de origen, replicando el pipeline (mismo `ancho=4`):

```
tol= 40:  alta=    94.2 ha · media=   717.2 ha
tol= 45:  alta=    97.2 ha · media=   722.4 ha
tol= 50:  alta=    99.9 ha · media=   727.2 ha
tol= 55:  alta=   102.0 ha · media=   732.5 ha
tol= 60:  alta=   104.1 ha · media=   740.0 ha
tol= 65:  alta=   106.0 ha · media=   758.9 ha
tol= 70:  alta=   107.7 ha · media=  3336.0 ha
```

**El acantilado existe y es brutal (×4,4 entre 65 y 70)**, pero está a **25–30 unidades** del valor
declarado, no a 15 como decía el hallazgo. Y tiene una explicación física exacta que vale la pena
dejar escrita: la distancia RGB entre el blanco del papel (255,255,255) y el color declarado de
«Susceptibilidad media» (191,231,255) es **68,35**. En cuanto la tolerancia supera esa cifra, la
hoja entera se clasifica como clase media. El margen real de seguridad es la diferencia entre 40 y
68,35, y ningún control lo comprueba: nada en el pipeline verifica que el fondo de la lámina esté
fuera de la tolerancia de todas las clases. Ese es el defecto reutilizable, más que el número.

---

## P-22 — `area_minima_m2 = 2000` con 17 polígonos a un paso (GRAVEDAD 2, CONFIRMADO)

**Archivo:línea** — `scripts/18_vectorizar_laminas.py:286, 494`; `config/laminas.yaml:69-70, 107, 156`.

```
[angol-peligro-inundacion-2013]  n=98  m/px=7.74
  área m²: min 2037 · p10 2516 · mediana 7189 · p90 41665 · max 319482
  bajo el umbral (2000 m²): 0
  en [2000, 3000) m²: 17  · en [2000, 4000): 26  · ≤ 1 ha: 56
  umbral en píxeles: 33 px de 7.74 m
[angol-prc-ar2a-lamina1]  n=26  en [2000, 3000) m²: 4
[curarrehue-catripulli-inundacion-2025]  n=39  en [2000, 3000) m²: 5
```

Y el barrido de sensibilidad, corrido por mí:

```
   area_min= 1000 m²: Alto   90 pol    190.5 ha · Medio   38 pol     21.8 ha
   area_min= 2000 m²: Alto   70 pol    188.0 ha · Medio   28 pol     20.5 ha
   area_min= 4000 m²: Alto   54 pol    183.4 ha · Medio   18 pol     17.8 ha
```

17 de los 98 polígonos de Angol están a menos de 1.000 m² del umbral, y bajar el umbral a 1.000 m²
resucita 30 polígonos (2,8 ha). Un predio de 2.000 m² es un sitio urbano corriente. El parámetro se
justifica en el código como «descarta motas sueltas del antialiasing», pero el efecto real es
descartar áreas del tamaño de un terreno. Como el área es proporcional a `m_por_pixel²`, el umbral
fijo en m² equivale a 33 píxeles en Angol y a 2.777 en el plano AR-2a: la misma cifra significa
cosas muy distintas.

---

## P-23 — La lámina 09201-2 existe y nadie la declara (GRAVEDAD 2, CONFIRMADO / SIN DATO)

**Archivo:línea** — `config/laminas.yaml:114-124` (declara sólo `…09201-1.pdf`).

```
$ ls data/raw/documentos/angol/ | grep -i 09201
Plano_Zonificacion_Vialidad-PRC_09201-1.pdf
Plano_Zonificacion_Vialidad-PRC_09201-2.pdf

$ grep -rn "09201-2" config docs scripts web README.md REGLAS.md
docs/auditorias/2026-09-06/frente-7-poligonos.md:66:  (el informe del auditor; nada más)
```

Confirmado el hecho: el pliego 2 de 2 del Plano de Zonificación del PRC de Angol está descargado y
ninguna configuración, script, documento o página del visor lo menciona. El visor publica 26
polígonos AR-2a que son los de **una** de las dos láminas y no lo declara en ninguna parte, así que
alguien cuyo predio esté en la mitad de la ciudad que cubre la lámina 2 recibe silencio. Qué
contiene esa lámina queda **SIN DATO**: no la procesé, porque hacerlo exige leer sus vértices
rotulados a ojo y anotarlos en `config/`, que es modificar configuración.

---

## P-24 — Documentación que no coincide con el dato (GRAVEDAD 2, CONFIRMADO)

**215 — Ningún script declara `Requiere:`.**
`REGLAS.md:193` dice «Cada script declara en su docstring **`Requiere:`** además de `Salida:`».

```
$ grep -c "Requiere:" scripts/*.py | grep -v ":0"
(sin resultados: 0 de 20 scripts)
```

`tests/test_scripts.py:50-64` sólo busca `"Salida:"`. La regla lleva escrita el tiempo que lleve, y
la prueba que debería hacerla cumplir no la mira. Consecuencia concreta: el grafo de dependencias
—lo único que corrige el engaño de la numeración de scripts— no se puede reconstruir del código.

**216 — Tres referencias a `docs/REGLAS.md`, que no existe.**

```
scripts/07_buscar_laminas_riesgo.py:27:        con lo que ya había; ver regla 5 de docs/REGLAS.md)
scripts/20_paquete_practicante.py:393:`docs/REGLAS.md` del repositorio. Son doce y todas nacieron...
scripts/20_paquete_practicante.py:404:real está en `docs/REGLAS.md`.
data/processed/paquete_malleco/LEEME.md:37: (ya generado, con el mismo texto)
```

El archivo real es `REGLAS.md` en la raíz (249 líneas). El texto que recibe el practicante lo manda
tres veces a una ruta inexistente, y además le dice «son doce» cuando `REGLAS.md` tiene muchos más
encabezados. Un practicante que no encuentre las reglas simplemente no las aplica.

**403 — «23 planos» que son 20.** El hallazgo citaba dos ubicaciones; encontré cuatro:

```
web/app.js:185:  // ... cargar 23 imágenes de ~870 KB ...
web/app.js:190:  /** Rectángulos con la extensión de cada plano. Son 23 polígonos ...
docs/PROPUESTA.md:39:  ... 63 polígonos en 12 comunas + 23 planos georreferenciados ...
docs/PROPUESTA.md:167: Resultado sobre La Araucanía: **23 planos georreferenciados sin intervención**
docs/INVENTARIO_FUENTES.md:165: **Resultado: 23 planos georreferenciados automáticamente**
```

```
$ python -c "..."
20 planos en indice.json
```

`tests/auditoria_datos.py` valida «20» contra la documentación y da OK, así que el control existe y
no ve estas cinco copias: sólo persigue las cifras que tiene en su lista.

**401 — `estado_tramite` no está donde la regla dice.** `REGLAS.md:50-57` («Distinguir el peso
legal»: Vigente / Anteproyecto / **Derivado**) cierra con «Va escrito en el dato
(`estado_tramite`)». Verificado:

```
[401] estado_tramite presente?: 0 de 63   (areas-riesgo-inundacion.geojson)
     claves: ['anio','anio_fuente','clasificacion','comuna','eae_estado','eae_fecha_ingreso',
              'eae_procedimiento','es_inundacion','fuente','nombre','ordenanza_url',
              'ordenanza_url_vigente','origen_capa','sector','tipo_hidrico','usos_permitidos',
              'usos_prohibidos','zona']
laminas/vectorizadas.geojson props: ['amenaza','anio','clase','comuna','descripcion',
              'efecto_legal','escala_original','fuente','hectareas','origen_lamina']
```

`planos/indice.json` sí lo trae en los 20 (y el visor lo lee, `app.js:849,853`). Las dos capas de
polígonos, no. El caso más filoso es `vectorizadas.geojson`: «Derivado» es uno de los tres valores
que la regla nombra, y la capa derivada es justo la que no lo declara — y aunque lo declarara, el
visor no lee ninguna de sus propiedades (P-01).

---

## P-25 — `laminas.yaml`: el comentario huérfano resucita la lámina rechazada (GRAVEDAD 2, CONFIRMADO)

**Archivo:línea** — `config/laminas.yaml:158-182` (bloque «❌ RECHAZADA») y `:184-191`, que son las
últimas líneas del archivo (191 en total):

```
182:  # LECCIÓN: el título de una lámina nombra su MARCO, no necesariamente lo que mapea...
183:
184:  # ---------------------------------------------------------------------------
185:  # La única cartografía de inundación que alcanza a Ercilla y Los Sauces, las
186:  # dos comunas de Malleco sin ningún documento propio. Viene del álbum de planos
187:  # del Sistema de Alerta Temprana de crecidas del Biobío, cuyo marco se extiende
188:  # sobre la subcuenca de los ríos Malleco y Vergara.
189:  #
190:  # ⚠️ Es gruesa: 43,8 m/píxel, comparable al modelo regional del GORE...
```

El archivo termina con el encabezado —sin su entrada— de la lámina de la DGA que el bloque anterior
acaba de rechazar por escrito, y lo hace repitiendo textualmente la frase que motivó el error
original: «la única cartografía de inundación que alcanza a Ercilla y Los Sauces». Es el resto de
un borrado incompleto. Quien lea el archivo de arriba abajo encuentra primero el rechazo y después
el argumento a favor, sin marca de cuál manda. Absorbe 321 y 402, que son el mismo bloque descrito
dos veces.

---

## P-26 — Los propios instrumentos de auditoría se caen en Windows (GRAVEDAD 2, CONFIRMADO — hallazgo nuevo)

Tres de los instrumentos entregados abortan a mitad de su salida por `UnicodeEncodeError`, porque
imprimen `→` y `≤` sin fijar la codificación y la consola de este equipo es cp1252:

```
tools/auditoria/georref_independiente.py:173  -> UnicodeEncodeError: '→'  (aborta en la
    PRIMERA lámina; no llegué a ver ningún resultado suyo)
tools/auditoria/control_alcance_regional_laminas.py:79 -> UnicodeEncodeError: '→' (aborta
    después de Angol; las otras dos láminas no se midieron)
tools/auditoria/distribucion_areas_vs_area_minima.py:77 -> UnicodeEncodeError: '≤'
```

Los dos últimos se recuperan con `PYTHONIOENCODING=utf-8`; el primero no llegué a hacerlo correr
completo en el tiempo disponible. Importa por dos razones: (a) un instrumento que se cae a mitad
entrega una medición parcial que **parece** completa si sólo se mira el principio de la salida
—`control_alcance_regional` alcanzó a medir Angol y no las otras dos láminas—; (b) la regla del
propio proyecto sobre Unicode en Windows existe y no se aplicó a los instrumentos.

Por eso mis instrumentos nuevos abren con
`sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")`.

---

## P-27 · P-28 · P-29 · P-30 — gravedad 1

**P-27 (221) — Campos escritos que nadie lee.** Salida de `campos_visor_vs_datos.py`:

```
## estado-comunas.json  claves que el archivo trae y el visor NO lee (4):
   ['slug','mayores_60','viviendas_hacinadas','hogares_agua_de_rio']
## planos/indice.json   (8): ['ancho','alto','kb','crs_original','aptitud','fuente','anio',
   'procedencia_metodo']
## indice-comunas.json  (3): ['slug','puntos_total','causas']
## jrc/rp100.geojson    (3): ['fuente','anio','periodo_retorno_anios']
## areas-riesgo (campamentos) (4): ['hectareas','en_area_riesgo','es_inundacion','levantado_por']
## laminas/vectorizadas.geojson (11): TODAS  ← ver P-01
```

`mayores_60`, `viviendas_hacinadas` y `hogares_agua_de_rio` se escriben en
`scripts/19_estado_comunas.py:197-199` desde el Censo 2024 y no se muestran. Peso muerto, salvo el
caso de las láminas, que es P-01.

**P-28 (319) — `umbral_agua()` declara percentil 90 por omisión y en su docstring.**
`scripts/sar.py:157` (`percentil: float = 90.0`) y `:165-166` («Se toma su percentil 90 en la
imagen post»). El proyecto usa 50 (`config/araucania.yaml:170`,
`scripts/14_sar_huella_observada.py:518-521`, pasado explícitamente). El valor efectivo es correcto;
lo que miente es la documentación de la función, y es la que alguien leería para reutilizarla.

**P-29 (317) — `area_pixel_m2` con la latitud media de la región.**
`scripts/14:740-741` y `scripts/sar.py:390-394`.

```
lat media -38.5 cos 0.7826
  lat -37.35: sesgo vs media = +1.58 %
  lat -39.65: sesgo vs media = -1.62 %
```

El área mínima de agrupación (`min_pixeles_agrupados: 5`) queda ±1,6 % descalibrada en los extremos
norte y sur de la región. Es real y despreciable.

**P-30 (313) — `TOL_PASO` se aplica al paso de los VALORES, no de las posiciones.**
`scripts/08_georreferenciar_grilla.py:60` (`TOL_PASO = 0.02`) y `:194-200` (`pasos =
np.diff(valores)`). Confirmado por lectura: si un rótulo no se lee, el paso de valores salta de
1.000 a 2.000 m y una retícula perfectamente regular se declara irregular. Los 20 planos publicados
pasaron con RMSE *leave-one-out* de 0,02 a 1,81 m, así que **no se observa impacto en el corpus
actual**; el riesgo es de falsos negativos (planos que se rechazan pudiendo georreferenciarse), que
por definición no dejan huella en lo publicado.

---

## REFUTADO, con su evidencia

### 501 — «Ocho polígonos de Collipulli publicados como fluvial que MINVU clasifica como remoción en masa»

**Refutado el fundamento; el hecho publicado es otro.** Sí hay 8 polígonos —no 7— clasificados como
fluviales cuyo texto no dice «INUND»:

```
[501] tipo_hidrico=fluvial cuyo texto de clasificacion NO dice INUND:
  #18 #25 #28 #29 #42 #43 #44 #51  Collipulli
  clas='ZR-5 Área y/o Franja de Restricción por Quebradas'   total=8
```

Pero **no son polígonos que MINVU clasifique como remoción en masa**. Vienen exclusivamente de la
capa regional `PRC Riesgo Collipulli`, que no publica `CLASIFICACION_RIESGOS`; los polígonos de
remoción son otros, de la capa nacional. Lo medí cruzando geometrías:

```
$ python -c "...solape ZR-5 vs REMOSION EN MASA..."
ZR-5: 8   REMOSION nacional: 52
  ZR-5 #48  solapa  0.0% con REMOSION #3
  ZR-5 #63  solapa  0.0% con REMOSION #3
  ZR-5 #71  solapa  0.0% con REMOSION #3
  ZR-5 #75  solapa  0.0% con REMOSION #3
  ZR-5 #88  solapa  0.0% con REMOSION #3
  ZR-5 #89  solapa  0.0% con REMOSION #3
  ZR-5 #90  solapa 65.3% con REMOSION #91
  ZR-5 #100 solapa 32.5% con REMOSION #72
```

Seis de los ocho no tocan **ningún** polígono de remoción; los otros dos solapan parcialmente, como
es normal entre zonas contiguas de un mismo plan. Y clasificar una quebrada como fluvial es
coherente con el criterio que el propio proyecto escribió para la capa D:
`config/araucania.yaml:86-89` lista «Activación de quebradas» **dentro** de `causas_inundacion`. La
regla `"QUEBRAD": "fluvial"` de `scripts/06:78` aplica ese mismo criterio.

Lo que sí queda como reserva —y no pude medir porque exigiría consultar el servicio del MINVU, que
tengo prohibido— es si la capa nacional publica esos mismos ocho polígonos con otra etiqueta: la
deduplicación (P-11) los habría descartado antes de que se pudiera ver. Esa parte es **SIN DATO**.

### 314 — «`TOL_INLIER_M = 3 m` es menos de un punto tipográfico a escalas chicas»

**Refutado sobre el corpus publicado.** `scripts/08_georreferenciar_grilla.py:139` fija
`TOL_INLIER_M = 3.0` y `:180` lo aplica a los valores en metros de mapa. Convertido a píxeles del
render de 300 dpi de cada uno de los 20 planos publicados:

```
  Pucón v4 p001       res=0.773 m/px  escala~1:9,130  TOL_INLIER 3 m =  3.88 px  rmse_loo=1.31
  Traiguén            res=0.512 m/px  escala~1:6,047  TOL_INLIER 3 m =  5.86 px  rmse_loo=0.19
  Pitrufquén 2 p001   res=0.423 m/px  escala~1:4,996  TOL_INLIER 3 m =  7.09 px  rmse_loo=0.03
  Vilcún p001         res=0.212 m/px  escala~1:2,504  TOL_INLIER 3 m = 14.15 px  rmse_loo=0.09
  ... (los 20 entre 3,88 y 14,15 px)
```

A 300 dpi un punto tipográfico son 4,17 px. La tolerancia más ajustada del corpus es 3,88 px
—prácticamente un punto— y la más holgada, 14,15 px. No hay ningún plano donde sea sub-píxel, y los
RMSE *leave-one-out* publicados (0,02–1,81 m) confirman que la tolerancia está funcionando. El
escenario del hallazgo requeriría un plano a 1:50.000 o menor, y no hay ninguno en el corpus:
**SIN DATO** para ese caso hipotético, **REFUTADO** para lo publicado.

---

## VERIFICADO LIMPIO

**El *ray casting* del visor.** `tools/auditoria/raycasting_vs_shapely.py`, re-corrido:

```
TOTAL puntos evaluados: 13308   discrepancias visor↔shapely: 0
```

Coincide con `shapely` en anillos horarios y antihorarios, huecos en ambos sentidos, multipolígonos,
anillos abiertos, features solapadas, autointersecciones y puntos a 1, 3 y 10 m del borde por dentro
y por fuera. Las únicas casillas «indefinido» son puntos **exactamente sobre** un vértice o una
arista, donde la respuesta no está definida en ninguna implementación. Esto es importante dado P-10
(585 polígonos inválidos): el visor los consulta bien igual.

**705 — Georreferenciación.** No pude correr `georref_independiente.py` completo (P-26), pero
tengo tres mediciones propias que apuntan al mismo lado: el control positivo sintético devuelve
IoU 0,956 / 0,975 con desplazamientos de centroide de 5,2 y 15,2 m sobre una lámina de 5 m/px; el
control «guardián» falla como debe; y el ajuste por vértices del plano AR-2a se reproduce en
**RMSE 4,94 m** (residuos 3,48 / 6,36 / 4,56 m; rotación −0,057°; 0,8486 m/px). No encontré
evidencia de un corrimiento sistemático más allá del píxel de P-07. **Limpio con la reserva de que
sólo hay 3 puntos de control y 2 grados de libertad** (P-04).

**706 — Trama AR-2a.** Con `fidelidad_laminas.py` re-corrido:

```
 "marcas_del_tamaño_buscado": 22448,
 "marcas_dentro_de_lo_publicado": 17117,
 "recall_marcas_pct": 76.3,
 "densidad_dentro_marcas_por_ha": 154.9,
 "densidad_fuera_marcas_por_ha": 3.0
```

Le doy veredicto: **el 76,3 % de recall no es una falla**. El contraste de densidad es de ×52
(154,9 marcas/ha dentro contra 3,0 fuera), que es lo que hay que mirar: si el detector estuviera
disparando al azar, las dos densidades serían parecidas. El 23,7 % restante se explica por tres
causas ya identificadas y todas deliberadas: las marcas del bloque de leyenda que `excluir_x: 6900`
descarta, los polígonos bajo `area_minima_m2: 2000` (4 de los 26 publicados están entre 2.000 y
3.000 m², P-22), y las marcas sueltas —texto, símbolos, esquinas de edificios— que la densidad
mínima filtra a propósito.

**La capa A publicada, en validez y alcance.** 0 de 63 polígonos inválidos; los 124 del universo
dentro del bbox regional; los nombres de comuna con `comuna_fuente` conservado; ningún polígono
publicado sin `tipo_hidrico`. `python -m pytest tests -q` → 63 passed.

---

## Nota sobre método

Todo lo de arriba salió de leer el archivo y la función completa, enumerar por qué caminos pasa
cada defecto, y volver a medir. No reutilicé ninguna cifra de los informes de los auditores: los
números de este documento son los que produjeron mis comandos, y donde no coinciden con el
hallazgo provisional lo digo (P-12, P-14, P-21, 501, 314). Lo que no pude medir —el contenido de la
lámina 09201-2, la clasificación nacional de los ocho ZR-5, la mancha de 70 ha a 724 m— dice
SIN DATO y no cuenta como falla ni como OK.
