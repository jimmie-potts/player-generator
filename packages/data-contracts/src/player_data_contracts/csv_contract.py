"""Reusable validation for versioned, ordered CSV table contracts."""

from __future__ import annotations

import csv
import io
import math
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from numbers import Integral, Real
from pathlib import Path
from typing import Any

from player_data_contracts.validation import ContractValidationError

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_INTEGER_PATTERN = re.compile(r"[+-]?\d+")
_COLUMN_NAME_PATTERN = re.compile(r"[a-z][A-Za-z0-9]*")
_SUPPORTED_TYPES = {"string", "integer", "number", "date", "datetime", "sha256"}
_COLUMN_PROPERTIES = {
    "name",
    "type",
    "required",
    "nullable",
    "minimum",
    "maximum",
    "enum",
    "pattern",
}


def contract_files(
    contract: Mapping[str, Any],
    *,
    contract_name: str,
    contract_version: int,
) -> Mapping[str, Any]:
    """Return validated file definitions from an ordered CSV contract."""
    actual_version = contract.get("contractVersion")
    if type(actual_version) is not type(contract_version) or actual_version != contract_version:
        raise ContractValidationError(
            f"Unsupported {contract_name.lower()} contract version: "
            f"{_safe_repr(actual_version)}"
        )
    if contract.get("encoding") != "UTF-8":
        raise ContractValidationError(
            f"{contract_name} contract encoding must be 'UTF-8'"
        )
    if contract.get("lineEnding") != "LF":
        raise ContractValidationError(
            f"{contract_name} contract lineEnding must be 'LF'"
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
    if set(file_contract) != {"columns", "uniqueKeys"}:
        raise ContractValidationError(
            f"{contract_name} contract file {file_name} must contain columns and uniqueKeys"
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
    for column in columns:
        _validate_column_declaration(
            column,
            context=f"{contract_name} contract file {file_name} column {column['name']}",
        )
    return columns


def _empty(value: object) -> bool:
    return value is None or value == ""


def _type_error(context: str, expected: str) -> ContractValidationError:
    return ContractValidationError(f"{context} must be {expected}")


def _safe_repr(value: object) -> str:
    try:
        return repr(value)
    except (OverflowError, ValueError):
        return f"<{type(value).__name__} outside supported representation>"


def _integer(value: object, context: str) -> int:
    if isinstance(value, bool):
        raise _type_error(context, "an integer")
    if isinstance(value, Integral):
        normalized = int(value)
        try:
            str(normalized)
        except ValueError:
            raise _type_error(
                context, "an integer within the supported decimal length"
            ) from None
        return normalized
    if isinstance(value, Real):
        try:
            number = float(value)
        except (OverflowError, TypeError, ValueError):
            raise _type_error(context, "an integer") from None
        if math.isfinite(number) and number.is_integer():
            return int(number)
        raise _type_error(context, "an integer")
    if isinstance(value, str) and _INTEGER_PATTERN.fullmatch(value):
        try:
            return int(value)
        except ValueError:
            raise _type_error(
                context, "an integer within the supported decimal length"
            ) from None
    raise _type_error(context, "an integer")


def _number(value: object, context: str) -> float:
    if isinstance(value, bool):
        raise _type_error(context, "a finite number")
    try:
        if isinstance(value, Real):
            number = float(value)
        elif isinstance(value, str):
            number = float(value)
        else:
            raise _type_error(context, "a finite number")
    except (OverflowError, TypeError, ValueError):
        raise _type_error(context, "a finite number") from None
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
            f"{contract_name} contract field {context} uses unsupported type "
            f"{_safe_repr(field_type)}"
        )

    enum = column.get("enum")
    if enum is not None:
        if not isinstance(enum, list) or not enum:
            raise ContractValidationError(
                f"{contract_name} contract field {context} has an invalid enum"
            )
        if normalized not in enum:
            raise ContractValidationError(
                f"{context} must be one of {', '.join(_safe_repr(item) for item in enum)}"
            )

    pattern = column.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            raise ContractValidationError(
                f"{contract_name} contract field {context} has an invalid pattern"
            )
        try:
            matches = isinstance(normalized, str) and re.fullmatch(
                pattern, normalized
            ) is not None
        except (re.error, OverflowError) as error:
            raise ContractValidationError(
                f"{contract_name} contract field {context} has an invalid pattern"
            ) from error
        if not matches:
            raise ContractValidationError(f"{context} must match pattern {pattern!r}")

    for bound_name, comparison, phrase in (
        ("minimum", lambda number, bound: number >= bound, "at least"),
        ("maximum", lambda number, bound: number <= bound, "at most"),
    ):
        bound = column.get(bound_name)
        if bound is not None:
            invalid_bound = ContractValidationError(
                f"{contract_name} contract field {context} has an invalid {bound_name}"
            )
            if field_type == "integer":
                if isinstance(bound, bool) or not isinstance(bound, Real):
                    raise invalid_bound
                try:
                    normalized_bound: Real = _integer(bound, context)
                except ContractValidationError:
                    raise invalid_bound from None
                satisfies_bound = comparison(normalized, normalized_bound)
            elif field_type == "number":
                if isinstance(bound, bool) or not isinstance(bound, Real):
                    raise invalid_bound
                try:
                    normalized_bound = _number(bound, context)
                except ContractValidationError:
                    raise invalid_bound from None
                if normalized_bound != bound:
                    raise invalid_bound
                satisfies_bound = isinstance(normalized, Real) and comparison(
                    float(normalized), normalized_bound
                )
            else:
                raise invalid_bound
            if not satisfies_bound:
                raise ContractValidationError(
                    f"{context} must be {phrase} {bound}"
                )

    return normalized


def _validate_column_declaration(
    column: Mapping[str, Any],
    *,
    context: str,
) -> None:
    unexpected = set(column) - _COLUMN_PROPERTIES
    if unexpected:
        raise ContractValidationError(
            f"{context} has unknown properties: {', '.join(sorted(unexpected))}"
        )
    name = column.get("name")
    if not isinstance(name, str) or _COLUMN_NAME_PATTERN.fullmatch(name) is None:
        raise ContractValidationError(
            f"{context} name must be a lower camelCase header"
        )
    field_type = column.get("type")
    if not isinstance(field_type, str) or field_type not in _SUPPORTED_TYPES:
        raise ContractValidationError(
            f"{context} uses unsupported type {_safe_repr(field_type)}"
        )
    required = column.get("required")
    nullable = column.get("nullable")
    if type(required) is not bool or type(nullable) is not bool:
        raise ContractValidationError(
            f"{context} required and nullable must be boolean"
        )
    if required == nullable:
        raise ContractValidationError(
            f"{context} must be required and non-nullable or optional and nullable"
        )

    bounds: dict[str, Real] = {}
    for bound_name in ("minimum", "maximum"):
        if bound_name not in column:
            continue
        bound = column[bound_name]
        if field_type not in {"integer", "number"}:
            raise ContractValidationError(
                f"{context} cannot bound non-numeric type {field_type}"
            )
        if isinstance(bound, bool) or not isinstance(bound, Real):
            raise ContractValidationError(
                f"{context} has an invalid {bound_name}"
            )
        if field_type == "integer":
            try:
                normalized_bound: Real = _integer(bound, context)
            except ContractValidationError:
                raise ContractValidationError(
                    f"{context} has an invalid {bound_name}"
                ) from None
        else:
            try:
                normalized_bound = _number(bound, context)
            except ContractValidationError:
                raise ContractValidationError(
                    f"{context} has an invalid {bound_name}"
                ) from None
            if normalized_bound != bound:
                raise ContractValidationError(
                    f"{context} has an invalid {bound_name}"
                )
        bounds[bound_name] = normalized_bound
    if (
        "minimum" in bounds
        and "maximum" in bounds
        and bounds["minimum"] > bounds["maximum"]
    ):
        raise ContractValidationError(f"{context} minimum cannot exceed maximum")

    if "pattern" in column:
        pattern = column["pattern"]
        if field_type != "string" or not isinstance(pattern, str):
            raise ContractValidationError(
                f"{context} pattern requires a string field"
            )
        try:
            re.compile(pattern)
        except (re.error, OverflowError) as error:
            raise ContractValidationError(
                f"{context} pattern is invalid: {error}"
            ) from error

    if "enum" not in column:
        return
    enum = column["enum"]
    if not isinstance(enum, list) or not enum:
        raise ContractValidationError(f"{context} has an invalid enum")
    value_contract = dict(column)
    value_contract.pop("enum")
    serialized_values: list[str] = []
    for value in enum:
        if _empty(value):
            raise ContractValidationError(
                f"{context} enum value {_safe_repr(value)} does not match field type "
                f"{field_type}"
            )
        if field_type == "integer" and (
            isinstance(value, bool) or not isinstance(value, Integral)
        ):
            raise ContractValidationError(
                f"{context} enum value {_safe_repr(value)} does not match field type "
                f"{field_type}"
            )
        if field_type == "number":
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ContractValidationError(
                    f"{context} enum value {_safe_repr(value)} does not match field type "
                    f"{field_type}"
                )
            try:
                normalized_number = float(value)
            except (OverflowError, TypeError, ValueError):
                raise ContractValidationError(
                    f"{context} enum value {_safe_repr(value)} does not match field type "
                    f"{field_type}"
                ) from None
            if not math.isfinite(normalized_number) or normalized_number != value:
                raise ContractValidationError(
                    f"{context} enum value {_safe_repr(value)} does not round-trip "
                    "through IEEE-754 normalization"
                )
        if field_type in {"string", "date", "datetime", "sha256"} and not isinstance(
            value, str
        ):
            raise ContractValidationError(
                f"{context} enum value {_safe_repr(value)} does not match field type "
                f"{field_type}"
            )
        normalized = _validate_value(
            value,
            value_contract,
            f"{context} enum value {_safe_repr(value)}",
            contract_name="CSV",
        )
        serialized = serialize_csv_value(
            normalized,
            value_contract,
            context=f"{context} enum value {_safe_repr(value)}",
        )
        if field_type in {"date", "datetime"} and serialized != value:
            raise ContractValidationError(
                f"{context} enum value {_safe_repr(value)} must use canonical "
                f"{field_type} form {serialized!r}"
            )
        serialized_values.append(serialized)
    if len(serialized_values) != len(set(serialized_values)):
        raise ContractValidationError(
            f"{context} enum values must remain unique after CSV serialization"
        )


def serialize_csv_value(
    value: object,
    column: Mapping[str, Any],
    *,
    context: str = "CSV value",
) -> str:
    """Validate and serialize one scalar with the player-data v1 CSV rules."""
    normalized = _validate_value(value, column, context, contract_name="CSV")
    if normalized is None:
        return ""
    field_type = column.get("type")
    if field_type == "integer":
        try:
            return str(normalized)
        except ValueError:
            raise _type_error(
                context, "an integer within the supported decimal length"
            ) from None
    if field_type == "number":
        number = float(normalized)
        if number == 0:
            return "0"
        serialized = format(Decimal(repr(number)), "f")
        if "." in serialized:
            serialized = serialized.rstrip("0").rstrip(".")
        return serialized
    return str(normalized)


def _validate_unique_keys(
    file_name: str,
    rows: Sequence[Mapping[str, object]],
    file_contract: Mapping[str, Any],
    columns: Sequence[Mapping[str, Any]],
    *,
    contract_name: str,
) -> tuple[tuple[str, ...], ...]:
    unique_keys = file_contract.get("uniqueKeys")
    if not isinstance(unique_keys, list) or not unique_keys:
        raise ContractValidationError(
            f"{contract_name} contract file {file_name} has invalid uniqueKeys"
        )
    columns_by_name = {str(column["name"]): column for column in columns}
    seen_keys: set[tuple[str, ...]] = set()
    declared_keys: list[tuple[str, ...]] = []
    for fields in unique_keys:
        if (
            not isinstance(fields, list)
            or not fields
            or any(not isinstance(field, str) or not field.strip() for field in fields)
            or len(fields) != len(set(fields))
        ):
            raise ContractValidationError(
                f"{contract_name} contract file {file_name} has an invalid unique key"
            )
        key_fields = tuple(fields)
        unknown = set(key_fields) - set(columns_by_name)
        if unknown:
            raise ContractValidationError(
                f"{contract_name} contract file {file_name} unique key references unknown "
                f"fields: {', '.join(sorted(unknown))}"
            )
        nullable_fields = [
            field
            for field in key_fields
            if columns_by_name[field].get("required") is not True
            or columns_by_name[field].get("nullable") is not False
        ]
        if nullable_fields:
            raise ContractValidationError(
                f"{contract_name} contract file {file_name} unique key fields must be "
                f"required and non-nullable: {', '.join(nullable_fields)}"
            )
        if key_fields in seen_keys:
            raise ContractValidationError(
                f"{contract_name} contract file {file_name} repeats unique key "
                f"{key_fields!r}"
            )
        seen_keys.add(key_fields)
        declared_keys.append(key_fields)
        seen: set[tuple[object, ...]] = set()
        for row_index, row in enumerate(rows, start=1):
            key = tuple(row[field] for field in key_fields)
            if key in seen:
                names = ", ".join(key_fields)
                raise ContractValidationError(
                    f"{file_name} violates unique key ({names}) at row {row_index}: {key!r}"
                )
            seen.add(key)
    return tuple(declared_keys)


def _relationship_side(
    relationship: Mapping[str, Any],
    side: str,
    *,
    columns_by_file: Mapping[str, Mapping[str, Mapping[str, Any]]],
    contract_name: str,
) -> tuple[str, tuple[str, ...]]:
    value = relationship.get(side)
    if not isinstance(value, Mapping) or set(value) != {"file", "columns"}:
        raise ContractValidationError(
            f"{contract_name} contract relationship {relationship.get('name')!r} has invalid {side}"
        )
    file_name = value.get("file")
    columns = value.get("columns")
    if (
        not isinstance(file_name, str)
        or not file_name.strip()
        or file_name not in columns_by_file
        or not isinstance(columns, list)
        or not columns
    ):
        raise ContractValidationError(
            f"{contract_name} contract relationship {relationship.get('name')!r} has invalid {side}"
        )
    if (
        any(not isinstance(column, str) or not column.strip() for column in columns)
        or len(columns) != len(set(columns))
    ):
        raise ContractValidationError(
            f"{contract_name} contract relationship {relationship.get('name')!r} "
            f"has invalid {side} fields"
        )
    fields = tuple(columns)
    unknown = set(fields) - set(columns_by_file[file_name])
    if unknown:
        raise ContractValidationError(
            f"{contract_name} contract relationship {relationship.get('name')!r} "
            f"references unknown {side} fields in {file_name}: "
            f"{', '.join(sorted(unknown))}"
        )
    return file_name, fields


def _validate_value_reference(
    name: str,
    source_file: str,
    source_fields: Sequence[str],
    target_file: str,
    target_fields: Sequence[str],
    tables: Mapping[str, Sequence[Mapping[str, object]]],
) -> None:
    target_keys = {
        tuple(row[field] for field in target_fields) for row in tables[target_file]
    }
    source_rows = tables[source_file]
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
    name: str,
    file_names: Sequence[str],
    fields: Sequence[str],
    tables: Mapping[str, Sequence[Mapping[str, object]]],
) -> None:
    base_file = file_names[0]
    expected = {tuple(row[field] for field in fields) for row in tables[base_file]}
    for file_name in file_names[1:]:
        actual = {tuple(row[field] for field in fields) for row in tables[file_name]}
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
    columns_by_file: Mapping[str, Mapping[str, Mapping[str, Any]]],
    unique_keys_by_file: Mapping[str, Sequence[Sequence[str]]],
    contract_name: str,
) -> None:
    relationships = contract.get("relationships")
    if not isinstance(relationships, list):
        raise ContractValidationError(f"{contract_name} contract relationships must be a list")
    seen_names: set[str] = set()
    for relationship in relationships:
        if not isinstance(relationship, Mapping):
            raise ContractValidationError(f"{contract_name} contract has an invalid relationship")
        name = relationship.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ContractValidationError(
                f"{contract_name} contract relationship has an invalid name"
            )
        if name in seen_names:
            raise ContractValidationError(
                f"{contract_name} contract repeats relationship {name!r}"
            )
        seen_names.add(name)
        kind = relationship.get("kind")
        if kind in ("foreignKey", "valueExists"):
            if set(relationship) != {"name", "kind", "from", "to"}:
                raise ContractValidationError(
                    f"{contract_name} contract relationship {name!r} has invalid "
                    f"{kind} fields"
                )
            source_file, source_fields = _relationship_side(
                relationship,
                "from",
                columns_by_file=columns_by_file,
                contract_name=contract_name,
            )
            target_file, target_fields = _relationship_side(
                relationship,
                "to",
                columns_by_file=columns_by_file,
                contract_name=contract_name,
            )
            if len(source_fields) != len(target_fields):
                raise ContractValidationError(
                    f"{contract_name} contract relationship {name!r} has different "
                    "source and target arity"
                )
            source_types = tuple(
                columns_by_file[source_file][field]["type"] for field in source_fields
            )
            target_types = tuple(
                columns_by_file[target_file][field]["type"] for field in target_fields
            )
            if source_types != target_types:
                raise ContractValidationError(
                    f"{contract_name} contract relationship {name!r} source and target "
                    "columns must have matching scalar types"
                )
            nullable_source_fields = [
                f"{source_file}.{field}"
                for field in source_fields
                if columns_by_file[source_file][field].get("required") is not True
                or columns_by_file[source_file][field].get("nullable") is not False
            ]
            if nullable_source_fields:
                raise ContractValidationError(
                    f"{contract_name} contract relationship {name!r} source fields must "
                    "be required and non-nullable: "
                    f"{', '.join(nullable_source_fields)}"
                )
            if kind == "foreignKey" and tuple(target_fields) not in {
                tuple(key) for key in unique_keys_by_file[target_file]
            }:
                raise ContractValidationError(
                    f"{contract_name} contract relationship {name!r} target columns must "
                    f"be a declared unique key for {target_file}"
                )
            _validate_value_reference(
                name,
                source_file,
                source_fields,
                target_file,
                target_fields,
                tables,
            )
        elif kind == "exactKeySet":
            if set(relationship) != {"name", "kind", "files", "columns"}:
                raise ContractValidationError(
                    f"{contract_name} contract relationship {name!r} has invalid "
                    "exact-key-set fields"
                )
            file_names = relationship.get("files")
            fields = relationship.get("columns")
            if (
                not isinstance(file_names, list)
                or len(file_names) < 2
                or any(
                    not isinstance(file_name, str)
                    or not file_name.strip()
                    or file_name not in columns_by_file
                    for file_name in file_names
                )
                or len(file_names) != len(set(file_names))
                or not isinstance(fields, list)
                or not fields
                or any(not isinstance(field, str) or not field.strip() for field in fields)
                or len(fields) != len(set(fields))
            ):
                raise ContractValidationError(
                    f"{contract_name} contract relationship {name!r} has invalid "
                    "exact-key-set fields"
                )
            expected_types: tuple[object, ...] | None = None
            for file_name in file_names:
                unknown = set(fields) - set(columns_by_file[file_name])
                if unknown:
                    raise ContractValidationError(
                        f"{contract_name} contract relationship {name!r} references "
                        f"unknown columns in {file_name}: {', '.join(sorted(unknown))}"
                    )
                if not any(
                    set(key).issubset(set(fields))
                    for key in unique_keys_by_file[file_name]
                ):
                    raise ContractValidationError(
                        f"{contract_name} contract relationship {name!r} columns must "
                        f"include a declared unique key for {file_name}"
                    )
                current_types = tuple(
                    columns_by_file[file_name][field]["type"] for field in fields
                )
                if expected_types is None:
                    expected_types = current_types
                elif current_types != expected_types:
                    raise ContractValidationError(
                        f"{contract_name} contract relationship {name!r} columns must "
                        "have matching scalar types"
                    )
            _validate_exact_key_set(name, file_names, fields, tables)
        else:
            raise ContractValidationError(
                f"{contract_name} contract relationship {relationship.get('name')!r} "
                f"has unsupported kind {_safe_repr(kind)}"
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
    columns_by_file: dict[str, dict[str, Mapping[str, Any]]] = {}
    unique_keys_by_file: dict[str, tuple[tuple[str, ...], ...]] = {}
    for file_name in expected_files:
        rows = tables[file_name]
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
            raise ContractValidationError(
                f"{contract_name} table {file_name} rows must be a sequence"
            )
        file_contract = file_contracts[file_name]
        columns = columns_for(file_name, file_contract, contract_name=contract_name)
        columns_by_file[file_name] = {
            str(column["name"]): column for column in columns
        }
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
        unique_keys_by_file[file_name] = _validate_unique_keys(
            file_name,
            normalized_rows,
            file_contract,
            columns,
            contract_name=contract_name,
        )

    _validate_relationships(
        normalized_tables,
        contract,
        columns_by_file=columns_by_file,
        unique_keys_by_file=unique_keys_by_file,
        contract_name=contract_name,
    )
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
                content = handle.read()
                if contract.get("lineEnding") == "LF" and "\r" in content:
                    raise ContractValidationError(
                        f"{file_name} must use LF line endings"
                    )
                if contract.get("lineEnding") == "LF" and not content.endswith("\n"):
                    raise ContractValidationError(
                        f"{file_name} must end with an LF line ending"
                    )
                reader = csv.reader(io.StringIO(content, newline=""), strict=True)
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
