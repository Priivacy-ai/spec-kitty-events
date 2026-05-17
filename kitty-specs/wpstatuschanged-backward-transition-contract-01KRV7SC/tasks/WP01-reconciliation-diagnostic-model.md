---
work_package_id: WP01
title: ReconciliationDiagnostic model, enum, and schema
dependencies: []
requirement_refs:
- FR-006
- FR-010
- FR-013
- NFR-002
- C-001
- C-002
- C-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-wpstatuschanged-backward-transition-contract-01KRV7SC
base_commit: e670502aa049450b83cb2506a54d3cb2a3ab34fb
created_at: '2026-05-17T15:25:30.734163+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Contract model
agent: "claude:opus-4-7:python-pedro:implementer"
shell_pid: "1077"
history:
- timestamp: '2026-05-17T15:25:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/
execution_mode: code_change
lane: planned
owned_files:
- src/spec_kitty_events/status.py
- src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json
- tests/test_reconciliation_diagnostic_model.py
- tests/test_reconciliation_diagnostic_schema_drift.py
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package Prompt: WP01 – ReconciliationDiagnostic Model, Enum, and Schema

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile so you operate with the right governance scope and identity:

```text
/ad-hoc-profile-load python-pedro
```

If your environment does not support that slash command, run:

```bash
spec-kitty agent profile show python-pedro
```

and adopt the identity, governance scope, and boundaries it declares.

---

## ⚠️ IMPORTANT: Review Feedback Status

Read this first if you are implementing this task. If `review_status` above says `has_feedback`, scroll to **Review Feedback** below and treat each item as a must-do. Update `review_status: acknowledged` when you start.

---

## Review Feedback

*(empty)*

---

## Objectives & Success Criteria

Add a new closed-enum `ReconciliationReasonCode`, a re-exported `RECONCILIATION_REASON_CODES` tuple, and a frozen Pydantic `ReconciliationDiagnostic` model to `src/spec_kitty_events/status.py`. Emit and commit the matching JSON Schema at `src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json`. Update the `status.py` module docstring to link readers to the canonical contract document at `docs/contracts/wp-status-changed.md` (the file itself is produced by WP02). Cover with focused unit tests and a schema-drift test.

Done means:
- `ReconciliationReasonCode` (closed `str` Enum) lives in `src/spec_kitty_events/status.py` with exactly four members: `FROM_LANE_MISMATCH_REPLAY`, `FROM_LANE_MISMATCH_DRIFT`, `TERMINAL_REPLAY_SKIPPED`, `UNFORCED_ROLLBACK_WITHOUT_REVIEW_REF`. String values match the enum member name lowercased (e.g. `"from_lane_mismatch_replay"`).
- `RECONCILIATION_REASON_CODES: Tuple[str, ...]` is exported as a module-level constant.
- `ReconciliationDiagnostic` Pydantic model lives in `src/spec_kitty_events/status.py` with `model_config = ConfigDict(frozen=True, extra="forbid")` and the exact field set in [data-model.md](../data-model.md).
- `src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json` is committed and matches the model output (drift test passes).
- `status.py` module docstring (the top-of-file docstring) explicitly names `docs/contracts/wp-status-changed.md` as the canonical contract, and restates D-1 (review rollback does not require force; needs review_ref), D-2 (force is for terminal exit or off-matrix), D-3 (actor is audit-only), D-4 (from_lane mismatch reason codes), D-5 (replay idempotent at consumer).
- Two new test files exist and pass:
  - `tests/test_reconciliation_diagnostic_model.py`: constructs a valid diagnostic; asserts `extra="forbid"` rejects unknown fields; asserts the model is frozen (assignment raises); enumerates `ReconciliationReasonCode` and asserts the count is 4.
  - `tests/test_reconciliation_diagnostic_schema_drift.py`: loads the committed JSON Schema, calls `ReconciliationDiagnostic.model_json_schema()`, and asserts they match (normalize ordering and `$defs` placement as needed; reuse the existing drift-check pattern in this repo).
- `uv run pytest tests/test_reconciliation_diagnostic_model.py tests/test_reconciliation_diagnostic_schema_drift.py` passes.
- `uv run pytest` (full suite) passes (NFR-002). `mypy --strict src/spec_kitty_events/` passes.
- No change to `_ALLOWED_TRANSITIONS`, `TERMINAL_LANES`, `validate_transition`, or `StatusTransitionPayload` (C-001).

Mission requirements covered: FR-006, FR-010, FR-013 (enum part), NFR-002, C-001, C-002, C-003.

## Context & Constraints

- Charter (`.kittify/charter/charter.md`): Python 3.10+, Pydantic, committed JSON Schemas, conformance fixtures as public contract. Quality gates: pytest, schema generation check, mypy --strict.
- Spec: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/spec.md` (FR-006, FR-010, FR-013, NFR-002, C-001, C-002, C-003).
- Plan: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/plan.md`.
- Research: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/research.md` (Q4 replay detection, Q6 enum membership, Q7 schema drift).
- Data model: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/data-model.md` (binding shape).
- Contract (draft, also delivered by WP02): `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/contracts/wp-status-changed.contract.md`.
- Draft JSON Schema reference: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/contracts/reconciliation_diagnostic.schema.json`.
- Constraints to honour:
  - C-001: no change to `_ALLOWED_TRANSITIONS`, `TERMINAL_LANES`, `validate_transition`, or `StatusTransitionPayload` field set.
  - C-002: no new runtime dependencies. Use stdlib `enum.Enum` (project supports Python 3.10+; `StrEnum` requires 3.11). The data-model shows `StrEnum` as a convenience; the real implementation MAY use `class ReconciliationReasonCode(str, Enum): ...` if `requires-python` is `>=3.10`.
  - C-003: frozen + `extra="forbid"`.

## Subtasks & Detailed Guidance

### Subtask T001 – Add `ReconciliationReasonCode` enum and `RECONCILIATION_REASON_CODES` tuple

- **Purpose**: Lock the closed set of reconciliation reasons consumers may emit.
- **Steps**:
  1. Read `src/spec_kitty_events/status.py`. Identify where existing public types end and where to append (after `validate_transition` and any helper functions).
  2. Add an enum:
     ```python
     class ReconciliationReasonCode(str, Enum):
         """Closed enum of reasons a consumer may emit a ReconciliationDiagnostic.

         Adding a value requires updating docs/contracts/wp-status-changed.md AND
         adding at least one conformance fixture under
         src/spec_kitty_events/conformance/fixtures/wp_status_changed/.
         """

         FROM_LANE_MISMATCH_REPLAY = "from_lane_mismatch_replay"
         FROM_LANE_MISMATCH_DRIFT = "from_lane_mismatch_drift"
         TERMINAL_REPLAY_SKIPPED = "terminal_replay_skipped"
         UNFORCED_ROLLBACK_WITHOUT_REVIEW_REF = "unforced_rollback_without_review_ref"
     ```
  3. Add a module-level constant tuple:
     ```python
     RECONCILIATION_REASON_CODES: Tuple[str, ...] = tuple(code.value for code in ReconciliationReasonCode)
     ```
  4. Ensure imports at the top of the file include `from enum import Enum` and `from typing import Tuple` if not already present.
- **Files**: `src/spec_kitty_events/status.py`
- **Parallel?**: no — gates T002.
- **Notes**: Use `str, Enum` (not `StrEnum`) for Python 3.10 compatibility. The string values MUST match the contract document (snake_case lowercase).

### Subtask T002 – Add `ReconciliationDiagnostic` Pydantic model

- **Purpose**: Provide the payload shape consumers serialize when they emit a reconciliation diagnostic.
- **Steps**:
  1. Append after T001 in `status.py`:
     ```python
     class ReconciliationDiagnostic(BaseModel):
         """Consumer-emitted diagnostic for deterministic business-rule outcomes.

         Emitted when a consumer refuses to apply, or chooses to skip, a
         WPStatusChanged event under a known rule (see
         docs/contracts/wp-status-changed.md §5–§7). MUST NOT be counted toward
         infra-failure metrics.
         """

         model_config = ConfigDict(frozen=True, extra="forbid")

         mission_slug: str = Field(..., min_length=1, description="Mission identifier")
         wp_id: str = Field(..., min_length=1, description="Work-package identifier")
         event_id: str = Field(..., min_length=1, description="event_id of the offending WPStatusChanged event")
         expected_from_lane: Optional[Lane] = Field(
             None,
             description="from_lane on the offending event (None permitted for bootstrap edge cases)",
         )
         actual_projected_lane: Optional[Lane] = Field(
             None,
             description="Lane the consumer's projection had for this WP at receipt",
         )
         reason_code: ReconciliationReasonCode = Field(
             ..., description="Closed-enum reason (see ReconciliationReasonCode)"
         )
         actor: str = Field(
             ..., min_length=1, description="Audit identity of the consumer that produced the diagnostic"
         )
         detected_at: datetime = Field(
             ..., description="UTC timestamp the consumer made the determination"
         )
     ```
  2. Verify imports include `from datetime import datetime` (probably already present) and `BaseModel`, `ConfigDict`, `Field` from pydantic.
- **Files**: `src/spec_kitty_events/status.py`
- **Parallel?**: no — gates T003.
- **Notes**: Field order must match the JSON Schema (T003). Mirror the wording in `data-model.md` exactly.

### Subtask T003 – Generate and commit the JSON Schema

- **Purpose**: Ship a machine-readable contract artifact consistent with the existing schema discipline.
- **Steps**:
  1. Locate the existing schema regeneration entrypoint. Look in `scripts/`, `pyproject.toml`, or `Makefile`. Mirror the pattern used by `src/spec_kitty_events/schemas/status_transition_payload.schema.json` (already committed).
  2. If a script exists (e.g. `scripts/generate_schemas.py`), extend it to also write `reconciliation_diagnostic.schema.json` from `ReconciliationDiagnostic.model_json_schema()`.
  3. If no script exists, write a minimal regenerator (one function, ≤20 lines) and document it in the script's docstring.
  4. Run the regenerator. Verify the file at `src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json` matches the draft at `kitty-specs/.../contracts/reconciliation_diagnostic.schema.json` in shape (Pydantic adds `$defs` for the Lane enum — that is fine; the draft is illustrative).
- **Files**: `src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json`, possibly `scripts/<regenerator>.py`.
- **Parallel?**: no — gates T005 drift test.

### Subtask T004 – Update `status.py` module docstring to link the contract

- **Purpose**: Anyone reading the source lands on the canonical contract immediately.
- **Steps**:
  1. Add (or extend) the top-of-file module docstring in `src/spec_kitty_events/status.py` with a paragraph that:
     - Names `docs/contracts/wp-status-changed.md` as the canonical contract for WPStatusChanged semantics.
     - Restates D-1 (review rollback does not require force; needs review_ref).
     - Restates D-2 (force is for terminal exit or off-matrix transitions).
     - Restates D-3 (actor is audit-only; `"user"` is NOT an escape hatch).
     - Restates D-4 (from_lane mismatch sub-cases: replay and drift, both use `ReconciliationDiagnostic`).
     - Restates D-5 (replay is idempotent at the consumer; detected before validation).
  2. Keep the paragraph short (≤25 lines). The contract document carries the detail.
- **Files**: `src/spec_kitty_events/status.py`
- **Parallel?**: yes (different file region from T001/T002).

### Subtask T005 – Tests: model + schema drift

- **Purpose**: Lock the model shape and ensure the committed schema never drifts.
- **Steps**:
  1. Create `tests/test_reconciliation_diagnostic_model.py`:
     - `test_construct_valid_diagnostic_for_each_reason_code` — parametrized over `RECONCILIATION_REASON_CODES`; constructs a `ReconciliationDiagnostic` for each and asserts the round-trip via `model_dump()` and `model_validate()`.
     - `test_extra_forbid_rejects_unknown_field` — `ValidationError` on a payload with `foo: "bar"`.
     - `test_frozen_disallows_assignment` — constructing then `diag.actor = "evil"` raises.
     - `test_reason_code_enum_is_closed_with_four_members` — `len(RECONCILIATION_REASON_CODES) == 4` and the exact value set.
     - `test_mission_slug_and_wp_id_min_length_one` — empty string fails validation.
     - `test_detected_at_must_be_datetime` — string fails.
  2. Create `tests/test_reconciliation_diagnostic_schema_drift.py`:
     - Reads `src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json`.
     - Calls `ReconciliationDiagnostic.model_json_schema()`.
     - Normalizes (e.g. sort keys) and asserts equality. Mirror the existing drift test pattern in this repo (look at `tests/` for `status_transition_payload` drift checks, if any).
  3. Run `uv run pytest tests/test_reconciliation_diagnostic_model.py tests/test_reconciliation_diagnostic_schema_drift.py` and confirm both pass.
  4. Run the full suite `uv run pytest` and `mypy --strict src/spec_kitty_events/` to confirm no regressions (NFR-002).
- **Files**: `tests/test_reconciliation_diagnostic_model.py`, `tests/test_reconciliation_diagnostic_schema_drift.py`.
- **Parallel?**: no — gates handoff.

## Branch Strategy

- Planning base branch: `main`.
- Final merge target: `main`.
- Worktree allocation: spec-kitty assigns this WP to its computed lane via `lanes.json`. Implement inside that lane's worktree (`.worktrees/<slug>-lane-<X>/`).

## Test Strategy

- Add the two test files described in T005.
- Run `uv run pytest` to confirm the entire suite remains green.
- Run `mypy --strict src/spec_kitty_events/` to confirm no type regressions.

## Definition of Done

- [ ] `ReconciliationReasonCode` enum with 4 members
- [ ] `RECONCILIATION_REASON_CODES` tuple exported
- [ ] `ReconciliationDiagnostic` Pydantic model (frozen + extra=forbid)
- [ ] Committed JSON Schema at `src/spec_kitty_events/schemas/reconciliation_diagnostic.schema.json`
- [ ] Module docstring in `status.py` references the contract and restates D-1..D-5
- [ ] New model test file passes
- [ ] New schema-drift test passes
- [ ] Full `uv run pytest` passes
- [ ] `mypy --strict src/spec_kitty_events/` passes
- [ ] No change to `_ALLOWED_TRANSITIONS`, `TERMINAL_LANES`, `validate_transition`, or `StatusTransitionPayload` (verify via `git diff --stat`)

## Risks

- **Schema drift** between model and committed file. Mitigated by T005 drift test.
- **Accidentally importing `StrEnum`** which is 3.11+. Mitigated by the `str, Enum` pattern noted in T001.
- **Touching `validate_transition`** while editing. Mitigated by the explicit DoD check and the owned-files restriction.

## Reviewer Guidance

- Verify `git diff` on `status.py` ONLY adds new code; nothing in `_ALLOWED_TRANSITIONS`, `TERMINAL_LANES`, `validate_transition`, or `StatusTransitionPayload` is modified.
- Verify the committed schema and the model agree (re-run the drift test locally).
- Verify the module docstring names the contract path and the five decisions.
- Confirm no new dependencies were added to `pyproject.toml`.

## Activity Log

- 2026-05-17T15:25:32Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1077 – Assigned agent via action command
