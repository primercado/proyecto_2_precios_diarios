"""Extractor para recursos SEPA publicados en CKAN.

Uso:
    python -m src.extract.sepa_api --list
    python -m src.extract.sepa_api --list-dates
    python -m src.extract.sepa_api --download
    python -m src.extract.sepa_api --date 2026-05-23
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


CKAN_API_BASE_URL = "https://datos.produccion.gob.ar/api/3/action"
SEPA_MINORISTAS_DATASET = "sepa-precios"
DEFAULT_RAW_DIR = Path("data/raw")
REQUEST_TIMEOUT = 60
CHUNK_SIZE = 1024 * 1024


class SepaApiError(RuntimeError):
    """Error al consultar o descargar datos de SEPA."""


@dataclass(frozen=True)
class SepaResource:
    """Metadatos utiles de un recurso CKAN."""

    id: str
    name: str
    format: str
    url: str
    created: str | None = None
    metadata_modified: str | None = None
    last_modified: str | None = None

    @classmethod
    def from_ckan(cls, resource: dict[str, Any]) -> "SepaResource":
        return cls(
            id=str(resource.get("id", "")),
            name=str(resource.get("name") or resource.get("description") or ""),
            format=str(resource.get("format") or ""),
            url=str(resource.get("url") or ""),
            created=resource.get("created"),
            metadata_modified=resource.get("metadata_modified"),
            last_modified=resource.get("last_modified"),
        )

    @property
    def is_zip(self) -> bool:
        return self.format.lower() == "zip" or self.url.lower().endswith(".zip")


def _ckan_get(
    action: str,
    params: dict[str, Any] | None = None,
    *,
    api_base_url: str = CKAN_API_BASE_URL,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    http = session or requests.Session()
    url = f"{api_base_url.rstrip('/')}/{action}"

    try:
        response = http.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SepaApiError(f"No se pudo consultar CKAN: {url}") from exc

    payload = response.json()
    if not payload.get("success"):
        error = payload.get("error") or payload
        raise SepaApiError(f"CKAN respondio con error: {error}")

    return payload["result"]


def list_resources(
    dataset_id: str = SEPA_MINORISTAS_DATASET,
    *,
    api_base_url: str = CKAN_API_BASE_URL,
    session: requests.Session | None = None,
) -> list[SepaResource]:
    """Lista los recursos disponibles para el dataset SEPA indicado."""

    dataset = _ckan_get(
        "package_show",
        {"id": dataset_id},
        api_base_url=api_base_url,
        session=session,
    )
    return [SepaResource.from_ckan(resource) for resource in dataset.get("resources", [])]


def latest_zip_resource(resources: list[SepaResource]) -> SepaResource:
    """Devuelve el recurso ZIP mas reciente segun metadatos y nombre."""

    zip_resources = [resource for resource in resources if resource.is_zip and resource.url]
    if not zip_resources:
        raise SepaApiError("No se encontraron recursos ZIP disponibles.")

    return max(zip_resources, key=_resource_sort_key)


def zip_resource_for_date(resources: list[SepaResource], publication_date: date) -> SepaResource:
    """Devuelve el recurso ZIP que corresponde a una fecha de publicacion."""

    dated_resources = [
        resource
        for resource in resources
        if resource.is_zip
        and resource.url
        and _resource_publication_date(resource) == publication_date
    ]
    if not dated_resources:
        raise SepaApiError(
            "No se encontro un recurso ZIP para la fecha "
            f"{publication_date.isoformat()}."
        )

    return max(dated_resources, key=_resource_sort_key)


def list_available_dates(resources: list[SepaResource]) -> list[date]:
    """Lista fechas de publicacion disponibles para recursos ZIP de SEPA."""

    available_dates = {
        publication_date
        for resource in resources
        if resource.is_zip and resource.url
        for publication_date in [_resource_publication_date(resource)]
        if publication_date is not None
    }
    return sorted(available_dates)


def download_resource(
    resource: SepaResource,
    output_dir: Path | str = DEFAULT_RAW_DIR,
    *,
    overwrite: bool = False,
    session: requests.Session | None = None,
) -> Path:
    """Descarga un recurso CKAN en el directorio indicado."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = _filename_for_resource(resource)
    destination = output_path / filename
    if destination.exists() and not overwrite:
        return destination

    tmp_destination = destination.with_suffix(destination.suffix + ".tmp")
    http = session or requests.Session()

    try:
        with http.get(resource.url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            with tmp_destination.open("wb") as file:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        file.write(chunk)
    except requests.RequestException as exc:
        tmp_destination.unlink(missing_ok=True)
        raise SepaApiError(f"No se pudo descargar el recurso: {resource.url}") from exc
    except OSError:
        tmp_destination.unlink(missing_ok=True)
        raise

    tmp_destination.replace(destination)
    return destination


def download_latest_zip(
    dataset_id: str = SEPA_MINORISTAS_DATASET,
    output_dir: Path | str = DEFAULT_RAW_DIR,
    *,
    api_base_url: str = CKAN_API_BASE_URL,
    overwrite: bool = False,
    session: requests.Session | None = None,
) -> Path:
    """Lista recursos, elige el ZIP mas reciente y lo descarga."""

    resources = list_resources(dataset_id, api_base_url=api_base_url, session=session)
    latest_resource = latest_zip_resource(resources)
    return download_resource(
        latest_resource,
        output_dir,
        overwrite=overwrite,
        session=session,
    )


def download_zip_for_date(
    publication_date: date,
    dataset_id: str = SEPA_MINORISTAS_DATASET,
    output_dir: Path | str = DEFAULT_RAW_DIR,
    *,
    api_base_url: str = CKAN_API_BASE_URL,
    overwrite: bool = False,
    session: requests.Session | None = None,
) -> Path:
    """Lista recursos, elige el ZIP de la fecha indicada y lo descarga."""

    resources = list_resources(dataset_id, api_base_url=api_base_url, session=session)
    dated_resource = zip_resource_for_date(resources, publication_date)
    return download_resource(
        dated_resource,
        output_dir,
        overwrite=overwrite,
        session=session,
    )


def _resource_sort_key(resource: SepaResource) -> tuple[datetime, datetime]:
    metadata_date = _parse_ckan_datetime(
        resource.last_modified or resource.metadata_modified or resource.created
    )
    name_date = _parse_date_from_text(resource.name)
    return metadata_date, name_date


def _parse_ckan_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_date_from_text(value: str) -> datetime:
    match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", value)
    if not match:
        return datetime.min.replace(tzinfo=timezone.utc)

    try:
        return datetime(
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            tzinfo=timezone.utc,
        )
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _resource_publication_date(resource: SepaResource) -> date | None:
    for value in (resource.name, resource.url):
        parsed = _parse_date_from_text(value)
        if parsed != datetime.min.replace(tzinfo=timezone.utc):
            return parsed.date()

    metadata_date = _parse_ckan_datetime(
        resource.last_modified or resource.metadata_modified or resource.created
    )
    if metadata_date != datetime.min.replace(tzinfo=timezone.utc):
        return metadata_date.date()

    return None


def _parse_publication_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "La fecha debe tener formato YYYY-MM-DD."
        ) from exc


def _filename_for_resource(resource: SepaResource) -> str:
    parsed_name = Path(urlparse(resource.url).path).name
    if parsed_name.lower().endswith(".zip"):
        return parsed_name

    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", resource.name.strip()).strip("_")
    return f"{slug or resource.id or 'sepa_resource'}.zip"


def _print_resources(resources: list[SepaResource]) -> None:
    for resource in resources:
        marker = "ZIP" if resource.is_zip else resource.format or "sin formato"
        modified = resource.last_modified or resource.metadata_modified or resource.created or "sin fecha"
        print(f"{marker:12} {modified:26} {resource.name} ({resource.id})")


def _print_available_dates(resources: list[SepaResource]) -> None:
    available_dates = list_available_dates(resources)
    for publication_date in available_dates:
        print(publication_date.isoformat())

    if not available_dates:
        print("No se encontraron fechas disponibles en recursos ZIP.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extractor de recursos SEPA desde CKAN.")
    parser.add_argument(
        "--dataset-id",
        default=SEPA_MINORISTAS_DATASET,
        help="ID del dataset CKAN. Por defecto: sepa-precios.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Directorio donde guardar el ZIP descargado.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista los recursos disponibles del dataset.",
    )
    parser.add_argument(
        "--list-dates",
        action="store_true",
        help="Lista fechas disponibles detectadas en recursos ZIP.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Descarga el ZIP mas reciente en el directorio de salida.",
    )
    parser.add_argument(
        "--date",
        type=_parse_publication_date,
        help=(
            "Descarga el ZIP correspondiente a la fecha indicada "
            "(formato YYYY-MM-DD)."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribe el archivo local si ya existe.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    resources = list_resources(args.dataset_id)
    if args.list_dates:
        _print_available_dates(resources)

    if args.list or (not args.list_dates and not args.download and args.date is None):
        _print_resources(resources)

    if args.download or args.date is not None:
        resource = (
            zip_resource_for_date(resources, args.date)
            if args.date is not None
            else latest_zip_resource(resources)
        )
        destination = download_resource(resource, args.output_dir, overwrite=args.overwrite)
        print(f"Descargado: {destination}")


if __name__ == "__main__":
    main()
