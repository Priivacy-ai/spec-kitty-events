# Quickstart: Mission Collaboration Contracts

**Feature**: 006-mission-collaboration-soft-coordination-contracts

## Installation

```bash
pip install spec-kitty-events>=2.1.0,<3.0.0
```

## Constructing Collaboration Events

### 1. Participant Joins a Mission (SaaS emits)

```python
from spec_kitty_events import (
    Event, ParticipantIdentity, ParticipantJoinedPayload,
    PARTICIPANT_JOINED,
)
from ulid import ULID
from datetime import datetime, timezone

identity = ParticipantIdentity(
    participant_id="p-abc123",        # SaaS-minted, mission-scoped
    participant_type="human",
    display_name="Alice",
    session_id="sess-001",
)

payload = ParticipantJoinedPayload(
    participant_id="p-abc123",
    participant_identity=identity,
    mission_id="mission/M042",
    auth_principal_id="auth:alice@example.com",  # Optional, for live traffic
)

event = Event(
    event_id=str(ULID()),
    event_type=PARTICIPANT_JOINED,
    aggregate_id="mission/M042",          # Canonical: aggregate_id = mission_id
    payload=payload.model_dump(),
    timestamp=datetime.now(timezone.utc),
    node_id="saas-node-1",
    lamport_clock=1,
    project_uuid=project_uuid,
    correlation_id="run-001",             # Canonical: correlation_id = mission_run_id
)
```

### 2. Setting Drive Intent and Focus

```python
from spec_kitty_events import (
    DriveIntentSetPayload, FocusChangedPayload, FocusTarget,
    DRIVE_INTENT_SET, FOCUS_CHANGED,
)

# Declare active drive intent (mission-scoped)
intent_payload = DriveIntentSetPayload(
    participant_id="p-abc123",
    mission_id="mission/M042",
    intent="active",
)

# Set focus on a specific work package
focus_payload = FocusChangedPayload(
    participant_id="p-abc123",
    mission_id="mission/M042",
    focus_target=FocusTarget(target_type="wp", target_id="WP03"),
)
```

### 3. Acknowledging a Warning

```python
from spec_kitty_events import (
    WarningAcknowledgedPayload, WARNING_ACKNOWLEDGED,
)

ack_payload = WarningAcknowledgedPayload(
    participant_id="p-abc123",
    mission_id="mission/M042",
    warning_id="warn-001",
    acknowledgement="continue",  # One of: continue, hold, reassign, defer
)
```

## Reducing Collaboration Events

### Strict Mode (default — for live traffic)

```python
from spec_kitty_events import reduce_collaboration_events, UnknownParticipantError

try:
    state = reduce_collaboration_events(events)  # mode="strict" is default
except UnknownParticipantError as e:
    # Event from participant not in mission roster — reject
    print(f"Rejected: participant {e.participant_id} not rostered (event {e.event_id})")
```

### Permissive Mode (for replay/import)

```python
state = reduce_collaboration_events(events, mode="permissive")

# Check for anomalies (non-fatal issues)
for anomaly in state.anomalies:
    print(f"Anomaly: {anomaly.reason} (event {anomaly.event_id})")
```

### Reading Reduced State

```python
# Mission snapshot
print(f"Active participants: {len(state.participants)}")
print(f"Active drivers: {state.active_drivers}")

# Focus indexes
for pid, target in state.focus_by_participant.items():
    print(f"  {pid} focused on {target.target_type}:{target.target_id}")

# Reverse lookup: who's on WP03?
from spec_kitty_events import FocusTarget
wp03 = FocusTarget(target_type="wp", target_id="WP03")
participants_on_wp03 = state.participants_by_focus.get(wp03, frozenset())

# Warning timeline
for warning in state.warnings:
    print(f"  Warning {warning.warning_id}: {warning.warning_type}")
    print(f"  Acknowledged by: {list(warning.acknowledgements.keys())}")

# Decisions
for decision in state.decisions:
    print(f"  Decision: {decision.topic} → {decision.chosen_option}")
```

## Conformance Testing (consumer CI)

```bash
# Run conformance suite in your CI pipeline
pytest --pyargs spec_kitty_events.conformance
```

## Envelope Mapping Rules

All collaboration events follow this canonical mapping:

| Event field | Maps to |
|---|---|
| `aggregate_id` | `mission_id` (e.g., `"mission/M042"`) |
| `correlation_id` | `mission_run_id` (run-specific identifier) |
| `event_type` | One of the 14 `COLLABORATION_EVENT_TYPES` constants |
| `node_id` | Emitting process/node (not participant identity) |

## Key Constraints

- **SaaS-authoritative**: `participant_id` is minted by SaaS. CLI must not invent identities.
- **Strict mode default**: Unknown participants are rejected in live traffic.
- **Advisory warnings**: No hard locks. `ConcurrentDriverWarning` and `PotentialStepCollisionDetected` are informational.
- **Acknowledgement actions**: `continue` (proceed), `hold` (pause), `reassign` (hand off), `defer` (postpone).
