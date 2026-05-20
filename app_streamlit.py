from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from procesar_estados_financieros import buscar_archivos, procesar_estados_financieros


st.set_page_config(page_title="Automatizacion de estados financieros", layout="wide")


def mostrar_meses_en_columnas(df: pd.DataFrame, nombre_fila: str = "rubro") -> pd.DataFrame:
    columnas_excluidas = {"mes_numero"}
    tabla = df.drop(columns=[col for col in columnas_excluidas if col in df.columns]).copy()
    tabla = tabla.set_index("mes").transpose().reset_index()
    tabla = tabla.rename(columns={"index": nombre_fila})
    tabla[nombre_fila] = tabla[nombre_fila].str.replace("_", " ").str.title()
    return tabla


st.title("Automatizacion de estados financieros mensuales con Python")

carpeta_default = BASE_DIR / "data" / "2026"
carpeta_texto = st.text_input("Carpeta de archivos mensuales", value=str(carpeta_default))
carpeta_datos = Path(carpeta_texto)

st.subheader("Archivos detectados")
try:
    archivos = buscar_archivos(carpeta_datos)
    st.success(f"Se detectaron {len(archivos)} archivos .xlsx.")
    st.dataframe(pd.DataFrame({"archivo": [archivo.name for archivo in archivos]}), use_container_width=True)
except Exception as exc:
    archivos = []
    st.warning(str(exc))

if st.button("Procesar archivos", type="primary", disabled=not archivos):
    with st.spinner("Procesando movimientos, estados financieros y validaciones..."):
        try:
            st.session_state["resultado"] = procesar_estados_financieros(
                carpeta_datos,
                BASE_DIR / "salidas",
                exportar_png=False,
            )
            st.success("Procesamiento completado.")
        except Exception as exc:
            st.error(str(exc))

resultado = st.session_state.get("resultado")

if resultado:
    validaciones = resultado["validaciones"]
    alertas = validaciones[validaciones["estado"] != "OK"]
    if alertas.empty:
        st.success("Validacion contable superada: todos los balances mensuales cuadran.")
    else:
        st.error("Hay meses descuadrados en la validacion contable.")
        st.dataframe(alertas, use_container_width=True)

    tab_er, tab_balance, tab_flujo, tab_indicadores, tab_apalancamiento, tab_graficos, tab_descarga = st.tabs(
        [
            "Estado de resultados",
            "Balance general",
            "Flujo de caja",
            "Indicadores",
            "Apalancamiento",
            "Graficos",
            "Descarga",
        ]
    )

    with tab_er:
        st.dataframe(
            resultado["er_detallado_mensual"],
            use_container_width=True,
        )

    with tab_balance:
        st.dataframe(
            resultado["balance_detallado_mensual"],
            use_container_width=True,
        )

    with tab_flujo:
        st.dataframe(
            mostrar_meses_en_columnas(resultado["flujo_caja_simple"], "concepto"),
            use_container_width=True,
        )

    with tab_indicadores:
        st.dataframe(
            mostrar_meses_en_columnas(resultado["indicadores"], "indicador"),
            use_container_width=True,
        )

    with tab_apalancamiento:
        st.dataframe(
            mostrar_meses_en_columnas(resultado["ratios_apalancamiento"], "ratio"),
            use_container_width=True,
        )

    with tab_graficos:
        estado = resultado["estado_resultados_mensual"]
        balance = resultado["balance_general_mensual"]
        flujo = resultado["flujo_caja_simple"]
        indicadores = resultado["indicadores"]

        fig_ventas = px.bar(estado, x="mes", y="ventas", title="Ventas mensuales")
        st.plotly_chart(fig_ventas, use_container_width=True)

        fig_utilidad = px.line(estado, x="mes", y="utilidad_neta", markers=True, title="Utilidad neta mensual")
        st.plotly_chart(fig_utilidad, use_container_width=True)

        flujo_largo = flujo.melt(
            id_vars=["mes", "mes_numero"],
            value_vars=["entradas_efectivo", "salidas_efectivo", "flujo_neto", "saldo_final_bancos"],
            var_name="concepto",
            value_name="valor",
        )
        fig_flujo = px.line(
            flujo_largo,
            x="mes",
            y="valor",
            color="concepto",
            markers=True,
            title="Flujo de caja simple",
        )
        st.plotly_chart(fig_flujo, use_container_width=True)

        balance_largo = balance.melt(
            id_vars=["mes", "mes_numero"],
            value_vars=["activo", "pasivo", "patrimonio"],
            var_name="rubro",
            value_name="valor",
        )
        fig_balance = px.line(
            balance_largo,
            x="mes",
            y="valor",
            color="rubro",
            markers=True,
            title="Activo, pasivo y patrimonio",
        )
        st.plotly_chart(fig_balance, use_container_width=True)

        indicadores_largo = indicadores.melt(
            id_vars=["mes", "mes_numero"],
            value_vars=["margen_bruto", "margen_operacional", "margen_neto", "endeudamiento"],
            var_name="indicador",
            value_name="valor",
        )
        fig_indicadores = px.line(
            indicadores_largo,
            x="mes",
            y="valor",
            color="indicador",
            markers=True,
            title="Indicadores financieros",
        )
        st.plotly_chart(fig_indicadores, use_container_width=True)

    with tab_descarga:
        excel = Path(resultado["excel_salida"])
        st.write(f"Archivo generado: {excel}")
        with excel.open("rb") as archivo:
            st.download_button(
                "Descargar estados_financieros_2026.xlsx",
                data=archivo,
                file_name="estados_financieros_2026.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
