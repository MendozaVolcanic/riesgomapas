#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""¿Los enlaces que promete el paquete abren algo?

Las dos preguntas del instrumento
---------------------------------
1. ¿Qué mide? Cada URL que aparece en los documentos del paquete y en los campos
   `url` de sus capas, pedida de verdad por red, con su código de respuesta.
2. ¿Cómo sabría que se equivoca? Con `--control`, que agrega tres direcciones de
   veredicto conocido —un dominio que no existe, un 404 seguro y un 200 seguro—
   y exige que las clasifique bien. Un verificador de enlaces que llame «vivo» a
   todo es la manera más fácil de dar por buena una bibliografía muerta.

Por qué existe
--------------
La procedencia de este proyecto se apoya en poder abrir la fuente. Un enlace
muerto no rompe nada visible: el polígono se sigue dibujando, el documento sigue
diciendo de dónde salió, y sólo falla cuando alguien hace clic —normalmente,
cuando tiene que defender el dato—. Ya apareció uno así: el `ordenanza_url` de
la capa del MINVU, que apunta a observatoriourbano.cl y responde 404.

Esto informa, no borra. Un enlace caído sigue siendo la referencia correcta de
dónde salió el dato; lo que hay que hacer es decirlo, no esconderlo.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import glob
import io
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
UA = {"User-Agent": "riesgomapas/verificacion-de-enlaces"}
TIMEOUT = 45

CONTROLES = {
    "https://este-dominio-no-existe-riesgomapas.cl/x": "muerto",
    "https://eae.mma.gob.cl/storage/documents/no_existe_riesgomapas.pdf": "muerto",
    "https://www.minvu.gob.cl/": "vivo",
}


def codificar(u: str) -> str:
    """Percent-encoding del path: varias URLs traen ñ y tildes (Traiguén, Purén)."""
    p = urllib.parse.urlsplit(u)
    return urllib.parse.urlunsplit((
        p.scheme, p.netloc, urllib.parse.quote(p.path, safe="/%"),
        urllib.parse.quote(p.query, safe="=&%?"), p.fragment))


def probar(u: str) -> tuple[str, int | str]:
    """Devuelve el código HTTP, o el nombre del error de red.

    Se pide con GET y no con HEAD: varios servidores del Estado responden 405 o
    directamente mienten ante un HEAD. Se lee sólo el primer trozo del cuerpo,
    que basta para saber que el recurso está y no descarga el PDF entero.
    """
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(codificar(u), headers=UA), timeout=TIMEOUT)
        r.read(2048)
        return u, r.status
    except urllib.error.HTTPError as e:
        return u, e.code
    except Exception as e:                # noqa: BLE001 — DNS, TLS, timeout
        return u, type(e).__name__


def recolectar() -> dict[str, set[str]]:
    urls: dict[str, set[str]] = collections.defaultdict(set)
    base = RAIZ / "data" / "processed" / "paquete_malleco"
    for f in glob.glob(str(base / "**" / "*.md"), recursive=True):
        txt = io.open(f, encoding="utf-8").read()
        for u in re.findall(r'https?://[^\s)>\]"]+', txt):
            urls[u.rstrip(".,;")].add(str(Path(f).relative_to(base)))
    try:
        import warnings

        import fiona
        import geopandas as gpd
        warnings.filterwarnings("ignore")
        gpkg = base / "capas_malleco.gpkg"
        for capa in fiona.listlayers(gpkg):
            d = gpd.read_file(gpkg, layer=capa)
            for c in d.columns:
                if "url" not in c.lower():
                    continue
                for u in d[c].dropna().astype(str).unique():
                    if u.startswith("http"):
                        urls[u].add(f"capa {capa}.{c}")
    except Exception as exc:              # noqa: BLE001
        print(f"(no se pudieron leer las capas: {exc})")
    return urls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--hilos", type=int, default=6)
    a = ap.parse_args()

    urls = recolectar()
    if a.control:
        for u in CONTROLES:
            urls[u].add("CONTROL")

    print(f"probando {len(urls)} enlaces…\n")
    with cf.ThreadPoolExecutor(max_workers=a.hilos) as ex:
        res = dict(ex.map(probar, list(urls)))

    def vivo(c) -> bool:
        return isinstance(c, int) and 200 <= c < 400

    caidos = {u: c for u, c in res.items() if not vivo(c)}

    if a.control:
        ok = all(
            vivo(res[u]) == (esperado == "vivo")
            for u, esperado in CONTROLES.items())
        for u, esperado in CONTROLES.items():
            print(f"  CONTROL {esperado:<7} → {res[u]}   {u[:60]}")
        sys.stderr.write("CONTROL POSITIVO: %s\n" % (
            "OK — distingue vivo de muerto" if ok
            else "FALLA — no clasifica bien los casos conocidos"))
        return 0 if ok else 2

    for u in sorted(caidos):
        print(f"  ❌ {res[u]}  {u}")
        for d in sorted(urls[u]):
            print(f"        citado en {d}")
    print(f"\n{len(urls) - len(caidos)} vivos · {len(caidos)} caídos")
    return 0 if not caidos else 2


if __name__ == "__main__":
    sys.exit(main())
