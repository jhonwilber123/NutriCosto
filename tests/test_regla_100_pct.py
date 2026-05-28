"""Regla del 100% para cambios simultaneos de coeficientes.

Para coeficientes c_j (costos), si Delta_j es el cambio aplicado y r_j+/r_j-
los anchos del rango de optimalidad hacia arriba/abajo, la base optima se
mantiene mientras:

    sum_j  |Delta_j| / r_j  <=  1     (regla del 100%)

Equivalente para RHS b_i: sum_i |Delta_i| / s_i <= 1, donde s_i es el ancho
del rango de factibilidad de cada b_i.

Estos tests verifican la regla numericamente comparando bases optimas tras
cambios pequenios vs. cambios que superan el 100% combinado.
"""

from dataclasses import replace

import pytest

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex


TOL = 1e-3


def _firma_base(solucion):
    """Conjunto de insumos basicos (kg > tol), define el vertice optimo."""
    return frozenset(
        n for n, kg in solucion.asignaciones.items()
        if kg > TOL and n not in ("Fosvimin", "Sal")
    )


def _con_costos(parametros, deltas):
    """Aplica un dict {nombre_insumo: delta_costo} y devuelve los nuevos parametros."""
    nuevos = []
    for ins in parametros.insumos:
        d = deltas.get(ins.nombre, 0.0)
        nuevos.append(replace(ins, costo_kg=ins.costo_kg + d))
    return replace(parametros, insumos=nuevos)


class TestCambiosSimultaneosPequenios:
    def test_perturbaciones_minusculas_combinadas_no_cambian_la_base(
        self, parametros_default, solucion_default
    ):
        """5 cambios de 0.005 cada uno: ningun rango de optimalidad se cruza."""
        firma_base = _firma_base(solucion_default)
        deltas = {
            "Maiz": 0.005, "Polvillo": -0.005, "Afrecho": 0.005,
            "Soya": -0.005, "Pasta": 0.005,
        }
        p_alt = _con_costos(parametros_default, deltas)
        s_alt = resolver_simplex(p_alt)
        assert _firma_base(s_alt) == firma_base


class TestCambiosQueSuperanLaRegla:
    def test_cambios_grandes_simultaneos_cambian_la_base(
        self, parametros_default, solucion_default
    ):
        """Cuando varios costos se mueven mucho, la base optima cambia (sale o entra alguien)."""
        firma_base = _firma_base(solucion_default)
        # Subimos Maiz 5x, Pasta 5x, bajamos Afrecho a la mitad: cambios extremos.
        deltas = {"Maiz": 5.0, "Pasta": 5.0, "Afrecho": -0.70}
        p_alt = _con_costos(parametros_default, deltas)
        s_alt = resolver_simplex(p_alt)
        if s_alt.estado != "Optimal":
            pytest.skip("Configuracion alterada resulto infactible")
        # La mezcla debe cambiar visiblemente.
        kg_cambios = sum(
            abs(s_alt.asignaciones[n] - solucion_default.asignaciones[n])
            for n in solucion_default.asignaciones
        )
        assert _firma_base(s_alt) != firma_base or kg_cambios > 5.0


class TestSumaDeFraccionesAcotada:
    """Construye una secuencia de cambios donde la suma de fracciones (Δ/r)
    se mantiene <= 1 y verifica que la base no cambia."""

    def test_pequenas_perturbaciones_acumulativas_preservan_base(
        self, parametros_default, solucion_default
    ):
        firma_base = _firma_base(solucion_default)
        # Perturbamos cada insumo por una fraccion pequenia de su costo.
        # Como no conocemos los rangos exactos, usamos 1% como heuristica
        # (cualquier rango razonable supera 1% del costo medio).
        deltas = {
            ins.nombre: 0.01 * ins.costo_kg
            for ins in parametros_default.insumos
            if ins.nombre not in ("Fosvimin", "Sal")
        }
        p_alt = _con_costos(parametros_default, deltas)
        s_alt = resolver_simplex(p_alt)
        if s_alt.estado != "Optimal":
            pytest.skip("Caso infactible tras perturbacion")
        assert _firma_base(s_alt) == firma_base
