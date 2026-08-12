# Continuar riesgomapas — prompt para la próxima sesión

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
| **B · Observado** | ✅ | **5.776 ha** de huella observada en 3 órbitas (16,2 / 15,4 / 26,2 km²) sobre 17.382 km² mirados, **sin ninguna cuenta** |
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
- **60 tests unitarios** + **129 comprobaciones end-to-end** en navegador real
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

3. **Los 12 vacíos comunales.** El barrido automático ya cubrió los 32 sitios.
   - **Sin ningún documento (7)**: Cholchol, Loncoche, Melipeuco,
     **Padre Las Casas**, Perquenco, Ercilla, Los Sauces.
   - **Con documentos pero sin cartografía (5)**: Carahue, Lautaro, Curacautín,
     Renaico, Victoria.

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
- **Subir `VERSION` en `web/sw.js` en cada cambio del frontend** (va en v8). Sin
  eso el service worker sirve la versión vieja y los arreglos no llegan.
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
