"""Viabilidad economica: ¿que presupuesto soporta el modelo y donde duelen mas las restricciones?"""

from dataclasses import replace

import pytest

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex
from nutricosto.sacos import plan_de_compra


class TestPresupuestoMinimo:
    def test_existe_presupuesto_minimo_finito(self, solucion_default):
        """Z* es finito y > 0; representa el piso de costo economico."""
        assert 0 < solucion_default.costo_total < 1e6

    def test_relajar_todos_los_minimos_baja_a_cota_combinatoria(self, solucion_default):
        """Sin minimos nutricionales, el LP llena con los insumos mas baratos respetando topes."""
        p = ParametrosLote(
            pc_minima_kg=0, em_minima_mcal=0, fc_minima_kg=0,
            ca_minima_kg=0, p_minima_kg=0, ca_p_ratio_min=0,
        )
        s = resolver_simplex(p)
        assert s.estado == "Optimal"
        # Tiene que ser estrictamente menor al default (que tiene minimos activos).
        assert s.costo_total < solucion_default.costo_total - 1.0
        # Cota inferior absoluta: si pudieramos llenar todo con el insumo mas barato (Caliza 0.40/kg)
        masa = p.masa_total_kg
        cota_absoluta = 0.625 * 8.0 + 0.25 * 0.56 + (masa - 0.875) * 0.40  # = 24.79
        # El optimo real esta entre la cota absoluta y el default.
        assert cota_absoluta <= s.costo_total <= solucion_default.costo_total


class TestCostoMarginalDeCadaRestriccion:
    """Cuanto vale relajar 1 unidad de cada restriccion activa? (precio sombra)."""

    def test_precio_sombra_de_em_es_positivo_cuando_es_activa(self, solucion_default):
        em_dual = solucion_default.duales.get("Energia_metabolizable_minima")
        em_holg = solucion_default.holguras.get("Energia_metabolizable_minima")
        if em_dual is None or em_holg is None:
            pytest.skip("EM no disponible")
        if abs(em_holg) < 1e-3:  # activa
            assert em_dual > 0, "Precio sombra de EM activo debe ser positivo en min Z"

    def test_precio_sombra_de_fc_es_positivo_cuando_es_activa(self, solucion_default):
        fc_dual = solucion_default.duales.get("Fibra_cruda_minima")
        fc_holg = solucion_default.holguras.get("Fibra_cruda_minima")
        if fc_dual is None or fc_holg is None:
            pytest.skip("FC no disponible")
        if abs(fc_holg) < 1e-3:
            assert fc_dual > 0


class TestPlanFisicoConCostoReal:
    """El plan discreto debe costar mas que el continuo, pero no significativamente mas."""

    def test_sobrecosto_por_discretizacion_es_acotado_a_gran_escala(self, parametros_default, solucion_default):
        """Para 1 lote el sobrecosto es alto (sacos enteros vs kg fraccionales);
        a partir de ~50 lotes el sobrecosto relativo debe estar bajo 30%."""
        plan = plan_de_compra(parametros_default, solucion_default, lotes=50)
        assert plan.sobre_costo / max(plan.costo_teorico_total, 1e-6) < 0.30

    def test_sobrecosto_relativo_baja_al_producir_mas_lotes(self, parametros_default, solucion_default):
        """Discretizar a sacos enteros duele menos cuanto mas lotes se producen."""
        plan_1 = plan_de_compra(parametros_default, solucion_default, lotes=1)
        plan_100 = plan_de_compra(parametros_default, solucion_default, lotes=100)
        rel_1 = plan_1.sobre_costo / max(plan_1.costo_teorico_total, 1e-6)
        rel_100 = plan_100.sobre_costo / max(plan_100.costo_teorico_total, 1e-6)
        assert rel_100 <= rel_1 + 1e-6


class TestPresupuestoComoCotaSuperior:
    def test_si_relajamos_un_minimo_el_costo_baja_o_se_mantiene(self, parametros_default, solucion_default):
        """Funcion de viabilidad de presupuesto: cada relajacion solo puede abaratar."""
        deltas = [
            ("pc_minima_kg", -1.0),
            ("em_minima_mcal", -10.0),
            ("fc_minima_kg", -0.5),
            ("ca_minima_kg", -0.05),
        ]
        for attr, delta in deltas:
            p_alt = replace(parametros_default, **{attr: getattr(parametros_default, attr) + delta})
            if getattr(p_alt, attr) < 0:
                continue
            s_alt = resolver_simplex(p_alt)
            if s_alt.estado != "Optimal":
                continue
            assert s_alt.costo_total <= solucion_default.costo_total + 1e-3, (
                f"Relajar {attr} encarecio Z*: {s_alt.costo_total} > {solucion_default.costo_total}"
            )
