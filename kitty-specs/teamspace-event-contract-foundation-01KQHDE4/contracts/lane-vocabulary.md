# Contract: Canonical Lane Vocabulary

**Mission**: `teamspace-event-contract-foundation-01KQHDE4`
**Source spec FRs**: FR-001, FR-002, C-002 · **Source data model**: [Lane Vocabulary](../data-model.md#lane-vocabulary)

## Rule

There is exactly one canonical lane vocabulary. It includes `in_review`. The contract package, the CLI, and the SaaS projector each reference the same constant and never define their own.

## Authoritative location

`src/spec_kitty_events/status.py` — the `Lane` enum is the single source of truth. Consumers import from `spec_kitty_events`.

## Vocabulary (this mission's release)

The full canonical lane list is the union of the existing `Lane` enum members in `src/spec_kitty_events/status.py` plus `in_review` if not already a member. The audit step in the work package will read the existing enum and produce a diff against this contract; any unintended divergence (e.g., a previously-removed lane that should be re-added) is surfaced for resolution.

`in_review` MUST be a member of the canonical vocabulary.

## Validation

- An envelope whose payload references a lane outside the canonical vocabulary is rejected with `ValidationError(code="UNKNOWN_LANE", path=..., details={"lane": "<value>"})`.
- An envelope whose payload references `in_review` is accepted (subject to all other invariants).

## Cross-package consistency check

`tests/test_lane_vocabulary.py` MUST include:

1. A test that imports the canonical `Lane` enum from `spec_kitty_events` and asserts membership of `in_review`.
2. A test that asserts the canonical lane set has not silently drifted (compare to a committed expected set).
3. (Cross-repo handshake) a fixture or test name that downstream tranches (CLI Tranche A, SaaS Tranche A) can reference to assert their own constants match.

## Forbidden patterns

- Defining a duplicate lane constant elsewhere in the codebase.
- Comparing lane values to string literals (e.g., `if lane == "in_review"`) at API boundaries; consumers should compare to `Lane.IN_REVIEW`.

## Versioning

Adding a new canonical lane is a contract change subject to the major-bump rule (see [versioning-and-compatibility.md](./versioning-and-compatibility.md)).
