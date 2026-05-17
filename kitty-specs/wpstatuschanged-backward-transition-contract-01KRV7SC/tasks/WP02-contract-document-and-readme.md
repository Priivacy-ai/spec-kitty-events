---
work_package_id: WP02
title: Contract document and README integration
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-010
- FR-011
- FR-012
- FR-013
- NFR-003
- NFR-004
- C-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-wpstatuschanged-backward-transition-contract-01KRV7SC
base_commit: e670502aa049450b83cb2506a54d3cb2a3ab34fb
created_at: '2026-05-17T15:25:51.288891+00:00'
subtasks:
- T006
- T007
- T008
phase: Phase 1 - Contract document
agent: "claude:opus-4-7:curator-carla:implementer"
shell_pid: "1154"
history:
- timestamp: '2026-05-17T15:25:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/contracts/
execution_mode: code_change
lane: planned
owned_files:
- docs/contracts/wp-status-changed.md
- README.md
- tests/test_contract_docstring_links.py
review_status: ''
reviewed_by: ''
role: implementer
tags: []
---

# Work Package Prompt: WP02 – Contract Document and README Integration

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load curator-carla
```

If your environment does not support that slash command, run:

```bash
spec-kitty agent profile show curator-carla
```

---

## ⚠️ IMPORTANT: Review Feedback Status

If `review_status` above says `has_feedback`, scroll to **Review Feedback** below and treat each item as a must-do. Update `review_status: acknowledged` when you start.

## Review Feedback

*(empty)*

---

## Objectives & Success Criteria

Publish the canonical contract document at `docs/contracts/wp-status-changed.md`, link it from `README.md`, and add a docstring-link assertion test. The contract content is already drafted at `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/contracts/wp-status-changed.contract.md` — most of this WP is "promote the draft, link from README, lock the link with a test."

Done means:
- `docs/contracts/wp-status-changed.md` exists, is ≤ 600 lines (NFR-003), and contains:
  - The transition matrix table (FR-001 / C-005) reproducing `_ALLOWED_TRANSITIONS` from `src/spec_kitty_events/status.py:342-368`.
  - Explicit statement that review-rollback transitions DO NOT require force=True; they require `review_ref` (FR-002).
  - Explicit statement that `actor` is audit-only and `actor="user"` is NOT a policy escape hatch (FR-003).
  - `from_lane` mismatch semantics with the two reason codes `from_lane_mismatch_replay` and `from_lane_mismatch_drift` (FR-004).
  - Replay semantics: primary key `event_id`, fallback `(mission_slug, wp_id, sequence)`, idempotent skip without diagnostic (FR-005).
  - Consumer responsibilities section naming CLI, SaaS materializer, and drain worker (FR-011).
  - Diagnostic surface separation subsection: reconciliation diagnostics are NOT infra failures and MUST be reported on a separate health surface (FR-012).
  - Closed `reason_code` enum table; addition requires doc update AND a fixture (FR-013).
- `README.md` has a "Contracts" section (top-level `##`) that links to `docs/contracts/wp-status-changed.md`. The link text must include `wp-status-changed.md` so `grep "wp-status-changed.md" README.md` returns ≥ 1 hit (NFR-004).
- `tests/test_contract_docstring_links.py` exists and asserts that `src/spec_kitty_events/status.py` references the string `docs/contracts/wp-status-changed.md` in its module docstring (FR-010 lock).
- `uv run pytest tests/test_contract_docstring_links.py` passes.
- `uv run pytest` (full suite) passes (NFR-002).

Mission requirements covered: FR-001, FR-002, FR-003, FR-004, FR-005, FR-010 (lock test), FR-011, FR-012, FR-013 (doc part), NFR-003, NFR-004, C-005.

## Context & Constraints

- Spec: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/spec.md`.
- Plan: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/plan.md`.
- Research: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/research.md` (Q5 explains why `docs/contracts/` is the canonical home).
- Draft contract: `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/contracts/wp-status-changed.contract.md` — this is the substance to promote.
- Constraints to honour:
  - C-005: the contract MUST cite `_ALLOWED_TRANSITIONS` either by reproducing the table or by quoting the literal line range (`src/spec_kitty_events/status.py:342-368`). The draft already includes the table. Verify it matches the live code before publishing.
  - NFR-003: ≤ 600 lines. Run `wc -l docs/contracts/wp-status-changed.md` and trim if over budget.

## Subtasks & Detailed Guidance

### Subtask T006 – Promote the draft to `docs/contracts/wp-status-changed.md`

- **Purpose**: Move the canonical contract into the published-docs home.
- **Steps**:
  1. Create `docs/contracts/` if missing.
  2. Copy `kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/contracts/wp-status-changed.contract.md` to `docs/contracts/wp-status-changed.md`.
  3. Verify the transition table matches `src/spec_kitty_events/status.py:342-368`. If `_ALLOWED_TRANSITIONS` has been edited since the draft was written, update the table. Add a comment block at the top: `<!-- Generated from src/spec_kitty_events/status.py:342-368 (verbatim). Update when the matrix changes. -->`.
  4. Run `wc -l docs/contracts/wp-status-changed.md` and confirm ≤ 600.
- **Files**: `docs/contracts/wp-status-changed.md`.

### Subtask T007 – Link the contract from `README.md`

- **Purpose**: Downstream consumers find the contract from the README.
- **Steps**:
  1. Open `README.md`.
  2. Add a top-level `## Contracts` section near the top (or just before any existing `## License` section). Content:
     ```markdown
     ## Contracts

     Canonical event-shape and semantic contracts for consumers of this package:

     - [`docs/contracts/wp-status-changed.md`](docs/contracts/wp-status-changed.md) — `WPStatusChanged` event semantics, including the allowed-transition matrix, force/actor/review_ref rules, replay/idempotency, and reconciliation diagnostics.
     ```
  3. Verify `grep -c "wp-status-changed.md" README.md` returns at least 1.
- **Files**: `README.md`.

### Subtask T008 – Add docstring-link assertion test

- **Purpose**: Lock the WP01 docstring requirement so future refactors do not silently drop the contract pointer.
- **Steps**:
  1. Create `tests/test_contract_docstring_links.py`:
     ```python
     from pathlib import Path

     STATUS_PY = Path(__file__).resolve().parents[1] / "src" / "spec_kitty_events" / "status.py"
     CONTRACT_PATH = "docs/contracts/wp-status-changed.md"


     def test_status_py_docstring_references_contract() -> None:
         text = STATUS_PY.read_text()
         assert CONTRACT_PATH in text, (
             f"src/spec_kitty_events/status.py must reference the canonical contract path "
             f"{CONTRACT_PATH!r} (FR-010)."
         )
     ```
  2. Run `uv run pytest tests/test_contract_docstring_links.py` and confirm it passes (it will pass only after WP01 lands the docstring update).
- **Files**: `tests/test_contract_docstring_links.py`.
- **Notes**: This test verifies cross-WP integration. WP01 owns the docstring; WP02 owns the lock test. Order WP02 review AFTER WP01 merges to avoid a transient red.

## Branch Strategy

- Planning base branch: `main`.
- Final merge target: `main`.

## Test Strategy

- `uv run pytest tests/test_contract_docstring_links.py` (smoke).
- `uv run pytest` (full suite, NFR-002).

## Definition of Done

- [ ] `docs/contracts/wp-status-changed.md` published, ≤ 600 lines, contains transition matrix + FR-002..FR-005 / FR-011..FR-013 content
- [ ] `README.md` has a `## Contracts` section linking to the contract
- [ ] `tests/test_contract_docstring_links.py` exists and passes after WP01
- [ ] `uv run pytest` passes

## Risks

- **README merge conflicts** if WP03 also touches README. Mitigated by owning the README in this WP only and not touching it elsewhere.
- **Transition table drift** between the doc and `status.py`. Mitigated by the `<!-- Generated from … -->` comment and the C-005 reviewer check.

## Reviewer Guidance

- `wc -l docs/contracts/wp-status-changed.md` ≤ 600.
- `grep -c "wp-status-changed.md" README.md` ≥ 1.
- Spot-check the transition table against `_ALLOWED_TRANSITIONS` in `status.py:342-368`.
- Verify the four required reason codes appear in the doc's enum table.

## Activity Log

- 2026-05-17T15:25:52Z – claude:opus-4-7:curator-carla:implementer – shell_pid=1154 – Assigned agent via action command
