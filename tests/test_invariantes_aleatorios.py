"""Tests de propiedades con parametros aleatorios.

Genera escenarios variados (masa, precios, requerimientos) y verifica
invariantes que deben sostenerse en cualquier instancia factible.
"""

import math
import random
from dataclasses import replace

import pytest

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex


TOL = 1e-3


def _aleatoriza_precios(parametros, rng, factor_min=0.5, factor_max=2.0):
    nuevos = []
    for ins in parametros.insumos:
        f = rng.uniform(factor_min, factor_max)
        nuevos.append(replace(ins, costo_kg=ins.costo_kg * f, precio_saco=ins.precio_saco * f))
    return replace(parametros, insumos=nuevos)


@pytest.mark.parametrize("seed", list(range(15)))
def test_precios_aleatorios_dan_solucion_valida(seed):
    """Para 15 semillas distintas, una factorizacion factible cumple todas las restricciones."""
    rng = random.Random(seed)
    p = _aleatoriza_precios(ParametrosLote(), rng)
    s = resolver_simplex(p)
    if s.estado != "Optimal":
        pytest.skip(f"Seed {seed} produjo escenario infactible")
    assert abs(s.masa_total_kg - p.masa_total_kg) < TOL
    assert s.proteina_cruda_kg + TOL >= p.pc_minima_kg
    assert s.energia_metabolizable_mcal + TOL >= p.em_minima_mcal
    assert s.fibra_cruda_kg + TOL >= p.fc_minima_kg
    assert s.calcio_kg + 1e-5 >= p.ca_minima_kg
    assert s.fosforo_kg + 1e-5 >= p.p_minima_kg
    if s.fosforo_kg > 1e-9:
        ratio = s.calcio_kg / s.fosforo_kg
        assert ratio + TOL >= p.ca_p_ratio_min


@pytest.mark.parametrize("masa", [10.0, 25.0, 50.0, 100.0, 250.0, 500.0])
def test_escalado_de_masa_preserva_proporciones(masa):
    """Al duplicar la masa (y los minimos proporcionalmente), la mezcla en % se conserva."""
    base = ParametrosLote()
    factor = masa / base.masa_total_kg
    p_escalada = replace(
        base,
        masa_total_kg=masa,
        fosvimin_kg=base.fosvimin_kg * factor,
        sal_kg=base.sal_kg * factor,
        pc_minima_kg=base.pc_minima_kg * factor,
        em_minima_mcal=base.em_minima_mcal * factor,
        fc_minima_kg=base.fc_minima_kg * factor,
        ca_minima_kg=base.ca_minima_kg * factor,
        p_minima_kg=base.p_minima_kg * factor,
    )
    s_base = resolver_simplex(base)
    s_esc = resolver_simplex(p_escalada)
    assert s_base.estado == "Optimal"
    assert s_esc.estado == "Optimal"
    for nombre in s_base.asignaciones:
        pct_base = 100.0 * s_base.asignaciones[nombre] / base.masa_total_kg
        pct_esc = 100.0 * s_esc.asignaciones[nombre] / masa
        assert abs(pct_base - pct_esc) < 0.1, (
            f"{nombre}: pct base {pct_base:.4f} vs escalada {pct_esc:.4f}"
        )
    # Z* tambien escala linealmente.
    assert abs(s_esc.costo_total - s_base.costo_total * factor) < TOL


@pytest.mark.parametrize("seed", list(range(10)))
def test_resultado_es_determinista(seed):
    """Resolver dos veces el mismo problema da resultados identicos."""
    rng = random.Random(seed)
    p = _aleatoriza_precios(ParametrosLote(), rng)
    s1 = resolver_simplex(p)
    s2 = resolver_simplex(p)
    if s1.estado != "Optimal" or s2.estado != "Optimal":
        pytest.skip("Caso infactible")
    assert s1.costo_total == s2.costo_total
    for nombre in s1.asignaciones:
        assert s1.asignaciones[nombre] == s2.asignaciones[nombre]


def test_apretar_cualquier_minimo_no_abarata():
    """Monotonia global: apretar mas las restricciones >= nunca puede reducir Z*."""
    rng = random.Random(0)
    base = ParametrosLote()
    s_base = resolver_simplex(base)
    for attr, delta in [
        ("pc_minima_kg", 0.5),
        ("em_minima_mcal", 1.0),
        ("fc_minima_kg", 0.1),
        ("ca_minima_kg", 0.02),
        ("p_minima_kg", 0.02),
    ]:
        p_apretada = replace(base, **{attr: getattr(base, attr) + delta})
        s = resolver_simplex(p_apretada)
        if s.estado != "Optimal":
            continue  # paso fuera de feasibility - OK, no es una violacion
        assert s.costo_total + TOL >= s_base.costo_total, (
            f"Apretar {attr} en +{delta} redujo Z*: {s.costo_total} < {s_base.costo_total}"
        )
