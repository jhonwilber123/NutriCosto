"""CLI principal de NutriCosto.

Uso:
    python main.py                      # ejecucion con parametros por defecto
    python main.py --pc-min 15.0        # endurece la proteina cruda minima
    python main.py --em-min 300.0       # endurece la energia metabolizable
    python main.py --techo-nsc 0.65     # baja el techo de carbohidratos
    python main.py --verbose            # imprime trazas del solver CBC
"""

import argparse
import sys

from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex
from nutricosto.reporte import reporte_completo
from nutricosto.solver import resolver_interior_point


def parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Optimizador lineal de raciones para toros de engorde (Puno).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--masa", type=float, default=50.0, help="Masa total del lote (kg).")
    parser.add_argument("--fosvimin", type=float, default=0.625, help="Dosis de Fosvimin (kg).")
    parser.add_argument("--sal", type=float, default=0.25, help="Dosis de sal (kg).")
    parser.add_argument("--pc-min", type=float, default=7.0, help="Proteina cruda minima (kg).")
    parser.add_argument("--em-min", type=float, default=142.5, help="Energia metabolizable minima (Mcal).")
    parser.add_argument("--fc-min", type=float, default=2.5, help="Fibra cruda minima (kg).")
    parser.add_argument("--ca-min", type=float, default=0.10, help="Calcio minimo (kg).")
    parser.add_argument("--p-min", type=float, default=0.08, help="Fosforo minimo (kg).")
    parser.add_argument("--ca-p-ratio-min", type=float, default=1.3, help="Ratio Ca:P minimo.")
    parser.add_argument("--verbose", action="store_true", help="Mostrar trazas del solver.")
    return parser.parse_args()


def main() -> int:
    args = parsear_argumentos()

    parametros = ParametrosLote(
        masa_total_kg=args.masa,
        fosvimin_kg=args.fosvimin,
        sal_kg=args.sal,
        pc_minima_kg=args.pc_min,
        em_minima_mcal=args.em_min,
        fc_minima_kg=args.fc_min,
        ca_minima_kg=args.ca_min,
        p_minima_kg=args.p_min,
        ca_p_ratio_min=args.ca_p_ratio_min,
    )

    solucion = resolver_simplex(parametros, verbose=args.verbose)
    verificacion = resolver_interior_point(parametros)

    print(reporte_completo(parametros, solucion, verificacion))

    if solucion.estado != "Optimal":
        print(f"\n[!] Estado no optimo: {solucion.estado}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
