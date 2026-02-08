# Quickstart: Status State Model Contracts

**Feature**: 003-status-state-model-contracts
**Version**: 0.3.0-alpha

## Install

```bash
pip install -e ".[dev]"
```

## 1. Create a Status Transition Event

```python
from spec_kitty_events import (
    Lane, ExecutionMode, StatusTransitionPayload,
    Event, LamportClock, InMemoryClockStorage,
)
import uuid
from datetime import datetime, timezone
from ulid import ULID

# Build the status payload
payload = StatusTransitionPayload(
    feature_slug="003-status-state-model-contracts",
    wp_id="WP01",
    from_lane=Lane.PLANNED,
    to_lane=Lane.CLAIMED,
    actor="alice",
    execution_mode=ExecutionMode.WORKTREE,
)

# Wrap in a generic Event for the canonical log
clock_storage = InMemoryClockStorage()
clock = LamportClock(node_id="alice-laptop", storage=clock_storage)

event = Event(
    event_id=str(ULID()),
    event_type="WPStatusChanged",
    aggregate_id="003-status-state-model-contracts/WP01",
    payload=payload.model_dump(),
    timestamp=datetime.now(timezone.utc),
    node_id="alice-laptop",
    lamport_clock=clock.tick(),
    project_uuid=uuid.uuid4(),
)
```

## 2. Normalize Legacy Lane Names

```python
from spec_kitty_events import normalize_lane, Lane

lane = normalize_lane("doing")
assert lane == Lane.IN_PROGRESS

# Unknown values raise ValidationError
from spec_kitty_events import ValidationError
try:
    normalize_lane("unknown_lane")
except ValidationError:
    print("Caught unknown lane")
```

## 3. Validate a Transition Before Applying

```python
from spec_kitty_events import validate_transition, StatusTransitionPayload, Lane, ExecutionMode

payload = StatusTransitionPayload(
    feature_slug="my-feature",
    wp_id="WP01",
    from_lane=Lane.PLANNED,
    to_lane=Lane.CLAIMED,
    actor="bob",
    execution_mode=ExecutionMode.DIRECT_REPO,
)

result = validate_transition(payload)
assert result.valid

# Invalid: done is terminal
payload_bad = StatusTransitionPayload(
    feature_slug="my-feature",
    wp_id="WP01",
    from_lane=Lane.DONE,
    to_lane=Lane.PLANNED,
    actor="bob",
    force=True,
    reason="Reopening for fixes",
    execution_mode=ExecutionMode.WORKTREE,
)
result = validate_transition(payload_bad)
assert result.valid  # Force overrides terminal constraint
```

## 4. Build Done Evidence

```python
from spec_kitty_events import (
    DoneEvidence, RepoEvidence, VerificationEntry, ReviewVerdict,
)

evidence = DoneEvidence(
    repos=[
        RepoEvidence(
            repo="spec-kitty-events",
            branch="003-status-state-model-contracts-WP01",
            commit="abc1234",
            files_touched=["src/spec_kitty_events/status.py"],
        ),
    ],
    verification=[
        VerificationEntry(
            command="python3.11 -m pytest tests/",
            result="42 passed",
            summary="All tests green",
        ),
    ],
    review=ReviewVerdict(
        reviewer="charlie",
        verdict="approved",
        reference="PR #42",
    ),
)
```

## 5. Reduce Events to Current State

```python
from spec_kitty_events import reduce_status_events, Lane

# events: List[Event] with event_type="WPStatusChanged"
reduced = reduce_status_events(events)

# Check per-WP state
for wp_id, state in reduced.wp_states.items():
    print(f"{wp_id}: {state.current_lane}")

# Check for anomalies (invalid transitions)
if reduced.anomalies:
    for anomaly in reduced.anomalies:
        print(f"WARNING: {anomaly.wp_id} - {anomaly.reason}")
```

## 6. Merge and Deduplicate Event Logs

```python
from spec_kitty_events import dedup_events, status_event_sort_key

# Merge two event logs (e.g., after git merge)
merged = log_a + log_b

# Sort deterministically
sorted_events = sorted(merged, key=status_event_sort_key)

# Remove duplicates
unique_events = dedup_events(sorted_events)

# Reduce to canonical state
reduced = reduce_status_events(unique_events)
```
