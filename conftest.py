from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.fixture
def reference_config() -> dict:
    return _load_yaml(ROOT / "apps" / "reference-data" / "config" / "default.yaml")


@pytest.fixture
def roster_config() -> dict:
    return _load_yaml(ROOT / "apps" / "roster-generator" / "config" / "default.yaml")
