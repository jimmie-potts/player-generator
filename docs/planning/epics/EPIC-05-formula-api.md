# EPIC-05: Formula preview API

- **Status:** ready
- **Outcome:** Expose read-only formula inspection and temporary recalculation through a Python API.
- **Dependencies:** EPIC-02, EPIC-03

## Story

- [US-010: Provide formula and player preview endpoints](../user-stories/US-010-formula-preview-api.md)

## Success criteria

- The API serves formulas, metric metadata, searchable players, and baseline results.
- Preview requests return validated deltas and calculation breakdowns without persistent writes.
- A bounded in-memory data set provides responsive recalculation.
- The API invokes the shared formula engine rather than reimplementing calculations.

## Non-goals

- Authentication, multi-user persistence, or production hosting.
- Writing formula configuration or source data.

## Risks

- Large reference frames can make interactive previews slow.
- API response shapes can duplicate contract definitions if they are not versioned centrally.
