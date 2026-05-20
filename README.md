# Automatizacion de estados financieros mensuales con Python

Producto piloto para una ponencia sobre automatizacion aplicada a la solucion de problemas financieros. El proyecto genera 12 archivos mensuales de movimientos contables demo para una empresa comercial y luego los procesa automaticamente para construir estados financieros de 2026.

## Objetivo

Automatizar un flujo contable mensual completo:

1. Generar archivos Excel mensuales con movimientos en partida doble.
2. Validar estructura, nombres, columnas y cuadre de comprobantes.
3. Consolidar movimientos.
4. Construir estado de resultados, balance general, flujo de caja e indicadores.
5. Exportar salidas en Excel, graficos PNG y dashboard Streamlit.
6. Ampliar el analisis con detalle por cuenta y ratios de apalancamiento.

## Estructura

```text
automatizacion_estados_financieros/
  data/
    2026/
  salidas/
    graficos/
  src/
    generar_archivos_demo.py
    procesar_estados_financieros.py
  app_streamlit.py
  requirements.txt
  README.md
```

## Instalacion

Desde la carpeta del proyecto:

```bash
pip install -r requirements.txt
```

## Generar archivos de prueba

```bash
python src/generar_archivos_demo.py
```

Esto crea 12 archivos en `data/2026/`, desde `enero-26.xlsx` hasta `diciembre-26.xlsx`. Cada archivo contiene la hoja `Movimientos` con columnas obligatorias, clases contables validas y comprobantes cuadrados.

## Procesar estados financieros

```bash
python src/procesar_estados_financieros.py
```

El procesamiento realiza:

- busqueda automatica de archivos `.xlsx` en `data/2026/`;
- validacion del formato `mes-26.xlsx`;
- lectura de la hoja `Movimientos`;
- validacion de columnas obligatorias;
- validacion de partida doble por comprobante;
- consolidacion de movimientos;
- calculo de estado de resultados mensual y acumulado;
- calculo de balance general mensual;
- calculo de flujo de caja simple;
- calculo de indicadores financieros;
- calculo de ratios de apalancamiento;
- impuesto de renta estimado al 35%;
- validacion de la ecuacion `Activo = Pasivo + Patrimonio + Resultado acumulado del ejercicio`.

## Salidas

El sistema genera:

```text
salidas/estados_financieros_2026.xlsx
salidas/archivos_procesados.csv
salidas/graficos/ventas_mensuales.png
salidas/graficos/utilidad_neta_mensual.png
salidas/graficos/activos_pasivos_patrimonio.png
salidas/graficos/indicadores_financieros.png
```

El Excel final contiene estas hojas:

- `movimientos_consolidados`
- `estado_resultados_mensual`
- `estado_resultados_acumulado`
- `er_detallado_mensual`
- `balance_general_mensual`
- `balance_detallado_mensual`
- `flujo_caja_simple`
- `indicadores`
- `ratios_apalancamiento`
- `validaciones`

## Dashboard

```bash
streamlit run app_streamlit.py
```

La app permite seleccionar la carpeta de datos, ver archivos detectados, procesar movimientos, revisar estados financieros detallados por cuenta, consultar flujo de caja, indicadores, ratios de apalancamiento, visualizar graficos interactivos y descargar el Excel generado.

## Deteccion de archivos nuevos

Cada procesamiento actualiza `salidas/archivos_procesados.csv` con:

- `nombre_archivo`
- `fecha_procesamiento`
- `numero_registros`
- `total_debitos`
- `total_creditos`

Si se agrega un nuevo archivo mensual a `data/2026/`, el sistema lo detecta al comparar los archivos actuales contra la bitacora existente y lo incluye en el procesamiento.

## Flujo de automatizacion

El flujo simula una rutina mensual de cierre:

1. Contabilidad entrega archivos mensuales con movimientos.
2. Python revisa que los archivos tengan el nombre y estructura esperados.
3. El sistema valida que cada comprobante este cuadrado.
4. Los movimientos se consolidan en una sola base.
5. Se generan estados financieros e indicadores.
6. Se exportan resultados para Excel, graficos y dashboard.
7. La bitacora permite saber que archivos fueron procesados y detectar incorporaciones nuevas.
