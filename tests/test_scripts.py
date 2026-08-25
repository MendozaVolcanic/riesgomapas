

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
