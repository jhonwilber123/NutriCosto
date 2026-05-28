"""Fixtures compartidos para los tests de NutriCosto."""

import sys
from pathlib import Path

import pytest

# Permite ejecutar pytest desde la raiz del proyecto sin instalar el paquete.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nutricosto.insumos import ParametrosLote  # noqa: E402
from nutricosto.modelo import resolver_simplex  # noqa: E402
from nutricosto.solver import resolver_interior_point  # noqa: E402


@pytest.fixture
def parametros_default() -> ParametrosLote:
    """ParametrosLote con todos los defaults (lote de 50 kg, ratio Ca:P 1.3)."""
    return ParametrosLote()


@pytest.fixture
def solucion_default(parametros_default):
    """Solucion Simplex (CBC) usando defaults."""
    return resolver_simplex(parametros_default)


@pytest.fixture
def solucion_ip_default(parametros_default):
    """Solucion Interior Point (HiGHS) usando defaults."""
    return resolver_interior_point(parametros_default)
