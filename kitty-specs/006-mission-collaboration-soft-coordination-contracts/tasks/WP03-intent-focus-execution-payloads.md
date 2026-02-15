---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "Intent, Focus, and Execution Payloads"
phase: "Phase 1 - Payload Models"
lane: "planned"  # DO NOT EDIT - use: spec-kitty agent tasks move-task <WPID> --to <lane>
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-02-15T10:35:14Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Intent, Focus, and Execution Payloads

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add the 4 intent/focus/execution payload models to `collaboration.py` Section 3:
1. `DriveIntentSetPayload`
2. `FocusChangedPayload`
3. `PromptStepExecutionStartedPayload`
4. `PromptStepExecutionCompletedPayload`

**Success criteria**:
- All `Literal` constraints enforced (`intent`, `outcome`)
- `FocusChangedPayload` embeds `FocusTarget` model correctly
- All payloads frozen, round-trip through JSON
- `mypy --strict` passes

## Context & Constraints

**Reference documents**:
- Data model: `kitty-specs/006-.../data-model.md` (Drive Intent / Focus / Execution sections)
- Research: `kitty-specs/006-.../research.md` (R5: FocusTarget as standalone model)

**Prerequisites**: WP01 must be merged (provides `FocusTarget` model)

**Implementation command**: `spec-kitty implement WP03 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T013 – Implement DriveIntentSetPayload

- **Purpose**: Declares whether a participant has active or inactive drive intent for the mission.
- **Steps**:
  1. Add to Section 3 of `collaboration.py`:
     ```python
     class DriveIntentSetPayload(BaseModel):
         """Typed payload for DriveIntentSet events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Participant declaring intent")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         intent: Literal["active", "inactive"] = Field(..., description="Drive intent state")
     ```
  2. Verify invalid intent value (e.g., `"paused"`) raises `ValidationError`
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T014-T016)

### Subtask T014 – Implement FocusChangedPayload

- **Purpose**: Reports when a participant changes their focus to a different target.
- **Steps**:
  1. Add to Section 3:
     ```python
     class FocusChangedPayload(BaseModel):
         """Typed payload for FocusChanged events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Participant changing focus")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         focus_target: FocusTarget = Field(..., description="New focus target")
         previous_focus_target: Optional[FocusTarget] = Field(None, description="Previous focus (if any)")
     ```
  2. Verify nested `FocusTarget` round-trips correctly through `model_dump()` / `model_validate()`
  3. Verify `previous_focus_target` defaults to None when not provided
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T013, T015, T016)
- **Notes**: Both `focus_target` and `previous_focus_target` are `FocusTarget` instances. The nested model must serialize as a dict in JSON.

### Subtask T015 – Implement PromptStepExecutionStartedPayload

- **Purpose**: Signals that a participant (typically `llm_context`) has begun executing a prompt step.
- **Steps**:
  1. Add to Section 3:
     ```python
     class PromptStepExecutionStartedPayload(BaseModel):
         """Typed payload for PromptStepExecutionStarted events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Executing participant")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         step_id: str = Field(..., min_length=1, description="Step identifier")
         wp_id: Optional[str] = Field(None, description="Work package being targeted")
         step_description: Optional[str] = Field(None, description="Human-readable step description")
     ```
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T013, T014, T016)

### Subtask T016 – Implement PromptStepExecutionCompletedPayload

- **Purpose**: Reports completion of a prompt step execution with outcome.
- **Steps**:
  1. Add to Section 3:
     ```python
     class PromptStepExecutionCompletedPayload(BaseModel):
         """Typed payload for PromptStepExecutionCompleted events."""
         model_config = ConfigDict(frozen=True)
         participant_id: str = Field(..., min_length=1, description="Completing participant")
         mission_id: str = Field(..., min_length=1, description="Mission context")
         step_id: str = Field(..., min_length=1, description="Step identifier")
         wp_id: Optional[str] = Field(None, description="Work package targeted")
         outcome: Literal["success", "failure", "skipped"] = Field(..., description="Step outcome")
     ```
  2. Verify invalid outcome (e.g., `"error"`) raises `ValidationError`
- **Files**: `src/spec_kitty_events/collaboration.py`
- **Parallel?**: Yes (with T013-T015)

### Subtask T017 – Write unit tests for intent/focus/execution payloads

- **Purpose**: Test all 4 payloads including Literal constraints and FocusTarget embedding.
- **Steps**:
  1. Add tests (new file or extend existing):
     - **DriveIntentSetPayload**: valid `"active"` and `"inactive"`, invalid value rejected
     - **FocusChangedPayload**: valid with nested FocusTarget, round-trip preserves nested model, `previous_focus_target` optional
     - **PromptStepExecutionStartedPayload**: valid with/without optional fields
     - **PromptStepExecutionCompletedPayload**: valid outcomes `"success"/"failure"/"skipped"`, invalid outcome rejected
  2. Run: `python3.11 -m pytest tests/unit/ -k collaboration -v`
- **Files**: `tests/unit/test_collaboration_payloads.py` (extend or new)
- **Parallel?**: No — depends on T013-T016

## Test Strategy

- **Unit tests**: Focus on Literal constraint enforcement and nested model serialization
- **Run command**: `python3.11 -m pytest tests/unit/ -k collaboration -v`
- **mypy check**: `mypy --strict src/spec_kitty_events/collaboration.py`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Nested FocusTarget serialization in FocusChangedPayload | Dict key type confusion | Pydantic v2 handles nested models — verify round-trip in test |

## Review Guidance

- Verify all Literal types match data-model.md exactly
- Verify `FocusChangedPayload` accepts `FocusTarget` model instances (not raw dicts)
- Verify `PromptStepExecutionCompletedPayload.outcome` has all 3 values: success, failure, skipped

## Completion

```bash
git add -A && git commit -m "feat(WP03): intent, focus, and execution payloads"
spec-kitty agent tasks move-task WP03 --to for_review --note "Ready for review: 4 intent/focus/execution payloads with tests"
```

## Activity Log

- 2026-02-15T10:35:14Z – system – lane=planned – Prompt created.
