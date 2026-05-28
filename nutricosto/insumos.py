"""Parametrizacion de insumos y restricciones nutricionales.

Centraliza la matriz tecnologica del modelo: costos, aportes nutricionales y
limites maximos por insumo. Estos limites reflejan tanto tolerancias
fisiologicas (digestibilidad, palatabilidad) como restricciones tecnicas
de altitud >3,800 m.s.n.m. (prevencion del Sindrome Ascitico Bovino para el maiz).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Insumo:
    """Insumo con perfil nutricional, limite maximo y presentacion comercial.

    `limite_max_pct` se expresa como fraccion (0.60 = 60%). Es None para
    insumos cuya cantidad es fijada por prescripcion (Fosvimin, Sal).

    Aportes nutricionales se expresan como fraccion del peso del insumo
    (0.46 = 46%). `energia_metabolizable` esta en Mcal/kg.

    `precio_saco` y `kg_por_saco` describen la presentacion comercial del
    proveedor y se usan para traducir la composicion optima (en kg) a
    sacos fisicos a comprar.
    """
    indice: int
    nombre: str
    costo_kg: float
    proteina_cruda: float = 0.0
    energia_metabolizable: float = 0.0
    fibra_cruda: float = 0.0
    calcio: float = 0.0
    fosforo: float = 0.0
    limite_max_pct: float | None = None
    precio_saco: float = 0.0
    kg_por_saco: float = 0.0


@dataclass(frozen=True)
class Restriccion:
    """Restriccion tecnica o nutricional del lote."""
    nombre: str
    tipo: str
    valor: float
    unidad: str
    motivo: str


CATALOGO_INSUMOS = [
    Insumo(indice=1, nombre="Maiz",     costo_kg=1.35, proteina_cruda=0.08, energia_metabolizable=3.10, fibra_cruda=0.025, calcio=0.0002, fosforo=0.0028, limite_max_pct=0.60, precio_saco=50.0,  kg_por_saco=37.0),
    Insumo(indice=2, nombre="Polvillo", costo_kg=1.06, proteina_cruda=0.13, energia_metabolizable=2.80, fibra_cruda=0.07,  calcio=0.0007, fosforo=0.0150, limite_max_pct=0.40, precio_saco=53.0,  kg_por_saco=50.0),
    Insumo(indice=3, nombre="Afrecho",  costo_kg=1.38, proteina_cruda=0.15, energia_metabolizable=2.50, fibra_cruda=0.10,  calcio=0.0013, fosforo=0.0115, limite_max_pct=0.30, precio_saco=55.0,  kg_por_saco=40.0),
    Insumo(indice=4, nombre="Soya",     costo_kg=1.92, proteina_cruda=0.46, energia_metabolizable=2.90, fibra_cruda=0.07,  calcio=0.0030, fosforo=0.0065, limite_max_pct=0.20, precio_saco=92.0,  kg_por_saco=48.0),
    Insumo(indice=5, nombre="Pasta",    costo_kg=1.90, proteina_cruda=0.36, energia_metabolizable=2.60, fibra_cruda=0.12,  calcio=0.0015, fosforo=0.0095, limite_max_pct=0.20, precio_saco=95.0,  kg_por_saco=50.0),
    Insumo(indice=6, nombre="Fosvimin", costo_kg=8.00, proteina_cruda=0.00, energia_metabolizable=0.00, fibra_cruda=0.00,  calcio=0.2400, fosforo=0.1200, limite_max_pct=None, precio_saco=200.0, kg_por_saco=25.0),
    Insumo(indice=7, nombre="Sal",      costo_kg=0.56, proteina_cruda=0.00, energia_metabolizable=0.00, fibra_cruda=0.00,  calcio=0.0000, fosforo=0.0000, limite_max_pct=None, precio_saco=9.0,   kg_por_saco=16.0),
    Insumo(indice=8, nombre="Caliza",   costo_kg=0.40, proteina_cruda=0.00, energia_metabolizable=0.00, fibra_cruda=0.00,  calcio=0.3600, fosforo=0.0000, limite_max_pct=0.03, precio_saco=20.0,  kg_por_saco=50.0),
]


@dataclass(frozen=True)
class ParametrosLote:
    """Parametros operativos del lote y restricciones agregadas."""

    masa_total_kg: float = 50.0
    fosvimin_kg: float = 0.625
    sal_kg: float = 0.25
    pc_minima_kg: float = 7.0
    em_minima_mcal: float = 142.5
    fc_minima_kg: float = 2.5
    ca_minima_kg: float = 0.10
    p_minima_kg: float = 0.08
    ca_p_ratio_min: float = 1.3
    indice_fosvimin: int = 6
    indice_sal: int = 7

    insumos: list = field(default_factory=lambda: list(CATALOGO_INSUMOS))

    def restricciones(self) -> list:
        """Genera la lista descriptiva de todas las restricciones del modelo."""
        base = [
            Restriccion(
                nombre="Masa fija del lote",
                tipo="=",
                valor=self.masa_total_kg,
                unidad="kg",
                motivo=f"Estandarizacion por saco comercial ({self.masa_total_kg:.0f} kg).",
            ),
            Restriccion(
                nombre="Fosvimin (prescripcion medica)",
                tipo="=",
                valor=self.fosvimin_kg,
                unidad="kg",
                motivo="625 g por saco de 50 kg (indicacion del proveedor).",
            ),
            Restriccion(
                nombre="Sal (limite homeostatico)",
                tipo="=",
                valor=self.sal_kg,
                unidad="kg",
                motivo="Evita intoxicacion por sodio en rumiantes.",
            ),
            Restriccion(
                nombre="Proteina cruda minima",
                tipo=">=",
                valor=self.pc_minima_kg,
                unidad="kg",
                motivo="Requerimiento de tejido muscular para engorde.",
            ),
            Restriccion(
                nombre="Energia metabolizable minima",
                tipo=">=",
                valor=self.em_minima_mcal,
                unidad="Mcal",
                motivo="Demanda calorica para ganancia diaria de peso.",
            ),
            Restriccion(
                nombre="Fibra cruda minima",
                tipo=">=",
                valor=self.fc_minima_kg,
                unidad="kg",
                motivo="Salud ruminal: previene acidosis por exceso de NSC.",
            ),
            Restriccion(
                nombre="Calcio minimo",
                tipo=">=",
                valor=self.ca_minima_kg,
                unidad="kg",
                motivo="Mineralizacion osea y funcion muscular en engorde.",
            ),
            Restriccion(
                nombre="Fosforo minimo",
                tipo=">=",
                valor=self.p_minima_kg,
                unidad="kg",
                motivo="Crecimiento esqueletico y metabolismo energetico.",
            ),
            Restriccion(
                nombre="Ratio Ca:P minimo",
                tipo=">=",
                valor=self.ca_p_ratio_min,
                unidad="(adim)",
                motivo="Evita desbalance mineral (rango fisiologico 1.3-2.0:1).",
            ),
        ]
        for ins in self.insumos:
            if ins.limite_max_pct is None:
                continue
            motivo = (
                "Prevencion Sindrome Ascitico Bovino (>3,800 m.s.n.m.)."
                if ins.nombre == "Maiz"
                else f"Tolerancia digestiva/palatabilidad para {ins.nombre}."
            )
            base.append(
                Restriccion(
                    nombre=f"Limite maximo {ins.nombre}",
                    tipo="<=",
                    valor=ins.limite_max_pct * self.masa_total_kg,
                    unidad="kg",
                    motivo=motivo,
                )
            )
        return base
