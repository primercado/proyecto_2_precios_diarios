# Estructura observada de archivos SEPA

## Objetivo

Este documento registra la estructura real observada en los archivos descargados desde SEPA. Sirve como referencia para construir las próximas etapas del pipeline: inspección, extracción, limpieza, validación de esquemas y carga analítica.

La observación documentada corresponde al archivo:

```text
data/raw/sepa_sabado.zip
```

## Resumen ejecutivo

El ZIP principal descargado por el extractor no contiene CSV directamente. Contiene una carpeta con fecha y, dentro de esa carpeta, múltiples ZIPs internos. Cada ZIP interno corresponde a un comercio o lote y contiene tres CSV:

- `comercio.csv`
- `productos.csv`
- `sucursales.csv`

Los CSV observados usan separador `|` y saltos de línea CRLF.

## Estructura interna del ZIP principal

Ejemplo observado:

```text
data/raw/sepa_sabado.zip
└── 2026-05-23/
    ├── sepa_1_comercio-sepa-23_2026-05-23_09-05-11.zip
    ├── sepa_2_...zip
    ├── sepa_3_...zip
    └── ...
```

La carpeta de primer nivel representa la fecha de publicación o generación del paquete. Para el archivo inspeccionado, la carpeta fue:

```text
2026-05-23/
```

Ejemplo de ruta interna completa:

```text
2026-05-23/sepa_1_comercio-sepa-23_2026-05-23_09-05-11.zip
```

## Estructura de los ZIPs internos

Al abrir un ZIP interno se observaron tres archivos CSV:

```text
sepa_1_comercio-sepa-23_2026-05-23_09-05-11.zip
├── comercio.csv
├── productos.csv
└── sucursales.csv
```

Esta estructura sugiere una separación lógica entre:

- metadata del comercio o bandera;
- catálogo de productos y precios por sucursal;
- datos de sucursales, ubicación y horarios.

## Formato de los CSV

Características observadas:

| Característica | Valor observado |
|---|---|
| Separador | `|` |
| Saltos de línea | CRLF |
| Codificación | Pendiente de validación sistemática |
| Archivos por ZIP interno | 3 |
| Encabezados | Presentes |

Ejemplo de lectura recomendada con pandas:

```python
import pandas as pd

productos = pd.read_csv(
    "productos.csv",
    sep="|",
    dtype=str,
)
```

Para una lectura directa desde ZIPs anidados conviene usar `zipfile` y `io.TextIOWrapper`, evitando extraer datos crudos al repositorio.

## `comercio.csv`

`comercio.csv` contiene información general del comercio, bandera y versión SEPA.

Columnas observadas:

| Orden | Columna |
|---:|---|
| 1 | `id_comercio` |
| 2 | `id_bandera` |
| 3 | `comercio_cuit` |
| 4 | `comercio_razon_social` |
| 5 | `comercio_bandera_nombre` |
| 6 | `comercio_bandera_url` |
| 7 | `comercio_ultima_actualizacion` |
| 8 | `comercio_version_sepa` |

Particularidad observada: este archivo puede traer una línea final extra con metadata de actualización:

```text
Última actualización: 2026-05-23T04:00:00-0300
```

Esa línea no forma parte del esquema tabular y debe tratarse explícitamente en la etapa de limpieza o lectura. Una estrategia posible es descartar filas cuyo primer campo empiece con `Última actualización:`.

## `productos.csv`

`productos.csv` contiene productos, precios, unidades de presentación, precios de referencia y promociones.

Columnas observadas:

| Orden | Columna |
|---:|---|
| 1 | `id_comercio` |
| 2 | `id_bandera` |
| 3 | `id_sucursal` |
| 4 | `id_producto` |
| 5 | `productos_ean` |
| 6 | `productos_descripcion` |
| 7 | `productos_cantidad_presentacion` |
| 8 | `productos_unidad_medida_presentacion` |
| 9 | `productos_marca` |
| 10 | `productos_precio_lista` |
| 11 | `productos_precio_referencia` |
| 12 | `productos_cantidad_referencia` |
| 13 | `productos_unidad_medida_referencia` |
| 14 | `productos_precio_unitario_promo1` |
| 15 | `productos_leyenda_promo1` |
| 16 | `productos_precio_unitario_promo2` |
| 17 | `productos_leyenda_promo2` |

Campos a validar en transformación:

- precios como números decimales;
- cantidades de presentación y referencia;
- EAN como texto para preservar ceros a la izquierda;
- IDs como texto o enteros según necesidad analítica;
- valores faltantes en promociones.

## `sucursales.csv`

`sucursales.csv` contiene información de locales físicos, ubicación, dirección y horarios de atención.

Columnas observadas:

| Orden | Columna |
|---:|---|
| 1 | `id_comercio` |
| 2 | `id_bandera` |
| 3 | `id_sucursal` |
| 4 | `sucursales_nombre` |
| 5 | `sucursales_tipo` |
| 6 | `sucursales_calle` |
| 7 | `sucursales_numero` |
| 8 | `sucursales_latitud` |
| 9 | `sucursales_longitud` |
| 10 | `sucursales_observaciones` |
| 11 | `sucursales_barrio` |
| 12 | `sucursales_codigo_postal` |
| 13 | `sucursales_localidad` |
| 14 | `sucursales_provincia` |
| 15 | `sucursales_lunes_horario_atencion` |
| 16 | `sucursales_martes_horario_atencion` |
| 17 | `sucursales_miercoles_horario_atencion` |
| 18 | `sucursales_jueves_horario_atencion` |
| 19 | `sucursales_viernes_horario_atencion` |
| 20 | `sucursales_sabado_horario_atencion` |
| 21 | `sucursales_domingo_horario_atencion` |

Campos a validar en transformación:

- latitud y longitud como decimales;
- códigos postales como texto;
- provincia y localidad normalizadas;
- horarios con formatos heterogéneos;
- sucursales sin coordenadas o con coordenadas inválidas.

## Comandos útiles de inspección

Listar los primeros elementos del ZIP principal:

```bash
python - <<'PY'
from zipfile import ZipFile

with ZipFile("data/raw/sepa_sabado.zip") as zf:
    for name in zf.namelist()[:20]:
        print(name)
PY
```

Listar los archivos dentro del primer ZIP interno sin extraer a disco:

```bash
python - <<'PY'
from io import BytesIO
from zipfile import ZipFile

with ZipFile("data/raw/sepa_sabado.zip") as outer:
    inner_name = next(name for name in outer.namelist() if name.endswith(".zip"))
    with ZipFile(BytesIO(outer.read(inner_name))) as inner:
        print(inner_name)
        for name in inner.namelist():
            print(" -", name)
PY
```

Leer encabezados de los tres CSV del primer ZIP interno:

```bash
python - <<'PY'
from io import BytesIO, TextIOWrapper
import csv
from zipfile import ZipFile

with ZipFile("data/raw/sepa_sabado.zip") as outer:
    inner_name = next(name for name in outer.namelist() if name.endswith(".zip"))
    with ZipFile(BytesIO(outer.read(inner_name))) as inner:
        for csv_name in ["comercio.csv", "productos.csv", "sucursales.csv"]:
            with inner.open(csv_name) as raw:
                reader = csv.reader(TextIOWrapper(raw, encoding="utf-8-sig", newline=""), delimiter="|")
                print(csv_name)
                print(next(reader))
PY
```

## Recomendaciones para el pipeline

- Mantener `data/raw/` como zona inmutable de datos descargados.
- No versionar ZIPs ni CSV extraídos.
- Procesar ZIPs anidados en memoria cuando sea posible.
- Crear validaciones de esquema antes de cargar datos en DuckDB o PostgreSQL.
- Registrar la fecha del paquete externo y el nombre del ZIP interno como columnas técnicas.
- Separar errores de lectura, errores de esquema y errores de calidad de datos.

## Próximos pasos técnicos

- Construir un extractor de ZIPs internos que emita dataframes o archivos intermedios controlados.
- Definir contratos de esquema para los tres CSV.
- Implementar tests con un ZIP mínimo de ejemplo, sin incluir datos reales pesados.
- Diseñar tablas analíticas para comercios, sucursales, productos y precios diarios.
- Documentar reglas de limpieza para precios, promociones y ubicaciones.
