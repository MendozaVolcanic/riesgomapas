"""Capa A (normativa) paso 1 — descargar los documentos fuente y aislar las láminas.

Los mapas de inundación con efecto legal en Chile viven, casi siempre, dentro de
un PDF: el Estudio Fundado de Riesgos que acompaña al Plan Regulador Comunal, o
el Plan Maestro de Aguas Lluvias de la DOH. No son shapefiles ni GeoTIFF: son
cartografía rasterizada dentro de un informe de cientos de páginas.

Este script hace lo previo a georreferenciar: baja el documento, verifica que sea
un PDF real (no una página de error), inventaria sus páginas y renderiza a alta
resolución sólo las que parecen láminas cartográficas.

Criterio para "parece lámina": página con poco texto y al menos una imagen que
cubre buena parte de la hoja. Es una heurística — el inventario que se escribe en
`laminas.json` está para que una persona revise y corrija antes de invertir
tiempo en poner puntos de control.

Salida: data/raw/documentos/<comuna>/<doc>.pdf
        data/raw/laminas/<comuna>/<doc>_p<NNN>.png
        data/raw/laminas/<comuna>/inventario.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import DATA_RAW, descargar, log  # noqa: E402

# DPI de render. 400 es el punto de equilibrio: por debajo de 300 los rótulos de
# calle dejan de leerse y no se pueden poner puntos de control precisos; por
# encima de 500 el archivo crece sin ganar precisión sobre el escaneo original.
DPI = 400

DOCUMENTOS = [
    {
        "comuna": "temuco",
        "id": "prc_estudio_riesgos",
        "titulo": "Actualización diagnóstico territorial para la modificación del PRC "
                  "de Temuco — Estudio Fundado de Riesgos",
        "url": "https://www.temuco.cl/wp-content/uploads/2022/04/Cap9-5-Estudio-Fundado-Riesgos.pdf",
        "capa_evidencia": "A_normativo",
        "anio": 2022,
    },
    {
        "comuna": "temuco",
        "id": "estudio_aguas_lluvias",
        "titulo": "Estudio de aguas lluvias — diagnóstico PRC Temuco",
        "url": "https://www.temuco.cl/wp-content/uploads/2022/04/Cap9-2-Estudio-Aguas-Lluvias.pdf",
        "capa_evidencia": "A_normativo",
        "anio": 2022,
    },
    # Estudios de riesgo publicados directamente por los municipios. Son el
    # estudio propiamente tal —el que fundamenta la zonificación—, no la memoria
    # del anteproyecto, así que traen el análisis de amenaza con más detalle.
    # Se llega a ellos por sitio municipal, no por el registro EAE: conviene
    # tener las dos vías porque ninguna es completa.
    {
        "comuna": "pucon",
        "id": "estudio_fundado_riesgos",
        "titulo": "Estudio Fundado de Riesgos y Protección Ambiental — "
                  "actualización PRC de Pucón",
        "url": "https://www.sustentapucon.cl/wp-content/uploads/2022/02/"
               "Estudio_Fundado_Riesgos_Proteccion_Ambiental-3.pdf",
        "capa_evidencia": "A_normativo",
        "anio": 2022,
    },
    {
        "comuna": "teodoro-schmidt",
        "id": "estudio_riesgos_prc",
        "titulo": "Estudio de Riesgos del Plan Regulador Comunal de Teodoro Schmidt (E5)",
        "url": "https://muniteodoro.cl/portal/wp-content/uploads/2023/05/"
               "Estudio-Riesgos-PRCTS-E5.pdf",
        "capa_evidencia": "A_normativo",
        "anio": 2023,
    },
    {
        "comuna": "collipulli",
        "id": "prc_collipulli",
        "titulo": "Plan Regulador Comunal de Collipulli",
        "url": "https://municipalidadcollipulli.cl/wp-content/uploads/2022/07/PRC-1.pdf",
        "capa_evidencia": "A_normativo",
        "anio": 2022,
    },
    {
        "comuna": "temuco",
        "id": "memoria_explicativa",
        "titulo": "Memoria explicativa — modificación planes reguladores "
                  "Temuco y Labranza",
        "url": "https://www.temuco.cl/wp-content/uploads/2022/04/MEM-Explicativa-R-14.pdf",
        "capa_evidencia": "A_normativo",
        "anio": 2022,
    },
]


def inventariar(pdf_path: Path) -> list[dict]:
    doc = pdfium.PdfDocument(str(pdf_path))
    filas = []
    for i in range(len(doc)):
        pag = doc[i]
        ancho, alto = pag.get_size()
        try:
            texto = pag.get_textpage().get_text_bounded() or ""
        except Exception:  # noqa: BLE001
            texto = ""
        n_obj_img = sum(1 for o in pag.get_objects() if o.type == 3)  # 3 = imagen
        filas.append({
            "pagina": i + 1,
            "ancho_pt": round(ancho, 1),
            "alto_pt": round(alto, 1),
            "apaisada": ancho > alto,
            "caracteres_texto": len(texto.strip()),
            "objetos_imagen": n_obj_img,
            # Una lámina cartográfica tiene imagen y poco texto corrido.
            "probable_lamina": n_obj_img >= 1 and len(texto.strip()) < 1800,
        })
    doc.close()
    return filas


def render(pdf_path: Path, paginas: list[int], destino: Path, prefijo: str) -> list[str]:
    destino.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf_path))
    escala = DPI / 72.0
    salidas = []
    for n in paginas:
        out = destino / f"{prefijo}_p{n:03d}.png"
        if not out.exists():
            img = doc[n - 1].render(scale=escala).to_pil()
            img.save(out)
        salidas.append(out.name)
        log(f"    p{n:03d} -> {out.name}")
    doc.close()
    return salidas


def main() -> None:
    solo = set(sys.argv[1:])
    resumen = []

    for d in DOCUMENTOS:
        if solo and d["id"] not in solo and d["comuna"] not in solo:
            continue
        log(f"{d['comuna']} / {d['id']}")
        pdf = DATA_RAW / "documentos" / d["comuna"] / f"{d['id']}.pdf"
        try:
            descargar(d["url"], pdf)
        except Exception as exc:  # noqa: BLE001
            log(f"  no se pudo descargar: {exc}")
            resumen.append({**d, "estado": f"error: {exc}"})
            continue

        filas = inventariar(pdf)
        candidatas = [f["pagina"] for f in filas if f["probable_lamina"]]
        log(f"  {len(filas)} páginas, {len(candidatas)} candidatas a lámina")

        dir_lam = DATA_RAW / "laminas" / d["comuna"]
        # Tope de seguridad: renderizar 300 páginas a 400 dpi llena el disco.
        # Si el documento es casi todo láminas, hay que elegir a mano.
        a_render = candidatas[:25]
        if len(candidatas) > 25:
            log(f"  ⚠️ {len(candidatas)} candidatas: se renderizan las primeras 25. "
                f"Revisa inventario.json y ajusta a mano.")
        archivos = render(pdf, a_render, dir_lam, d["id"])

        (dir_lam / "inventario.json").write_text(json.dumps({
            "documento": d,
            "pdf": str(pdf.relative_to(DATA_RAW)),
            "paginas": filas,
            "renderizadas": archivos,
            "dpi": DPI,
        }, ensure_ascii=False, indent=1), encoding="utf-8")

        resumen.append({**d, "estado": "ok", "paginas": len(filas),
                        "candidatas": len(candidatas), "renderizadas": len(archivos)})

    log("")
    for r in resumen:
        log(f"  {r['comuna']}/{r['id']}: {r['estado']}"
            + (f" — {r.get('paginas')} pág, {r.get('renderizadas')} láminas"
               if r["estado"] == "ok" else ""))
    log("")
    log("Siguiente paso: abrir las PNG, elegir la lámina de inundación y crear el")
    log("archivo de puntos de control. Ver scripts/04_georreferenciar.py --plantilla")


if __name__ == "__main__":
    main()
