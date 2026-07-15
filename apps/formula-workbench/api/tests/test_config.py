from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from formula_preview_api import PreviewSettings, load_settings
from formula_preview_api.config import (
    API_V1_MAX_BASELINE_PLAYERS,
    API_V1_MAX_COHORT_SIZE,
    API_V1_MAX_PINNED_PLAYERS,
    API_V1_MAX_SEARCH_RESULTS,
    API_V1_MAX_SELECTED_PLAYERS,
)


def _maximum_settings() -> PreviewSettings:
    return PreviewSettings(
        reference_package=Path("reference-v2"),
        season=2026,
        default_sample_size=API_V1_MAX_BASELINE_PLAYERS,
        max_pinned_players=API_V1_MAX_PINNED_PLAYERS,
        max_selected_players=API_V1_MAX_SELECTED_PLAYERS,
        max_search_results=API_V1_MAX_SEARCH_RESULTS,
        max_cohort_size=API_V1_MAX_COHORT_SIZE,
        latency_budget_ms=3000,
    )


def test_default_configuration_declares_version_1_contract_maxima() -> None:
    settings = load_settings()

    assert settings.default_sample_size == API_V1_MAX_BASELINE_PLAYERS
    assert settings.max_pinned_players == API_V1_MAX_PINNED_PLAYERS
    assert settings.max_selected_players == API_V1_MAX_SELECTED_PLAYERS
    assert settings.max_search_results == API_V1_MAX_SEARCH_RESULTS
    assert settings.max_cohort_size == API_V1_MAX_COHORT_SIZE


def test_version_1_contract_maxima_and_reduced_limits_are_valid() -> None:
    maximum = _maximum_settings()
    reduced = replace(
        maximum,
        default_sample_size=10,
        max_pinned_players=4,
        max_selected_players=12,
        max_search_results=5,
        max_cohort_size=500,
    )

    assert maximum.default_sample_size == 25
    assert maximum.max_pinned_players == 25
    assert maximum.max_selected_players == 25
    assert maximum.max_search_results == 20
    assert maximum.max_cohort_size == 1000
    assert reduced.max_pinned_players == 4
    assert reduced.max_selected_players == 12


@pytest.mark.parametrize(
    ("field", "maximum"),
    [
        ("default_sample_size", API_V1_MAX_BASELINE_PLAYERS),
        ("max_pinned_players", API_V1_MAX_PINNED_PLAYERS),
        ("max_selected_players", API_V1_MAX_SELECTED_PLAYERS),
        ("max_search_results", API_V1_MAX_SEARCH_RESULTS),
        ("max_cohort_size", API_V1_MAX_COHORT_SIZE),
    ],
)
def test_settings_reject_values_above_version_1_contract_maxima(
    field: str,
    maximum: int,
) -> None:
    with pytest.raises(
        ValueError,
        match=rf"{field} cannot exceed the API version 1 maximum of {maximum}",
    ):
        replace(_maximum_settings(), **{field: maximum + 1})


def test_legacy_yaml_inherits_the_pin_limit_for_selected_players(tmp_path: Path) -> None:
    config_path = tmp_path / "preview.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "paths": {"reference_package_dir": "reference-v2"},
                "preview": {
                    "season": 2026,
                    "default_sample_size": 10,
                    "max_pinned_players": 7,
                    "max_search_results": 5,
                    "max_cohort_size": 500,
                    "latency_budget_ms": 3000,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.max_pinned_players == 7
    assert settings.max_selected_players == 7


def test_yaml_can_narrow_pin_and_selected_player_limits_independently(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "preview.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "paths": {"reference_package_dir": "reference-v2"},
                "preview": {
                    "season": 2026,
                    "default_sample_size": 10,
                    "max_pinned_players": 2,
                    "max_selected_players": 8,
                    "max_search_results": 5,
                    "max_cohort_size": 500,
                    "latency_budget_ms": 3000,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.max_pinned_players == 2
    assert settings.max_selected_players == 8
