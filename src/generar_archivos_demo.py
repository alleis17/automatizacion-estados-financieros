from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "2026"

MESES = [
    ("enero", 1),
    ("febrero", 2),
    ("marzo", 3),
    ("abril", 4),
    ("mayo", 5),
    ("junio", 6),
    ("julio", 7),
    ("agosto", 8),
    ("septiembre", 9),
    ("octubre", 10),
    ("noviembre", 11),
    ("diciembre", 12),
]

CUENTAS = {
    "1105": ("Bancos", "Activo"),
    "1305": ("Clientes", "Activo"),
    "1435": ("Inventarios", "Activo"),
    "1520": ("Propiedad y equipo", "Activo"),
    "2205": ("Proveedores", "Pasivo"),
    "2105": ("Obligaciones financieras", "Pasivo"),
    "2408": ("Impuestos por pagar", "Pasivo"),
    "3105": ("Capital social", "Patrimonio"),
    "3605": ("Utilidades acumuladas", "Patrimonio"),
    "4135": ("Ventas de mercancia", "Ingreso"),
    "6135": ("Costo de ventas", "Costo"),
    "5105": ("Gastos administrativos", "Gasto"),
    "5205": ("Gastos de ventas", "Gasto"),
    "5106": ("Pagos de nomina", "Gasto"),
    "5305": ("Gastos financieros", "Gasto"),
    "5405": ("Impuesto de renta", "Gasto"),
}


def _linea(
    fecha: pd.Timestamp,
    comprobante: str,
    descripcion: str,
    cuenta_codigo: str,
    debito: float,
    credito: float,
    tercero: str,
    centro_costo: str,
    mes: str,
) -> dict:
    cuenta_nombre, clase = CUENTAS[cuenta_codigo]
    return {
        "fecha": fecha.date(),
        "comprobante": comprobante,
        "descripcion": descripcion,
        "cuenta_codigo": cuenta_codigo,
        "cuenta_nombre": cuenta_nombre,
        "clase": clase,
        "debito": round(float(debito), 2),
        "credito": round(float(credito), 2),
        "tercero": tercero,
        "centro_costo": centro_costo,
        "mes": mes,
        "anio": 2026,
    }


def _agregar_comprobante(
    registros: list[dict],
    fecha: pd.Timestamp,
    comprobante: str,
    descripcion: str,
    lineas: list[tuple[str, float, float, str, str]],
    mes: str,
) -> None:
    for cuenta_codigo, debito, credito, tercero, centro_costo in lineas:
        registros.append(
            _linea(
                fecha=fecha,
                comprobante=comprobante,
                descripcion=descripcion,
                cuenta_codigo=cuenta_codigo,
                debito=debito,
                credito=credito,
                tercero=tercero,
                centro_costo=centro_costo,
                mes=mes,
            )
        )

    total_debito = sum(linea[1] for linea in lineas)
    total_credito = sum(linea[2] for linea in lineas)
    if round(total_debito - total_credito, 2) != 0:
        raise ValueError(f"El comprobante {comprobante} no esta cuadrado.")


def construir_movimientos_mes(nombre_mes: str, numero_mes: int, rng: np.random.Generator) -> pd.DataFrame:
    registros: list[dict] = []
    prefijo = f"{numero_mes:02d}"
    fecha_inicio = pd.Timestamp(year=2026, month=numero_mes, day=1)

    if numero_mes == 1:
        _agregar_comprobante(
            registros,
            fecha_inicio,
            f"{prefijo}-AP-001",
            "Aporte inicial de socios y utilidades acumuladas",
            [
                ("1105", 300_000_000, 0, "Socios fundadores", "Administracion"),
                ("3105", 0, 250_000_000, "Socios fundadores", "Administracion"),
                ("3605", 0, 50_000_000, "Socios fundadores", "Administracion"),
            ],
            nombre_mes,
        )
        _agregar_comprobante(
            registros,
            fecha_inicio + pd.Timedelta(days=1),
            f"{prefijo}-OB-001",
            "Desembolso de obligacion financiera inicial",
            [
                ("1105", 80_000_000, 0, "Banco Andino", "Administracion"),
                ("2105", 0, 80_000_000, "Banco Andino", "Administracion"),
            ],
            nombre_mes,
        )
        _agregar_comprobante(
            registros,
            fecha_inicio + pd.Timedelta(days=2),
            f"{prefijo}-IN-001",
            "Compra inicial de inventario a credito",
            [
                ("1435", 120_000_000, 0, "Distribuidora Central", "Compras"),
                ("2205", 0, 120_000_000, "Distribuidora Central", "Compras"),
            ],
            nombre_mes,
        )
        _agregar_comprobante(
            registros,
            fecha_inicio + pd.Timedelta(days=3),
            f"{prefijo}-AF-001",
            "Compra de equipo operativo",
            [
                ("1520", 45_000_000, 0, "Equipos Comerciales SAS", "Administracion"),
                ("1105", 0, 45_000_000, "Equipos Comerciales SAS", "Administracion"),
            ],
            nombre_mes,
        )

    estacionalidad = 1 + 0.05 * np.sin((numero_mes - 1) / 12 * 2 * np.pi)
    venta_neta = round((155_000_000 + numero_mes * 3_800_000) * estacionalidad + rng.normal(0, 5_000_000), -3)
    iva = round(venta_neta * 0.19, -3)
    contado = round(venta_neta * rng.uniform(0.35, 0.48), -3)
    credito = venta_neta - contado
    costo_ventas = round(venta_neta * rng.uniform(0.56, 0.62), -3)
    compras = round(costo_ventas * rng.uniform(0.95, 1.12), -3)
    cobros = round(credito * rng.uniform(0.72, 0.88), -3)
    pago_proveedores = round(compras * rng.uniform(0.58, 0.75), -3)
    gastos_admin = round(18_000_000 + numero_mes * 350_000 + rng.normal(0, 650_000), -3)
    gastos_ventas = round(venta_neta * rng.uniform(0.055, 0.075), -3)
    nomina = round(26_000_000 + numero_mes * 450_000 + rng.normal(0, 800_000), -3)
    impuesto_pagado = round(iva * rng.uniform(0.45, 0.65), -3)
    abono_capital = round(4_000_000 + numero_mes * 120_000, -3)
    interes = round(2_100_000 - numero_mes * 55_000, -3)
    utilidad_antes_impuesto = venta_neta - costo_ventas - gastos_admin - gastos_ventas - nomina - interes
    impuesto_renta = round(max(utilidad_antes_impuesto, 0) * 0.35, -3)

    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=5),
        f"{prefijo}-VT-001",
        "Ventas mensuales de mercancia",
        [
            ("1105", contado + iva * contado / venta_neta, 0, "Clientes varios", "Comercial"),
            ("1305", credito + iva * credito / venta_neta, 0, "Clientes credito", "Comercial"),
            ("4135", 0, venta_neta, "Clientes varios", "Comercial"),
            ("2408", 0, iva, "DIAN", "Administracion"),
        ],
        nombre_mes,
    )
    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=6),
        f"{prefijo}-CV-001",
        "Reconocimiento del costo de ventas",
        [
            ("6135", costo_ventas, 0, "Inventario interno", "Comercial"),
            ("1435", 0, costo_ventas, "Inventario interno", "Comercial"),
        ],
        nombre_mes,
    )
    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=9),
        f"{prefijo}-CP-001",
        "Compras de inventario a proveedores",
        [
            ("1435", compras, 0, "Proveedores nacionales", "Compras"),
            ("2205", 0, compras, "Proveedores nacionales", "Compras"),
        ],
        nombre_mes,
    )
    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=13),
        f"{prefijo}-CC-001",
        "Cobros de cartera de clientes",
        [
            ("1105", cobros, 0, "Clientes credito", "Tesoreria"),
            ("1305", 0, cobros, "Clientes credito", "Tesoreria"),
        ],
        nombre_mes,
    )
    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=17),
        f"{prefijo}-PP-001",
        "Pagos a proveedores",
        [
            ("2205", pago_proveedores, 0, "Proveedores nacionales", "Tesoreria"),
            ("1105", 0, pago_proveedores, "Proveedores nacionales", "Tesoreria"),
        ],
        nombre_mes,
    )
    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=20),
        f"{prefijo}-GA-001",
        "Gastos administrativos del mes",
        [
            ("5105", gastos_admin, 0, "Servicios administrativos", "Administracion"),
            ("1105", 0, gastos_admin, "Servicios administrativos", "Administracion"),
        ],
        nombre_mes,
    )
    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=21),
        f"{prefijo}-GV-001",
        "Gastos de ventas y mercadeo",
        [
            ("5205", gastos_ventas, 0, "Agencia comercial", "Comercial"),
            ("1105", 0, gastos_ventas, "Agencia comercial", "Comercial"),
        ],
        nombre_mes,
    )
    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=25),
        f"{prefijo}-NO-001",
        "Pagos de nomina",
        [
            ("5106", nomina, 0, "Empleados", "Administracion"),
            ("1105", 0, nomina, "Empleados", "Administracion"),
        ],
        nombre_mes,
    )
    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=26),
        f"{prefijo}-IM-001",
        "Pago parcial de impuestos por pagar",
        [
            ("2408", impuesto_pagado, 0, "DIAN", "Tesoreria"),
            ("1105", 0, impuesto_pagado, "DIAN", "Tesoreria"),
        ],
        nombre_mes,
    )
    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=28),
        f"{prefijo}-OF-001",
        "Pago de obligacion financiera e intereses",
        [
            ("2105", abono_capital, 0, "Banco Andino", "Tesoreria"),
            ("5305", interes, 0, "Banco Andino", "Administracion"),
            ("1105", 0, abono_capital + interes, "Banco Andino", "Tesoreria"),
        ],
        nombre_mes,
    )
    _agregar_comprobante(
        registros,
        fecha_inicio + pd.Timedelta(days=29),
        f"{prefijo}-IR-001",
        "Causacion de impuesto de renta estimado",
        [
            ("5405", impuesto_renta, 0, "DIAN", "Administracion"),
            ("2408", 0, impuesto_renta, "DIAN", "Administracion"),
        ],
        nombre_mes,
    )

    df = pd.DataFrame(registros)
    columnas = [
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
    return df[columnas]


def generar_archivos_demo(data_dir: Path = DATA_DIR) -> list[Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)
    archivos: list[Path] = []

    for nombre_mes, numero_mes in MESES:
        df = construir_movimientos_mes(nombre_mes, numero_mes, rng)
        ruta = data_dir / f"{nombre_mes}-26.xlsx"
        with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Movimientos", index=False)
        archivos.append(ruta)

    return archivos


if __name__ == "__main__":
    rutas = generar_archivos_demo()
    print(f"Archivos generados: {len(rutas)}")
    for ruta in rutas:
        print(f"- {ruta}")
