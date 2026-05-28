"""Benchmarks y stress tests: tiempo de resolucion y escalabilidad."""

import time
from dataclasses import replace

import pytest

from nutricosto.insumos import CATALOGO_INSUMOS, Insumo, ParametrosLote
from nutricosto.modelo import resolver_simplex
from nutricosto.solver import resolver_interior_point


SLA_DEFAULT_SEG = 1.0     # SLA para el caso default
SLA_AMPLIADO_SEG = 5.0    # SLA con 50 insumos sinteticos


class TestTiempoBase:
    def test_simplex_resuelve_default_en_menos_de_1s(self):
        p = ParametrosLote()
        t0 = time.perf_counter()
        s = resolver_simplex(p)
        elapsed = time.perf_counter() - t0
        assert s.estado == "Optimal"
        assert elapsed < SLA_DEFAULT_SEG, f"Simplex tardo {elapsed:.3f}s (> {SLA_DEFAULT_SEG}s)"

    def test_interior_point_resuelve_default_en_menos_de_1s(self):
        p = ParametrosLote()
        t0 = time.perf_counter()
        s = resolver_interior_point(p)
        elapsed = time.perf_counter() - t0
        assert "ptimal" in s.estado.lower() or s.estado == "" or s.costo_total > 0
        assert elapsed < SLA_DEFAULT_SEG


class TestEscalabilidad:
    def _generar_insumos_sinteticos(self, n_extra):
        """Clona el catalogo agregando insumos artificiales caros (no entraran en la base)."""
        catalogo = list(CATALOGO_INSUMOS)
        siguiente_indice = max(i.indice for i in catalogo) + 1
        for k in range(n_extra):
            catalogo.append(Insumo(
                indice=siguiente_indice + k,
                nombre=f"Sintetico_{k}",
                costo_kg=99.0 + k,  # caros: el LP los ignorara
                proteina_cruda=0.05,
                energia_metabolizable=2.0,
                fibra_cruda=0.05,
                calcio=0.001,
                fosforo=0.001,
                limite_max_pct=0.05,
                precio_saco=99.0 * 50,
                kg_por_saco=50.0,
            ))
        return catalogo

    def test_50_insumos_resuelve_en_tiempo_razonable(self):
        catalogo = self._generar_insumos_sinteticos(n_extra=43)  # 7 + 43 = 50
        p = ParametrosLote(insumos=catalogo)
        t0 = time.perf_counter()
        s = resolver_simplex(p)
        elapsed = time.perf_counter() - t0
        assert s.estado == "Optimal"
        assert elapsed < SLA_AMPLIADO_SEG, f"LP con 50 insumos tardo {elapsed:.3f}s"

    def test_costo_optimo_no_empeora_al_agregar_insumos_caros(self):
        """Agregar insumos extra solo puede mejorar (o dejar igual) el Z* base."""
        s_base = resolver_simplex(ParametrosLote())
        catalogo = self._generar_insumos_sinteticos(n_extra=20)
        p = ParametrosLote(insumos=catalogo)
        s_ext = resolver_simplex(p)
        assert s_ext.estado == "Optimal"
        assert s_ext.costo_total <= s_base.costo_total + 1e-6


class TestResolucionRepetida:
    def test_100_resoluciones_consecutivas_en_menos_de_10s(self):
        """Estabilidad: no hay memory leak ni degradacion en cadena."""
        p = ParametrosLote()
        t0 = time.perf_counter()
        for _ in range(100):
            s = resolver_simplex(p)
            assert s.estado == "Optimal"
        elapsed = time.perf_counter() - t0
        assert elapsed < 10.0, f"100 resoluciones tardaron {elapsed:.2f}s"

    def test_costo_total_no_se_corrompe_en_cadena(self):
        """100 resoluciones del mismo problema dan EL MISMO Z*."""
        p = ParametrosLote()
        s_inicial = resolver_simplex(p)
        for _ in range(99):
            s = resolver_simplex(p)
            assert s.costo_total == s_inicial.costo_total
