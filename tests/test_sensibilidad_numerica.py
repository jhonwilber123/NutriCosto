"""Tests del rango de optimalidad de los coeficientes de costo c_j.

Mover c_j dentro de su rango de optimalidad NO cambia la base optima
(misma mezcla, misma asignacion en kg); solo cambia Z*. Fuera del rango,
otra base se vuelve optima y la mezcla salta a otro vertice.
"""

from dataclasses import replace

import pytest

from nutricosto.modelo import resolver_simplex


TOL_KG = 1e-3


def _mezcla_clave(solucion):
    """Tupla de (nombre, kg redondeado) para comparar bases optimas."""
    return tuple(
        (nombre, round(kg, 3))
        for nombre, kg in sorted(solucion.asignaciones.items())
    )


def _con_costo_alterado(parametros, nombre_insumo, nuevo_costo):
    nuevos_insumos = [
        replace(ins, costo_kg=nuevo_costo) if ins.nombre == nombre_insumo else ins
        for ins in parametros.insumos
    ]
    return replace(parametros, insumos=nuevos_insumos)


class TestRangoDeOptimalidadBasicas:
    def test_subir_costo_de_insumo_no_basico_no_cambia_la_mezcla(self, parametros_default, solucion_default):
        """Si un insumo esta en 0 (no basico), subir su precio nunca lo vuelve mas atractivo."""
        no_basicos = [
            n for n, kg in solucion_default.asignaciones.items()
            if kg < TOL_KG and n not in ("Fosvimin", "Sal")
        ]
        if not no_basicos:
            pytest.skip("No hay insumos no basicos en el default")
        for nombre in no_basicos:
            p_alt = _con_costo_alterado(
                parametros_default, nombre, parametros_default.insumos[0].costo_kg * 10
            )
            s_alt = resolver_simplex(p_alt)
            assert _mezcla_clave(s_alt) == _mezcla_clave(solucion_default), (
                f"Subir costo de {nombre} (no basico) no deberia cambiar la mezcla"
            )

    def test_perturbacion_pequena_no_cambia_la_base(self, parametros_default, solucion_default):
        """Cambiar c_j en 0.001 nunca debe cruzar un umbral de sensibilidad."""
        for ins in parametros_default.insumos:
            if ins.nombre in ("Fosvimin", "Sal"):
                continue
            p_alt = _con_costo_alterado(parametros_default, ins.nombre, ins.costo_kg + 0.001)
            s_alt = resolver_simplex(p_alt)
            assert _mezcla_clave(s_alt) == _mezcla_clave(solucion_default), (
                f"Perturbacion de 0.001 en {ins.nombre} cambio la base optima"
            )


class TestUmbralDeSensibilidad:
    def test_precios_extremos_cambian_significativamente_la_mezcla(self, parametros_default):
        """Barriendo el precio de Pasta de 0.3 a 100, su asignacion debe variar al menos 50%."""
        precios_test = [0.3, 1.0, 1.9, 5.0, 20.0, 100.0]
        kg_pasta = []
        for precio in precios_test:
            p_alt = _con_costo_alterado(parametros_default, "Pasta", precio)
            s_alt = resolver_simplex(p_alt)
            if s_alt.estado != "Optimal":
                continue
            kg_pasta.append(s_alt.asignaciones["Pasta"])
        assert max(kg_pasta) - min(kg_pasta) > 2.0, (
            f"La asignacion de Pasta apenas varia con precios: {kg_pasta}"
        )

    def test_pasta_satura_su_tope_cuando_es_casi_gratis(self, parametros_default):
        """Pasta a S/.0.10/kg debe llegar al tope del 20%."""
        p_alt = _con_costo_alterado(parametros_default, "Pasta", 0.10)
        s_alt = resolver_simplex(p_alt)
        assert s_alt.estado == "Optimal"
        pasta = next(i for i in parametros_default.insumos if i.nombre == "Pasta")
        techo = pasta.limite_max_pct * parametros_default.masa_total_kg
        assert s_alt.asignaciones["Pasta"] >= techo - TOL_KG

    def test_monotonia_costo_vs_precio_de_insumo_basico(self, parametros_default, solucion_default):
        """Si Maiz esta en la base, subir su costo nunca puede abaratar Z*."""
        if solucion_default.asignaciones["Maiz"] < TOL_KG:
            pytest.skip("Maiz no esta en la base optima")
        costos_prueba = [1.35, 1.50, 1.75, 2.00, 2.50]
        Z = []
        for c in costos_prueba:
            p_alt = _con_costo_alterado(parametros_default, "Maiz", c)
            s_alt = resolver_simplex(p_alt)
            if s_alt.estado != "Optimal":
                pytest.skip("Infactible en algun punto del barrido")
            Z.append(s_alt.costo_total)
        for i in range(1, len(Z)):
            assert Z[i] + TOL_KG >= Z[i - 1], (
                f"Z* no monotono: c_Maiz={costos_prueba[i]} dio Z*={Z[i]} < Z*={Z[i - 1]}"
            )
