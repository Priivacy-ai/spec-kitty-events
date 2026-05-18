# Specification: Force-Required Review-Rejection Contract

**Mission**: `force-required-review-rejection-01KRWWVJ`
**Mission ID**: `01KRWWVJM6FSH9GW2GNC8VF1QW`
**Type**: software-dev
**Target branch**: `main`
**Tracker issues**: `spec-kitty-events#32`, `#29` (resolved-by), `#31` (superseded-by)

## Purpose

### TLDR

Make every layer of `spec-kitty-events` agree that the WPStatusChanged review-rejection family requires `force=True`.

### Context

Today the runtime contradicts the docs. The module docstring, the consumer
contract dossier, the conformance manifest, and the unit-test class name all
state that backward transitions out of the review lanes (`in_progress`,
`for_review`, `in_review`, `approved`) into `planned` require
`force=True`. The runtime `validate_transition()` does not enforce that:
because the same pairs are present in `_ALLOWED_TRANSITIONS`, the matrix
check accepts them when `force=False`. The only thing that currently
rejects an unforced rollback is the `review_ref` guard, which fires only
when `review_ref` is missing. An emitter who supplies a `review_ref` (or a
fuzzer that does) gets a "valid" result for an unforced rollback and the
contract silently degrades.

That silent degradation is what tracker `spec-kitty-events#32` exists to
close. Issue `#29` cannot be closed until `#32` is closed, because its
"consumers must not have to infer" acceptance criterion is unmet while the
runtime accepts the inferred shape. Issue `#31` is the original
investigation report; once the contract is unambiguous, `#31` is
superseded by `#32`.

## User Scenarios & Testing

### Primary Actor

A producer of WPStatusChanged events. In practice this is the
`spec-kitty` CLI emit path, the `spec-kitty-saas` materializer when
replaying historical events, and any third-party consumer building on
the published Pydantic models.

### Primary Scenario (happy path)

1. A reviewer rejects work-package `WP01` of mission `m` from the
   `in_review` lane back to `planned`.
2. The producer constructs a `StatusTransitionPayload` with
   `from_lane=in_review`, `to_lane=planned`, `force=True`, a non-empty
   `reason`, and (recommended) a `review_ref` pointer.
3. `validate_transition(payload)` returns `valid=True`.
4. Downstream materializers project the lane change as a business event,
   not as an infrastructure failure.

### Primary Exception (the bug we are closing)

1. A producer constructs the same payload but forgets `force=True`,
   keeping `force=False`. They do supply `review_ref="feedback://m/WP01/r.md"`
   and a `reason`.
2. Today: `validate_transition(payload)` returns `valid=True`. This is
   the contract violation.
3. After this mission: `validate_transition(payload)` returns
   `valid=False` and the violation message explicitly names `force=True`
   as the missing element, not `review_ref` and not `reason`.

### Secondary Scenario: bootstrap planned

1. A producer constructs a payload with `from_lane=None`,
   `to_lane=planned`, `force=True`, and a non-empty `reason`.
2. This is the bootstrap transition that creates a new WP at the
   `planned` lane. It MUST continue to be accepted.
3. The review-rejection family predicate MUST NOT classify
   `from_lane=None -> planned` as a rejection, regardless of `force`.

### Edge Cases

- A payload with `force=False` and a review-rejection pair but no
  `review_ref` and no `reason` still rejects, and the violation set
  explicitly includes the missing-`force` violation alongside any other
  applicable violations.
- A payload with `force=True`, a review-rejection pair, a non-empty
  `reason`, and a `review_ref` is accepted.
- A payload with `force=True`, a review-rejection pair, and a non-empty
  `reason` but no `review_ref` is accepted. The force-required
  review-rejection family treats `review_ref` as recommended, not
  required, when `force=True`.
- Replay fixtures that include the documented "approved rewind"
  scenario continue to load and validate.

## Domain Language

| Canonical term                  | Meaning                                                                                                                                                | Avoid                                |
|---------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| review-rejection family         | The four ordered lane pairs `in_progress -> planned`, `for_review -> planned`, `in_review -> planned`, `approved -> planned`.                          | "rewind family", "rollback set"      |
| forced backward transition      | A WPStatusChanged event whose `from_lane -> to_lane` is in the review-rejection family AND whose `force=True`.                                          | "review rewind" without `force` qualifier |
| unforced backward transition    | A WPStatusChanged event whose `from_lane -> to_lane` is in the review-rejection family but whose `force=False`. Contract-invalid.                       | "soft rewind"                        |
| bootstrap-planned transition    | A WPStatusChanged event with `from_lane=None, to_lane=planned, force=True`. Not a rejection.                                                            | "initial rewind"                     |
| explicit family-guard           | A `validate_transition()` predicate that rejects unforced backward transitions BEFORE the matrix check, with a violation message that names `force=True`.| "matrix check"                       |

## Functional Requirements

| ID      | Description                                                                                                                                                                                              | Status   |
|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-001  | `validate_transition()` MUST reject every payload whose `(from_lane, to_lane)` is in the review-rejection family AND whose `force` is `False`, regardless of whether `review_ref` and `reason` are populated. | Required |
| FR-002  | The violation produced by FR-001 MUST be a single, distinct, machine-greppable string that explicitly names `force=True` as the missing element. The required substring is `force=True` and the family name (`review-rejection`). | Required |
| FR-003  | `validate_transition()` MUST accept every payload whose `(from_lane, to_lane)` is in the review-rejection family, whose `force` is `True`, and whose `reason` is non-empty. `review_ref` is optional/recommended for these forced family members. | Required |
| FR-004  | The review-rejection family predicate MUST treat exactly these four pairs as family members: `in_progress -> planned`, `for_review -> planned`, `in_review -> planned`, `approved -> planned`. No others.   | Required |
| FR-005  | The bootstrap-planned transition (`from_lane=None, to_lane=planned, force=True`) MUST continue to validate as before. It MUST NOT be classified as a review-rejection.                                       | Required |
| FR-006  | The module docstring of `status.py` and the consumer-contract dossier MUST describe the contract in one consistent way: family enumerated, `force=True` required, and the enforcement mechanism named (explicit family-guard, not "via the lane matrix check"). | Required |
| FR-007  | The conformance fixture set MUST contain at least one INVALID fixture per family pair where the failure mode is unambiguously "missing `force=True`" (review_ref and reason supplied). | Required |
| FR-008  | The conformance fixture set MUST contain at least one VALID fixture per family pair where `force=True` and `reason` are supplied (review_ref may be supplied or omitted as documented). | Required |
| FR-009  | The conformance manifest MUST register every added/changed fixture with the correct category (`valid`/`invalid`/`replay`) and the correct expectation metadata.                                            | Required |
| FR-010  | `TestReviewRejectionFamily` MUST contain at least one parametrized test that asserts FR-001 with a fully populated `review_ref` and `reason`, proving the rejection is driven by the missing `force=True` and not by missing siblings. | Required |
| FR-011  | `TestReviewRejectionFamily` MUST contain at least one parametrized test that asserts FR-003 across all four family pairs.                                                                                  | Required |
| FR-012  | Replay-fixture tests that exercise the approved-rewind cycle MUST continue to pass, demonstrating no regression to existing valid forced rewinds.                                                          | Required |

## Non-Functional Requirements

| ID       | Description                                                                                                                                                                                 | Threshold                                                                 | Status   |
|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|----------|
| NFR-001  | The full unit-test suite that exercises `status.py` and the fixture loader MUST pass with the changes in place.                                                                              | `pytest tests/unit/test_status.py tests/unit/test_fixtures.py` exits 0.   | Required |
| NFR-002  | The conformance fixture set MUST remain manifest-consistent (every referenced file exists, every existing file is referenced, expectation metadata matches the fixture body).                  | Existing manifest-consistency tests exit 0.                               | Required |
| NFR-003  | Type checking MUST remain strict-clean.                                                                                                                                                       | `mypy --strict src/spec_kitty_events` exits 0.                            | Required |
| NFR-004  | The reproduction snippet in `start-here.md` Phase 1 MUST print `False` and a violation that contains the substring `force=True` after the fix.                                                | Manual run prints `False` + violation containing `force=True`.            | Required |
| NFR-005  | `validate_transition()` MUST remain a pure function that never raises for business-rule violations. The new family guard MUST append to `violations` and not raise.                            | Existing "never raises" tests exit 0; behavior unchanged for valid inputs.| Required |
| NFR-006  | The committed JSON Schema for `StatusTransitionPayload` MUST remain byte-stable across this mission, demonstrating that no wire-shape change leaked in.                                          | Project's schema-generation / schema-drift check exits 0 with no diff.    | Required |

## Constraints

| ID    | Description                                                                                                                                       | Status   |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| C-001 | The wire shape of `StatusTransitionPayload` MUST NOT change. No new required fields, no removed fields, no renamed fields.                          | Required |
| C-002 | The existing `_ALLOWED_TRANSITIONS` matrix MAY be edited only if doing so keeps every assertion in the existing test suite coherent. If kept, the explicit family-guard is authoritative and runs before the matrix check. | Required |
| C-003 | No change to `ReviewRollbackPayload` (mission-level event) is in scope. This mission concerns per-WP `WPStatusChanged` validation only.              | Required |
| C-004 | No change to SaaS materializer behavior, drain classification, or projection logic is in scope. SaaS already classifies these as business-rule rejections. | Required |
| C-005 | The package version SHOULD be bumped from `5.1.0` to `5.1.1` only if downstream consumers (the CLI) need to depend on the corrected behavior via a pinned dependency. Tag/publish only after CI passes. Version bump itself is optional within this mission. | Optional |

## Rules and Invariants

- **R-1 (fail-closed)**: An unforced backward transition in the review-rejection family is contract-invalid. The runtime, the documentation, the fixtures, and the test suite must agree on that fact and on which field is the missing one.
- **R-2 (single owner of the truth)**: The explicit family-guard in `validate_transition()` is the authoritative enforcement point. Documentation may not point at the matrix check as the mechanism unless the matrix check is the literal mechanism in code.
- **R-3 (bootstrap preserved)**: `from_lane=None -> planned, force=True` is never a review-rejection.
- **R-4 (no inference)**: A consumer reading the violation list MUST NOT have to infer whether the missing field is `force`, `review_ref`, or `reason`. Each missing-field violation names its own field.

## Success Criteria

- **SC-1**: After this mission, the reproduction snippet from `start-here.md` Phase 1 prints `False` and a violation message containing the substring `force=True`. The failure does not depend on omitting `review_ref`.
- **SC-2**: A consumer reading the published documentation and the conformance fixtures can determine, without reading runtime source, that an unforced backward transition into `planned` from any of `in_progress`/`for_review`/`in_review`/`approved` is invalid because `force` is missing.
- **SC-3**: Tracker `spec-kitty-events#32` is closable from this evidence alone. Tracker `#29` is closable as a downstream consequence. Tracker `#31` is closable as superseded.
- **SC-4**: The targeted test command `pytest tests/unit/test_status.py::TestReviewRejectionFamily tests/unit/test_fixtures.py::TestEdgeCaseFixtures -q` exits 0.
- **SC-5**: The broader command `pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q` exits 0, demonstrating no regression.
- **SC-6**: 100% of the four review-rejection family pairs have at least one INVALID-with-missing-force fixture and at least one VALID-with-force fixture registered in the conformance manifest.

## Key Entities

- **`StatusTransitionPayload`** (`src/spec_kitty_events/status.py`): the Pydantic model whose validation is being tightened. Wire shape unchanged.
- **`TransitionValidationResult`** (`src/spec_kitty_events/status.py`): the dataclass returned by `validate_transition()`. Carries `valid` and `violations`. Shape unchanged; populated more strictly.
- **`_ALLOWED_TRANSITIONS`** (`src/spec_kitty_events/status.py`): the matrix of permitted unforced transitions. The four review-rejection pairs may stay or be removed; the explicit guard is authoritative either way.
- **Review-rejection family predicate** (new internal helper in `status.py`): pure function that decides whether `(from_lane, to_lane)` is one of the four family pairs.
- **Conformance fixtures** (`src/spec_kitty_events/conformance/fixtures/...`): the canonical published examples. INVALID and VALID examples for each family pair.
- **Conformance manifest** (`src/spec_kitty_events/conformance/fixtures/manifest.json`): the index of fixtures and their expectations. Must stay in sync with file changes.
- **`TestReviewRejectionFamily`** and **`TestEdgeCaseFixtures`**: the unit tests that pin the runtime to the contract.

## Out of Scope

- Changes to `ReviewRollbackPayload` or any mission-level (non-WP) lifecycle event.
- Changes to the SaaS materializer, projection engine, or drain classification.
- Changes to CLI emit-path behavior in `spec-kitty` itself. The CLI is expected to either pre-validate or set `force=True` and a canonical `reason`; that work is `Phase 2` of the operator brief and a separate repository.
- Re-opening the force-required vs force-optional debate.
- Wire-shape changes to `StatusTransitionPayload`.
- Auto-promotion logic (silent `force=True` injection by the validator). The validator stays a pure checker.

## Assumptions

- The existing model validator that enforces `force=True requires a non-empty reason` remains active. The new family guard does not duplicate that check.
- The `review_ref` shape `feedback://<mission>/<wp>/<artifact>.md` remains recommended-but-not-mandatory when `force=True`.
- Consumers reduce both `ReviewRollback` (mission-level) and per-WP `WPStatusChanged` event streams; this mission does not change that reducer contract.
- Releasing a new patch version of the package is optional within this mission. A version bump is treated as a deployment activity, not a spec requirement.
- The charter recommends `hypothesis` for event-contract changes. This mission uses `pytest.mark.parametrize` instead because the review-rejection family is a fixed 4-element enumeration; parametrizing over it is exhaustive and deterministic, whereas hypothesis would only re-discover the same four pairs. No property-based shrinker would surface a missed case. If a future mission widens the family, hypothesis becomes appropriate.

## Dependencies

- Pydantic v2 models in `status.py`, `lifecycle.py`.
- Existing conformance manifest format and loader at
  `src/spec_kitty_events/conformance/`.
- Existing test infrastructure (`pytest`, `tests/unit/test_status.py`,
  `tests/unit/test_fixtures.py`).
- No new third-party dependencies introduced.

## Related Trackers

- `Priivacy-ai/spec-kitty-events#32` — authoritative no-history-rewrite WPStatusChanged doctrine reconciliation (the one this mission closes).
- `Priivacy-ai/spec-kitty-events#29` — original WPStatusChanged rewind/force/reconciliation contract (closable once `#32` lands).
- `Priivacy-ai/spec-kitty-events#31` — original reconciliation report with incorrect provenance (closable as superseded by `#32`).
