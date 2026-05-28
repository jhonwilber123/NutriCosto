"""Verificacion cruzada del modelo LP via scipy.optimize.linprog.

Resuelve el mismo problema con metodo HiGHS (interior-point dual) para corroborar
numericamente la solucion obtenida por el simplex CBC. La discrepancia entre
ambos solucionadores debe ser despreciable (tolerancia 1e-6).
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog

from .insumos import ParametrosLote


@dataclass
class SolucionScipy:
    estado: str
    costo_total: float
    asignaciones: dict
    solver: str


def resolver_interior_point(parametros: ParametrosLote) -> SolucionScipy:
    """Resuelve el LP con el solver HiGHS de SciPy.

    Construye las matrices A_eq, b_eq, A_ub, b_ub a partir del catalogo.
    """
    insumos = parametros.insumos
    n = len(insumos)
    nombres = [ins.nombre for ins in insumos]
    indices = {ins.indice: pos for pos, ins in enumerate(insumos)}

    c = np.array([ins.costo_kg for ins in insumos], dtype=float)

    fila_masa = np.ones(n)
    fila_fosvimin = np.zeros(n)
    fila_fosvimin[indices[parametros.indice_fosvimin]] = 1.0
    fila_sal = np.zeros(n)
    fila_sal[indices[parametros.indice_sal]] = 1.0

    A_eq = np.vstack([fila_masa, fila_fosvimin, fila_sal])
    b_eq = np.array(
        [parametros.masa_total_kg, parametros.fosvimin_kg, parametros.sal_kg],
        dtype=float,
    )

    fila_pc = np.array([-ins.proteina_cruda for ins in insumos])
    fila_em = np.array([-ins.energia_metabolizable for ins in insumos])
    fila_fc = np.array([-ins.fibra_cruda for ins in insumos])
    fila_ca = np.array([-ins.calcio for ins in insumos])
    fila_p = np.array([-ins.fosforo for ins in insumos])
    fila_ratio = np.array(
        [-(ins.calcio - parametros.ca_p_ratio_min * ins.fosforo) for ins in insumos]
    )

    filas_techos = []
    b_techos = []
    for ins in insumos:
        if ins.limite_max_pct is None:
            continue
        fila = np.zeros(n)
        fila[indices[ins.indice]] = 1.0
        filas_techos.append(fila)
        b_techos.append(ins.limite_max_pct * parametros.masa_total_kg)

    A_ub = np.vstack(
        [fila_pc, fila_em, fila_fc, fila_ca, fila_p, fila_ratio, *filas_techos]
    ) if filas_techos else np.vstack(
        [fila_pc, fila_em, fila_fc, fila_ca, fila_p, fila_ratio]
    )
    b_ub = np.array(
        [
            -parametros.pc_minima_kg,
            -parametros.em_minima_mcal,
            -parametros.fc_minima_kg,
            -parametros.ca_minima_kg,
            -parametros.p_minima_kg,
            0.0,
            *b_techos,
        ],
        dtype=float,
    )

    bounds = [(0, None)] * n

    resultado = linprog(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    asignaciones = {
        nombres[i]: float(resultado.x[i]) if resultado.x is not None else float("nan")
        for i in range(n)
    }

    return SolucionScipy(
        estado=resultado.message,
        costo_total=float(resultado.fun) if resultado.fun is not None else float("nan"),
        asignaciones=asignaciones,
        solver="HiGHS (Interior Point via SciPy)",
    )
