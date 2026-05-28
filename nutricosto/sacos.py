"""Traduce la composicion optima continua a un plan de compra discreto en sacos.

Dada la solucion LP por lote de M kg y el numero de lotes que se desea
producir, calcula:

  - kg totales requeridos por insumo
  - sacos enteros a comprar (techo) usando la presentacion comercial
  - kg comprados realmente (sacos x kg_por_saco)
  - sobrante en kg respecto al requerimiento exacto
  - costo real al comprar sacos (sacos x precio_saco)
  - comparacion con el costo teorico continuo (kg x costo_kg)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .insumos import ParametrosLote
from .modelo import SolucionLP


@dataclass(frozen=True)
class FilaCompra:
    indice: int
    nombre: str
    kg_por_lote: float
    kg_requeridos: float
    kg_por_saco: float
    sacos_a_comprar: int
    kg_comprados: float
    sobrante_kg: float
    precio_saco: float
    costo_real: float
    costo_teorico_kg: float


@dataclass(frozen=True)
class PlanCompra:
    lotes: int
    masa_lote_kg: float
    masa_total_kg: float
    filas: list[FilaCompra]
    costo_real_total: float
    costo_teorico_total: float
    sobre_costo: float


def plan_de_compra(
    parametros: ParametrosLote,
    solucion: SolucionLP,
    lotes: int,
) -> PlanCompra:
    """Construye el plan de compra para `lotes` sacos terminados de concentrado."""

    lotes = max(int(lotes), 1)
    filas: list[FilaCompra] = []
    costo_real_total = 0.0
    costo_teorico_total = 0.0

    for ins in parametros.insumos:
        kg_por_lote = solucion.asignaciones.get(ins.nombre, 0.0) or 0.0
        kg_requeridos = kg_por_lote * lotes

        if ins.kg_por_saco and ins.kg_por_saco > 0 and ins.precio_saco > 0:
            sacos = int(math.ceil(kg_requeridos / ins.kg_por_saco)) if kg_requeridos > 1e-9 else 0
            kg_comprados = sacos * ins.kg_por_saco
            costo_real = sacos * ins.precio_saco
        else:
            sacos = 0
            kg_comprados = kg_requeridos
            costo_real = kg_requeridos * ins.costo_kg

        sobrante = kg_comprados - kg_requeridos
        costo_teorico = kg_requeridos * ins.costo_kg

        filas.append(
            FilaCompra(
                indice=ins.indice,
                nombre=ins.nombre,
                kg_por_lote=kg_por_lote,
                kg_requeridos=kg_requeridos,
                kg_por_saco=ins.kg_por_saco,
                sacos_a_comprar=sacos,
                kg_comprados=kg_comprados,
                sobrante_kg=sobrante,
                precio_saco=ins.precio_saco,
                costo_real=costo_real,
                costo_teorico_kg=costo_teorico,
            )
        )
        costo_real_total += costo_real
        costo_teorico_total += costo_teorico

    return PlanCompra(
        lotes=lotes,
        masa_lote_kg=parametros.masa_total_kg,
        masa_total_kg=parametros.masa_total_kg * lotes,
        filas=filas,
        costo_real_total=costo_real_total,
        costo_teorico_total=costo_teorico_total,
        sobre_costo=costo_real_total - costo_teorico_total,
    )
