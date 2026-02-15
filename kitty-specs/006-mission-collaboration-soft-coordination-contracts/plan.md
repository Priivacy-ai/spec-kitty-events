# Implementation Plan: Mission Collaboration Soft Coordination Contracts

**Branch**: `006-mission-collaboration-soft-coordination-contracts` | **Date**: 2026-02-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/006-mission-collaboration-soft-coordination-contracts/spec.md`

## Summary

Add 14 typed event payloads, 3 identity/target models, a dual-mode collaboration reducer, and conformance artifacts to `spec-kitty-events`. This is the contract authority for N-participant mission collaboration with advisory (soft) coordination semantics. The reducer operates in strict mode (default, for live traffic — rejects unknown participants) or permissive mode (for replay/import — records anomalies). All artifacts follow existing patterns from Features 001–005.

## Technical Context

**Language/Version**: Python >=3.10 (mypy target 3.10, dev on 3.11)
**Primary Dependencies**: Pydantic >=2.0.0,<3.0.0, python-ulid >=1.1.0
**Storage**: N/A (pure data contracts, no persistence)
**Testing**: pytest >=7.0.0, pytest-cov >=4.0.0, hypothesis >=6.0.0, mypy --strict
**Target Platform**: Library (pip-installable, cross-platform)
**Project Type**: Single Python package
**Performance Goals**: Reducer processes 10K events in <1s (pure CPU, no I/O)
**Constraints**: mypy --strict, 98%+ coverage, frozen Pydantic v2 models, no new external dependencies
**Scale/Scope**: 14 new event types, ~35 new exports, ~550-630 LOC in collaboration.py

## Constitution Check

*No constitution file found at `.kittify/memory/constitution.md`. Gate skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/006-mission-collaboration-soft-coordination-contracts/
├── plan.md              # This file
├── research.md          # Phase 0 output — design decisions and rationale
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — developer integration guide
├── contracts/           # Phase 1 output — API contracts
│   └── collaboration-api.md    # Collaboration module public API contract
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/spec_kitty_events/
├── collaboration.py          # NEW — 14 payloads, 3 identity models, reducer, constants
├── models.py                 # UNCHANGED — Event envelope (reused)
├── lifecycle.py              # UNCHANGED — Mission lifecycle (composed by consumers)
├── status.py                 # UNCHANGED — Status reducer (sort/dedup reused)
├── gates.py                  # UNCHANGED
├── __init__.py               # MODIFIED — Add ~35 new exports
├── schemas/
│   ├── generate.py           # MODIFIED — Register 17 new models for schema gen
│   ├── participant_identity.schema.json      # NEW
│   ├── auth_principal_binding.schema.json    # NEW
│   ├── focus_target.schema.json              # NEW
│   ├── participant_invited_payload.schema.json        # NEW (14 payload schemas)
│   ├── participant_joined_payload.schema.json         # NEW
│   ├── participant_left_payload.schema.json           # NEW
│   ├── presence_heartbeat_payload.schema.json         # NEW
│   ├── drive_intent_set_payload.schema.json           # NEW
│   ├── focus_changed_payload.schema.json              # NEW
│   ├── prompt_step_execution_started_payload.schema.json   # NEW
│   ├── prompt_step_execution_completed_payload.schema.json # NEW
│   ├── concurrent_driver_warning_payload.schema.json       # NEW
│   ├── potential_step_collision_detected_payload.schema.json # NEW
│   ├── warning_acknowledged_payload.schema.json       # NEW
│   ├── comment_posted_payload.schema.json             # NEW
│   ├── decision_captured_payload.schema.json          # NEW
│   └── session_linked_payload.schema.json             # NEW
└── conformance/
    ├── validators.py         # MODIFIED — Register collaboration payloads
    └── fixtures/
        ├── manifest.json     # MODIFIED — Add collaboration fixture entries
        └── collaboration/    # NEW — Collaboration fixture directory
            ├── valid/
            │   ├── 3-participant-overlap.json         # NEW
            │   ├── step-collision-llm.json            # NEW
            │   ├── decision-with-comments.json        # NEW
            │   ├── participant-lifecycle.json          # NEW
            │   └── session-linking.json               # NEW
            └── invalid/
                ├── unknown-participant-strict.json     # NEW
                └── missing-required-fields.json        # NEW

tests/
├── unit/
│   └── test_collaboration.py    # NEW — Unit tests for all payloads + reducer
└── property/
    └── test_collaboration_determinism.py  # NEW — Hypothesis property tests
```

**Structure Decision**: Single `collaboration.py` module following the same one-module-per-domain pattern as `lifecycle.py` (459 LOC) and `status.py` (540 LOC). Internal sections:
1. Constants / event-type strings
2. Identity models (ParticipantIdentity, AuthPrincipalBinding, FocusTarget)
3. Payload models (14)
4. Reducer output models (ReducedCollaborationState, CollaborationAnomaly, UnknownParticipantError)
5. Reducer + helper functions

**Split trigger**: If collaboration.py exceeds ~700 LOC or reducer/helpers dominate and hurt testability, split into `collaboration/` package with `payloads.py`, `reducer.py`, `models.py`.

## Key Design Decisions

### D1: Single collaboration.py (not a sub-package)

**Decision**: All collaboration Python API surface lives in one file.
**Rationale**: Consistent with lifecycle.py / status.py pattern. Estimated ~550-630 LOC — well under the 700 LOC split trigger. Cross-team discoverability: developers find all collaboration contracts in one place.
**Alternative rejected**: `collaboration/` sub-package — premature for initial delivery, adds import complexity.

### D2: Strict mode as default

**Decision**: `reduce_collaboration_events(events, mode="strict")` — strict is the default.
**Rationale**: Live traffic is the primary use case. Unknown participant = hard error prevents silent data corruption. Permissive mode is opt-in for replay/import tooling.
**Implementation**: `mode` parameter as `Literal["strict", "permissive"]` with default `"strict"`. Type narrowing in reducer body.

### D3: Reuse existing sort/dedup utilities

**Decision**: Import `status_event_sort_key()` and `dedup_events()` from `status.py`.
**Rationale**: Same ordering semantics (lamport_clock, timestamp, event_id). No reason to duplicate. Already tested and proven deterministic.

### D4: Warning payloads are multi-actor

**Decision**: `ConcurrentDriverWarningPayload` and `PotentialStepCollisionDetectedPayload` use `participant_ids: list[str]` (not `participant_id: str`).
**Rationale**: These events describe a risk condition involving multiple participants. Single-actor payloads use `participant_id`. This distinction is explicit in FR-003.

### D5: Acknowledgement enum is `continue|hold|reassign|defer`

**Decision**: `WarningAcknowledgedPayload.acknowledgement` is `Literal["continue", "hold", "reassign", "defer"]`.
**Rationale**: Actionable responses that consumers can switch on. Maps to real coordination decisions: proceed as-is, pause, hand off, postpone.

### D6: Canonical envelope mapping convention

**Decision**: `Event.aggregate_id = mission_id`, `Event.correlation_id = mission_run_id`.
**Rationale**: Consistent with how lifecycle events use `aggregate_id = "mission/M001"`. The `correlation_id` carries the run-specific identifier so replays can be scoped.

### D7: AuthPrincipalBinding as roster-level, not per-event

**Decision**: `auth_principal_id` appears on `ParticipantJoinedPayload` (optional), not on every event.
**Rationale**: Auth binding is established once at join time. Repeating it on every event is wasteful and creates a consistency risk. The binding is a roster-level association.

## Deliverables

### Deliverable 1: Collaboration Module (`collaboration.py`)

**Scope**: 14 payload models, 3 identity/target models, event constants, reducer with strict/permissive modes, output state model, anomaly model, exception.
**Estimated LOC**: 550-630
**Files**: `src/spec_kitty_events/collaboration.py`
**Dependencies**: `models.py` (Event), `status.py` (sort/dedup utilities)

### Deliverable 2: Exports and Package Integration

**Scope**: ~35 new symbols in `__init__.py`, schema generation registration, conformance validator updates.
**Files**: `src/spec_kitty_events/__init__.py`, `src/spec_kitty_events/schemas/generate.py`, `src/spec_kitty_events/conformance/validators.py`

### Deliverable 3: JSON Schemas

**Scope**: 17 new `.schema.json` files (14 payloads + 3 identity/target models), generated from Pydantic models.
**Files**: `src/spec_kitty_events/schemas/*.schema.json`

### Deliverable 4: Conformance Fixtures

**Scope**: 7 fixture files (5 valid, 2 invalid), manifest.json updates.
**Files**: `src/spec_kitty_events/conformance/fixtures/collaboration/`

### Deliverable 5: Tests

**Scope**: Unit tests for all 14 payloads, reducer strict/permissive modes, all edge cases. Property tests for reducer determinism with Hypothesis.
**Files**: `tests/unit/test_collaboration.py`, `tests/property/test_collaboration_determinism.py`

### Deliverable 6: Documentation

**Scope**: README, COMPATIBILITY.md, CHANGELOG updates with collaboration event reference, reducer contract, envelope mapping, SaaS-authoritative participation model.
**Files**: `README.md`, `COMPATIBILITY.md`, `CHANGELOG.md`

## Complexity Tracking

*No constitution violations to justify.*
