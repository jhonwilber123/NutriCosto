"""Tests del modelo LP: factibilidad, restricciones activas y sensibilidad."""

import math
from dataclasses import replace

import pytest

from nutricosto.insumos import CATALOGO_INSUMOS, Insumo, ParametrosLote
from nutricosto.modelo import resolver_simplex


TOL = 1e-3


class TestFactibilidad:
    def test_defaults_son_factibles(self, solucion_default):
        assert solucion_default.estado == "Optimal"

    def test_costo_optimo_en_rango_esperado(self, solucion_default):
        # Con caliza y ratio Ca:P 1.3 el optimo cae cerca de S/.74-75.
        assert 70.0 < solucion_default.costo_total < 80.0


class TestRestriccionesIgualdad:
    def test_masa_total(self, parametros_default, solucion_default):
        assert abs(solucion_default.masa_total_kg - parametros_default.masa_total_kg) < TOL

    def test_fosvimin_fijo(self, parametros_default, solucion_default):
        assert abs(
            solucion_default.asignaciones["Fosvimin"] - parametros_default.fosvimin_kg
        ) < TOL

    def test_sal_fija(self, parametros_default, solucion_default):
        assert abs(
            solucion_default.asignaciones["Sal"] - parametros_default.sal_kg
        ) < TOL


class TestRestriccionesNutricionales:
    def test_proteina_cumple_minimo(self, parametros_default, solucion_default):
        assert solucion_default.proteina_cruda_kg + TOL >= parametros_default.pc_minima_kg

    def test_energia_cumple_minimo(self, parametros_default, solucion_default):
        assert (
            solucion_default.energia_metabolizable_mcal + TOL
            >= parametros_default.em_minima_mcal
        )

    def test_fibra_cumple_minimo(self, parametros_default, solucion_default):
        assert solucion_default.fibra_cruda_kg + TOL >= parametros_default.fc_minima_kg

    def test_calcio_cumple_minimo(self, parametros_default, solucion_default):
        assert solucion_default.calcio_kg + 1e-5 >= parametros_default.ca_minima_kg

    def test_fosforo_cumple_minimo(self, parametros_default, solucion_default):
        assert solucion_default.fosforo_kg + 1e-5 >= parametros_default.p_minima_kg

    def test_ratio_ca_p_cumple_minimo(self, parametros_default, solucion_default):
        ratio = solucion_default.calcio_kg / solucion_default.fosforo_kg
        assert ratio + TOL >= parametros_default.ca_p_ratio_min


class TestTopesPorInsumo:
    def test_ningun_insumo_excede_su_tope(self, parametros_default, solucion_default):
        for ins in parametros_default.insumos:
            if ins.limite_max_pct is None:
                continue
            kg = solucion_default.asignaciones[ins.nombre]
            techo = ins.limite_max_pct * parametros_default.masa_total_kg
            assert kg <= techo + TOL, f"{ins.nombre}: {kg} > {techo}"

    def test_no_hay_asignaciones_negativas(self, solucion_default):
        for nombre, kg in solucion_default.asignaciones.items():
            assert kg + 1e-9 >= 0, f"{nombre} negativa: {kg}"


class TestSensibilidad:
    def test_polvillo_carisimo_obliga_a_excluirlo(self, parametros_default):
        insumos = [
            replace(ins, costo_kg=20.0) if ins.nombre == "Polvillo" else ins
            for ins in parametros_default.insumos
        ]
        p = replace(parametros_default, insumos=insumos)
        s = resolver_simplex(p)
        assert s.estado == "Optimal"
        assert s.asignaciones["Polvillo"] < 1.0

    def test_pasta_muy_barata_la_hace_entrar(self, parametros_default):
        insumos = [
            replace(ins, costo_kg=0.10) if ins.nombre == "Pasta" else ins
            for ins in parametros_default.insumos
        ]
        p = replace(parametros_default, insumos=insumos)
        s = resolver_simplex(p)
        assert s.estado == "Optimal"
        assert s.asignaciones["Pasta"] > 5.0

    def test_costo_baja_al_relajar_em_minima(self, parametros_default, solucion_default):
        """EM esta binding por default; relajarla deberia abaratar Z*."""
        p_relajada = replace(parametros_default, em_minima_mcal=parametros_default.em_minima_mcal - 5.0)
        s = resolver_simplex(p_relajada)
        assert s.costo_total < solucion_default.costo_total

    def test_costo_sube_al_apretar_pc_minima(self, parametros_default, solucion_default):
        p_apretada = replace(parametros_default, pc_minima_kg=parametros_default.pc_minima_kg + 1.0)
        s = resolver_simplex(p_apretada)
        assert s.costo_total > solucion_default.costo_total

    def test_costo_sube_al_apretar_ratio_ca_p(self, parametros_default, solucion_default):
        """Subir el ratio Ca:P min obliga a usar mas caliza y/o reformular."""
        p_apretada = replace(parametros_default, ca_p_ratio_min=parametros_default.ca_p_ratio_min + 0.3)
        s = resolver_simplex(p_apretada)
        if s.estado == "Optimal":
            assert s.costo_total > solucion_default.costo_total


class TestPreciosSombra:
    def test_restriccion_activa_tiene_precio_sombra_no_nulo(self, solucion_default):
        """Una restriccion >= activa (binding) debe tener pi != 0."""
        # PC minima esta normalmente activa o cerca. Si no, EM o FC lo estaran.
        activas = [
            nombre for nombre, holgura in solucion_default.holguras.items()
            if abs(holgura or 0) < TOL
        ]
        assert activas, "Esperabamos al menos una restriccion activa"
        precios_activos = [
            solucion_default.duales[n] for n in activas
            if solucion_default.duales.get(n) is not None
        ]
        assert any(abs(pi) > 1e-6 for pi in precios_activos)
