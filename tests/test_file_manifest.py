from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from scripts.update_file_manifest import update_manifest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "FILE_MANIFEST.sha256"
MANIFEST_PATH = MANIFEST.relative_to(ROOT).as_posix()


def _manifest_entries() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line_number, line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), start=1):
        digest, separator, relative_path = line.partition("  ")
        assert separator and relative_path, f"Malformed manifest entry on line {line_number}"
        assert len(digest) == 64 and all(character in "0123456789abcdef" for character in digest), (
            f"Invalid SHA-256 digest on line {line_number}"
        )
        entries.append((relative_path, digest))
    return entries


def _tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return sorted(
        os.fsdecode(path)
        for path in result.stdout.split(b"\0")
        if path and os.fsdecode(path) != MANIFEST_PATH
    )


def test_file_manifest_entries_are_sorted_and_unique() -> None:
    paths = [path for path, _digest in _manifest_entries()]

    assert paths == sorted(paths)
    assert len(paths) == len(set(paths))


def test_file_manifest_covers_every_other_tracked_file() -> None:
    manifest_paths = [path for path, _digest in _manifest_entries()]

    assert manifest_paths == _tracked_paths()


def test_file_manifest_hashes_match_current_content() -> None:
    for relative_path, expected_digest in _manifest_entries():
        path = ROOT / relative_path
        assert path.is_file(), f"Manifest path does not exist: {relative_path}"
        actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual_digest == expected_digest, f"Manifest hash mismatch: {relative_path}"


def test_manifest_generator_hashes_staged_content(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)

    tracked = repository / "tracked.txt"
    tracked.write_text("staged\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True)
    tracked.write_text("unstaged\n", encoding="utf-8")

    update_manifest(repository)

    expected = hashlib.sha256(b"staged\n").hexdigest()
    assert (repository / MANIFEST_PATH).read_text(encoding="utf-8") == (
        f"{expected}  tracked.txt\n"
    )
