"""Generacion de reportes tabulares de la solucion optima.

Incluye:
- Funcion objetivo formulada simbolicamente.
- Composicion del lote (kg, %, costo parcial).
- Verificacion del cumplimiento de restricciones.
- Precios sombra (variables duales) e interpretacion economica.
- Comparacion cruzada Simplex vs Interior Point.
"""

from tabulate import tabulate

from .insumos import ParametrosLote
from .modelo import SolucionLP
from .solver import SolucionScipy


def formato_funcion_objetivo(parametros: ParametrosLote) -> str:
    terminos = []
    for ins in parametros.insumos:
        terminos.append(f"{ins.costo_kg:.2f}*x{ins.indice}")
    return "Z = " + " + ".join(terminos)


def tabla_composicion(parametros: ParametrosLote, solucion: SolucionLP) -> str:
    filas = []
    masa = solucion.masa_total_kg or 1.0
    for ins in parametros.insumos:
        kg = solucion.asignaciones[ins.nombre]
        porcentaje = 100.0 * kg / masa
        costo_parcial = kg * ins.costo_kg
        filas.append(
            [
                f"x{ins.indice}",
                ins.nombre,
                f"{ins.costo_kg:.2f}",
                f"{kg:.4f}",
                f"{porcentaje:.2f}%",
                f"{costo_parcial:.4f}",
            ]
        )
    filas.append(
        [
            "",
            "TOTAL",
            "",
            f"{solucion.masa_total_kg:.4f}",
            "100.00%",
            f"{solucion.costo_total:.4f}",
        ]
    )
    return tabulate(
        filas,
        headers=["Var", "Insumo", "Costo/kg", "kg", "%", "Costo parcial"],
        tablefmt="github",
        stralign="right",
    )


def tabla_restricciones(parametros: ParametrosLote, solucion: SolucionLP) -> str:
    filas = []
    for restriccion in parametros.restricciones():
        filas.append(
            [
                restriccion.nombre,
                restriccion.tipo,
                f"{restriccion.valor:.2f} {restriccion.unidad}",
                restriccion.motivo,
            ]
        )
    return tabulate(
        filas,
        headers=["Restriccion", "Tipo", "RHS", "Justificacion"],
        tablefmt="github",
    )


def tabla_nutricional(parametros: ParametrosLote, solucion: SolucionLP) -> str:
    ratio = (
        solucion.calcio_kg / solucion.fosforo_kg if solucion.fosforo_kg > 1e-9 else 0.0
    )
    filas = [
        [
            "Masa total",
            f"{solucion.masa_total_kg:.4f} kg",
            f"= {parametros.masa_total_kg:.2f} kg",
            _check(abs(solucion.masa_total_kg - parametros.masa_total_kg) < 1e-3),
        ],
        [
            "Proteina cruda",
            f"{solucion.proteina_cruda_kg:.4f} kg",
            f">= {parametros.pc_minima_kg:.2f} kg",
            _check(solucion.proteina_cruda_kg + 1e-3 >= parametros.pc_minima_kg),
        ],
        [
            "Energia metabolizable",
            f"{solucion.energia_metabolizable_mcal:.4f} Mcal",
            f">= {parametros.em_minima_mcal:.2f} Mcal",
            _check(
                solucion.energia_metabolizable_mcal + 1e-3
                >= parametros.em_minima_mcal
            ),
        ],
        [
            "Fibra cruda",
            f"{solucion.fibra_cruda_kg:.4f} kg",
            f">= {parametros.fc_minima_kg:.2f} kg",
            _check(solucion.fibra_cruda_kg + 1e-3 >= parametros.fc_minima_kg),
        ],
        [
            "Calcio",
            f"{solucion.calcio_kg:.4f} kg",
            f">= {parametros.ca_minima_kg:.2f} kg",
            _check(solucion.calcio_kg + 1e-5 >= parametros.ca_minima_kg),
        ],
        [
            "Fosforo",
            f"{solucion.fosforo_kg:.4f} kg",
            f">= {parametros.p_minima_kg:.2f} kg",
            _check(solucion.fosforo_kg + 1e-5 >= parametros.p_minima_kg),
        ],
        [
            "Ratio Ca:P",
            f"{ratio:.4f}",
            f">= {parametros.ca_p_ratio_min:.2f}",
            _check(ratio + 1e-3 >= parametros.ca_p_ratio_min),
        ],
        [
            "Fosvimin (x6)",
            f"{solucion.asignaciones['Fosvimin']:.4f} kg",
            f"= {parametros.fosvimin_kg:.2f} kg",
            _check(abs(solucion.asignaciones["Fosvimin"] - parametros.fosvimin_kg) < 1e-3),
        ],
        [
            "Sal (x7)",
            f"{solucion.asignaciones['Sal']:.4f} kg",
            f"= {parametros.sal_kg:.2f} kg",
            _check(abs(solucion.asignaciones["Sal"] - parametros.sal_kg) < 1e-3),
        ],
    ]
    for ins in parametros.insumos:
        if ins.limite_max_pct is None:
            continue
        techo_kg = ins.limite_max_pct * parametros.masa_total_kg
        valor = solucion.asignaciones[ins.nombre]
        filas.append(
            [
                f"Limite max {ins.nombre} ({int(ins.limite_max_pct * 100)}%)",
                f"{valor:.4f} kg",
                f"<= {techo_kg:.2f} kg",
                _check(valor <= techo_kg + 1e-3),
            ]
        )
    return tabulate(
        filas,
        headers=["Metrica", "Obtenido", "Limite", "Cumple"],
        tablefmt="github",
    )


def tabla_sensibilidad(solucion: SolucionLP) -> str:
    filas = []
    for nombre, holgura in solucion.holguras.items():
        dual = solucion.duales.get(nombre)
        filas.append(
            [
                nombre,
                f"{holgura:.6f}" if holgura is not None else "n/d",
                f"{dual:.6f}" if dual is not None else "n/d",
                _interpretar_dual(dual),
            ]
        )
    return tabulate(
        filas,
        headers=["Restriccion", "Holgura", "Precio sombra", "Interpretacion"],
        tablefmt="github",
    )


def tabla_verificacion_cruzada(simplex: SolucionLP, ip: SolucionScipy) -> str:
    filas = []
    for nombre in simplex.asignaciones:
        v_simplex = simplex.asignaciones[nombre]
        v_ip = ip.asignaciones[nombre]
        delta = abs(v_simplex - v_ip)
        filas.append(
            [
                nombre,
                f"{v_simplex:.6f}",
                f"{v_ip:.6f}",
                f"{delta:.2e}",
                _check(delta < 1e-3),
            ]
        )
    filas.append(
        [
            "Z (costo)",
            f"{simplex.costo_total:.6f}",
            f"{ip.costo_total:.6f}",
            f"{abs(simplex.costo_total - ip.costo_total):.2e}",
            _check(abs(simplex.costo_total - ip.costo_total) < 1e-3),
        ]
    )
    return tabulate(
        filas,
        headers=["Variable", "Simplex (CBC)", "Interior Point (HiGHS)", "|delta|", "OK"],
        tablefmt="github",
    )


def _check(ok: bool) -> str:
    return "OK" if ok else "FALLA"


def _interpretar_dual(dual):
    if dual is None:
        return "no disponible"
    if abs(dual) < 1e-9:
        return "restriccion no activa (holgura)"
    signo = "encarece" if dual > 0 else "abarata"
    return f"relajar en 1 unidad {signo} el optimo en {abs(dual):.4f}"


def reporte_completo(
    parametros: ParametrosLote,
    solucion: SolucionLP,
    verificacion: SolucionScipy,
) -> str:
    encabezado = (
        "=" * 78
        + "\nNUTRICOSTO :: OPTIMIZACION LINEAL DE RACIONES (Puno, Altiplano)\n"
        + "=" * 78
    )
    secciones = [
        encabezado,
        f"\n[1] FUNCION OBJETIVO\n    Minimizar  {formato_funcion_objetivo(parametros)}",
        f"\n[2] RESTRICCIONES DEL MODELO\n{tabla_restricciones(parametros, solucion)}",
        f"\n[3] ESTADO DEL SOLVER\n    Solver primario : {solucion.solver}\n"
        f"    Estado          : {solucion.estado}\n"
        f"    Costo optimo Z* : {solucion.costo_total:.4f} (unidades monetarias)",
        f"\n[4] COMPOSICION OPTIMA DEL LOTE ({parametros.masa_total_kg:.0f} kg)\n{tabla_composicion(parametros, solucion)}",
        f"\n[5] CUMPLIMIENTO NUTRICIONAL Y TECNICO\n{tabla_nutricional(parametros, solucion)}",
        f"\n[6] ANALISIS DE SENSIBILIDAD (precios sombra)\n{tabla_sensibilidad(solucion)}",
        f"\n[7] VERIFICACION CRUZADA Simplex vs Interior Point\n{tabla_verificacion_cruzada(solucion, verificacion)}",
        "\n" + "=" * 78,
    ]
    return "\n".join(secciones)
