"""Create dashboard-oriented analytic tables in DuckDB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb


REQUIRED_TABLES = ("dim_comercios", "dim_sucursales", "fact_precios")
DEFAULT_DUCKDB_MEMORY_LIMIT = "2GB"
DEFAULT_DUCKDB_THREADS = 1
DUCKDB_TEMP_DIRECTORY = Path("data/processed/tmp_duckdb")

MART_QUERIES: dict[str, str] = {
    "mart_resumen_general": """
        CREATE OR REPLACE TABLE mart_resumen_general AS
        SELECT
            f.fecha_publicacion,
            COUNT(*) AS cantidad_registros_precios,
            COUNT(DISTINCT f.id_producto) AS cantidad_productos_unicos,
            COUNT(DISTINCT f.id_comercio) AS cantidad_comercios,
            COUNT(DISTINCT hash(f.id_comercio, f.id_bandera)) AS cantidad_banderas,
            COUNT(DISTINCT hash(f.id_comercio, f.id_bandera, f.id_sucursal)) AS cantidad_sucursales,
            COUNT(DISTINCT s.sucursales_provincia) AS cantidad_provincias,
            COUNT(DISTINCT s.sucursales_localidad) AS cantidad_localidades,
            AVG(f.productos_precio_lista) AS precio_promedio_general
        FROM fact_precios AS f
        LEFT JOIN dim_sucursales AS s
            ON f.fecha_publicacion = s.fecha_publicacion
            AND f.id_comercio = s.id_comercio
            AND f.id_bandera = s.id_bandera
            AND f.id_sucursal = s.id_sucursal
        GROUP BY f.fecha_publicacion
    """,
    "mart_evolucion_productos": """
        CREATE OR REPLACE TABLE mart_evolucion_productos AS
        SELECT
            f.fecha_publicacion,
            f.id_producto,
            f.productos_descripcion,
            f.productos_marca,
            f.productos_cantidad_presentacion,
            f.productos_unidad_medida_presentacion,
            COUNT(*) AS cantidad_registros,
            MIN(f.productos_precio_lista) AS precio_minimo,
            MAX(f.productos_precio_lista) AS precio_maximo,
            AVG(f.productos_precio_lista) AS precio_promedio,
            AVG(f.productos_precio_referencia) AS precio_referencia_promedio
        FROM fact_precios AS f
        WHERE f.productos_precio_lista IS NOT NULL
        GROUP BY
            f.fecha_publicacion,
            f.id_producto,
            f.productos_descripcion,
            f.productos_marca,
            f.productos_cantidad_presentacion,
            f.productos_unidad_medida_presentacion
    """,
    "mart_variacion_productos": """
        CREATE OR REPLACE TABLE mart_variacion_productos AS
        WITH pares_fechas AS (
            SELECT
                actual.fecha_publicacion,
                MAX(anterior.fecha_publicacion) AS fecha_anterior,
                actual.id_producto,
                actual.productos_descripcion,
                actual.productos_marca,
                actual.productos_cantidad_presentacion,
                actual.productos_unidad_medida_presentacion,
                actual.precio_promedio AS precio_promedio_actual,
                actual.cantidad_registros AS cantidad_registros_actual
            FROM mart_evolucion_productos AS actual
            INNER JOIN mart_evolucion_productos AS anterior
                ON actual.id_producto = anterior.id_producto
                AND actual.productos_descripcion IS NOT DISTINCT FROM anterior.productos_descripcion
                AND actual.productos_marca IS NOT DISTINCT FROM anterior.productos_marca
                AND actual.productos_cantidad_presentacion IS NOT DISTINCT FROM anterior.productos_cantidad_presentacion
                AND actual.productos_unidad_medida_presentacion IS NOT DISTINCT FROM anterior.productos_unidad_medida_presentacion
                AND anterior.fecha_publicacion < actual.fecha_publicacion
            GROUP BY
                actual.fecha_publicacion,
                actual.id_producto,
                actual.productos_descripcion,
                actual.productos_marca,
                actual.productos_cantidad_presentacion,
                actual.productos_unidad_medida_presentacion,
                actual.precio_promedio,
                actual.cantidad_registros
        )
        SELECT
            pares.fecha_publicacion,
            pares.fecha_anterior,
            pares.id_producto,
            pares.productos_descripcion,
            pares.productos_marca,
            pares.productos_cantidad_presentacion,
            pares.productos_unidad_medida_presentacion,
            pares.precio_promedio_actual,
            anterior.precio_promedio AS precio_promedio_anterior,
            pares.precio_promedio_actual - anterior.precio_promedio AS variacion_absoluta,
            CASE
                WHEN anterior.precio_promedio > 0
                    THEN ((pares.precio_promedio_actual - anterior.precio_promedio) / anterior.precio_promedio) * 100
                ELSE NULL
            END AS variacion_porcentual,
            pares.cantidad_registros_actual,
            anterior.cantidad_registros AS cantidad_registros_anterior
        FROM pares_fechas AS pares
        INNER JOIN mart_evolucion_productos AS anterior
            ON pares.fecha_anterior = anterior.fecha_publicacion
            AND pares.id_producto = anterior.id_producto
            AND pares.productos_descripcion IS NOT DISTINCT FROM anterior.productos_descripcion
            AND pares.productos_marca IS NOT DISTINCT FROM anterior.productos_marca
            AND pares.productos_cantidad_presentacion IS NOT DISTINCT FROM anterior.productos_cantidad_presentacion
            AND pares.productos_unidad_medida_presentacion IS NOT DISTINCT FROM anterior.productos_unidad_medida_presentacion
    """,
    "mart_resumen_productos": """
        CREATE OR REPLACE TABLE mart_resumen_productos AS
        SELECT
            f.fecha_publicacion,
            f.id_producto,
            ANY_VALUE(f.productos_descripcion) AS productos_descripcion,
            ANY_VALUE(f.productos_marca) AS productos_marca,
            COUNT(*) AS cantidad_registros,
            COUNT(DISTINCT f.id_comercio) AS cantidad_comercios,
            COUNT(DISTINCT hash(f.id_comercio, f.id_bandera, f.id_sucursal)) AS cantidad_sucursales,
            MIN(f.productos_precio_lista) AS precio_minimo,
            MAX(f.productos_precio_lista) AS precio_maximo,
            AVG(f.productos_precio_lista) AS precio_promedio,
            approx_quantile(f.productos_precio_lista, 0.5) AS precio_mediano_aproximado,
            MAX(f.productos_precio_lista) - MIN(f.productos_precio_lista) AS diferencia_absoluta_max_min,
            CASE
                WHEN MIN(f.productos_precio_lista) > 0
                    THEN ((MAX(f.productos_precio_lista) - MIN(f.productos_precio_lista)) / MIN(f.productos_precio_lista)) * 100
                ELSE NULL
            END AS diferencia_porcentual_max_min
        FROM fact_precios AS f
        WHERE f.productos_precio_lista IS NOT NULL
        GROUP BY f.fecha_publicacion, f.id_producto
    """,
    "mart_precios_por_comercio": """
        CREATE OR REPLACE TABLE mart_precios_por_comercio AS
        SELECT
            f.fecha_publicacion,
            f.id_comercio,
            f.id_bandera,
            ANY_VALUE(c.comercio_bandera_nombre) AS comercio_bandera_nombre,
            COUNT(*) AS cantidad_registros,
            COUNT(DISTINCT f.id_producto) AS cantidad_productos,
            COUNT(DISTINCT hash(f.id_comercio, f.id_bandera, f.id_sucursal)) AS cantidad_sucursales,
            AVG(f.productos_precio_lista) AS precio_promedio,
            MIN(f.productos_precio_lista) AS precio_minimo,
            MAX(f.productos_precio_lista) AS precio_maximo
        FROM fact_precios AS f
        LEFT JOIN dim_comercios AS c
            ON f.fecha_publicacion = c.fecha_publicacion
            AND f.id_comercio = c.id_comercio
            AND f.id_bandera = c.id_bandera
        WHERE f.productos_precio_lista IS NOT NULL
        GROUP BY f.fecha_publicacion, f.id_comercio, f.id_bandera
    """,
    "mart_precios_por_ubicacion": """
        CREATE OR REPLACE TABLE mart_precios_por_ubicacion AS
        SELECT
            f.fecha_publicacion,
            s.sucursales_provincia,
            s.sucursales_localidad,
            COUNT(*) AS cantidad_registros,
            COUNT(DISTINCT f.id_producto) AS cantidad_productos,
            COUNT(DISTINCT f.id_comercio) AS cantidad_comercios,
            COUNT(DISTINCT hash(f.id_comercio, f.id_bandera, f.id_sucursal)) AS cantidad_sucursales,
            AVG(f.productos_precio_lista) AS precio_promedio
        FROM fact_precios AS f
        LEFT JOIN dim_sucursales AS s
            ON f.fecha_publicacion = s.fecha_publicacion
            AND f.id_comercio = s.id_comercio
            AND f.id_bandera = s.id_bandera
            AND f.id_sucursal = s.id_sucursal
        WHERE f.productos_precio_lista IS NOT NULL
        GROUP BY f.fecha_publicacion, s.sucursales_provincia, s.sucursales_localidad
    """,
    "mart_promociones": """
        CREATE OR REPLACE TABLE mart_promociones AS
        SELECT
            f.fecha_publicacion,
            f.id_producto,
            ANY_VALUE(f.productos_descripcion) AS productos_descripcion,
            ANY_VALUE(f.productos_marca) AS productos_marca,
            COUNT(*) FILTER (WHERE f.productos_precio_unitario_promo1 IS NOT NULL) AS cantidad_registros_con_promo1,
            COUNT(*) FILTER (WHERE f.productos_precio_unitario_promo2 IS NOT NULL) AS cantidad_registros_con_promo2,
            string_agg(DISTINCT NULLIF(f.productos_leyenda_promo1, ''), ' | ') AS ejemplos_leyendas_promo1,
            string_agg(DISTINCT NULLIF(f.productos_leyenda_promo2, ''), ' | ') AS ejemplos_leyendas_promo2,
            AVG(f.productos_precio_lista) AS precio_promedio_lista,
            AVG(f.productos_precio_unitario_promo1) AS precio_promedio_promo1,
            AVG(f.productos_precio_unitario_promo2) AS precio_promedio_promo2
        FROM fact_precios AS f
        WHERE f.productos_precio_unitario_promo1 IS NOT NULL
            OR f.productos_precio_unitario_promo2 IS NOT NULL
            OR NULLIF(f.productos_leyenda_promo1, '') IS NOT NULL
            OR NULLIF(f.productos_leyenda_promo2, '') IS NOT NULL
        GROUP BY f.fecha_publicacion, f.id_producto
    """,
    "mart_productos_mayor_dispersion": """
        CREATE OR REPLACE TABLE mart_productos_mayor_dispersion AS
        SELECT
            f.fecha_publicacion,
            f.id_producto,
            ANY_VALUE(f.productos_descripcion) AS productos_descripcion,
            ANY_VALUE(f.productos_marca) AS productos_marca,
            COUNT(*) AS cantidad_registros,
            COUNT(DISTINCT f.id_comercio) AS cantidad_comercios,
            COUNT(DISTINCT hash(f.id_comercio, f.id_bandera, f.id_sucursal)) AS cantidad_sucursales,
            MIN(f.productos_precio_lista) AS precio_minimo,
            MAX(f.productos_precio_lista) AS precio_maximo,
            AVG(f.productos_precio_lista) AS precio_promedio,
            MAX(f.productos_precio_lista) - MIN(f.productos_precio_lista) AS diferencia_absoluta_max_min,
            CASE
                WHEN MIN(f.productos_precio_lista) > 0
                    THEN ((MAX(f.productos_precio_lista) - MIN(f.productos_precio_lista)) / MIN(f.productos_precio_lista)) * 100
                ELSE NULL
            END AS diferencia_porcentual_max_min
        FROM fact_precios AS f
        WHERE f.productos_precio_lista IS NOT NULL
        GROUP BY f.fecha_publicacion, f.id_producto
        HAVING COUNT(*) >= 20
    """,
    "mart_sucursales_geografia": """
        CREATE OR REPLACE TABLE mart_sucursales_geografia AS
        SELECT
            s.fecha_publicacion,
            s.id_comercio,
            s.id_bandera,
            c.comercio_bandera_nombre,
            s.id_sucursal,
            s.sucursales_nombre,
            s.sucursales_tipo,
            s.sucursales_calle,
            s.sucursales_numero,
            s.sucursales_localidad,
            s.sucursales_provincia,
            s.sucursales_latitud,
            s.sucursales_longitud
        FROM dim_sucursales AS s
        LEFT JOIN dim_comercios AS c
            ON s.fecha_publicacion = c.fecha_publicacion
            AND s.id_comercio = c.id_comercio
            AND s.id_bandera = c.id_bandera
        WHERE s.sucursales_latitud IS NOT NULL
            AND s.sucursales_longitud IS NOT NULL
    """,
    "mart_calidad_precios": """
        CREATE OR REPLACE TABLE mart_calidad_precios AS
        SELECT
            f.fecha_publicacion,
            COUNT(*) AS cantidad_registros,
            COUNT(*) FILTER (WHERE f.productos_precio_lista IS NULL) AS cantidad_precio_nulo,
            COUNT(*) FILTER (WHERE f.productos_precio_lista = 0) AS cantidad_precio_cero,
            COUNT(*) FILTER (
                WHERE f.productos_precio_lista > 0
                    AND f.productos_precio_lista < 10
            ) AS cantidad_precio_menor_10,
            MIN(f.productos_precio_lista) AS precio_minimo,
            MAX(f.productos_precio_lista) AS precio_maximo,
            AVG(f.productos_precio_lista) AS precio_promedio
        FROM fact_precios AS f
        GROUP BY f.fecha_publicacion
    """,
    "mart_productos_comparables": """
        CREATE OR REPLACE TABLE mart_productos_comparables AS
        SELECT
            f.fecha_publicacion,
            f.id_producto,
            f.productos_descripcion,
            f.productos_marca,
            f.productos_cantidad_presentacion,
            f.productos_unidad_medida_presentacion,
            COUNT(*) AS cantidad_registros,
            MIN(f.productos_precio_lista) AS precio_minimo,
            MAX(f.productos_precio_lista) AS precio_maximo,
            AVG(f.productos_precio_lista) AS precio_promedio,
            AVG(f.productos_precio_referencia) AS precio_referencia_promedio,
            MAX(f.productos_precio_lista) - MIN(f.productos_precio_lista) AS diferencia_absoluta_max_min,
            CASE
                WHEN MIN(f.productos_precio_lista) > 0
                    THEN ((MAX(f.productos_precio_lista) - MIN(f.productos_precio_lista)) / MIN(f.productos_precio_lista)) * 100
                ELSE NULL
            END AS diferencia_porcentual_max_min
        FROM fact_precios AS f
        WHERE f.productos_precio_lista IS NOT NULL
        GROUP BY
            f.fecha_publicacion,
            f.id_producto,
            f.productos_descripcion,
            f.productos_marca,
            f.productos_cantidad_presentacion,
            f.productos_unidad_medida_presentacion
    """,
    "mart_precios_sospechosos": """
        CREATE OR REPLACE TABLE mart_precios_sospechosos AS
        SELECT *
        FROM (
            SELECT
                f.fecha_publicacion,
                f.id_producto,
                f.productos_descripcion,
                f.productos_marca,
                f.productos_cantidad_presentacion,
                f.productos_unidad_medida_presentacion,
                f.productos_precio_lista,
                f.productos_precio_referencia,
                CASE
                    WHEN f.productos_precio_lista <= 0 THEN 'precio_menor_o_igual_cero'
                    WHEN f.productos_precio_lista < 10 THEN 'precio_menor_10'
                    WHEN f.productos_precio_lista >= 100000 THEN 'precio_muy_alto'
                    ELSE 'revisar'
                END AS regla_calidad
            FROM fact_precios AS f
            WHERE f.productos_precio_lista <= 0
                OR f.productos_precio_lista < 10
                OR f.productos_precio_lista >= 100000
        )
        LIMIT 10000
    """,
    "mart_canasta_basica_candidatos": """
        CREATE OR REPLACE TABLE mart_canasta_basica_candidatos AS
        WITH candidatos AS (
            SELECT
                f.fecha_publicacion,
                CASE
                    WHEN f.productos_descripcion ILIKE '%LECHE%' THEN 'LECHE'
                    WHEN f.productos_descripcion ILIKE '%ARROZ%' THEN 'ARROZ'
                    WHEN f.productos_descripcion ILIKE '%FIDEO%' THEN 'FIDEO'
                    WHEN f.productos_descripcion ILIKE '%YERBA%' THEN 'YERBA'
                    WHEN f.productos_descripcion ILIKE '%ACEITE%' THEN 'ACEITE'
                    WHEN f.productos_descripcion ILIKE '%AZUCAR%' THEN 'AZUCAR'
                    WHEN f.productos_descripcion ILIKE '%HARINA%' THEN 'HARINA'
                    WHEN f.productos_descripcion ILIKE '%HUEVO%' THEN 'HUEVO'
                    ELSE NULL
                END AS categoria_canasta,
                f.id_producto,
                f.productos_descripcion,
                f.productos_marca,
                f.productos_cantidad_presentacion,
                f.productos_unidad_medida_presentacion,
                f.productos_precio_lista,
                f.productos_precio_referencia
            FROM fact_precios AS f
            WHERE f.productos_precio_lista IS NOT NULL
                AND (
                    f.productos_descripcion ILIKE '%LECHE%'
                    OR f.productos_descripcion ILIKE '%ARROZ%'
                    OR f.productos_descripcion ILIKE '%FIDEO%'
                    OR f.productos_descripcion ILIKE '%YERBA%'
                    OR f.productos_descripcion ILIKE '%ACEITE%'
                    OR f.productos_descripcion ILIKE '%AZUCAR%'
                    OR f.productos_descripcion ILIKE '%HARINA%'
                    OR f.productos_descripcion ILIKE '%HUEVO%'
                )
        )
        SELECT
            fecha_publicacion,
            categoria_canasta,
            id_producto,
            productos_descripcion,
            productos_marca,
            productos_cantidad_presentacion,
            productos_unidad_medida_presentacion,
            COUNT(*) AS cantidad_registros,
            MIN(productos_precio_lista) AS precio_minimo,
            MAX(productos_precio_lista) AS precio_maximo,
            AVG(productos_precio_lista) AS precio_promedio,
            AVG(productos_precio_referencia) AS precio_referencia_promedio
        FROM candidatos
        WHERE categoria_canasta IS NOT NULL
        GROUP BY
            fecha_publicacion,
            categoria_canasta,
            id_producto,
            productos_descripcion,
            productos_marca,
            productos_cantidad_presentacion,
            productos_unidad_medida_presentacion
    """,
}

MART_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "mart_variacion_productos": ("mart_evolucion_productos",),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea marts analiticos para dashboard en DuckDB."
    )
    parser.add_argument(
        "--db",
        required=True,
        type=Path,
        help="Ruta de la base DuckDB generada por el pipeline de carga.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/dashboard"),
        help="Directorio para exportar CSV y Parquet de los marts.",
    )
    parser.add_argument(
        "--memory-limit",
        default=DEFAULT_DUCKDB_MEMORY_LIMIT,
        help="Limite de memoria para DuckDB. Default: %(default)s.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=DEFAULT_DUCKDB_THREADS,
        help="Cantidad de threads de DuckDB. Default: %(default)s.",
    )
    parser.add_argument(
        "--only-mart",
        choices=tuple(MART_QUERIES),
        help="Crea y exporta solo un mart. Util para probar o retomar una corrida.",
    )
    return parser.parse_args()


def validate_database_path(db_path: Path) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base DuckDB: {db_path}")
    if not db_path.is_file():
        raise ValueError(f"La ruta de base DuckDB no es un archivo: {db_path}")


def validate_required_tables(con: duckdb.DuckDBPyConnection) -> None:
    existing_tables = {
        row[0]
        for row in con.sql(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            """
        ).fetchall()
    }
    missing_tables = sorted(set(REQUIRED_TABLES) - existing_tables)
    if missing_tables:
        raise RuntimeError(
            "Faltan tablas requeridas en DuckDB: " + ", ".join(missing_tables)
        )


def configure_duckdb_connection(
    con: duckdb.DuckDBPyConnection,
    temp_directory: Path,
    memory_limit: str,
    threads: int,
) -> None:
    con.execute(f"SET memory_limit='{memory_limit}'")
    con.execute(f"SET threads={threads}")
    con.execute(f"SET temp_directory='{temp_directory}'")
    con.execute("SET preserve_insertion_order=false")

    print(f"Limite de memoria DuckDB: {memory_limit}")
    print(f"Threads DuckDB: {threads}")
    print(f"Directorio temporal DuckDB: {temp_directory}")
    print("Preservar orden de insercion DuckDB: false")


def create_mart(con: duckdb.DuckDBPyConnection, mart_name: str, query: str) -> int:
    print(f"Creando {mart_name}...")
    con.execute(query)
    row_count = con.sql(f"SELECT COUNT(*) FROM {mart_name}").fetchone()[0]
    print(f"  {mart_name}: {row_count:,} filas")
    return int(row_count)


def get_queries_to_run(only_mart: str | None) -> dict[str, str]:
    if only_mart is None:
        return MART_QUERIES

    queries: dict[str, str] = {}
    for dependency in MART_DEPENDENCIES.get(only_mart, ()):
        queries[dependency] = MART_QUERIES[dependency]
    queries[only_mart] = MART_QUERIES[only_mart]
    return queries


def export_mart(con: duckdb.DuckDBPyConnection, mart_name: str, output_dir: Path) -> None:
    csv_path = output_dir / f"{mart_name}.csv"
    parquet_path = output_dir / f"{mart_name}.parquet"

    con.execute(f"COPY {mart_name} TO ? (HEADER, DELIMITER ',')", [str(csv_path)])
    print(f"  CSV: {csv_path}")

    try:
        con.execute(f"COPY {mart_name} TO ? (FORMAT PARQUET)", [str(parquet_path)])
        print(f"  Parquet: {parquet_path}")
    except Exception as exc:  # noqa: BLE001 - CSV is the required fallback.
        print(f"  No se pudo exportar Parquet para {mart_name}: {exc}")


def create_dashboard_tables(
    db_path: Path,
    output_dir: Path,
    memory_limit: str,
    threads: int,
    only_mart: str | None,
) -> dict[str, int]:
    validate_database_path(db_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    DUCKDB_TEMP_DIRECTORY.mkdir(parents=True, exist_ok=True)

    row_counts: dict[str, int] = {}
    with duckdb.connect(str(db_path)) as con:
        configure_duckdb_connection(con, DUCKDB_TEMP_DIRECTORY, memory_limit, threads)
        validate_required_tables(con)
        selected_queries = get_queries_to_run(only_mart)
        for mart_name, query in selected_queries.items():
            row_counts[mart_name] = create_mart(con, mart_name, query)
            export_mart(con, mart_name, output_dir)

    return row_counts


def main() -> None:
    args = parse_args()
    try:
        print(f"Base DuckDB: {args.db}")
        print(f"Directorio de salida: {args.output_dir}")
        row_counts = create_dashboard_tables(
            args.db,
            args.output_dir,
            args.memory_limit,
            args.threads,
            args.only_mart,
        )
    except Exception as exc:  # noqa: BLE001 - convert technical failures to clear CLI output.
        print(f"Error al crear la capa analitica: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print()
    print("Marts creados:")
    for mart_name, row_count in row_counts.items():
        print(f"  {mart_name}: {row_count:,} filas")


if __name__ == "__main__":
    main()
