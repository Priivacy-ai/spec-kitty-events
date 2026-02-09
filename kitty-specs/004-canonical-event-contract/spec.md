# Feature Specification: Canonical Event Contract Consolidation

**Feature Branch**: `004-canonical-event-contract`
**Created**: 2026-02-09
**Status**: Draft
**Input**: Phase 2 of the local-first runtime convergence plan. Freezes the canonical event schema for the entire mission and WP lifecycle. spec-kitty-events is the CONTRACT AUTHORITY.

## User Scenarios & Testing

### User Story 1 - Lifecycle Reducer Determinism (Priority: P1)

A consumer (spec-kitty CLI or spec-kitty-saas) replays a sequence of mission and WP lifecycle events through the reference reducer. Regardless of the physical order events arrive (as long as causal order is preserved), the reducer produces an identical final state. This guarantees that local projections (status.json, dashboard views) are reproducible from the event log alone.

**Why this priority**: Determinism is the foundational guarantee of the entire event-sourced architecture. Without it, local and server projections diverge and the convergence plan collapses. Every other feature builds on this.

**Independent Test**: Replay the same event set in 100 random physical orderings (preserving causal constraints). Assert all runs produce byte-identical projected state.

**Acceptance Scenarios**:

1. **Given** a set of 20 lifecycle events with known causal relationships, **When** the reducer processes them in 100 different physical orderings that each respect causal order, **Then** all 100 runs produce identical ReducedMissionState output.
2. **Given** a mission event log containing MissionStarted, PhaseEntered, WPStatusChanged, GatePassed, and MissionCompleted events, **When** the reducer folds them, **Then** the final state shows the mission as completed with all WPs in their terminal lanes.
3. **Given** an empty event sequence, **When** the reducer processes it, **Then** the result is a valid empty ReducedMissionState with no WPs and no anomalies.

---

### User Story 2 - Conflict Precedence Rules (Priority: P1)

When concurrent lifecycle events create ambiguity (e.g., one node cancels a mission while another re-opens it), the reducer resolves conflicts using explicit, documented precedence rules rather than arbitrary ordering. This ensures predictable behavior in distributed scenarios.

**Why this priority**: Without clear precedence rules, concurrent operations produce nondeterministic state. The three precedence rules (cancel > re-open, rollback creates new event, idempotent dedup) are acceptance criteria 2E-04 through 2E-06.

**Independent Test**: Submit concurrent cancel and re-open events for the same mission. Assert cancel always wins regardless of physical order.

**Acceptance Scenarios**:

1. **Given** a mission in "active" state, **When** concurrent MissionCancelled and a re-activating event arrive (same Lamport clock), **Then** the reducer resolves to cancelled state regardless of physical event order (F-Reducer-001).
2. **Given** a WP in for_review state with active implementation on another WP, **When** a ReviewRollback event is emitted, **Then** the rollback creates a new event in the log (never modifies or overwrites the original WP status events) (F-Reducer-002).
3. **Given** an event sequence, **When** the same event (identical event_id) is delivered twice, **Then** the reducer produces the same final state as if the event were delivered once (F-Reducer-003).

---

### User Story 3 - Typed Lifecycle Event Payloads (Priority: P1)

Consumers receive events with validated, typed payloads for each lifecycle event type. Each event type has a Pydantic model that enforces required fields and constraints at construction time, preventing malformed events from entering the system.

**Why this priority**: Typed payloads are the contract surface. Without them, consumers must defensively parse opaque dicts, leading to bugs and divergent implementations across repos.

**Independent Test**: Construct each lifecycle event type with valid data (assert success) and with missing/invalid fields (assert ValidationError).

**Acceptance Scenarios**:

1. **Given** valid mission metadata, **When** a MissionStartedPayload is constructed, **Then** it contains mission_id, mission_type, and initial_phase fields.
2. **Given** a PhaseEntered event payload with a phase name not in the mission's defined phases, **When** validated, **Then** construction succeeds (phase name validation is the mission DSL's concern, not the contract's).
3. **Given** a MissionCancelledPayload, **When** constructed without a reason field, **Then** a ValidationError is raised.
4. **Given** a ReviewRollbackPayload, **When** constructed, **Then** it contains the review_ref linking to the review that triggered rollback, the target phase to rollback to, and the affected WP IDs.

---

### User Story 4 - Event Envelope Versioning (Priority: P2)

The Event envelope includes an explicit schema_version field. Consumers can detect which version of the envelope they received and handle version differences. The versioning rules guarantee backward compatibility within major versions.

**Why this priority**: Version evolution is essential for long-term maintainability but not blocking for initial Phase 2 delivery. The version field must be present from day one so consumers can rely on it.

**Independent Test**: Create events with version "1.0.0". Verify consumers can read the version field. Verify that adding a new optional field (simulating minor version bump) does not break deserialization of existing events.

**Acceptance Scenarios**:

1. **Given** an Event with schema_version "1.0.0", **When** serialized and deserialized, **Then** the schema_version field round-trips correctly.
2. **Given** an Event serialized under version "1.0.0" (without a new optional field), **When** deserialized by a consumer that knows version "1.1.0" (which added the optional field), **Then** deserialization succeeds with the new field defaulting to None.
3. **Given** an Event serialized under version "1.1.0" (with the new optional field populated), **When** deserialized by a consumer that only knows version "1.0.0", **Then** deserialization succeeds (unknown fields are ignored per Pydantic behavior).

---

### User Story 5 - Data Tier Annotation (Priority: P2)

Each event carries a data_tier annotation (0-4) that controls its sync scope in the progressive data sharing model. Tier 0 events never leave the local machine; higher tiers enable broader sharing.

**Why this priority**: The tier annotation must be present on every event from day one so that future sync protocols can filter correctly. However, sync itself is Phase 4 (out of scope).

**Independent Test**: Construct events with each tier value (0-4). Assert values outside 0-4 are rejected. Assert default tier is 0 (local-only).

**Acceptance Scenarios**:

1. **Given** an event constructed without specifying data_tier, **When** inspected, **Then** data_tier defaults to 0 (local-only).
2. **Given** data_tier value of 5, **When** used to construct an event, **Then** a ValidationError is raised.
3. **Given** events with tiers 0 through 4, **When** serialized and deserialized, **Then** tier values round-trip correctly.

---

### User Story 6 - Projection Replay Correctness (Priority: P2)

The reference reducer can rebuild projection state (status.json equivalent, dashboard state) entirely from the event log. Rebuilding from scratch produces output identical to incrementally maintained state.

**Why this priority**: Projection replay correctness is acceptance criteria 2E-07 and 2E-08. It proves that the event log is the single source of truth.

**Independent Test**: Build projection state incrementally as events arrive. Rebuild from scratch by replaying all events. Assert outputs are identical.

**Acceptance Scenarios**:

1. **Given** a mission event log, **When** the lifecycle reducer rebuilds WP status state from the full event sequence, **Then** the output matches the existing reduce_status_events() output for the same WP events.
2. **Given** a mission event log with MissionStarted, multiple PhaseEntered, and MissionCompleted events, **When** the lifecycle reducer projects mission state, **Then** the projection includes current phase, mission status (active/completed/cancelled), and all WP states.
3. **Given** an incrementally-maintained projection and a from-scratch replay, **When** compared, **Then** they produce identical output.

---

### Edge Cases

- What happens when a MissionCancelled event arrives for an already-completed mission? Anomaly flagged, mission stays completed -- completed is terminal.
- What happens when a PhaseEntered event references a phase that doesn't match the mission type? Accepted by the contract -- phase validation is the mission DSL's responsibility.
- What happens when events arrive with Lamport clocks that go backward? Reducer sorts by Lamport clock -- out-of-order arrival is handled by the sort step.
- What happens when a correlation_id is missing on a mission-level event? ValidationError -- correlation_id is required on all events.
- What happens when a WPStatusChanged event's from_lane doesn't match the WP's current state in the reducer? Anomaly flagged, not fatal -- existing behavior from Feature 003.

## Requirements

### Functional Requirements

**Event Envelope Extension**

- **FR-001**: The Event model MUST include a `correlation_id` field (ULID format, required) that groups all events belonging to the same mission execution.
- **FR-002**: The Event model MUST include a `schema_version` field (string, required, semver format e.g. "1.0.0") indicating the envelope schema version.
- **FR-003**: The Event model MUST include a `data_tier` field (integer, 0-4, default 0) indicating the progressive data sharing tier.
- **FR-004**: All existing Event fields (event_id, event_type, aggregate_id, payload, timestamp, node_id, lamport_clock, causation_id, project_uuid, project_slug) MUST be preserved with their current validation rules.

**Lifecycle Event Type Payloads**

- **FR-005**: The library MUST define a `MissionStartedPayload` model with fields: mission_id (str), mission_type (str), initial_phase (str), and actor (str).
- **FR-006**: The library MUST define a `MissionCompletedPayload` model with fields: mission_id (str), mission_type (str), final_phase (str), and actor (str).
- **FR-007**: The library MUST define a `MissionCancelledPayload` model with fields: mission_id (str), reason (str, required), actor (str), and cancelled_wp_ids (List[str]).
- **FR-008**: The library MUST define a `PhaseEnteredPayload` model with fields: mission_id (str), phase_name (str), previous_phase (Optional[str]), and actor (str).
- **FR-009**: The library MUST define a `ReviewRollbackPayload` model with fields: mission_id (str), review_ref (str, required), target_phase (str), affected_wp_ids (List[str]), and actor (str).
- **FR-010**: All lifecycle payload models MUST be frozen Pydantic v2 models (ConfigDict(frozen=True)), consistent with existing Event and gate payload patterns.
- **FR-011**: Existing GatePassed/GateFailed payloads and WPStatusChanged handling from Features 002 and 003 MUST remain unchanged and compatible.

**Envelope Versioning Rules**

- **FR-012**: The initial schema_version MUST be "1.0.0".
- **FR-013**: Minor version increments (e.g., 1.0.0 to 1.1.0) MUST only add optional fields with defaults -- existing events remain valid.
- **FR-014**: Major version increments MUST be reserved for breaking changes (removing fields, changing field types, changing required/optional status).
- **FR-015**: The library MUST provide a `SCHEMA_VERSION` constant reflecting the current envelope version.

**Idempotency and Ordering Primitives**

- **FR-016**: The lifecycle reducer MUST deduplicate events by event_id (same behavior as existing dedup_events()).
- **FR-017**: The lifecycle reducer MUST sort events by (lamport_clock, timestamp, event_id) for deterministic total ordering (same behavior as existing status_event_sort_key()).
- **FR-018**: The lifecycle reducer MUST use causation_id chains to establish event lineage when resolving causal relationships.

**Reference Lifecycle Reducer**

- **FR-019**: The library MUST provide a `reduce_lifecycle_events()` function that folds a sequence of events into a `ReducedMissionState`.
- **FR-020**: The ReducedMissionState MUST include: mission_id, mission_status (active/completed/cancelled), current_phase, wp_states (reusing existing WPState model), anomalies, event_count, and last_processed_event_id.
- **FR-021**: The reducer MUST delegate WP status reduction to the existing `reduce_status_events()` function from Feature 003.
- **FR-022**: The reducer MUST track mission-level state transitions: MissionStarted sets active, PhaseEntered updates current_phase, MissionCompleted sets completed, MissionCancelled sets cancelled.

**Precedence Rules**

- **FR-023**: Cancel beats re-open: when concurrent MissionCancelled and re-activating events share the same Lamport clock for the same mission, the reducer MUST resolve to cancelled state.
- **FR-024**: Rollback creates new event: ReviewRollback MUST append a new event to the log -- it MUST NOT modify or overwrite any existing events.
- **FR-025**: Duplicate delivery is idempotent: processing the same event (same event_id) multiple times MUST produce the same final state as processing it once.

**LWW Restriction Policy**

- **FR-026**: The library MUST NOT use Last-Writer-Wins semantics for any lifecycle state field (mission status, WP lane, phase).
- **FR-027**: LWW MAY be used only for non-authoritative register fields (user preferences, cursor positions, cache hints). This feature does not implement any LWW registers but documents the restriction.

**Test Fixtures**

- **FR-028**: The library MUST include test fixture F-Reducer-001: concurrent cancel vs re-open events, asserting cancel wins.
- **FR-029**: The library MUST include test fixture F-Reducer-002: review rollback during active implementation, asserting new event created (no overwrite).
- **FR-030**: The library MUST include test fixture F-Reducer-003: duplicate event delivery, asserting idempotent final state.

### Key Entities

- **Event (extended)**: The immutable event envelope. Extended with correlation_id, schema_version, and data_tier fields. Preserves all existing fields from Feature 001.
- **MissionStartedPayload**: Typed payload for mission initiation events. Contains mission identity and initial phase.
- **MissionCompletedPayload**: Typed payload for mission completion events. Contains final phase reached.
- **MissionCancelledPayload**: Typed payload for mission cancellation. Contains reason and list of affected WP IDs.
- **PhaseEnteredPayload**: Typed payload for phase transition events. Contains phase name and optional previous phase.
- **ReviewRollbackPayload**: Typed payload for review rollback events. Contains review reference, target phase, and affected WPs.
- **ReducedMissionState**: The projected state produced by the lifecycle reducer. Contains mission status, current phase, and delegated WP states.
- **MissionStatus**: Enumeration of mission lifecycle states: active, completed, cancelled.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Reducer determinism verified -- same event set replayed in 100 random physical orderings (preserving causal order) produces identical final state every time.
- **SC-002**: All three precedence rule fixtures (F-Reducer-001, F-Reducer-002, F-Reducer-003) pass with zero failures across 1000 test iterations.
- **SC-003**: Every lifecycle event type payload model rejects construction with missing required fields (100% coverage of required field validation).
- **SC-004**: Event envelope round-trip: serialize to dict and deserialize back produces identical Event for all lifecycle event types including new fields (correlation_id, schema_version, data_tier).
- **SC-005**: Projection replay produces identical output whether built incrementally or from-scratch replay, verified for mission sequences containing all event types.
- **SC-006**: Backward compatibility: events serialized without new optional fields (simulating older versions) deserialize successfully with defaults applied.
- **SC-007**: Published as tagged release on main branch with all tests passing and coverage at 99% or above.
- **SC-008**: All consumer-facing models are typed, frozen, and pass mypy --strict validation.

## Assumptions

- The Event model extension (adding correlation_id, schema_version, data_tier) is backward-compatible because all new fields either have defaults or are required on new events only. Existing test fixtures will be updated to include the new required fields.
- Phase validation (whether a phase name is valid for a mission type) is the mission DSL's responsibility (spec-kitty Phase 1B), not the event contract's. The contract accepts any phase name string.
- The lifecycle reducer delegates WP-level reduction to the existing Feature 003 reducer, avoiding duplication.
- The MissionCancelled precedence rule (cancel beats re-open) applies at the mission level. At the WP level, the existing Feature 003 CANCELED terminal lane behavior already handles this.
- correlation_id is required on ALL events (not optional) because every event belongs to a mission execution context.
