# Comparison reports

`comparison_report.json` is the machine-readable validation result. `comparison_table.csv` is a
compact per-rating table suitable for spreadsheets or CI summaries.

The starter run is considered a pass when distribution drift remains below configured review
thresholds and no roster-player name collides with the named reference snapshot.

These reports retain the current comparison contract under the roster-generator application.
Reporting for the normalized player-only package is not yet specified beyond the validation
requirements in the roster-package stories.
