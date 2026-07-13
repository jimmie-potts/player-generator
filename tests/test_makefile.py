from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_target_downloads_reference_data_before_building() -> None:
    result = subprocess.run(
        ["make", "--dry-run", "all", "PYTHON=python"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    commands = result.stdout.splitlines()
    download_index = commands.index(
        "python -m reference_data_app --config apps/reference-data/config/default.yaml download"
    )
    build_index = commands.index(
        "python -m reference_data_app --config apps/reference-data/config/default.yaml build"
    )
    assert download_index < build_index
