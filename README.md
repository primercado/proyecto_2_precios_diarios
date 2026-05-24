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

## Documentación técnica

- [Extractor SEPA desde CKAN](docs/01_extractor_sepa_api.md)
- [Estructura observada de archivos SEPA](docs/02_estructura_archivos_sepa.md)
