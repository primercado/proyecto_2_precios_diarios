"""Run the SEPA daily pipeline end to end."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from src.analysis.create_dashboard_tables import (
    DEFAULT_DUCKDB_MEMORY_LIMIT,
    DEFAULT_DUCKDB_THREADS,
    create_dashboard_tables,
)
from src.extract.sepa_api import (
    DEFAULT_RAW_DIR,
    SEPA_MINORISTAS_DATASET,
    download_resource,
    download_latest_zip,
    download_zip_for_date,
    list_resources,
    recent_zip_resources,
)
from src.load.load_duckdb import load_zip_to_duckdb, parse_publication_date


DEFAULT_DB_PATH = Path("data/processed/precios_diarios.duckdb")
DEFAULT_DASHBOARD_DIR = Path("data/processed/dashboard")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta descarga, carga incremental y marts de dashboard."
    )
    parser.add_argument(
        "--date",
        type=parse_publication_date,
        help="Fecha SEPA a descargar/cargar, en formato YYYY-MM-DD.",
    )
    parser.add_argument(
        "--zip",
        type=Path,
        help="ZIP principal ya descargado. Si se informa, no se descarga desde CKAN.",
    )
    parser.add_argument(
        "--last-days",
        type=int,
        help=(
            "Descarga y carga las publicaciones disponibles de los ultimos N dias, "
            "tomando como referencia la fecha mas reciente publicada por SEPA."
        ),
    )
    parser.add_argument(
        "--dataset-id",
        default=SEPA_MINORISTAS_DATASET,
        help="ID del dataset CKAN. Por defecto: sepa-precios.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="Directorio donde guardar ZIPs descargados.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Ruta de la base DuckDB.",
    )
    parser.add_argument(
        "--dashboard-output-dir",
        type=Path,
        default=DEFAULT_DASHBOARD_DIR,
        help="Directorio para exportar CSV y Parquet de marts.",
    )
    parser.add_argument(
        "--overwrite-download",
        action="store_true",
        help="Vuelve a descargar el ZIP aunque exista localmente.",
    )
    parser.add_argument(
        "--reload-existing-dates",
        action="store_true",
        help="Borra y vuelve a cargar fechas ya presentes en DuckDB.",
    )
    parser.add_argument(
        "--replace-db",
        action="store_true",
        help="Recrea tablas limpias en vez de cargar incrementalmente.",
    )
    parser.add_argument(
        "--skip-marts",
        action="store_true",
        help="Carga DuckDB pero no recrea marts de dashboard.",
    )
    parser.add_argument(
        "--memory-limit",
        default=DEFAULT_DUCKDB_MEMORY_LIMIT,
        help="Limite de memoria para crear marts. Default: %(default)s.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=DEFAULT_DUCKDB_THREADS,
        help="Threads DuckDB para crear marts. Default: %(default)s.",
    )
    args = parser.parse_args()
    validate_args(parser, args)
    return args


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    selected_sources = sum(
        [
            args.zip is not None,
            args.date is not None,
            args.last_days is not None,
        ]
    )
    if selected_sources > 1:
        parser.error("usar solo una opcion entre --zip, --date o --last-days.")

    if args.last_days is not None and args.last_days < 1:
        parser.error("--last-days debe ser mayor o igual a 1.")


def resolve_zip_path(
    *,
    zip_path: Path | None,
    publication_date: date | None,
    dataset_id: str,
    raw_dir: Path,
    overwrite_download: bool,
) -> Path:
    if zip_path is not None:
        if not zip_path.exists():
            raise FileNotFoundError(f"No existe el ZIP principal: {zip_path}")
        return zip_path

    if publication_date is not None:
        print(f"Descargando ZIP SEPA para fecha {publication_date.isoformat()}...")
        return download_zip_for_date(
            publication_date,
            dataset_id=dataset_id,
            output_dir=raw_dir,
            overwrite=overwrite_download,
        )

    print("Descargando ultimo ZIP SEPA disponible...")
    return download_latest_zip(
        dataset_id=dataset_id,
        output_dir=raw_dir,
        overwrite=overwrite_download,
    )


def resolve_recent_zip_paths(
    *,
    days: int,
    dataset_id: str,
    raw_dir: Path,
    overwrite_download: bool,
) -> list[tuple[date, Path]]:
    print(f"Buscando publicaciones SEPA disponibles para los ultimos {days} dias...")
    resources = list_resources(dataset_id)
    recent_resources = recent_zip_resources(resources, days)
    if not recent_resources:
        raise RuntimeError(f"No se encontraron ZIPs SEPA para los ultimos {days} dias.")

    print(f"Publicaciones detectadas: {len(recent_resources)}")
    zip_paths: list[tuple[date, Path]] = []
    for publication_date, resource in recent_resources:
        print(f"Descargando ZIP SEPA para fecha {publication_date.isoformat()}...")
        zip_paths.append(
            (
                publication_date,
                download_resource(
                    resource,
                    output_dir=raw_dir,
                    overwrite=overwrite_download,
                ),
            )
        )
    return zip_paths


def load_zip_paths(
    *,
    zip_paths: list[tuple[date | None, Path]],
    db_path: Path,
    replace_db: bool,
    reload_existing_dates: bool,
) -> dict[str, int]:
    total_counts: dict[str, int] = {}
    for index, (publication_date, zip_path) in enumerate(zip_paths, start=1):
        should_replace = replace_db and index == 1
        print()
        print(f"Cargando {index}/{len(zip_paths)}: {zip_path}")
        counts = load_zip_to_duckdb(
            zip_path=zip_path,
            db_path=db_path,
            replace=should_replace,
            publication_date=publication_date,
            reload_existing_dates=reload_existing_dates,
        )
        for table_name, count in counts.items():
            total_counts[table_name] = total_counts.get(table_name, 0) + count

    return total_counts


def main() -> None:
    args = parse_args()

    if args.last_days is not None:
        zip_paths = resolve_recent_zip_paths(
            days=args.last_days,
            dataset_id=args.dataset_id,
            raw_dir=args.raw_dir,
            overwrite_download=args.overwrite_download,
        )
    else:
        zip_path = resolve_zip_path(
            zip_path=args.zip,
            publication_date=args.date,
            dataset_id=args.dataset_id,
            raw_dir=args.raw_dir,
            overwrite_download=args.overwrite_download,
        )
        zip_paths = [(args.date, zip_path)]

    print(f"ZIPs principales: {len(zip_paths)}")
    print(f"Base DuckDB: {args.db}")
    counts = load_zip_paths(
        zip_paths=zip_paths,
        db_path=args.db,
        replace_db=args.replace_db,
        reload_existing_dates=args.reload_existing_dates,
    )

    if args.skip_marts:
        print("Creacion de marts omitida por --skip-marts.")
        return

    print()
    print("Creando marts de dashboard...")
    mart_counts = create_dashboard_tables(
        db_path=args.db,
        output_dir=args.dashboard_output_dir,
        memory_limit=args.memory_limit,
        threads=args.threads,
        only_mart=None,
    )

    print()
    print("Pipeline finalizado.")
    print(f"Filas cargadas: {counts}")
    print(f"Marts creados: {mart_counts}")


if __name__ == "__main__":
    main()
