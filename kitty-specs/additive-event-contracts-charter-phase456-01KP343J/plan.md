# Implementation Plan: Additive Event Contracts for Charter Phase 4/5/6

**Branch**: `main` | **Date**: 2026-04-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/additive-event-contracts-charter-phase456-01KP343J/spec.md`
**Mission ID**: `01KP343JBG2V7WSWSDJ0HD76BR`

## Summary

Add two new domain modules (`profile_invocation.py`, `retrospective.py`) to `spec-kitty-events` with three new event types (`ProfileInvocationStarted`, `RetrospectiveCompleted`, `RetrospectiveSkipped`), plus two reserved constants. Integrate into the conformance suite, validator dispatch, package exports, and auto-generated JSON schemas. Bump package version from `3.0.0` to `3.1.0`. All changes are additive-only with full backward compatibility.

## Technical Context

**Language/Version**: Python 3.10+ (mypy target), 3.11 for tests
**Primary Dependencies**: Pydantic v2 (existing), Hypothesis (property tests)
**Storage**: N/A (pure event contract library)
**Testing**: pytest + Hypothesis, `mypy --strict`, dual-layer conformance (Pydantic + JSON Schema)
**Target Platform**: Python library (pip installable)
**Project Type**: Single Python package (`src/spec_kitty_events/`)
**Performance Goals**: < 1ms per payload validation (NFR-001)
**Constraints**: All models `ConfigDict(frozen=True, extra="forbid")`, additive-only, no envelope changes
**Scale/Scope**: 2 new modules, 3 new payload models, 2 reserved constants, ~200 lines of new source code, ~300 lines of new tests

## Charter Check

*No charter file found at `.kittify/charter/charter.md`. Section skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/additive-event-contracts-charter-phase456-01KP343J/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal — patterns well-established)
├── data-model.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist (all passing)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── profile_invocation.py     # NEW: WP01 — domain module
├── retrospective.py          # NEW: WP02 — domain module
├── __init__.py               # MODIFIED: WP04 — re-export new symbols
├── conformance/
│   ├── validators.py         # MODIFIED: WP04 — dispatch map entries
│   ├── loader.py             # MODIFIED: WP03 — new categories
│   └── fixtures/
│       ├── manifest.json     # MODIFIED: WP03 — new fixture entries
│       ├── profile_invocation/
│       │   ├── valid/        # NEW: WP03
│       │   │   ├── profile_invocation_started_minimal.json
│       │   │   └── profile_invocation_started_full.json
│       │   └── invalid/      # NEW: WP03
│       │       ├── profile_invocation_started_missing_profile_slug.json
│       │       └── profile_invocation_started_empty_action.json
│       └── retrospective/
│           ├── valid/        # NEW: WP03
│           │   ├── retrospective_completed_minimal.json
│           │   ├── retrospective_completed_with_artifact.json
│           │   └── retrospective_skipped.json
│           └── invalid/      # NEW: WP03
│               ├── retrospective_completed_missing_actor.json
│               └── retrospective_skipped_empty_reason.json
└── schemas/
    ├── profile_invocation_started_payload.schema.json  # NEW: WP04
    ├── retrospective_completed_payload.schema.json     # NEW: WP04
    └── retrospective_skipped_payload.schema.json       # NEW: WP04

tests/
├── unit/
│   ├── test_profile_invocation.py    # NEW: WP01 — domain-local unit tests
│   └── test_retrospective.py         # NEW: WP02 — domain-local unit tests
├── test_profile_invocation_conformance.py  # NEW: WP03 — conformance tests
└── test_retrospective_conformance.py       # NEW: WP03 — conformance tests
```

**Structure Decision**: Single project, existing layout. Two new domain modules alongside 11 existing ones. No structural changes.

## Design Decisions

### D1: Separate domain modules, not extension of existing ones

Profile invocation and retrospective are distinct contract surfaces with different lifecycle semantics. Profile invocation tracks runtime execution context; retrospective tracks post-merge closeout. They do not share state, reducers, or event type sets. Separate modules follow the established one-domain-per-file pattern (cf. `lifecycle.py`, `glossary.py`, `dossier.py`, `mission_next.py`).

### D2: Reuse existing value objects

`RuntimeActorIdentity` (from `mission_next.py`) is reused for `ProfileInvocationStartedPayload.actor` rather than defining a new actor model. `ProvenanceRef` (from `dossier.py`) is reused for `RetrospectiveCompletedPayload.artifact_ref`. This keeps the value object surface flat and avoids near-duplicate models.

**Cross-module import**: New modules MUST import value objects directly from their defining modules, not from `spec_kitty_events.__init__`. The `__init__.py` eagerly imports all domain modules, so importing from it would create circular imports. This matches the existing repo pattern (e.g., `mission_audit.py` imports `ProvenanceRef` from `spec_kitty_events.dossier`, not from the package root).

- `profile_invocation.py`: `from spec_kitty_events.mission_next import RuntimeActorIdentity`
- `retrospective.py`: `from spec_kitty_events.dossier import ProvenanceRef`

### D3: No reducers in this tranche

- **Retrospective**: Two terminal signals (`Completed`, `Skipped`). No state machine — a mission either has one or the other, or neither. A projection can be a simple `Optional[Literal["completed", "skipped"]]` without a reducer.
- **Profile invocation**: Only `Started` is defined; `Completed`/`Failed` are reserved. A reducer that tracks only start events with no completion is not useful. Defer until the full lifecycle is contracted.

### D4: Reserved constants follow NextStepPlanned pattern

`PROFILE_INVOCATION_COMPLETED` and `PROFILE_INVOCATION_FAILED` are defined as string constants with a `# Reserved — payload contract deferred` comment. They are included in the `PROFILE_INVOCATION_EVENT_TYPES` frozen set so that future payload additions don't change the type set contract. No conformance fixtures are created for reserved types.

### D5: trigger_source as Literal, not free-form string

The retrospective `trigger_source` field uses `Literal["runtime", "operator", "policy"]` because the set of triggers is small, known, and unlikely to grow rapidly. This enables downstream projections to filter/group by trigger source without string matching. If a new trigger source is needed, it requires a spec amendment and minor version bump — which is the correct level of friction for a contract change.

### D6: Domain schema version 3.1.0

Both new modules use `3.1.0` as their domain schema version, aligning with the package version bump. This follows the existing pattern where domain versions track when the domain was introduced (e.g., `AUDIT_SCHEMA_VERSION = "2.5.0"`). The envelope `schema_version` remains `3.0.0`.

## Work Package Structure

### Dependency Graph

```
WP01 ─────┐
           ├──> WP03 ──> WP04
WP02 ─────┘
```

- **WP01** and **WP02** execute in parallel (no dependencies between them)
- **WP03** depends on WP01 and WP02 (needs domain modules to exist for fixture validation)
- **WP04** depends on WP03 (needs conformance infrastructure before wiring package-wide integration)

### WP01: Profile Invocation Domain + Unit Tests

**FR coverage**: FR-001, FR-002, FR-007, FR-008, FR-013, FR-014
**Constraint coverage**: C-001, C-006, C-007

**Deliverables**:

| File | Action | Description |
|------|--------|-------------|
| `src/spec_kitty_events/profile_invocation.py` | Create | Domain module: constants (`PROFILE_INVOCATION_STARTED`, reserved `_COMPLETED`/`_FAILED`), `PROFILE_INVOCATION_SCHEMA_VERSION`, `PROFILE_INVOCATION_EVENT_TYPES` frozenset, `ProfileInvocationStartedPayload` model |
| `tests/unit/test_profile_invocation.py` | Create | Unit tests: valid construction (minimal + full), required field enforcement, `min_length` constraints, `extra="forbid"` rejection, frozen immutability, `RuntimeActorIdentity` embedding, reserved constant existence, type set membership |

**Acceptance gate**: `pytest tests/unit/test_profile_invocation.py` passes, `mypy --strict src/spec_kitty_events/profile_invocation.py` passes.

### WP02: Retrospective Domain + Unit Tests

**FR coverage**: FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-013, FR-015
**Constraint coverage**: C-001, C-006, C-008

**Deliverables**:

| File | Action | Description |
|------|--------|-------------|
| `src/spec_kitty_events/retrospective.py` | Create | Domain module: constants (`RETROSPECTIVE_COMPLETED`, `RETROSPECTIVE_SKIPPED`), `RETROSPECTIVE_SCHEMA_VERSION`, `RETROSPECTIVE_EVENT_TYPES` frozenset, `RetrospectiveCompletedPayload`, `RetrospectiveSkippedPayload` models |
| `tests/unit/test_retrospective.py` | Create | Unit tests: valid construction (minimal + full with artifact_ref), required field enforcement, `trigger_source` Literal validation, `skip_reason` min_length, `extra="forbid"` rejection, frozen immutability, `ProvenanceRef` embedding |

**Acceptance gate**: `pytest tests/unit/test_retrospective.py` passes, `mypy --strict src/spec_kitty_events/retrospective.py` passes.

### WP03: Shared Conformance + Fixture Integration

**FR coverage**: FR-012
**NFR coverage**: NFR-004
**Constraint coverage**: C-002

**Deliverables**:

| File | Action | Description |
|------|--------|-------------|
| `src/spec_kitty_events/conformance/loader.py` | Modify | Add `"profile_invocation"` and `"retrospective"` to `_VALID_CATEGORIES` |
| `src/spec_kitty_events/conformance/fixtures/profile_invocation/valid/*.json` | Create | 2 valid fixtures (minimal, full) |
| `src/spec_kitty_events/conformance/fixtures/profile_invocation/invalid/*.json` | Create | 2 invalid fixtures (missing profile_slug, empty action) |
| `src/spec_kitty_events/conformance/fixtures/retrospective/valid/*.json` | Create | 3 valid fixtures (completed minimal, completed with artifact, skipped) |
| `src/spec_kitty_events/conformance/fixtures/retrospective/invalid/*.json` | Create | 2 invalid fixtures (missing actor, empty skip_reason) |
| `src/spec_kitty_events/conformance/fixtures/manifest.json` | Modify | Add 9 fixture entries for new event types |
| `tests/test_profile_invocation_conformance.py` | Create | Conformance tests: load fixtures, validate via `validate_event()`, assert expected_valid matches |
| `tests/test_retrospective_conformance.py` | Create | Conformance tests: load fixtures, validate via `validate_event()`, assert expected_valid matches |

**Acceptance gate**: `pytest tests/test_profile_invocation_conformance.py tests/test_retrospective_conformance.py` passes. All fixtures load without error. Invalid fixtures produce appropriate violations.

**Note**: WP03 imports from the domain modules created in WP01/WP02 but does NOT register them in `validators.py` — that's WP04. Conformance tests in WP03 will use direct model validation, not the `validate_event()` dispatch. The dispatch wiring happens in WP04.

**Correction**: Actually, conformance tests use `validate_event()` which requires dispatch registration. Two options:
1. WP03 conformance tests use direct Pydantic model construction instead of `validate_event()`.
2. WP03 includes the validator dispatch entries.

**Resolution**: WP03 conformance tests validate fixtures using direct Pydantic model instantiation (same pattern used in early domain conformance tests before dispatch was wired). WP04 adds the dispatch entries and verifies that `validate_event()` works end-to-end. This keeps WP03 independent of WP04.

### WP04: Package Integration + Schema + Version Bump

**FR coverage**: FR-009, FR-010, FR-011
**NFR coverage**: NFR-002, NFR-003, NFR-005
**Constraint coverage**: C-005

**Deliverables**:

| File | Action | Description |
|------|--------|-------------|
| `src/spec_kitty_events/conformance/validators.py` | Modify | Add entries to `_EVENT_TYPE_TO_MODEL` and `_EVENT_TYPE_TO_SCHEMA` for all 3 new event types |
| `src/spec_kitty_events/__init__.py` | Modify | Import and re-export new constants, payload models, type sets, schema versions; add to `__all__`; bump `__version__` from `"3.0.0"` to `"3.1.0"` |
| `src/spec_kitty_events/schemas/*.schema.json` | Create (generated) | Run `python -m spec_kitty_events.schemas.generate` to create 3 new JSON schema files |
| `pyproject.toml` | Modify | Bump `version` from `"3.0.0"` to `"3.1.0"` |

**Acceptance gate**:
- `python -m spec_kitty_events.schemas.generate --check` passes (zero drift)
- `mypy --strict src/spec_kitty_events/` passes (zero errors on full package)
- `pytest` (full suite) passes with zero failures
- `validate_event()` correctly dispatches for all 3 new event types
- Package imports work: `from spec_kitty_events import ProfileInvocationStartedPayload` succeeds
- Both version surfaces agree: `pyproject.toml` version and `spec_kitty_events.__version__` are both `"3.1.0"`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Circular import between new modules and `mission_next.py`/`dossier.py` | Low | Medium | Import value objects from `__init__.py` or use deferred imports; tested in WP01/WP02 unit tests |
| `_VALID_CATEGORIES` extension breaks existing fixture loading | Very Low | Medium | Additive-only change to a frozenset; existing tests continue to pass unmodified |
| Reserved constants in type set cause unexpected behavior in consumers | Low | Low | Follows `NextStepPlanned` precedent; conformance suite explicitly does NOT create fixtures for reserved types |
| Pydantic v2 schema generation drift for new models | Low | Low | Schema generation is deterministic; `--check` mode catches drift in CI |

## Complexity Tracking

No charter violations. No complexity justification needed.
