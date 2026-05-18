# Tasks: Force-Required Review-Rejection Contract

**Mission**: `force-required-review-rejection-01KRWWVJ`
**Mission ID**: `01KRWWVJM6FSH9GW2GNC8VF1QW`
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)
**Planning base branch**: `main`
**Final merge target**: `main`
**Current branch**: `fix/events-32-force-required-wpstatuschanged`

This mission is intentionally scoped to two independently
executable work packages. WP01 lands the runtime guard plus unit
tests; WP02 lands the conformance fixtures, manifest, dossier
documentation, and fixture-level tests. The two WPs touch
disjoint owned-files sets and can be implemented in parallel by
two agents, but WP02's fixture-level tests will most naturally
pass only once WP01 has landed the new validation behavior; the
intended sequence is WP01 → WP02 to keep the test signal clean.

## Subtask Index

| ID    | Description                                                                                             | WP   | Parallel |
|-------|---------------------------------------------------------------------------------------------------------|------|----------|
| T001  | Add `_REVIEW_REJECTION_FAMILY` constant and `_is_review_rejection_pair()` predicate in `status.py`      | WP01 |          |
| T002  | Insert explicit family-guard at the top of `validate_transition()` (runs before the matrix check)       | WP01 |          |
| T003  | Update `status.py` module docstring "Unforced backward transitions are contract-invalid" wording        | WP01 | [P]      |
| T004  | Strengthen `TestReviewRejectionFamily`: parametrized "missing-force" test with populated `review_ref` + `reason` | WP01 |          |
| T005  | Add parametrized "forced-rollback accepted" + "bootstrap-planned unaffected" tests                       | WP01 |          |
| T006  | Run `pytest tests/unit/test_status.py -q`, `mypy --strict src/spec_kitty_events`, AND the committed schema-drift check (NFR-006 / C-001); all exit 0 with no diff | WP01 |          |
| T007  | Update existing `wp_status_changed_unforced_in_review_to_planned.json` to populate `review_ref` + `reason` (isolate cause) | WP02 | [P]      |
| T008  | Create three new INVALID fixtures: `wp_status_changed_unforced_in_progress_to_planned.json`, `..._for_review_to_planned.json`, `..._approved_to_planned.json` | WP02 | [P]      |
| T009  | Create up-to-three new VALID fixtures for any family pair not already covered (in_progress, for_review, in_review forced rollbacks) | WP02 | [P]      |
| T010  | Update `src/spec_kitty_events/conformance/fixtures/manifest.json` to register every added/changed fixture with correct `expected_violations` substrings | WP02 |          |
| T011  | Align `docs/consumer-contract-dossier-v2.4.0.md` sections (review-rejection family + unforced backward invalid) with explicit family-guard mechanism | WP02 | [P]      |
| T012  | Extend `TestEdgeCaseFixtures` in `tests/unit/test_fixtures.py` to verify the new INVALID/VALID fixtures load and validate as expected | WP02 |          |
| T013  | Run targeted + broad pytest commands and the `start-here.md` reproduction snippet; record output in commit notes | WP02 |          |

## Work Packages

### WP01 — Runtime family-guard + unit tests

**Goal**: Tighten `validate_transition()` so unforced backward transitions in the
review-rejection family are rejected with a violation message that explicitly
names `force=True`, regardless of whether `review_ref` and `reason` are
populated. Strengthen `TestReviewRejectionFamily` so the new behavior is
pinned by tests that cannot pass under the current lenient runtime.

**Priority**: P0 (MVP).
**Estimated size**: ~350 lines of prompt, 6 subtasks.
**Owned files**:

- `src/spec_kitty_events/status.py`
- `tests/unit/test_status.py`

**Authoritative surface**: `src/spec_kitty_events/`

**Independent test**: From the repository root —

```bash
uv run pytest tests/unit/test_status.py::TestReviewRejectionFamily -q
uv run mypy --strict src/spec_kitty_events
```

**Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-010, FR-011, NFR-001 (partial), NFR-003, NFR-005, NFR-006, C-001, C-002, R-1..R-4.

**Included subtasks**:

- [ ] T001 Add `_REVIEW_REJECTION_FAMILY` and `_is_review_rejection_pair()` (WP01)
- [ ] T002 Insert explicit family-guard in `validate_transition()` (WP01)
- [ ] T003 Update module docstring enforcement-mechanism wording (WP01)
- [ ] T004 Add parametrized "missing-force isolated" test (WP01)
- [ ] T005 Add parametrized "forced rollback accepted" + bootstrap-planned tests (WP01)
- [ ] T006 Run unit tests + mypy and report (WP01)

**Implementation sketch**:

1. Define `_REVIEW_REJECTION_FAMILY: FrozenSet[Tuple[Lane, Lane]]` adjacent to `_ALLOWED_TRANSITIONS`, with exactly the four pairs.
2. Add `_is_review_rejection_pair(from_lane, to_lane)` returning `False` when `from_lane is None`.
3. In `validate_transition()`, immediately after the terminal-lane check and BEFORE the matrix check, append `"review-rejection rollback {from} -> {to} requires force=True"` to `violations` when `not payload.force` and `_is_review_rejection_pair(...)`.
4. Update the module docstring so the "Unforced backward transitions are contract-invalid" paragraph names the explicit family-guard rather than the matrix check.
5. In `TestReviewRejectionFamily`, parametrize over the four pairs with both `review_ref` and `reason` populated; assert `valid is False` and the violation list contains a string with both substrings `force=True` and `review-rejection`.
6. Parametrize a "forced rollback accepted" test over the four pairs; add an explicit `from_lane=None -> planned, force=True` assertion that still validates and that `_is_review_rejection_pair(None, planned)` returns `False`.

**Dependencies**: None.
**Parallel opportunities**: T003 (docstring) is `[P]` and can happen any time during the WP; T004/T005 must follow T002.
**Risks**: see plan §"Risks & Premortem". Mitigations are in this WP's prompt.

---

### WP02 — Conformance fixtures, manifest, dossier doc, fixture tests

**Goal**: Update the published conformance surface so every family pair has
an INVALID fixture that isolates "missing `force=True`" as the failure cause
and a VALID fixture that proves forced rollback is accepted. Align the
consumer-contract dossier wording with the explicit family-guard mechanism.
Cover the new fixtures with `TestEdgeCaseFixtures`.

**Priority**: P0 (MVP). Sequenced AFTER WP01 lands so that fixture-level
assertions match runtime behavior.
**Estimated size**: ~400 lines of prompt, 7 subtasks.
**Owned files**:

- `src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/wp_status_changed_unforced_*.json`
- `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_forced_*.json`
- `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/wp_status_changed_approved_rewind.json`
- `src/spec_kitty_events/conformance/fixtures/manifest.json`
- `docs/consumer-contract-dossier-v2.4.0.md`
- `tests/unit/test_fixtures.py`

**Authoritative surface**: `src/spec_kitty_events/conformance/fixtures/`

**Independent test**: From the repository root —

```bash
uv run pytest \
  tests/unit/test_fixtures.py::TestEdgeCaseFixtures \
  tests/unit/test_status.py::TestReviewRejectionFamily -q
uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q
```

**Requirements**: FR-006, FR-007, FR-008, FR-009, FR-012, NFR-001, NFR-002, NFR-004, SC-1, SC-2, SC-6.

**Included subtasks**:

- [ ] T007 Update existing `unforced_in_review_to_planned` fixture to isolate cause (WP02)
- [ ] T008 Create three new INVALID fixtures, one per remaining family pair (WP02)
- [ ] T009 Create up-to-three new VALID fixtures for uncovered pairs (WP02)
- [ ] T010 Update manifest to register new/changed fixtures and expected violation substrings (WP02)
- [ ] T011 Update dossier doc to name the explicit family-guard mechanism (WP02)
- [ ] T012 Extend `TestEdgeCaseFixtures` to cover the new fixtures (WP02)
- [ ] T013 Run targeted + broad pytest + reproduction snippet; record evidence (WP02)

**Implementation sketch**:

1. Edit `wp_status_changed_unforced_in_review_to_planned.json` so `review_ref` and `reason` are populated. Update its manifest entry's `expected_violations` to include the substring `force=True`.
2. Add new INVALID fixtures for `in_progress`, `for_review`, `approved` pairs with the same shape (force=False, populated `review_ref`/`reason`, distinct `wp_id`/`mission_slug` so they remain readable).
3. Add VALID fixtures for `in_progress`, `for_review`, `in_review` forced rollbacks (force=True, reason; review_ref optional but recommended). The existing `wp_status_changed_approved_rewind.json` already covers `approved -> planned`.
4. Update `manifest.json` to register every new entry with category `valid`/`invalid` and the right `expected_violations` or `expected_lane`.
5. In the dossier doc, update the two sections so they describe the explicit family-guard predicate and the canonical violation substrings (`force=True`, `review-rejection`). Remove the "via the lane matrix check" phrasing.
6. Extend `TestEdgeCaseFixtures` to load each new fixture; assert INVALID fixtures fail validation with the expected substring, VALID fixtures pass.
7. Run the targeted + broad pytest commands and execute the `start-here.md` reproduction snippet; capture stdout and put it in the commit message.

**Dependencies**: `WP01`.
**Parallel opportunities**: T007/T008/T009/T011 are `[P]` within the WP (different files); T010, T012, T013 must follow them.
**Risks**: Manifest drift will fail manifest-consistency tests; running `validate-only` after editing the manifest is the safety check. Dossier doc edit is mechanical wording but must remain valid Markdown.

## Sequencing

```
WP01 (runtime + unit tests)  →  WP02 (fixtures + manifest + dossier + fixture tests)
```

WP01 is the MVP: it lands the runtime guarantee and proves the new behavior
via unit tests. WP02 extends the published contract surface so external
consumers and conformance pipelines can rely on the same guarantee. The
mission is not complete until both ship.

## Parallelization Summary

- WP01 and WP02 own disjoint files and can be **kicked off in parallel** if
  two agents are available. The natural finish order is WP01 then WP02 so
  WP02's fixture-level tests have green runtime to validate against.
- Within each WP, items marked `[P]` in the subtask index touch independent
  files and may be split across cooperating agents if desired.

## MVP Scope

WP01. Once WP01 lands, `validate_transition()` is fail-closed; downstream
consumers see the corrected behavior immediately even if WP02 fixtures lag.

## Done Criteria for the Mission

- WP01 done + WP02 done, all checkboxes ticked.
- `pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q` exits 0.
- `mypy --strict src/spec_kitty_events` exits 0.
- Manual reproduction snippet output from `start-here.md` recorded in commit / quickstart.
- No edits outside the union of WP01 + WP02 owned files.

## Next Suggested Command

`/spec-kitty.analyze` to cross-check spec ⇄ plan ⇄ tasks consistency before implementation.
