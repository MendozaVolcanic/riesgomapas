"""Capa A-derivada — convertir una lámina de peligro impresa en polígonos.

El caso que lo motiva: Angol tiene un Plan Regulador vigente y un Estudio de
Riesgo propio, pero **cero polígonos en el vectorial que publica el MINVU**. Su
cartografía de peligro de inundación existe y es pública: está en la página 30 de
`Estudio_Riesgo.pdf`, como figura. Mientras siga siendo una figura, no se puede
consultar por dirección, no se puede cruzar con el censo y no le sirve a nadie.

Este script la convierte en geometría, y es la primera vez que el proyecto
**produce** una capa en vez de recolectarla.

Cómo se puede hacer
-------------------
Estas figuras no son fotos: son salidas de un SIG impresas con su **retícula UTM
rotulada**. Dos rótulos por eje bastan para fijar la transformación afín, porque
la relación píxel↔metro es lineal y un mapa tiene una sola escala. Y la leyenda
es discreta —«Alto», «Medio»—, no un degradado, así que cada clase es un color
plano que se separa por distancia en RGB.

Medido en Angol: 646 píxeles entre las líneas de 700.000 y 705.000, o sea
**7,74 m por píxel**. El modelo regional del GORE que hoy cubre esa comuna tiene
35 m. La figura de 200 dpi resuelve 4,5 veces más fino que la mejor capa modelada
que Angol tenía.

Las tres trampas, y qué se hace con cada una
--------------------------------------------
1. **La red hídrica se dibuja en el mismo azul que la clase «Alto».** Una
   clasificación por color convierte el cauce en mancha de inundación, y el
   resultado queda plausible porque el río sí está dentro del área inundable. Se
   separa por **grosor**, no por tono: apertura morfológica con un elemento del
   ancho declarado en `ancho_minimo_px`.

2. **Los rótulos de la grilla están dentro del ráster.** Leerlos exige OCR y el
   binario de tesseract no está instalado. Se declaran a mano en
   `config/laminas.yaml`, una vez por lámina, y el script los verifica: la escala
   en X y en Y tiene que coincidir y el resultado tiene que aterrizar donde vive
   la comuna. Una coordenada mal tecleada mueve la mancha cientos de metros y
   cualquiera de las dos comprobaciones la detecta.

3. **Vectorizar sube la precisión aparente sin subir el conocimiento.** Un
   polígono de borde nítido *parece* un modelo hidráulico. El de Angol viene de
   álgebra de mapas sobre morfometría, de 2013, sin caudales ni períodos de
   retorno. Por eso el método original va **literal, pegado a cada polígono**, y
   la capa se etiqueta `A_derivado` — nunca se mezcla con el vectorial del MINVU,
   que sí tiene efecto legal.

Uso:
    python 18_vectorizar_laminas.py                       # todas las declaradas
    python 18_vectorizar_laminas.py --id angol-peligro-inundacion-2013
    python 18_vectorizar_laminas.py --inspeccionar <pdf> --pagina 30
    python 18_vectorizar_laminas.py --censo               # ¿qué otras se pueden?

Salida: data/processed/laminas/<id>.geojson
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    CONFIG, DATA_PROC, DATA_RAW, cargar_config, escribir_geojson, log, procedencia,
)

SALIDA = DATA_PROC / "laminas"


# ---------------------------------------------------------------- imagen

def renderizar(pdf: Path, pagina: int, escala: float) -> Image.Image:
    """Rasteriza la página completa.

    Hace falta cuando la lámina NO es una imagen incrustada sino un dibujo
    vectorial: las láminas de plóter de la DGA traen el mapa como ~1.500 trazos
    más unas pocas imágenes sueltas, así que extraer «la imagen» devuelve un
    logo o un recuadro, no el mapa.

    La escala se declara en la configuración y no se elige sola, porque las
    posiciones de la retícula se anotan en píxeles de ESTE render: cambiarla
    invalidaría los rótulos ya leídos.
    """
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return doc[pagina - 1].render(scale=escala).to_pil().convert("RGB")
    finally:
        doc.close()


def imagenes_de(pdf: Path, pagina: int) -> list[Image.Image]:
    """Imágenes incrustadas en una página, en orden de aparición."""
    doc = pdfium.PdfDocument(str(pdf))
    try:
        out = []
        for obj in doc[pagina - 1].get_objects():
            if obj.type != 3:          # 3 = imagen
                continue
            try:
                out.append(obj.get_bitmap().to_pil().convert("RGB"))
            except Exception:          # noqa: BLE001 — imagen que pdfium no rasteriza
                continue
        return out
    finally:
        doc.close()


def lineas_de_grilla(a: np.ndarray) -> tuple[list[int], list[int]]:
    """Posiciones en píxeles de las líneas continuas y neutras (la retícula).

    Se buscan píxeles grises/negros porque la retícula se imprime en gris y el
    marco en negro; el mapa que hay debajo es de color. Se exige que la línea
    cubra buena parte del alto (o del ancho) para no confundirla con una calle.
    """
    h, w, _ = a.shape
    neutro = (a.max(2) - a.min(2) < 25) & (a.max(2) < 210)

    def picos(suma: np.ndarray, largo: int) -> list[int]:
        orden = np.argsort(suma)[::-1]
        sel: list[int] = []
        for i in orden:
            if suma[i] < largo * 0.55:
                break
            if all(abs(int(i) - t) > 8 for t in sel):
                sel.append(int(i))
            if len(sel) >= 14:
                break
        return sorted(sel)

    # Se evita la franja inferior, donde suele ir la caja de leyenda.
    bv = neutro[int(h * .05):int(h * .75)]
    bh = neutro[:, int(w * .05):int(w * .62)]
    return picos(bv.sum(0), bv.shape[0]), picos(bh.sum(1), bh.shape[1])


# ---------------------------------------------------------------- afín

def escala_de(anclas: list[list[float]]) -> tuple[float, float, float]:
    """De [[px, coord], …] a (metros_por_pixel, px_ref, coord_ref)."""
    if len(anclas) < 2:
        raise ValueError("se necesitan dos anclas para medir la escala")
    (p0, c0), (p1, c1) = anclas[0], anclas[-1]
    if p1 == p0:
        raise ValueError("dos anclas en el mismo píxel")
    return abs((c1 - c0) / (p1 - p0)), float(p0), float(c0)


def afin(cfg: dict) -> tuple[float, float, float, float, float, str]:
    """Devuelve (m_por_px, x_ref, e_ref, y_ref, n_ref, nota)."""
    gx, gy = cfg["grilla"]["x"], cfg["grilla"]["y"]
    sx, x_ref, e_ref = escala_de(gx)

    if len(gy) >= 2:
        sy, y_ref, n_ref = escala_de(gy)
        dif = abs(sx - sy) / max(sx, sy)
        if dif > 0.01:
            raise SystemExit(
                f"[{cfg['id']}] la escala horizontal ({sx:.3f} m/px) y la vertical "
                f"({sy:.3f} m/px) difieren {100 * dif:.1f} %. Un mapa tiene una "
                "sola escala: hay un rótulo mal leído en config/laminas.yaml.")
        nota = (f"escala verificada en ambos ejes ({sx:.2f} y {sy:.2f} m/px, "
                f"difieren {100 * dif:.2f} %)")
        s = (sx + sy) / 2
    else:
        # Una sola ancla vertical: la escala se toma de la horizontal. Es válido
        # —un mapa tiene una sola escala— pero se pierde la verificación cruzada,
        # así que queda dicho en la procedencia.
        y_ref, n_ref = float(gy[0][0]), float(gy[0][1])
        s = sx
        nota = (f"escala tomada del eje horizontal ({sx:.2f} m/px); el eje "
                "vertical trae una sola línea rotulada visible, así que NO hay "
                "verificación cruzada de escala")
    return s, x_ref, float(e_ref), y_ref, float(n_ref), nota


def afin_por_vertices(cfg: dict):
    """Ajuste de semejanza a partir de vértices con su coordenada impresa.

    Los planos de zonificación rotulan cada vértice del límite urbano con su
    coordenada («13 — E: 700238, S: 5815912»). Son puntos de control de mejor
    calidad que la retícula: hay varios, repartidos por el pliego, y **sobran**,
    así que el ajuste deja residuos y se puede declarar un RMSE de verdad en vez
    de suponer que la transformación es exacta.

    Se ajusta una SEMEJANZA (escala + rotación + traslación, 4 parámetros), no
    una afín general de 6: un plano no tiene dos escalas ni cizalla, y dejar esos
    grados de libertad sueltos absorbería los errores de lectura en deformaciones
    falsas.

        E =  a·x + b·y + tx
        N =  b·x − a·y + ty        (y crece hacia abajo, N hacia arriba)
    """
    import math

    V = cfg["vertices"]
    if len(V) < 3:
        raise SystemExit(f"[{cfg['id']}] se necesitan ≥3 vértices para tener "
                         "residuos; con 2 el ajuste es exacto y el RMSE miente")
    A, L = [], []
    for _, x, y, e, n in V:
        A.append([x, y, 1, 0]); L.append(e)
        A.append([-y, x, 0, 1]); L.append(n)
    A, L = np.array(A, float), np.array(L, float)
    sol, *_ = np.linalg.lstsq(A, L, rcond=None)
    a_, b_, tx, ty = sol
    s = math.hypot(a_, b_)
    rot = math.degrees(math.atan2(b_, a_))
    resid = (L - A @ sol).reshape(-1, 2)
    d = np.hypot(resid[:, 0], resid[:, 1])
    rmse = float(np.sqrt((d ** 2).mean()))
    return sol, s, rot, rmse, [(V[i][0], float(d[i])) for i in range(len(V))]


# ------------------------------------------------------- detección por trama

def mascara_por_trama(a, cfg_clase: dict, s_m_px: float, excluir_x: int | None):
    """Máscara de una clase que se distingue por su ACHURADO, no por su color.

    Los planos de zonificación no colorean las áreas de riesgo: las achuran
    encima del color de la zona urbana que haya debajo. En el plano de Angol la
    misma AR-2a aparece sobre el verde del área verde y sobre el amarillo de la
    Z-3, así que clasificar por color no la encuentra — y si se intentara, se
    traería la zonificación entera.

    Lo que sí la identifica es la marca: un triángulo de unos 5×5 px, repetido
    en retícula. El punteado de AR-1a/b/c, que convive con ella, mide 2×2. Esa
    diferencia de tamaño las separa limpiamente, y la densidad local separa el
    achurado de las marcas sueltas (texto, símbolos, esquinas de edificios).
    """
    import cv2

    g = cv2.cvtColor(a.astype("uint8"), cv2.COLOR_RGB2GRAY)
    # Fondo local: cada zona tiene su color, así que la marca se define como
    # «más oscura que su vecindad», no como un color absoluto.
    fondo = cv2.medianBlur(g, 21)
    osc = ((fondo.astype("int16") - g.astype("int16"))
           > cfg_clase.get("contraste_minimo", 28)).astype("uint8")

    n, lab, st, cent = cv2.connectedComponentsWithStats(osc, 8)
    amin, amax = cfg_clase.get("marca_area", [8, 45])
    lmin, lmax = cfg_clase.get("marca_lado", [4, 11])
    ar = st[1:, cv2.CC_STAT_AREA]
    an = st[1:, cv2.CC_STAT_WIDTH]
    al = st[1:, cv2.CC_STAT_HEIGHT]
    sel = ((ar >= amin) & (ar <= amax) & (an >= lmin) & (an <= lmax)
           & (al >= lmin) & (al <= lmax))
    marcas = cent[1:][sel]

    cel = int(cfg_clase.get("celda_px", 8))
    h, w = g.shape
    dens = np.zeros((h // cel + 1, w // cel + 1), "float32")
    for x, y in marcas:
        if excluir_x is not None and x >= excluir_x:
            continue          # bloque de leyenda: tiene las mismas tramas de muestra
        dens[int(y) // cel, int(x) // cel] += 1

    ventana = int(cfg_clase.get("ventana_celdas", 5))
    local = cv2.filter2D(dens, -1, np.ones((ventana, ventana), "float32"))
    m = (local >= cfg_clase.get("densidad_minima", 8)).astype("uint8")
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), "uint8"))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), "uint8"))
    return m, cel, int(sel.sum()), len(marcas)


# ---------------------------------------------------------------- vectorizar

def limpiar_por_grosor(cruda: np.ndarray, ancho: int) -> np.ndarray:
    """Borra los rasgos más delgados que `ancho` píxeles SIN morder el borde de
    los que conserva.

    Lo obvio —y lo que había— es una apertura morfológica: erosionar y volver a
    dilatar. Borra lo fino, sí, pero de paso muerde el borde de toda mancha que
    conserva, y con un elemento de lado PAR la corre además un píxel entero,
    porque el ancla queda descentrada. Medido el 7-sep-2026 con un cuadrado
    sintético: entraba en 100..199 px y salía en 101..200, o sea que cada
    polígono publicado quedaba un píxel al sureste de donde la lámina lo dibuja
    —7,7 m en Angol, 5,3 m en Catripulli—. Y la mordida no era cosmética: se
    llevaba el 25 % de la clase «Alto» y el 41 % de «Medio» de Angol, sobre todo
    franjas delgadas a lo largo de esteros, que son riesgo legítimo y no ruido.

    La reconstrucción hace lo que aquí se quiere: la erosión sólo DECIDE qué
    componentes sobreviven, y las que sobreviven se devuelven enteras, con su
    borde intacto y con las franjas finas que cuelgan de ellas.
    """
    import cv2

    el = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ancho, ancho))
    marcador = cv2.erode(cruda.astype("uint8"), el).astype(bool)
    _, etiquetas = cv2.connectedComponents(cruda.astype("uint8"), connectivity=8)
    vivas = np.unique(etiquetas[marcador])
    return np.isin(etiquetas, vivas[vivas > 0])


def poligonos(mask: np.ndarray, transform, area_min: float):
    """Máscara booleana → geometrías en la proyección del transform."""
    from rasterio.features import shapes
    from shapely.geometry import shape

    out = []
    for geom, val in shapes(mask.astype("uint8"), mask=mask, transform=transform):
        if not val:
            continue
        g = shape(geom)
        if not g.is_valid:
            g = g.buffer(0)
        if g.is_empty or g.area < area_min:
            continue
        # Suaviza el escalonado del píxel sin mover el borde más que medio píxel.
        out.append(g.simplify(transform.a * 0.5, preserve_topology=True))
    return out


def procesar(cfg: dict, region: dict) -> dict | None:
    import cv2
    from affine import Affine
    from pyproj import Transformer
    from shapely.ops import transform as sh_transform

    pdf = DATA_RAW / cfg["pdf"]
    if not pdf.exists():
        log(f"  [{cfg['id']}] falta el PDF: {pdf}")
        return None

    if cfg.get("renderizar"):
        im = renderizar(pdf, cfg["pagina"], float(cfg["renderizar"]))
        log(f"  página rasterizada a escala {cfg['renderizar']}")
    else:
        ims = imagenes_de(pdf, cfg["pagina"])
        idx = cfg.get("imagen", 0)
        if idx >= len(ims):
            log(f"  [{cfg['id']}] la página {cfg['pagina']} tiene {len(ims)} "
                f"imagen(es), se pidió la #{idx}")
            return None
        im = ims[idx]
    a = np.array(im).astype(int)
    h, w, _ = a.shape
    log(f"  imagen {w}×{h} px")

    s, x_ref, e_ref, y_ref, n_ref, nota_escala = afin(cfg)
    log(f"  {s:.2f} m/píxel · {nota_escala}")

    # Norte disminuye al bajar en la imagen: el término vertical va negativo.
    transform = Affine(s, 0, e_ref - x_ref * s,
                       0, -s, n_ref + y_ref * s)

    tr = Transformer.from_crs(f"EPSG:{cfg['epsg']}", "EPSG:4326", always_xy=True)
    tol = cfg.get("tolerancia_color", 45)
    ancho = int(cfg.get("ancho_minimo_px", 4))
    area_min = float(cfg.get("area_minima_m2", 0))

    # Distancia a cada color de la leyenda; cada píxel se asigna al más cercano
    # dentro de la tolerancia, para que «Alto» y «Medio» no se solapen.
    # Una lámina de plóter suele traer VARIOS mapas en la misma hoja: el de
    # detalle, uno general de contexto y uno de ubicación regional. Todos usan
    # los mismos colores de leyenda y están a escalas distintas, así que
    # clasificar la hoja entera georreferencia el mapa de contexto con la afín
    # del de detalle — y produce polígonos plausibles en el lugar equivocado.
    # `excluir_x` recorta a la derecha del mapa que sí corresponde.
    if cfg.get("excluir_x"):
        a = a[:, :int(cfg["excluir_x"])]
        log(f"  recortado a los primeros {cfg['excluir_x']} px de ancho "
            "(el resto de la hoja son otros mapas)")
    if cfg.get("excluir_y"):
        a = a[:int(cfg["excluir_y"]), :]
        log(f"  recortado a los primeros {cfg['excluir_y']} px de alto")

    # La caja de leyenda dibuja los cuadros de muestra con el color EXACTO de
    # cada clase, y a la escala del mapa un cuadro de 30×20 px mide varias
    # hectáreas: se vectoriza como si fuera territorio. Medido el 6-sep-2026
    # sobre lo ya publicado — en Angol salían dos rectángulos de 6,1 y 5,6 ha en
    # un potrero al sur del pueblo, y en Catripulli otros dos de 0,3 y 0,5 ha.
    # La caja se declara a mano, igual que los rótulos de la retícula: separar un
    # recuadro de leyenda de un recuadro de mapa es de una mirada para una
    # persona y no para un detector. Va DESPUÉS de los recortes de arriba porque
    # ésos siempre cortan desde el origen y no mueven el origen de coordenadas.
    excluidas = np.zeros(a.shape[:2], bool)
    for caja in cfg.get("excluir_cajas") or []:
        x0, y0, x1, y1 = (int(v) for v in caja)
        if not (0 <= x0 < x1 <= a.shape[1] and 0 <= y0 < y1 <= a.shape[0]):
            raise SystemExit(
                f"[{cfg['id']}] la caja a excluir {caja} se sale de la imagen "
                f"({a.shape[1]}×{a.shape[0]} px) o está al revés. Las cajas van "
                "en píxeles de ESTA imagen, como [x0, y0, x1, y1]; revisa "
                "config/laminas.yaml.")
        excluidas[y0:y1, x0:x1] = True
    if excluidas.any():
        log(f"  {len(cfg['excluir_cajas'])} caja(s) excluidas (leyenda): "
            f"{int(excluidas.sum())} px")

    dists = [np.linalg.norm(a - np.array(c["rgb"]), axis=2) for c in cfg["clases"]]
    apilado = np.stack(dists)
    ganador = apilado.argmin(0)
    dmin = apilado.min(0)

    feats, resumen = [], []
    for i, clase in enumerate(cfg["clases"]):
        cruda = (ganador == i) & (dmin < tol) & ~excluidas
        px_crudos = int(cruda.sum())

        limpia = limpiar_por_grosor(cruda, ancho)
        px_limpios = int(limpia.sum())

        gs = poligonos(limpia, transform, area_min)
        ha = sum(g.area for g in gs) / 10_000
        resumen.append({
            "clase": clase["nombre"], "poligonos": len(gs), "hectareas": round(ha, 1),
            "px_antes_de_limpiar": px_crudos, "px_despues": px_limpios,
            "descartado_por_grosor_pct": round(
                100 * (px_crudos - px_limpios) / px_crudos, 1) if px_crudos else 0.0,
        })
        log(f"    {clase['nombre']:6s} {len(gs):>4} polígonos · {ha:8.1f} ha · "
            f"{resumen[-1]['descartado_por_grosor_pct']:.0f} % de píxeles "
            "descartados por ser demasiado delgados")

        for g in gs:
            g4326 = sh_transform(tr.transform, g)
            feats.append({
                "type": "Feature",
                "geometry": json.loads(json.dumps(g4326.__geo_interface__)),
                "properties": {
                    "clase": clase["nombre"],
                    "comuna": cfg["comuna"],
                    "amenaza": "inundación",
                    "fuente": cfg["fuente"],
                    "anio": str(cfg["anio_estudio"]),
                    "metodo_original": cfg["metodo_original"],
                    "escala_original": cfg["escala_impresa"],
                    "hectareas": round(g.area / 10_000, 2),
                },
            })

    if not feats:
        log(f"  [{cfg['id']}] no se obtuvo ningún polígono")
        return None

    # --- verificación independiente: ¿aterrizó donde vive la comuna? ---------
    xs = [c[0] for f in feats for c in _coords(f["geometry"])]
    ys = [c[1] for f in feats for c in _coords(f["geometry"])]
    o, su, e, n = region["bbox"]
    if not (o <= min(xs) and max(xs) <= e and su <= min(ys) and max(ys) <= n):
        raise SystemExit(
            f"[{cfg['id']}] el resultado cae FUERA de la región: "
            f"lon {min(xs):.3f}..{max(xs):.3f}, lat {min(ys):.3f}..{max(ys):.3f}. "
            "Casi siempre es un rótulo de grilla mal leído o un huso UTM "
            "equivocado en config/laminas.yaml.")
    log(f"  aterriza en lon {min(xs):.3f}..{max(xs):.3f} · lat {min(ys):.3f}..{max(ys):.3f}")

    meta = procedencia(
        fuente=cfg["fuente"],
        url=cfg.get("url", ""),
        metodo=(
            f"Vectorización de la figura «{cfg['titulo']}» (página {cfg['pagina']} "
            f"del PDF de origen) por clasificación de los colores de su leyenda. "
            f"Georreferenciada desde la retícula UTM impresa: {nota_escala}. "
            f"Resolución de la figura: {s:.2f} m por píxel. Se descartan los "
            f"rasgos más delgados que {ancho} píxeles —texto, símbolos y trazos "
            f"sueltos que comparten color con una clase—; lo que se conserva se "
            f"conserva entero, sin recortarle el borde. "
            f"MÉTODO DEL ESTUDIO ORIGINAL: {cfg['metodo_original']}."
        ),
        capa_evidencia="A_normativo",
        incertidumbre=(
            f"Producto DERIVADO: la geometría la construimos nosotros a partir de "
            f"una figura impresa, no la publica la fuente. El contenido es del "
            f"estudio de {cfg['anio_estudio']}; la georreferenciación y la "
            f"vectorización son nuestras. El borde tiene la incertidumbre del "
            f"píxel de la figura (±{s:.1f} m) más la del trazado original. "
            f"NO es modelación hidráulica y no lleva período de retorno asociado. "
            f"No tiene efecto legal: no es el vectorial del plan regulador."
        ),
        escala_original=cfg["escala_impresa"],
        fecha_dato=str(cfg["anio_estudio"]),
    )
    meta["resumen_por_clase"] = resumen
    meta["metros_por_pixel"] = round(s, 3)
    escribir_geojson(feats, SALIDA / f"{cfg['id']}.geojson", meta)
    return {"id": cfg["id"], "comuna": cfg["comuna"], "features": len(feats),
            "resumen": resumen, "m_px": round(s, 2)}


def procesar_plano(cfg: dict, region: dict) -> dict | None:
    """Pliego de plóter georreferenciado por sus vértices y clasificado por trama.

    Es el caso del Plano de Zonificación y Vialidad de un plan regulador: el
    instrumento con efecto legal. A diferencia de una figura de informe, acá el
    área de riesgo no tiene color propio —se achura sobre la zona urbana que
    haya debajo— y la georreferencia sale de los vértices rotulados.
    """
    import math
    from affine import Affine
    from pyproj import Transformer
    from rasterio.features import shapes
    from shapely.geometry import shape
    from shapely.ops import transform as sh_transform

    pdf = DATA_RAW / cfg["pdf"]
    if not pdf.exists():
        log(f"  [{cfg['id']}] falta el PDF: {pdf}")
        return None
    ims = imagenes_de(pdf, cfg["pagina"])
    im = ims[cfg.get("imagen", 0)]
    if cfg.get("rotar"):
        im = im.rotate(cfg["rotar"], expand=True)
    a = np.array(im).astype(int)
    log(f"  pliego {im.width}×{im.height} px"
        + (f" (rotado {cfg['rotar']}°)" if cfg.get("rotar") else ""))

    sol, s, rot, rmse, residuos = afin_por_vertices(cfg)
    a_, b_, tx, ty = sol
    log(f"  {s:.4f} m/píxel · rotación {rot:+.3f}° · escala impresa "
        f"1:{s / (2.54 / cfg.get('dpi', 150) / 100):.0f}")
    log(f"  RMSE {rmse:.2f} m ({rmse / s:.1f} px) sobre {len(cfg['vertices'])} "
        f"vértices — {2 * len(cfg['vertices']) - 4} grados de libertad")
    for nom, dd in residuos:
        log(f"     vértice {nom:>3s}: {dd:5.2f} m")
    tope = cfg.get("rmse_maximo_m", 15)
    if rmse > tope:
        raise SystemExit(
            f"[{cfg['id']}] RMSE {rmse:.1f} m supera el tope de {tope} m. "
            "Casi siempre es un vértice mal leído en config/laminas.yaml.")

    tr = Transformer.from_crs(f"EPSG:{cfg['epsg']}", "EPSG:4326", always_xy=True)
    feats, resumen = [], []
    for clase in cfg["clases"]:
        m, cel, n_marcas, n_usadas = mascara_por_trama(
            a, clase, s, cfg.get("excluir_x"))
        T = Affine(a_ * cel, b_ * cel, tx, b_ * cel, -a_ * cel, ty)
        area_min = float(cfg.get("area_minima_m2", 2000))
        gs = []
        for geom, val in shapes(m, mask=m.astype(bool), transform=T):
            g = shape(geom)
            if not g.is_valid:
                g = g.buffer(0)
            if g.is_empty or g.area < area_min:
                continue
            gs.append(g.simplify(s * cel * 0.5, preserve_topology=True))
        ha = sum(g.area for g in gs) / 10_000
        resumen.append({"clase": clase["nombre"], "poligonos": len(gs),
                        "hectareas": round(ha, 1), "marcas_detectadas": n_marcas})
        log(f"    {clase['nombre']:8s} {n_marcas:>6} marcas del tamaño buscado "
            f"→ {len(gs):>3} polígonos · {ha:.1f} ha")
        for g in gs:
            feats.append({
                "type": "Feature",
                "geometry": json.loads(json.dumps(
                    sh_transform(tr.transform, g).__geo_interface__)),
                "properties": {
                    "clase": clase["nombre"],
                    "descripcion": clase.get("descripcion", ""),
                    "comuna": cfg["comuna"], "amenaza": "inundación",
                    "fuente": cfg["fuente"], "anio": str(cfg["anio_estudio"]),
                    "efecto_legal": cfg.get("efecto_legal", ""),
                    "escala_original": cfg["escala_impresa"],
                    "hectareas": round(g.area / 10_000, 2),
                },
            })
    if not feats:
        log(f"  [{cfg['id']}] sin polígonos")
        return None

    xs = [c[0] for f in feats for c in _coords(f["geometry"])]
    ys = [c[1] for f in feats for c in _coords(f["geometry"])]
    o, su, e, n = region["bbox"]
    if not (o <= min(xs) and max(xs) <= e and su <= min(ys) and max(ys) <= n):
        raise SystemExit(f"[{cfg['id']}] el resultado cae fuera de la región")
    log(f"  aterriza en lon {min(xs):.4f}..{max(xs):.4f} · lat {min(ys):.4f}..{max(ys):.4f}")

    meta = procedencia(
        fuente=cfg["fuente"], url=cfg.get("url", ""),
        metodo=(
            f"Vectorización del achurado de la lámina «{cfg['titulo']}». "
            f"Georreferenciada por ajuste de semejanza sobre "
            f"{len(cfg['vertices'])} vértices del límite urbano rotulados con su "
            f"coordenada UTM en el propio plano: RMSE {rmse:.2f} m, rotación "
            f"{rot:+.3f}°, {s:.3f} m por píxel. Las clases no tienen color "
            f"propio —se achuran sobre la zona urbana— así que se identifican "
            f"por el tamaño de su marca y su densidad local, no por el tono."),
        capa_evidencia="A_normativo",
        incertidumbre=(
            f"Producto DERIVADO: la geometría la construimos nosotros a partir "
            f"del plano impreso; el organismo no la publica en vectorial. El "
            f"contenido y su efecto legal son del instrumento; la "
            f"georreferenciación y la vectorización son nuestras, con RMSE "
            f"{rmse:.1f} m. El borde hereda además el grosor del achurado."),
        escala_original=cfg["escala_impresa"], fecha_dato=str(cfg["anio_estudio"]),
    )
    meta["rmse_m"] = round(rmse, 2)
    meta["metros_por_pixel"] = round(s, 4)
    meta["resumen_por_clase"] = resumen
    escribir_geojson(feats, SALIDA / f"{cfg['id']}.geojson", meta)
    return {"id": cfg["id"], "comuna": cfg["comuna"], "features": len(feats),
            "resumen": resumen, "m_px": round(s, 2)}


def _coords(geom: dict):
    def rec(c):
        if not c:
            return
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for x in c:
                yield from rec(x)
    return list(rec(geom.get("coordinates", [])))


# ---------------------------------------------------------------- inspección

def inspeccionar(pdf: Path, pagina: int) -> None:
    """Deja la imagen con la grilla detectada marcada, para leer los rótulos."""
    from PIL import ImageDraw

    destino = SALIDA / "_inspeccion"
    destino.mkdir(parents=True, exist_ok=True)
    ims = imagenes_de(pdf, pagina)
    if not ims:
        log(f"la página {pagina} de {pdf.name} no tiene imágenes incrustadas")
        return
    for i, im in enumerate(ims):
        a = np.array(im).astype(int)
        xs, ys = lineas_de_grilla(a)
        vis = im.copy()
        d = ImageDraw.Draw(vis)
        for x in xs:
            d.line([(x, 0), (x, im.height)], fill=(255, 0, 0), width=1)
            d.text((x + 3, 6), str(x), fill=(255, 0, 0))
        for y in ys:
            d.line([(0, y), (im.width, y)], fill=(0, 160, 0), width=1)
            d.text((6, y + 3), str(y), fill=(0, 160, 0))
        ruta = destino / f"{pdf.stem}_p{pagina}_img{i}.png"
        vis.save(ruta)
        log(f"  imagen #{i}: {im.width}×{im.height} px")
        log(f"     verticales   x = {xs}")
        log(f"     horizontales y = {ys}")
        log(f"     {ruta}")
    log("")
    log("Leer en esa imagen los rótulos UTM que caen sobre las líneas marcadas y "
        "los colores de la leyenda, y anotarlos en config/laminas.yaml.")


# ------------------------------------------------------------------- censo

def _regular(pos: list[int], tol: float = 0.03, minimo: int = 2) -> list[int]:
    """Mayor subconjunto de posiciones con paso constante."""
    pos = sorted(set(int(p) for p in pos))
    mejor: list[int] = []
    for i, j in itertools.combinations(range(len(pos)), 2):
        paso = pos[j] - pos[i]
        if paso < 60:            # una retícula útil no cae cada 30 px
            continue
        serie, sig = [pos[i]], pos[i] + paso
        while sig <= pos[-1] + paso * tol:
            cand = [p for p in pos if abs(p - sig) <= max(4, paso * tol)]
            if not cand:
                break
            serie.append(min(cand, key=lambda p: abs(p - sig)))
            sig = serie[-1] + paso
        if len(serie) > len(mejor):
            mejor = serie
    return mejor if len(mejor) >= minimo else []


def censo() -> None:
    """¿A qué otras láminas del corpus se les puede aplicar esto?

    Criterio: la figura tiene que traer una retícula regular de paso grande. Un
    «paso» de 30 píxeles no es una grilla UTM, es la trama de calles, y contarla
    como grilla es la forma más fácil de publicar una mancha corrida.
    """
    idx = DATA_PROC / "eae" / "laminas_candidatas_municipales.json"
    if not idx.exists():
        raise SystemExit("falta el índice de láminas — corre antes el script 07")
    docs = json.loads(idx.read_text(encoding="utf-8"))
    ya = {l["pdf"] + f"#{l['pagina']}" for l in
          (yaml.safe_load((CONFIG / "laminas.yaml").read_text(encoding="utf-8"))
           or {}).get("laminas", [])}

    filas = []
    for doc in docs:
        if not doc["n_laminas_candidatas"]:
            continue
        pdf = DATA_RAW / doc["archivo_local"]
        if not pdf.exists():
            continue
        for hit in doc["paginas_con_amenaza"]:
            if not hit["es_probable_lamina"]:
                continue
            try:
                ims = imagenes_de(pdf, hit["pagina"])
            except Exception:  # noqa: BLE001
                continue
            for i, im in enumerate(ims):
                if im.width < 500 or im.height < 400:
                    continue
                a = np.array(im).astype(int)
                xs, ys = lineas_de_grilla(a)
                gx, gy = _regular(xs), _regular(ys)
                if not (gx and gy):
                    continue
                px = float(np.mean(np.diff(gx))) if len(gx) > 1 else 0
                py = float(np.mean(np.diff(gy))) if len(gy) > 1 else 0
                filas.append({
                    "comuna": doc["comuna"], "archivo": doc["archivo"],
                    "pdf": doc["archivo_local"].replace("\\", "/"),
                    "pagina": hit["pagina"], "imagen": i,
                    "px": f"{im.width}x{im.height}",
                    "lineas": f"{len(gx)}x{len(gy)}",
                    "paso_px": f"{px:.0f}/{py:.0f}",
                    "ya_declarada": (doc["archivo_local"].replace("\\", "/")
                                     + f"#{hit['pagina']}") in ya,
                })
    filas.sort(key=lambda f: (f["comuna"], f["pagina"]))
    log(f"{len(filas)} figura(s) con retícula regular de paso grande:")
    log("")
    for f in filas:
        marca = "ya" if f["ya_declarada"] else "  "
        log(f"  {marca} {f['comuna'][:16]:18s} p{f['pagina']:<4d} {f['px']:>10s} "
            f"{f['lineas']:>5s} líneas · paso {f['paso_px']:>9s} px  {f['archivo'][:38]}")
    destino = SALIDA / "_censo_reticulas.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
    log("")
    log(f"  índice: {destino}")
    log("  Cada una necesita que una persona lea sus rótulos UTM y los colores de "
        "su leyenda, y los anote en config/laminas.yaml. Detectar dónde está la "
        "grilla es automático; saber qué dice, no.")


# --------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="procesar sólo esta lámina")
    ap.add_argument("--inspeccionar", metavar="PDF",
                    help="marcar la grilla detectada de un PDF, para leer sus rótulos")
    ap.add_argument("--pagina", type=int, help="página, junto con --inspeccionar")
    ap.add_argument("--censo", action="store_true",
                    help="listar qué otras láminas del corpus traen retícula")
    a = ap.parse_args()

    if a.inspeccionar:
        if not a.pagina:
            raise SystemExit("--inspeccionar necesita --pagina")
        p = Path(a.inspeccionar)
        inspeccionar(p if p.exists() else DATA_RAW / a.inspeccionar, a.pagina)
        return
    if a.censo:
        censo()
        return

    region = cargar_config()["region"]
    decl = yaml.safe_load((CONFIG / "laminas.yaml").read_text(encoding="utf-8")) or {}
    laminas = decl.get("laminas", [])
    if a.id:
        laminas = [l for l in laminas if l["id"] == a.id]
        if not laminas:
            raise SystemExit(f"no hay ninguna lámina con id «{a.id}» en config/laminas.yaml")

    log(f"{len(laminas)} lámina(s) declarada(s) en config/laminas.yaml")
    hechas = []
    for cfg in laminas:
        log("")
        log(f"[{cfg['id']}] {cfg['comuna']} — {cfg['titulo']}")
        r = (procesar_plano(cfg, region) if cfg.get("vertices")
             else procesar(cfg, region))
        if r:
            hechas.append(r)

    log("")
    log(f"RESULTADO: {len(hechas)} de {len(laminas)} lámina(s) vectorizada(s)")
    for r in hechas:
        tot = sum(c["hectareas"] for c in r["resumen"])
        log(f"  {r['comuna']:14s} {r['features']:>4} polígonos · {tot:.0f} ha · "
            f"{r['m_px']} m/px")


if __name__ == "__main__":
    main()
