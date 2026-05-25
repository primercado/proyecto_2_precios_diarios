# App local en Streamlit

## Objetivo

Esta app permite explorar desde el navegador los marts analiticos de precios diarios SEPA ya generados en DuckDB. Es una primera version local y funcional para uso en Fedora, no un dashboard final de produccion.

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

Tambien requiere que existan estos marts:

- `mart_resumen_general`
- `mart_resumen_productos`
- `mart_precios_por_comercio`
- `mart_precios_por_ubicacion`
- `mart_promociones`
- `mart_productos_mayor_dispersion`
- `mart_sucursales_geografia`

## Generar la base

Si la base no existe, ejecutar primero la carga a DuckDB:

```bash
python -m src.load.load_duckdb --zip data/raw/sepa_sabado.zip --db data/processed/precios_diarios.duckdb
```

## Generar los marts

Luego crear la capa analitica:

```bash
python -m src.analysis.create_dashboard_tables --db data/processed/precios_diarios.duckdb
```

## Ejecutar la app

Desde la raiz del proyecto:

```bash
streamlit run app/dashboard_precios.py
```

URL esperada:

```text
http://localhost:8501
```

## Secciones disponibles

- Resumen general: metricas principales y tabla completa de `mart_resumen_general`.
- Precios por comercio: resumen por bandera/comercio y grafico simple.
- Buscador de productos: busqueda parametrizada sobre `mart_resumen_productos`.
- Precios por ubicacion: filtros por provincia y localidad.
- Promociones: productos con registros promocionales.
- Productos con mayor dispersion: productos con mayor diferencia entre precio minimo y maximo.
- Sucursales georreferenciadas: tabla y mapa simple con latitud/longitud.

## Limitaciones actuales

- Es una app local de exploracion, no un dashboard final de produccion.
- No incluye autenticacion ni control de usuarios.
- No escribe en DuckDB; abre la base en modo solo lectura.
- Los graficos son simples y priorizan validar los marts.
- Las busquedas y tablas grandes usan `LIMIT` para evitar operaciones pesadas en memoria.
- La dispersion de precios puede estar afectada por productos mal comparados, distintas presentaciones, errores de carga o diferencias reales entre comercios.

## Proximos pasos

- Refinar filtros por fecha si se cargan multiples publicaciones.
- Agregar mejores visualizaciones y formatos monetarios.
- Incorporar comparaciones por producto entre comercios y ubicaciones.
- Validar reglas de matching de productos antes de interpretar dispersiones altas.
- Evaluar una version de dashboard final cuando el modelo analitico este estabilizado.
