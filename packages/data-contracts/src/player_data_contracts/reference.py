from __future__ import annotations

import csv
import json
import math
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from importlib.resources import files
from numbers import Integral, Real
from pathlib import Path
from typing import Any, Final

from player_data_contracts.validation import ContractValidationError

REFERENCE_CONTRACT_VERSION: Final = 1

_REFERENCE_SCHEMA_NAME = "schemas/reference-v1.schema.json"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_INTEGER_PATTERN = re.compile(r"[+-]?\d+")


def load_reference_contract(
    version: int = REFERENCE_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Load the machine-readable normalized reference CSV contract."""
    if version != REFERENCE_CONTRACT_VERSION:
        raise ContractValidationError(f"Unsupported reference contract version: {version}")

    resource = files("player_data_contracts").joinpath(_REFERENCE_SCHEMA_NAME)
    try:
        with resource.open("r", encoding="utf-8") as handle:
            contract = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError(
            f"Unable to load reference contract version {version}: {error}"
        ) from error
    if not isinstance(contract, dict) or contract.get("contractVersion") != version:
        raise ContractValidationError(
            f"Reference contract resource does not declare version {version}"
        )
    _contract_files(contract)
    return contract


def _contract_files(contract: Mapping[str, Any]) -> Mapping[str, Any]:
    if contract.get("contractVersion") != REFERENCE_CONTRACT_VERSION:
        raise ContractValidationError(
            "Unsupported reference contract version: "
            f"{contract.get('contractVersion')!r}"
        )
    file_contracts = contract.get("files")
    if not isinstance(file_contracts, Mapping) or not file_contracts:
        raise ContractValidationError("Reference contract has no file definitions")
    return file_contracts


def _columns_for(file_name: str, file_contract: object) -> list[Mapping[str, Any]]:
    if not isinstance(file_contract, Mapping):
        raise ContractValidationError(
            f"Reference contract file definition {file_name} must be an object"
        )
    columns = file_contract.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ContractValidationError(
            f"Reference contract file {file_name} has no column definitions"
        )
    if any(not isinstance(column, Mapping) for column in columns):
        raise ContractValidationError(
            f"Reference contract file {file_name} has an invalid column definition"
        )
    names = [column.get("name") for column in columns]
    if any(not isinstance(name, str) or not name for name in names):
        raise ContractValidationError(
            f"Reference contract file {file_name} has an invalid column name"
        )
    if len(names) != len(set(names)):
        raise ContractValidationError(
            f"Reference contract file {file_name} has duplicate column names"
        )
    return columns


def _empty(value: object) -> bool:
    return value is None or value == ""


def _type_error(context: str, expected: str) -> ContractValidationError:
    return ContractValidationError(f"{context} must be {expected}")


def _integer(value: object, context: str) -> int:
    if isinstance(value, bool):
        raise _type_error(context, "an integer")
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        if math.isfinite(number) and number.is_integer():
            return int(number)
        raise _type_error(context, "an integer")
    if isinstance(value, str) and _INTEGER_PATTERN.fullmatch(value):
        return int(value)
    raise _type_error(context, "an integer")


def _number(value: object, context: str) -> float:
    if isinstance(value, bool):
        raise _type_error(context, "a finite number")
    if isinstance(value, Real):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value)
        except ValueError as error:
            raise _type_error(context, "a finite number") from error
    else:
        raise _type_error(context, "a finite number")
    if not math.isfinite(number):
        raise _type_error(context, "a finite number")
    return number


def _date(value: object, context: str) -> str:
    if isinstance(value, datetime):
        raise _type_error(context, "an ISO 8601 date")
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise _type_error(context, "an ISO 8601 date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise _type_error(context, "an ISO 8601 date") from error
    return parsed.isoformat()


def _datetime(value: object, context: str) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as error:
            raise _type_error(context, "an ISO 8601 datetime with a timezone") from error
    else:
        raise _type_error(context, "an ISO 8601 datetime with a timezone")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _type_error(context, "an ISO 8601 datetime with a timezone")
    return parsed.isoformat()


def _validate_value(value: object, column: Mapping[str, Any], context: str) -> object:
    required = column.get("required") is True
    nullable = column.get("nullable") is True
    if _empty(value):
        if required:
            raise ContractValidationError(f"{context} is required and cannot be empty")
        if not nullable:
            raise ContractValidationError(f"{context} is not nullable")
        return None

    field_type = column.get("type")
    if field_type == "string":
        if not isinstance(value, str) or not value.strip():
            raise _type_error(context, "non-empty text")
        return value
    if field_type == "integer":
        return _integer(value, context)
    if field_type == "number":
        return _number(value, context)
    if field_type == "date":
        return _date(value, context)
    if field_type == "datetime":
        return _datetime(value, context)
    if field_type == "sha256":
        if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
            raise _type_error(context, "a lowercase 64-character SHA-256 hash")
        return value
    raise ContractValidationError(
        f"Reference contract field {context} uses unsupported type {field_type!r}"
    )


def _validate_unique_keys(
    file_name: str,
    rows: Sequence[Mapping[str, object]],
    file_contract: Mapping[str, Any],
) -> None:
    unique_keys = file_contract.get("uniqueKeys", [])
    if not isinstance(unique_keys, list):
        raise ContractValidationError(
            f"Reference contract file {file_name} has invalid uniqueKeys"
        )
    for fields in unique_keys:
        if not isinstance(fields, list) or any(not isinstance(field, str) for field in fields):
            raise ContractValidationError(
                f"Reference contract file {file_name} has an invalid unique key"
            )
        seen: set[tuple[object, ...]] = set()
        for row_index, row in enumerate(rows, start=1):
            key = tuple(row[field] for field in fields)
            if key in seen:
                names = ", ".join(fields)
                raise ContractValidationError(
                    f"{file_name} violates unique key ({names}) at row {row_index}: {key!r}"
                )
            seen.add(key)


def _relationship_side(
    relationship: Mapping[str, Any], side: str
) -> tuple[str, tuple[str, ...]]:
    value = relationship.get(side)
    if not isinstance(value, Mapping):
        raise ContractValidationError(
            f"Reference contract relationship {relationship.get('name')!r} has invalid {side}"
        )
    file_name = value.get("file")
    columns = value.get("columns")
    if not isinstance(file_name, str) or not isinstance(columns, list) or not columns:
        raise ContractValidationError(
            f"Reference contract relationship {relationship.get('name')!r} has invalid {side}"
        )
    if any(not isinstance(column, str) for column in columns):
        raise ContractValidationError(
            f"Reference contract relationship {relationship.get('name')!r} "
            f"has invalid {side} fields"
        )
    return file_name, tuple(columns)


def _validate_foreign_key(
    relationship: Mapping[str, Any], tables: Mapping[str, Sequence[Mapping[str, object]]]
) -> None:
    name = relationship.get("name")
    source_file, source_fields = _relationship_side(relationship, "from")
    target_file, target_fields = _relationship_side(relationship, "to")
    if len(source_fields) != len(target_fields):
        raise ContractValidationError(
            f"Reference contract relationship {name!r} has different source and target arity"
        )
    try:
        target_keys = {
            tuple(row[field] for field in target_fields) for row in tables[target_file]
        }
        source_rows = tables[source_file]
    except KeyError as error:
        raise ContractValidationError(
            f"Reference contract relationship {name!r} references unknown table or field "
            f"{error.args[0]}"
        ) from error
    for row_index, row in enumerate(source_rows, start=1):
        key = tuple(row[field] for field in source_fields)
        if key not in target_keys:
            source_names = ", ".join(source_fields)
            target_names = ", ".join(target_fields)
            raise ContractValidationError(
                f"relationship {name} failed: {source_file} row {row_index} fields "
                f"({source_names}) reference unknown {target_file} fields "
                f"({target_names}) key {key!r}"
            )


def _validate_exact_key_set(
    relationship: Mapping[str, Any], tables: Mapping[str, Sequence[Mapping[str, object]]]
) -> None:
    name = relationship.get("name")
    file_names = relationship.get("files")
    fields = relationship.get("columns")
    if (
        not isinstance(file_names, list)
        or len(file_names) < 2
        or any(not isinstance(file_name, str) for file_name in file_names)
        or not isinstance(fields, list)
        or not fields
        or any(not isinstance(field, str) for field in fields)
    ):
        raise ContractValidationError(
            f"Reference contract relationship {name!r} has invalid exact-key-set fields"
        )
    base_file = file_names[0]
    try:
        expected = {tuple(row[field] for field in fields) for row in tables[base_file]}
    except KeyError as error:
        raise ContractValidationError(
            f"Reference contract relationship {name!r} references unknown table or field "
            f"{error.args[0]}"
        ) from error
    for file_name in file_names[1:]:
        try:
            actual = {tuple(row[field] for field in fields) for row in tables[file_name]}
        except KeyError as error:
            raise ContractValidationError(
                f"Reference contract relationship {name!r} references unknown table or field "
                f"{error.args[0]}"
            ) from error
        if actual != expected:
            names = ", ".join(fields)
            raise ContractValidationError(
                f"relationship {name} key-set mismatch: {file_name} does not match "
                f"{base_file} fields ({names}); missing={len(expected - actual)}, "
                f"extra={len(actual - expected)}"
            )


def _validate_relationships(
    tables: Mapping[str, Sequence[Mapping[str, object]]], contract: Mapping[str, Any]
) -> None:
    relationships = contract.get("relationships")
    if not isinstance(relationships, list):
        raise ContractValidationError("Reference contract relationships must be a list")
    for relationship in relationships:
        if not isinstance(relationship, Mapping):
            raise ContractValidationError("Reference contract has an invalid relationship")
        kind = relationship.get("kind")
        if kind == "foreignKey":
            _validate_foreign_key(relationship, tables)
        elif kind == "exactKeySet":
            _validate_exact_key_set(relationship, tables)
        else:
            raise ContractValidationError(
                f"Reference contract relationship {relationship.get('name')!r} "
                f"has unsupported kind {kind!r}"
            )


def validate_reference_tables(
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> None:
    """Validate in-memory rows for all normalized reference CSV tables."""
    active_contract = contract if contract is not None else load_reference_contract()
    file_contracts = _contract_files(active_contract)
    expected_files = tuple(file_contracts)
    missing = [file_name for file_name in expected_files if file_name not in tables]
    extra = [file_name for file_name in tables if file_name not in file_contracts]
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing files: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected files: {', '.join(extra)}")
        raise ContractValidationError(f"Reference tables have {'; '.join(details)}")

    normalized_tables: dict[str, list[dict[str, object]]] = {}
    for file_name in expected_files:
        rows = tables[file_name]
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
            raise ContractValidationError(f"Reference table {file_name} rows must be a sequence")
        file_contract = file_contracts[file_name]
        columns = _columns_for(file_name, file_contract)
        expected_header = tuple(str(column["name"]) for column in columns)
        normalized_rows: list[dict[str, object]] = []
        for row_index, row in enumerate(rows, start=1):
            if not isinstance(row, Mapping):
                raise ContractValidationError(
                    f"{file_name} row {row_index} must be a field mapping"
                )
            actual_header = tuple(row)
            if actual_header != expected_header:
                raise ContractValidationError(
                    f"{file_name} row {row_index} fields do not match the ordered header: "
                    f"expected {expected_header!r}, found {actual_header!r}"
                )
            normalized_row: dict[str, object] = {}
            for column in columns:
                field = str(column["name"])
                normalized_row[field] = _validate_value(
                    row[field], column, f"{file_name} row {row_index} field {field}"
                )
            normalized_rows.append(normalized_row)
        normalized_tables[file_name] = normalized_rows
        if not isinstance(file_contract, Mapping):
            raise ContractValidationError(
                f"Reference contract file definition {file_name} must be an object"
            )
        _validate_unique_keys(file_name, normalized_rows, file_contract)

    _validate_relationships(normalized_tables, active_contract)


def validate_reference_package(
    package_dir: str | Path,
    *,
    contract: Mapping[str, Any] | None = None,
) -> None:
    """Read and validate the six normalized CSVs in a reference package directory."""
    directory = Path(package_dir)
    if not directory.is_dir():
        raise ContractValidationError(f"Reference package directory does not exist: {directory}")
    active_contract = contract if contract is not None else load_reference_contract()
    file_contracts = _contract_files(active_contract)
    tables: dict[str, list[dict[str, object]]] = {}

    for file_name, file_contract in file_contracts.items():
        path = directory / file_name
        if not path.is_file():
            raise ContractValidationError(
                f"Reference package is missing required table {file_name}: {path}"
            )
        columns = _columns_for(file_name, file_contract)
        expected_header = tuple(str(column["name"]) for column in columns)
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                try:
                    actual_header = tuple(next(reader))
                except StopIteration as error:
                    raise ContractValidationError(
                        f"{file_name} is empty and has no header"
                    ) from error
                if actual_header != expected_header:
                    raise ContractValidationError(
                        f"{file_name} header mismatch: expected {expected_header!r}, "
                        f"found {actual_header!r}"
                    )
                rows: list[dict[str, object]] = []
                for csv_row_number, values in enumerate(reader, start=2):
                    if len(values) != len(expected_header):
                        raise ContractValidationError(
                            f"{file_name} row {csv_row_number} has {len(values)} fields; "
                            f"expected {len(expected_header)}"
                        )
                    rows.append(dict(zip(expected_header, values, strict=True)))
                tables[file_name] = rows
        except UnicodeDecodeError as error:
            raise ContractValidationError(f"{file_name} must use UTF-8 encoding") from error
        except csv.Error as error:
            raise ContractValidationError(f"Unable to parse {file_name}: {error}") from error

    validate_reference_tables(tables, contract=active_contract)
