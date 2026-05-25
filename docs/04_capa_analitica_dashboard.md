# Capa analitica para dashboard

## Objetivo

La capa analitica prepara tablas resumen para un futuro dashboard ciudadano de comparacion diaria de precios. Parte de las tablas limpias cargadas en DuckDB y genera marts mas livianos, estables y orientados a visualizacion.

Esta etapa no modifica datos crudos, no toca notebooks y no implementa PostgreSQL.

## Por que no conectar Power BI directo a `fact_precios`

La tabla `fact_precios` contiene millones de filas al nivel mas detallado: fecha, comercio, bandera, sucursal y producto. Ese nivel sirve para auditoria y consultas exploratorias, pero no es ideal como fuente directa de un dashboard.

Conectar Power BI directamente a esa tabla puede traer problemas:

- modelos mas pesados y lentos;
- refresh mas costoso;
- mayor consumo de memoria;
- medidas repetidas dentro de Power BI que conviene calcular una sola vez;
- mas riesgo de inconsistencias entre paginas del dashboard;
- dificultad para usuarios no tecnicos que solo necesitan indicadores claros.

La capa analitica reduce ese costo al materializar respuestas frecuentes: resumen general, productos, comercios, ubicaciones, promociones, dispersion y sucursales georreferenciadas.

## Por que DuckDB

DuckDB funciona como motor analitico local para esta etapa porque permite:

- ejecutar SQL sobre millones de filas sin cargar todo en pandas;
- crear tablas persistentes dentro de un archivo `.duckdb`;
- exportar resultados a CSV y Parquet;
- trabajar sin servidor;
- mantener un flujo simple antes de sumar infraestructura.

PostgreSQL queda para una etapa futura, cuando el proyecto necesite una API, multiples usuarios, despliegue persistente o integracion con una aplicacion web.

## Consultas SQL de referencia

El archivo [`sql/04_queries_dashboard_duckdb.sql`](../sql/04_queries_dashboard_duckdb.sql) contiene consultas documentadas para validar preguntas de dashboard:

- resumen general del dataset;
- resumen por producto;
- precios por comercio;
- precios por provincia y localidad;
- productos con promocion;
- productos con mayor dispersion de precios;
- buscador de producto por texto;
- sucursales georreferenciadas.

Estas consultas son utiles para revisar la logica, probar metricas en DuckDB y dejar trazabilidad de como se calculan los indicadores principales.

## Script de generacion de marts

El modulo [`src/analysis/create_dashboard_tables.py`](../src/analysis/create_dashboard_tables.py) crea tablas analiticas dentro de la base DuckDB y exporta cada mart a `data/processed/dashboard/`.

Uso principal:

```bash
python -m src.analysis.create_dashboard_tables --db data/processed/precios_diarios.duckdb
```

Uso indicando directorio de salida:

```bash
python -m src.analysis.create_dashboard_tables \
  --db data/processed/precios_diarios.duckdb \
  --output-dir data/processed/dashboard
```

El script:

- valida que exista la base DuckDB;
- valida que existan `dim_comercios`, `dim_sucursales` y `fact_precios`;
- crea la carpeta de salida si no existe;
- ejecuta transformaciones con SQL dentro de DuckDB;
- crea cada mart con `CREATE OR REPLACE TABLE`;
- muestra progreso y conteo de filas;
- exporta CSV;
- exporta Parquet si DuckDB lo permite.

## Marts generados

### `mart_resumen_general`

Resume el dataset por fecha de publicacion.

Responde:

- cuantos registros de precios hay;
- cuantos productos unicos hay;
- cuantos comercios, banderas y sucursales participan;
- cuantas provincias y localidades tienen cobertura.

### `mart_resumen_productos`

Agrega metricas por fecha y producto.

Responde:

- en cuantos comercios y sucursales aparece cada producto;
- precio minimo, maximo, promedio y mediano aproximado;
- diferencia absoluta y porcentual entre precio maximo y minimo.

### `mart_precios_por_comercio`

Resume precios por comercio y bandera.

Responde:

- cuantos productos informa cada comercio;
- cuantas sucursales tiene representadas;
- precio promedio, minimo y maximo por comercio.

### `mart_precios_por_ubicacion`

Agrega informacion por provincia y localidad.

Responde:

- volumen de precios por ubicacion;
- cantidad de productos, comercios y sucursales;
- precio promedio por localidad.

### `mart_promociones`

Agrupa productos con promociones informadas.

Responde:

- que productos tienen promo1 o promo2;
- cuantas veces aparece cada tipo de promocion;
- ejemplos de leyendas promocionales;
- precio promedio de lista y precios promedio promocionales.

### `mart_productos_mayor_dispersion`

Identifica productos con mayor diferencia entre precio minimo y maximo.

Aplica `HAVING COUNT(*) >= 20` para reducir casos poco representativos.

Responde:

- que productos muestran mayor dispersion de precios;
- donde conviene investigar diferencias grandes;
- que productos pueden ser buenos candidatos para comparativas ciudadanas.

### `mart_sucursales_geografia`

Prepara una tabla de sucursales con coordenadas.

Responde:

- que sucursales tienen latitud y longitud;
- donde estan ubicadas por localidad y provincia;
- que comercio y bandera corresponde a cada sucursal.

Sirve como base para mapas en Power BI.

## Exportaciones

Los archivos se guardan en:

```text
data/processed/dashboard/
```

CSV generados:

```text
mart_resumen_general.csv
mart_resumen_productos.csv
mart_precios_por_comercio.csv
mart_precios_por_ubicacion.csv
mart_promociones.csv
mart_productos_mayor_dispersion.csv
mart_sucursales_geografia.csv
```

Parquet generados si esta disponible:

```text
mart_resumen_general.parquet
mart_resumen_productos.parquet
mart_precios_por_comercio.parquet
mart_precios_por_ubicacion.parquet
mart_promociones.parquet
mart_productos_mayor_dispersion.parquet
mart_sucursales_geografia.parquet
```

Los CSV y Parquet generados no deben subirse al repositorio. La carpeta queda preparada con `.gitkeep`.

## Uso en Power BI

Para una primera version del dashboard, se puede conectar Power BI a los CSV o Parquet exportados en `data/processed/dashboard/`.

Recomendacion inicial:

- usar `mart_resumen_general` para tarjetas de cobertura;
- usar `mart_resumen_productos` para rankings y comparativas por producto;
- usar `mart_precios_por_comercio` para comparacion entre cadenas;
- usar `mart_precios_por_ubicacion` para filtros geograficos;
- usar `mart_promociones` para analisis de ofertas;
- usar `mart_productos_mayor_dispersion` para detectar oportunidades de ahorro;
- usar `mart_sucursales_geografia` para mapas.

## Limitaciones actuales

- La capa actual trabaja con la fecha cargada en DuckDB; cuando se acumulen mas dias, los marts ya quedan preparados para agrupar por `fecha_publicacion`.
- No normaliza nombres de productos, marcas, provincias o localidades mas alla de la limpieza previa.
- No crea una dimension canonica de productos equivalentes.
- No calcula canastas de consumo.
- No resuelve calidad de coordenadas fuera de lo informado por SEPA.
- No implementa dashboard todavia.
- No implementa PostgreSQL todavia.

## Proximos pasos recomendados

- Acumular varios dias de datos para analizar evolucion.
- Definir una canasta inicial de productos comparables.
- Crear reglas de normalizacion de productos y marcas.
- Preparar medidas y relaciones en Power BI usando los marts exportados.
- Agregar tests de consistencia para los marts principales.
- Evaluar PostgreSQL solo cuando haya una necesidad clara de API, app web o uso multiusuario.
