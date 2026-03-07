# Quickstart: Per-User Identity in Connector Events

## What changed

`CONNECTOR_SCHEMA_VERSION` bumped from `2.7.0` to `2.8.0`. All changes are additive.

## New imports

```python
from spec_kitty_events import (
    # New event type constants
    USER_CONNECTED,           # "UserConnected"
    USER_DISCONNECTED,        # "UserDisconnected"

    # New payload models
    UserConnectedPayload,
    UserDisconnectedPayload,

    # New roster model
    UserConnectionStatus,

    # Existing (updated with user_connections field)
    ReducedConnectorState,
    reduce_connector_events,
)
```

## Emitting per-user events

```python
from spec_kitty_events import Event, USER_CONNECTED

# User authenticates their Jira connection
event = Event(
    event_id=str(ULID()),
    event_type=USER_CONNECTED,
    aggregate_id="connector/binding-001",
    payload={
        "connector_id": "binding-001",
        "connector_type": "jira",
        "provider": "jira",
        "mission_id": "mission-001",
        "project_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "actor_id": "user-123",
        "actor_type": "human",
        "endpoint_url": "https://mycompany.atlassian.net",
        "recorded_at": "2026-03-05T10:00:00Z",
        "user_id": "user-123",  # Required for user-level events
    },
    timestamp=datetime.now(timezone.utc),
    node_id="saas-web",
    lamport_clock=42,
    project_uuid=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
    correlation_id=str(ULID()),
)
```

## Using user_id on existing events

```python
# System health check on user-123's token
degraded_payload = {
    "connector_id": "binding-001",
    "connector_type": "jira",
    "provider": "jira",
    "mission_id": "mission-001",
    "project_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "actor_id": "system",          # system triggered the check
    "actor_type": "system",
    "endpoint_url": "https://mycompany.atlassian.net",
    "recorded_at": "2026-03-05T11:00:00Z",
    "degradation_reason": "OAuth token expired",
    "last_healthy_at": "2026-03-04T10:00:00Z",
    "user_id": "user-123",         # whose token expired (Optional, new)
}
```

## Reading per-user roster from reducer

```python
state = reduce_connector_events(events)

# Binding-level state (unchanged)
print(state.current_state)     # e.g., ConnectorState.HEALTHY
print(state.transition_log)    # binding-level transitions

# Per-user roster (new)
for uc in state.user_connections:
    print(f"  {uc.user_id}: {uc.state.value} (last: {uc.last_event_at})")
```

## Backward compatibility

Events without `user_id` continue to work. The field defaults to `None` on all existing payload models. The reducer ignores `None` user_id values when building the roster.
