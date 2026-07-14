from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _dry_run(target: str, *arguments: str) -> list[str]:
    result = subprocess.run(
        ["make", "--dry-run", *arguments, target, "PYTHON=python"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def test_all_target_runs_the_pipeline_sequentially_even_with_parallel_make() -> None:
    commands = _dry_run("all", "--jobs=4")

    pipeline_commands = [
        command
        for command in commands
        if command.startswith("python -m reference_data_app")
        or command.startswith("python -m roster_generator")
    ]
    assert pipeline_commands == [
        "python -m reference_data_app --config apps/reference-data/config/default.yaml publish",
        "python -m roster_generator --config apps/roster-generator/config/default.yaml generate",
    ]


def test_clean_target_removes_only_ignored_roster_packages() -> None:
    commands = "\n".join(_dry_run("clean"))

    assert "roster_data/packages" in commands
    assert "roster_data/default_roster.json" not in commands
    assert "roster_data/players.csv" not in commands
    assert "reports" not in commands
    assert "build" in commands
    assert ".pytest_cache" in commands


def test_manifest_target_uses_the_deterministic_generator() -> None:
    assert _dry_run("manifest") == ["python scripts/update_file_manifest.py"]


def test_formula_api_target_uses_its_application_configuration() -> None:
    assert _dry_run("formula-api") == [
        "python -m formula_preview_api --config apps/formula-workbench/api/config/default.yaml"
    ]
