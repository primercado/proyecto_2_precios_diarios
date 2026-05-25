# Guía de uso local

Esta guía resume cómo ejecutar el proyecto en una máquina local sin correr procesos pesados innecesarios.

## Requisitos

- Python 3.10 o superior.
- Dependencias instaladas desde `requirements.txt`.
- Acceso a internet solo si se van a listar o descargar publicaciones desde SEPA.
- Base DuckDB local en `data/processed/precios_diarios.duckdb` para abrir el dashboard.

## Instalación

Desde la raíz del proyecto:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Ver fechas disponibles en SEPA

```bash
python -m src.extract.sepa_api --list-dates
```

Este comando consulta los recursos publicados en CKAN/SEPA y muestra las fechas detectadas.

## Ejecutar pipeline para una fecha

```bash
python -m src.pipeline.run_daily_pipeline --date 2026-05-24
```

El pipeline descarga o localiza el ZIP diario, inspecciona la estructura, limpia los archivos necesarios, carga DuckDB de manera incremental y deja la fecha registrada en `control_ingestas`.

## Cargar los últimos 5 días disponibles

```bash
python -m src.pipeline.run_daily_pipeline --last-days 5
```

Esta opción consulta CKAN/SEPA, toma como referencia la publicación más reciente disponible, descarga las fechas publicadas dentro de los últimos 5 días y las carga de forma incremental antes de regenerar los marts del dashboard. Es el rango recomendado para mostrar evolución temporal sin volver demasiado pesada la base local.

Si alguna fecha ya está cargada en DuckDB, se omite. Para reconstruir fechas ya existentes:

```bash
python -m src.pipeline.run_daily_pipeline \
  --last-days 5 \
  --reload-existing-dates
```

## Ejecutar pipeline con ZIP local

```bash
python -m src.pipeline.run_daily_pipeline \
  --date 2026-05-24 \
  --zip data/raw/sepa_2026-05-24.zip
```

Esta opción sirve cuando el archivo ya fue descargado y se quiere evitar una nueva descarga.

## Regenerar marts analíticos

```bash
python -m src.analysis.create_dashboard_tables \
  --db data/processed/precios_diarios.duckdb
```

Los marts quedan materializados dentro de DuckDB y también se exportan a `data/processed/dashboard/` como CSV y, cuando está disponible, Parquet.

## Ejecutar dashboard

```bash
streamlit run app/dashboard_precios.py
```

URL local esperada:

```text
http://localhost:8501
```

La app abre DuckDB en modo solo lectura y consulta únicamente tablas `mart_*`.

## Flujo recomendado para revisar el portfolio

1. Abrir `Sobre el proyecto` para entender el alcance y las métricas generales.
2. Revisar `Resumen general` para validar volumen de datos por fecha.
3. Usar `Buscador de productos` o `Buscador avanzado` para comparar productos.
4. Explorar `Canasta básica exploratoria` con filtros de registros mínimos y unidad.
5. Usar `Comparación entre fechas` para analizar variaciones entre publicaciones.
6. Usar `Evolución de producto` para seguir un producto específico en el tiempo.

## Notas de interpretación

- Los datos dependen de la publicación oficial de SEPA.
- La comparación entre productos puede verse afectada por diferencias de descripción, marca, presentación o unidad de medida.
- Los precios sospechosos se marcan para revisión; no se eliminan automáticamente.
- La canasta exploratoria no es una canasta oficial.
- El dashboard es local y exploratorio; no incluye autenticación ni despliegue.
