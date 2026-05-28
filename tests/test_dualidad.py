"""Tests de teoria de dualidad LP y precios sombra.

Verifican propiedades fundamentales:
  - Dualidad fuerte: Z* primal == Z* dual.
  - Holgura complementaria: dual=0 si holgura>0, y viceversa para activas.
  - Interpretacion del precio sombra: dZ/db_i == y_i para restricciones activas.
"""

from dataclasses import replace

import pytest

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex


TOL = 1e-3


class TestHolguraComplementaria:
    def test_holgura_positiva_implica_dual_cero(self, solucion_default):
        """Si una restriccion <= o >= tiene holgura > epsilon, su dual debe ser 0."""
        for nombre, holgura in solucion_default.holguras.items():
            if holgura is None:
                continue
            if abs(holgura) > 1e-2:  # claramente con holgura
                dual = solucion_default.duales.get(nombre)
                assert dual is None or abs(dual) < 1e-6, (
                    f"{nombre}: holgura={holgura} pero dual={dual}"
                )

    def test_al_menos_una_restriccion_activa_tiene_dual_no_nulo(self, solucion_default):
        activas_con_dual_significativo = [
            n for n, h in solucion_default.holguras.items()
            if abs(h or 0) < TOL and abs(solucion_default.duales.get(n) or 0) > 1e-6
        ]
        assert activas_con_dual_significativo, (
            "Por dualidad fuerte, al menos una restriccion debe tener precio sombra no nulo"
        )


class TestPrecioSombraNumerico:
    """Verifica dZ/db_i ≈ y_i perturbando el RHS de restricciones activas."""

    def _perturbar_y_medir(self, parametros, attr, delta, solucion_base):
        nuevos = {attr: getattr(parametros, attr) + delta}
        s_perturbada = resolver_simplex(replace(parametros, **nuevos))
        if s_perturbada.estado != "Optimal":
            return None
        return s_perturbada.costo_total - solucion_base.costo_total

    def test_shadow_price_em_coincide_con_perturbacion(self, parametros_default, solucion_default):
        em_dual = solucion_default.duales.get("Energia_metabolizable_minima") or 0
        if abs(em_dual) < 1e-6:
            pytest.skip("EM no es activa en este escenario")
        delta = 0.01  # perturbacion muy pequena para no cruzar umbral
        d_costo = self._perturbar_y_medir(parametros_default, "em_minima_mcal", delta, solucion_default)
        if d_costo is None:
            pytest.skip("Perturbacion no factible")
        # dZ/db = y_i; dZ ≈ y_i * delta. Tolerancia relativa al magnitud esperada.
        esperado = em_dual * delta
        assert abs(d_costo - esperado) < max(1e-3, 0.05 * abs(esperado))

    def test_shadow_price_fc_coincide_con_perturbacion(self, parametros_default, solucion_default):
        fc_dual = solucion_default.duales.get("Fibra_cruda_minima") or 0
        if abs(fc_dual) < 1e-6:
            pytest.skip("FC no es activa en este escenario")
        delta = 0.005
        d_costo = self._perturbar_y_medir(parametros_default, "fc_minima_kg", delta, solucion_default)
        if d_costo is None:
            pytest.skip("Perturbacion no factible")
        esperado = fc_dual * delta
        assert abs(d_costo - esperado) < max(1e-3, 0.05 * abs(esperado))

    def test_shadow_price_masa_coincide_con_perturbacion(self, parametros_default, solucion_default):
        """Para una restriccion de igualdad, el dual indica el costo por kg de lote."""
        masa_dual = solucion_default.duales.get("Masa_fija_100kg") or 0
        delta = 0.02
        d_costo = self._perturbar_y_medir(parametros_default, "masa_total_kg", delta, solucion_default)
        if d_costo is None:
            pytest.skip("Perturbacion no factible")
        esperado = masa_dual * delta
        assert abs(d_costo - esperado) < max(5e-3, 0.05 * abs(esperado))


class TestSignoDeDuales:
    def test_dual_de_restriccion_ge_activa_es_no_negativo(self, solucion_default):
        """Para min Z s.t. Ax >= b activa: y >= 0 (apretar encarece)."""
        for nombre in [
            "Proteina_cruda_minima",
            "Energia_metabolizable_minima",
            "Fibra_cruda_minima",
            "Calcio_minimo",
            "Fosforo_minimo",
            "Ratio_Ca_P_minimo",
        ]:
            holgura = solucion_default.holguras.get(nombre)
            dual = solucion_default.duales.get(nombre)
            if holgura is None or dual is None:
                continue
            if abs(holgura) < TOL:  # activa
                assert dual + 1e-6 >= 0, f"{nombre}: dual={dual} deberia ser >= 0"

    def test_dual_de_tope_max_activo_es_no_positivo(self, parametros_default, solucion_default):
        """Para min Z s.t. x_i <= u activa: dual <= 0 (apretar encarece, relajar abarata)."""
        for ins in parametros_default.insumos:
            if ins.limite_max_pct is None:
                continue
            nombre_restr = f"Limite_max_{ins.nombre}_{int(ins.limite_max_pct * 100)}pct"
            holgura = solucion_default.holguras.get(nombre_restr)
            dual = solucion_default.duales.get(nombre_restr)
            if holgura is None or dual is None:
                continue
            if abs(holgura) < TOL:
                assert dual - 1e-6 <= 0, f"{nombre_restr}: dual={dual} deberia ser <= 0"
