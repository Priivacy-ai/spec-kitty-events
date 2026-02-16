---
work_package_id: WP03
title: Gate & Clarification Payload Models
lane: "doing"
dependencies: [WP02]
base_branch: 007-glossary-semantic-integrity-contracts-WP02
base_commit: 421824f411e5452ce78bc91a713e6960e4a0a4ab
created_at: '2026-02-16T13:18:21.106217+00:00'
subtasks:
- T010
- T011
- T012
- T013
phase: Phase 1 - Payload Models
assignee: ''
agent: "claude-opus"
shell_pid: "21232"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-16T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Gate & Clarification Payload Models

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Define the remaining 3 payload models: `SemanticCheckEvaluatedPayload`, `GlossaryClarificationRequestedPayload`/`GlossaryClarificationResolvedPayload`, and `GenerationBlockedBySemanticConflictPayload`.
- `SemanticCheckEvaluatedPayload` references `SemanticConflictEntry` from WP02.
- `GenerationBlockedBySemanticConflictPayload.blocking_strictness` cannot be `"off"`.
- `mypy --strict` passes.

**Success**: All models construct/validate/round-trip. Business rules enforced (non-empty conflict_event_ids, blocking_strictness ∈ {"medium", "max"}).

## Context & Constraints

- **Reference**: `kitty-specs/007-glossary-semantic-integrity-contracts/data-model.md` — full field specs.
- **Reference**: `kitty-specs/007-glossary-semantic-integrity-contracts/contracts/glossary-events.md` — contract definitions.
- **Dependency**: `SemanticConflictEntry` from WP02 must exist in `glossary.py`.
- **Burst-window key**: `semantic_check_event_id` on clarification request payload — this is the deterministic grouping key for the burst cap (P2 review finding).

**Implementation command**: `spec-kitty implement WP03 --base WP02`

## Subtasks & Detailed Guidance

### Subtask T010 – Define `SemanticCheckEvaluatedPayload`

- **Purpose**: Payload for step-level pre-generation semantic check results. This is the most complex payload model — it carries the conflict list, severity, recommended action, and effective strictness.
- **Steps**:
  1. Define in Section 3 of `glossary.py`:
     ```python
     class SemanticCheckEvaluatedPayload(BaseModel):
         """Payload for SemanticCheckEvaluated event (step-level semantic check)."""

         model_config = ConfigDict(frozen=True)

         mission_id: str = Field(..., min_length=1, description="Mission context")
         scope_id: str = Field(..., min_length=1, description="Scope checked against")
         step_id: str = Field(..., min_length=1, description="Step being evaluated")
         conflicts: Tuple[SemanticConflictEntry, ...] = Field(
             ..., description="List of detected conflicts"
         )
         severity: Literal["low", "medium", "high"] = Field(
             ..., description="Overall check severity (max of conflicts)"
         )
         confidence: float = Field(
             ..., ge=0.0, le=1.0, description="Overall confidence score"
         )
         recommended_action: Literal["block", "warn", "pass"] = Field(
             ..., description="Action recommendation based on severity and strictness"
         )
         effective_strictness: Literal["off", "medium", "max"] = Field(
             ..., description="Strictness mode used for this evaluation"
         )
         step_metadata: Dict[str, str] = Field(
             default_factory=dict,
             description="Mission primitive metadata (no hardcoded step names)",
         )
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 3).
- **Parallel?**: No — T011/T012 can start alongside, but T010 should be placed first in the file since it's the primary gate event.
- **Notes**: `conflicts` is a `Tuple[SemanticConflictEntry, ...]` — can be empty for a "pass" check. The `effective_strictness` can be `"off"` — this represents the check result even when strictness is off (though in practice the CLI shouldn't emit these events when strictness is off per the spec).

### Subtask T011 – Define `GlossaryClarificationRequestedPayload`

- **Purpose**: Payload for when policy requires human/actor clarification on an ambiguous term.
- **Steps**:
  1. Define in Section 3:
     ```python
     class GlossaryClarificationRequestedPayload(BaseModel):
         """Payload for GlossaryClarificationRequested event."""

         model_config = ConfigDict(frozen=True)

         mission_id: str = Field(..., min_length=1, description="Mission context")
         scope_id: str = Field(..., min_length=1, description="Scope context")
         step_id: str = Field(..., min_length=1, description="Step that triggered clarification")
         semantic_check_event_id: str = Field(
             ...,
             min_length=1,
             description="Event ID of triggering SemanticCheckEvaluated (burst-window key)",
         )
         term: str = Field(..., min_length=1, description="The ambiguous term")
         question: str = Field(..., description="Clarification question text")
         options: Tuple[str, ...] = Field(..., description="Available answer options")
         urgency: Literal["low", "medium", "high"] = Field(
             ..., description="Urgency level"
         )
         actor: str = Field(..., min_length=1, description="Actor who triggered the request")
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 3).
- **Parallel?**: Yes — independent of T010 and T013.
- **Notes**: `semantic_check_event_id` is the burst-window grouping key (P2 review finding fix). The reducer uses this to enforce the 3-per-burst cap.

### Subtask T012 – Define `GlossaryClarificationResolvedPayload`

- **Purpose**: Payload for when a clarification question is answered.
- **Steps**:
  1. Define in Section 3:
     ```python
     class GlossaryClarificationResolvedPayload(BaseModel):
         """Payload for GlossaryClarificationResolved event."""

         model_config = ConfigDict(frozen=True)

         mission_id: str = Field(..., min_length=1, description="Mission context")
         clarification_event_id: str = Field(
             ...,
             min_length=1,
             description="Event ID of the originating clarification request",
         )
         selected_meaning: str = Field(
             ..., min_length=1, description="The chosen or entered meaning"
         )
         actor: str = Field(..., min_length=1, description="Identity of the resolving actor")
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 3).
- **Parallel?**: Yes.
- **Notes**: `clarification_event_id` links back to the originating `GlossaryClarificationRequested` event. Multiple resolutions for the same request are handled by the reducer (last-write-wins).

### Subtask T013 – Define `GenerationBlockedBySemanticConflictPayload`

- **Purpose**: Payload for when a high-severity unresolved conflict blocks LLM generation at a step boundary.
- **Steps**:
  1. Define in Section 3:
     ```python
     class GenerationBlockedBySemanticConflictPayload(BaseModel):
         """Payload for GenerationBlockedBySemanticConflict event."""

         model_config = ConfigDict(frozen=True)

         mission_id: str = Field(..., min_length=1, description="Mission context")
         step_id: str = Field(..., min_length=1, description="Step that was blocked")
         conflict_event_ids: Tuple[str, ...] = Field(
             ...,
             min_length=1,
             description="Event IDs of unresolved SemanticCheckEvaluated events",
         )
         blocking_strictness: Literal["medium", "max"] = Field(
             ..., description="Policy mode that triggered the block (never 'off')"
         )
         step_metadata: Dict[str, str] = Field(
             default_factory=dict,
             description="Mission primitive metadata",
         )
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 3).
- **Parallel?**: No — should be placed last in Section 3 as it represents the final enforcement outcome.
- **Notes**: `blocking_strictness` uses `Literal["medium", "max"]` — intentionally excludes `"off"` because generation is never blocked when strictness is off. `conflict_event_ids` uses `min_length=1` on the `Tuple` to enforce at least one conflict reference.

## Risks & Mitigations

- **Risk**: Pydantic v2 `min_length` on `Tuple[str, ...]` may not work as expected. **Mitigation**: Test in WP07. If `min_length` doesn't apply to tuples, use a `@field_validator` instead.
- **Risk**: `Literal["medium", "max"]` for `blocking_strictness` might confuse consumers expecting all 3 strictness values. **Mitigation**: The docstring explicitly states "never 'off'"; tests in WP07 verify that `"off"` is rejected.

## Review Guidance

- `SemanticCheckEvaluatedPayload` has the most fields (9) — verify all are present with correct types.
- `blocking_strictness` must be `Literal["medium", "max"]` — NOT `Literal["off", "medium", "max"]`.
- `conflict_event_ids` must enforce non-empty (min_length=1 or validator).
- `semantic_check_event_id` on clarification request — verify it's required (not optional).

## Activity Log

- 2026-02-16T12:00:00Z – system – lane=planned – Prompt created.
- 2026-02-16T13:18:21Z – claude-opus – shell_pid=21232 – lane=doing – Assigned agent via workflow command
