# Quickstart: Canonical Event Contract

**Feature**: 004-canonical-event-contract

## Creating Lifecycle Events

```python
from datetime import datetime, timezone
from ulid import ULID
from spec_kitty_events import Event
from spec_kitty_events.lifecycle import (
    SCHEMA_VERSION,
    MISSION_STARTED,
    MissionStartedPayload,
    PhaseEnteredPayload,
    MissionCompletedPayload,
)

# Generate IDs for this mission execution
mission_correlation_id = str(ULID())
project_uuid = "550e8400-e29b-41d4-a716-446655440000"

# Create a MissionStarted event
payload = MissionStartedPayload(
    mission_id="mission-001",
    mission_type="software-dev",
    initial_phase="specify",
    actor="agent-claude",
)
event = Event(
    event_id=str(ULID()),
    event_type=MISSION_STARTED,
    aggregate_id="mission-001",
    payload=payload.model_dump(),
    timestamp=datetime.now(timezone.utc),
    node_id="local",
    lamport_clock=1,
    correlation_id=mission_correlation_id,
    project_uuid=project_uuid,
)

# schema_version defaults to "1.0.0"
# data_tier defaults to 0 (local-only)
```

## Reducing a Mission Event Sequence

```python
from spec_kitty_events.lifecycle import (
    reduce_lifecycle_events,
    MissionStatus,
)

# Given a list of events from a mission execution
events: list[Event] = [mission_started, phase_entered, wp_changed, gate_passed, mission_completed]

# Reduce to projected state
state = reduce_lifecycle_events(events)

print(state.mission_status)   # MissionStatus.COMPLETED
print(state.current_phase)    # "review"
print(state.wp_states)        # {"WP01": WPState(current_lane=Lane.DONE, ...)}
print(state.anomalies)        # [] (no anomalies)
print(state.event_count)      # 5
```

## Precedence: Cancel Beats Re-Open

```python
# Two concurrent events at same Lamport clock
cancel_event = Event(
    event_type=MISSION_CANCELLED,
    lamport_clock=10,
    # ...
)
reopen_event = Event(
    event_type=PHASE_ENTERED,  # attempting to re-enter a phase
    lamport_clock=10,
    # ...
)

# Regardless of physical order, cancel wins
state = reduce_lifecycle_events([reopen_event, cancel_event])
assert state.mission_status == MissionStatus.CANCELLED

state = reduce_lifecycle_events([cancel_event, reopen_event])
assert state.mission_status == MissionStatus.CANCELLED
```

## Data Tier Annotation

```python
# Local-only event (default)
local_event = Event(data_tier=0, ...)  # Never synced

# Team-scoped event
team_event = Event(data_tier=2, ...)   # Visible to team

# Telemetry event
telemetry_event = Event(data_tier=4, ...)  # Anonymized, aggregated
```

## Envelope Versioning

```python
from spec_kitty_events.lifecycle import SCHEMA_VERSION

# Current version
print(SCHEMA_VERSION)  # "1.0.0"

# Events carry their schema version
event = Event(schema_version="1.0.0", ...)

# Future: events from older versions still deserialize
# (new optional fields get defaults)
old_event_dict = {"schema_version": "1.0.0", ...}  # no future field
Event.from_dict(old_event_dict)  # works, future field defaults to None
```
