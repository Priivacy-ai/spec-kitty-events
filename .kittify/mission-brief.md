# Mission Brief: Backward-Transition Contract — Events Repo Layer

## Objective

Establish the canonical contract surface in `spec-kitty-events` for **user-deliberate backward lane transitions** in `WPStatusChanged` events (the review-rejection family: `in_review → planned`, `approved → planned`, etc.). The contract layer must make it unambiguous to every downstream consumer (CLI emitter in `spec-kitty`, SaaS materializer/projection in `spec-kitty-saas`, durable drain in `spec-kitty-saas`) what a legitimate backward transition looks like on the wire and what an illegitimate one looks like.

This is the foundation mission. Two sibling missions in `spec-kitty` (CLI emit path) and `spec-kitty-saas` (materializer + drain/readiness) will consume the conformance contract this mission lands. A fourth mission in `spec-kitty-planning` will close out tracking once all three code repos merge.

## Cross-Repo Issue

- Planning issue: https://github.com/Priivacy-ai/spec-kitty-planning/issues/16 — "Research: backward-transition contract has no shared model across CLI, SaaS materializer, and drain-health"
- Evidence pack: `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json` (22 `stuck_events`, 17 `per_target_wp_history`)
- Ground truth: stuck events on `spec-kitty-dev` show the bug — `from_lane=approved → to_lane=planned` with `force=False` and `reason="move-task: approved -> planned"`. The CLI emit path knows it is a rewind but does not promote `force=True`.

## Current State of the Contract

`src/spec_kitty_events/status.py` already supports forced transitions:
- `WPStatusChangedPayload.force: bool = False`
- `WPStatusChangedPayload.reason: str | None` — required when `force=True` (`force=True requires a non-empty reason`)
- `ForceMetadata` with `force: Literal[True]`, `actor: str`, `reason: str`
- `validate_status_transition()` already rejects unforced backward moves via the matrix check
- `is_bootstrap_planned_event()` documents one legitimate forced-backward family (bootstrap `* → planned`)

What is **missing**:
- A normative section in the contract docs (and a canonical fixture set) that explicitly enumerates the **review-rejection family** of legitimate forced backward transitions (`in_review → planned`, `approved → planned`).
- A clear statement that unforced backward transitions are contract-invalid (forward-only outside the listed exceptions), so SaaS materializer rejection of `force=False` backward events is correct contract enforcement, not a bug to paper over.
- Conformance fixtures for `WPStatusChanged` that exercise the review-rejection cycle (`planned → claimed → in_progress → for_review → in_review → planned → claimed → …`).
- Tests that codify the audit-reason shape we expect for review rejection (`reason` must contain a backward-rewind audit string; we recommend the canonical form `backward rewind: <from> -> <to>: <human-supplied feedback ref>` or similar normative shape).

## Functional Requirements

- **FR-001**: The `WPStatusChanged` contract MUST document the **review-rejection transition family** as a named set of legitimate forced backward transitions: `{in_review → planned, approved → planned, for_review → planned, in_progress → planned}`. Documentation belongs in `src/spec_kitty_events/status.py` module docstring and in a referenced contract markdown under `docs/` (or equivalent) so CLI and SaaS authors can cite the same source.
- **FR-002**: The contract MUST state explicitly that for every transition in the review-rejection family, `force=True` and `reason` MUST be set, and `actor` SHOULD be present (already enforced via `ForceMetadata` when present).
- **FR-003**: The contract MUST state explicitly that **unforced backward transitions are contract-invalid**. Consumers are entitled to reject them as graph violations (this validates current SaaS materializer behavior).
- **FR-004**: A canonical conformance fixture for the **review-rejection cycle** MUST exist (one full happy-path lifecycle that includes one review rejection: `planned → claimed → in_progress → for_review → in_review → planned (force=True) → claimed → in_progress → for_review → in_review → approved`). Fixture lives under `tests/unit/` or the existing fixture surface.
- **FR-005**: A canonical conformance fixture for the **approved-rewind** case (`approved → planned (force=True)`) MUST exist, matching the shape seen in the evidence pack but as a synthetic, minimal fixture — not by copying any of the 22 dev events.
- **FR-006**: A **negative** conformance fixture MUST exist showing an unforced `in_review → planned` event and asserting that `validate_status_transition()` (or the equivalent contract validator) classifies it as invalid.
- **FR-007**: `tests/unit/test_status.py` MUST cover: (a) the review-rejection family is accepted with `force=True + reason`; (b) the same family is rejected with `force=False`; (c) `reason` is required when `force=True` for backward transitions (already covered for general force, must remain covered for backward specifically).
- **FR-008**: `tests/unit/test_fixtures.py` (or equivalent) MUST load the new fixtures and assert they parse cleanly through the public `WPStatusChanged` model.
- **FR-009**: The contract MUST NOT introduce a new event type. The review-rejection family is expressed through existing `WPStatusChanged` events with `force=True` plus the canonical `reason` shape. No `WPStatusReverted` or similar new event is added.
- **FR-010**: The module docstring or a referenced contract doc MUST contain a normative recommendation for the `reason` field shape used by the CLI emit path: include both the lane transition and a human-supplied feedback reference (for example: `"backward rewind: in_review -> planned: feedback://<mission>/<wp>/<feedback-id>.md"`). This is normative on the contract side (consumers MAY parse) and binding on the CLI side (mission 2 will adopt it).

## Non-Functional Requirements

- **NFR-001**: All new tests MUST run under `uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q` from the repo root and complete in under 10 seconds.
- **NFR-002**: All new fixtures MUST be minimal — only the fields the contract validator inspects plus the lifecycle shape. No noise fields.
- **NFR-003**: No mutation of any of the 22 dev evidence events in `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json`. Fixtures are written from scratch as synthetic minimal sequences.
- **NFR-004**: All public model changes MUST be additive — no breaking changes to existing `WPStatusChanged` consumers (CLI / SaaS / drain).
- **NFR-005**: Contract docs MUST be cross-linked from `status.py` module docstring so the CLI and SaaS sibling missions can cite a stable anchor.

## Constraints

- **C-001**: Target branch is `main`. All work merges back to `main`.
- **C-002**: Do not introduce any dependency on `spec-kitty` (CLI) or `spec-kitty-saas` from this repo. Direction of dependency is downstream-only.
- **C-003**: Do not modify the wire shape of `WPStatusChangedPayload` (no new required fields, no removed fields). Documentation, normative recommendations, fixtures, and tests are the deliverables — not schema changes.
- **C-004**: `SPEC_KITTY_ENABLE_SAAS_SYNC=1` must be set for any CLI invocation in this working tree.

## Success Criteria

- A reviewer of `Priivacy-ai/spec-kitty-planning#16` can read `status.py` (module docstring) plus the new conformance fixtures and answer the question "what does a legitimate review-rejection event look like on the wire?" in under two minutes without reading the CLI source.
- The new fixture-driven tests fail before the change and pass after.
- No existing test fails.
- Downstream missions (`spec-kitty` CLI, `spec-kitty-saas` materializer, `spec-kitty-saas` drain) can cite this mission's docstring/fixture by file path as their source of truth for the contract.

## Out of Scope

- Changes to CLI `move-task` behavior (mission 2 in `spec-kitty`).
- Changes to SaaS materializer / drain / readiness (mission 3 in `spec-kitty-saas`).
- Closing planning#16 (mission 4 in `spec-kitty-planning`).
- Any mutation of the 22 dev evidence events.

## Test Plan

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260517-161351-nNtfEd/spec-kitty-events
uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q
```

If a `tests/test_payload_reconciliation.py` is added or already present, include it.

## Mission Type

`software-dev`. Output is contract code (docstrings, fixtures, tests). Mission proceeds with the standard specify → plan → tasks → analyze → implement-review → mission-review → merge loop.
