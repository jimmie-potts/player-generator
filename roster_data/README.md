# Roster output

Generated player-only packages are written to the ignored
`roster_data/packages/roster-v1/` directory by default. Each package contains:

- `players.csv`
- `player_stats.csv`
- `player_advanced_stats.csv`
- `player_attributes.csv`
- `manifest.json`

The four CSVs share stable generated `playerId` values. The manifest pins roster contract version
1, the reference-package content hash, formula version and document hash, seed, semantic
configuration hash, row counts, per-file hashes, and aggregate content hash.

No source player or team identity, source-row index, template identifier, or source-to-roster
crosswalk may appear here. Regenerate the package with `roster-generator generate`; do not hand-edit
its files.
