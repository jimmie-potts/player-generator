# Third-party notices

The software in this repository is MIT licensed. That license does not grant rights to third-party
data. Local named reference data is intentionally separated from roster output.

## llimllib/nba_data

- Repository: <https://github.com/llimllib/nba_data>
- Pinned commit: `a7bc98d73324300bd28d77260f45c98c239d1e87`
- Used file: `data/playerstats.parquet` (2,433,415 bytes)
- Used fields: regular-season totals, per-game, per-36, per-100, advanced, shooting and bio fields
- License status: no root license file was observed when this snapshot was selected
- Local use only: rating calibration and roster generation

Do not commit or redistribute the downloaded Parquet file or derived named reference tables. Users
must obtain the pinned input themselves through the project downloader.

## NBA-Data-2010-2024 validation source

- Repository: <https://github.com/NocturneBear/NBA-Data-2010-2024>
- Repository-declared license: MIT
- Use: optional manual cross-check of traditional box-score distributions
- Normal pipeline: not downloaded or ingested

The previous `Brescou/NBA-dataset-stats-player-team` dependency has been removed. ESPN analytics
files are not used by the current implementation. They are planned as a separate local-file adapter
in version 2.

The source manifest records the exact pinned URL, SHA-256 hash and file size. Review upstream terms
and provenance before using any third-party data.
