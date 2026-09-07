"""Capa A paso 0 — rastrear el registro de Evaluación Ambiental Estratégica.

Este es el atajo al problema de fondo del proyecto: la cartografía de riesgo de
inundación existe, es pública, y está sepultada dentro de informes que nadie
abre. Encontrarla comuna por comuna a mano es inviable.

La palanca: **todo Plan Regulador Comunal en Chile debe pasar por Evaluación
Ambiental Estratégica**, y el Ministerio del Medio Ambiente publica cada
procedimiento con sus documentos adjuntos en un portal único.

    https://eae.mma.gob.cl/reporte-general   -> tabla nacional de procedimientos
    https://eae.mma.gob.cl/file/<id>         -> ficha con los PDF adjuntos

Es decir: un solo portal da acceso a los expedientes de planificación de todo el
país, sin autenticación. No hay índice de documentos ni buscador de texto — por
eso este script arma el índice que falta.

Requiere: nada (rastrea eae.mma.gob.cl directo; sólo relee su propia caché en
        data/processed/eae/indice_nacional.json si ya existe)
Salida: data/processed/eae/indice_nacional.json
        data/processed/eae/araucania.json
        data/processed/eae/araucania.csv   (para revisar a ojo qué vale la pena bajar)
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import DATA_PROC, log  # noqa: E402
from comun import _CTX, UA  # noqa: E402

import urllib.request  # noqa: E402

BASE = "https://eae.mma.gob.cl"
ID_MAX = 700          # el portal tenía 536 fichas en ago-2026; se deja holgura
PAUSA = 0.35          # cortesía con un sitio del Estado: ~3 req/s como techo

# Palabras que hacen probable que un documento contenga cartografía de riesgo.
# Deliberadamente amplio: es más barato revisar un falso positivo que perder el
# único plano de inundación de una comuna.
CLAVES_RIESGO = [
    "riesgo", "inunda", "anegam", "amenaza", "peligro", "aluvi", "remocion",
    "crecida", "hidrolog", "hidraul", "aguas lluvia", "cauce", "fundado",
]
# Los Informes Ambientales suelen traer el capítulo de riesgos y sus figuras.
CLAVES_INFORME = ["informe ambiental", "_ia_", "ia_prc", "anteproyecto", "diagnostico"]


def norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def get(url: str, intentos: int = 3) -> str | None:
    u = urllib.parse.quote(url, safe=":/?&=%,*#@+$;~")
    for i in range(intentos):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, context=_CTX, timeout=60) as r:
                # Cuando la ficha no existe el portal redirige a la portada.
                if r.url.rstrip("/") == BASE:
                    return None
                return r.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            time.sleep(1.5 * (i + 1))
    return None


def texto_plano(h: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


# --------------------------------------------------------- reporte nacional

def leer_reporte() -> list[dict]:
    """Tabla nacional de procedimientos: código, nombre, región, comunas."""
    h = get(f"{BASE}/reporte-general")
    if not h:
        raise SystemExit("no se pudo leer el reporte general de EAE")
    tabla = h[h.find("<table"):h.find("</table>")]
    campos = ["fecha", "codigo", "nombre", "instrumento", "region", "provincia",
              "comunas", "escala", "organismo", "oficina", "docs_diseno",
              "docs_aprobacion", "docs_termino", "procedimiento_actual"]
    filas = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tabla, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) < len(campos):
            continue
        vals = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))).strip()
                for t in tds[:len(campos)]]
        filas.append(dict(zip(campos, vals)))
    log(f"reporte nacional: {len(filas)} procedimientos EAE")
    return filas


# ------------------------------------------------------------ fichas /file

def leer_ficha(idf: int) -> dict | None:
    h = get(f"{BASE}/file/{idf}")
    if not h:
        return None
    txt = texto_plano(h)
    cod = re.search(r"C[óo]digo\s*:\s*([A-Z]\d{2})", txt)
    nom = re.search(r"Nombre\s*:\s*(.+?)\s+C[óo]digo\s*:", txt)
    tipo = re.search(r"Tipo\s*:\s*(.+?)\s+Escala\s*:", txt)

    docs = []
    for m in re.finditer(r'href="((?:https?://eae\.mma\.gob\.cl)?/storage/documents/[^"]+)"', h):
        ruta = m.group(1)
        if ruta.startswith("/"):
            ruta = BASE + ruta
        nombre = urllib.parse.unquote(ruta.rsplit("/", 1)[-1])
        n = norm(nombre)
        docs.append({
            "archivo": nombre,
            "url": ruta,
            "probable_riesgo": any(k in n for k in CLAVES_RIESGO),
            "probable_informe": any(k in n for k in CLAVES_INFORME),
        })
    # El mismo PDF puede aparecer en varias etapas del procedimiento.
    vistos, unicos = set(), []
    for d in docs:
        if d["url"] not in vistos:
            vistos.add(d["url"])
            unicos.append(d)
    return {
        "file_id": idf,
        "codigo": cod.group(1) if cod else None,
        "nombre": nom.group(1).strip() if nom else None,
        "tipo": tipo.group(1).strip() if tipo else None,
        "documentos": unicos,
    }


def main() -> None:
    destino = DATA_PROC / "eae"
    destino.mkdir(parents=True, exist_ok=True)
    cache = destino / "indice_nacional.json"

    reporte = leer_reporte()
    por_codigo = {r["codigo"]: r for r in reporte if r.get("codigo")}

    if cache.exists() and "--refrescar" not in sys.argv:
        fichas = json.loads(cache.read_text(encoding="utf-8"))
        log(f"usando índice en caché: {len(fichas)} fichas "
            f"(usa --refrescar para volver a rastrear)")
    else:
        fichas, vacias = [], 0
        for i in range(1, ID_MAX + 1):
            f = leer_ficha(i)
            time.sleep(PAUSA)
            if not f:
                vacias += 1
                # 25 huecos seguidos: se acabaron las fichas.
                if vacias >= 25 and fichas:
                    log(f"  fin del rango en id={i}")
                    break
                continue
            vacias = 0
            fichas.append(f)
            if len(fichas) % 50 == 0:
                log(f"  {len(fichas)} fichas rastreadas (id={i})")
        cache.write_text(json.dumps(fichas, ensure_ascii=False), encoding="utf-8")
        log(f"índice nacional: {len(fichas)} fichas, "
            f"{sum(len(f['documentos']) for f in fichas)} documentos")

    # ---- cruce con el reporte y filtro regional --------------------------
    ara = []
    for f in fichas:
        meta = por_codigo.get(f["codigo"] or "")
        if not meta or "araucan" not in norm(meta.get("region", "")):
            continue
        ara.append({**f,
                    "region": meta["region"], "provincia": meta["provincia"],
                    "comunas": meta["comunas"], "instrumento": meta["instrumento"],
                    "fecha_ingreso": meta["fecha"],
                    "estado": meta["procedimiento_actual"]})

    ara.sort(key=lambda x: (x["comunas"], x["nombre"] or ""))
    (destino / "araucania.json").write_text(
        json.dumps(ara, ensure_ascii=False, indent=1), encoding="utf-8")

    with open(destino / "araucania.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["comuna", "procedimiento", "codigo", "estado", "archivo",
                    "probable_riesgo", "url"])
        for p in ara:
            for d in p["documentos"]:
                w.writerow([p["comunas"], p["nombre"], p["codigo"], p["estado"],
                            d["archivo"], "SI" if d["probable_riesgo"] else "",
                            d["url"]])

    # ---- resumen ---------------------------------------------------------
    docs = [d for p in ara for d in p["documentos"]]
    riesgo = [d for d in docs if d["probable_riesgo"]]
    comunas = sorted({p["comunas"] for p in ara})
    log("")
    log(f"ARAUCANÍA: {len(ara)} procedimientos, {len(docs)} documentos públicos")
    log(f"  con nombre que sugiere cartografía de riesgo: {len(riesgo)}")
    log(f"  comunas cubiertas ({len(comunas)}): {', '.join(comunas)}")
    log("")
    log("Procedimientos con documentos de riesgo:")
    for p in ara:
        r = [d for d in p["documentos"] if d["probable_riesgo"]]
        if r:
            log(f"  {p['comunas']:22s} {p['nombre'][:38]:40s} {len(r):2d} doc")
            for d in r[:3]:
                log(f"      {d['archivo'][:88]}")


if __name__ == "__main__":
    main()
