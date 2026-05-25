# App local en Streamlit

## Objetivo

Esta app permite explorar desde el navegador los marts analíticos de precios diarios SEPA ya generados en DuckDB. Está pensada como dashboard local de portfolio, no como aplicación final de producción.

La app consulta solamente tablas `mart_*` y evita leer directamente `fact_precios`.

## Dependencias

Instalar las dependencias del proyecto:

```bash
python -m pip install -r requirements.txt
```

La app usa:

- `streamlit`
- `duckdb`
- `pandas`
- `plotly`

## Base DuckDB y marts requeridos

La app espera encontrar la base local en:

```text
data/processed/precios_diarios.duckdb
```

También requiere que existan estos marts:

- `mart_resumen_general`
- `mart_evolucion_productos`
- `mart_variacion_productos`
- `mart_resumen_productos`
- `mart_precios_por_comercio`
- `mart_precios_por_ubicacion`
- `mart_promociones`
- `mart_productos_mayor_dispersion`
- `mart_sucursales_geografia`
- `mart_calidad_precios`
- `mart_productos_comparables`
- `mart_precios_sospechosos`
- `mart_canasta_basica_candidatos`

## Generar la base

Si la base no existe, ejecutar primero la carga a DuckDB:

```bash
python -m src.load.load_duckdb --zip data/raw/sepa_sabado.zip --db data/processed/precios_diarios.duckdb
```

## Generar los marts

Luego crear la capa analítica:

```bash
python -m src.analysis.create_dashboard_tables --db data/processed/precios_diarios.duckdb
```

## Ejecutar la app

Desde la raíz del proyecto:

```bash
streamlit run app/dashboard_precios.py
```

URL esperada:

```text
http://localhost:8501
```

## Secciones disponibles

- Sobre el proyecto: presentación, alcance, fuente, stack y métricas generales.
- Resumen general: métricas principales y tabla completa de `mart_resumen_general`.
- Precios por comercio: resumen por bandera/comercio y gráfico simple.
- Buscador de productos: búsqueda parametrizada sobre `mart_resumen_productos`.
- Precios por ubicación: filtros por provincia y localidad.
- Promociones: productos con registros promocionales.
- Productos con mayor dispersión: productos con mayor diferencia entre precio mínimo y máximo.
- Sucursales georreferenciadas: tabla y mapa simple con latitud/longitud.
- Calidad de precios: reglas exploratorias para identificar valores sospechosos.
- Buscador avanzado: filtros por texto, marca, unidad, precio máximo y registros mínimos.
- Canasta básica exploratoria: candidatos por categoría usando búsquedas por texto.
- Comparación entre fechas: variación de métricas generales y productos comparables.
- Evolución de producto: serie temporal por producto seleccionado.

## Limitaciones actuales

- Es una app local de exploración, no un dashboard final de producción.
- No incluye autenticación ni control de usuarios.
- No escribe en DuckDB; abre la base en modo solo lectura.
- Las búsquedas y tablas grandes usan `LIMIT` para evitar operaciones pesadas en memoria.
- La dispersión de precios puede estar afectada por productos mal comparados, distintas presentaciones, errores de carga o diferencias reales entre comercios.
- La canasta exploratoria no representa una canasta oficial.

## Próximos pasos

- Sumar más fechas para fortalecer el análisis temporal.
- Validar reglas de matching de productos antes de interpretar dispersiones altas.
- Agregar capturas al README cuando se prepare la publicación del portfolio.
