# User story workflow

Each story is an independently reviewable unit of work. Implement stories in dependency order and
do not silently expand their scope.

## Status values

- `ready`: sufficiently specified and not started.
- `in_progress`: implementation is actively underway.
- `blocked`: progress requires a recorded decision or external change.
- `complete`: every acceptance criterion and validation item is satisfied.

## Starting a story

1. Confirm all listed dependencies are complete.
2. Reconcile the story with the implemented repository, relevant decisions, and later learnings.
3. Change its status to `in_progress`.
4. Record any newly discovered scope conflict before changing an interface.

## Completing a story

Do not mark a story complete until its acceptance criteria pass. In the story's `Completion notes`
section, replace the placeholder with:

- completion date and pull request or commit;
- concise summary of the implementation;
- important deviations from the original plan and their decision record;
- commands and tests used for validation;
- follow-up work deliberately left out;
- new reusable lessons, also copied into [LEARNINGS.md](LEARNINGS.md).

Update the parent epic status after its last story is complete. Documentation and contract changes
are part of the story, not optional cleanup.

## Definition of done

- Acceptance criteria are demonstrably satisfied.
- Public contracts are versioned and documented.
- Automated tests cover expected behavior and relevant failure modes.
- No local reference data or unlicensed upstream data is newly tracked.
- Current-state documentation matches the implementation.
- Completion notes and applicable learning or decision records are present.
