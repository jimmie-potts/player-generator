from __future__ import annotations

import math
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from reference_data_app.adapters import NormalizedSourceRow, normalize_source
from reference_data_app.config import resolve_path
from reference_data_app.registration import (
    RegisteredSource,
    load_registered_sources,
    verify_registered_source,
)

PLAYER_FIELDS = (
    "displayName",
    "firstName",
    "lastName",
    "birthDate",
    "heightInches",
    "weightPounds",
    "country",
    "college",
    "draftYear",
    "draftRound",
    "draftNumber",
)

PLAYER_STATS_CONTEXT_FIELDS = (
    "season",
    "teamId",
    "teamAbbreviation",
    "age",
    "games",
    "starts",
    "wins",
    "losses",
    "minutes",
)

_PLAYER_NAMESPACE = UUID("ac4f1138-fb68-4c9a-a8fc-e9580c3568df")
_PLAYER_SEASON_NAMESPACE = UUID("19d9d5b7-ae02-45c3-9044-e13c289c9f7e")
_PRIMARY_SOURCE_TYPE = "nba_playerstats"

IdentityKey = tuple[str, str]


class CanonicalNormalizationError(ValueError):
    """Raised when reconciliation or configured canonicalization cannot be completed."""


class CanonicalValidationError(ValueError):
    """Raised when canonical keys, values, or relationships are invalid."""


@dataclass(frozen=True)
class CanonicalBundle:
    players: list[dict[str, Any]]
    player_stats: list[dict[str, Any]]
    player_source_ids: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    audit: dict[str, list[dict[str, Any]]]


class _DisjointSet:
    def __init__(self, keys: Iterable[IdentityKey]) -> None:
        self._parent = {key: key for key in keys}

    def find(self, key: IdentityKey) -> IdentityKey:
        parent = self._parent[key]
        if parent != key:
            self._parent[key] = self.find(parent)
        return self._parent[key]

    def union(self, left: IdentityKey, right: IdentityKey) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        keep, replace = sorted((left_root, right_root), key=_identity_priority)
        self._parent[replace] = keep


def _identity_priority(key: IdentityKey) -> tuple[int, str, str]:
    return (0 if key[0] == _PRIMARY_SOURCE_TYPE else 1, key[0], key[1])


def _identity_payload(key: IdentityKey) -> dict[str, str]:
    return {"sourceType": key[0], "sourcePlayerId": key[1]}


def _normalized_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _player_id(keys: Sequence[IdentityKey]) -> str:
    anchor = min(keys, key=_identity_priority)
    return f"player_{uuid5(_PLAYER_NAMESPACE, f'{anchor[0]}:{anchor[1]}').hex}"


def _player_season_id(player_id: str, season: int) -> str:
    return f"playerSeason_{uuid5(_PLAYER_SEASON_NAMESPACE, f'{player_id}:{season}').hex}"


def _manual_override_keys(
    configuration: Mapping[str, Any], identities: set[IdentityKey]
) -> list[tuple[IdentityKey, IdentityKey]]:
    raw_overrides = configuration.get("reviewedManualOverrides", [])
    if not isinstance(raw_overrides, list):
        raise CanonicalNormalizationError("reviewedManualOverrides must be a list")
    result: list[tuple[IdentityKey, IdentityKey]] = []
    for index, raw in enumerate(raw_overrides):
        if not isinstance(raw, Mapping) or raw.get("reviewed") is not True:
            raise CanonicalNormalizationError(
                f"Manual override {index} must be an object with reviewed: true"
            )
        required = (
            "sourceType",
            "sourcePlayerId",
            "targetSourceType",
            "targetSourcePlayerId",
        )
        missing = [field for field in required if not str(raw.get(field, "")).strip()]
        if missing:
            raise CanonicalNormalizationError(
                f"Manual override {index} is missing: {', '.join(missing)}"
            )
        source = (str(raw["sourceType"]), str(raw["sourcePlayerId"]))
        target = (str(raw["targetSourceType"]), str(raw["targetSourcePlayerId"]))
        for label, key in (("source", source), ("target", target)):
            if key not in identities:
                raise CanonicalNormalizationError(
                    f"Manual override {index} {label} identity does not exist: "
                    f"{key[0]}:{key[1]}"
                )
        if source == target:
            raise CanonicalNormalizationError(f"Manual override {index} maps an identity to itself")
        result.append((source, target))
    sources = [source for source, _target in result]
    if len(sources) != len(set(sources)):
        raise CanonicalNormalizationError("A source identity has more than one manual override")
    return result


def _reconcile(
    rows_by_identity: Mapping[IdentityKey, list[NormalizedSourceRow]],
    configuration: Mapping[str, Any],
) -> tuple[dict[IdentityKey, list[IdentityKey]], list[dict[str, Any]]]:
    identities = set(rows_by_identity)
    groups = _DisjointSet(identities)
    overrides = _manual_override_keys(configuration, identities)
    override_targets = {source: target for source, target in overrides}
    for source, target in overrides:
        groups.union(source, target)

    nba_by_name: dict[str, set[IdentityKey]] = defaultdict(set)
    for key, rows in rows_by_identity.items():
        if key[0] == _PRIMARY_SOURCE_TYPE:
            nba_by_name[_normalized_name(rows[-1].display_name)].add(key)

    audit: list[dict[str, Any]] = []
    for key in sorted(identities, key=_identity_priority):
        rows = rows_by_identity[key]
        if key in override_targets:
            target = override_targets[key]
            audit.append(
                {
                    **_identity_payload(key),
                    "status": "matched",
                    "rule": "reviewedManualOverride",
                    "target": _identity_payload(target),
                    "candidates": [_identity_payload(target)],
                }
            )
            continue
        if key[0] == _PRIMARY_SOURCE_TYPE:
            audit.append(
                {
                    **_identity_payload(key),
                    "status": "anchor",
                    "rule": "exactSourceId" if len(rows) > 1 else "primarySource",
                    "candidates": [],
                }
            )
            continue

        display_name = rows[-1].display_name
        candidates = sorted(nba_by_name.get(_normalized_name(display_name), set()))
        if len(candidates) == 1:
            groups.union(key, candidates[0])
            status = "matched"
            rule = "uniqueExactDisplayName"
            target_payload: dict[str, Any] | None = _identity_payload(candidates[0])
        elif candidates:
            status = "ambiguous"
            rule = "ambiguousExactDisplayName"
            target_payload = None
        else:
            status = "unmatched"
            rule = "noExactDisplayName"
            target_payload = None
        record: dict[str, Any] = {
            **_identity_payload(key),
            "displayName": display_name,
            "status": status,
            "rule": rule,
            "candidates": [_identity_payload(candidate) for candidate in candidates],
        }
        if target_payload is not None:
            record["target"] = target_payload
        audit.append(record)

    reconciled: dict[IdentityKey, list[IdentityKey]] = defaultdict(list)
    for key in identities:
        reconciled[groups.find(key)].append(key)
    ordered = {
        root: sorted(keys, key=_identity_priority)
        for root, keys in sorted(reconciled.items(), key=lambda item: _identity_priority(item[0]))
    }
    return ordered, audit


def _field_precedence(configuration: Mapping[str, Any]) -> dict[str, list[str]]:
    raw = configuration.get("fieldPrecedence")
    if not isinstance(raw, Mapping):
        raise CanonicalNormalizationError("normalization.fieldPrecedence must be an object")
    missing = [field for field in PLAYER_FIELDS if field not in raw]
    if missing:
        raise CanonicalNormalizationError(
            f"Missing canonical field precedence rules: {', '.join(missing)}"
        )
    result: dict[str, list[str]] = {}
    for field in PLAYER_FIELDS:
        order = raw[field]
        if not isinstance(order, list) or not order or any(not isinstance(x, str) for x in order):
            raise CanonicalNormalizationError(
                f"Field precedence for {field} must be a non-empty source-type list"
            )
        if len(order) != len(set(order)):
            raise CanonicalNormalizationError(f"Field precedence for {field} has duplicates")
        result[field] = order
    return result


def _candidate_value(row: NormalizedSourceRow, field: str) -> Any:
    if field == "displayName":
        return row.display_name
    return row.player_fields.get(field)


def _candidate_sort_key(
    candidate: dict[str, Any], source_order: list[str]
) -> tuple[int, int, str, str]:
    try:
        source_rank = source_order.index(candidate["sourceType"])
    except ValueError as error:
        raise CanonicalNormalizationError(
            f"Field precedence does not include source type {candidate['sourceType']}"
        ) from error
    season = candidate["season"] if isinstance(candidate["season"], int) else -1
    return source_rank, -season, candidate["sourceId"], candidate["sourcePlayerId"]


def _merge_player(
    player_id: str,
    identity_keys: Sequence[IdentityKey],
    rows_by_identity: Mapping[IdentityKey, list[NormalizedSourceRow]],
    precedence: Mapping[str, list[str]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    player: dict[str, Any] = {"playerId": player_id}
    conflicts: list[dict[str, Any]] = []
    all_rows = [row for key in identity_keys for row in rows_by_identity[key]]
    for field in PLAYER_FIELDS:
        candidates = [
            {
                "sourceId": row.source_id,
                "sourceType": row.source_type,
                "sourcePlayerId": row.source_player_id,
                "season": row.season,
                "value": _candidate_value(row, field),
            }
            for row in all_rows
            if _candidate_value(row, field) is not None
        ]
        candidates.sort(key=lambda item: _candidate_sort_key(item, precedence[field]))
        player[field] = candidates[0]["value"] if candidates else None
        distinct_values: list[Any] = []
        for candidate in candidates:
            if candidate["value"] not in distinct_values:
                distinct_values.append(candidate["value"])
        if len(distinct_values) > 1:
            conflicts.append(
                {
                    "playerId": player_id,
                    "field": field,
                    "candidates": candidates,
                    "chosenValue": player[field],
                    "rule": (
                        f"fieldPrecedence[{','.join(precedence[field])}];"
                        "latestSeasonThenSourceId"
                    ),
                }
            )
    if player["displayName"] is None:
        raise CanonicalNormalizationError(f"Player {player_id} has no displayName")
    return player, conflicts


def canonicalize_rows(
    rows: Sequence[NormalizedSourceRow],
    sources: Sequence[RegisteredSource],
    configuration: Mapping[str, Any],
) -> CanonicalBundle:
    if not rows:
        raise CanonicalNormalizationError("No normalized source rows were supplied")
    ordered_rows = sorted(
        rows,
        key=lambda item: (
            item.source_type,
            item.source_player_id,
            item.season if item.season is not None else -1,
            item.source_id,
        ),
    )
    rows_by_identity: dict[IdentityKey, list[NormalizedSourceRow]] = defaultdict(list)
    for row in ordered_rows:
        rows_by_identity[(row.source_type, row.source_player_id)].append(row)

    groups, reconciliation_audit = _reconcile(rows_by_identity, configuration)
    precedence = _field_precedence(configuration)
    identity_to_player: dict[IdentityKey, str] = {}
    players: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for identity_keys in groups.values():
        player_id = _player_id(identity_keys)
        for key in identity_keys:
            identity_to_player[key] = player_id
        player, player_conflicts = _merge_player(
            player_id, identity_keys, rows_by_identity, precedence
        )
        players.append(player)
        conflicts.extend(player_conflicts)

    player_source_ids = [
        {
            "playerId": player_id,
            "sourceType": source_type,
            "sourcePlayerId": source_player_id,
        }
        for (source_type, source_player_id), player_id in identity_to_player.items()
    ]

    player_stats: list[dict[str, Any]] = []
    source_contexts: list[dict[str, Any]] = []
    seen_seasons: set[tuple[str, int]] = set()
    for row in ordered_rows:
        if row.season_fields is None:
            continue
        player_id = identity_to_player[(row.source_type, row.source_player_id)]
        season = row.season
        if season is None:
            raise CanonicalNormalizationError(
                f"Source identity {row.source_type}:{row.source_player_id} has an invalid season"
            )
        canonical_key = (player_id, season)
        if canonical_key in seen_seasons:
            raise CanonicalValidationError(
                f"Duplicate canonical player-season key: {player_id}, {season}"
            )
        seen_seasons.add(canonical_key)
        if row.traditional_stats is None or row.advanced_stats is None:
            raise CanonicalNormalizationError(
                f"Source identity {row.source_type}:{row.source_player_id} season {season} "
                "does not supply both statistical projections"
            )
        player_season_id = _player_season_id(player_id, season)
        identity = {
            "playerSeasonId": player_season_id,
            "playerId": player_id,
            "season": season,
        }
        player_stats.append(
            {
                **identity,
                **{
                    field: row.season_fields.get(field)
                    for field in PLAYER_STATS_CONTEXT_FIELDS[1:]
                },
                **row.traditional_stats,
                **row.advanced_stats,
            }
        )
        source_contexts.append(
            {
                **identity,
                "sourceId": row.source_id,
                "sourceType": row.source_type,
                "sourcePlayerId": row.source_player_id,
                **row.source_context,
            }
        )

    bundle = CanonicalBundle(
        players=sorted(players, key=lambda item: item["playerId"]),
        player_stats=sorted(player_stats, key=lambda item: item["playerSeasonId"]),
        player_source_ids=sorted(
            player_source_ids,
            key=lambda item: (item["playerId"], item["sourceType"], item["sourcePlayerId"]),
        ),
        sources=[source.to_dict() for source in sorted(sources, key=lambda item: item.source_id)],
        audit={
            "reconciliation": reconciliation_audit,
            "conflicts": sorted(
                conflicts, key=lambda item: (item["playerId"], item["field"])
            ),
            "sourceContexts": sorted(
                source_contexts,
                key=lambda item: (
                    item["playerSeasonId"],
                    item["sourceType"],
                    item["sourceId"],
                ),
            ),
        },
    )
    validate_canonical_bundle(bundle)
    return bundle


def normalize_registered_sources(config: Mapping[str, Any]) -> CanonicalBundle:
    registry_path = resolve_path(dict(config), "source_registry")
    sources = load_registered_sources(registry_path)
    if not sources:
        raise CanonicalNormalizationError(f"No local sources are registered in {registry_path}")
    rows: list[NormalizedSourceRow] = []
    for source in sources:
        source_path = Path(source.input_path)
        verify_registered_source(source)
        source_rows = normalize_source(
            source_path,
            source.source_id,
            source.source_type,
            source.adapter_version,
        )
        verify_registered_source(source)
        rows.extend(source_rows)
    normalization = config.get("normalization")
    if not isinstance(normalization, Mapping):
        raise CanonicalNormalizationError("Configuration is missing normalization settings")
    return canonicalize_rows(rows, sources, normalization)


def _validate_number(value: object, context: str, *, integral: bool = False) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        expected = "integer" if integral else "number"
        raise CanonicalValidationError(f"{context} must be a {expected} or null")
    if not math.isfinite(float(value)):
        raise CanonicalValidationError(f"{context} must be finite")
    if integral and not float(value).is_integer():
        raise CanonicalValidationError(f"{context} must be an integer or null")


def _validate_unique(
    rows: Sequence[Mapping[str, Any]], fields: tuple[str, ...], table: str
) -> set[tuple[Any, ...]]:
    keys: list[tuple[Any, ...]] = []
    for index, row in enumerate(rows):
        try:
            key = tuple(row[field] for field in fields)
        except KeyError as error:
            raise CanonicalValidationError(
                f"{table} row {index} is missing required field {error.args[0]}"
            ) from error
        if any(value is None or value == "" for value in key):
            raise CanonicalValidationError(
                f"{table} row {index} has an empty key field in {fields}"
            )
        keys.append(key)
    if len(keys) != len(set(keys)):
        raise CanonicalValidationError(f"{table} contains duplicate key {fields}")
    return set(keys)


def _validate_player_rows(players: Sequence[Mapping[str, Any]]) -> set[str]:
    player_keys = _validate_unique(players, ("playerId",), "players")
    for index, row in enumerate(players):
        if not isinstance(row["playerId"], str) or not row["playerId"].startswith("player_"):
            raise CanonicalValidationError(f"players row {index} has an invalid playerId")
        if not isinstance(row.get("displayName"), str) or not row["displayName"].strip():
            raise CanonicalValidationError(f"players row {index} has an invalid displayName")
        for field in ("firstName", "lastName", "country", "college"):
            value = row.get(field)
            if value is not None and not isinstance(value, str):
                raise CanonicalValidationError(f"players row {index} field {field} must be text")
        birth_date = row.get("birthDate")
        if birth_date is not None:
            if not isinstance(birth_date, str):
                raise CanonicalValidationError(f"players row {index} birthDate must be ISO text")
            try:
                date.fromisoformat(birth_date)
            except ValueError as error:
                raise CanonicalValidationError(
                    f"players row {index} birthDate must be an ISO 8601 date"
                ) from error
        for field in ("heightInches", "weightPounds"):
            _validate_number(row.get(field), f"players row {index} field {field}")
        for field in ("draftYear", "draftRound", "draftNumber"):
            _validate_number(
                row.get(field), f"players row {index} field {field}", integral=True
            )
    return {key[0] for key in player_keys}


def validate_canonical_bundle(bundle: CanonicalBundle) -> None:
    player_ids = _validate_player_rows(bundle.players)
    stats_ids = _validate_unique(
        bundle.player_stats, ("playerSeasonId",), "player_stats"
    )
    stats_grain = _validate_unique(
        bundle.player_stats, ("playerId", "season"), "player_stats"
    )
    for index, row in enumerate(bundle.player_stats):
        if row["playerId"] not in player_ids:
            raise CanonicalValidationError(
                f"player_stats row {index} references unknown playerId {row['playerId']}"
            )
        if not isinstance(row["playerSeasonId"], str) or not row["playerSeasonId"].startswith(
            "playerSeason_"
        ):
            raise CanonicalValidationError(
                f"player_stats row {index} has an invalid playerSeasonId"
            )
        _validate_number(row["season"], f"player_stats row {index} season", integral=True)
        for field in ("games", "starts", "wins", "losses"):
            _validate_number(
                row.get(field), f"player_stats row {index} field {field}", integral=True
            )
        for field in ("age", "minutes"):
            _validate_number(row.get(field), f"player_stats row {index} field {field}")
        for field in ("teamId", "teamAbbreviation"):
            value = row.get(field)
            if value is not None and not isinstance(value, str):
                raise CanonicalValidationError(
                    f"player_stats row {index} field {field} must be text or null"
                )
        for field, value in row.items():
            if field not in {
                "playerSeasonId",
                "playerId",
                "season",
                "teamId",
                "teamAbbreviation",
                "games",
                "starts",
                "wins",
                "losses",
                "age",
                "minutes",
            }:
                _validate_number(value, f"player_stats row {index} field {field}")

    source_identity_keys = _validate_unique(
        bundle.player_source_ids,
        ("sourceType", "sourcePlayerId"),
        "player_source_ids",
    )
    player_source_keys = _validate_unique(
        bundle.player_source_ids, ("playerId", "sourceType"), "player_source_ids"
    )
    del source_identity_keys, player_source_keys, stats_ids, stats_grain
    source_types = {source.get("sourceType") for source in bundle.sources}
    for index, row in enumerate(bundle.player_source_ids):
        if row["playerId"] not in player_ids:
            raise CanonicalValidationError(
                f"player_source_ids row {index} references unknown playerId {row['playerId']}"
            )
        if row["sourceType"] not in source_types:
            raise CanonicalValidationError(
                f"player_source_ids row {index} references unregistered source type "
                f"{row['sourceType']}"
            )
    _validate_unique(bundle.sources, ("sourceId",), "sources")
