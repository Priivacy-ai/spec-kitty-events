---
work_package_id: WP03
title: Ordering Primitives and Reference Reducer
lane: "doing"
dependencies: []
base_branch: main
base_commit: 20112f62248c9c9a7a0203b735453fb08a7faba6
created_at: '2026-02-08T14:25:05.042627+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - Ordering and Reduction
assignee: ''
agent: "claude-opus"
shell_pid: "41460"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Ordering Primitives and Reference Reducer

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

## Objectives & Success Criteria

Implement `status_event_sort_key()`, `dedup_events()`, reducer output models (WPState, TransitionAnomaly, ReducedStatus), and the reference `reduce_status_events()` function with rollback-aware precedence. Write unit tests and Hypothesis property tests for determinism and idempotency.

**Success criteria**:
- `status_event_sort_key()` returns deterministic `(lamport_clock, timestamp_iso, event_id)` tuple
- `dedup_events()` removes duplicates by event_id, preserving first occurrence
- `reduce_status_events()` produces correct per-WP state from any permutation of events
- Rollback-aware precedence: reviewer rollback outranks concurrent forward progression
- Invalid transitions flagged as anomalies, not raised as exceptions
- Property tests prove determinism (any permutation → same result) and dedup idempotency
- `__init__.py` updated with remaining 6 exports
- mypy --strict clean, all tests pass

## Context & Constraints

**Reference documents**:
- `kitty-specs/003-status-state-model-contracts/data-model.md` — WPState, TransitionAnomaly, ReducedStatus definitions
- `kitty-specs/003-status-state-model-contracts/contracts/status-api.md` — function signatures
- `kitty-specs/003-status-state-model-contracts/research.md` — R3 (payload/Event relationship), R4 (sort key), R5 (rollback precedence)
- `kitty-specs/003-status-state-model-contracts/plan.md` — D5 (reducer pipeline), D6 (rollback-aware precedence)

**WP01 provides**: Lane, ExecutionMode, StatusTransitionPayload, DoneEvidence, evidence models, constants
**WP02 provides**: validate_transition(), TransitionValidationResult, transition matrix

**Key design decisions**:
- Sort/dedup/reduce functions operate on `Event` objects (from `spec_kitty_events.models`), not bare payloads
- The reducer extracts `StatusTransitionPayload` from `Event.payload` internally
- `status_event_sort_key` uses `(lamport_clock, timestamp_iso, event_id)` — different from existing `total_order_key` which uses `(lamport_clock, node_id)`
- The reducer is a single pure function: no I/O, no streaming, no callbacks

## Subtasks & Detailed Guidance

### Subtask T013 – Implement status_event_sort_key()

**Purpose**: Provide a deterministic sort key for status events that produces a total ordering. Used by the reducer and available to consumers for manual sorting.

**Steps**:

1. Add section marker in `status.py`:
   ```python
   # === Section 5: Ordering ===
   ```

2. Implement the function:
   ```python
   def status_event_sort_key(event: Event) -> Tuple[int, str, str]:
       """Deterministic sort key for status events.

       Returns (lamport_clock, timestamp_isoformat, event_id).
       Primary sort: lamport_clock (ascending).
       Secondary: timestamp ISO string (lexicographic, ascending).
       Tertiary: event_id (ULID string, lexicographic — provides unique tiebreak).
       """
       return (event.lamport_clock, event.timestamp.isoformat(), event.event_id)
   ```

3. Import `Event` from `spec_kitty_events.models` at the top of the file.

**Files**: `src/spec_kitty_events/status.py` (append to Section 5)
**Parallel?**: Independent of T014, T015.
**Notes**: The timestamp isoformat string is lexicographically sortable for ISO 8601 dates. ULIDs are also lexicographically sortable and embed a timestamp, providing a natural final tiebreaker.

### Subtask T014 – Implement dedup_events()

**Purpose**: Remove duplicate events by `event_id`, preserving the first occurrence. Essential for merging event logs after git merge.

**Steps**:

1. Implement:
   ```python
   def dedup_events(events: Sequence[Event]) -> List[Event]:
       """Remove duplicate events by event_id, preserving first occurrence."""
       seen: Set[str] = set()
       result: List[Event] = []
       for event in events:
           if event.event_id not in seen:
               seen.add(event.event_id)
               result.append(event)
       return result
   ```

2. Type imports: `from typing import Sequence, Set, List`

**Files**: `src/spec_kitty_events/status.py` (append to Section 5)
**Parallel?**: Independent of T013, T015.
**Notes**: Simple and correct. The caller should pre-sort for canonical results, but the function works on any input order.

### Subtask T015 – Implement WPState, TransitionAnomaly, ReducedStatus models

**Purpose**: Define the output types for the reference reducer.

**Steps**:

1. Add section marker:
   ```python
   # === Section 6: Reducer ===
   ```

2. Implement `WPState(BaseModel)`:
   ```python
   class WPState(BaseModel):
       """Per-work-package current state from reducer."""
       model_config = ConfigDict(frozen=True)

       wp_id: str = Field(..., min_length=1)
       current_lane: Lane
       last_event_id: str = Field(..., min_length=1)
       last_transition_at: datetime
       evidence: Optional[DoneEvidence] = None
   ```

3. Implement `TransitionAnomaly(BaseModel)`:
   ```python
   class TransitionAnomaly(BaseModel):
       """Records an invalid transition encountered during reduction."""
       model_config = ConfigDict(frozen=True)

       event_id: str = Field(..., min_length=1)
       wp_id: str = Field(..., min_length=1)
       from_lane: Optional[Lane] = None
       to_lane: Lane
       reason: str = Field(..., min_length=1)
   ```

4. Implement `ReducedStatus(BaseModel)`:
   ```python
   class ReducedStatus(BaseModel):
       """Output of the reference reducer."""
       model_config = ConfigDict(frozen=True)

       wp_states: Dict[str, WPState] = Field(default_factory=dict)
       anomalies: List[TransitionAnomaly] = Field(default_factory=list)
       event_count: int = Field(default=0, ge=0)
       last_processed_event_id: Optional[str] = None
   ```

**Files**: `src/spec_kitty_events/status.py` (append to Section 6)
**Parallel?**: Independent of T013, T014.

### Subtask T016 – Implement reduce_status_events()

**Purpose**: The reference reducer — the most important function in this feature. Takes a sequence of Events and produces deterministic per-WP state.

**Steps**:

1. Implement the full pipeline:
   ```python
   def reduce_status_events(events: Sequence[Event]) -> ReducedStatus:
       """Reduce status events to per-WP current lane state.

       Pipeline: filter -> sort -> dedup -> rollback-aware reduce.
       Pure function, no I/O. Deterministic for any permutation.
       """
   ```

2. **Step 1 — Filter**: Keep only events with `event_type == WP_STATUS_CHANGED`:
   ```python
   status_events = [e for e in events if e.event_type == WP_STATUS_CHANGED]
   ```

3. **Step 2 — Sort**: Using `status_event_sort_key`:
   ```python
   sorted_events = sorted(status_events, key=status_event_sort_key)
   ```

4. **Step 3 — Dedup**:
   ```python
   unique_events = dedup_events(sorted_events)
   ```

5. **Step 4 — Group by (wp_id, lamport_clock)** for rollback-aware precedence:
   ```python
   from itertools import groupby

   # Parse payloads
   parsed: List[Tuple[Event, StatusTransitionPayload]] = []
   for event in unique_events:
       try:
           payload = StatusTransitionPayload.model_validate(event.payload)
           parsed.append((event, payload))
       except Exception:
           # Skip events with unparseable payloads (not status events)
           continue
   ```

6. **Step 5 — Sequential reduce per WP** with rollback-aware precedence:
   ```python
   wp_states: Dict[str, WPState] = {}
   anomalies: List[TransitionAnomaly] = []

   # Group parsed events by (wp_id, lamport_clock) for concurrent detection
   # Process in sorted order, but within each (wp_id, clock) group,
   # apply rollback-aware precedence

   for event, payload in parsed:
       wp_id = payload.wp_id
       current_state = wp_states.get(wp_id)
       current_lane = current_state.current_lane if current_state else None

       # Check for rollback-aware precedence:
       # Look ahead for concurrent events (same wp_id, same lamport_clock)
       # If any is a reviewer rollback, it wins
       # (Implementation: process sequentially, but if a rollback is detected
       #  in the same clock tier, override the last forward move)

       # Validate transition
       result = validate_transition(payload)
       if not result.valid:
           # Check if current_lane matches payload.from_lane
           if current_lane != payload.from_lane:
               anomalies.append(TransitionAnomaly(
                   event_id=event.event_id,
                   wp_id=wp_id,
                   from_lane=payload.from_lane,
                   to_lane=payload.to_lane,
                   reason=f"Expected from_lane={current_lane}, got {payload.from_lane}; "
                          f"violations: {'; '.join(result.violations)}",
               ))
               continue
           anomalies.append(TransitionAnomaly(
               event_id=event.event_id,
               wp_id=wp_id,
               from_lane=payload.from_lane,
               to_lane=payload.to_lane,
               reason='; '.join(result.violations),
           ))
           continue

       # Check from_lane consistency with current state
       if current_lane != payload.from_lane:
           anomalies.append(TransitionAnomaly(
               event_id=event.event_id,
               wp_id=wp_id,
               from_lane=payload.from_lane,
               to_lane=payload.to_lane,
               reason=f"from_lane mismatch: WP is in {current_lane}, event says {payload.from_lane}",
           ))
           continue

       # Apply transition
       wp_states[wp_id] = WPState(
           wp_id=wp_id,
           current_lane=payload.to_lane,
           last_event_id=event.event_id,
           last_transition_at=event.timestamp,
           evidence=payload.evidence if payload.to_lane == Lane.DONE else None,
       )
   ```

7. **Step 6 — Rollback-aware precedence** (the subtle part):

   The above sequential approach works for most cases. For rollback-aware precedence specifically:

   After the sequential reduce, check for concurrent events (same `wp_id` and same `lamport_clock`) where one is a reviewer rollback (`from_lane=FOR_REVIEW, to_lane=IN_PROGRESS, review_ref is not None`). If found, the rollback should be the final state, overriding any concurrent forward move.

   **Implementation approach**: Group parsed events by `(wp_id, lamport_clock)`. Within groups of size > 1, if any event is a reviewer rollback, apply it last. This can be done as a pre-processing sort within each concurrent group:
   ```python
   def _rollback_aware_order(group: List[Tuple[Event, StatusTransitionPayload]]) -> List[Tuple[Event, StatusTransitionPayload]]:
       """Within a concurrent group, ensure reviewer rollbacks are applied last."""
       rollbacks = [(e, p) for e, p in group
                    if p.from_lane == Lane.FOR_REVIEW
                    and p.to_lane == Lane.IN_PROGRESS
                    and p.review_ref is not None]
       non_rollbacks = [(e, p) for e, p in group if (e, p) not in rollbacks]
       return non_rollbacks + rollbacks
   ```

   Apply this reordering within each `(wp_id, lamport_clock)` group before the sequential reduce.

8. **Step 7 — Return result**:
   ```python
   return ReducedStatus(
       wp_states=wp_states,
       anomalies=anomalies,
       event_count=len(unique_events),
       last_processed_event_id=unique_events[-1].event_id if unique_events else None,
   )
   ```

**Files**: `src/spec_kitty_events/status.py` (append to Section 6)
**Parallel?**: Depends on T013, T014, T015. This is the integration point.
**Notes**: The pseudocode above is guidance — the implementer should refine for clarity and correctness. The key invariant is: any permutation of the same event set produces the same ReducedStatus.

### Subtask T017 – Write unit tests for sort key, dedup, and reducer

**Purpose**: Cover the happy path and edge cases for all ordering/reduction functions.

**Steps**:

1. Add test classes in `tests/unit/test_status.py`:

2. **TestStatusEventSortKey**:
   - `test_sort_by_lamport_clock`: Events with clocks 1,3,2 → sorted 1,2,3
   - `test_tiebreak_by_timestamp`: Same clock, different timestamps → timestamp order
   - `test_tiebreak_by_event_id`: Same clock and timestamp → event_id lexicographic order

3. **TestDedupEvents**:
   - `test_removes_duplicates`: Two events with same event_id → one remains
   - `test_preserves_first_occurrence`: First occurrence by input order is kept
   - `test_no_duplicates_passthrough`: All unique → no change
   - `test_empty_input`: Empty list → empty list

4. **TestReduceStatusEvents**:
   - `test_happy_path_full_lifecycle`: Events moving WP01 through planned→claimed→in_progress→for_review→done. Verify final state is done with evidence.
   - `test_multiple_wps`: Events for WP01 and WP02 in interleaved order. Verify both WPs have correct final state.
   - `test_empty_events`: Empty list → ReducedStatus with empty wp_states, no anomalies
   - `test_non_status_events_skipped`: Events with event_type != "WPStatusChanged" are ignored
   - `test_invalid_transition_flagged`: Event that jumps planned→done without force → anomaly recorded, not raised
   - `test_from_lane_mismatch_flagged`: Event claims from_lane=claimed when WP is in planned → anomaly
   - `test_rollback_precedence`: Two concurrent events (same lamport_clock) for same WP: one moves to done, other is reviewer rollback (for_review→in_progress with review_ref). Verify final state is in_progress (rollback wins).
   - `test_event_count_correct`: Verify event_count matches number of unique status events processed
   - `test_last_processed_event_id`: Verify it's the event_id of the last event in sorted order

5. Use helper functions to create test events:
   ```python
   def _make_event(
       event_id: str,
       wp_id: str,
       from_lane: Optional[Lane],
       to_lane: Lane,
       lamport_clock: int,
       timestamp: Optional[datetime] = None,
       **kwargs: Any,
   ) -> Event:
       payload = StatusTransitionPayload(
           feature_slug="test-feature",
           wp_id=wp_id,
           from_lane=from_lane,
           to_lane=to_lane,
           actor="test-actor",
           execution_mode=ExecutionMode.WORKTREE,
           **kwargs,
       )
       return Event(
           event_id=event_id,
           event_type=WP_STATUS_CHANGED,
           aggregate_id=f"test-feature/{wp_id}",
           payload=payload.model_dump(),
           timestamp=timestamp or datetime.now(timezone.utc),
           node_id="test-node",
           lamport_clock=lamport_clock,
           project_uuid=uuid.uuid4(),
       )
   ```

**Files**: `tests/unit/test_status.py` (append)
**Parallel?**: Can start once T013-T016 are done.

### Subtask T018 – Write property tests for determinism and idempotency

**Purpose**: Use Hypothesis to prove that the reducer is deterministic (any permutation → same result) and that dedup is idempotent.

**Steps**:

1. Create `tests/property/test_status_determinism.py`:

2. **test_reduce_deterministic_under_permutation**:
   ```python
   from hypothesis import given, settings
   from hypothesis import strategies as st

   @given(st.data())
   @settings(max_examples=50)
   def test_reduce_deterministic_under_permutation(data):
       """Any permutation of the same event set produces identical ReducedStatus."""
       # Generate a small set of valid status events (3-8 events)
       # Create two different permutations
       # Reduce both
       # Assert wp_states and anomalies are identical
   ```

   Strategy:
   - Generate 3-8 events forming a valid lifecycle for 1-2 WPs
   - Shuffle them randomly
   - Reduce both original and shuffled
   - Compare: `result1.wp_states == result2.wp_states` and `sorted(result1.anomalies) == sorted(result2.anomalies)`

3. **test_dedup_idempotent**:
   ```python
   @given(st.data())
   def test_dedup_idempotent(data):
       """dedup_events(dedup_events(events)) == dedup_events(events)"""
       # Generate events with some duplicates
       # Apply dedup twice
       # Assert same result
   ```

4. **test_sort_key_total_order**:
   ```python
   @given(st.data())
   def test_sort_key_total_order(data):
       """Sorting by status_event_sort_key produces a total order (no ties)."""
       # Generate events with distinct event_ids
       # Sort them
       # Assert no two adjacent events have identical sort keys
   ```

5. Update `__init__.py` to export remaining 6 symbols:
   - Add to imports: `status_event_sort_key`, `dedup_events`, `reduce_status_events`, `WPState`, `TransitionAnomaly`, `ReducedStatus`
   - Add to `__all__`

6. Run mypy --strict and full test suite.

**Files**: `tests/property/test_status_determinism.py` (new), `src/spec_kitty_events/__init__.py` (edit)
**Parallel?**: Depends on T016 (needs reduce_status_events to exist).
**Notes**: Use existing `tests/property/test_determinism.py` and `tests/property/test_gates_determinism.py` as pattern references.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Rollback-aware precedence logic is subtle and easy to get wrong | Dedicated unit test (test_rollback_precedence) + property test with random concurrent events |
| Payload deserialization from Event.payload may fail on edge cases | Wrap in try/except, skip unparseable events, log warning |
| from_lane mismatch detection too strict (rejects valid concurrent events) | Anomaly is recorded but reducer continues — doesn't halt |
| Property test Hypothesis strategies are hard to write for valid event sequences | Start with simple strategies (linear lifecycle), add concurrent events as separate test |
| `itertools.groupby` requires pre-sorted input | Events are already sorted by sort key before grouping |

## Review Guidance

- Verify `status_event_sort_key` returns `(lamport_clock, timestamp_iso, event_id)` — not `(lamport_clock, node_id)` like existing `total_order_key`
- Verify reducer handles empty input correctly (returns empty ReducedStatus)
- Verify rollback-aware precedence: concurrent forward + rollback → rollback wins
- Verify anomalies are recorded, not raised — reducer never halts
- Verify property tests prove determinism under permutation
- Verify `__init__.py` now has all 21 exports total (13 from WP01 + 2 from WP02 + 6 from WP03)
- Verify all existing tests still pass

## Activity Log

- 2026-02-08T00:00:00Z – system – lane=planned – Prompt created.
- 2026-02-08T14:25:05Z – claude-opus – shell_pid=41460 – lane=doing – Assigned agent via workflow command
