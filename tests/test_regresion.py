"""Tests de regresion via snapshot: la solucion default queda anclada.

Si alguien edita el catalogo, las restricciones o los topes sin actualizar
estos snapshots, el test falla. Eso obliga a revisar conscientemente cualquier
cambio en la solucion de referencia (no se acepta accidentalmente).
"""

from nutricosto.modelo import resolver_simplex


# Snapshot capturado el 2026-05-27 con el catalogo + restricciones vigentes.
# Z* = 74.59, mezcla con caliza para ratio Ca:P = 1.3.
SNAPSHOT_DEFAULT = {
    "Z_star": 74.5858,
    "asignaciones_kg": {
        "Maiz": 30.0000,
        "Polvillo": 7.3522,
        "Afrecho": 0.0000,
        "Soya": 1.5527,
        "Pasta": 9.3888,
        "Fosvimin": 0.6250,
        "Sal": 0.2500,
        "Caliza": 0.8313,
    },
    "nutrientes": {
        "pc_kg": 7.4500,
        "em_mcal": 142.5000,
        "fc_kg": 2.5000,
        "ca_kg": 0.4791,
        "p_kg": 0.3686,
    },
    "ratio_ca_p": 1.30,
}


TOL_KG = 1e-2
TOL_COSTO = 1e-2
TOL_NUTRI = 1e-2
TOL_RATIO = 1e-2


class TestSnapshotDefault:
    def test_costo_optimo_no_cambia(self, solucion_default):
        assert abs(solucion_default.costo_total - SNAPSHOT_DEFAULT["Z_star"]) < TOL_COSTO, (
            f"Z* cambio: actual={solucion_default.costo_total:.4f} "
            f"vs snapshot={SNAPSHOT_DEFAULT['Z_star']}"
        )

    def test_mezcla_default_no_cambia(self, solucion_default):
        for nombre, kg_esperado in SNAPSHOT_DEFAULT["asignaciones_kg"].items():
            actual = solucion_default.asignaciones[nombre]
            assert abs(actual - kg_esperado) < TOL_KG, (
                f"{nombre}: actual={actual:.4f} vs snapshot={kg_esperado}"
            )

    def test_nutrientes_default_no_cambian(self, solucion_default):
        s = solucion_default
        n = SNAPSHOT_DEFAULT["nutrientes"]
        assert abs(s.proteina_cruda_kg - n["pc_kg"]) < TOL_NUTRI
        assert abs(s.energia_metabolizable_mcal - n["em_mcal"]) < TOL_NUTRI
        assert abs(s.fibra_cruda_kg - n["fc_kg"]) < TOL_NUTRI
        assert abs(s.calcio_kg - n["ca_kg"]) < TOL_NUTRI
        assert abs(s.fosforo_kg - n["p_kg"]) < TOL_NUTRI

    def test_ratio_ca_p_default_no_cambia(self, solucion_default):
        ratio = solucion_default.calcio_kg / solucion_default.fosforo_kg
        assert abs(ratio - SNAPSHOT_DEFAULT["ratio_ca_p"]) < TOL_RATIO


class TestSnapshotEscenariosAlternativos:
    """Pequena bateria de escenarios anclados: cambios deliberados quedan registrados."""

    def test_lote_100kg_duplica_Z(self):
        from nutricosto.insumos import ParametrosLote
        from dataclasses import replace as r
        base = ParametrosLote()
        p_100 = r(
            base,
            masa_total_kg=100.0,
            fosvimin_kg=1.25,
            sal_kg=0.50,
            pc_minima_kg=14.0,
            em_minima_mcal=285.0,
            fc_minima_kg=5.0,
            ca_minima_kg=0.20,
            p_minima_kg=0.16,
        )
        s = resolver_simplex(p_100)
        assert s.estado == "Optimal"
        # Z* debe duplicarse (linealidad exacta).
        assert abs(s.costo_total - 2 * SNAPSHOT_DEFAULT["Z_star"]) < TOL_COSTO * 2

    def test_ratio_caP_relajado_05_baja_caliza_a_aprox_05(self):
        from nutricosto.insumos import ParametrosLote
        s = resolver_simplex(ParametrosLote(ca_p_ratio_min=0.5))
        # En este snapshot la caliza ronda 0.5 kg para ratio 0.5.
        assert 0.3 < s.asignaciones["Caliza"] < 0.7
