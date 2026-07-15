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


def test_current_profiles_match_exact_declared_alignment_ledger() -> None:
    validate_player_data_profile_parity()


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
            "kind": "foreignKey",
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
