"""Regenerate the tracked SHA-256 manifest from Git's staged file set."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path("FILE_MANIFEST.sha256")


def _tracked_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return sorted(
        Path(os.fsdecode(raw_path))
        for raw_path in result.stdout.split(b"\0")
        if raw_path and Path(os.fsdecode(raw_path)) != MANIFEST_PATH
    )


def _staged_content(root: Path, relative_path: Path) -> bytes:
    result = subprocess.run(
        ["git", "show", f":{relative_path.as_posix()}"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return result.stdout


def update_manifest(root: Path = ROOT) -> None:
    lines: list[str] = []
    for relative_path in _tracked_paths(root):
        digest = hashlib.sha256(_staged_content(root, relative_path)).hexdigest()
        lines.append(f"{digest}  {relative_path.as_posix()}\n")

    (root / MANIFEST_PATH).write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    update_manifest()
