# Feature Specification: Per-User Identity in Connector Events

**Feature Branch**: `013-per-user-identity-connector-events`
**Created**: 2026-03-05
**Status**: Draft
**Input**: Per-user connector auth redesign (PRD section 3: spec-kitty-events)

## Problem

The connector lifecycle event contracts (`ConnectorProvisioned`, `ConnectorHealthChecked`, `ConnectorDegraded`, `ConnectorRevoked`, `ConnectorReconnected`) model connectors at the binding level with a single `actor_id` and `credentials_ref` per event. With per-user OAuth connections replacing the shared binding-level credential model, events need to represent *which user's connection* changed state, not just which binding was affected. Without this, downstream consumers cannot attribute connector health changes, degradation alerts, or revocations to the correct user.

## Goals

- Track per-user connection identity in all connector lifecycle events.
- Introduce user-level lifecycle events (`UserConnected`, `UserDisconnected`) distinct from binding-level events.
- Extend the reducer to produce a per-user connection roster alongside binding-level state.
- Maintain full backward compatibility with pre-migration events that lack user context.

## Non-goals

- Replicate full per-user state machines in the reducer (the SaaS `UserProviderConnection` model owns that).
- Add OAuth token storage, refresh logic, or Nango integration to the events library.
- Change existing binding-level transition rules or state machine semantics.
- Add provider-specific payload schemas.

## User Scenarios & Testing

### User Story 1 - Per-User Event Attribution (Priority: P1)

A downstream consumer (spec-kitty-saas) emits connector lifecycle events that identify which user's OAuth connection was affected. When a system health check detects that user-123's Jira token has expired, the emitted `ConnectorDegraded` event carries `user_id="user-123"` alongside `actor_id="system"`, allowing the SaaS app to notify the correct user.

**Why this priority**: Core requirement. Without user attribution, the entire per-user auth redesign cannot propagate connection state through the event system.

**Independent Test**: Create a `ConnectorDegraded` event with `actor_id="system"` and `user_id="user-123"`. Validate that the payload round-trips through serialization and the reducer correctly processes it.

**Acceptance Scenarios**:

1. **Given** a `ConnectorDegradedPayload` with `user_id="user-123"` and `actor_id="system"`, **When** serialized and deserialized, **Then** both fields retain their distinct values.
2. **Given** a `ConnectorReconnectedPayload` where `actor_id` and `user_id` are the same user, **When** validated, **Then** the payload is accepted (coinciding values are valid).
3. **Given** a `ConnectorProvisionedPayload` without `user_id` (legacy event), **When** validated, **Then** `user_id` defaults to `None` and the payload is accepted.

---

### User Story 2 - User Connection Lifecycle Events (Priority: P1)

A SaaS application emits `UserConnected` when a user authenticates their OAuth connection to a binding, and `UserDisconnected` when a user disconnects. These are distinct from binding-level `ConnectorProvisioned`/`ConnectorRevoked` because multiple users can connect to the same binding independently.

**Why this priority**: Required for the per-user connection model. Without these events, there is no canonical way to record user-level connect/disconnect actions.

**Independent Test**: Emit a `UserConnected` event for user-456 on a binding that already has user-123 connected. Reduce the event stream and verify the roster shows both users.

**Acceptance Scenarios**:

1. **Given** a binding with no user connections, **When** a `UserConnected` event is emitted for user-456, **Then** the reducer roster contains one entry for user-456 with state reflecting their connection.
2. **Given** a binding with user-456 connected, **When** a `UserDisconnected` event is emitted for user-456, **Then** the reducer roster updates user-456's state accordingly.
3. **Given** a `UserConnected` event without `user_id`, **When** validated, **Then** validation fails (user_id is required for user-level events).

---

### User Story 3 - Reducer Per-User Roster (Priority: P2)

The connector event reducer produces a `user_connections` roster showing the latest state and last event timestamp for each user who has interacted with the connector. This allows consumers to answer "who is connected to this binding and what is their status?" without querying the database.

**Why this priority**: Enhances the reducer output for downstream consumers but the SaaS app can function without it (it has `UserProviderConnection` in the database).

**Independent Test**: Reduce a stream of mixed binding-level and user-level events. Verify the roster contains correct per-user entries while binding-level `current_state` and `transition_log` remain unchanged.

**Acceptance Scenarios**:

1. **Given** a stream with `ConnectorProvisioned`, `UserConnected(user-123)`, `UserConnected(user-456)`, `ConnectorHealthChecked(user_id=user-123)`, **When** reduced, **Then** `user_connections` contains entries for both users with correct latest states.
2. **Given** a stream with only pre-migration events (no `user_id`), **When** reduced, **Then** `user_connections` is empty and binding-level state reduces correctly.
3. **Given** duplicate `UserConnected` events for the same user (same event_id), **When** reduced, **Then** deduplication produces a single roster entry.

---

### Edge Cases

- What happens when a `UserDisconnected` event arrives for a user who was never connected? The reducer records an anomaly.
- What happens when `user_id` is present on a binding-level event but the event stream has no corresponding `UserConnected`? The roster includes the user from the binding-level event's `user_id`.
- What happens when events arrive out of order (e.g., `UserDisconnected` before `UserConnected` by timestamp)? The existing sort pipeline orders them; the reducer applies transitions in sorted order.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | user_id on payloads | As a consumer, I want all connector payload models to carry an optional `user_id` so that I can attribute events to specific users. | High | Open |
| FR-002 | UserConnected event | As a consumer, I want a `UserConnected` event type so that I can record when a user establishes their connection to a binding. | High | Open |
| FR-003 | UserDisconnected event | As a consumer, I want a `UserDisconnected` event type so that I can record when a user disconnects from a binding. | High | Open |
| FR-004 | UserConnectionStatus model | As a consumer, I want a `UserConnectionStatus` model so that the reducer can output per-user state. | Medium | Open |
| FR-005 | Reducer roster | As a consumer, I want `ReducedConnectorState.user_connections` to contain per-user latest state so that I can query user connection status from reduced state. | Medium | Open |
| FR-006 | Schema version bump | As a consumer, I want `CONNECTOR_SCHEMA_VERSION` incremented so that I can detect the contract change. | High | Open |
| FR-007 | Backward compatibility | As a consumer, I want events without `user_id` to reduce correctly so that pre-migration event streams continue to work. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Deterministic reduction | Reducer produces identical output for any ordering of the same event set. | Correctness | High | Open |
| NFR-002 | Type safety | All new models pass `mypy --strict` with frozen Pydantic config. | Quality | High | Open |
| NFR-003 | Test coverage | New code maintains 98%+ line coverage. | Quality | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Pydantic frozen models | All payload and output models use `ConfigDict(frozen=True)`. | Technical | High | Open |
| C-002 | Additive changes only | No breaking changes to existing event types, payload shapes, or public exports. | Technical | High | Open |
| C-003 | Optional user_id | `user_id` is `Optional[str]` with default `None` on existing payloads for backward compatibility. | Technical | High | Open |
| C-004 | Required user_id on user events | `user_id` is required (non-optional) on `UserConnected` and `UserDisconnected` payloads. | Technical | High | Open |

### Key Entities

- **UserConnectionStatus**: Per-user connection state entry containing `user_id`, latest `ConnectorState`, and `last_event_at` timestamp. Aggregated into a tuple on `ReducedConnectorState`.
- **UserConnectedPayload**: Payload for the `UserConnected` event capturing which user authenticated to which binding.
- **UserDisconnectedPayload**: Payload for the `UserDisconnected` event capturing which user disconnected from which binding.

## Assumptions

- The `user_id` value is an opaque string identifier provided by the SaaS layer. The events library does not validate its format.
- `UserConnected`/`UserDisconnected` are user-level lifecycle events orthogonal to the binding-level state machine. They do not participate in the binding-level transition rules.
- The roster is a simple "latest state" projection. No per-user transition logs are maintained.
- The schema version bump follows SemVer minor increment (additive, non-breaking).

## Success Criteria

### Measurable Outcomes

- **SC-001**: All five existing connector payload models accept an optional `user_id` field and round-trip it through serialization without data loss.
- **SC-002**: Two new event types (`UserConnected`, `UserDisconnected`) are defined with required `user_id` fields and pass conformance validation.
- **SC-003**: The reducer produces a `user_connections` roster that accurately reflects the latest state of each user seen in the event stream.
- **SC-004**: Pre-migration event streams (no `user_id` on any event) reduce to identical binding-level state as before the change, with an empty user roster.
- **SC-005**: Property tests confirm reducer determinism holds across randomized event orderings including the new event types.
