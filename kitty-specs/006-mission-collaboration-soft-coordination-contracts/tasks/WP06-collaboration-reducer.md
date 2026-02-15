---
work_package_id: WP06
title: Collaboration Reducer
lane: planned
dependencies:
- WP01
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
- T037
phase: Phase 2 - Reducer
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-15T10:35:14Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – Collaboration Reducer

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Implement `reduce_collaboration_events()` — the core pure function in Section 5 of `collaboration.py` that processes collaboration events into `ReducedCollaborationState`.

**Success criteria**:
- Reducer processes all 14 collaboration event types
- Strict mode (default): raises `UnknownParticipantError` for non-rostered participants
- Permissive mode: records `CollaborationAnomaly` for integrity violations
- Seeded roster support: `roster` parameter pre-loads known participants
- Deterministic output for any causal-order-preserving permutation of inputs
- Reuses `status_event_sort_key()` and `dedup_events()` from `status.py`
- All edge cases from spec handled (duplicate join, duplicate leave, departed participant actions, etc.)
- Comprehensive unit tests covering all modes and event types
- `mypy --strict` passes

## Context & Constraints

**Reference documents**:
- Reducer contract: `kitty-specs/006-.../contracts/collaboration-api.md` (Reducer section, Strict Mode Enforcement Points)
- Data model: `kitty-specs/006-.../data-model.md` (State Transitions section)
- Research: `kitty-specs/006-.../research.md` (R2: Reducer Mode, R3: Sort/Dedup Reuse, R4: Participant Roster, R11: Seeded Roster)

**Prerequisites**: WP01-WP05 must all be merged (all models available)

**Implementation command**: `spec-kitty implement WP06 --base WP05`
(WP05 has WP01 as dependency, and WP02-WP04 are parallel with WP05 — all must be merged to main first)

**Architecture reference**:
- `reduce_lifecycle_events()` in `lifecycle.py` lines 345-454: pipeline pattern (sort → dedup → partition → reduce → assemble)
- `status_event_sort_key()` in `status.py` line 327: `(lamport_clock, timestamp.isoformat(), event_id)`
- `dedup_events()` in `status.py` line 335: remove duplicates by event_id, preserving first occurrence
- Both are pure functions imported from `status.py`

**Strict mode enforcement points** (from contract):
1. Any event with `participant_id`: participant must be in roster
2. Any event with `participant_ids`: all participant_ids must be in roster
3. `WarningAcknowledged`: referenced `warning_id` must exist in warning timeline
4. `PromptStepExecutionCompleted`: matching started event must exist
5. `PresenceHeartbeat` / `FocusChanged` / `DriveIntentSet`: participant must not have departed

## Subtasks & Detailed Guidance

### Subtask T031 – Implement reducer pipeline skeleton

- **Purpose**: Create the top-level function with filter → sort → dedup → process loop.
- **Steps**:
  1. Add to Section 5 of `collaboration.py`:
     ```python
     def reduce_collaboration_events(
         events: Sequence[Event],
         *,
         mode: Literal["strict", "permissive"] = "strict",
         roster: Optional[Dict[str, ParticipantIdentity]] = None,
     ) -> ReducedCollaborationState:
         """Reduce collaboration events into materialized state.

         Pipeline: filter → sort → dedup → process → assemble
         """
         from spec_kitty_events.status import status_event_sort_key, dedup_events
         from spec_kitty_events.models import Event as EventModel

         # Filter to collaboration events only
         collab_events = [e for e in events if e.event_type in COLLABORATION_EVENT_TYPES]

         if not collab_events:
             return ReducedCollaborationState(
                 mission_id="",
                 event_count=0,
                 last_processed_event_id=None,
             )

         # Sort and dedup
         sorted_events = sorted(collab_events, key=status_event_sort_key)
         unique_events = dedup_events(sorted_events)

         # Process loop (T032-T035 fill this in)
         # ...

         # Assemble output (T036)
         # ...
     ```
  2. Import `Event` from `spec_kitty_events.models` — use late import inside function to avoid circular deps (matches lifecycle.py pattern)
  3. The empty-input case returns a minimal `ReducedCollaborationState` with empty collections
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: No — foundation for T032-T036
- **Notes**: The `Sequence[Event]` input may contain non-collaboration events; the filter step handles this.

### Subtask T032 – Implement roster management

- **Purpose**: Track participant join/leave lifecycle, handle seeded roster.
- **Steps**:
  1. Initialize mutable state at start of process loop:
     ```python
     # Mutable state during reduction
     participants: Dict[str, ParticipantIdentity] = dict(roster) if roster else {}
     departed: Dict[str, ParticipantIdentity] = {}
     mission_id: str = ""
     anomalies: List[CollaborationAnomaly] = []
     ```
  2. Extract `mission_id` from first event's payload (all collaboration payloads have `mission_id`)
  3. Handle `PARTICIPANT_JOINED`:
     - Parse `ParticipantJoinedPayload(**event.payload)`
     - If participant already in `participants`: record anomaly (duplicate join) in both modes
     - If participant in `departed`: re-join (move from departed back to participants)
     - Otherwise: add to `participants`
  4. Handle `PARTICIPANT_LEFT`:
     - Parse `ParticipantLeftPayload(**event.payload)`
     - If participant not in `participants` and not in `departed`: membership check (mode-dependent)
     - If participant already in `departed`: record anomaly in both modes (duplicate leave — protocol error)
     - Otherwise: move from `participants` to `departed`
  5. Handle `PARTICIPANT_INVITED`:
     - Parse `ParticipantInvitedPayload(**event.payload)`
     - Validate `invited_by` is in roster (mode-dependent)
     - Invitations don't modify roster (only join does)
  6. Create membership check helper:
     ```python
     def _check_participant(
         participant_id: str,
         participants: Dict[str, ParticipantIdentity],
         departed: Dict[str, ParticipantIdentity],
         event: Event,
         mode: Literal["strict", "permissive"],
         anomalies: List[CollaborationAnomaly],
         *,
         check_departed: bool = False,
     ) -> bool:
         """Check participant membership. Returns True if valid."""
     ```
     - In strict mode: raise `UnknownParticipantError` if not in roster
     - In permissive mode: append `CollaborationAnomaly` and return False
     - If `check_departed=True`: also fail for departed participants
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: No — sequential with T031

### Subtask T033 – Implement strict/permissive mode branching

- **Purpose**: Centralize the mode-dependent logic for roster validation.
- **Steps**:
  1. The `_check_participant()` helper from T032 handles the mode branching
  2. Additionally, implement multi-actor check for warning payloads:
     ```python
     def _check_participants(
         participant_ids: List[str],
         participants: Dict[str, ParticipantIdentity],
         event: Event,
         mode: Literal["strict", "permissive"],
         anomalies: List[CollaborationAnomaly],
     ) -> bool:
         """Check all participant_ids in roster. Returns True if all valid."""
     ```
  3. Implement warning reference check (strict mode enforcement point 3):
     - `WarningAcknowledged` must reference an existing `warning_id`
     - Strict: raise error. Permissive: anomaly.
  4. Implement execution pairing check (strict mode enforcement point 4):
     - `PromptStepExecutionCompleted` must have a matching `Started` in `active_executions`
     - Strict: raise error. Permissive: anomaly.
  5. Implement departed check (strict mode enforcement point 5):
     - `PresenceHeartbeat`, `FocusChanged`, `DriveIntentSet` from departed participants
     - Strict: raise error. Permissive: anomaly.
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: No — extends T032

### Subtask T034 – Implement event handlers: intent, focus, presence, sessions

- **Purpose**: Process DriveIntentSet, FocusChanged, PresenceHeartbeat, SessionLinked events.
- **Steps**:
  1. Initialize additional mutable state:
     ```python
     active_drivers: Set[str] = set()
     focus_by_participant: Dict[str, FocusTarget] = {}
     presence: Dict[str, datetime] = {}
     linked_sessions: Dict[str, List[str]] = {}
     ```
  2. Handle `DRIVE_INTENT_SET`:
     - Check membership + not departed
     - Parse `DriveIntentSetPayload(**event.payload)`
     - If `intent == "active"`: add to `active_drivers`
     - If `intent == "inactive"`: discard from `active_drivers` (idempotent)
  3. Handle `FOCUS_CHANGED`:
     - Check membership + not departed
     - Parse `FocusChangedPayload(**event.payload)`
     - Update `focus_by_participant[participant_id] = payload.focus_target`
  4. Handle `PRESENCE_HEARTBEAT`:
     - Check membership + not departed
     - Parse `PresenceHeartbeatPayload(**event.payload)`
     - Update `presence[participant_id] = event.timestamp`
  5. Handle `SESSION_LINKED`:
     - Check membership
     - Parse `SessionLinkedPayload(**event.payload)`
     - Append `payload.linked_session_id` to `linked_sessions[participant_id]`
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: No — sequential with T032-T033

### Subtask T035 – Implement event handlers: warnings, acks, executions, comments, decisions

- **Purpose**: Process warning, acknowledgement, execution, comment, and decision events.
- **Steps**:
  1. Initialize additional mutable state:
     ```python
     warnings_list: List[WarningEntry] = []
     warnings_by_id: Dict[str, int] = {}  # warning_id -> index in warnings_list
     decisions_list: List[DecisionEntry] = []
     comments_list: List[CommentEntry] = []
     active_executions: Dict[str, List[str]] = {}  # participant_id -> list of step_ids
     ```
  2. Handle `CONCURRENT_DRIVER_WARNING`:
     - Check all participant_ids in roster
     - Parse `ConcurrentDriverWarningPayload(**event.payload)`
     - Create `WarningEntry` and append to `warnings_list`
     - Index by `warning_id` in `warnings_by_id`
  3. Handle `POTENTIAL_STEP_COLLISION_DETECTED`:
     - Same pattern as concurrent driver warning
  4. Handle `WARNING_ACKNOWLEDGED`:
     - Check membership
     - Parse `WarningAcknowledgedPayload(**event.payload)`
     - Check `warning_id` exists in `warnings_by_id` (mode-dependent)
     - Update `WarningEntry.acknowledgements[participant_id] = acknowledgement`
     - **Note**: Since WarningEntry is frozen, you'll need to reconstruct it or use a mutable intermediate. Prefer mutable dict during processing, convert to frozen WarningEntry at assembly time (T036).
  5. Handle `PROMPT_STEP_EXECUTION_STARTED`:
     - Check membership
     - Parse `PromptStepExecutionStartedPayload(**event.payload)`
     - Append `step_id` to `active_executions[participant_id]`
  6. Handle `PROMPT_STEP_EXECUTION_COMPLETED`:
     - Check membership
     - Parse `PromptStepExecutionCompletedPayload(**event.payload)`
     - Check matching started exists in `active_executions[participant_id]` (mode-dependent)
     - Remove `step_id` from `active_executions[participant_id]`
  7. Handle `COMMENT_POSTED`:
     - Check membership
     - Parse `CommentPostedPayload(**event.payload)`
     - Append `CommentEntry` to `comments_list`
  8. Handle `DECISION_CAPTURED`:
     - Check membership
     - Parse `DecisionCapturedPayload(**event.payload)`
     - Append `DecisionEntry` to `decisions_list`
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: No — sequential with T034
- **Notes**: For WarningEntry acknowledgements, use a mutable dict during processing. At assembly time (T036), create frozen WarningEntry objects from the accumulated data.

### Subtask T036 – Implement state assembly

- **Purpose**: Build the final `ReducedCollaborationState` from accumulated mutable state.
- **Steps**:
  1. After the process loop, build the reverse focus index:
     ```python
     # Build participants_by_focus reverse index
     participants_by_focus: Dict[FocusTarget, FrozenSet[str]] = {}
     for pid, target in focus_by_participant.items():
         if target in participants_by_focus:
             participants_by_focus[target] = participants_by_focus[target] | frozenset({pid})
         else:
             participants_by_focus[target] = frozenset({pid})
     ```
  2. Convert mutable warnings to frozen WarningEntry objects (if using mutable intermediates)
  3. Return:
     ```python
     return ReducedCollaborationState(
         mission_id=mission_id,
         participants=participants,
         departed_participants=departed,
         presence=presence,
         active_drivers=frozenset(active_drivers),
         focus_by_participant=focus_by_participant,
         participants_by_focus=participants_by_focus,
         warnings=tuple(warnings_list),
         decisions=tuple(decisions_list),
         comments=tuple(comments_list),
         active_executions=active_executions,
         linked_sessions=linked_sessions,
         anomalies=tuple(anomalies),
         event_count=len(unique_events),
         last_processed_event_id=unique_events[-1].event_id,
     )
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: No — final step of reducer

### Subtask T037 – Write comprehensive reducer unit tests

- **Purpose**: Verify the reducer handles all modes, event types, and edge cases.
- **Steps**:
  1. Create `tests/unit/test_collaboration_reducer.py` with these test categories:

  **a) Strict mode with full history**:
  - 3 participants join → drive intent → focus → warning → ack → state is correct
  - Event from unknown participant raises `UnknownParticipantError`
  - All participant_ids in warning must be in roster

  **b) Strict mode with seeded roster**:
  - Seed 2 participants, send events without join events → works
  - Seed empty roster, send non-join event → raises `UnknownParticipantError`

  **c) Permissive mode**:
  - Event from unknown participant → anomaly recorded, not raised
  - Duplicate join → anomaly recorded
  - Duplicate leave → anomaly recorded (in both modes)

  **d) All 14 event types**:
  - One test per event type verifying correct state mutation
  - `ParticipantJoined` → adds to roster
  - `ParticipantLeft` → moves to departed
  - `DriveIntentSet(active)` → adds to active_drivers
  - `DriveIntentSet(inactive)` → removes from active_drivers
  - `FocusChanged` → updates focus_by_participant and participants_by_focus
  - `PresenceHeartbeat` → updates presence timestamp
  - `ConcurrentDriverWarning` → adds to warnings
  - `WarningAcknowledged` → updates warning acknowledgements
  - `PromptStepExecutionStarted` → adds to active_executions
  - `PromptStepExecutionCompleted` → removes from active_executions
  - `CommentPosted` → adds to comments
  - `DecisionCaptured` → adds to decisions
  - `SessionLinked` → adds to linked_sessions

  **e) Edge cases**:
  - Empty event list → minimal state
  - Non-collaboration events filtered out
  - Duplicate events deduped
  - Departed participant actions (heartbeat, focus, intent) → mode-dependent
  - Warning ack for non-existent warning → mode-dependent
  - Execution complete without matching start → mode-dependent

  **f) Determinism**:
  - Same events in different orders produce same output (basic — property test in WP08 does exhaustive)

  2. Helper function to create test events:
     ```python
     def _make_event(event_type: str, payload: dict, clock: int = 0, ...) -> Event:
         """Create a test Event with sensible defaults."""
     ```

  3. Run: `python3.11 -m pytest tests/unit/test_collaboration_reducer.py -v`
- **Files**: `tests/unit/test_collaboration_reducer.py` (new)
- **Parallel?**: No — depends on T031-T036

## Test Strategy

- **Unit tests**: `tests/unit/test_collaboration_reducer.py`
- **Run command**: `python3.11 -m pytest tests/unit/test_collaboration_reducer.py -v`
- **mypy check**: `mypy --strict src/spec_kitty_events/collaboration.py`
- **Coverage target**: All reducer branches covered (strict mode raise, permissive mode anomaly, each event type handler)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Reducer complexity (~200 LOC) | Hard to review | Clear handler dispatch, helper functions for membership checks |
| WarningEntry immutability during processing | Can't update acknowledgements on frozen model | Use mutable dict during processing, convert at assembly |
| Circular import with status.py | Import error at module level | Late import inside function (matches lifecycle.py pattern) |
| mode parameter type checking with mypy | Literal type narrowing | Use `if mode == "strict":` branches — mypy narrows correctly |

## Review Guidance

- Verify all 5 strict mode enforcement points from the contract are implemented
- Verify seeded roster is pre-loaded before event processing begins
- Verify empty input returns minimal state (not error)
- Verify non-collaboration events are filtered out (not error)
- Verify `status_event_sort_key` and `dedup_events` are imported from `status.py` (not duplicated)
- Verify the reverse focus index (`participants_by_focus`) is correctly built
- Verify departed participant re-join scenario is handled
- Count total reducer LOC — should be under 300 (200 target + helpers)

## Completion

```bash
git add -A && git commit -m "feat(WP06): collaboration reducer with strict/permissive modes"
spec-kitty agent tasks move-task WP06 --to for_review --note "Ready for review: reducer with all 14 event handlers, strict/permissive modes, seeded roster"
```

## Activity Log

- 2026-02-15T10:35:14Z – system – lane=planned – Prompt created.
