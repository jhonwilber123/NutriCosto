"""Analisis de programacion lineal parametrica.

Cuando se varia el RHS b_i de una restriccion activa de forma continua,
Z*(b) es una funcion lineal a trozos y convexa (para problemas de minimizacion
con RHS de restricciones >=). Estos tests verifican esa propiedad estructural,
ademas de la continuidad de la solucion en regiones donde la base no cambia.
"""

from dataclasses import replace

import numpy as np
import pytest

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex


TOL = 1e-3


def _barrer_parametro(attr, valores, base=None):
    """Resuelve el LP variando un atributo de ParametrosLote, devuelve (valor, Z*)."""
    base = base or ParametrosLote()
    resultados = []
    for v in valores:
        p = replace(base, **{attr: v})
        s = resolver_simplex(p)
        if s.estado == "Optimal":
            resultados.append((v, s.costo_total))
    return resultados


class TestParametrizacionRHS:
    def test_Z_es_monotono_no_decreciente_al_apretar_PC(self):
        """Aumentar pc_minima_kg nunca puede abaratar Z*."""
        valores = np.linspace(5.0, 9.0, 9)
        datos = _barrer_parametro("pc_minima_kg", valores)
        assert len(datos) >= 3
        zs = [z for _, z in datos]
        for i in range(1, len(zs)):
            assert zs[i] + TOL >= zs[i - 1], (
                f"Z* no es monotono: PC={datos[i][0]} dio Z*={zs[i]} < Z*={zs[i - 1]}"
            )

    def test_Z_es_convexa_en_RHS_de_FC(self):
        """Z*(FC_min) es convexa: segundas diferencias finitas >= 0."""
        valores = np.linspace(1.5, 2.8, 14)
        datos = _barrer_parametro("fc_minima_kg", valores)
        if len(datos) < 5:
            pytest.skip("No hay suficientes puntos factibles en el barrido")
        v = np.array([x for x, _ in datos])
        z = np.array([y for _, y in datos])
        dz = np.diff(z) / np.diff(v)
        # convexidad: dz/dv no decreciente -> diff(dz) >= 0 (con tolerancia)
        d2 = np.diff(dz)
        assert np.all(d2 + 1e-2 >= 0), (
            f"Z*(FC) no es convexa: segundas diferencias {d2.tolist()}"
        )

    def test_Z_es_monotono_no_decreciente_en_ratio_CaP(self):
        """Variar ca_p_ratio_min altera coeficientes de A (no RHS), por lo que
        la convexidad estricta no aplica; pero monotonia >= si: apretar el ratio
        no puede abaratar la solucion factible."""
        valores = np.linspace(0.4, 1.6, 13)
        datos = _barrer_parametro("ca_p_ratio_min", valores)
        if len(datos) < 5:
            pytest.skip("Pocos puntos factibles")
        zs = [z for _, z in datos]
        for i in range(1, len(zs)):
            assert zs[i] + TOL >= zs[i - 1], (
                f"Apretar ratio Ca:P abarato Z*: {datos[i - 1]} -> {datos[i]}"
            )


class TestPuntosDeQuiebre:
    def test_Z_es_lineal_a_trozos_en_PC(self):
        """En cada region donde la base no cambia, Z*(PC) es lineal: pendiente constante."""
        valores = np.linspace(5.0, 9.0, 41)  # malla fina
        datos = _barrer_parametro("pc_minima_kg", valores)
        if len(datos) < 10:
            pytest.skip("Pocos puntos factibles")
        v = np.array([x for x, _ in datos])
        z = np.array([y for _, y in datos])
        dz = np.diff(z) / np.diff(v)
        # Contamos cuantas pendientes distintas hay (con tolerancia).
        pendientes_unicas = []
        for s in dz:
            if not any(abs(s - p) < 1e-2 for p in pendientes_unicas):
                pendientes_unicas.append(s)
        # Idealmente esperamos 1-3 regiones lineales; un numero excesivo
        # delataria ruido numerico, pero el formato general debe ser bajo.
        assert len(pendientes_unicas) <= 5, (
            f"Demasiadas pendientes distintas ({len(pendientes_unicas)}): "
            f"posible inestabilidad numerica"
        )


class TestSaltosBruscos:
    def test_no_hay_saltos_grandes_en_Z(self):
        """Z* es continuo en RHS (no debe haber discontinuidades dentro del rango factible)."""
        valores = np.linspace(0.5, 1.6, 23)
        datos = _barrer_parametro("ca_p_ratio_min", valores)
        if len(datos) < 5:
            pytest.skip("Pocos puntos factibles")
        v = np.array([x for x, _ in datos])
        z = np.array([y for _, y in datos])
        # Diferencias absolutas consecutivas
        diffs = np.abs(np.diff(z))
        # Ningun salto debe ser >> que la mediana (heuristica de continuidad).
        mediana = float(np.median(diffs[diffs > 0])) if (diffs > 0).any() else 1.0
        max_salto = float(diffs.max())
        assert max_salto < 50 * max(mediana, 0.01), (
            f"Discontinuidad sospechosa: salto max {max_salto:.4f} vs mediana {mediana:.4f}"
        )
