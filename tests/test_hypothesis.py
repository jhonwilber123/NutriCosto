"""Property-based testing real con la libreria hypothesis.

A diferencia de pytest.parametrize (casos enumerados), hypothesis genera
miles de casos aleatorios dentro de estrategias definidas y reduce
automaticamente cualquier contraejemplo encontrado al caso minimo.
"""

from dataclasses import replace

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex


TOL = 1e-3


# Estrategias reutilizables -------------------------------------------------

@st.composite
def parametros_factibles(draw):
    """Genera ParametrosLote con minimos lo bastante laxos como para que sea factible."""
    masa = draw(st.floats(min_value=10.0, max_value=500.0, allow_nan=False))
    pc = draw(st.floats(min_value=0.10 * masa, max_value=0.15 * masa))
    em = draw(st.floats(min_value=2.7 * masa, max_value=2.9 * masa))
    fc = draw(st.floats(min_value=0.04 * masa, max_value=0.055 * masa))
    fosvimin = draw(st.floats(min_value=0.005 * masa, max_value=0.02 * masa))
    sal = draw(st.floats(min_value=0.002 * masa, max_value=0.01 * masa))
    return ParametrosLote(
        masa_total_kg=masa,
        fosvimin_kg=fosvimin,
        sal_kg=sal,
        pc_minima_kg=pc,
        em_minima_mcal=em,
        fc_minima_kg=fc,
        ca_minima_kg=0.002 * masa,
        p_minima_kg=0.0015 * masa,
        ca_p_ratio_min=draw(st.floats(min_value=0.5, max_value=1.5)),
    )


# Reglas suaves para hypothesis (test crece y puede ser lento)
SLOW = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


# Tests ---------------------------------------------------------------------

@given(parametros_factibles())
@SLOW
def test_solucion_factible_satisface_masa(p):
    s = resolver_simplex(p)
    if s.estado != "Optimal":
        return
    assert abs(s.masa_total_kg - p.masa_total_kg) < max(TOL, 1e-4 * p.masa_total_kg)


@given(parametros_factibles())
@SLOW
def test_solucion_factible_no_tiene_kg_negativos(p):
    s = resolver_simplex(p)
    if s.estado != "Optimal":
        return
    for nombre, kg in s.asignaciones.items():
        assert kg + 1e-7 >= 0, f"{nombre} negativo: {kg}"


@given(parametros_factibles())
@SLOW
def test_solucion_factible_satisface_todos_los_minimos(p):
    s = resolver_simplex(p)
    if s.estado != "Optimal":
        return
    assert s.proteina_cruda_kg + TOL >= p.pc_minima_kg
    assert s.energia_metabolizable_mcal + TOL >= p.em_minima_mcal
    assert s.fibra_cruda_kg + TOL >= p.fc_minima_kg
    assert s.calcio_kg + 1e-5 >= p.ca_minima_kg
    assert s.fosforo_kg + 1e-5 >= p.p_minima_kg


@given(parametros_factibles())
@SLOW
def test_ningun_insumo_supera_su_tope(p):
    s = resolver_simplex(p)
    if s.estado != "Optimal":
        return
    for ins in p.insumos:
        if ins.limite_max_pct is None:
            continue
        kg = s.asignaciones[ins.nombre]
        techo = ins.limite_max_pct * p.masa_total_kg
        assert kg <= techo + TOL, f"{ins.nombre} supera tope: {kg} > {techo}"


@given(
    factor_costo=st.floats(min_value=0.5, max_value=3.0),
    nombre_insumo=st.sampled_from(["Maiz", "Polvillo", "Afrecho", "Soya", "Pasta", "Caliza"]),
)
@settings(max_examples=30, deadline=None)
def test_aumentar_costo_nunca_abarata_Z(factor_costo, nombre_insumo):
    """Multiplicar el costo de un insumo por k>=1 jamas puede reducir Z*."""
    if factor_costo < 1.0:
        return  # solo nos importan aumentos
    base = ParametrosLote()
    s_base = resolver_simplex(base)
    nuevos = [
        replace(ins, costo_kg=ins.costo_kg * factor_costo)
        if ins.nombre == nombre_insumo else ins
        for ins in base.insumos
    ]
    s = resolver_simplex(replace(base, insumos=nuevos))
    if s.estado != "Optimal":
        return
    assert s.costo_total + TOL >= s_base.costo_total


@given(
    delta_pc=st.floats(min_value=0.0, max_value=3.0),
    delta_em=st.floats(min_value=0.0, max_value=10.0),
)
@settings(max_examples=25, deadline=None)
def test_apretar_minimos_jamas_abarata_Z(delta_pc, delta_em):
    """Subir simultaneamente PC_min y EM_min nunca puede reducir Z*."""
    base = ParametrosLote()
    s_base = resolver_simplex(base)
    p = replace(
        base,
        pc_minima_kg=base.pc_minima_kg + delta_pc,
        em_minima_mcal=base.em_minima_mcal + delta_em,
    )
    s = resolver_simplex(p)
    if s.estado != "Optimal":
        return
    assert s.costo_total + TOL >= s_base.costo_total
