# Feature Specification: Mission Collaboration Soft Coordination Contracts

**Feature Branch**: `006-mission-collaboration-soft-coordination-contracts`
**Created**: 2026-02-15
**Status**: Draft
**Input**: User description: "Add typed payloads, schemas, exports, and reducer semantics for N-participant mission collaboration with advisory coordination. Contract authority for CLI and SaaS. Sprint S1/M1 Step 1."

## User Scenarios & Testing

### User Story 1 — CLI Emits Participant Lifecycle Events (Priority: P1)

A developer opens a CLI session and joins a running mission. The CLI emits `ParticipantJoined` with a structured identity (`participant_id`, `participant_type: "human"`, `display_name`, `session_id`). A second developer joins the same mission from their own CLI session. Both participants are visible in the collaboration state. When the first developer disconnects, a `ParticipantLeft` event is emitted, and the collaboration snapshot updates to show one active participant.

**Why this priority**: Participant lifecycle is the foundation — every other collaboration event depends on knowing who is present. Without typed participant events, there is no collaboration model.

**Independent Test**: Can be tested by constructing `ParticipantJoined` and `ParticipantLeft` payloads, feeding them through the collaboration reducer, and verifying the materialized participant roster.

**Acceptance Scenarios**:

1. **Given** an empty mission with no participants, **When** a `ParticipantJoined` event is processed with `participant_type: "human"`, **Then** the collaboration snapshot shows exactly one active participant with the correct identity fields.
2. **Given** a mission with 2 active participants, **When** one emits `ParticipantLeft`, **Then** the collaboration snapshot shows 1 active participant and the departed participant is recorded in history.
3. **Given** a participant has already joined, **When** a duplicate `ParticipantJoined` with the same `participant_id` arrives, **Then** the reducer records an anomaly and does not create a second participant entry.

---

### User Story 2 — Concurrent Drive Intent Without Hard Rejection (Priority: P1)

Two developers are both actively driving a mission. Developer A sets `DriveIntentSet(intent: "active")` and focuses on WP03. Developer B also sets active drive intent and focuses on WP03. The system emits a `ConcurrentDriverWarning` because both active drivers share the same focus target. Neither developer is blocked — the warning is advisory. Developer A acknowledges the warning via `WarningAcknowledged`. The collaboration state reflects: two active drivers, one warning, one acknowledgement.

**Why this priority**: The soft coordination model — overlap is valid, warnings are advisory, no hard locks — is the core differentiator of this design. If this doesn't work correctly with N participants, the entire collaboration contract is unusable.

**Independent Test**: Can be tested by constructing a sequence of `DriveIntentSet`, `FocusChanged`, `ConcurrentDriverWarning`, and `WarningAcknowledged` events for 3 participants, feeding them through the reducer, and verifying the warning timeline and acknowledgement state.

**Acceptance Scenarios**:

1. **Given** participants A and B both have `intent: "active"`, **When** both set focus to WP03 via `FocusChanged`, **Then** the reducer's `participants_by_focus` index shows both on WP03 and a `ConcurrentDriverWarning` is valid for this state.
2. **Given** a `ConcurrentDriverWarning` has been emitted referencing participants A and B, **When** participant A emits `WarningAcknowledged`, **Then** the warning timeline shows the warning with one acknowledgement attributed to A.
3. **Given** 3 participants with active drive intent all focused on WP03, **When** the reducer processes this state, **Then** the warning is valid for all 3 participants and no participant is blocked or rejected.

---

### User Story 3 — LLM Context Execution Tracking (Priority: P1)

An LLM agent context (e.g., Claude Code session) joins a mission as `participant_type: "llm_context"`. It begins executing a prompt step against WP02 by emitting `PromptStepExecutionStarted`. While executing, another LLM context attempts the same step on WP02. A `PotentialStepCollisionDetected` warning is emitted. The first context completes and emits `PromptStepExecutionCompleted`. The collaboration state shows the execution timeline, the collision warning, and the completion.

**Why this priority**: LLM contexts are first-class participants. Step execution tracking is how the observe+decide vertical slice detects and surfaces potential conflicts between agents.

**Independent Test**: Can be tested by constructing `PromptStepExecutionStarted`, `PotentialStepCollisionDetected`, and `PromptStepExecutionCompleted` events for 2 LLM contexts, feeding them through the reducer, and verifying execution state and collision warnings.

**Acceptance Scenarios**:

1. **Given** an LLM context participant has joined, **When** it emits `PromptStepExecutionStarted` with a step reference and WP target, **Then** the collaboration state tracks this as an active execution for that participant.
2. **Given** two LLM contexts are executing steps targeting the same WP, **When** `PotentialStepCollisionDetected` is processed, **Then** the warning timeline includes the collision with both participant IDs and the overlapping target.
3. **Given** an active execution exists, **When** `PromptStepExecutionCompleted` is processed for the same participant and step, **Then** the execution is marked complete and the participant's active execution count decrements.

---

### User Story 4 — Decision Capture and Comment Audit Trail (Priority: P2)

During a mission, participants discuss approach via `CommentPosted` events and resolve a design question via `DecisionCaptured`. All comments and decisions are attributed to specific participants and are replayable from the event stream. A consumer replaying the event log can reconstruct the full discussion and decision history in order.

**Why this priority**: Decisions and comments are the coordination primitives that make soft coordination useful — without them, warnings have no resolution mechanism. They are lower priority than lifecycle and intent because they build on top of those.

**Independent Test**: Can be tested by constructing `CommentPosted` and `DecisionCaptured` events from 3 participants, feeding them through the reducer, and verifying the decision state and comment ordering.

**Acceptance Scenarios**:

1. **Given** 3 active participants, **When** each posts a `CommentPosted` event with different Lamport clocks, **Then** the reducer produces comments in causal order attributed to the correct participants.
2. **Given** a `DecisionCaptured` event referencing a specific topic and chosen option, **When** processed by the reducer, **Then** the decision state records the decision with its author, rationale, and referenced warning (if any).
3. **Given** a replayed event stream containing interleaved comments and decisions from multiple participants, **When** reduced, **Then** the output is identical regardless of the order events are fed in (determinism guarantee).

---

### User Story 5 — Session Linking and Presence (Priority: P2)

A developer has both a CLI session and a SaaS dashboard open for the same mission. A `SessionLinked` event associates the CLI `session_id` with the SaaS `session_id` under the same `participant_id`. `PresenceHeartbeat` events arrive periodically from both sessions. The collaboration state shows the participant as present with two linked sessions.

**Why this priority**: Session linking and presence are observability features that consumers need for the dashboard vertical slice, but they don't block core coordination semantics.

**Independent Test**: Can be tested by constructing `SessionLinked` and `PresenceHeartbeat` events and verifying the reducer tracks linked sessions and presence timestamps.

**Acceptance Scenarios**:

1. **Given** a participant with one active session, **When** a `SessionLinked` event arrives linking a second session, **Then** the collaboration state shows the participant with two linked session IDs.
2. **Given** periodic `PresenceHeartbeat` events from a participant, **When** processed by the reducer, **Then** the presence state reflects the most recent heartbeat timestamp for that participant.
3. **Given** no heartbeat from a participant for a configurable threshold, **When** the collaboration state is inspected, **Then** the participant's presence status can be derived as stale (presence is data, staleness is consumer interpretation).

---

### User Story 6 — Conformance Fixtures for 3+ Participant Overlap (Priority: P2)

A consumer repo (`spec-kitty` CLI or `spec-kitty-saas`) runs `pytest --pyargs spec_kitty_events.conformance` and the conformance suite includes fixtures exercising 3+ participant scenarios: overlapping drive intent, concurrent driver warnings, warning acknowledgement sequences, and interleaved step executions. The fixtures validate that the consumer's pinned version of `spec-kitty-events` correctly handles multi-participant collaboration.

**Why this priority**: Conformance fixtures enforce the contract across repos. Without multi-participant fixtures, consumers could break under real-world cardinality.

**Independent Test**: Can be tested by running the conformance suite and verifying all 3+ participant fixtures pass validation.

**Acceptance Scenarios**:

1. **Given** the conformance fixture set, **When** a consumer loads the "3-participant-overlap" fixture, **Then** the fixture contains valid `ParticipantJoined`, `DriveIntentSet`, `FocusChanged`, `ConcurrentDriverWarning`, and `WarningAcknowledged` events for 3 distinct participants.
2. **Given** the conformance fixture set, **When** the "step-collision" fixture is validated, **Then** it contains `PromptStepExecutionStarted` events from 2 LLM contexts targeting the same WP, a `PotentialStepCollisionDetected` warning, and a `PromptStepExecutionCompleted` resolution.
3. **Given** all collaboration fixtures, **When** validated against the collaboration event JSON schemas, **Then** 100% pass dual-layer validation (Pydantic + JSON Schema).

---

### Edge Cases

- What happens when a participant emits events before `ParticipantJoined`? The reducer records an anomaly ("event from unknown participant") but still processes the event — soft coordination does not reject.
- What happens when `DriveIntentSet(intent: "active")` is emitted twice by the same participant without an intervening `"inactive"`? The reducer is idempotent — the participant remains active, no state change, no anomaly.
- What happens when `WarningAcknowledged` references a warning that doesn't exist in the event stream? The reducer records an anomaly ("acknowledgement for unknown warning") and stores the acknowledgement anyway.
- What happens when `PromptStepExecutionCompleted` arrives without a matching `PromptStepExecutionStarted`? The reducer records an anomaly ("completion without start") and processes the event.
- What happens when a `ParticipantLeft` event arrives for a participant that already left? The reducer is idempotent — no state change, no anomaly for the duplicate leave.
- What happens when a `PresenceHeartbeat` arrives for a participant that has left? The reducer records an anomaly ("heartbeat from departed participant") but updates the timestamp — the participant may have reconnected.
- What happens with 100+ concurrent participants? The reducer has no cardinality limit — it processes all participant events and produces indexed state. Performance is a consumer concern.
- What happens when events arrive with identical Lamport clocks from different nodes? The deterministic sort tiebreaker (`lamport_clock`, `timestamp.isoformat()`, `event_id`) ensures total ordering, consistent with the existing sort semantics.

## Requirements

### Functional Requirements

#### Participant Identity Model

- **FR-001**: Package MUST define a `ParticipantIdentity` structured type with required fields `participant_id: str` and `participant_type: str` (constrained to known values: `"human"`, `"llm_context"`), and optional fields `display_name: str` and `session_id: str`.
- **FR-002**: The `participant_type` field MUST be extensible — new values MAY be added in minor versions without breaking the contract. The initial set is `"human"` and `"llm_context"`.
- **FR-003**: All 14 collaboration event payloads MUST include a `participant_id: str` field identifying the acting participant. Payloads that introduce a participant (`ParticipantInvited`, `ParticipantJoined`) MUST include the full `ParticipantIdentity` structure.

#### Participant Lifecycle Events

- **FR-004**: Package MUST export `ParticipantInvitedPayload` with fields: `participant_id`, `participant_identity` (full identity), `invited_by` (participant_id of inviter), `mission_id`.
- **FR-005**: Package MUST export `ParticipantJoinedPayload` with fields: `participant_id`, `participant_identity` (full identity), `mission_id`.
- **FR-006**: Package MUST export `ParticipantLeftPayload` with fields: `participant_id`, `mission_id`, `reason` (optional, e.g., `"disconnect"`, `"explicit"`).
- **FR-007**: Package MUST export `PresenceHeartbeatPayload` with fields: `participant_id`, `mission_id`, `session_id` (optional).

#### Drive Intent and Focus Events

- **FR-008**: Package MUST export `DriveIntentSetPayload` with fields: `participant_id`, `mission_id`, `intent` constrained to `Literal["active", "inactive"]`.
- **FR-009**: Package MUST export `FocusChangedPayload` with fields: `participant_id`, `mission_id`, `focus_target` (structured: `target_type` as `Literal["wp", "step", "file"]` + `target_id: str`), `previous_focus_target` (optional, same structure).
- **FR-010**: Drive intent is mission-scoped. Multiple active drivers on a mission is valid state and MUST NOT be rejected.

#### Prompt Step Execution Events

- **FR-011**: Package MUST export `PromptStepExecutionStartedPayload` with fields: `participant_id`, `mission_id`, `step_id`, `wp_id` (optional), `step_description` (optional).
- **FR-012**: Package MUST export `PromptStepExecutionCompletedPayload` with fields: `participant_id`, `mission_id`, `step_id`, `wp_id` (optional), `outcome` (e.g., `"success"`, `"failure"`, `"skipped"`).

#### Advisory Warning Events

- **FR-013**: Package MUST export `ConcurrentDriverWarningPayload` with fields: `warning_id`, `mission_id`, `participant_ids` (list of all concurrent active drivers on the overlapping focus target), `focus_target` (the shared target), `severity` (e.g., `"info"`, `"warning"`).
- **FR-014**: Package MUST export `PotentialStepCollisionDetectedPayload` with fields: `warning_id`, `mission_id`, `participant_ids` (list of colliding participants), `step_id`, `wp_id` (optional), `severity`.
- **FR-015**: Package MUST export `WarningAcknowledgedPayload` with fields: `participant_id`, `mission_id`, `warning_id` (reference to the acknowledged warning), `acknowledgement` (optional, e.g., `"noted"`, `"will_coordinate"`, `"proceeding"`).
- **FR-016**: Warnings MUST be advisory only — no hard rejection, no locking, no blocking. The default coordination mode is soft.

#### Communication and Decision Events

- **FR-017**: Package MUST export `CommentPostedPayload` with fields: `participant_id`, `mission_id`, `comment_id`, `content: str`, `reply_to` (optional comment_id for threading).
- **FR-018**: Package MUST export `DecisionCapturedPayload` with fields: `participant_id`, `mission_id`, `decision_id`, `topic: str`, `chosen_option: str`, `rationale` (optional), `referenced_warning_id` (optional).

#### Session Linking Event

- **FR-019**: Package MUST export `SessionLinkedPayload` with fields: `participant_id`, `mission_id`, `primary_session_id`, `linked_session_id`, `link_type` (e.g., `"cli_to_saas"`, `"saas_to_cli"`).

#### Event Type Constants

- **FR-020**: Package MUST export string constants for all 14 event types (e.g., `PARTICIPANT_INVITED = "ParticipantInvited"`, `DRIVE_INTENT_SET = "DriveIntentSet"`, etc.) and a `COLLABORATION_EVENT_TYPES` frozenset containing all 14.

#### Collaboration Reducer

- **FR-021**: Package MUST export a `reduce_collaboration_events()` pure function that accepts a sequence of `Event` objects and returns a `ReducedCollaborationState`.
- **FR-022**: `ReducedCollaborationState` MUST include: active participants (roster with identity), presence state (last heartbeat per participant), active drivers (participants with `intent: "active"`), `focus_by_participant` (current focus target per participant), `participants_by_focus` (reverse index: focus target → participant set), warning timeline (ordered warnings with acknowledgement state), decision state (decisions with authorship), active executions (in-flight prompt steps), anomalies, `event_count`, `last_processed_event_id`.
- **FR-023**: The reducer MUST be deterministic — given any causal-order-preserving permutation of the same events, the output MUST be identical.
- **FR-024**: The reducer MUST handle N participants (no hardcoded cardinality limit).
- **FR-025**: The reducer MUST follow the existing pipeline pattern: sort → dedup → process → collect anomalies.
- **FR-026**: The reducer MUST produce anomalies (not raise exceptions) for: events from unknown participants, acknowledgements for unknown warnings, completions without starts, duplicate join/leave, heartbeats from departed participants.

#### Conformance Artifacts

- **FR-027**: Package MUST ship JSON Schema files for all 14 payload models and the `ParticipantIdentity` model, generated from Pydantic v2 models via the existing schema generation infrastructure.
- **FR-028**: Package MUST ship conformance fixtures including: (a) a 3-participant overlap scenario (join → drive intent → shared focus → concurrent driver warning → acknowledgement), (b) a step collision scenario (2 LLM contexts, same WP), (c) a decision capture scenario with comments.
- **FR-029**: Conformance fixtures MUST be registered in the existing `manifest.json` with appropriate `event_type` values and `min_version: "2.1.0"` (or the version where this feature ships).

#### Exports and Compatibility

- **FR-030**: All new public symbols (14 payload models, `ParticipantIdentity`, 14 event type constants, `COLLABORATION_EVENT_TYPES`, `ReducedCollaborationState`, `CollaborationAnomaly`, `reduce_collaboration_events`, `FocusTarget`) MUST be exported from `spec_kitty_events.__init__`.
- **FR-031**: Package MUST include updated README, COMPATIBILITY.md, and CHANGELOG documenting: all 14 event types with payload field references, reducer input/output contract, advisory warning semantics, and consumer integration guidance for CLI and SaaS.

### Key Entities

- **ParticipantIdentity**: Structured identity for mission participants. Required: `participant_id` (unique string), `participant_type` (`"human"` | `"llm_context"`). Optional: `display_name`, `session_id`. Frozen Pydantic model.
- **FocusTarget**: Structured focus reference. Required: `target_type` (`"wp"` | `"step"` | `"file"`), `target_id` (string identifier). Frozen Pydantic model.
- **ReducedCollaborationState**: Materialized view from collaboration event reduction. Contains mission-level snapshot, per-participant focus, reverse indexes, warning timeline, decision state, execution state, and anomalies. Frozen Pydantic model.
- **CollaborationAnomaly**: Records non-fatal issues during reduction (event_id, event_type, reason). Follows existing `LifecycleAnomaly` / `TransitionAnomaly` pattern.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The collaboration reducer produces identical output for any causal-order-preserving permutation of the same event sequence, verified by property-based tests with 200+ orderings.
- **SC-002**: All 14 collaboration event payloads pass dual-layer validation (Pydantic model + JSON Schema) in the conformance suite with zero failures.
- **SC-003**: Conformance fixtures include at least one scenario with 3+ participants, overlapping drive intent on the same focus target, and a warning-acknowledgement sequence — all passing validation.
- **SC-004**: Consumer developers can construct, validate, and reduce collaboration events using only the public API exported from `spec_kitty_events`, with no private imports required.
- **SC-005**: README and COMPATIBILITY.md document all 14 event types, reducer contract, and consumer integration guidance — enabling a CLI or SaaS developer to integrate without reading source code.
- **SC-006**: Warning and decision events are fully replayable — a consumer can replay the event log and reconstruct the complete warning timeline and decision history with actor attribution.

## Assumptions

- The existing `Event` envelope model (from Feature 001/004) is stable and sufficient for collaboration events — no envelope changes needed.
- The existing conformance infrastructure (Feature 005) — schema generation, fixture manifest, dual-layer validation — is stable and extensible for new event types.
- `participant_type` starts with `"human"` and `"llm_context"` but is designed for extension. New types in minor versions are additive and non-breaking.
- The collaboration reducer is additive to the existing codebase — it does not modify `reduce_lifecycle_events()` or `reduce_status_events()`. Higher-level consumers may compose all three reducers.
- Lamport clock ordering and the existing deterministic sort key (`lamport_clock`, `timestamp.isoformat()`, `event_id`) apply to collaboration events without modification.
- Presence staleness thresholds are consumer-defined — this package provides the heartbeat data, not the staleness policy.
- The `[conformance]` extra already provides `jsonschema` — no new optional dependencies are needed for this feature.
- This feature targets the `2.x` line. The version will be `2.1.0` or the next minor version after `2.0.0`.

## Dependencies

- Existing `Event` model from `models.py` (Features 001, 004) — event envelope for all collaboration events.
- Existing conformance infrastructure from `conformance/` (Feature 005) — schema generation, fixture manifest, validators.
- Existing reducer patterns from `lifecycle.py` and `status.py` (Features 003, 004) — pipeline pattern, anomaly handling, sort/dedup utilities.
- Pydantic v2 for frozen models, field validators, and JSON Schema generation.
- No new external dependencies required.

## Out of Scope

- CLI command implementation for collaboration features — CLI consumes these contracts but is built separately.
- SaaS projection UI implementation — SaaS consumes these contracts but is built separately.
- Hard locking or pessimistic concurrency control — this feature is advisory-only by design.
- Presence staleness detection logic — this package provides heartbeat data; consumers define staleness thresholds.
- Real-time transport (WebSockets, SSE) — events are data contracts, not transport mechanisms.
- Participant authentication or authorization — `participant_id` is opaque; auth is a consumer concern.
- Conflict resolution automation — warnings are informational; resolution is human/consumer-driven.
