---
work_package_id: WP05
title: Reducer Output Models
lane: "done"
dependencies: [WP01]
base_branch: 006-mission-collaboration-soft-coordination-contracts-WP01
base_commit: f058d167abbbbbd8460757676b7e12ee4fb0ed3b
created_at: '2026-02-15T11:08:14.255816+00:00'
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
phase: Phase 1 - Payload Models
assignee: ''
agent: "claude-coordinator"
shell_pid: "80547"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-15T10:35:14Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Reducer Output Models

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add the reducer output models to `collaboration.py` Section 4:
1. `CollaborationAnomaly` — non-fatal issue record
2. `WarningEntry` — warning timeline entry
3. `DecisionEntry` — decision history entry
4. `CommentEntry` — comment history entry
5. `ReducedCollaborationState` — the main reducer output (full state snapshot)

**Success criteria**:
- All models frozen Pydantic v2
- `ReducedCollaborationState` has all required fields from `data-model.md` (including `last_processed_event_id`)
- `ReducedCollaborationState.participants_by_focus` uses a deterministic string key (`"{target_type}:{target_id}"`)
- All tuple fields use `Tuple[X, ...]` for immutability
- `mypy --strict` passes

## Context & Constraints

**Reference documents**:
- Data model: `kitty-specs/006-.../data-model.md` (Reducer Output Models section)
- Existing pattern: `ReducedMissionState` in `lifecycle.py` (lines 190-240)

**Prerequisites**: WP01 must be merged (provides `ParticipantIdentity`, `FocusTarget`)

**Implementation command**: `spec-kitty implement WP05 --base WP01`

**Pattern**: Follow `ReducedMissionState` from `lifecycle.py` — frozen BaseModel with tuple for ordered collections, dict for indexed lookups, frozenset for sets.

## Subtasks & Detailed Guidance

### Subtask T025 – Implement CollaborationAnomaly model

- **Purpose**: Records non-fatal issues encountered during collaboration event reduction.
- **Steps**:
  1. Add to Section 4 of `collaboration.py`:
     ```python
     class CollaborationAnomaly(BaseModel):
         """Non-fatal issue encountered during collaboration event reduction."""
         model_config = ConfigDict(frozen=True)
         event_id: str = Field(..., description="Event that caused the anomaly")
         event_type: str = Field(..., description="Type of the problematic event")
         reason: str = Field(..., description="Human-readable anomaly description")
     ```
  2. Follows `LifecycleAnomaly` pattern from `lifecycle.py`
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: No — needed by T029

### Subtask T026 – Implement WarningEntry model

- **Purpose**: Represents a warning in the reduced state timeline with acknowledgement tracking.
- **Steps**:
  1. Add to Section 4:
     ```python
     class WarningEntry(BaseModel):
         """Warning timeline entry in reduced collaboration state."""
         model_config = ConfigDict(frozen=True)
         warning_id: str = Field(..., description="Warning identifier")
         event_id: str = Field(..., description="Event that created this warning")
         warning_type: str = Field(..., description="'ConcurrentDriverWarning' or 'PotentialStepCollisionDetected'")
         participant_ids: Tuple[str, ...] = Field(..., description="Affected participants")
         acknowledgements: Dict[str, str] = Field(default_factory=dict, description="participant_id -> acknowledgement action")
     ```
  2. Note: `acknowledgements` is mutable-looking but the frozen model prevents reassignment. The dict values are strings from `Literal["continue", "hold", "reassign", "defer"]`.
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T027, T028)
- **Notes**: `participant_ids` is `Tuple[str, ...]` (immutable) not `List[str]` since this is in the output model

### Subtask T027 – Implement DecisionEntry model

- **Purpose**: Represents a captured decision in the reduced state history.
- **Steps**:
  1. Add to Section 4:
     ```python
     class DecisionEntry(BaseModel):
         """Decision history entry in reduced collaboration state."""
         model_config = ConfigDict(frozen=True)
         decision_id: str = Field(..., description="Decision identifier")
         event_id: str = Field(..., description="Event that captured this decision")
         participant_id: str = Field(..., description="Decision author")
         topic: str = Field(..., description="Decision topic")
         chosen_option: str = Field(..., description="Selected option")
         referenced_warning_id: Optional[str] = Field(None, description="Related warning")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T026, T028)

### Subtask T028 – Implement CommentEntry model

- **Purpose**: Represents a posted comment in the reduced state history.
- **Steps**:
  1. Add to Section 4:
     ```python
     class CommentEntry(BaseModel):
         """Comment history entry in reduced collaboration state."""
         model_config = ConfigDict(frozen=True)
         comment_id: str = Field(..., description="Comment identifier")
         event_id: str = Field(..., description="Event that posted this comment")
         participant_id: str = Field(..., description="Comment author")
         content: str = Field(..., description="Comment text")
         reply_to: Optional[str] = Field(None, description="Parent comment_id")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T026, T027)

### Subtask T029 – Implement ReducedCollaborationState model

- **Purpose**: The main output of the collaboration reducer. Frozen model containing the full mission collaboration snapshot.
- **Steps**:
  1. Add to Section 4:
     ```python
     class ReducedCollaborationState(BaseModel):
         """Materialized collaboration state from event reduction."""
         model_config = ConfigDict(frozen=True)

         mission_id: str = Field(..., description="Mission this state represents")
         participants: Dict[str, ParticipantIdentity] = Field(
             default_factory=dict, description="Active participant roster (participant_id -> identity)")
         departed_participants: Dict[str, ParticipantIdentity] = Field(
             default_factory=dict, description="Historical departed participants")
         presence: Dict[str, datetime] = Field(
             default_factory=dict, description="Last heartbeat timestamp per participant_id")
         active_drivers: FrozenSet[str] = Field(
             default_factory=frozenset, description="participant_ids with active drive intent")
         focus_by_participant: Dict[str, FocusTarget] = Field(
             default_factory=dict, description="Current focus per participant")
         participants_by_focus: Dict[str, FrozenSet[str]] = Field(
             default_factory=dict, description="Reverse index: focus_key -> participant set (focus_key = '{target_type}:{target_id}')")
         warnings: Tuple[WarningEntry, ...] = Field(
             default_factory=tuple, description="Ordered warning timeline")
         decisions: Tuple[DecisionEntry, ...] = Field(
             default_factory=tuple, description="Ordered decision history")
         comments: Tuple[CommentEntry, ...] = Field(
             default_factory=tuple, description="Ordered comment history")
         active_executions: Dict[str, List[str]] = Field(
             default_factory=dict, description="In-flight step_ids per participant_id")
         linked_sessions: Dict[str, List[str]] = Field(
             default_factory=dict, description="Linked session_ids per participant_id")
         anomalies: Tuple[CollaborationAnomaly, ...] = Field(
             default_factory=tuple, description="Non-fatal issues encountered")
         event_count: int = Field(default=0, description="Total events processed")
         last_processed_event_id: Optional[str] = Field(
             None, description="Last event_id in processed sequence")
     ```
  2. **Critical**: `participants_by_focus` uses normalized string keys to guarantee JSON/Pydantic serialization safety
  3. Note: `active_drivers` uses `FrozenSet[str]`, `warnings`/`decisions`/`comments`/`anomalies` use `Tuple[X, ...]` for immutability
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: No — depends on T025-T028 (uses all entry models)
- **Notes**: The data-model.md says 14 fields but we actually have 15 (including `last_processed_event_id`). This matches the `ReducedMissionState` pattern.

### Subtask T030 – Write unit tests for output models

- **Purpose**: Verify all output models can be constructed, are frozen, and pass type checks.
- **Steps**:
  1. Add tests:
     - **CollaborationAnomaly**: valid construction, frozen
     - **WarningEntry**: construction with participant_ids tuple and acknowledgements dict, frozen
     - **DecisionEntry**: construction with/without referenced_warning_id, frozen
     - **CommentEntry**: construction with/without reply_to, frozen
     - **ReducedCollaborationState**: construction with representative data including:
       - Non-empty participants dict
       - String focus keys in participants_by_focus (for example `wp:WP03`)
       - Frozen assertion (attribute assignment raises)
       - Default factory values (empty collections when not provided)
  2. Run: `python3.11 -m pytest tests/unit/ -k collaboration -v`
- **Files**: `tests/unit/test_collaboration_models.py` (extend)
- **Parallel?**: No — depends on T025-T029

## Test Strategy

- **Unit tests**: Focus on frozen model construction and deterministic focus-key indexing
- **Run command**: `python3.11 -m pytest tests/unit/ -k collaboration -v`
- **mypy check**: `mypy --strict src/spec_kitty_events/collaboration.py`
- **Key validation**: `ReducedCollaborationState` can be constructed with `participants_by_focus={"wp:WP03": frozenset({"p-001"})}`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Frozen model with dict fields | Pydantic may reject dict in frozen model | `ConfigDict(frozen=True)` prevents reassignment but allows dict values — verify |
| Non-string map keys in JSON serialization | Pydantic/json serialization can fail | Store `participants_by_focus` keys as normalized strings (`"{target_type}:{target_id}"`) |
| `Tuple[WarningEntry, ...]` Pydantic support | Type annotation complexity | Pydantic v2 supports tuple of BaseModel — verify |

## Review Guidance

- Verify all 15 fields of `ReducedCollaborationState` match `data-model.md`
- Verify tuple types for ordered collections, dict for indexed, frozenset for sets
- Verify normalized focus-key test exists and passes
- Verify all models use `ConfigDict(frozen=True)`

## Completion

```bash
git add -A && git commit -m "feat(WP05): reducer output models"
spec-kitty agent tasks move-task WP05 --to for_review --note "Ready for review: 5 output models including ReducedCollaborationState with 15 fields"
```

## Activity Log

- 2026-02-15T10:35:14Z – system – lane=planned – Prompt created.
- 2026-02-15T11:08:15Z – claude-coordinator – shell_pid=80547 – lane=doing – Assigned agent via workflow command
- 2026-02-15T11:11:32Z – claude-coordinator – shell_pid=80547 – lane=for_review – Ready for review: 5 output models including ReducedCollaborationState with 15 fields
- 2026-02-15T11:11:33Z – claude-coordinator – shell_pid=80547 – lane=done – Review passed: output models validated, 30 tests, mypy clean
