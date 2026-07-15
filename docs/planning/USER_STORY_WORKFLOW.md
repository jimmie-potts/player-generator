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
3. For a change to a shared player, statistics, or attribute field or CSV-formatting rule, identify
   and include the corresponding reference and roster contract, fixture, validator, and
   documentation changes required by D-033.
4. Change its status to `in_progress`.
5. Record any newly discovered scope conflict before changing an interface.

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

## Pre-review adversarial contract pass

Before publishing a story that adds or changes a contract family, profile, schema, or alignment
ledger, perform a separate mutation-oriented review:

1. Test missing, extra, malformed, and wrong-typed values for every new declaration and sentinel.
2. Validate effective definitions after all profile constraints, overrides, and temporary gaps are
   composed, not only each declaration in isolation.
3. Exercise numeric boundaries on both sides of minimums and maximums, including exact-integer and
   IEEE-754 normalization boundaries where applicable.
4. Attempt to weaken key, relationship, requiredness, ordering, and inventory invariants through
   every override or gap mechanism.
5. Compare the family, both flat profiles, runtime validators, publishers, fixtures, and current-state
   documentation. Represent planned differences as exact gaps rather than copying future claims into
   current interfaces.
6. Have a reviewer that did not author the patch inspect the final unpushed diff and its mutation
   matrix before handoff.

## Pull-request handoff

A completed story, epic, or other logical unit is ready for publication without a separate user
prompt unless the user explicitly requests local-only work or says not to publish it.

1. Confirm the branch contains only the intended logical unit and all required validation passes.
2. Commit the intended files and push the working branch.
3. Open a pull request against the repository's default branch, or the user-specified base, with a
   clear summary, motivation, impact, and validation results.
4. Open the pull request ready for review. If the publishing path creates a draft, mark it ready
   before reporting the handoff complete.
5. Add the pull-request link to each applicable story's completion notes.

This handoff is non-blocking for local completion and story status. If authentication, network,
permissions, or another external dependency prevents publication, preserve the validated commits,
record and report the exact blocker, and retry once it clears. Do not revert a completed story to
`in_progress` solely because the remote handoff is temporarily unavailable.

## Pull-request review feedback

Treat each review thread as a traceable unit of follow-up work:

1. Confirm that the feedback is still applicable and identify the behavior or documentation it
   requires.
2. Implement and validate the fix, then push the resulting commit before changing the thread state.
3. When the pushed change fully addresses the feedback, reply in the thread with a brief summary of
   the fix and relevant validation, then resolve the thread.
4. Leave partially addressed, conflicting, or ambiguous feedback open and state the remaining work
   or decision instead of closing it prematurely.

## Definition of done

- Acceptance criteria are demonstrably satisfied.
- Public contracts are versioned and documented.
- Stories that change corresponding reference or roster player files satisfy D-033 and, once US-017
  delivers the automated parity checks, pass those checks.
- Automated tests cover expected behavior and relevant failure modes.
- No local reference data or unlicensed upstream data is newly tracked.
- Current-state documentation matches the implementation.
- Completion notes and applicable learning or decision records are present.
- The logical unit has a ready-for-review pull request, or its external publication blocker and
  validated branch are explicitly documented for retry.
