# spec-kitty-events

Event log library with Lamport clocks, CRDT merge, and canonical event contracts for distributed
systems.

**Version**: 2.1.0 | **SCHEMA_VERSION**: 2.0.0 | **Python**: >= 3.10

## Features

- **Lamport Clocks**: Establish causal ordering in distributed systems
- **Event Immutability**: Events are immutable (frozen Pydantic models)
- **Conflict Detection**: Detect concurrent events with `is_concurrent()`
- **CRDT Merge Rules**: Merge grow-only sets and counters with CRDT semantics
- **State-Machine Merge**: Resolve state conflicts with priority-based selection
- **Status State Model**: 7-lane canonical lifecycle (`Lane`) with transition validation and reducer
- **Lane Mapping Contract**: `SyncLaneV1` maps 7 canonical lanes to 4 consumer-facing sync lanes
- **Gate Observability**: Typed payloads for GitHub `check_run` gate events
- **Lifecycle Events**: Mission lifecycle contracts with typed payloads and reducer
- **Collaboration Events**: N-participant mission collaboration with advisory coordination (soft
  locks, not hard locks), 14 event types, dual-mode reducer
- **Conformance Suite**: Dual-layer validation (Pydantic + JSON Schema), manifest-driven fixtures,
  pytest-runnable conformance tests
- **JSON Schemas**: 28 committed schema artifacts generated from Pydantic models
- **Error Logging**: Systematic error tracking with retention policies
- **Storage Adapters**: Abstract storage interfaces (bring your own database)
- **Type Safety**: Full `mypy --strict` compliance with `py.typed` marker

## Installation

### From PyPI

```bash
pip install "spec-kitty-events>=2.1.0,<3.0.0"
```

With conformance testing support (adds `jsonschema`):

```bash
pip install "spec-kitty-events[conformance]>=2.0.0rc1,<3.0.0"
```

### From Git

```bash
pip install "git+https://github.com/Priivacy-ai/spec-kitty-events.git@v2.1.0"
```

### Development Installation

```bash
git clone https://github.com/Priivacy-ai/spec-kitty-events.git
cd spec-kitty-events
pip install -e ".[dev,conformance]"
```

## Quick Start

### Lane Mapping (New in 2.0.0)

```python
from spec_kitty_events import Lane, SyncLaneV1, canonical_to_sync_v1

# Convert canonical 7-lane model to consumer-facing 4-lane model
sync_lane = canonical_to_sync_v1(Lane.IN_PROGRESS)
assert sync_lane == SyncLaneV1.DOING

sync_lane = canonical_to_sync_v1(Lane.BLOCKED)
assert sync_lane == SyncLaneV1.DOING  # blocked collapses to doing
```

### Event Emission

```python
import uuid
from datetime import datetime
from spec_kitty_events import (
    Event,
    LamportClock,
    InMemoryClockStorage,
    InMemoryEventStore,
)

clock_storage = InMemoryClockStorage()
event_store = InMemoryEventStore()
clock = LamportClock(node_id="alice", storage=clock_storage)

clock.tick()
event = Event(
    event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    event_type="WPStatusChanged",
    aggregate_id="WP001",
    timestamp=datetime.now(),
    node_id="alice",
    lamport_clock=clock.current(),
    project_uuid=uuid.uuid4(),
    correlation_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    payload={"state": "doing"},
)
event_store.save_event(event)
```

### Conformance Validation

```python
from spec_kitty_events.conformance import validate_event

payload = {
    "feature_slug": "005-my-feature",
    "wp_id": "WP01",
    "to_lane": "in_progress",
    "actor": "ci-bot",
    "execution_mode": "worktree",
}
result = validate_event(payload, "WPStatusChanged")
assert result.valid
```

### Collaboration Events (New in 2.1.0)

N-participant mission collaboration with advisory coordination. Soft locks, not hard locks --
warnings are informational and participants decide how to respond.

**14 event types** grouped by category:

| Category | Event Types |
|---|---|
| Participant Lifecycle | `ParticipantInvited`, `ParticipantJoined`, `ParticipantLeft`, `PresenceHeartbeat` |
| Drive Intent & Focus | `DriveIntentSet`, `FocusChanged` |
| Step Execution | `PromptStepExecutionStarted`, `PromptStepExecutionCompleted` |
| Advisory Warnings | `ConcurrentDriverWarning`, `PotentialStepCollisionDetected`, `WarningAcknowledged` |
| Communication | `CommentPosted`, `DecisionCaptured` |
| Session | `SessionLinked` |

**Key exports**: `ParticipantIdentity`, `FocusTarget`, `reduce_collaboration_events`,
`ReducedCollaborationState`, `UnknownParticipantError`, `CollaborationAnomaly`

```python
from spec_kitty_events import (
    Event,
    ParticipantIdentity,
    ParticipantJoinedPayload,
    PARTICIPANT_JOINED,
    reduce_collaboration_events,
    FocusTarget,
)

# Construct a participant identity
identity = ParticipantIdentity(
    participant_id="p-abc123",
    participant_type="human",
    display_name="Alice",
)

# Construct a typed payload
payload = ParticipantJoinedPayload(
    participant_id="p-abc123",
    participant_identity=identity,
    mission_id="mission/M042",
)

# Reduce collaboration events into materialized state
state = reduce_collaboration_events([])
assert state.event_count == 0
```

See [COMPATIBILITY.md](COMPATIBILITY.md) for the full collaboration event contracts, reducer
pipeline details, and SaaS-authoritative participation model.

### Conflict Detection and Resolution

```python
from spec_kitty_events import is_concurrent, state_machine_merge

# Detect concurrent events
if is_concurrent(event1, event2):
    priority_map = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}
    resolution = state_machine_merge([event1, event2], priority_map)
    winner = resolution.merged_event
```

## Documentation

- **[CHANGELOG.md](CHANGELOG.md)**: Version history and migration notes
- **[COMPATIBILITY.md](COMPATIBILITY.md)**: Lane mapping table, field reference, versioning policy,
  CI integration guide
- **Type hints**: Full mypy --strict compliance (source is the documentation)
- **Conformance suite**: `pytest --pyargs spec_kitty_events.conformance -v`

## Public API (104 Exports)

The `spec_kitty_events` package exports 104 symbols covering:

| Category | Count | Key Exports |
|---|---|---|
| Core models | 4 | `Event`, `ErrorEntry`, `ConflictResolution` |
| Exceptions | 4 | `SpecKittyEventsError`, `StorageError`, `ValidationError`, `CyclicDependencyError` |
| Storage | 6 | `EventStore`, `ClockStorage`, `ErrorStorage`, `InMemory*` |
| Clocks | 1 | `LamportClock` |
| Conflict detection | 3 | `is_concurrent`, `total_order_key`, `topological_sort` |
| Merge functions | 3 | `merge_gset`, `merge_counter`, `state_machine_merge` |
| Error logging | 1 | `ErrorLog` |
| Gate observability | 5 | `GatePayloadBase`, `GatePassedPayload`, `GateFailedPayload`, `map_check_run_conclusion`, `UnknownConclusionError` |
| Lifecycle events | 15 | `SCHEMA_VERSION`, `MissionStatus`, payload models, reducer, constants |
| Status model | 25 | `Lane`, `SyncLaneV1`, `canonical_to_sync_v1`, `StatusTransitionPayload`, reducer, validators |
| Collaboration events | 36 | `ParticipantIdentity`, `FocusTarget`, payload models, reducer, constants, warnings |
| Version | 1 | `__version__` |

## Testing

Run the full test suite (790 tests, 98% coverage):

```bash
pytest --cov --cov-report=html
```

Run conformance tests only:

```bash
pytest --pyargs spec_kitty_events.conformance -v
```

Type checking:

```bash
mypy src/spec_kitty_events --strict
```

Schema drift check:

```bash
python -m spec_kitty_events.schemas.generate --check
```

## Requirements

- Python >= 3.10
- Pydantic >= 2.0.0, < 3.0.0
- python-ulid >= 1.1.0
- jsonschema >= 4.21.0, < 5.0.0 (optional, for `[conformance]` extra)

## Release and Publishing

This repository uses GitHub Actions trusted publishing:

1. `publish-testpypi.yml`: Manual TestPyPI dry run.
2. `publish-pypi.yml`: Publish on `v*` tags (or manual dispatch) to PyPI.

Release flow:

1. Update `project.version` in `pyproject.toml`.
2. Commit to `main`.
3. Create and push matching tag (e.g., `v2.1.0` for `version = "2.1.0"`).
4. Approve the `pypi` GitHub environment (if required).
5. Verify package on PyPI and install in a clean environment.

## License

All rights reserved. This is a private repository owned by Priivacy AI.

---

Generated with [Spec Kitty](https://github.com/robdouglass/SpecKitty)
