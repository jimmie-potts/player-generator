"""Shared integrity primitives for deterministic data packages."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping


def content_hash(file_hashes: Mapping[str, str]) -> str:
    """Hash a filename-sorted set of per-file hashes into one package content hash."""
    pairs = "\n".join(f"{filename}:{file_hashes[filename]}" for filename in sorted(file_hashes))
    return hashlib.sha256(pairs.encode("utf-8")).hexdigest()
