# Research: Mission Collaboration Soft Coordination Contracts

**Feature**: 006-mission-collaboration-soft-coordination-contracts
**Date**: 2026-02-15
**Status**: Complete

## R1: Module Organization

**Decision**: Single `collaboration.py` file, not a sub-package.
**Rationale**: Follows established pattern (lifecycle.py = 459 LOC, status.py = 540 LOC). Estimated collaboration.py at 550-630 LOC — under 700 LOC split trigger. Cross-team consistency and discoverability are higher priorities than premature modularization.
**Alternatives considered**:
- `collaboration/` package with `payloads.py`, `reducer.py`, `models.py` — rejected as premature; adds import indirection without current benefit.

## R2: Reducer Mode Design (strict vs permissive)

**Decision**: `mode: Literal["strict", "permissive"]` parameter with `"strict"` as default.
**Rationale**: Live traffic is the primary use case (SaaS-authoritative participation). Unknown participant events are data corruption in live mode. Replay/import tooling needs permissive handling for incomplete historical streams.
**Alternatives considered**:
- Separate reducer functions (`reduce_collaboration_strict()` / `reduce_collaboration_permissive()`) — rejected; 90% of reducer logic is shared, duplication is worse than a mode parameter.
- Callback-based error handling (`on_error: Callable`) — rejected; over-engineered for two well-defined modes.
- Always permissive (like existing lifecycle reducer) — rejected; SaaS-authoritative model requires strict enforcement as the default.

**Implementation approach**: Mode check at validation points within the reducer loop. In strict mode: raise `UnknownParticipantError` (or similar). In permissive mode: append `CollaborationAnomaly` and continue. This is 5-6 `if mode == "strict"` branches in the reducer body — manageable complexity.

## R3: Sort/Dedup Reuse

**Decision**: Import `status_event_sort_key()` and `dedup_events()` from `status.py`.
**Rationale**: Existing functions implement the canonical sort key `(lamport_clock, timestamp.isoformat(), event_id)` which applies identically to collaboration events. Both are pure functions with no status-specific logic. Already proven deterministic by property tests.
**Alternatives considered**:
- Copy/paste into collaboration.py — rejected; violates DRY, creates drift risk.
- Extract to shared `_ordering.py` module — acceptable future refactor but not needed for S1/M1. Both lifecycle.py and collaboration.py importing from status.py is fine.

## R4: Participant Roster as Reducer State

**Decision**: The reducer builds the participant roster from `ParticipantJoined` / `ParticipantLeft` events during reduction. Roster membership is the gate for all subsequent events in strict mode.
**Rationale**: The roster is not provided as an external input — it is derived from the event stream itself. This makes the reducer self-contained and replayable. In strict mode, events that reference non-rostered participants are rejected as they are encountered (processing order matters — sort ensures determinism).
**Alternatives considered**:
- External roster parameter (`reduce_collaboration_events(events, roster=...)`) — rejected; breaks self-containment, introduces external state dependency.
- Pre-scan for all ParticipantJoined events before processing — rejected; breaks the single-pass pipeline pattern and adds complexity. The sorted event stream ensures ParticipantJoined events precede subsequent events from that participant (by Lamport clock ordering).

## R5: FocusTarget as Embedded Model vs Standalone

**Decision**: `FocusTarget` is a standalone frozen Pydantic model embedded in `FocusChangedPayload` and warning payloads.
**Rationale**: Reused across multiple payloads. Standalone model enables JSON Schema generation and independent validation. Follows the `ParticipantIdentity` pattern.
**Alternatives considered**:
- Inline `target_type` + `target_id` fields directly on payloads — rejected; duplicates fields across 4+ payloads, no schema reuse.

## R6: Warning Event Authorship

**Decision**: Warning events (`ConcurrentDriverWarningPayload`, `PotentialStepCollisionDetectedPayload`) use `participant_ids: list[str]` for the affected parties. The `Event.node_id` field identifies which node/process detected and emitted the warning.
**Rationale**: Warnings describe multi-actor risk conditions. The emitter (typically SaaS or an observer process) is not one of the affected participants — it's the system detecting the condition. Using `Event.node_id` for emitter identity and `participant_ids` for affected parties maintains clean separation.
**Alternatives considered**:
- Single `emitted_by: str` field on warning payloads — rejected; `Event.node_id` already serves this purpose. Adding a redundant field creates consistency risk.

## R7: Envelope Mapping Convention

**Decision**: `Event.aggregate_id = mission_id`, `Event.correlation_id = mission_run_id`.
**Rationale**: Lifecycle events already use `aggregate_id = "mission/{id}"`. Collaboration events operate on the same aggregate (the mission). `correlation_id` scopes to a specific run, enabling replay isolation.
**Implementation**: This is a usage convention documented in contracts, not an envelope model change. Conformance fixtures will enforce the pattern. Consumers are responsible for correct envelope construction.

## R8: Conformance Fixture Strategy

**Decision**: 7 fixtures (5 valid scenarios, 2 invalid) covering the required acceptance criteria:
1. **3-participant-overlap** (valid): 3 humans join → active drive intent → shared WP focus → ConcurrentDriverWarning → WarningAcknowledged (continue + hold)
2. **step-collision-llm** (valid): 2 llm_context participants → same WP step execution → PotentialStepCollisionDetected → completion
3. **decision-with-comments** (valid): 3 participants → CommentPosted thread → DecisionCaptured with referenced warning
4. **participant-lifecycle** (valid): Join with auth_principal_id → heartbeats → session link → leave
5. **session-linking** (valid): 1 participant, 2 sessions (CLI + SaaS) → SessionLinked → heartbeats from both
6. **unknown-participant-strict** (invalid): Event from participant_id not in roster — validates strict-mode rejection
7. **missing-required-fields** (invalid): Payload missing participant_id — validates schema rejection

**Rationale**: Covers all 6 user stories, all 3 required acceptance criteria (3+ participants, overlapping intent, strict rejection). Balanced valid/invalid ratio.
