# Frente 7 — ¿Estamos reconociendo bien los polígonos? (IDs provisionales 701+)

Medido sobre los artefactos (`data/processed/laminas/*.geojson`, `web/data/laminas/vectorizadas.geojson`)
y sobre las láminas de origen, el 6-sep-2026, por el orquestador. Instrumentos, todos en
`tools/auditoria/`: `lamina_sintetica.py` (controles positivo/negativo/guardián),
`fidelidad_laminas.py` (IoU por clase, apertura, leyenda, trama), `georref_independiente.py`
(SENAPRED, GORE, barrido de corrimiento, consistencia entre láminas). Evidencia visual en
`tools/auditoria/evidencia_laminas/` y `tools/auditoria/salida_sintetica/`.

## Las dos preguntas del instrumento, por arnés

| Arnés | ¿Fallaría si lo medido estuviera roto? | ¿Se vería distinto si el instrumento estuviera muerto? |
|---|---|---|
| lámina sintética | sí: afín invertida, clases confundidas o apertura que se come todo bajan el IoU < 0,9; un guardián que no se cae reprueba | sí: `procesar()` → None imprime «SIN POLÍGONOS»; el negativo exige 0 y el positivo exige > 0, un cero permanente reprueba |
| fidelidad | sí: el mismo GeoJSON corrido 5 px baja el IoU (Angol Alto 0,70 → 0,43; Catripulli media 0,94 → 0,85) | sí: la réplica del pipeline se valida con IoU publicado↔máscara limpia ≈ 1 (0,98 / 0,90 / 0,996 / 0,997) |
| georref | parcial: el barrido resuelve corrimientos ≥ 50 m con 7 puntos (control +150 m → −100 m); no resuelve con 6 puntos y un outlier a 1,6 km (Catripulli: SIN DATO) | sí: n = 0 imprime SIN DATO |

## Control sintético (salida cruda de `lamina_sintetica.py`, tercera corrida)

```
positivo:  iou_Alto 0.9558 · iou_Alto_con_franja 0.958 · iou_Medio 0.9745
           desplazamiento_Medio 5.23 m (1,05 px) · hausdorff_Medio 9.9 m
           franja_15m_recuperada 67.9 % · leyenda_vectorizada 32400 m² · n_poligonos_en_leyenda Alto 1 Medio 1
           falso_positivo_fuera_de_verdad 4 m² (el río de 2 px desapareció) · anillos_interiores_Alto 1
positivo_jpeg80: iou_Alto 0.9688 · iou_Medio 0.9703 · franja_15m_recuperada 3.7 % · leyenda 29875 m²
negativo:  0 polígonos (procesar devolvió None) — OK
guardian:  SystemExit — OK ([sintetica-guardian] el resultado cae FUERA de la región: lon -70.456..-70.418)
=== VEREDICTO === todos los controles pasan
```

Lectura: el pipeline recupera geometría y posición conocidas con ≈1 px de precisión, respeta
huecos, elimina líneas de 2 px y se cae si la lámina aterriza fuera de la región. Pero
**publica la caja de leyenda como territorio** (un polígono extra por clase), y una franja
legítima de 3 px sobrevive al 68 % sin compresión y al 4 % con JPEG.

## Hallazgos

### 701 · Los cuadros de la leyenda están publicados como área de riesgo — GRAVEDAD 5 · CONFIRMADO
- `scripts/18_vectorizar_laminas.py:347-350` (clasificación por color sobre la hoja entera; `excluir_y` existe en :343-345 pero ninguna lámina de `config/laminas.yaml` lo declara).
- QUÉ PASA: los cuadros de muestra de la leyenda tienen el color exacto de la clase y superan `area_minima_m2`, así que se vectorizan y georreferencian con la afín del mapa.
- CÓMO SE VE: en Angol, dos rectángulos de **6,12 ha «Alto»** (371×170 m, centroide lon −72,70378 lat −37,83436) y **5,62 ha «Medio»** (356×162 m, lon −72,70369 lat −37,83663) en campo abierto al sur del pueblo, a 2 km del punto crítico más cercano; en Catripulli, 0,3 ha «Susceptibilidad alta» (lon −71,68301 lat −39,37424) y 0,5 ha «media» (lon −71,68303 lat −39,37484). Una persona que mire el mapa ahí ve una mancha «Alto» dibujada sobre un potrero. (Si además el veredicto la nombra es SOSPECHA: el frente 2 reporta en 201 que `evaluar()` no consulta `estado.laminas`; lo resuelve el verificador.)
- SALIDA CRUDA (`fidelidad_laminas.py`, `publicados_en_zona_de_leyenda`): Angol Alto `[{px:[1027,782],ha:0.28},{px:[588,866],ha:6.12}]`, Medio `[{px:[588,898],ha:5.62}]`; Catripulli alta `[{px:[1081,895],ha:0.3}]`, media `[{px:[1081,908],ha:0.5}]`. Recortes `tools/auditoria/salida_sintetica/angol_recorte_leyenda.png` y `catripulli_recorte_leyenda.png` muestran que px (588, 866/898) y (1081, 895/908) son los cuadros «Alto/Medio» y «Susceptibilidad Alta/Media» de la leyenda. Total: 4 polígonos, 12,5 ha, de 163 publicados.
- REPRODUCIR: `python tools/auditoria/fidelidad_laminas.py` y `python tools/auditoria/lamina_sintetica.py` (la sintética lo reproduce: `n_poligonos_en_leyenda`).

### 702 · La apertura con núcleo par (4×4) corre toda la mancha +1 px al este y +1 px al sur — GRAVEDAD 3 · CONFIRMADO
- `scripts/18_vectorizar_laminas.py:359-360` (`getStructuringElement(MORPH_ELLIPSE,(ancho,ancho))` con `ancho=4`, `morphologyEx(...MORPH_OPEN...)`).
- QUÉ PASA: en OpenCV la apertura con un elemento de tamaño par no es anti-extensiva (el ancla queda descentrada): un cuadrado 100..199 sale 101..200. Es un corrimiento sistemático de 7,74 m (Angol) y 5,34 m (Catripulli), del mismo orden que la incertidumbre que la procedencia declara como aleatoria (±7,7 m).
- SALIDA CRUDA:
  ```
  cuadrado sintético 100x100: núcleo 4x4 · px de la apertura que NO estaban en la cruda: 196 · dx=+0.995 dy=+0.985 px
     control núcleo 5x5: px fuera 0 · dx=+0.000 dy=+0.000 px
     cuadrado abierto: x 101 200  y 101 200  (original 100..199)
  Angol Alto: núcleo 4x4 · px de la apertura que NO estaban en la cruda: 2227
  ```
- CÓMO SE VE: todos los bordes publicados están 1 px al sureste de donde la lámina los pinta. No lo ve ningún control externo (los puntos SENAPRED resuelven ≥ 50 m).
- REPRODUCIR: bloque «apertura con núcleo PAR» en este frente (comando en el informe).

### 703 · La premisa «el río tiene el mismo azul que Alto» es falsa en Angol; la apertura se come franjas legítimas — GRAVEDAD 3 · CONFIRMADO
- `config/laminas.yaml:64-68` y docstring `scripts/18_vectorizar_laminas.py:27`.
- QUÉ PASA: la red hídrica de la lámina de Angol va en azul marino ≈ (0,8,48), a distancia RGB 135 del color «Alto» (4,78,163): con `tolerancia_color: 45` ya queda fuera. 9.056 px del cuerpo tienen ese color y **0** están a < 45 de «Alto». Lo que la apertura de 4 px descarta son píxeles del color «Alto»: 47,2 ha de 188 publicadas (25,6 ha de borde pegado a polígonos publicados y 34,9 ha de franjas aisladas a lo largo de esteros, 733 componentes, la más larga 58 px); en «Medio», 12 ha sobre 20,5 publicadas. La lámina sí dibuja el río *dentro* de la banda «Alto», y esa línea excluida parte la banda en dos franjas que, donde son angostas, mueren.
- CÓMO SE VE: quebradas y esteros de los cerros al oeste de Angol que la lámina pinta de «Alto» no tienen polígono; una persona ahí lee «no cae dentro».
- SALIDA CRUDA (`fidelidad_laminas.py`): Angol Alto `iou_publicado_vs_cruda 0.6976 · comido 47.16 ha · FRANJA 25.57 · LÍNEA 34.93`; Medio `iou 0.4934 · comido 11.98 · FRANJA 4.71 · LÍNEA 9.89`; Catripulli alta `iou 0.8275 · comido 5.79 · FRANJA 7.54 · LÍNEA 4.35`; media `iou 0.9416 · comido 16.01 · FRANJA 20.66 · LÍNEA 8.49`. (FRANJA+LÍNEA supera «comido» porque la apertura par también agrega píxeles fuera de la cruda, ver 702.) Color del río: `píxeles de color río en el cuerpo: 9056 · de ellos a <45 del color Alto: 0`. Imagen: `evidencia_laminas/angol2013_huerfanos_x05.png` (magenta = azul fuera de toda tolerancia: bordes antialiasados y red hídrica).
- NOTA: en la sintética el río sí compartía color y sí lo eliminó la apertura; el mecanismo funciona, pero en la lámina real no era necesario para el río y cuesta el 30 % de «Alto».

### 704 · El plano AR-2a publicado es la lámina 09201-1 de dos, y nadie lo declara — GRAVEDAD 4 · CONFIRMADO (cobertura) / SIN DATO (contenido de la lámina 2)
- `config/laminas.yaml:114-124`; `data/raw/documentos/angol/Plano_Zonificacion_Vialidad-PRC_09201-2.pdf` existe (3,3 MB) y `grep -rn "09201-2"` en config, docs, scripts y web no devuelve nada.
- QUÉ PASA: los tres puntos crónicos «Alto» de SENAPRED (Villa La Arboleda, Santa Teresita, Los Ríos, N ≈ 5.812.200) quedan a 1.058-1.274 m del AR-2a publicado, fuera del marco de la lámina 1 (vértice 10 en N 5.814.024), pero a 29-37 m del «Alto» del Estudio 2013. El visor dirá «no cae en área AR-2a del plan regulador» donde puede haber AR-2a en la lámina 2.
- SALIDA CRUDA (`georref_independiente.py`): `distancias_a_AR-2a: n=7 <=0:0 <=50:0 <=100:1 <=300:2 mediana=1159`; `distancias_a_Alto (2013): <=50:4 · [VILLA LA ARBOLEDA 29, VILLA SANTA TERESITA 31, VILLA LOS RIOS 37, PUENTE MALLECO 12]`. Mapa: `evidencia_laminas/angol_mapa_laminas_vs_evidencia.png`.

### 705 · Georreferenciación: consistente con toda la evidencia independiente disponible — VERIFICADO LIMPIO con reservas
- Las dos láminas de Angol, georreferenciadas por métodos distintos (retícula de dos rótulos vs tres vértices), coinciden: el corrimiento de AR-2a que maximiza su intersección con «Alto» 2013 es **(0, 0)** en una grilla de ±400 m cada 20 m (`interseccion 45.0 ha`; 40,7 % de AR-2a dentro de «Alto», 42,8 % dentro de Alto∪Medio).
- SENAPRED (no participó en la derivación): Angol 2013, 4 de 4 puntos «Alto» a 12-37 m (1,5-5 px); Catripulli, 4 de 6 a 0 m y 5 de 6 a ≤ 236 m (el sexto, Angostura, a 1,6 km, fuera del marco).
- GORE (35 m): Angol «Alto» 66 % en MÁXIMA + 11 % MEDIA, 23 % fuera; Catripulli «alta» 87 % MÁXIMA + 13 % MEDIA; AR-2a 74 % MÁXIMA. Coherentes.
- Barrido de corrimiento: Angol 2013 mejor (50, 0) con media 128,6 vs 144 en el origen — dentro de la resolución del instrumento (control +150 → −100). **Catripulli SIN DATO** (6 puntos, control positivo no resuelve). AR-2a SIN DATO por 704.
- RESERVA: dos de tres láminas no tienen `rmse_m` (`rmse_declarado_m: no declarado`) porque su afín se fija con dos rótulos horizontales y uno vertical (0 grados de libertad); AR-2a declara RMSE 4,94 m sobre **2 grados de libertad** (3 vértices). Un RMSE con 2 gdl es una estimación con enorme varianza, no una medida.

### 706 · Trama AR-2a: 76 % de las marcas de achurado caen dentro de lo publicado — SIN VEREDICTO
- `recall_marcas_pct 76.3 · marcas 22448 · dentro 17117 · densidad dentro 154.9/ha · fuera 3.0/ha`. El 24 % fuera puede ser texto, símbolos y bordes (la densidad fuera es 50× menor) o áreas AR-2a perdidas: hay que mirarlo sobre `evidencia_laminas/angol-prc-ar2a-lamina1_publicado_sobre_plano_x025.png`. Va a la cola de campo.

## Respuesta directa

**Sí reconocemos la forma y la posición de lo que la lámina pinta, dentro de ~1 px, y lo sabemos porque una lámina de geometría conocida pasa por el mismo código y vuelve con IoU 0,96-0,97 y 1 px de desplazamiento.** Sobre las láminas reales, la clase principal se recupera con IoU 0,70 (Angol Alto), 0,83 (Catripulli alta) y 0,94 (Catripulli media); las clases menores peor (Angol Medio 0,49). Lo que falta no es error de posición: es (a) la apertura de 4 px que se come franjas legítimas de riesgo a lo largo de esteros, apoyada en una premisa sobre el color del río que en Angol es falsa; (b) un corrimiento sistemático de 1 px por el núcleo par; (c) cuatro polígonos que son la leyenda de la hoja y están publicados como territorio; y (d) la mitad sur de Angol sin el plano legal porque sólo se vectorizó una de dos láminas.
