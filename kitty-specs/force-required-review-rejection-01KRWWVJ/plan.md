# Implementation Plan: Force-Required Review-Rejection Contract

**Branch**: `fix/events-32-force-required-wpstatuschanged`
**Date**: 2026-05-18
**Spec**: [spec.md](spec.md)
**Mission ID**: `01KRWWVJM6FSH9GW2GNC8VF1QW`
**Mission slug**: `force-required-review-rejection-01KRWWVJ`
**Final merge target**: `main` (per operator brief in `start-here.md` Phase 1; setup-plan recorded the planning base as the feature branch itself because the mission was created from the feature branch).

## Summary

Close the runtime/doc/fixture/test split for the WPStatusChanged
review-rejection family. Introduce an explicit family-guard inside
`validate_transition()` so unforced backward transitions into `planned`
from `in_progress`/`for_review`/`in_review`/`approved` always reject
with a violation message that names `force=True` as the missing element
— independent of whether `review_ref` or `reason` is supplied.
Strengthen `TestReviewRejectionFamily` and the conformance fixtures so
every family pair has both a "missing-force" INVALID fixture (with
`review_ref` and `reason` populated to isolate the cause) and a
"forced-and-reasoned" VALID fixture. Align the module docstring and the
consumer-contract dossier so they name the explicit family-guard as the
mechanism. Preserve bootstrap-planned semantics (`from_lane=None,
to_lane=planned, force=True`).

## Technical Context

**Language/Version**: Python 3.10+ (per `pyproject.toml`)
**Primary Dependencies**: Pydantic v2 (existing), no new third-party dependencies.
**Storage**: N/A — this package ships Pydantic models, JSON Schemas, and conformance fixtures; no runtime storage.
**Testing**: `pytest` with the existing `tests/unit/` suite, `hypothesis` where already in use, conformance-manifest consistency tests, `mypy --strict`.
**Target Platform**: Python library consumed by `spec-kitty` (CLI), `spec-kitty-saas` (materializer), and third parties.
**Project Type**: single Python package (`src/spec_kitty_events/`)
**Performance Goals**: `validate_transition()` remains O(1) per call; the family-guard is a small set membership check. No measurable performance regression on the existing 1000-event replay benchmarks.
**Constraints**: `validate_transition()` MUST remain a pure function; never raises on business-rule failure. Wire shape of `StatusTransitionPayload` MUST NOT change. Mission stays inside this repository — no SaaS or CLI changes here.
**Scale/Scope**: ~10 files touched: `status.py`, ~4 conformance fixture files, manifest, dossier doc, `test_status.py`, `test_fixtures.py`. ≤300 LOC delta expected.

## Charter Check

Charter loaded (mode: bootstrap). Relevant policy:

- **Intent**: "Publish canonical event envelopes, conformance fixtures, and compatibility rules consumed by Spec Kitty systems." → This mission is on-charter: it tightens a published validation rule and aligns docs/fixtures.
- **Quality gates**: `pytest`, committed schema generation checks, `mypy --strict` must pass before merge → captured in NFR-001/NFR-002/NFR-003 of the spec; reaffirmed below.
- **Review policy**: "Any change to event envelopes, payload fields, schema versioning, or conformance fixtures requires deliberate compatibility review." → The wire shape does not change (C-001) and the JSON Schemas regenerated from `StatusTransitionPayload` will be byte-equivalent. A compatibility note is added in the plan's release section.

**Action-specific directives**:
- DIRECTIVE_003 (Decision Documentation): the choice between "remove pairs from `_ALLOWED_TRANSITIONS`" and "keep pairs, add explicit family-guard" is documented in `research.md` with rationale.
- DIRECTIVE_010 (Specification Fidelity): every FR/NFR/C in the spec maps to a task or to an explicit acceptance check in this plan.

**Gate status**: PASS.

## Approach

### Single design decision (resolved in research.md)

Keep `_ALLOWED_TRANSITIONS` as-is (the four review-rejection pairs remain present) and add an explicit family-guard at the top of `validate_transition()` that fires before the matrix check whenever `force=False` and the pair is in the family. Rationale: the explicit guard is a single, code-greppable rule that produces a single, code-greppable violation string. Removing the pairs from the matrix would also reject unforced rollbacks, but the resulting violation would be the generic "transition X -> Y is not allowed" message rather than the `force=True` message that consumers need to act on. See `research.md` for trade-off detail.

### Touched files

| File                                                                                                            | Change                                                                                  |
|-----------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| `src/spec_kitty_events/status.py`                                                                                | Add `_REVIEW_REJECTION_FAMILY` frozenset; add `_is_review_rejection_pair()` predicate; add explicit guard in `validate_transition()`; update module docstring sections "Unforced backward transitions are contract-invalid" so it names the explicit guard rather than the matrix check. |
| `docs/consumer-contract-dossier-v2.4.0.md`                                                                       | Align wording in the "review-rejection family" and "unforced backward invalid" sections with the explicit-guard mechanism and the canonical violation substring. |
| `src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/wp_status_changed_unforced_in_review_to_planned.json` | Update payload so `review_ref` and `reason` ARE present (isolating "missing force" as the failure cause). Update expectation metadata to reference the new violation substring. |
| `src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/wp_status_changed_unforced_in_progress_to_planned.json` (new) | INVALID fixture for `in_progress -> planned` with `force=False`, `review_ref`/`reason` present. |
| `src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/wp_status_changed_unforced_for_review_to_planned.json` (new) | INVALID fixture for `for_review -> planned` with `force=False`, `review_ref`/`reason` present. |
| `src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/wp_status_changed_unforced_approved_to_planned.json` (new) | INVALID fixture for `approved -> planned` with `force=False`, `review_ref`/`reason` present. |
| `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_approved_rewind.json`             | Confirm fixture remains valid (force=True; reason; review_ref); minor metadata harmonization only. |
| `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_forced_in_review_to_planned.json` (new, if missing) | VALID fixture for `in_review -> planned` with `force=True`, reason, review_ref. |
| `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_forced_for_review_to_planned.json` (new, if missing) | VALID fixture for `for_review -> planned` with `force=True`, reason. |
| `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_forced_in_progress_to_planned.json` (new, if missing) | VALID fixture for `in_progress -> planned` with `force=True`, reason. |
| `src/spec_kitty_events/conformance/fixtures/manifest.json`                                                       | Register every added INVALID/VALID fixture; update expectations for the modified INVALID fixture. |
| `tests/unit/test_status.py` (`TestReviewRejectionFamily`)                                                        | Add parametrized test that asserts unforced rollback with full `review_ref` and `reason` still rejects, and the violation contains `force=True`; add parametrized test asserting forced rollback for all four pairs is accepted. |
| `tests/unit/test_fixtures.py` (`TestEdgeCaseFixtures`)                                                           | Cover the new INVALID/VALID fixtures via the existing replay/contract fixture tests. |

### Mechanics of the explicit family-guard

In `validate_transition()`, before the matrix check, evaluate:

- If `payload.force is False` AND `payload.from_lane is not None` AND `(payload.from_lane, payload.to_lane)` is in the family set, append a violation: `"review-rejection rollback {from} -> {to} requires force=True"`.
- This guard is checked regardless of whether `review_ref` or `reason` is populated. The existing `review_ref` guard and `reason` guard continue to fire independently for their own missing-field cases (R-4 / FR-002 says each violation names its own field).
- The bootstrap-planned transition is unaffected because `from_lane is None` short-circuits the guard.

### Out-of-scope reaffirmed

- No edit to `ReviewRollbackPayload`, mission-level lifecycle events, projection logic, SaaS materializer, drain classification, or CLI emit paths.
- No release/publish from this mission. A `5.1.0` → `5.1.1` version bump is left as a downstream operator decision (C-005); a release-notes block is drafted in `quickstart.md` but tagging is not part of this plan's work packages.

## Project Structure

### Documentation (this feature)

```
kitty-specs/force-required-review-rejection-01KRWWVJ/
├── plan.md              # This file
├── research.md          # Phase 0 output — design-decision record
├── data-model.md        # Phase 1 output — family predicate + result shape
├── quickstart.md        # Phase 1 output — reproduce, verify, release notes
├── contracts/           # Phase 1 output — validate_transition behavior contract
└── spec.md              # Authored by /spec-kitty.specify
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── status.py                                  # primary change point
└── conformance/
    └── fixtures/
        ├── manifest.json                       # updated to register new fixtures
        └── edge_cases/
            ├── invalid/                        # new + updated INVALID fixtures
            └── valid/                          # new + confirmed VALID fixtures

docs/
└── consumer-contract-dossier-v2.4.0.md         # wording alignment

tests/unit/
├── test_status.py                              # TestReviewRejectionFamily
└── test_fixtures.py                            # TestEdgeCaseFixtures
```

**Structure Decision**: Single Python package layout, unchanged. All edits land under the existing top-level directories.

## Risks & Premortem

| Risk                                                                                                         | Likelihood | Mitigation                                                                                       |
|--------------------------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------|
| Tightened validation rejects fixtures that previously passed in downstream replay corpora.                    | Medium     | The four affected pairs were already documented as requiring force=True; downstream replayers that produced unforced rollbacks were already producing contract-invalid events. NFR-002 + the conformance manifest check verify no existing committed fixtures regress. |
| Violation string changes break consumer-grep scripts.                                                         | Low        | The new substring is `force=True` (per FR-002), which is the canonical wording in dossier and module docstring. The existing `review_ref` and `reason` violation strings are preserved. |
| `mypy --strict` regression from frozenset typing of family set.                                               | Low        | Pattern is identical to existing `TERMINAL_LANES` / `_ALLOWED_TRANSITIONS` declarations; reuse the same typing. |
| Hidden coupling: SaaS or CLI tests assume the current (lenient) behavior.                                     | Out of scope | Spec C-004 declares SaaS materializer behavior unchanged. CLI emit-path is Phase 2 of operator brief. |
| Schema regeneration produces a churn diff.                                                                    | Low        | Wire shape is unchanged (C-001); committed schema generation should be byte-stable. CI's schema-drift check catches any unintended change. |

## Acceptance Mapping

| Spec ID  | Validated by                                                                                                  |
|----------|---------------------------------------------------------------------------------------------------------------|
| FR-001   | New parametrized test in `TestReviewRejectionFamily`; new INVALID fixtures per pair.                          |
| FR-002   | Test asserts violation list contains substring `force=True` AND `review-rejection`.                            |
| FR-003   | New parametrized test in `TestReviewRejectionFamily`; new VALID fixtures per pair (or existing where present). |
| FR-004   | Family set defined as exactly four ordered pairs; unit test enumerates them.                                   |
| FR-005   | Existing bootstrap test (preserved); new assertion that family predicate returns False for `from_lane=None`.   |
| FR-006   | Docstring + dossier edit; manifest-consistency test verifies dossier matches fixtures.                         |
| FR-007/8 | New INVALID + VALID fixtures registered in manifest; manifest-consistency test passes.                        |
| FR-009   | Manifest delta; existing manifest test passes.                                                                |
| FR-010/11| Tests added in `TestReviewRejectionFamily`.                                                                    |
| FR-012   | Existing replay-fixture tests continue to pass without modification beyond expectation metadata.               |
| NFR-001  | `pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q` exits 0.                                     |
| NFR-002  | Existing manifest-consistency tests exit 0.                                                                    |
| NFR-003  | `mypy --strict src/spec_kitty_events` exits 0.                                                                 |
| NFR-004  | Manual run of the reproduction snippet from `start-here.md` Phase 1; output documented in `quickstart.md`.     |
| NFR-005  | No `raise` added in `validate_transition()`; existing "never raises" test continues to pass.                   |
| NFR-006  | WP01 T006 runs the project schema-drift / schema-generation check; expected output is a byte-stable diff.       |
| C-001    | NFR-006 + WP01 T006 + lack of edit to `StatusTransitionPayload`.                                                |
| C-002    | WP01 T002 leaves `_ALLOWED_TRANSITIONS` unchanged; explicit family-guard runs before the matrix check.          |
| SC-1..SC-6 | Cross-referenced by all of the above.                                                                       |

## Release Note (drafted, not landed by this mission)

If the operator chooses to publish a patch:

> spec-kitty-events 5.1.1 — Force-Required Review-Rejection Contract
>
> `validate_transition()` now rejects unforced backward transitions from
> `in_progress`/`for_review`/`in_review`/`approved` to `planned` with a
> violation message naming `force=True`, even when `review_ref` and
> `reason` are supplied. The wire shape of `StatusTransitionPayload` is
> unchanged. Bootstrap transitions (`from_lane=None -> planned,
> force=True`) are unaffected. Conformance fixtures and module
> documentation were aligned to describe the explicit family-guard
> mechanism.

## Final branch reminder

- Current branch at plan completion: `fix/events-32-force-required-wpstatuschanged`
- Planning/base branch per `setup-plan --json`: `fix/events-32-force-required-wpstatuschanged`
- Final merge target per operator brief: `main`
- `branch_matches_target=true` for the planning record; merge into `main` is a downstream activity outside this mission's tasks.
