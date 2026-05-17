# Backward-Transition Contract

**Mission ID**: 01KRV52CHQFTJ522SMP9NDNZ41
**Slug**: backward-transition-contract-01KRV52C
**Mission Type**: software-dev
**Target Branch**: main
**Created**: 2026-05-17

## Purpose

Document and codify forced backward lane transitions (the review-rejection family) in the canonical `WPStatusChanged` event contract so that the CLI emit path, SaaS materializer, durable drain, and any future consumer can cite a single source of truth for what a legitimate review-rejection event looks like on the wire.

## Context

Cross-repo planning issue `Priivacy-ai/spec-kitty-planning#16` reported a contradiction: the CLI emits `WPStatusChanged` events with `force=False` for user-deliberate backward lane moves (review rejections), SaaS rejects them as graph-invalid transitions, and the durable drain then parks them as `terminal_failed` infrastructure debris that poisons `/health/ready/`. The evidence pack at `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json` (22 stuck events, 17 per-target WP histories) shows the wire shape: `from_lane=approved → to_lane=planned`, `force=False`, `reason="move-task: approved -> planned"`.

The contract layer already supports `force=True + reason` semantics in `WPStatusChangedPayload` and `ForceMetadata`; what is missing is a normative statement enumerating the review-rejection transition family, a recommended `reason` field shape, and conformance fixtures the sibling repos can reference.

This mission is the foundation. Two sibling missions in `spec-kitty` (CLI emit path) and `spec-kitty-saas` (materializer + drain/readiness) consume what this mission lands. A fourth mission in `spec-kitty-planning` closes out tracking after all three code repos merge.

## User Scenarios & Testing

### Primary Scenario — Contract Author Documents the Review-Rejection Family

**Actor**: A contract author working in `spec-kitty-events`.
**Trigger**: A downstream consumer (CLI implementer, SaaS materializer maintainer) asks "what does a legitimate review-rejection event look like on the wire?".
**Happy-path outcome**: The author points at a single anchor — the module docstring of `src/spec_kitty_events/status.py` (or a referenced contract markdown) — that enumerates the review-rejection transition family, states the `force=True + reason` requirement, and points to a conformance fixture in `tests/unit/` showing a full lifecycle including one review-rejection round-trip. The consumer can answer their own question in under two minutes without reading any sibling repo's source.

### Secondary Scenario — Sibling Repo Implementer Writes a New Test

**Actor**: An implementer in `spec-kitty` or `spec-kitty-saas` writing a regression test for the planning#16 fix.
**Trigger**: The implementer needs a canonical wire fixture for a review-rejection event.
**Happy-path outcome**: The implementer imports or copies a fixture from `tests/unit/test_fixtures.py` (or equivalent) shipping in this repo. The fixture passes the public `WPStatusChanged` model and exercises the review-rejection transition family. The implementer's test runs in the sibling repo against the published package without code duplication.

### Exception Path — Unforced Backward Transition

**Actor**: A consumer running `validate_status_transition()` against an event with `from_lane=in_review, to_lane=planned, force=False`.
**Trigger**: The CLI emit path emits an unforced backward transition (today's bug).
**Outcome**: `validate_status_transition()` rejects the event as graph-invalid. The negative conformance fixture proves this behavior. Consumers that reject such events (SaaS materializer) are contract-conformant, not buggy.

### Acceptance Rule (must always hold)

For every transition in the review-rejection family (`{in_review → planned, approved → planned, for_review → planned, in_progress → planned}`):

- The event MUST set `force=True`.
- The event MUST set a non-empty `reason`.
- An unforced backward transition is contract-invalid and consumers MAY reject it as a graph violation.
- The contract does not introduce a new event type — review rejection is expressed via existing `WPStatusChanged` events.

## Domain Language

| Term | Meaning |
|---|---|
| Review-rejection family | The set of legitimate forced backward lane transitions originating from a user-deliberate rewind: `{in_review → planned, approved → planned, for_review → planned, in_progress → planned}`. |
| Forced backward transition | A `WPStatusChanged` event where `to_lane` precedes `from_lane` in the canonical lane progression AND `force=True` with a non-empty `reason`. |
| Unforced backward transition | A `WPStatusChanged` event where `to_lane` precedes `from_lane` AND `force=False`. Contract-invalid; consumers MAY reject. |
| Bootstrap-planned event | A pre-existing legitimate forced family (`* → planned`) representing initial seeding, already documented by `is_bootstrap_planned_event()`. Distinct from review-rejection. |
| Audit reason shape | Recommended (normative on the contract side, binding on CLI side) string format for the `reason` field of a forced backward transition. Includes lane pair and an optional human-supplied feedback reference. |

Synonyms to avoid: "rewind", "revert", "undo", "rollback". The contract uses "backward transition" (general) and "review-rejection family" (specific set).

## Functional Requirements

| ID | Description | Status |
|---|---|---|
| FR-001 | The `WPStatusChanged` contract documents the **review-rejection transition family** as the named set `{in_review → planned, approved → planned, for_review → planned, in_progress → planned}`. Documentation lives in the `src/spec_kitty_events/status.py` module docstring AND in a referenced contract markdown under `docs/` (or equivalent location resolved during plan). | Required |
| FR-002 | The contract documentation states explicitly that for every transition in the review-rejection family, `force=True` and a non-empty `reason` are REQUIRED. | Required |
| FR-003 | The contract documentation states explicitly that **unforced backward transitions are contract-invalid** and consumers MAY reject them as graph violations. This validates current SaaS materializer rejection behavior. | Required |
| FR-004 | A positive conformance fixture for the **review-rejection cycle** exists: a full minimal lifecycle including one review rejection (`planned → claimed → in_progress → for_review → in_review → planned (force=True) → claimed → in_progress → for_review → in_review → approved`). Fixture lives under `tests/unit/` or the equivalent fixture surface. | Required |
| FR-005 | A positive conformance fixture for the **approved-rewind case** exists (`approved → planned (force=True)`), matching the shape seen in the planning#16 evidence pack but written as a synthetic minimal fixture. No copying of any of the 22 dev evidence events. | Required |
| FR-006 | A negative conformance fixture exists for an unforced `in_review → planned` event, with an assertion that `validate_status_transition()` (or the equivalent public validator) classifies it as invalid. | Required |
| FR-007 | `tests/unit/test_status.py` covers: (a) review-rejection family is accepted with `force=True + reason`; (b) review-rejection family is rejected with `force=False`; (c) `reason` is required when `force=True` for backward transitions. | Required |
| FR-008 | `tests/unit/test_fixtures.py` (or the file the plan identifies) loads the new positive fixtures and asserts they parse cleanly through the public `WPStatusChanged` model. | Required |
| FR-009 | The contract does NOT introduce a new event type. Review rejection is expressed entirely through existing `WPStatusChanged` events with `force=True + reason`. | Required |
| FR-010 | The module docstring or referenced contract doc contains a normative recommendation for the `reason` field shape used by CLI emitters: include the lane pair and SHOULD include a human-supplied feedback reference. Recommended canonical form: `"backward rewind: <from> -> <to>: <feedback-ref>"` (the colon-separated feedback ref is optional but recommended). | Required |
| FR-011 | A reviewer reading `status.py` (module docstring) plus the new conformance fixtures can answer "what does a legitimate review-rejection event look like on the wire?" in under two minutes without reading any sibling repo's source. | Required |
| FR-012 | All new fixtures and tests live under `tests/unit/` and are runnable as `uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q` from the events repo root. | Required |
| FR-013 | The contract docstring cross-links to the sibling-mission anchor points so the CLI (`spec-kitty`) and SaaS (`spec-kitty-saas`) implementers can cite a stable URL/path. | Required |

## Non-Functional Requirements

| ID | Description | Measurable Threshold | Status |
|---|---|---|---|
| NFR-001 | Test runtime for the new fixture- and validator-driven tests | New test files complete in under 10 seconds wall-clock under `uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q` on a developer laptop. | Required |
| NFR-002 | Fixture minimality | Each new fixture file contains only the fields the contract validator inspects plus the lifecycle shape. Median fixture event payload has ≤ 12 keys. | Required |
| NFR-003 | Test reliability | New tests are deterministic — zero flakes across 10 consecutive `uv run pytest tests/unit/test_status.py tests/unit/test_fixtures.py -q` runs. | Required |
| NFR-004 | Schema compatibility | All public `WPStatusChanged` consumers (CLI, SaaS materializer, durable drain) continue to parse pre-existing fixtures without modification. Schema-drift check (`mypy --strict` + committed JSON schema generation) passes with zero changes. | Required |
| NFR-005 | Documentation discoverability | The `status.py` module docstring (or top-of-file docstring) references the contract markdown by relative path. The markdown references the conformance fixtures by relative path. The fixtures reference back to the markdown by relative path comment. | Required |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | Target branch is `main`; all work merges back to `main`. | Required |
| C-002 | This repo does not depend on `spec-kitty` or `spec-kitty-saas`. Dependency direction is downstream-only. | Required |
| C-003 | Wire shape of `WPStatusChangedPayload` MUST NOT change. No new required fields, no removed fields, no renamed fields. Documentation, normative recommendations, fixtures, and tests are the deliverables. | Required |
| C-004 | `SPEC_KITTY_ENABLE_SAAS_SYNC=1` must be set for any CLI invocation in this working tree. | Required |
| C-005 | No mutation of any of the 22 dev evidence events in `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json`. Fixtures are synthetic minimal sequences written from scratch. | Required |
| C-006 | All public-model surface changes are additive. No breaking changes to existing `WPStatusChanged` consumers. | Required |

## Success Criteria

| ID | Statement | Measurement |
|---|---|---|
| SC-001 | A downstream contract reader can identify the legitimate review-rejection event shape in under 2 minutes by reading only the events-repo sources. | Time-boxed walkthrough by a reviewer unfamiliar with the change. |
| SC-002 | Sibling-mission tests in `spec-kitty` and `spec-kitty-saas` can be authored against the new fixtures with zero contract duplication. | Cross-repo test review confirms fixture references rather than copies. |
| SC-003 | Negative-case behavior (unforced backward transition rejected by the contract validator) is provable by running one named test. | A single `pytest -k` invocation against the new negative test passes. |
| SC-004 | All pre-existing tests in `tests/unit/` continue to pass. | `uv run pytest tests/unit/ -q` exit code is 0. |
| SC-005 | Schema drift check passes with zero changes to the committed JSON schemas. | Schema generation step in CI (or local equivalent) produces a clean diff. |

## Key Entities

| Entity | Notes |
|---|---|
| `WPStatusChangedPayload` | Existing Pydantic model in `src/spec_kitty_events/status.py`. Wire-shape unchanged. |
| `ForceMetadata` | Existing Pydantic model representing `force=True + actor + reason`. Wire-shape unchanged. |
| `validate_status_transition()` | Existing validator. Documented behavior reaffirmed; no behavior change unless the analyze phase surfaces a gap. |
| Review-rejection family | Named conceptual set documented in module docstring. Not a new class. |
| Conformance fixtures | New test-only artifacts under `tests/unit/` (or where the plan resolves). Loaded via existing fixture mechanism. |

## Assumptions

- The existing `validate_status_transition()` already correctly rejects unforced backward transitions in the matrix check. Plan phase will verify; if a gap is found, FR-007(b) test will surface it and the gap is in-scope as a contract-completeness fix.
- The committed JSON schema generation, mypy --strict gate, and pytest are the standing quality gates the charter requires. No new gates are introduced by this mission.
- The phrase "or equivalent" in FR-001/FR-008 is left for the plan phase to resolve to a concrete path; the spec does not pre-commit to a specific markdown filename.
- Forward-transition guard semantics in any consumer are out of scope for this mission. This mission documents a backward-transition family; forward-transition guard preservation is enforced by the sibling missions in `spec-kitty` and `spec-kitty-saas`.

## Dependencies

- **Downstream**: `spec-kitty` (CLI emit path, mission 2 of this program) and `spec-kitty-saas` (materializer + drain/readiness, mission 3) depend on this mission's published contract surface.
- **Upstream**: None inside the spec-kitty-events repo. External upstream is planning#16 (problem statement, evidence pack).

## Out of Scope

- Any changes to CLI `move-task` behavior (covered by mission 2 in `spec-kitty`).
- Any changes to SaaS materializer, projection, durable drain, or readiness (covered by mission 3 in `spec-kitty-saas`).
- Closing `Priivacy-ai/spec-kitty-planning#16` (covered by mission 4 in `spec-kitty-planning`).
- Any mutation of the 22 dev evidence events.
- Introducing a new event type (explicitly forbidden by FR-009).

## References

- Cross-repo planning issue: https://github.com/Priivacy-ai/spec-kitty-planning/issues/16
- Evidence pack (read-only): `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json`
- Implementation prompt: `/Users/robert/spec-kitty-dev/spec-kitty-20260517-161351-nNtfEd/IMPLEMENTATION_PROMPT_planning16.md`
- Existing contract surface: `src/spec_kitty_events/status.py` (`WPStatusChangedPayload`, `ForceMetadata`, `validate_status_transition`, `is_bootstrap_planned_event`).
