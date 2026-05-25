# Precios Diarios SEPA Argentina

Pipeline de datos y dashboard interactivo para analizar precios diarios de supermercados a partir de datos oficiales SEPA.

## Descripción breve

Este proyecto descarga, limpia, carga y analiza publicaciones diarias de precios de supermercados de Argentina usando datos oficiales de SEPA. El flujo está pensado para trabajar localmente con archivos diarios grandes, cargar millones de registros en DuckDB y exponer una capa analítica liviana para exploración.

El problema que aborda es la dificultad de comparar precios entre fechas, comercios, ubicaciones y productos cuando la fuente original llega como archivos masivos y poco cómodos para consulta directa. El proyecto transforma esos datos en tablas analíticas preparadas para responder preguntas de evolución temporal, dispersión de precios, promociones y calidad de datos.

Es un proyecto de portfolio de análisis e ingeniería de datos. Muestra un pipeline incremental reproducible, una base analítica local, marts orientados a dashboard y una app Streamlit para explorar resultados sin consultar directamente las tablas transaccionales más pesadas.

Estado local actual: la base `data/processed/precios_diarios.duckdb` contiene publicaciones de `2026-05-21` a `2026-05-25`, con más de 75 millones de registros de precios procesados.

## Funcionalidades principales

- Descarga de datos desde CKAN/SEPA.
- Procesamiento de ZIPs anidados.
- Limpieza de archivos `comercio.csv`, `productos.csv` y `sucursales.csv`.
- Carga incremental en DuckDB.
- Control de ingestas.
- Generación de marts analíticos.
- Dashboard local en Streamlit.
- Comparación entre fechas.
- Evolución temporal de productos.
- Detección exploratoria de precios sospechosos.
- Canasta básica exploratoria.

## Arquitectura del proyecto

```text
CKAN / SEPA
    ↓
Descarga de ZIP diario
    ↓
Inspección y limpieza
    ↓
DuckDB
    ↓
Marts analíticos
    ↓
Dashboard Streamlit
```

## Estructura del repositorio

```text
app/
  dashboard_precios.py              # Dashboard local en Streamlit
docs/
  01_extractor_sepa_api.md          # Documentación del extractor CKAN/SEPA
  02_estructura_archivos_sepa.md    # Estructura observada de archivos fuente
  03_pipeline_limpieza_carga_duckdb.md
  04_capa_analitica_dashboard.md
  05_app_streamlit_dashboard.md
  10_evolucion_temporal_dashboard.md
  11_pulido_interfaz_portfolio.md
  12_guia_uso_local.md
sql/
  01_create_tables_duckdb.sql
  04_queries_dashboard_duckdb.sql
  05_queries_calidad_precios.sql
  06_queries_evolucion_temporal.sql
src/
  extract/sepa_api.py               # Descarga y listado de recursos SEPA
  load/load_duckdb.py               # Limpieza y carga incremental en DuckDB
  pipeline/run_daily_pipeline.py    # Orquestación diaria por fecha
  analysis/create_dashboard_tables.py
data/
  raw/                              # ZIPs diarios descargados o provistos localmente
  processed/                        # DuckDB local y exports de marts
```

## Stack técnico

- Python
- DuckDB
- Pandas
- Polars
- Streamlit
- Plotly
- CKAN API
- SQL

## Instalación

Crear y activar un entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

## Uso rápido

Ejecutar el dashboard local si la base DuckDB y los marts ya existen:

```bash
streamlit run app/dashboard_precios.py
```

URL esperada:

```text
http://localhost:8501
```

## Flujo de carga por fecha

Listar fechas disponibles publicadas por SEPA:

```bash
python -m src.extract.sepa_api --list-dates
```

Ejecutar el pipeline completo para una fecha:

```bash
python -m src.pipeline.run_daily_pipeline --date 2026-05-24
```

Cargar las publicaciones disponibles de los últimos 5 días para poblar mejor el dashboard sin volver demasiado pesada la base local:

```bash
python -m src.pipeline.run_daily_pipeline --last-days 5
```

Usar un ZIP ya descargado localmente:

```bash
python -m src.pipeline.run_daily_pipeline \
  --date 2026-05-24 \
  --zip data/raw/sepa_2026-05-24.zip
```

Si una fecha ya existe, la carga incremental la omite. Para reconstruir una fecha:

```bash
python -m src.pipeline.run_daily_pipeline \
  --date 2026-05-24 \
  --reload-existing-dates
```

## Carga manual por etapa

Descargar datos desde SEPA:

```bash
python -m src.extract.sepa_api --date 2026-05-24
```

Cargar un ZIP en DuckDB:

```bash
python -m src.load.load_duckdb \
  --zip data/raw/sepa_2026-05-24.zip \
  --db data/processed/precios_diarios.duckdb \
  --append \
  --date 2026-05-24
```

Crear o actualizar marts analíticos:

```bash
python -m src.analysis.create_dashboard_tables \
  --db data/processed/precios_diarios.duckdb
```

Crear un mart puntual:

```bash
python -m src.analysis.create_dashboard_tables \
  --db data/processed/precios_diarios.duckdb \
  --only-mart mart_variacion_productos
```

## Dashboard Streamlit

La app consulta tablas `mart_*` materializadas en DuckDB y abre la base en modo solo lectura. Incluye:

- Vista de presentación del proyecto.
- Resumen general por fecha.
- Precios por comercio y ubicación.
- Buscador simple y buscador avanzado de productos.
- Promociones.
- Productos con mayor dispersión de precios.
- Sucursales georreferenciadas.
- Calidad de precios.
- Canasta básica exploratoria.
- Comparación entre fechas.
- Evolución temporal de producto.

Ejecutar:

```bash
streamlit run app/dashboard_precios.py
```

## Datos y limitaciones

- La fuente es SEPA Argentina a través de CKAN.
- El proyecto no modifica los datos crudos descargados.
- Las reglas de calidad son exploratorias: marcan casos para revisar, no corrigen precios automáticamente.
- La canasta básica exploratoria se basa en búsquedas por texto y no representa una canasta oficial.
- Las comparaciones entre productos dependen de la consistencia de descripciones, marcas, presentaciones y unidades de medida publicadas.
- El dashboard está pensado para ejecución local, no como aplicación productiva con autenticación o despliegue público.

## Documentación

- [Guía de uso local](docs/12_guia_uso_local.md)
- [Extractor SEPA desde CKAN](docs/01_extractor_sepa_api.md)
- [Estructura observada de archivos SEPA](docs/02_estructura_archivos_sepa.md)
- [Pipeline de limpieza y carga en DuckDB](docs/03_pipeline_limpieza_carga_duckdb.md)
- [Capa analítica para dashboard](docs/04_capa_analitica_dashboard.md)
- [App local en Streamlit](docs/05_app_streamlit_dashboard.md)
- [Reglas de calidad de precios](docs/06_reglas_calidad_precios.md)
- [Mejoras de dashboard: calidad y canasta](docs/07_mejoras_dashboard_calidad_canasta.md)
- [Evolución temporal en el dashboard](docs/10_evolucion_temporal_dashboard.md)
- [Pulido de interfaz para portfolio](docs/11_pulido_interfaz_portfolio.md)

## Próximos pasos posibles

- Sumar más fechas para mejorar el análisis temporal.
- Refinar reglas de comparación entre productos equivalentes.
- Agregar capturas de pantalla al README.
- Preparar una publicación técnica para LinkedIn con decisiones de arquitectura y resultados.
