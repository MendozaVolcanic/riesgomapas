"""Verificación del georreferenciador con transformaciones conocidas.

La idea: fabricar puntos de control a partir de una transformación que conocemos
exactamente y comprobar que el ajuste la recupera. Si el RMSE no da ~0 con datos
perfectos, el código está mal y ningún resultado sobre una lámina real es creíble.

También se comprueba lo contrario: que un punto de control mal puesto SUBA el
RMSE leave-one-out. Un georreferenciador que no delata un GCP malo es peor que
no tener georreferenciador.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "geo", Path(__file__).resolve().parent.parent / "scripts" / "04_georreferenciar.py")
geo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(geo)


def gcps_sinteticos(n=12, semilla=7):
    """Píxeles al azar mapeados por una afín conocida (escala, rotación, traslación)."""
    rng = np.random.default_rng(semilla)
    px = rng.uniform(0, 4000, n)
    py = rng.uniform(0, 3000, n)
    escala, ang = 1.7, np.deg2rad(2.5)   # 1,7 m/px con leve rotación
    ox, oy = 700_000.0, 5_700_000.0
    mx = ox + escala * (np.cos(ang) * px - np.sin(ang) * py)
    my = oy - escala * (np.sin(ang) * px + np.cos(ang) * py)
    return px, py, mx, my


def test_afin_exacta_da_error_casi_cero():
    px, py, mx, my = gcps_sinteticos()
    m = geo.metricas(px, py, mx, my, orden=1)
    assert m["rmse_m"] < 1e-6, m
    assert m["rmse_loo_m"] < 1e-6, m
    assert m["aptitud"] == "predial"


def test_orden_2_tambien_ajusta_una_afin():
    """Un polinomio de orden 2 contiene a la afín: debe reproducirla sin inventar."""
    px, py, mx, my = gcps_sinteticos(n=20)
    m = geo.metricas(px, py, mx, my, orden=2)
    assert m["rmse_loo_m"] < 1e-5, m


def test_gcp_desplazado_es_delatado_por_leave_one_out():
    px, py, mx, my = gcps_sinteticos()
    mx = mx.copy()
    mx[3] += 60.0  # un punto mal picado, 60 m fuera de lugar
    m = geo.metricas(px, py, mx, my, orden=1)

    # El RMSE del ajuste reparte el error entre todos y lo disimula;
    # el leave-one-out lo expone. Ese es justamente el motivo de calcularlo.
    assert m["rmse_loo_m"] > m["rmse_m"], m
    assert m["peor_punto"] == 3, m
    assert m["aptitud"] != "predial", "un GCP 60 m fuera no puede quedar como predial"


def test_puntos_insuficientes_falla_explicito():
    px, py, mx, my = gcps_sinteticos(n=4)
    with pytest.raises(SystemExit):
        geo.metricas(px, py, mx, my, orden=2)  # orden 2 necesita 6


def test_lectura_points_de_qgis_corrige_el_signo_de_y(tmp_path: Path):
    p = tmp_path / "gcp.points"
    p.write_text(
        "#CRS: EPSG:32718\n"
        "mapX,mapY,sourceX,sourceY,enable,dX,dY,residual\n"
        "700000,5700000,100,-200,1,0,0,0\n"
        "701000,5700000,900,-200,1,0,0,0\n"
        "700000,5699000,100,-950,1,0,0,0\n",
        encoding="utf-8")
    px, py, mx, my, proyectado = geo.leer_puntos(p)
    assert proyectado is True
    assert list(py) == [200.0, 200.0, 950.0], "sourceY debe quedar positivo hacia abajo"
    assert list(mx) == [700000.0, 701000.0, 700000.0]


def test_ida_y_vuelta_del_polinomio_inverso():
    """El warp usa un polinomio inverso ajustado aparte; debe cerrar el círculo."""
    px, py, mx, my = gcps_sinteticos(n=15)
    cx, cy = geo.ajustar(px, py, mx, my, 1)
    ix, iy = geo.ajustar(mx, my, px, py, 1)
    ex, ey = geo.aplicar(px, py, cx, cy, 1)
    vx, vy = geo.aplicar(ex, ey, ix, iy, 1)
    assert np.allclose(vx, px, atol=1e-6) and np.allclose(vy, py, atol=1e-6)


def test_plantilla_se_escribe_y_es_json_valido(tmp_path: Path):
    import json
    destino = tmp_path / "plantilla.json"
    r = subprocess.run(
        [sys.executable,
         str(Path(__file__).resolve().parent.parent / "scripts" / "04_georreferenciar.py"),
         "--plantilla", str(destino)],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    d = json.loads(destino.read_text(encoding="utf-8"))
    assert "puntos" in d and "crs_puntos" in d
