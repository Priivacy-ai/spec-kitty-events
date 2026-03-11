---
work_package_id: WP01
title: Payload Models & Constants
lane: done
dependencies: []
base_branch: 2.x
base_commit: 4dda9d5509284bd062cdfe1ebfe5e0faca37f22e
created_at: '2026-03-05T15:49:35.816568+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
assignee: ''
agent: claude-opus-reviewer
shell_pid: '37263'
review_status: approved
reviewed_by: Robert Douglass
review_feedback: feedback://013-per-user-identity-connector-events/WP01/20260305T161214Z-b89988d9.md
history:
- timestamp: '2026-03-05T11:15:54Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-006
- C-001
- C-002
- C-003
- C-004
---

# Work Package Prompt: WP01 – Payload Models & Constants

## Objectives & Success Criteria

- Bump `CONNECTOR_SCHEMA_VERSION` from `"2.7.0"` to `"2.8.0"`.
- Add `user_id: Optional[str] = None` to all 5 existing connector payload models.
- Define `USER_CONNECTED` and `USER_DISCONNECTED` event type constants.
- Expand `CONNECTOR_EVENT_TYPES` from 5 to 7 members.
- Create `UserConnectedPayload` and `UserDisconnectedPayload` with required `user_id`.
- Create `UserConnectionStatus` roster model.
- Update `_EVENT_TO_STATE`, `_EVENT_TO_PAYLOAD`, and `ConnectorPayload` union.
- All changes pass `mypy --strict`.

**Implementation command**: `spec-kitty implement WP01`

## Context & Constraints

- **Spec**: `kitty-specs/013-per-user-identity-connector-events/spec.md`
- **Plan**: `kitty-specs/013-per-user-identity-connector-events/plan.md`
- **Data model**: `kitty-specs/013-per-user-identity-connector-events/data-model.md`
- **Target file**: `src/spec_kitty_events/connector.py`
- **Constraint C-001**: All models use `ConfigDict(frozen=True)`.
- **Constraint C-002**: Additive changes only — no breaking changes to existing types.
- **Constraint C-003**: `user_id` is `Optional[str]` with default `None` on existing payloads.
- **Constraint C-004**: `user_id` is required (non-optional) on `UserConnected` and `UserDisconnected` payloads.

**Key distinction**: `user_id` identifies whose OAuth connection is affected. `actor_id` identifies who triggered the event. They may coincide (user reconnects their own connection) or differ (system health check on a user's token).

## Subtasks & Detailed Guidance

### Subtask T001 – Bump CONNECTOR_SCHEMA_VERSION

- **Purpose**: Signal the contract change to downstream consumers.
- **Steps**:
  1. In `src/spec_kitty_events/connector.py`, line 23, change:
     ```python
     CONNECTOR_SCHEMA_VERSION: str = "2.7.0"
     ```
     to:
     ```python
     CONNECTOR_SCHEMA_VERSION: str = "2.8.0"
     ```
- **Files**: `src/spec_kitty_events/connector.py`
- **Notes**: SemVer minor bump — additive, non-breaking.

### Subtask T002 – Add user_id to existing connector payloads

- **Purpose**: Allow all connector lifecycle events to attribute state changes to specific users (FR-001).
- **Steps**:
  1. Add the following field to each of these 5 models in `src/spec_kitty_events/connector.py`:
     - `ConnectorProvisionedPayload` (after `config_hash`)
     - `ConnectorHealthCheckedPayload` (after `latency_ms`)
     - `ConnectorDegradedPayload` (after `last_healthy_at`)
     - `ConnectorRevokedPayload` (after `revocation_reason`)
     - `ConnectorReconnectedPayload` (after `reconnect_strategy`)
  2. Field definition (identical for all 5):
     ```python
     user_id: Optional[str] = None
     ```
  3. Import `Optional` is already imported from `typing`.
- **Files**: `src/spec_kitty_events/connector.py`
- **Notes**: `None` default ensures backward compatibility. Pre-migration events without `user_id` will validate correctly.

### Subtask T003 – Add USER_CONNECTED and USER_DISCONNECTED constants

- **Purpose**: Define canonical event type strings for per-user lifecycle events (FR-002, FR-003).
- **Steps**:
  1. After the existing constants block (after line 31, `CONNECTOR_RECONNECTED`), add:
     ```python
     USER_CONNECTED: str = "UserConnected"
     USER_DISCONNECTED: str = "UserDisconnected"
     ```
  2. Update the `CONNECTOR_EVENT_TYPES` frozenset to include both new constants:
     ```python
     CONNECTOR_EVENT_TYPES: FrozenSet[str] = frozenset({
         CONNECTOR_PROVISIONED,
         CONNECTOR_HEALTH_CHECKED,
         CONNECTOR_DEGRADED,
         CONNECTOR_REVOKED,
         CONNECTOR_RECONNECTED,
         USER_CONNECTED,
         USER_DISCONNECTED,
     })
     ```
- **Files**: `src/spec_kitty_events/connector.py`
- **Notes**: The frozenset grows from 5 to 7 members.

### Subtask T004 – Create UserConnectedPayload and UserDisconnectedPayload

- **Purpose**: Payload models for user-level lifecycle events (FR-002, FR-003).
- **Steps**:
  1. After the existing payload models section (after `ConnectorReconnectedPayload`), add:

     ```python
     class UserConnectedPayload(BaseModel):
         """Payload for UserConnected events."""

         model_config = ConfigDict(frozen=True)

         connector_id: str = Field(..., min_length=1)
         connector_type: str = Field(..., min_length=1)
         provider: str = Field(..., min_length=1)
         mission_id: str = Field(..., min_length=1)
         project_uuid: UUID
         actor_id: str = Field(..., min_length=1)
         actor_type: str = Field(..., pattern=r"^(human|service|system)$")
         endpoint_url: AnyHttpUrl
         recorded_at: datetime
         user_id: str = Field(..., min_length=1)


     class UserDisconnectedPayload(BaseModel):
         """Payload for UserDisconnected events."""

         model_config = ConfigDict(frozen=True)

         connector_id: str = Field(..., min_length=1)
         connector_type: str = Field(..., min_length=1)
         provider: str = Field(..., min_length=1)
         mission_id: str = Field(..., min_length=1)
         project_uuid: UUID
         actor_id: str = Field(..., min_length=1)
         actor_type: str = Field(..., pattern=r"^(human|service|system)$")
         endpoint_url: AnyHttpUrl
         recorded_at: datetime
         user_id: str = Field(..., min_length=1)
         reason: str = ""
     ```

  2. Update `ConnectorPayload` union to include the new types:
     ```python
     ConnectorPayload = Union[
         ConnectorProvisionedPayload,
         ConnectorHealthCheckedPayload,
         ConnectorDegradedPayload,
         ConnectorRevokedPayload,
         ConnectorReconnectedPayload,
         UserConnectedPayload,
         UserDisconnectedPayload,
     ]
     ```

  3. Update `_EVENT_TO_STATE` mapping:
     ```python
     _EVENT_TO_STATE: Dict[str, ConnectorState] = {
         CONNECTOR_PROVISIONED: ConnectorState.PROVISIONED,
         CONNECTOR_HEALTH_CHECKED: ConnectorState.HEALTHY,
         CONNECTOR_DEGRADED: ConnectorState.DEGRADED,
         CONNECTOR_REVOKED: ConnectorState.REVOKED,
         CONNECTOR_RECONNECTED: ConnectorState.RECONNECTED,
         USER_CONNECTED: ConnectorState.PROVISIONED,
         USER_DISCONNECTED: ConnectorState.REVOKED,
     }
     ```

  4. Update `_EVENT_TO_PAYLOAD` mapping:
     ```python
     _EVENT_TO_PAYLOAD: Dict[str, type[ConnectorPayload]] = {
         CONNECTOR_PROVISIONED: ConnectorProvisionedPayload,
         CONNECTOR_HEALTH_CHECKED: ConnectorHealthCheckedPayload,
         CONNECTOR_DEGRADED: ConnectorDegradedPayload,
         CONNECTOR_REVOKED: ConnectorRevokedPayload,
         CONNECTOR_RECONNECTED: ConnectorReconnectedPayload,
         USER_CONNECTED: UserConnectedPayload,
         USER_DISCONNECTED: UserDisconnectedPayload,
     }
     ```

- **Files**: `src/spec_kitty_events/connector.py`
- **Notes**: `user_id` is **required** (`Field(..., min_length=1)`) on both new payloads. This is constraint C-004. Note that `UserConnectedPayload.user_id` is required, unlike the `Optional[str]` on existing payloads.

### Subtask T005 – Create UserConnectionStatus model

- **Purpose**: Roster entry model for reducer output (FR-004).
- **Steps**:
  1. After the `ConnectorAnomaly` model (Section 4), add:
     ```python
     class UserConnectionStatus(BaseModel):
         """Per-user connection state entry in ReducedConnectorState roster."""

         model_config = ConfigDict(frozen=True)

         user_id: str
         state: ConnectorState
         last_event_at: Optional[datetime] = None
     ```
- **Files**: `src/spec_kitty_events/connector.py`
- **Notes**: This model is not an event payload — it's a projection output used by the reducer.

## Risks & Mitigations

- **Pydantic validation on existing payloads**: Adding `user_id: Optional[str] = None` is fully backward-compatible. Existing payloads without `user_id` will validate with `None`.
- **mypy strict**: The `from __future__ import annotations` import is already present. Use `Optional[str]` (not `str | None`) for consistency with existing code.

## Review Guidance

- Verify `user_id` defaults to `None` on all 5 existing payloads (C-003).
- Verify `user_id` is required (no default) on both new payloads (C-004).
- Verify `CONNECTOR_EVENT_TYPES` has exactly 7 members.
- Verify `_EVENT_TO_STATE` maps `USER_CONNECTED` → `PROVISIONED`, `USER_DISCONNECTED` → `REVOKED`.
- Verify `ConnectorPayload` union includes all 7 types.
- Run `mypy --strict src/spec_kitty_events/connector.py` — must pass.

## Activity Log

- 2026-03-05T11:15:54Z – system – lane=planned – Prompt created.
- 2026-03-05T15:49:36Z – claude-opus-4-6 – shell_pid=31530 – lane=doing – Assigned agent via workflow command
- 2026-03-05T15:52:51Z – claude-opus-4-6 – shell_pid=31530 – lane=for_review – Ready for review: all 5 subtasks implemented. mypy --strict passes. 55/57 tests pass (2 assertion updates deferred to WP03).
- 2026-03-05T15:58:58Z – claude-opus-4-6 – shell_pid=32940 – lane=doing – Started review via workflow command
- 2026-03-05T16:00:49Z – claude-opus-4-6 – shell_pid=32940 – lane=planned – Moved to planned
- 2026-03-05T16:05:15Z – claude-opus-4-6 – shell_pid=34814 – lane=doing – Started implementation via workflow command
- 2026-03-05T16:07:21Z – claude-opus-4-6 – shell_pid=34814 – lane=for_review – Fixed review feedback: regenerated JSON schemas, updated golden file, fixed test assertions. All 1438 tests pass, mypy --strict clean.
- 2026-03-05T16:08:32Z – claude-opus-4-6 – shell_pid=35474 – lane=doing – Started review via workflow command
- 2026-03-05T16:12:14Z – claude-opus-4-6 – shell_pid=35474 – lane=planned – Moved to planned
- 2026-03-05T16:13:01Z – claude-opus-4-6 – shell_pid=36004 – lane=doing – Started implementation via workflow command
- 2026-03-05T16:14:02Z – claude-opus-4-6 – shell_pid=36004 – lane=for_review – Fixed missing __init__.py exports for 5 new symbols. All 1438 tests pass, mypy --strict clean.
- 2026-03-05T21:40:58Z – claude-opus-reviewer – shell_pid=37263 – lane=doing – Started review via workflow command
- 2026-03-05T21:56:25Z – claude-opus-reviewer – shell_pid=37263 – lane=done – Review passed: All 5 subtasks verified. mypy --strict clean, 1438/1438 tests pass. Merged to 2.x. Schema version 2.8.0, user_id on all payloads, 7 event types, reducer roster tracking, exports and schemas updated.
