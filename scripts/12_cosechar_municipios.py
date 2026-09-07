"""Barrido de los sitios municipales en busca de estudios de riesgo.

Por qué hace falta además del registro EAE: las dos vías publican cosas
distintas. El registro ambiental tiene el expediente del procedimiento
(anteproyecto, planos, informes ambientales); el municipio publica el **Estudio
Fundado de Riesgos**, que es el estudio que fundamenta la zonificación y trae el
análisis de amenaza con más detalle. Ninguna de las dos es completa.

Cómo funciona:

1. **Descubre el dominio** de cada municipalidad probando los patrones que usan
   en Chile (`municipalidad<comuna>.cl`, `muni<comuna>.cl`, `<comuna>.cl`, …) y
   verificando cuál responde. Es más barato y más reproducible que buscar a mano
   32 veces, y deja constancia de cuáles no se encontraron.
2. **Rastrea el sitio** a poca profundidad siguiendo sólo enlaces que parezcan
   llevar a instrumentos de planificación, y recoge los PDF.
3. **Filtra por nombre** con el vocabulario del rubro y verifica que sean PDF de
   verdad antes de quedárselos.

Es deliberadamente conservador con los sitios del Estado: un hilo, pausa entre
peticiones y profundidad 2. No es un scraper masivo, es un barrido de cortesía.

Requiere: nada (descubre los dominios municipales solo; sólo relee su propia
        caché en data/processed/municipios/ si ya existe)
Salida: config/municipios.yaml           (dominios descubiertos, editable a mano)
        data/processed/municipios/hallazgos.json
        data/raw/documentos/<comuna>/<archivo>.pdf
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import CONFIG, DATA_PROC, DATA_RAW, UA, _CTX, cargar_config, log  # noqa: E402

PAUSA = 0.7          # cortesía con sitios municipales, que suelen ser modestos
PROFUNDIDAD = 2
MAX_PAGINAS = 60
TIEMPO_MAX = 40

# Vocabulario del rubro. Amplio a propósito: es más barato descartar un falso
# positivo que perder el único estudio de riesgo de una comuna.
CLAVES_DOC = [
    "riesgo", "riesgos", "inunda", "anegam", "amenaza", "peligro",
    "plan-regulador", "plan_regulador", "planregulador", "prc",
    "aguas-lluvia", "aguaslluvia", "fundado", "zonificacion",
    # gestión del riesgo de desastres (Ley 21.364) y cambio climático (21.455).
    # Ver la nota extensa en BUSQUEDAS_WP: son los mismos peligros bajo otro
    # marco legal, con nombres de archivo que no comparten ni una palabra con
    # los del plan regulador.
    "rrd", "reduccion-del-riesgo", "reduccion_del_riesgo", "desastre",
    "emergencia", "proteccion-civil", "pladeco", "evacuacion",
    "cambio-climatico", "cambio_climatico", "climatico", "paccc",
    "vulnerabilidad", "defensa-fluvial", "ribera", "desborde", "drenaje",
]
# Palabras que sólo valen ACOMPAÑADAS. Una municipalidad publica decenas de
# ordenanzas y memorias que no tienen nada que ver: la de tenencia de mascotas,
# la de medio ambiente (50 MB), la memoria anual de gestión. Sin esta distinción
# el barrido se llena de ruido pesado.
CLAVES_CONDICIONALES = ["ordenanza", "memoria", "decreto", "plano"]
CLAVES_CONTEXTO = ["regulador", "prc", "riesgo", "urban", "territorial",
                   "zonificacion", "inunda", "seccional"]
# Enlaces que vale la pena seguir para llegar a esos documentos.
CLAVES_ENLACE = [
    "plan", "regulador", "territorial", "urbanismo", "obras", "transparencia",
    "documento", "descarga", "instrumento", "ordenanza", "riesgo", "prc",
]

PATRONES_DOMINIO = [
    "municipalidad{c}.cl", "muni{c}.cl", "{c}.cl", "imunicipalidad{c}.cl",
    "municipalidadde{c}.cl", "municipalidad-{c}.cl", "muni-{c}.cl",
    "ilustremunicipalidad{c}.cl",
    "m{c}.cl",        # Lonquimay usa mlonquimay.cl
    "www.{c}.cl", "imuni{c}.cl",
]


def slug(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", t)


def slug_guion(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def pedir(url: str, timeout: int = TIEMPO_MAX) -> tuple[int, bytes, str]:
    req = urllib.request.Request(
        urllib.parse.quote(url, safe=":/?&=%,*#@+$;~"),
        headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, context=_CTX, timeout=timeout) as r:
        return r.status, r.read(), r.headers.get("Content-Type", "")


# ------------------------------------------------------------ descubrimiento

def descubrir(comuna: str) -> str | None:
    """Prueba los patrones habituales y devuelve el primero que responde HTML."""
    s = slug(comuna)
    for patron in PATRONES_DOMINIO:
        host = patron.format(c=s)
        for esquema in ("https", "http"):
            url = f"{esquema}://{host}/"
            try:
                cod, cuerpo, tipo = pedir(url, timeout=18)
            except Exception:  # noqa: BLE001
                continue
            if cod == 200 and "html" in tipo.lower() and len(cuerpo) > 800:
                return url
            time.sleep(0.1)
    return None


def cargar_o_descubrir(cfg: dict, forzar: bool) -> dict:
    ruta = CONFIG / "municipios.yaml"
    datos = {}
    if ruta.exists() and not forzar:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    sitios = datos.get("sitios", {})

    comunas = [c for prov in cfg["provincias"].values() for c in prov]
    faltan = [c for c in comunas if c not in sitios]
    if faltan:
        log(f"descubriendo dominio de {len(faltan)} comuna(s)…")
        for c in faltan:
            url = descubrir(c)
            sitios[c] = url
            log(f"  {c:20s} {url or '— no encontrado con los patrones habituales'}")
    ruta.write_text(yaml.safe_dump(
        {"_nota": "Dominios de las municipalidades. Los que quedaron en null hay "
                  "que completarlos a mano: el patrón de dominio no acertó, pero "
                  "el sitio puede existir.",
         "sitios": sitios}, allow_unicode=True, sort_keys=True), encoding="utf-8")
    return sitios


# ------------------------------------------------------------------ rastreo

def interesante_enlace(href: str) -> bool:
    h = slug_guion(urllib.parse.unquote(href))
    return any(k in h for k in CLAVES_ENLACE)


def interesante_doc(href: str) -> bool:
    h = slug_guion(urllib.parse.unquote(href))
    if RUIDO_NOMBRE.search(h):
        return False
    if any(k in h for k in CLAVES_DOC):
        return True
    # "ordenanza", "memoria", "decreto" o "plano" sólo cuentan si además hay algo
    # que los ate a planificación territorial.
    return (any(k in h for k in CLAVES_CONDICIONALES)
            and any(k in h for k in CLAVES_CONTEXTO))


# Términos con que se consulta la biblioteca de medios. Son los que aparecen en
# los nombres reales de estos documentos, no sinónimos genéricos.
#
# Las tres familias están acá a propósito, porque el municipio publica la misma
# amenaza bajo tres marcos legales distintos y con vocabularios que no se tocan:
#
#   1. Planificación territorial (Ley General de Urbanismo). El Estudio Fundado
#      de Riesgos que sostiene la zonificación del plan regulador.
#   2. Gestión del riesgo de desastres (Ley 21.364, 2021). El Plan Comunal para
#      la Reducción del Riesgo de Desastres y el plan de emergencia comunal.
#   3. Cambio climático (Ley 21.455, 2022). El Plan de Acción Comunal de Cambio
#      Climático (PACCC), que trae diagnóstico de amenazas y sus láminas.
#
# La primera versión de este cosechador sólo tenía el vocabulario de la familia 1
# y pasaba por encima de las otras dos sin verlas. Al agregarlas aparecieron 31
# documentos —el plan de RRD de Lautaro, el PACCC de Collipulli con su lámina de
# vulnerabilidad en A3, el plan de cambio climático de Lonquimay— y dos comunas
# que figuraban «sin cartografía» dejaron de estarlo. Un plan reciente pesa más
# que uno viejo: los de las familias 2 y 3 son de 2024-2026 y por tanto
# posteriores a casi todo el registro EAE.
BUSQUEDAS_WP = [
    # 1 · planificación territorial
    "riesgo", "riesgos", "inundacion", "anegamiento", "plan regulador",
    "prc", "aguas lluvias", "memoria explicativa", "ordenanza", "zonificacion",
    "amenaza", "estudio fundado",
    # 2 · gestión del riesgo de desastres
    "reduccion del riesgo", "gestion del riesgo", "proteccion civil",
    "emergencia", "desastre", "plan comunal", "pladeco", "evacuacion",
    # 3 · cambio climático
    "cambio climatico", "climatico", "paccc", "adaptacion", "vulnerabilidad",
    # 4 · obras y cauces
    "defensa fluvial", "ribera", "cauce", "drenaje", "desborde", "mitigacion",
]

# "emergencia", "adaptacion" y "vulnerabilidad" son necesarias pero traen ruido
# propio: compras de vehículos de emergencia, bases de concurso para jefaturas de
# protección civil, el Ingreso Familiar de Emergencia. Se descartan por nombre
# antes de gastar una descarga.
RUIDO_NOMBRE = re.compile(
    r"(vehiculo|bases?-jefatura|ingreso-familiar|nota-de-prensa|costos-operacion"
    r"|llamado-a-concurso|acta-de-evaluacion)", re.I)


def cosechar_wp(base: str) -> tuple[list[dict], bool]:
    """Consulta la biblioteca de medios de WordPress por palabra clave.

    Casi todos los sitios municipales chilenos son WordPress y dejan abierto
    `/wp-json/wp/v2/media`, que permite **buscar directamente entre los archivos
    subidos**. Es mucho más efectivo que rastrear enlaces —el rastreo a
    profundidad 2 devolvía cero en Temuco, que sí tiene los documentos— y es más
    considerado con el sitio: una decena de consultas a la API en vez de sesenta
    descargas de páginas.

    Devuelve (documentos, hay_api) para poder caer al rastreo cuando no la haya.
    """
    encontrados: dict[str, dict] = {}
    hay_api = False
    for termino in BUSQUEDAS_WP:
        # Sin `media_type=application`: ese filtro descarta resultados válidos
        # —en Galvarino la misma búsqueda pasa de 2 documentos a 0— porque no
        # todos los sitios clasifican los PDF con ese tipo. Se filtra por la
        # extensión de la URL más abajo, que es lo que de verdad importa.
        url = (f"{base.rstrip('/')}/wp-json/wp/v2/media"
               f"?search={urllib.parse.quote(termino)}&per_page=100"
               f"&_fields=source_url,title,date")
        try:
            cod, cuerpo, tipo = pedir(url, timeout=30)
        except Exception:  # noqa: BLE001
            continue
        if cod != 200 or "json" not in tipo.lower():
            continue
        hay_api = True
        try:
            datos = json.loads(cuerpo.decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(datos, list):
            continue
        for it in datos:
            u = (it.get("source_url") or "")
            if not u.lower().endswith(".pdf"):
                continue
            if u not in encontrados:
                titulo = (it.get("title") or {}).get("rendered") or ""
                encontrados[u] = {
                    "url": u, "encontrado_en": f"wp-json (buscando «{termino}»)",
                    "titulo": re.sub(r"<[^>]+>", "", titulo).strip() or None,
                    "fecha_subida": (it.get("date") or "")[:10] or None,
                }
        time.sleep(PAUSA / 2)
    return list(encontrados.values()), hay_api


def rastrear(base: str, comuna: str) -> list[dict]:
    vistas: set[str] = set()
    pdfs: dict[str, dict] = {}
    cola = [(base, 0)]
    host = urllib.parse.urlparse(base).netloc

    while cola and len(vistas) < MAX_PAGINAS:
        url, prof = cola.pop(0)
        if url in vistas or prof > PROFUNDIDAD:
            continue
        vistas.add(url)
        try:
            cod, cuerpo, tipo = pedir(url)
        except Exception:  # noqa: BLE001
            continue
        time.sleep(PAUSA)
        if cod != 200 or "html" not in tipo.lower():
            continue
        html = cuerpo.decode("utf-8", "replace")

        for m in re.finditer(r'href=["\']([^"\'#]+)', html, re.I):
            href = urllib.parse.urljoin(url, m.group(1))
            p = urllib.parse.urlparse(href)
            if p.netloc and p.netloc != host:
                continue          # no salir del sitio municipal
            if href.lower().split("?")[0].endswith(".pdf"):
                if interesante_doc(href) and href not in pdfs:
                    pdfs[href] = {"url": href, "encontrado_en": url}
            elif prof < PROFUNDIDAD and interesante_enlace(href):
                cola.append((href, prof + 1))

    return list(pdfs.values())


def tamano(url: str) -> int | None:
    """HEAD previo, para no empezar a bajar un PDF de 50 MB y arrepentirse."""
    try:
        req = urllib.request.Request(
            urllib.parse.quote(url, safe=":/?&=%,*#@+$;~"), method="HEAD",
            headers={"User-Agent": UA})
        with urllib.request.urlopen(req, context=_CTX, timeout=30) as r:
            n = r.headers.get("Content-Length")
            return int(n) if n else None
    except Exception:  # noqa: BLE001
        return None


def bajar(doc: dict, comuna: str, max_mb: float) -> dict:
    nombre = urllib.parse.unquote(doc["url"].rsplit("/", 1)[-1].split("?")[0])
    destino = DATA_RAW / "documentos" / slug_guion(comuna) / nombre
    if destino.exists() and destino.stat().st_size > 0:
        return {**doc, "archivo_local": str(destino.relative_to(DATA_RAW)),
                "kb": round(destino.stat().st_size / 1024), "estado": "ya estaba"}
    n = tamano(doc["url"])
    if n and n / 1e6 > max_mb:
        return {**doc, "estado": f"omitido: {n / 1e6:.0f} MB supera el tope de {max_mb:.0f} MB",
                "kb": round(n / 1024)}
    try:
        cod, datos, _ = pedir(doc["url"], timeout=180)
    except Exception as exc:  # noqa: BLE001
        return {**doc, "estado": f"error: {str(exc)[:60]}"}
    if not datos.startswith(b"%PDF-"):
        return {**doc, "estado": "no es un PDF pese a la extensión"}
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)
    return {**doc, "archivo_local": str(destino.relative_to(DATA_RAW)),
            "kb": round(len(datos) / 1024), "estado": "descargado"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--comuna", help="sólo esta comuna")
    ap.add_argument("--redescubrir", action="store_true",
                    help="vuelve a probar los dominios en vez de leer el YAML")
    ap.add_argument("--solo-listar", action="store_true",
                    help="rastrea y lista, sin descargar")
    ap.add_argument("--max-mb", type=float, default=40,
                    help="omitir PDF más pesados que esto (MB)")
    a = ap.parse_args()

    cfg = cargar_config()
    sitios = cargar_o_descubrir(cfg, a.redescubrir)

    objetivo = {c: u for c, u in sitios.items() if u}
    if a.comuna:
        objetivo = {c: u for c, u in objetivo.items()
                    if slug(a.comuna) in slug(c)}
    log("")
    log(f"{len(objetivo)} sitio(s) municipal(es) a rastrear "
        f"(de {len(sitios)} comunas)")

    resultados = []
    for comuna, url in sorted(objetivo.items()):
        log(f"{comuna} — {url}")
        # Primero la API de medios; sólo si el sitio no la expone se rastrea.
        try:
            docs, hay_api = cosechar_wp(url)
        except Exception as exc:  # noqa: BLE001
            log(f"  API de medios falló: {str(exc)[:70]}")
            docs, hay_api = [], False
        via = "wp-json"
        if not hay_api:
            try:
                docs = rastrear(url, comuna)
                via = "rastreo de enlaces"
            except Exception as exc:  # noqa: BLE001
                log(f"  rastreo falló: {str(exc)[:80]}")
                continue
        # Se filtra por vocabulario también lo que viene de la API: la búsqueda
        # de WordPress mira el título, y el nombre del archivo puede no tener
        # nada que ver con lo que buscamos.
        docs = [d for d in docs if interesante_doc(d["url"]) or
                (d.get("titulo") and interesante_doc(d["titulo"]))]
        log(f"  {len(docs)} PDF de interés (vía {via})")
        for d in docs:
            if a.solo_listar:
                log(f"    {d['url'].rsplit('/', 1)[-1][:82]}")
                resultados.append({**d, "comuna": comuna, "estado": "listado"})
                continue
            r = bajar(d, comuna, a.max_mb)
            r["comuna"] = comuna
            resultados.append(r)
            marca = {"descargado": "+", "ya estaba": "="}.get(r["estado"], "x")
            log(f"    [{marca}] {Path(d['url']).name[:66]} "
                f"({r.get('kb', 0)} KB)")
            time.sleep(PAUSA)

    destino = DATA_PROC / "municipios"
    destino.mkdir(parents=True, exist_ok=True)
    registro = destino / "hallazgos.json"
    # Se FUSIONA con lo anterior. Correr el script para una sola comuna —para
    # probar o reintentar— no puede borrar el resultado de las otras 31; ya pasó
    # una vez y dejó el escáner de láminas viendo 5 documentos en vez de 92.
    previos: dict[str, dict] = {}
    if registro.exists():
        try:
            for r in json.loads(registro.read_text(encoding="utf-8")):
                previos[r["url"]] = r
        except Exception:  # noqa: BLE001
            pass
    for r in resultados:
        previos[r["url"]] = r
    registro.write_text(
        json.dumps(sorted(previos.values(), key=lambda r: (r.get("comuna") or "", r["url"])),
                   ensure_ascii=False, indent=1), encoding="utf-8")
    resultados = list(previos.values())

    bajados = [r for r in resultados if r.get("estado") in ("descargado", "ya estaba")]
    sin_sitio = [c for c, u in sitios.items() if not u]
    log("")
    log(f"RESULTADO: {len(resultados)} documentos hallados, {len(bajados)} disponibles")
    log(f"  comunas con sitio: {len(objetivo)} · sin dominio detectado: {len(sin_sitio)}")
    if sin_sitio:
        log(f"  completar a mano en config/municipios.yaml: {', '.join(sorted(sin_sitio))}")
    por_comuna: dict[str, int] = {}
    for r in bajados:
        por_comuna[r["comuna"]] = por_comuna.get(r["comuna"], 0) + 1
    for c, n in sorted(por_comuna.items(), key=lambda t: -t[1]):
        log(f"    {n:3d}  {c}")


if __name__ == "__main__":
    main()
