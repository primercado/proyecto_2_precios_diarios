"""Inspect nested SEPA ZIP files without extracting raw data."""

from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import BytesIO, TextIOWrapper
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile


EXPECTED_COLUMNS: dict[str, list[str]] = {
    "comercio.csv": [
        "id_comercio",
        "id_bandera",
        "comercio_cuit",
        "comercio_razon_social",
        "comercio_bandera_nombre",
        "comercio_bandera_url",
        "comercio_ultima_actualizacion",
        "comercio_version_sepa",
    ],
    "productos.csv": [
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
    ],
    "sucursales.csv": [
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
    ],
}


def _csv_basename(name: str) -> str:
    return Path(name).name.lower()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _is_update_footer(row: list[str]) -> bool:
    first_value = _normalize_text(row[0].strip()).lower() if row else ""
    return first_value.startswith("ultima actualizacion")


def inspect_csv(inner_zip: ZipFile, csv_name: str, expected_columns: list[str]) -> dict[str, Any]:
    """Count rows and schema problems for one CSV inside an inner ZIP."""
    info = {
        "present": True,
        "empty": False,
        "header_ok": False,
        "rows_total": 0,
        "rows_valid": 0,
        "rows_invalid": 0,
        "footer_rows_removed": 0,
        "error": None,
    }

    try:
        with inner_zip.open(csv_name) as raw_file:
            text_file = TextIOWrapper(raw_file, encoding="utf-8-sig", newline="")
            reader = csv.reader(text_file, delimiter="|")
            header = next(reader, None)

            if header is None:
                info["empty"] = True
                return info

            header = [column.strip() for column in header]
            info["header_ok"] = header == expected_columns

            expected_len = len(expected_columns)
            for row in reader:
                if not row or all(not value.strip() for value in row):
                    continue
                if _is_update_footer(row):
                    info["footer_rows_removed"] += 1
                    continue

                info["rows_total"] += 1
                if len(row) == expected_len:
                    info["rows_valid"] += 1
                else:
                    info["rows_invalid"] += 1
    except UnicodeDecodeError:
        info["error"] = "No se pudo decodificar como UTF-8."
    except Exception as exc:  # noqa: BLE001 - inspection should continue with other files.
        info["error"] = f"{type(exc).__name__}: {exc}"

    return info


def inspect_zip(zip_path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "zip_path": str(zip_path),
        "inspected_at": datetime.now(timezone.utc).isoformat(),
        "inner_zips_total": 0,
        "inner_zips_valid": 0,
        "inner_zips_empty": 0,
        "inner_zips_corrupt": 0,
        "files_present": Counter(),
        "files_with_valid_header": Counter(),
        "rows_by_file": defaultdict(int),
        "invalid_rows_by_file": defaultdict(int),
        "footer_rows_removed_by_file": defaultdict(int),
        "errors": [],
        "inner_zips": [],
    }

    with ZipFile(zip_path) as outer_zip:
        inner_names = [
            name
            for name in outer_zip.namelist()
            if name.lower().endswith(".zip") and not name.endswith("/")
        ]
        summary["inner_zips_total"] = len(inner_names)

        for inner_name in inner_names:
            inner_result: dict[str, Any] = {
                "archivo_origen": inner_name,
                "files": {},
                "error": None,
            }

            try:
                inner_bytes = outer_zip.read(inner_name)
                if not inner_bytes:
                    summary["inner_zips_empty"] += 1
                    inner_result["error"] = "ZIP interno vacío."
                    summary["errors"].append(inner_result)
                    summary["inner_zips"].append(inner_result)
                    continue

                with ZipFile(BytesIO(inner_bytes)) as inner_zip:
                    inner_files_by_base = {
                        _csv_basename(name): name
                        for name in inner_zip.namelist()
                        if not name.endswith("/")
                    }

                    for base_name, expected_columns in EXPECTED_COLUMNS.items():
                        csv_name = inner_files_by_base.get(base_name)
                        if csv_name is None:
                            inner_result["files"][base_name] = {"present": False}
                            continue

                        summary["files_present"][base_name] += 1
                        csv_result = inspect_csv(inner_zip, csv_name, expected_columns)
                        inner_result["files"][base_name] = csv_result

                        if csv_result.get("header_ok"):
                            summary["files_with_valid_header"][base_name] += 1
                        summary["rows_by_file"][base_name] += int(csv_result["rows_valid"])
                        summary["invalid_rows_by_file"][base_name] += int(
                            csv_result["rows_invalid"]
                        )
                        summary["footer_rows_removed_by_file"][base_name] += int(
                            csv_result["footer_rows_removed"]
                        )

                        if csv_result.get("error"):
                            summary["errors"].append(
                                {
                                    "archivo_origen": inner_name,
                                    "archivo_csv": base_name,
                                    "error": csv_result["error"],
                                }
                            )

                summary["inner_zips_valid"] += 1
            except BadZipFile:
                summary["inner_zips_corrupt"] += 1
                inner_result["error"] = "ZIP interno corrupto."
                summary["errors"].append(inner_result)
            except Exception as exc:  # noqa: BLE001 - inspection should continue.
                inner_result["error"] = f"{type(exc).__name__}: {exc}"
                summary["errors"].append(inner_result)

            summary["inner_zips"].append(inner_result)

    for key in (
        "files_present",
        "files_with_valid_header",
        "rows_by_file",
        "invalid_rows_by_file",
        "footer_rows_removed_by_file",
    ):
        summary[key] = dict(summary[key])

    return summary


def print_summary(summary: dict[str, Any]) -> None:
    print(f"ZIP principal: {summary['zip_path']}")
    print(f"ZIPs internos encontrados: {summary['inner_zips_total']}")
    print(f"ZIPs internos legibles: {summary['inner_zips_valid']}")
    print(f"ZIPs internos vacíos: {summary['inner_zips_empty']}")
    print(f"ZIPs internos corruptos: {summary['inner_zips_corrupt']}")
    print()

    for file_name in EXPECTED_COLUMNS:
        present = summary["files_present"].get(file_name, 0)
        headers_ok = summary["files_with_valid_header"].get(file_name, 0)
        rows = summary["rows_by_file"].get(file_name, 0)
        invalid = summary["invalid_rows_by_file"].get(file_name, 0)
        footers = summary["footer_rows_removed_by_file"].get(file_name, 0)
        print(f"{file_name}:")
        print(f"  presentes: {present}")
        print(f"  encabezado válido: {headers_ok}")
        print(f"  filas válidas: {rows}")
        print(f"  filas inválidas: {invalid}")
        print(f"  líneas de actualización removidas: {footers}")

    if summary["errors"]:
        print()
        print(f"Errores detectados: {len(summary['errors'])}")
        for error in summary["errors"][:10]:
            print(f"  - {error}")
        if len(summary["errors"]) > 10:
            print("  - ...")


def save_summary(summary: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspecciona un ZIP principal de SEPA.")
    parser.add_argument("--zip", required=True, type=Path, help="Ruta del ZIP principal.")
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=Path("data/processed/inspection_summary.json"),
        help="Ruta para guardar el resumen JSON.",
    )
    parser.add_argument(
        "--no-summary-json",
        action="store_true",
        help="No guarda el resumen JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.zip.exists():
        raise FileNotFoundError(f"No existe el ZIP principal: {args.zip}")

    summary = inspect_zip(args.zip)
    print_summary(summary)

    if not args.no_summary_json:
        save_summary(summary, args.summary_json)
        print()
        print(f"Resumen JSON guardado en: {args.summary_json}")


if __name__ == "__main__":
    main()
