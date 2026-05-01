# Tasks: TeamSpace Event Contract Foundation

**Mission**: `teamspace-event-contract-foundation-01KQHDE4`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data Model**: [data-model.md](./data-model.md) · **Contracts**: [contracts/](./contracts/)
**Branch contract**: planning base `main`, merge target `main`
**Reviewer**: Codex (mandatory at mission close)

---

## Subtask Index

This is a reference table only — progress tracking happens via the per-WP checkbox rows below.

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add `IN_REVIEW` to the `Lane` enum in `src/spec_kitty_events/status.py` | WP01 | | [D] |
| T002 | Move `in_review` out of "invalid lane" fixtures (lane_mapping/invalid/unknown_lanes.json + events/invalid/wp_status_changed_invalid_lane.json) | WP01 | | [D] |
| T003 | Author `tests/test_lane_vocabulary.py` proving canonical-lane single-source-of-truth and `Lane.IN_REVIEW` membership | WP01 | | [D] |
| T004 | Update any existing tests that asserted `in_review` was invalid (search-and-fix pass) | WP01 | | [D] |
| T005 | Create `src/spec_kitty_events/validation_errors.py` with `ValidationError` Pydantic model and `ValidationErrorCode` closed enum | WP02 | [D] |
| T006 | Add `as_validation_error()` adapter methods on existing typed exceptions (TransitionError, lifecycle errors) | WP02 | [D] |
| T007 | Author `tests/test_validation_error.py` for shape, enum membership, determinism | WP02 | [D] |
| T008 | Audit `spec-kitty-saas` ingress rejection rules + epic #920 historical-row survey to expand the forbidden-key set; document audit results | WP03 | | [D] |
| T009 | Create `src/spec_kitty_events/forbidden_keys.py` with `FORBIDDEN_LEGACY_KEYS` constant and recursive validator | WP03 | | [D] |
| T010 | Author `tests/test_forbidden_keys.py` targeted fixtures: top, depth-1, depth-3, depth-10, array element, must-accept-when-value | WP03 | | [D] |
| T011 | Add hypothesis property tests for the recursive validator + determinism test | WP03 | | [D] |
| T012 | Audit CLI emission sites for `MissionCreated`, `WPStatusChanged`, `MissionClosed` and document field disposition | WP04 | | [D] |
| T013 | Append reconciliation log to `contracts/payload-reconciliation.md` recording decisions per event type | WP04 | | [D] |
| T014 | Update payload models (`MissionCreatedPayload`, `MissionClosedPayload`, `StatusTransitionPayload`) with reconciled fields and `extra='forbid'` | WP04 | | [D] |
| T015 | Regenerate `src/spec_kitty_events/schemas/*.schema.json` from updated models | WP04 | | [D] |
| T016 | Author `tests/test_payload_reconciliation.py` covering cross-shape acceptance and rejection | WP04 | | [D] |
| T017 | Reorganize `src/spec_kitty_events/conformance/fixtures/` into 8 named class directories | WP05 | |
| T018 | Author `envelope_valid_canonical` fixtures (one per event type, including `in_review`-using `WPStatusChanged`) | WP05 | |
| T019 | Author `envelope_valid_historical_synthesized` fixtures (CLI canonicalizer dry-run shapes) | WP05 | |
| T020 | Author `envelope_invalid_*` fixtures (forbidden_key at top/nested/depth-10/array, unknown_lane, payload_schema, envelope_shape) with `expected_error_code` | WP05 | |
| T021 | Author `historical_row_raw` fixtures (real shapes from epic survey, deterministic values) | WP05 | |
| T022 | Update `manifest.json` with full class registrations; add `src/spec_kitty_events/conformance/fixtures/README.md` | WP05 | |
| T023 | Author `tests/test_fixture_determinism.py` (audit forbidden patterns: recent timestamps, non-pinned ULIDs) | WP05 | |
| T024 | Author `tests/test_conformance_classes.py` asserting every fixture's expected outcome and `expected_error_code` | WP05 | |
| T025 | Update `COMPATIBILITY.md` with "Local-CLI compatibility vs TeamSpace ingress validity" section | WP06 | |
| T026 | Update `CHANGELOG.md` with a "Breaking Changes" section (in_review canonical, payload reconciliation, recursive forbidden-key validator) | WP06 | |
| T027 | Bump package version in `pyproject.toml` per major-bump rule | WP06 | |
| T028 | Author `tests/test_validation_benchmark.py` enforcing < 5 ms p95 envelope validation (NFR-005) | WP07 | |
| T029 | Run full pytest + mypy --strict + schema-drift CI; document results | WP07 | |
| T030 | Author `kitty-specs/.../contracts/.review-handoff.md` summarizing all SC-### satisfaction for Codex review | WP07 | |

---

## Phase 1 — Foundation (parallel)

### WP01 — Lane Vocabulary Canonicalization

**Goal**: Make `in_review` a canonical lane in `spec_kitty_events`, so envelopes referencing it validate as accepted.

**Priority**: P0 — every other WP depends on this directly or transitively.

**Independent test**: `pytest tests/test_lane_vocabulary.py` passes; existing `Lane` enum membership round-trips include `IN_REVIEW`.

**Spec coverage**: FR-001, FR-002, C-002, C-004, SC-003

**Prompt**: [tasks/WP01-lane-vocabulary-canonicalization.md](./tasks/WP01-lane-vocabulary-canonicalization.md) (~280 lines)

**Subtasks**:
- [x] T001 Add `IN_REVIEW` to the `Lane` enum (WP01)
- [x] T002 Move `in_review` out of "invalid lane" fixtures (WP01)
- [x] T003 Author `tests/test_lane_vocabulary.py` (WP01)
- [x] T004 Update existing tests that asserted `in_review` was invalid (WP01)

**Dependencies**: none.

**Risks**: A test elsewhere may assume `in_review` is rejected; T004 catches this with a search-and-fix pass.

---

### WP02 — Validation Error Shape

**Goal**: Introduce the structured `ValidationError` (`code`, `message`, `path`, `details`) with a closed `ValidationErrorCode` enum, layered on top of existing typed exceptions.

**Priority**: P0 — blocks WP03, WP04 (their rejection paths use this shape).

**Independent test**: `pytest tests/test_validation_error.py` passes; existing exceptions expose `as_validation_error()`.

**Spec coverage**: NFR-006

**Prompt**: [tasks/WP02-validation-error-shape.md](./tasks/WP02-validation-error-shape.md) (~250 lines)

**Subtasks**:
- [x] T005 Create `src/spec_kitty_events/validation_errors.py` (WP02)
- [x] T006 Add `as_validation_error()` adapters on existing typed exceptions (WP02)
- [x] T007 Author `tests/test_validation_error.py` (WP02)

**Dependencies**: none. **Parallel** with WP01.

**Risks**: Existing exception users may break if we change inheritance — mitigation is to add the adapter, not replace the exceptions.

---

## Phase 2 — Validators & Reconciliation (parallel)

### WP03 — Recursive Forbidden-Key Validator

**Goal**: Ship a recursive validator that rejects any envelope or payload containing a forbidden legacy key (`feature_slug`, `feature_number`, `mission_key`, plus the audit-derived expansion) at any nesting depth or inside any array element.

**Priority**: P0 — gates fixture work and final ingress rule.

**Independent test**: `pytest tests/test_forbidden_keys.py` passes including the depth ≥ 10 fixture, the array-element fixture, and the must-accept-when-value fixture; hypothesis tests pass.

**Spec coverage**: FR-005, NFR-002, C-001, SC-005

**Prompt**: [tasks/WP03-recursive-forbidden-key-validator.md](./tasks/WP03-recursive-forbidden-key-validator.md) (~400 lines)

**Subtasks**:
- [x] T008 Audit SaaS ingress + epic survey; expand the forbidden-key set (WP03)
- [x] T009 Create `src/spec_kitty_events/forbidden_keys.py` (WP03)
- [x] T010 Targeted fixtures (top/depth-1/depth-3/depth-10/array/must-accept) (WP03)
- [x] T011 Hypothesis property tests + determinism test (WP03)

**Dependencies**: WP02.

**Risks**: Over-rejection (matching values not just keys) — covered by a dedicated must-accept fixture.

---

### WP04 — Payload Reconciliation

**Goal**: Reconcile `MissionCreatedPayload`, `WPStatusChangedPayload`/`StatusTransitionPayload`, and `MissionClosedPayload` so the events package is the single source of truth (R-02 direction); CLI canonicalizer is the transformation layer.

**Priority**: P0 — blocks fixture authoring (canonical envelopes need reconciled payloads).

**Independent test**: `pytest tests/test_payload_reconciliation.py` passes; schema-drift CI green; reconciliation log present in [contracts/payload-reconciliation.md](./contracts/payload-reconciliation.md).

**Spec coverage**: FR-003, FR-004, C-002, C-004, SC-004

**Prompt**: [tasks/WP04-payload-reconciliation.md](./tasks/WP04-payload-reconciliation.md) (~480 lines)

**Subtasks**:
- [x] T012 Audit CLI emission sites (WP04)
- [x] T013 Append reconciliation log to contracts/payload-reconciliation.md (WP04)
- [x] T014 Update payload models with reconciled fields + `extra='forbid'` (WP04)
- [x] T015 Regenerate `src/spec_kitty_events/schemas/*.schema.json` (WP04)
- [x] T016 Author `tests/test_payload_reconciliation.py` (WP04)

**Dependencies**: WP01, WP02.

**Risks**: Field-disposition decisions need to align with downstream tranches in `spec-kitty` (Tranches A/B). The reconciliation log is the cross-tranche handshake.

---

## Phase 3 — Conformance Suite

### WP05 — Conformance Fixture Suite

**Goal**: Reorganize `src/spec_kitty_events/conformance/fixtures/` into the eight named classes from R-05; populate every class with at least one fixture; update the manifest; add the deterministic-fixture audit and the conformance-class assertion test.

**Priority**: P0 — proves the contract.

**Independent test**: `pytest tests/test_conformance_classes.py` and `pytest tests/test_fixture_determinism.py` both green; manifest's class population satisfies coverage rules.

**Spec coverage**: FR-006, FR-007, FR-008, C-006, SC-001, SC-002, SC-005

**Prompt**: [tasks/WP05-conformance-fixture-suite.md](./tasks/WP05-conformance-fixture-suite.md) (~700 lines — at upper limit)

**Subtasks**:
- [ ] T017 Reorganize fixtures into 8 named class directories (WP05)
- [ ] T018 Author envelope_valid_canonical fixtures (WP05)
- [ ] T019 Author envelope_valid_historical_synthesized fixtures (WP05)
- [ ] T020 Author envelope_invalid_* fixtures with expected_error_code (WP05)
- [ ] T021 Author historical_row_raw fixtures with deterministic values (WP05)
- [ ] T022 Update manifest.json + add fixtures README (WP05)
- [ ] T023 Author tests/test_fixture_determinism.py (WP05)
- [ ] T024 Author tests/test_conformance_classes.py (WP05)

**Dependencies**: WP01, WP02, WP03, WP04.

**Risks**: 8 subtasks is at the recommended upper bound. The risk is mitigated by the strict R-06 deterministic-value convention and by class-by-class fixture authoring (subtasks are parallelizable internally by class).

---

## Phase 4 — Release & Compatibility

### WP06 — Compatibility Doc + Version Bump

**Goal**: Land the major schema version bump, the local-vs-ingress compatibility section, and the CHANGELOG breaking-changes entry.

**Priority**: P0 — release-blocking artifact.

**Independent test**: `pyproject.toml` major bump applied; CHANGELOG and COMPATIBILITY have the required sections; schema-drift CI green.

**Spec coverage**: FR-009, FR-010, C-003, SC-006

**Prompt**: [tasks/WP06-compatibility-doc-and-version-bump.md](./tasks/WP06-compatibility-doc-and-version-bump.md) (~250 lines)

**Subtasks**:
- [ ] T025 Update `COMPATIBILITY.md` with local-vs-ingress section (WP06)
- [ ] T026 Update `CHANGELOG.md` with Breaking Changes section (WP06)
- [ ] T027 Bump package version in `pyproject.toml` (WP06)

**Dependencies**: WP01–WP05.

**Risks**: Forgetting to regen schemas on bump — mitigated by schema-drift CI gate.

---

## Phase 5 — Verification & Codex Handoff

### WP07 — Performance Benchmark + Codex Review Handoff

**Goal**: Prove the per-envelope validation benchmark (< 5 ms p95) and produce the Codex review handoff document mapping every SC-### to its evidence.

**Priority**: P1 — final mission-close gate.

**Independent test**: `pytest tests/test_validation_benchmark.py` passes; the review handoff doc enumerates evidence for SC-001…SC-007.

**Spec coverage**: NFR-005, C-005, SC-007

**Prompt**: [tasks/WP07-performance-benchmark-and-codex-handoff.md](./tasks/WP07-performance-benchmark-and-codex-handoff.md) (~200 lines)

**Subtasks**:
- [ ] T028 Author `tests/test_validation_benchmark.py` (WP07)
- [ ] T029 Run full pytest + mypy --strict + schema-drift; document results (WP07)
- [ ] T030 Author `kitty-specs/.../contracts/.review-handoff.md` (WP07)

**Dependencies**: WP01–WP06.

**Risks**: Benchmark flakiness on shared CI — mitigated by p95 over a fixture sample, not p100.

---

## Execution Notes

- **Parallelization**: WP01 ‖ WP02; then WP03 ‖ WP04; then WP05; then WP06; then WP07.
- **MVP scope recommendation**: WP01 + WP02 alone produce a runnable improvement (in_review accepted, ValidationError available). WP03 + WP04 + WP05 are required for the contract foundation to be useful to downstream tranches. WP06 + WP07 land the public-release artifacts.
- **Cross-tranche coordination**: WP04's reconciliation log is the handshake to `spec-kitty` Tranche A (audit) and Tranche B (canonicalizer). Those tranches must reference the log.
- **Codex review** (per C-005) is the mission-close gate. WP07's review-handoff doc is the input.

---

## Branch Contract (restated)

- Planning/base branch: `main`
- Merge target: `main`
- WP execution worktrees will live under `.worktrees/teamspace-event-contract-foundation-01KQHDE4-<mid8>-lane-<x>/` once `finalize-tasks` computes the lanes.
