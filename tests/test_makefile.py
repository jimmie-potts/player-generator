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
        "python -m reference_data_app --config apps/reference-data/config/default.yaml download",
        "python -m reference_data_app --config apps/reference-data/config/default.yaml build",
        "python -m roster_generator --config apps/roster-generator/config/default.yaml generate",
        "python -m roster_generator --config apps/roster-generator/config/default.yaml compare",
    ]


def test_clean_target_never_removes_tracked_sample_outputs() -> None:
    commands = "\n".join(_dry_run("clean"))

    assert "roster_data" not in commands
    assert "reports" not in commands
    assert "build" in commands
    assert ".pytest_cache" in commands


def test_manifest_target_uses_the_deterministic_generator() -> None:
    assert _dry_run("manifest") == ["python scripts/update_file_manifest.py"]
