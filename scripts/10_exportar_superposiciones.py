"""Publicar los planos georreferenciados como capa visible en el visor web.

Los GeoTIFF que produce el script 08 son enormes (18.897 × 7.084 px, ~30 MB cada
uno) porque conservan la resolución del plano original a 21 cm/px. Eso está bien
para trabajar en QGIS, pero es inservible para un celular en zona rural.

Acá se generan versiones web: reproyectadas a Web Mercator, reducidas a un ancho
máximo razonable y guardadas como PNG con transparencia, más un índice con sus
esquinas en coordenadas geográficas para que MapLibre las ubique.

Se reproyecta a EPSG:3857 y no se entrega el UTM directo porque MapLibre coloca
las superposiciones de imagen por sus cuatro esquinas en lon/lat, e interpola
linealmente entre ellas: una imagen en UTM se vería progresivamente corrida hacia
los bordes de la hoja.

Requiere: 08_georreferenciar_grilla.py (los GeoTIFF de data/processed/georreferenciado/)
Salida: web/data/planos/<nombre>.png + web/data/planos/indice.json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject, transform_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import DATA_PROC, WEB_DATA, log, procedencia  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

ANCHO_MAX = 2600      # px; suficiente para leer la zonificación en pantalla
PESO_OBJETIVO_KB = 900


def _nombre_web(stem: str) -> str:
    """Nombre de archivo publicable: sólo ASCII, sin espacios.

    Los planos vienen de comunas con tilde (Pucón, Vilcún, Pitrufquén, Traiguén):
    14 de 23. Publicar el nombre tal cual obliga a que TODO lo que lo consuma
    —el navegador, MapLibre, un CDN, un zip, otro sistema de archivos— haga la
    misma codificación de la URL, y basta que uno no la haga para que la imagen
    devuelva 404 en silencio y la capa se vea vacía. Es lo que pasaba: los 9
    planos sin tilde cargaban y los 14 con tilde, no.
    """
    t = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    t = re.sub(r"[^\w.-]+", "_", t)
    return re.sub(r"_+", "_", t).strip("_")


def exportar(tif: Path, destino_dir: Path) -> dict | None:
    with rasterio.open(tif) as src:
        if src.crs is None:
            log(f"  {tif.name}: sin CRS, se omite")
            return None

        # Reproyección a Web Mercator sobre una grilla acotada por ANCHO_MAX.
        transform, w, h = calculate_default_transform(
            src.crs, "EPSG:3857", src.width, src.height, *src.bounds)
        escala = min(1.0, ANCHO_MAX / max(w, h))
        w2, h2 = max(1, int(w * escala)), max(1, int(h * escala))
        transform2 = transform * transform.scale(w / w2, h / h2)

        salida = np.zeros((4, h2, w2), dtype="uint8")
        for b in range(1, min(src.count, 4) + 1):
            reproject(
                source=rasterio.band(src, b),
                destination=salida[b - 1],
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=transform2, dst_crs="EPSG:3857",
                resampling=Resampling.average if b <= 3 else Resampling.nearest,
            )
        if src.count < 4:  # sin banda alfa: todo opaco
            salida[3] = 255

        bounds_wgs = transform_bounds(src.crs, "EPSG:4326", *src.bounds, densify_pts=21)

    px = np.transpose(salida, (1, 2, 0))
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"{_nombre_web(tif.stem)}.png"

    def guardar(arr_rgb: np.ndarray, fuera: np.ndarray, ruta: Path) -> float:
        """Guarda como PNG de paleta (8 bits) en vez de RGBA (32 bits).

        Un plano regulador usa un puñado de colores planos, así que cuantizar a
        255 entradas es prácticamente sin pérdida visual y reduce el archivo
        entre 3 y 5 veces. Es la diferencia entre servir 37 MB o 9 MB a un
        celular en zona rural, que es justo el público de esto.

        El índice 255 queda reservado para "fuera de la hoja" y se declara
        transparente; la traslucidez del plano sobre el mapa base la pone
        MapLibre con `raster-opacity`, no la imagen.
        """
        pal = Image.fromarray(arr_rgb, "RGB").quantize(
            colors=255, method=Image.MEDIANCUT, dither=Image.NONE)
        idx = np.array(pal)
        idx[fuera] = 255
        out = Image.fromarray(idx, "P")
        paleta = list(pal.getpalette()[:255 * 3]) + [255, 255, 255]
        out.putpalette(paleta)

        # Alfa POR ENTRADA DE PALETA, no un único índice transparente.
        #
        # El fondo de la hoja es blanco y opaco: si se publica tal cual, el plano
        # tapa el mapa base y deja de verse la ciudad sobre la que está puesto.
        # Como el PNG admite una tabla de transparencia con un valor por color,
        # se puede dejar el papel casi transparente y conservar opacos los
        # trazos y los colores de la zonificación, que es lo que interesa ver.
        alfas = bytearray(256)
        for i in range(255):
            r, g, b = paleta[i * 3: i * 3 + 3]
            if r > 240 and g > 240 and b > 240:
                alfas[i] = 28          # papel: casi transparente
            elif r > 215 and g > 215 and b > 215:
                alfas[i] = 120         # grises muy claros: semitransparentes
            else:
                alfas[i] = 255         # dibujo y zonificación: opacos
        alfas[255] = 0                 # fuera de la hoja: invisible

        out.save(ruta, optimize=True, compress_level=9, transparency=bytes(alfas))
        return ruta.stat().st_size / 1024

    fuera = px[:, :, 3] == 0
    kb = guardar(px[:, :, :3], fuera, destino)
    tam = (w2, h2)
    if kb > PESO_OBJETIVO_KB:
        f = (PESO_OBJETIVO_KB / kb) ** 0.5
        tam = (max(1, int(w2 * f)), max(1, int(h2 * f)))
        rgb_p = np.array(Image.fromarray(px[:, :, :3], "RGB").resize(tam, Image.LANCZOS))
        fuera_p = np.array(Image.fromarray(fuera.astype("uint8") * 255, "L")
                           .resize(tam, Image.NEAREST)) > 127
        kb = guardar(rgb_p, fuera_p, destino)

    log(f"  {destino.name}: {tam[0]}x{tam[1]} px, {kb:.0f} KB")
    img = type("I", (), {"size": tam})()
    return {"archivo": destino.name,
            "ancho": img.size[0], "alto": img.size[1], "kb": round(kb),
            "bounds_wgs84": [round(v, 7) for v in bounds_wgs]}


# Estado de tramitación del instrumento del que sale cada plano.
#
# POR QUÉ IMPORTA Y NO ES UN DETALLE: un **anteproyecto** es la propuesta que
# está en tramitación; puede cambiar y todavía no obliga a nadie. El plano
# **vigente** es el que rige tu terreno hoy. Los 20 planos publicados hasta ahora
# son los tres primeros: salen del expediente ambiental, donde lo que se publica
# es la propuesta, no el decreto. Mostrarlos rotulados «Plano original del Plan
# Regulador», bajo una capa que el sitio describe como «la única con efecto
# jurídico», le atribuye a una propuesta un peso que no tiene — y alguien podría
# tomar una decisión sobre su terreno con eso.
ESTADO_TRAMITE = {
    "anteproyecto": ("Anteproyecto",
                     "Propuesta en tramitación. Puede cambiar y todavía no tiene "
                     "efecto legal."),
    "vigente": ("Vigente",
                "Instrumento aprobado y promulgado. Rige hoy sobre el territorio."),
}


def estado_de_tramite(nombre: str) -> tuple[str, str]:
    """Deduce el estado desde el nombre del archivo, y sólo cuando es explícito.

    No adivina: si el nombre no lo dice, devuelve «no declarado». Suponer
    «vigente» porque sí sería exactamente el error que este campo existe para
    evitar.
    """
    n = nombre.lower()
    if "anteproyecto" in n:
        return ESTADO_TRAMITE["anteproyecto"]
    if "promulga" in n or "aprueba" in n or "publicacion" in n or "publicación" in n:
        return ESTADO_TRAMITE["vigente"]
    return ("No declarado",
            "El documento de origen no dice si es propuesta o instrumento "
            "vigente. Trátalo como referencia, no como norma.")


def main() -> None:
    origen = DATA_PROC / "georreferenciado"
    tifs = sorted(origen.glob("*.tif"))
    if not tifs:
        raise SystemExit(
            f"no hay ningún GeoTIFF en {origen}.\n"
            "Los .tif no se versionan (298 MB): en un clon limpio hay que "
            "regenerarlos antes con:\n"
            "    python scripts/08_georreferenciar_grilla.py --todas\n"
            "que a su vez necesita los PDF de data/raw/ (scripts 03 y 12).\n"
            "No se reescribe web/data/planos/indice.json para no borrar lo que "
            "ya está publicado.")

    log(f"{len(tifs)} planos georreferenciados a publicar")
    items = []
    # Un mismo plano puede venir repetido en el expediente: el anteproyecto se
    # vuelve a presentar en cada Informe Ambiental sin que la cartografía cambie.
    # Galvarino es el caso extremo — el mismo archivo en el 2°, 3° y 4° informe,
    # idéntico byte a byte. Publicarlos todos hacía que el visor dibujara tres
    # imágenes encima de sí mismas y que el sitio cargara 4,5 MB de repetición.
    vistos: dict[str, str] = {}
    for t in tifs:
        r = exportar(t, destino_dir)
        if not r:
            continue
        h = hashlib.md5((destino_dir / r["archivo"]).read_bytes()).hexdigest()
        if h in vistos:
            log(f"  duplicado exacto de {vistos[h][:46]}, no se publica: {r['archivo'][:46]}")
            (destino_dir / r["archivo"]).unlink(missing_ok=True)
            continue
        vistos[h] = r["archivo"]
        rep = reportes.get(t.stem, {})
        aj = rep.get("ajuste", {})
        # Un plano con error de decenas de metros no se publica como si nada:
        # se marca para que el visor lo muestre con advertencia.
        estado, nota_estado = estado_de_tramite(r["archivo"])
        items.append({
            **r,
            "titulo": t.stem.replace("_", " ").replace(".pdf", ""),
            "estado_tramite": estado,
            "estado_tramite_nota": nota_estado,
            "crs_original": rep.get("crs"),
            "resolucion_m_px": (rep.get("raster") or {}).get("resolucion_m"),
            "rmse_loo_m": aj.get("rmse_loo_m"),
            "aptitud": aj.get("aptitud"),
            "puntos_control": aj.get("n_puntos"),
            "fuente": rep.get("fuente"),
            "anio": rep.get("anio"),
            "procedencia_metodo": (rep.get("procedencia") or {}).get("metodo"),
        })

    meta = procedencia(
        fuente="Planos de planes reguladores comunales georreferenciados desde su "
               "grilla UTM impresa",
        url="https://eae.mma.gob.cl/reporte-general",
        metodo=f"Reproyección a EPSG:3857 y reducción a un máximo de {ANCHO_MAX} px "
               "de lado; el blanco de la hoja se vuelve semitransparente para no "
               "tapar el mapa base",
        capa_evidencia="A_normativo",
        incertidumbre="Cada plano declara su propio RMSE. La imagen web está "
                      "remuestreada: para trabajo de precisión hay que usar el "
                      "GeoTIFF original, no esta versión. Y cada plano declara su "
                      "ESTADO DE TRAMITACIÓN: un anteproyecto es una propuesta que "
                      "puede cambiar y no obliga a nadie; sólo el instrumento "
                      "vigente rige sobre el territorio.",
    )
    (destino_dir / "indice.json").write_text(
        json.dumps({"procedencia": meta, "planos": items}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    total_kb = sum(i["kb"] for i in items)
    log("")
    log(f"{len(items)} superposiciones publicadas, {total_kb / 1024:.1f} MB en total")
    for i in items:
        log(f"  {i['titulo'][:52]:54s} {i['aptitud'] or '?':8s} "
            f"RMSE {i['rmse_loo_m']} m")


if __name__ == "__main__":
    main()
