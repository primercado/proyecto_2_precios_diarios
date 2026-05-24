# Pipeline de limpieza y carga analítica con DuckDB

## Objetivo

Este pipeline prepara una primera capa analítica para comparar precios diarios de supermercados en Argentina usando los datos publicados por SEPA.

La fuente cruda sigue siendo el ZIP principal descargado en `data/raw/`. Ese archivo no se modifica ni se extrae de forma permanente al repositorio. El procesamiento lee los ZIPs anidados en memoria, limpia lo mínimo necesario y genera tablas listas para análisis en DuckDB y archivos exportados en `data/processed/`.

## Por qué DuckDB

DuckDB funciona bien como capa analítica intermedia porque:

- permite consultar datos localmente con SQL sin levantar un servidor;
- escribe una base portable en un único archivo `.duckdb`;
- puede exportar a CSV y Parquet para herramientas externas;
- se integra bien con pandas durante una etapa inicial de desarrollo;
- es suficiente para preparar datos que luego pueden alimentar Power BI.

PostgreSQL queda documentado como etapa futura para una app web, API multiusuario o backend transaccional. En esta versión no se implementa PostgreSQL para mantener el pipeline simple y enfocado en análisis local.

## Inspección del ZIP

El módulo `src/transform/inspect_sepa_zip.py` inspecciona el ZIP principal descargado desde SEPA.

Uso:

```bash
python -m src.transform.inspect_sepa_zip --zip data/raw/sepa_sabado.zip
```

Qué hace:

- abre el ZIP principal;
- identifica los ZIPs internos;
- valida cuántos contienen `comercio.csv`, `productos.csv` y `sucursales.csv`;
- revisa encabezados esperados;
- cuenta filas válidas por archivo;
- cuenta filas inválidas por cantidad de columnas;
- detecta ZIPs internos vacíos o corruptos;
- elimina del conteo tabular líneas tipo `Última actualización: ...`;
- muestra un resumen por consola;
- guarda un JSON en `data/processed/inspection_summary.json`, salvo que se use `--no-summary-json`.

## Carga en DuckDB

El módulo `src/load/load_duckdb.py` carga los datos limpios en DuckDB.

Uso:

```bash
python -m src.load.load_duckdb --zip data/raw/sepa_sabado.zip --db data/processed/precios_diarios.duckdb
```

Qué hace:

- abre el ZIP principal;
- recorre cada ZIP interno sin extraer archivos crudos a disco;
- lee `comercio.csv`, `productos.csv` y `sucursales.csv` con separador `|`;
- descarta líneas inválidas o no tabulares;
- elimina líneas finales de actualización en `comercio.csv`;
- agrega `fecha_publicacion`, inferida desde la carpeta o nombre interno con formato `YYYY-MM-DD`;
- agrega `archivo_origen`, con la ruta del ZIP interno;
- normaliza precios, cantidades, latitud y longitud como valores numéricos;
- preserva IDs, EAN, códigos postales y nombres como texto para no perder ceros a la izquierda;
- carga las tablas en DuckDB;
- exporta CSV y, si DuckDB puede hacerlo, Parquet.

Por defecto recrea las tablas. Para acumular más días en la misma base se puede usar:

```bash
python -m src.load.load_duckdb --zip data/raw/otro_dia.zip --db data/processed/precios_diarios.duckdb --append
```

## Lectura de ZIPs anidados

La estructura observada es:

```text
data/raw/sepa_sabado.zip
└── 2026-05-23/
    ├── sepa_1_...zip
    ├── sepa_2_...zip
    └── ...
```

Cada ZIP interno contiene:

```text
comercio.csv
productos.csv
sucursales.csv
```

El pipeline usa `zipfile.ZipFile` y `io.BytesIO` para abrir cada ZIP interno directamente desde el ZIP principal. Esto evita generar copias crudas en `data/processed/` o en carpetas versionadas.

## Tablas generadas

### `dim_comercios`

Columnas:

- `id_comercio`
- `id_bandera`
- `comercio_cuit`
- `comercio_razon_social`
- `comercio_bandera_nombre`
- `comercio_bandera_url`
- `comercio_ultima_actualizacion`
- `comercio_version_sepa`
- `fecha_publicacion`
- `archivo_origen`

### `dim_sucursales`

Columnas:

- `id_comercio`
- `id_bandera`
- `id_sucursal`
- `sucursales_nombre`
- `sucursales_tipo`
- `sucursales_calle`
- `sucursales_numero`
- `sucursales_latitud`
- `sucursales_longitud`
- `sucursales_barrio`
- `sucursales_codigo_postal`
- `sucursales_localidad`
- `sucursales_provincia`
- `fecha_publicacion`
- `archivo_origen`

### `fact_precios`

Columnas:

- `fecha_publicacion`
- `id_comercio`
- `id_bandera`
- `id_sucursal`
- `id_producto`
- `productos_ean`
- `productos_descripcion`
- `productos_cantidad_presentacion`
- `productos_unidad_medida_presentacion`
- `productos_marca`
- `productos_precio_lista`
- `productos_precio_referencia`
- `productos_cantidad_referencia`
- `productos_unidad_medida_referencia`
- `productos_precio_unitario_promo1`
- `productos_leyenda_promo1`
- `productos_precio_unitario_promo2`
- `productos_leyenda_promo2`
- `archivo_origen`

## Limpieza mínima aplicada

- lectura con `sep="|"`;
- eliminación de filas completamente vacías;
- descarte de líneas tipo `Última actualización: ...`;
- descarte de líneas con estructura inválida durante la lectura;
- conversión de precios y cantidades a número;
- conversión de coordenadas a número;
- conversión de fechas disponibles a fecha o timestamp;
- preservación de nulos en promociones;
- conservación de productos sin promoción;
- conservación de datos crudos sin modificar en `data/raw/`.

## Archivos exportados

Después de la carga se generan:

```text
data/processed/precios_diarios.duckdb
data/processed/dim_comercios.csv
data/processed/dim_sucursales.csv
data/processed/fact_precios.csv
data/processed/dim_comercios.parquet
data/processed/dim_sucursales.parquet
data/processed/fact_precios.parquet
```

Los Parquet son opcionales en la práctica: si la exportación falla por dependencias o soporte local, los CSV quedan como salida compatible.

## Uso con Power BI

Para una primera versión del dashboard, Power BI puede conectarse a los CSV limpios en `data/processed/`. La base DuckDB queda como fuente analítica principal para validar consultas, preparar métricas y acumular días.

Métricas futuras esperadas:

- precio mínimo, máximo y promedio por producto;
- comparación por comercio;
- comparación por localidad y provincia;
- canasta de productos;
- productos con precio promocional;
- ranking de productos más baratos;
- evolución diaria cuando haya varios días cargados.

## Limitaciones actuales

- No se deduplican productos, sucursales o comercios entre ZIPs internos.
- No se normalizan marcas, localidades ni provincias más allá de conservar el texto recibido.
- No se corrigen coordenadas fuera de rango.
- No se valida todavía una clave única de producto por comercio, sucursal y fecha.
- PostgreSQL queda para una etapa posterior orientada a app web o API.
