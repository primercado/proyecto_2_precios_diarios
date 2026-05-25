# Evolucion temporal en el dashboard

## Que permite analizar

La capa temporal permite comparar publicaciones diarias de SEPA ya cargadas en
DuckDB. La app Streamlit puede mostrar:

- variacion de volumen entre dos fechas;
- productos unicos por fecha;
- precio promedio general y su variacion porcentual;
- productos que mas subieron y mas bajaron;
- evolucion historica de un producto seleccionado.

## Mart `mart_evolucion_productos`

Este mart agrega `fact_precios` por fecha y producto comparable:

- `fecha_publicacion`;
- `id_producto`;
- descripcion;
- marca;
- cantidad de presentacion;
- unidad de medida de presentacion.

Calcula cantidad de registros, precio minimo, maximo, promedio y precio de
referencia promedio. Se genera con SQL dentro de DuckDB, sin cargar
`fact_precios` completa en pandas.

```bash
python -m src.analysis.create_dashboard_tables \
  --db data/processed/precios_diarios.duckdb \
  --only-mart mart_evolucion_productos
```

## Mart `mart_variacion_productos`

Este mart compara cada producto contra su fecha anterior disponible usando como
base `mart_evolucion_productos`. Si hay una sola fecha cargada, queda vacio y no
falla.

Campos principales:

- fecha actual y fecha anterior;
- producto, descripcion, marca, presentacion y unidad;
- precio promedio actual y anterior;
- variacion absoluta y porcentual;
- cantidad de registros actual y anterior.

```bash
python -m src.analysis.create_dashboard_tables \
  --db data/processed/precios_diarios.duckdb \
  --only-mart mart_variacion_productos
```

Si `mart_evolucion_productos` no existe, el script lo crea antes porque es una
dependencia necesaria.

## Cargar mas fechas

Para sumar nuevas publicaciones al historico:

```bash
python -m src.pipeline.run_daily_pipeline --date 2026-05-25
```

Para cargar desde un ZIP ya descargado:

```bash
python -m src.pipeline.run_daily_pipeline \
  --zip data/raw/sepa_domingo.zip \
  --date 2026-05-24
```

Si una fecha ya existe y se necesita recalcular:

```bash
python -m src.pipeline.run_daily_pipeline \
  --date 2026-05-24 \
  --reload-existing-dates
```

Despues de cargar mas fechas, regenerar los marts temporales o toda la capa
analitica.

## Comparacion entre fechas

En Streamlit, abrir la seccion `Comparación entre fechas`.

La barra lateral permite seleccionar fecha inicial y fecha final. La pantalla
muestra metricas generales desde `mart_resumen_general` y rankings desde
`mart_variacion_productos`.

Filtros disponibles:

- cantidad minima de registros;
- limite de resultados;
- unidad de medida cuando existe.

Los graficos Plotly muestran top de aumentos y bajas porcentuales, limitado para
evitar tablas y visualizaciones demasiado grandes.

## Evolucion de producto

En la seccion `Evolución de producto` se puede buscar por texto, filtrar por
marca y unidad, y seleccionar un producto comparable.

La app muestra:

- tabla de evolucion por fecha;
- primera y ultima fecha disponible;
- precio promedio inicial y final;
- variacion absoluta y porcentual;
- grafico de linea con precio promedio, minimo y maximo.

Con una sola fecha cargada, la app muestra el dato disponible y aclara que la
evolucion temporal requiere mas publicaciones.

## Limitaciones de comparabilidad

Las comparaciones se realizan agrupando productos por ID, descripcion, marca,
presentacion y unidad. Aun asi, pueden existir inconsistencias de carga o
productos no estrictamente equivalentes.

El analisis no reemplaza una dimension canonica de productos ni un proceso de
normalizacion avanzada. Los rankings deben leerse como indicadores exploratorios
y no como mediciones definitivas de inflacion por producto.

## Ejecutar la app

```bash
streamlit run app/dashboard_precios.py
```

La app abre la base en modo solo lectura y consulta tablas `mart_*`.

## Proximos pasos

- Acumular mas fechas para observar tendencias mas estables.
- Crear reglas de normalizacion para productos y marcas.
- Definir canastas comparables por categoria.
- Agregar tests de consistencia para variaciones extremas.
- Preparar una version desplegable cuando el modelo temporal este validado.
