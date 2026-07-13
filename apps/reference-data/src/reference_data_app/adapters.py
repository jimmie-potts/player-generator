from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from reference_data_app.ingest import PLAYER_STATS_REQUIRED_COLUMNS

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


class AdapterValidationError(ValueError):
    """Raised when a local source is incompatible with its declared adapter."""


@dataclass(frozen=True)
class SourceInspection:
    row_count: int
    columns: tuple[str, ...]


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
