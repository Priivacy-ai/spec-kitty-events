---
work_package_id: WP02
title: Reducer & Roster Logic
lane: "doing"
dependencies: [WP01]
base_branch: 2.x
base_commit: d45029ecf6ac5ee103de06c97bb3899492e11dce
created_at: '2026-03-05T21:57:04.912012+00:00'
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 1 - Foundation
assignee: ''
agent: "claude-opus-4-6"
shell_pid: "38223"
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-05T11:15:54Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-005
- FR-007
- NFR-001
- C-002
---

# Work Package Prompt: WP02 – Reducer & Roster Logic

## Objectives & Success Criteria

- Add `user_connections: Tuple[UserConnectionStatus, ...] = ()` to `ReducedConnectorState`.
- Update `reduce_connector_events()` to build a per-user roster from `user_id` fields on binding-level events.
- Handle `UserConnected`/`UserDisconnected` events: update roster only, skip binding-level state transitions.
- Record anomalies for `UserDisconnected` events targeting users not yet seen.
- Pre-migration event streams (no `user_id`) must produce identical binding-level state with an empty roster.
- Reducer must remain deterministic (same events in any order → same output).

**Implementation command**: `spec-kitty implement WP02 --base WP01`

## Context & Constraints

- **Spec**: `kitty-specs/013-per-user-identity-connector-events/spec.md`
- **Plan**: `kitty-specs/013-per-user-identity-connector-events/plan.md` (Design Decision D2, D3, D4)
- **Data model**: `kitty-specs/013-per-user-identity-connector-events/data-model.md` (State Mapping table)
- **Target file**: `src/spec_kitty_events/connector.py`
- **Depends on**: WP01 (models, constants, and mappings must exist)
- **Key constraint**: `UserConnected`/`UserDisconnected` are orthogonal to the binding-level state machine. They do NOT update `current_state` or `transition_log`.

## Subtasks & Detailed Guidance

### Subtask T006 – Add user_connections to ReducedConnectorState

- **Purpose**: Expose per-user roster in reducer output (FR-005).
- **Steps**:
  1. In the `ReducedConnectorState` model (Section 6 of `connector.py`), add after `transition_log`:
     ```python
     user_connections: Tuple[UserConnectionStatus, ...] = ()
     ```
  2. Ensure the import of `UserConnectionStatus` is available (it's defined in the same file from WP01).
- **Files**: `src/spec_kitty_events/connector.py`
- **Notes**: Default `()` preserves backward compatibility — callers that don't check `user_connections` see no change.

### Subtask T007 – Update reducer to build per-user roster from user_id

- **Purpose**: When binding-level events carry `user_id`, track the user's latest state in the roster (FR-005).
- **Steps**:
  1. In `reduce_connector_events()` (Section 7), add a mutable roster accumulator before the fold loop:
     ```python
     # Per-user roster accumulator: user_id -> (state, last_event_at)
     user_roster: Dict[str, Tuple[ConnectorState, Optional[datetime]]] = {}
     ```
  2. After the existing "Apply transition" block (after line ~327 `transition_log.append(...)`), add roster update logic:
     ```python
     # Update per-user roster if user_id is present
     payload_user_id = payload_dict.get("user_id")
     if isinstance(payload_user_id, str) and payload_user_id:
         recorded_at_raw = payload_dict.get("recorded_at")
         roster_ts: Optional[datetime] = None
         if isinstance(payload, (ConnectorHealthCheckedPayload,
                                  ConnectorDegradedPayload,
                                  ConnectorRevokedPayload,
                                  ConnectorReconnectedPayload,
                                  ConnectorProvisionedPayload)):
             roster_ts = payload.recorded_at
         user_roster[payload_user_id] = (target_state, roster_ts)
     ```
     Note: Access `user_id` from `payload_dict` (the raw dict) rather than `payload` object, because `payload` is typed as the union and not all members had `user_id` pre-WP01. After WP01 lands, all payload models have `user_id`, so you can also use `getattr(payload, 'user_id', None)`.
  3. In the "Step 6: Freeze and return" section, build the frozen roster:
     ```python
     frozen_roster = tuple(
         UserConnectionStatus(user_id=uid, state=st, last_event_at=ts)
         for uid, (st, ts) in sorted(user_roster.items())
     )
     ```
  4. Pass `user_connections=frozen_roster` to the `ReducedConnectorState` constructor.
- **Files**: `src/spec_kitty_events/connector.py`
- **Notes**: Sorting by `user_id` ensures deterministic output regardless of event processing order.

### Subtask T008 – Handle UserConnected/UserDisconnected in reducer

- **Purpose**: User-level events update roster only, not binding-level state (Design Decision D2).
- **Steps**:
  1. The current reducer loop structure already handles new event types via `_EVENT_TO_STATE` and `_EVENT_TO_PAYLOAD`. However, `UserConnected`/`UserDisconnected` should NOT participate in binding-level state transitions.
  2. Identify user-level event types. Add a constant set after the existing `_ALLOWED_TRANSITIONS`:
     ```python
     _USER_LEVEL_EVENT_TYPES: FrozenSet[str] = frozenset({
         USER_CONNECTED,
         USER_DISCONNECTED,
     })
     ```
  3. In the reducer fold loop, after payload validation succeeds but BEFORE the binding-level transition check, add a branch:
     ```python
     if event_type in _USER_LEVEL_EVENT_TYPES:
         # User-level events update roster only
         user_id_val = getattr(payload, 'user_id', None)
         if isinstance(user_id_val, str) and user_id_val:
             user_roster[user_id_val] = (target_state, payload.recorded_at)
         continue  # Skip binding-level state transition
     ```
  4. This `continue` skips the `current_state = target_state` and `transition_log.append(...)` lines for user-level events.
  5. The existing binding-level transition check (`_ALLOWED_TRANSITIONS`) is bypassed for user-level events, which is correct — they don't participate in the binding state machine.
- **Files**: `src/spec_kitty_events/connector.py`
- **Notes**: The reducer loop order matters. The user-level branch must come AFTER payload validation but BEFORE binding-level transition logic. Structure:
  ```
  for event in conn_events:
      ... (get target_state)
      ... (validate payload)
      if event_type in _USER_LEVEL_EVENT_TYPES:
          ... (update roster, continue)
      ... (check allowed transitions)
      ... (apply binding-level state change)
      ... (update roster if user_id present)
  ```

### Subtask T009 – Add anomaly for UserDisconnected without prior UserConnected

- **Purpose**: Detect when a `UserDisconnected` event arrives for a user who was never seen (edge case from spec).
- **Steps**:
  1. In the user-level event handling branch (from T008), add anomaly detection:
     ```python
     if event_type in _USER_LEVEL_EVENT_TYPES:
         user_id_val = getattr(payload, 'user_id', None)
         if isinstance(user_id_val, str) and user_id_val:
             # Anomaly: UserDisconnected for unknown user
             if event_type == USER_DISCONNECTED and user_id_val not in user_roster:
                 anomalies.append(ConnectorAnomaly(
                     kind="invalid_transition",
                     event_id=event_id,
                     message=(
                         f"UserDisconnected for user {user_id_val!r} "
                         f"who has no prior connection event"
                     ),
                 ))
             user_roster[user_id_val] = (target_state, payload.recorded_at)
         continue
     ```
  2. Note: the anomaly is recorded but the roster is still updated. This is non-fatal — the user appears in the roster with REVOKED state despite no prior PROVISIONED state.
- **Files**: `src/spec_kitty_events/connector.py`
- **Notes**: This matches the spec edge case: "What happens when a UserDisconnected event arrives for a user who was never connected? The reducer records an anomaly."

## Risks & Mitigations

- **Determinism**: The roster is sorted by `user_id` before freezing. This ensures identical output regardless of event arrival order. The existing `status_event_sort_key` pipeline handles event ordering before the fold.
- **Backward compatibility**: Events without `user_id` produce `payload_dict.get("user_id")` → `None`. The roster update is skipped. Binding-level state is unchanged. The `user_connections` tuple is empty.
- **Reducer loop restructuring**: The user-level branch must use `continue` to skip binding-level logic. Verify that `connector_id`, `provider`, and `last_health_check` are NOT updated by user-level events.

## Review Guidance

- Verify pre-migration event stream produces empty `user_connections` and identical binding-level state.
- Verify `UserConnected` event updates roster but NOT `current_state` or `transition_log`.
- Verify `UserDisconnected` for unknown user records anomaly AND updates roster.
- Verify roster is sorted by `user_id` (determinism).
- Verify binding-level events WITH `user_id` update BOTH the binding state AND the roster.
- Run `mypy --strict src/spec_kitty_events/connector.py` — must pass.

## Activity Log

- 2026-03-05T11:15:54Z – system – lane=planned – Prompt created.
- 2026-03-05T21:57:05Z – claude-opus-4-6 – shell_pid=38223 – lane=doing – Assigned agent via workflow command
