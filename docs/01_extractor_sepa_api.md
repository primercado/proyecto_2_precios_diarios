# Extractor SEPA desde CKAN

## Objetivo

El módulo `src/extract/sepa_api.py` implementa la etapa de extracción del proyecto. Su responsabilidad es conectarse al CKAN oficial donde se publican los recursos de SEPA, listar los archivos disponibles y descargar el ZIP más reciente en `data/raw/`.

Este extractor conserva los datos en crudo. No descomprime, limpia, normaliza ni carga información en bases analíticas. Esas tareas corresponden a etapas posteriores del pipeline.

## Ubicación

```text
proyecto_2_precios_diarios/
├── data/
│   ├── external/
│   │   └── .gitkeep
│   ├── processed/
│   │   └── .gitkeep
│   └── raw/
│       └── .gitkeep
├── docs/
│   ├── 01_extractor_sepa_api.md
│   └── 02_estructura_archivos_sepa.md
└── src/
    └── extract/
        └── sepa_api.py
```

## Fuente de datos

El extractor consulta el dataset `sepa-precios` publicado en CKAN.

```text
API CKAN:
https://datos.produccion.gob.ar/api/3/action

Dataset por defecto:
sepa-precios
```

La acción CKAN utilizada para consultar metadatos es `package_show`. A partir de esa respuesta, el extractor obtiene la lista de recursos asociados al dataset y filtra los que corresponden a archivos ZIP.

## Flujo general

```text
CKAN oficial de SEPA
        ↓
Consulta de metadatos del dataset
        ↓
Listado de recursos disponibles
        ↓
Filtrado de recursos ZIP
        ↓
Selección del ZIP más reciente
        ↓
Descarga por chunks
        ↓
Guardado en data/raw/
```

## Responsabilidades del módulo

- Consultar la API CKAN oficial.
- Representar los recursos con la dataclass `SepaResource`.
- Identificar recursos ZIP por formato o por extensión de URL.
- Seleccionar el recurso ZIP más reciente usando fechas de metadata y, como apoyo, fechas presentes en el nombre.
- Listar fechas disponibles detectadas en los recursos ZIP publicados.
- Descargar el archivo por partes para evitar cargar archivos grandes completos en memoria.
- Escribir primero en un archivo temporal `.tmp`.
- Reemplazar el archivo final solo cuando la descarga termina correctamente.
- Evitar sobrescribir archivos existentes salvo que se use `--overwrite`.
- Exponer funciones reutilizables desde Python y una interfaz de línea de comandos.

## Componentes principales

### Constantes

```python
CKAN_API_BASE_URL = "https://datos.produccion.gob.ar/api/3/action"
SEPA_MINORISTAS_DATASET = "sepa-precios"
DEFAULT_RAW_DIR = Path("data/raw")
REQUEST_TIMEOUT = 60
CHUNK_SIZE = 1024 * 1024
```

| Constante | Uso |
|---|---|
| `CKAN_API_BASE_URL` | URL base de la API CKAN. |
| `SEPA_MINORISTAS_DATASET` | Dataset consultado por defecto. |
| `DEFAULT_RAW_DIR` | Directorio local donde se guardan los ZIP descargados. |
| `REQUEST_TIMEOUT` | Tiempo máximo de espera para requests HTTP. |
| `CHUNK_SIZE` | Tamaño de cada bloque de descarga. |

### `SepaResource`

`SepaResource` encapsula los metadatos mínimos que el extractor necesita de cada recurso CKAN:

```python
id: str
name: str
format: str
url: str
created: str | None
metadata_modified: str | None
last_modified: str | None
```

La propiedad `is_zip` permite decidir si un recurso es descargable como ZIP:

```python
resource.format.lower() == "zip" or resource.url.lower().endswith(".zip")
```

### Consulta de CKAN

La función `_ckan_get()` centraliza la llamada HTTP a CKAN:

- construye la URL de la acción;
- ejecuta el request con timeout;
- valida errores HTTP;
- valida que CKAN responda `success=True`;
- devuelve el bloque `result`.

La función `list_resources()` usa `_ckan_get("package_show", {"id": dataset_id})` y transforma cada recurso crudo en un objeto `SepaResource`.

### Fechas disponibles

`list_available_dates()` recibe una lista de recursos y devuelve las fechas de publicación detectadas en recursos ZIP.

El criterio usa fechas con formato `YYYY-MM-DD` encontradas en el nombre del recurso o en la URL. Si CKAN no publica la fecha en esos campos, usa como respaldo `last_modified`, `metadata_modified` o `created`.

La salida no incluye duplicados y queda ordenada de menor a mayor.

### Selección del ZIP más reciente

`latest_zip_resource()` recibe una lista de recursos y selecciona el ZIP más reciente.

El criterio de ordenamiento usa:

1. `last_modified`, `metadata_modified` o `created`, según disponibilidad.
2. Una fecha con formato `YYYY-MM-DD` encontrada en el nombre del recurso, si existe.

Si no hay recursos ZIP con URL, lanza `SepaApiError`.

### Descarga

`download_resource()` descarga el recurso seleccionado en el directorio de salida.

El comportamiento esperado es:

- crear el directorio si no existe;
- calcular el nombre local desde la URL o desde el nombre del recurso;
- devolver el archivo existente si ya fue descargado y no se pidió `--overwrite`;
- descargar por chunks de 1 MB;
- escribir en `archivo.zip.tmp`;
- mover el temporal al destino final al terminar.

Esto reduce el riesgo de dejar un ZIP incompleto con nombre definitivo si la descarga se interrumpe.

## Uso desde línea de comandos

Listar recursos disponibles:

```bash
python -m src.extract.sepa_api --list
```

Listar fechas disponibles en recursos ZIP:

```bash
python -m src.extract.sepa_api --list-dates
```

Listar fechas disponibles dentro de los últimos 5 días publicados:

```bash
python -m src.extract.sepa_api --last-days 5
```

Descargar el ZIP más reciente en `data/raw/`:

```bash
python -m src.extract.sepa_api --download
```

Forzar una nueva descarga aunque el archivo ya exista:

```bash
python -m src.extract.sepa_api --download --overwrite
```

Cambiar el directorio de salida:

```bash
python -m src.extract.sepa_api --download --output-dir data/raw
```

Consultar explícitamente el dataset por defecto:

```bash
python -m src.extract.sepa_api --list --dataset-id sepa-precios
```

## Uso desde Python

```python
from src.extract.sepa_api import download_latest_zip, list_available_dates, list_resources

resources = list_resources()
available_dates = list_available_dates(resources)
zip_path = download_latest_zip()

print(available_dates)
print(zip_path)
```

Manejo de errores:

```python
from src.extract.sepa_api import SepaApiError, download_latest_zip

try:
    path = download_latest_zip()
except SepaApiError as error:
    print(f"No se pudo descargar SEPA: {error}")
```

## Salida esperada

Después de ejecutar la descarga, el resultado queda en `data/raw/`:

```text
data/
└── raw/
    ├── .gitkeep
    └── sepa_sabado.zip
```

Los archivos dentro de `data/raw/` no deben versionarse. Solo se conserva `.gitkeep` para mantener la carpeta en el repositorio.

## Validaciones sugeridas

Comprobar que el extractor lista recursos:

```bash
python -m src.extract.sepa_api --list
```

Comprobar que descarga el ZIP:

```bash
python -m src.extract.sepa_api --download
```

Verificar que el archivo descargado no queda trackeado por Git:

```bash
git status --short
```

Inspeccionar el contenido del ZIP sin extraerlo:

```bash
python - <<'PY'
from zipfile import ZipFile

with ZipFile("data/raw/sepa_sabado.zip") as zf:
    for name in zf.namelist()[:20]:
        print(name)
PY
```

## Próximos pasos técnicos

- Implementar un módulo de inspección o extracción controlada de los ZIP internos.
- Validar esquemas de `comercio.csv`, `productos.csv` y `sucursales.csv`.
- Definir tipos de datos para precios, coordenadas, IDs y fechas.
- Cargar una primera muestra en DuckDB para análisis exploratorio.
- Diseñar pruebas automatizadas con sesiones HTTP simuladas para no depender de la red.
