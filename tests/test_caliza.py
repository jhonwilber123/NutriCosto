"""Tests del rol de la caliza: balancear Ca:P sin volver el LP infactible."""

from dataclasses import replace

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex


def test_caliza_activa_cuando_ratio_es_estricto(solucion_default):
    """Con ratio Ca:P 1.3 la LP usa caliza para balancear los cereales."""
    assert solucion_default.asignaciones["Caliza"] > 0.1


def test_caliza_dentro_de_su_tope(parametros_default, solucion_default):
    caliza = next(ins for ins in parametros_default.insumos if ins.nombre == "Caliza")
    techo_kg = caliza.limite_max_pct * parametros_default.masa_total_kg
    assert solucion_default.asignaciones["Caliza"] <= techo_kg + 1e-6


def test_sin_caliza_ratio_estricto_es_infactible():
    """Eliminar caliza con ratio Ca:P 1.3 hace el LP infactible (cereales muy P-ricos)."""
    p_base = ParametrosLote()
    insumos_sin_caliza = [ins for ins in p_base.insumos if ins.nombre != "Caliza"]
    p_sin = replace(p_base, insumos=insumos_sin_caliza)
    s = resolver_simplex(p_sin)
    assert s.estado != "Optimal"


def test_caliza_disminuye_cuando_ratio_se_relaja(solucion_default):
    """Al bajar el ratio Ca:P min, el LP necesita menos caliza para balancear."""
    p_relajada = ParametrosLote(ca_p_ratio_min=0.5)
    s_relajada = resolver_simplex(p_relajada)
    assert s_relajada.estado == "Optimal"
    assert s_relajada.asignaciones["Caliza"] < solucion_default.asignaciones["Caliza"]


def test_ratio_mas_estricto_demanda_mas_caliza():
    s_13 = resolver_simplex(ParametrosLote(ca_p_ratio_min=1.3))
    s_18 = resolver_simplex(ParametrosLote(ca_p_ratio_min=1.8))
    if s_18.estado == "Optimal":
        assert s_18.asignaciones["Caliza"] >= s_13.asignaciones["Caliza"] - 1e-6
