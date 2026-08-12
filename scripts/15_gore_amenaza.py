"""Capa C regional — amenaza de inundación modelada por el Gobierno Regional.

QUÉ ES ESTO Y POR QUÉ IMPORTA
------------------------------
El Gobierno Regional de La Araucanía modeló la amenaza de inundación de toda la
región en **2016**, para el Informe Componente Amenazas Naturales del Plan
Regional de Ordenamiento Territorial. Ese modelo está público, y hasta ahora no
lo usaba nadie.

Frente al JRC —la otra fuente modelada del visor, global y a ~1 km— este es un
salto grande de resolución: los campos `gridcode` y `count_` son la firma de un
ráster clasificado convertido a polígonos, y del área por celda sale un píxel de
**~35 m**.

AMENAZA, NO RIESGO
-------------------
El mismo estudio publica las dos, y **no son lo mismo**:

  amenaza = el fenómeno físico, dónde puede llegar el agua
  riesgo  = amenaza combinada con exposición y vulnerabilidad

Para la pregunta de este visor —«¿hasta dónde llega el agua?»— la correcta es
**amenaza**. Usar la de riesgo mete población dentro de una capa que se presenta
como física, y luego cruzarla con población sería contar dos veces lo mismo.

Y hay una segunda razón para preferirla: el estudio distingue «Amenaza de
inundación» de «Riesgo de anegamiento», es decir **separa el desborde de cauce
del anegamiento urbano**, que es exactamente el alcance de este proyecto.

LO QUE ESTA CAPA NO PUEDE DECIR
--------------------------------
Sus clases son ordinales y **no tienen significado físico**: «MEDIA» no
corresponde a ningún período de retorno, a diferencia del JRC que sí dice «100
años». Más resolución, menos interpretabilidad — el canje hay que declararlo.

Además el PROT que la encargó **nunca se aprobó**: entró a evaluación ambiental
en 2013 y no tiene resolución de término ni de aprobación. El modelo existe, el
instrumento que lo pedía murió. Y el informe metodológico no está publicado en
ningún canal del Gobierno Regional, así que **no sabemos cómo se construyó**.

Tampoco declara licencia. Antes de publicarlo hay que preguntarle al GORE.

Salida:
  data/processed/gore/amenaza-inundacion.geojson
  data/processed/gore/unidades-geomorfologicas.geojson
  web/data/gore/amenaza-inundacion.geojson    sólo clases con contenido

Uso:
  python scripts/15_gore_amenaza.py
  python scripts/15_gore_amenaza.py --verificar
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (  # noqa: E402
    DATA_PROC,
    WEB_DATA,
    escribir_geojson,
    get_bytes,
    log,
    procedencia,
)

BASE = ("https://services7.arcgis.com/UeyripQFTg6pfUe5/arcgis/rest/services/"
        "{nombre}/FeatureServer/0")

# El servicio tiene `capabilities = Query` y **no** `Extract`: no hay endpoint de
# descarga ni botón de exportación. Pero la API de consulta sí entrega geometría
# con `f=geojson`, paginando. Es el mismo patrón de comun.py.
CAPAS = {
    "amenaza-inundacion": "Amenaza_de_inundación_Región_de_la_Araucanía",
    "unidades-geomorfologicas": "Unidades_geomorfológicas_Región_de_la_Araucanía",
}

# Clases del modelo, de menor a mayor. `NULA` cubre el territorio donde el modelo
# no ve amenaza: se descarga para poder decir «acá el modelo miró y dijo que no»,
# pero no se publica al visor porque son 2.756 polígonos que no aportan nada
# visualmente y sí pesan.
ORDEN_CLASES = ["NULA", "MINIMA", "MEDIA", "MAXIMA"]

# Se publican sólo MEDIA y MAXIMA, y la razón es medida, no estética. Contrastado
# contra los puntos críticos fluviales de SENAPRED, que no participaron en el
# modelo:
#
#     NULA     ×0,2   los desbordes reales son 5 veces MÁS RAROS que el azar
#     MINIMA   ×1,0   azar puro: la clase no informa nada
#     MEDIA    ×2,9
#     MAXIMA   ×4,8   el 39,5 % de los desbordes reales, en el 8,2 % del territorio
#
# `MINIMA` son 5.909 polígonos que no distinguen nada: publicarlos sería pintar
# de color un tercio de la región para no decir nada, y pesan 4 MB en un sitio
# que tiene que descargarse por una conexión mala.
CLASES_PUBLICADAS = ["MEDIA", "MAXIMA"]

PAGINA = 1000

# El servicio devuelve 13 decimales, que a esta latitud son décimas de nanómetro.
# Para un modelo derivado de un ráster de ~35 m eso es ruido puro y ocupa la mitad
# del archivo. Cinco decimales son ~1 m: treinta y cinco veces más fino que el
# píxel del que salió el dato, así que no se pierde nada real.
DECIMALES = 5


def redondear(geom: dict) -> dict:
    """Recorta la precisión de coordenadas a la del dato de origen."""
    def r(x):
        if isinstance(x, (int, float)):
            return round(x, DECIMALES)
        return [r(v) for v in x]
    return {**geom, "coordinates": r(geom["coordinates"])}


def descargar(nombre_servicio: str, donde: str = "1=1") -> list[dict]:
    """Descarga paginando por `resultOffset`.

    La condición de parada es la bandera `exceededTransferLimit`, **nunca**
    «vino menos de lo que pedí»: un servicio puede devolver exactamente el
    tamaño de página en la última tanda y el corte por longitud perdería datos
    en silencio. Es la trampa que este proyecto ya pagó una vez.
    """
    url = BASE.format(nombre=urllib.parse.quote(nombre_servicio))
    feats: list[dict] = []
    offset = 0
    while True:
        q = (f"{url}/query?where={urllib.parse.quote(donde)}&outFields=*"
             f"&f=geojson&outSR=4326&resultOffset={offset}"
             f"&resultRecordCount={PAGINA}")
        d = json.loads(get_bytes(q))
        if "error" in d:
            # Un `outFields` inválido devuelve HTTP 200 con un objeto `error`.
            # Leer `features` con default [] lo convertiría en «capa vacía».
            raise SystemExit(f"el servicio devolvió error: {d['error']}")
        lote = d.get("features", [])
        feats.extend(lote)
        if not d.get("properties", {}).get("exceededTransferLimit"):
            break
        offset += len(lote)
        if offset > 60000:
            raise SystemExit("paginación desbocada: más de 60.000 registros")
    return feats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verificar", action="store_true",
                    help="contrasta la amenaza contra los puntos críticos fluviales")
    args = ap.parse_args()

    meta = procedencia(
        fuente="Gobierno Regional de La Araucanía — Informe Componente Amenazas "
               "Naturales, Plan Regional de Ordenamiento Territorial",
        url="https://services7.arcgis.com/UeyripQFTg6pfUe5/arcgis/rest/services",
        metodo="Ráster clasificado convertido a polígonos (los campos gridcode y "
               "count_ son su firma); del área por celda se deduce un píxel de "
               "~35 m. Republicado por CIGIDEN. Se descarga por la API de "
               "consulta porque el servicio no habilita exportación.",
        capa_evidencia="C_modelado",
        incertidumbre="Las clases son ordinales y NO tienen significado físico: "
                      "«MEDIA» no corresponde a ningún período de retorno. El PROT "
                      "que encargó el estudio nunca se aprobó, y el informe "
                      "metodológico no está publicado, así que no se conoce cómo "
                      "se construyó el modelo. No declara licencia.",
        fecha_dato="2016-05-02",
    )

    salida = DATA_PROC / "gore"
    salida.mkdir(parents=True, exist_ok=True)

    for slug, servicio in CAPAS.items():
        log(f"descargando {slug}…")
        feats = descargar(servicio)
        log(f"  {len(feats):,} polígonos")
        escribir_geojson(feats, salida / f"{slug}.geojson", meta)

        if slug == "amenaza-inundacion":
            por_clase: dict[str, int] = {}
            for f in feats:
                c = str(f["properties"].get("leyenda"))
                por_clase[c] = por_clase.get(c, 0) + 1
            for c in ORDEN_CLASES:
                if c in por_clase:
                    log(f"    {c:8s} {por_clase[c]:6,}")
            desconocidas = set(por_clase) - set(ORDEN_CLASES)
            if desconocidas:
                raise SystemExit(f"clases no previstas en el modelo: {sorted(desconocidas)}")

            publicables = [f for f in feats
                           if str(f["properties"].get("leyenda")) in CLASES_PUBLICADAS]
            for f in publicables:
                f["geometry"] = redondear(f["geometry"])
                p = f["properties"]
                f["properties"] = {
                    "clase": p.get("leyenda"),
                    "hectareas": round(float(p.get("hectares") or 0), 2),
                    "fuente": meta["fuente"],
                    "anio": 2016,
                }
            (WEB_DATA / "gore").mkdir(parents=True, exist_ok=True)
            escribir_geojson(publicables,
                             WEB_DATA / "gore" / "amenaza-inundacion.geojson", meta)

    if args.verificar:
        verificar(salida / "amenaza-inundacion.geojson")

    log("listo")


def verificar(ruta: Path) -> None:
    """Contraste contra los puntos críticos FLUVIALES de SENAPRED.

    SENAPRED no participó en la elaboración del modelo, así que la coincidencia
    es independiente. Se compara contra puntos al azar sobre la misma envolvente
    porque una capa que cubre medio territorio acierta por tamaño, no por
    acertar.
    """
    import numpy as np
    from matplotlib.path import Path as Camino

    d = json.loads(ruta.read_text(encoding="utf-8"))
    pc = json.loads((WEB_DATA / "puntos-criticos-inundacion.geojson").read_text(encoding="utf-8"))

    caminos: dict[str, list] = {}
    for f in d["features"]:
        c = str(f["properties"].get("leyenda"))
        g = f["geometry"]
        anillos = (g["coordinates"] if g["type"] == "Polygon"
                   else [a for p in g["coordinates"] for a in p])
        if anillos and len(anillos[0]) >= 4:
            caminos.setdefault(c, []).append(Camino(np.array(anillos[0])[:, :2]))

    pts = np.array([f["geometry"]["coordinates"][:2] for f in pc["features"]])
    rng = np.random.default_rng(11)
    azar = np.column_stack([rng.uniform(pts[:, 0].min(), pts[:, 0].max(), 20000),
                            rng.uniform(pts[:, 1].min(), pts[:, 1].max(), 20000)])

    def dentro(cs, p):
        m = np.zeros(len(p), bool)
        for c in cs:
            x0, y0 = c.vertices.min(0)
            x1, y1 = c.vertices.max(0)
            idx = np.where((p[:, 0] >= x0) & (p[:, 0] <= x1) &
                           (p[:, 1] >= y0) & (p[:, 1] <= y1) & ~m)[0]
            if len(idx):
                m[idx] |= c.contains_points(p[idx])
        return m

    log("")
    log("VERIFICACIÓN — amenaza GORE 2016 vs puntos críticos fluviales SENAPRED")
    log(f"  puntos fluviales: {len(pts):,}")
    log("")
    log("  clase        SENAPRED dentro        al azar         enriquecimiento")
    for c in ORDEN_CLASES:
        if c not in caminos:
            continue
        a = dentro(caminos[c], pts).mean()
        b = dentro(caminos[c], azar).mean()
        log(f"  {c:8s}   {100*a:5.1f} %              {100*b:5.1f} %          "
            f"×{a/max(b,1e-9):.1f}")
    log("")
    log("  (SENAPRED no participó en la elaboración del modelo: es independiente.)")


if __name__ == "__main__":
    main()
