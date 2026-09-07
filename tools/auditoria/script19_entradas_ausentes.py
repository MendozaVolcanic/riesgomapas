"""¿Qué escribe `scripts/19_estado_comunas.py` cuando le falta una entrada?
(auditoría 2026-09-06, frente 2, patrón 6: la misma forma de falla que arregló
el commit a6c08f1 en el script 10 —leer un índice previo, encontrar vacío,
escribir vacío— buscada en el script 19).

Corre el script 19 contra una COPIA de web/data en el scratchpad (nunca contra
el repositorio) en tres escenarios:
  E0  copia completa                → línea base
  E1  sin catalogo-documentos.json  → ¿le_falta de las 32 comunas?
  E2  sin indice-comunas.json       → ¿puntos_inundacion de las 32?
y compara el estado-comunas.json resultante con el publicado.

Preguntas del instrumento:
  (1) Si el script degradara bien (parar o declarar «no disponible») esto lo
      vería: E1/E2 terminarían con SystemExit o con valores None, no con ceros.
  (2) Si el instrumento estuviera muerto, E0 no reproduciría el archivo
      publicado y se imprimiría la diferencia.

Uso:  python tools/auditoria/script19_entradas_ausentes.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
SCRATCH = Path(os.environ.get("SCRATCH", tempfile.gettempdir())) / "auditoria_script19"


def cargar_modulo():
    spec = importlib.util.spec_from_file_location("s19", RAIZ / "scripts" / "19_estado_comunas.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def escenario(nombre: str, quitar: list[str]) -> dict | str:
    dest = SCRATCH / nombre
    if dest.exists():
        shutil.rmtree(dest)
    web = dest / "web" / "data"
    shutil.copytree(RAIZ / "web" / "data", web, ignore=shutil.ignore_patterns("*.png"))
    # data/processed/laminas se necesita para que E0 reproduzca el publicado
    proc = dest / "data" / "processed"
    shutil.copytree(RAIZ / "data" / "processed" / "laminas", proc / "laminas",
                    ignore=shutil.ignore_patterns("_*"))
    for q in quitar:
        (web / q).unlink()
    mod = cargar_modulo()
    mod.WEB_DATA = web
    mod.DATA_PROC = proc
    mod.log = lambda *a, **k: None
    try:
        mod.main()
    except SystemExit as e:
        return f"SystemExit: {e}"
    return json.loads((web / "estado-comunas.json").read_text(encoding="utf-8"))


def resumen(d) -> str:
    if isinstance(d, str):
        return d
    cs = d["comunas"]
    return (f"{len(cs)} comunas · puntos_inundacion total={sum(c['puntos_inundacion'] for c in cs)} · "
            f"documentos total={sum(c['documentos'] for c in cs)} · "
            f"con le_falta vacío={sum(1 for c in cs if not c['le_falta'])} · "
            f"frases le_falta={Counter(f for c in cs for f in c['le_falta'])}")


def main():
    pub = json.loads((RAIZ / "web/data/estado-comunas.json").read_text(encoding="utf-8"))
    print("PUBLICADO :", resumen(pub))
    e0 = escenario("E0_completo", [])
    print("E0 completo:", resumen(e0))
    if not isinstance(e0, str):
        iguales = [c for c in e0["comunas"]] == [c for c in pub["comunas"]]
        print("  E0 reproduce el publicado (lista de comunas idéntica):", iguales)
    e1 = escenario("E1_sin_catalogo", ["catalogo-documentos.json"])
    print("E1 sin catálogo:", resumen(e1))
    e2 = escenario("E2_sin_indice_comunas", ["indice-comunas.json"])
    print("E2 sin índice de comunas:", resumen(e2))
    if not isinstance(e1, str):
        print("  E1 escribió estado-comunas.json:", (SCRATCH / "E1_sin_catalogo/web/data/estado-comunas.json").exists())
        print("  E1 Angol:", {k: e1["comunas"][0][k] for k in ("comuna", "documentos", "laminas_localizadas", "le_falta")})


if __name__ == "__main__":
    main()
