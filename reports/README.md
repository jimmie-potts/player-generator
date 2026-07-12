# Comparison reports

`comparison_report.json` is the machine-readable validation result. `comparison_table.csv` is a
compact per-rating table suitable for spreadsheets or CI summaries.

The starter run is considered a pass when distribution drift remains below configured review
thresholds and no generated name collides with the named reference snapshot.
