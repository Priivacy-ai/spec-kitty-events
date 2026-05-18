# Phase 1 — Data Model: Force-Required Review-Rejection Contract

This mission introduces no new public types. It introduces one private
constant and one private predicate inside
`src/spec_kitty_events/status.py`, and tightens the behavior of an
existing public function. Public Pydantic models are unchanged.

## Public surface (unchanged)

### `StatusTransitionPayload`

Existing Pydantic model. Wire shape unchanged.

- Required fields: `mission_slug`, `wp_id`, `to_lane`, `actor`, `execution_mode`, `force`.
- Optional fields relevant to this mission: `from_lane`, `reason`, `review_ref`, `evidence`.
- Existing model-level validator (`_check_business_rules`):
  - `force=True` requires non-empty `reason`.
  - `to_lane in {APPROVED, DONE}` requires `evidence`.

This mission does not alter `_check_business_rules`.

### `TransitionValidationResult`

Existing frozen dataclass. Shape unchanged.

- `valid: bool`
- `violations: Tuple[str, ...]`

This mission appends one new possible violation string into
`violations` (see "Violations" below).

### `validate_transition(payload) -> TransitionValidationResult`

Existing public function. Behavior tightened:

- Pure function. Never raises on business-rule violations.
- New step inserted at the top of the function (after the terminal-lane
  check), evaluating the explicit family-guard before the matrix check.

## Private additions (new)

### `_REVIEW_REJECTION_FAMILY`

A `FrozenSet[Tuple[Lane, Lane]]` declared adjacent to `_ALLOWED_TRANSITIONS`. Members:

| from_lane     | to_lane |
|---------------|---------|
| `IN_PROGRESS` | `PLANNED` |
| `FOR_REVIEW`  | `PLANNED` |
| `IN_REVIEW`   | `PLANNED` |
| `APPROVED`    | `PLANNED` |

Exactly four ordered pairs. No more, no fewer.

### `_is_review_rejection_pair(from_lane: Optional[Lane], to_lane: Lane) -> bool`

Pure predicate. Returns `True` iff `from_lane is not None` and
`(from_lane, to_lane) in _REVIEW_REJECTION_FAMILY`.

Bootstrap-planned (`from_lane=None`) returns `False`.

## Violations

### Existing violation strings (unchanged)

- `"{lane} is terminal; requires force=True to exit"` (terminal-lane guard)
- `"Transition {from} -> {to} is not allowed"` (matrix guard)
- `"{from} -> {to} requires review_ref"` (review_ref guard)
- `"in_progress -> planned requires reason"` (reason guard)
- `"force=True requires a non-empty reason"` (model-level, raised at construct time)

### New violation string (this mission)

- `"review-rejection rollback {from} -> {to} requires force=True"`

Where `{from}` is the literal `Lane` value (e.g. `in_review`) and
`{to}` is `planned`. The substring `force=True` and the substring
`review-rejection` are both guaranteed by FR-002.

## Invariants

- **I-1**: For any payload P, `validate_transition(P)` returns a
  `TransitionValidationResult` and never raises.
- **I-2**: For any payload P where `_is_review_rejection_pair(P.from_lane, P.to_lane)` is True
  and `P.force is False`, the new violation string appears in
  `validate_transition(P).violations`, regardless of `P.review_ref` and
  `P.reason`.
- **I-3**: For any payload P where `_is_review_rejection_pair(P.from_lane, P.to_lane)` is True
  and `P.force is True` and `P.reason` is non-empty, the new violation
  string does NOT appear in `validate_transition(P).violations`.
- **I-4**: For any payload P where `P.from_lane is None`, the new
  violation string never appears.
- **I-5**: Existing violation strings remain triggerable; they are not
  consumed or suppressed by the new guard.

## State transitions

Lane state machine unchanged. The only behavioral change is in
**which** events `validate_transition()` accepts as valid for transitions
already enumerated in the state machine.

## Conformance fixture surface

Each fixture file in
`src/spec_kitty_events/conformance/fixtures/edge_cases/` is a JSON
document conforming to the existing fixture schema. The manifest at
`src/spec_kitty_events/conformance/fixtures/manifest.json` indexes
each file with its category, expected validity, and (for invalid
fixtures) the expected violation substring.

New / updated fixture metadata MUST include the substring
`force=True` in the `expected_violations` field for the four new
INVALID fixtures. The replay-fixture cycle file
(`wp_review_rejection_cycle.jsonl`) MUST continue to validate end-to-end
because every transition in the canonical cycle already carries
`force=True`.
