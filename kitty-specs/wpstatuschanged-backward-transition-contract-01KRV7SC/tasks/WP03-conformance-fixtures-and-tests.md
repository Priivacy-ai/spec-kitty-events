---
work_package_id: WP03
title: Conformance fixtures, manifest entries, and tests
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-013
- NFR-001
- NFR-002
- C-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Conformance
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/conformance/fixtures/
execution_mode: code_change
lane: planned
owned_files:
- src/spec_kitty_events/conformance/fixtures/wp_status_changed/**
- src/spec_kitty_events/conformance/fixtures/manifest.json
- tests/test_wp_status_changed_contract_fixtures.py
review_status: ''
reviewed_by: ''
role: implementer
agent: "claude:opus-4-7:python-pedro:implementer"
tags: []
shell_pid: "2650"
history:
- timestamp: '2026-05-17T15:25:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Conformance Fixtures, Manifest Entries, and Tests

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

If your environment does not support that slash command, run:

```bash
spec-kitty agent profile show python-pedro
```

---

## ⚠️ IMPORTANT: Review Feedback Status

If `review_status` above says `has_feedback`, scroll to **Review Feedback** below. Update `review_status: acknowledged` when you start.

## Review Feedback

*(empty)*

---

## Objectives & Success Criteria

Ship six conformance fixtures covering the FR-007 scenarios, append matching entries to `manifest.json`, and write a test file that proves each fixture's declared outcome matches what `validate_transition` (or a small consumer reconciler stub) produces. Add a coverage assertion that every `ReconciliationReasonCode` member is exercised by at least one fixture.

Done means:
- `src/spec_kitty_events/conformance/fixtures/wp_status_changed/` exists with these six files:
  1. `forward_lifecycle.json` — chains `planned→claimed→in_progress→for_review→approved→done`. Outcome `accept` for every step; `reason_code: null`.
  2. `review_rejection_in_review_to_planned.json` — `from_lane: in_review, to_lane: planned, actor: "user", force: false, review_ref: "<path>"`. Outcome `accept`; `reason_code: null`.
  3. `backward_no_force_no_review_ref.json` — `from_lane: in_review, to_lane: planned, actor: "user", force: false, review_ref: null`. Outcome `reject`; `reason_code: "unforced_rollback_without_review_ref"`. (The consumer-side reason; `validate_transition` will surface a violation message.)
  4. `backward_with_force_and_reason.json` — `from_lane: done, to_lane: in_progress, actor: "migration", force: true, reason: "operator-authorized re-open"`. Outcome `accept`; `reason_code: null`.
  5. `from_lane_mismatch_drift.json` — `current_projection_lane: planned`, event has `from_lane: in_progress, to_lane: for_review, ...`. Outcome `reconcile`; `reason_code: "from_lane_mismatch_drift"`.
  6. `replay_idempotency_skip.json` — same `event_id` already in consumer's seen-set; current projection at `for_review`; event has `from_lane: in_progress, to_lane: for_review, ...`. Outcome `idempotency_skip`; `reason_code: null` (replay is silent by D-4 / contract §6.1).
- `src/spec_kitty_events/conformance/fixtures/manifest.json` has six new entries (one per fixture), each with `fixture_id`, `fixture_file`, `event_type: "WPStatusChanged"`, `outcome`, `reason_code`, and `notes` referencing the relevant FR.
- `tests/test_wp_status_changed_contract_fixtures.py` exists and:
  - Loads each fixture file via the existing fixture-loading helper (or builds one if missing).
  - For each fixture, asserts the declared outcome matches what the validator or reconciler produces:
    - `accept` → `validate_transition(...).valid is True` AND `violations == ()`.
    - `reject` → `validate_transition(...).valid is False`; if `reason_code` is set, the consumer-side `ReconciliationDiagnostic` (constructed from the offending event + reason_code) round-trips through `model_validate(model_dump())`.
    - `reconcile` → a small inline `consumer_reconcile(projection_lane, event)` helper in the test file returns a `ReconciliationDiagnostic` with the declared `reason_code`. The helper logic is: if event.from_lane != projection_lane and event.from_lane has never been the projection's lane in this test's mini event-log, emit `from_lane_mismatch_drift`; otherwise emit `from_lane_mismatch_replay`.
    - `idempotency_skip` → the helper checks `event_id in seen_event_ids` and returns `None` (no diagnostic).
- A `test_every_reason_code_has_a_fixture` assertion iterates `ReconciliationReasonCode` and verifies each value appears as a `reason_code` in at least one manifest entry (FR-013 / D-6).
- Aggregate runtime for the new test file is < 5 seconds (NFR-001). Confirm with `uv run pytest tests/test_wp_status_changed_contract_fixtures.py --durations=10`.
- `uv run pytest` (full suite) passes. `mypy --strict src/spec_kitty_events/` passes.

Mission requirements covered: FR-007, FR-008, FR-009, FR-013 (coverage assertion), NFR-001, NFR-002, C-002.

## Context & Constraints

- Spec: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/spec.md`.
- Plan: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/plan.md`.
- Data model (binding shape for fixture and manifest): `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/data-model.md` — "Conformance fixture format" and "Manifest entry shape".
- Existing manifest: `src/spec_kitty_events/conformance/fixtures/manifest.json` — read 2–3 existing entries to mirror the shape.
- Existing fixture loader / validators: `src/spec_kitty_events/conformance/validators.py` (note the `_PAYLOAD_MODELS` map at line ~166 maps `"WPStatusChanged" → StatusTransitionPayload`).
- Depends on WP01 outputs: `ReconciliationReasonCode`, `ReconciliationDiagnostic`.
- Constraints to honour:
  - C-002: no new runtime dependencies.
  - C-001 (reviewer check): tests must NOT modify `_ALLOWED_TRANSITIONS`, `validate_transition`, or `StatusTransitionPayload`.

## Subtasks & Detailed Guidance

### Subtask T009 – Create the six fixture JSON files

- **Purpose**: Lock the binding examples that consumers implement against.
- **Steps**:
  1. Create directory `src/spec_kitty_events/conformance/fixtures/wp_status_changed/`.
  2. Create the six files listed in the success criteria above, using the JSON envelope shape documented in `data-model.md`. Required top-level keys per file: `fixture_id`, `description`, `input`, `expected`.
  3. For the `forward_lifecycle` fixture, structure `input` as `{ "events": [<envelope>, …] }` and `expected` as `{ "outcomes": ["accept", "accept", …] }`. The test will iterate and validate each step.
  4. Use ULID-shaped strings for `event_id` (26 chars from `0-9A-HJKMNP-TV-Z`). Use stable example values; do not generate fresh ULIDs (determinism, NFR-001).
- **Files**: six new JSON files under `src/spec_kitty_events/conformance/fixtures/wp_status_changed/`.
- **Notes**: Keep fixtures small (≤ 80 lines each). Do not include verbose comments inside JSON; rely on `description` field.

### Subtask T010 – Append six manifest entries

- **Purpose**: Make the fixtures discoverable via the existing conformance machinery.
- **Steps**:
  1. Read 2–3 existing entries in `src/spec_kitty_events/conformance/fixtures/manifest.json` to confirm the shape (keys present, ordering, list-vs-dict structure).
  2. Append six entries — one per fixture — preserving existing JSON formatting (indentation, trailing newline). Each entry must include `fixture_id`, `fixture_file`, `event_type: "WPStatusChanged"`, `outcome`, `reason_code`, and `notes`. Cite the relevant FR in `notes` (e.g. `"FR-007(b): review rejection from in_review to planned without force"`).
  3. Run `python -c "import json; json.load(open('src/spec_kitty_events/conformance/fixtures/manifest.json'))"` to confirm the file is still valid JSON.
- **Files**: `src/spec_kitty_events/conformance/fixtures/manifest.json`.

### Subtask T011 – Test: each fixture matches its declared outcome

- **Purpose**: Prove every fixture is correct against the live validator and consumer-reconciler logic.
- **Steps**:
  1. Create `tests/test_wp_status_changed_contract_fixtures.py`.
  2. Define a small `consumer_reconcile(projection_lane, prior_event_log, event)` helper (≤30 lines) that returns either a `ReconciliationDiagnostic` (for drift / replay-by-shape / terminal-replay) or `None` (for normal-flow events). The helper implements contract §5/§6.
  3. Define a small `is_replay(event_id, seen_event_ids)` helper (3 lines).
  4. Parametrize a test over each manifest entry tagged `event_type == "WPStatusChanged"` and loaded from `wp_status_changed/`. For each fixture:
     - `outcome == "accept"`: every event in `input.events` (or the single event in `input.event`) must pass `validate_transition`.
     - `outcome == "reject"`: the offending event must fail `validate_transition`.
     - `outcome == "reconcile"`: `consumer_reconcile` returns a `ReconciliationDiagnostic` whose `reason_code` matches the manifest entry.
     - `outcome == "idempotency_skip"`: `is_replay` returns True for the offending `event_id` against the provided seen-set.
  5. Run `uv run pytest tests/test_wp_status_changed_contract_fixtures.py --durations=10` and confirm runtime < 5 seconds (NFR-001).
- **Files**: `tests/test_wp_status_changed_contract_fixtures.py`.

### Subtask T012 – Coverage assertion: every reason code has a fixture

- **Purpose**: Lock D-6 / FR-013 into CI.
- **Steps**:
  1. In `tests/test_wp_status_changed_contract_fixtures.py`, add `test_every_reason_code_has_a_fixture`:
     ```python
     from spec_kitty_events.status import RECONCILIATION_REASON_CODES

     def test_every_reason_code_has_a_fixture() -> None:
         manifest = _load_manifest()
         covered = {
             entry["reason_code"]
             for entry in manifest
             if entry.get("event_type") == "WPStatusChanged" and entry.get("reason_code")
         }
         missing = set(RECONCILIATION_REASON_CODES) - covered
         assert not missing, f"reason codes without a fixture: {sorted(missing)}"
     ```
  2. Confirm all four codes are represented across the six fixtures. Codes that need explicit fixtures:
     - `from_lane_mismatch_replay` — add a 7th fixture or extend an existing one if the initial six only cover `from_lane_mismatch_drift`. Easiest: rename `replay_idempotency_skip.json` to also cover the `from_lane_mismatch_replay` reconciliation case OR add a separate `from_lane_mismatch_replay.json`. Pick whichever keeps the fixture set small. If you add a 7th file, update T009 → T010 → T011 accordingly.
     - `terminal_replay_skipped` — add an 8th fixture if needed. Same rule.
     - `from_lane_mismatch_drift` — covered by fixture #5.
     - `unforced_rollback_without_review_ref` — covered by fixture #3.
  3. Decision rule: prefer extending an existing fixture's manifest entry if the fixture exercises the same payload, otherwise add a small dedicated fixture file. Update tasks.md if the fixture count grows.
- **Files**: `tests/test_wp_status_changed_contract_fixtures.py`, possibly one or two additional fixture files.

### Subtask T013 – Full suite + mypy

- **Purpose**: Ensure no regressions in the broader test surface or in type checking.
- **Steps**:
  1. `uv run pytest` — full suite green.
  2. `mypy --strict src/spec_kitty_events/` — green.
  3. Schema drift check passes if the existing entrypoint is wired into pytest.
- **Files**: none (verification step).

## Branch Strategy

- Planning base: `main`.
- Final merge target: `main`.
- Worktree allocation: this WP runs in its own lane (likely `lane-c`); see `lanes.json` after finalize-tasks.

## Test Strategy

- `tests/test_wp_status_changed_contract_fixtures.py` is the WP's primary test surface.
- Full `uv run pytest` and `mypy --strict` for regression coverage.

## Definition of Done

- [ ] Six (or 6–8) fixture JSON files under `wp_status_changed/`
- [ ] Manifest entries added with `outcome` and `reason_code`
- [ ] `tests/test_wp_status_changed_contract_fixtures.py` written and passing
- [ ] `test_every_reason_code_has_a_fixture` passes (all four `ReconciliationReasonCode` values covered)
- [ ] Aggregate fixture-suite runtime < 5 seconds
- [ ] Full `uv run pytest` passes
- [ ] `mypy --strict src/spec_kitty_events/` passes

## Risks

- **Manifest schema drift** if existing entries omit `reason_code` field. Mitigated by reading existing entries first and treating `reason_code: null` as the explicit non-applicable value.
- **Reconciler helper drift** from the contract document. Mitigated by writing the helper in the test file itself, with a comment block citing contract §5/§6.

## Reviewer Guidance

- Each fixture's declared outcome MUST be derivable from contract document semantics; spot-check by reading the contract.
- All four `ReconciliationReasonCode` values appear in at least one manifest entry.
- The test runtime is under 5 seconds (`--durations=10` output).
- No changes to `_ALLOWED_TRANSITIONS`, `validate_transition`, or `StatusTransitionPayload` (C-001 reviewer check).

## Activity Log

- 2026-05-17T15:33:45Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2650 – Started implementation via action command
