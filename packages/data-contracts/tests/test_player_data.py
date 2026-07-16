from __future__ import annotations

import copy

import pytest
from player_data_contracts import (
    PLAYER_DATA_CONTRACT_FAMILY,
    PLAYER_DATA_CONTRACT_VERSION,
    ContractValidationError,
    load_player_data_contract,
    load_reference_contract,
    load_roster_contract,
    serialize_csv_value,
    validate_player_data_contract_family,
    validate_player_data_profile_parity,
)
from player_data_contracts.csv_contract import contract_files


def _column(contract: dict, file_name: str, field_name: str) -> dict:
    return next(
        column
        for column in contract["sharedFiles"][file_name]["columns"]
        if column["name"] == field_name
    )


def test_loads_version_one_shared_contract_family() -> None:
    contract = load_player_data_contract()

    assert contract["contractFamily"] == PLAYER_DATA_CONTRACT_FAMILY
    assert contract["contractVersion"] == PLAYER_DATA_CONTRACT_VERSION
    assert tuple(contract["sharedFiles"]) == (
        "players.csv",
        "player_stats.csv",
        "player_attributes.csv",
    )
    assert contract["csv"] == {
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
        "numericSerializationDescription": (
            "Finite IEEE-754 values use their shortest round-trip significand expanded to plain "
            "base-10 notation with no exponent; insignificant fractional zeros are removed, "
            "integral values omit the decimal point, and negative zero is 0."
        ),
        "deterministicOrdering": True,
    }


def test_family_rejects_boolean_contract_version_lookalikes() -> None:
    family = load_player_data_contract()
    family["contractVersion"] = True

    with pytest.raises(ContractValidationError, match="must declare version 1"):
        validate_player_data_contract_family(family)


def test_shared_statistics_catalog_owns_the_final_common_payload() -> None:
    contract = load_player_data_contract()
    stats = [
        column["name"]
        for column in contract["sharedFiles"]["player_stats.csv"]["columns"]
    ]

    assert stats[:12] == [
        "playerId",
        "season",
        "games",
        "minutes",
        "fieldGoalsMade",
        "fieldGoalsAttempted",
        "twoPointersMade",
        "twoPointersAttempted",
        "threePointersMade",
        "threePointersAttempted",
        "freeThrowsMade",
        "freeThrowsAttempted",
    ]
    for field in (
        "fieldGoalPercentage",
        "threePointPercentage",
        "freeThrowPercentage",
        "pointsPerGame",
        "reboundsPerGame",
        "assistsPerGame",
        "turnoversPerGame",
    ):
        assert field in stats
    assert "possessions" not in stats
    assert _column(contract, "players.csv", "heightInches")["type"] == "number"
    assert _column(contract, "players.csv", "weightPounds")["maximum"] == 400
    assert "maximum" not in _column(contract, "player_stats.csv", "offensiveRating")
    assert "minimum" not in _column(contract, "player_stats.csv", "netRating")
    assert "minimum" not in _column(contract, "player_stats.csv", "playerImpactEstimate")
    assist_turnover = _column(contract, "player_stats.csv", "assistTurnoverRatio")
    assert assist_turnover["derivation"] == "assists / max(turnovers, 1)"

    roster_extensions = contract["profiles"]["roster"]["extensionColumns"]
    assert [column["name"] for column in roster_extensions["player_stats.csv"]] == [
        "possessions"
    ]
    assert roster_extensions["player_stats.csv"][0]["minimum"] == 0


def test_nonnegative_and_season_bounds_are_materialized() -> None:
    family = load_player_data_contract()
    minutes = _column(family, "player_stats.csv", "minutes")
    reference_stats_extensions = {
        column["name"]: column
        for column in family["profiles"]["reference"]["extensionColumns"][
            "player_stats.csv"
        ]
    }
    reference_player_extensions = {
        column["name"]: column
        for column in family["profiles"]["reference"]["extensionColumns"][
            "players.csv"
        ]
    }
    reference_attribute_season = next(
        column
        for column in family["profiles"]["reference"]["extensionColumns"][
            "player_attributes.csv"
        ]
        if column["name"] == "season"
    )
    row_count = next(
        column
        for column in family["profiles"]["reference"]["profileOnlyFiles"][
            "sources.csv"
        ]["columns"]
        if column["name"] == "rowCount"
    )
    reference_row_count = next(
        column
        for column in load_reference_contract()["files"]["sources.csv"]["columns"]
        if column["name"] == "rowCount"
    )
    reference_contract = load_reference_contract()
    flat_reference_stats = {
        column["name"]: column
        for column in reference_contract["files"]["player_stats.csv"]["columns"]
    }
    flat_reference_players = {
        column["name"]: column
        for column in reference_contract["files"]["players.csv"]["columns"]
    }
    flat_reference_attribute_season = next(
        column
        for column in reference_contract["files"]["player_attributes.csv"]["columns"]
        if column["name"] == "season"
    )

    assert minutes["minimum"] == 0
    assert row_count["minimum"] == 0
    assert reference_row_count["minimum"] == 0
    for field_name in ("draftYear", "draftRound", "draftNumber"):
        assert (
            reference_player_extensions[field_name]["minimum"]
            == flat_reference_players[field_name]["minimum"]
            == 0
        )
    assert (
        reference_stats_extensions["age"]["minimum"]
        == flat_reference_stats["age"]["minimum"]
        == 0
    )
    for field_name in ("starts", "wins", "losses"):
        family_column = reference_stats_extensions[field_name]
        flat_column = flat_reference_stats[field_name]
        assert family_column["minimum"] == flat_column["minimum"] == 0
        with pytest.raises(ContractValidationError, match="must be at least 0"):
            serialize_csv_value(-1, family_column)
        assert serialize_csv_value(0, family_column) == "0"
    assert (
        reference_attribute_season["minimum"],
        reference_attribute_season["maximum"],
    ) == (1000, 9999)
    assert (
        flat_reference_attribute_season["minimum"],
        flat_reference_attribute_season["maximum"],
    ) == (1000, 9999)
    assert {
        gap["profile"]
        for gap in family["declaredAlignmentGaps"]
        if gap.get("file") == "player_stats.csv"
        and "minutes" in gap.get("fields", [])
        and gap.get("properties") == ["minimum"]
    } == {"reference", "roster"}
    for column in (minutes, row_count):
        with pytest.raises(ContractValidationError, match="must be at least 0"):
            serialize_csv_value(-1, column)
        assert serialize_csv_value(0, column) == "0"


def test_roster_v1_keeps_age_and_package_scoped_player_ids() -> None:
    contract = load_player_data_contract()
    roster = contract["profiles"]["roster"]
    roster_player_fields = roster["currentColumnOrder"]["players.csv"]
    age = next(
        column
        for column in roster["extensionColumns"]["players.csv"]
        if column["name"] == "age"
    )

    assert age["type"] == "integer"
    assert (age["minimum"], age["maximum"], age["decision"]) == (18, 45, "D-038")
    assert "birthDate" not in roster_player_fields
    assert roster["fieldConstraints"][0]["value"] == r"^player_[0-9a-f]{16}$"
    assert "manifest.contentHash" in roster["keyRationales"]["players.csv"]


def test_current_profiles_match_exact_declared_alignment_ledger() -> None:
    validate_player_data_profile_parity()


def test_profile_parity_rejects_relationship_kind_drift() -> None:
    reference = load_reference_contract()
    relationship = next(
        item
        for item in reference["relationships"]
        if item["name"] == "playerSourceTypesReferenceSources"
    )
    relationship["kind"] = "foreignKey"

    with pytest.raises(
        ContractValidationError,
        match=r"unexpected issues: relationships:reference",
    ):
        validate_player_data_profile_parity(reference_contract=reference)


def test_profile_parity_rejects_new_shared_definition_drift() -> None:
    roster = load_roster_contract()
    points = next(
        column
        for column in roster["files"]["player_stats.csv"]["columns"]
        if column["name"] == "points"
    )
    points["type"] = "number"

    with pytest.raises(
        ContractValidationError,
        match=r"unexpected issues: definition:roster:player_stats\.csv:points:type",
    ):
        validate_player_data_profile_parity(roster_contract=roster)


def test_profile_parity_pins_values_inside_a_declared_definition_gap() -> None:
    roster = load_roster_contract()
    height = next(
        column
        for column in roster["files"]["players.csv"]["columns"]
        if column["name"] == "heightInches"
    )
    height["type"] = "string"

    with pytest.raises(
        ContractValidationError,
        match=r"unexpected issues: definition:roster:players\.csv:heightInches:type",
    ):
        validate_player_data_profile_parity(roster_contract=roster)


def test_profile_parity_rejects_a_stale_gap_after_the_schema_is_fixed() -> None:
    roster = load_roster_contract()
    height = next(
        column
        for column in roster["files"]["players.csv"]["columns"]
        if column["name"] == "heightInches"
    )
    height["type"] = "number"

    with pytest.raises(
        ContractValidationError,
        match=r"declared gaps no longer observed: "
        r"definition:roster:players\.csv:heightInches:type",
    ):
        validate_player_data_profile_parity(roster_contract=roster)


def test_profile_parity_rejects_shared_order_drift() -> None:
    roster = load_roster_contract()
    columns = roster["files"]["player_stats.csv"]["columns"]
    left = next(index for index, column in enumerate(columns) if column["name"] == "points")
    right = next(
        index for index, column in enumerate(columns) if column["name"] == "plusMinusPoints"
    )
    columns[left], columns[right] = columns[right], columns[left]

    with pytest.raises(ContractValidationError, match=r"column-order:roster:player_stats\.csv"):
        validate_player_data_profile_parity(roster_contract=roster)


def test_profile_parity_pins_order_inside_a_declared_order_gap() -> None:
    family = load_player_data_contract()
    reference = load_reference_contract()
    family_order = family["profiles"]["reference"]["currentColumnOrder"][
        "player_stats.csv"
    ]
    columns = reference["files"]["player_stats.csv"]["columns"]
    left = family_order.index("games")
    right = family_order.index("minutes")
    family_order[left], family_order[right] = family_order[right], family_order[left]
    columns[left], columns[right] = columns[right], columns[left]

    with pytest.raises(
        ContractValidationError,
        match=r"unexpected issues: shared-order:reference:player_stats\.csv",
    ):
        validate_player_data_profile_parity(
            family=family,
            reference_contract=reference,
        )


def test_profile_parity_rejects_stale_or_missing_gap_declarations() -> None:
    family = load_player_data_contract()
    missing = next(
        gap
        for gap in family["declaredAlignmentGaps"]
        if gap["kind"] == "missingSharedColumns"
    )
    missing["fields"].remove("fieldGoalPercentage")

    with pytest.raises(
        ContractValidationError,
        match=r"unexpected issues: missing:reference:player_stats\.csv:fieldGoalPercentage",
    ):
        validate_player_data_profile_parity(family=family)


def test_family_rejects_semantic_metadata_omissions() -> None:
    family = load_player_data_contract()
    _column(family, "player_stats.csv", "season")["meaning"] = ""

    with pytest.raises(ContractValidationError, match="season meaning must be non-empty text"):
        validate_player_data_contract_family(family)


def test_family_rejects_enum_members_with_the_wrong_scalar_type() -> None:
    family = load_player_data_contract()
    _column(family, "player_stats.csv", "season")["enum"] = ["2025"]

    with pytest.raises(
        ContractValidationError,
        match=r"enum value '2025' does not match field type integer",
    ):
        validate_player_data_contract_family(family)


def test_family_rejects_enum_members_outside_active_bounds() -> None:
    family = load_player_data_contract()
    _column(family, "player_stats.csv", "season")["enum"] = [999]

    with pytest.raises(ContractValidationError, match=r"enum value 999 must be at least 1000"):
        validate_player_data_contract_family(family)


def test_family_rejects_enum_members_outside_active_patterns() -> None:
    family = load_player_data_contract()
    display_name = _column(family, "players.csv", "displayName")
    display_name["enum"] = ["lowercase"]
    display_name["pattern"] = r"^[A-Z].*"

    with pytest.raises(ContractValidationError, match=r"enum value 'lowercase' must match pattern"):
        validate_player_data_contract_family(family)


def test_family_requires_runtime_canonical_datetime_enum_members() -> None:
    family = load_player_data_contract()
    processed_at = next(
        column
        for column in family["profiles"]["reference"]["profileOnlyFiles"]["sources.csv"][
            "columns"
        ]
        if column["name"] == "processedAt"
    )
    processed_at["enum"] = ["2026-07-15T00:00:00Z"]

    with pytest.raises(
        ContractValidationError,
        match=r"must use canonical datetime form '2026-07-15T00:00:00\+00:00'",
    ):
        validate_player_data_contract_family(family)

    processed_at["enum"] = ["2026-07-15T00:00:00+00:00"]
    validate_player_data_contract_family(family)
    assert (
        serialize_csv_value("2026-07-15T00:00:00Z", processed_at)
        == "2026-07-15T00:00:00+00:00"
    )


def test_family_rejects_number_enums_that_do_not_round_trip() -> None:
    family = load_player_data_contract()
    minutes = _column(family, "player_stats.csv", "minutes")
    minutes["enum"] = [9_007_199_254_740_993]

    with pytest.raises(
        ContractValidationError,
        match="does not round-trip through IEEE-754 normalization",
    ):
        validate_player_data_contract_family(family)

    minutes["enum"] = [10**400]
    with pytest.raises(
        ContractValidationError,
        match="does not match field type number",
    ):
        validate_player_data_contract_family(family)

    minutes["enum"] = [10**5000]
    with pytest.raises(
        ContractValidationError,
        match="does not match field type number",
    ):
        validate_player_data_contract_family(family)

    minutes["enum"] = [9_007_199_254_740_992]
    validate_player_data_contract_family(family)


@pytest.mark.parametrize("enum_values", [[1, 1.0], [-0.0, 0.0]])
def test_family_rejects_number_enums_with_duplicate_canonical_tokens(
    enum_values: list[float],
) -> None:
    family = load_player_data_contract()
    _column(family, "player_stats.csv", "minutes")["enum"] = enum_values

    with pytest.raises(
        ContractValidationError,
        match="must remain unique after canonical CSV serialization",
    ):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize("declaration", ["shared", "extension", "profileOnly"])
def test_family_requires_camel_case_column_names(declaration: str) -> None:
    family = load_player_data_contract()
    if declaration == "shared":
        _column(family, "players.csv", "playerId")["name"] = "player_id"
    elif declaration == "extension":
        family["profiles"]["roster"]["extensionColumns"]["players.csv"][0][
            "name"
        ] = "player_age"
    else:
        family["profiles"]["reference"]["profileOnlyFiles"]["sources.csv"][
            "columns"
        ][0]["name"] = "source_id"

    with pytest.raises(ContractValidationError, match="must be a lower camelCase header"):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize("required, nullable", [(True, True), (False, False)])
def test_family_rejects_contradictory_column_null_rules(
    required: bool, nullable: bool
) -> None:
    family = load_player_data_contract()
    display_name = _column(family, "players.csv", "displayName")
    display_name.update({"required": required, "nullable": nullable})

    with pytest.raises(
        ContractValidationError,
        match="must be required and non-nullable or optional and nullable",
    ):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize("required, nullable", [(True, True), (False, False)])
def test_family_rejects_contradictory_availability_overrides(
    required: bool, nullable: bool
) -> None:
    family = load_player_data_contract()
    override = family["profiles"]["roster"]["availabilityOverrides"][0]
    override.update({"required": required, "nullable": nullable})

    with pytest.raises(
        ContractValidationError,
        match="must be required and non-nullable or optional and nullable",
    ):
        validate_player_data_contract_family(family)


def test_family_rejects_unknown_authored_properties() -> None:
    family = load_player_data_contract()
    _column(family, "players.csv", "heightInches")["maximun"] = 80

    with pytest.raises(ContractValidationError, match="unknown properties: maximun"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    family["profiles"]["roster"]["mysteryPolicy"] = "anything"

    with pytest.raises(ContractValidationError, match="unknown properties: mysteryPolicy"):
        validate_player_data_contract_family(family)


def test_family_requires_complete_valid_row_order_rules() -> None:
    family = load_player_data_contract()
    del family["profiles"]["roster"]["rowOrder"]["player_stats.csv"]

    with pytest.raises(ContractValidationError, match="rowOrder must define every CSV file"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    family["profiles"]["roster"]["rowOrder"]["players.csv"] = ["ghostField"]

    with pytest.raises(ContractValidationError, match="references unknown fields: ghostField"):
        validate_player_data_contract_family(family)


def test_family_requires_row_order_to_include_a_unique_key() -> None:
    family = load_player_data_contract()
    family["profiles"]["roster"]["rowOrder"]["player_stats.csv"] = ["season"]

    with pytest.raises(ContractValidationError, match="must include a declared unique key"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    family["profiles"]["reference"]["rowOrder"]["player_source_ids.csv"] = [
        "sourcePlayerId"
    ]

    with pytest.raises(ContractValidationError, match="must include a declared unique key"):
        validate_player_data_contract_family(family)


def test_family_rejects_non_availability_overrides() -> None:
    family = load_player_data_contract()
    override = family["profiles"]["roster"]["availabilityOverrides"][0]
    override["type"] = "string"

    with pytest.raises(ContractValidationError, match="may change only required and nullable"):
        validate_player_data_contract_family(family)


def test_family_rejects_null_rules_disguised_as_alignment_gaps() -> None:
    family = load_player_data_contract()
    family["declaredAlignmentGaps"].append(
        {
            "kind": "sharedDefinition",
            "profile": "reference",
            "file": "players.csv",
            "fields": ["displayName"],
            "properties": ["nullable"],
            "currentValues": {"nullable": False},
            "rationale": "Invalid null waiver.",
            "followUp": "US-017",
        }
    )

    with pytest.raises(ContractValidationError, match="may not waive null rules or semantics"):
        validate_player_data_contract_family(family)


def test_family_rejects_shared_fields_disguised_as_extensions() -> None:
    family = load_player_data_contract()
    shared = copy.deepcopy(_column(family, "players.csv", "displayName"))
    shared.update(
        {
            "rationale": "Invalid duplicate.",
            "decision": "D-033",
        }
    )
    family["profiles"]["roster"]["extensionColumns"]["players.csv"].append(shared)

    with pytest.raises(ContractValidationError, match="declares shared fields as extensions"):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize("malformed", [{}, "", None, False])
def test_family_validates_empty_extension_declarations_as_arrays(malformed: object) -> None:
    family = load_player_data_contract()
    family["profiles"]["roster"]["extensionColumns"]["player_attributes.csv"] = malformed

    with pytest.raises(
        ContractValidationError,
        match=r"extensionColumns player_attributes\.csv must be an array",
    ):
        validate_player_data_contract_family(family)


def test_family_rejects_shared_files_disguised_as_profile_only() -> None:
    family = load_player_data_contract()
    family["profiles"]["roster"]["profileOnlyFiles"]["players.csv"] = {}

    with pytest.raises(
        ContractValidationError,
        match=r"profile-only files overlap shared files: players\.csv",
    ):
        validate_player_data_contract_family(family)


def test_family_keeps_profile_only_column_order_single_sourced() -> None:
    family = load_player_data_contract()
    order = family["profiles"]["reference"]["currentColumnOrder"]["sources.csv"]
    order[0], order[1] = order[1], order[0]

    with pytest.raises(
        ContractValidationError,
        match=r"currentColumnOrder sources\.csv must match its profile-only column declaration",
    ):
        validate_player_data_contract_family(family)


def test_family_rejects_availability_overrides_for_key_fields() -> None:
    family = load_player_data_contract()
    family["profiles"]["roster"]["availabilityOverrides"].append(
        {
            "file": "players.csv",
            "fields": ["playerId"],
            "required": False,
            "nullable": True,
            "rationale": "Invalid key weakening.",
            "decision": "D-033",
        }
    )

    with pytest.raises(
        ContractValidationError,
        match=r"may not change key or relationship field players\.csv\.playerId",
    ):
        validate_player_data_contract_family(family)


def test_family_rejects_availability_overrides_for_relationship_fields() -> None:
    family = load_player_data_contract()
    roster = family["profiles"]["roster"]
    roster["relationships"].append(
        {
            "name": "displayNameRelationshipGuard",
            "kind": "valueExists",
            "from": {"file": "players.csv", "columns": ["displayName"]},
            "to": {"file": "players.csv", "columns": ["displayName"]},
        }
    )
    roster["availabilityOverrides"].append(
        {
            "file": "players.csv",
            "fields": ["displayName"],
            "required": False,
            "nullable": True,
            "rationale": "Invalid relationship weakening.",
            "decision": "D-033",
        }
    )

    with pytest.raises(
        ContractValidationError,
        match=r"may not change key or relationship field players\.csv\.displayName",
    ):
        validate_player_data_contract_family(family)


def test_family_restricts_pattern_constraints_to_string_fields() -> None:
    family = load_player_data_contract()
    constraint = family["profiles"]["roster"]["fieldConstraints"][0]
    constraint["files"] = ["player_stats.csv"]
    constraint["field"] = "season"

    with pytest.raises(
        ContractValidationError,
        match=r"pattern requires a string field: player_stats\.csv\.season",
    ):
        validate_player_data_contract_family(family)


def test_family_composes_profile_patterns_with_shared_enums() -> None:
    family = load_player_data_contract()
    _column(family, "players.csv", "displayName")["enum"] = ["alice"]
    family["profiles"]["roster"]["fieldConstraints"].append(
        {
            "files": ["players.csv"],
            "field": "displayName",
            "property": "pattern",
            "value": r"^[A-Z].*",
            "rationale": "Exercise the effective profile constraint.",
            "decision": "D-033",
        }
    )

    with pytest.raises(
        ContractValidationError,
        match=r"enum value 'alice' must match pattern",
    ):
        validate_player_data_contract_family(family)


def test_profile_parity_rejects_semantic_or_format_redefinitions() -> None:
    roster = load_roster_contract()
    height = next(
        column
        for column in roster["files"]["players.csv"]["columns"]
        if column["name"] == "heightInches"
    )
    height["unit"] = "feet"

    with pytest.raises(
        ContractValidationError,
        match=r"column-properties:roster:players\.csv:heightInches:unit",
    ):
        validate_player_data_profile_parity(roster_contract=roster)

    roster = load_roster_contract()
    roster["numericSerialization"] = "fixed two decimals"
    with pytest.raises(
        ContractValidationError,
        match=r"csv:roster:numericSerialization",
    ):
        validate_player_data_profile_parity(roster_contract=roster)


@pytest.mark.parametrize("profile_name", ["reference", "roster"])
def test_profile_parity_pins_every_family_csv_rule(profile_name: str) -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == profile_name
    )
    present_properties = {"encoding", "lineEnding"}
    absent_properties = set(family["csv"]) - present_properties

    assert set(gap["properties"]) == absent_properties
    assert all(
        gap["currentValues"][property_name] == {"absent": True}
        for property_name in absent_properties
    )

    def load_profile() -> dict:
        return (
            load_reference_contract()
            if profile_name == "reference"
            else load_roster_contract()
        )

    profile_contract = load_profile()
    assert absent_properties.isdisjoint(profile_contract)
    for property_name in present_properties:
        assert profile_contract[property_name] == family["csv"][property_name]

    for property_name in absent_properties:
        incorrect_contract = load_profile()
        incorrect_contract[property_name] = "incorrect"
        with pytest.raises(
            ContractValidationError,
            match=rf"unexpected issues: csv:{profile_name}:{property_name}",
        ):
            if profile_name == "reference":
                validate_player_data_profile_parity(
                    family=family,
                    reference_contract=incorrect_contract,
                )
            else:
                validate_player_data_profile_parity(
                    family=family,
                    roster_contract=incorrect_contract,
                )

        aligned_contract = load_profile()
        aligned_contract[property_name] = family["csv"][property_name]
        with pytest.raises(
            ContractValidationError,
            match=rf"declared gaps no longer observed: csv:{profile_name}:{property_name}",
        ):
            if profile_name == "reference":
                validate_player_data_profile_parity(
                    family=family,
                    reference_contract=aligned_contract,
                )
            else:
                validate_player_data_profile_parity(
                    family=family,
                    roster_contract=aligned_contract,
                )

    for property_name in present_properties:
        missing_contract = load_profile()
        missing_contract.pop(property_name)
        with pytest.raises(
            ContractValidationError,
            match=rf"unexpected issues: csv:{profile_name}:{property_name}",
        ):
            if profile_name == "reference":
                validate_player_data_profile_parity(
                    family=family,
                    reference_contract=missing_contract,
                )
            else:
                validate_player_data_profile_parity(
                    family=family,
                    roster_contract=missing_contract,
                )


def test_family_closes_profile_csv_rule_gap_declarations() -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["properties"].append("unknownRule")
    gap["currentValues"]["unknownRule"] = {"absent": True}
    with pytest.raises(ContractValidationError, match="references unknown CSV rules"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"].pop("delimiter")
    with pytest.raises(ContractValidationError, match="currentValues must match properties"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"]["delimiter"] = {"absent": 1}
    with pytest.raises(ContractValidationError, match="invalid absence marker"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    family["declaredAlignmentGaps"].append(
        {
            **copy.deepcopy(gap),
            "properties": ["delimiter"],
            "currentValues": {"delimiter": {"absent": True}},
        }
    )
    with pytest.raises(ContractValidationError, match="repeats current CSV rule"):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize(
    ("property_name", "current_value"),
    [
        ("headerRow", 1),
        ("headerRow", 1.0),
        ("deterministicOrdering", 0),
        ("delimiter", True),
        ("numericSerializationDescription", None),
    ],
)
def test_profile_csv_gaps_reject_coordinated_wrong_typed_current_values(
    property_name: str,
    current_value: object,
) -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"][property_name] = current_value
    roster = load_roster_contract()
    roster[property_name] = current_value

    with pytest.raises(
        ContractValidationError,
        match=rf"current value for {property_name} must use the same JSON scalar type",
    ):
        validate_player_data_profile_parity(family=family, roster_contract=roster)


def test_profile_csv_gaps_require_concrete_descriptions_to_be_non_empty() -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"]["numericSerializationDescription"] = ""
    roster = load_roster_contract()
    roster["numericSerializationDescription"] = ""

    with pytest.raises(ContractValidationError, match="must be non-empty text"):
        validate_player_data_profile_parity(family=family, roster_contract=roster)


@pytest.mark.parametrize(
    ("property_name", "current_value"),
    [
        ("delimiter", ""),
        ("delimiter", "||"),
        ("delimiter", "\n"),
        ("delimiter", "\t"),
        ("delimiter", "\x00"),
        ("quoteCharacter", ""),
        ("quoteCharacter", "''"),
        ("quoteCharacter", "\r"),
    ],
)
def test_profile_csv_gaps_require_single_character_dialect_tokens(
    property_name: str,
    current_value: str,
) -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"][property_name] = current_value
    roster = load_roster_contract()
    roster[property_name] = current_value

    with pytest.raises(ContractValidationError, match="must be exactly one"):
        validate_player_data_profile_parity(family=family, roster_contract=roster)


def test_profile_csv_gaps_reject_identical_delimiter_and_quote_character() -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"]["delimiter"] = ";"
    gap["currentValues"]["quoteCharacter"] = ";"
    roster = load_roster_contract()
    roster["delimiter"] = ";"
    roster["quoteCharacter"] = ";"

    with pytest.raises(
        ContractValidationError,
        match="delimiter and quoteCharacter must be different",
    ):
        validate_player_data_profile_parity(family=family, roster_contract=roster)


def test_profile_csv_gaps_compose_target_and_split_dialect_values() -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["properties"].remove("delimiter")
    gap["currentValues"].pop("delimiter")
    gap["currentValues"]["quoteCharacter"] = ","
    roster = load_roster_contract()
    roster["delimiter"] = ","
    roster["quoteCharacter"] = ","

    with pytest.raises(
        ContractValidationError,
        match="delimiter and quoteCharacter must be different",
    ):
        validate_player_data_profile_parity(family=family, roster_contract=roster)

    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"]["delimiter"] = ";"
    gap["properties"].remove("quoteCharacter")
    gap["currentValues"].pop("quoteCharacter")
    family["declaredAlignmentGaps"].append(
        {
            "kind": "profileCsvRules",
            "profile": "roster",
            "properties": ["quoteCharacter"],
            "currentValues": {"quoteCharacter": ";"},
            "rationale": "Invalid split dialect declaration.",
            "followUp": "US-017",
        }
    )
    roster = load_roster_contract()
    roster["delimiter"] = ";"
    roster["quoteCharacter"] = ";"

    with pytest.raises(
        ContractValidationError,
        match="delimiter and quoteCharacter must be different",
    ):
        validate_player_data_profile_parity(family=family, roster_contract=roster)


@pytest.mark.parametrize("quoting", ["banana", "none"])
def test_profile_csv_gaps_reject_unsupported_quoting_modes(quoting: str) -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"]["quoting"] = quoting
    roster = load_roster_contract()
    roster["quoting"] = quoting

    with pytest.raises(ContractValidationError, match="supported CSV quoting mode"):
        validate_player_data_profile_parity(family=family, roster_contract=roster)


def test_profile_csv_gaps_require_double_quote_escaping() -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"]["doubleQuoteEscaping"] = False
    roster = load_roster_contract()
    roster["doubleQuoteEscaping"] = False

    with pytest.raises(ContractValidationError, match="no escape-character rule"):
        validate_player_data_profile_parity(family=family, roster_contract=roster)


@pytest.mark.parametrize(
    ("property_name", "current_value"),
    [
        ("headerRow", False),
        ("delimiter", ";"),
        ("numericSerializationDescription", "Legacy serializer semantics."),
    ],
)
def test_profile_csv_gaps_allow_well_typed_concrete_current_drift(
    property_name: str,
    current_value: object,
) -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"][property_name] = current_value
    roster = load_roster_contract()
    roster[property_name] = current_value

    validate_player_data_contract_family(family)
    validate_player_data_profile_parity(family=family, roster_contract=roster)


def test_profile_csv_gaps_pin_exact_concrete_current_values() -> None:
    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["currentValues"]["delimiter"] = ";"
    roster = load_roster_contract()
    roster["delimiter"] = "|"

    with pytest.raises(ContractValidationError) as error:
        validate_player_data_profile_parity(family=family, roster_contract=roster)

    message = str(error.value)
    assert 'unexpected issues: csv:roster:delimiter:current="|":target=","' in message
    stale_issue = (
        'declared gaps no longer observed: csv:roster:delimiter:current=";":target=","'
    )
    assert stale_issue in message


@pytest.mark.parametrize(
    "property_name",
    ["doubleQuoteEscaping", "headerRow", "deterministicOrdering"],
)
@pytest.mark.parametrize("numeric_true", [1, 1.0])
def test_csv_boolean_rules_reject_numeric_lookalikes(
    property_name: str,
    numeric_true: object,
) -> None:
    family = load_player_data_contract()
    family["csv"][property_name] = numeric_true
    with pytest.raises(ContractValidationError, match=rf"csv {property_name} must be True"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    gap = next(
        item
        for item in family["declaredAlignmentGaps"]
        if item["kind"] == "profileCsvRules" and item["profile"] == "roster"
    )
    gap["properties"].remove(property_name)
    gap["currentValues"].pop(property_name)
    roster = load_roster_contract()
    roster[property_name] = numeric_true
    with pytest.raises(
        ContractValidationError,
        match=rf"unexpected issues: csv:roster:{property_name}",
    ):
        validate_player_data_profile_parity(family=family, roster_contract=roster)


def test_profile_parity_rejects_file_metadata_and_relationship_drift() -> None:
    roster = load_roster_contract()
    roster["files"]["players.csv"]["encoding"] = "UTF-16"
    with pytest.raises(
        ContractValidationError,
        match=r"file-properties:roster:players\.csv:encoding",
    ):
        validate_player_data_profile_parity(roster_contract=roster)

    roster = load_roster_contract()
    roster["relationships"] = []
    with pytest.raises(ContractValidationError, match="relationships:roster"):
        validate_player_data_profile_parity(roster_contract=roster)


def test_profile_parity_uses_type_strict_structural_comparisons() -> None:
    roster = load_roster_contract()
    roster["contractVersion"] = True
    with pytest.raises(ContractValidationError, match="contract-version:roster"):
        validate_player_data_profile_parity(roster_contract=roster)

    roster = load_roster_contract()
    games = next(
        column
        for column in roster["files"]["player_stats.csv"]["columns"]
        if column["name"] == "games"
    )
    games["required"] = 1
    with pytest.raises(
        ContractValidationError,
        match=r"definition:roster:player_stats\.csv:games:required",
    ):
        validate_player_data_profile_parity(roster_contract=roster)


def test_family_rejects_undeclared_package_inventory_entries() -> None:
    family = load_player_data_contract()
    family["profiles"]["roster"]["packageInventory"].append("notes.json")

    with pytest.raises(ContractValidationError, match="undeclared or missing package files"):
        validate_player_data_contract_family(family)


def test_family_rejects_invalid_unique_keys_and_relationships() -> None:
    family = load_player_data_contract()
    family["profiles"]["roster"]["uniqueKeys"]["players.csv"] = [["ghostField"]]
    with pytest.raises(ContractValidationError, match="references unknown fields: ghostField"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    family["profiles"]["roster"]["relationships"] = [{"nonsense": True}]
    with pytest.raises(ContractValidationError, match="name must be non-empty text"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    family["profiles"]["roster"]["relationships"][0]["kind"] = []
    with pytest.raises(ContractValidationError, match="unsupported kind"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    family["profiles"]["roster"]["relationships"][0]["kind"] = 10**5000
    with pytest.raises(ContractValidationError, match="unsupported kind"):
        validate_player_data_contract_family(family)


def test_family_rejects_untyped_alignment_gap_coordinates() -> None:
    family = load_player_data_contract()
    family["declaredAlignmentGaps"][0]["kind"] = []
    with pytest.raises(ContractValidationError, match="unsupported kind"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    file_gap = next(
        gap
        for gap in family["declaredAlignmentGaps"]
        if gap["kind"] != "profileCsvRules"
    )
    file_gap["file"] = []
    with pytest.raises(ContractValidationError, match="file must be non-empty text"):
        validate_player_data_contract_family(family)


def test_family_requires_extension_columns_in_current_order() -> None:
    family = load_player_data_contract()
    family["profiles"]["roster"]["currentColumnOrder"]["players.csv"].remove("age")

    with pytest.raises(
        ContractValidationError,
        match=r"currentColumnOrder players\.csv is missing declared extension columns: age",
    ):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize("field_name", ["heightInches", "age"])
def test_family_requires_shared_and_extension_key_fields_to_be_non_nullable(
    field_name: str,
) -> None:
    family = load_player_data_contract()
    family["profiles"]["roster"]["uniqueKeys"]["players.csv"] = [[field_name]]

    with pytest.raises(
        ContractValidationError,
        match=rf"key 1 fields must be required and non-nullable: {field_name}",
    ):
        validate_player_data_contract_family(family)


def test_family_requires_profile_only_key_fields_to_be_non_nullable() -> None:
    family = load_player_data_contract()
    sources = family["profiles"]["reference"]["profileOnlyFiles"]["sources.csv"]
    sources["uniqueKeys"] = [["upstreamVersion"]]

    with pytest.raises(
        ContractValidationError,
        match="key 1 fields must be required and non-nullable: upstreamVersion",
    ):
        validate_player_data_contract_family(family)


def test_family_requires_foreign_key_types_to_match() -> None:
    family = load_player_data_contract()
    relationship = next(
        item
        for item in family["profiles"]["roster"]["relationships"]
        if item["name"] == "playerStatsReferencePlayers"
    )
    relationship["from"]["columns"] = ["season"]

    with pytest.raises(ContractValidationError, match="must have matching scalar types"):
        validate_player_data_contract_family(family)


def test_family_requires_foreign_key_sources_to_be_non_nullable() -> None:
    family = load_player_data_contract()
    family["profiles"]["reference"]["relationships"].append(
        {
            "name": "optionalTeamAbbreviation",
            "kind": "foreignKey",
            "from": {
                "file": "player_stats.csv",
                "columns": ["teamAbbreviation"],
            },
            "to": {"file": "players.csv", "columns": ["playerId"]},
        }
    )

    with pytest.raises(
        ContractValidationError,
        match=(
            r"source fields must be required and non-nullable: "
            r"player_stats\.csv\.teamAbbreviation"
        ),
    ):
        validate_player_data_contract_family(family)


def test_family_requires_foreign_keys_to_target_declared_unique_keys() -> None:
    family = load_player_data_contract()
    relationship = next(
        item
        for item in family["profiles"]["reference"]["relationships"]
        if item["name"] == "playerStatsReferencePlayers"
    )
    relationship["to"]["columns"] = ["displayName"]

    with pytest.raises(
        ContractValidationError,
        match=r"target columns must be a declared unique key for players\.csv",
    ):
        validate_player_data_contract_family(family)


def test_family_treats_nonunique_source_type_matching_as_value_membership() -> None:
    family = load_player_data_contract()
    relationship = next(
        item
        for item in family["profiles"]["reference"]["relationships"]
        if item["name"] == "playerSourceTypesReferenceSources"
    )

    assert relationship["kind"] == "valueExists"
    assert family["profiles"]["reference"]["profileOnlyFiles"]["sources.csv"][
        "uniqueKeys"
    ] == [["sourceId"]]
    validate_player_data_contract_family(family)


def test_family_requires_composite_foreign_key_target_order_to_match_a_key() -> None:
    family = load_player_data_contract()
    family["profiles"]["reference"]["relationships"].append(
        {
            "name": "reorderedPlayerSeasonForeignKey",
            "kind": "foreignKey",
            "from": {
                "file": "player_stats.csv",
                "columns": ["season", "playerId"],
            },
            "to": {
                "file": "player_stats.csv",
                "columns": ["season", "playerId"],
            },
        }
    )

    with pytest.raises(
        ContractValidationError,
        match=r"target columns must be a declared unique key for player_stats\.csv",
    ):
        validate_player_data_contract_family(family)


def test_family_requires_exact_key_set_types_to_match() -> None:
    family = load_player_data_contract()
    season = next(
        column
        for column in family["profiles"]["reference"]["extensionColumns"][
            "player_attributes.csv"
        ]
        if column["name"] == "season"
    )
    season["type"] = "string"
    season.pop("minimum")
    season.pop("maximum")

    with pytest.raises(ContractValidationError, match="must have matching scalar types"):
        validate_player_data_contract_family(family)


def test_family_requires_exact_key_sets_to_include_a_unique_key() -> None:
    family = load_player_data_contract()
    exact_key_set = next(
        relationship
        for relationship in family["profiles"]["reference"]["relationships"]
        if relationship["kind"] == "exactKeySet"
    )
    exact_key_set["columns"] = ["season"]
    with pytest.raises(ContractValidationError, match="must include a declared unique key"):
        validate_player_data_contract_family(family)


def test_family_rejects_incoherent_columns_constraints_and_csv_rules() -> None:
    family = load_player_data_contract()
    height = _column(family, "players.csv", "heightInches")
    height["minimum"] = 100
    with pytest.raises(ContractValidationError, match="minimum cannot exceed maximum"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    family["profiles"]["roster"]["fieldConstraints"].append(
        copy.deepcopy(family["profiles"]["roster"]["fieldConstraints"][0])
    )
    with pytest.raises(ContractValidationError, match="repeats field constraint"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    family["profiles"]["roster"]["fieldConstraints"][0]["value"] = "[broken"
    with pytest.raises(ContractValidationError, match="pattern is invalid"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    family["csv"]["headerStyle"] = "snake_case"
    with pytest.raises(ContractValidationError, match="headerStyle must be 'camelCase'"):
        validate_player_data_contract_family(family)


def test_family_rejects_oversized_regex_declarations() -> None:
    oversized_pattern = "a{999999999999999999999999999999999999}"
    family = load_player_data_contract()
    _column(family, "players.csv", "displayName")["pattern"] = oversized_pattern
    with pytest.raises(ContractValidationError, match="pattern is invalid"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    family["profiles"]["roster"]["fieldConstraints"][0][
        "value"
    ] = oversized_pattern
    with pytest.raises(ContractValidationError, match="pattern is invalid"):
        validate_player_data_contract_family(family)


def test_profile_parity_rejects_roster_extension_bound_drift() -> None:
    roster = load_roster_contract()
    possessions = next(
        column
        for column in roster["files"]["player_stats.csv"]["columns"]
        if column["name"] == "possessions"
    )
    possessions.pop("minimum")

    with pytest.raises(
        ContractValidationError,
        match=r"extension-definition:roster:player_stats\.csv:possessions",
    ):
        validate_player_data_profile_parity(roster_contract=roster)


@pytest.mark.parametrize("property_name", ["minimum", "maximum"])
def test_family_rejects_explicit_null_numeric_bounds(property_name: str) -> None:
    family = load_player_data_contract()
    _column(family, "player_stats.csv", "season")[property_name] = None

    with pytest.raises(
        ContractValidationError,
        match=rf"{property_name} must be finite numeric when present",
    ):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize("invalid_bound", [float("nan"), float("inf"), float("-inf")])
def test_family_rejects_nonfinite_numeric_bounds(invalid_bound: float) -> None:
    family = load_player_data_contract()
    _column(family, "players.csv", "heightInches")["maximum"] = invalid_bound

    with pytest.raises(ContractValidationError, match="maximum must be finite numeric"):
        validate_player_data_contract_family(family)


def test_family_rejects_fractional_integer_bounds() -> None:
    family = load_player_data_contract()
    _column(family, "player_stats.csv", "games")["minimum"] = 1.5

    with pytest.raises(ContractValidationError, match="minimum must be an integer bound"):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize(
    ("property_name", "bound", "accepted", "rejected", "message"),
    [
        ("minimum", 2**53 + 1, 2**53 + 1, 2**53, "must be at least"),
        ("maximum", 2**53, 2**53, 2**53 + 1, "must be at most"),
        ("minimum", 10**400, 10**400, 10**400 - 1, "must be at least"),
        ("maximum", 10**400, 10**400, 10**400 + 1, "must be at most"),
    ],
)
def test_integer_bounds_compare_exactly_without_float_aliasing(
    property_name: str,
    bound: int,
    accepted: int,
    rejected: int,
    message: str,
) -> None:
    family = load_player_data_contract()
    season = _column(family, "player_stats.csv", "season")
    season[property_name] = bound
    if property_name == "minimum":
        season["maximum"] = bound + 1

    validate_player_data_contract_family(family)
    assert serialize_csv_value(accepted, season) == str(accepted)
    with pytest.raises(ContractValidationError, match=message):
        serialize_csv_value(rejected, season)


def test_number_bounds_and_values_reject_float_overflow_cleanly() -> None:
    family = load_player_data_contract()
    minutes = _column(family, "player_stats.csv", "minutes")
    minutes["maximum"] = 10**400

    with pytest.raises(ContractValidationError, match="maximum must be finite numeric"):
        validate_player_data_contract_family(family)

    minutes.pop("maximum")
    with pytest.raises(ContractValidationError, match="must be a finite number"):
        serialize_csv_value(10**400, minutes)


@pytest.mark.parametrize("property_name", ["minimum", "maximum"])
def test_number_bounds_require_exact_ieee754_round_trips(property_name: str) -> None:
    family = load_player_data_contract()
    minutes = _column(family, "player_stats.csv", "minutes")
    minutes[property_name] = 2**53 + 1

    with pytest.raises(
        ContractValidationError,
        match=rf"{property_name} does not round-trip through IEEE-754 normalization",
    ):
        validate_player_data_contract_family(family)

    runtime_column = {
        "type": "number",
        "required": True,
        "nullable": False,
        property_name: 2**53 + 1,
    }
    with pytest.raises(ContractValidationError, match=rf"invalid {property_name}"):
        serialize_csv_value(2**53, runtime_column)

    for exact_bound in (2**53, 2**53 + 2):
        exact_family = load_player_data_contract()
        exact_minutes = _column(exact_family, "player_stats.csv", "minutes")
        exact_minutes[property_name] = exact_bound
        validate_player_data_contract_family(exact_family)


def test_oversized_integers_fail_with_contract_errors() -> None:
    family = load_player_data_contract()
    season = _column(family, "player_stats.csv", "season")
    oversized_text = "9" * 5000
    oversized_integer = 10**5000

    for value in (oversized_text, oversized_integer):
        with pytest.raises(ContractValidationError, match="supported decimal length"):
            serialize_csv_value(value, season)

    bounded_column = {
        "type": "integer",
        "required": True,
        "nullable": False,
        "minimum": oversized_integer,
    }
    with pytest.raises(ContractValidationError, match="invalid minimum"):
        serialize_csv_value(1, bounded_column)

    season["minimum"] = oversized_integer
    with pytest.raises(ContractValidationError, match="exceeds the supported integer length"):
        validate_player_data_contract_family(family)

    family = load_player_data_contract()
    _column(family, "player_stats.csv", "season")["enum"] = [oversized_integer]
    with pytest.raises(
        ContractValidationError,
        match="cannot be represented as canonical JSON",
    ):
        validate_player_data_contract_family(family)

    for field_type in ("integer", "number"):
        enum_column = {
            "type": field_type,
            "required": True,
            "nullable": False,
            "enum": [oversized_integer],
        }
        with pytest.raises(ContractValidationError, match="must be one of"):
            serialize_csv_value(1, enum_column)

    with pytest.raises(ContractValidationError, match="Unsupported test contract version"):
        contract_files(
            {"contractVersion": oversized_integer, "files": {"test.csv": {}}},
            contract_name="Test",
            contract_version=1,
        )

    with pytest.raises(ContractValidationError, match="uses unsupported type"):
        serialize_csv_value(
            1,
            {
                "type": oversized_integer,
                "required": True,
                "nullable": False,
            },
        )

    family = load_player_data_contract()
    _column(family, "player_stats.csv", "season")["type"] = oversized_integer
    with pytest.raises(ContractValidationError, match="uses unsupported type"):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize("current_type", ["bogus", {"absent": True}, None])
def test_family_validates_declared_current_gap_types(current_type: object) -> None:
    family = load_player_data_contract()
    type_gap = next(
        gap
        for gap in family["declaredAlignmentGaps"]
        if gap["profile"] == "roster"
        and gap.get("file") == "players.csv"
        and gap.get("properties") == ["type"]
    )
    type_gap["currentValues"]["type"] = current_type

    with pytest.raises(ContractValidationError, match="uses unsupported type"):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize("marker", [1, 1.0])
def test_family_requires_strict_boolean_absence_markers(marker: object) -> None:
    family = load_player_data_contract()
    type_gap = next(
        gap
        for gap in family["declaredAlignmentGaps"]
        if gap["profile"] == "roster"
        and gap.get("file") == "players.csv"
        and gap.get("properties") == ["type"]
    )
    type_gap["currentValues"]["type"] = {"absent": marker}

    with pytest.raises(ContractValidationError, match="invalid absence marker"):
        validate_player_data_contract_family(family)


@pytest.mark.parametrize(
    ("field_name", "property_name", "current_value", "message"),
    [
        (
            "insideScoring",
            "minimum",
            "25",
            "minimum must be finite numeric when present",
        ),
        (
            "insideScoring",
            "maximum",
            None,
            "maximum must be finite numeric when present",
        ),
        ("season", "enum", [], "enum must be non-empty and unique"),
        (
            "season",
            "enum",
            ["2025"],
            "enum value '2025' does not match field type integer",
        ),
        ("playerId", "pattern", "[broken", "pattern is invalid"),
    ],
)
def test_family_validates_declared_current_gap_constraints(
    field_name: str,
    property_name: str,
    current_value: object,
    message: str,
) -> None:
    family = load_player_data_contract()
    if field_name == "season":
        file_name = "player_stats.csv"
    elif field_name == "insideScoring":
        file_name = "player_attributes.csv"
    else:
        file_name = "players.csv"
    family["declaredAlignmentGaps"].append(
        {
            "kind": "sharedDefinition",
            "profile": "roster",
            "file": file_name,
            "fields": [field_name],
            "properties": [property_name],
            "currentValues": {property_name: current_value},
            "rationale": "Invalid pinned current definition.",
            "followUp": "US-017",
        }
    )

    with pytest.raises(ContractValidationError, match=message):
        validate_player_data_contract_family(family)


def test_family_rechecks_relationships_against_declared_current_gap_types() -> None:
    family = load_player_data_contract()
    family["declaredAlignmentGaps"].append(
        {
            "kind": "sharedDefinition",
            "profile": "reference",
            "file": "player_attributes.csv",
            "fields": ["playerId"],
            "properties": ["type"],
            "currentValues": {"type": "integer"},
            "rationale": "Invalid relationship type drift.",
            "followUp": "US-017",
        }
    )

    with pytest.raises(ContractValidationError, match="must have matching scalar types"):
        validate_player_data_contract_family(family)


def test_family_preserves_unique_key_types_across_declared_gaps() -> None:
    family = load_player_data_contract()
    season_gap = next(
        gap
        for gap in family["declaredAlignmentGaps"]
        if gap["profile"] == "roster"
        and gap.get("file") == "player_stats.csv"
        and gap.get("fields") == ["season"]
    )
    season_gap["properties"] = ["type", "minimum", "maximum"]
    season_gap["currentValues"] = {
        "type": "string",
        "minimum": {"absent": True},
        "maximum": {"absent": True},
    }

    with pytest.raises(
        ContractValidationError,
        match=r"may not change the type of key or relationship field "
        r"player_stats\.csv\.season",
    ):
        validate_player_data_contract_family(family)


def test_family_preserves_relationship_only_field_types_across_declared_gaps() -> None:
    family = load_player_data_contract()
    family["profiles"]["roster"]["relationships"].append(
        {
            "name": "displayNameRelationshipGuard",
            "kind": "valueExists",
            "from": {"file": "players.csv", "columns": ["displayName"]},
            "to": {"file": "players.csv", "columns": ["displayName"]},
        }
    )
    family["declaredAlignmentGaps"].append(
        {
            "kind": "sharedDefinition",
            "profile": "roster",
            "file": "players.csv",
            "fields": ["displayName"],
            "properties": ["type"],
            "currentValues": {"type": "sha256"},
            "rationale": "Invalid relationship-only type drift.",
            "followUp": "US-017",
        }
    )

    with pytest.raises(
        ContractValidationError,
        match=r"may not change the type of key or relationship field "
        r"players\.csv\.displayName",
    ):
        validate_player_data_contract_family(family)


def test_family_checks_target_relationship_types_before_applying_gaps() -> None:
    family = load_player_data_contract()
    family["profiles"]["reference"]["relationships"].append(
        {
            "name": "invalidTargetTypeMaskedByGap",
            "kind": "foreignKey",
            "from": {"file": "player_stats.csv", "columns": ["season"]},
            "to": {"file": "players.csv", "columns": ["displayName"]},
        }
    )
    family["declaredAlignmentGaps"].append(
        {
            "kind": "sharedDefinition",
            "profile": "reference",
            "file": "players.csv",
            "fields": ["displayName"],
            "properties": ["type"],
            "currentValues": {"type": "integer"},
            "rationale": "Invalid attempt to mask a final relationship mismatch.",
            "followUp": "US-017",
        }
    )

    with pytest.raises(ContractValidationError, match="must have matching scalar types"):
        validate_player_data_contract_family(family)


def test_family_rechecks_constraints_against_declared_current_gap_types() -> None:
    family = load_player_data_contract()
    for file_name in ("players.csv", "player_stats.csv", "player_attributes.csv"):
        family["declaredAlignmentGaps"].append(
            {
                "kind": "sharedDefinition",
                "profile": "roster",
                "file": file_name,
                "fields": ["playerId"],
                "properties": ["type"],
                "currentValues": {"type": "integer"},
                "rationale": "Invalid profile constraint type drift.",
                "followUp": "US-017",
            }
        )

    with pytest.raises(
        ContractValidationError,
        match=r"pattern requires a string field: players\.csv\.playerId",
    ):
        validate_player_data_contract_family(family)


def test_family_rejects_duplicate_declared_current_gap_coordinates() -> None:
    family = load_player_data_contract()
    for current_type in (["bogus"], "integer"):
        family["declaredAlignmentGaps"].append(
            {
                "kind": "sharedDefinition",
                "profile": "reference",
                "file": "player_attributes.csv",
                "fields": ["playerId"],
                "properties": ["type"],
                "currentValues": {"type": current_type},
                "rationale": "Conflicting current definition pins.",
                "followUp": "US-017",
            }
        )

    with pytest.raises(
        ContractValidationError,
        match=(
            r"repeats current definition for "
            r"reference\.player_attributes\.csv\.playerId\.type"
        ),
    ):
        validate_player_data_contract_family(family)


def test_canonical_numeric_serialization_is_shared_across_scalar_inputs() -> None:
    family = load_player_data_contract()
    number_column = _column(family, "player_stats.csv", "minutes")
    integer_column = _column(family, "player_stats.csv", "points")

    assert serialize_csv_value(5, number_column) == "5"
    assert serialize_csv_value(5.0, number_column) == "5"
    assert serialize_csv_value(-0.0, number_column) == "0"
    assert serialize_csv_value(0.125, number_column) == "0.125"
    assert serialize_csv_value(1e20, number_column) == "100000000000000000000"
    assert serialize_csv_value(1e-7, number_column) == "0.0000001"
    assert serialize_csv_value(42.0, integer_column) == "42"
    assert serialize_csv_value(None, number_column) == ""

    with pytest.raises(ContractValidationError, match="must be an integer"):
        serialize_csv_value(42.5, integer_column)


@pytest.mark.parametrize("version", [0, 2, True, "1"])
def test_rejects_unsupported_player_data_contract_versions(version: object) -> None:
    with pytest.raises(ContractValidationError, match="Unsupported player data contract version"):
        load_player_data_contract(version)  # type: ignore[arg-type]


def test_safely_rejects_oversized_player_data_contract_versions() -> None:
    with pytest.raises(
        ContractValidationError,
        match="Unsupported player data contract version: <int outside supported representation>",
    ):
        load_player_data_contract(10**5000)
