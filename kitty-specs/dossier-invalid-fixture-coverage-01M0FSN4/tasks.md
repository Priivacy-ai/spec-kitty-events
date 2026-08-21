# Tasks: Dossier Invalid Fixture Coverage

**Input**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/manifest-entry-contract.md`, `quickstart.md`
**Branch**: `feat/dossier-invalid-fixture-coverage` (planning and merge target — same branch, PR-bound)

## Subtask Index

| ID | Description | WP | Parallel |
|----|--------------|----|----------|
| T001 | Write `dossier_artifact_missing_empty_step.json` fixture | WP01 | [P] |
| T002 | Locally validate T001 fixture fails `validate_event()` | WP01 | [P] |
| T003 | Write `dossier_snapshot_computed_negative_count.json` fixture | WP01 | [P] |
| T004 | Locally validate T003 fixture fails `validate_event()` | WP01 | [P] |
| T005 | Add both fixtures' entries to `manifest.json` | WP02 | |
| T006 | Bump hardcoded count assertions in `tests/test_dossier_conformance.py` | WP02 | |
| T007 | Run full `tests/test_dossier_conformance.py` suite; confirm no regressions | WP02 | |
| T008 | Verify `fixtures/dossier/invalid/` ↔ `manifest.json` 1:1 consistency | WP02 | |

`[P]` marks subtasks safe to parallelize (different files). Subtask completion is event-sourced — record with `spec-kitty agent tasks mark-status <ids> --status done`, not by editing this table.

---

## WP01 — Author the two invalid fixtures

**Goal**: Create both new invalid conformance fixture JSON files, each a minimally-modified valid sibling with exactly one genuine constraint violation.

**Priority**: P1 (both target user stories, FR-001 and FR-002)

**Independent test**: Each fixture, loaded standalone and passed through `validate_event()`, fails with a violation pointing at the deliberately broken field; all other fields remain valid.

**Included subtasks**: T001, T002, T003, T004

**Implementation sketch**:
1. Copy `dossier_artifact_missing_required_always.json` → `dossier_artifact_missing_empty_step.json`, set `manifest_step: ""`.
2. Run it through `validate_event()` locally; confirm it fails on `manifest_step` (min_length=1), not on anything else.
3. Copy `dossier_snapshot_computed_clean.json` → `dossier_snapshot_computed_negative_count.json`, set `artifact_count: -1`.
4. Run it through `validate_event()` locally; confirm it fails on `artifact_count` (ge=0), not on anything else.

**Parallel opportunities**: T001/T002 (ArtifactMissing fixture) and T003/T004 (SnapshotComputed fixture) touch entirely different files — safe to do in either order or concurrently.

**Dependencies**: none

**Risks**: A fixture that looks broken but Pydantic silently coerces (e.g. wrong type on a docstring-only field) would pass instead of fail — must be caught by local validation (T002/T004), not left for CI to discover.

**Estimated size**: ~180 lines (2 subtasks × 2, small fixture files, low complexity)

**Prompt file**: `tasks/WP01-author-invalid-fixtures.md`

---

## WP02 — Register fixtures and update count gates

**Goal**: Wire both new fixtures into the canonical manifest-driven conformance harness so they are actually exercised, not silently inert.

**Priority**: P1 (FR-003 — the mechanism the post-spec adversarial review found missing from the original spec)

**Independent test**: `pytest tests/test_dossier_conformance.py` passes with both new fixtures appearing as parametrized cases in `test_invalid_fixture_fails_conformance`, and the fixture-count/invalid-case-count assertions match the new totals (15 / 5).

**Included subtasks**: T005, T006, T007, T008

**Implementation sketch**:
1. Add two entries to `fixtures/manifest.json` (see `contracts/manifest-entry-contract.md` and `data-model.md` for exact field values) — `expected_result: "invalid"`, `notes` naming the exact violation, `min_version: "2.4.0"`.
2. Bump `test_dossier_fixture_count` (13→15) and `test_dossier_invalid_case_count` (3→5) in `tests/test_dossier_conformance.py`. Leave `test_dossier_valid_case_count` (10) untouched.
3. Run `pytest tests/test_dossier_conformance.py -v`; confirm all tests pass, including the two new parametrized cases — no new test function should be needed.
4. Cross-check: every file under `fixtures/dossier/invalid/` has exactly one `manifest.json` entry, and vice versa.

**Parallel opportunities**: None internally — steps are sequential (manifest before count bump before test run before consistency check).

Depends on WP01 (both fixture files must exist before they can be registered and counted).

**Risks**: This is the mission's single shared touchpoint (`manifest.json` + one test file) — if WP01's two fixtures aren't both finished first, this WP's count bump would be wrong.

**Estimated size**: ~220 lines

**Prompt file**: `tasks/WP02-register-fixtures-and-update-gates.md`

---

## MVP scope

WP01 alone produces two real fixture files but delivers no verifiable value until WP02 wires them in — treat WP01+WP02 together as the minimum shippable unit for this mission (there is no smaller meaningful slice).

## Note: out-of-code follow-up (not a work package)

Per spec.md User Story 3 / Acceptance Scenario 3: once this mission merges, post a comment on `Priivacy-ai/spec-kitty-events`#23 recording that the fixture-coverage acceptance criterion is now met via this mission. This is a manual GitHub action outside the code-change ownership model (no `owned_files` surface applies), not a WP — do not skip it at mission close-out.
