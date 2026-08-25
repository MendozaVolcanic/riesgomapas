"""Capa A — encontrar la lámina de inundación DENTRO de los informes.

El problema real del proyecto en una frase: la cartografía de riesgo de
inundación de cada comuna existe, es pública y está en la página 87 de un PDF de
300 páginas que nadie abre. Buscarla a mano, comuna por comuna, es lo que hace
que esta información no llegue a nadie.

Este script convierte esos 411 documentos de La Araucanía en un índice
consultable: para cada PDF, qué páginas hablan de inundación y cuáles de esas
páginas son además una lámina cartográfica y no texto corrido.

No adivina: entrega candidatos con evidencia (los términos encontrados, cuánto
texto tiene la página, si trae imágenes) para que una persona confirme antes de
invertir tiempo en georreferenciar.

Prioridad de descarga, de mayor a menor rendimiento:
  1. `*Planos*`        — son las láminas del anteproyecto, cartografía pura
  2. `*Anteproyecto*`  — memoria explicativa, suele traer figuras de riesgo
  3. `*IA*`            — Informe Ambiental, capítulo de riesgos

Uso:
    python 07_buscar_laminas_riesgo.py --solo-listar
    python 07_buscar_laminas_riesgo.py --prioridad planos --max-mb 60
    python 07_buscar_laminas_riesgo.py --comuna Angol
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

import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import DATA_PROC, DATA_RAW, _CTX, UA, log  # noqa: E402

TERMINOS = ["inundacion", "inundable", "anegamiento", "anegable", "desborde",
            "crecida", "area de riesgo", "zona de riesgo", "cauce", "quebrada"]

PRIORIDAD = {
    "planos": re.compile(r"planos", re.I),
    "anteproyecto": re.compile(r"anteproyecto", re.I),
    "ia": re.compile(r"_ia[-_]|informe", re.I),
}


def tareas_municipales() -> list[dict]:
    """Documentos bajados directamente de sitios municipales (script 03).

    Van por una vía distinta al registro EAE porque ninguna de las dos es
    completa: el municipio publica el Estudio Fundado de Riesgos —el estudio que
    fundamenta la zonificación— y el registro EAE publica el expediente del
    procedimiento. Conviene tener ambas.
    """
    import importlib.util

    ruta = Path(__file__).resolve().parent / "03_descargar_documentos.py"
    spec = importlib.util.spec_from_file_location("g3", ruta)
    g3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g3)

    out, vistos = [], set()
    for d in g3.DOCUMENTOS:
        local = DATA_RAW / "documentos" / d["comuna"] / f"{d['id']}.pdf"
        if not local.exists():
            continue
        vistos.add(local.resolve())
        out.append({
            "comuna": d["comuna"].replace("-", " ").title(),
            "procedimiento": d["titulo"],
            "codigo": d["id"],
            "archivo": local.name,
            "url": d["url"],
            "anio": d.get("anio"),
            "_local": local,
        })

    # Todo lo que haya en data/raw/documentos/, venga de donde venga.
    #
    # La fuente de verdad es el DISCO, no el índice del cosechador: ese índice se
    # puede quedar atrás o quedar sobrescrito por una corrida parcial, y el
    # síntoma es silencioso —el escáner ve 5 documentos donde hay 92 y nadie se
    # entera—. El índice sólo se usa para recuperar la URL de origen.
    urls: dict[str, dict] = {}
    hallazgos = DATA_PROC / "municipios" / "hallazgos.json"
    if hallazgos.exists():
        try:
            for h in json.loads(hallazgos.read_text(encoding="utf-8")):
                if h.get("archivo_local"):
                    urls[str((DATA_RAW / h["archivo_local"]).resolve())] = h
        except Exception:  # noqa: BLE001
            pass

    for local in sorted((DATA_RAW / "documentos").rglob("*.pdf")):
        clave = str(local.resolve())
        if local.resolve() in vistos:
            continue
        vistos.add(local.resolve())
        h = urls.get(clave, {})
        out.append({
            "comuna": (h.get("comuna") or local.parent.name.replace("-", " ")).title(),
            "procedimiento": h.get("titulo") or local.stem.replace("-", " ").replace("_", " "),
            "codigo": "sitio municipal",
            "archivo": local.name,
            "url": h.get("url", ""),
            "anio": (h.get("fecha_subida") or "")[:4] or None,
            "_local": local,
        })
    return out


def norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


# A4 son ~501.000 pt². Por encima de este umbral la hoja ya es formato de plano.
AREA_PLOTER = 1_000_000
OBJETOS_MIN_PLOTER = 200
FRAC_IMAGEN_MIN = 0.18
TEXTO_MAX_RASTER = 1500


def clasificar_lamina(area: float, caracteres: int, n_img: int, n_trazo: int,
                      n_texto: int, frac_img: float,
                      fallo_caja: bool = False) -> str | None:
    """Decide si una página es cartografía, y de qué tipo. None = no es lámina.

    Hay DOS tipos de lámina y el detector inicial sólo veía una:

    (a) **Plano de plóter**: hoja enorme (4252x1700 pt ≈ 150x60 cm) con miles de
        trazos vectoriales y de rótulos. Tiene MUCHO texto —son las etiquetas del
        mapa—, así que el criterio "poco texto" lo descartaba justo al revés de
        lo que corresponde.
    (b) **Lámina rasterizada** dentro de un informe tamaño carta: poca letra y una
        imagen que ocupa buena parte de la hoja.

    Para (b) no basta con que exista una imagen: el logo del pie de página de la
    consultora aparece en TODAS las hojas y convertía cualquier página de texto
    corto en "lámina". Se exige que la imagen cubra una fracción sustantiva.

    `fallo_caja` indica que no se pudo medir ninguna imagen; en ese caso se cae al
    criterio antiguo, más laxo, para no perder la lámina en silencio.
    """
    if area > AREA_PLOTER and (n_trazo + n_texto + n_img) >= OBJETOS_MIN_PLOTER:
        return "plano"
    if area <= AREA_PLOTER and caracteres < TEXTO_MAX_RASTER and (
            frac_img >= FRAC_IMAGEN_MIN or (fallo_caja and n_img >= 1)):
        return "raster"
    return None


def _caja(obj) -> tuple[float, float, float, float] | None:
    """Rectángulo de un objeto de página, tolerando el nombre del método.

    En pypdfium2 los objetos exponen `get_bounds()`; versiones distintas han
    usado `get_pos()`. Se prueban ambos y se devuelve None si ninguno responde,
    para que quien llama pueda avisar en vez de asumir 'la imagen mide cero'.
    """
    for nombre in ("get_bounds", "get_pos"):
        m = getattr(obj, nombre, None)
        if m is None:
            continue
        try:
            v = m()
            if v and len(v) == 4:
                return tuple(float(x) for x in v)
        except Exception:  # noqa: BLE001
            continue
    return None


def tamano(url: str) -> int | None:
    """HEAD previo: evita empezar a bajar un PDF de 800 MB para descubrirlo después."""
    try:
        req = urllib.request.Request(
            urllib.parse.quote(url, safe=":/?&=%,*"), method="HEAD",
            headers={"User-Agent": UA})
        with urllib.request.urlopen(req, context=_CTX, timeout=60) as r:
            n = r.headers.get("Content-Length")
            return int(n) if n else None
    except Exception:  # noqa: BLE001
        return None


def bajar(url: str, destino: Path) -> Path | None:
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(urllib.parse.quote(url, safe=":/?&=%,*"),
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, context=_CTX, timeout=600) as r:
            datos = r.read()
    except Exception as exc:  # noqa: BLE001
        log(f"    descarga falló: {str(exc)[:70]}")
        return None
    if not datos.startswith(b"%PDF-"):
        log(f"    no es PDF (magic {datos[:8]!r})")
        return None
    destino.write_bytes(datos)
    return destino


def escanear(pdf: Path) -> list[dict]:
    """Devuelve las páginas que mencionan amenaza hídrica, con su evidencia."""
    try:
        doc = pdfium.PdfDocument(str(pdf))
    except Exception as exc:  # noqa: BLE001
        log(f"    no se pudo abrir: {str(exc)[:60]}")
        return []
    hits = []
    try:
        for i in range(len(doc)):
            pag = doc[i]
            try:
                txt = pag.get_textpage().get_text_bounded() or ""
            except Exception:  # noqa: BLE001
                txt = ""
            n = norm(txt)
            encontrados = [t for t in TERMINOS if t in n]
            if not encontrados:
                continue
            # Tipos de objeto de pdfium: 1 = TEXTO, 2 = TRAZO (path), 3 = IMAGEN,
            # 4 = sombreado, 5 = form. (Ojo: es fácil invertir 1 y 2.)
            largo = len(txt.strip())
            ancho, alto = pag.get_size()
            area = ancho * alto

            n_img = n_trazo = n_texto = 0
            frac_img_mayor = 0.0
            fallo_caja = False
            try:
                for o in pag.get_objects():
                    if o.type == 3:
                        n_img += 1
                        # No basta con que haya una imagen: el logo del pie de
                        # página de la consultora aparece en TODAS las hojas y
                        # convertía cualquier página de texto corto en "lámina".
                        # Lo que distingue a una lámina es que la imagen ocupe
                        # una parte sustantiva de la hoja.
                        caja = _caja(o)
                        if caja is None:
                            fallo_caja = True
                        else:
                            l, b, r, t = caja
                            frac_img_mayor = max(frac_img_mayor,
                                                 abs((r - l) * (t - b)) / area)
                    elif o.type == 2:
                        n_trazo += 1
                    elif o.type == 1:
                        n_texto += 1
            except Exception:  # noqa: BLE001
                pass

            tipo = clasificar_lamina(area, largo, n_img, n_trazo, n_texto,
                                     frac_img_mayor, fallo_caja)

            hits.append({
                "pagina": i + 1,
                "terminos": encontrados,
                "caracteres": largo,
                "imagenes": n_img,
                "fraccion_imagen": round(frac_img_mayor, 3),
                "trazos": n_trazo,
                "objetos_texto": n_texto,
                "cm": [round(ancho / 28.35), round(alto / 28.35)],
                "apaisada": ancho > alto,
                "tipo_lamina": tipo,
                "es_probable_lamina": tipo is not None,
            })
    finally:
        doc.close()
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prioridad",
                    choices=["planos", "anteproyecto", "ia", "todo", "municipales"],
                    default="planos")
    ap.add_argument("--comuna", help="filtrar por comuna")
    ap.add_argument("--max-mb", type=float, default=80.0,
                    help="omitir documentos más grandes que esto")
    ap.add_argument("--limite", type=int, default=40, help="máximo de PDFs a procesar")
    ap.add_argument("--solo-listar", action="store_true")
    a = ap.parse_args()

    if a.prioridad == "municipales":
        tareas = tareas_municipales()
        if a.comuna:
            tareas = [t for t in tareas if norm(a.comuna) in norm(t["comuna"])]
    else:
        idx = DATA_PROC / "eae" / "araucania.json"
        if not idx.exists():
            raise SystemExit(
                "falta data/processed/eae/araucania.json — corre antes el script 05")
        procs = json.loads(idx.read_text(encoding="utf-8"))
        tareas = []
        for p in procs:
            if a.comuna and norm(a.comuna) not in norm(p["comunas"]):
                continue
            for d in p["documentos"]:
                if a.prioridad != "todo" and not PRIORIDAD[a.prioridad].search(d["archivo"]):
                    continue
                tareas.append({"comuna": p["comunas"], "procedimiento": p["nombre"],
                               "codigo": p["codigo"], **d})
    log(f"{len(tareas)} documentos coinciden con prioridad='{a.prioridad}'"
        + (f", comuna='{a.comuna}'" if a.comuna else ""))

    if a.solo_listar:
        for t in tareas:
            log(f"  {t['comuna'][:20]:22s} {t['archivo'][:80]}")
        return

    salida, procesados, omitidos = [], 0, 0
    for t in tareas:
        if procesados >= a.limite:
            log(f"límite de {a.limite} documentos alcanzado — quedan "
                f"{len(tareas) - procesados - omitidos} sin procesar")
            break
        n = tamano(t["url"])
        mb = (n or 0) / 1e6
        if n and mb > a.max_mb:
            log(f"  omitido ({mb:.0f} MB > {a.max_mb:.0f}): {t['archivo'][:60]}")
            omitidos += 1
            continue
        log(f"[{procesados + 1}] {t['comuna'][:18]:20s} {t['archivo'][:56]} ({mb:.0f} MB)")
        if t.get("_local"):
            pdf = t["_local"]          # ya lo bajó el script 03
        else:
            destino = DATA_RAW / "eae" / norm(t["comuna"]).replace(" ", "-") / t["archivo"]
            pdf = bajar(t["url"], destino)
            time.sleep(0.4)
        if not pdf:
            continue
        procesados += 1
        hits = escanear(pdf)
        laminas = [h for h in hits if h["es_probable_lamina"]]
        log(f"      {len(hits)} páginas mencionan amenaza hídrica, "
            f"{len(laminas)} parecen lámina cartográfica")
        for h in laminas[:5]:
            log(f"        p{h['pagina']:<4d} {h['tipo_lamina']:6s} "
                f"{h['cm'][0]}x{h['cm'][1]} cm  {'|'.join(h['terminos'][:4])}")
        salida.append({**{k: t[k] for k in
                          ("comuna", "procedimiento", "codigo", "archivo", "url")},
                       "archivo_local": str(pdf.relative_to(DATA_RAW)),
                       "mb": round(mb, 1),
                       "paginas_con_amenaza": hits,
                       "n_laminas_candidatas": len(laminas)})

    # Se FUSIONA con lo que ya había, no se reemplaza.
    #
    # Este script casi nunca procesa el corpus entero: `--limite` vale 40 por
    # omisión y los documentos municipales pasan de 150, así que hasta la corrida
    # normal —sin `--comuna` ni ningún filtro— dejaba fuera todo lo que no
    # alcanzó a mirar. Y lo que quedaba fuera no era «pendiente»: desaparecía del
    # índice, y con él del catálogo público que arma el script 09. El síntoma es
    # mudo: no hay error, sólo comunas que dejan de existir.
    #
    # Es la cuarta vez que este patrón muerde al proyecto. La clave es la ruta
    # local del PDF, que identifica al documento sin depender de la URL.
    dest = DATA_PROC / "eae" / f"laminas_candidatas_{a.prioridad}.json"
    previo: dict[str, dict] = {}
    if dest.exists():
        try:
            for x in json.loads(dest.read_text(encoding="utf-8")):
                previo[x.get("archivo_local") or x.get("archivo")] = x
        except Exception as exc:  # noqa: BLE001
            # Un índice ilegible es motivo para parar, no para reescribirlo desde
            # cero: seguir adelante lo borraría en silencio, que es justo el daño
            # que esta fusión existe para evitar.
            raise SystemExit(
                f"{dest} existe pero no se puede leer ({type(exc).__name__}: {exc}). "
                "Revísalo o muévelo a mano; no se reescribe automáticamente para "
                "no perder lo que ya estaba indexado.")
    antes = len(previo)
    for x in salida:
        previo[x.get("archivo_local") or x.get("archivo")] = x
    fusionado = list(previo.values())
    dest.write_text(json.dumps(fusionado, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"índice: {antes} documento(s) previos + {len(salida)} de esta corrida "
        f"= {len(fusionado)} en total")
    salida = fusionado

    total_lam = sum(x["n_laminas_candidatas"] for x in salida)
    con = [x for x in salida if x["n_laminas_candidatas"]]
    log("")
    log(f"RESULTADO: {procesados} PDFs revisados, {omitidos} omitidos por tamaño")
    log(f"  {len(con)} documentos contienen láminas candidatas")
    log(f"  {total_lam} láminas candidatas en total")
    log(f"  índice: {dest.relative_to(DATA_PROC.parent.parent)}")
    log("")
    for x in sorted(con, key=lambda y: -y["n_laminas_candidatas"])[:15]:
        pgs = [h["pagina"] for h in x["paginas_con_amenaza"] if h["es_probable_lamina"]]
        log(f"  {x['comuna'][:18]:20s} {x['n_laminas_candidatas']:3d} láminas  "
            f"p{pgs[:6]}  {x['archivo'][:44]}")


if __name__ == "__main__":
    main()
