"""Analisis Monte Carlo: propagacion de incertidumbre de precios al optimo.

Si los precios del mercado fluctuan +-X%, ¿cual es la distribucion de Z*?
¿Que tan estable es la mezcla optima? Estos tests cuantifican la robustez
del plan recomendado frente a variabilidad en el costo de insumos.
"""

import random
import statistics
from collections import Counter
from dataclasses import replace

import pytest

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex


N_MUESTRAS = 200
SEED = 42


def _muestra_precios(base, rng, sigma_relativo):
    """Aplica un factor multiplicativo gaussiano a cada costo_kg."""
    nuevos = []
    for ins in base.insumos:
        if ins.costo_kg <= 0:
            nuevos.append(ins)
            continue
        factor = max(0.1, rng.gauss(1.0, sigma_relativo))
        nuevos.append(replace(
            ins,
            costo_kg=ins.costo_kg * factor,
            precio_saco=ins.precio_saco * factor,
        ))
    return replace(base, insumos=nuevos)


def _simular(sigma):
    rng = random.Random(SEED)
    base = ParametrosLote()
    Z = []
    mezclas = []
    for _ in range(N_MUESTRAS):
        p = _muestra_precios(base, rng, sigma)
        s = resolver_simplex(p)
        if s.estado != "Optimal":
            continue
        Z.append(s.costo_total)
        # Codificamos la "firma" de la mezcla (que insumos basicos)
        basicos = tuple(sorted(
            n for n, kg in s.asignaciones.items()
            if kg > 0.1 and n not in ("Fosvimin", "Sal")
        ))
        mezclas.append(basicos)
    return Z, mezclas


class TestDistribucionDeZ:
    def test_Z_es_finito_y_positivo_en_todas_las_muestras(self):
        Z, _ = _simular(sigma=0.15)
        assert len(Z) >= int(0.9 * N_MUESTRAS), "Demasiados casos infactibles bajo perturbacion 15%"
        for z in Z:
            assert z > 0 and z < 1_000_000

    def test_volatilidad_de_Z_escala_con_sigma_de_precios(self):
        """Mayor sigma de precios -> mayor std de Z* (relacion monotona)."""
        Z_baja, _ = _simular(sigma=0.05)
        Z_alta, _ = _simular(sigma=0.30)
        std_baja = statistics.stdev(Z_baja)
        std_alta = statistics.stdev(Z_alta)
        assert std_alta > std_baja, (
            f"Volatilidad no escala: std(sigma=0.05)={std_baja:.2f}, "
            f"std(sigma=0.30)={std_alta:.2f}"
        )

    def test_media_de_Z_es_razonable_cerca_del_caso_base(self):
        """Con sigma pequeno la media debe estar cerca del Z* deterministico."""
        Z, _ = _simular(sigma=0.05)
        Z_base = resolver_simplex(ParametrosLote()).costo_total
        media = statistics.mean(Z)
        # +-20% de margen para 200 muestras con sigma=5%.
        assert abs(media - Z_base) / Z_base < 0.20


class TestRobustezDeLaMezcla:
    def test_existe_una_mezcla_dominante_con_volatilidad_moderada(self):
        """Bajo sigma=10%, una sola firma de basicos debe aparecer en >=20% de muestras."""
        _, mezclas = _simular(sigma=0.10)
        if not mezclas:
            pytest.skip("Sin muestras factibles")
        conteo = Counter(mezclas)
        firma_top, ocurr = conteo.most_common(1)[0]
        fraccion = ocurr / len(mezclas)
        assert fraccion >= 0.20, (
            f"Ninguna firma de mezcla domina: top={firma_top} con {fraccion*100:.1f}%"
        )

    def test_diversidad_de_mezclas_crece_con_sigma(self):
        """Mas incertidumbre -> el LP cambia de vertice mas seguido."""
        _, mezclas_baja = _simular(sigma=0.05)
        _, mezclas_alta = _simular(sigma=0.40)
        if not mezclas_baja or not mezclas_alta:
            pytest.skip("Sin muestras factibles")
        n_firmas_baja = len(set(mezclas_baja))
        n_firmas_alta = len(set(mezclas_alta))
        assert n_firmas_alta >= n_firmas_baja, (
            f"Diversidad cae con mas sigma: baja={n_firmas_baja}, alta={n_firmas_alta}"
        )


class TestPercentiles:
    def test_percentil_95_define_presupuesto_de_seguridad(self):
        """Z*_95 (presupuesto al que <=5% de escenarios lo superan) > mediana."""
        Z, _ = _simular(sigma=0.20)
        Z_ord = sorted(Z)
        mediana = Z_ord[len(Z_ord) // 2]
        p95 = Z_ord[int(len(Z_ord) * 0.95)]
        assert p95 > mediana
        # Y debe ser razonablemente cercano: factor <=2x para sigma=20%.
        assert p95 / mediana < 2.0
