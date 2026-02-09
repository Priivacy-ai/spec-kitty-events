# API Contract: Lifecycle Module

**Feature**: 004-canonical-event-contract
**Module**: `spec_kitty_events.lifecycle`

## Constants

```python
SCHEMA_VERSION: str = "1.0.0"
MISSION_STARTED: str = "MissionStarted"
MISSION_COMPLETED: str = "MissionCompleted"
MISSION_CANCELLED: str = "MissionCancelled"
PHASE_ENTERED: str = "PhaseEntered"
REVIEW_ROLLBACK: str = "ReviewRollback"
MISSION_EVENT_TYPES: FrozenSet[str]  # All mission-level event type strings
TERMINAL_MISSION_STATUSES: FrozenSet[MissionStatus]  # {COMPLETED, CANCELLED}
```

## Enums

```python
class MissionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

## Payload Models

All models: `ConfigDict(frozen=True)`

```python
class MissionStartedPayload(BaseModel):
    mission_id: str
    mission_type: str
    initial_phase: str
    actor: str

class MissionCompletedPayload(BaseModel):
    mission_id: str
    mission_type: str
    final_phase: str
    actor: str

class MissionCancelledPayload(BaseModel):
    mission_id: str
    reason: str
    actor: str
    cancelled_wp_ids: List[str]

class PhaseEnteredPayload(BaseModel):
    mission_id: str
    phase_name: str
    previous_phase: Optional[str]
    actor: str

class ReviewRollbackPayload(BaseModel):
    mission_id: str
    review_ref: str
    target_phase: str
    affected_wp_ids: List[str]
    actor: str
```

## Output Models

```python
class LifecycleAnomaly(BaseModel):
    """Flagged issue during lifecycle reduction."""
    model_config = ConfigDict(frozen=True)
    event_id: str
    event_type: str
    reason: str

class ReducedMissionState(BaseModel):
    """Projected mission state from lifecycle event reduction."""
    model_config = ConfigDict(frozen=True)
    mission_id: Optional[str]
    mission_status: Optional[MissionStatus]
    mission_type: Optional[str]
    current_phase: Optional[str]
    phases_entered: Tuple[str, ...]
    wp_states: Dict[str, WPState]
    anomalies: Tuple[LifecycleAnomaly, ...]
    event_count: int
    last_processed_event_id: Optional[str]
```

## Functions

```python
def reduce_lifecycle_events(events: Sequence[Event]) -> ReducedMissionState:
    """
    Fold a sequence of lifecycle events into projected mission state.

    Pipeline:
    1. Sort by (lamport_clock, timestamp, event_id)
    2. Deduplicate by event_id
    3. Partition into mission-level and WP-level events
    4. Reduce mission events with cancel-beats-re-open precedence
    5. Delegate WP events to reduce_status_events()
    6. Merge results

    Pure function. No I/O. Deterministic for any causal-order-preserving permutation.
    """
```

## Event Model Extension (models.py)

```python
class Event(BaseModel):
    # ... existing fields unchanged ...

    correlation_id: str = Field(
        ..., min_length=26, max_length=26,
        description="ULID grouping all events in the same mission execution"
    )
    schema_version: str = Field(
        default="1.0.0", pattern=r"^\d+\.\d+\.\d+$",
        description="Envelope schema version (semver)"
    )
    data_tier: int = Field(
        default=0, ge=0, le=4,
        description="Progressive data sharing tier (0=local, 4=telemetry)"
    )
```

## Exports (__init__.py additions)

```python
# Lifecycle
from spec_kitty_events.lifecycle import (
    SCHEMA_VERSION,
    MISSION_STARTED,
    MISSION_COMPLETED,
    MISSION_CANCELLED,
    PHASE_ENTERED,
    REVIEW_ROLLBACK,
    MISSION_EVENT_TYPES,
    TERMINAL_MISSION_STATUSES,
    MissionStatus,
    MissionStartedPayload,
    MissionCompletedPayload,
    MissionCancelledPayload,
    PhaseEnteredPayload,
    ReviewRollbackPayload,
    LifecycleAnomaly,
    ReducedMissionState,
    reduce_lifecycle_events,
)
```

Total new exports: 17
