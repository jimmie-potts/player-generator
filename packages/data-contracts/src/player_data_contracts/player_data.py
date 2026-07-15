"""Shared player-data contract family and cross-profile drift validation."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import date, datetime
from importlib.resources import files
from numbers import Integral, Real
from typing import Any, Final

from player_data_contracts.csv_contract import serialize_csv_value
from player_data_contracts.validation import ContractValidationError

PLAYER_DATA_CONTRACT_FAMILY: Final = "player-data"
PLAYER_DATA_CONTRACT_VERSION: Final = 1

_FAMILY_SCHEMA_NAME = "schemas/player-data-v1.contract.json"
_PROFILE_NAMES = ("reference", "roster")
_SHARED_FILE_NAMES = ("players.csv", "player_stats.csv", "player_attributes.csv")
_SUPPORTED_TYPES = {"string", "integer", "number", "date", "datetime", "sha256"}
_CSV_RULES = {
    "encoding": "UTF-8",
    "lineEnding": "LF",
    "delimiter": ",",
    "quoteCharacter": '"',
    "doubleQuoteEscaping": True,
    "quoting": "minimal",
    "headerRow": True,
    "headerStyle": "camelCase",
    "nullEncoding": "",
    "numericSerialization": "ieee754-shortest-roundtrip-expanded-v1",
    "deterministicOrdering": True,
}
_PROFILE_CSV_RULE_PROPERTIES = (*_CSV_RULES, "numericSerializationDescription")
_STRUCTURAL_PROPERTIES = (
    "type",
    "required",
    "nullable",
    "minimum",
    "maximum",
    "enum",
    "pattern",
)
_PROFILE_SCHEMA_PROPERTIES = {
    "title",
    "description",
    "contractVersion",
    *_PROFILE_CSV_RULE_PROPERTIES,
    "files",
    "relationships",
}
_PROFILE_FILE_PROPERTIES = {"columns", "uniqueKeys"}
_PROFILE_COLUMN_PROPERTIES = {"name", *_STRUCTURAL_PROPERTIES}
_GAP_DEFINITION_PROPERTIES = {"type", "minimum", "maximum", "enum", "pattern"}
_FAMILY_PROPERTIES = {
    "title",
    "description",
    "contractFamily",
    "contractVersion",
    "csv",
    "sharedFiles",
    "profiles",
    "declaredAlignmentGaps",
}
_PROFILE_PROPERTIES = {
    "schemaResource",
    "packageInventory",
    "packageFileExtensions",
    "currentColumnOrder",
    "rowOrder",
    "availabilityOverrides",
    "fieldConstraints",
    "extensionColumns",
    "profileOnlyFiles",
    "uniqueKeys",
    "keyRationales",
    "relationships",
}
_CAMEL_CASE_HEADER_PATTERN = re.compile(r"[a-z][A-Za-z0-9]*")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_MISSING = object()


def _is_absence_marker(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == {"absent"}
        and value["absent"] is True
    )


def _same_json_value(left: object, right: object) -> bool:
    if left is _MISSING or right is _MISSING:
        return left is right
    if type(left) is not type(right):
        return False
    if isinstance(left, Mapping):
        if len(left) != len(right):
            return False
        right_items = list(right.items())
        for left_key, left_value in left.items():
            matches = [
                right_value
                for right_key, right_value in right_items
                if type(left_key) is type(right_key) and left_key == right_key
            ]
            if len(matches) != 1 or not _same_json_value(left_value, matches[0]):
                return False
        return True
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_json_value(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    return left == right


def _safe_repr(value: object) -> str:
    try:
        return repr(value)
    except (OverflowError, ValueError):
        return f"<{type(value).__name__} outside supported representation>"


def _mapping(value: object, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{context} must be an object")
    return value


def _sequence(value: object, context: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ContractValidationError(f"{context} must be an array")
    return value


def _text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{context} must be non-empty text")
    return value


def _text_list(value: object, context: str) -> list[str]:
    items = list(_sequence(value, context))
    if any(not isinstance(item, str) or not item for item in items):
        raise ContractValidationError(f"{context} must contain only non-empty field names")
    if len(items) != len(set(items)):
        raise ContractValidationError(f"{context} contains duplicate field names")
    return items


def _validate_enum_member(value: object, field_type: str, context: str) -> None:
    valid = False
    if field_type == "string":
        valid = isinstance(value, str) and bool(value.strip())
    elif field_type == "integer":
        valid = not isinstance(value, bool) and isinstance(value, Integral)
    elif (
        field_type == "number"
        and not isinstance(value, bool)
        and isinstance(value, Real)
    ):
        try:
            valid = math.isfinite(float(value))
        except (OverflowError, TypeError, ValueError):
            pass
    elif field_type == "date" and isinstance(value, str):
        try:
            date.fromisoformat(value)
        except ValueError:
            pass
        else:
            valid = True
    elif field_type == "datetime" and isinstance(value, str):
        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            pass
        else:
            valid = parsed.tzinfo is not None and parsed.utcoffset() is not None
    elif field_type == "sha256":
        valid = isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None
    if not valid:
        raise ContractValidationError(
            f"{context} enum value {_safe_repr(value)} does not match field type {field_type}"
        )


def _validate_null_rules(value: Mapping[str, Any], context: str) -> tuple[bool, bool]:
    required = value.get("required")
    nullable = value.get("nullable")
    if not isinstance(required, bool) or not isinstance(nullable, bool):
        raise ContractValidationError(
            f"{context} required and nullable must be boolean"
        )
    if required == nullable:
        raise ContractValidationError(
            f"{context} must be required and non-nullable or optional and nullable"
        )
    return required, nullable


def _validate_bound(
    value: object,
    *,
    property_name: str,
    field_type: str,
    context: str,
) -> Real:
    if field_type not in {"integer", "number"}:
        raise ContractValidationError(
            f"{context} cannot bound non-numeric type {field_type}"
        )
    if value is None or isinstance(value, bool) or not isinstance(value, Real):
        raise ContractValidationError(
            f"{context} {property_name} must be finite numeric when present"
        )
    if field_type == "integer" and isinstance(value, Integral):
        try:
            str(value)
        except ValueError:
            raise ContractValidationError(
                f"{context} {property_name} exceeds the supported integer length"
            ) from None
        return value
    try:
        normalized = float(value)
    except (OverflowError, TypeError, ValueError):
        raise ContractValidationError(
            f"{context} {property_name} must be finite numeric when present"
        ) from None
    if not math.isfinite(normalized):
        raise ContractValidationError(
            f"{context} {property_name} must be finite numeric when present"
        )
    if field_type == "integer" and not normalized.is_integer():
        raise ContractValidationError(
            f"{context} {property_name} must be an integer bound"
        )
    if field_type == "number" and normalized != value:
        raise ContractValidationError(
            f"{context} {property_name} does not round-trip through "
            "IEEE-754 normalization"
        )
    return value


def _validate_enum(value: object, *, field_type: str, context: str) -> list[object]:
    enum_values = list(_sequence(value, f"{context} enum"))
    if not enum_values:
        raise ContractValidationError(f"{context} enum must be non-empty and unique")
    for enum_value in enum_values:
        _validate_enum_member(enum_value, field_type, context)
    if len(enum_values) != len({_value_token(item) for item in enum_values}):
        raise ContractValidationError(f"{context} enum must be non-empty and unique")
    return enum_values


def _validate_pattern(value: object, *, field_type: str, context: str) -> None:
    if field_type != "string" or not isinstance(value, str):
        raise ContractValidationError(f"{context} pattern requires a string field")
    try:
        re.compile(value)
    except re.error as error:
        raise ContractValidationError(f"{context} pattern is invalid: {error}") from error


def _validate_column_definition(
    column: Mapping[str, Any],
    context: str,
    *,
    semantic_metadata: bool,
    allowed_extra_properties: set[str] | None = None,
) -> str:
    name = _text(column.get("name"), f"{context} name")
    if _CAMEL_CASE_HEADER_PATTERN.fullmatch(name) is None:
        raise ContractValidationError(
            f"{context} name {name!r} must be a lower camelCase header"
        )
    field_type = column.get("type")
    if not isinstance(field_type, str) or field_type not in _SUPPORTED_TYPES:
        raise ContractValidationError(
            f"{context} {name} uses unsupported type {_safe_repr(field_type)}"
        )
    allowed_properties = {"name", *_STRUCTURAL_PROPERTIES}
    if semantic_metadata:
        allowed_properties.update({"meaning", "unit", "classification"})
    allowed_properties.update(allowed_extra_properties or set())
    unexpected = set(column) - allowed_properties
    if unexpected:
        raise ContractValidationError(
            f"{context} {name} has unknown properties: "
            f"{', '.join(sorted(unexpected))}"
        )
    _validate_null_rules(column, f"{context} {name}")
    bounds: dict[str, Real] = {}
    for property_name in ("minimum", "maximum"):
        if property_name in column:
            bounds[property_name] = _validate_bound(
                column[property_name],
                property_name=property_name,
                field_type=field_type,
                context=f"{context} {name}",
            )
    if (
        "minimum" in bounds
        and "maximum" in bounds
        and bounds["minimum"] > bounds["maximum"]
    ):
        raise ContractValidationError(
            f"{context} {name} minimum cannot exceed maximum"
        )
    if "pattern" in column:
        _validate_pattern(
            column["pattern"], field_type=field_type, context=f"{context} {name}"
        )
    if "enum" in column:
        enum_values = _validate_enum(
            column["enum"], field_type=field_type, context=f"{context} {name}"
        )
        runtime_column = dict(column)
        runtime_column.pop("enum")
        serialized_values: list[str] = []
        for enum_value in enum_values:
            rendered_value = _safe_repr(enum_value)
            serialized = serialize_csv_value(
                enum_value,
                runtime_column,
                context=f"{context} {name} enum value {rendered_value}",
            )
            if field_type == "number" and float(serialized) != enum_value:
                raise ContractValidationError(
                    f"{context} {name} enum value {rendered_value} does not round-trip "
                    "through IEEE-754 normalization"
                )
            if field_type in {"date", "datetime"} and serialized != enum_value:
                raise ContractValidationError(
                    f"{context} {name} enum value {rendered_value} must use canonical "
                    f"{field_type} form {serialized!r}"
                )
            serialized_values.append(serialized)
        if len(serialized_values) != len(set(serialized_values)):
            raise ContractValidationError(
                f"{context} {name} enum values must remain unique after canonical "
                "CSV serialization"
            )
    if semantic_metadata:
        for property_name in ("meaning", "unit", "classification"):
            _text(
                column.get(property_name),
                f"{context} {name} {property_name}",
            )
    if "derivation" in column:
        _text(column.get("derivation"), f"{context} {name} derivation")
    return name


def _column_map(
    value: object,
    context: str,
    *,
    semantic_metadata: bool,
    allowed_extra_properties: set[str] | None = None,
    allow_empty: bool = False,
) -> dict[str, Mapping[str, Any]]:
    columns = list(_sequence(value, context))
    result: dict[str, Mapping[str, Any]] = {}
    for index, raw_column in enumerate(columns, start=1):
        column = _mapping(raw_column, f"{context} column {index}")
        name = _validate_column_definition(
            column,
            f"{context} column {index}",
            semantic_metadata=semantic_metadata,
            allowed_extra_properties=allowed_extra_properties,
        )
        if name in result:
            raise ContractValidationError(f"{context} has duplicate column {name!r}")
        result[name] = column
    if not result and not allow_empty:
        raise ContractValidationError(f"{context} must define at least one column")
    return result


def _validate_unique_key_declarations(
    value: object,
    *,
    columns: Mapping[str, Mapping[str, Any]],
    context: str,
) -> tuple[tuple[str, ...], ...]:
    keys = list(_sequence(value, context))
    if not keys:
        raise ContractValidationError(f"{context} must define at least one key")
    seen: set[tuple[str, ...]] = set()
    declared_keys: list[tuple[str, ...]] = []
    for index, raw_key in enumerate(keys, start=1):
        fields = tuple(_text_list(raw_key, f"{context} key {index}"))
        if not fields:
            raise ContractValidationError(f"{context} key {index} must name fields")
        unknown = set(fields) - set(columns)
        if unknown:
            raise ContractValidationError(
                f"{context} key {index} references unknown fields: "
                f"{', '.join(sorted(unknown))}"
            )
        nullable_fields = [
            field_name
            for field_name in fields
            if columns[field_name].get("required") is not True
            or columns[field_name].get("nullable") is not False
        ]
        if nullable_fields:
            raise ContractValidationError(
                f"{context} key {index} fields must be required and non-nullable: "
                f"{', '.join(nullable_fields)}"
            )
        if fields in seen:
            raise ContractValidationError(f"{context} repeats key {fields!r}")
        seen.add(fields)
        declared_keys.append(fields)
    return tuple(declared_keys)


def _relationship_side(
    value: object,
    *,
    columns_by_file: Mapping[str, Mapping[str, Mapping[str, Any]]],
    context: str,
) -> tuple[str, tuple[str, ...]]:
    side = _mapping(value, context)
    if set(side) != {"file", "columns"}:
        raise ContractValidationError(f"{context} must contain file and columns")
    file_name = _text(side.get("file"), f"{context} file")
    if file_name not in columns_by_file:
        raise ContractValidationError(f"{context} references unknown file {file_name}")
    fields = tuple(_text_list(side.get("columns"), f"{context} columns"))
    if not fields:
        raise ContractValidationError(f"{context} must name columns")
    unknown = set(fields) - set(columns_by_file[file_name])
    if unknown:
        raise ContractValidationError(
            f"{context} references unknown columns in {file_name}: "
            f"{', '.join(sorted(unknown))}"
        )
    return file_name, fields


def _relationship_types(
    file_name: str,
    fields: Sequence[str],
    columns_by_file: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> tuple[str, ...]:
    return tuple(str(columns_by_file[file_name][field_name]["type"]) for field_name in fields)


def _validate_relationship_declarations(
    value: object,
    *,
    columns_by_file: Mapping[str, Mapping[str, Mapping[str, Any]]],
    unique_keys_by_file: Mapping[str, Sequence[Sequence[str]]],
    context: str,
) -> set[tuple[str, str]]:
    relationships = list(_sequence(value, context))
    seen_names: set[str] = set()
    participating_fields: set[tuple[str, str]] = set()
    for index, raw_relationship in enumerate(relationships, start=1):
        relationship = _mapping(raw_relationship, f"{context} relationship {index}")
        name = _text(
            relationship.get("name"), f"{context} relationship {index} name"
        )
        if name in seen_names:
            raise ContractValidationError(f"{context} repeats relationship {name!r}")
        seen_names.add(name)
        kind = relationship.get("kind")
        if kind == "foreignKey":
            if set(relationship) != {"name", "kind", "from", "to"}:
                raise ContractValidationError(
                    f"{context} relationship {name} has invalid foreign-key fields"
                )
            source_file, source_fields = _relationship_side(
                relationship.get("from"),
                columns_by_file=columns_by_file,
                context=f"{context} relationship {name} from",
            )
            target_file, target_fields = _relationship_side(
                relationship.get("to"),
                columns_by_file=columns_by_file,
                context=f"{context} relationship {name} to",
            )
            if len(source_fields) != len(target_fields):
                raise ContractValidationError(
                    f"{context} relationship {name} has different source and target arity"
                )
            source_types = _relationship_types(
                source_file, source_fields, columns_by_file
            )
            target_types = _relationship_types(
                target_file, target_fields, columns_by_file
            )
            if source_types != target_types:
                raise ContractValidationError(
                    f"{context} relationship {name} source and target columns must "
                    "have matching scalar types"
                )
            nullable_source_fields = [
                f"{source_file}.{field_name}"
                for field_name in source_fields
                if columns_by_file[source_file][field_name].get("required") is not True
                or columns_by_file[source_file][field_name].get("nullable") is not False
            ]
            if nullable_source_fields:
                raise ContractValidationError(
                    f"{context} relationship {name} source fields must be required and "
                    f"non-nullable: {', '.join(nullable_source_fields)}"
                )
            participating_fields.update(
                (source_file, field_name) for field_name in source_fields
            )
            participating_fields.update(
                (target_file, field_name) for field_name in target_fields
            )
        elif kind == "exactKeySet":
            if set(relationship) != {"name", "kind", "files", "columns"}:
                raise ContractValidationError(
                    f"{context} relationship {name} has invalid exact-key-set fields"
                )
            file_names = _text_list(
                relationship.get("files"), f"{context} relationship {name} files"
            )
            if len(file_names) < 2:
                raise ContractValidationError(
                    f"{context} relationship {name} must compare at least two files"
                )
            fields = _text_list(
                relationship.get("columns"), f"{context} relationship {name} columns"
            )
            if not fields:
                raise ContractValidationError(
                    f"{context} relationship {name} must name columns"
                )
            expected_types: tuple[str, ...] | None = None
            expected_type_file: str | None = None
            for file_name in file_names:
                if file_name not in columns_by_file:
                    raise ContractValidationError(
                        f"{context} relationship {name} references unknown file {file_name}"
                    )
                unknown = set(fields) - set(columns_by_file[file_name])
                if unknown:
                    raise ContractValidationError(
                        f"{context} relationship {name} references unknown columns in "
                        f"{file_name}: {', '.join(sorted(unknown))}"
                    )
                relationship_fields = set(fields)
                if not any(
                    set(unique_key).issubset(relationship_fields)
                    for unique_key in unique_keys_by_file[file_name]
                ):
                    raise ContractValidationError(
                        f"{context} relationship {name} columns must include a declared "
                        f"unique key for {file_name}"
                    )
                current_types = _relationship_types(
                    file_name, fields, columns_by_file
                )
                if expected_types is None:
                    expected_types = current_types
                    expected_type_file = file_name
                elif current_types != expected_types:
                    raise ContractValidationError(
                        f"{context} relationship {name} columns must have matching "
                        f"scalar types in {expected_type_file} and {file_name}"
                    )
                participating_fields.update(
                    (file_name, field_name) for field_name in fields
                )
        else:
            raise ContractValidationError(
                f"{context} relationship {name} has unsupported kind {kind!r}"
            )
    return participating_fields


def _validate_profile_definition(
    profile_name: str,
    profile: Mapping[str, Any],
    shared_columns: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> set[tuple[str, str]]:
    context = f"Player data profile {profile_name}"
    unexpected_profile_properties = set(profile) - _PROFILE_PROPERTIES
    if unexpected_profile_properties:
        raise ContractValidationError(
            f"{context} has unknown properties: "
            f"{', '.join(sorted(unexpected_profile_properties))}"
        )
    _text(profile.get("schemaResource"), f"{context} schemaResource")
    inventory = _text_list(profile.get("packageInventory"), f"{context} packageInventory")
    if "manifest.json" not in inventory:
        raise ContractValidationError(f"{context} packageInventory must include manifest.json")

    current_orders = _mapping(profile.get("currentColumnOrder"), f"{context} currentColumnOrder")
    row_orders = _mapping(profile.get("rowOrder"), f"{context} rowOrder")
    if set(row_orders) != set(current_orders):
        raise ContractValidationError(f"{context} rowOrder must define every CSV file")
    row_order_fields: dict[str, list[str]] = {}
    for file_name, raw_fields in row_orders.items():
        fields = _text_list(raw_fields, f"{context} rowOrder {file_name}")
        if not fields:
            raise ContractValidationError(f"{context} rowOrder {file_name} must name fields")
        unknown = set(fields) - set(
            _text_list(current_orders[file_name], f"{context} currentColumnOrder {file_name}")
        )
        if unknown:
            raise ContractValidationError(
                f"{context} rowOrder {file_name} references unknown fields: "
                f"{', '.join(sorted(unknown))}"
            )
        row_order_fields[file_name] = fields
    package_extensions = _mapping(
        profile.get("packageFileExtensions"), f"{context} packageFileExtensions"
    )
    for file_name, raw_extension in package_extensions.items():
        if (
            not isinstance(file_name, str)
            or file_name == "manifest.json"
            or file_name.endswith(".csv")
        ):
            raise ContractValidationError(
                f"{context} has invalid package file extension {file_name!r}"
            )
        extension = _mapping(
            raw_extension, f"{context} packageFileExtensions {file_name}"
        )
        if set(extension) != {"rationale", "decision"}:
            raise ContractValidationError(
                f"{context} package file extension {file_name} must declare rationale and decision"
            )
        _text(extension.get("rationale"), f"{context} {file_name} rationale")
        _text(extension.get("decision"), f"{context} {file_name} decision")
    expected_inventory = {"manifest.json", *current_orders, *package_extensions}
    if set(inventory) != expected_inventory:
        raise ContractValidationError(
            f"{context} packageInventory contains undeclared or missing package files"
        )

    extensions = _mapping(profile.get("extensionColumns"), f"{context} extensionColumns")
    profile_files = _mapping(profile.get("profileOnlyFiles"), f"{context} profileOnlyFiles")
    profile_file_overlap = set(profile_files) & set(_SHARED_FILE_NAMES)
    if profile_file_overlap:
        raise ContractValidationError(
            f"{context} profile-only files overlap shared files: "
            f"{', '.join(sorted(profile_file_overlap))}"
        )
    expected_schema_files = {*_SHARED_FILE_NAMES, *profile_files}
    if set(current_orders) != expected_schema_files:
        raise ContractValidationError(
            f"{context} currentColumnOrder must define exactly "
            f"{', '.join(sorted(expected_schema_files))}"
        )
    if set(extensions) != set(_SHARED_FILE_NAMES):
        raise ContractValidationError(
            f"{context} extensionColumns must define all three shared files"
        )

    extension_columns_by_file: dict[str, dict[str, Mapping[str, Any]]] = {}
    for file_name in _SHARED_FILE_NAMES:
        file_extensions = _column_map(
            extensions[file_name],
            f"{context} extensionColumns {file_name}",
            semantic_metadata=True,
            allowed_extra_properties={"rationale", "decision", "derivation"},
            allow_empty=True,
        )
        overlap = set(file_extensions) & set(shared_columns[file_name])
        if overlap:
            raise ContractValidationError(
                f"{context} declares shared fields as extensions in {file_name}: "
                f"{', '.join(sorted(overlap))}"
            )
        for name, column in file_extensions.items():
            _text(column.get("rationale"), f"{context} extension {file_name}.{name} rationale")
            _text(column.get("decision"), f"{context} extension {file_name}.{name} decision")
        extension_columns_by_file[file_name] = file_extensions

    profile_file_columns_by_file: dict[str, dict[str, Mapping[str, Any]]] = {}
    for file_name, raw_file in profile_files.items():
        if not isinstance(file_name, str) or not file_name.endswith(".csv"):
            raise ContractValidationError(f"{context} has invalid profile-only file {file_name!r}")
        file_contract = _mapping(raw_file, f"{context} profileOnlyFiles {file_name}")
        expected_file_properties = {
            "rationale",
            "decision",
            "columns",
            "uniqueKeys",
            "keyRationale",
        }
        if set(file_contract) != expected_file_properties:
            raise ContractValidationError(
                f"{context} profile-only file {file_name} has unknown or missing properties"
            )
        _text(file_contract.get("rationale"), f"{context} {file_name} rationale")
        _text(file_contract.get("decision"), f"{context} {file_name} decision")
        profile_file_columns = _column_map(
            file_contract.get("columns"),
            f"{context} profileOnlyFiles {file_name}",
            semantic_metadata=True,
            allowed_extra_properties={"rationale", "decision", "derivation"},
        )
        profile_file_columns_by_file[file_name] = profile_file_columns
        for name, column in profile_file_columns.items():
            _text(
                column.get("rationale"),
                f"{context} profile-only column {file_name}.{name} rationale",
            )
            _text(
                column.get("decision"),
                f"{context} profile-only column {file_name}.{name} decision",
            )
        _text(file_contract.get("keyRationale"), f"{context} {file_name} keyRationale")

    for file_name, raw_order in current_orders.items():
        order = _text_list(raw_order, f"{context} currentColumnOrder {file_name}")
        if file_name in shared_columns:
            extension_names = set(extension_columns_by_file[file_name])
            missing_extensions = extension_names - set(order)
            if missing_extensions:
                raise ContractValidationError(
                    f"{context} currentColumnOrder {file_name} is missing declared "
                    f"extension columns: {', '.join(sorted(missing_extensions))}"
                )
            allowed = set(shared_columns[file_name]) | extension_names
        else:
            declared_order = list(profile_file_columns_by_file[file_name])
            if order != declared_order:
                raise ContractValidationError(
                    f"{context} currentColumnOrder {file_name} must match its "
                    "profile-only column declaration"
                )
            allowed = set(declared_order)
        unknown = set(order) - allowed
        if unknown:
            raise ContractValidationError(
                f"{context} currentColumnOrder {file_name} contains undeclared fields: "
                f"{', '.join(sorted(unknown))}"
            )

    columns_by_file: dict[str, dict[str, Mapping[str, Any]]] = {}
    for file_name, raw_order in current_orders.items():
        order = _text_list(raw_order, f"{context} currentColumnOrder {file_name}")
        if file_name in shared_columns:
            declared_columns = {
                **shared_columns[file_name],
                **extension_columns_by_file[file_name],
            }
            columns_by_file[file_name] = {
                field_name: declared_columns[field_name] for field_name in order
            }
        else:
            columns_by_file[file_name] = profile_file_columns_by_file[file_name]

    unique_keys = _mapping(profile.get("uniqueKeys"), f"{context} uniqueKeys")
    if set(unique_keys) != set(_SHARED_FILE_NAMES):
        raise ContractValidationError(f"{context} uniqueKeys must define all shared files")
    protected_fields: set[tuple[str, str]] = set()
    unique_keys_by_file: dict[str, tuple[tuple[str, ...], ...]] = {}
    for file_name in _SHARED_FILE_NAMES:
        declared_keys = _validate_unique_key_declarations(
            unique_keys[file_name],
            columns=columns_by_file[file_name],
            context=f"{context} uniqueKeys {file_name}",
        )
        unique_keys_by_file[file_name] = declared_keys
        for declared_key in declared_keys:
            protected_fields.update(
                (file_name, field_name) for field_name in declared_key
            )
    for file_name, raw_file in profile_files.items():
        file_contract = _mapping(raw_file, f"{context} profileOnlyFiles {file_name}")
        unique_keys_by_file[file_name] = _validate_unique_key_declarations(
            file_contract.get("uniqueKeys"),
            columns=columns_by_file[file_name],
            context=f"{context} profileOnlyFiles {file_name} uniqueKeys",
        )
    for file_name, fields in row_order_fields.items():
        row_fields = set(fields)
        if not any(
            set(unique_key).issubset(row_fields)
            for unique_key in unique_keys_by_file[file_name]
        ):
            raise ContractValidationError(
                f"{context} rowOrder {file_name} must include a declared unique key"
            )
    key_rationales = _mapping(profile.get("keyRationales"), f"{context} keyRationales")
    if set(key_rationales) != set(_SHARED_FILE_NAMES):
        raise ContractValidationError(f"{context} keyRationales must define all shared files")
    for file_name, rationale in key_rationales.items():
        _text(rationale, f"{context} keyRationales {file_name}")
    relationship_fields = _validate_relationship_declarations(
        profile.get("relationships"),
        columns_by_file=columns_by_file,
        unique_keys_by_file=unique_keys_by_file,
        context=f"{context} relationships",
    )
    protected_fields.update(
        coordinate
        for coordinate in relationship_fields
        if coordinate[0] in shared_columns
    )

    seen_overrides: set[tuple[str, str]] = set()
    for index, raw_override in enumerate(
        _sequence(profile.get("availabilityOverrides"), f"{context} availabilityOverrides"),
        start=1,
    ):
        override = _mapping(raw_override, f"{context} availability override {index}")
        allowed_keys = {"file", "fields", "required", "nullable", "rationale", "decision"}
        if set(override) != allowed_keys:
            raise ContractValidationError(
                f"{context} availability override {index} may change only required and nullable"
            )
        file_name = _text(override.get("file"), f"{context} availability override {index} file")
        if file_name not in shared_columns:
            raise ContractValidationError(
                f"{context} availability override {index} references unknown shared file "
                f"{file_name}"
            )
        fields = _text_list(
            override.get("fields"), f"{context} availability override {index} fields"
        )
        if not fields:
            raise ContractValidationError(
                f"{context} availability override {index} must name fields"
            )
        _validate_null_rules(override, f"{context} availability override {index}")
        _text(override.get("rationale"), f"{context} availability override {index} rationale")
        _text(override.get("decision"), f"{context} availability override {index} decision")
        for field in fields:
            if field not in shared_columns[file_name]:
                raise ContractValidationError(
                    f"{context} availability override references unknown field {file_name}.{field}"
                )
            key = (file_name, field)
            if key in protected_fields:
                raise ContractValidationError(
                    f"{context} availability override may not change key or relationship "
                    f"field {file_name}.{field}"
                )
            if key in seen_overrides:
                raise ContractValidationError(
                    f"{context} repeats availability override for {file_name}.{field}"
                )
            seen_overrides.add(key)

    seen_constraints: set[tuple[str, str, str]] = set()
    for index, raw_constraint in enumerate(
        _sequence(profile.get("fieldConstraints"), f"{context} fieldConstraints"), start=1
    ):
        constraint = _mapping(raw_constraint, f"{context} field constraint {index}")
        allowed_keys = {"files", "field", "property", "value", "rationale", "decision"}
        if set(constraint) != allowed_keys or constraint.get("property") != "pattern":
            raise ContractValidationError(
                f"{context} field constraint {index} must be a declared pattern constraint"
            )
        field_name = _text(
            constraint.get("field"), f"{context} field constraint {index} field"
        )
        constraint_files = _text_list(
            constraint.get("files"), f"{context} field constraint {index} files"
        )
        if not constraint_files:
            raise ContractValidationError(
                f"{context} field constraint {index} must name files"
            )
        for file_name in constraint_files:
            if file_name not in shared_columns or field_name not in shared_columns[file_name]:
                raise ContractValidationError(
                    f"{context} field constraint references unknown field {file_name}.{field_name}"
                )
            if shared_columns[file_name][field_name]["type"] != "string":
                raise ContractValidationError(
                    f"{context} field constraint pattern requires a string field: "
                    f"{file_name}.{field_name}"
                )
            key = (file_name, field_name, str(constraint["property"]))
            if key in seen_constraints:
                raise ContractValidationError(
                    f"{context} repeats field constraint for {file_name}.{field_name}"
                )
            seen_constraints.add(key)
        pattern = _text(
            constraint.get("value"), f"{context} field constraint {index} value"
        )
        try:
            re.compile(pattern)
        except re.error as error:
            raise ContractValidationError(
                f"{context} field constraint {index} pattern is invalid: {error}"
            ) from error
        for file_name in constraint_files:
            effective_column = dict(shared_columns[file_name][field_name])
            effective_column["pattern"] = pattern
            _validate_column_definition(
                effective_column,
                (
                    f"{context} field constraint {index} effective "
                    f"{file_name}.{field_name}"
                ),
                semantic_metadata=True,
                allowed_extra_properties={"derivation"},
            )
        _text(constraint.get("rationale"), f"{context} field constraint {index} rationale")
        _text(constraint.get("decision"), f"{context} field constraint {index} decision")

    return {
        (file_name, field_name)
        for file_name, field_name in protected_fields
        if file_name in shared_columns and field_name in shared_columns[file_name]
    }


def _shared_column_maps(
    contract: Mapping[str, Any],
) -> dict[str, dict[str, Mapping[str, Any]]]:
    shared_files = _mapping(contract.get("sharedFiles"), "Player data sharedFiles")
    if tuple(shared_files) != _SHARED_FILE_NAMES:
        raise ContractValidationError(
            "Player data sharedFiles must define players.csv, player_stats.csv, and "
            "player_attributes.csv in that order"
        )
    result: dict[str, dict[str, Mapping[str, Any]]] = {}
    for file_name in _SHARED_FILE_NAMES:
        file_contract = _mapping(
            shared_files[file_name], f"Player data shared file {file_name}"
        )
        if set(file_contract) != {"columns"}:
            raise ContractValidationError(
                f"Player data shared file {file_name} may contain only columns"
            )
        result[file_name] = _column_map(
            file_contract.get("columns"),
            f"Player data shared file {file_name}",
            semantic_metadata=True,
            allowed_extra_properties={"derivation"},
        )
    return result


def _validate_gap_current_definitions(
    gaps: Sequence[Mapping[str, Any]],
    shared_columns: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    current_definitions: dict[str, dict[str, dict[str, dict[str, Any]]]] = {
        profile_name: {
            file_name: {
                field_name: dict(deepcopy(column))
                for field_name, column in file_columns.items()
            }
            for file_name, file_columns in shared_columns.items()
        }
        for profile_name in _PROFILE_NAMES
    }
    affected_fields: set[tuple[str, str, str]] = set()
    for gap in gaps:
        if gap["kind"] != "sharedDefinition":
            continue
        profile_name = str(gap["profile"])
        file_name = str(gap["file"])
        properties = [str(property_name) for property_name in gap["properties"]]
        current_values = _mapping(
            gap["currentValues"], "Player data alignment gap currentValues"
        )
        for field_name in gap["fields"]:
            definition = current_definitions[profile_name][file_name][str(field_name)]
            for property_name in properties:
                current_value = current_values[property_name]
                if _is_absence_marker(current_value):
                    definition.pop(property_name, None)
                else:
                    definition[property_name] = deepcopy(current_value)
            affected_fields.add((profile_name, file_name, str(field_name)))

    for profile_name, file_name, field_name in sorted(affected_fields):
        _validate_column_definition(
            current_definitions[profile_name][file_name][field_name],
            (
                "Player data declared current definition "
                f"{profile_name} {file_name}.{field_name}"
            ),
            semantic_metadata=True,
            allowed_extra_properties={"derivation"},
        )
    return current_definitions


def validate_player_data_contract_family(contract: Mapping[str, Any]) -> None:
    """Validate the authored family resource and its closed profile declarations."""
    unexpected_family_properties = set(contract) - _FAMILY_PROPERTIES
    if unexpected_family_properties:
        raise ContractValidationError(
            "Player data contract has unknown properties: "
            f"{', '.join(sorted(unexpected_family_properties))}"
        )
    _text(contract.get("title"), "Player data contract title")
    _text(contract.get("description"), "Player data contract description")
    if contract.get("contractFamily") != PLAYER_DATA_CONTRACT_FAMILY:
        raise ContractValidationError(
            f"Player data contract must declare family {PLAYER_DATA_CONTRACT_FAMILY!r}"
        )
    if not _same_json_value(
        contract.get("contractVersion", _MISSING), PLAYER_DATA_CONTRACT_VERSION
    ):
        raise ContractValidationError(
            f"Player data contract must declare version {PLAYER_DATA_CONTRACT_VERSION}"
        )
    csv_rules = _mapping(contract.get("csv"), "Player data csv conventions")
    if set(csv_rules) != {*_CSV_RULES, "numericSerializationDescription"}:
        raise ContractValidationError(
            "Player data csv conventions have unexpected or missing rules"
        )
    for property_name, expected in _CSV_RULES.items():
        if not _same_json_value(csv_rules.get(property_name, _MISSING), expected):
            raise ContractValidationError(
                f"Player data csv {property_name} must be {expected!r}"
            )
    _text(
        csv_rules.get("numericSerializationDescription"),
        "Player data csv numericSerializationDescription",
    )

    shared_columns = _shared_column_maps(contract)
    profiles = _mapping(contract.get("profiles"), "Player data profiles")
    if tuple(profiles) != _PROFILE_NAMES:
        raise ContractValidationError(
            "Player data profiles must define reference and roster in that order"
        )
    protected_fields_by_profile: dict[str, set[tuple[str, str]]] = {}
    for profile_name in _PROFILE_NAMES:
        protected_fields_by_profile[profile_name] = _validate_profile_definition(
            profile_name,
            _mapping(profiles[profile_name], f"Player data profile {profile_name}"),
            shared_columns,
        )

    declared_gaps: list[Mapping[str, Any]] = []
    seen_gap_coordinates: set[tuple[str, str, str, str]] = set()
    seen_csv_gap_coordinates: set[tuple[str, str]] = set()
    for index, raw_gap in enumerate(
        _sequence(contract.get("declaredAlignmentGaps"), "Player data declaredAlignmentGaps"),
        start=1,
    ):
        gap = _mapping(raw_gap, f"Player data alignment gap {index}")
        kind = gap.get("kind")
        required_keys = {"kind", "profile", "rationale", "followUp"}
        if kind != "profileCsvRules":
            required_keys.add("file")
        if kind in {"missingSharedColumns", "sharedDefinition"}:
            required_keys.add("fields")
        if kind == "sharedOrder":
            required_keys.add("currentOrder")
        if kind == "sharedDefinition":
            required_keys.add("properties")
            required_keys.add("currentValues")
        if kind == "profileCsvRules":
            required_keys.add("properties")
            required_keys.add("currentValues")
        if kind not in {
            "missingSharedColumns",
            "sharedOrder",
            "sharedDefinition",
            "profileCsvRules",
        }:
            raise ContractValidationError(
                f"Player data alignment gap {index} has unsupported kind {_safe_repr(kind)}"
            )
        if set(gap) != required_keys:
            raise ContractValidationError(
                f"Player data alignment gap {index} has invalid fields for {kind}"
            )
        profile_name = gap.get("profile")
        if profile_name not in _PROFILE_NAMES:
            raise ContractValidationError(
                f"Player data alignment gap {index} references an unknown profile"
            )
        _text(gap.get("rationale"), f"Player data alignment gap {index} rationale")
        _text(gap.get("followUp"), f"Player data alignment gap {index} followUp")
        if kind == "profileCsvRules":
            properties = _text_list(
                gap["properties"], f"Player data alignment gap {index} properties"
            )
            if not properties or any(
                property_name not in _PROFILE_CSV_RULE_PROPERTIES
                for property_name in properties
            ):
                raise ContractValidationError(
                    f"Player data alignment gap {index} references unknown CSV rules"
                )
            current_values = _mapping(
                gap["currentValues"],
                f"Player data alignment gap {index} currentValues",
            )
            if set(current_values) != set(properties):
                raise ContractValidationError(
                    f"Player data alignment gap {index} currentValues must match properties"
                )
            for property_name, value in current_values.items():
                if isinstance(value, Mapping) and not _is_absence_marker(value):
                    raise ContractValidationError(
                        f"Player data alignment gap {index} current value for "
                        f"{property_name} has an invalid absence marker"
                    )
                coordinate = (str(profile_name), property_name)
                if coordinate in seen_csv_gap_coordinates:
                    raise ContractValidationError(
                        f"Player data alignment gap {index} repeats current CSV rule "
                        f"for {profile_name}.{property_name}"
                    )
                seen_csv_gap_coordinates.add(coordinate)
            declared_gaps.append(gap)
            continue

        file_name = gap.get("file")
        if file_name not in shared_columns:
            raise ContractValidationError(
                f"Player data alignment gap {index} references an unknown file"
            )
        if "fields" in gap:
            for field in _text_list(gap["fields"], f"Player data alignment gap {index} fields"):
                if field not in shared_columns[str(file_name)]:
                    raise ContractValidationError(
                        f"Player data alignment gap {index} references unknown shared field "
                        f"{file_name}.{field}"
                    )
        if "properties" in gap:
            properties = _text_list(
                gap["properties"], f"Player data alignment gap {index} properties"
            )
            if any(property_name not in _GAP_DEFINITION_PROPERTIES for property_name in properties):
                raise ContractValidationError(
                    f"Player data alignment gap {index} may not waive null rules or semantics"
                )
            current_values = _mapping(
                gap["currentValues"], f"Player data alignment gap {index} currentValues"
            )
            if set(current_values) != set(properties):
                raise ContractValidationError(
                    f"Player data alignment gap {index} currentValues must match properties"
                )
            for property_name, value in current_values.items():
                if isinstance(value, Mapping) and not _is_absence_marker(value):
                    raise ContractValidationError(
                        f"Player data alignment gap {index} current value for {property_name} "
                        "has an invalid absence marker"
                    )
            for field_name in _text_list(
                gap["fields"], f"Player data alignment gap {index} fields"
            ):
                for property_name in properties:
                    coordinate = (
                        str(profile_name),
                        str(file_name),
                        field_name,
                        property_name,
                    )
                    if coordinate in seen_gap_coordinates:
                        raise ContractValidationError(
                            f"Player data alignment gap {index} repeats current definition "
                            f"for {profile_name}.{file_name}.{field_name}.{property_name}"
                        )
                    seen_gap_coordinates.add(coordinate)
        if "currentOrder" in gap:
            current_order = _text_list(
                gap["currentOrder"], f"Player data alignment gap {index} currentOrder"
            )
            unknown = set(current_order) - set(shared_columns[str(file_name)])
            if unknown:
                raise ContractValidationError(
                    f"Player data alignment gap {index} currentOrder contains unknown fields: "
                    f"{', '.join(sorted(unknown))}"
                )
        declared_gaps.append(gap)

    current_shared_columns = _validate_gap_current_definitions(
        declared_gaps, shared_columns
    )
    for profile_name in _PROFILE_NAMES:
        _validate_profile_definition(
            profile_name,
            _mapping(profiles[profile_name], f"Player data profile {profile_name}"),
            current_shared_columns[profile_name],
        )
        for file_name, field_name in sorted(protected_fields_by_profile[profile_name]):
            current_type = current_shared_columns[profile_name][file_name][field_name][
                "type"
            ]
            target_type = shared_columns[file_name][field_name]["type"]
            if current_type != target_type:
                raise ContractValidationError(
                    f"Player data profile {profile_name} may not change the type of key or "
                    f"relationship field {file_name}.{field_name}"
                )

    seen_gap_codes: set[str] = set()
    for index, gap in enumerate(declared_gaps, start=1):
        current_codes = _codes_for_gap(contract, gap)
        duplicates = current_codes & seen_gap_codes
        if duplicates:
            raise ContractValidationError(
                f"Player data alignment gap {index} duplicates declared issues: "
                f"{', '.join(sorted(duplicates))}"
            )
        seen_gap_codes.update(current_codes)


def _load_resource(resource_name: str, *, label: str) -> dict[str, Any]:
    resource = files("player_data_contracts").joinpath(resource_name)
    try:
        with resource.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError(f"Unable to load {label}: {error}") from error
    if not isinstance(payload, dict):
        raise ContractValidationError(f"{label} must be a JSON object")
    return payload


def load_player_data_contract(
    version: int = PLAYER_DATA_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Load the authored shared player-data contract family."""
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version != PLAYER_DATA_CONTRACT_VERSION
    ):
        raise ContractValidationError(f"Unsupported player data contract version: {version}")
    contract = _load_resource(_FAMILY_SCHEMA_NAME, label="player data contract version 1")
    validate_player_data_contract_family(contract)
    return contract


def _availability_overrides(profile: Mapping[str, Any]) -> dict[tuple[str, str], dict[str, bool]]:
    result: dict[tuple[str, str], dict[str, bool]] = {}
    for raw_override in profile["availabilityOverrides"]:
        override = _mapping(raw_override, "availability override")
        for field in override["fields"]:
            result[(str(override["file"]), str(field))] = {
                "required": bool(override["required"]),
                "nullable": bool(override["nullable"]),
            }
    return result


def _field_constraints(profile: Mapping[str, Any]) -> dict[tuple[str, str, str], object]:
    result: dict[tuple[str, str, str], object] = {}
    for raw_constraint in profile["fieldConstraints"]:
        constraint = _mapping(raw_constraint, "field constraint")
        for file_name in constraint["files"]:
            result[(str(file_name), str(constraint["field"]), str(constraint["property"]))] = (
                constraint["value"]
            )
    return result


def _structural_column(column: Mapping[str, Any]) -> dict[str, object]:
    return {
        property_name: deepcopy(column[property_name])
        for property_name in _STRUCTURAL_PROPERTIES
        if property_name in column
    }


def _value_token(value: object) -> str:
    if value is _MISSING:
        return "<absent>"
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        raise ContractValidationError(
            "Contract value cannot be represented as canonical JSON"
        ) from None


def _declared_current_value(value: object) -> object:
    return _MISSING if _is_absence_marker(value) else value


def _csv_issue_code(
    profile_name: str,
    property_name: str,
    current_value: object,
    target_value: object,
) -> str:
    return (
        f"csv:{profile_name}:{property_name}:"
        f"current={_value_token(current_value)}:target={_value_token(target_value)}"
    )


def _definition_issue_code(
    profile_name: str,
    file_name: str,
    field_name: str,
    property_name: str,
    current_value: object,
    target_value: object,
) -> str:
    return (
        f"definition:{profile_name}:{file_name}:{field_name}:{property_name}:"
        f"current={_value_token(current_value)}:target={_value_token(target_value)}"
    )


def _order_issue_code(
    profile_name: str,
    file_name: str,
    current_order: Sequence[str],
    target_order: Sequence[str],
) -> str:
    return (
        f"shared-order:{profile_name}:{file_name}:"
        f"current={_value_token(list(current_order))}:target={_value_token(list(target_order))}"
    )


def _codes_for_gap(contract: Mapping[str, Any], gap: Mapping[str, Any]) -> set[str]:
    profile_name = str(gap["profile"])
    if gap["kind"] == "profileCsvRules":
        current_values = _mapping(gap["currentValues"], "alignment gap currentValues")
        csv_rules = _mapping(contract["csv"], "csv")
        return {
            _csv_issue_code(
                profile_name,
                str(property_name),
                _declared_current_value(current_values[property_name]),
                csv_rules[property_name],
            )
            for property_name in gap["properties"]
        }
    file_name = str(gap["file"])
    prefix = f"{profile_name}:{file_name}"
    if gap["kind"] == "missingSharedColumns":
        return {f"missing:{prefix}:{field}" for field in gap["fields"]}
    shared_columns = _shared_column_maps(contract)[file_name]
    if gap["kind"] == "sharedOrder":
        missing: set[str] = set()
        for raw_candidate in contract["declaredAlignmentGaps"]:
            if not isinstance(raw_candidate, Mapping):
                continue
            if (
                raw_candidate.get("kind") == "missingSharedColumns"
                and raw_candidate.get("profile") == profile_name
                and raw_candidate.get("file") == file_name
            ):
                raw_fields = raw_candidate.get("fields", [])
                if isinstance(raw_fields, Sequence) and not isinstance(
                    raw_fields, (str, bytes)
                ):
                    missing.update(str(field) for field in raw_fields)
        target_order = [field for field in shared_columns if field not in missing]
        return {
            _order_issue_code(
                profile_name,
                file_name,
                [str(field) for field in gap["currentOrder"]],
                target_order,
            )
        }
    current_values = _mapping(gap["currentValues"], "alignment gap currentValues")
    return {
        _definition_issue_code(
            profile_name,
            file_name,
            str(field),
            str(property_name),
            _declared_current_value(current_values[property_name]),
            shared_columns[str(field)].get(str(property_name), _MISSING),
        )
        for field in gap["fields"]
        for property_name in gap["properties"]
    }


def _gap_codes(contract: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for raw_gap in contract["declaredAlignmentGaps"]:
        gap = _mapping(raw_gap, "alignment gap")
        result.update(_codes_for_gap(contract, gap))
    return result


def _profile_only_unique_keys(profile: Mapping[str, Any], file_name: str) -> object:
    profile_files = _mapping(profile["profileOnlyFiles"], "profileOnlyFiles")
    return _mapping(profile_files[file_name], f"profileOnlyFiles {file_name}").get(
        "uniqueKeys", []
    )


def _collect_profile_issues(
    family: Mapping[str, Any],
    profile_name: str,
    profile_contract: Mapping[str, Any],
) -> set[str]:
    issues: set[str] = set()
    profile = _mapping(
        _mapping(family["profiles"], "profiles")[profile_name],
        f"profile {profile_name}",
    )
    shared_columns = _shared_column_maps(family)
    current_orders = _mapping(profile["currentColumnOrder"], "currentColumnOrder")
    file_contracts = profile_contract.get("files")
    if not isinstance(file_contracts, Mapping):
        return {f"schema-files:{profile_name}"}

    if not _same_json_value(
        profile_contract.get("contractVersion", _MISSING), family["contractVersion"]
    ):
        issues.add(f"contract-version:{profile_name}")
    csv_rules = _mapping(family["csv"], "csv")
    for property_name in _PROFILE_CSV_RULE_PROPERTIES:
        current_value = profile_contract.get(property_name, _MISSING)
        target_value = csv_rules[property_name]
        if not _same_json_value(current_value, target_value):
            issues.add(
                _csv_issue_code(
                    profile_name,
                    property_name,
                    current_value,
                    target_value,
                )
            )
    unexpected_schema_properties = set(profile_contract) - _PROFILE_SCHEMA_PROPERTIES
    if unexpected_schema_properties:
        issues.add(
            f"schema-properties:{profile_name}:"
            f"{','.join(sorted(str(item) for item in unexpected_schema_properties))}"
        )
    if set(file_contracts) != set(current_orders):
        issues.add(f"schema-files:{profile_name}")

    overrides = _availability_overrides(profile)
    constraints = _field_constraints(profile)
    extensions_by_file = {
        file_name: {
            column["name"]: column for column in profile["extensionColumns"][file_name]
        }
        for file_name in _SHARED_FILE_NAMES
    }
    unique_keys = _mapping(profile["uniqueKeys"], "uniqueKeys")

    for file_name, raw_order in current_orders.items():
        if file_name not in file_contracts:
            continue
        actual_file = file_contracts[file_name]
        if not isinstance(actual_file, Mapping):
            issues.add(f"file-definition:{profile_name}:{file_name}")
            continue
        unexpected_file_properties = set(actual_file) - _PROFILE_FILE_PROPERTIES
        if unexpected_file_properties:
            issues.add(
                f"file-properties:{profile_name}:{file_name}:"
                f"{','.join(sorted(str(item) for item in unexpected_file_properties))}"
            )
        actual_columns_raw = actual_file.get("columns")
        if not isinstance(actual_columns_raw, list) or any(
            not isinstance(column, Mapping) for column in actual_columns_raw
        ):
            issues.add(f"columns:{profile_name}:{file_name}")
            continue
        actual_columns = {str(column.get("name")): column for column in actual_columns_raw}
        actual_order = [str(column.get("name")) for column in actual_columns_raw]
        if actual_order != list(raw_order):
            issues.add(f"column-order:{profile_name}:{file_name}")

        expected_keys = (
            unique_keys[file_name]
            if file_name in unique_keys
            else _profile_only_unique_keys(profile, file_name)
        )
        if not _same_json_value(actual_file.get("uniqueKeys", []), expected_keys):
            issues.add(f"unique-keys:{profile_name}:{file_name}")
        for field_name, actual_column in actual_columns.items():
            unexpected_properties = set(actual_column) - _PROFILE_COLUMN_PROPERTIES
            if unexpected_properties:
                issues.add(
                    f"column-properties:{profile_name}:{file_name}:{field_name}:"
                    f"{','.join(sorted(str(item) for item in unexpected_properties))}"
                )

        if file_name not in shared_columns:
            expected_file = _mapping(
                _mapping(profile["profileOnlyFiles"], "profileOnlyFiles")[file_name],
                f"profileOnlyFiles {file_name}",
            )
            expected_columns = _column_map(
                expected_file["columns"],
                f"profileOnlyFiles {file_name}",
                semantic_metadata=True,
                allowed_extra_properties={"rationale", "decision", "derivation"},
            )
            for field_name, expected_column in expected_columns.items():
                actual_column = actual_columns.get(field_name)
                if actual_column is None:
                    issues.add(f"missing-profile-field:{profile_name}:{file_name}:{field_name}")
                    continue
                if not _same_json_value(
                    _structural_column(actual_column),
                    _structural_column(expected_column),
                ):
                    issues.add(
                        f"profile-field-definition:{profile_name}:{file_name}:{field_name}"
                    )
            continue

        target_columns = shared_columns[file_name]
        target_order = list(target_columns)
        actual_shared_order = [field for field in actual_order if field in target_columns]
        target_present_order = [field for field in target_order if field in actual_columns]
        if actual_shared_order != target_present_order:
            issues.add(
                _order_issue_code(
                    profile_name,
                    file_name,
                    actual_shared_order,
                    target_present_order,
                )
            )

        for field_name, target_column in target_columns.items():
            actual_column = actual_columns.get(field_name)
            if actual_column is None:
                issues.add(f"missing:{profile_name}:{file_name}:{field_name}")
                continue
            expected = _structural_column(target_column)
            expected.update(overrides.get((file_name, field_name), {}))
            for property_name in _STRUCTURAL_PROPERTIES:
                constraint_key = (file_name, field_name, property_name)
                if constraint_key in constraints:
                    expected[property_name] = constraints[constraint_key]
                actual_value = actual_column.get(property_name, _MISSING)
                expected_value = expected.get(property_name, _MISSING)
                if not _same_json_value(actual_value, expected_value):
                    issues.add(
                        _definition_issue_code(
                            profile_name,
                            file_name,
                            field_name,
                            property_name,
                            actual_value,
                            expected_value,
                        )
                    )

        extensions = extensions_by_file[file_name]
        for field_name, actual_column in actual_columns.items():
            if field_name in target_columns:
                continue
            expected_extension = extensions.get(field_name)
            if expected_extension is None:
                issues.add(f"undeclared-extension:{profile_name}:{file_name}:{field_name}")
            elif not _same_json_value(
                _structural_column(actual_column),
                _structural_column(expected_extension),
            ):
                issues.add(
                    f"extension-definition:{profile_name}:{file_name}:{field_name}"
                )
        for field_name in extensions:
            if field_name not in actual_columns:
                issues.add(f"missing-extension:{profile_name}:{file_name}:{field_name}")

    if not _same_json_value(
        profile_contract.get("relationships", _MISSING), profile["relationships"]
    ):
        issues.add(f"relationships:{profile_name}")
    return issues


def validate_player_data_profile_parity(
    *,
    family: Mapping[str, Any] | None = None,
    reference_contract: Mapping[str, Any] | None = None,
    roster_contract: Mapping[str, Any] | None = None,
) -> None:
    """Reject profile drift beyond the family resource's explicit temporary gap ledger."""
    active_family = family if family is not None else load_player_data_contract()
    validate_player_data_contract_family(active_family)
    profiles = _mapping(active_family["profiles"], "Player data profiles")
    active_reference = (
        reference_contract
        if reference_contract is not None
        else _load_resource(
            str(_mapping(profiles["reference"], "reference profile")["schemaResource"]),
            label="reference profile contract",
        )
    )
    active_roster = (
        roster_contract
        if roster_contract is not None
        else _load_resource(
            str(_mapping(profiles["roster"], "roster profile")["schemaResource"]),
            label="roster profile contract",
        )
    )
    actual = _collect_profile_issues(active_family, "reference", active_reference)
    actual.update(_collect_profile_issues(active_family, "roster", active_roster))
    declared = _gap_codes(active_family)
    unexpected = sorted(actual - declared)
    stale = sorted(declared - actual)
    if unexpected or stale:
        details: list[str] = []
        if unexpected:
            details.append(f"unexpected issues: {', '.join(unexpected)}")
        if stale:
            details.append(f"declared gaps no longer observed: {', '.join(stale)}")
        raise ContractValidationError(
            "Player data profile parity differs from the declared alignment ledger; "
            + "; ".join(details)
        )
