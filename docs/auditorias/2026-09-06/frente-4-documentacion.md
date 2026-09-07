# Frente 4 — Documentación contra realidad

Auditoría de 2026-09-06, rama `visor-simple-y-laminas-vectorizadas`, commit `b293aad`.
Sesión de sólo lectura: no se tocó `scripts/`, `web/`, `tests/`, `config/` ni `data/`.
Nota de proceso: `docs/auditorias/2026-09-06/` **no existía** al empezar (el prompt decía
que sí); se creó sólo para depositar este archivo, como indicaba la instrucción de
entrega.

Herramientas propias en `tools/auditoria/`: ninguna fue necesaria — todo se verificó con
`python -c` inline y los comandos que ya trae el proyecto (`pytest`, `auditoria_datos.py`).

---

## Tabla 1 — README.md

| Afirmación | Dónde | Cómo se verificó | Salida cruda | Veredicto |
|---|---|---|---|---|
| «63 tests» (implícito por el comando de tests) | README.md:392 | `python -m pytest tests -q --collect-only` | `63 tests collected in 0.56s` | OK |
| «124 polígonos... 63 de inundación» / «63 por amenaza hídrica, 12 comunas» | README.md:33,40-43 | `python tests/auditoria_datos.py` | `[OK] capa A · 124 polígonos, 63 de inundación` / `[OK] capa A · comunas · 13 con área de riesgo, 12 con inundación` | OK |
| «5.776 ha» huella satelital | README.md:34,134 | `auditoria_datos.py` | `[OK] capa B · 1075 polígonos, 5,776.0 ha` | OK |
| Órbitas 16,2 / 15,4 / 26,2 km² | README.md:139-141 | `auditoria_datos.py` | `[OK] capa B · suma por track · 57.8 km²` (16,2+15,4+26,2=57,8) | OK (aritmética consistente; no hay comprobación por track individual en el arnés, así que el desglose exacto por fila queda SIN DATO) |
| «24 planos georreferenciados... 20 se publican; 4 resultaron ser copias» | README.md:62-63 | `auditoria_datos.py` + conteo directo del índice | `[OK] planos · 20 archivos, ninguno duplicado`; `python -c` sobre `web/data/planos/indice.json` → `n planos: 20` | OK (el 20 publicado está confirmado; el total "24" y el "4 duplicados" no se pudieron confirmar de forma independiente — SIN DATO parcial) |
| «354 documentos y 224 láminas en 25 comunas» (catálogo) | README.md:57-59 | no verificado esta sesión | — | SIN DATO |
| «440 son de inundación fluvial... 211 crónicos» | README.md:44-48 | `auditoria_datos.py` | `[OK] alcance de la capa D · 440 puntos, todos fluviales` | OK para 440; 211 crónicos SIN DATO (no hay línea del arnés que lo repita) |
| «Subir VERSION en sw.js en cada publicación» (regla 9) — coherencia con el código | REGLAS.md / README.md:480-483 | `grep VERSION web/sw.js` | `const VERSION = 'riesgomapas-v21';` | OK, la regla se cumple hoy (v21, consistente con lo verde) |

## Tabla 2 — REGLAS.md

| Afirmación | Dónde | Cómo se verificó | Salida cruda | Veredicto |
|---|---|---|---|---|
| §1.5 «el peso legal (vigente/anteproyecto/derivado) va escrito en el dato (`estado_tramite`)» | REGLAS.md:56 | `grep -rl estado_tramite web/data/` + inspección de propiedades de cada GeoJSON de capa A | Sólo `web/data/planos/indice.json` trae `estado_tramite` (proviene de `scripts/10_exportar_superposiciones.py:223`). `web/data/areas-riesgo-inundacion.geojson` (63 polígonos, el vectorial con efecto legal) **no tiene** `estado_tramite` en ninguna propiedad — sus campos son `clasificacion, usos_prohibidos, ..., eae_estado`, que es el estado del **trámite EAE**, no el peso legal vigente/anteproyecto/derivado. `web/data/laminas/vectorizadas.geojson` (163 polígonos, "derivado" por definición) tampoco lo trae. | **MIENTE** (hallazgo 401) |
| §4.5 «antes de declarar algo arreglado, correr `pytest`, `auditoria_datos.py`, `auditoria_e2e.py`» | REGLAS.md:133-137 | se corrieron los dos primeros esta sesión (el tercero estaba prohibido por instrucción, ya corrido hoy) | 63 tests OK; 151 comprobaciones OK, 1 hallazgo MEDIA | OK, la regla describe bien el flujo que existe |
| §5.4 lección DGA — «se dejó documentada para que nadie la reintente» | REGLAS.md:169-184 | ver Tabla 4 (`config/laminas.yaml`) | ver abajo | Coherente con REGLAS.md, pero el archivo de configuración que se supone la deja "sólo documentada" en realidad la deja documentada **dos veces, contradictoriamente** — ver hallazgo 402 |

## Tabla 3 — scripts/ORDEN.md

| Afirmación | Dónde | Cómo se verificó | Salida cruda | Veredicto |
|---|---|---|---|---|
| 07 requiere 05, 12 | ORDEN.md:14 | grep de rutas leídas en `07_buscar_laminas_riesgo.py` | lee `DATA_PROC/eae` (escrito por 05) y `DATA_PROC/municipios` (escrito por 12) | OK |
| 08 requiere 07 | ORDEN.md:15 | grep de rutas leídas/escritas en 07 y 08 | 07 escribe `DATA_PROC/eae/laminas_candidatas_<prioridad>.json` (docstring línea 26); 08 lee `(DATA_PROC/"eae").glob("laminas_candidatas_*.json")` (línea 324) | OK — confirmado el archivo exacto, no sólo la carpeta compartida |
| Los demás pares `Requiere` de la tabla (18↔07, 19↔{01,06,09,10,16,18}, 20↔{...}) | ORDEN.md:9-30 | sólo se hizo el grep superficial de qué `DATA_PROC/WEB_DATA` toca cada script | ver Tabla "grep DATA_PROC/WEB_DATA/DATA_RAW por script" (ejecutada, no reproducida acá por espacio) | SIN DATO — el grep de carpetas no basta para confirmar dependencia de archivo exacto en los pares restantes; no se profundizó por presupuesto de tiempo |
| «Correr 01…20 en orden numérico produce un catálogo vacío» | ORDEN.md:6-7 | no se ejecutó (implicaría correr el pipeline completo) | — | SIN DATO |

## Tabla 4 — config/laminas.yaml (comentarios)

| Afirmación | Dónde | Cómo se verificó | Salida cruda | Veredicto |
|---|---|---|---|---|
| Bloque «❌ RECHAZADA — no se publica. Se deja documentada para que nadie la reintente» (líneas 159-183), inmediatamente seguido por un bloque sin `id:` que dice «La única cartografía de inundación que alcanza a Ercilla y Los Sauces... ⚠️ Es gruesa: 43,8 m/píxel» (líneas 184-192) | config/laminas.yaml:158-192, leído completo | `Read` del archivo completo | Texto citado tal cual arriba | **MIENTE por contradicción interna** (hallazgo 402): un bloque dice que la lámina se rechazó y no se publica, el bloque siguiente la describe en presente como "la única cartografía" disponible, sin ningún `id:` de YAML real que la convierta en entrada activa — es indistinguible, leyendo el archivo, de un resto de una versión anterior a la reversión del commit `af47b56` ("Descartar la lámina de la DGA") |

## Tabla 5 — docstrings de scripts/*.py (Salida / Requiere)

| Afirmación | Dónde | Cómo se verificó | Salida cruda | Veredicto |
|---|---|---|---|---|
| «la capa se etiqueta `A_derivado`» | scripts/18_vectorizar_laminas.py:35 (docstring) | grep de `assert capa_evidencia in (...)` en `scripts/comun.py:290-292`; lectura de `capa_evidencia` real en los 3 GeoJSON de `data/processed/laminas/` y en `web/data/laminas/vectorizadas.geojson` | `comun.procedencia()` sólo admite `A_normativo, B_observado, C_modelado, D_operacional, inventario` — `A_derivado` haría fallar el `assert`. Los 4 archivos leídos traen `"capa_evidencia": "A_normativo"` | **MIENTE, y es más que cosmético** (hallazgo 400 — ver abajo) |
| «Salida: data/processed/laminas/\<id\>.geojson» | scripts/18_vectorizar_laminas.py:47 | `ls data/processed/laminas/*.geojson` | 3 archivos con nombre `<id>.geojson` | OK |
| «Salida: data/processed/eae/laminas_candidatas_\<prioridad\>.json» | scripts/07_buscar_laminas_riesgo.py:26 | grep de escritura en el propio script | coincide con lo que lee `08` (ver Tabla 3) | OK |
| «Salida: data/processed/georreferenciado/\*.tif + \*.json» | scripts/08_georreferenciar_grilla.py:39 | grep `salida = DATA_PROC / "georreferenciado"` línea 353 | coincide | OK |
| Resto de docstrings `Requiere:`/`Salida:` de los 20 scripts | scripts/\*.py | sólo grep superficial de constantes `DATA_PROC/DATA_RAW/WEB_DATA` por archivo (hecho para los 20) | tabla completa obtenida, no se contrastó línea por línea contra cada docstring por presupuesto de tiempo | SIN DATO (parcial — sólo 3 de 20 confirmados a nivel de archivo exacto) |

## Tabla 6 — el texto público (web/index.html, web/app.js)

| Afirmación | Dónde | Cómo se verificó | Salida cruda | Veredicto |
|---|---|---|---|---|
| Comentario de código «cargar 23 imágenes... Son 23 polígonos» sobre los rectángulos de planos | web/app.js:185-190 | conteo real de `web/data/planos/indice.json` | `n planos: 20` (y `auditoria_datos.py`: `[OK] planos · 20 archivos, ninguno duplicado`) | **MIENTE** (hallazgo 403 — comentario de desarrollador desactualizado, no texto que vea el público, pero es la misma cifra "23" que aparece en `docs/PROPUESTA.md`, señal de que ambos quedaron pegados a un estado anterior del dato) |
| Resto del texto visible en `index.html`/`app.js` (cifras de portada, fichas por capa) | web/index.html, web/app.js | grep dirigido a patrones numéricos; no se abrió el visor en navegador esta sesión (instrucción explícita de no correr `auditoria_e2e.py`, que sí lo hace) | grep no encontró más cifras hardcodeadas que las de arriba — los números de portada se calculan de los datos en tiempo de carga, según README.md:518 | OK para "no hay cifras hardcodeadas sospechosas", SIN DATO para "el cálculo en tiempo real da el número correcto" (requeriría abrir el visor) |

## Tabla 7 — docs/PROPUESTA.md, docs/GUIA_PRACTICANTE.md, docs/PRACTICA_PROFESIONAL.md, docs/DIFUSION.md

| Afirmación | Dónde | Cómo se verificó | Salida cruda | Veredicto |
|---|---|---|---|---|
| «63 polígonos en 12 comunas + 23 planos georreferenciados» (tabla de arquitectura, capa A) | docs/PROPUESTA.md:39 | mismo conteo que Tabla 6 | planos reales: 20 (no 23) | **MIENTE / cifra desactualizada** (mismo "23" que app.js — hallazgo 403, mismo origen) |
| «124 polígonos, 13 comunas» (capa A) | docs/GUIA_PRACTICANTE.md:18,40,209 | `auditoria_datos.py` | `[OK] capa A · comunas · 13 con área de riesgo` | OK |
| «Cerrar los 4 polígonos sin año — Loncoche, Nueva Imperial y Pucón» | docs/GUIA_PRACTICANTE.md:332 | lectura directa de `data/processed/areas_riesgo_prc_araucania.geojson` con la misma condición que usa `auditoria_datos.py` (`not anio or "no declarado" in str(anio)`) | `count 5`: Loncoche (2 sectores), Nueva Imperial, Pucón, **Saavedra** (Puerto Saavedra) — coincide exacto con `auditoria_datos.py`: `[MEDIA] capa A — año: 5 de 124 polígonos sin año` | **MIENTE** (hallazgo 404): dice "4" cuando son 5, y omite la comuna Saavedra por completo de la lista de comunas afectadas |
| «19 de las 32 comunas no tienen ningún vectorial de áreas de riesgo» | docs/GUIA_PRACTICANTE.md:346 | 32 (región) − 13 (con vectorial, confirmado en Tabla 1) = 19 | aritmética directa sobre cifras ya verificadas | OK |
| «737 manzanas urbanas y 94 entidades rurales» en Angol | docs/GUIA_PRACTICANTE.md:437 | filtro directo de `data/processed/censo/censo-2024-araucania.geojson` por `NOM_COMUNA=='Angol'` y conteo por `unidad_censal` | `Counter({'manzana_urbana': 737, 'entidad_rural': 94})` | OK, exacto |
| Tabla de capas censales (12.886/691.173, 4.188/312.373, 33/17.887, total 17.107/1.021.433) | docs/GUIA_PRACTICANTE.md:424-428 | conteo total del GeoJSON | `17107` features totales coincide con la fila "Total" de la tabla | OK para el total; los tres subtotales por capa (0/1/2) no se distinguieron en el archivo consolidado (no hay campo "capa" o "tipo" en las propiedades) — SIN DATO para los subtotales individuales |
| «17 de los 30 procedimientos están en comunas sin vectorial, y 15 ya tienen sus láminas localizadas» | docs/GUIA_PRACTICANTE.md:352 | no verificado | — | SIN DATO |
| «102 nombres distintos» en el Atlas de CIGIDEN | docs/GUIA_PRACTICANTE.md:326 | no verificado (fuente externa, no está en el repo) | — | SIN DATO |
| Recuento del docstring de `20_paquete_practicante.py` sobre GeoPackage/CSV truncando `estado_tramite` | scripts/20_paquete_practicante.py:10 | confirma indirectamente que el autor del script sabe que `estado_tramite` existe en **algunos** productos (los planos), consistente con el hallazgo 401 de que NO existe en el vectorial principal | grep ya citado en Tabla 2 | OK como afirmación puntual sobre el campo en general; no contradice el hallazgo 401, lo hace más notable: el propio código sabe que el campo existe para planos y aun así el vectorial de 63 polígonos no lo lleva |
| `docs/DIFUSION.md`, `docs/PRACTICA_PROFESIONAL.md` — resto de cifras y comandos citados | ambos archivos completos, líneas listadas arriba | grep dirigido a comandos `python scripts/`/`python tests/` y a cifras de cobertura | **cero** comandos `python scripts/...` citados en estos dos documentos (no son guías operativas, son de difusión/gestión) | OK — no hay superficie de verificación mecánica en estos dos documentos; ningún hallazgo, tampoco falso positivo |

---

## Hallazgos

### 400 — El docstring de la capa derivada dice una etiqueta que el propio validador rechaza, y la etiqueta real es la de más peso legal

**ARCHIVO:LÍNEA**: `scripts/18_vectorizar_laminas.py:35` (docstring) vs `scripts/comun.py:290-292` (`assert`) vs `web/data/laminas/vectorizadas.geojson` (campo `procedencia.capa_evidencia`, leído completo)

**QUÉ PASA**: el docstring del script que vectoriza láminas impresas dice literalmente «la capa se etiqueta `A_derivado`». Esa etiqueta no existe: `comun.procedencia()` sólo acepta `A_normativo | B_observado | C_modelado | D_operacional | inventario` con un `assert` que haría fallar el script si se intentara. Lo que el pipeline efectivamente escribe — verificado en los 3 archivos de `data/processed/laminas/` y en `web/data/laminas/vectorizadas.geojson` (163 polígonos) — es `capa_evidencia: "A_normativo"`, que es la etiqueta de **mayor peso legal** del sistema (la misma que llevan los 63 polígonos vectoriales de MINVU con efecto jurídico real).

Dentro del mismo bloque de `procedencia` de `vectorizadas.geojson` el texto de `incertidumbre` dice, en la misma respiración: «PRODUCTO DERIVADO: la geometría la construimos nosotros... NO tiene el efecto legal del vectorial del MINVU». Es decir, el propio archivo se contradice: la etiqueta estructurada (`capa_evidencia`) dice `A_normativo`, y la prosa libre al lado dice que no lo es.

**CÓMO SE VE**: cualquier código del frontend, o cualquier practicante, que filtre o coloree por `capa_evidencia == "A_normativo"` para mostrar "esto tiene efecto legal" va a incluir sin darse cuenta los 163 polígonos derivados de láminas impresas por el propio proyecto, que REGLAS.md §1.3 y §1.5 dicen explícitamente que nunca se deben fusionar con lo normativo. Es exactamente el error que el proyecto lleva trece reglas advirtiendo que no hay que cometer.

**CÓMO REPRODUCIRLO**:
```
grep -n "A_derivado" scripts/18_vectorizar_laminas.py
sed -n '290,292p' scripts/comun.py
python -c "import json; d=json.load(open('web/data/laminas/vectorizadas.geojson',encoding='utf-8')); print(d['procedencia']['capa_evidencia']); print(d['procedencia']['incertidumbre'])"
```

**SALIDA CRUDA**:
```
scripts/18_vectorizar_laminas.py:35:   la capa se etiqueta `A_derivado` — nunca se mezcla con el vectorial del MINVU,

scripts/comun.py:290-292:
    assert capa_evidencia in ("A_normativo", "B_observado", "C_modelado",
                              "D_operacional", "inventario"), (
        f"capa de evidencia desconocida: {capa_evidencia!r}")

capa_evidencia real: A_normativo
incertidumbre real (recortada): "PRODUCTO DERIVADO: la geometría la construimos nosotros a partir de una lámina impresa; el organismo NO la publica así. ... NO tiene el efecto legal del vectorial del MINVU."
```

**CONFIANZA**: CONFIRMADO (leí el docstring, el assert, y los 4 GeoJSON con `json.load`).

**GRAVEDAD**: 5 — es exactamente la clase de error que hace que alguien lea "área de riesgo normativa" sobre un polígono que en realidad es una reconstrucción del proyecto desde una figura de PDF, en un visor cuyo propósito es distinguir peso legal.

---

### 401 — `estado_tramite` no está en el dato que REGLAS.md dice que lo lleva

**ARCHIVO:LÍNEA**: `REGLAS.md:56` vs `web/data/areas-riesgo-inundacion.geojson` (propiedades de sus 63 features) vs `web/data/laminas/vectorizadas.geojson` (propiedades de sus 163 features)

**QUÉ PASA**: REGLAS.md §1.5 dice que el peso legal (vigente/anteproyecto/derivado) «va escrito en el dato (`estado_tramite`)». Es cierto sólo para `web/data/planos/indice.json` (los recuadros de planos escaneados, que sí traen `estado_tramite` desde `scripts/10_exportar_superposiciones.py:223`). No es cierto para `web/data/areas-riesgo-inundacion.geojson` — el vectorial de 63 polígonos con efecto legal real, el que más necesitaría distinguir "vigente" — ni para `web/data/laminas/vectorizadas.geojson`, que según la propia regla 1.5 es, por definición, "derivado".

**CÓMO SE VE**: un desarrollador del frontend que busque el campo `estado_tramite` en la capa principal de área de riesgo (63 polígonos) para mostrar el peso legal en pantalla no lo va a encontrar; sólo existe para la capa secundaria de recuadros de planos.

**CÓMO REPRODUCIRLO**:
```
grep -rl "estado_tramite" web/data/
python -c "import json; d=json.load(open('web/data/areas-riesgo-inundacion.geojson',encoding='utf-8')); print(list(d['features'][0]['properties'].keys()))"
```

**SALIDA CRUDA**:
```
web/data/planos/indice.json

['comuna', 'sector', 'zona', 'nombre', 'clasificacion', 'usos_prohibidos', 'usos_permitidos',
 'ordenanza_url', 'ordenanza_url_vigente', 'es_inundacion', 'tipo_hidrico', 'origen_capa',
 'fuente', 'anio', 'eae_procedimiento', 'eae_fecha_ingreso', 'eae_estado', 'anio_fuente']
```
(sin `estado_tramite`; `eae_estado` es el estado del trámite ante EAE, un concepto distinto)

**CONFIANZA**: CONFIRMADO.

**GRAVEDAD**: 3 — no es que el dato mienta al usuario (nada en pantalla dice hoy "vigente" sobre algo que no lo es, por lo que se pudo verificar sin abrir el navegador), pero la regla que se supone que impide justamente ese error no se cumple donde más importa, y contradice a la lección que la propia regla cita como motivo de su existencia (los 20 planos mostrados como "la única capa con efecto jurídico" siendo anteproyectos).

---

### 402 — `config/laminas.yaml` tiene dos versiones contradictorias de la lámina de la DGA, una encima de la otra

**ARCHIVO:LÍNEA**: `config/laminas.yaml:158-192`

**QUÉ PASA**: el archivo trae, en ese orden y sin separación de fecha ni de commit: (a) un bloque que dice «❌ RECHAZADA — no se publica. Se deja documentada para que nadie la reintente», con la evidencia completa del descarte (0/77 puntos SENAPRED cerca, 0,1% de intersección con el modelo GORE); y (b), inmediatamente después, sin ningún separador que indique que es historia superada, otro bloque que empieza «La única cartografía de inundación que alcanza a Ercilla y Los Sauces» y sigue en presente, describiéndola como si fuera parte activa del proyecto, con su propia advertencia de resolución («43,8 m/píxel»). El segundo bloque no tiene ninguna entrada YAML real (`id:`, `pdf:`, etc.) — es sólo comentario — así que no rompe el script, pero si alguien lee el archivo de arriba a abajo (como este mismo prompt de auditoría instruyó hacer) llega a una contradicción sin resolver.

**CÓMO SE VE**: alguien que entra al archivo buscando "¿qué pasó con la lámina de la DGA?" lee primero que se rechazó y luego, dos párrafos después, que es "la única cartografía" de dos comunas — sin saber cuál de las dos afirmaciones es la vigente ni por qué coexisten.

**CÓMO REPRODUCIRLO**: `sed -n '158,192p' config/laminas.yaml` (o ver la cita completa en la Tabla 4 de este informe).

**SALIDA CRUDA**: citada verbatim en la Tabla 4.

**CONFIANZA**: CONFIRMADO (archivo leído completo). El origen probable (que sea un resto sin limpiar de antes de `af47b56`, "Descartar la lámina de la DGA") es SOSPECHA — no verifiqué el diff de ese commit.

**GRAVEDAD**: 2 — no afecta ningún dato publicado (el bloque (b) no tiene `id:`, no se procesa), pero es exactamente el tipo de documentación-que-miente que este frente existe para cazar: confunde a la próxima persona sobre el estado real de una decisión ya tomada.

---

### 403 — El plano cuenta "23" quedó pegado en dos lugares después de bajar a 20

**ARCHIVO:LÍNEA**: `web/app.js:185,190` (comentarios de código) y `docs/PROPUESTA.md:39` (tabla de arquitectura)

**QUÉ PASA**: ambos dicen "23" planos/imágenes donde el dato real —confirmado por `auditoria_datos.py` y por conteo directo de `web/data/planos/indice.json`— es 20. Es la misma cifra en dos archivos no relacionados, señal de que ambos describían un estado del proyecto anterior a que se descartaran los 4 duplicados (README.md sí lo tiene actualizado: "20 se publican; 4 resultaron ser copias exactas").

**CÓMO SE VE**: no es texto que el público del visor vea (son comentarios de desarrollador y un documento de arquitectura interna), pero un desarrollador nuevo que lea el comentario de `app.js` antes de mirar el dato real va a esperar 23 rectángulos y ver 20, y se va a preguntar si faltan 3.

**CÓMO REPRODUCIRLO**:
```
grep -n "23 " web/app.js docs/PROPUESTA.md
python -c "import json; d=json.load(open('web/data/planos/indice.json',encoding='utf-8')); print(len(d['planos']))"
```

**SALIDA CRUDA**:
```
web/app.js:185: // cargar 23 imágenes de ~870 KB para no mostrar nada es lo peor de los dos
web/app.js:190: * Rectángulos con la extensión de cada plano. Son 23 polígonos: se pueden
docs/PROPUESTA.md:39: | ... 63 polígonos en 12 comunas + 23 planos georreferenciados | ...

n planos reales: 20
```

**CONFIANZA**: CONFIRMADO.

**GRAVEDAD**: 1 — cosmético, no llega al usuario final, no afecta ningún cálculo.

---

### 404 — La guía del practicante dice "4 polígonos sin año" y omite una comuna; son 5

**ARCHIVO:LÍNEA**: `docs/GUIA_PRACTICANTE.md:332`

**QUÉ PASA**: la guía dice «Cerrar los 4 polígonos sin año — Loncoche, Nueva Imperial y Pucón no están en el Atlas». La cifra real, verificada con la misma condición que usa `tests/auditoria_datos.py` sobre `data/processed/areas_riesgo_prc_araucania.geojson`, es **5**: Loncoche aparece dos veces (dos sectores, no uno), y falta **Saavedra (Puerto Saavedra)** en la lista de comunas nombradas.

**CÓMO SE VE**: un practicante que siga la guía al pie de la letra completa el año de 4 registros en 3 comunas y da la tarea por cerrada, dejando sin año el polígono de Puerto Saavedra sin saber que existía.

**CÓMO REPRODUCIRLO**:
```
python -c "
import json
d=json.load(open('data/processed/areas_riesgo_prc_araucania.geojson', encoding='utf-8'))
cnt=0
for f in d['features']:
    a=f['properties'].get('anio')
    if not a or 'no declarado' in str(a):
        cnt+=1
        print(f['properties'].get('comuna'), f['properties'].get('sector'))
print('count', cnt)
"
python tests/auditoria_datos.py 2>&1 | grep "capa A .. a.o"
```

**SALIDA CRUDA**:
```
Loncoche Loncoche
Loncoche Loncoche
Nueva Imperial Nueva Imperial
Pucón Pucón
Saavedra Puerto Saavedra
count 5

[MEDIA] capa A — año: 5 de 124 polígonos sin año; el Atlas de CIGIDEN lo tiene para 11 comunas
```

**CONFIANZA**: CONFIRMADO — coincide exacto con el propio arnés de auditoría del proyecto.

**GRAVEDAD**: 2 — no llega al público (es una guía interna de trabajo), pero es un documento operativo que alguien va a seguir literalmente, y deja un vacío de dato sin que quien lo siga se entere de que existe.

---

## VERIFICADO LIMPIO

- **README.md** — cifras de capa A (124/63/12/13 comunas), capa B (5.776 ha), capa D (440 fluviales), planos publicados (20) y VERSION de sw.js (v21) están todas al día. Comando: `python tests/auditoria_datos.py` (151 comprobaciones OK, salida completa arriba) + `grep VERSION web/sw.js`.
- **Conteo de tests**: `python -m pytest tests -q --collect-only` → `63 tests collected`, coincide con lo que dice `docs/PROXIMA_SESION.md` («63 tests»).
- **Comprobaciones de datos**: `python tests/auditoria_datos.py` → `151 comprobaciones OK · 1 hallazgo (0 de gravedad alta)`, coincide exacto con `docs/PROXIMA_SESION.md` («151 comprobaciones de datos»).
- **`scripts/ORDEN.md`**, dependencias 07→05,12 y 08→07: confirmadas por grep de archivo exacto (no sólo carpeta), ver Tabla 3.
- **Censo**: la tabla de capas censales de `docs/GUIA_PRACTICANTE.md` (17.107 features totales) coincide exacto con `data/processed/censo/censo-2024-araucania.geojson`; el desglose Angol (737 manzanas urbanas / 94 entidades rurales) también coincide exacto.
- **`config/araucania.yaml`**: comprobación aritmética «19 de 32 comunas sin vectorial» = 32 − 13 (confirmado en README/auditoria_datos) es consistente.
- **`docs/DIFUSION.md` y `docs/PRACTICA_PROFESIONAL.md`**: no contienen comandos operativos (`python scripts/...`) que verificar mecánicamente; sus afirmaciones son de gestión/difusión, fuera del alcance de un contraste dato-contra-documento. No se encontró ninguna cifra técnica falsa en el barrido dirigido que se hizo sobre ambos.
- **`docs/GUIA_PRACTICANTE.md`**: cifras de capa A (124/13), 19/32 comunas sin vectorial, y censo — todas confirmadas.

## SIN DATO (no se pudo verificar esta sesión, por alcance o presupuesto de tiempo)

- El desglose exacto por track de la capa B (16,2 / 15,4 / 26,2 km²) — el arnés sólo valida la suma (57,8 km²), no cada fila.
- El total real de "24 planos" y el detalle de "4 duplicados" citado en README — sólo se pudo confirmar el subconjunto publicado (20).
- «354 documentos y 224 láminas en 25 comunas» del catálogo (README.md:57-59).
- «211 crónicos» de los 440 puntos fluviales (README.md:47).
- Dependencias `Requiere:` de `scripts/ORDEN.md` para los pares 18↔07, 19↔{01,06,09,10,16,18} y 20↔{...} — sólo se verificó el grep superficial de carpetas, no el archivo exacto como se hizo para 07/08.
- «17 de los 30 procedimientos... 15 ya tienen sus láminas localizadas» (docs/GUIA_PRACTICANTE.md:352).
- «102 nombres distintos» del Atlas de CIGIDEN (fuente externa, no está en el repo).
- Los subtotales por capa censal (0/1/2) de la tabla de `docs/GUIA_PRACTICANTE.md:424-428` — el GeoJSON consolidado no trae un campo que distinga la capa de origen de cada feature, sólo `unidad_censal` (manzana_urbana/entidad_rural), así que no se pudo aislar la fila "Aldeas" (33/17.887) de forma independiente.
- El texto exacto que ve el público en `web/index.html`/`web/app.js` en tiempo de ejecución (portada, fichas por capa) — no se abrió el visor en navegador esta sesión, por instrucción explícita de no correr `auditoria_e2e.py`.
