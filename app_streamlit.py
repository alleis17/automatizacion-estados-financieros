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

MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

ETIQUETAS = {
    "ventas": "Ventas",
    "costo_ventas": "Costo de ventas",
    "utilidad_bruta": "Utilidad bruta",
    "gastos_administrativos_nomina_financieros": "Gastos administrativos, nomina y financieros",
    "gastos_ventas": "Gastos de ventas",
    "utilidad_antes_impuestos": "Utilidad antes de impuestos",
    "impuesto_renta": "Impuesto de renta",
    "total_gastos": "Total gastos",
    "utilidad_operacional": "Utilidad operacional",
    "utilidad_neta": "Utilidad neta",
    "entradas_efectivo": "Entradas de efectivo",
    "salidas_efectivo": "Salidas de efectivo",
    "flujo_neto": "Flujo neto",
    "saldo_final_bancos": "Saldo final bancos",
    "margen_bruto": "Margen bruto",
    "margen_operacional": "Margen operacional",
    "margen_neto": "Margen neto",
    "razon_corriente": "Razon corriente",
    "endeudamiento": "Endeudamiento",
    "rentabilidad_sobre_activos": "Rentabilidad sobre activos",
    "rentabilidad_sobre_patrimonio": "Rentabilidad sobre patrimonio",
    "pasivo_sobre_patrimonio": "Pasivo / patrimonio",
    "deuda_financiera_sobre_activos": "Deuda financiera / activos",
    "deuda_financiera_sobre_patrimonio": "Deuda financiera / patrimonio",
    "multiplicador_patrimonio": "Multiplicador del patrimonio",
    "cobertura_intereses": "Cobertura de intereses",
}

FILAS_PORCENTAJE = {
    "Margen bruto",
    "Margen operacional",
    "Margen neto",
    "Endeudamiento",
    "Rentabilidad sobre activos",
    "Rentabilidad sobre patrimonio",
    "Deuda financiera / activos",
}

FILAS_VECES = {
    "Razon corriente",
    "Pasivo / patrimonio",
    "Deuda financiera / patrimonio",
    "Multiplicador del patrimonio",
    "Cobertura de intereses",
}


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        max-width: 1240px;
    }
    h1 {
        color: #233142;
        letter-spacing: 0;
    }
    h2, h3 {
        color: #2F3A4A;
    }
    div.stButton > button:first-child {
        border-radius: 8px;
        border: 0;
        background: #D94F45;
        color: #FFFFFF;
        font-weight: 700;
    }
    div.stButton > button:first-child:hover {
        background: #B93F37;
        color: #FFFFFF;
    }
    div[data-testid="stTabs"] button {
        font-weight: 600;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #E5E2DA;
        border-radius: 8px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _numero_es(valor: float, decimales: int = 0) -> str:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return ""

    texto = f"{abs(numero):,.{decimales}f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    if decimales == 0:
        texto = texto.split(",")[0]
    return f"({texto})" if numero < 0 else texto


def formato_moneda(valor: float) -> str:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return ""
    texto = _numero_es(numero, 0)
    return f"$ {texto}" if numero >= 0 else f"$ {texto}"


def formato_porcentaje(valor: float) -> str:
    try:
        return f"{_numero_es(float(valor) * 100, 1)}%"
    except (TypeError, ValueError):
        return ""


def formato_veces(valor: float) -> str:
    try:
        return f"{_numero_es(float(valor), 2)}x"
    except (TypeError, ValueError):
        return ""


def mostrar_meses_en_columnas(df: pd.DataFrame, nombre_fila: str = "rubro") -> pd.DataFrame:
    columnas_excluidas = {"mes_numero"}
    tabla = df.drop(columns=[col for col in columnas_excluidas if col in df.columns]).copy()
    tabla = tabla.set_index("mes").transpose().reset_index()
    tabla = tabla.rename(columns={"index": nombre_fila})
    tabla[nombre_fila] = tabla[nombre_fila].map(ETIQUETAS).fillna(
        tabla[nombre_fila].str.replace("_", " ").str.title()
    )
    return tabla


def formatear_columnas_monetarias(df: pd.DataFrame) -> pd.DataFrame:
    tabla = df.copy()
    columnas_valor = [col for col in df.columns if col in MESES or col == "total_2026"]
    for columna in columnas_valor:
        tabla[columna] = tabla[columna].apply(formato_moneda).astype("string")
    return tabla


def formatear_tabla_por_fila(df: pd.DataFrame, columna_nombre: str) -> pd.DataFrame:
    tabla = df.copy()
    columnas_mes = [col for col in tabla.columns if col in MESES]
    tabla[columnas_mes] = tabla[columnas_mes].astype("object")

    for indice, fila in tabla.iterrows():
        nombre = fila[columna_nombre]
        if nombre in FILAS_PORCENTAJE:
            formato = formato_porcentaje
        elif nombre in FILAS_VECES:
            formato = formato_veces
        else:
            formato = formato_moneda
        for columna in columnas_mes:
            tabla.at[indice, columna] = formato(fila[columna])
    return tabla


st.title("Automatizacion de estados financieros mensuales con Python")

carpeta_default = BASE_DIR / "data" / "2026"
carpeta_texto = st.text_input("Carpeta de archivos mensuales", value=str(carpeta_default))
carpeta_datos = Path(carpeta_texto)

st.subheader("Archivos detectados")
try:
    archivos = buscar_archivos(carpeta_datos)
    st.success(f"Se detectaron {len(archivos)} archivos .xlsx.")
    st.dataframe(pd.DataFrame({"archivo": [archivo.name for archivo in archivos]}), width="stretch")
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
        st.dataframe(alertas, width="stretch")

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
            formatear_columnas_monetarias(resultado["er_detallado_mensual"]),
            width="stretch",
            hide_index=True,
        )

    with tab_balance:
        st.dataframe(
            formatear_columnas_monetarias(resultado["balance_detallado_mensual"]),
            width="stretch",
            hide_index=True,
        )

    with tab_flujo:
        flujo_tabla = mostrar_meses_en_columnas(resultado["flujo_caja_simple"], "concepto")
        st.dataframe(
            formatear_tabla_por_fila(flujo_tabla, "concepto"),
            width="stretch",
            hide_index=True,
        )

    with tab_indicadores:
        indicadores_tabla = mostrar_meses_en_columnas(resultado["indicadores"], "indicador")
        st.dataframe(
            formatear_tabla_por_fila(indicadores_tabla, "indicador"),
            width="stretch",
            hide_index=True,
        )

    with tab_apalancamiento:
        apalancamiento_tabla = mostrar_meses_en_columnas(resultado["ratios_apalancamiento"], "ratio")
        st.dataframe(
            formatear_tabla_por_fila(apalancamiento_tabla, "ratio"),
            width="stretch",
            hide_index=True,
        )

    with tab_graficos:
        estado = resultado["estado_resultados_mensual"]
        balance = resultado["balance_general_mensual"]
        flujo = resultado["flujo_caja_simple"]
        indicadores = resultado["indicadores"]

        fig_ventas = px.bar(estado, x="mes", y="ventas", title="Ventas mensuales")
        st.plotly_chart(fig_ventas, width="stretch")

        fig_utilidad = px.line(estado, x="mes", y="utilidad_neta", markers=True, title="Utilidad neta mensual")
        st.plotly_chart(fig_utilidad, width="stretch")

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
        st.plotly_chart(fig_flujo, width="stretch")

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
        st.plotly_chart(fig_balance, width="stretch")

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
        st.plotly_chart(fig_indicadores, width="stretch")

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
