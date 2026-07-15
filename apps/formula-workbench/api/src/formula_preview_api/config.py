from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Final

import yaml

DEFAULT_CONFIG_PATH = Path("apps/formula-workbench/api/config/default.yaml")
API_V1_MAX_BASELINE_PLAYERS: Final = 25
API_V1_MAX_PINNED_PLAYERS: Final = 25
API_V1_MAX_SELECTED_PLAYERS: Final = 25
API_V1_MAX_SEARCH_RESULTS: Final = 20
API_V1_MAX_COHORT_SIZE: Final = 1000


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "apps").is_dir():
            return candidate
    return current


def _positive_integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"Preview configuration field {field} must be a positive integer.")
    return value


def _bounded_positive_integer(value: object, field: str, maximum: int) -> int:
    parsed = _positive_integer(value, field)
    if parsed > maximum:
        raise ValueError(
            f"Preview configuration field {field} cannot exceed the API version 1 "
            f"maximum of {maximum}."
        )
    return parsed


@dataclass(frozen=True)
class PreviewSettings:
    reference_package: Path
    season: int
    default_sample_size: int
    max_pinned_players: int
    max_search_results: int
    max_cohort_size: int
    latency_budget_ms: int
    max_selected_players: int | None = None

    def __post_init__(self) -> None:
        max_selected_players = (
            self.max_pinned_players
            if self.max_selected_players is None
            else self.max_selected_players
        )
        _positive_integer(self.season, "season")
        _bounded_positive_integer(
            self.default_sample_size,
            "default_sample_size",
            API_V1_MAX_BASELINE_PLAYERS,
        )
        _bounded_positive_integer(
            self.max_pinned_players,
            "max_pinned_players",
            API_V1_MAX_PINNED_PLAYERS,
        )
        _bounded_positive_integer(
            max_selected_players,
            "max_selected_players",
            API_V1_MAX_SELECTED_PLAYERS,
        )
        object.__setattr__(self, "max_selected_players", max_selected_players)
        _bounded_positive_integer(
            self.max_search_results,
            "max_search_results",
            API_V1_MAX_SEARCH_RESULTS,
        )
        _bounded_positive_integer(
            self.max_cohort_size,
            "max_cohort_size",
            API_V1_MAX_COHORT_SIZE,
        )
        _positive_integer(self.latency_budget_ms, "latency_budget_ms")
        if self.default_sample_size > self.max_cohort_size:
            raise ValueError(
                "Preview configuration default_sample_size cannot exceed max_cohort_size."
            )
        if self.max_pinned_players > self.max_cohort_size:
            raise ValueError(
                "Preview configuration max_pinned_players cannot exceed max_cohort_size."
            )

    def with_overrides(
        self,
        *,
        reference_package: str | Path | None = None,
        season: int | None = None,
    ) -> PreviewSettings:
        if season is not None:
            _positive_integer(season, "season override")
        if reference_package is not None and not str(reference_package).strip():
            raise ValueError("Reference package override must be a non-empty path.")
        return replace(
            self,
            reference_package=(
                Path(reference_package).expanduser().resolve()
                if reference_package is not None
                else self.reference_package
            ),
            season=self.season if season is None else season,
        )


def _settings_from_mapping(payload: object, root: Path) -> PreviewSettings:
    if not isinstance(payload, dict):
        raise ValueError("Formula preview configuration must be a mapping.")
    paths = payload.get("paths")
    preview = payload.get("preview")
    if not isinstance(paths, dict) or not isinstance(preview, dict):
        raise ValueError("Formula preview configuration requires paths and preview mappings.")

    raw_package = paths.get("reference_package_dir")
    if not isinstance(raw_package, str) or not raw_package.strip():
        raise ValueError(
            "Preview configuration field paths.reference_package_dir must be non-empty text."
        )
    package = Path(raw_package).expanduser()
    if not package.is_absolute():
        package = root / package

    season = _positive_integer(preview.get("season"), "preview.season")
    default_sample_size = _positive_integer(
        preview.get("default_sample_size"), "preview.default_sample_size"
    )
    max_pinned_players = _positive_integer(
        preview.get("max_pinned_players"), "preview.max_pinned_players"
    )
    max_selected_players = _positive_integer(
        preview.get("max_selected_players", max_pinned_players),
        "preview.max_selected_players",
    )
    max_search_results = _positive_integer(
        preview.get("max_search_results"), "preview.max_search_results"
    )
    max_cohort_size = _positive_integer(
        preview.get("max_cohort_size"), "preview.max_cohort_size"
    )
    latency_budget_ms = _positive_integer(
        preview.get("latency_budget_ms"), "preview.latency_budget_ms"
    )
    return PreviewSettings(
        reference_package=package.resolve(),
        season=season,
        default_sample_size=default_sample_size,
        max_pinned_players=max_pinned_players,
        max_search_results=max_search_results,
        max_cohort_size=max_cohort_size,
        latency_budget_ms=latency_budget_ms,
        max_selected_players=max_selected_players,
    )


def load_settings(path: str | Path | None = None) -> PreviewSettings:
    root = find_project_root()
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not config_path.is_absolute():
        config_path = root / config_path
    if not config_path.is_file():
        raise FileNotFoundError(f"Formula preview configuration file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        payload: Any = yaml.safe_load(handle) or {}
    return _settings_from_mapping(payload, root)
