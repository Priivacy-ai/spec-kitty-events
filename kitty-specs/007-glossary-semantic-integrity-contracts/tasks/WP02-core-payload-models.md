---
work_package_id: WP02
title: Core Payload Models — Scope, Term, Sense, Strictness
lane: "doing"
dependencies: [WP01]
base_branch: 007-glossary-semantic-integrity-contracts-WP01
base_commit: b784a988a468e02443875607213646fa89a9a4bc
created_at: '2026-02-16T13:16:38.576849+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
phase: Phase 1 - Payload Models
assignee: ''
agent: "claude-opus"
shell_pid: "19899"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-16T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Core Payload Models — Scope, Term, Sense, Strictness

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Define 5 frozen Pydantic payload models in `src/spec_kitty_events/glossary.py` Section 2 (value objects) and Section 3 (payload models).
- All models use `ConfigDict(frozen=True)` and have typed, validated fields.
- `mypy --strict` passes on the updated module.

**Success**: Each model can be constructed with valid data, serialized via `.model_dump()`, and reconstructed from the dict — round-trip fidelity. Invalid data raises `ValidationError`.

## Context & Constraints

- **Reference**: `kitty-specs/007-glossary-semantic-integrity-contracts/data-model.md` — full field specifications.
- **Reference**: `kitty-specs/007-glossary-semantic-integrity-contracts/contracts/glossary-events.md` — payload contract definitions.
- **Pattern**: Match `collaboration.py` model style (frozen BaseModel, Field descriptors with descriptions).
- **Actor identity**: Use `str` for actor fields (Design Decision D6 in plan.md).
- **Constrained fields**: Use `Literal` types (Design Decision D3 in plan.md).

**Implementation command**: `spec-kitty implement WP02 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T005 – Define `SemanticConflictEntry` value object

- **Purpose**: Typed conflict entry used within `SemanticCheckEvaluatedPayload.conflicts` (defined in WP03). Placed in Section 2 (Value Objects).
- **Steps**:
  1. In Section 2 of `glossary.py`, define:
     ```python
     class SemanticConflictEntry(BaseModel):
         """Single conflict finding within a semantic check evaluation."""

         model_config = ConfigDict(frozen=True)

         term: str = Field(..., min_length=1, description="The conflicting term surface text")
         nature: Literal["overloaded", "drift", "ambiguous"] = Field(
             ..., description="Classification of the conflict"
         )
         severity: Literal["low", "medium", "high"] = Field(
             ..., description="Severity level of this conflict"
         )
         description: str = Field(..., description="Human-readable explanation of the conflict")
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 2).
- **Parallel?**: Yes — independent of other models.
- **Notes**: All 4 fields are required, no defaults. `term` has `min_length=1` to prevent empty strings.

### Subtask T006 – Define `GlossaryScopeActivatedPayload`

- **Purpose**: Payload for when a glossary scope is activated for a mission.
- **Steps**:
  1. In Section 3 of `glossary.py`, define:
     ```python
     class GlossaryScopeActivatedPayload(BaseModel):
         """Payload for GlossaryScopeActivated event."""

         model_config = ConfigDict(frozen=True)

         mission_id: str = Field(..., min_length=1, description="Mission context")
         scope_id: str = Field(..., min_length=1, description="Unique scope identifier")
         scope_type: Literal[
             "spec_kitty_core", "team_domain", "audience_domain", "mission_local"
         ] = Field(..., description="Scope category")
         glossary_version_id: str = Field(
             ..., min_length=1, description="Version of the glossary being activated"
         )
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 3).
- **Parallel?**: Yes.
- **Notes**: `scope_type` uses `Literal` with exactly 4 allowed values. All fields required.

### Subtask T007 – Define `TermCandidateObservedPayload`

- **Purpose**: Payload for when a new or uncertain term appears in mission input.
- **Steps**:
  1. Define in Section 3:
     ```python
     class TermCandidateObservedPayload(BaseModel):
         """Payload for TermCandidateObserved event."""

         model_config = ConfigDict(frozen=True)

         mission_id: str = Field(..., min_length=1, description="Mission context")
         scope_id: str = Field(..., min_length=1, description="Scope the term was observed in")
         step_id: str = Field(..., min_length=1, description="Mission step that produced the term")
         term_surface: str = Field(
             ..., min_length=1, description="Raw text form of the observed term"
         )
         confidence: float = Field(
             ..., ge=0.0, le=1.0, description="Confidence score (0.0–1.0)"
         )
         actor: str = Field(..., min_length=1, description="Identity of the observing actor")
         step_metadata: Dict[str, str] = Field(
             default_factory=dict,
             description="Mission primitive metadata for the step (no hardcoded step names)",
         )
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 3).
- **Parallel?**: Yes.
- **Notes**: `confidence` uses `ge=0.0, le=1.0` for bounds validation. `step_metadata` is optional with empty dict default — carries mission primitive metadata per FR-009/FR-028.

### Subtask T008 – Define `GlossarySenseUpdatedPayload`

- **Purpose**: Payload for when a term's meaning is created or updated.
- **Steps**:
  1. Define in Section 3:
     ```python
     class GlossarySenseUpdatedPayload(BaseModel):
         """Payload for GlossarySenseUpdated event."""

         model_config = ConfigDict(frozen=True)

         mission_id: str = Field(..., min_length=1, description="Mission context")
         scope_id: str = Field(..., min_length=1, description="Scope of the term")
         term_surface: str = Field(..., min_length=1, description="Term being updated")
         before_sense: Optional[str] = Field(
             None, description="Previous sense value (None if first definition)"
         )
         after_sense: str = Field(..., min_length=1, description="New sense value")
         reason: str = Field(..., description="Why the sense was changed")
         actor: str = Field(..., min_length=1, description="Actor who made the change")
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 3).
- **Parallel?**: Yes.
- **Notes**: `before_sense` is `Optional[str]` with `None` default for initial definitions. `after_sense` is required and non-empty.

### Subtask T009 – Define `GlossaryStrictnessSetPayload`

- **Purpose**: Payload for when the mission-wide strictness policy is set or changed.
- **Steps**:
  1. Define in Section 3:
     ```python
     class GlossaryStrictnessSetPayload(BaseModel):
         """Payload for GlossaryStrictnessSet event (mission-wide policy change)."""

         model_config = ConfigDict(frozen=True)

         mission_id: str = Field(..., min_length=1, description="Mission context")
         new_strictness: Literal["off", "medium", "max"] = Field(
             ..., description="The new strictness mode"
         )
         previous_strictness: Optional[Literal["off", "medium", "max"]] = Field(
             None, description="Previous mode (None if initial setting)"
         )
         actor: str = Field(..., min_length=1, description="Actor who changed the setting")
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 3).
- **Parallel?**: Yes.
- **Notes**: `previous_strictness` is `Optional` for the initial setting case. Strictness is mission-wide, not per-scope (P1 review finding fix).

## Risks & Mitigations

- **Risk**: `Literal` type with `Optional` wrapper may have Pydantic v2 serialization quirks. **Mitigation**: Verify round-trip in WP07 tests; check `.model_dump()` output for `previous_strictness=None`.
- **Risk**: `confidence` bounds may not error on exactly `0.0` or `1.0` (boundary behavior). **Mitigation**: Pydantic `ge`/`le` are inclusive — test these exact values in WP07.

## Review Guidance

- All 5 models must have `ConfigDict(frozen=True)`.
- All `str` fields with `min_length=1` where empty strings are semantically invalid.
- `confidence: float` with `ge=0.0, le=1.0`.
- `scope_type` Literal has exactly 4 values.
- `step_metadata: Dict[str, str]` with `default_factory=dict`.

## Activity Log

- 2026-02-16T12:00:00Z – system – lane=planned – Prompt created.
- 2026-02-16T13:16:38Z – claude-opus – shell_pid=19899 – lane=doing – Assigned agent via workflow command
