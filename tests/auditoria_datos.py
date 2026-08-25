"""Auditoría de los datos publicados — coherencia, integridad y procedencia.

POR QUÉ EXISTE
--------------
`auditoria_e2e.py` comprueba que el visor **se comporta** bien: que las capas
dibujen, que la ficha declare fuente y año, que los controles no estén tapados.
No comprueba que los **datos** sean coherentes: puede pasar en verde con cifras
equivocadas, capas duplicadas o archivos publicados que nadie lee.

Esta auditoría mira el dato, no la pantalla. Se corre antes de publicar y antes de
entregarle el material a alguien más.

    python tests/auditoria_datos.py

Sale con código 1 si hay hallazgos de gravedad alta.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "web" / "data"
PROC = RAIZ / "data" / "processed"

# La región, con holgura. Una coordenada fuera de acá es un error de proyección o
# de signo, no un dato válido.
BBOX = (-74.2, -40.2, -70.5, -37.0)

hallazgos: list[tuple[str, str, str]] = []
ok_n = 0


def ok(area: str, detalle: str = "") -> None:
    global ok_n
    ok_n += 1
    print(f"  [OK] {area}" + (f" — {detalle}" if detalle else ""))


def falla(area: str, detalle: str, gravedad: str = "alta") -> None:
    hallazgos.append((gravedad, area, detalle))
    print(f"  [{gravedad.upper()}] {area}: {detalle}")


def cargar(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        falla(f"lectura {p.name}", f"{type(exc).__name__}: {exc}")
        return None


def coords(geom: dict):
    """Todas las coordenadas de una geometría, sin importar su tipo."""
    def rec(c):
        if not c:
            return
        if isinstance(c[0], (int, float)):
            yield c[:2]
        else:
            for x in c:
                yield from rec(x)
    return list(rec(geom.get("coordinates", [])))


def firma(geom: dict) -> str:
    return hashlib.md5(
        json.dumps(geom.get("coordinates"), sort_keys=True).encode()
    ).hexdigest()


# ---------------------------------------------------------- 1. archivos publicados

def auditar_geojson() -> None:
    print("\n=== 1. Integridad de los GeoJSON publicados ===")
    for p in sorted(WEB.rglob("*.geojson")):
        rel = p.relative_to(WEB)
        d = cargar(p)
        if d is None:
            continue
        feats = d.get("features")
        if not isinstance(feats, list):
            falla(f"{rel}", "no tiene lista de features")
            continue
        if not feats:
            falla(f"{rel}", "no tiene ninguna feature", "media")
            continue

        # Procedencia: la regla 2 del proyecto es que todo dato publicado declare
        # su fuente y su año. Un archivo sin eso es inservible a los seis meses.
        proc = d.get("procedencia") or {}
        faltan = [k for k in ("fuente", "metodo", "incertidumbre") if not proc.get(k)]
        if faltan:
            falla(f"procedencia de {rel}", f"sin {', '.join(faltan)}")
        elif not (proc.get("fecha_dato") or proc.get("anio")):
            falla(f"procedencia de {rel}", "no declara fecha del dato", "media")
        else:
            ok(f"procedencia de {rel}")

        # Coordenadas dentro de la región
        fuera = 0
        sin_geom = 0
        for f in feats:
            g = f.get("geometry")
            if not g:
                sin_geom += 1
                continue
            for x, y in coords(g):
                if not (BBOX[0] <= x <= BBOX[2] and BBOX[1] <= y <= BBOX[3]):
                    fuera += 1
                    break
        if sin_geom:
            falla(f"{rel}", f"{sin_geom} features sin geometría")
        if fuera:
            falla(f"{rel}", f"{fuera} features con coordenadas fuera de la región")
        if not sin_geom and not fuera:
            ok(f"{rel}", f"{len(feats):,} features, coordenadas dentro de la región")

        # Features realmente duplicadas: misma geometría Y mismas propiedades.
        # Comparar sólo la geometría da falsos positivos legítimos — dos órbitas
        # satelitales distintas cubren el mismo bloque en fechas distintas, y
        # SENAPRED registra el mismo punto una vez por cada causa.
        c = Counter(
            (firma(f["geometry"]), json.dumps(f.get("properties"), sort_keys=True))
            for f in feats if f.get("geometry"))
        rep = sum(n - 1 for n in c.values() if n > 1)
        if rep:
            falla(f"{rel}", f"{rep} features idénticas en geometría y atributos", "media")


# ------------------------------------------------------- 2. coherencia de cifras

def auditar_cifras() -> None:
    print("\n=== 2. Coherencia entre capas y sus índices ===")

    pc = cargar(WEB / "puntos-criticos-inundacion.geojson")
    if pc:
        n = len(pc["features"])
        causas = Counter(f["properties"].get("causa") for f in pc["features"])
        fluv = {"Inundación por desborde de cauce", "Activación de quebradas"}
        intrusos = {c: v for c, v in causas.items() if c not in fluv}
        if intrusos:
            falla("alcance de la capa D",
                  f"causas que no son fluviales en la capa publicada: {intrusos}")
        else:
            ok("alcance de la capa D", f"{n} puntos, todos fluviales")

        # Los shards por comuna tienen que sumar el total de la capa completa
        completa = cargar(PROC / "senapred_puntos_criticos_araucania.geojson")
        shards = list((WEB / "puntos-criticos").glob("*.geojson"))
        suma = 0
        for s in shards:
            d = cargar(s)
            suma += len(d["features"]) if d else 0
        if completa and suma != len(completa["features"]):
            falla("shards de puntos críticos",
                  f"suman {suma} y la capa completa tiene {len(completa['features'])}")
        else:
            ok("shards de puntos críticos", f"{len(shards)} comunas suman {suma}")

        # SENAPRED registra un punto por CAUSA, no por lugar: la misma coordenada
        # aparece varias veces con causas distintas, y a veces con el nombre del
        # sector escrito de dos formas. No es un error del dato, pero significa
        # que el número de puntos NO es el número de lugares distintos, y hay que
        # decirlo cada vez que se publica la cifra.
        xy = Counter(tuple(round(v, 6) for v in f["geometry"]["coordinates"][:2])
                     for f in pc["features"])
        colocalizados = sum(n - 1 for n in xy.values() if n > 1)
        if colocalizados:
            falla("capa D — puntos co-localizados",
                  f"{len(pc['features'])} puntos ocupan {len(xy)} coordenadas "
                  f"distintas: {colocalizados} comparten sitio con otro punto. "
                  "La cifra publicada cuenta registros, no lugares", "baja")
        else:
            ok("capa D — un punto por lugar")

    ar = cargar(PROC / "areas_riesgo_prc_araucania.geojson")
    arw = cargar(WEB / "areas-riesgo-inundacion.geojson")
    if ar and arw:
        inund = [f for f in ar["features"] if f["properties"].get("es_inundacion")]
        if len(inund) != len(arw["features"]):
            falla("capa A", f"{len(inund)} marcadas es_inundacion pero se publican "
                            f"{len(arw['features'])}")
        else:
            ok("capa A", f"{len(ar['features'])} polígonos, {len(inund)} de inundación")
        comunas = {f["properties"].get("comuna") for f in ar["features"]}
        com_inund = {f["properties"].get("comuna") for f in inund}
        ok("capa A — comunas", f"{len(comunas)} con área de riesgo, "
                               f"{len(com_inund)} con inundación")
        sin_anio = sum(1 for f in ar["features"]
                       if not f["properties"].get("anio")
                       or "no declarado" in str(f["properties"].get("anio")))
        if sin_anio:
            falla("capa A — año", f"{sin_anio} de {len(ar['features'])} polígonos sin "
                                  "año; el Atlas de CIGIDEN lo tiene para 11 comunas",
                  "media")

    idx = cargar(WEB / "sar" / "indice.json")
    huella = cargar(WEB / "sar" / "huella-observada.geojson")
    if idx and huella:
        r = idx.get("resumen", {})
        if r.get("poligonos") != len(huella["features"]):
            falla("capa B", f"el índice dice {r.get('poligonos')} polígonos y el "
                            f"archivo tiene {len(huella['features'])}")
        else:
            ok("capa B", f"{r.get('poligonos')} polígonos, {r.get('hectareas'):,} ha")
        suma_km2 = round(sum(t["km2"] for t in idx.get("tracks", [])), 1)
        if abs(suma_km2 - r.get("km2", 0)) > 0.5:
            falla("capa B", f"los tracks suman {suma_km2} km² y el resumen dice "
                            f"{r.get('km2')}", "media")
        else:
            ok("capa B — suma por track", f"{suma_km2} km²")


# ---------------------------------------------------------------- 3. planos

def auditar_planos() -> None:
    print("\n=== 3. Planos georreferenciados ===")
    pngs = sorted((WEB / "planos").glob("*.png"))
    por_hash: dict[str, list[str]] = defaultdict(list)
    total = 0
    for p in pngs:
        b = p.read_bytes()
        total += len(b)
        por_hash[hashlib.md5(b).hexdigest()].append(p.name)
    dup = {k: v for k, v in por_hash.items() if len(v) > 1}
    if dup:
        desperdicio = sum(
            (WEB / "planos" / v[0]).stat().st_size * (len(v) - 1) for v in dup.values())
        detalle = "; ".join(f"{len(v)} copias de {v[0][:40]}" for v in dup.values())
        falla("planos duplicados",
              f"{len(pngs)} archivos son {len(por_hash)} planos únicos — "
              f"{desperdicio/1e6:.1f} MB de {total/1e6:.1f} MB repetidos ({detalle})",
              "media")
    else:
        ok("planos", f"{len(pngs)} archivos, ninguno duplicado")

    # RMSE declarado y aptitud
    malos = []
    for j in sorted((PROC / "georreferenciado").glob("*.json")):
        d = cargar(j)
        if not d:
            continue
        r = (d.get("ajuste") or {}).get("rmse_loo_m")
        if r is None:
            malos.append(f"{j.name}: sin RMSE")
        elif r > 5:
            malos.append(f"{j.name}: RMSE {r} m")
    if malos:
        falla("RMSE de planos", "; ".join(malos[:5]), "media")
    else:
        ok("RMSE de planos", "todos declarados y bajo 5 m")


# ------------------------------------------------- 4. archivos huérfanos y caché

def auditar_publicacion() -> None:
    print("\n=== 4. Qué se publica y qué se usa ===")
    app = (RAIZ / "web" / "app.js").read_text(encoding="utf-8")
    cat = (RAIZ / "web" / "catalogo.js").read_text(encoding="utf-8")
    sw = (RAIZ / "web" / "sw.js").read_text(encoding="utf-8")
    codigo = app + cat

    huerfanos, pesados = [], 0
    for p in sorted(WEB.rglob("*")):
        if p.is_dir() or p.suffix not in (".geojson", ".json"):
            continue
        rel = p.relative_to(WEB).as_posix()
        # Los shards por comuna se cargan por nombre calculado, no literal.
        if rel.startswith(("puntos-criticos/", "planos/", "jrc/")):
            continue
        if rel not in codigo and p.name not in codigo:
            huerfanos.append((rel, p.stat().st_size))
            pesados += p.stat().st_size
    if huerfanos:
        falla("datos publicados que nadie lee",
              f"{len(huerfanos)} archivos, {pesados/1e6:.1f} MB: "
              + ", ".join(f"{r} ({t/1e6:.1f} MB)" for r, t in huerfanos))
    else:
        ok("sin archivos publicados huérfanos")

    m = re.search(r"const VERSION = '([^']+)'", sw)
    ok("service worker", f"versión {m.group(1) if m else '?'}")


def auditar_cifras_en_documentos() -> None:
    """Las cifras citadas en la documentación contra el dato real.

    Es la brecha de proceso que este proyecto ya pisó: el mismo número vive en el
    dato, en el README, en tres documentos y en el mapa del workspace. Al depurar
    el alcance de la capa D —de 992 puntos a 440— hubo que perseguirlo a mano por
    cinco archivos, y basta olvidar uno para que el proyecto se contradiga a sí
    mismo en público. Escribirlo a mano garantiza que vuelva a divergir; esta
    comprobación al menos lo detecta.
    """
    print("\n=== 5. Cifras citadas en la documentación vs el dato ===")
    pc = cargar(WEB / "puntos-criticos-inundacion.geojson")
    ar = cargar(PROC / "areas_riesgo_prc_araucania.geojson")
    idx = cargar(WEB / "sar" / "indice.json")
    planos = cargar(WEB / "planos" / "indice.json")
    if not (pc and ar and idx and planos):
        return

    reales = {
        "puntos fluviales de SENAPRED": len(pc["features"]),
        "polígonos de área de riesgo": len(ar["features"]),
        "hectáreas de huella satelital": int(idx["resumen"]["hectareas"]),
        "planos publicados": len(planos["planos"]),
    }
    # Cómo se escribe cada cifra en la prosa, con separador de miles chileno.
    def formas(n: int) -> list[str]:
        return {str(n), f"{n:,}".replace(",", "."), f"{n:,}".replace(",", " ")}

    docs = [RAIZ / "README.md"] + sorted((RAIZ / "docs").glob("*.md"))
    # Cifras viejas que ya no deberían aparecer en ninguna parte.
    # Con límite de palabra: sin él, «992» calza dentro de «1992», que es el año
    # del plan regulador de Villarrica. Un detector que grita por eso se ignora.
    obsoletas = {
        r"\b992\b": "puntos «hídricos» antes de acotar el alcance a lo fluvial",
        r"×1,7": "enriquecimiento antes de separar drenaje de desborde",
        r"\b24 planos publicados": "sólo se publican 20; 24 es lo georreferenciado",
    }
    # Una cifra vieja citada a propósito —«esta cifra era X hasta que…»— es
    # historia, no divergencia. Se reconoce por el contexto de la misma línea.
    historico = re.compile(r"\b(era|fue|hasta que|antes de|antes del|en vez de)\b", re.I)
    sucios = []
    for d in docs:
        for i, linea in enumerate(d.read_text(encoding="utf-8").splitlines(), 1):
            if historico.search(linea):
                continue
            for patron, motivo in obsoletas.items():
                if re.search(patron, linea):
                    sucios.append(f"{d.name}:{i} cita «{patron}» ({motivo})")
    if sucios:
        falla("cifras obsoletas en la documentación", "; ".join(sucios), "media")
    else:
        ok("ninguna cifra obsoleta en la documentación")

    for etiqueta, n in reales.items():
        ok(f"cifra vigente — {etiqueta}", str(n))


def auditar_alcance_regional() -> None:
    """Nada publicado puede salirse de La Araucanía.

    El visor es un prototipo regional y así lo declara: el mapa no se deja
    desplazar fuera del recuadro y un punto de otra región recibe «fuera del
    alcance» en vez de una ficha vacía. Si una capa publicada tuviera geometría
    nacional, se dibujaría igual en el borde y contradiría esa promesa — con el
    agravante de que sería visible sólo desde afuera del área que se prueba.

    El bbox es el mismo de config/araucania.yaml y de `REGION` en web/app.js.
    Las tres copias tienen que coincidir; ésta es la que avisa si se separan.
    """
    O, S, E, N = -73.70, -39.65, -70.90, -37.35
    TOL = 0.01          # margen por redondeo de coordenadas
    revisados = 0
    for ruta in sorted(WEB.rglob("*.geojson")) + sorted(WEB.rglob("*.json")):
        datos = cargar(ruta)
        if not isinstance(datos, dict) or not datos.get("features"):
            continue
        revisados += 1
        xs, ys = [], []
        for f in datos["features"]:
            if not f.get("geometry"):
                continue
            for x, y in coords(f["geometry"]):
                xs.append(x)
                ys.append(y)
        if not xs:
            continue
        rel = ruta.relative_to(WEB)
        if (min(xs) < O - TOL or max(xs) > E + TOL
                or min(ys) < S - TOL or max(ys) > N + TOL):
            falla(f"alcance regional — {rel}",
                  f"geometría fuera de La Araucanía: lon {min(xs):.2f}..{max(xs):.2f}, "
                  f"lat {min(ys):.2f}..{max(ys):.2f}; el recuadro es "
                  f"{O}..{E} / {S}..{N}")
        else:
            ok(f"alcance regional — {rel}", f"{len(datos['features'])} features dentro")
    if not revisados:
        falla("alcance regional", "no se revisó ningún GeoJSON publicado")


def main() -> int:
    print("AUDITORÍA DE DATOS — riesgomapas")
    auditar_geojson()
    auditar_alcance_regional()
    auditar_cifras()
    auditar_planos()
    auditar_publicacion()
    auditar_cifras_en_documentos()

    print("\n" + "=" * 72)
    altas = [h for h in hallazgos if h[0] == "alta"]
    print(f"{ok_n} comprobaciones OK · {len(hallazgos)} hallazgos "
          f"({len(altas)} de gravedad alta)")
    for g, a, d in sorted(hallazgos):
        print(f"  [{g.upper()}] {a}: {d}")
    return 1 if altas else 0


if __name__ == "__main__":
    sys.exit(main())
