"""NutriCosto - Aplicacion Streamlit con diseno Claude.

Interfaz interactiva para optimizar raciones balanceadas, editar precios y
persistir tandas de produccion en SQLite.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from nutricosto.db import (
    borrar_tanda,
    detalle_tanda,
    guardar_tanda,
    listar_tandas,
)
from nutricosto.estilos import CSS
from nutricosto.insumos import CATALOGO_INSUMOS, Insumo, ParametrosLote
from nutricosto.modelo import resolver_simplex
from nutricosto.solver import resolver_interior_point


st.set_page_config(
    page_title="NutriCosto",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(CSS, unsafe_allow_html=True)


def hero() -> None:
    st.markdown(
        """
        <div class="nc-hero">
            <div class="nc-hero-eyebrow">Optimizacion lineal · Altiplano peruano</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("# NutriCosto")
    st.markdown(
        """
        <div class="nc-hero-sub">
            Formulacion automatica de alimento balanceado para toros de engorde
            en Puno. Minimiza el costo del lote sujeto a requerimientos
            nutricionales, prescripciones veterinarias y restricciones
            geograficas (techo de NSC anti Sindrome Ascitico Bovino).
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)


def seccion(titulo: str) -> None:
    st.markdown(f'<div class="nc-section-title">{titulo}</div>', unsafe_allow_html=True)


def pill(texto: str, tono: str = "") -> str:
    clase = f"nc-pill {tono}".strip()
    return f'<span class="{clase}">{texto}</span>'


def construir_parametros(
    precios: dict[str, float],
    pc_min: float,
    em_min: float,
    techo_nsc: float,
    fosvimin_kg: float,
    sal_kg: float,
    masa_total: float,
) -> ParametrosLote:
    insumos_editados = [
        Insumo(
            indice=base.indice,
            nombre=base.nombre,
            costo_kg=precios[base.nombre],
            proteina_cruda=base.proteina_cruda,
            energia_metabolizable=base.energia_metabolizable,
        )
        for base in CATALOGO_INSUMOS
    ]
    return ParametrosLote(
        masa_total_kg=masa_total,
        fosvimin_kg=fosvimin_kg,
        sal_kg=sal_kg,
        pc_minima_kg=pc_min,
        em_minima_mcal=em_min,
        techo_nsc_porcentaje=techo_nsc,
        insumos=insumos_editados,
    )


def tab_optimizar() -> None:
    col_inputs, col_resultado = st.columns([1, 1.25], gap="large")

    with col_inputs:
        seccion("Precios de insumos")
        st.caption("Costo en soles por kilogramo. Refleja la cotizacion vigente del proveedor.")

        precios: dict[str, float] = {}
        pares = [CATALOGO_INSUMOS[i:i + 2] for i in range(0, len(CATALOGO_INSUMOS), 2)]
        for fila in pares:
            cols = st.columns(len(fila))
            for col, ins in zip(cols, fila):
                with col:
                    precios[ins.nombre] = st.number_input(
                        label=f"{ins.nombre}  ·  x{ins.indice}",
                        min_value=0.0,
                        value=float(ins.costo_kg),
                        step=0.05,
                        format="%.2f",
                        key=f"p_{ins.nombre}",
                        help=(
                            f"Proteina cruda: {ins.proteina_cruda * 100:.0f}%  ·  "
                            f"Energia: {ins.energia_metabolizable:.2f} Mcal/kg"
                        ),
                    )

        st.markdown("<br>", unsafe_allow_html=True)
        seccion("Restricciones nutricionales")

        col_a, col_b = st.columns(2)
        with col_a:
            pc_min = st.number_input(
                "Proteina cruda min (kg)", min_value=0.0, value=7.0, step=0.5
            )
            fosvimin_kg = st.number_input(
                "Fosvimin (kg)", min_value=0.0, value=0.625, step=0.025
            )
        with col_b:
            em_min = st.number_input(
                "Energia metab. min (Mcal)", min_value=0.0, value=142.5, step=2.5
            )
            sal_kg = st.number_input(
                "Sal (kg)", min_value=0.0, value=0.25, step=0.05
            )

        masa_total = st.number_input(
            "Masa total del lote (kg)", min_value=1.0, value=50.0, step=1.0
        )
        techo_nsc = st.slider(
            "Techo de NSC sobre el maiz",
            min_value=0.10, max_value=1.00, value=0.70, step=0.05,
            format="%.0f%%",
            help="Prevencion del Sindrome Ascitico Bovino a >3,800 m.s.n.m.",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Optimizar lote", type="primary", use_container_width=True):
            parametros = construir_parametros(
                precios, pc_min, em_min, techo_nsc, fosvimin_kg, sal_kg, masa_total
            )
            try:
                solucion = resolver_simplex(parametros)
                verificacion = resolver_interior_point(parametros)
                st.session_state["sol"] = solucion
                st.session_state["ver"] = verificacion
                st.session_state["par"] = parametros
            except Exception as exc:
                st.error(f"Error en el solver: {exc}")

    with col_resultado:
        seccion("Resultado")
        sol = st.session_state.get("sol")
        if sol is None:
            st.markdown(
                """
                <div class="nc-card">
                    <h4>Sin resolver aun</h4>
                    <p style="color:var(--text-muted); margin:0;">
                        Configure los precios y restricciones, luego presione
                        <strong>Optimizar lote</strong> para encontrar la
                        combinacion de minimo costo que cumple los requisitos
                        nutricionales.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        ver = st.session_state["ver"]
        par = st.session_state["par"]

        if sol.estado != "Optimal":
            st.error(f"Estado del solver: {sol.estado}")
            return

        delta_ip = abs(sol.costo_total - ver.costo_total)
        badge = pill("OPTIMO", "ok") + " " + pill(
            f"Δ vs Interior Point: {delta_ip:.2e}", "ok" if delta_ip < 1e-4 else "warn"
        )
        st.markdown(badge, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("Costo optimo Z*", f"S/. {sol.costo_total:.2f}")
        m2.metric("Proteina cruda", f"{sol.proteina_cruda_kg:.2f} kg")
        m3.metric("Energia metab.", f"{sol.energia_metabolizable_mcal:.1f} Mcal")

        st.markdown("<br>", unsafe_allow_html=True)

        composicion = pd.DataFrame(
            [
                {
                    "Var": f"x{ins.indice}",
                    "Insumo": ins.nombre,
                    "kg": round(sol.asignaciones[ins.nombre], 3),
                    "%": round(100.0 * sol.asignaciones[ins.nombre] / sol.masa_total_kg, 2),
                    "S/./kg": ins.costo_kg,
                    "Parcial S/.": round(sol.asignaciones[ins.nombre] * ins.costo_kg, 2),
                }
                for ins in par.insumos
            ]
        )

        st.markdown('<div class="nc-card"><h4>Composicion del lote</h4>', unsafe_allow_html=True)
        st.dataframe(
            composicion.style.bar(
                subset=["kg"], color="#F1CDB8", align="left"
            ).format({"%": "{:.2f}", "S/./kg": "{:.2f}", "Parcial S/.": "{:.2f}"}),
            use_container_width=True,
            hide_index=True,
            height=290,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("Analisis de sensibilidad (precios sombra)"):
            sensibilidad = pd.DataFrame(
                [
                    {
                        "Restriccion": nombre.replace("_", " "),
                        "Holgura": round(sol.holguras.get(nombre, 0.0) or 0.0, 4),
                        "Precio sombra": round(sol.duales.get(nombre, 0.0) or 0.0, 4),
                        "Activa": "Si" if abs(sol.holguras.get(nombre, 0.0) or 0.0) < 1e-4 else "No",
                    }
                    for nombre in sol.holguras
                ]
            )
            st.dataframe(sensibilidad, use_container_width=True, hide_index=True)
            st.caption(
                "Una restriccion activa (holgura ≈ 0) marca el cuello de botella: "
                "su precio sombra indica cuanto cambia Z* por relajar 1 unidad."
            )

        st.markdown("<br>", unsafe_allow_html=True)
        seccion("Registrar tanda")
        with st.form("guardar_tanda", clear_on_submit=True):
            col_c, col_n = st.columns([1, 2])
            with col_c:
                codigo = st.text_input("Codigo", placeholder="LOT-2026-001")
            with col_n:
                notas = st.text_input("Notas", placeholder="Observaciones de la tanda")
            if st.form_submit_button("Guardar en base de datos", type="primary"):
                tid = guardar_tanda(par, sol, codigo=codigo or None, notas=notas or None)
                st.success(f"Tanda #{tid} registrada. Disponible en 'Historico'.")


def tab_historico() -> None:
    seccion("Tandas registradas")
    tandas = listar_tandas()
    if not tandas:
        st.markdown(
            """
            <div class="nc-card">
                <h4>Sin registros</h4>
                <p style="color:var(--text-muted); margin:0;">
                    Optimiza un lote y presiona <strong>Guardar en base de datos</strong>
                    para construir el historico de tandas.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    df = pd.DataFrame(tandas)
    df["fecha"] = pd.to_datetime(df["fecha"])

    col_resumen = st.columns(3)
    col_resumen[0].metric("Tandas registradas", len(df))
    col_resumen[1].metric("Z* promedio", f"S/. {df['costo_optimo'].mean():.2f}")
    col_resumen[2].metric("Ultimo Z*", f"S/. {df.iloc[0]['costo_optimo']:.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    vista = df.rename(
        columns={
            "id": "ID", "fecha": "Fecha", "codigo": "Codigo",
            "masa_kg": "Masa", "pc_min_kg": "PC min", "em_min_mcal": "EM min",
            "techo_nsc": "NSC", "estado_solver": "Estado", "costo_optimo": "Z* (S/.)",
        }
    )[["ID", "Fecha", "Codigo", "Masa", "PC min", "EM min", "NSC", "Estado", "Z* (S/.)"]]
    vista["Fecha"] = vista["Fecha"].dt.strftime("%Y-%m-%d %H:%M")

    st.dataframe(
        vista.style.format({"Z* (S/.)": "{:.2f}", "NSC": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
        height=280,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    seccion("Detalle de tanda")

    seleccion = st.selectbox(
        "Selecciona una tanda",
        options=[t["id"] for t in tandas],
        format_func=lambda i: (
            f"#{i}  ·  "
            + next((t["codigo"] or t["fecha"][:16]) for t in tandas if t["id"] == i)
        ),
    )
    if seleccion is None:
        return

    detalle = detalle_tanda(seleccion)
    cab = detalle["cabecera"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Z* (S/.)", f"{cab['costo_optimo']:.2f}")
    c2.metric("Masa", f"{cab['masa_kg']:.0f} kg")
    c3.metric("PC min", f"{cab['pc_min_kg']:.1f} kg")
    c4.metric("EM min", f"{cab['em_min_mcal']:.0f} Mcal")

    col_p, col_c = st.columns(2)
    with col_p:
        st.markdown('<div class="nc-card"><h4>Precios usados</h4>', unsafe_allow_html=True)
        st.dataframe(
            pd.DataFrame(detalle["precios"]).rename(
                columns={"insumo": "Insumo", "costo_kg": "S/. / kg"}
            ).style.format({"S/. / kg": "{:.2f}"}),
            use_container_width=True, hide_index=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with col_c:
        st.markdown('<div class="nc-card"><h4>Composicion resultante</h4>', unsafe_allow_html=True)
        st.dataframe(
            pd.DataFrame(detalle["composicion"]).rename(
                columns={"insumo": "Insumo", "kg": "kg", "costo_parcial": "S/. parcial"}
            ).style.format({"kg": "{:.3f}", "S/. parcial": "{:.2f}"}),
            use_container_width=True, hide_index=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if cab.get("notas"):
        st.info(f"**Notas:** {cab['notas']}")

    if st.button("Eliminar esta tanda", type="secondary"):
        borrar_tanda(seleccion)
        st.warning(f"Tanda #{seleccion} eliminada. Recarga la pestania.")


def tab_analisis() -> None:
    seccion("Evolucion del costo optimo")
    tandas = listar_tandas()
    if not tandas:
        st.markdown(
            """
            <div class="nc-card">
                <h4>Sin datos</h4>
                <p style="color:var(--text-muted); margin:0;">
                    Necesitas registrar al menos una tanda para ver tendencias.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    df = pd.DataFrame(tandas)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha")

    c1, c2, c3 = st.columns(3)
    c1.metric("Tandas", len(df))
    c2.metric("Z* promedio", f"S/. {df['costo_optimo'].mean():.2f}")
    c3.metric(
        "Volatilidad",
        f"S/. {df['costo_optimo'].std():.2f}" if len(df) > 1 else "—",
        help="Desviacion estandar del costo entre tandas.",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="nc-card"><h4>Serie temporal de Z*</h4>', unsafe_allow_html=True)
    st.line_chart(
        df.set_index("fecha")["costo_optimo"], height=320, color="#C96442"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        "Cada punto representa una tanda. Las subidas reflejan presiones de "
        "precio en insumos clave; las bajadas, condiciones favorables o "
        "renegociacion con proveedores."
    )


def main() -> None:
    hero()
    tab1, tab2, tab3 = st.tabs(["  Optimizar  ", "  Historico  ", "  Analisis  "])
    with tab1:
        tab_optimizar()
    with tab2:
        tab_historico()
    with tab3:
        tab_analisis()


if __name__ == "__main__":
    main()
