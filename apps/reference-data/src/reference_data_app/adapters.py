from __future__ import annotations

import hashlib
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from numbers import Integral, Real
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from reference_data_app.playerstats_source import PLAYER_STATS_REQUIRED_COLUMNS

NBA_PLAYERSTATS_V1_REQUIRED_COLUMNS = (
    *PLAYER_STATS_REQUIRED_COLUMNS,
    "team_id",
    "w",
    "l",
    "team_count",
)

# Version 1 deliberately requires only the stable identity fields exposed by ESPN player-detail
# records. Bio fields differ across upstream snapshots and remain optional until an observed source
# contract can be documented without inventing values.
ESPN_PLAYER_DETAILS_V1_REQUIRED_COLUMNS = (
    "id",
    "displayName",
)

NBA_PLAYER_FIELD_MAP = {
    "player_height_inches": "heightInches",
    "player_weight": "weightPounds",
    "country": "country",
    "college": "college",
    "draft_year": "draftYear",
    "draft_round": "draftRound",
    "draft_number": "draftNumber",
}

NBA_TRADITIONAL_STAT_MAP = {
    "fgm": "fieldGoalsMade",
    "fga": "fieldGoalsAttempted",
    "fg3m": "threePointersMade",
    "fg3a": "threePointersAttempted",
    "ftm": "freeThrowsMade",
    "fta": "freeThrowsAttempted",
    "oreb": "reboundsOffensive",
    "dreb": "reboundsDefensive",
    "reb": "reboundsTotal",
    "ast": "assists",
    "tov": "turnovers",
    "stl": "steals",
    "blk": "blocks",
    "pf": "foulsPersonal",
    "pts": "points",
    "plus_minus": "plusMinusPoints",
    "fg2m": "twoPointersMade",
    "fg2a": "twoPointersAttempted",
    "fg2_pct": "twoPointPercentage",
    "min_pergame": "minutesPerGame",
    "fg3a_per36": "threePointAttemptsPer36",
    "fta_per36": "freeThrowAttemptsPer36",
    "oreb_per36": "offensiveReboundsPer36",
    "dreb_per36": "defensiveReboundsPer36",
    "ast_per36": "assistsPer36",
    "tov_per36": "turnoversPer36",
    "stl_per36": "stealsPer36",
    "blk_per36": "blocksPer36",
    "pts_per36": "pointsPer36",
    "plus_minus_per36": "plusMinusPer36",
    "pts_per100possessions": "pointsPer100",
    "ast_per100possessions": "assistsPer100",
    "tov_per100possessions": "turnoversPer100",
    "stl_per100possessions": "stealsPer100",
    "blk_per100possessions": "blocksPer100",
    "fg2a_frequency": "twoPointAttemptFrequency",
    "fg3a_frequency": "threePointAttemptFrequency",
}

NBA_ADVANCED_STAT_MAP = {
    "e_off_rating": "estimatedOffensiveRating",
    "off_rating": "offensiveRating",
    "e_def_rating": "estimatedDefensiveRating",
    "def_rating": "defensiveRating",
    "e_net_rating": "estimatedNetRating",
    "net_rating": "netRating",
    "ast_pct": "assistPercentage",
    "ast_to": "assistTurnoverRatio",
    "ast_ratio": "assistRatio",
    "oreb_pct": "offensiveReboundPercentage",
    "dreb_pct": "defensiveReboundPercentage",
    "reb_pct": "reboundPercentage",
    "e_tov_pct": "estimatedTurnoverPercentage",
    "efg_pct": "effectiveFieldGoalPercentage",
    "ts_pct": "trueShootingPercentage",
    "usg_pct": "usagePercentage",
    "pie": "playerImpactEstimate",
    "def_ws": "defensiveWinShares",
    "def_ws_per36": "defensiveWinSharesPer36",
}

# ESPN v1 maps only fields whose source names state the canonical unit or meaning. Ambiguous
# `height` and `weight` fields are intentionally ignored rather than assuming units.
ESPN_OPTIONAL_PLAYER_FIELD_MAP = {
    "firstName": "firstName",
    "lastName": "lastName",
    "birthDate": "birthDate",
    "dateOfBirth": "birthDate",
    "heightInches": "heightInches",
    "weightPounds": "weightPounds",
    "country": "country",
    "college": "college",
    "draftYear": "draftYear",
    "draftRound": "draftRound",
    "draftNumber": "draftNumber",
}


class AdapterValidationError(ValueError):
    """Raised when a local source is incompatible with its declared adapter."""


@dataclass(frozen=True)
class SourceInspection:
    row_count: int
    columns: tuple[str, ...]


@dataclass(frozen=True)
class NormalizedSourceRow:
    source_id: str
    source_type: str
    source_player_id: str
    display_name: str
    player_fields: dict[str, object]
    season_fields: dict[str, object] | None
    traditional_stats: dict[str, object] | None
    advanced_stats: dict[str, object] | None
    source_context: dict[str, object]

    @property
    def season(self) -> int | None:
        if self.season_fields is None:
            return None
        value = self.season_fields.get("season")
        return value if isinstance(value, int) else None

    @property
    def player(self) -> dict[str, object]:
        return self.player_fields

    @property
    def player_season(self) -> dict[str, object] | None:
        return self.season_fields

    @property
    def player_stats(self) -> dict[str, object] | None:
        return self.traditional_stats

    @property
    def player_advanced_stats(self) -> dict[str, object] | None:
        return self.advanced_stats

    @property
    def sourceId(self) -> str:
        return self.source_id

    @property
    def sourceType(self) -> str:
        return self.source_type

    @property
    def sourcePlayerId(self) -> str:
        return self.source_player_id

    @property
    def displayName(self) -> str:
        return self.display_name

    @property
    def playerFields(self) -> dict[str, object]:
        return self.player_fields

    @property
    def seasonFields(self) -> dict[str, object] | None:
        return self.season_fields

    @property
    def traditionalStats(self) -> dict[str, object] | None:
        return self.traditional_stats

    @property
    def advancedStats(self) -> dict[str, object] | None:
        return self.advanced_stats

    @property
    def sourceContext(self) -> dict[str, object]:
        return self.source_context


@dataclass(frozen=True)
class ParquetAdapter:
    source_type: str
    version: int
    required_columns: tuple[str, ...]

    @property
    def name(self) -> str:
        return f"{self.source_type} v{self.version}"

    def inspect(self, path: Path) -> SourceInspection:
        resolved_path = path.expanduser().resolve()
        context = f"{resolved_path}: adapter {self.name}"
        if not resolved_path.exists():
            raise AdapterValidationError(f"{context}: file does not exist")
        if not resolved_path.is_file():
            raise AdapterValidationError(f"{context}: path is not a file")

        try:
            parquet_file = pq.ParquetFile(resolved_path)
            columns = tuple(parquet_file.schema_arrow.names)
            row_count = parquet_file.metadata.num_rows
        except (OSError, pa.ArrowException) as error:
            raise AdapterValidationError(f"{context}: unreadable Parquet file: {error}") from error

        missing = sorted(set(self.required_columns) - set(columns))
        if missing:
            raise AdapterValidationError(
                f"{context}: missing required fields: {', '.join(missing)}"
            )
        return SourceInspection(row_count=row_count, columns=columns)


_ADAPTERS = {
    ("nba_playerstats", 1): ParquetAdapter(
        source_type="nba_playerstats",
        version=1,
        required_columns=NBA_PLAYERSTATS_V1_REQUIRED_COLUMNS,
    ),
    ("espn_player_details", 1): ParquetAdapter(
        source_type="espn_player_details",
        version=1,
        required_columns=ESPN_PLAYER_DETAILS_V1_REQUIRED_COLUMNS,
    ),
}

SUPPORTED_SOURCE_TYPES = tuple(sorted({source_type for source_type, _version in _ADAPTERS}))


def get_adapter(source_type: str, version: int, path: Path) -> ParquetAdapter:
    try:
        return _ADAPTERS[(source_type, version)]
    except KeyError as error:
        versions = sorted(
            adapter_version
            for adapter_source_type, adapter_version in _ADAPTERS
            if adapter_source_type == source_type
        )
        adapter_name = f"{source_type} v{version}"
        context = f"{path.expanduser().resolve()}: adapter {adapter_name}"
        if versions:
            supported = ", ".join(str(supported_version) for supported_version in versions)
            detail = f"unsupported adapter schema version; supported versions: {supported}"
        else:
            supported_types = ", ".join(SUPPORTED_SOURCE_TYPES)
            detail = f"unsupported source type; supported source types: {supported_types}"
        raise AdapterValidationError(f"{context}: {detail}") from error


def inspect_source(path: Path, source_type: str, adapter_version: int) -> SourceInspection:
    return get_adapter(source_type, adapter_version, path).inspect(path)


def _row_context(path: Path, source_type: str, adapter_version: int, row_number: int) -> str:
    return (
        f"{path.expanduser().resolve()}: adapter {source_type} v{adapter_version}: "
        f"row {row_number}"
    )


def _normalize_scalar(value: object) -> object:
    null_result = pd.isna(value)
    if isinstance(null_result, bool) and null_result:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        if math.isnan(number):
            return None
        if not math.isfinite(number):
            return number
        return int(number) if number.is_integer() else number
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _required_text(value: object, field: str, context: str) -> str:
    normalized = _normalize_scalar(value)
    if not isinstance(normalized, str) or not normalized.strip():
        raise AdapterValidationError(f"{context}: field {field!r} must be a non-empty string")
    return normalized.strip()


def _optional_text(value: object, field: str, context: str) -> str | None:
    normalized = _normalize_scalar(value)
    if normalized is None:
        return None
    if not isinstance(normalized, str):
        raise AdapterValidationError(f"{context}: field {field!r} must be a string or null")
    stripped = normalized.strip()
    return stripped or None


def _optional_date(value: object, field: str, context: str) -> str | None:
    normalized = _normalize_scalar(value)
    if normalized is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(normalized, str):
        raise AdapterValidationError(
            f"{context}: field {field!r} must be an ISO 8601 date or null"
        )
    stripped = normalized.strip()
    if not stripped:
        return None
    try:
        return date.fromisoformat(stripped).isoformat()
    except ValueError as error:
        raise AdapterValidationError(
            f"{context}: field {field!r} must be an ISO 8601 date or null"
        ) from error


def _numeric(
    value: object,
    field: str,
    context: str,
    *,
    integral: bool = False,
    allow_numeric_text: bool = False,
) -> int | float | None:
    normalized = _normalize_scalar(value)
    if normalized is None:
        return None
    if allow_numeric_text and isinstance(normalized, str):
        text = normalized.strip()
        if not text or text.casefold() == "undrafted":
            return None
        try:
            normalized = float(text)
        except ValueError as error:
            raise AdapterValidationError(
                f"{context}: field {field!r} must be numeric or null"
            ) from error
        normalized = int(normalized) if normalized.is_integer() else normalized
    if isinstance(normalized, bool) or not isinstance(normalized, (int, float)):
        raise AdapterValidationError(f"{context}: field {field!r} must be numeric or null")
    if not math.isfinite(float(normalized)):
        raise AdapterValidationError(f"{context}: field {field!r} must be finite or null")
    if integral and not float(normalized).is_integer():
        raise AdapterValidationError(f"{context}: field {field!r} must be an integer or null")
    return int(normalized) if integral or float(normalized).is_integer() else float(normalized)


def _nba_source_player_id(value: object, context: str) -> str:
    player_id = _numeric(value, "player_id", context, integral=True, allow_numeric_text=True)
    if player_id is None:
        raise AdapterValidationError(f"{context}: field 'player_id' is required")
    return str(player_id)


def _espn_source_player_id(value: object, context: str) -> str:
    normalized = _normalize_scalar(value)
    if isinstance(normalized, str) and normalized.strip():
        return normalized.strip()
    if isinstance(normalized, int):
        return str(normalized)
    raise AdapterValidationError(
        f"{context}: field 'id' must be a non-empty string or integral number"
    )


def _required_season(value: object, context: str) -> int:
    season = _numeric(value, "year", context, integral=True, allow_numeric_text=True)
    if season is None:
        raise AdapterValidationError(f"{context}: field 'year' is required")
    return season


def _opaque_team_id(source_team_id: object, context: str) -> str:
    normalized = _normalize_scalar(source_team_id)
    if normalized is None or isinstance(normalized, bool) or not isinstance(normalized, (int, str)):
        raise AdapterValidationError(
            f"{context}: field 'team_id' must be an integral number or non-empty string "
            "for a single-team season"
        )
    text = str(normalized).strip()
    if not text:
        raise AdapterValidationError(
            f"{context}: field 'team_id' must be non-empty for a single-team season"
        )
    digest = hashlib.sha256(f"nba_playerstats:{text}".encode()).hexdigest()[:16]
    return f"team_{digest}"


def _map_numeric_fields(
    row: dict[str, Any],
    mapping: dict[str, str],
    context: str,
) -> dict[str, object]:
    return {
        canonical_field: _numeric(row[source_field], source_field, context)
        for source_field, canonical_field in mapping.items()
    }


def _nba_player_fields(row: dict[str, Any], context: str) -> dict[str, object]:
    result: dict[str, object] = {
        "heightInches": _numeric(row["player_height_inches"], "player_height_inches", context),
        "weightPounds": _numeric(
            row["player_weight"],
            "player_weight",
            context,
            allow_numeric_text=True,
        ),
    }
    for source_field in ("country", "college"):
        canonical_field = NBA_PLAYER_FIELD_MAP[source_field]
        result[canonical_field] = _optional_text(row.get(source_field), source_field, context)
    for source_field in ("draft_year", "draft_round", "draft_number"):
        canonical_field = NBA_PLAYER_FIELD_MAP[source_field]
        result[canonical_field] = _numeric(
            row.get(source_field),
            source_field,
            context,
            integral=True,
            allow_numeric_text=True,
        )
    return result


def _normalize_nba_row(
    row: dict[str, Any],
    *,
    path: Path,
    source_id: str,
    adapter_version: int,
    row_number: int,
) -> NormalizedSourceRow:
    context = _row_context(path, "nba_playerstats", adapter_version, row_number)
    source_player_id = _nba_source_player_id(row["player_id"], context)
    display_name = _required_text(row["player_name"], "player_name", context)
    season = _required_season(row["year"], context)
    team_count = _numeric(row["team_count"], "team_count", context, integral=True)
    source_team_id = _normalize_scalar(row["team_id"])
    source_team_abbreviation = _optional_text(
        row["team_abbreviation"], "team_abbreviation", context
    )
    single_team = team_count == 1
    team_id = _opaque_team_id(source_team_id, context) if single_team else None
    team_abbreviation = source_team_abbreviation if single_team else None

    season_fields: dict[str, object] = {
        "season": season,
        "teamId": team_id,
        "teamAbbreviation": team_abbreviation,
        "age": _numeric(row["age"], "age", context),
        "games": _numeric(row["gp"], "gp", context, integral=True),
        "starts": None,
        "wins": _numeric(row["w"], "w", context, integral=True),
        "losses": _numeric(row["l"], "l", context, integral=True),
        "minutes": _numeric(row["min"], "min", context),
    }
    source_context = {
        "sourceTeamId": source_team_id,
        "sourceTeamAbbreviation": source_team_abbreviation,
        "teamCount": team_count,
    }
    return NormalizedSourceRow(
        source_id=source_id,
        source_type="nba_playerstats",
        source_player_id=source_player_id,
        display_name=display_name,
        player_fields=_nba_player_fields(row, context),
        season_fields=season_fields,
        traditional_stats=_map_numeric_fields(row, NBA_TRADITIONAL_STAT_MAP, context),
        advanced_stats=_map_numeric_fields(row, NBA_ADVANCED_STAT_MAP, context),
        source_context=source_context,
    )


def _espn_optional_player_fields(
    row: dict[str, Any], columns: set[str], context: str
) -> dict[str, object]:
    result: dict[str, object] = {}
    converters: dict[str, Callable[[object, str, str], object]] = {
        "firstName": _optional_text,
        "lastName": _optional_text,
        "birthDate": _optional_date,
        "dateOfBirth": _optional_date,
        "country": _optional_text,
        "college": _optional_text,
    }
    numeric_fields = {"heightInches", "weightPounds"}
    integral_fields = {"draftYear", "draftRound", "draftNumber"}
    for source_field, canonical_field in ESPN_OPTIONAL_PLAYER_FIELD_MAP.items():
        if source_field not in columns:
            continue
        if canonical_field in result and result[canonical_field] is not None:
            continue
        if source_field in converters:
            value = converters[source_field](row[source_field], source_field, context)
        elif source_field in numeric_fields:
            value = _numeric(row[source_field], source_field, context)
        elif source_field in integral_fields:
            value = _numeric(
                row[source_field],
                source_field,
                context,
                integral=True,
                allow_numeric_text=True,
            )
        else:
            raise AssertionError(f"Unhandled ESPN player field: {source_field}")
        result[canonical_field] = value
    return result


def _normalize_espn_row(
    row: dict[str, Any],
    *,
    columns: set[str],
    path: Path,
    source_id: str,
    adapter_version: int,
    row_number: int,
) -> NormalizedSourceRow:
    context = _row_context(path, "espn_player_details", adapter_version, row_number)
    return NormalizedSourceRow(
        source_id=source_id,
        source_type="espn_player_details",
        source_player_id=_espn_source_player_id(row["id"], context),
        display_name=_required_text(row["displayName"], "displayName", context),
        player_fields=_espn_optional_player_fields(row, columns, context),
        season_fields=None,
        traditional_stats=None,
        advanced_stats=None,
        source_context={},
    )


def normalize_source(
    path: Path,
    source_id: str,
    source_type: str,
    adapter_version: int,
) -> list[NormalizedSourceRow]:
    resolved_path = path.expanduser().resolve()
    inspection = inspect_source(resolved_path, source_type, adapter_version)
    try:
        frame = pd.read_parquet(resolved_path, engine="pyarrow")
    except (OSError, pa.ArrowException) as error:
        raise AdapterValidationError(
            f"{resolved_path}: adapter {source_type} v{adapter_version}: "
            f"unable to read source rows: {error}"
        ) from error

    columns = set(inspection.columns)
    normalized: list[NormalizedSourceRow] = []
    seen_keys: set[tuple[str, int | None]] = set()
    for row_number, row in enumerate(frame.to_dict(orient="records"), start=1):
        if source_type == "nba_playerstats":
            normalized_row = _normalize_nba_row(
                row,
                path=resolved_path,
                source_id=source_id,
                adapter_version=adapter_version,
                row_number=row_number,
            )
        elif source_type == "espn_player_details":
            normalized_row = _normalize_espn_row(
                row,
                columns=columns,
                path=resolved_path,
                source_id=source_id,
                adapter_version=adapter_version,
                row_number=row_number,
            )
        else:
            raise AssertionError(f"Unhandled adapter: {source_type} v{adapter_version}")

        key = (normalized_row.source_player_id, normalized_row.season)
        if key in seen_keys:
            context = _row_context(resolved_path, source_type, adapter_version, row_number)
            raise AdapterValidationError(
                f"{context}: duplicate source player-season key {key!r}"
            )
        seen_keys.add(key)
        normalized.append(normalized_row)

    return sorted(
        normalized,
        key=lambda row: (row.source_player_id, row.season if row.season is not None else -1),
    )
