"""Tests de integracion end-to-end: form web -> LP -> plan compra -> SQLite."""

from pathlib import Path

import pytest

from nutricosto.db import borrar_tanda, detalle_tanda, guardar_tanda, listar_tandas
from nutricosto.modelo import resolver_simplex
from nutricosto.sacos import plan_de_compra
from nutricosto.solver import resolver_interior_point
from nutricosto.web import _build_parametros


@pytest.fixture
def db_temporal(tmp_path):
    return tmp_path / "tanda_test.db"


def test_pipeline_completo_form_a_plan_de_compra():
    """Simula un POST del formulario y verifica que llega hasta el plan de compra."""
    form = {
        "masa": "50",
        "lotes": "3",
        "pc_min": "7.0",
        "em_min": "142.5",
        "fc_min": "2.5",
        "ca_min": "0.10",
        "p_min": "0.08",
        "ca_p_ratio_min": "1.3",
    }
    parametros = _build_parametros(form)
    solucion = resolver_simplex(parametros)
    assert solucion.estado == "Optimal"

    plan = plan_de_compra(parametros, solucion, lotes=int(form["lotes"]))
    assert plan.lotes == 3
    assert plan.masa_total_kg == 150.0
    assert plan.costo_real_total >= solucion.costo_total * plan.lotes - 1e-6


def test_persistencia_sqlite_roundtrip(db_temporal):
    """Guardar una tanda y recuperarla por id devuelve los datos esenciales."""
    parametros = _build_parametros({})
    solucion = resolver_simplex(parametros)

    tanda_id = guardar_tanda(
        parametros,
        solucion,
        codigo="TEST-001",
        notas="Tanda de prueba integration",
        db_path=db_temporal,
    )
    assert tanda_id > 0

    detalle = detalle_tanda(tanda_id, db_path=db_temporal)
    assert detalle["cabecera"]["codigo"] == "TEST-001"
    assert detalle["cabecera"]["estado_solver"] == "Optimal"
    assert abs(detalle["cabecera"]["costo_optimo"] - solucion.costo_total) < 1e-6

    nombres_persistidos = {row["insumo"] for row in detalle["composicion"]}
    nombres_modelo = set(solucion.asignaciones.keys())
    assert nombres_persistidos == nombres_modelo

    for row in detalle["composicion"]:
        assert abs(row["kg"] - solucion.asignaciones[row["insumo"]]) < 1e-6


def test_listar_tandas_devuelve_filas_descendentes(db_temporal):
    parametros = _build_parametros({})
    solucion = resolver_simplex(parametros)
    ids = [
        guardar_tanda(parametros, solucion, codigo=f"T-{i}", db_path=db_temporal)
        for i in range(3)
    ]
    listado = listar_tandas(db_path=db_temporal)
    assert [t["id"] for t in listado] == sorted(ids, reverse=True)


def test_borrado_es_cascada(db_temporal):
    parametros = _build_parametros({})
    solucion = resolver_simplex(parametros)
    tanda_id = guardar_tanda(parametros, solucion, codigo="TEMP", db_path=db_temporal)
    borrar_tanda(tanda_id, db_path=db_temporal)
    with pytest.raises(ValueError):
        detalle_tanda(tanda_id, db_path=db_temporal)


def test_simplex_y_interior_point_acuerdan_en_pipeline():
    """Tras pasar por el parseo del form, ambos solvers siguen coincidiendo."""
    form = {"masa": "50", "pc_min": "7.5", "fc_min": "2.5"}
    parametros = _build_parametros(form)
    s = resolver_simplex(parametros)
    v = resolver_interior_point(parametros)
    assert abs(s.costo_total - v.costo_total) < 1e-3
