# Tasks: WPStatusChanged Backward Transition Contract

**Mission**: `wpstatuschanged-backward-transition-contract-01KRV7SC`
**Planning base**: `main`
**Merge target**: `main`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Overview

Three small work packages. WP01 ships the new `ReconciliationDiagnostic` Pydantic model + closed enum + schema; WP02 ships the contract document and README link; WP03 ships the conformance fixtures, manifest entries, and tests. WP02 has no dependencies. WP03 depends on WP01 (tests use the new model).

| WP | Title | Subtasks | Estimated lines | Dependencies | Parallel-safe |
|----|-------|----------|------|--------------|---------------|
| WP01 | ReconciliationDiagnostic model, enum, and schema | T001–T005 | ~340 | none | yes (different files than WP02/WP03) |
| WP02 | Contract document and README integration | T006–T008 | ~210 | none | yes |
| WP03 | Conformance fixtures, manifest entries, and tests | T009–T013 | ~390 | WP01 | sequential after WP01 |

Total subtasks: 13. All WPs are within the 3–7 subtask ideal range.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `ReconciliationReasonCode` StrEnum + `RECONCILIATION_REASON_CODES` tuple to `src/spec_kitty_events/status.py` | WP01 | |
| T002 | Add `ReconciliationDiagnostic` Pydantic frozen model to `src/spec_kitty_events/status.py` | WP01 | |
| T003 | Generate `src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json` from the model and commit it | WP01 | |
| T004 | Update `src/spec_kitty_events/status.py` module docstring to link to `docs/contracts/wp-status-changed.md` and inline-state D-1..D-5 | WP01 | |
| T005 | Add `tests/test_reconciliation_diagnostic_model.py` (model construction, frozen, `extra="forbid"`, enum closure) and `tests/test_reconciliation_diagnostic_schema_drift.py` (committed schema matches model output) | WP01 | |
| T006 | Copy `kitty-specs/.../contracts/wp-status-changed.contract.md` to `docs/contracts/wp-status-changed.md` as the canonical contract document | WP02 | [P] |
| T007 | Add a "Contracts" section to `README.md` that links to `docs/contracts/wp-status-changed.md` | WP02 | [P] |
| T008 | Add `tests/test_contract_docstring_links.py` asserting `src/spec_kitty_events/status.py` references the contract path | WP02 | [P] |
| T009 | Create `src/spec_kitty_events/conformance/fixtures/wp_status_changed/` directory and write six fixture JSON files (one per FR-007 scenario) | WP03 | |
| T010 | Append six entries to `src/spec_kitty_events/conformance/fixtures/manifest.json` with `outcome` and `reason_code` | WP03 | |
| T011 | Write `tests/test_wp_status_changed_contract_fixtures.py` that loads each fixture and asserts `validate_transition` (or the reconciler) produces the declared outcome | WP03 | |
| T012 | Add a fixture-coverage assertion: every value in `ReconciliationReasonCode` appears in at least one fixture (enforces D-6 / FR-013) | WP03 | |
| T013 | Run the full `uv run pytest` suite and `mypy --strict src/spec_kitty_events/` to confirm no regressions (NFR-002) | WP03 | |

## Requirement coverage

| Requirement | WPs |
|---|---|
| FR-001 (contract doc exists at `docs/contracts/wp-status-changed.md`) | WP02 |
| FR-002 (doc explicitly states review-rollback does not require force) | WP02 |
| FR-003 (doc states actor is audit-only, not policy escape hatch) | WP02 |
| FR-004 (doc defines `from_lane` mismatch reason codes) | WP02 |
| FR-005 (doc defines replay semantics) | WP02 |
| FR-006 (`ReconciliationDiagnostic` Pydantic model) | WP01 |
| FR-007 (six conformance fixtures) | WP03 |
| FR-008 (manifest entries with `outcome`+`reason_code`) | WP03 |
| FR-009 (tests prove fixture outcomes) | WP03 |
| FR-010 (status.py docstrings link to contract) | WP01, WP02 |
| FR-011 (consumer responsibilities section) | WP02 |
| FR-012 (diagnostic surface separation subsection) | WP02 |
| FR-013 (closed enum + fixture-addition rule) | WP01 (enum), WP03 (coverage assertion) |
| NFR-001 (fixture suite < 5s) | WP03 |
| NFR-002 (pytest clean) | WP01, WP02, WP03 |
| NFR-003 (doc ≤ 600 lines) | WP02 |
| NFR-004 (README links to contract) | WP02 |
| C-001 (no change to `_ALLOWED_TRANSITIONS`/`validate_transition`/`StatusTransitionPayload`) | WP01 (reviewer check) |
| C-002 (no new runtime dependencies) | WP01, WP03 (reviewer check) |
| C-003 (frozen + extra=forbid) | WP01 |
| C-004 (this mission lands before consumers) | program-level (no per-WP test) |
| C-005 (contract cites `_ALLOWED_TRANSITIONS` verbatim) | WP02 |

## Work Packages

### WP01 — ReconciliationDiagnostic model, enum, and schema

**Goal**: Add the new `ReconciliationReasonCode`, `RECONCILIATION_REASON_CODES`, and `ReconciliationDiagnostic` to `src/spec_kitty_events/status.py`; emit the matching JSON Schema; update status.py docstrings to point readers at the canonical contract; cover with focused tests.

**Independent test**: `uv run pytest tests/test_reconciliation_diagnostic_model.py tests/test_reconciliation_diagnostic_schema_drift.py` passes.

**Owned files**: `src/spec_kitty_events/status.py`, `src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json`, `tests/test_reconciliation_diagnostic_model.py`, `tests/test_reconciliation_diagnostic_schema_drift.py`.

**Authoritative surface**: `src/spec_kitty_events/`.

**Dependencies**: none.

**Risks**: 1) Drift between committed schema and model. Mitigated by T005 drift test. 2) Importing `StrEnum` requires Python 3.11; project supports 3.10+. Mitigated by importing from `enum` and using `str, Enum` pattern instead of `StrEnum` if Python 3.10 compatibility is needed (verify in pyproject `requires-python`).

**Included subtasks**:
- [ ] T001 Add `ReconciliationReasonCode` enum + `RECONCILIATION_REASON_CODES` tuple
- [ ] T002 Add `ReconciliationDiagnostic` Pydantic frozen model
- [ ] T003 Generate `reconciliation_diagnostic.schema.json` and commit it
- [ ] T004 Update `status.py` module docstring to link the contract document
- [ ] T005 Add model and schema-drift tests

### WP02 — Contract document and README integration

**Goal**: Promote the contract draft from `kitty-specs/.../contracts/wp-status-changed.contract.md` into the canonical home `docs/contracts/wp-status-changed.md` and link it from `README.md`. Add a docstring-link assertion test.

**Independent test**: `uv run pytest tests/test_contract_docstring_links.py` passes; `grep "wp-status-changed.md" README.md` returns at least one hit; `wc -l docs/contracts/wp-status-changed.md` returns ≤ 600.

**Owned files**: `docs/contracts/wp-status-changed.md`, `README.md`, `tests/test_contract_docstring_links.py`.

**Authoritative surface**: `docs/contracts/`.

**Dependencies**: none (the contract content is already drafted in the mission folder).

**Risks**: README structure changes are sometimes contentious. Mitigated by inserting a minimal "Contracts" section without restructuring existing sections.

**Included subtasks**:
- [x] T006 Copy contract draft to `docs/contracts/wp-status-changed.md`
- [x] T007 Add "Contracts" section to `README.md`
- [x] T008 Add `tests/test_contract_docstring_links.py`

### WP03 — Conformance fixtures, manifest entries, and tests

**Goal**: Ship six conformance fixtures covering the FR-007 scenarios, append matching manifest entries, and write tests that prove each fixture's declared outcome matches `validate_transition` (or the small reconciler used for `from_lane` mismatch and replay cases).

**Independent test**: `uv run pytest tests/test_wp_status_changed_contract_fixtures.py` passes; the test runtime is under 5 seconds (NFR-001).

**Owned files**: `src/spec_kitty_events/conformance/fixtures/wp_status_changed/**`, `src/spec_kitty_events/conformance/fixtures/manifest.json`, `tests/test_wp_status_changed_contract_fixtures.py`.

**Authoritative surface**: `src/spec_kitty_events/conformance/fixtures/`.

**Dependencies**: WP01 (tests import `ReconciliationDiagnostic` and `ReconciliationReasonCode`).

**Risks**: Manifest schema drift if the existing manifest expects fields not yet documented. Mitigated by reading a few existing entries before appending and matching their shape.

**Included subtasks**:
- [ ] T009 Create `wp_status_changed/` fixture directory with six JSON files
- [ ] T010 Append six manifest entries with `outcome` and `reason_code`
- [ ] T011 Write `tests/test_wp_status_changed_contract_fixtures.py`
- [ ] T012 Add reason_code coverage assertion to the fixture test
- [ ] T013 Run full `uv run pytest` and `mypy --strict` to confirm no regressions

## Parallelization

- WP01 and WP02 are independent and can run in two lanes concurrently.
- WP03 starts after WP01 approves.

## MVP scope

WP01 + WP02 + WP03 are all required for the contract to be useful. There is no MVP subset; the whole mission is the MVP for the downstream missions.

## Next command

`/spec-kitty.analyze --mission wpstatuschanged-backward-transition-contract-01KRV7SC`
