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
          TAREAS.md                qué falta, por comuna, ordenado por prioridad
          LEEME.md                 cómo trabajar y qué devolver
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

    # Los documentos con lámina localizada que aún no se vectorizan: el trabajo
    # que se le encarga al practicante, con su PDF al lado.
    pendientes = carpeta_pendientes(
        dest / "2_laminas_por_georreferenciar", comunas,
        {(DATA_RAW / declaradas[f["id"]]["pdf"]).name: f["carpeta"]
         for f in fichas if f.get("id") in declaradas})
    log(f"  2_laminas_por_georreferenciar: {pendientes} PDF copiados + índice")

    escribir_tareas(dest, a.provincia.title(), filas, ret_por_comuna)
    escribir_leeme(dest, a.provincia.title(), gpkg.name, fichas, pendientes)
    log("")
    log(f"PAQUETE LISTO → {dest}")
    log(f"  {gpkg.name} · TAREAS.md · LEEME.md · "
        f"{len(fichas)} carpeta(s) por documento")


# Lado mayor de la imagen de la lámina que se copia a cada carpeta. Es una
# elección de entrega, no del dato: el PDF original va al lado y ahí está todo
# el detalle.
LADO_MAYOR_LAMINA_PX = 4000


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
         "| `poligonos.gpkg` | Lo mismo, para arrastrar a QGIS. |", "",
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
                       ya_hechos: dict[str, str] | None = None) -> int:
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
         "Cómo se hace una: `python scripts/18_vectorizar_laminas.py --inspeccionar",
         "<pdf> --pagina N` marca la retícula que detecta; se leen sus rótulos con el",
         "ojo, se anotan en `config/laminas.yaml` y se corre el script. El detalle",
         "está en el docstring de ese script.", "",
         "La columna **«Lámina en la página»** es la que importa: estos son",
         "informes de decenas o cientos de páginas y el mapa está en dos o tres.",
         "",
         "| Comuna | Documento | Lámina en la página | De un total de | PDF en esta carpeta | Enlace |",
         "|---|---|---|---:|---|---|"]
    copiados = 0
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
                sub = dest / _slug(com)
                sub.mkdir(exist_ok=True)
                shutil.copy2(hallado, sub / hallado.name)
                local = f"`{_slug(com)}/{hallado.name}`"
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
          "### 1. Georreferenciar las láminas que ya tienen retícula detectada", "",
          "Es lo más barato: la posición de la grilla ya está detectada, falta",
          "**leer sus rótulos** —que están dentro de la imagen y no hay OCR en el",
          "equipo— y anotarlos. Cada lámina toma unos minutos.", "",
          "```bash",
          "python scripts/18_vectorizar_laminas.py --censo",
          "python scripts/18_vectorizar_laminas.py --inspeccionar <pdf> --pagina N",
          "```", "",
          "El segundo comando deja la imagen con las líneas de grilla marcadas y",
          "sus posiciones en píxeles. Se leen los rótulos UTM con el ojo, se anotan",
          "en `config/laminas.yaml`, y el script hace el resto y **verifica solo**",
          "que la escala cuadre en ambos ejes y que el resultado aterrice en la",
          "región.", "",
          "⚠️ **Antes de declarar una lámina, lee el texto de su página.** Una",
          "lámina marcada por vocabulario de inundación no siempre es de",
          "inundación: ya descartamos una de Teodoro Schmidt que resultó ser",
          "riesgo multiamenaza «sin discriminar niveles de peligrosidad».", "",
          "Retículas detectadas en esta provincia:", ""]
    if reticulas:
        for c, rs in sorted(reticulas.items()):
            L.append(f"**{c.title()}**")
            for r in rs:
                L.append(f"- `{r['pdf']}` página {r['pagina']}, imagen {r['imagen']} "
                         f"— {r['px']} px, {r['lineas']} líneas, paso {r['paso_px']} px")
            L.append("")
    else:
        L.append("_Ninguna. Corre `18_vectorizar_laminas.py --censo` para actualizar._")
        L.append("")
    L += ["### 2. Las láminas SIN retícula: puntos de control a mano en QGIS", "",
          "Cuando la figura viene recortada sin márgenes no hay rótulos que leer, y",
          "no se puede inventar una coordenada. Ahí toca georreferenciar a mano",
          "contra el mapa base, usando cruces de calles y puentes reconocibles.", "",
          "El script `04_georreferenciar.py` ya lee el formato `.points` que exporta",
          "el georreferenciador de QGIS, así que el flujo es: georreferenciar en",
          "QGIS → guardar los puntos de control → pasarle el `.points` al script.", "",
          "**Declara siempre cuántos puntos usaste y el RMSE que dio.** Un plano",
          "sin error declarado no se publica.", "",
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
    (dest / "LEEME.md").write_text(f"""# Paquete de trabajo — provincia de {prov}

## Qué hay acá

- **`1_cartografia_ya_vectorizada/`** — una carpeta **por documento**. Adentro va
  el PDF original, la página con la lámina en imagen, los polígonos que sacamos de
  ella y un `LEEME.md` que explica qué es, de dónde salió y cuánto se equivoca.
  Ésta es la parte que hay que revisar primero:
{listado}
- **`2_laminas_por_georreferenciar/`** — {pendientes} documento(s) donde ya
  localizamos una lámina de inundación y que **todavía no convertimos en
  geometría**. Es el trabajo que sigue; su `LEEME.md` los lista con su página.
- **`{gpkg}`** — todas las capas del proyecto que caen en esta provincia, en un
  solo archivo. Arrástralo a QGIS y aparecen todas.
- **`TAREAS.md`** — qué falta, por comuna, ordenado por lo que más importa.

## Por qué el documento va junto al polígono

Los polígonos de `1_cartografia_ya_vectorizada/` **los dibujamos nosotros** a
partir de una figura impresa: el contenido es del municipio, el trazado es
nuestro. Un polígono así, suelto, es una afirmación sin respaldo. Con la lámina
al lado se puede comparar, discutir y corregir — que es exactamente lo que
queremos que pase.

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

## Antes de tocar nada, lee las reglas

`REGLAS.md`, en la raíz del repositorio. Son ocho capítulos y todas sus reglas
nacieron de un error real que ya se cometió. Las cuatro que más te van a tocar:

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
