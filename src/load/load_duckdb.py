"""Load cleaned SEPA data from nested ZIP files into DuckDB."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
import uuid
from datetime import date, datetime, timezone
from io import BytesIO, TextIOWrapper
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import duckdb
import pandas as pd


COMERCIO_COLUMNS = [
    "id_comercio",
    "id_bandera",
    "comercio_cuit",
    "comercio_razon_social",
    "comercio_bandera_nombre",
    "comercio_bandera_url",
    "comercio_ultima_actualizacion",
    "comercio_version_sepa",
]

PRODUCTOS_COLUMNS = [
    "id_comercio",
    "id_bandera",
    "id_sucursal",
    "id_producto",
    "productos_ean",
    "productos_descripcion",
    "productos_cantidad_presentacion",
    "productos_unidad_medida_presentacion",
    "productos_marca",
    "productos_precio_lista",
    "productos_precio_referencia",
    "productos_cantidad_referencia",
    "productos_unidad_medida_referencia",
    "productos_precio_unitario_promo1",
    "productos_leyenda_promo1",
    "productos_precio_unitario_promo2",
    "productos_leyenda_promo2",
]

SUCURSALES_COLUMNS = [
    "id_comercio",
    "id_bandera",
    "id_sucursal",
    "sucursales_nombre",
    "sucursales_tipo",
    "sucursales_calle",
    "sucursales_numero",
    "sucursales_latitud",
    "sucursales_longitud",
    "sucursales_observaciones",
    "sucursales_barrio",
    "sucursales_codigo_postal",
    "sucursales_localidad",
    "sucursales_provincia",
    "sucursales_lunes_horario_atencion",
    "sucursales_martes_horario_atencion",
    "sucursales_miercoles_horario_atencion",
    "sucursales_jueves_horario_atencion",
    "sucursales_viernes_horario_atencion",
    "sucursales_sabado_horario_atencion",
    "sucursales_domingo_horario_atencion",
]

TABLE_SPECS = {
    "dim_comercios": {
        "file": "comercio.csv",
        "source_columns": COMERCIO_COLUMNS,
        "output_columns": COMERCIO_COLUMNS + ["fecha_publicacion", "archivo_origen"],
        "numeric_columns": [],
        "date_columns": ["comercio_ultima_actualizacion"],
    },
    "dim_sucursales": {
        "file": "sucursales.csv",
        "source_columns": SUCURSALES_COLUMNS,
        "output_columns": [
            "id_comercio",
            "id_bandera",
            "id_sucursal",
            "sucursales_nombre",
            "sucursales_tipo",
            "sucursales_calle",
            "sucursales_numero",
            "sucursales_latitud",
            "sucursales_longitud",
            "sucursales_barrio",
            "sucursales_codigo_postal",
            "sucursales_localidad",
            "sucursales_provincia",
            "fecha_publicacion",
            "archivo_origen",
        ],
        "numeric_columns": ["sucursales_latitud", "sucursales_longitud"],
        "date_columns": [],
    },
    "fact_precios": {
        "file": "productos.csv",
        "source_columns": PRODUCTOS_COLUMNS,
        "output_columns": [
            "fecha_publicacion",
            "id_comercio",
            "id_bandera",
            "id_sucursal",
            "id_producto",
            "productos_ean",
            "productos_descripcion",
            "productos_cantidad_presentacion",
            "productos_unidad_medida_presentacion",
            "productos_marca",
            "productos_precio_lista",
            "productos_precio_referencia",
            "productos_cantidad_referencia",
            "productos_unidad_medida_referencia",
            "productos_precio_unitario_promo1",
            "productos_leyenda_promo1",
            "productos_precio_unitario_promo2",
            "productos_leyenda_promo2",
            "archivo_origen",
        ],
        "numeric_columns": [
            "productos_cantidad_presentacion",
            "productos_precio_lista",
            "productos_precio_referencia",
            "productos_cantidad_referencia",
            "productos_precio_unitario_promo1",
            "productos_precio_unitario_promo2",
        ],
        "date_columns": [],
    },
}

CREATE_TABLE_SQL = {
    "dim_comercios": """
        CREATE TABLE IF NOT EXISTS dim_comercios (
            id_comercio VARCHAR,
            id_bandera VARCHAR,
            comercio_cuit VARCHAR,
            comercio_razon_social VARCHAR,
            comercio_bandera_nombre VARCHAR,
            comercio_bandera_url VARCHAR,
            comercio_ultima_actualizacion TIMESTAMP,
            comercio_version_sepa VARCHAR,
            fecha_publicacion DATE,
            archivo_origen VARCHAR
        )
    """,
    "dim_sucursales": """
        CREATE TABLE IF NOT EXISTS dim_sucursales (
            id_comercio VARCHAR,
            id_bandera VARCHAR,
            id_sucursal VARCHAR,
            sucursales_nombre VARCHAR,
            sucursales_tipo VARCHAR,
            sucursales_calle VARCHAR,
            sucursales_numero VARCHAR,
            sucursales_latitud DOUBLE,
            sucursales_longitud DOUBLE,
            sucursales_barrio VARCHAR,
            sucursales_codigo_postal VARCHAR,
            sucursales_localidad VARCHAR,
            sucursales_provincia VARCHAR,
            fecha_publicacion DATE,
            archivo_origen VARCHAR
        )
    """,
    "fact_precios": """
        CREATE TABLE IF NOT EXISTS fact_precios (
            fecha_publicacion DATE,
            id_comercio VARCHAR,
            id_bandera VARCHAR,
            id_sucursal VARCHAR,
            id_producto VARCHAR,
            productos_ean VARCHAR,
            productos_descripcion VARCHAR,
            productos_cantidad_presentacion DOUBLE,
            productos_unidad_medida_presentacion VARCHAR,
            productos_marca VARCHAR,
            productos_precio_lista DOUBLE,
            productos_precio_referencia DOUBLE,
            productos_cantidad_referencia DOUBLE,
            productos_unidad_medida_referencia VARCHAR,
            productos_precio_unitario_promo1 DOUBLE,
            productos_leyenda_promo1 VARCHAR,
            productos_precio_unitario_promo2 DOUBLE,
            productos_leyenda_promo2 VARCHAR,
            archivo_origen VARCHAR
        )
    """,
}

CREATE_CONTROL_INGESTAS_SQL = """
    CREATE TABLE IF NOT EXISTS control_ingestas (
        id_ingesta VARCHAR,
        started_at TIMESTAMP,
        finished_at TIMESTAMP,
        zip_path VARCHAR,
        zip_filename VARCHAR,
        fechas_publicacion VARCHAR,
        modo_carga VARCHAR,
        estado VARCHAR,
        filas_dim_comercios BIGINT,
        filas_dim_sucursales BIGINT,
        filas_fact_precios BIGINT,
        errores INTEGER,
        detalle VARCHAR
    )
"""


def _base_name(name: str) -> str:
    return Path(name).name.lower()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def infer_fecha_publicacion(inner_name: str) -> pd.Timestamp | pd.NaT:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", inner_name)
    if not match:
        return pd.NaT
    return pd.to_datetime(match.group(1), errors="coerce")


def parse_publication_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "La fecha debe tener formato YYYY-MM-DD."
        ) from exc


def publication_date_as_timestamp(value: date | None) -> pd.Timestamp | None:
    if value is None:
        return None
    return pd.Timestamp(value.isoformat())


def normalize_number(series: pd.Series) -> pd.Series:
    values = series.astype("string").str.strip()
    has_comma = values.str.contains(",", regex=False, na=False)
    values = values.mask(
        has_comma,
        values.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    return pd.to_numeric(values, errors="coerce")


def clean_dataframe(
    df: pd.DataFrame,
    source_columns: list[str],
    numeric_columns: list[str],
    date_columns: list[str],
    fecha_publicacion: pd.Timestamp | pd.NaT,
    archivo_origen: str,
) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna(how="all")

    first_column = source_columns[0]
    if first_column in df.columns:
        first_values = df[first_column].astype("string").str.strip()
        normalized_first_values = first_values.map(
            lambda value: _normalize_text(str(value)).lower()
        )
        df = df[~normalized_first_values.str.startswith("ultima actualizacion", na=False)]
        first_values = df[first_column].astype("string").str.strip()
        df = df[first_values.str.fullmatch(r"\d+", na=False)]

    df = df[source_columns]
    for column in source_columns:
        df[column] = df[column].astype("string").str.strip()
        df[column] = df[column].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    for column in numeric_columns:
        df[column] = normalize_number(df[column])

    for column in date_columns:
        df[column] = pd.to_datetime(df[column], errors="coerce")

    df["fecha_publicacion"] = fecha_publicacion
    df["archivo_origen"] = archivo_origen
    return df


def iter_inner_csv_chunks(
    inner_zip: ZipFile,
    csv_name: str,
    source_columns: list[str],
    numeric_columns: list[str],
    date_columns: list[str],
    fecha_publicacion: pd.Timestamp | pd.NaT,
    archivo_origen: str,
) -> pd.DataFrame:
    chunk_rows: list[list[str]] = []
    with inner_zip.open(csv_name) as raw_file:
        text_file = TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
        reader = csv.reader(text_file, delimiter="|")
        header = next(reader, None)
        if header is None:
            return

        header = [column.strip() for column in header]
        if header != source_columns:
            raise ValueError(f"Encabezado inesperado: {header}")

        expected_len = len(source_columns)
        for row in reader:
            if not row or all(not value.strip() for value in row):
                continue
            if len(row) != expected_len:
                continue

            chunk_rows.append(row)
            if len(chunk_rows) >= 250_000:
                df = pd.DataFrame(chunk_rows, columns=source_columns, dtype="string")
                yield clean_dataframe(
                    df=df,
                    source_columns=source_columns,
                    numeric_columns=numeric_columns,
                    date_columns=date_columns,
                    fecha_publicacion=fecha_publicacion,
                    archivo_origen=archivo_origen,
                )
                chunk_rows = []

    if chunk_rows:
        df = pd.DataFrame(chunk_rows, columns=source_columns, dtype="string")
        yield clean_dataframe(
            df=df,
            source_columns=source_columns,
            numeric_columns=numeric_columns,
            date_columns=date_columns,
            fecha_publicacion=fecha_publicacion,
            archivo_origen=archivo_origen,
        )


def ensure_tables(con: duckdb.DuckDBPyConnection, replace: bool) -> None:
    for table_name, sql in CREATE_TABLE_SQL.items():
        if replace:
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(sql)
    if replace:
        con.execute("DROP TABLE IF EXISTS control_ingestas")
    con.execute(CREATE_CONTROL_INGESTAS_SQL)


def create_ingestion_record(
    con: duckdb.DuckDBPyConnection,
    zip_path: Path,
    mode: str,
) -> str:
    ingestion_id = str(uuid.uuid4())
    con.execute(
        """
        INSERT INTO control_ingestas (
            id_ingesta,
            started_at,
            zip_path,
            zip_filename,
            modo_carga,
            estado,
            filas_dim_comercios,
            filas_dim_sucursales,
            filas_fact_precios,
            errores,
            detalle
        )
        VALUES (?, ?, ?, ?, ?, 'running', 0, 0, 0, 0, NULL)
        """,
        [
            ingestion_id,
            datetime.now(timezone.utc),
            str(zip_path),
            zip_path.name,
            mode,
        ],
    )
    return ingestion_id


def finish_ingestion_record(
    con: duckdb.DuckDBPyConnection,
    ingestion_id: str,
    *,
    status: str,
    fechas_publicacion: list[str],
    counts: dict[str, int],
    errors: list[str],
    detail: str | None = None,
) -> None:
    detail_payload = {
        "detalle": detail,
        "errores": errors[:100],
    }
    con.execute(
        """
        UPDATE control_ingestas
        SET
            finished_at = ?,
            fechas_publicacion = ?,
            estado = ?,
            filas_dim_comercios = ?,
            filas_dim_sucursales = ?,
            filas_fact_precios = ?,
            errores = ?,
            detalle = ?
        WHERE id_ingesta = ?
        """,
        [
            datetime.now(timezone.utc),
            json.dumps(fechas_publicacion, ensure_ascii=True),
            status,
            counts.get("dim_comercios", 0),
            counts.get("dim_sucursales", 0),
            counts.get("fact_precios", 0),
            len(errors),
            json.dumps(detail_payload, ensure_ascii=True),
            ingestion_id,
        ],
    )


def fecha_key(fecha_publicacion: pd.Timestamp | pd.NaT) -> str | None:
    if pd.isna(fecha_publicacion):
        return None
    return pd.Timestamp(fecha_publicacion).date().isoformat()


def existing_publication_dates(con: duckdb.DuckDBPyConnection) -> set[str]:
    try:
        rows = con.execute(
            """
            SELECT DISTINCT fecha_publicacion
            FROM fact_precios
            WHERE fecha_publicacion IS NOT NULL
            """
        ).fetchall()
    except duckdb.CatalogException:
        return set()
    return {str(row[0]) for row in rows if row[0] is not None}


def delete_publication_dates(
    con: duckdb.DuckDBPyConnection,
    fechas_publicacion: set[str],
) -> None:
    if not fechas_publicacion:
        return
    for table_name in TABLE_SPECS:
        for date_key in sorted(fechas_publicacion):
            con.execute(
                f"DELETE FROM {table_name} WHERE fecha_publicacion = ?",
                [date_key],
            )


def insert_dataframe(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    df: pd.DataFrame,
    output_columns: list[str],
) -> int:
    if df.empty:
        return 0

    df = df[output_columns]
    con.register("df_to_insert", df)
    columns_sql = ", ".join(output_columns)
    con.execute(f"INSERT INTO {table_name} ({columns_sql}) SELECT {columns_sql} FROM df_to_insert")
    con.unregister("df_to_insert")
    return len(df)


def load_zip_to_duckdb(
    zip_path: Path,
    db_path: Path,
    replace: bool = True,
    *,
    publication_date: date | None = None,
    reload_existing_dates: bool = False,
) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    counts = {table_name: 0 for table_name in TABLE_SPECS}
    errors: list[str] = []
    processed_dates: set[str] = set()
    skipped_dates: set[str] = set()
    forced_publication_date = publication_date_as_timestamp(publication_date)

    with duckdb.connect(str(db_path)) as con:
        ensure_tables(con, replace=replace)
        ingestion_id = create_ingestion_record(
            con,
            zip_path,
            "replace" if replace else "append",
        )

        try:
            with ZipFile(zip_path) as outer_zip:
                inner_names = [
                    name
                    for name in outer_zip.namelist()
                    if name.lower().endswith(".zip") and not name.endswith("/")
                ]

                print(f"ZIPs internos encontrados: {len(inner_names)}")
                fechas_in_zip = {
                    key
                    for key in (
                        fecha_key(forced_publication_date or infer_fecha_publicacion(name))
                        for name in inner_names
                    )
                    if key is not None
                }
                existing_dates = set() if replace else existing_publication_dates(con)
                if reload_existing_dates:
                    delete_publication_dates(con, fechas_in_zip)
                    existing_dates = existing_publication_dates(con)

                for index, inner_name in enumerate(inner_names, start=1):
                    try:
                        fecha_publicacion = (
                            forced_publication_date or infer_fecha_publicacion(inner_name)
                        )
                        date_key = fecha_key(fecha_publicacion)
                        if date_key in existing_dates:
                            skipped_dates.add(date_key)
                            continue

                        inner_bytes = outer_zip.read(inner_name)
                        if not inner_bytes:
                            raise ValueError("ZIP interno vacio.")

                        with ZipFile(BytesIO(inner_bytes)) as inner_zip:
                            inner_files = {
                                _base_name(name): name
                                for name in inner_zip.namelist()
                                if not name.endswith("/")
                            }

                            for table_name, spec in TABLE_SPECS.items():
                                csv_file = inner_files.get(str(spec["file"]))
                                if csv_file is None:
                                    errors.append(f"{inner_name}: falta {spec['file']}")
                                    continue

                                for df in iter_inner_csv_chunks(
                                    inner_zip=inner_zip,
                                    csv_name=csv_file,
                                    source_columns=list(spec["source_columns"]),
                                    numeric_columns=list(spec["numeric_columns"]),
                                    date_columns=list(spec["date_columns"]),
                                    fecha_publicacion=fecha_publicacion,
                                    archivo_origen=inner_name,
                                ):
                                    inserted = insert_dataframe(
                                        con=con,
                                        table_name=table_name,
                                        df=df,
                                        output_columns=list(spec["output_columns"]),
                                    )
                                    counts[table_name] += inserted

                        if date_key is not None:
                            processed_dates.add(date_key)

                        if index % 25 == 0 or index == len(inner_names):
                            print(f"Procesados {index}/{len(inner_names)} ZIPs internos.")
                    except BadZipFile:
                        errors.append(f"{inner_name}: ZIP interno corrupto.")
                    except Exception as exc:  # noqa: BLE001 - continue with other inner ZIPs.
                        errors.append(f"{inner_name}: {type(exc).__name__}: {exc}")

            export_tables(con, db_path.parent)
            status = "success"
            detail = None
            if not any(counts.values()) and skipped_dates:
                status = "skipped"
                detail = "Fechas ya cargadas; no se insertaron filas nuevas."
            elif errors:
                status = "success_with_warnings"
            finish_ingestion_record(
                con,
                ingestion_id,
                status=status,
                fechas_publicacion=sorted(processed_dates | skipped_dates),
                counts=counts,
                errors=errors,
                detail=detail,
            )
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            finish_ingestion_record(
                con,
                ingestion_id,
                status="failed",
                fechas_publicacion=sorted(processed_dates | skipped_dates),
                counts=counts,
                errors=errors,
            )
            raise

    print()
    print("Filas cargadas:")
    for table_name, count in counts.items():
        print(f"  {table_name}: {count}")
    if skipped_dates:
        print(f"Fechas omitidas por estar cargadas: {', '.join(sorted(skipped_dates))}")

    if errors:
        print()
        print(f"Advertencias/errores no fatales: {len(errors)}")
        for error in errors[:20]:
            print(f"  - {error}")
        if len(errors) > 20:
            print("  - ...")

    return counts


def export_tables(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for table_name in TABLE_SPECS:
        csv_path = output_dir / f"{table_name}.csv"
        parquet_path = output_dir / f"{table_name}.parquet"
        con.execute(f"COPY {table_name} TO ? (HEADER, DELIMITER ',')", [str(csv_path)])
        try:
            con.execute(f"COPY {table_name} TO ? (FORMAT PARQUET)", [str(parquet_path)])
        except Exception as exc:  # noqa: BLE001 - CSV export is the required fallback.
            print(f"No se pudo exportar Parquet para {table_name}: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Carga datos SEPA limpios en DuckDB.")
    parser.add_argument("--zip", required=True, type=Path, help="Ruta del ZIP principal.")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/processed/precios_diarios.duckdb"),
        help="Ruta de la base DuckDB.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Agrega datos a tablas existentes en vez de recrearlas.",
    )
    parser.add_argument(
        "--date",
        type=parse_publication_date,
        help="Fuerza fecha_publicacion para todos los ZIPs internos (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--reload-existing-dates",
        action="store_true",
        help="Borra y vuelve a cargar las fechas presentes en el ZIP.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.zip.exists():
        raise FileNotFoundError(f"No existe el ZIP principal: {args.zip}")

    load_zip_to_duckdb(
        zip_path=args.zip,
        db_path=args.db,
        replace=not args.append,
        publication_date=args.date,
        reload_existing_dates=args.reload_existing_dates,
    )
    print()
    print(f"Base DuckDB: {args.db}")
    print(f"Exportaciones: {args.db.parent}")


if __name__ == "__main__":
    main()
