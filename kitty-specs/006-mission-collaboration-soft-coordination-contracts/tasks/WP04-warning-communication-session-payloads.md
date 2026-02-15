---
work_package_id: WP04
title: Warning, Communication, and Session Payloads
lane: "doing"
dependencies: [WP01]
base_branch: 006-mission-collaboration-soft-coordination-contracts-WP01
base_commit: f058d167abbbbbd8460757676b7e12ee4fb0ed3b
created_at: '2026-02-15T11:02:25.052265+00:00'
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
- T024
phase: Phase 1 - Payload Models
assignee: ''
agent: "claude-coordinator"
shell_pid: "67115"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-15T10:35:14Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Warning, Communication, and Session Payloads

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add the remaining 6 payload models to `collaboration.py` Section 3:
1. `ConcurrentDriverWarningPayload` (multi-actor: `participant_ids`)
2. `PotentialStepCollisionDetectedPayload` (multi-actor: `participant_ids`)
3. `WarningAcknowledgedPayload` (single-actor: `participant_id`)
4. `CommentPostedPayload`
5. `DecisionCapturedPayload`
6. `SessionLinkedPayload`

**Success criteria**:
- Multi-actor warning payloads use `participant_ids: list[str]` with `min_length=2`
- Single-actor payloads use `participant_id: str` with `min_length=1`
- Literal constraints enforced on `acknowledgement`, `severity`, `link_type`
- All 6 payloads frozen and round-trip through JSON
- `mypy --strict` passes

## Context & Constraints

**Reference documents**:
- Data model: `kitty-specs/006-.../data-model.md` (Warning, Communication, Session sections)
- API contract: `kitty-specs/006-.../contracts/collaboration-api.md` (Payload Actor Field Contract)
- Spec FR-003: Multi-actor warning distinction

**Prerequisites**: WP01 must be merged (provides `FocusTarget` for `ConcurrentDriverWarningPayload`)

**Implementation command**: `spec-kitty implement WP04 --base WP01`

**Critical distinction**: Warning payloads use `participant_ids: list[str]` (plural), NOT `participant_id: str`. This is the single-actor vs multi-actor split from FR-003.

## Subtasks & Detailed Guidance

### Subtask T018 – Implement ConcurrentDriverWarningPayload

- **Purpose**: Advisory warning emitted when multiple participants have active drive intent on overlapping focus targets.
- **Steps**:
  1. Add to Section 3 of `collaboration.py`:
     ```python
     class ConcurrentDriverWarningPayload(BaseModel):
         """Typed payload for ConcurrentDriverWarning events."""
         model_config = ConfigDict(frozen=True)
         warning_id: str = Field(..., min_length=1, description="Unique warning identifier")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         participant_ids: List[str] = Field(..., min_length=2, description="All concurrent active drivers on overlapping target")
         focus_target: FocusTarget = Field(..., description="Shared focus target triggering warning")
         severity: Literal["info", "warning"] = Field(..., description="Warning severity level")
     ```
  2. Verify `participant_ids` with 1 element raises `ValidationError` (min_length=2)
  3. Verify `participant_ids` with 2+ elements passes
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T019-T023)
- **Notes**: Uses `List[str]` with `min_length=2` — Pydantic v2 Field `min_length` works on lists as minimum list length.

### Subtask T019 – Implement PotentialStepCollisionDetectedPayload

- **Purpose**: Advisory warning when multiple participants attempt the same prompt step.
- **Steps**:
  1. Add to Section 3:
     ```python
     class PotentialStepCollisionDetectedPayload(BaseModel):
         """Typed payload for PotentialStepCollisionDetected events."""
         model_config = ConfigDict(frozen=True)
         warning_id: str = Field(..., min_length=1, description="Unique warning identifier")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         participant_ids: List[str] = Field(..., min_length=2, description="Colliding participants")
         step_id: str = Field(..., min_length=1, description="Colliding step")
         wp_id: Optional[str] = Field(None, description="Work package context")
         severity: Literal["info", "warning"] = Field(..., description="Warning severity level")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T018, T020-T023)

### Subtask T020 – Implement WarningAcknowledgedPayload

- **Purpose**: Records a participant's response to an advisory warning.
- **Steps**:
  1. Add to Section 3:
     ```python
     class WarningAcknowledgedPayload(BaseModel):
         """Typed payload for WarningAcknowledged events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Acknowledging participant")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         warning_id: str = Field(..., min_length=1, description="Warning being acknowledged")
         acknowledgement: Literal["continue", "hold", "reassign", "defer"] = Field(..., description="Response action")
     ```
  2. Verify all 4 acknowledgement values accepted
  3. Verify invalid value (e.g., `"noted"`) rejected
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T018-T019, T021-T023)
- **Notes**: The acknowledgement enum was fixed during spec review — must be exactly `continue|hold|reassign|defer`

### Subtask T021 – Implement CommentPostedPayload

- **Purpose**: Free-form comment posted to a mission context by a participant.
- **Steps**:
  1. Add to Section 3:
     ```python
     class CommentPostedPayload(BaseModel):
         """Typed payload for CommentPosted events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Comment author")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         comment_id: str = Field(..., min_length=1, description="Unique comment identifier")
         content: str = Field(..., min_length=1, description="Comment text")
         reply_to: Optional[str] = Field(None, description="Parent comment_id for threading")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T018-T020, T022-T023)

### Subtask T022 – Implement DecisionCapturedPayload

- **Purpose**: Records a formal decision made in the context of a mission.
- **Steps**:
  1. Add to Section 3:
     ```python
     class DecisionCapturedPayload(BaseModel):
         """Typed payload for DecisionCaptured events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Decision author")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         decision_id: str = Field(..., min_length=1, description="Unique decision identifier")
         topic: str = Field(..., min_length=1, description="Decision topic/question")
         chosen_option: str = Field(..., min_length=1, description="Selected option")
         rationale: Optional[str] = Field(None, description="Reasoning for the decision")
         referenced_warning_id: Optional[str] = Field(None, description="Warning that prompted this decision")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T018-T021, T023)

### Subtask T023 – Implement SessionLinkedPayload

- **Purpose**: Links two sessions (e.g., CLI and SaaS) for a single participant.
- **Steps**:
  1. Add to Section 3:
     ```python
     class SessionLinkedPayload(BaseModel):
         """Typed payload for SessionLinked events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Participant linking sessions")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         primary_session_id: str = Field(..., min_length=1, description="Primary session")
         linked_session_id: str = Field(..., min_length=1, description="Session being linked")
         link_type: Literal["cli_to_saas", "saas_to_cli"] = Field(..., description="Direction of link")
     ```
  2. Verify both `link_type` values accepted, invalid rejected
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T018-T022)

### Subtask T024 – Write unit tests for warning/communication/session payloads

- **Purpose**: Comprehensive tests for all 6 payloads, especially multi-actor and Literal constraints.
- **Steps**:
  1. Add tests covering:
     - **ConcurrentDriverWarningPayload**: valid with 2+ participant_ids, rejected with 1, embedded FocusTarget round-trip, severity Literal
     - **PotentialStepCollisionDetectedPayload**: valid with 2+ participant_ids, rejected with 1, severity Literal
     - **WarningAcknowledgedPayload**: all 4 acknowledgement values, invalid value rejected
     - **CommentPostedPayload**: valid with/without reply_to, empty content rejected (min_length=1)
     - **DecisionCapturedPayload**: valid with/without rationale and referenced_warning_id
     - **SessionLinkedPayload**: both link_type values, invalid rejected
  2. Run: `python3.11 -m pytest tests/unit/ -k collaboration -v`
- **Files**: `tests/unit/test_collaboration_payloads.py` (extend)
- **Parallel?**: No — depends on T018-T023

## Test Strategy

- **Unit tests**: Focus on `min_length=2` validation for `participant_ids` and Literal constraint enforcement
- **Run command**: `python3.11 -m pytest tests/unit/ -k collaboration -v`
- **mypy check**: `mypy --strict src/spec_kitty_events/collaboration.py`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `min_length=2` on `List[str]` field behavior | May not work as expected in Pydantic v2 | Test explicitly with 0, 1, and 2 element lists |
| `participant_ids` vs `participant_id` confusion | Wrong field name in multi-actor payloads | Warning payloads use `participant_ids` (plural) — test both field names |

## Review Guidance

- **Critical**: Verify warning payloads use `participant_ids` (plural, `List[str]`) NOT `participant_id` (singular)
- Verify `participant_ids` has `min_length=2` constraint
- Verify `acknowledgement` Literal is exactly `["continue", "hold", "reassign", "defer"]`
- Verify `severity` Literal is exactly `["info", "warning"]`
- Verify `link_type` Literal is exactly `["cli_to_saas", "saas_to_cli"]`
- Cross-check all field names with `data-model.md`

## Completion

```bash
git add -A && git commit -m "feat(WP04): warning, communication, and session payloads"
spec-kitty agent tasks move-task WP04 --to for_review --note "Ready for review: 6 payloads (2 multi-actor, 4 single-actor) with tests"
```

## Activity Log

- 2026-02-15T10:35:14Z – system – lane=planned – Prompt created.
- 2026-02-15T11:02:25Z – claude-coordinator – shell_pid=67115 – lane=doing – Assigned agent via workflow command
