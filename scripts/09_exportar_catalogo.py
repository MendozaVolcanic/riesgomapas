"""Catálogo público de documentos y láminas de riesgo, comuna por comuna.

El objetivo del proyecto no es sólo dibujar un mapa: es que la información que ya
es pública deje de estar sepultada. Un vecino de Gorbea no va a rastrear el
registro de Evaluación Ambiental Estratégica, abrir un PDF de 300 páginas y
buscar dónde está la figura de inundación.

Este script arma la respuesta corta: **para tu comuna, estos documentos, y el
mapa está en tal página.** Con enlace directo al PDF oficial.

Consolida lo producido por:
  · 05_eae_documentos.py       — qué documentos existen por comuna
  · 07_buscar_laminas_riesgo.py — en qué página está la cartografía
  · 08_georreferenciar_grilla.py — cuáles ya quedaron georreferenciadas

Salida: web/data/catalogo-documentos.json
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import DATA_PROC, WEB_DATA, log, procedencia  # noqa: E402

# Documentos de puro trámite: no aportan nada a un vecino y ensucian el listado.
RUIDO = ("01_ingreso", "03_rpt", "difusion", "difusión", "desistimiento",
         "resolucion", "resolución", "decreto", "consulta")


def norm(t: str | None) -> str:
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def util(archivo: str) -> bool:
    n = norm(archivo)
    return not any(r in n for r in RUIDO)


def cargar_laminas() -> dict[str, list[dict]]:
    """archivo -> páginas con cartografía, de todos los barridos del script 07."""
    out: dict[str, list[dict]] = {}
    for f in sorted((DATA_PROC / "eae").glob("laminas_candidatas_*.json")):
        for d in json.loads(f.read_text(encoding="utf-8")):
            hits = [h for h in d["paginas_con_amenaza"] if h["es_probable_lamina"]]
            if hits:
                out.setdefault(d["archivo"], [])
                vistas = {h["pagina"] for h in out[d["archivo"]]}
                out[d["archivo"]] += [h for h in hits if h["pagina"] not in vistas]
    return out


def cargar_georreferenciadas() -> dict[tuple[str, int], dict]:
    """(archivo, página) -> resultado de georreferenciación automática.

    Se lee de los reportes individuales que acompañan a cada GeoTIFF y no de un
    archivo de lote: hay un reporte por producto, así que la fuente de verdad es
    lo que efectivamente se generó en disco. Un índice agregado puede quedar
    desactualizado; los archivos, no.
    """
    out: dict[tuple[str, int], dict] = {}
    for j in sorted((DATA_PROC / "georreferenciado").glob("*.json")):
        try:
            r = json.loads(j.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        aj = r.get("ajuste") or {}
        if not aj:
            continue
        # El nombre del producto es "<stem del pdf>_pNNN"; la ruta del PDF de
        # origen queda registrada en la procedencia.
        m = re.search(r"_p(\d{3})$", j.stem)
        pdf = (r.get("procedencia") or {}).get("url", "")
        if not m or not pdf:
            continue
        out[(Path(pdf).name, int(m.group(1)))] = {
            "crs": r.get("crs"),
            "rmse_loo_m": aj.get("rmse_loo_m"),
            "aptitud": aj.get("aptitud"),
            "resolucion_m_px": (r.get("raster") or {}).get("resolucion_m"),
            "puntos_control": aj.get("n_puntos"),
        }
    return out


def main() -> None:
    idx = DATA_PROC / "eae" / "araucania.json"
    if not idx.exists():
        raise SystemExit("falta data/processed/eae/araucania.json — corre el script 05")
    procs = json.loads(idx.read_text(encoding="utf-8"))
    laminas = cargar_laminas()
    geo = cargar_georreferenciadas()

    comunas: dict[str, dict] = {}
    for p in procs:
        for comuna in [c.strip() for c in (p["comunas"] or "").split(",") if c.strip()]:
            if comuna.lower() in ("todas",):
                continue
            entrada = comunas.setdefault(comuna, {"comuna": comuna, "documentos": []})
            for d in p["documentos"]:
                if not util(d["archivo"]):
                    continue
                hits = laminas.get(d["archivo"], [])
                entrada["documentos"].append({
                    "archivo": d["archivo"],
                    "url": d["url"],
                    "procedimiento": p["nombre"],
                    "codigo": p["codigo"],
                    "instrumento": p["instrumento"],
                    "fecha_ingreso_eae": p["fecha_ingreso"],
                    "estado_eae": p["estado"],
                    "laminas": [{
                        "pagina": h["pagina"],
                        "tipo": h.get("tipo_lamina"),
                        "cm": h.get("cm"),
                        "terminos": h["terminos"],
                        "georreferenciada": geo.get((d["archivo"], h["pagina"])),
                    } for h in sorted(hits, key=lambda x: x["pagina"])],
                })

    # --- documentos bajados de sitios municipales (vía distinta al registro EAE)
    muni = DATA_PROC / "eae" / "laminas_candidatas_municipales.json"
    if muni.exists():
        # Las dos vías escriben el nombre de comuna distinto ("Pucon" vs
        # "Pucón"): se empareja por nombre normalizado para no crear una comuna
        # duplicada en el catálogo.
        por_norm = {norm(k): k for k in comunas}
        for d in json.loads(muni.read_text(encoding="utf-8")):
            clave = por_norm.get(norm(d["comuna"]), d["comuna"])
            entrada = comunas.setdefault(clave, {"comuna": clave, "documentos": []})
            hits = [h for h in d["paginas_con_amenaza"] if h["es_probable_lamina"]]
            entrada["documentos"].append({
                "archivo": d["archivo"],
                "url": d["url"],
                "procedimiento": d["procedimiento"],
                "codigo": d["codigo"],
                "instrumento": "Estudio municipal",
                "fecha_ingreso_eae": None,
                "estado_eae": "publicado por el municipio",
                "laminas": [{
                    "pagina": h["pagina"],
                    "tipo": h.get("tipo_lamina"),
                    "cm": h.get("cm"),
                    "terminos": h["terminos"],
                    "georreferenciada": geo.get((d["archivo"], h["pagina"])),
                } for h in sorted(hits, key=lambda x: x["pagina"])],
            })

    # Ordenar: primero los documentos que tienen cartografía.
    for e in comunas.values():
        e["documentos"].sort(key=lambda d: (-len(d["laminas"]), d["archivo"]))
        e["n_documentos"] = len(e["documentos"])
        e["n_laminas"] = sum(len(d["laminas"]) for d in e["documentos"])
        e["n_georreferenciadas"] = sum(
            1 for d in e["documentos"] for l in d["laminas"] if l["georreferenciada"])

    orden = sorted(comunas.values(), key=lambda e: (-e["n_laminas"], e["comuna"]))

    meta = procedencia(
        fuente="Registro de Evaluación Ambiental Estratégica (Ministerio del Medio "
               "Ambiente) — expedientes de planes reguladores comunales",
        url="https://eae.mma.gob.cl/reporte-general",
        metodo="Rastreo del registro nacional, apertura de cada PDF y localización "
               "de las páginas con cartografía de amenaza hídrica. Las páginas "
               "marcadas son candidatas detectadas automáticamente: conviene "
               "confirmarlas al abrirlas.",
        capa_evidencia="A_normativo",
        incertidumbre="La detección de láminas es automática y puede traer falsos "
                      "positivos. Los enlaces apuntan al documento oficial sin "
                      "modificar: la fuente de verdad es el PDF, no este índice.",
    )
    destino = WEB_DATA / "catalogo-documentos.json"
    destino.write_text(json.dumps({"procedencia": meta, "comunas": orden},
                                  ensure_ascii=False), encoding="utf-8")

    tot_doc = sum(e["n_documentos"] for e in orden)
    tot_lam = sum(e["n_laminas"] for e in orden)
    tot_geo = sum(e["n_georreferenciadas"] for e in orden)
    log(f"catálogo: {len(orden)} comunas, {tot_doc} documentos, {tot_lam} láminas, "
        f"{tot_geo} georreferenciadas")
    log(f"  {destino.relative_to(WEB_DATA.parent.parent)} "
        f"({destino.stat().st_size / 1024:.0f} KB)")
    log("")
    for e in orden[:18]:
        log(f"  {e['comuna'][:20]:22s} {e['n_documentos']:3d} doc · "
            f"{e['n_laminas']:3d} láminas · {e['n_georreferenciadas']:2d} georref.")


if __name__ == "__main__":
    main()
