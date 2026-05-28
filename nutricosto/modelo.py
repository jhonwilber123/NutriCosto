"""Construccion del modelo de Programacion Lineal con PuLP (Simplex).

Implementa la formulacion algebraica del plan maestro:

    Minimizar Z = sum(c_i * x_i)
    sujeto a:
        sum(x_i) = M                (masa fija del lote)
        x_fosvimin = 1.25           (prescripcion medica)
        x_sal = 0.50                (limite homeostatico)
        sum(pc_i * x_i) >= 14.0     (proteina cruda minima)
        sum(em_i * x_i) >= 285.0    (energia metabolizable minima)
        x_i <= limite_max_pct_i * M (techo por insumo: 70/40/30/20/20% para Maiz/Polvillo/Afrecho/Soya/Pasta)
        x_i >= 0                    (no negatividad)
"""

from dataclasses import dataclass

import pulp

from .insumos import ParametrosLote


@dataclass
class SolucionLP:
    """Resultado de la resolucion del modelo."""

    estado: str
    costo_total: float
    asignaciones: dict
    proteina_cruda_kg: float
    energia_metabolizable_mcal: float
    fibra_cruda_kg: float
    calcio_kg: float
    fosforo_kg: float
    masa_total_kg: float
    holguras: dict
    duales: dict
    solver: str


def construir_modelo(parametros: ParametrosLote):
    """Construye el problema LP en PuLP y devuelve (problema, variables)."""

    problema = pulp.LpProblem("NutriCosto_Puno", pulp.LpMinimize)

    variables = {
        ins.indice: pulp.LpVariable(
            name=f"x{ins.indice}_{ins.nombre}",
            lowBound=0,
            cat="Continuous",
        )
        for ins in parametros.insumos
    }

    problema += (
        pulp.lpSum(ins.costo_kg * variables[ins.indice] for ins in parametros.insumos),
        "Costo_total_del_lote",
    )

    problema += (
        pulp.lpSum(variables.values()) == parametros.masa_total_kg,
        "Masa_fija_100kg",
    )
    problema += (
        variables[parametros.indice_fosvimin] == parametros.fosvimin_kg,
        "Fosvimin_prescripcion",
    )
    problema += (
        variables[parametros.indice_sal] == parametros.sal_kg,
        "Sal_homeostatica",
    )
    problema += (
        pulp.lpSum(
            ins.proteina_cruda * variables[ins.indice] for ins in parametros.insumos
        )
        >= parametros.pc_minima_kg,
        "Proteina_cruda_minima",
    )
    problema += (
        pulp.lpSum(
            ins.energia_metabolizable * variables[ins.indice]
            for ins in parametros.insumos
        )
        >= parametros.em_minima_mcal,
        "Energia_metabolizable_minima",
    )
    problema += (
        pulp.lpSum(
            ins.fibra_cruda * variables[ins.indice] for ins in parametros.insumos
        )
        >= parametros.fc_minima_kg,
        "Fibra_cruda_minima",
    )
    problema += (
        pulp.lpSum(
            ins.calcio * variables[ins.indice] for ins in parametros.insumos
        )
        >= parametros.ca_minima_kg,
        "Calcio_minimo",
    )
    problema += (
        pulp.lpSum(
            ins.fosforo * variables[ins.indice] for ins in parametros.insumos
        )
        >= parametros.p_minima_kg,
        "Fosforo_minimo",
    )
    problema += (
        pulp.lpSum(
            (ins.calcio - parametros.ca_p_ratio_min * ins.fosforo) * variables[ins.indice]
            for ins in parametros.insumos
        )
        >= 0,
        "Ratio_Ca_P_minimo",
    )
    for ins in parametros.insumos:
        if ins.limite_max_pct is None:
            continue
        problema += (
            variables[ins.indice]
            <= ins.limite_max_pct * parametros.masa_total_kg,
            f"Limite_max_{ins.nombre}_{int(ins.limite_max_pct * 100)}pct",
        )

    return problema, variables


def resolver_simplex(parametros: ParametrosLote, verbose: bool = False) -> SolucionLP:
    """Resuelve el modelo via el solver CBC (Simplex) embebido en PuLP."""

    problema, variables = construir_modelo(parametros)
    solver = pulp.PULP_CBC_CMD(msg=1 if verbose else 0)
    problema.solve(solver)

    estado = pulp.LpStatus[problema.status]
    asignaciones = {
        ins.nombre: pulp.value(variables[ins.indice]) for ins in parametros.insumos
    }
    pc = sum(
        ins.proteina_cruda * asignaciones[ins.nombre] for ins in parametros.insumos
    )
    em = sum(
        ins.energia_metabolizable * asignaciones[ins.nombre]
        for ins in parametros.insumos
    )
    fc = sum(
        ins.fibra_cruda * asignaciones[ins.nombre] for ins in parametros.insumos
    )
    ca = sum(
        ins.calcio * asignaciones[ins.nombre] for ins in parametros.insumos
    )
    p = sum(
        ins.fosforo * asignaciones[ins.nombre] for ins in parametros.insumos
    )
    masa = sum(asignaciones.values())
    costo = pulp.value(problema.objective)

    holguras = {
        restriccion.name: restriccion.slack for restriccion in problema.constraints.values()
    }
    duales = {
        restriccion.name: restriccion.pi for restriccion in problema.constraints.values()
    }

    return SolucionLP(
        estado=estado,
        costo_total=float(costo) if costo is not None else float("nan"),
        asignaciones=asignaciones,
        proteina_cruda_kg=pc,
        energia_metabolizable_mcal=em,
        fibra_cruda_kg=fc,
        calcio_kg=ca,
        fosforo_kg=p,
        masa_total_kg=masa,
        holguras=holguras,
        duales=duales,
        solver="CBC (Simplex via PuLP)",
    )
