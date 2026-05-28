"""Tests de casos extremos y degenerados."""

from dataclasses import replace

import pytest

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex


TOL = 1e-3


class TestParametrosExtremos:
    def test_lote_muy_pequeno(self):
        """Lote de 5 kg: minimos proporcionalmente escalados."""
        p = ParametrosLote(
            masa_total_kg=5.0,
            fosvimin_kg=0.0625,
            sal_kg=0.025,
            pc_minima_kg=0.7,
            em_minima_mcal=14.25,
            fc_minima_kg=0.25,
            ca_minima_kg=0.01,
            p_minima_kg=0.008,
        )
        s = resolver_simplex(p)
        assert s.estado == "Optimal"
        assert abs(s.masa_total_kg - 5.0) < TOL

    def test_lote_grande_1000kg(self):
        """Escalamos a una tonelada y todo debe seguir factible."""
        factor = 20.0
        base = ParametrosLote()
        p = ParametrosLote(
            masa_total_kg=base.masa_total_kg * factor,
            fosvimin_kg=base.fosvimin_kg * factor,
            sal_kg=base.sal_kg * factor,
            pc_minima_kg=base.pc_minima_kg * factor,
            em_minima_mcal=base.em_minima_mcal * factor,
            fc_minima_kg=base.fc_minima_kg * factor,
            ca_minima_kg=base.ca_minima_kg * factor,
            p_minima_kg=base.p_minima_kg * factor,
        )
        s = resolver_simplex(p)
        assert s.estado == "Optimal"
        assert abs(s.masa_total_kg - 1000.0) < TOL


class TestRestriccionesTriviales:
    def test_minimos_en_cero_dan_solucion_economica(self, solucion_default):
        """Sin minimos nutricionales, la LP solo paga masa + dosis fijas."""
        p = ParametrosLote(
            pc_minima_kg=0.0,
            em_minima_mcal=0.0,
            fc_minima_kg=0.0,
            ca_minima_kg=0.0,
            p_minima_kg=0.0,
            ca_p_ratio_min=0.0,
        )
        s = resolver_simplex(p)
        assert s.estado == "Optimal"
        # Sin restricciones de calidad, el optimo es estrictamente mas barato.
        assert s.costo_total + TOL < solucion_default.costo_total


class TestInfactibilidadDetectable:
    def test_pc_imposible_es_infactible(self):
        """Pedir PC=100 kg en un lote de 50 kg es imposible."""
        p = ParametrosLote(pc_minima_kg=100.0)
        s = resolver_simplex(p)
        assert s.estado != "Optimal"

    def test_tope_demasiado_bajo_para_masa_es_infactible(self):
        """Si bajamos los topes tanto que no llenan 50 kg, hay infactibilidad."""
        p_base = ParametrosLote()
        nuevos_insumos = [
            replace(ins, limite_max_pct=0.05) if ins.limite_max_pct is not None else ins
            for ins in p_base.insumos
        ]
        p = replace(p_base, insumos=nuevos_insumos)
        s = resolver_simplex(p)
        assert s.estado != "Optimal"


class TestComportamientoDegenerado:
    def test_dos_insumos_con_mismo_costo_y_perfil_son_intercambiables(self):
        """Soya y Pasta con costos y perfiles identicos -> la LP elige cualquiera, ambas son optimas."""
        p = ParametrosLote()
        nuevos = []
        ref = next(i for i in p.insumos if i.nombre == "Soya")
        for ins in p.insumos:
            if ins.nombre == "Pasta":
                nuevos.append(replace(ins,
                    costo_kg=ref.costo_kg,
                    proteina_cruda=ref.proteina_cruda,
                    energia_metabolizable=ref.energia_metabolizable,
                    fibra_cruda=ref.fibra_cruda,
                    calcio=ref.calcio,
                    fosforo=ref.fosforo,
                ))
            else:
                nuevos.append(ins)
        p2 = replace(p, insumos=nuevos)
        s = resolver_simplex(p2)
        assert s.estado == "Optimal"
        # Cualquiera de las dos soluciones del cuello es valida; lo importante es que el LP no rompa.
        assert s.asignaciones["Soya"] >= 0
        assert s.asignaciones["Pasta"] >= 0


class TestCostosNumericamentePequenos:
    def test_costos_extremadamente_pequenos_no_rompen_el_solver(self):
        """Caliza casi gratis (0.001 /kg): el LP la usa al maximo sin overflow."""
        p_base = ParametrosLote()
        nuevos = [
            replace(ins, costo_kg=0.001) if ins.nombre == "Caliza" else ins
            for ins in p_base.insumos
        ]
        p = replace(p_base, insumos=nuevos)
        s = resolver_simplex(p)
        assert s.estado == "Optimal"
        caliza = next(i for i in p.insumos if i.nombre == "Caliza")
        techo = caliza.limite_max_pct * p.masa_total_kg
        assert s.asignaciones["Caliza"] <= techo + TOL
