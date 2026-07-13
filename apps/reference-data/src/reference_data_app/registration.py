from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from player_data_contracts.io import sha256_file

from reference_data_app.adapters import AdapterValidationError, inspect_source

REGISTRY_VERSION = 1


class RegistrationError(ValueError):
    """Raised when source registration or registered-source verification fails."""


@dataclass(frozen=True)
class RegisteredSource:
    source_id: str
    source_type: str
    input_path: str
    original_filename: str
    sha256: str
    adapter_version: int
    row_count: int
    processed_at: str
    upstream_version: str | None = None
    license_status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "sourceId": self.source_id,
            "sourceType": self.source_type,
            "inputPath": self.input_path,
            "originalFilename": self.original_filename,
            "sha256": self.sha256,
            "adapterVersion": self.adapter_version,
            "rowCount": self.row_count,
            "processedAt": self.processed_at,
        }
        if self.upstream_version is not None:
            result["upstreamVersion"] = self.upstream_version
        result["licenseStatus"] = self.license_status
        return result

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RegisteredSource:
        return cls(
            source_id=str(payload["sourceId"]),
            source_type=str(payload["sourceType"]),
            input_path=str(payload["inputPath"]),
            original_filename=str(payload["originalFilename"]),
            sha256=str(payload["sha256"]),
            adapter_version=int(payload["adapterVersion"]),
            row_count=int(payload["rowCount"]),
            processed_at=str(payload["processedAt"]),
            upstream_version=_optional_text(payload.get("upstreamVersion")),
            license_status=_optional_text(payload.get("licenseStatus")) or "unknown",
        )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _timestamp(processed_at: datetime | None) -> str:
    value = processed_at or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise RegistrationError("Processing timestamp must include a timezone.")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def derive_source_id(source_type: str, path: Path) -> str:
    sanitized_stem = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    return f"{source_type}:{sanitized_stem or 'source'}"


def load_registered_sources(registry_path: Path) -> list[RegisteredSource]:
    if not registry_path.exists():
        return []
    try:
        with registry_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise RegistrationError(
            f"Unable to read source registry {registry_path}: {error}"
        ) from error

    if not isinstance(payload, dict):
        raise RegistrationError(f"Invalid source registry {registry_path}: expected an object.")
    if payload.get("registryVersion") != REGISTRY_VERSION:
        raise RegistrationError(
            f"Unsupported source registry version in {registry_path}: "
            f"{payload.get('registryVersion')!r}"
        )
    try:
        sources = [RegisteredSource.from_dict(source) for source in payload["sources"]]
    except (KeyError, TypeError, ValueError) as error:
        raise RegistrationError(f"Invalid source registry {registry_path}: {error}") from error

    source_ids = [source.source_id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise RegistrationError(f"Source registry {registry_path} contains duplicate source IDs.")
    return sorted(sources, key=lambda source: source.source_id)


def verify_registered_source(source: RegisteredSource) -> None:
    path = Path(source.input_path).expanduser().resolve()
    context = (
        f"{path}: adapter {source.source_type} v{source.adapter_version}: "
        f"source ID {source.source_id!r}"
    )
    action = "Restore the registered file or rebuild its local registration before publishing."
    try:
        inspection = inspect_source(path, source.source_type, source.adapter_version)
    except AdapterValidationError as error:
        raise RegistrationError(
            f"{context}: registered source cannot be verified: {error}. {action}"
        ) from error
    try:
        actual_sha256 = sha256_file(path)
    except OSError as error:
        raise RegistrationError(
            f"{context}: registered source cannot be hashed: {error}. {action}"
        ) from error

    mismatches: list[str] = []
    if actual_sha256 != source.sha256:
        mismatches.append(
            f"SHA-256 changed (registered {source.sha256}, current {actual_sha256})"
        )
    if inspection.row_count != source.row_count:
        mismatches.append(
            f"row count changed (registered {source.row_count}, current {inspection.row_count})"
        )
    if mismatches:
        raise RegistrationError(
            f"{context}: registered source no longer matches its local file: "
            f"{'; '.join(mismatches)}. {action}"
        )


def _write_registry(registry_path: Path, sources: Sequence[RegisteredSource]) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "registryVersion": REGISTRY_VERSION,
        "sources": [
            source.to_dict() for source in sorted(sources, key=lambda item: item.source_id)
        ],
    }
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{registry_path.name}.",
        suffix=".tmp",
        dir=registry_path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, registry_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _same_registration(existing: RegisteredSource, candidate: RegisteredSource) -> bool:
    return replace(existing, processed_at=candidate.processed_at) == candidate


def _conflict_message(existing: RegisteredSource, candidate: RegisteredSource) -> str:
    context = (
        f"{candidate.input_path}: adapter {candidate.source_type} v{candidate.adapter_version}: "
        f"source ID {candidate.source_id!r}"
    )
    if existing.sha256 != candidate.sha256:
        return (
            f"{context} is already registered with different content "
            f"({existing.sha256} != {candidate.sha256})"
        )
    return f"{context} conflicts with the existing registration for {existing.input_path}"


def register_sources(
    paths: Sequence[str | Path],
    *,
    registry_path: Path,
    source_type: str,
    adapter_version: int = 1,
    source_id: str | None = None,
    upstream_version: str | None = None,
    license_status: str | None = None,
    processed_at: datetime | None = None,
) -> list[RegisteredSource]:
    if not paths:
        raise RegistrationError("At least one local Parquet path is required.")
    if source_id is not None and len(paths) != 1:
        raise RegistrationError("An explicit source ID can only be used with exactly one path.")
    explicit_source_id = _optional_text(source_id)
    if source_id is not None and explicit_source_id is None:
        raise RegistrationError("Source ID cannot be empty.")

    timestamp = _timestamp(processed_at)
    candidates: list[RegisteredSource] = []
    for supplied_path in paths:
        original_path = Path(supplied_path).expanduser()
        path = original_path.resolve()
        inspection = inspect_source(path, source_type, adapter_version)
        candidates.append(
            RegisteredSource(
                source_id=explicit_source_id or derive_source_id(source_type, original_path),
                source_type=source_type,
                input_path=str(path),
                original_filename=original_path.name,
                sha256=sha256_file(path),
                adapter_version=adapter_version,
                row_count=inspection.row_count,
                processed_at=timestamp,
                upstream_version=_optional_text(upstream_version),
                license_status=_optional_text(license_status) or "unknown",
            )
        )

    existing_sources = load_registered_sources(registry_path)
    sources_by_id = {source.source_id: source for source in existing_sources}
    results: list[RegisteredSource] = []
    changed = False
    for candidate in candidates:
        existing = sources_by_id.get(candidate.source_id)
        if existing is None:
            sources_by_id[candidate.source_id] = candidate
            results.append(candidate)
            changed = True
            continue

        if _same_registration(existing, candidate):
            results.append(existing)
            continue
        raise RegistrationError(_conflict_message(existing, candidate))

    if changed:
        _write_registry(registry_path, list(sources_by_id.values()))
    return results
