# Data boundaries

The project treats named reference data and fictional game data as different trust zones.

## Reference zone

Path: `reference_data/`

Allowed contents:

- Source player IDs and names.
- Historical team names and abbreviations.
- Raw and aggregate statistics.
- Derived ratings associated with real players.
- Source manifests and checksums.

Rules:

- Keep local by default.
- Do not load from the game client or production server.
- Do not copy source IDs or names into generated output.
- Refresh intentionally and review source provenance.

## Generated zone

Path: `generated_data/`

Allowed contents:

- Fictional player and team names.
- Synthetic ratings and development values.
- Fictional roster assignments.
- Generation metadata such as schema version and seed.

Forbidden contents:

- `personId`, `sourcePlayerId`, `sourcePlayerName` or source-row indexes.
- NBA team abbreviations or source team names.
- A real-to-fictional player crosswalk.

## Reports zone

Path: `reports/`

Reports compare populations rather than identities. They may contain aggregated reference values,
but should not contain direct mappings between named and fictional players.
