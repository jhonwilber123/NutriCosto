"""Propiedades combinatorias de la base optima del simplex.

En LP, la solucion optima esta en un vertice del politopo factible. En forma
estandar, un vertice tiene a lo sumo m variables basicas (m = numero de
restricciones activas linealmente independientes). Estos tests verifican esa
estructura sobre el modelo NutriCosto.
"""

import pytest

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex


TOL_KG = 1e-4


def _variables_basicas(solucion):
    return {n for n, kg in solucion.asignaciones.items() if kg > TOL_KG}


def _restricciones_activas(solucion):
    return {
        n for n, h in solucion.holguras.items()
        if h is not None and abs(h) < 1e-3
    }


class TestEstructuraDeLaBase:
    def test_hay_al_menos_una_variable_basica(self, solucion_default):
        assert len(_variables_basicas(solucion_default)) >= 1

    def test_dosis_fijas_siempre_son_basicas(self, solucion_default):
        """Fosvimin y Sal estan fijados >0 por igualdad: siempre basicos."""
        basicas = _variables_basicas(solucion_default)
        assert "Fosvimin" in basicas
        assert "Sal" in basicas

    def test_numero_de_basicas_no_supera_numero_de_restricciones(self, parametros_default, solucion_default):
        """Cota tipica: |basicas| <= numero de restricciones (incluyendo bounds)."""
        n_restricciones = len(parametros_default.restricciones())
        assert len(_variables_basicas(solucion_default)) <= n_restricciones


class TestActivacionDeRestricciones:
    def test_alguna_restriccion_activa_define_el_optimo(self, solucion_default):
        """En el optimo siempre hay restricciones activas (sino, el problema es trivial)."""
        activas = _restricciones_activas(solucion_default)
        assert len(activas) >= 2  # masa + al menos otra

    def test_masa_total_siempre_es_activa(self, solucion_default):
        """La restriccion de igualdad masa = M siempre esta activa."""
        assert "Masa_fija_100kg" in _restricciones_activas(solucion_default)


class TestComplementariedadEstricta:
    """Para LPs no degenerados: |basicas| + |activas_lt| = n (variables totales)."""

    def test_complementariedad_aproximada(self, parametros_default, solucion_default):
        n_variables = len(parametros_default.insumos)
        # Variables no basicas (en cota inferior x_j = 0):
        no_basicas = n_variables - len(_variables_basicas(solucion_default))
        # Restricciones <= activas:
        activas_lt = [
            n for n in _restricciones_activas(solucion_default)
            if "Limite_max" in n
        ]
        # Cota suelta (no aplicable estrictamente con degeneracion):
        # |no_basicas| + |activas_eq| + |activas_lt| + |activas_gt| = n + m
        # Para nuestro modelo verificamos que el conteo total sea coherente.
        n_eq = 3   # masa, fosvimin, sal
        n_gt_activas = sum(
            1 for n in _restricciones_activas(solucion_default)
            if n in {
                "Proteina_cruda_minima",
                "Energia_metabolizable_minima",
                "Fibra_cruda_minima",
                "Calcio_minimo",
                "Fosforo_minimo",
                "Ratio_Ca_P_minimo",
            }
        )
        total_restricciones_que_aprietan = n_eq + n_gt_activas + len(activas_lt)
        # En un LP no degenerado: |basicas| == total_aprietan, no_basicas == n - total.
        # Aceptamos diferencia <= 1 por posible degeneracion.
        assert abs(len(_variables_basicas(solucion_default)) - total_restricciones_que_aprietan) <= 1


class TestVerticesCambianEntreEscenarios:
    """La base optima cambia segun los parametros: cubre vertices distintos."""

    def test_dos_escenarios_distintos_dan_bases_distintas(self):
        """Afrecho casi gratis lo mete en la base y saca a Polvillo."""
        from dataclasses import replace
        p1 = ParametrosLote()
        s1 = resolver_simplex(p1)
        nuevos = [
            replace(ins, costo_kg=0.10) if ins.nombre == "Afrecho" else ins
            for ins in p1.insumos
        ]
        p2 = replace(p1, insumos=nuevos)
        s2 = resolver_simplex(p2)
        if s2.estado != "Optimal":
            pytest.skip("Escenario alterno infactible")
        b1 = _variables_basicas(s1)
        b2 = _variables_basicas(s2)
        diff_simetrica = (b1 - b2) | (b2 - b1)
        assert diff_simetrica, f"Misma base en ambos escenarios: {b1}"


class TestDimensionalidadDelOptimo:
    def test_punto_optimo_es_unico_o_arista_definida(self):
        """Resolver dos veces da la misma solucion (LP determinista en CBC con tiebreak)."""
        s1 = resolver_simplex(ParametrosLote())
        s2 = resolver_simplex(ParametrosLote())
        assert s1.asignaciones == s2.asignaciones
