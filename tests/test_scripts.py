

def test_todos_los_scripts_importan():
    """Cada script del pipeline tiene que poder importarse sin ejecutarse.

    Existe por una regresión real: al unificar `anillos_a_geojson` en comun.py se
    borró de dos scripts y no se agregó a su import. Los dos quedaron con un
    NameError que sólo aparecía **a mitad de una descarga larga**, después de
    varios minutos de red. Los tests unitarios no lo veían porque ninguno los
    importaba.
    """
    import importlib.util
    from pathlib import Path

    scripts = sorted((Path(__file__).resolve().parent.parent / "scripts").glob("[0-9]*.py"))
    assert scripts, "no se encontró ningún script numerado"
    rotos = []
    for ruta in scripts:
        spec = importlib.util.spec_from_file_location(f"s_{ruta.stem}", ruta)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except SystemExit:
            pass                     # un script que valida argumentos al importarse
        except Exception as exc:     # noqa: BLE001
            rotos.append(f"{ruta.name}: {type(exc).__name__}: {exc}")
    assert not rotos, "scripts que no importan:\n  " + "\n  ".join(rotos)


def test_el_orden_documentado_cubre_todos_los_scripts():
    """`scripts/ORDEN.md` tiene que nombrar cada script numerado que existe.

    Existe porque la numeración 01..20 NO es el orden de ejecución —del 11 en
    adelante el número es la fecha en que se escribió el script— y quien corra
    en orden numérico obtiene un catálogo vacío. El orden real está escrito a
    mano en scripts/ORDEN.md, y un documento escrito a mano se desactualiza en silencio
    apenas alguien agrega un script.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    orden = (raiz / "scripts" / "ORDEN.md").read_text(encoding="utf-8")
    numeros = sorted(p.name[:2] for p in (raiz / "scripts").glob("[0-9][0-9]_*.py"))
    faltan = [n for n in numeros if n not in orden]
    assert not faltan, (
        f"scripts que existen y no aparecen en scripts/ORDEN.md: {faltan}. "
        "Agrégalos en su lugar del orden topológico, no al final.")


def test_cada_script_declara_su_salida():
    """Todo script numerado dice en su docstring qué produce.

    Sin eso no se puede reconstruir el grafo de dependencias, que es justamente
    lo que hace que la numeración engañe.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    sin = []
    for p in sorted((raiz / "scripts").glob("[0-9][0-9]_*.py")):
        doc = p.read_text(encoding="utf-8")[:3000]
        if "Salida:" not in doc and "Salida " not in doc:
            sin.append(p.name)
    assert not sin, f"scripts sin «Salida:» en su docstring: {sin}"
