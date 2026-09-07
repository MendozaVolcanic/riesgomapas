"""Utilidades compartidas del pipeline riesgomapas.

Convenciones del proyecto:
  - Todo dato se almacena en EPSG:4326. La proyección a UTM se hace al vuelo
    cuando hace falta medir distancias o áreas.
  - Todo producto derivado lleva metadatos de PROCEDENCIA obligatorios
    (fuente, fecha de captura, método, incertidumbre). Ver `procedencia()`.
  - Nada de mojibake-fixing sobre los servicios ArcGIS: entregan UTF-8 válido.
    Lo que se rompe es la consola de Windows, no el dato.
"""
from __future__ import annotations

import io
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

# La consola de Windows por defecto es cp1252 y rompe cualquier acento.
# Regla del workspace: forzar UTF-8 en stdout antes de imprimir nada.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
DATA_RAW = RAIZ / "data" / "raw"
DATA_PROC = RAIZ / "data" / "processed"
WEB_DATA = RAIZ / "web" / "data"
CONFIG = RAIZ / "config"

for _d in (DATA_RAW, DATA_PROC, WEB_DATA):
    _d.mkdir(parents=True, exist_ok=True)

# Varios servicios del Estado chileno sirven con cadenas de certificados
# incompletas. Se desactiva la verificación sólo para lectura de datos
# públicos; nunca se envían credenciales por estos canales.
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

UA = "riesgomapas/0.1 (proyecto abierto de mapas de inundacion Chile)"


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def cargar_config(nombre: str = "araucania.yaml") -> dict:
    with open(CONFIG / nombre, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _url_ascii(url: str) -> str:
    """Percent-encodea los caracteres no-ASCII del path.

    Varios servicios de SENAPRED tienen tildes en el nombre del servicio
    (`Puntos_Críticos_...`). `urllib.request` exige URL ASCII y falla con
    UnicodeEncodeError, que se confunde fácil con "el servicio no existe".
    """
    return urllib.parse.quote(url, safe=":/?&=%,*#@+$;~")


def get_json(url: str, params: dict | None = None, reintentos: int = 3) -> dict:
    """GET con reintentos y backoff. Devuelve JSON decodificado como UTF-8."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    url = _url_ascii(url)
    ultimo = None
    for intento in range(reintentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, context=_CTX, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            espera = 2 ** intento
            log(f"  reintento {intento + 1}/{reintentos} en {espera}s ({exc})")
            time.sleep(espera)
    raise RuntimeError(f"falló GET {url[:120]}: {ultimo}")


def get_bytes(url: str, reintentos: int = 3, timeout: int = 180) -> bytes:
    """GET crudo con reintentos, sin escribir a disco.

    Lo usa la capa B para leer los anexos de calibración de Sentinel-1, que se
    consumen en memoria y no tiene sentido versionar.
    """
    url = _url_ascii(url)
    ultimo = None
    for intento in range(reintentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, context=_CTX, timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            espera = 2 ** intento
            log(f"  reintento {intento + 1}/{reintentos} en {espera}s ({exc})")
            time.sleep(espera)
    raise RuntimeError(f"falló GET {url[:120]}: {ultimo}")


def post_json(url: str, cuerpo: dict, reintentos: int = 3) -> dict:
    """POST de JSON con reintentos. El STAC se consulta por POST."""
    datos = json.dumps(cuerpo).encode("utf-8")
    ultimo = None
    for intento in range(reintentos):
        try:
            req = urllib.request.Request(
                _url_ascii(url), data=datos,
                headers={"User-Agent": UA, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, context=_CTX, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            espera = 2 ** intento
            log(f"  reintento {intento + 1}/{reintentos} en {espera}s ({exc})")
            time.sleep(espera)
    raise RuntimeError(f"falló POST {url[:120]}: {ultimo}")


def descargar(url: str, destino: Path, forzar: bool = False) -> Path:
    """Descarga un archivo y verifica que no sea HTML disfrazado.

    Regla de la guía maestra de investigación: verificar magic bytes y tamaño.
    Un PDF de <100 KB casi siempre es una página de error.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not forzar and destino.stat().st_size > 0:
        log(f"  ya existe: {destino.name} ({destino.stat().st_size / 1024:.0f} KB)")
        return destino

    req = urllib.request.Request(_url_ascii(url), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=_CTX, timeout=300) as r:
        datos = r.read()

    if datos[:15].lstrip().lower().startswith((b"<!doctype", b"<html")):
        raise RuntimeError(f"{url} devolvió HTML, no un archivo binario")
    if destino.suffix.lower() == ".pdf" and not datos.startswith(b"%PDF-"):
        raise RuntimeError(f"{url} no es un PDF válido (magic bytes: {datos[:8]!r})")

    destino.write_bytes(datos)
    log(f"  descargado: {destino.name} ({len(datos) / 1024:.0f} KB)")
    return destino


def consultar_capa_arcgis(
    base_url: str,
    where: str = "1=1",
    campos: str = "*",
    geometria: bool = True,
    pagina: int = 2000,
) -> list[dict]:
    """Descarga todos los registros de una capa ArcGIS REST, paginando.

    ArcGIS limita cada respuesta (típicamente 1000-2000 registros) sin avisar.
    No paginar es la causa nº1 de datasets silenciosamente truncados.
    """
    # El tope por respuesta lo fija el servicio y NO es uniforme: dentro del mismo
    # org de SENAPRED hay capas con maxRecordCount=16000 y otras con 1000. Pedir
    # un tamaño de página mayor al tope y cortar cuando "vino menos de lo pedido"
    # trunca el dataset en silencio. La condición correcta de parada es la
    # bandera `exceededTransferLimit` que devuelve el propio servicio.
    try:
        tope = int(get_json(base_url, {"f": "json"}).get("maxRecordCount") or pagina)
    except Exception:  # noqa: BLE001
        tope = pagina
    pagina = max(1, min(pagina, tope))

    feats: list[dict] = []
    offset = 0
    while True:
        r = get_json(
            f"{base_url}/query",
            {
                "where": where,
                "outFields": campos,
                "returnGeometry": str(geometria).lower(),
                "outSR": 4326,
                "resultOffset": offset,
                "resultRecordCount": pagina,
                "f": "json",
            },
        )
        # ArcGIS responde HTTP 200 con un objeto `error` cuando la consulta es
        # inválida (por ejemplo un campo que esa capa no tiene). Leer
        # `features` con default [] convierte ese error en "no hay datos": la
        # capa aparece vacía y nadie se entera. Hay que reventar.
        if isinstance(r.get("error"), dict):
            e = r["error"]
            raise RuntimeError(
                f"ArcGIS rechazó la consulta a {base_url}: "
                f"[{e.get('code')}] {e.get('message')} {e.get('details') or ''}")
        lote = r.get("features", [])
        feats.extend(lote)
        if not lote or not r.get("exceededTransferLimit"):
            break
        offset += len(lote)
        if offset > 500_000:  # cortafuegos ante servicio que ignora el offset
            raise RuntimeError("paginación desbocada — el servicio ignora resultOffset")
    return feats


def anillos_a_geojson(geom: dict | None) -> dict | None:
    """ArcGIS entrega polígonos como lista de anillos con orientación implícita.

    Convención ArcGIS: anillo exterior en sentido horario, huecos en antihorario.
    GeoJSON no comparte esa regla, así que hay que separarlos por el signo del
    área firmada; si no, los huecos se dibujan como polígonos macizos y una zona
    excluida del área de riesgo aparece como incluida.
    """
    anillos = (geom or {}).get("rings") or []
    if not anillos:
        return None

    def area(a):
        return sum((a[i][0] * a[i + 1][1] - a[i + 1][0] * a[i][1])
                   for i in range(len(a) - 1)) / 2.0

    exteriores, huecos = [], []
    for a in anillos:
        if len(a) < 4:
            continue
        (exteriores if area(a) < 0 else huecos).append(
            [[float(x), float(y)] for x, y, *_ in a])

    if not exteriores:  # todos dieron el mismo signo: tratarlos como exteriores
        exteriores = [[[float(x), float(y)] for x, y, *_ in a]
                      for a in anillos if len(a) >= 4]
        huecos = []
    if not exteriores:
        return None

    polis = [[e] for e in exteriores]
    for h in huecos:                       # cada hueco al primer exterior disponible
        polis[0].append(h)
    if len(polis) == 1:
        return {"type": "Polygon", "coordinates": polis[0]}
    return {"type": "MultiPolygon", "coordinates": polis}


def sello(fuente: str, anio: str | int | None) -> dict:
    """Sello de fuente y año que va PEGADO A CADA FEATURE, no sólo a la colección.

    Motivo: los features se filtran, se shardean y se mezclan en el mapa. Si la
    atribución vive sólo en la cabecera del archivo, en cuanto un polígono se
    muestra junto a otro de distinta fuente ya no se sabe de dónde salió cada uno.

    `anio` nunca se inventa. Si la fuente no lo declara, va la cadena
    "no declarado por la fuente" — que es información, no un hueco.
    """
    return {
        "fuente": fuente,
        "anio": str(anio) if anio not in (None, "") else "no declarado por la fuente",
    }


ANIO_NO_DECLARADO = "no declarado por la fuente"


def procedencia(
    fuente: str,
    url: str,
    metodo: str,
    capa_evidencia: str,
    incertidumbre: str,
    escala_original: str | None = None,
    fecha_dato: str | None = None,
) -> dict:
    """Bloque de procedencia que acompaña a TODO producto del pipeline.

    `capa_evidencia` es una de: A_normativo | B_observado | C_modelado |
    D_operacional | inventario. Esta etiqueta es la que el frontend usa para no
    mezclar evidencia legal con modelo global. Si un producto no puede declarar
    su capa, no se publica.
    """
    # Las cuatro capas de evidencia dicen algo sobre EL TERRITORIO y nunca se
    # fusionan entre sí. `inventario` es de otra naturaleza: no habla del
    # territorio sino de **lo que sabemos de él** — qué comuna tiene mapa y cuál
    # no. Se admite como categoría aparte justamente para que no pueda colarse
    # como si fuera evidencia de amenaza: nadie debe poder mezclar «esta comuna
    # no tiene cartografía» con «esta comuna no se inunda».
    # `A_derivado` es geometría que construimos NOSOTROS desde una lámina
    # impresa (REGLAS §1.5): el contenido y su peso legal son de la fuente, el
    # trazado y la ubicación son nuestros. Existe aparte de `A_normativo`
    # porque hasta el 7-sep-2026 las 163 láminas vectorizadas se sellaban como
    # `A_normativo` —la etiqueta de más peso— junto al vectorial del MINVU, que
    # el organismo sí publica y que sí tiene efecto legal por sí mismo. El
    # docstring del script 18 prometía esta etiqueta desde el principio; el
    # `assert` la rechazaba, así que quedaba la de más peso por omisión.
    assert capa_evidencia in ("A_normativo", "A_derivado", "B_observado",
                              "C_modelado", "D_operacional", "inventario"), (
        f"capa de evidencia desconocida: {capa_evidencia!r}")
    return {
        "fuente": fuente,
        "url": url,
        "metodo": metodo,
        "capa_evidencia": capa_evidencia,
        "incertidumbre": incertidumbre,
        "escala_original": escala_original,
        "fecha_dato": fecha_dato,
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def escribir_geojson(features: list[dict], destino: Path, meta: dict) -> Path:
    """Escribe un FeatureCollection con el bloque de procedencia en la raíz."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection", "procedencia": meta, "features": features}
    destino.write_text(
        json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    kb = destino.stat().st_size / 1024
    log(f"  escrito: {destino.relative_to(RAIZ)} — {len(features)} features, {kb:.0f} KB")
    return destino


def slug(texto: str) -> str:
    """Normaliza un nombre de comuna a identificador de archivo."""
    import unicodedata

    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "-".join(t.lower().split())


def utm_para(lon: float, cfg: dict) -> str:
    """Devuelve el EPSG UTM correcto según la longitud.

    La Araucanía está partida por el meridiano 72°W: Temuco y la costa caen en
    18S, pero Pucón, Curarrehue y Lonquimay caen en 19S. Usar un solo huso para
    toda la región mete error de varios cientos de metros en la cordillera.
    """
    u = cfg["region"]["utm"]
    return u["cordillera"] if lon >= u["limite_lon"] else u["principal"]
