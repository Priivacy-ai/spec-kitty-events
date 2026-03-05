# Data Model: Per-User Identity in Connector Events

**Feature**: 013-per-user-identity-connector-events
**Date**: 2026-03-05

## Modified Entities

### ConnectorProvisionedPayload (modified)

| Field | Type | Required | Change |
|-------|------|----------|--------|
| connector_id | str (min 1) | yes | existing |
| connector_type | str (min 1) | yes | existing |
| provider | str (min 1) | yes | existing |
| mission_id | str (min 1) | yes | existing |
| project_uuid | UUID | yes | existing |
| actor_id | str (min 1) | yes | existing |
| actor_type | str (human/service/system) | yes | existing |
| endpoint_url | AnyHttpUrl | yes | existing |
| recorded_at | datetime | yes | existing |
| credentials_ref | str (min 1) | yes | existing |
| config_hash | str (min 1) | yes | existing |
| **user_id** | **Optional[str]** | **no (default None)** | **NEW** |

### ConnectorHealthCheckedPayload (modified)

All existing fields unchanged. Added:

| Field | Type | Required | Change |
|-------|------|----------|--------|
| **user_id** | **Optional[str]** | **no (default None)** | **NEW** |

### ConnectorDegradedPayload (modified)

All existing fields unchanged. Added:

| Field | Type | Required | Change |
|-------|------|----------|--------|
| **user_id** | **Optional[str]** | **no (default None)** | **NEW** |

### ConnectorRevokedPayload (modified)

All existing fields unchanged. Added:

| Field | Type | Required | Change |
|-------|------|----------|--------|
| **user_id** | **Optional[str]** | **no (default None)** | **NEW** |

### ConnectorReconnectedPayload (modified)

All existing fields unchanged. Added:

| Field | Type | Required | Change |
|-------|------|----------|--------|
| **user_id** | **Optional[str]** | **no (default None)** | **NEW** |

## New Entities

### UserConnectedPayload

Event: `UserConnected` — emitted when a user establishes their OAuth connection to a binding.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| connector_id | str (min 1) | yes | Binding identifier |
| connector_type | str (min 1) | yes | Provider type |
| provider | str (min 1) | yes | Provider name |
| mission_id | str (min 1) | yes | Mission context |
| project_uuid | UUID | yes | Project context |
| actor_id | str (min 1) | yes | Who triggered the connection |
| actor_type | str (human/service/system) | yes | Actor classification |
| endpoint_url | AnyHttpUrl | yes | Provider endpoint |
| recorded_at | datetime | yes | When connection was established |
| user_id | str (min 1) | yes | **Required** — whose connection |

### UserDisconnectedPayload

Event: `UserDisconnected` — emitted when a user disconnects from a binding.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| connector_id | str (min 1) | yes | Binding identifier |
| connector_type | str (min 1) | yes | Provider type |
| provider | str (min 1) | yes | Provider name |
| mission_id | str (min 1) | yes | Mission context |
| project_uuid | UUID | yes | Project context |
| actor_id | str (min 1) | yes | Who triggered the disconnection |
| actor_type | str (human/service/system) | yes | Actor classification |
| endpoint_url | AnyHttpUrl | yes | Provider endpoint |
| recorded_at | datetime | yes | When disconnection occurred |
| user_id | str (min 1) | yes | **Required** — whose connection |
| reason | str | no (default "") | Disconnect reason |

### UserConnectionStatus

Roster entry in reducer output. Not an event payload.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| user_id | str | yes | User identifier |
| state | ConnectorState | yes | Latest state for this user |
| last_event_at | Optional[datetime] | no (default None) | Timestamp of last event affecting this user |

### ReducedConnectorState (modified)

| Field | Type | Required | Change |
|-------|------|----------|--------|
| connector_id | Optional[str] | no | existing |
| current_state | Optional[ConnectorState] | no | existing |
| provider | Optional[str] | no | existing |
| last_health_check | Optional[datetime] | no | existing |
| anomalies | tuple[ConnectorAnomaly, ...] | no | existing |
| event_count | int | no | existing |
| transition_log | tuple[tuple[str, str], ...] | no | existing |
| **user_connections** | **tuple[UserConnectionStatus, ...]** | **no (default ())** | **NEW** |

## State Mapping

| Event Type | Binding-Level State | Roster State |
|------------|-------------------|--------------|
| ConnectorProvisioned | PROVISIONED | (updates roster if user_id present) |
| ConnectorHealthChecked | HEALTHY | (updates roster if user_id present) |
| ConnectorDegraded | DEGRADED | (updates roster if user_id present) |
| ConnectorRevoked | REVOKED | (updates roster if user_id present) |
| ConnectorReconnected | RECONNECTED | (updates roster if user_id present) |
| UserConnected | (no binding-level change) | PROVISIONED |
| UserDisconnected | (no binding-level change) | REVOKED |

## Constants

| Constant | Value | Change |
|----------|-------|--------|
| CONNECTOR_SCHEMA_VERSION | "2.8.0" | **BUMPED from 2.7.0** |
| USER_CONNECTED | "UserConnected" | **NEW** |
| USER_DISCONNECTED | "UserDisconnected" | **NEW** |
| CONNECTOR_EVENT_TYPES | frozenset (7 members) | **EXPANDED from 5** |
