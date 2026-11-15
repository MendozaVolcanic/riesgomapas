"""Guardas del censo 2024: que nadie se cuente dos veces.

Existen por F-300 (auditoría del 15-nov-2026): la capa de aldeas del censo no es
territorio nuevo, es la suma de 505 manzanas «ALDEA» que ya venían en la capa de
manzanas. Sumar las tres capas contaba 17.887 personas dos veces, la región daba
1.021.433 en vez de 1.003.546, y 19 comunas mostraban habitantes inflados. El
control de integridad del script 16 comparaba cada capa por separado y no podía
verlo (F-309).
"""
import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# Población regional del Censo 2024 sin doble conteo: manzanas (urbanas y de
# aldea) más entidades rurales, leídas del GPKG del INE (Cartografia_censo2024_R09).
POBLACION_REGION = 1_003_546


def _script16():
    ruta = RAIZ / "scripts" / "16_censo_2024.py"
    spec = importlib.util.spec_from_file_location("s16", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mz(id_ent, n, tipo, area):
    return {"ID_ENTIDAD": id_ent, "n_per": n, "TIPO_MZ": tipo, "AREA_C": area,
            "COMUNA": "X"}


def test_las_aldeas_no_se_suman_a_sus_manzanas():
    """La aldea es la suma de sus manzanas: la salida no la incluye, y las
    manzanas de aldea salen rotuladas como tales, no como urbanas (F-380)."""
    s16 = _script16()
    manzanas = [_mz(1, 10, "URBANO", "URBANO"), _mz(2, 7, "ALDEA", "RURAL"),
                _mz(2, 3, "ALDEA", "RURAL")]
    entidades = [{"ID_ENTIDAD": 9, "n_per": 5, "AREA_C": "RURAL", "COMUNA": "X"}]
    aldeas = [{"ID_ENTIDAD": 2, "n_per": 10, "ENTIDAD": "A"}]
    unidades = s16.unidades_censales(manzanas, entidades, aldeas)
    assert sum(u["n_per"] for u in unidades) == 25          # no 35
    assert sorted(u["unidad_censal"] for u in unidades) == [
        "entidad_rural", "manzana_aldea", "manzana_aldea", "manzana_urbana"]


def test_una_aldea_que_no_es_la_suma_de_sus_manzanas_detiene_el_script():
    """Si el INE cambia la relación entre capas, omitir las aldeas podría perder
    gente: eso es dato incoherente, y el script se cae (REGLAS §2)."""
    s16 = _script16()
    manzanas = [_mz(2, 7, "ALDEA", "RURAL")]
    aldeas = [{"ID_ENTIDAD": 2, "n_per": 10, "ENTIDAD": "A"}]
    with pytest.raises(SystemExit):
        s16.unidades_censales(manzanas, [], aldeas)


def test_estado_comunas_no_cuenta_aldeas_dos_veces():
    d = json.loads((RAIZ / "web" / "data" / "estado-comunas.json").read_text("utf-8"))
    total = sum(c["personas"] or 0 for c in d["comunas"])
    assert total == POBLACION_REGION, (
        f"estado-comunas.json suma {total:,} personas; el censo sin aldeas "
        f"duplicadas da {POBLACION_REGION:,}. Corre scripts 16 y 19.")


def test_agua_de_rio_se_rotula_como_viviendas():
    """El INE define n_fuente_agua_rio como viviendas, no hogares (F-308)."""
    d = json.loads((RAIZ / "web" / "data" / "estado-comunas.json").read_text("utf-8"))
    c = d["comunas"][0]
    assert "hogares_agua_de_rio" not in c
    assert "viviendas_agua_de_rio" in c
