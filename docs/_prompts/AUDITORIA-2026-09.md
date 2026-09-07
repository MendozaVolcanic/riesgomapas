# Auditoría profunda de riesgomapas — prompt para la próxima sesión (Fable 5.1)

Copiar entero desde la línea siguiente. Escrito el 6-sep-2026 según
`GUIA_MAESTRA_AUDITORIAS.md` y `GUIA_PROMPTING_prompting-claude-fable-5-1.md`.

---

Vas a auditar el proyecto **riesgomapas** (`C:\Users\nmend\OneDrive\Escritorio\claude\Volcanologia\riesgomapas`, rama `visor-simple-y-laminas-vectorizadas`). Estás corriendo en Claude Fable 5.1 y vas a lanzar subagentes: antes de escribir el primer prompt de auditor lee **enteras** estas dos guías y aplícalas —son vinculantes, no sugerencias—:

- `C:\Users\nmend\OneDrive\Escritorio\claude\GUIA_MAESTRA_AUDITORIAS.md` (el preámbulo anti-fabricación se pega ENTERO en cada auditor; cobertura primero; el que verifica no es el que encontró y verifica con contexto limpio; las dos preguntas del instrumento en el encabezado de toda prueba; línea base roja antes del verde).
- `C:\Users\nmend\OneDrive\Escritorio\claude\GUIA_PROMPTING_prompting-claude-fable-5-1.md` (objetivo + límites, no checklist; bloque de autonomía; qué preservar si se compacta; batching de llamadas independientes).

Después reconstruye el estado **desde el sistema, no desde lo que recuerdes**: `git log --oneline -25`, `git status`, `REGLAS.md`, `scripts/ORDEN.md`, `docs/PROXIMA_SESION.md` (sección «Estado al 6-sep-2026»), y corre en la sesión las tres pruebas que hoy están verdes antes de apoyarte en ellas (`python -m pytest tests -q` → 63; `python tests/auditoria_datos.py` → 151 OK, 1 hallazgo medio; `python tests/auditoria_e2e.py` → 273 OK, tarda ~12 min, lánzala en segundo plano). Un verde que no corriste hoy es SOSPECHA, no respaldo.

## Por qué importa

Este sitio le dice a una persona si el terreno que va a comprar, o la casa que ya tiene, está en un área que un plan regulador, un radar, un modelo o un municipio marcó como inundable. Quien sufre un bug no es un desarrollador: es alguien que firma una compraventa mirando un polígono que se dibujó tres metros corrido, o que lee «no cae dentro» porque el borde de una mancha vectorizada a mano pasó por el patio y no por la casa. El proyecto tiene doce reglas escritas en `REGLAS.md` que ya se cumplen en el código; lo que nadie ha verificado es si se cumplen **sobre los artefactos publicados**.

## Objetivo

Dos preguntas, y la segunda es la que más le importa al dueño:

1. **¿Está todo en orden o hay algo que mejorar?** Auditoría profunda por los frentes de §4 de la guía: por uso (cadena promesa → supuesto → control para cada acción visible del visor), por relación (los siete patrones de §1, con los grep declarados), por magnitudes (todo umbral y constante que manda en `scripts/` y `web/app.js`, con sus unidades: píxeles, metros, grados, m², fracciones), y documentación contra realidad (una guía que miente es un bug: README, REGLAS.md, ORDEN.md, docstrings `Salida:`, PROXIMA_SESION.md).

2. **¿Estamos reconociendo bien los polígonos?** Este frente se mide **sobre el artefacto**, no leyendo el código que lo generó (regla 9 de la guía). Lo que hay: tres láminas vectorizadas por `scripts/18_vectorizar_laminas.py` en `data/processed/laminas/` (Angol peligro 2013: 98 polígonos por color, Alto/Medio; Angol PRC AR-2a: 26 por achurado, RMSE 4,94 m con 3 vértices; Curarrehue-Catripulli 2025: 39 por color), fundidas en `web/data/laminas/vectorizadas.geojson`; la capa A oficial del MINVU filtrada a inundación (`web/data/areas-riesgo-inundacion.geojson`, 63 polígonos, 36 de ellos en Collipulli); y el veredicto del visor, un ray-casting propio (`dentroAnillo`, `web/app.js` ~l.146). Lo que **nunca se ha medido** y quiero que se mida:
   - Fidelidad: re-renderizar cada polígono vectorizado sobre la lámina de origen y calcular IoU **por clase**; cuantificar la confusión río↔clase «Alto» (mismo azul, separados sólo por grosor con `ancho_minimo_px: 4`) y cuánta franja de riesgo legítima pero delgada se comió la apertura morfológica.
   - Georreferenciación con evidencia independiente: los 77 puntos críticos de SENAPRED y el modelo del GORE contra cada lámina (ese control fue el que desenmascaró a la lámina de la DGA con 0 de 77 puntos a menos de 300 m). Dos de tres láminas no declaran `rmse` ni `puntos_control` como campo — verificar si la regla 8 de REGLAS.md se cumple de verdad o sólo en el texto de `metodo`.
   - Control positivo y negativo del pipeline: una lámina **sintética** con clases y coordenadas conocidas → ¿el script recupera esas geometrías y esa posición? Una lámina sin riesgo → ¿0 polígonos? Sin esos dos controles, ningún IoU cuenta.
   - El ray-casting con multipolígonos y anillos interiores: caso adversarial (punto en un hueco, punto sobre un vértice, punto a 1 m del borde). Y la contradicción del sitio consigo mismo: dice «mira la mancha, no su borde» y a 3 m del borde responde «no cae dentro».
   - La capa A oficial: por qué Collipulli tiene 36 de 63 polígonos; si el filtro «inundación» sobre el universo del MINVU conservó y descartó las clases correctas.
   - Capa B (SAR): falsos positivos de nieve húmeda y océano se detectan mirando **dónde** caen las detecciones (`data/processed/sar/`), no cuántas son.

## Cómo organizarlo

- Auditores en paralelo, uno por frente, disjuntos. Censos exhaustivos → subagentes Fable con effort alto para lo semántico; verificación de lo crítico → Opus con contexto limpio (recibe sólo título + archivo:línea, relee, enumera los caminos, re-corre los bancos, pone su gravedad). El verificador funde duplicados y asigna IDs finales; los auditores numeran en rangos provisionales distintos (101+, 201+, 301+, 401+).
- Cada hallazgo: título · archivo:línea · qué pasa · cómo se ve · cómo reproducir · CONFIANZA y GRAVEDAD 1-5 · **salida cruda** del comando junto al número. Sin filtro de severidad en el prompt del auditor. Sección **VERIFICADO LIMPIO** obligatoria: lo que se miró y está bien vale tanto como lo roto.
- Mientras los subagentes corren, sigue trabajando: prepara la lámina sintética y el arnés de IoU tú mismo; no te quedes esperando.
- Batching: antes de cada ronda de llamadas, lista en privado lo que necesitas y pide en una sola respuesta todo lo que no dependa de otro resultado.

## Límites

- **Auditar no es arreglar.** No se toca `scripts/`, `web/` ni `tests/` existentes. Los instrumentos nuevos (lámina sintética, arnés de IoU, casos adversariales del ray-casting) van a `tools/auditoria/` y se commitean el mismo día — un instrumento en un scratchpad se pierde.
- No inventes valores: ni un RMSE, ni un IoU, ni un porcentaje que no salga de un comando corrido en esta sesión. Lo que no pudiste medir es SIN DATO, que no es FALLA ni OK.
- No borres nada que un informe dé por muerto sin `grep` en `tests/`, `scripts/` y `docs/`: el 6-sep una auditoría reportó los shards de `web/data/puntos-criticos/` como «nadie los lee» y `tests/auditoria_datos.py` los usa. Antes de crear un documento, `ls` de la raíz y de `docs/`: ese día se creó un `REGLAS.md` duplicado.
- No crees ramas ni tests permanentes en `tests/`; no cambies `VERSION` en `web/sw.js`.
- Español de Chile en todo lo que escribas (tú, no vos; computador; celular).

## Entregable

`docs/auditorias/2026-09-XX/INFORME.md` con: hallazgos confirmados agrupados **por familia** (un defecto raíz, todos sus síntomas), no una lista de 40 cosas; VERIFICADO LIMPIO; la respuesta directa a «¿reconocemos bien los polígonos?» con los IoU por clase, los controles positivo/negativo y su salida cruda; una **cola de validación en campo** (ID · qué mirar · qué decide · qué desbloquea · de dónde sale); una **tabla de decisiones** para el dueño con opciones y recomendación; y un prompt para la sesión siguiente. Actualiza la sección «Estado» de `docs/PROXIMA_SESION.md` y commitea con un mensaje que describa qué se midió y cómo, no el parche.

## Autonomía

Nadie va a contestar a mitad de la sesión. Si una decisión te bloquea, toma la opción conservadora, déjala anotada en la tabla de decisiones y sigue; termina el entregable completo aunque un frente quede en SIN DATO. Si se compacta el contexto, preserva: las rutas de las dos guías, los tres números de las pruebas de hoy (63 / 151 / 273), la lista de los frentes con su rango de IDs, y el estado de cada subagente (lanzado / informó / verificado). Da un avance en texto visible cada vez que un frente cierre, no sólo al final.
