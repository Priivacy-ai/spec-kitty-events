---
work_package_id: WP03
title: Lifecycle Reducer + Precedence Rules
lane: "doing"
dependencies: []
base_branch: 004-canonical-event-contract-WP02
base_commit: 2cbbcb8e80e7d85853b0e984ad8d29f0a32ce61f
created_at: '2026-02-09T11:46:09.591389+00:00'
subtasks: [T014, T015, T016, T017, T018, T019, T020]
agent: "claude-opus"
shell_pid: "18661"
history:
- date: '2026-02-09'
  agent: claude-opus
  action: created
  note: Generated from /spec-kitty.tasks
---

# WP03: Lifecycle Reducer + Precedence Rules

## Objective

Implement the lifecycle reducer function (`reduce_lifecycle_events()`) that folds a sequence of events into projected mission state, with explicit precedence rules for cancel-beats-re-open (F-Reducer-001), rollback-creates-new-event (F-Reducer-002), and idempotent dedup (F-Reducer-003). This is the core acceptance criteria WP (2E-03 through 2E-06).

## Context

The lifecycle reducer builds on the WP-level `reduce_status_events()` from Feature 003. It:
1. Handles mission-level events (MissionStarted, PhaseEntered, MissionCompleted, MissionCancelled, ReviewRollback)
2. Delegates WP-level events (WPStatusChanged) to the existing Feature 003 reducer
3. Applies cancel-beats-re-open precedence for concurrent mission events
4. Is a pure function — no I/O, deterministic for any causal-order-preserving permutation

**Reference files**:
- `src/spec_kitty_events/status.py` — Read Section 6 (reducer implementation) for the reduce pipeline pattern
- `src/spec_kitty_events/lifecycle.py` — The models from WP02 (MissionStatus, payload models, constants)
- `tests/property/test_status_determinism.py` — Reference for Hypothesis property test patterns

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

## Detailed Guidance

### T014: Implement LifecycleAnomaly and ReducedMissionState Models

**File**: `src/spec_kitty_events/lifecycle.py` — Section 4

```python
class LifecycleAnomaly(BaseModel):
    """Flagged issue during lifecycle reduction.

    Anomalies are non-fatal — the reducer continues processing but records
    the issue for observability.
    """
    model_config = ConfigDict(frozen=True)

    event_id: str = Field(..., description="Event that caused the anomaly")
    event_type: str = Field(..., description="Type of the problematic event")
    reason: str = Field(..., description="Human-readable explanation")
```

```python
class ReducedMissionState(BaseModel):
    """Projected mission state from lifecycle event reduction.

    Produced by reduce_lifecycle_events(). Contains both mission-level
    state (status, phase) and delegated WP-level state (via reduce_status_events).
    """
    model_config = ConfigDict(frozen=True)

    mission_id: Optional[str] = Field(None, description="Mission ID from MissionStarted")
    mission_status: Optional[MissionStatus] = Field(None, description="Current mission status")
    mission_type: Optional[str] = Field(None, description="Mission type from MissionStarted")
    current_phase: Optional[str] = Field(None, description="Current phase from PhaseEntered")
    phases_entered: tuple[str, ...] = Field(default_factory=tuple, description="Ordered list of phases entered")
    wp_states: dict[str, "WPState"] = Field(default_factory=dict, description="WP states from delegated reduction")
    anomalies: tuple[LifecycleAnomaly, ...] = Field(default_factory=tuple, description="Flagged issues")
    event_count: int = Field(0, description="Total events processed")
    last_processed_event_id: Optional[str] = Field(None, description="Last event ID processed")
```

**Design notes**:
- Use `tuple` for immutable sequences (phases_entered, anomalies) to match frozen model pattern
- For Python 3.10 compat, use `from __future__ import annotations` at module top OR use `Tuple` from typing
- Import `WPState` from status module: `from spec_kitty_events.status import WPState, ReducedStatus, reduce_status_events, status_event_sort_key, dedup_events, WP_STATUS_CHANGED`

### T015: Implement reduce_lifecycle_events() Core Pipeline

**File**: `src/spec_kitty_events/lifecycle.py` — Section 5

```python
from typing import Sequence
from spec_kitty_events.models import Event
from spec_kitty_events.status import (
    WPState,
    ReducedStatus,
    reduce_status_events,
    status_event_sort_key,
    dedup_events,
    WP_STATUS_CHANGED,
)


def reduce_lifecycle_events(events: Sequence[Event]) -> ReducedMissionState:
    """Fold a sequence of lifecycle events into projected mission state.

    Pipeline:
    1. Sort by (lamport_clock, timestamp, event_id)
    2. Deduplicate by event_id
    3. Partition into mission-level and WP-level events
    4. Reduce mission events with cancel-beats-re-open precedence
    5. Delegate WP events to reduce_status_events()
    6. Merge results

    Pure function. No I/O. Deterministic for any causal-order-preserving
    permutation.
    """
```

**Implementation steps**:

1. **Sort**: Use `status_event_sort_key` from status.py (reuse, don't reimplement)
   ```python
   sorted_events = sorted(events, key=status_event_sort_key)
   ```

2. **Dedup**: Use `dedup_events` from status.py
   ```python
   unique_events = dedup_events(sorted_events)
   ```

3. **Partition**: Split into mission-level and WP-level events
   ```python
   mission_events = [e for e in unique_events if e.event_type in MISSION_EVENT_TYPES]
   wp_events = [e for e in unique_events if e.event_type == WP_STATUS_CHANGED]
   # Events with unknown types are ignored (not an error)
   ```

4. **Reduce mission events**: Process sequentially with concurrent group handling
   - Group by lamport_clock
   - Within each group, apply cancel-beats-re-open precedence (T016)
   - Track mission_id, mission_status, current_phase, phases_entered
   - Flag anomalies for: events before MissionStarted, events after terminal state, unknown event types

5. **Delegate WP events**: Pass to `reduce_status_events(wp_events)`
   ```python
   wp_result: ReducedStatus = reduce_status_events(wp_events)
   ```

6. **Merge**: Combine mission state + WP states + anomalies from both levels

7. **Return**: `ReducedMissionState` with all fields populated

**Edge cases to handle**:
- Empty event list → return default ReducedMissionState (all None/empty)
- No MissionStarted event → process what's there, flag anomaly for first non-start event
- Multiple MissionStarted events → first one wins, subsequent flagged as anomalies
- Events with unknown event_type → silently skip (not mission-level, not WP-level)

### T016: Implement Cancel-Beats-Re-Open Precedence (F-Reducer-001)

**Location**: Inside `reduce_lifecycle_events()` mission event processing

Within each concurrent group (events with same lamport_clock):
1. Collect all mission events in the group
2. If ANY event in the group is MissionCancelled:
   - Process all non-cancel events first
   - Process MissionCancelled LAST so it overwrites any concurrent state changes
3. If no MissionCancelled in group:
   - Process events in their sorted order (by event_id as tiebreaker)

```python
# Within a concurrent group (same lamport_clock):
group_events = [e for e in mission_events if e.lamport_clock == current_clock]

# Sort: MissionCancelled events go last within the group
def cancel_last_key(e: Event) -> tuple[int, str]:
    # 1 for cancel (sorts after 0), then by event_id for stability
    is_cancel = 1 if e.event_type == MISSION_CANCELLED else 0
    return (is_cancel, e.event_id)

group_events.sort(key=cancel_last_key)
```

**This mirrors Feature 003's rollback-aware precedence** (status.py Section 6) where reviewer rollbacks apply last within concurrent groups.

**F-Reducer-001 test scenario**:
- Create mission in ACTIVE state (MissionStarted at clock=1)
- At clock=5: simultaneous MissionCancelled and PhaseEntered events (different node_ids, same clock)
- Verify: regardless of physical order in input, reducer produces CANCELLED state
- Verify: run with [cancel, phase_entered] and [phase_entered, cancel] — same result both ways

### T017: Implement Rollback Handling (F-Reducer-002)

**Location**: Inside `reduce_lifecycle_events()` mission event processing

When a ReviewRollback event is processed:
1. Parse the ReviewRollbackPayload from the event's payload
2. Update current_phase to the rollback's target_phase
3. Add the target_phase to phases_entered (re-entering a phase)
4. Do NOT modify or remove any previously processed events
5. The event log remains strictly append-only

```python
if event.event_type == REVIEW_ROLLBACK:
    try:
        payload = ReviewRollbackPayload(**event.payload)
        current_phase = payload.target_phase
        phases_entered.append(payload.target_phase)
    except Exception:
        anomalies.append(LifecycleAnomaly(
            event_id=event.event_id,
            event_type=event.event_type,
            reason="Invalid ReviewRollback payload",
        ))
```

**F-Reducer-002 test scenario**:
- Create mission: MissionStarted → PhaseEntered("implement") → WPStatusChanged(doing) → ReviewRollback(target_phase="specify")
- Verify: current_phase == "specify" after reduction
- Verify: all 4 events are present in the event count (nothing deleted/overwritten)
- Verify: phases_entered contains both "implement" and "specify"

### T018: Verify Idempotent Dedup (F-Reducer-003)

**Location**: This is verified by the existing `dedup_events()` from Feature 003, which the lifecycle reducer reuses.

**F-Reducer-003 test scenario**:
- Create a full mission event sequence (5 events)
- Duplicate every event (10 events total, each with same event_id)
- Reduce the duplicated sequence
- Reduce the original sequence
- Verify: both produce identical ReducedMissionState

No new code needed — just the test verifying the behavior.

### T019: Add Unit Tests for Reducer

**File**: `tests/unit/test_lifecycle.py` (append to existing file from WP02)

**Test categories**:

1. **Empty sequence**: `reduce_lifecycle_events([])` returns default state (all None/empty)

2. **Single MissionStarted**: Returns ACTIVE status with mission_id, mission_type, initial_phase

3. **Full happy path**: MissionStarted → PhaseEntered("specify") → PhaseEntered("implement") → MissionCompleted → returns COMPLETED with all phases tracked

4. **Cancellation path**: MissionStarted → PhaseEntered → MissionCancelled → returns CANCELLED with reason

5. **Mixed mission + WP events**: MissionStarted + PhaseEntered + WPStatusChanged(planned→doing) + WPStatusChanged(doing→for_review) + MissionCompleted → ReducedMissionState has both mission status and wp_states

6. **Anomaly: event before MissionStarted**: PhaseEntered without prior MissionStarted → anomaly flagged

7. **Anomaly: event after terminal state**: MissionCompleted → PhaseEntered → anomaly on the PhaseEntered

8. **F-Reducer-001 (cancel beats re-open)**: Concurrent MissionCancelled + PhaseEntered at same clock → CANCELLED, both physical orderings tested

9. **F-Reducer-002 (rollback creates new event)**: ReviewRollback updates phase, event count includes all events

10. **F-Reducer-003 (idempotent dedup)**: Duplicate event delivery → same result as single delivery

### T020: Add Property Tests for Reducer Determinism

**File**: `tests/property/test_lifecycle_determinism.py` (NEW)

```python
"""Property tests proving lifecycle reducer determinism."""
import random
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Strategy: generate a valid mission event sequence
# then shuffle preserving causal order (Lamport clock ordering)
# and verify identical output

@settings(max_examples=200, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**32))
def test_reducer_determinism_across_physical_orderings(seed: int) -> None:
    """Same event set in different physical orderings produces identical state.

    Acceptance criteria 2E-03: replay same events in varied physical order
    where causal order is equivalent → identical final state.
    """
    # Build a deterministic event sequence
    events = build_test_mission_sequence()  # helper function

    # Shuffle N times preserving causal order (sort by lamport_clock)
    rng = random.Random(seed)
    shuffled = list(events)
    # Group by lamport_clock, shuffle within groups (causal order preserved)
    # Then shuffle group order (same clock = concurrent = can reorder)

    result_original = reduce_lifecycle_events(events)
    result_shuffled = reduce_lifecycle_events(shuffled)

    assert result_original == result_shuffled
```

**Key**: The property test should generate events with varying Lamport clocks, then prove that any causal-order-preserving permutation yields the same result. Use `@settings(deadline=None)` for complex strategies.

## Definition of Done

- [ ] `reduce_lifecycle_events()` implemented in lifecycle.py
- [ ] ReducedMissionState and LifecycleAnomaly models implemented
- [ ] Cancel-beats-re-open precedence works (F-Reducer-001 test passes)
- [ ] Rollback handling works (F-Reducer-002 test passes)
- [ ] Idempotent dedup works (F-Reducer-003 test passes)
- [ ] Property tests prove determinism across 200 random orderings
- [ ] Unit tests cover empty, single, happy path, cancel, rollback, anomaly scenarios
- [ ] `mypy --strict src/spec_kitty_events/lifecycle.py` passes
- [ ] All existing tests still pass

## Risks

- **Composition with reduce_status_events()**: The lifecycle reducer filters WP events and delegates. If a WP event has an unexpected format, reduce_status_events() may flag anomalies. Test with realistic mixed sequences.
- **Concurrent group handling**: The cancel-beats-re-open logic must correctly identify concurrent events (same lamport_clock). Events with different clocks are sequential and don't need precedence resolution.
- **Property test performance**: Limit Hypothesis to 200 examples with deadline=None to avoid CI timeouts.

## Reviewer Guidance

1. Verify reduce_lifecycle_events is a pure function (no I/O, no mutable state)
2. Verify cancel-beats-re-open precedence with both physical orderings
3. Verify rollback does NOT modify event list (append-only)
4. Verify dedup uses existing dedup_events() (no reimplementation)
5. Verify anomaly detection for: events before start, events after terminal, invalid payloads
6. Run `python3.11 -m pytest tests/unit/test_lifecycle.py tests/property/test_lifecycle_determinism.py`
7. Run `python3.11 -m pytest` for full suite

## Activity Log

- 2026-02-09T11:46:09Z – claude-opus – shell_pid=13053 – lane=doing – Assigned agent via workflow command
- 2026-02-09T11:53:11Z – claude-opus – shell_pid=13053 – lane=for_review – Ready for review: lifecycle reducer with cancel-beats-re-open, rollback handling, idempotent dedup, 420 tests pass, mypy clean
- 2026-02-09T11:53:27Z – claude-opus – shell_pid=18661 – lane=doing – Started review via workflow command
