# API Contract: Status State Model

**Feature**: 003-status-state-model-contracts
**Module**: `src/spec_kitty_events/status.py`
**Date**: 2026-02-08

## Public API Surface

All symbols below are exported from `spec_kitty_events.__init__` and included in `__all__`.

### Enums

```python
# Lane enumeration (str, Enum for Python 3.10 compat)
Lane.PLANNED        # "planned"
Lane.CLAIMED        # "claimed"
Lane.IN_PROGRESS    # "in_progress"
Lane.FOR_REVIEW     # "for_review"
Lane.DONE           # "done"
Lane.BLOCKED        # "blocked"
Lane.CANCELED       # "canceled"

# Execution mode enumeration
ExecutionMode.WORKTREE     # "worktree"
ExecutionMode.DIRECT_REPO  # "direct_repo"
```

### Functions

```python
def normalize_lane(value: str) -> Lane:
    """Normalize a lane name string to canonical Lane enum.

    Accepts canonical names and known aliases (e.g., "doing" -> Lane.IN_PROGRESS).
    Raises spec_kitty_events.ValidationError for unknown values.
    """

def validate_transition(payload: StatusTransitionPayload) -> TransitionValidationResult:
    """Validate a proposed status transition against the transition matrix.

    Checks:
    - from_lane -> to_lane is a legal transition (or force is True)
    - Guard conditions are met (actor, evidence, review_ref, reason)
    - Terminal lane constraints (done/canceled require force for exit)

    Returns TransitionValidationResult with valid=True or valid=False + violations.
    Never raises exceptions for business rule violations.
    """

def status_event_sort_key(event: Event) -> Tuple[int, str, str]:
    """Deterministic sort key for status events.

    Returns (lamport_clock, timestamp_isoformat, event_id).
    Provides total ordering: lamport_clock first, then wall-clock, then ULID.
    """

def dedup_events(events: Sequence[Event]) -> List[Event]:
    """Remove duplicate events by event_id.

    Preserves first occurrence in input order.
    Input should be pre-sorted for canonical results.
    """

def reduce_status_events(events: Sequence[Event]) -> ReducedStatus:
    """Reduce a list of status events to per-WP current state.

    Pipeline: sort -> dedup -> validate transitions -> reduce.
    Pure function, no I/O. Deterministic for any permutation of the same event set.

    Events must have event_type="WPStatusChanged" and payload deserializable
    as StatusTransitionPayload. Non-matching events are silently skipped.

    Invalid transitions are recorded as anomalies, not raised as exceptions.
    Rollback-aware: reviewer rollback outranks concurrent forward progression.
    """
```

### Models (frozen Pydantic BaseModel)

```python
# Evidence models
RepoEvidence(repo=..., branch=..., commit=..., files_touched=None)
VerificationEntry(command=..., result=..., summary=None)
ReviewVerdict(reviewer=..., verdict=..., reference=None)
DoneEvidence(repos=[...], verification=[...], review=...)

# Force metadata
ForceMetadata(force=True, actor=..., reason=...)

# Core transition payload
StatusTransitionPayload(
    feature_slug=..., wp_id=...,
    from_lane=None,  # Optional[Lane], None for initial
    to_lane=...,     # Lane (aliases normalized)
    actor=...,
    force=False,     # bool
    reason=None,     # Optional[str], required when force=True
    execution_mode=...,  # ExecutionMode
    review_ref=None,     # Optional[str], required for review rollback
    evidence=None,       # Optional[DoneEvidence], required for ->done
)

# Reducer output models
WPState(wp_id=..., current_lane=..., last_event_id=..., last_transition_at=..., evidence=None)
TransitionAnomaly(event_id=..., wp_id=..., from_lane=..., to_lane=..., reason=...)
ReducedStatus(wp_states={...}, anomalies=[...], event_count=..., last_processed_event_id=None)
```

### Result Types (frozen dataclass)

```python
TransitionValidationResult(valid=True, violations=())
TransitionValidationResult(valid=False, violations=("done is terminal without force",))
```

### Exceptions

```python
TransitionError(SpecKittyEventsError)
    # Available for consumers who want to raise on invalid transitions.
    # Not raised by the library's reducer (which records anomalies instead).
```

### Constants

```python
TERMINAL_LANES: FrozenSet[Lane]  # {Lane.DONE, Lane.CANCELED}
LANE_ALIASES: Dict[str, Lane]   # {"doing": Lane.IN_PROGRESS}
WP_STATUS_CHANGED: str           # "WPStatusChanged" — canonical event_type
```

## Total New Exports (added to __init__.py __all__)

| Symbol | Type | Count |
|--------|------|-------|
| Lane | Enum | 1 |
| ExecutionMode | Enum | 1 |
| RepoEvidence | Model | 1 |
| VerificationEntry | Model | 1 |
| ReviewVerdict | Model | 1 |
| DoneEvidence | Model | 1 |
| ForceMetadata | Model | 1 |
| StatusTransitionPayload | Model | 1 |
| WPState | Model | 1 |
| TransitionAnomaly | Model | 1 |
| ReducedStatus | Model | 1 |
| TransitionValidationResult | Dataclass | 1 |
| TransitionError | Exception | 1 |
| normalize_lane | Function | 1 |
| validate_transition | Function | 1 |
| status_event_sort_key | Function | 1 |
| dedup_events | Function | 1 |
| reduce_status_events | Function | 1 |
| TERMINAL_LANES | Constant | 1 |
| LANE_ALIASES | Constant | 1 |
| WP_STATUS_CHANGED | Constant | 1 |
| **Total** | | **21** |

Combined with existing 37 exports → **58 total exports**.

## Backward Compatibility

- Zero changes to existing modules (`models.py`, `gates.py`, `clock.py`, `conflict.py`, `topology.py`, `crdt.py`, `merge.py`, `storage.py`, `error_log.py`)
- Zero changes to existing 37 exports
- New `status.py` module is purely additive
- `__init__.py` gains new import block and `__all__` entries only
