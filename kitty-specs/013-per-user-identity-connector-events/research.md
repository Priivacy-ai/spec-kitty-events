# Research: Per-User Identity in Connector Events

**Feature**: 013-per-user-identity-connector-events
**Date**: 2026-03-05
**Status**: Complete (no unknowns — feature is well-scoped)

## R1: user_id vs actor_id semantics

**Decision**: `user_id` is a distinct field from `actor_id`. They represent different concepts.
**Rationale**: `actor_id` identifies who/what triggered the event (system, cron, admin, user). `user_id` identifies whose OAuth connection is affected. They coincide when a user acts on their own connection but diverge for system-initiated events (health checks, automated revocations).
**Alternatives considered**: Overloading `actor_id` to carry user context — rejected because it conflates trigger identity with affected-connection identity.

## R2: Reducer architecture for per-user roster

**Decision**: Single `reduce_connector_events()` function, simple latest-state roster.
**Rationale**: User-level events belong to the same CONNECTOR event family. A separate reducer would force consumers to call two functions and merge results. The roster is intentionally simple (latest state per user, no transition logs) because the SaaS `UserProviderConnection` model owns detailed per-user state tracking.
**Alternatives considered**: (a) Separate `reduce_user_connection_events()` — rejected for complexity. (b) Full per-user state machine with transition logs — rejected as overkill; the SaaS database already tracks this.

## R3: Schema version strategy

**Decision**: Bump `CONNECTOR_SCHEMA_VERSION` from `2.7.0` to `2.8.0`.
**Rationale**: All changes are additive (new optional field, new event types, new output model field). SemVer minor increment is appropriate. No breaking changes to existing consumers.
**Alternatives considered**: `3.0.0` major bump — rejected because nothing breaks.

## R4: UserConnected / UserDisconnected state mapping

**Decision**: `UserConnected` maps to `ConnectorState.PROVISIONED`, `UserDisconnected` maps to `ConnectorState.REVOKED` for roster state tracking.
**Rationale**: Reuses existing `ConnectorState` enum values. A connected user is analogous to a provisioned connector; a disconnected user is analogous to a revoked connector. No new enum members needed.
**Alternatives considered**: New `UserConnectionState` enum with `CONNECTED`/`DISCONNECTED` values — rejected to avoid enum proliferation; existing states carry the right semantics.
