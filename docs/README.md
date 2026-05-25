# Documentación del proyecto

Este directorio reúne la documentación técnica del proyecto `proyecto_2_precios_diarios`.

## Índice

- [Guía de uso local](12_guia_uso_local.md)
- [Extractor SEPA desde CKAN](01_extractor_sepa_api.md)
- [Estructura observada de archivos SEPA](02_estructura_archivos_sepa.md)
- [Pipeline de limpieza y carga en DuckDB](03_pipeline_limpieza_carga_duckdb.md)
- [Capa analítica para dashboard](04_capa_analitica_dashboard.md)
- [App local en Streamlit](05_app_streamlit_dashboard.md)
- [Reglas de calidad de precios](06_reglas_calidad_precios.md)
- [Mejoras de dashboard: calidad y canasta](07_mejoras_dashboard_calidad_canasta.md)
- [Evolución temporal en el dashboard](10_evolucion_temporal_dashboard.md)
- [Pulido de interfaz para portfolio](11_pulido_interfaz_portfolio.md)

## Alcance

La documentación cubre la extracción desde SEPA, la estructura observada de los archivos crudos, la carga incremental en DuckDB, la generación de marts analíticos y el uso local del dashboard Streamlit.

El proyecto está orientado a portfolio y ejecución local. No incluye instrucciones de deploy ni configuración productiva.
