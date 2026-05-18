# Behavior Contract: `validate_transition()` after this mission

**Module**: `src/spec_kitty_events/status.py`
**Signature** (unchanged): `validate_transition(payload: StatusTransitionPayload) -> TransitionValidationResult`

## Pre-conditions

- `payload` is a fully-constructed `StatusTransitionPayload`. (Pydantic
  construction has already enforced field types and the
  `force=True requires reason` model-level rule.)

## Post-conditions

The function returns `TransitionValidationResult(valid, violations)` where:

1. **Pure**: No exception raised under any input that successfully
   constructed as a `StatusTransitionPayload`.
2. **Deterministic**: Two calls with equal payloads return equal
   results.
3. **Idempotent**: Side-effect-free.

The `violations` tuple contains zero or more violation strings drawn
from the union of:

- Existing strings (terminal-lane, matrix, review_ref, reason guards).
- The new family-guard string: `"review-rejection rollback {from} -> {to} requires force=True"`.

## Decision table

| Pair `(from, to)`              | `force` | `reason`         | `review_ref`     | Expected `valid` | New-guard violation present? |
|--------------------------------|---------|------------------|------------------|------------------|------------------------------|
| `(in_review, planned)`         | False   | "..."            | "feedback://..." | False            | YES (this mission's contract) |
| `(in_review, planned)`         | False   | None             | "feedback://..." | False            | YES                          |
| `(in_review, planned)`         | False   | "..."            | None             | False            | YES                          |
| `(in_review, planned)`         | True    | "..."            | "feedback://..." | True             | NO                           |
| `(in_review, planned)`         | True    | "..."            | None             | True             | NO                           |
| `(for_review, planned)`        | False   | "..."            | "..."            | False            | YES                          |
| `(in_progress, planned)`       | False   | "..."            | "..."            | False            | YES                          |
| `(approved, planned)`          | False   | "..."            | "..."            | False            | YES                          |
| `(None, planned)`              | True    | "..."            | None             | True             | NO (bootstrap)               |
| `(claimed, in_progress)`       | False   | None             | None             | True             | NO (forward)                 |
| `(planned, claimed)`           | False   | None             | None             | True             | NO (forward)                 |

## Violation message contract

For any unforced backward transition in the family, the violations
tuple MUST contain at least one string that satisfies all three of:

- contains the literal substring `force=True`
- contains the literal substring `review-rejection`
- contains the literal substring of the `from_lane` value (e.g. `in_review`)

Consumers MAY route on either substring. Either substring is part of
the public contract for this mission.

## Compatibility

- The function signature is unchanged.
- The wire shape of `StatusTransitionPayload` is unchanged.
- The wire shape of `TransitionValidationResult` is unchanged.
- The set of triggerable violation strings GROWS by one. Consumers that
  perform exact-match comparison on the historic set of violations MUST
  be aware of the new string. Consumers that perform substring search
  (`"force=True" in v` etc.) are unaffected.

## Performance contract

- `validate_transition()` performs O(1) work. The family-guard adds one
  set-membership test against a 4-element frozen set; no measurable
  regression in replay benchmarks.
