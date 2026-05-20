from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "2026"
SALIDAS_DIR = BASE_DIR / "salidas"
GRAFICOS_DIR = SALIDAS_DIR / "graficos"
EXCEL_SALIDA = SALIDAS_DIR / "estados_financieros_2026.xlsx"
BITACORA_ARCHIVOS = SALIDAS_DIR / "archivos_procesados.csv"

MESES_ORDEN = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

COLUMNAS_OBLIGATORIAS = [
    "fecha",
    "comprobante",
    "descripcion",
    "cuenta_codigo",
    "cuenta_nombre",
    "clase",
    "debito",
    "credito",
    "tercero",
    "centro_costo",
    "mes",
    "anio",
]

CLASES_VALIDAS = {"Activo", "Pasivo", "Patrimonio", "Ingreso", "Costo", "Gasto"}
PATRON_ARCHIVO = re.compile(
    r"^(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)-26\.xlsx$",
    re.IGNORECASE,
)


def validar_nombre_archivo(ruta: Path) -> str:
    nombre = ruta.name.lower()
    if not PATRON_ARCHIVO.match(nombre):
        raise ValueError(f"Nombre de archivo invalido: {ruta.name}. Debe tener formato mes-26.xlsx.")
    return nombre.split("-")[0]


def buscar_archivos(data_dir: Path = DATA_DIR) -> list[Path]:
    if not data_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de datos: {data_dir}")
    archivos = sorted(
        data_dir.glob("*.xlsx"),
        key=lambda ruta: MESES_ORDEN.get(ruta.name.lower().split("-")[0], 99),
    )
    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos .xlsx en {data_dir}")
    return archivos


def leer_y_validar_archivo(ruta: Path) -> pd.DataFrame:
    mes_nombre = validar_nombre_archivo(ruta)
    try:
        df = pd.read_excel(ruta, sheet_name="Movimientos", engine="openpyxl")
    except ValueError as exc:
        raise ValueError(f"{ruta.name}: no existe la hoja obligatoria 'Movimientos'.") from exc

    faltantes = [col for col in COLUMNAS_OBLIGATORIAS if col not in df.columns]
    if faltantes:
        raise ValueError(f"{ruta.name}: faltan columnas obligatorias: {', '.join(faltantes)}")

    df = df[COLUMNAS_OBLIGATORIAS].copy()
    df["archivo_origen"] = ruta.name
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["debito"] = pd.to_numeric(df["debito"], errors="coerce").fillna(0.0)
    df["credito"] = pd.to_numeric(df["credito"], errors="coerce").fillna(0.0)
    df["cuenta_codigo"] = df["cuenta_codigo"].astype(str)
    df["mes"] = df["mes"].astype(str).str.lower()
    df["mes_numero"] = df["mes"].map(MESES_ORDEN)

    if df["mes_numero"].isna().any():
        raise ValueError(f"{ruta.name}: contiene meses no reconocidos.")
    if not (df["mes"] == mes_nombre).all():
        raise ValueError(f"{ruta.name}: el valor de la columna mes no coincide con el nombre del archivo.")
    if not (df["anio"] == 2026).all():
        raise ValueError(f"{ruta.name}: la columna anio debe ser 2026 en todos los registros.")

    clases_invalidas = sorted(set(df["clase"].dropna()) - CLASES_VALIDAS)
    if clases_invalidas:
        raise ValueError(f"{ruta.name}: clases contables invalidas: {', '.join(clases_invalidas)}")

    validar_comprobantes_cuadrados(df, ruta.name)
    return df


def validar_comprobantes_cuadrados(df: pd.DataFrame, nombre_archivo: str = "movimientos") -> None:
    cuadre = (
        df.groupby("comprobante", as_index=False)[["debito", "credito"]]
        .sum()
        .assign(diferencia=lambda x: (x["debito"] - x["credito"]).round(2))
    )
    descuadrados = cuadre[cuadre["diferencia"].abs() > 0.01]
    if not descuadrados.empty:
        detalle = descuadrados[["comprobante", "debito", "credito", "diferencia"]].to_dict("records")
        raise ValueError(f"{nombre_archivo}: comprobantes descuadrados: {detalle}")


def consolidar_movimientos(archivos: list[Path]) -> pd.DataFrame:
    dataframes = [leer_y_validar_archivo(ruta) for ruta in archivos]
    movimientos = pd.concat(dataframes, ignore_index=True)
    movimientos = movimientos.sort_values(["mes_numero", "fecha", "comprobante", "cuenta_codigo"])
    validar_comprobantes_cuadrados(movimientos, "consolidado")
    return movimientos


def _serie_clase(movimientos: pd.DataFrame, clase: str, naturaleza: str = "debito") -> pd.Series:
    df = movimientos[movimientos["clase"] == clase]
    if naturaleza == "credito":
        valores = df["credito"] - df["debito"]
    else:
        valores = df["debito"] - df["credito"]
    return valores.groupby(df["mes_numero"]).sum()


def construir_estado_resultados_mensual(movimientos: pd.DataFrame) -> pd.DataFrame:
    meses = pd.Index(range(1, 13), name="mes_numero")
    ventas = _serie_clase(movimientos, "Ingreso", "credito").reindex(meses, fill_value=0)
    costo = _serie_clase(movimientos, "Costo", "debito").reindex(meses, fill_value=0)
    gastos = _serie_clase(movimientos, "Gasto", "debito").reindex(meses, fill_value=0)

    gastos_admin = movimientos[
        (movimientos["clase"] == "Gasto") & (movimientos["cuenta_codigo"].isin(["5105", "5106", "5305"]))
    ]
    gastos_ventas = movimientos[(movimientos["clase"] == "Gasto") & (movimientos["cuenta_codigo"] == "5205")]
    impuesto_renta = movimientos[(movimientos["clase"] == "Gasto") & (movimientos["cuenta_codigo"] == "5405")]
    admin = (gastos_admin["debito"] - gastos_admin["credito"]).groupby(gastos_admin["mes_numero"]).sum()
    ventas_gasto = (gastos_ventas["debito"] - gastos_ventas["credito"]).groupby(gastos_ventas["mes_numero"]).sum()
    impuesto = (impuesto_renta["debito"] - impuesto_renta["credito"]).groupby(impuesto_renta["mes_numero"]).sum()
    utilidad_antes_impuesto = ventas - costo - admin.reindex(meses, fill_value=0) - ventas_gasto.reindex(meses, fill_value=0)

    estado = pd.DataFrame(
        {
            "ventas": ventas,
            "costo_ventas": costo,
            "utilidad_bruta": ventas - costo,
            "gastos_administrativos_nomina_financieros": admin.reindex(meses, fill_value=0),
            "gastos_ventas": ventas_gasto.reindex(meses, fill_value=0),
            "utilidad_antes_impuestos": utilidad_antes_impuesto,
            "impuesto_renta": impuesto.reindex(meses, fill_value=0),
            "total_gastos": gastos,
            "utilidad_operacional": utilidad_antes_impuesto,
        }
    )
    estado["utilidad_neta"] = estado["ventas"] - estado["costo_ventas"] - estado["total_gastos"]
    estado = estado.reset_index()
    estado["mes"] = estado["mes_numero"].map({v: k for k, v in MESES_ORDEN.items()})
    return estado[["mes", "mes_numero", *[c for c in estado.columns if c not in {"mes", "mes_numero"}]]]


def construir_estado_resultados_acumulado(estado_mensual: pd.DataFrame) -> pd.DataFrame:
    columnas_valor = [
        col
        for col in estado_mensual.columns
        if col not in {"mes", "mes_numero"} and pd.api.types.is_numeric_dtype(estado_mensual[col])
    ]
    acumulado = estado_mensual[["mes", "mes_numero"]].copy()
    acumulado[columnas_valor] = estado_mensual[columnas_valor].cumsum()
    return acumulado


def construir_estado_resultados_detallado(movimientos: pd.DataFrame) -> pd.DataFrame:
    detalle = movimientos[movimientos["clase"].isin(["Ingreso", "Costo", "Gasto"])].copy()
    detalle["valor"] = detalle.apply(
        lambda fila: fila["credito"] - fila["debito"] if fila["clase"] == "Ingreso" else fila["debito"] - fila["credito"],
        axis=1,
    )
    tabla = (
        detalle.pivot_table(
            index=["clase", "cuenta_codigo", "cuenta_nombre"],
            columns="mes",
            values="valor",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(columns=MESES_ORDEN.keys(), fill_value=0)
        .reset_index()
    )
    tabla["total_2026"] = tabla[list(MESES_ORDEN.keys())].sum(axis=1)
    orden_clase = {"Ingreso": 1, "Costo": 2, "Gasto": 3}
    tabla["orden"] = tabla["clase"].map(orden_clase)
    tabla = tabla.sort_values(["orden", "cuenta_codigo"]).drop(columns="orden")
    return tabla


def construir_balance_general_mensual(movimientos: pd.DataFrame, resultado_acumulado: pd.Series) -> pd.DataFrame:
    filas = []
    for mes_numero in range(1, 13):
        corte = movimientos[movimientos["mes_numero"] <= mes_numero]
        activo = (corte.loc[corte["clase"] == "Activo", "debito"] - corte.loc[corte["clase"] == "Activo", "credito"]).sum()
        pasivo = (corte.loc[corte["clase"] == "Pasivo", "credito"] - corte.loc[corte["clase"] == "Pasivo", "debito"]).sum()
        patrimonio = (
            corte.loc[corte["clase"] == "Patrimonio", "credito"] - corte.loc[corte["clase"] == "Patrimonio", "debito"]
        ).sum()
        resultado = float(resultado_acumulado.get(mes_numero, 0.0))
        diferencia = activo - (pasivo + patrimonio + resultado)
        filas.append(
            {
                "mes": {v: k for k, v in MESES_ORDEN.items()}[mes_numero],
                "mes_numero": mes_numero,
                "activo": activo,
                "pasivo": pasivo,
                "patrimonio": patrimonio,
                "resultado_acumulado_ejercicio": resultado,
                "diferencia": diferencia,
            }
        )
    return pd.DataFrame(filas)


def construir_balance_detallado_mensual(movimientos: pd.DataFrame, resultado_acumulado: pd.Series) -> pd.DataFrame:
    cuentas_balance = movimientos[movimientos["clase"].isin(["Activo", "Pasivo", "Patrimonio"])]
    cuentas = (
        cuentas_balance[["clase", "cuenta_codigo", "cuenta_nombre"]]
        .drop_duplicates()
        .sort_values(["clase", "cuenta_codigo"])
    )

    filas = []
    for _, cuenta in cuentas.iterrows():
        fila = {
            "clase": cuenta["clase"],
            "cuenta_codigo": cuenta["cuenta_codigo"],
            "cuenta_nombre": cuenta["cuenta_nombre"],
        }
        movimientos_cuenta = cuentas_balance[cuentas_balance["cuenta_codigo"] == cuenta["cuenta_codigo"]]
        for mes_nombre, mes_numero in MESES_ORDEN.items():
            corte = movimientos_cuenta[movimientos_cuenta["mes_numero"] <= mes_numero]
            if cuenta["clase"] == "Activo":
                valor = (corte["debito"] - corte["credito"]).sum()
            else:
                valor = (corte["credito"] - corte["debito"]).sum()
            fila[mes_nombre] = valor
        filas.append(fila)

    resultado = {
        "clase": "Patrimonio",
        "cuenta_codigo": "3705",
        "cuenta_nombre": "Resultado acumulado del ejercicio",
    }
    for mes_nombre, mes_numero in MESES_ORDEN.items():
        resultado[mes_nombre] = float(resultado_acumulado.get(mes_numero, 0.0))
    filas.append(resultado)

    tabla = pd.DataFrame(filas)
    orden_clase = {"Activo": 1, "Pasivo": 2, "Patrimonio": 3}
    tabla["orden"] = tabla["clase"].map(orden_clase)
    tabla = tabla.sort_values(["orden", "cuenta_codigo"]).drop(columns="orden")
    return tabla


def construir_flujo_caja_simple(movimientos: pd.DataFrame) -> pd.DataFrame:
    banco = movimientos[movimientos["cuenta_codigo"] == "1105"].copy()
    flujo = banco.groupby("mes_numero")[["debito", "credito"]].sum().reindex(range(1, 13), fill_value=0)
    flujo = flujo.rename(columns={"debito": "entradas_efectivo", "credito": "salidas_efectivo"})
    flujo["flujo_neto"] = flujo["entradas_efectivo"] - flujo["salidas_efectivo"]
    flujo["saldo_final_bancos"] = flujo["flujo_neto"].cumsum()
    flujo = flujo.reset_index()
    flujo["mes"] = flujo["mes_numero"].map({v: k for k, v in MESES_ORDEN.items()})
    return flujo[["mes", "mes_numero", "entradas_efectivo", "salidas_efectivo", "flujo_neto", "saldo_final_bancos"]]


def construir_indicadores(estado: pd.DataFrame, balance: pd.DataFrame) -> pd.DataFrame:
    df = estado.merge(balance, on=["mes", "mes_numero"], how="left")
    indicadores = pd.DataFrame({"mes": df["mes"], "mes_numero": df["mes_numero"]})
    indicadores["margen_bruto"] = df["utilidad_bruta"] / df["ventas"]
    indicadores["margen_operacional"] = df["utilidad_operacional"] / df["ventas"]
    indicadores["margen_neto"] = df["utilidad_neta"] / df["ventas"]
    indicadores["razon_corriente"] = df["activo"] / df["pasivo"].replace(0, pd.NA)
    indicadores["endeudamiento"] = df["pasivo"] / df["activo"].replace(0, pd.NA)
    indicadores["rentabilidad_sobre_activos"] = df["utilidad_neta"] / df["activo"].replace(0, pd.NA)
    indicadores["rentabilidad_sobre_patrimonio"] = df["utilidad_neta"] / df["patrimonio"].replace(0, pd.NA)
    return indicadores.fillna(0)


def construir_ratios_apalancamiento(
    movimientos: pd.DataFrame,
    estado: pd.DataFrame,
    balance: pd.DataFrame,
) -> pd.DataFrame:
    obligaciones = movimientos[movimientos["cuenta_codigo"] == "2105"].copy()
    intereses = movimientos[movimientos["cuenta_codigo"] == "5305"].copy()
    filas = []

    for _, fila_balance in balance.iterrows():
        mes_numero = int(fila_balance["mes_numero"])
        corte_obligaciones = obligaciones[obligaciones["mes_numero"] <= mes_numero]
        deuda_financiera = (corte_obligaciones["credito"] - corte_obligaciones["debito"]).sum()
        gasto_intereses = (
            intereses.loc[intereses["mes_numero"] == mes_numero, "debito"]
            - intereses.loc[intereses["mes_numero"] == mes_numero, "credito"]
        ).sum()
        fila_estado = estado.loc[estado["mes_numero"] == mes_numero].iloc[0]
        patrimonio_total = fila_balance["patrimonio"] + fila_balance["resultado_acumulado_ejercicio"]

        filas.append(
            {
                "mes": fila_balance["mes"],
                "mes_numero": mes_numero,
                "pasivo_sobre_patrimonio": fila_balance["pasivo"] / patrimonio_total if patrimonio_total else 0,
                "deuda_financiera_sobre_activos": deuda_financiera / fila_balance["activo"] if fila_balance["activo"] else 0,
                "deuda_financiera_sobre_patrimonio": deuda_financiera / patrimonio_total if patrimonio_total else 0,
                "multiplicador_patrimonio": fila_balance["activo"] / patrimonio_total if patrimonio_total else 0,
                "cobertura_intereses": fila_estado["utilidad_operacional"] / gasto_intereses if gasto_intereses else 0,
            }
        )

    return pd.DataFrame(filas).fillna(0)


def validar_balance(balance: pd.DataFrame) -> pd.DataFrame:
    validaciones = balance[
        ["mes", "activo", "pasivo", "patrimonio", "resultado_acumulado_ejercicio", "diferencia"]
    ].copy()
    validaciones["estado"] = validaciones["diferencia"].abs().apply(lambda valor: "OK" if valor <= 0.01 else "ALERTA")
    validaciones["mensaje"] = validaciones.apply(
        lambda fila: "Balance cuadrado"
        if fila["estado"] == "OK"
        else (
            f"ALERTA {fila['mes']}: Activo={fila['activo']:.2f}; Pasivo={fila['pasivo']:.2f}; "
            f"Patrimonio={fila['patrimonio']:.2f}; Resultado acumulado={fila['resultado_acumulado_ejercicio']:.2f}; "
            f"Diferencia={fila['diferencia']:.2f}"
        ),
        axis=1,
    )
    return validaciones


def actualizar_bitacora(movimientos: pd.DataFrame, salida: Path = BITACORA_ARCHIVOS) -> tuple[pd.DataFrame, list[str]]:
    salida.parent.mkdir(parents=True, exist_ok=True)
    nombres_previos: set[str] = set()
    if salida.exists():
        anterior = pd.read_csv(salida)
        if "nombre_archivo" in anterior.columns:
            nombres_previos = set(anterior["nombre_archivo"].astype(str))

    resumen = (
        movimientos.groupby("archivo_origen")
        .agg(numero_registros=("comprobante", "size"), total_debitos=("debito", "sum"), total_creditos=("credito", "sum"))
        .reset_index()
        .rename(columns={"archivo_origen": "nombre_archivo"})
    )
    resumen["fecha_procesamiento"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    resumen = resumen[["nombre_archivo", "fecha_procesamiento", "numero_registros", "total_debitos", "total_creditos"]]
    resumen.to_csv(salida, index=False, encoding="utf-8")
    nuevos = sorted(set(resumen["nombre_archivo"]) - nombres_previos)
    return resumen, nuevos


def guardar_excel(resultados: dict[str, pd.DataFrame], ruta: Path = EXCEL_SALIDA) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        for hoja, df in resultados.items():
            df.to_excel(writer, sheet_name=hoja, index=False)
    return ruta


def _guardar_figura(fig: go.Figure, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.write_image(str(ruta), width=1200, height=720, scale=2)
    except Exception as exc:
        raise RuntimeError(
            f"No fue posible generar {ruta.name}. Plotly requiere kaleido para exportar PNG. "
            "Instala dependencias con: pip install -r requirements.txt"
        ) from exc


def generar_graficos(estado: pd.DataFrame, balance: pd.DataFrame, indicadores: pd.DataFrame) -> list[Path]:
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)
    rutas = [
        GRAFICOS_DIR / "ventas_mensuales.png",
        GRAFICOS_DIR / "utilidad_neta_mensual.png",
        GRAFICOS_DIR / "activos_pasivos_patrimonio.png",
        GRAFICOS_DIR / "indicadores_financieros.png",
    ]

    fig_ventas = go.Figure(data=[go.Bar(x=estado["mes"], y=estado["ventas"], marker_color="#1f77b4")])
    fig_ventas.update_layout(title="Ventas mensuales 2026", xaxis_title="Mes", yaxis_title="Ventas")

    fig_utilidad = go.Figure(data=[go.Scatter(x=estado["mes"], y=estado["utilidad_neta"], mode="lines+markers")])
    fig_utilidad.update_layout(title="Utilidad neta mensual 2026", xaxis_title="Mes", yaxis_title="Utilidad neta")

    fig_balance = go.Figure()
    fig_balance.add_trace(go.Scatter(x=balance["mes"], y=balance["activo"], mode="lines+markers", name="Activo"))
    fig_balance.add_trace(go.Scatter(x=balance["mes"], y=balance["pasivo"], mode="lines+markers", name="Pasivo"))
    fig_balance.add_trace(go.Scatter(x=balance["mes"], y=balance["patrimonio"], mode="lines+markers", name="Patrimonio"))
    fig_balance.update_layout(title="Activo, pasivo y patrimonio", xaxis_title="Mes", yaxis_title="Valor")

    fig_ind = go.Figure()
    for columna in ["margen_bruto", "margen_operacional", "margen_neto", "endeudamiento"]:
        fig_ind.add_trace(go.Scatter(x=indicadores["mes"], y=indicadores[columna], mode="lines+markers", name=columna))
    fig_ind.update_layout(title="Indicadores financieros", xaxis_title="Mes", yaxis_title="Indicador")

    for fig, ruta in zip([fig_ventas, fig_utilidad, fig_balance, fig_ind], rutas):
        _guardar_figura(fig, ruta)
    return rutas


def procesar_estados_financieros(
    data_dir: Path | str = DATA_DIR,
    salidas_dir: Path | str = SALIDAS_DIR,
    exportar_png: bool = True,
) -> dict:
    global SALIDAS_DIR, GRAFICOS_DIR, EXCEL_SALIDA, BITACORA_ARCHIVOS

    data_dir = Path(data_dir)
    SALIDAS_DIR = Path(salidas_dir)
    GRAFICOS_DIR = SALIDAS_DIR / "graficos"
    EXCEL_SALIDA = SALIDAS_DIR / "estados_financieros_2026.xlsx"
    BITACORA_ARCHIVOS = SALIDAS_DIR / "archivos_procesados.csv"

    archivos = buscar_archivos(data_dir)
    movimientos = consolidar_movimientos(archivos)
    estado_mensual = construir_estado_resultados_mensual(movimientos)
    estado_acumulado = construir_estado_resultados_acumulado(estado_mensual)
    resultado_acumulado = estado_mensual.set_index("mes_numero")["utilidad_neta"].cumsum()
    balance = construir_balance_general_mensual(movimientos, resultado_acumulado)
    estado_detallado = construir_estado_resultados_detallado(movimientos)
    balance_detallado = construir_balance_detallado_mensual(movimientos, resultado_acumulado)
    flujo_caja = construir_flujo_caja_simple(movimientos)
    indicadores = construir_indicadores(estado_mensual, balance)
    ratios_apalancamiento = construir_ratios_apalancamiento(movimientos, estado_mensual, balance)
    validaciones = validar_balance(balance)

    resultados = {
        "movimientos_consolidados": movimientos,
        "estado_resultados_mensual": estado_mensual,
        "estado_resultados_acumulado": estado_acumulado,
        "er_detallado_mensual": estado_detallado,
        "balance_general_mensual": balance,
        "balance_detallado_mensual": balance_detallado,
        "flujo_caja_simple": flujo_caja,
        "indicadores": indicadores,
        "ratios_apalancamiento": ratios_apalancamiento,
        "validaciones": validaciones,
    }
    excel = guardar_excel(resultados, EXCEL_SALIDA)
    graficos = generar_graficos(estado_mensual, balance, indicadores) if exportar_png else []
    bitacora, archivos_nuevos = actualizar_bitacora(movimientos, BITACORA_ARCHIVOS)

    return {
        "archivos_detectados": [ruta.name for ruta in archivos],
        "archivos_nuevos": archivos_nuevos,
        "movimientos": movimientos,
        "estado_resultados_mensual": estado_mensual,
        "estado_resultados_acumulado": estado_acumulado,
        "er_detallado_mensual": estado_detallado,
        "balance_general_mensual": balance,
        "balance_detallado_mensual": balance_detallado,
        "flujo_caja_simple": flujo_caja,
        "indicadores": indicadores,
        "ratios_apalancamiento": ratios_apalancamiento,
        "validaciones": validaciones,
        "bitacora": bitacora,
        "excel_salida": excel,
        "graficos": graficos,
    }


if __name__ == "__main__":
    resultado = procesar_estados_financieros()
    print("Procesamiento completado.")
    print(f"Archivos detectados: {len(resultado['archivos_detectados'])}")
    print(f"Archivos nuevos segun bitacora: {len(resultado['archivos_nuevos'])}")
    print(f"Movimientos consolidados: {len(resultado['movimientos'])}")
    print(f"Validaciones OK: {(resultado['validaciones']['estado'] == 'OK').sum()} de {len(resultado['validaciones'])}")
    print(f"Excel generado: {resultado['excel_salida']}")
    print("Graficos generados:")
    for ruta in resultado["graficos"]:
        print(f"- {ruta}")
