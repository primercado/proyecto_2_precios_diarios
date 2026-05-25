# Proyecto 2: Precios Diarios de Supermercados

## Descripción

Este proyecto tiene como objetivo crear una aplicación que compare diariamente los precios de productos de supermercados en Argentina, utilizando como fuente principal los datos abiertos del sistema SEPA.

La idea es construir un flujo de trabajo que permita extraer datos desde la API o fuente oficial de SEPA, almacenarlos en una base de datos analítica como DuckDB o PostgreSQL, analizarlos con Python y visualizar los resultados en un dashboard desarrollado con Power BI.

## Objetivo principal

Crear una aplicación que permita comparar diariamente precios de supermercados, analizar su evolución y generar visualizaciones útiles para detectar variaciones, diferencias entre comercios y cambios en productos seleccionados.

## Flujo general del proyecto

```text
Fuente SEPA
    ↓
Extracción diaria de datos
    ↓
Guardado de datos crudos
    ↓
Limpieza y transformación con Python
    ↓
Carga en DuckDB o PostgreSQL
    ↓
Análisis con Python y SQL
    ↓
Dashboard en Power BI
```

## Pipeline historico incremental

El proyecto puede cargar varios dias en la misma base DuckDB sin duplicar fechas ya procesadas. Cada ejecucion queda registrada en `control_ingestas`.

Ejecutar pipeline completo para una fecha:

```bash
python -m src.pipeline.run_daily_pipeline --date 2026-05-23
```

Usar un ZIP ya descargado:

```bash
python -m src.pipeline.run_daily_pipeline \
  --date 2026-05-23 \
  --zip data/raw/sepa_2026-05-23.zip
```

Si una fecha ya existe, la carga incremental la omite. Para rehacer una fecha:

```bash
python -m src.pipeline.run_daily_pipeline \
  --date 2026-05-23 \
  --reload-existing-dates
```

Comandos por etapa:

```bash
python -m src.extract.sepa_api --list
python -m src.extract.sepa_api --list-dates
python -m src.extract.sepa_api --download
python -m src.extract.sepa_api --date 2026-05-23

python -m src.load.load_duckdb \
  --zip data/raw/sepa_2026-05-23.zip \
  --db data/processed/precios_diarios.duckdb \
  --append \
  --date 2026-05-23
```

## Documentación técnica

- [Extractor SEPA desde CKAN](docs/01_extractor_sepa_api.md)
- [Estructura observada de archivos SEPA](docs/02_estructura_archivos_sepa.md)

## Capa analítica para dashboard

La capa analítica crea tablas resumen en DuckDB para que un futuro dashboard en Power BI no consuma directamente los millones de filas de `fact_precios`. Los marts quedan materializados en la base local y se exportan a `data/processed/dashboard/` como CSV y, si está disponible, Parquet.

Crear marts:

```bash
python -m src.analysis.create_dashboard_tables --db data/processed/precios_diarios.duckdb
```

Crear marts indicando directorio de salida:

```bash
python -m src.analysis.create_dashboard_tables \
  --db data/processed/precios_diarios.duckdb \
  --output-dir data/processed/dashboard
```

Referencias:

- [Consultas SQL para dashboard](sql/04_queries_dashboard_duckdb.sql)
- [Script de creación de marts](src/analysis/create_dashboard_tables.py)
- [Documentación de la capa analítica](docs/04_capa_analitica_dashboard.md)

## App local en Streamlit

El proyecto incluye una primera app local en Streamlit para explorar desde el navegador los marts analiticos generados en DuckDB.

Ejecutar:

```bash
streamlit run app/dashboard_precios.py
```

Referencias:

- [App Streamlit](app/dashboard_precios.py)
- [Documentacion de la app local](docs/05_app_streamlit_dashboard.md)

## Calidad de precios y canasta exploratoria

El dashboard suma reglas iniciales de calidad para marcar precios sospechosos,
un buscador avanzado de productos comparables y una primera canasta exploratoria
basada en busquedas por texto.

Referencias:

- [Reglas de calidad de precios](docs/06_reglas_calidad_precios.md)
- [Mejoras del dashboard de calidad y canasta](docs/07_mejoras_dashboard_calidad_canasta.md)
- [Consultas SQL de calidad](sql/05_queries_calidad_precios.sql)
