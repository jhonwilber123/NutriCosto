"""Tests de concurrencia y aislamiento.

PuLP construye un LpProblem nuevo en cada llamada a `resolver_simplex`, asi
que en teoria no hay estado compartido entre invocaciones. Estos tests lo
verifican empiricamente bajo ejecucion paralela.
"""

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import replace
import random

import pytest

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex
from nutricosto.sacos import plan_de_compra


def _resolver_un_caso(seed):
    rng = random.Random(seed)
    base = ParametrosLote()
    nuevos = []
    for ins in base.insumos:
        f = rng.uniform(0.5, 2.0)
        nuevos.append(replace(ins, costo_kg=ins.costo_kg * f, precio_saco=ins.precio_saco * f))
    p = replace(base, insumos=nuevos)
    s = resolver_simplex(p)
    return seed, s.estado, s.costo_total, tuple(
        round(s.asignaciones[ins.nombre], 4) for ins in p.insumos
    )


def _resolver_default(_):
    return resolver_simplex(ParametrosLote()).costo_total


class TestThreads:
    def test_resoluciones_en_paralelo_no_interfieren(self):
        """16 hilos resolviendo el mismo problema deben dar el mismo Z*."""
        with ThreadPoolExecutor(max_workers=8) as ex:
            costos = list(ex.map(_resolver_default, range(16)))
        assert len(set(costos)) == 1, f"Variabilidad inesperada: {set(costos)}"

    def test_resoluciones_diferentes_en_paralelo_son_correctas(self):
        """Cada hilo recibe un problema distinto y obtiene su solucion correcta."""
        seeds = list(range(20))
        with ThreadPoolExecutor(max_workers=8) as ex:
            resultados_paralelos = list(ex.map(_resolver_un_caso, seeds))
        resultados_seriales = [_resolver_un_caso(s) for s in seeds]
        assert resultados_paralelos == resultados_seriales


class TestProcesos:
    def test_resoluciones_en_procesos_separados_son_identicas(self):
        """Misma comprobacion pero con procesos (aislamiento absoluto)."""
        seeds = list(range(10))
        try:
            with ProcessPoolExecutor(max_workers=4) as ex:
                resultados = list(ex.map(_resolver_un_caso, seeds))
        except Exception:
            pytest.skip("ProcessPoolExecutor no disponible en este entorno")
        resultados_seriales = [_resolver_un_caso(s) for s in seeds]
        assert resultados == resultados_seriales


class TestSinEstadoGlobal:
    def test_resolver_dos_problemas_distintos_no_los_mezcla(self):
        """Cambiar parametros en la segunda llamada no contamina la primera."""
        p1 = ParametrosLote(pc_minima_kg=7.0)
        s1_antes = resolver_simplex(p1)
        # Llamada intermedia con parametros muy distintos
        p2 = ParametrosLote(pc_minima_kg=15.0, em_minima_mcal=300.0)
        _ = resolver_simplex(p2)
        # La solucion para p1 vuelve a calcularse y debe ser igual a la primera.
        s1_despues = resolver_simplex(p1)
        assert s1_antes.costo_total == s1_despues.costo_total
        for nombre in s1_antes.asignaciones:
            assert s1_antes.asignaciones[nombre] == s1_despues.asignaciones[nombre]

    def test_plan_de_compra_no_modifica_la_solucion(self, parametros_default, solucion_default):
        """plan_de_compra es puro: no debe mutar `solucion`."""
        Z_antes = solucion_default.costo_total
        mezcla_antes = dict(solucion_default.asignaciones)
        _ = plan_de_compra(parametros_default, solucion_default, lotes=12)
        assert solucion_default.costo_total == Z_antes
        for nombre, kg in mezcla_antes.items():
            assert solucion_default.asignaciones[nombre] == kg
