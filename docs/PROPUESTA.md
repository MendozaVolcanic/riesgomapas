# Propuesta — visor de inundaciones para Chile

Borrador 1 · 6-ago-2026 · basado en [`INVENTARIO_FUENTES.md`](INVENTARIO_FUENTES.md)

---

## 1. Por qué copiar Chile Preparado sería un error

Chile Preparado funciona para tsunami y volcanismo porque esas amenazas tienen una
propiedad que la inundación **no tiene**: una zonificación binaria, estable y
oficialmente definida. La cota 30 no cambia. La zona de peligro del Villarrica no
cambia. Un polígono, una respuesta: estás dentro o estás fuera.

La inundación fluvial rompe esas tres condiciones:

| | Tsunami / volcán | Inundación |
|---|---|---|
| ¿Hay zonificación nacional oficial? | Sí | **No** (1 cuenca de ~100) |
| ¿Es estable en el tiempo? | Sí (décadas) | No — cambia con obras, sedimentación, uso de suelo |
| ¿La pregunta útil es "estoy dentro"? | Sí | **No** — es "¿cuánto y cuándo" |

Si replicamos el modelo de Chile Preparado terminamos con un visor que, para el 99%
del territorio, tendría que decir "no hay información" — que es exactamente el
problema que queremos resolver.

**El cambio de producto**: pasar de *visor de zonificación* a
**visor de exposición con evidencia declarada y nowcast**.

---

## 2. Arquitectura conceptual — cuatro capas de evidencia

La idea central: para cualquier punto del territorio, responder con **todas** las
fuentes disponibles, cada una **etiquetada por tipo y calidad de evidencia**. No
fusionarlas en un número único. El usuario ve de qué está hecha la respuesta.

| Capa | Qué es | Cobertura Araucanía | Fuente |
|---|---|---|---|
| **A · Normativo** | Área de riesgo de PRC, MAI DGA | 63 polígonos en 12 comunas + 20 planos publicados (de 24 georreferenciados) | Servicio ArcGIS de MINVU + planos del registro EAE |
| **B · Observado** | Huella real de inundación por SAR, con fecha | 3 órbitas sobre el evento de ago-2026 | Sentinel-1 GRD vía Planetary Computer, **sin cuenta** |
| **C · Modelado** | Períodos de retorno 10–500 años | **Total** | JRC GloFAS v2.1 + HAND propio sobre DEM 12,5 m |
| **D · Operacional** | Puntos críticos, nivel de río actual, pronóstico | **Total** | SENAPRED (1.374 pts), DGA HIDROlínea, Flood Hub |

> ✅ **Actualización.** La capa A resultó estar mucho más disponible de lo que
> suponía este documento: MINVU publica los polígonos normativos en vectorial
> abierto (no encerrados en PDFs), y los planos que sí están en PDF traen grilla
> UTM y se georreferencian solos. Ver §5.

> ✅ **Actualización — la capa B está implementada, y sin ninguna cuenta.** Este
> documento asumía Copernicus Data Space o Google Earth Engine, los dos con
> registro. No hacía falta: el catálogo STAC de Microsoft Planetary Computer y su
> firma SAS son anónimos, los assets son COG (se lee una ventana, no la escena de
> 1 GB) y la anotación SAFE completa —incluida la tabla de calibración— está en el
> mismo contenedor. Ver `scripts/14_sar_huella_observada.py` y §5b del inventario.
>
> El error de fondo vale más que el dato, y es **el mismo error que en la capa A**:
> ahí se concluyó «no existe la capa» porque el catálogo oficial apuntaba a un
> servidor caído; acá se concluyó «requiere credenciales» mirando un solo
> proveedor. En los dos casos el dato estaba disponible y lo que fallaba era el
> camino por el que se lo buscó.

**La capa B es el diferenciador.** Ningún visor chileno muestra la huella observada
de inundación. Es gratis, reproducible, tiene fecha verificable y responde a la
pregunta que la gente realmente hace: *"¿acá llegó el agua?"* — no *"¿modelaron que
podría llegar?"*. Y la emergencia del 30-jul al 4-ago-2026 acaba de darnos el evento
de calibración perfecto.

### Cómo se deriva, y por qué así

Para cada **órbita relativa** se compara la pasada posterior al evento contra la
**mediana de cuatro pasadas previas de esa misma órbita**. Emparejar por órbita y
no por fecha no es un detalle de implementación: dos pasadas con geometría de
vista distinta difieren en retrodispersión por el terreno, no por el agua.

Esa elección hace la mitad del trabajo sola. Como la geometría es idéntica entre
las dos fechas, **la sombra de radar y el relieve se cancelan**: son estáticos.
Lo mismo el asfalto liso y cualquier otra superficie que sea oscura siempre. Y el
agua permanente es oscura en las dos fechas, así que no produce caída — el río
estaba ahí antes, y marcarlo como inundación sería el error más vistoso posible.

Se marca agua donde se cumplen cuatro condiciones a la vez: caída ≥ 3 dB respecto
de la mediana previa; valor posterior tan oscuro como el **agua permanente de la
propia escena** (percentil 90, que es una referencia mucho mejor que un umbral de
la literatura: es agua indiscutible vista por el mismo sensor, la misma geometría
y el mismo día); referencia previa estable; y al menos tres observaciones previas.

Se publica además **la cobertura**: dónde el satélite sí pudo mirar. Sin esa capa
el visor mentiría por omisión, porque «no hay huella» se leería como «no se
inundó» cuando puede significar «no se miró».

La capa D ya está publicada, es oficial, es nacional, y nadie la usa así.

### Por qué no fusionar en un índice único

Tentador y equivocado. Un "índice de riesgo 0–100" mezcla evidencia legal (capa A,
que afecta permisos de edificación) con un modelo global de 90 m (capa C, que se
equivoca en cuencas chicas). Si alguien toma una decisión predial con eso, el error
es nuestro. **Separadas y etiquetadas, o no van.**

---

## 3. Qué ve el usuario

No un mapa. Una **respuesta**.

```
📍 Av. Pedro de Valdivia 1234, Temuco

  ⚠️  EXPOSICIÓN ALTA A INUNDACIÓN

  🛰️  El agua llegó hasta acá el 2-ago-2026        [ver imagen satelital]
      También el 21-jun-2023

  📋  El municipio registra 3 puntos críticos a <300 m
      "Colapso colectores de aguas lluvia" — nivel Alto
      Responsable: Dirección de Obras Hidráulicas (MOP)

  📐  Modelo global: dentro de la mancha de 100 años
      (referencial, resolución 90 m — no apto para decisión predial)

  📜  Plan Regulador de Temuco: zona de riesgo por inundación
      Fuente: Estudio Fundado de Riesgos, 2022, esc. 1:20.000
      Georreferenciación: error ±18 m                [ver PDF original]

  🏃  Punto de encuentro más cercano fuera de zona inundable
      Escuela X — 600 m — [cómo llegar]

  📲  [Descargar ficha para WhatsApp]
```

Chile Preparado te entrega una capa. Esto te entrega una decisión, con la evidencia
a la vista y el error declarado.

---

## 4. Plataforma — recomendación

**Sitio web estático + PWA offline. No app nativa, no Streamlit.**

| Decisión | Por qué |
|---|---|
| **Estático (PMTiles + MapLibre)** sobre Cloudflare/GitHub Pages | Costo cero, sin servidor que se caiga justo durante la emergencia. Chile Preparado depende de ArcGIS Online. |
| **PWA con caché offline por comuna** | En la Araucanía rural la conexión se cae *durante* el evento. Un visor que necesita internet en emergencia no sirve. Descargas tu comuna una vez (~5 MB) y funciona sin señal. |
| **Ficha PDF/imagen exportable** | La información de emergencia en Chile rural circula por WhatsApp, no por links. Hay que diseñar para ese canal. |
| **Sin login, sin analytics invasivo** | Barrera de entrada cero. |
| **Mobile-first, gama baja** | El usuario objetivo no tiene un iPhone. |

Streamlit (como en `Valles/`) sirve para el dashboard técnico interno — pero no
aguanta tráfico ciudadano en emergencia ni funciona offline. Recomiendo **dos
frontends sobre el mismo pipeline de datos**: el estático público y, si hace falta,
un Streamlit interno para OVDAS/municipios.

---

## 5. Georreferenciar los PDF — resuelto mejor de lo previsto

> ✅ **Actualización tras la implementación.** Esta sección se escribió asumiendo
> 30–90 minutos de trabajo manual por plancha. Resultó estar equivocada para el
> caso más importante.

**Los planos de anteproyecto de los planes reguladores se georreferencian solos.**
Se dibujan en formato de plóter con la retícula UTM rotulada en los márgenes, y
esos rótulos son texto vectorial con posición exacta dentro del PDF, no una
imagen. El producto cartesiano de las líneas de la grilla entrega decenas de
puntos de control de coordenada exacta.

Resultado sobre La Araucanía: **24 planos georreferenciados sin intervención**
(20 se publican; 4 resultaron ser copias exactas del mismo plano), con error de
ubicación mayoritariamente bajo 20 cm. Ver `scripts/08_georreferenciar_grilla.py`.

Los cuatro controles que decide aplicar antes de dar por bueno un plano importan
tanto como el ajuste, porque el RMSE mide la coherencia interna de la grilla y no
que la grilla sea realmente una grilla:

1. regularidad del paso entre líneas (tolerancia 2%);
2. linealidad valor↔posición (R² ≥ 0,9999);
3. misma escala en X e Y (≤1%);
4. el huso UTM se deduce probando 18S/19S y verificando que el resultado caiga
   dentro de la región — un plano en PSAD56 aterriza ~200 m corrido y esto lo
   detecta.

El ajuste es robusto por RANSAC: en una hoja conviven con la grilla otros números
de 6–7 dígitos, y basta uno para arruinar una regresión ordinaria.

De 33 láminas candidatas, 10 fueron rechazadas por no tener grilla legible. **El
rechazo es el comportamiento correcto.**

### Para las láminas sin grilla, sigue el trabajo manual

Es el caso de las figuras rasterizadas dentro de informes, como el catastro de
anegamientos de Temuco. Ahí sí hay que poner puntos de control a mano, y aplica
el pipeline original:

1. `pdftoppm -r 400 -png` → raster de la lámina
2. Identificar GCPs contra base OSM/ESRI: esquinas de manzanas, cruces de calles,
   puentes. Mínimo 8–12 bien distribuidos, no alineados.
3. `gdal_translate -gcp ...` + `gdalwarp -tps` (thin plate spline — las planchetas
   escaneadas tienen distorsión no afín)
4. **Calcular y publicar el RMSE de cada plancha.** Regla dura:
   - RMSE < 10 m → apto para consulta predial
   - 10–25 m → referencial a nivel de manzana
   - \> 25 m → solo contexto, se muestra difuminado
5. Vectorizar el polígono (manual o clasificación por color) → GeoJSON
6. **Cada polígono lleva procedencia obligatoria**: fuente, año, escala original,
   método, RMSE, enlace al PDF y a la página exacta.

Ese último punto es lo que separa un visor útil de uno peligroso. Nunca mostrar un
polígono sin decir de dónde salió y cuánto se equivoca.

**CRS**: almacenar en EPSG:4326, servir en 3857, trabajar en UTM por huso
(Araucanía cae entre 18S y 19S — el meridiano 72°W parte la región, ojo con
Curarrehue/Pucón).

---

## 6. Alcance del prototipo

**Fase 1 — Araucanía, principales poblados.** Priorización por población × puntos
críticos SENAPRED:

Temuco · Padre Las Casas · Angol · Villarrica · Pucón · Nueva Imperial · Victoria ·
Lautaro · Purén · Carahue · Traiguén · Collipulli · Pitrufquén · Loncoche ·
Curacautín · Teodoro Schmidt · Galvarino · Saavedra

Entrega mínima viable, en este orden:

1. ✅ **D + C nacional** (barato, automático, cobertura total): ingestar los 1.374 puntos
   críticos + recortar JRC GloFAS a la región. Esto solo ya es más de lo que hay hoy.
2. ✅ **B para el evento ago-2026** (alto valor, medio esfuerzo): huella SAR
   Sentinel-1 pre/post del sistema frontal del 30-jul al 4-ago.
   Resultó **más barato de lo previsto**, porque no hizo falta ninguna cuenta.
3. 🔶 **A para 4–6 comunas** (caro, alto valor legal): georreferenciar Temuco,
   Padre Las Casas, Nueva Imperial, Carahue, Angol, Villarrica.
   Hecho para 24 planos por grilla UTM; falta Temuco, que es figura rasterizada.
4. ✅ Frontend + PWA + ficha WhatsApp.

---

## 7. Riesgos y decisiones que hay que tomar antes de codear

### 7.1 Responsabilidad — la decisión más importante

Publicar mapas de inundación que la gente use para decidir (evacuar o no, comprar o
no) tiene consecuencias reales. Y Nicolás trabaja en SERNAGEOMIN, lo que hace
ambiguo si esto es institucional o personal.

Hay que definirlo **antes**, porque cambia el branding, el disclaimer, la validación
requerida y el respaldo jurídico. No se puede resolver después.

### 7.2 Transparencia algorítmica

Según el `CLAUDE.md` de `Volcanologia/`, un proyecto desplegado y público que
clasifica/predice para apoyar decisiones de un sujeto obligado califica como Sistema
de Decisiones Automatizadas bajo la Resolución CPLT N°372. Si esto se publica, hay
que hacer la ficha y aplicar la convención de comentarios.

### 7.3 Limitaciones técnicas que hay que declarar

- **SAR bajo dosel**: la Araucanía tiene bosque denso. Sentinel-1 no ve agua bajo
  copa cerrada → falsos negativos en zonas rurales arboladas.
- **SAR en zona urbana**: el doble rebote de las edificaciones enmascara la
  inundación → subestimación justo donde vive la gente. Mitigación parcial con
  coherencia interferométrica.
- **SAR es una foto, no un máximo** ⚠️ *la limitación que más fácil se olvida*:
  la huella es el estado del terreno **en el instante de la pasada**. El agua que
  subió y bajó entre dos pasadas simplemente no existe para este método. Con
  revisita de 6–12 días por órbita, un evento de cuatro días se muestrea una o dos
  veces. Por eso la capa se rotula con **fecha de pasada**, no con el nombre del
  evento a secas.
- **SAR con viento**: el oleaje capilar rugosiza la lámina de agua y la vuelve
  brillante. Un lago con viento puede pasar por tierra.
- **Sin corrección por modelo de elevación**: no se aplica corrección
  radiométrica por terreno. Comparar dentro de la misma órbita relativa cancela
  la sombra de radar por ser estática, pero en ladera empinada puede quedar
  residuo.
- **JRC GloFAS 90 m**: no modela drenaje urbano ni cuencas <500 km². Los 278 puntos
  críticos de "colapso de colectores" en Araucanía son invisibles para ese modelo.
- **DEM**: ALOS PALSAR 12,5 m y SRTM sobrestiman la elevación bajo vegetación.
  Para HAND hay que usar FABDEM (corregido por dosel) o la corrección se propaga.
- **Puntos críticos SENAPRED**: son puntos, no polígonos, y reflejan dónde el
  municipio *reportó* problemas — hay sesgo de reporte hacia comunas con más
  capacidad técnica.

### 7.4 Riesgo de duplicar esfuerzo

Kimün-Ko (UFRO, en Temuco) ya trabaja en alertas hidrometeorológicas para la región.
Antes de construir, vale una conversación — puede ser aliado en vez de competencia.

---

## 8. Reutilización desde `Valles/`

El proyecto `Valles/` ya resolvió piezas directamente aplicables:

- `08_descargar_senapred.py` / `09_sharding_senapred.py` — ingesta del mismo org
  ArcGIS de SENAPRED (`geoportalonemi`)
- `02_download_dem.py` — descarga de DEM desde AWS S3
- `06_watershed_pysheds.py` — flow tracing D8 (base para HAND)
- `export_geojson.py` — patrón de shardeo por unidad territorial + índice precomputado
- Las dos lecciones de deploy documentadas en su README

No reescribir. Extraer a un módulo compartido o copiar con atribución.
