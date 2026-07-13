from __future__ import annotations

from copy import deepcopy

import pytest
from reference_data_app.adapters import NormalizedSourceRow
from reference_data_app.canonical import (
    CanonicalNormalizationError,
    CanonicalValidationError,
    canonicalize_rows,
    validate_canonical_bundle,
)
from reference_data_app.registration import RegisteredSource


def _nba_row(
    source_player_id: str,
    display_name: str,
    *,
    season: int = 2026,
    source_id: str = "nba:fixture",
    player_fields: dict[str, object] | None = None,
    team_id: str | None = "team_single",
    team_abbreviation: str | None = "TST",
    source_team_id: object = 10,
    source_team_abbreviation: str | None = "TST",
    team_count: int | None = 1,
) -> NormalizedSourceRow:
    return NormalizedSourceRow(
        source_id=source_id,
        source_type="nba_playerstats",
        source_player_id=source_player_id,
        display_name=display_name,
        player_fields=player_fields or {},
        season_fields={
            "season": season,
            "teamId": team_id,
            "teamAbbreviation": team_abbreviation,
            "age": 26,
            "games": 72,
            "starts": None,
            "wins": 45,
            "losses": 27,
            "minutes": 2100,
        },
        traditional_stats={"points": 1000, "assists": 300},
        advanced_stats={"usagePercentage": 0.22},
        source_context={
            "sourceTeamId": source_team_id,
            "sourceTeamAbbreviation": source_team_abbreviation,
            "teamCount": team_count,
        },
    )


def _espn_row(
    source_player_id: str,
    display_name: str,
    *,
    source_id: str = "espn:fixture",
    player_fields: dict[str, object] | None = None,
) -> NormalizedSourceRow:
    return NormalizedSourceRow(
        source_id=source_id,
        source_type="espn_player_details",
        source_player_id=source_player_id,
        display_name=display_name,
        player_fields=player_fields or {},
        season_fields=None,
        traditional_stats=None,
        advanced_stats=None,
        source_context={},
    )


def _registered_sources(rows: list[NormalizedSourceRow]) -> list[RegisteredSource]:
    identities = sorted({(row.source_id, row.source_type) for row in rows})
    return [
        RegisteredSource(
            source_id=source_id,
            source_type=source_type,
            input_path=f"/tmp/{source_id.replace(':', '-')}.parquet",
            original_filename=f"{source_id.replace(':', '-')}.parquet",
            sha256="0" * 64,
            adapter_version=1,
            row_count=sum(row.source_id == source_id for row in rows),
            processed_at="2026-07-13T12:00:00Z",
            license_status="test-fixture",
        )
        for source_id, source_type in identities
    ]


def _canonicalize(
    rows: list[NormalizedSourceRow],
    reference_config: dict,
    *,
    overrides: list[dict[str, object]] | None = None,
):
    configuration = deepcopy(reference_config["normalization"])
    if overrides is not None:
        configuration["reviewedManualOverrides"] = overrides
    return canonicalize_rows(rows, _registered_sources(rows), configuration)


def _mapping(bundle, source_type: str, source_player_id: str) -> str:
    return next(
        row["playerId"]
        for row in bundle.player_source_ids
        if row["sourceType"] == source_type
        and row["sourcePlayerId"] == source_player_id
    )


def test_repeated_exact_source_id_across_seasons_has_one_stable_player(
    reference_config: dict,
) -> None:
    rows = [
        _nba_row("101", "Season Player", season=2025),
        _nba_row("101", "Season Player", season=2026),
    ]

    bundle = _canonicalize(rows, reference_config)

    assert len(bundle.players) == 1
    assert len(bundle.player_seasons) == 2
    assert len(bundle.player_source_ids) == 1
    reconciliation = bundle.audit["reconciliation"]
    assert reconciliation == [
        {
            "sourceType": "nba_playerstats",
            "sourcePlayerId": "101",
            "status": "anchor",
            "rule": "exactSourceId",
            "candidates": [],
        }
    ]
    assert all(
        row["playerId"] == bundle.players[0]["playerId"]
        for row in bundle.player_seasons
    )


def test_unique_normalized_display_name_matches_nba_anchor(reference_config: dict) -> None:
    rows = [
        _nba_row("101", "Sample Player"),
        _espn_row("espn-101", " sample-player "),
    ]

    bundle = _canonicalize(rows, reference_config)

    assert len(bundle.players) == 1
    assert _mapping(bundle, "nba_playerstats", "101") == _mapping(
        bundle, "espn_player_details", "espn-101"
    )
    espn_audit = next(
        row
        for row in bundle.audit["reconciliation"]
        if row["sourceType"] == "espn_player_details"
    )
    assert espn_audit["status"] == "matched"
    assert espn_audit["rule"] == "uniqueExactDisplayName"


def test_reviewed_manual_override_precedes_name_matching(reference_config: dict) -> None:
    rows = [
        _nba_row("101", "NBA Name"),
        _espn_row("espn-101", "Different ESPN Name"),
    ]
    overrides = [
        {
            "reviewed": True,
            "sourceType": "espn_player_details",
            "sourcePlayerId": "espn-101",
            "targetSourceType": "nba_playerstats",
            "targetSourcePlayerId": "101",
        }
    ]

    bundle = _canonicalize(rows, reference_config, overrides=overrides)

    assert len(bundle.players) == 1
    assert bundle.players[0]["displayName"] == "NBA Name"
    override_audit = next(
        row
        for row in bundle.audit["reconciliation"]
        if row["sourceType"] == "espn_player_details"
    )
    assert override_audit["rule"] == "reviewedManualOverride"


def test_ambiguous_name_is_reported_and_never_auto_merged(reference_config: dict) -> None:
    rows = [
        _nba_row("101", "Shared Name"),
        _nba_row("202", "Shared Name"),
        _espn_row("espn-shared", "Shared Name"),
    ]

    bundle = _canonicalize(rows, reference_config)

    assert len(bundle.players) == 3
    audit = next(
        row
        for row in bundle.audit["reconciliation"]
        if row["sourcePlayerId"] == "espn-shared"
    )
    assert audit["status"] == "ambiguous"
    assert audit["rule"] == "ambiguousExactDisplayName"
    assert len(audit["candidates"]) == 2


def test_unmatched_identity_is_standalone_and_reported(reference_config: dict) -> None:
    rows = [_nba_row("101", "NBA Name"), _espn_row("espn-404", "No NBA Match")]

    bundle = _canonicalize(rows, reference_config)

    assert len(bundle.players) == 2
    audit = next(
        row
        for row in bundle.audit["reconciliation"]
        if row["sourcePlayerId"] == "espn-404"
    )
    assert audit["status"] == "unmatched"
    assert audit["rule"] == "noExactDisplayName"


def test_field_precedence_uses_latest_season_and_audits_conflicts(
    reference_config: dict,
) -> None:
    rows = [
        _nba_row("101", "Sample Player", season=2025, player_fields={"heightInches": 76}),
        _nba_row("101", "Sample Player", season=2026, player_fields={"heightInches": 78}),
        _espn_row("espn-101", "Sample Player", player_fields={"heightInches": 80}),
    ]

    bundle = _canonicalize(rows, reference_config)

    assert bundle.players[0]["heightInches"] == 78
    conflict = next(
        row for row in bundle.audit["conflicts"] if row["field"] == "heightInches"
    )
    assert [candidate["value"] for candidate in conflict["candidates"]] == [78, 76, 80]
    assert conflict["chosenValue"] == 78
    assert "latestSeasonThenSourceId" in conflict["rule"]


def test_null_field_falls_back_to_next_configured_source(reference_config: dict) -> None:
    rows = [
        _nba_row("101", "Sample Player", player_fields={"country": None}),
        _espn_row("espn-101", "Sample Player", player_fields={"country": "Canada"}),
    ]

    bundle = _canonicalize(rows, reference_config)

    assert bundle.players[0]["country"] == "Canada"
    assert all(row["field"] != "country" for row in bundle.audit["conflicts"])


def test_multi_team_identity_stays_empty_while_source_context_is_audited(
    reference_config: dict,
) -> None:
    row = _nba_row(
        "101",
        "Traded Player",
        team_id=None,
        team_abbreviation=None,
        source_team_id=1610612737,
        source_team_abbreviation="TOT",
        team_count=2,
    )

    bundle = _canonicalize([row], reference_config)

    assert bundle.player_seasons[0]["teamId"] is None
    assert bundle.player_seasons[0]["teamAbbreviation"] is None
    context = bundle.audit["sourceContexts"][0]
    assert context["sourceTeamId"] == 1610612737
    assert context["sourceTeamAbbreviation"] == "TOT"
    assert context["teamCount"] == 2


def test_canonicalization_is_independent_of_input_order(reference_config: dict) -> None:
    rows = [
        _nba_row("101", "First Player", season=2025),
        _nba_row("101", "First Player", season=2026),
        _nba_row("202", "Second Player"),
        _espn_row("espn-101", "First Player"),
    ]
    sources = _registered_sources(rows)
    configuration = deepcopy(reference_config["normalization"])

    forward = canonicalize_rows(rows, sources, configuration)
    reversed_result = canonicalize_rows(
        list(reversed(rows)), list(reversed(sources)), configuration
    )

    assert forward == reversed_result


def test_manual_override_target_must_exist(reference_config: dict) -> None:
    rows = [_nba_row("101", "NBA Name"), _espn_row("espn-101", "ESPN Name")]
    overrides = [
        {
            "reviewed": True,
            "sourceType": "espn_player_details",
            "sourcePlayerId": "espn-101",
            "targetSourceType": "nba_playerstats",
            "targetSourcePlayerId": "missing",
        }
    ]

    with pytest.raises(CanonicalNormalizationError, match="target identity does not exist"):
        _canonicalize(rows, reference_config, overrides=overrides)


def test_one_source_player_id_per_player_and_source_is_enforced(
    reference_config: dict,
) -> None:
    rows = [
        _nba_row("101", "Shared Name"),
        _espn_row("espn-a", "Shared Name"),
        _espn_row("espn-b", "Shared Name"),
    ]

    with pytest.raises(CanonicalValidationError, match="playerId.*sourceType"):
        _canonicalize(rows, reference_config)


def test_duplicate_canonical_player_season_stops_normalization(reference_config: dict) -> None:
    rows = [
        _nba_row("101", "Sample Player", source_id="nba:first"),
        _nba_row("101", "Sample Player", source_id="nba:second"),
    ]

    with pytest.raises(CanonicalValidationError, match="Duplicate canonical player-season"):
        _canonicalize(rows, reference_config)


def test_validation_rejects_invalid_birth_date(reference_config: dict) -> None:
    bundle = _canonicalize([_nba_row("101", "Sample Player")], reference_config)
    bundle.players[0]["birthDate"] = "not-a-date"

    with pytest.raises(CanonicalValidationError, match="ISO 8601 date"):
        validate_canonical_bundle(bundle)


def test_validation_rejects_non_finite_metrics(reference_config: dict) -> None:
    bundle = _canonicalize([_nba_row("101", "Sample Player")], reference_config)
    bundle.player_stats[0]["points"] = float("inf")

    with pytest.raises(CanonicalValidationError, match="must be finite"):
        validate_canonical_bundle(bundle)


def test_validation_rejects_orphan_player_relationship(reference_config: dict) -> None:
    bundle = _canonicalize([_nba_row("101", "Sample Player")], reference_config)
    bundle.player_seasons[0]["playerId"] = "player_missing"

    with pytest.raises(CanonicalValidationError, match="unknown playerId"):
        validate_canonical_bundle(bundle)


def test_validation_rejects_mismatched_season_table_key_sets(reference_config: dict) -> None:
    bundle = _canonicalize([_nba_row("101", "Sample Player")], reference_config)
    bundle.player_advanced_stats.clear()

    with pytest.raises(CanonicalValidationError, match="keys do not match"):
        validate_canonical_bundle(bundle)


def test_validation_rejects_duplicate_player_keys(reference_config: dict) -> None:
    bundle = _canonicalize([_nba_row("101", "Sample Player")], reference_config)
    bundle.players.append(deepcopy(bundle.players[0]))

    with pytest.raises(CanonicalValidationError, match="players contains duplicate key"):
        validate_canonical_bundle(bundle)
