# Implementation Plan: WPStatusChanged Backward Transition Contract

**Branch**: `main` (planning + merge target)
**Date**: 2026-05-17
**Spec**: [/Users/robert/spec-kitty-dev/spec-kitty-20260517-165635-WafwWc/spec-kitty-events/kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/spec.md](./spec.md)

## Summary

Lock the canonical WPStatusChanged contract for backward transitions, force, actor, from_lane mismatch, replay, and reconciliation. Ship a contract document, a new `ReconciliationDiagnostic` Pydantic model, conformance fixtures + manifest entries, tests, and a README link. No changes to `_ALLOWED_TRANSITIONS`, `validate_transition`, or any field on `StatusTransitionPayload`.

## Technical Context

**Language/Version**: Python 3.10+ (pyproject.toml: `requires-python = ">=3.10"`)
**Primary Dependencies**: `pydantic>=2.0.0,<3.0.0`, `python-ulid>=1.1.0` (already declared). Dev: `pytest>=7.0.0`, `hypothesis>=6.0.0`, `mypy>=1.0.0`. Conformance: `jsonschema>=4.21.0,<5.0.0`.
**Storage**: N/A (library only). Conformance fixtures live on disk under `src/spec_kitty_events/conformance/fixtures/`.
**Testing**: `pytest` (with hypothesis where applicable), conformance fixture validation, schema drift checks, `mypy --strict`. Run with `uv run pytest`.
**Target Platform**: Python library; consumed by spec-kitty CLI and spec-kitty-saas server.
**Project Type**: Single Python package (`src/spec_kitty_events/`).
**Performance Goals**: Deterministic; new conformance suite < 5s aggregate (NFR-001).
**Constraints**: No new runtime dependencies (C-002). No change to `_ALLOWED_TRANSITIONS`, `TERMINAL_LANES`, `validate_transition`, or `StatusTransitionPayload` field set (C-001). All new models frozen + `extra="forbid"` (C-003).
**Scale/Scope**: Library serving low-volume event flows (CLI emits dozens of events per mission; SaaS materializes hundreds of events per drain batch).

## Charter Check

| Charter element | Status | Notes |
|----|----|----|
| Intent: publish canonical event envelopes, conformance fixtures, compatibility rules | PASS | This mission codifies the contract and ships fixtures. |
| Languages/Frameworks: Python 3.10+, Pydantic, committed JSON Schemas, conformance fixtures | PASS | New `ReconciliationDiagnostic` is Pydantic frozen + extra="forbid"; new JSON Schema file will be committed; fixtures added. |
| Testing: pytest, hypothesis, schema drift checks, conformance fixture validation | PASS | All test surfaces exercised. |
| Quality gates: pytest + schema generation + mypy --strict | PASS | New code passes mypy --strict; schema regen committed. |
| Review Policy: deliberate compatibility review for any envelope/payload/schema/fixture change | PASS | Mission is a contract-locking effort; compatibility review is the point. |
| Performance Targets: deterministic, efficient | PASS | New helpers are pure functions; NFR-001 caps fixture runtime at < 5s. |
| Deployment Constraints: ships as Python library; live consumers rely on fail-closed compat | PASS | New diagnostic is additive (does not change `StatusTransitionPayload`); existing consumers stay valid. |

No violations. No Complexity Tracking needed.

## Phase 0 outputs

See [research.md](./research.md).

## Phase 1 outputs

- [data-model.md](./data-model.md) — entities (`ReconciliationDiagnostic`, `ReconciliationReasonCode`) and how they relate to existing `StatusTransitionPayload`.
- [contracts/](./contracts/) — `wp-status-changed.contract.md` (the contract document that will be promoted to `docs/contracts/wp-status-changed.md` during implementation) and `reconciliation_diagnostic.schema.json` (the JSON Schema for the new payload).
- [quickstart.md](./quickstart.md) — five-minute consumer onboarding.

## Project Structure

### Documentation (this feature)

```
kitty-specs/wpstatuschanged-backward-transition-contract-01KRV7SC/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── spec.md
├── contracts/
│   ├── wp-status-changed.contract.md
│   └── reconciliation_diagnostic.schema.json
├── tasks.md                       (created by /spec-kitty.tasks)
└── tasks/                         (per-WP prompts created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── status.py                      (CHANGED: add ReconciliationDiagnostic + ReconciliationReasonCode; add docstring links to contract)
├── schemas/
│   └── reconciliation_diagnostic.schema.json    (NEW: JSON Schema generated from the Pydantic model)
└── conformance/
    ├── fixtures/
    │   └── wp_status_changed/      (NEW directory with six fixture JSON files)
    │       ├── forward_lifecycle.json
    │       ├── review_rejection_in_review_to_planned.json
    │       ├── backward_no_force_no_review_ref.json
    │       ├── backward_with_force_and_reason.json
    │       ├── from_lane_mismatch_drift.json
    │       └── replay_idempotency_skip.json
    └── fixtures/manifest.json      (CHANGED: append six new fixture entries with outcome+reason_code)

docs/contracts/
└── wp-status-changed.md            (NEW: canonical contract document promoted from contracts/wp-status-changed.contract.md)

tests/
├── test_reconciliation_diagnostic_model.py     (NEW)
├── test_wp_status_changed_contract_fixtures.py (NEW)
└── test_contract_docstring_links.py            (NEW: asserts status.py docstrings name the contract path)

README.md                            (CHANGED: add "Contracts" section linking docs/contracts/wp-status-changed.md per NFR-004)
```

**Structure Decision**: Single-package Python project. New code lives in existing `src/spec_kitty_events/` directories; new contract doc under `docs/contracts/`. No new top-level directories.

## Branch contract (restated)

- Current branch: `main`
- Planning / base branch: `main`
- Merge target branch: `main`
- `branch_matches_target`: true. No additional branch coordination needed; spec-kitty merge will land WP lanes back onto `main`.

## Complexity Tracking

(No violations to justify.)

## Next step

`/spec-kitty.tasks --mission wpstatuschanged-backward-transition-contract-01KRV7SC`
