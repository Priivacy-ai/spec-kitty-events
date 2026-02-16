---
work_package_id: WP04
title: Reducer Output Models & Exports
lane: "doing"
dependencies: [WP03]
base_branch: 007-glossary-semantic-integrity-contracts-WP03
base_commit: b16d591b8f032989376528aa0ed974102c513e36
created_at: '2026-02-16T13:19:45.919745+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Payload Models
assignee: ''
agent: ''
shell_pid: "22012"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-16T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Reducer Output Models & Exports

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Define 3 reducer output models: `GlossaryAnomaly`, `ClarificationRecord`, and `ReducedGlossaryState`.
- Wire all ~21 glossary exports into `__init__.py` (imports + `__all__` entries).
- `mypy --strict` passes on `glossary.py` and `__init__.py`.

**Success**: `from spec_kitty_events import ReducedGlossaryState, GlossaryAnomaly, reduce_glossary_events` works (reduce_glossary_events will be a placeholder/stub until WP05).

## Context & Constraints

- **Reference**: `kitty-specs/007-glossary-semantic-integrity-contracts/data-model.md` — ReducedGlossaryState field specification.
- **Reference**: `src/spec_kitty_events/__init__.py` — current export structure (65 exports, will grow to ~86).
- **Pattern**: Follow `ReducedCollaborationState` from `collaboration.py` — frozen Pydantic model with Field defaults.
- **`current_strictness`**: Defaults to `"medium"` (spec: medium is the default strictness).

**Implementation command**: `spec-kitty implement WP04 --base WP03`

## Subtasks & Detailed Guidance

### Subtask T014 – Define `GlossaryAnomaly` model

- **Purpose**: Non-fatal issue recorded by the reducer in permissive mode.
- **Steps**:
  1. In Section 4 of `glossary.py`, define:
     ```python
     class GlossaryAnomaly(BaseModel):
         """Non-fatal issue encountered during glossary event reduction."""

         model_config = ConfigDict(frozen=True)

         event_id: str = Field(..., description="ID of the event that caused the anomaly")
         event_type: str = Field(..., description="Type of the problematic event")
         reason: str = Field(..., description="Human-readable explanation")
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 4).
- **Parallel?**: Yes — independent of T015/T016.
- **Notes**: Matches `CollaborationAnomaly` and `LifecycleAnomaly` pattern exactly.

### Subtask T015 – Define `ClarificationRecord` model

- **Purpose**: Tracks clarification state for burst-cap enforcement within the reducer.
- **Steps**:
  1. In Section 4, define:
     ```python
     class ClarificationRecord(BaseModel):
         """Tracks clarification lifecycle for burst-cap enforcement."""

         model_config = ConfigDict(frozen=True)

         request_event_id: str = Field(
             ..., description="Event ID of the clarification request"
         )
         semantic_check_event_id: str = Field(
             ..., description="Burst-window grouping key"
         )
         term: str = Field(..., description="The ambiguous term")
         resolved: bool = Field(default=False, description="Whether resolution received")
         resolution_event_id: Optional[str] = Field(
             None, description="Event ID of the resolution (if resolved)"
         )
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 4).
- **Parallel?**: Yes.
- **Notes**: `resolved` defaults to `False`. `resolution_event_id` is `None` until a matching `GlossaryClarificationResolved` event is processed.

### Subtask T016 – Define `ReducedGlossaryState` model

- **Purpose**: The frozen projected state produced by `reduce_glossary_events()`. This is the main output model.
- **Steps**:
  1. In Section 4, define:
     ```python
     class ReducedGlossaryState(BaseModel):
         """Projected glossary state from reduce_glossary_events()."""

         model_config = ConfigDict(frozen=True)

         mission_id: str = Field(default="", description="Mission context (from first event)")
         active_scopes: Dict[str, GlossaryScopeActivatedPayload] = Field(
             default_factory=dict, description="scope_id → activation payload"
         )
         current_strictness: Literal["off", "medium", "max"] = Field(
             default="medium", description="Latest mission-wide strictness mode"
         )
         strictness_history: Tuple[GlossaryStrictnessSetPayload, ...] = Field(
             default_factory=tuple, description="Ordered history of strictness changes"
         )
         term_candidates: Dict[str, Tuple[TermCandidateObservedPayload, ...]] = Field(
             default_factory=dict,
             description="term_surface → observed candidate payloads",
         )
         term_senses: Dict[str, GlossarySenseUpdatedPayload] = Field(
             default_factory=dict, description="term_surface → latest sense update"
         )
         clarifications: Tuple[ClarificationRecord, ...] = Field(
             default_factory=tuple, description="Ordered clarification timeline"
         )
         semantic_checks: Tuple[SemanticCheckEvaluatedPayload, ...] = Field(
             default_factory=tuple, description="Ordered check history"
         )
         generation_blocks: Tuple[GenerationBlockedBySemanticConflictPayload, ...] = Field(
             default_factory=tuple, description="Ordered block history"
         )
         anomalies: Tuple[GlossaryAnomaly, ...] = Field(
             default_factory=tuple, description="Non-fatal issues encountered"
         )
         event_count: int = Field(default=0, description="Total glossary events processed")
         last_processed_event_id: Optional[str] = Field(
             None, description="Last event_id in processed sequence"
         )
     ```
- **Files**: `src/spec_kitty_events/glossary.py` (Section 4).
- **Parallel?**: No — references models from T014, T015, and WP02/WP03 payloads.
- **Notes**: `current_strictness` defaults to `"medium"` per spec. All tuple fields use `default_factory=tuple`, dict fields use `default_factory=dict`. The `active_scopes` dict maps `scope_id` to the full activation payload for context access.

### Subtask T017 – Add glossary exports to `__init__.py`

- **Purpose**: Make all glossary symbols importable from the package top-level.
- **Steps**:
  1. Add import block after the collaboration imports in `__init__.py`:
     ```python
     # Glossary semantic integrity contracts
     from spec_kitty_events.glossary import (
         GLOSSARY_SCOPE_ACTIVATED,
         TERM_CANDIDATE_OBSERVED,
         SEMANTIC_CHECK_EVALUATED,
         GLOSSARY_CLARIFICATION_REQUESTED,
         GLOSSARY_CLARIFICATION_RESOLVED,
         GLOSSARY_SENSE_UPDATED,
         GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT,
         GLOSSARY_STRICTNESS_SET,
         GLOSSARY_EVENT_TYPES,
         SemanticConflictEntry,
         GlossaryScopeActivatedPayload,
         TermCandidateObservedPayload,
         SemanticCheckEvaluatedPayload,
         GlossaryClarificationRequestedPayload,
         GlossaryClarificationResolvedPayload,
         GlossarySenseUpdatedPayload,
         GenerationBlockedBySemanticConflictPayload,
         GlossaryStrictnessSetPayload,
         GlossaryAnomaly,
         ClarificationRecord,
         ReducedGlossaryState,
         reduce_glossary_events,
     )
     ```
  2. Add all 22 names to `__all__` list under a `# Glossary semantic integrity contracts` comment.
  3. Note: `reduce_glossary_events` won't exist yet (defined in WP05/WP06). Add a placeholder stub in `glossary.py`:
     ```python
     def reduce_glossary_events(
         events: Sequence["Event"],
         *,
         mode: Literal["strict", "permissive"] = "strict",
     ) -> ReducedGlossaryState:
         """Placeholder — implemented in WP05/WP06."""
         raise NotImplementedError("Reducer not yet implemented")
     ```
     This ensures imports work and mypy can check the signature.
- **Files**: `src/spec_kitty_events/__init__.py`, `src/spec_kitty_events/glossary.py` (stub).
- **Parallel?**: No — depends on all models being defined.
- **Notes**: The import of `Event` in the stub function signature needs a string annotation or a `TYPE_CHECKING` import to avoid circular imports. Use `from __future__ import annotations` (already present) and import `Event` at TYPE_CHECKING time:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from spec_kitty_events.models import Event
  ```

### Subtask T018 – Run `mypy --strict` checkpoint

- **Purpose**: Catch type errors early before building the reducer on top of these models.
- **Steps**:
  1. Run: `mypy --strict src/spec_kitty_events/glossary.py`
  2. Run: `mypy --strict src/spec_kitty_events/__init__.py`
  3. Fix any type errors found.
- **Files**: None (verification only).
- **Parallel?**: No — must run after T016/T017.
- **Notes**: Common issues: `Dict` vs `dict` (use typing imports for 3.10 compat), `Tuple` vs `tuple`, Optional import.

## Risks & Mitigations

- **Risk**: Circular import between `glossary.py` and `models.py` for `Event` type. **Mitigation**: Use `TYPE_CHECKING` guard and string annotations (`from __future__ import annotations` handles this).
- **Risk**: `__init__.py` becomes very long (~300+ lines). **Mitigation**: Follow existing section pattern with clear comment headers. Alphabetical order within each section.

## Review Guidance

- `ReducedGlossaryState.current_strictness` must default to `"medium"`.
- All `Tuple` fields must use `default_factory=tuple`, not `default=()`.
- All `Dict` fields must use `default_factory=dict`, not `default={}`.
- `__all__` list must contain exactly 22 new entries (8 constants + 1 frozenset + 8 payloads + 1 value object + 1 anomaly + 1 record + 1 state + 1 reducer).
- Placeholder `reduce_glossary_events` must have correct type signature for mypy.

## Activity Log

- 2026-02-16T12:00:00Z – system – lane=planned – Prompt created.
