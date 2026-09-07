"""¿Qué hacen `scripts/09_exportar_catalogo.py` y `scripts/20_paquete_practicante.py`
cuando les falta una entrada? (auditoría 2026-09-06, familia F-12, sitios 2 y 3
de 4 — el sitio 1 lo cubre `script19_entradas_ausentes.py`, el sitio 4
`script14_bbox_no_pisa_publicado.py`).

Corre cada script contra una COPIA en el scratchpad (nunca contra el
repositorio):

  09 sin laminas_candidatas_municipales.json (data/processed/eae/) — es un
     barrido OPCIONAL (una corrida aparte de 07 --prioridad municipales), no
     declarado en el Requiere: de scripts/ORDEN.md para el script 09. La
     conducta correcta es degradar: publicar el catálogo igual, sin los
     documentos municipales, y decirlo con log().

  20 sin estado-comunas.json (web/data/) — SÍ está en el Requiere: de 20 en
     ORDEN.md (01,06,14,15,18,19). La conducta correcta es SystemExit con
     instrucción, porque TAREAS.md saldría diciendo "nada falta en ninguna
     comuna" en vez de fallar.

Uso: python tools/auditoria/script09_20_entradas_ausentes.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
SCRATCH = Path(os.environ.get("SCRATCH", tempfile.gettempdir())) / "auditoria_script09_20"


def cargar_modulo(nombre_archivo: str, alias: str):
    spec = importlib.util.spec_from_file_location(alias, RAIZ / "scripts" / nombre_archivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===================================================================== sitio 2

def escenario_09(quitar_municipales: bool) -> tuple[str, list[str]]:
    nombre = "sin_municipales" if quitar_municipales else "completo"
    dest = SCRATCH / f"s09_{nombre}"
    if dest.exists():
        shutil.rmtree(dest)
    eae_dest = dest / "data" / "processed" / "eae"
    shutil.copytree(RAIZ / "data" / "processed" / "eae", eae_dest)
    georref_dest = dest / "data" / "processed" / "georreferenciado"
    georref_dest.mkdir(parents=True)
    for j in (RAIZ / "data" / "processed" / "georreferenciado").glob("*.json"):
        shutil.copy(j, georref_dest / j.name)  # sólo los sidecar: los .tif pesan 298 MB
    web_dest = dest / "web" / "data"
    web_dest.mkdir(parents=True)

    if quitar_municipales:
        (eae_dest / "laminas_candidatas_municipales.json").unlink()

    mod = cargar_modulo("09_exportar_catalogo.py", "s09")
    mod.DATA_PROC = dest / "data" / "processed"
    mod.WEB_DATA = web_dest
    logs: list[str] = []
    mod.log = logs.append
    try:
        mod.main()
    except SystemExit as e:
        return f"SystemExit: {e}", logs
    salida = web_dest / "catalogo-documentos.json"
    d = json.loads(salida.read_text(encoding="utf-8"))
    tot_doc = sum(len(c["documentos"]) for c in d["comunas"])
    tot_muni = sum(1 for c in d["comunas"] for doc in c["documentos"]
                   if doc.get("instrumento") == "Estudio municipal")
    return f"catalogo escrito: {tot_doc} documentos ({tot_muni} municipales)", logs


# ===================================================================== sitio 3

def escenario_20(quitar_estado: bool) -> str:
    nombre = "sin_estado" if quitar_estado else "completo"
    dest = SCRATCH / f"s20_{nombre}"
    if dest.exists():
        shutil.rmtree(dest)
    web_dest = dest / "web" / "data"
    shutil.copytree(RAIZ / "web" / "data", web_dest, ignore=shutil.ignore_patterns("*.png"))
    proc_dest = dest / "data" / "processed"
    (proc_dest / "laminas").mkdir(parents=True)
    origen_censo = RAIZ / "data" / "processed" / "laminas" / "_censo_reticulas.json"
    if origen_censo.exists():
        shutil.copy(origen_censo, proc_dest / "laminas" / "_censo_reticulas.json")

    if quitar_estado:
        (web_dest / "estado-comunas.json").unlink()

    mod = cargar_modulo("20_paquete_practicante.py", "s20")
    mod.WEB_DATA = web_dest
    mod.DATA_PROC = proc_dest
    mod.DATA_RAW = dest / "data" / "raw"
    logs: list[str] = []
    mod.log = logs.append
    sys.argv = ["20_paquete_practicante.py", "--provincia", "Malleco",
               "--salida", str(dest / "salida")]
    try:
        mod.main()
    except SystemExit as e:
        return f"SystemExit: {e}"
    return "TERMINÓ SIN ERROR (mal — debía pararse)"


def main() -> None:
    print("=== sitio 2: 09_exportar_catalogo.py — municipales ausente (ausente LEGÍTIMO) ===")
    r0, l0 = escenario_09(quitar_municipales=False)
    print("completo    :", r0)
    r1, l1 = escenario_09(quitar_municipales=True)
    print("sin muni    :", r1)
    print("  logs sin muni:", [l for l in l1 if "municipal" in l.lower()])

    print()
    print("=== sitio 3: 20_paquete_practicante.py — estado-comunas.json ausente (INCOHERENTE) ===")
    print("sin estado  :", escenario_20(quitar_estado=True))


if __name__ == "__main__":
    main()
