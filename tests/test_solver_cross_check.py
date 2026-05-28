"""Verificacion cruzada: Simplex (CBC) y Interior Point (HiGHS) deben coincidir."""

from dataclasses import replace

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex
from nutricosto.solver import resolver_interior_point


TOL_COSTO = 1e-3
TOL_ASIGNACION = 1e-3


def test_costo_optimo_coincide(solucion_default, solucion_ip_default):
    assert abs(solucion_default.costo_total - solucion_ip_default.costo_total) < TOL_COSTO


def test_asignaciones_coinciden_insumo_por_insumo(solucion_default, solucion_ip_default):
    for nombre, kg_simplex in solucion_default.asignaciones.items():
        kg_ip = solucion_ip_default.asignaciones[nombre]
        assert abs(kg_simplex - kg_ip) < TOL_ASIGNACION, (
            f"{nombre}: simplex={kg_simplex} vs ip={kg_ip}"
        )


def test_cross_check_se_mantiene_con_parametros_apretados():
    """Si apretamos las restricciones, ambos solvers siguen coincidiendo."""
    p = ParametrosLote(pc_minima_kg=7.5, em_minima_mcal=144.0, fc_minima_kg=2.5)
    s_simplex = resolver_simplex(p)
    s_ip = resolver_interior_point(p)
    assert s_simplex.estado == "Optimal"
    assert abs(s_simplex.costo_total - s_ip.costo_total) < TOL_COSTO


def test_cross_check_con_precios_alterados():
    p = ParametrosLote()
    insumos_modificados = [
        replace(ins, costo_kg=ins.costo_kg * 1.5) if ins.nombre == "Maiz" else ins
        for ins in p.insumos
    ]
    p2 = replace(p, insumos=insumos_modificados)
    s_simplex = resolver_simplex(p2)
    s_ip = resolver_interior_point(p2)
    assert abs(s_simplex.costo_total - s_ip.costo_total) < TOL_COSTO
