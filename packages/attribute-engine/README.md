# Attribute-engine package

This Python package owns the shared version 1 percentile, interpolation, and player-rating
calculations. The reference-data application uses it to rate canonical player-season rows.

US-006 will replace the hard-coded formula definitions with a declarative, versioned formula
contract. Until then, moving the current formulas here changes ownership without changing their
behavior.
