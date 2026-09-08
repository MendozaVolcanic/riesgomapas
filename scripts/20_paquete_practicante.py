"""Paquete de trabajo para georreferenciar: una provincia, un archivo, una lista.

Para qué: entregarle a alguien que va a trabajar en QGIS todo lo que el proyecto
tiene de su zona, en un formato que abra de un doble clic, más la lista de lo que
falta ordenada por lo que más importa.

Por qué un **GeoPackage** y no una carpeta de shapefiles: un `.gpkg` es un solo
archivo con todas las capas adentro, sin el enredo de los seis archivos sueltos
por capa del formato SHP, sin el límite de 10 caracteres en los nombres de campo
—que truncaría `usos_prohibidos` y `estado_tramite`— y sin problemas de
codificación con las tildes. QGIS lo abre arrastrándolo.

Y una regla que el paquete respeta a propósito: **cada capa se entrega con su
procedencia adentro**, en una tabla `procedencia` del mismo archivo. Si el
paquete circula y alguien lo abre en seis meses, tiene que poder saber de dónde
salió cada polígono sin volver a preguntar. Es la misma regla del visor.

Uso:
    python 20_paquete_practicante.py --provincia Malleco
    python 20_paquete_practicante.py --provincia Cautin --salida /ruta/

Requiere: 19_estado_comunas.py (web/data/estado-comunas.json — obligatorio,
        alimenta TAREAS.md) — opcional, cada capa entra si existe: 01, 02, 06,
        13, 14, 15 y 17 (las ocho capas de web/data/ y data/processed/arclim/
        listadas en CAPAS) y 18 (láminas vectorizadas y censo de retículas).
Salida: data/processed/paquete_<provincia>/
          1_cartografia_ya_vectorizada/<lamina>/
                                   una carpeta POR DOCUMENTO: el PDF original, la
                                   página con la lámina en JPG, los polígonos que
                                   salieron de ella y un LEEME que dice qué es
          2_laminas_por_georreferenciar/
                                   los documentos con lámina localizada que
                                   todavía no se convierten, con su PDF e índice
          capas_<provincia>.gpkg   todas las capas recortadas a la provincia
          TAREAS.md / .docx        qué falta, por comuna, ordenado por prioridad
          LEEME.md / .docx         cómo trabajar y qué devolver

        Todo texto sale en Markdown y en Word. El `.md` es la copia de
        referencia —se versiona, se compara, se abre en cualquier sistema—; el
        `.docx` es el que abre quien recibe el paquete, que trabaja en Windows
        con Word y para quien un `.md` es marcado crudo en el Bloc de notas.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import CONFIG, DATA_PROC, DATA_RAW, WEB_DATA, cargar_config, log  # noqa: E402


def nz(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z ]", "", t.upper()).strip()


def cargar(p: Path):
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# Qué capas van al paquete. El nombre corto es el que verá en QGIS, así que se
# elige para que se entienda sin leer documentación: dice QUÉ ES y de cuándo.
CAPAS = [
    ("areas_riesgo_PRC_MINVU", WEB_DATA / "areas-riesgo-inundacion.geojson",
     "Área de riesgo por inundación del Plan Regulador. ÚNICA capa con efecto "
     "legal. Ojo: sólo existe en las comunas cuyo PRC la definió."),
    ("puntos_criticos_SENAPRED", WEB_DATA / "puntos-criticos-inundacion.geojson",
     "Dónde el municipio reportó inundación. `cronico`=true significa que se "
     "repite en 3 o más temporadas."),
    ("huella_observada_satelite", WEB_DATA / "sar" / "huella-observada.geojson",
     "Agua observada por radar Sentinel-1 en el evento de jul-ago 2026. Es "
     "medición, no modelo — pero mira `fecha_observacion`: si la pasada fue "
     "días después, el agua ya había bajado."),
    ("cobertura_satelite", WEB_DATA / "sar" / "cobertura-sar.geojson",
     "Dónde SÍ pudo mirar el satélite. Fuera de esto, «no hay huella» no "
     "significa «no se inundó»."),
    ("amenaza_modelada_GORE_2016", WEB_DATA / "gore" / "amenaza-inundacion.geojson",
     "Modelo regional del Gobierno Regional, 2016, ~35 m. Clases cualitativas "
     "(mínima/media/máxima), sin período de retorno."),
    ("amenaza_modelada_JRC_100a", WEB_DATA / "jrc" / "rp100.geojson",
     "Modelo global europeo, retorno 100 años, ~1 km. Sirve de línea base "
     "donde no hay nada; a esa resolución no distingue calles."),
    ("campamentos", WEB_DATA / "campamentos-inundacion.geojson",
     "Campamentos catastrados por MINVU que caen dentro de área de riesgo."),
    ("desbordes_ARClim", DATA_PROC / "arclim" / "desbordes-araucania.geojson",
     "Sitios de análisis de desborde del atlas ARClim (MMA). Puntos, no áreas."),
]


def recortar(fc: dict, comunas: set[str], caja: tuple | None = None) -> list[dict]:
    """Recorta a la provincia. Por comuna si el dato la trae; si no, por caja.

    Las capas MODELADAS y la SATELITAL no tienen campo `comuna` —son ráster
    vectorizado, no un registro administrativo—, así que filtrar sólo por ese
    campo las dejaba fuera enteras. Y son justamente las que sirven para
    comparar contra lo que declara el plan regulador.

    Para ésas se usa la caja envolvente de la provincia, derivada de los datos
    que SÍ traen comuna. Es aproximada y se dice: sobra territorio en los
    bordes, y eso es preferible a entregar la capa vacía o a inventar un límite
    provincial que no tenemos.
    """
    out = []
    tiene_comuna = any(f.get("properties", {}).get("comuna")
                       for f in fc.get("features", [])[:50])
    for f in fc.get("features", []):
        if tiene_comuna:
            c = nz(f.get("properties", {}).get("comuna"))
            if c and c in comunas:
                out.append(f)
        elif caja and _toca(f.get("geometry"), caja):
            out.append(f)
    return out


def _toca(geom: dict | None, caja: tuple) -> bool:
    """¿La geometría cae dentro de la caja? Basta con que un vértice lo haga."""
    if not geom:
        return False
    o, s, e, n = caja

    def rec(c) -> bool:
        if not c:
            return False
        if isinstance(c[0], (int, float)):
            return o <= c[0] <= e and s <= c[1] <= n
        return any(rec(x) for x in c)
    return rec(geom.get("coordinates"))


def caja_de(comunas: set[str]) -> tuple:
    """Caja envolvente de la provincia, con margen, desde los datos que sí
    declaran comuna. Los puntos críticos cubren las 32 comunas de la región, así
    que dan un contorno razonable de dónde está cada provincia."""
    xs, ys = [], []
    fc = cargar(WEB_DATA / "puntos-criticos-inundacion.geojson") or {"features": []}
    for f in fc["features"]:
        if nz(f["properties"].get("comuna")) in comunas:
            x, y = f["geometry"]["coordinates"]
            xs.append(x)
            ys.append(y)
    if not xs:
        raise SystemExit("no hay puntos con comuna de esta provincia; sin ellos "
                         "no se puede acotar la extensión")
    m = 0.15                      # ~15 km de margen
    return (min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provincia", default="Malleco")
    ap.add_argument("--salida", help="carpeta destino (por omisión, data/processed/)")
    ap.add_argument("--solo-zip", action="store_true",
                    help="no rehace el paquete: sólo vuelve a comprimirlo. Sirve "
                         "para incluir algo que se agregó después, como el "
                         "informe de revisión de los polígonos.")
    a = ap.parse_args()

    cfg = cargar_config()
    prov = {nz(k): v for k, v in cfg["provincias"].items()}
    clave = nz(a.provincia)
    if clave not in prov:
        raise SystemExit(f"provincia desconocida: {a.provincia}. "
                         f"Las que hay: {sorted(prov)}")
    comunas = {nz(c) for c in prov[clave]}
    log(f"provincia de {a.provincia.title()}: {len(comunas)} comunas")

    base = Path(a.salida) if a.salida else DATA_PROC
    dest = base / f"paquete_{clave.lower()}"
    if a.solo_zip:
        if not dest.exists():
            raise SystemExit(f"no existe {dest}: no hay nada que comprimir. "
                             "Corre este script sin --solo-zip.")
        empaquetar(dest)
        return
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------ GeoPackage
    import geopandas as gpd
    from shapely.geometry import shape

    caja = caja_de(comunas)
    log(f"  extensión de la provincia: lon {caja[0]:.2f}..{caja[2]:.2f} · "
        f"lat {caja[1]:.2f}..{caja[3]:.2f} (con 15 km de margen)")

    gpkg = dest / f"capas_{clave.lower()}.gpkg"
    proc_filas = []
    vacias = []
    for nombre, ruta, ayuda in CAPAS:
        fc = cargar(ruta)
        if not fc:
            vacias.append((nombre, f"no existe {ruta.name} — corre el script que lo produce"))
            continue
        feats = recortar(fc, comunas, caja)
        if not feats:
            vacias.append((nombre, "ninguna geometría cae en esta provincia"))
            continue
        gdf = gpd.GeoDataFrame(
            [{k: v for k, v in f["properties"].items()} for f in feats],
            geometry=[shape(f["geometry"]) for f in feats], crs="EPSG:4326")
        gdf.to_file(gpkg, layer=nombre, driver="GPKG")
        p = (fc.get("procedencia") or {})
        proc_filas.append({
            "capa": nombre, "para_que_sirve": ayuda,
            "fuente": p.get("fuente", ""), "url": p.get("url", ""),
            "metodo": p.get("metodo", ""),
            "incertidumbre": p.get("incertidumbre", ""),
            "capa_evidencia": p.get("capa_evidencia", ""),
            "n_geometrias": len(feats),
        })
        log(f"  {nombre:32s} {len(feats):>5} geometrías")

    # Las láminas que ya convertimos: van aparte y MARCADAS como derivadas, para
    # que nadie las confunda con el vectorial oficial. Y además de entrar al
    # GeoPackage, cada una arma su propia carpeta con el documento del que salió
    # (ver `carpeta_por_documento`).
    import yaml
    declaradas = {c["id"]: c for c in (yaml.safe_load(
        (CONFIG / "laminas.yaml").read_text(encoding="utf-8")) or {}).get("laminas", [])}
    docs_dir = dest / "1_cartografia_ya_vectorizada"
    fichas = []
    for f in sorted((DATA_PROC / "laminas").glob("*.geojson")):
        fc = cargar(f)
        feats = recortar(fc, comunas, caja)
        if not feats:
            continue
        cfg_lam = declaradas.get(f.stem)
        if cfg_lam:
            # El id ya empieza por la comuna («angol-prc-ar2a-lamina1»), así que
            # anteponerla otra vez sólo alargaba el nombre.
            nombre_carpeta = _slug(cfg_lam["id"])
            fichas.append(carpeta_por_documento(
                cfg_lam, fc, feats, docs_dir / nombre_carpeta))
            log(f"    carpeta {nombre_carpeta}: documento + lámina + "
                f"{len(feats)} polígonos + resumen")
        else:
            log(f"    [{f.stem}] no está declarada en config/laminas.yaml: "
                "va al GeoPackage pero sin carpeta propia")
        gdf = gpd.GeoDataFrame(
            [f2["properties"] for f2 in feats],
            geometry=[shape(f2["geometry"]) for f2 in feats], crs="EPSG:4326")
        nombre = f"DERIVADO_{f.stem.replace('-', '_')[:50]}"
        gdf.to_file(gpkg, layer=nombre, driver="GPKG")
        p = (fc.get("procedencia") or {})
        proc_filas.append({
            "capa": nombre,
            "para_que_sirve": "GEOMETRÍA CONSTRUIDA POR NOSOTROS desde una lámina "
                              "impresa. NO la publica la fuente. Útil para "
                              "comparar, no para citar como oficial.",
            "fuente": p.get("fuente", ""), "url": p.get("url", ""),
            "metodo": p.get("metodo", ""),
            "incertidumbre": p.get("incertidumbre", ""),
            "capa_evidencia": p.get("capa_evidencia", ""),
            "n_geometrias": len(feats),
        })
        log(f"  {nombre:32s} {len(feats):>5} geometrías")

    if proc_filas:
        import pandas as pd
        pd.DataFrame(proc_filas).to_file if False else None
        gpd.GeoDataFrame(proc_filas, geometry=[None] * len(proc_filas),
                         crs="EPSG:4326").to_file(
            gpkg, layer="00_procedencia_de_cada_capa", driver="GPKG")
    log(f"  → {gpkg.name} ({gpkg.stat().st_size // 1024} KB)")
    for n, motivo in vacias:
        log(f"  (sin datos) {n}: {motivo}")

    # ------------------------------------------------------------- las tareas
    #
    # estado-comunas.json (script 19) está en el Requiere: de este script
    # (scripts/ORDEN.md). TAREAS.md existe para decirle al practicante qué
    # falta por comuna: si este archivo no está, la línea de abajo lo
    # reemplazaba por `{"comunas": []}` y el paquete salía con TAREAS.md
    # diciendo, en silencio, «nada falta en ninguna comuna» — el resultado
    # falso opuesto a lo que el archivo promete (F-12, auditoría 2026-09-06).
    _estado_ruta = WEB_DATA / "estado-comunas.json"
    _estado_json = cargar(_estado_ruta)
    if _estado_json is None:
        raise SystemExit(
            f"no existe {_estado_ruta}.\n"
            "TAREAS.md se arma a partir de ese inventario: sin él saldría "
            "diciendo que a ninguna comuna le falta nada, que es falso. Corre "
            "antes:\n"
            "    python scripts/19_estado_comunas.py")
    estado = {nz(c["comuna"]): c for c in _estado_json["comunas"]}
    censo = cargar(DATA_PROC / "laminas" / "_censo_reticulas.json") or []
    ret_por_comuna: dict[str, list] = {}
    for r in censo:
        if nz(r["comuna"]) in comunas:
            ret_por_comuna.setdefault(nz(r["comuna"]), []).append(r)

    filas = []
    for c in sorted(comunas):
        e = estado.get(c, {})
        filas.append({
            "comuna": e.get("comuna", c.title()),
            "hab": e.get("personas") or 0,
            "puntos": e.get("puntos_inundacion", 0),
            "cronicos": e.get("puntos_cronicos", 0),
            "area": e.get("poligonos_area_riesgo", 0),
            "docs": e.get("documentos", 0),
            "laminas": e.get("laminas_localizadas", 0),
            "reticulas": len(ret_por_comuna.get(c, [])),
            "derivados": e.get("poligonos_vectorizados_por_nosotros", 0),
        })
    # Prioridad: gente sin nada consultable, y con registro de que sí se inunda.
    def prioridad(f):
        sin_nada = (f["area"] == 0 and f["laminas"] == 0)
        return (-int(sin_nada), -f["cronicos"], -f["hab"])
    filas.sort(key=prioridad)

    # Todas las capas, también en shapefile. El GeoPackage sigue siendo la copia
    # de referencia —conserva los nombres de campo completos y los textos de
    # procedencia enteros—, pero el shapefile es lo que circula entre servicios
    # públicos y lo que abre un ArcGIS antiguo, y pedirle a alguien que exporte
    # doce capas a mano antes de empezar es una barrera tonta.
    shp_todas = dest / "3_capas_en_shapefile"
    shp_todas.mkdir(parents=True, exist_ok=True)
    import fiona
    recortes = []
    for capa in fiona.listlayers(gpkg):
        if capa.startswith("00_"):
            continue
        g = gpd.read_file(gpkg, layer=capa)
        if g.empty:
            continue
        destino_shp = shp_todas / f"{capa[:40]}.shp"
        g.to_file(destino_shp, driver="ESRI Shapefile", encoding="utf-8")
        # Qué pasó de verdad, leyendo el shapefile recién escrito. Deducirlo de
        # la regla «se corta a diez caracteres» no basta: cuando dos campos
        # colisionan al acortarse, uno se PIERDE entero y en silencio. Pasó con
        # `ordenanza_url` y `ordenanza_url_vigente`, que quedan en el mismo
        # `ordenanza_`: se publicaba la URL de la ordenanza y desaparecía el
        # campo que dice si sigue vigente.
        # Se comparan las columnas POR POSICIÓN contra el shapefile recién
        # escrito, que es la única forma de saber qué nombre quedó de verdad.
        # Deducirlo de la regla «se corta a diez caracteres» da un resultado
        # falso cuando dos campos chocan: `ordenanza_url` y
        # `ordenanza_url_vigente` no se pierden —eso llegué a escribir— sino
        # que el segundo queda como `ordenanz_1`, un nombre que nadie asocia
        # con el original si no se le dice.
        acortados, raros = [], []
        try:
            vuelta = gpd.read_file(destino_shp)
            orig = [c for c in g.columns if c != "geometry"]
            nuevo = [c for c in vuelta.columns if c != "geometry"]
            for o, n in zip(orig, nuevo):
                if o == n:
                    continue
                (raros if n.lower() != o[:10].lower() else acortados).append((o, n))
        except Exception:               # noqa: BLE001
            acortados = [(c, c[:10]) for c in g.columns
                         if c != "geometry" and len(c) > 10]
        recortes.append((capa, len(g), acortados, raros))
    (shp_todas / "LEEME.md").write_text("\n".join(
        ["# Las mismas capas, en shapefile", "",
         "Están acá por comodidad: es lo que circula entre servicios públicos y lo",
         "que abre un ArcGIS antiguo. **La copia de referencia sigue siendo**",
         f"**`../{gpkg.name}`**, porque el shapefile corta los nombres de campo a",
         "diez caracteres y el texto a 254, y la procedencia de este proyecto vive",
         "en campos de texto largo.", "",
         "⚠️ **Mira la última columna antes de usar una capa.** Cuando dos campos",
         "quedan iguales al cortarse a diez caracteres, el segundo no se pierde:",
         "queda con un nombre que nadie asocia con el original. Lo de abajo NO",
         "está deducido de la regla — se midió leyendo cada shapefile después de",
         "escribirlo y comparando columna por columna.", "",
         "| Capa | Geometrías | Nombres acortados | RENOMBRADOS sin parecido |",
         "|---|---:|---|---|"]
        + [f"| {c} | {n} | "
           f"{', '.join(f'`{o}` → `{d}`' for o, d in ac) if ac else '—'} | "
           f"{'**' + ', '.join(f'`{o}` → `{d}`' for o, d in ra) + '**' if ra else '—'} |"
           for c, n, ac, ra in recortes]
        + ["", "Si una capa tiene campos renombrados sin parecido y necesitas ese",
           f"dato, ábrela desde `../{gpkg.name}`, que conserva los nombres enteros.",
           "",
           "Cada capa son cinco archivos (`.shp`, `.dbf`, `.shx`, `.prj`, `.cpg`)",
           "y **se copian juntos o no funciona**.", ""]),
        encoding="utf-8")
    log(f"  3_capas_en_shapefile: {len(recortes)} capas exportadas a .shp")

    # De dónde salió cada polígono, con su enlace: la primera pregunta de
    # cualquiera que recibe geometría ajena.
    n_filas = tabla_de_fuentes(dest, gpkg)
    log(f"  FUENTE_DE_CADA_POLIGONO: {n_filas} geometrías con su fuente y enlace")

    # La guía de trabajo, en QGIS y sin una línea de código: quien recibe esto
    # no tiene el repositorio ni corre los scripts.
    escribir_guia_qgis(dest, a.provincia.title())

    # Los documentos con lámina localizada que aún no se vectorizan: el trabajo
    # que se le encarga al practicante, con su PDF al lado.
    pendientes = carpeta_pendientes(
        dest / "2_laminas_por_georreferenciar", comunas,
        {(DATA_RAW / declaradas[f["id"]]["pdf"]).name: f["carpeta"]
         for f in fichas if f.get("id") in declaradas},
        ret_por_comuna)
    log(f"  2_laminas_por_georreferenciar: {pendientes} PDF copiados + índice")

    escribir_tareas(dest, a.provincia.title(), filas, ret_por_comuna)
    escribir_leeme(dest, a.provincia.title(), gpkg.name, fichas, pendientes)

    # Todo lo que se escribió en Markdown, también en Word: el paquete lo abre
    # alguien en Windows, donde un .md se ve como marcado crudo.
    convertidos = sum(a_word(m) for m in sorted(dest.rglob("*.md")))
    if convertidos:
        log(f"  {convertidos} documento(s) convertidos a Word (.docx)")

    empaquetar(dest)
    log("")
    log(f"PAQUETE LISTO → {dest}")
    log(f"  {gpkg.name} · TAREAS.md · LEEME.md · "
        f"{len(fichas)} carpeta(s) por documento")


# Lado mayor de la imagen de la lámina que se copia a cada carpeta. Es una
# elección de entrega, no del dato: el PDF original va al lado y ahí está todo
# el detalle.
LADO_MAYOR_LAMINA_PX = 4000


def tabla_de_fuentes(dest: Path, gpkg: Path) -> int:
    """Un polígono por fila, con su fuente y el enlace para abrirla.

    Por qué hace falta si cada polígono ya lleva su fuente pegada: porque para
    verla hay que abrir QGIS, cargar la capa y hacer clic uno por uno. Esta
    tabla contesta de una mirada «¿de dónde salió cada cosa que hay acá?», que
    es la primera pregunta de cualquiera que reciba geometría ajena.

    Sale en dos formas por el mismo motivo por el que existe: el `.csv` se abre
    en Excel y se ordena y filtra —son cientos de filas—; el resumen agrupado
    por documento cabe en una página y es el que se lee.
    """
    import csv
    import fiona
    import geopandas as gpd

    # Las capas que bajamos de un servicio no traen `url` por geometría —su
    # dirección es de la capa entera, no de cada polígono— así que se toma de la
    # tabla de procedencia que el propio paquete lleva adentro. Sin esto la
    # columna «Enlace» quedaba vacía justo en las capas oficiales, que son las
    # que más falta hace poder ir a mirar.
    url_de_capa: dict[str, str] = {}
    try:
        proc = gpd.read_file(gpkg, layer="00_procedencia_de_cada_capa")
        url_de_capa = {str(r["capa"]): str(r.get("url") or "")
                       for _, r in proc.iterrows()}
    except Exception:                   # noqa: BLE001
        pass

    filas = []
    for capa in fiona.listlayers(gpkg):
        if capa.startswith("00_"):
            continue
        g = gpd.read_file(gpkg, layer=capa)
        if g.empty:
            continue
        cols = set(g.columns)
        for i, r in g.iterrows():
            geom = r.geometry
            filas.append({
                "capa": capa,
                "id_en_la_capa": i,
                "que_es": next((str(r[c]) for c in ("clase", "clasificacion",
                                                    "nombre", "sector", "causa")
                                if c in cols and r.get(c) not in (None, "")), ""),
                "comuna": str(r.get("comuna", "")) if "comuna" in cols else "",
                "hectareas": (round(geom.area * 1.11e10 / 1e4, 2)
                              if geom is not None and geom.geom_type in
                              ("Polygon", "MultiPolygon") else ""),
                "anio": str(r.get("anio", "")) if "anio" in cols else "",
                "fuente": str(r.get("fuente", "")) if "fuente" in cols else "",
                "enlace": (str(r.get("url", "")) if "url" in cols and r.get("url")
                           else url_de_capa.get(capa, "")),
                "estado_tramite": (str(r.get("estado_tramite", ""))
                                   if "estado_tramite" in cols else ""),
                "incertidumbre_borde_m": (str(r.get("incertidumbre_borde_m", ""))
                                          if "incertidumbre_borde_m" in cols else ""),
            })
    if not filas:
        return 0

    with open(dest / "FUENTE_DE_CADA_POLIGONO.csv", "w", newline="",
              encoding="utf-8-sig") as fh:      # BOM: Excel abre las tildes bien
        w = csv.DictWriter(fh, fieldnames=list(filas[0]), delimiter=";")
        w.writeheader()
        w.writerows(filas)

    # El resumen: una fila por documento, no por polígono.
    from collections import defaultdict
    grupos: dict[tuple, list] = defaultdict(list)
    for f in filas:
        grupos[(f["capa"], f["fuente"], f["enlace"], f["anio"])].append(f)
    L = ["# De dónde salió cada polígono", "",
         "Cada polígono lleva su fuente y su enlace **pegados en la tabla de**",
         "**atributos**: en QGIS, clic derecho en la capa → *Abrir tabla de",
         "atributos*, o la herramienta *Identificar objetos espaciales* y un clic",
         "sobre el polígono. Ahí están las columnas `fuente`, `url`, `anio` y",
         "—en lo que trazamos nosotros— `incertidumbre_borde_m`.",
         "",
         "Esta tabla es el resumen: una fila por documento. El detalle polígono",
         "por polígono está en **`FUENTE_DE_CADA_POLIGONO.csv`**, que se abre en",
         "Excel y se puede ordenar y filtrar.",
         "",
         "| Capa | Qué contiene | Polígonos | Año | Fuente | Enlace |",
         "|---|---|---:|---|---|---|"]
    for (capa, fuente, enlace, anio), fs in sorted(grupos.items()):
        clases = sorted({f["que_es"] for f in fs if f["que_es"]})
        que = ", ".join(clases[:4]) + ("…" if len(clases) > 4 else "")
        link = f"[abrir]({enlace})" if str(enlace).startswith("http") else "—"
        L.append(f"| {capa} | {que[:60]} | {len(fs)} | {anio or '—'} | "
                 f"{(fuente or '—')[:110]} | {link} |")
    L += ["",
          "Ojo con qué abre cada enlace. Los de las láminas llevan al documento",
          "del municipio; los de las capas oficiales, al **servicio de datos** del",
          "que se descargan —un servidor ArcGIS o un catálogo—, no a un informe.",
          "El detalle de cómo se procesó cada una está en la tabla",
          "`00_procedencia_de_cada_capa` del GeoPackage.", ""]
    (dest / "FUENTE_DE_CADA_POLIGONO.md").write_text("\n".join(L), encoding="utf-8")
    return len(filas)


def empaquetar(dest: Path) -> Path:
    """El .zip que se entrega, SIN los `.md`.

    Quien lo recibe abre los `.docx`; tener el mismo texto dos veces en formatos
    distintos sólo invita a preguntar cuál es el bueno. Los `.md` se quedan en la
    carpeta de trabajo, que es donde sirven para comparar entre versiones.
    """
    import zipfile
    zip_path = dest.parent / f"{dest.name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    n = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(dest.rglob("*")):
            if f.is_dir() or f.suffix.lower() == ".md":
                continue
            z.write(f, Path(dest.name) / f.relative_to(dest))
            n += 1
    log(f"  {zip_path.name}: {n} archivos, "
        f"{zip_path.stat().st_size / 1e6:.0f} MB (sin los .md)")
    return zip_path


def escribir_guia_qgis(dest: Path, prov: str) -> None:
    """El procedimiento completo en QGIS, sin una sola línea de código.

    Existe porque quien recibe este paquete trabaja SÓLO en QGIS: no tiene el
    repositorio, no corre los scripts y no tiene por qué. Las instrucciones que
    había antes le mandaban a correr `18_vectorizar_laminas.py --inspeccionar`,
    que para él es otro idioma.
    """
    (dest / "COMO_TRABAJAR_EN_QGIS.md").write_text("\n".join([
        "# Cómo georreferenciar y digitalizar una lámina, en QGIS",
        "",
        "Todo esto se hace dentro de QGIS. No necesitas programar ni instalar",
        "nada más. Se explica con una lámina que tenga **cuadrícula UTM impresa**",
        "—las coordenadas rotuladas en los márgenes—, que es el caso fácil y el",
        "de casi todas las de `2_laminas_por_georreferenciar`.",
        "",
        "---",
        "",
        "## 0. Antes de empezar: ¿esta lámina sirve?",
        "",
        "Cinco minutos acá ahorran una tarde.",
        "",
        "1. **Lee el texto de la página**, no sólo el título. Una lámina de",
        "   «riesgo» puede ser multiamenaza y no distinguir niveles de",
        "   inundación; ésa no sirve para esto.",
        "2. **Mira dónde caen los colores de la leyenda.** El título de una lámina",
        "   nombra su MARCO, no lo que mapea: descartamos una que decía «Mapa",
        "   Inundación Subcuenca Ríos Malleco y Vergara» y tenía todos sus",
        "   polígonos de riesgo fuera de esa subcuenca.",
        "3. **Busca los rótulos de la cuadrícula.** Si la figura está recortada al",
        "   marco y no se ve ninguna coordenada, no se puede georreferenciar por",
        "   cuadrícula: pasa al método del punto 6.",
        "",
        "## 1. Sacar la lámina del PDF como imagen",
        "",
        "En tu lector de PDF, abre el documento en la página que dice el índice y",
        "expórtala como imagen (**Archivo → Exportar → Imagen**, o una captura a",
        "pantalla completa con el PDF al máximo zoom). Guárdala como PNG o JPG.",
        "",
        "Mientras más resolución, mejor: cada píxel de la imagen es la unidad más",
        "fina que vas a poder dibujar después.",
        "",
        "## 2. Abrir el Georreferenciador",
        "",
        "En QGIS 3.x: **Capa → Georreferenciador…** (en versiones anteriores está",
        "en *Ráster → Georreferenciador*; si no aparece, actívalo en",
        "*Complementos → Administrar e instalar complementos → Georeferencer GDAL*).",
        "",
        "Se abre una ventana aparte. Ahí dentro: **Archivo → Abrir ráster** y",
        "eliges la imagen del paso 1.",
        "",
        "## 3. Poner los puntos de control",
        "",
        "Un punto de control le dice a QGIS «este píxel de la imagen es esta",
        "coordenada del mundo». Con la cuadrícula impresa los tienes regalados:",
        "cada cruce de la retícula viene rotulado.",
        "",
        "Con la herramienta **Añadir punto**, haz clic exactamente en un cruce de",
        "la cuadrícula. Se abre un cuadro pidiendo las coordenadas: escribe las",
        "que dice el rótulo de ese cruce, **Este (X) primero, Norte (Y) después**.",
        "",
        "**El sistema de coordenadas.** Las láminas chilenas vienen casi siempre",
        "en UTM WGS84. En La Araucanía hay dos husos y elegir mal manda la lámina",
        "al Pacífico:",
        "",
        "| Si el Este ronda… | Es huso | Código a elegir |",
        "|---|---|---|",
        "| 600.000 – 780.000 (Angol, Purén, Traiguén, Collipulli) | 18 Sur | **EPSG:32718** |",
        "| 200.000 – 350.000 (Lonquimay, Curacautín cordillera) | 19 Sur | **EPSG:32719** |",
        "",
        "⚠️ **No le creas al recuadro de información cartográfica de la lámina.**",
        "La de Catripulli declara «Huso 18 Sur» y es 19: con 18 caería en el mar.",
        "Si al terminar la lámina no aterriza sobre su pueblo, el huso es lo",
        "primero que hay que revisar.",
        "",
        "**Cuántos puntos.** Cuatro o más, **repartidos por toda la hoja** —las",
        "cuatro esquinas antes que cuatro juntos en un rincón—. Con tres el ajuste",
        "todavía deja residuo que medir; con dos, el error sale 0 y esa cifra",
        "miente: no es que esté perfecto, es que no hay nada contra qué comparar.",
        "",
        "## 4. Configurar y ejecutar",
        "",
        "Botón **Configuración de transformación** (el engranaje):",
        "",
        "| Campo | Qué poner | Por qué |",
        "|---|---|---|",
        "| Tipo de transformación | **Polinomial 1** (o Helmert) | Un mapa impreso tiene una sola escala y no está deformado: mover, girar y escalar basta. Los polinomios de grado 2 o 3 «arreglan» el error deformando la imagen, y el RMSE baja sin que la ubicación mejore. |",
        "| Método de remuestreo | **Vecino más próximo** | No inventa colores nuevos entre píxeles, y acá los colores son la clase. |",
        "| SRC de destino | El huso de la tabla de arriba | |",
        "| Ráster de salida | Un `.tif` con nombre claro | |",
        "| Cargar en QGIS al terminar | ✔ | |",
        "",
        "Antes de ejecutar, **mira la columna de residuos** en la tabla de puntos:",
        "es cuánto se equivoca cada punto. Si uno tiene un residuo mucho mayor que",
        "el resto, casi siempre es un rótulo mal tecleado o un clic corrido;",
        "corrígelo antes de seguir.",
        "",
        "**Guarda los puntos de control** (Archivo → Guardar puntos GCP como…):",
        "es un `.points` que va en la entrega y permite rehacer todo.",
        "",
        "Después, **Ejecutar**.",
        "",
        "## 5. Comprobar que quedó donde debe",
        "",
        "Esto no es opcional. Una lámina puede estar perfectamente ajustada y",
        "aterrizar en el lugar equivocado.",
        "",
        "1. Carga encima **`puntos_criticos_SENAPRED`** del GeoPackage. Son sitios",
        "   donde el municipio reportó inundación y no participaron en tu ajuste.",
        "   Si tu lámina de inundación no tiene **ningún** punto crítico cerca,",
        "   sospecha antes de creerle.",
        "2. Enciende un mapa base (**Complementos → QuickMapServices**, o",
        "   *XYZ Tiles → OpenStreetMap* en el panel Explorador) y comprueba que",
        "   los ríos y calles de la lámina calzan con los del mapa.",
        "",
        "## 6. Si la lámina NO tiene cuadrícula rotulada",
        "",
        "Mismo procedimiento, pero los puntos de control los sacas comparando la",
        "lámina con el mapa base: cruces de calle, puentes, esquinas de manzana,",
        "confluencias de ríos. Elige puntos **nítidos en las dos imágenes** y",
        "repartidos. Espera un error mayor, y **déjalo declarado**: un polígono",
        "sin error declarado no se publica.",
        "",
        "## 7. Digitalizar los polígonos",
        "",
        "Con el ráster ya ubicado, se dibuja encima.",
        "",
        "1. **Capa → Crear capa → Nueva capa de GeoPackage** (o shapefile si",
        "   prefieres). Tipo de geometría: **Polígono**. SRC: el mismo huso UTM.",
        "2. Crea estos campos, con estos nombres, para que calce con lo que ya",
        "   existe. Si usas shapefile los nombres se cortan a diez caracteres: el",
        "   de la derecha es el que quedará.",
        "",
        "| Campo | En shapefile | Qué va |",
        "|---|---|---|",
        "| `clase` | `clase` | El nombre EXACTO que usa la leyenda: «Alto», «AR-2a», «Susceptibilidad media». No lo traduzcas ni lo uniformes. |",
        "| `comuna` | `comuna` | En mayúsculas, como en las otras capas. |",
        "| `amenaza` | `amenaza` | `inundación` |",
        "| `fuente` | `fuente` | Nombre completo del documento, con su organismo y su fecha. |",
        "| `anio` | `anio` | El año del ESTUDIO, no el del decreto que lo aprueba. Son distintos. |",
        "| `escala_original` | `escala_ori` | La escala impresa de la lámina, si la declara. |",
        "| `estado_tramite` | `estado_tra` | `derivado` |",
        "| `incertidumbre_borde_m` | `incertidum` | El RMSE que te dio el georreferenciador, en metros. |",
        "",
        "3. Activa la edición (el lápiz), **Añadir polígono**, y dibuja siguiendo",
        "   el borde del color. Un clic por vértice, clic derecho para cerrar.",
        "4. Usa **Ajustar (snapping)** para que los polígonos vecinos compartan",
        "   borde y no queden huecos ni solapes entre ellos.",
        "5. Guarda la edición y apaga el lápiz.",
        "",
        "**Un polígono por mancha continua**, no uno gigante con todo. Y si una",
        "mancha tiene un hueco adentro, dibújalo como anillo interior (herramienta",
        "*Añadir anillo*), no como un polígono aparte.",
        "",
        "## 8. Antes de entregar, revísalo",
        "",
        "- **Vector → Herramientas de geometría → Comprobar validez**: no puede",
        "  quedar ninguna geometría inválida.",
        "- Abre la tabla de atributos y confirma que **ningún campo quedó vacío**.",
        "- Compara de nuevo contra los puntos críticos de SENAPRED.",
        "- Mira si algún polígono quedó **pegado al borde de la lámina**: eso",
        "  significa que la mancha sigue fuera de la hoja y está cortada. Anótalo,",
        "  no lo dibujes «hacia afuera» adivinando.",
        "",
        "---",
        "",
        "## Qué entregar de vuelta",
        "",
        f"Una carpeta por lámina, igual que las de `1_cartografia_ya_vectorizada`:",
        "",
        "- El **`.gpkg` o el `.shp`** con los polígonos y sus campos llenos.",
        "- El **`.tif` georreferenciado** que produjo el paso 4.",
        "- El **`.points`** con los puntos de control.",
        "- Un **texto corto** que diga: qué lámina es, de qué documento y página,",
        "  qué huso usaste, cuántos puntos de control y qué RMSE dio, y **qué no",
        "  pudiste hacer y por qué**. Esa última parte vale tanto como el resto:",
        "  es la que evita que la próxima persona repita el intento.",
        "",
        "## Lo que nunca hay que hacer",
        "",
        "- **No dibujar polígonos «aproximando»** dónde se inundaría. Si no sale",
        "  de un documento con autor y fecha, no entra.",
        "- **No inventar una coordenada** que no esté en la lámina, ni siquiera",
        "  «redondeando» un rótulo que se ve borroso.",
        "- **No mezclar capas de distinto origen** en un mismo archivo. Cada",
        "  documento, su carpeta.",
        "- **No rellenar un campo que no sabes.** Va vacío o «no declarado», nunca",
        "  un valor plausible.",
        "",
    ]), encoding="utf-8")


def a_word(md: Path) -> bool:
    """Deja al lado del `.md` un `.docx` con el mismo contenido.

    Por qué. Este paquete lo abre alguien en un computador con Windows y Word,
    donde un `.md` se abre con el Bloc de notas y se ve el marcado crudo:
    almohadillas, asteriscos y tablas hechas de barras verticales. El texto que
    explica de dónde salió cada polígono no se lee, y lo que no se lee da lo
    mismo que no esté.

    El `.md` se conserva porque es la fuente —se versiona, se compara, se abre
    en cualquier sistema— y porque pesa nada. El `.docx` es la copia para leer.

    Si pandoc no está instalado se avisa y se sigue: el paquete queda completo
    con los `.md`, que es una degradación honesta y no una falla silenciosa
    (REGLAS §2).
    """
    import subprocess
    try:
        subprocess.run(
            ["pandoc", str(md), "-o", str(md.with_suffix(".docx")),
             "--from", "gfm", "--to", "docx"],
            check=True, capture_output=True, timeout=120)
        return True
    except FileNotFoundError:
        log("  pandoc no está instalado: el paquete queda sólo con los .md "
            "(instalar desde pandoc.org y volver a correr este script)")
        return False
    except Exception as exc:            # noqa: BLE001
        log(f"  no se pudo convertir {md.name} a Word: {exc}")
        return False


def _slug(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", t.lower())).strip("-")


def carpeta_por_documento(cfg: dict, fc: dict, feats: list[dict], destino: Path) -> dict:
    """Una carpeta por documento fuente: el PDF, su lámina, los polígonos y un
    resumen de qué es cada cosa.

    Por qué así y no todo junto en el GeoPackage: quien recibe esto tiene que
    poder abrir el documento del que salió cada polígono SIN volver a
    preguntarnos. Un polígono derivado sin su lámina al lado es una afirmación
    sin respaldo — y estos polígonos los dibujamos nosotros, así que tener el
    respaldo al lado es lo que permite discutirlos. El GeoPackage único sigue
    existiendo para trabajar cómodo en QGIS; esto es para entender y verificar.
    """
    import geopandas as gpd
    import pypdfium2 as pdfium
    from shapely.geometry import shape

    destino.mkdir(parents=True, exist_ok=True)
    proc = fc.get("procedencia") or {}
    pdf = DATA_RAW / cfg["pdf"]
    n_paginas = 0

    # 1. El documento original, tal como se descargó. `data/raw` es de sólo
    #    lectura (REGLAS §1.6): se copia, nunca se toca.
    if pdf.exists():
        shutil.copy2(pdf, destino / f"documento_original{pdf.suffix}")

        # 2. La página con la lámina, rasterizada, para verla sin abrir el PDF
        #    ni buscar la página entre cientos.
        try:
            doc = pdfium.PdfDocument(str(pdf))
            try:
                n_paginas = len(doc)
                img = doc[cfg["pagina"] - 1].render(scale=2).to_pil()
                if cfg.get("rotar"):
                    img = img.rotate(cfg["rotar"], expand=True)
                # Un pliego de plóter a escala 2 son 17.500 px de largo y 24 MB
                # de PNG: no cabe en un correo ni se abre en un computador
                # cualquiera. Esta imagen existe para MIRAR la lámina sin abrir
                # el PDF; el detalle fino está en el PDF, que va al lado. Se
                # acota el lado mayor y se guarda como JPEG, que para una hoja
                # completa pesa una fracción y se ve igual de bien.
                if max(img.size) > LADO_MAYOR_LAMINA_PX:
                    k = LADO_MAYOR_LAMINA_PX / max(img.size)
                    img = img.resize((max(1, int(img.width * k)),
                                      max(1, int(img.height * k))))
                img.convert("RGB").save(
                    destino / f"lamina_pagina-{cfg['pagina']}.jpg",
                    quality=88, optimize=True)
            finally:
                doc.close()
        except Exception as exc:            # noqa: BLE001
            log(f"    (no se pudo rasterizar la página: {exc})")

    # 3. Los polígonos, en los dos formatos que sirven: GeoJSON para leer y
    #    versionar, GeoPackage para arrastrar a QGIS.
    gdf = gpd.GeoDataFrame([f["properties"] for f in feats],
                           geometry=[shape(f["geometry"]) for f in feats],
                           crs="EPSG:4326")
    gdf.to_file(destino / "poligonos.geojson", driver="GeoJSON")
    gdf.to_file(destino / "poligonos.gpkg", layer=_slug(cfg["id"]), driver="GPKG")

    # 3-bis. Y en shapefile, porque es lo que circula en los servicios públicos
    # chilenos y lo que abre un ArcGIS antiguo. Va en su propia subcarpeta —son
    # cinco o seis archivos por capa— y con el aviso de lo que el formato le
    # hace al dato: nombres de campo cortados a diez caracteres y texto cortado
    # a 254. Ese aviso NO está escrito a mano: se genera comparando el
    # shapefile recién escrito contra el original, así que dice lo que pasó de
    # verdad en esta corrida y no lo que pasaba la última vez que alguien miró.
    shp_dir = destino / "shapefile"
    shp_dir.mkdir(exist_ok=True)
    gdf.to_file(shp_dir / "poligonos.shp", driver="ESRI Shapefile", encoding="utf-8")
    perdidas = []
    try:
        vuelta = gpd.read_file(shp_dir / "poligonos.shp")
        for col in gdf.columns:
            if col == "geometry":
                continue
            corto = col[:10]
            if corto not in vuelta.columns:
                perdidas.append(f"- `{col}`: **se perdió** al exportar.")
                continue
            a0, b0 = str(gdf[col].iloc[0]), str(vuelta[corto].iloc[0])
            if a0 != b0:
                perdidas.append(
                    f"- `{col}` → `{corto}`: **truncado** de {len(a0)} a "
                    f"{len(b0)} caracteres. El texto completo está en "
                    "`../poligonos.geojson` y en `../LEEME.md`.")
            elif col != corto:
                perdidas.append(f"- `{col}` → `{corto}`: sólo se acortó el "
                                "nombre; el contenido está entero.")
    except Exception as exc:            # noqa: BLE001
        perdidas.append(f"- (no se pudo verificar qué se perdió: {exc})")
    (shp_dir / "LEEME_shapefile.md").write_text("\n".join(
        ["# Los mismos polígonos, en shapefile", "",
         "Están acá porque es el formato que circula entre servicios públicos y",
         "el que abre un ArcGIS antiguo. **No son la copia de referencia**: el",
         "formato pierde cosas, y acá está exactamente qué perdió esta vez.", "",
         "## Qué le hizo el formato a este dato", ""]
        + (perdidas or ["- Nada: ningún campo se acortó ni se truncó."])
        + ["", "## Si vas a citar o revisar la procedencia", "",
           "Usa `../poligonos.geojson` o `../poligonos.gpkg`. El shapefile corta",
           "los nombres de campo a diez caracteres y el texto a 254, y la",
           "procedencia de este proyecto vive justamente en campos de texto",
           "largo. Para dibujar y medir, el shapefile sirve igual.", "",
           "## Los archivos", "",
           "`.shp` la geometría · `.dbf` la tabla · `.shx` el índice · `.prj` el",
           "sistema de coordenadas (EPSG:4326) · `.cpg` la codificación.",
           "**Se copian los cinco juntos o no funciona.**", ""]),
        encoding="utf-8")

    # 4. El resumen. Todo sale de la procedencia que el propio dato lleva
    #    adentro, así que si mañana cambia el método, este texto cambia solo.
    clases = proc.get("resumen_por_clase") or []
    ha = sum(c.get("hectareas", 0) for c in clases)
    incert = {f["properties"].get("incertidumbre_borde_m") for f in feats}
    efecto = next((f["properties"].get("efecto_legal") for f in feats
                   if f["properties"].get("efecto_legal")), "")
    L = [f"# {cfg['titulo']}", "",
         # Lo primero, y en grande: de qué página del documento salió esto. Un
         # estudio de riesgo son doscientas páginas de texto con dos mapas
         # adentro; sin este dato, encontrar la lámina de la que salieron los
         # polígonos es media hora de buscar.
         f"> ## 📄 La lámina está en la **página {cfg['pagina']}"
         + (f" de {n_paginas}" if n_paginas else "") + "** del documento.",
         ">",
         f"> Ábrela directo: `documento_original.pdf#page={cfg['pagina']}` "
         "(pega esa ruta en el navegador, o usa el buscador de páginas de tu "
         "lector de PDF). La misma página está copiada como imagen en esta "
         "carpeta.", "",
         f"**Comuna:** {cfg['comuna'].title()}  ",
         f"**Documento:** {pdf.name}"
         + (f" ({n_paginas} páginas)" if n_paginas else "") + "  ",
         f"**Año del contenido:** {proc.get('fecha_dato', 'no declarado')}  ",
         f"**Escala impresa:** {cfg.get('escala_impresa', 'no declarada')}", "",
         "## Qué hay en esta carpeta", "",
         "| Archivo | Qué es |",
         "|---|---|",
         "| `documento_original.pdf` | El documento tal como lo publica la fuente. No se modifica. |",
         f"| `lamina_pagina-{cfg['pagina']}.jpg` | La página con la lámina, para mirarla sin abrir el PDF. El detalle fino está en el PDF. |",
         "| `poligonos.geojson` | Los polígonos que derivamos de esa lámina, en EPSG:4326. |",
         "| `poligonos.gpkg` | Lo mismo, para arrastrar a QGIS. |",
         "| `shapefile/` | Los mismos polígonos en `.shp`, para ArcGIS o para intercambiar. Lee su LEEME: el formato corta nombres y textos. |", "",
         "## Qué contiene la geometría", "",
         "| Clase | Polígonos | Hectáreas |",
         "|---|---:|---:|"]
    # Coma decimal: esto lo lee una persona en Chile.
    coma = lambda x: str(x).replace(".", ",")
    for c in clases:
        L.append(f"| {c.get('clase')} | {c.get('poligonos')} | {coma(c.get('hectareas'))} |")
    L += ["", f"**Total: {len(feats)} polígonos · {ha:.0f} ha.**", "",
          "## De dónde salió, y qué es nuestro", "",
          f"**Fuente:** {proc.get('fuente', '')}", ""]
    if cfg.get("url"):
        L += [f"**Enlace:** {cfg['url']}", ""]
    L += [f"**Cómo se hizo:** {proc.get('metodo', '')}", "",
          f"**Precisión del borde:** ±{coma(incert.pop()) if len(incert) == 1 else '—'} m.", "",
          f"**Lo que la fuente advierte:** {proc.get('incertidumbre', '')}", ""]
    if efecto:
        L += ["## Efecto legal del contenido", "", efecto, "",
              "Ojo: el efecto legal es **del instrumento**, no de nuestro trazado. "
              "El plano rige; dónde exactamente cae su borde en el mapa es una "
              "reconstrucción nuestra, con la precisión de más arriba.", ""]
    else:
        L += ["## Peso legal", "",
              "Este documento es un **levantamiento de riesgo**, no una norma: "
              "describe dónde hay peligro, no impone condiciones a los permisos de "
              "edificación. Distinto es el plano de un plan regulador, que sí las "
              "impone.", ""]
    L += ["## Qué NO es", "",
          "- **No es el vectorial oficial.** El organismo publica esta cartografía "
          "sólo en papel; la geometría la construimos nosotros.",
          "- **No es una modelación hidráulica**, salvo que el método de arriba lo "
          "diga: no lleva caudales ni período de retorno.",
          "- **El borde no es un deslinde.** Con la precisión declarada, a esa "
          "distancia del borde adentro y afuera no se distinguen.",
          "", "## Si encuentras un error", "",
          f"Abre `lamina_pagina-{cfg['pagina']}.jpg` al lado de los polígonos en "
          "QGIS y compáralos. Si el trazado no calza con la "
          "lámina, avísanos con la coordenada: el trazado es lo nuestro, y es "
          "exactamente lo que se puede corregir.", ""]
    (destino / "LEEME.md").write_text("\n".join(L), encoding="utf-8")
    return {"carpeta": destino.name, "id": cfg["id"],
            "poligonos": len(feats), "hectareas": round(ha)}


def carpeta_pendientes(dest: Path, comunas: set[str],
                       ya_hechos: dict[str, str] | None = None,
                       reticulas: dict[str, list] | None = None) -> int:
    """Los documentos con lámina localizada que TODAVÍA no se vectorizaron.

    Es el trabajo que se le encarga al practicante, y va con el PDF al lado por
    la misma razón que el resto: para empezar no hace falta pedirnos nada.
    """
    cat = cargar(WEB_DATA / "catalogo-documentos.json")
    if not cat:
        return 0
    # Un documento que YA tiene su carpeta en 1_cartografia_ya_vectorizada no se
    # copia otra vez acá: verlo en «ya hecho» y en «por hacer» a la vez es la
    # clase de contradicción que hace desconfiar del paquete entero. Se lista
    # igual, marcado, para que se vea que no se olvidó.
    ya_hechos = ya_hechos or {}
    dest.mkdir(parents=True, exist_ok=True)
    L = ["# Láminas por georreferenciar", "",
         "Documentos donde ya localizamos una lámina con contenido de inundación y",
         "que **todavía no convertimos en geometría**. Cada uno trae su PDF si lo",
         "tenemos descargado; si no, va el enlace a la fuente.", "",
         "**Cómo se hace una: el paso a paso está en `COMO_TRABAJAR_EN_QGIS`**, en",
         "la carpeta de arriba. Todo se hace dentro de QGIS.", "",
         "La columna **«Lámina en la página»** es la que importa: estos son",
         "informes de decenas o cientos de páginas y el mapa está en dos o tres.",
         "",
         "| Comuna | Documento | Lámina en la página | De un total de | PDF en esta carpeta | Enlace |",
         "|---|---|---|---:|---|---|"]
    copiados = 0
    vistos: dict[str, str] = {}          # hash del archivo → dónde quedó la copia
    for c in cat["comunas"]:
        com = nz(c.get("comuna") or c.get("nombre"))
        if com not in comunas:
            continue
        for d in c.get("documentos", []):
            if not d.get("laminas"):
                continue
            pags = ", ".join(str(l["pagina"]) for l in d["laminas"][:8])
            if d["archivo"] in ya_hechos:
                L.append(f"| {com.title()} | {d['archivo'][:52]} | **{pags}** | — | "
                         f"✅ ya vectorizado → `1_cartografia_ya_vectorizada/"
                         f"{ya_hechos[d['archivo']]}/` | — |")
                continue
            hallado = next(iter(DATA_RAW.glob(f"documentos/**/{d['archivo']}")), None)
            local, total = "—", "—"
            if hallado and hallado.exists():
                # El registro EAE publica el mismo documento con nombres
                # distintos —«IA-Completo» e «IA-Incompleto», «Anteproyecto-Plano»
                # y «Anteproyecto_Planos» son byte por byte el mismo archivo—, y
                # copiarlos todos infla el paquete y hace que alguien
                # georreferencie dos veces la misma lámina. Se compara el
                # contenido, no el nombre.
                import hashlib
                h = hashlib.sha256(hallado.read_bytes()).hexdigest()
                if h in vistos:
                    local = f"↩ mismo archivo que `{vistos[h]}`"
                else:
                    sub = dest / _slug(com)
                    sub.mkdir(exist_ok=True)
                    shutil.copy2(hallado, sub / hallado.name)
                    local = f"`{_slug(com)}/{hallado.name}`"
                    vistos[h] = f"{_slug(com)}/{hallado.name}"
                    copiados += 1
                try:
                    import pypdfium2 as pdfium
                    doc = pdfium.PdfDocument(str(hallado))
                    total = str(len(doc))
                    doc.close()
                except Exception:       # noqa: BLE001 — un PDF ilegible no frena el índice
                    pass
            url = d.get("url") or ""
            L.append(f"| {com.title()} | {d['archivo'][:52]} | **{pags}** | {total} | "
                     f"{local} | {'[ver](' + url + ')' if url else '—'} |")
    # Y los documentos donde se DETECTÓ una cuadrícula, que es otra vía y no
    # coincide con la anterior: TAREAS los nombra uno por uno y hasta ahora
    # podía nombrar un PDF que no viajaba en el paquete —el PLADECO de Renaico,
    # por ejemplo—. Prometer evidencia que no se puede abrir es el defecto que
    # este proyecto persigue en todas partes; también acá.
    import hashlib
    extra = []
    for com, rs in sorted((reticulas or {}).items()):
        for r in rs:
            nombre = Path(r["pdf"]).name
            hallado = next(iter(DATA_RAW.glob(f"documentos/**/{nombre}")), None)
            if not hallado or not hallado.exists():
                extra.append((com, nombre, r["pagina"], "no lo tenemos descargado"))
                continue
            h = hashlib.sha256(hallado.read_bytes()).hexdigest()
            if h in vistos:
                extra.append((com, nombre, r["pagina"], f"ya está en `{vistos[h]}`"))
                continue
            sub = dest / _slug(com)
            sub.mkdir(exist_ok=True)
            shutil.copy2(hallado, sub / nombre)
            vistos[h] = f"{_slug(com)}/{nombre}"
            copiados += 1
            extra.append((com, nombre, r["pagina"], f"`{_slug(com)}/{nombre}`"))
    if extra:
        L += ["", "## Documentos con cuadrícula detectada", "",
              "Acá el programa vio una retícula regular en la página, que es la",
              "señal de que la lámina se puede georreferenciar por sus rótulos y",
              "no contra el mapa base. **No garantiza que sea de inundación: lee",
              "la página antes de invertir tiempo.**", "",
              "| Comuna | Documento | Página | PDF |", "|---|---|---:|---|"]
        for com, nombre, pag, donde in extra:
            L.append(f"| {com.title()} | {nombre[:52]} | {pag} | {donde} |")
        L.append("")

    (dest / "LEEME.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return copiados


def escribir_tareas(dest: Path, prov: str, filas: list[dict],
                    reticulas: dict[str, list]) -> None:
    L = [f"# Tareas de georreferenciación — provincia de {prov}", "",
         "Ordenadas por lo que más importa: **comunas con gente y con registro de",
         "inundación, pero sin ninguna cartografía consultable**. Una comuna con",
         "muchos documentos ya tiene por dónde empezar; una sin nada, no.", "",
         "> ⚠️ Que una comuna aparezca sin cartografía **no significa que no se",
         "> inunde**. Significa que nadie la levantó, o que no la encontramos en",
         "> fuentes públicas. Esa distinción es el corazón del proyecto: no la",
         "> pierdas al redactar nada.", "",
         "| Comuna | Hab. | Puntos | Crónicos | Área PRC | Docs | Láminas | Retículas | Ya derivados |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for f in filas:
        L.append(f"| **{f['comuna']}** | {f['hab']:,} | {f['puntos']} | "
                 f"{f['cronicos']} | {f['area']} | {f['docs']} | {f['laminas']} | "
                 f"{f['reticulas']} | {f['derivados']} |")
    L += ["", "**Cómo leer las columnas:**", "",
          "- **Área PRC** — polígonos en el vectorial público del MINVU. Un 0 con",
          "  documentos significa que la cartografía existe pero no está publicada",
          "  en formato consultable: ése es el caso que más rinde georreferenciar.",
          "- **Láminas** — figuras de cartografía de inundación ya localizadas",
          "  dentro de los PDF, con su número de página. No hay que buscarlas.",
          "- **Retículas** — de esas láminas, cuántas traen una grilla de",
          "  coordenadas regular detectada automáticamente. Son las que se pueden",
          "  georreferenciar sin puntos de control a mano.",
          "- **Ya derivados** — polígonos que el proyecto ya construyó desde una",
          "  lámina. No los rehagas; revísalos.", "",
          "---", "", "## Las tres tareas, en orden", "",
          "### 1. Georreferenciar y digitalizar las láminas que ya tienen retícula", "",
          "Son las más baratas: su cuadrícula UTM está impresa y rotulada, así que",
          "los puntos de control te los da la propia lámina y no hay que",
          "adivinarlos contra el mapa base. **El paso a paso completo está en",
          "`COMO_TRABAJAR_EN_QGIS`**, en esta misma carpeta.", "",
          "⚠️ **Antes de georreferenciar una lámina, lee el texto de su página.**",
          "Una lámina marcada por vocabulario de inundación no siempre es de",
          "inundación: ya descartamos una de Teodoro Schmidt que resultó ser",
          "riesgo multiamenaza «sin discriminar niveles de peligrosidad». Y una",
          "de la DGA que estaba perfectamente ubicada y no mapeaba ni un polígono",
          "de riesgo dentro de la zona que su título nombraba.", "",
          "Láminas con cuadrícula ya detectada en esta provincia:", ""]
    if reticulas:
        for c, rs in sorted(reticulas.items()):
            L.append(f"**{c.title()}**")
            for r in rs:
                L.append(f"- `{r['pdf']}` página {r['pagina']}, imagen {r['imagen']} "
                         f"— {r['px']} px, {r['lineas']} líneas, paso {r['paso_px']} px")
            L.append("")
    else:
        L.append("_Ninguna detectada por ahora en esta provincia._")
        L.append("")
    L += ["### 2. Las láminas SIN cuadrícula: puntos de control contra el mapa", "",
          "Cuando la figura viene recortada sin márgenes no hay rótulos que leer, y",
          "**no se puede inventar una coordenada**. Ahí toca georreferenciar contra",
          "el mapa base, usando cruces de calles, puentes y esquinas de manzana",
          "reconocibles en las dos imágenes. Mismo procedimiento de",
          "`COMO_TRABAJAR_EN_QGIS`, cambiando de dónde salen los puntos.", "",
          "Es más lento y menos preciso: espera un RMSE mayor y déjalo declarado.",
          "**Un polígono sin error declarado no se publica.**", "",
          "### 3. Las comunas sin ningún documento", "",
          "Para ésas no hay nada que georreferenciar todavía: falta conseguir el",
          "documento. Dos vías, en este orden:", "",
          "1. **Pedirlo por Ley 20.285** en portaltransparencia.cl a la",
          "   municipalidad: el Estudio Fundado de Riesgos de su Plan Regulador.",
          "   Responden obligatoriamente en 20 días hábiles.",
          "2. Revisar a mano el sitio municipal, que el cosechador automático puede",
          "   no haber alcanzado (algunos no exponen la API de WordPress).", "",
          "---", "", "## Qué NO hacer", "",
          "- **No dibujar polígonos a mano** «aproximando» dónde se inundaría. Si",
          "  no sale de un documento con autor y fecha, no entra.",
          "- **No rellenar un año que la fuente no declara.** Va «no declarado por",
          "  la fuente». El año del plan y el año de su estudio de riesgo son cosas",
          "  distintas: el PRC de Angol es de 2022 y su estudio, de 2013.",
          "- **No mezclar** el achurado de área de riesgo por inundación con el de",
          "  remoción en masa. En Angol son AR-2a y AR-1a/b/c, y se parecen.",
          "- **No confundir anteproyecto con instrumento vigente.** El anteproyecto",
          "  es una propuesta en tramitación y no rige sobre nadie.",
          ]
    (dest / "TAREAS.md").write_text("\n".join(L), encoding="utf-8")


def escribir_leeme(dest: Path, prov: str, gpkg: str,
                   fichas: list[dict] | None = None, pendientes: int = 0) -> None:
    fichas = fichas or []
    listado = "\n".join(
        f"  - `{f['carpeta']}/` — {f['poligonos']} polígonos, {f['hectareas']} ha"
        for f in fichas) or "  (ninguna todavía en esta provincia)"
    from datetime import date
    (dest / "LEEME.md").write_text(f"""# Paquete de trabajo — provincia de {prov}

> Armado el **{date.today().isoformat()}**. Los datos son los que el proyecto
> tenía ese día: si pasaron meses, pídenos una copia nueva antes de apoyarte en
> los conteos.

## Qué hay acá

- **`1_cartografia_ya_vectorizada/`** — una carpeta **por documento**. Adentro va
  el PDF original, la página con la lámina en imagen, los polígonos que sacamos de
  ella y un LEEME que explica qué es, de dónde salió y cuánto se equivoca.
  Ésta es la parte que hay que revisar primero:
{listado}
- **`2_laminas_por_georreferenciar/`** — {pendientes} documento(s) donde ya
  localizamos una lámina de inundación y que **todavía no convertimos en
  geometría**. Es el trabajo que sigue; su LEEME los lista con su página.
- **`{gpkg}`** — todas las capas del proyecto que caen en esta provincia, en un
  solo archivo. Arrástralo a QGIS y aparecen todas.
- **`COMO_TRABAJAR_EN_QGIS`** — el procedimiento completo, paso a paso, sin una
  sola línea de código: georreferenciar una lámina, digitalizar los polígonos,
  comprobar que quedaron donde deben y qué entregar de vuelta. **Empieza por
  acá si vas a producir cartografía nueva.**
- **`3_capas_en_shapefile/`** — todas las capas del GeoPackage exportadas a
  `.shp`, por comodidad. La copia de referencia sigue siendo el `.gpkg`.
- **`FUENTE_DE_CADA_POLIGONO`** — de dónde salió cada cosa que hay acá, con el
  enlace para abrir el documento. El resumen por documento en el texto; el
  detalle polígono por polígono en el `.csv`, que se abre en Excel.
- **`TAREAS`** — qué falta, por comuna, ordenado por lo que más importa.
- **`ESTADO_DE_LOS_POLIGONOS`** — la revisión que le hicimos a lo ya
  vectorizado antes de entregártelo: geometrías inválidas, polígonos cortados
  en el borde de su lámina, duplicados y los que están cerca del umbral de
  área. Léelo: te dice qué mirar con desconfianza.

## Por qué el documento va junto al polígono

Los polígonos de `1_cartografia_ya_vectorizada/` **los dibujamos nosotros** a
partir de una figura impresa: el contenido es del municipio, el trazado es
nuestro. Un polígono así, suelto, es una afirmación sin respaldo. Con la lámina
al lado se puede comparar, discutir y corregir — que es exactamente lo que
queremos que pase.

## En qué formato está todo, y con qué se abre

| Extensión | Qué es | Con qué se abre |
|---|---|---|
| `.gpkg` | **GeoPackage**: un solo archivo con varias capas adentro, tabla de atributos incluida. | QGIS (arrástralo al lienzo), ArcGIS, R, Python. |
| `.geojson` | Texto plano con la geometría y sus atributos. Se puede abrir con el Bloc de notas y leer. | QGIS, cualquier editor, cualquier lenguaje. |
| `.jpg` | La página del documento donde está la lámina. | Cualquier visor de imágenes. |
| `.pdf` | El documento original de la fuente. | Cualquier lector de PDF. |
| `.md` | Texto con formato (esto que estás leyendo). | Bloc de notas, o cualquier editor que muestre Markdown. |

**Todas las geometrías vienen en EPSG:4326** (WGS84, latitud y longitud en
grados). Es el sistema en que se publican y el que entiende cualquier
herramienta sin configurar nada. Si vas a medir distancias o áreas, reproyecta
antes a UTM 18S (EPSG:32718) o 19S (EPSG:32719) según la zona: en grados, un
área en «metros cuadrados» no significa nada.

**Sobre los shapefiles.** Cada carpeta de documento trae además una subcarpeta
`shapefile/` con los mismos polígonos en `.shp`, porque es lo que circula entre
servicios públicos y lo que abre un ArcGIS antiguo. Pero **no es la copia de
referencia**: el formato corta los nombres de campo a diez caracteres
—`estado_tramite` queda en `estado_tra`— y el texto a 254, que es justo donde
vive la procedencia de este proyecto. En cada subcarpeta hay un LEEME que dice,
medido en esa misma corrida, qué campo se acortó y cuál se truncó. Para dibujar y
medir, el shapefile sirve igual; para citar de dónde salió un polígono, usa el
GeoJSON o el GeoPackage.

Las capas regionales del `.gpkg` no vienen en shapefile: si las necesitas,
expórtalas desde QGIS con clic derecho en la capa → Exportar → Guardar como.

## Cómo saber si tu trabajo quedó bien

Ésta es la parte que más importa y la más fácil de saltarse. Una lámina puede
estar **perfectamente** georreferenciada y aun así no servir; y puede verse bien
en pantalla y estar corrida cientos de metros.

Compara siempre contra algo que **no haya participado** en tu trabajo:

1. **Los puntos críticos de SENAPRED** (`puntos_criticos_SENAPRED` en el
   GeoPackage). Son sitios donde el municipio reportó inundación, y nadie los
   usó para georreferenciar nada. Si vectorizaste un área de inundación y
   **ningún** punto crítico cae cerca, sospecha de tu georreferenciación antes
   de creerle al resultado.
2. **El modelo del GORE** (`amenaza_modelada_GORE_2016`). Es grueso —35 m— pero
   independiente: si tu mancha no solapa nada de la clase máxima, algo pasa.

Así se descartó una lámina de la DGA que parecía perfecta: la escala calzaba al
0,09 % en ambos ejes y los pueblos caían exactos, pero **0 de 77** puntos
críticos quedaban a menos de 300 m de sus polígonos de riesgo. El mapa estaba
bien ubicado; lo que dibujaba no era el área que su título prometía.

En cambio, cuando la lámina 2 del plano de Angol se vectorizó, cuatro de seis
puntos críticos cayeron **dentro** del área de riesgo. Ése es el resultado que
se busca.

## Glosario de las siglas que vas a encontrar

| Sigla | Qué significa |
|---|---|
| **PRC** | Plan Regulador Comunal: el instrumento que zonifica el suelo urbano de una comuna. Lo aprueba el municipio y lo visa la SEREMI. |
| **IPT** | Instrumento de Planificación Territorial. El PRC es uno. |
| **AR-1, AR-2a…** | Códigos de «Área de Riesgo» dentro de un PRC. El número y la letra los define cada plan: **AR-2a** en Angol son las áreas inundables o potencialmente inundables. Otro plan puede usar otro código para lo mismo. |
| **ZR-3, ZR-5…** | Lo mismo, en los planes que numeran sus zonas de riesgo con «ZR». |
| **OGUC** | Ordenanza General de Urbanismo y Construcciones. Su **artículo 2.1.17** es el que rige las áreas de riesgo: no prohíben construir, **condicionan** — exigen un estudio fundado de un especialista y obras de mitigación. |
| **EAE** | Evaluación Ambiental Estratégica: el trámite por el que pasan los planes reguladores. Su registro público es de donde salen muchos de estos documentos. |
| **RRD** | Reducción del Riesgo de Desastres. Los Planes Comunales de RRD (Ley 21.364) suelen traer cartografía que no está en ninguna otra parte. |
| **PACCC** | Plan de Acción Comunal de Cambio Climático (Ley 21.455). Otra vía por la que aparecen mapas de inundación. |
| **RMSE** | El error del ajuste al georreferenciar, en metros. Con menos de tres puntos de control no significa nada: no hay residuo que medir. |
| **SENAPRED** | Servicio Nacional de Prevención y Respuesta ante Desastres, ex ONEMI. |
| **Derivado** | Geometría que construimos **nosotros** desde una figura impresa. El contenido es de la fuente; el trazado es nuestro. |

## Lo primero que hay que abrir

La capa **`00_procedencia_de_cada_capa`** del GeoPackage. No tiene geometría: es
una tabla que dice, para cada capa, de dónde salió, con qué método, y **cuánto se
equivoca**. Ábrela antes de usar cualquier capa.

Esto no es burocracia. Las capas de este proyecto **no son comparables entre
sí**: una es un instrumento legal, otra es agua medida por satélite en una fecha,
otra es un modelo global de 1 km. Usarlas como si dijeran lo mismo es el error
que el proyecto entero existe para evitar.

## Las cuatro capas de evidencia, y por qué nunca se fusionan

| Capa | Qué es | Qué NO es |
|---|---|---|
| **A · Normativo** | Lo que el plan regulador declaró área de riesgo. Tiene efecto legal. | No es una modelación: puede venir de un estudio cualitativo de hace 13 años. |
| **B · Observado** | Agua que el radar midió, con fecha. | No es «hasta dónde puede llegar»: es hasta dónde llegó ese día, si el satélite pasó a tiempo. |
| **C · Modelado** | Lo que un estudio calculó bajo un escenario. | No es un pronóstico. |
| **D · Operacional** | Dónde el municipio reportó problemas. | No es una delimitación: son puntos, no áreas. |

**Nunca las promedies, ni las unas, ni saques una capa «síntesis».** Si se
fusionan, se pierde lo único que hace confiable a este proyecto: poder decir de
dónde salió cada borde.

## Antes de tocar nada, cuatro reglas

Son del proyecto y todas nacieron de un error real que ya se cometió. Éstas son
las cuatro que más te van a tocar:

- Las **cuatro capas de evidencia nunca se fusionan**.
- **Nunca se inventa un valor**: si la fuente no lo dice, va «no declarado».
- Los **índices agregados se fusionan**, jamás se sobrescriben. Este error mordió
  cuatro veces y su síntoma es mudo.
- **El título de una lámina nombra su marco, no lo que mapea.** Mira dónde caen
  las clases de la leyenda antes de invertir horas en georreferenciarla.

⚠️ Y ojo: **la numeración de los scripts NO es el orden de ejecución.** El orden
real está en `scripts/ORDEN.md`.

## Reglas que hay que respetar al entregar

1. **Todo lo que produzcas lleva su procedencia**: fuente, año, método y error.
   Si no puede declararlos, no se publica.
2. **Nunca inventes un valor.** Ni una coordenada, ni un año, ni una clase. Si la
   fuente no lo dice, va «no declarado por la fuente».
3. **Declara el RMSE** de cada georreferenciación, y con cuántos puntos de
   control se obtuvo.
4. **Los archivos originales no se tocan.** `data/raw/` es de sólo lectura;
   todo lo derivado va a `data/processed/`.
5. **Si algo te parece dudoso, márcalo en vez de resolverlo por tu cuenta.** Un
   polígono mal ubicado que nadie cuestiona es peor que uno pendiente.

## Qué devolver

- El `config/laminas.yaml` con las láminas nuevas declaradas.
- Los `.points` de QGIS de lo que georreferenciaste a mano.
- Un archivo de notas con lo que **no** pudiste hacer y por qué. Esa lista vale
  tanto como lo que sí salió: es la que evita que la próxima persona repita el
  intento.

## Dudas frecuentes

**¿Y si la lámina no dice su huso UTM, o lo dice mal?**
Pasa. La lámina de Catripulli declara «Huso 18 Sur» y es 19 Sur — con 18 caería
en el Pacífico. El script lo detecta porque verifica que el resultado aterrice
dentro de la región. No le creas al recuadro de información cartográfica: creele
a dónde aterriza.

**¿Cuántos puntos de control necesito?**
Tres como mínimo, y repartidos. Con dos el ajuste es exacto y el RMSE miente: no
hay residuo que medir. Mientras más repartidos por la hoja, mejor.

**¿Qué hago si un polígono queda a medias entre dos comunas?**
Déjalo con la comuna que declara el documento de origen, no con la que te parece.
El campo `comuna` es la llave con que se cruza todo lo demás.
""", encoding="utf-8")


if __name__ == "__main__":
    main()
