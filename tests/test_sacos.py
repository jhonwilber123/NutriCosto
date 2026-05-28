"""Tests de la discretizacion: kg optimos -> sacos enteros del proveedor."""

import math

from nutricosto.sacos import plan_de_compra


class TestPlanDeCompra:
    def test_un_lote_basico(self, parametros_default, solucion_default):
        plan = plan_de_compra(parametros_default, solucion_default, lotes=1)
        assert plan.lotes == 1
        assert plan.masa_lote_kg == parametros_default.masa_total_kg
        assert plan.masa_total_kg == parametros_default.masa_total_kg

    def test_lotes_escalan_la_masa_y_kg_requeridos(self, parametros_default, solucion_default):
        plan_uno = plan_de_compra(parametros_default, solucion_default, lotes=1)
        plan_diez = plan_de_compra(parametros_default, solucion_default, lotes=10)
        assert plan_diez.masa_total_kg == plan_uno.masa_total_kg * 10
        for f_uno, f_diez in zip(plan_uno.filas, plan_diez.filas):
            assert abs(f_diez.kg_requeridos - f_uno.kg_requeridos * 10) < 1e-9

    def test_sacos_siempre_alcanzan_el_requerimiento(self, parametros_default, solucion_default):
        plan = plan_de_compra(parametros_default, solucion_default, lotes=5)
        for fila in plan.filas:
            if fila.kg_por_saco > 0 and fila.kg_requeridos > 1e-9:
                assert fila.kg_comprados + 1e-9 >= fila.kg_requeridos

    def test_sacos_son_enteros(self, parametros_default, solucion_default):
        plan = plan_de_compra(parametros_default, solucion_default, lotes=3)
        for fila in plan.filas:
            assert fila.sacos_a_comprar == int(fila.sacos_a_comprar)
            assert fila.sacos_a_comprar >= 0

    def test_sobrante_nunca_es_negativo(self, parametros_default, solucion_default):
        plan = plan_de_compra(parametros_default, solucion_default, lotes=7)
        for fila in plan.filas:
            assert fila.sobrante_kg + 1e-9 >= 0

    def test_costo_real_es_mayor_o_igual_al_teorico(self, parametros_default, solucion_default):
        """Comprar sacos enteros nunca puede salir mas barato que comprar a granel."""
        plan = plan_de_compra(parametros_default, solucion_default, lotes=4)
        assert plan.costo_real_total + 1e-6 >= plan.costo_teorico_total
        assert plan.sobre_costo + 1e-6 >= 0

    def test_lotes_minimo_uno(self, parametros_default, solucion_default):
        """Pedir 0 o negativo se trata como 1 lote."""
        plan_cero = plan_de_compra(parametros_default, solucion_default, lotes=0)
        plan_neg = plan_de_compra(parametros_default, solucion_default, lotes=-5)
        assert plan_cero.lotes == 1
        assert plan_neg.lotes == 1

    def test_sacos_techo_de_kg_requeridos(self, parametros_default, solucion_default):
        """sacos = ceil(kg_requeridos / kg_por_saco)."""
        plan = plan_de_compra(parametros_default, solucion_default, lotes=2)
        for fila in plan.filas:
            if fila.kg_por_saco > 0 and fila.kg_requeridos > 1e-9:
                esperados = math.ceil(fila.kg_requeridos / fila.kg_por_saco)
                assert fila.sacos_a_comprar == esperados
