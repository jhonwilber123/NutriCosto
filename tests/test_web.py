"""Tests del parseo del formulario web: precios, nutrientes y minimos globales."""

from nutricosto.web import _build_parametros


def _form_default():
    """Form vacio: _build_parametros debe caer a los defaults del catalogo."""
    return {}


class TestParseoMinimosGlobales:
    def test_form_vacio_usa_defaults(self):
        p = _build_parametros(_form_default())
        assert p.masa_total_kg == 50.0
        assert p.pc_minima_kg == 7.0
        assert p.em_minima_mcal == 142.5
        assert p.fc_minima_kg == 2.5
        assert p.ca_minima_kg == 0.10
        assert p.p_minima_kg == 0.08
        assert p.ca_p_ratio_min == 1.3

    def test_form_lee_overrides_globales(self):
        form = {
            "masa": "100",
            "pc_min": "14",
            "em_min": "285",
            "fc_min": "5.0",
            "ca_min": "0.20",
            "p_min": "0.15",
            "ca_p_ratio_min": "1.5",
        }
        p = _build_parametros(form)
        assert p.masa_total_kg == 100.0
        assert p.pc_minima_kg == 14.0
        assert p.em_minima_mcal == 285.0
        assert p.fc_minima_kg == 5.0
        assert p.ca_minima_kg == 0.20
        assert p.p_minima_kg == 0.15
        assert p.ca_p_ratio_min == 1.5

    def test_valores_no_numericos_se_ignoran(self):
        form = {"pc_min": "abc", "ca_min": ""}
        p = _build_parametros(form)
        assert p.pc_minima_kg == 7.0
        assert p.ca_minima_kg == 0.10


class TestParseoPorInsumo:
    def test_costo_kg_derivado_de_precio_saco(self):
        form = {"precio_saco_Maiz": "100", "kg_saco_Maiz": "50"}
        p = _build_parametros(form)
        maiz = next(i for i in p.insumos if i.nombre == "Maiz")
        assert abs(maiz.costo_kg - 2.0) < 1e-9
        assert maiz.precio_saco == 100.0
        assert maiz.kg_por_saco == 50.0

    def test_kg_saco_cero_cae_a_costo_default(self):
        form = {"precio_saco_Soya": "100", "kg_saco_Soya": "0"}
        p = _build_parametros(form)
        soya = next(i for i in p.insumos if i.nombre == "Soya")
        # Cuando kg_saco=0, costo_kg se mantiene en el default del catalogo.
        assert soya.costo_kg == 1.92

    def test_nutrientes_porcentaje_se_convierten_a_fraccion(self):
        form = {"pc_Soya": "50", "fc_Soya": "8.5", "ca_Soya": "0.40", "p_Soya": "0.70"}
        p = _build_parametros(form)
        soya = next(i for i in p.insumos if i.nombre == "Soya")
        assert abs(soya.proteina_cruda - 0.50) < 1e-9
        assert abs(soya.fibra_cruda - 0.085) < 1e-9
        assert abs(soya.calcio - 0.0040) < 1e-9
        assert abs(soya.fosforo - 0.0070) < 1e-9

    def test_em_se_lee_directo_en_mcal_por_kg(self):
        form = {"em_Maiz": "3.25"}
        p = _build_parametros(form)
        maiz = next(i for i in p.insumos if i.nombre == "Maiz")
        assert abs(maiz.energia_metabolizable - 3.25) < 1e-9

    def test_limite_max_pct_se_convierte_de_porcentaje(self):
        form = {"limite_Maiz": "55"}
        p = _build_parametros(form)
        maiz = next(i for i in p.insumos if i.nombre == "Maiz")
        assert abs(maiz.limite_max_pct - 0.55) < 1e-9

    def test_insumos_fijos_mantienen_limite_none(self):
        """Fosvimin y Sal no tienen tope porcentual (cantidad fijada por prescripcion)."""
        p = _build_parametros(_form_default())
        fosv = next(i for i in p.insumos if i.nombre == "Fosvimin")
        sal = next(i for i in p.insumos if i.nombre == "Sal")
        assert fosv.limite_max_pct is None
        assert sal.limite_max_pct is None

    def test_caliza_incluida_con_36_pct_ca(self):
        p = _build_parametros(_form_default())
        caliza = next(i for i in p.insumos if i.nombre == "Caliza")
        assert abs(caliza.calcio - 0.36) < 1e-9
        assert caliza.fosforo == 0.0
        assert caliza.limite_max_pct == 0.03
