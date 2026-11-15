# Continuar riesgomapas: prompt para la próxima sesión

## Estado al 15-nov-2026, tarde: la auditoría de los tres frentes está hecha y verificada

Los tres frentes que dejó planeados el traspaso de la mañana corrieron en paralelo, cada
uno con su verificador de contexto limpio y del otro modelo. **50 hallazgos de los
auditores, ninguno refutado, y 7 nuevos de los verificadores.** La síntesis por familias, con los IDs finales y la gravedad del verificador,
está en `docs/auditorias/2026-11-15/SINTESIS.md`; empezar por ahí.

Lo que cambia el plan:

1. **Angol: la capa derivada es una copia degradada del vectorial oficial.** GeoIDE
   publica el AR-2a de la Resolución 40/2022 y nuestras láminas cubren el 72 % (faltan
   78,4 ha), sin el AR-2b. No es georreferencia ni otra versión del plan: el contorno
   oficial calza con el achurado. Es el vectorizador, que no ve el achurado sobre fondo
   oscuro, y bajar el umbral no lo arregla. El IoU de 0,20 de septiembre queda explicado
   (plan contra estudio de 2013). Y el visor dice en cinco textos que ese vectorial no
   existe (F-103).
2. **La capa A está vieja o incompleta** en Nueva Imperial (Res. 111/2025), Renaico (falta
   el pueblo) y Toltén (faltan Nueva Toltén y Villa Boldos). GeoIDE lo trae.
3. **El censo cuenta dos veces a 17.887 personas**: las 33 aldeas son 505 manzanas de la
   capa 0. La región suma 1.003.546, no 1.021.433, y el visor muestra habitantes inflados
   en 19 comunas. El GPKG del INE es el mismo dato que el de Esri (17 campos, cero
   diferencias) y trae `TIPO_MZ`, que es lo que revela el duplicado.
4. **La población expuesta depende más del criterio que de la capa**: el AR-2a de Angol va
   de 429 a 22.113 personas; el reparto por área da 4.943, -16/+17 % con el error de borde.
   Publicar por manzana pesaría 0,7 a 6,1 MB con gzip; por comuna, 15 kB.
5. **Veredicto**: elegir comuna responde «Sin registros» en 22 de 30 (F-101), la pestaña de
   detalle contradice al titular de borde (F-100), el texto reenviado no nombra la capa que
   decidió (F-102), la banda de borde rebaja alto a medio (F-105).

Además, hecho hoy:

- Sin guiones largos en `GUIA_PRACTICANTE.md`, `PRACTICA_PROFESIONAL.md` y el script 20
  (`d7d46e5`). **Quedan unos 25** en los `.md` del paquete, que vienen de los textos de
  `fuente` de los scripts 01, 02 y 18 (el rótulo de fuente del MINVU y de SENAPRED, por
  ejemplo) y de `tools/auditoria/revisar_poligonos_provincia.py`. Corregirlos cambia
  `web/data/`, así que va con la regeneración de capas. `web/app.js` tiene 53 y el resto
  del repo unos 2.000.
- Las descargas quedaron en `data/raw/geoide_minvu_araucania/`,
  `data/raw/geoide_minvu_araucania_verif/` y `data/raw/censo_ine_2024_R09/` (111 MB).
- Los recortes de lámina de la verificación B no se versionan (`.gitignore`); se regeneran
  con `tools/auditoria/vB_angol_fondo_oscuro.py`.
- Borrador del mensaje para pedirle los datos al practicante, entregado a Nicolás en el
  chat. **Sigue pendiente pedirle** el GeoPackage con la tabla del Anexo 1, los `.points` y
  el script del cruce.

### Decisiones que son de Nicolás, no tareas

1. **Angol**: ¿la capa oficial de GeoIDE reemplaza a la vectorizada como A normativo, y la
   vectorizada queda como respaldo trazable o se retira? La evidencia apoya reemplazar.
2. **Fuente del censo**: pasar al GPKG del INE (mismo dato, archivo fijo con sha256).
3. **Publicar población al visor**: por comuna precalculada (15 kB) o por manzana recortada
   (0,7 a 6,1 MB), y con qué criterio a la vista (se publica siempre el rango).
4. **Tsunami**: GeoIDE tiene un servicio de inundación por tsunami para cuatro comunas
   costeras (F-208, F-280). riesgomapas es fluvial; ¿entra como capa aparte o no?
5. **Publicar la rama**: sigue sin merge a `main`.

### Prompt para abrir la próxima sesión

> Estoy en `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas`. Lee
> `CLAUDE.md`, `REGLAS.md`, la primera sección de `docs/PROXIMA_SESION.md` y
> `docs/auditorias/2026-11-15/SINTESIS.md`. Verifica que la rama esté al día con `origin`.
> Las decisiones que tomé sobre la lista «Decisiones que son de Nicolás» son: [completar].
> Con eso, arma un plan por familia contra el código de hoy (GUIA_MAESTRA_AUDITORIAS.md
> §6: un defecto raíz por plan, medición antes y después, test que falle primero) y
> ejecútalo en paralelo donde las familias no toquen los mismos archivos. La familia 3
> (veredicto) toca `web/app.js`; la 1 y la 2 tocan la capa A y `estado-comunas.json`; la 4
> toca los scripts 16 y 19. Nada de guiones largos, y las capas no se fusionan.

---

Lo de abajo es el traspaso anterior. Se conserva entero.

---

## Histórico: estado al 15-nov-2026, mañana: el proyecto despertó con tres novedades que reordenan el plan

El proyecto estuvo dormido dos meses (último commit, 8-sep). Al retomarlo: **64 tests
verdes sin tocar nada** y árbol limpio, así que lo que el traspaso de septiembre afirma
sigue siendo cierto contra el código de hoy.

Lo primero que se hizo fue poner a salvo el trabajo: había **45 commits locales sin
subir** y `origin/main` seguía en el 12 de agosto. Tres meses de trabajo existían solo
en un disco. La rama `visor-simple-y-laminas-vectorizadas` ya está en GitHub con
upstream configurado (132 archivos, 30.394 inserciones), revisada antes de empujar: sin
credenciales, sin archivos sobre 5 MB, y el zip del paquete y el censo correctamente
ignorados. **`main` no se tocó**, así que la decisión de publicar sigue pendiente.

### 1. El practicante entregó su informe, y hay que pedirle los datos

`ANALISIS_MALLECO_FINAL.docx` de Sebastián Ignacio Catalán Mancilla, fechado el
13-nov-2026. Hizo con nuestro paquete exactamente el análisis que a riesgomapas le
falta, y en algunas cosas fue más lejos:

- **Vectorizó siete comunas** (Angol, Collipulli, Los Sauces, Lumaco, Purén, Renaico y
  Traiguén) partiendo de los documentos que `TAREAS.md` le priorizó. Nosotros teníamos
  tres láminas de una sola comuna.
- **Amplió a tres peligros**: remoción en masa, inundación y anegamiento. riesgomapas
  está acotado a inundación fluvial.
- **Calculó población expuesta por reparto de área**: habitantes por la fracción de
  superficie de la manzana que cae dentro de la zona. Resultado: **14.158 de 125.584
  habitantes de poblados (11,3 %)**, y Angol concentra el 73 % (10.387 personas,
  20,1 %). Lumaco es el de mayor porcentaje (44,3 %).
- **Hizo el análisis de sensibilidad que el método exige**, y es la parte más honesta
  del informe: según el criterio, Angol va de 2.175 personas (4 %, solo manzanas
  enteramente dentro) a 28.192 (55 %, cualquier manzana que roce la zona). Eligió el
  reparto por área, 10.387, que coincide con el del punto representativo (10.674).
- Cruzó además establecimientos educacionales, de salud, antenas y red vial, y declaró
  sus límites sin adornos: exposición potencial y no riesgo, sin obras de mitigación,
  y los porcentajes entre comunas no son comparables ni son un ranking.

**Lo que falta y hay que pedirle: los polígonos.** En Descargas solo está el `.docx`.
Sin su base georreferenciada no se puede integrar a riesgomapas ni verificar ninguna de
sus cifras. Pedirle el GeoPackage o los shapefiles con la tabla de atributos del Anexo 1,
y si los tiene, el `.points` de cada georreferenciación y el script de Python del cruce.

**La tensión conceptual que hay que resolver antes de integrar**: él construyó una «base
unificada de peligros» y riesgomapas tiene prohibido fusionar capas de evidencia. No es
contradicción automática, porque cada polígono suyo conserva fuente, año y escala, pero
hay que decidir cómo entra: como capa A derivado con su procedencia por polígono, y
nunca como una capa única de «peligro».

### 2. Angol sí está en el vectorial del MINVU, en otro servidor

Esto corrige una conclusión del proyecto. riesgomapas afirma que Angol no tiene ni un
polígono de área de riesgo en el vectorial del MINVU, y ésa fue la razón de vectorizar
sus láminas a mano. Es cierto para el servicio que usamos
(`services3.arcgis.com/.../prc_riesgo_nacional_visor_P`, el agregado nacional) y **falso
para GeoIDE**, otro servidor del mismo ministerio que el practicante citó en su
bibliografía:

    https://geoide.minvu.cl/server/rest/services/IPT/PRC_Araucania/FeatureServer

38 capas, una por comuna, con capas propias de área de riesgo. Medido el 15-nov:

| Capa | Polígonos | Lo que teníamos |
|---|---:|---:|
| `PRC_Angol_Area_de_riesgo` (29) | 81 | 0 |
| `PRC_Collipulli_Area_de_riesgo` (23) | 68 | 38 |
| `PRC_Renaico_Area_de_riesgo` (31) | 20 | 1 |

Traen `ZONA` (AR-1c, AR-2a), `NOM` («Áreas de Riesgo Inundables o Potencialmente
Inundables», el texto exacto que usamos), `UPERM`, `UPROH`, y los datos del
instrumento: `T_DO` Resolución, `N_DOC` 40, `P_DO` **14/10/2022**.

Tres consecuencias:

1. **Responde la pregunta que quedó abierta el 8-sep.** El plano del PRC de Angol
   declara 2026 (su ordenanza) y no se sabía de qué año era la evidencia. GeoIDE dice
   que el instrumento es la Resolución 40 del 14-10-2022.
2. **Es la validación independiente que faltaba** para los 54 polígonos AR-2a que
   derivamos de las láminas, y el IoU de 0,20 contra el clasificador independiente
   seguía sin explicación. Ahora hay con qué contrastar, geometría contra geometría.
3. **El anti-patrón se generaliza**: ya estaba anotado que un catálogo estatal caído no
   prueba que el dato no exista. La variante nueva es que **un servicio del MINVU no
   son todos los servicios del MINVU**. Hay que barrer `geoide.minvu.cl` completo antes
   de volver a declarar que a una comuna le falta su vectorial.

### 3. El censo por manzana ya está descargado, pero no llega al visor

Nicolás propuso agregar la población por manzana del Censo 2024. Ya está:
`data/processed/censo/censo-2024-araucania.geojson`, que produce
`scripts/16_censo_2024.py`. **17.107 polígonos** (12.381 manzanas urbanas y 4.726
entidades rurales), **1.021.433 personas**, y campos que para inundación valen oro:

`n_fuente_agua_rio` (quien saca agua del río pierde el agua potable, no solo la casa),
`n_viv_hacinadas`, `n_mat_paredes_precarios`, `n_tipo_viv_mediagua`, `n_edad_60_mas`,
`n_edad_0_5`, `n_discapacidad`, `n_jefatura_mujer`, `n_hog_allegados`,
`n_distrib_agua_acarreo`.

**Dos cosas lo frenan.** Pesa **69,8 MB**, y el visor tiene que funcionar offline en un
celular de gama baja, así que hay que decidir qué se publica (agregado por manzana
recortado a las manchas, teselas vectoriales, o precalculado). Y hoy el cruce es solo
**agregado por comuna** en `estado-comunas.json`: dice que Angol tiene 52.605 personas
y 495 hogares con agua de río, pero no cuántos de ellos están **dentro** de la mancha.
Ésa es la brecha de lógica central del visor, y es la misma que el practicante resolvió
para su informe.

Nicolás también pasó la **fuente oficial del INE** en GPKG, que no es la que usamos
(nosotros vamos al servicio de Esri Chile). Responde 200, pesa 40,1 MB y está
actualizada a diciembre de 2025:

    https://storage.googleapis.com/bktdescargascenso2024/Cartografia/GPKG/Cartografia_censo2024_R09.zip

Vale compararlas antes de elegir: la del INE es fuente primaria y la de Esri trae los
microdatos. Descargarla en carpeta propia y vacía, como dato no confiable.

## Lo que sigue pendiente de antes

1. **Regenerar la capa B.** El total ya está bien (5.082 ha, la unión). Lo que exige
   volver a bajar los rásters: `make_valid` al vectorizar (585 de 1.075 polígonos
   inválidos en origen, 0 en lo que se entrega) y medir el enriquecimiento sobre lo
   publicado y no sobre la máscara ráster.
2. **Cuatro polígonos sin año** en la capa A: Loncoche (dos sectores), Nueva Imperial y
   Pucón. Ahora hay dónde buscarlo: GeoIDE trae `P_DO` y `N_DOC` por comuna.
3. **La cola de validación en campo** (C-01 a C-13 del informe del 6-sep).
4. **Publicar**, que sigue siendo decisión y no tarea: falta hosting, gzip, y
   geocodificador y teselas propios. Hoy usa Nominatim y el servidor de OSM, que no
   admiten tráfico de producción.
5. **Deuda de estilo**: los documentos del paquete del practicante tienen guiones
   largos, contra la regla del workspace. `grep -c "—"` tiene que dar 0 en cada `.md`
   antes de entregar, y los `.docx` se regeneran con el script 20.

## Prompt para abrir la próxima sesión

Copiar y pegar todo lo que sigue.

> Estoy en `C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas`. Lee
> `CLAUDE.md`, `REGLAS.md` y la primera sección de `docs/PROXIMA_SESION.md` (estado al
> 15-nov-2026). Lo que te pedí en la sesión anterior, con mis palabras:
>
> 1. «Revisa el estado de este proyecto, ¿hay sesiones de él que sean más nuevas?»
> 2. «Realiza una auditoría sobre la lógica que tenemos y revisa si podemos mejorarla.»
> 3. «También buscamos mejoras en el mismo dashboard. Dime cuáles crees que son los
>    objetivos.»
> 4. «Analiza si hacemos todo esto en esta o en una nueva sesión.»
> 5. «Acá hay una información que podría ayudar, agrégala: la población por manzana
>    censal del último censo»:
>    `https://storage.googleapis.com/bktdescargascenso2024/Cartografia/GPKG/Cartografia_censo2024_R09.zip`
> 6. «Dejé un informe en Descargas, `C:\Users\nmend\Downloads\ANALISIS_MALLECO_FINAL.docx`,
>    del practicante que trabajó con nosotros para hacer algo similar pero solo para
>    Malleco.»
> 7. «Continúa con todo de forma paralela si es posible.»
>
> Los puntos 1, 3 y 4 ya quedaron respondidos en el traspaso: no hay sesiones más nuevas,
> los objetivos están escritos, y se decidió esta sesión nueva. Verifica que siga siendo
> cierto (`git log`, `git status`, que la rama esté al día con `origin`) y sigue con lo
> demás.
>
> **El plan que quedó listo para ejecutar**, en tres frentes disjuntos y en paralelo con
> subagentes (la sesión anterior no tenía herramienta para abrir sesiones, y los
> subagentes además dan el contexto limpio que la guía exige):
>
> - **Frente A, auditoría de la lógica del veredicto** (Opus). `evaluar()` y los textos de
>   `web/app.js`: qué capas consulta, cómo combina sin fusionar, qué dice cuando no hay
>   dato, la diferencia entre «no se inunda» y «nadie midió», la banda de borde, y si la
>   lógica sigue siendo la correcta ahora que hay población por manzana y vectorial
>   oficial para Angol. Solo audita. IDs F-100 a F-199.
> - **Frente B, GeoIDE del MINVU** (Sonnet, es el más mecánico). Barrer las 38 capas de
>   `geoide.minvu.cl/server/rest/services/IPT/PRC_Araucania/FeatureServer`, inventariar
>   qué hay por comuna y qué es hídrico, y el contraste geometría contra geometría entre
>   los AR-2a de `PRC_Angol_Area_de_riesgo` y nuestros 54 AR-2a derivados de las láminas
>   (IoU, área, desplazamiento). Eso cierra el IoU de 0,20 que quedó sin explicar. No
>   toca la capa A publicada. IDs F-200 a F-299.
> - **Frente C, población expuesta espacial** (Opus, es el más delicado de método). Cruce
>   del censo que ya está en `data/processed/censo/censo-2024-araucania.geojson` contra
>   cada capa de evidencia **por separado**, con los cuatro criterios de sensibilidad del
>   practicante (manzana entera dentro, punto representativo, reparto por área, cualquier
>   intersección), piezas sin traslape, y los campos de vulnerabilidad (agua del río,
>   hacinamiento, mayores de 60, discapacidad). Comparar además la fuente del INE del
>   punto 5 contra la de Esri que usamos, descargándola en carpeta propia y vacía como
>   dato no confiable. No publica al visor. IDs F-300 a F-399.
>
> Reglas para lanzarlos, de `GUIA_MAESTRA_AUDITORIAS.md` (léela antes, §5 sobre todo):
> el bloque de `docs/_prompts/PREAMBULO-AUDITOR.md` se pega **entero** en cada prompt, sin
> resumir; cada frente escribe sus instrumentos en `tools/auditoria/` con nombres que no
> choquen y con `--control`; los informes van a `docs/auditorias/<fecha de hoy>/`; los
> hallazgos los verifica después **otro** agente con contexto limpio, que escribe sus
> caminos de ruptura antes de leer el informe. Usa los modelos que correspondan a cada
> tarea, sin abusar del más caro.
>
> Del practicante: solo dejó el `.docx`, sin polígonos. Recuérdame pedirle el GeoPackage
> con la tabla del Anexo 1, los `.points` y el script del cruce. El informe no se sube al
> repositorio, que es público y el documento es suyo: se lee desde Descargas.
>
> Nada de guiones largos en lo que escribas, y las capas de evidencia no se fusionan.

---

Lo de abajo es el traspaso anterior. Se conserva entero: saber qué se creía antes es
lo que caza los falsos positivos.

---

## Histórico: traspaso del 7-sep-2026

## Estado al 7-sep-2026: el ciclo de arreglo de la auditoría está hecho

**Verde y árbol limpio**: 64 tests · 151 comprobaciones de datos con 2 hallazgos medios
declarados · **285** comprobaciones en navegador real (eran 273; las 12 nuevas son las que
faltaban para que el defecto grande no pudiera volver a pasar).

**Lo que se arregló**, en once commits, cada uno con su medición antes y después. El informe
completo de la auditoría sigue en `docs/auditorias/2026-09-06/INFORME.md` y su numeración F-xx
es la que usan los mensajes de commit.

- **El veredicto miraba cuatro de las siete capas que el visor dibuja** (F-01). La capa
  derivada, el modelo del GORE y el JRC no entraban. Un vecino de Angol dentro del AR-2a de su
  plan regulador vigente leía «no cae dentro de un área de riesgo»: Angol y Curarrehue no
  tienen ni un polígono en el vectorial del MINVU, así que ésa era su única evidencia
  normativa. Ahora entra, con bloque propio, sello «trazado derivado» en texto y los metros de
  incertidumbre del borde.
- **Los cuadros de la leyenda se publicaban como territorio** (F-03): 6,1 y 5,6 ha de «Alto» y
  «Medio» sobre un potrero al sur de Angol. Se declara la caja de leyenda y se excluye.
- **La limpieza por grosor mordía el borde y corría la mancha** (F-04). La apertura con núcleo
  par desplazaba todo 1 px al sureste y se comía el 25 % de «Alto» de Angol. Se cambió por
  apertura por reconstrucción: IoU contra la lámina de 0,70 a 0,84 en Angol y de 0,83 a 0,96 en
  Catripulli, desplazamiento del control sintético de 5,23 m a 0,04 m.
- **Faltaba media Angol** (F-05): el plano del PRC son dos pliegos y sólo estaba vectorizado
  uno. Al cargar el segundo, los tres puntos crónicos «Alto» de SENAPRED que estaban a 1,1-1,3
  km del AR-2a caen **dentro**. RMSE 1,22 m con 4 grados de libertad.
- **Sin señal el service worker servía `index.html` como si fuera un plano** (F-06), y el botón
  decía «Plano cargado». Y **la advertencia «no significa que acá no se inunde» nunca viajaba**
  en el texto que se reenvía (F-07), por leer un campo que no existe.
- **A tres metros del borde el visor decía «sin registros»** (F-09) mientras el sitio pide
  «mira la mancha, no su borde». Hay banda de borde con los dos números, y se usa la precisión
  que informa el GPS.
- La comuna se atribuía por el punto crítico más cercano a cualquier distancia (F-10): Temuco
  salía como Padre Las Casas. Una entrada ausente publicaba un inventario falso en silencio
  (F-12). La capa A tenía un duplicado exacto, tres canales fuera del filtro y un año perdido
  (F-14). La capa B sumaba órbitas que se solapan (F-15).

**Lo que queda pendiente y por qué:**

1. **Regenerar la capa B.** El total ya no está mal: se recalculó la unión sobre la huella
   que está en disco —`tools/auditoria/indice_sar_es_la_union.py`, con su control positivo— y
   el índice publicado declara 5.082 ha en vez de 5.776. Lo que sigue pendiente exige volver a
   bajar los rásters: aplicar `make_valid` al vectorizar (585 de 1.075 polígonos son inválidos,
   sin efecto medido en el visor) y medir el enriquecimiento sobre lo publicado y no sobre la
   máscara ráster.
2. **Cuatro polígonos sin año** en la capa A: Loncoche (dos sectores), Nueva Imperial y Pucón
   no están en el Atlas de CIGIDEN. El año hay que sacarlo del decreto.
3. ~~**El «Medio» de Angol se reconoce mal**~~ — **medido el 8-sep, no era un defecto.** El
   color declarado `(0,114,255)` está a **3,6 unidades RGB** del que la lámina usa de verdad
   `(0,112,252)`; el «Alto», a 4,6. Los 54 de la sospecha original venían de un muestreo que
   confundía la nube de «Alto» con la de «Medio»: son las dos únicas manchas azules de la
   lámina y están a 99 unidades una de otra, así que un radio de búsqueda generoso alrededor
   de «Medio» devuelve el dominante de «Alto», que es siete veces más numeroso.
   `tools/auditoria/color_declarado_vs_lamina.py` asigna cada píxel a la clase declarada más
   cercana ANTES de muestrear, y así ninguna clase puede contestar por otra. El IoU de 0,20
   contra el clasificador independiente sigue abierto, pero ya no se explica por el color.
4. **La cola de validación en campo** (C-01 a C-13 del informe) sigue abierta: son las
   preguntas que sólo se responden mirando el terreno, la ortofoto o el documento.

**El paquete de Malleco para el practicante está generado** con los arreglos ya aplicados:
`data/processed/paquete_malleco/` — 12 capas en un GeoPackage, con la procedencia embebida capa
por capa, las tres láminas derivadas de Angol (150 polígonos) con su `estado_tramite` y su
incertidumbre en metros, y `TAREAS.md` priorizado por comunas con gente y registro de
inundación pero sin cartografía: Los Sauces, Curacautín, Victoria y Ercilla no tienen nada. Se
regenera con `python scripts/20_paquete_practicante.py --provincia Malleco`.

**Lo siguiente es una decisión, no una tarea**: publicar. Falta hosting, gzip, y geocodificador
y teselas propios — hoy usa Nominatim y el servidor de OSM, cuyas políticas no admiten tráfico
de producción.

Lo de abajo es el traspaso anterior (9-ago-2026); sigue vigente como contexto.

---

Estado al **9-ago-2026**. Copiar y pegar la sección de abajo al abrir la próxima
sesión.

---

Estoy trabajando en `Volcanologia/riesgomapas/`: un visor abierto de exposición a
inundaciones para La Araucanía. Lee primero `README.md`,
`docs/INVENTARIO_FUENTES.md` y `docs/PROPUESTA.md`.

## Lo que ya está hecho (no rehacer)

Arquitectura: **cuatro capas de evidencia separadas y etiquetadas** (A normativo /
B observado / C modelado / D operacional), **nunca fusionadas en un índice único**.

| Capa | Estado | Cifras |
|---|---|---|
| **A · Normativo** | ✅ | 63 polígonos de área de riesgo por inundación (MINVU, vectorial abierto) + **24 planos de PRC georreferenciados** desde su grilla UTM impresa, error < 2 m |
| **B · Observado** | ✅ | **5.082 ha** de huella observada —la unión de 3 órbitas que se solapan; su suma daría 5.776— sobre 17.382 km² mirados, **sin ninguna cuenta** |
| **C · Modelado** | ✅ | 6 períodos de retorno del JRC (2016, ~1 km) |
| **D · Operacional** | ✅ | 1.374 puntos críticos SENAPRED, **440 de inundación fluvial** (211 crónicos) + 15 campamentos con 537 hogares en área de riesgo |

Además:

- **Índice de 5.991 documentos** del registro EAE nacional (411 de La Araucanía,
  todos escaneados) + **97 documentos** cosechados de los 32 sitios municipales.
- **Catálogo público** en `web/documentos.html`: **354 documentos, 224 láminas,
  25 comunas**, con enlace directo a la página del PDF (`...#page=13`).
  20 de las 32 comunas tienen al menos una lámina localizada.
- **Frontend estático + PWA offline**, rediseñado: paleta anclada en cartografía
  de riesgo, cifras calculadas de los datos, buscador con sugerencias que
  funcionan sin señal.
- Todo dato publicado lleva **fuente y año pegados a cada geometría**; el año
  nunca se inventa (va «no declarado por la fuente» cuando corresponde).
- **63 tests unitarios** + **273 comprobaciones end-to-end** en navegador real
  (`python tests/auditoria_e2e.py`), sobre escritorio claro, oscuro y celular.
  ⚠️ Al integrar la capa B la auditoría daba **108/108 sin mirarla ni una vez**:
  si se agrega una capa, hay que agregarle comprobaciones o su verde no dice nada.

## La capa B no estaba bloqueada — corrección del 9-ago-2026

Este documento decía que la capa B requería credenciales de Copernicus Data
Space. **Eso era cierto de CDSE, no del dato.** El error de razonamiento vale más
que el dato: se anotó «requiere credenciales» como una propiedad del *producto*
cuando era una propiedad de *un proveedor*. El mismo Sentinel-1 se distribuye por
varios espejos con políticas de acceso distintas.

Las tres piezas, todas verificadas leyendo bytes reales, sin ninguna cuenta:

1. **El catálogo de CDSE responde anónimo.** El endpoint OData
   `catalogue.dataspace.copernicus.eu/odata/v1/Products` contesta consultas sin
   token; sólo la *descarga* exige OAuth. El pipeline usa el STAC de Microsoft
   Planetary Computer, que también es anónimo, porque además entrega los enlaces
   a los assets.
2. **Los píxeles salen por Microsoft Planetary Computer.** La colección
   `sentinel-1-grd` se firma con un token SAS que entrega
   `planetarycomputer.microsoft.com/api/sas/v1/token/sentinel1euwest/s1-grd`
   **sin autenticación**. Los assets `vv`/`vh` son COG: un `Range: bytes=…`
   devuelve una ventana espacial sin bajar la escena de ~1 GB.
3. **La anotación SAFE completa está en el mismo contenedor.** Es lo que permite
   calibrar de verdad: `annotation/calibration/calibration-iw-vv.xml` trae la LUT
   de `sigmaNought`, así que se llega a σ⁰ absoluto y no a números de sensor sin
   unidad.

Salvedades reales: el token SAS **caduca en ~1 hora** —hay que re-firmar dentro
del bucle, no al principio— y hay límite de tasa para anónimos. La colección
`sentinel-1-rtc`, ya corregida por terreno, **sí** exige cuenta: con GRD hay que
hacer la geocodificación uno mismo.

> **Regla que queda**: antes de anotar un dataset como bloqueado por credenciales,
> recorrer los espejos (CDSE, Planetary Computer, AWS Open Data, ASF) y probar una
> **lectura real de bytes**, no la existencia del registro.

### Lo que costó caro, y no hay que volver a pagar

Los dos falsos positivos grandes **no se ven en el total: se ven en la
distribución espacial**. Los dos casi se publican.

1. **Nieve húmeda.** La primera corrida declaró 1.252 km². El 74,7 % caía en la
   franja cordillerana. En banda C la nieve mojada es radiométricamente
   **indistinguible** del agua: ningún umbral la separa, sólo la geomorfología.
2. **El océano.** Después de filtrar la nieve, una órbita seguía declarando
   903 km²: altitud mediana **0 m**, 98 % a menos de 1 km de agua permanente. El
   mar liso en la pasada vespertina contra el mar picado de las referencias
   matinales. Aportaba **871 de esos 903 km²**.

Los dos se descartan con el DEM **Copernicus GLO-30** (pendiente ≤ 5°, altura
entre 0,5 y 1.200 m), que también es COG público sin credenciales.

Tercer error, de otra familia: el umbral de agua se derivaba del **percentil 90**
del agua permanente. Esa cola brillante es agua rugosizada por viento —erosionar
la máscara tres veces no la mueve—, así que el umbral quedaba tan permisivo como
el agua peor comportada de la escena. Va en la **mediana**.

Y uno de infraestructura: con el disco lleno quedó un **GeoTIFF truncado pero
presente**, y la corrida siguiente lo dio por bueno. Ahora la caché se valida
leyendo las esquinas. Ojo: **Windows Storage Sense borra `%TEMP%`** cuando el
disco se llena — se llevó dos logs y el Chromium de Playwright a mitad de sesión.

**Verificación** contra los puntos críticos hídricos de SENAPRED, que no
participaron en la derivación: **×2,8 de enriquecimiento** a 300 m (55/371 contra
390/7.420 al azar), ~8 σ. La cifra era ×1,7 mientras la capa D mezclaba desborde
de cauce con drenaje urbano: los puntos de colector, que el radar no puede ver,
diluían la verificación de nuestra propia capa.

## Lo que sigue, por valor

1. **Georreferenciar el Catastro de Anegamientos de Temuco.** Es el caso que
   motivó el proyecto y el de mayor población afectada. Está en el Estudio de
   Aguas Lluvias, **página 13**, como figura rasterizada sin grilla: requiere
   puntos de control a mano en QGIS y `04_georreferenciar.py`, que ya lee el
   formato `.points`.

2. **OCR de márgenes** para los 25 planos rechazados por grilla vectorizada
   (Purén, Collipulli, PRI Villarrica–Pucón, entre otros). Verificado en Purén:
   la capa de texto del PDF sólo contiene `1976`, `1992` y `2026`; la grilla se
   ve al renderizar pero es dibujo. Habría que renderizar las franjas de margen,
   pasarles OCR y alimentar el mismo `08_georreferenciar_grilla.py`.

3. **Los vacíos comunales — actualizado 24-ago-2026, quedan 11.**

   Dos cosas los redujeron. Ver §6bis y §4.3 del inventario.

   **(a) El cosechador municipal preguntaba por un solo marco legal.** Un
   municipio publica la misma amenaza bajo tres leyes con vocabularios que no
   comparten ni una palabra: plan regulador (Ley General de Urbanismo), **Plan
   Comunal de RRD (Ley 21.364)** y **PACCC (Ley 21.455)**. `12_cosechar_municipios.py`
   sólo tenía el vocabulario del primero. Al agregar los otros dos aparecieron
   **40 documentos**, casi todos de 2024-2026 y por tanto posteriores al registro
   EAE: el índice municipal pasó de 140 a **173 documentos** y de 70 a **80
   láminas**. **Renaico, Villarrica y Lonquimay** ganaron cartografía.

   **Lo mejor: Curarrehue.** Su Plan RRD de diciembre-2025 trae la «Zonificación
   de áreas inundables de Catripulli» —susceptibilidad y riesgo de inundación,
   con grilla UTM impresa, lista para `08_georreferenciar_grilla.py`—. Viene del
   levantamiento de riesgos del PRC: **el estudio del plan regulador llegó antes
   por la vía del plan de desastres que por el registro EAE**. Ése es el patrón a
   explotar, no la excepción.

   **(b) ARClim cubre cinco de las siete comunas sin documento**, incluida
   **Padre Las Casas**. Ver el punto 5.

   - **Sin ningún documento (7)**: Cholchol, Loncoche, Melipeuco,
     **Padre Las Casas**, Perquenco, Ercilla, Los Sauces. De ésas, ARClim cubre
     cinco; **sólo Ercilla y Perquenco quedan sin ninguna fuente**.
   - **Con documentos pero sin cartografía (4)**: Carahue, Lautaro, Curacautín,
     Victoria. El plan de RRD de Lautaro se revisó página a página: es texto y
     tablas, no tiene mapas.

   ⚠️ **Punto ciego confirmado del escáner de láminas**: exige vocabulario
   hídrico en la **capa de texto**. La lámina del PACCC de Collipulli es un PDF
   aparte, A3, con el texto convertido a trazos — cero caracteres extraíbles, así
   que es invisible para el índice. Es justo el formato más valioso. Falta una
   segunda vía que detecte lámina por **geometría de página** (A3/A2 apaisado,
   miles de objetos vectoriales, poco o nada de texto) y no por vocabulario.

   **Padre Las Casas es la prioridad**: 76.000 habitantes, 54 puntos críticos de
   inundación y **38 crónicos —el máximo de la región**— y cero documentos. Su
   PRC rige desde 1984, de cuando era un barrio de Temuco, y por eso nunca pasó
   por el registro EAE; en marzo de 2025 se anunció que tendrá el primero propio.
   Su sitio no expone API de WordPress. La vía realista es **pedirlo al
   municipio** o esperar a que el nuevo PRC entre a EAE.

   Verificado que Melipeuco, Perquenco y Renaico **sí tienen API y miles de
   archivos**, pero ninguno de planificación territorial: no es que el cosechador
   falle, es que no los publican.

4. **Publicar.** Falta decidir hosting (Cloudflare / GitHub Pages), asegurar que
   sirva gzip (1,9 MB en crudo → 397 KB comprimido) y montar geocodificador y
   tiles propios: hoy usa Nominatim y el servidor de teselas de OSM, cuyas
   políticas de uso no admiten tráfico de producción.

5. **Decidir si ARClim entra al visor. Es una decisión, no una tarea.**

   `scripts/17_arclim_desbordes.py` ya deja **46 sitios de desborde de río** de
   La Araucanía en `data/processed/arclim/`, con río asociado, estaciones DGA e
   índices de exposición, vulnerabilidad y riesgo para T=25/50/100 en presente y
   proyectado a 2035-2065. Cubre **26 de 32 comunas**, entre ellas cinco que no
   tienen ni un documento.

   Lo que hay que resolver antes de publicarlo: **es un punto por localidad con
   un índice adimensional, no una mancha de inundación.** El visor existe para
   responder «¿se inunda donde vivo?», y este dato no puede responder eso. Un
   punto rojo sobre el nombre de un pueblo se lee como si lo hiciera. O se
   presenta de una forma que no admita esa lectura, o no entra.

   Y si entra, **hay que agregarle comprobaciones a `auditoria_e2e.py`**: ya pasó
   con la capa B que la auditoría diera 108/108 sin mirarla ni una vez.

   ⚠️ Dos cosas de la fuente, ya verificadas y codificadas en el script: el
   índice de amenaza **presente** es una constante nacional (0,4/0,6/0,8 según el
   período de retorno) y no mide nada local — se excluye; y las rutas de la API
   van **sin barra final**, al revés de lo que dice su documentación.

6. **Vectorizar láminas: funciona, y ya hay dos.** `scripts/18_vectorizar_laminas.py`
   convierte una figura de peligro impresa en polígonos, leyendo su retícula UTM
   rotulada y clasificando los colores de su leyenda. Es la primera vez que el
   proyecto **produce** una capa en vez de recolectarla.

   | Lámina | Resolución | Resultado | Verificación independiente |
   |---|---|---|---|
   | **Angol** — peligro de inundación, Estudio de Riesgo 2013, p30 | 7,74 m/px | 98 polígonos · 208 ha | los 4 puntos SENAPRED «Alto» a **12-37 m** de la mancha; los 3 «Medio», a 636-716 m |
   | **Curarrehue** — Catripulli, Plan RRD dic-2025, p72 | 5,34 m/px | 39 polígonos · 809 ha | **5 de 6** puntos crónicos dentro o a ≤17 m |

   Los puntos de SENAPRED no participan en la derivación, así que esa separación
   valida a la vez la georreferenciación y el contenido. En Angol, 12-37 m son
   1,5 a 5 píxeles de la figura: es el límite de precisión, no error.

   ⚠️ **Van a `data/processed/laminas/`, NO al visor.** Publicarlas es una
   decisión aparte: son producto **derivado** —la geometría la construimos
   nosotros— y no pueden mezclarse con el vectorial del MINVU, que sí tiene
   efecto legal. Si entran, van como capa propia y con comprobaciones propias en
   `auditoria_e2e.py`.

   **Lo que frena a las demás** (censo con `--censo`, índice en
   `data/processed/laminas/_censo_reticulas.json`):

   - **No hay OCR.** `pytesseract` está instalado pero **el binario de tesseract
     no**, así que los rótulos de la grilla se declaran a mano en
     `config/laminas.yaml`. Detectar dónde está la grilla es automático; saber
     qué dice, no. Instalar tesseract abriría el resto de golpe.
   - **Figuras recortadas sin márgenes.** Purén p10 —«Mapa Riesgo de inundación
     a nivel urbano de Purén y Caupolicán», oct-2025— tiene una retícula regular
     preciosa de 6×4 y **ningún rótulo**: la figura está cortada al marco. Sin
     rótulos no hay georreferenciación, y adivinarlos sería inventar coordenadas.
   - **Una lámina marcada por vocabulario de inundación no siempre es de
     inundación.** Teodoro Schmidt p56 se descartó al leer su página: muestra
     «el riesgo actual asociado a las amenazas analizadas» y en inundación va
     «sin discriminar entre los niveles de peligrosidad». Es multiamenaza.
     **Hay que leer el texto alrededor antes de declarar una lámina.**

   ⚠️ Y una trampa que conviene conocer: la lámina de Catripulli **declara mal su
   propio huso** («UTM, Huso 18 Sur» cuando es 19 Sur; con 18 caería en el
   Pacífico, a 77°O). La verificación de alcance regional del script lo detecta
   sola. No confiar en el recuadro de información cartográfica.

## Antes de buscar fuentes nuevas

Leer **§6b del inventario**: ahí están documentadas las que ya se sondearon y
**no rinden**, con lo que se verificó de cada una — DOH (publica 1 documento en su
CMS), catálogo MINVU (bibliotecario, sin archivos), `repositoriodigital.minvu.cl`
y tienda SERNAGEOMIN (DNS no resuelve), GORE Araucanía (403), SEIA (500).

## Advertencias que no hay que perder

- Proyecto **personal/abierto, sin marca institucional SERNAGEOMIN**. Todo el copy
  y los disclaimers están escritos bajo ese supuesto. Cambiarlo obliga a rehacer
  el encuadre legal y a agregar la ficha de transparencia algorítmica
  (Res. CPLT N°372).
- **Ausencia de dato ≠ ausencia de riesgo.** Está dicho en el frontend; mantenerlo.
- **Correr `tests/auditoria_e2e.py` antes de declarar algo arreglado.** Tres de los
  cuatro hallazgos del primer informe de auditoría eran bugs de la propia prueba.
- **Subir `VERSION` en `web/sw.js` en cada cambio del frontend** (hoy va en v21).
  Sin eso el service worker sirve la versión vieja y los arreglos no llegan.
- Al correr un script sobre una sola comuna o un solo archivo, **verificar que
  fusione y no sobrescriba su índice**. Ese error ya ocurrió tres veces y su
  síntoma es mudo.
- Contacto en terreno sin explorar: **Kimün-Ko (UFRO, Temuco)**, que trabaja en
  alertas hidrometeorológicas para la misma región.

## Cómo levantar todo

```bash
python -m http.server 8788 --directory web
```

`data/raw/` pesa ~2,6 GB y `data/processed/sar/` otros ~800 MB de caché; los dos
están fuera de control de versiones y se regeneran con los scripts 01→14. Lo que el visor consume vive en `web/data/` y **sí** está
versionado.
