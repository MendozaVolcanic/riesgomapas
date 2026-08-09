"""Capa B (observada) — huella real de inundación derivada de Sentinel-1.

QUÉ RESPONDE ESTA CAPA, Y POR QUÉ ES LA QUE FALTABA
----------------------------------------------------
Las otras tres capas del visor responden preguntas distintas de la que la gente
hace. La capa A dice qué declaró el plan regulador; la C, qué modeló alguien en
2016 a un kilómetro de resolución; la D, dónde reportó problemas el municipio.
Ninguna dice **hasta dónde llegó el agua**. Esta sí, con fecha y hora de pasada
satelital verificables, y ningún visor chileno la tiene.

CÓMO SE OBTIENE SIN NINGUNA CUENTA
-----------------------------------
Estaba anotado como «bloqueado por credenciales de Copernicus Data Space». Era
cierto de CDSE y falso del dato: el mismo Sentinel-1 se distribuye por varios
espejos con políticas distintas.

  1. El catálogo STAC de Microsoft Planetary Computer responde **anónimo**.
  2. Sus assets se firman con un token SAS que se pide **sin autenticación**, y
     son COG: un `Range: bytes=…` trae una ventana en vez de la escena de ~1 GB.
  3. En el mismo contenedor está la anotación SAFE completa, con la tabla de
     calibración. Eso es lo que permite llegar a σ⁰ físico y no a cuentas de
     sensor sin unidad.

El token **caduca en ~1 hora**: se re-firma dentro del bucle, no al principio.

EL MÉTODO, EN UNA FRASE
------------------------
Para cada órbita relativa se compara la pasada posterior al evento contra la
**mediana de varias pasadas previas de esa misma órbita**, y se marca como agua
lo que cayó al menos 3 dB, quedó tan oscuro como el agua permanente de la propia
escena y venía de una referencia estable. El razonamiento físico y las cuatro
condiciones están en `sar.py`, que es donde vive la lógica probable sin red.

Emparejar por órbita relativa y no por fecha no es un detalle: dos pasadas de
geometría de vista distinta difieren por el terreno, no por el agua.

Salida:
  data/processed/sar/<evento>/<track>/<fecha>.tif   σ⁰ dB por fecha (caché)
  data/processed/sar/<evento>/<track>/estadistica_pre.tif
  web/data/sar/huella-observada.geojson             la huella, capa B
  web/data/sar/cobertura-sar.geojson                dónde SÍ se pudo mirar
  web/data/sar/indice.json                          diagnóstico por track

Uso:
  python scripts/14_sar_huella_observada.py
  python scripts/14_sar_huella_observada.py --bbox -73.2 -39.1 -72.6 -38.6   (prueba)
  python scripts/14_sar_huella_observada.py --verificar
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import warnings
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.control import GroundControlPoint
from rasterio.enums import Resampling
from rasterio.features import shapes
from rasterio.transform import from_origin
from rasterio.warp import reproject
from rasterio.windows import Window

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sar  # noqa: E402
from comun import (  # noqa: E402
    DATA_PROC,
    WEB_DATA,
    cargar_config,
    escribir_geojson,
    get_bytes,
    log,
    post_json,
    procedencia,
    sello,
)

# Config de GDAL para leer COG remotos sin desperdiciar peticiones.
# `GDAL_DISABLE_READDIR_ON_OPEN` es la importante: sin ella GDAL intenta listar
# el directorio del blob en cada apertura, que acá son cientos de peticiones
# inútiles contra un contenedor que ni siquiera permite listar.
ENTORNO_GDAL = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MULTIRANGE": "YES",
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_RETRY_DELAY": "2",
}

# Filas por bloque al apilar. 512 × 6.223 × 5 fechas × 4 bytes ≈ 64 MB: el
# apilado no puede cargar la región entera cinco veces en memoria.
FILAS_BLOQUE = 512

# Decimación para la capa de cobertura. No hace falta al detalle del dato: sólo
# responde «¿este punto fue mirado por el satélite?», y a 16 pesaba 600 KB —
# desproporcionado frente a los 1,1 MB de la huella, que es el dato de verdad, en
# un sitio que tiene que descargarse por una conexión mala y quedar en caché.
DECIMACION_COBERTURA = 32


# ------------------------------------------------------------------- catálogo

class Firma:
    """Token SAS anónimo, re-firmado antes de que caduque.

    El token dura ~1 hora y una corrida completa se pasa de eso. Si se firma una
    sola vez al principio, la corrida muere a mitad de camino con un 403 que se
    lee como «no tengo permiso» cuando en realidad es «se me venció».
    """

    def __init__(self, url: str, margen_s: int = 600):
        self.url = url
        self.margen_s = margen_s
        self._token: str | None = None
        self._vence = 0.0

    def token(self) -> str:
        if self._token is None or time.time() > self._vence - self.margen_s:
            datos = json.loads(get_bytes(self.url))
            self._token = datos["token"]
            vence = datos.get("msft:expiry")
            self._vence = (
                datetime.fromisoformat(vence.replace("Z", "+00:00")).timestamp()
                if vence else time.time() + 3000
            )
            log(f"  token SAS firmado, vence {vence}")
        return self._token

    def firmar(self, url: str) -> str:
        return f"{url}?{self.token()}"


def buscar_items(cfg_sar: dict, bbox: list[float], desde: str, hasta: str) -> list[dict]:
    """Consulta el STAC paginando por los enlaces `next` que devuelve el servicio."""
    cuerpo = {
        "collections": [cfg_sar["coleccion"]],
        "bbox": list(bbox),
        "datetime": f"{desde}T00:00:00Z/{hasta}T23:59:59Z",
        "limit": 500,
    }
    items: list[dict] = []
    url = cfg_sar["stac"]
    while True:
        r = post_json(url, cuerpo)
        items.extend(r.get("features", []))
        siguiente = next((l for l in r.get("links", []) if l.get("rel") == "next"), None)
        if not siguiente or len(items) > 5000:
            break
        url = siguiente["href"]
        cuerpo = siguiente.get("body", cuerpo)
    return items


def agrupar_por_track(items: list[dict]) -> dict:
    """Agrupa por órbita relativa + sentido, y dentro de eso por fecha.

    La órbita relativa identifica la traza sobre el suelo: dos pasadas con el
    mismo número ven el terreno desde la misma geometría, que es la condición
    para que restarlas mida agua y no relieve.
    """
    grupos: dict = defaultdict(lambda: defaultdict(list))
    for it in items:
        p = it["properties"]
        orbita = p.get("sat:relative_orbit")
        sentido = p.get("sat:orbit_state")
        if orbita is None or sentido is None:
            continue
        grupos[(int(orbita), sentido)][p["datetime"][:10]].append(it)
    return grupos


def elegir_pares(grupos: dict, ev: dict, cfg_sar: dict) -> list[dict]:
    """Arma, por track, el par (pasadas de referencia → pasada posterior)."""
    s = ev["sar"]
    pares = []
    for (orbita, sentido), por_fecha in sorted(grupos.items()):
        post = sorted(f for f in por_fecha if s["post_desde"] <= f <= s["post_hasta"])
        # Referencia: estrictamente anterior al inicio del evento. Una pasada del
        # mismo día en que empezó a llover ya no es «antes».
        pre = sorted((f for f in por_fecha if s["pre_desde"] <= f < ev["fecha_inicio"]),
                     reverse=True)[: int(cfg_sar["max_pre"])]
        if not post:
            continue
        if len(pre) < int(cfg_sar["min_pre"]):
            log(f"  track {orbita}{sentido[0].upper()}: descartado, sólo "
                f"{len(pre)} pasadas de referencia (mínimo {cfg_sar['min_pre']})")
            continue
        elegida = post[-1]
        pares.append({
            "orbita": orbita,
            "sentido": sentido,
            "track": f"{orbita}{sentido[0].upper()}",
            "fecha_post": elegida,
            "items_post": por_fecha[elegida],
            "fechas_pre": sorted(pre),
            "items_pre": {f: por_fecha[f] for f in pre},
            "plataforma": por_fecha[elegida][0]["properties"].get("platform", ""),
        })
    return pares


# --------------------------------------------------------------------- grilla

def cache_utilizable(ruta: Path, alto: int, ancho: int, bandas: int = 1) -> bool:
    """¿Existe el ráster en caché Y se puede leer de verdad?

    Comprobar sólo que el archivo exista no basta, y la diferencia costó una
    corrida entera: cuando el disco se llenó a mitad de escritura quedó un
    GeoTIFF **truncado pero presente**, y la corrida siguiente lo dio por bueno y
    reventó mucho más adelante con un `TIFFReadEncodedTile() failed` que no se
    parece en nada a su causa.

    Se leen las esquinas —no el ráster completo— porque lo que falla en un
    archivo truncado son los últimos tiles, y leerlo entero costaría tanto como
    regenerarlo.
    """
    if not ruta.exists() or ruta.stat().st_size == 0:
        return False
    try:
        with rasterio.open(ruta) as f:
            if (f.height, f.width, f.count) != (alto, ancho, bandas):
                log(f"    caché con dimensiones distintas ({f.width}×{f.height}×"
                    f"{f.count}), se regenera: {ruta.name}")
                return False
            lado = min(64, alto, ancho)
            for fila in (0, max(0, alto - lado)):
                for col in (0, max(0, ancho - lado)):
                    f.read(1, window=Window(col, fila, lado, lado))
        return True
    except Exception as exc:  # noqa: BLE001
        log(f"    caché ilegible ({type(exc).__name__}), se regenera: {ruta.name}")
        ruta.unlink(missing_ok=True)
        return False


class Rejilla:
    """Rejilla de salida común a todas las fechas y todos los tracks.

    Que sea **una sola** rejilla fija es lo que hace comparables las pasadas: si
    cada fecha se reproyectara a su propia grilla, la resta pre/post compararía
    píxeles corridos entre sí y produciría bordes falsos a lo largo de todo
    contraste fuerte del terreno.
    """

    def __init__(self, bbox, res: float):
        self.oeste, self.sur, self.este, self.norte = [float(v) for v in bbox]
        self.res = float(res)
        self.ancho = int(math.ceil((self.este - self.oeste) / self.res))
        self.alto = int(math.ceil((self.norte - self.sur) / self.res))
        self.transform = from_origin(self.oeste, self.norte, self.res, self.res)

    def ventana(self, bbox) -> tuple[int, int, int, int] | None:
        """(col, fila, ancho, alto) del recorte que cubre `bbox`, o None."""
        w, s, e, n = bbox
        c0 = max(0, int(math.floor((w - self.oeste) / self.res)))
        c1 = min(self.ancho, int(math.ceil((e - self.oeste) / self.res)))
        r0 = max(0, int(math.floor((self.norte - n) / self.res)))
        r1 = min(self.alto, int(math.ceil((self.norte - s) / self.res)))
        if c1 <= c0 or r1 <= r0:
            return None
        return c0, r0, c1 - c0, r1 - r0

    def transform_ventana(self, v):
        c0, r0, _, _ = v
        return from_origin(self.oeste + c0 * self.res,
                           self.norte - r0 * self.res, self.res, self.res)

    def perfil(self, **extra) -> dict:
        p = {"driver": "GTiff", "width": self.ancho, "height": self.alto,
             "count": 1, "dtype": "float32", "crs": "EPSG:4326",
             "transform": self.transform, "nodata": float("nan"),
             "compress": "deflate", "tiled": True, "predictor": 3}
        p.update(extra)
        return p


# ------------------------------------------------------------- procesamiento

def procesar_item(item: dict, firma: Firma, rejilla: Rejilla, cfg_sar: dict):
    """Una escena → σ⁰ lineal sobre el recorte de la rejilla que le corresponde.

    Se lee la escena decimada (10 m → 40 m), se calibra **en geometría de radar**
    —que es donde la tabla de calibración está definida— y recién entonces se
    reproyecta usando los puntos de control del propio producto.

    El orden importa: calibrar después de reproyectar obligaría a arrastrar la
    tabla por la deformación del warp, y calibrar es lo único que hace
    comparables dos escenas de plataformas distintas.
    """
    pol = cfg_sar["polarizacion"]
    if pol not in item["assets"]:
        log(f"    {item['id'][:38]}: sin asset {pol}")
        return None, None

    ventana = rejilla.ventana(item["bbox"])
    if ventana is None:
        return None, None

    href = item["assets"][pol]["href"]
    base = href.rsplit("/measurement/", 1)[0]
    nombre = href.rsplit("/", 1)[1].replace(".tiff", "")
    factor = int(cfg_sar["decimacion_lectura"])

    xml = get_bytes(firma.firmar(f"{base}/annotation/calibration/calibration-{nombre}.xml"))
    lineas, pixeles, sigma = sar.leer_lut_sigma_nought(xml)

    with rasterio.Env(**ENTORNO_GDAL):
        with rasterio.open(firma.firmar(href)) as src:
            alto = src.height // factor
            ancho = src.width // factor
            gcps, gcps_crs = src.gcps
            if not gcps:
                log(f"    {item['id'][:38]}: sin puntos de control, no se puede ubicar")
                return None, None
            dn = src.read(1, out_shape=(alto, ancho), resampling=Resampling.average)

    lut = sar.interpolar_lut(lineas, pixeles, sigma, alto, ancho, factor)
    s0 = sar.a_sigma0(dn, lut)
    del dn, lut

    # Los puntos de control vienen en fila/columna del producto a resolución
    # nativa; al leer decimado hay que escalarlos o la escena aterriza corrida
    # por el factor de decimación.
    gcps_esc = [GroundControlPoint(row=g.row / factor, col=g.col / factor,
                                   x=g.x, y=g.y, z=g.z) for g in gcps]

    _, _, w, h = ventana
    destino = np.zeros((h, w), dtype=np.float32)
    reproject(
        source=s0, destination=destino,
        gcps=gcps_esc, src_crs=gcps_crs, src_nodata=0,
        dst_transform=rejilla.transform_ventana(ventana), dst_crs="EPSG:4326",
        dst_nodata=0, resampling=Resampling.average,
    )
    return ventana, destino


def mosaico_fecha(items, firma, rejilla, cfg_sar, destino: Path, forzar: bool) -> Path | None:
    """Todas las rebanadas de una pasada → un σ⁰ dB sobre la rejilla, en caché.

    Una pasada sobre la región se entrega partida en 2-3 rebanadas que se
    solapan. Donde se solapan se promedia en intensidad lineal, no en dB:
    promediar decibeles es promediar logaritmos y sesga el resultado hacia el
    valor más bajo.
    """
    if not forzar and cache_utilizable(destino, rejilla.alto, rejilla.ancho):
        log(f"    caché: {destino.name}")
        return destino

    suma = np.zeros((rejilla.alto, rejilla.ancho), dtype=np.float32)
    cuenta = np.zeros((rejilla.alto, rejilla.ancho), dtype=np.uint8)
    usadas = 0
    for it in items:
        t0 = time.time()
        ventana, arr = procesar_item(it, firma, rejilla, cfg_sar)
        if arr is None:
            continue
        c0, r0, w, h = ventana
        m = arr > 0
        if not m.any():
            continue
        suma[r0:r0 + h, c0:c0 + w][m] += arr[m]
        cuenta[r0:r0 + h, c0:c0 + w][m] += 1
        usadas += 1
        log(f"    {it['id'][:38]} → {int(m.sum()):,} px en {time.time() - t0:.0f}s")

    if usadas == 0:
        log("    ninguna rebanada aportó datos")
        return None

    # Se divide sobre el propio arreglo: `np.where` construiría un temporal
    # float64 de la región entera, que son cientos de MB por nada.
    np.divide(suma, np.maximum(cuenta, 1, dtype=np.float32), out=suma)
    suma[cuenta == 0] = np.nan
    db = sar.a_db(suma)
    del suma, cuenta

    destino.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(destino, "w", **rejilla.perfil()) as dst:
        dst.write(db, 1)
    log(f"    escrito {destino.name} — {int(np.isfinite(db).sum()):,} px con dato")
    return destino


def estadistica_pre(rutas: list[Path], rejilla: Rejilla, destino: Path,
                    forzar: bool) -> Path:
    """Mediana, desviación y número de observaciones de la referencia.

    Se hace por bloques de filas porque el apilado necesita todas las fechas a la
    vez: la región completa son ~32 millones de píxeles, y cinco copias en
    memoria son 640 MB que no hacen falta.

    Mediana y no media: una sola pasada con un chubasco encima arrastra la media
    y deja de ser una línea base. La mediana la ignora.
    """
    if not forzar and cache_utilizable(destino, rejilla.alto, rejilla.ancho, 3):
        log(f"    caché: {destino.name}")
        return destino

    perfil = rejilla.perfil(count=3)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fuentes = [rasterio.open(r) for r in rutas]
    try:
        with rasterio.open(destino, "w", **perfil) as dst:
            for fila in range(0, rejilla.alto, FILAS_BLOQUE):
                n_filas = min(FILAS_BLOQUE, rejilla.alto - fila)
                ven = Window(0, fila, rejilla.ancho, n_filas)
                pila = np.stack([f.read(1, window=ven) for f in fuentes])
                with warnings.catch_warnings():
                    # Un bloque enteramente fuera de la traza es todo NaN. No es
                    # un error: es que ahí el satélite no pasó.
                    warnings.simplefilter("ignore", RuntimeWarning)
                    mediana = np.nanmedian(pila, axis=0).astype(np.float32)
                    desviacion = np.nanstd(pila, axis=0).astype(np.float32)
                n = np.isfinite(pila).sum(axis=0).astype(np.float32)
                dst.write(mediana, 1, window=ven)
                dst.write(desviacion, 2, window=ven)
                dst.write(n, 3, window=ven)
    finally:
        for f in fuentes:
            f.close()
    log(f"    escrito {destino.name}")
    return destino


def mosaico_dem(rejilla: Rejilla, cfg_sar: dict, destino: Path, forzar: bool) -> Path | None:
    """Modelo de elevación Copernicus GLO-30 sobre la rejilla, con su pendiente.

    Se accede igual que a Sentinel-1 y por el mismo motivo: son COG públicos en
    AWS Open Data, sin credenciales, leídos por `Range`. Los tiles cubren 1°×1° y
    **se nombran por su esquina suroeste**, así que el tile de un punto se obtiene
    con el piso de sus coordenadas.

    Guarda dos bandas: elevación y pendiente. La pendiente se calcula ya sobre la
    rejilla de trabajo, no sobre los 30 m originales, porque lo que importa es si
    el terreno es plano a la escala a la que se afirma que hay agua.
    """
    if not forzar and cache_utilizable(destino, rejilla.alto, rejilla.ancho, 2):
        log(f"  caché: {destino.name}")
        return destino

    dem = np.full((rejilla.alto, rejilla.ancho), np.nan, dtype=np.float32)
    base = cfg_sar["dem_base"].rstrip("/")
    faltantes = []
    for la in range(int(math.floor(rejilla.sur)), int(math.floor(rejilla.norte)) + 1):
        for lo in range(int(math.floor(rejilla.oeste)), int(math.floor(rejilla.este)) + 1):
            ventana = rejilla.ventana([lo, la, lo + 1, la + 1])
            if ventana is None:
                continue
            nom = (f"Copernicus_DSM_COG_10_{'S' if la < 0 else 'N'}{abs(la):02d}_00_"
                   f"{'W' if lo < 0 else 'E'}{abs(lo):03d}_00_DEM")
            _, _, w, h = ventana
            trozo = np.full((h, w), np.nan, dtype=np.float32)
            try:
                with rasterio.Env(**ENTORNO_GDAL):
                    with rasterio.open(f"{base}/{nom}/{nom}.tif") as src:
                        reproject(
                            source=rasterio.band(src, 1), destination=trozo,
                            src_transform=src.transform, src_crs=src.crs,
                            dst_transform=rejilla.transform_ventana(ventana),
                            dst_crs="EPSG:4326", dst_nodata=float("nan"),
                            resampling=Resampling.average)
            except Exception:  # noqa: BLE001
                # Un tile ausente casi siempre es océano: el DEM no cubre el mar.
                faltantes.append(nom[-16:])
                continue
            c0, r0, _, _ = ventana
            m = np.isfinite(trozo)
            dem[r0:r0 + h, c0:c0 + w][m] = trozo[m]

    con_dato = float(np.isfinite(dem).mean())
    if faltantes:
        log(f"  tiles de DEM sin respuesta ({len(faltantes)}): {', '.join(faltantes[:6])}")
    log(f"  DEM sobre {con_dato * 100:.1f} % de la rejilla")
    if con_dato < 0.5:
        # Sin DEM el terreno se declara no apto, así que un fallo de descarga
        # borraría la capa entera en silencio. Mejor reventar.
        raise RuntimeError(
            f"sólo se pudo armar el DEM sobre el {con_dato * 100:.0f} % de la región; "
            "sin él la máscara de terreno dejaría fuera casi todo")

    pend = sar.pendiente_grados(dem, rejilla.res, (rejilla.sur + rejilla.norte) / 2)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(destino, "w", **rejilla.perfil(count=2)) as dst:
        dst.write(dem, 1)
        dst.write(pend, 2)
    log(f"  escrito {destino.name}")
    return destino


def detectar_track(par: dict, ruta_post: Path, ruta_pre: Path, ruta_terreno: Path,
                   rejilla: Rejilla, cfg_sar: dict) -> dict:
    """Aplica el criterio de agua y devuelve máscaras y diagnóstico del track."""
    with rasterio.open(ruta_post) as f:
        post = f.read(1)
    with rasterio.open(ruta_pre) as f:
        mediana, desviacion, n_pre = f.read(1), f.read(2), f.read(3)

    with rasterio.open(ruta_terreno) as f:
        dem, pend = f.read(1), f.read(2)
    apto = sar.terreno_apto(dem, pend, float(cfg_sar["pendiente_max_grados"]),
                            float(cfg_sar["altitud_max_m"]),
                            float(cfg_sar["altitud_min_m"]))
    del dem, pend

    permanente = sar.agua_permanente(
        mediana, desviacion, float(cfg_sar["permanente_db"]),
        float(cfg_sar["estabilidad_pre_db"]))

    # La referencia del umbral se toma sólo del agua permanente CONTINENTAL. El
    # mar es un mal patrón de comparación: es mucho más liso que una inundación
    # sobre potrero o calle, así que calibrar contra él produce un umbral que la
    # huella real no alcanza a cumplir. Ríos y lagos son el análogo correcto.
    umbral, crudo, n_perm = sar.umbral_agua(
        post, permanente & apto, float(cfg_sar["agua_db_min"]),
        float(cfg_sar["agua_db_max"]), float(cfg_sar["agua_db_respaldo"]),
        percentil=float(cfg_sar["percentil_agua"]))
    log(f"    agua permanente: {n_perm:,} px · umbral crudo "
        f"{crudo:.1f} dB → aplicado {umbral:.1f} dB")

    # Se calculan las dos versiones para poder informar cuánto descartó la
    # máscara de terreno. Ese número es el diagnóstico de nieve húmeda y tiene
    # que quedar publicado, no escondido: en la primera corrida era el 75 % del
    # resultado.
    sin_terreno = sar.detectar_agua_nueva(
        post, mediana, desviacion, n_pre, umbral,
        float(cfg_sar["caida_db"]), float(cfg_sar["estabilidad_pre_db"]),
        int(cfg_sar["min_pre"]), permanente)
    agua = sin_terreno & apto

    cobertura = np.isfinite(post) & (n_pre >= int(cfg_sar["min_pre"])) & apto
    descartado = int(sin_terreno.sum() - agua.sum())
    log(f"    cobertura {int(cobertura.sum()):,} px · agua nueva "
        f"{int(agua.sum()):,} px · descartados por terreno {descartado:,} "
        f"({100 * descartado / max(1, int(sin_terreno.sum())):.0f} %)")
    return {"agua": agua, "cobertura": cobertura, "umbral_db": umbral,
            "umbral_crudo_db": crudo, "px_permanente": n_perm,
            "px_cobertura": int(cobertura.sum()), "px_agua": int(agua.sum()),
            "px_descartados_terreno": descartado}


# ------------------------------------------------------------- vectorización

def vectorizar(mascara: np.ndarray, transform, props: dict, area_min_m2: float):
    """Máscara → polígonos, descartando lo que es speckle y no inundación.

    `shapes` ya agrupa píxeles conectados, así que el filtro de tamaño se aplica
    sobre el polígono resultante y no hace falta etiquetar componentes conexas a
    mano. Se usa conectividad 8 porque una lengua de agua que avanza en diagonal
    por un cauce es una sola mancha, no una hilera de manchas sueltas.
    """
    feats = []
    total_m2 = 0.0
    for geom, valor in shapes(mascara.astype("uint8"), mask=mascara,
                              transform=transform, connectivity=8):
        if valor != 1:
            continue
        area = sar.area_poligono_m2(geom)
        if area < area_min_m2:
            continue
        total_m2 += area
        feats.append({
            "type": "Feature",
            "geometry": sar.aligerar(geom),
            "properties": {**props, "hectareas": round(area / 10_000.0, 2)},
        })
    return feats, total_m2


def cobertura_geojson(mascara: np.ndarray, rejilla: Rejilla, props: dict):
    """Contorno grueso de dónde se pudo mirar.

    Va como capa propia porque sin ella el visor mentiría por omisión: si el
    satélite no pasó por un sector, «no hay huella» significa «no se miró», no
    «no se inundó». La regla 5 del proyecto —ausencia de dato ≠ ausencia de
    riesgo— exige poder distinguir esos dos casos.
    """
    d = DECIMACION_COBERTURA
    alto, ancho = mascara.shape[0] // d, mascara.shape[1] // d
    recorte = mascara[:alto * d, :ancho * d]
    # Un bloque cuenta como observado si al menos la cuarta parte lo fue: así el
    # borde de la traza no se dentella por píxeles sueltos.
    bloques = recorte.reshape(alto, d, ancho, d).sum(axis=(1, 3)) >= (d * d) // 4
    transform = from_origin(rejilla.oeste, rejilla.norte,
                            rejilla.res * d, rejilla.res * d)
    feats = []
    for geom, valor in shapes(bloques.astype("uint8"), mask=bloques,
                              transform=transform, connectivity=8):
        if valor != 1:
            continue
        if sar.area_poligono_m2(geom) < 5e6:      # < 5 km², borde suelto
            continue
        feats.append({"type": "Feature", "geometry": sar.aligerar(geom, 5),
                      "properties": dict(props)})
    return feats


# ---------------------------------------------------------------- verificación

def _hay_agua_cerca(agua: np.ndarray, fila: int, col: int, rf: int, rc: int) -> bool:
    """¿Hay algún píxel de agua en la vecindad de (fila, col)?"""
    f0, f1 = max(0, fila - rf), min(agua.shape[0], fila + rf + 1)
    c0, c1 = max(0, col - rc), min(agua.shape[1], col + rc + 1)
    if f1 <= f0 or c1 <= c0:
        return False
    return bool(agua[f0:f1, c0:c1].any())


def verificar(agua: np.ndarray, cobertura: np.ndarray, rejilla: Rejilla,
              radios_m=(0, 300, 1000)) -> None:
    """Contrasta la huella contra un dataset que no participó en derivarla.

    Los puntos críticos de origen hídrico de SENAPRED son dónde el municipio
    reportó que se inunda. No entraron en ningún paso de este pipeline: ni en la
    selección de escenas, ni en la calibración, ni en el umbral. Si la huella SAR
    fuera ruido, no tendría por qué caer donde ellos están.

    Dos decisiones para que la comparación sea honesta:

    1. **Por proximidad y no por contención.** Un punto crítico es un punto —una
       alcantarilla, un puente, un paso bajo nivel—, no un área. Exigir que caiga
       exactamente dentro de un polígono de 40 m castiga por la geometría del
       registro, no por la calidad de la detección.
    2. **Contra puntos al azar dentro de la misma cobertura.** Una huella grande
       acierta por tamaño; lo que hay que medir es cuánto mejor lo hace que el
       azar sobre el mismo territorio observado.
    """
    ruta_pc = WEB_DATA / "puntos-criticos-inundacion.geojson"
    if not ruta_pc.exists():
        log("verificación omitida: falta puntos-criticos-inundacion.geojson")
        return
    fc = json.loads(ruta_pc.read_text(encoding="utf-8"))

    lat_media = (rejilla.sur + rejilla.norte) / 2
    m_por_px_y = rejilla.res * 111_320.0
    m_por_px_x = m_por_px_y * math.cos(math.radians(lat_media))

    def a_celda(lon, lat):
        c = int((lon - rejilla.oeste) / rejilla.res)
        f = int((rejilla.norte - lat) / rejilla.res)
        if 0 <= c < rejilla.ancho and 0 <= f < rejilla.alto:
            return f, c
        return None

    observados = []
    for feat in fc["features"]:
        lon, lat = feat["geometry"]["coordinates"]
        celda = a_celda(lon, lat)
        if celda and cobertura[celda]:
            observados.append(celda)
    if not observados:
        log("verificación: ningún punto crítico cae dentro de la cobertura SAR")
        return

    # Puntos al azar sobre el mismo territorio observado, como grupo de control.
    rng = np.random.default_rng(20260809)
    azar, intentos = [], 0
    objetivo = len(observados) * 20
    while len(azar) < objetivo and intentos < 5_000_000:
        intentos += 1
        f = int(rng.integers(0, rejilla.alto))
        c = int(rng.integers(0, rejilla.ancho))
        if cobertura[f, c]:
            azar.append((f, c))

    frac = 100.0 * agua.sum() / max(1, cobertura.sum())
    log("")
    log("VERIFICACIÓN INDEPENDIENTE — puntos críticos SENAPRED vs huella SAR")
    log(f"  la huella cubre el {frac:.2f} % del territorio observado")
    log(f"  puntos críticos hídricos dentro de la cobertura SAR: {len(observados)}")
    log(f"  puntos de control al azar sobre la misma cobertura: {len(azar)}")
    log("")
    log("  radio    puntos SENAPRED    puntos al azar    enriquecimiento")
    for r in radios_m:
        rf = int(math.ceil(r / m_por_px_y))
        rc = int(math.ceil(r / m_por_px_x))
        a_obs = sum(1 for f, c in observados if _hay_agua_cerca(agua, f, c, rf, rc))
        a_azar = sum(1 for f, c in azar if _hay_agua_cerca(agua, f, c, rf, rc))
        p_obs = 100.0 * a_obs / len(observados)
        p_azar = 100.0 * a_azar / max(1, len(azar))
        enr = f"×{p_obs / p_azar:.1f}" if p_azar > 0 else "(azar en 0)"
        log(f"  {r:>4} m   {a_obs:>4}/{len(observados)} ({p_obs:5.1f} %)   "
            f"{a_azar:>5}/{len(azar)} ({p_azar:5.1f} %)   {enr}")
    log("")
    log("  (SENAPRED no participó en ningún paso de la derivación: la coincidencia")
    log("   es independiente. Un enriquecimiento cercano a ×1 significaría que la")
    log("   huella no distingue nada.)")


# ----------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="Capa B — huella de inundación Sentinel-1")
    ap.add_argument("--evento", help="id del evento en config; por defecto el primero")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("O", "S", "E", "N"),
                    help="recorta el área de trabajo (para probar rápido)")
    ap.add_argument("--forzar", action="store_true", help="ignora la caché de rásteres")
    ap.add_argument("--conservar-fechas", action="store_true",
                    help="no borra los rásteres de cada pasada de referencia "
                         "(útil para depurar; ocupan ~85 MB cada uno)")
    ap.add_argument("--verificar", action="store_true",
                    help="contrasta la huella contra los puntos críticos SENAPRED")
    args = ap.parse_args()

    cfg = cargar_config()
    cfg_sar = cfg["sar"]
    eventos = cfg["eventos_validacion"]
    ev = next((e for e in eventos if e["id"] == args.evento), eventos[0]) \
        if args.evento else eventos[0]
    bbox = args.bbox or cfg["region"]["bbox"]

    log(f"evento: {ev['nombre']}")
    log(f"área de trabajo: {[round(b, 3) for b in bbox]}")

    rejilla = Rejilla(bbox, float(cfg_sar["resolucion_grados"]))
    log(f"rejilla de salida: {rejilla.ancho} × {rejilla.alto} px "
        f"a {cfg_sar['resolucion_grados']}° (~{cfg_sar['resolucion_grados'] * 111320:.0f} m)")

    firma = Firma(cfg_sar["firma_sas"])
    log("consultando el catálogo (anónimo)…")
    items = buscar_items(cfg_sar, bbox, ev["sar"]["pre_desde"], ev["sar"]["post_hasta"])
    log(f"  {len(items)} escenas en el catálogo")

    pares = elegir_pares(agrupar_por_track(items), ev, cfg_sar)
    if not pares:
        log("no hay ningún track con pasada posterior y referencia suficiente")
        sys.exit(1)
    for p in pares:
        log(f"  track {p['track']} ({p['plataforma']}): post {p['fecha_post']} "
            f"← referencia {', '.join(p['fechas_pre'])}")

    raiz = DATA_PROC / "sar" / ev["id"]
    area_min = (int(cfg_sar["min_pixeles_agrupados"])
                * sar.area_pixel_m2(rejilla.res, (rejilla.sur + rejilla.norte) / 2))

    log("")
    log("modelo de elevación Copernicus GLO-30 (anónimo, COG por Range)…")
    ruta_terreno = mosaico_dem(rejilla, cfg_sar, raiz / "terreno.tif", args.forzar)

    huella_feats: list[dict] = []
    cobertura_feats: list[dict] = []
    diagnostico: list[dict] = []
    agua_union = np.zeros((rejilla.alto, rejilla.ancho), dtype=bool)
    cobertura_union = np.zeros((rejilla.alto, rejilla.ancho), dtype=bool)

    for par in pares:
        log("")
        log(f"track {par['track']} — {par['plataforma']}")
        carpeta = raiz / par["track"]

        ruta_post = mosaico_fecha(par["items_post"], firma, rejilla, cfg_sar,
                                  carpeta / f"{par['fecha_post']}.tif", args.forzar)
        if ruta_post is None:
            continue

        # La estadística pre es lo único que se necesita aguas abajo. Si ya está,
        # no se vuelve a bajar ni una escena de referencia: son ~25 min y ~500 MB
        # por track, y en la primera corrida el disco se llenó por guardarlas.
        ruta_pre = carpeta / "estadistica_pre.tif"
        if not args.forzar and cache_utilizable(ruta_pre, rejilla.alto, rejilla.ancho, 3):
            log(f"    caché: {ruta_pre.name} (no se rebajan las pasadas de referencia)")
        else:
            rutas_pre = []
            for fecha in par["fechas_pre"]:
                r = mosaico_fecha(par["items_pre"][fecha], firma, rejilla, cfg_sar,
                                  carpeta / f"{fecha}.tif", args.forzar)
                if r is not None:
                    rutas_pre.append(r)
            if len(rutas_pre) < int(cfg_sar["min_pre"]):
                log(f"  referencia insuficiente tras procesar ({len(rutas_pre)})")
                continue
            estadistica_pre(rutas_pre, rejilla, ruta_pre, args.forzar)
            if not args.conservar_fechas:
                for r in rutas_pre:
                    r.unlink(missing_ok=True)
                log(f"    borradas {len(rutas_pre)} pasadas de referencia "
                    f"(ya resumidas; --conservar-fechas las mantiene)")

        res = detectar_track(par, ruta_post, ruta_pre, ruta_terreno, rejilla, cfg_sar)

        props = {
            **sello(f"Sentinel-1 {par['plataforma'].upper()} GRD "
                    f"(Copernicus / ESA) vía Microsoft Planetary Computer",
                    par["fecha_post"][:4]),
            "tipo": "agua_nueva",
            "evento": ev["nombre"],
            "fecha_observacion": par["fecha_post"],
            "track": par["track"],
            "orbita_relativa": par["orbita"],
            "direccion": par["sentido"],
            "plataforma": par["plataforma"],
            "fechas_referencia": par["fechas_pre"],
            "umbral_agua_db": round(res["umbral_db"], 1),
            "caida_db": float(cfg_sar["caida_db"]),
        }
        feats, area_m2 = vectorizar(res["agua"], rejilla.transform, props, area_min)
        log(f"    {len(feats)} polígonos · {area_m2 / 1e6:.1f} km² "
            f"({area_m2 / 1e4:,.0f} ha)")
        huella_feats.extend(feats)
        cobertura_feats.extend(cobertura_geojson(res["cobertura"], rejilla, {
            **sello(f"Sentinel-1 {par['plataforma'].upper()} GRD", par["fecha_post"][:4]),
            "tipo": "cobertura",
            "track": par["track"],
            "fecha_observacion": par["fecha_post"],
        }))
        agua_union |= res["agua"]
        cobertura_union |= res["cobertura"]

        diagnostico.append({
            "track": par["track"], "plataforma": par["plataforma"],
            "fecha_observacion": par["fecha_post"],
            "fechas_referencia": par["fechas_pre"],
            "umbral_agua_db": round(res["umbral_db"], 2),
            "umbral_crudo_db": (None if not math.isfinite(res["umbral_crudo_db"])
                                else round(res["umbral_crudo_db"], 2)),
            "px_agua_permanente": res["px_permanente"],
            "px_cobertura": res["px_cobertura"],
            "px_agua_nueva": res["px_agua"],
            "px_descartados_por_terreno": res["px_descartados_terreno"],
            "poligonos": len(feats),
            "km2": round(area_m2 / 1e6, 2),
        })

    if not diagnostico:
        log("ningún track produjo huella; no se escribe nada")
        sys.exit(1)

    meta = procedencia(
        fuente="Sentinel-1 GRD (Copernicus / ESA), distribuido por Microsoft "
               "Planetary Computer",
        url=cfg_sar["stac"],
        metodo=(
            "Detección de cambio en σ⁰ VV entre la pasada posterior al evento y la "
            f"mediana de hasta {cfg_sar['max_pre']} pasadas previas de la MISMA órbita "
            "relativa. Calibración a σ⁰ con la tabla sigmaNought del propio producto; "
            "reproyección por los puntos de control del GRD. Se marca agua donde la "
            f"caída es ≥ {abs(float(cfg_sar['caida_db']))} dB, el valor posterior es tan "
            f"oscuro como el agua permanente de la propia escena (percentil "
            f"{cfg_sar['percentil_agua']:.0f}, acotado a "
            f"[{cfg_sar['agua_db_min']}, {cfg_sar['agua_db_max']}] dB) y la referencia era "
            f"estable (desviación ≤ {cfg_sar['estabilidad_pre_db']} dB). Se excluye el agua "
            "permanente y los grupos menores a "
            f"{cfg_sar['min_pixeles_agrupados']} píxeles. Se excluye además todo terreno "
            f"con pendiente > {cfg_sar['pendiente_max_grados']}° o sobre "
            f"{cfg_sar['altitud_max_m']:.0f} m (Copernicus GLO-30): es la máscara que separa "
            "la inundación de la NIEVE HÚMEDA, que en banda C se ve igual de oscura que el "
            "agua y ningún umbral radiométrico distingue."
        ),
        capa_evidencia="B_observado",
        incertidumbre=(
            "Es una FOTO del instante de la pasada, no el máximo del evento: agua que "
            "subió y bajó entre pasadas no aparece. El radar NO ve agua bajo dosel "
            "cerrado (la copa devuelve la señal antes de llegar al suelo) ni en zona "
            "urbana densa (el doble rebote pared-suelo mantiene alta la retrodispersión), "
            "así que SUBESTIMA justo donde vive más gente. El agua con viento se rugosiza "
            "y tampoco se detecta. Por el otro lado, la NIEVE HÚMEDA es radiométricamente "
            "indistinguible del agua, y sólo se descarta por geomorfología: se excluye "
            f"pendiente > {cfg_sar['pendiente_max_grados']}° y altura > "
            f"{cfg_sar['altitud_max_m']:.0f} m. Eso implica que esta capa NO puede afirmar "
            "nada sobre inundación en cordillera ni en ladera. Comparar dentro de la misma "
            "órbita relativa cancela la sombra de radar por ser estática, pero no se aplica "
            "corrección radiométrica por terreno. Resolución de salida "
            f"~{float(cfg_sar['resolucion_grados']) * 111320:.0f} m: no apto para decisión predial."
        ),
        escala_original="Sentinel-1 IW GRDH, 10 m de espaciado, leído 1 de cada "
                        f"{cfg_sar['decimacion_lectura']}",
        fecha_dato=f"{ev['nombre']} — pasadas {', '.join(d['fecha_observacion'] for d in diagnostico)}",
    )

    salida = WEB_DATA / "sar"
    escribir_geojson(huella_feats, salida / "huella-observada.geojson", meta)
    escribir_geojson(cobertura_feats, salida / "cobertura-sar.geojson", meta)

    area_total = sum(d["km2"] for d in diagnostico)
    indice = {
        "evento": {"id": ev["id"], "nombre": ev["nombre"],
                   "fecha_inicio": ev["fecha_inicio"], "fecha_fin": ev["fecha_fin"],
                   "rios": ev.get("rios", [])},
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "resolucion_m": round(float(cfg_sar["resolucion_grados"]) * 111320),
        "tracks": diagnostico,
        "resumen": {
            "tracks": len(diagnostico),
            "poligonos": len(huella_feats),
            "km2": round(area_total, 2),
            "hectareas": round(area_total * 100, 0),
            "km2_observados": round(
                float(cobertura_union.sum())
                * sar.area_pixel_m2(rejilla.res, (rejilla.sur + rejilla.norte) / 2) / 1e6, 1),
        },
        "procedencia": meta,
    }
    (salida / "indice.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"  escrito web/data/sar/indice.json")

    log("")
    log(f"TOTAL: {len(huella_feats)} polígonos · {area_total:.1f} km² "
        f"({area_total * 100:,.0f} ha) en {len(diagnostico)} tracks")

    if args.verificar:
        verificar(agua_union, cobertura_union, rejilla)

    log("listo")


if __name__ == "__main__":
    main()
