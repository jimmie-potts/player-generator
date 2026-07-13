"""Reusable validation for versioned, ordered CSV table contracts."""

from __future__ import annotations

import csv
import math
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from numbers import Integral, Real
from pathlib import Path
from typing import Any

from player_data_contracts.validation import ContractValidationError

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_INTEGER_PATTERN = re.compile(r"[+-]?\d+")


def contract_files(
    contract: Mapping[str, Any],
    *,
    contract_name: str,
    contract_version: int,
) -> Mapping[str, Any]:
    """Return validated file definitions from an ordered CSV contract."""
    if contract.get("contractVersion") != contract_version:
        raise ContractValidationError(
            f"Unsupported {contract_name.lower()} contract version: "
            f"{contract.get('contractVersion')!r}"
        )
    file_contracts = contract.get("files")
    if not isinstance(file_contracts, Mapping) or not file_contracts:
        raise ContractValidationError(f"{contract_name} contract has no file definitions")
    return file_contracts


def columns_for(
    file_name: str,
    file_contract: object,
    *,
    contract_name: str,
) -> list[Mapping[str, Any]]:
    """Return validated, ordered column definitions for one contracted file."""
    if not isinstance(file_contract, Mapping):
        raise ContractValidationError(
            f"{contract_name} contract file definition {file_name} must be an object"
        )
    columns = file_contract.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ContractValidationError(
            f"{contract_name} contract file {file_name} has no column definitions"
        )
    if any(not isinstance(column, Mapping) for column in columns):
        raise ContractValidationError(
            f"{contract_name} contract file {file_name} has an invalid column definition"
        )
    names = [column.get("name") for column in columns]
    if any(not isinstance(name, str) or not name for name in names):
        raise ContractValidationError(
            f"{contract_name} contract file {file_name} has an invalid column name"
        )
    if len(names) != len(set(names)):
        raise ContractValidationError(
            f"{contract_name} contract file {file_name} has duplicate column names"
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


def _validate_value(
    value: object,
    column: Mapping[str, Any],
    context: str,
    *,
    contract_name: str,
) -> object:
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
        normalized: object = value
    elif field_type == "integer":
        normalized = _integer(value, context)
    elif field_type == "number":
        normalized = _number(value, context)
    elif field_type == "date":
        normalized = _date(value, context)
    elif field_type == "datetime":
        normalized = _datetime(value, context)
    elif field_type == "sha256":
        if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
            raise _type_error(context, "a lowercase 64-character SHA-256 hash")
        normalized = value
    else:
        raise ContractValidationError(
            f"{contract_name} contract field {context} uses unsupported type {field_type!r}"
        )

    enum = column.get("enum")
    if enum is not None:
        if not isinstance(enum, list) or not enum:
            raise ContractValidationError(
                f"{contract_name} contract field {context} has an invalid enum"
            )
        if normalized not in enum:
            raise ContractValidationError(
                f"{context} must be one of {', '.join(repr(item) for item in enum)}"
            )

    pattern = column.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            raise ContractValidationError(
                f"{contract_name} contract field {context} has an invalid pattern"
            )
        if not isinstance(normalized, str) or re.fullmatch(pattern, normalized) is None:
            raise ContractValidationError(f"{context} must match pattern {pattern!r}")

    for bound_name, comparison, phrase in (
        ("minimum", lambda number, bound: number >= bound, "at least"),
        ("maximum", lambda number, bound: number <= bound, "at most"),
    ):
        bound = column.get(bound_name)
        if bound is not None:
            if isinstance(bound, bool) or not isinstance(bound, Real):
                raise ContractValidationError(
                    f"{contract_name} contract field {context} has an invalid {bound_name}"
                )
            if not isinstance(normalized, Real) or not comparison(float(normalized), float(bound)):
                raise ContractValidationError(f"{context} must be {phrase} {bound}")

    return normalized


def _validate_unique_keys(
    file_name: str,
    rows: Sequence[Mapping[str, object]],
    file_contract: Mapping[str, Any],
    *,
    contract_name: str,
) -> None:
    unique_keys = file_contract.get("uniqueKeys", [])
    if not isinstance(unique_keys, list):
        raise ContractValidationError(
            f"{contract_name} contract file {file_name} has invalid uniqueKeys"
        )
    for fields in unique_keys:
        if not isinstance(fields, list) or any(not isinstance(field, str) for field in fields):
            raise ContractValidationError(
                f"{contract_name} contract file {file_name} has an invalid unique key"
            )
        seen: set[tuple[object, ...]] = set()
        for row_index, row in enumerate(rows, start=1):
            try:
                key = tuple(row[field] for field in fields)
            except KeyError as error:
                raise ContractValidationError(
                    f"{contract_name} contract file {file_name} unique key references "
                    f"unknown field {error.args[0]}"
                ) from error
            if key in seen:
                names = ", ".join(fields)
                raise ContractValidationError(
                    f"{file_name} violates unique key ({names}) at row {row_index}: {key!r}"
                )
            seen.add(key)


def _relationship_side(
    relationship: Mapping[str, Any], side: str, *, contract_name: str
) -> tuple[str, tuple[str, ...]]:
    value = relationship.get(side)
    if not isinstance(value, Mapping):
        raise ContractValidationError(
            f"{contract_name} contract relationship {relationship.get('name')!r} has invalid {side}"
        )
    file_name = value.get("file")
    columns = value.get("columns")
    if not isinstance(file_name, str) or not isinstance(columns, list) or not columns:
        raise ContractValidationError(
            f"{contract_name} contract relationship {relationship.get('name')!r} has invalid {side}"
        )
    if any(not isinstance(column, str) for column in columns):
        raise ContractValidationError(
            f"{contract_name} contract relationship {relationship.get('name')!r} "
            f"has invalid {side} fields"
        )
    return file_name, tuple(columns)


def _validate_foreign_key(
    relationship: Mapping[str, Any],
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    contract_name: str,
) -> None:
    name = relationship.get("name")
    source_file, source_fields = _relationship_side(
        relationship, "from", contract_name=contract_name
    )
    target_file, target_fields = _relationship_side(relationship, "to", contract_name=contract_name)
    if len(source_fields) != len(target_fields):
        raise ContractValidationError(
            f"{contract_name} contract relationship {name!r} has different source and target arity"
        )
    try:
        target_keys = {tuple(row[field] for field in target_fields) for row in tables[target_file]}
        source_rows = tables[source_file]
    except KeyError as error:
        raise ContractValidationError(
            f"{contract_name} contract relationship {name!r} references unknown table or field "
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
    relationship: Mapping[str, Any],
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    contract_name: str,
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
            f"{contract_name} contract relationship {name!r} has invalid exact-key-set fields"
        )
    base_file = file_names[0]
    try:
        expected = {tuple(row[field] for field in fields) for row in tables[base_file]}
    except KeyError as error:
        raise ContractValidationError(
            f"{contract_name} contract relationship {name!r} references unknown table or field "
            f"{error.args[0]}"
        ) from error
    for file_name in file_names[1:]:
        try:
            actual = {tuple(row[field] for field in fields) for row in tables[file_name]}
        except KeyError as error:
            raise ContractValidationError(
                f"{contract_name} contract relationship {name!r} "
                f"references unknown table or field {error.args[0]}"
            ) from error
        if actual != expected:
            names = ", ".join(fields)
            raise ContractValidationError(
                f"relationship {name} key-set mismatch: {file_name} does not match "
                f"{base_file} fields ({names}); missing={len(expected - actual)}, "
                f"extra={len(actual - expected)}"
            )


def _validate_relationships(
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    contract: Mapping[str, Any],
    *,
    contract_name: str,
) -> None:
    relationships = contract.get("relationships")
    if not isinstance(relationships, list):
        raise ContractValidationError(f"{contract_name} contract relationships must be a list")
    for relationship in relationships:
        if not isinstance(relationship, Mapping):
            raise ContractValidationError(f"{contract_name} contract has an invalid relationship")
        kind = relationship.get("kind")
        if kind == "foreignKey":
            _validate_foreign_key(relationship, tables, contract_name=contract_name)
        elif kind == "exactKeySet":
            _validate_exact_key_set(relationship, tables, contract_name=contract_name)
        else:
            raise ContractValidationError(
                f"{contract_name} contract relationship {relationship.get('name')!r} "
                f"has unsupported kind {kind!r}"
            )


def validate_csv_tables(
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    contract: Mapping[str, Any],
    contract_name: str,
    contract_version: int,
) -> dict[str, list[dict[str, object]]]:
    """Validate and normalize in-memory rows for an ordered CSV contract."""
    file_contracts = contract_files(
        contract, contract_name=contract_name, contract_version=contract_version
    )
    expected_files = tuple(file_contracts)
    missing = [file_name for file_name in expected_files if file_name not in tables]
    extra = [file_name for file_name in tables if file_name not in file_contracts]
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing files: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected files: {', '.join(extra)}")
        raise ContractValidationError(f"{contract_name} tables have {'; '.join(details)}")

    normalized_tables: dict[str, list[dict[str, object]]] = {}
    for file_name in expected_files:
        rows = tables[file_name]
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
            raise ContractValidationError(
                f"{contract_name} table {file_name} rows must be a sequence"
            )
        file_contract = file_contracts[file_name]
        columns = columns_for(file_name, file_contract, contract_name=contract_name)
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
                    row[field],
                    column,
                    f"{file_name} row {row_index} field {field}",
                    contract_name=contract_name,
                )
            normalized_rows.append(normalized_row)
        normalized_tables[file_name] = normalized_rows
        if not isinstance(file_contract, Mapping):
            raise ContractValidationError(
                f"{contract_name} contract file definition {file_name} must be an object"
            )
        _validate_unique_keys(
            file_name, normalized_rows, file_contract, contract_name=contract_name
        )

    _validate_relationships(normalized_tables, contract, contract_name=contract_name)
    return normalized_tables


def validate_csv_package(
    package_dir: str | Path,
    *,
    contract: Mapping[str, Any],
    contract_name: str,
    contract_version: int,
) -> dict[str, list[dict[str, object]]]:
    """Read, validate, and normalize every CSV declared by a contract."""
    directory = Path(package_dir)
    if not directory.is_dir():
        raise ContractValidationError(
            f"{contract_name} package directory does not exist: {directory}"
        )
    file_contracts = contract_files(
        contract, contract_name=contract_name, contract_version=contract_version
    )
    tables: dict[str, list[dict[str, object]]] = {}

    for file_name, file_contract in file_contracts.items():
        path = directory / file_name
        if not path.is_file():
            raise ContractValidationError(
                f"{contract_name} package is missing required table {file_name}: {path}"
            )
        columns = columns_for(file_name, file_contract, contract_name=contract_name)
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

    return validate_csv_tables(
        tables,
        contract=contract,
        contract_name=contract_name,
        contract_version=contract_version,
    )
