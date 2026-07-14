from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("apps/roster-generator/config/default.yaml")


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "apps").exists():
            return candidate
    return current


def load_config(path: str | Path | None = None) -> tuple[dict[str, Any], Path]:
    root = find_project_root()
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.is_absolute():
        config_path = root / config_path
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if not isinstance(config, dict):
        raise ValueError(f"Roster configuration must be a mapping: {config_path}")
    config["_meta"] = {
        "project_root": str(root),
        "config_path": str(config_path.resolve()),
    }
    return config, root


def resolve_path(config: dict[str, Any], key: str) -> Path:
    root = Path(config["_meta"]["project_root"])
    path = Path(config["paths"][key])
    return path if path.is_absolute() else root / path


def resolve_optional_path(config: Mapping[str, Any], key: str) -> Path | None:
    value = config["paths"].get(key)
    if value in {None, ""}:
        return None
    root = Path(str(config["_meta"]["project_root"]))
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def semantic_configuration(config: Mapping[str, Any], seed: int) -> dict[str, object]:
    """Return only settings that can affect generated roster content."""
    return {
        "rosterContractVersion": config["project"]["roster_contract_version"],
        "seed": seed,
        "selection": config["selection"],
        "mutation": config["mutation"],
    }


def configuration_hash(config: Mapping[str, Any], seed: int) -> str:
    payload = json.dumps(
        semantic_configuration(config, seed),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
