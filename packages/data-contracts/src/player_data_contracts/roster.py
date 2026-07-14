"""Versioned contracts and semantic validation for roster CSV packages."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from importlib.resources import files
from pathlib import Path
from typing import Any, Final

from player_data_contracts.csv_contract import (
    contract_files,
    validate_csv_package,
    validate_csv_tables,
)
from player_data_contracts.validation import ContractValidationError

ROSTER_CONTRACT_VERSION: Final = 1

_ROSTER_SCHEMA_NAME = "schemas/roster-v1.schema.json"
_CONTRACT_NAME = "Roster"
_RELATIVE_TOLERANCE = 1e-8
_ABSOLUTE_TOLERANCE = 1e-7


def load_roster_contract(version: int = ROSTER_CONTRACT_VERSION) -> dict[str, Any]:
    """Load the machine-readable normalized roster CSV contract."""
    if version != ROSTER_CONTRACT_VERSION:
        raise ContractValidationError(f"Unsupported roster contract version: {version}")

    resource = files("player_data_contracts").joinpath(_ROSTER_SCHEMA_NAME)
    try:
        with resource.open("r", encoding="utf-8") as handle:
            contract = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError(
            f"Unable to load roster contract version {version}: {error}"
        ) from error
    if not isinstance(contract, dict) or contract.get("contractVersion") != version:
        raise ContractValidationError(
            f"Roster contract resource does not declare version {version}"
        )
    contract_files(
        contract,
        contract_name=_CONTRACT_NAME,
        contract_version=ROSTER_CONTRACT_VERSION,
    )
    return contract


def _number(row: Mapping[str, object], field: str) -> float | None:
    value = row[field]
    return None if value is None else float(value)


def _semantic_error(
    file_name: str, row_index: int, field: str, detail: str
) -> ContractValidationError:
    return ContractValidationError(
        f"{file_name} row {row_index} field {field} violates semantic invariant: {detail}"
    )


def _require_close(
    *,
    file_name: str,
    row_index: int,
    field: str,
    actual: float,
    expected: float,
    formula: str,
) -> None:
    if not math.isclose(
        actual,
        expected,
        rel_tol=_RELATIVE_TOLERANCE,
        abs_tol=_ABSOLUTE_TOLERANCE,
    ):
        raise _semantic_error(
            file_name,
            row_index,
            field,
            f"expected {expected:.12g} from {formula}, found {actual:.12g}",
        )


def _validate_derived(
    row: Mapping[str, object],
    *,
    file_name: str,
    row_index: int,
    field: str,
    numerator: float | None,
    denominator: float | None,
    formula: str,
    scale: float = 1.0,
) -> None:
    actual = _number(row, field)
    if numerator is None or denominator is None or denominator == 0:
        if actual is not None:
            raise _semantic_error(
                file_name,
                row_index,
                field,
                f"must be empty when {formula} has an unavailable or zero denominator",
            )
        return
    if actual is None:
        raise _semantic_error(
            file_name,
            row_index,
            field,
            f"is required when {formula} is available",
        )
    _require_close(
        file_name=file_name,
        row_index=row_index,
        field=field,
        actual=actual,
        expected=numerator / denominator * scale,
        formula=formula,
    )


def _validate_difference(
    row: Mapping[str, object],
    *,
    file_name: str,
    row_index: int,
    field: str,
    minuend_field: str,
    subtrahend_field: str,
) -> None:
    actual = _number(row, field)
    minuend = _number(row, minuend_field)
    subtrahend = _number(row, subtrahend_field)
    formula = f"{minuend_field} - {subtrahend_field}"
    if minuend is None or subtrahend is None:
        if actual is not None:
            raise _semantic_error(
                file_name,
                row_index,
                field,
                f"must be empty when {formula} has an unavailable operand",
            )
        return
    if actual is None:
        raise _semantic_error(
            file_name,
            row_index,
            field,
            f"is required when {formula} is available",
        )
    _require_close(
        file_name=file_name,
        row_index=row_index,
        field=field,
        actual=actual,
        expected=minuend - subtrahend,
        formula=formula,
    )


def _validate_traditional_row(row: Mapping[str, object], row_index: int) -> None:
    file_name = "player_stats.csv"
    minutes = float(row["minutes"])
    possessions = float(row["possessions"])
    if minutes <= 0:
        raise _semantic_error(file_name, row_index, "minutes", "must be greater than zero")
    if possessions <= 0:
        raise _semantic_error(file_name, row_index, "possessions", "must be greater than zero")

    for made_field, attempted_field in (
        ("fieldGoalsMade", "fieldGoalsAttempted"),
        ("twoPointersMade", "twoPointersAttempted"),
        ("threePointersMade", "threePointersAttempted"),
        ("freeThrowsMade", "freeThrowsAttempted"),
    ):
        if int(row[made_field]) > int(row[attempted_field]):
            raise _semantic_error(
                file_name,
                row_index,
                made_field,
                f"cannot exceed {attempted_field}",
            )

    exact_equations = (
        (
            "fieldGoalsMade",
            int(row["twoPointersMade"]) + int(row["threePointersMade"]),
            "twoPointersMade + threePointersMade",
        ),
        (
            "fieldGoalsAttempted",
            int(row["twoPointersAttempted"]) + int(row["threePointersAttempted"]),
            "twoPointersAttempted + threePointersAttempted",
        ),
        (
            "points",
            2 * int(row["twoPointersMade"])
            + 3 * int(row["threePointersMade"])
            + int(row["freeThrowsMade"]),
            "2 * twoPointersMade + 3 * threePointersMade + freeThrowsMade",
        ),
    )
    for field, expected, formula in exact_equations:
        if int(row[field]) != expected:
            raise _semantic_error(
                file_name,
                row_index,
                field,
                f"expected {expected} from {formula}, found {row[field]}",
            )

    rebounds_offensive = _number(row, "reboundsOffensive")
    rebounds_defensive = _number(row, "reboundsDefensive")
    rebounds_total = _number(row, "reboundsTotal")
    if rebounds_offensive is None or rebounds_defensive is None:
        if rebounds_total is not None:
            raise _semantic_error(
                file_name,
                row_index,
                "reboundsTotal",
                "must be empty when an offensive or defensive rebound total is unavailable",
            )
    elif rebounds_total is None:
        raise _semantic_error(
            file_name,
            row_index,
            "reboundsTotal",
            "is required when offensive and defensive rebound totals are available",
        )
    elif rebounds_total != rebounds_offensive + rebounds_defensive:
        raise _semantic_error(
            file_name,
            row_index,
            "reboundsTotal",
            "expected "
            f"{rebounds_offensive + rebounds_defensive:g} from "
            "reboundsOffensive + reboundsDefensive, "
            f"found {rebounds_total:g}",
        )

    for field, numerator_field, denominator_field in (
        ("fieldGoalPercentage", "fieldGoalsMade", "fieldGoalsAttempted"),
        ("twoPointPercentage", "twoPointersMade", "twoPointersAttempted"),
        ("threePointPercentage", "threePointersMade", "threePointersAttempted"),
        ("freeThrowPercentage", "freeThrowsMade", "freeThrowsAttempted"),
        ("twoPointAttemptFrequency", "twoPointersAttempted", "fieldGoalsAttempted"),
        ("threePointAttemptFrequency", "threePointersAttempted", "fieldGoalsAttempted"),
    ):
        _validate_derived(
            row,
            file_name=file_name,
            row_index=row_index,
            field=field,
            numerator=_number(row, numerator_field),
            denominator=_number(row, denominator_field),
            formula=f"{numerator_field} / {denominator_field}",
        )

    for field, numerator_field in (
        ("minutesPerGame", "minutes"),
        ("pointsPerGame", "points"),
        ("reboundsPerGame", "reboundsTotal"),
        ("assistsPerGame", "assists"),
        ("turnoversPerGame", "turnovers"),
    ):
        _validate_derived(
            row,
            file_name=file_name,
            row_index=row_index,
            field=field,
            numerator=_number(row, numerator_field),
            denominator=_number(row, "games"),
            formula=f"{numerator_field} / games",
        )

    for field, numerator_field in (
        ("threePointAttemptsPer36", "threePointersAttempted"),
        ("freeThrowAttemptsPer36", "freeThrowsAttempted"),
        ("offensiveReboundsPer36", "reboundsOffensive"),
        ("defensiveReboundsPer36", "reboundsDefensive"),
        ("assistsPer36", "assists"),
        ("turnoversPer36", "turnovers"),
        ("stealsPer36", "steals"),
        ("blocksPer36", "blocks"),
        ("pointsPer36", "points"),
        ("plusMinusPer36", "plusMinusPoints"),
    ):
        _validate_derived(
            row,
            file_name=file_name,
            row_index=row_index,
            field=field,
            numerator=_number(row, numerator_field),
            denominator=minutes,
            formula=f"{numerator_field} / minutes * 36",
            scale=36,
        )

    for field, numerator_field in (
        ("pointsPer100", "points"),
        ("assistsPer100", "assists"),
        ("turnoversPer100", "turnovers"),
        ("stealsPer100", "steals"),
        ("blocksPer100", "blocks"),
    ):
        _validate_derived(
            row,
            file_name=file_name,
            row_index=row_index,
            field=field,
            numerator=_number(row, numerator_field),
            denominator=possessions,
            formula=f"{numerator_field} / possessions * 100",
            scale=100,
        )


def _validate_advanced_row(
    row: Mapping[str, object],
    stats: Mapping[str, object],
    row_index: int,
) -> None:
    file_name = "player_advanced_stats.csv"
    _validate_difference(
        row,
        file_name=file_name,
        row_index=row_index,
        field="estimatedNetRating",
        minuend_field="estimatedOffensiveRating",
        subtrahend_field="estimatedDefensiveRating",
    )
    _validate_difference(
        row,
        file_name=file_name,
        row_index=row_index,
        field="netRating",
        minuend_field="offensiveRating",
        subtrahend_field="defensiveRating",
    )

    field_goals_attempted = _number(stats, "fieldGoalsAttempted")
    effective_numerator = _number(stats, "fieldGoalsMade") + 0.5 * _number(
        stats, "threePointersMade"
    )
    _validate_derived(
        row,
        file_name=file_name,
        row_index=row_index,
        field="effectiveFieldGoalPercentage",
        numerator=effective_numerator,
        denominator=field_goals_attempted,
        formula="(fieldGoalsMade + 0.5 * threePointersMade) / fieldGoalsAttempted",
    )

    true_shooting_denominator = 2 * (
        field_goals_attempted + 0.44 * _number(stats, "freeThrowsAttempted")
    )
    _validate_derived(
        row,
        file_name=file_name,
        row_index=row_index,
        field="trueShootingPercentage",
        numerator=_number(stats, "points"),
        denominator=true_shooting_denominator,
        formula="points / (2 * (fieldGoalsAttempted + 0.44 * freeThrowsAttempted))",
    )
    turnovers = _number(stats, "turnovers")
    _validate_derived(
        row,
        file_name=file_name,
        row_index=row_index,
        field="assistTurnoverRatio",
        numerator=_number(stats, "assists"),
        denominator=None if turnovers is None else max(turnovers, 1),
        formula="assists / max(turnovers, 1)",
    )
    play_ending_denominator = (
        _number(stats, "fieldGoalsAttempted")
        + 0.44 * _number(stats, "freeThrowsAttempted")
        + _number(stats, "assists")
        + _number(stats, "turnovers")
    )
    _validate_derived(
        row,
        file_name=file_name,
        row_index=row_index,
        field="assistRatio",
        numerator=_number(stats, "assists"),
        denominator=play_ending_denominator,
        formula=(
            "assists / (fieldGoalsAttempted + 0.44 * freeThrowsAttempted + assists + "
            "turnovers) * 100"
        ),
        scale=100,
    )
    _validate_derived(
        row,
        file_name=file_name,
        row_index=row_index,
        field="estimatedTurnoverPercentage",
        numerator=_number(stats, "turnovers"),
        denominator=play_ending_denominator,
        formula=(
            "turnovers / (fieldGoalsAttempted + 0.44 * freeThrowsAttempted + assists + "
            "turnovers) * 100"
        ),
        scale=100,
    )
    _validate_derived(
        row,
        file_name=file_name,
        row_index=row_index,
        field="defensiveWinSharesPer36",
        numerator=_number(row, "defensiveWinShares"),
        denominator=_number(stats, "minutes"),
        formula="defensiveWinShares / minutes * 36",
        scale=36,
    )


def _validate_semantics(
    tables: Mapping[str, Sequence[Mapping[str, object]]],
) -> None:
    stats_rows = tables["player_stats.csv"]
    for row_index, row in enumerate(stats_rows, start=1):
        _validate_traditional_row(row, row_index)

    stats_by_key = {(row["playerId"], row["season"]): row for row in stats_rows}
    for row_index, row in enumerate(tables["player_advanced_stats.csv"], start=1):
        key = (row["playerId"], row["season"])
        _validate_advanced_row(row, stats_by_key[key], row_index)


def validate_roster_tables(
    tables: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> None:
    """Validate normalized roster rows, relationships, and statistical semantics."""
    active_contract = contract if contract is not None else load_roster_contract()
    normalized_tables = validate_csv_tables(
        tables,
        contract=active_contract,
        contract_name=_CONTRACT_NAME,
        contract_version=ROSTER_CONTRACT_VERSION,
    )
    _validate_semantics(normalized_tables)


def validate_roster_package(
    package_dir: str | Path,
    *,
    contract: Mapping[str, Any] | None = None,
) -> None:
    """Read and validate the four normalized CSVs in a roster package directory."""
    active_contract = contract if contract is not None else load_roster_contract()
    normalized_tables = validate_csv_package(
        package_dir,
        contract=active_contract,
        contract_name=_CONTRACT_NAME,
        contract_version=ROSTER_CONTRACT_VERSION,
    )
    _validate_semantics(normalized_tables)
