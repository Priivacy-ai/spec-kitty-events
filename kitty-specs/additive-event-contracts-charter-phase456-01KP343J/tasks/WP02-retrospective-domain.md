---
work_package_id: WP02
title: Retrospective Domain + Unit Tests
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-013
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude:opus:implementer:implementer"
shell_pid: "99465"
history:
- date: '2026-04-13'
  author: spec-kitty.tasks
  action: created
authoritative_surface: src/spec_kitty_events/retrospective.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/retrospective.py
- tests/unit/test_retrospective.py
tags: []
---

# WP02: Retrospective Domain + Unit Tests

## Objective

Create the `retrospective.py` domain module with constants, two typed payload models (`RetrospectiveCompleted`, `RetrospectiveSkipped`), and comprehensive unit tests that validate field enforcement, `trigger_source` Literal validation, `ProvenanceRef` embedding, and immutability.

## Context

This module tracks post-merge retrospective lifecycle: whether a retrospective was completed (with optional artifact) or explicitly skipped (with reason). It is a bounded terminal-signal contract, not a state machine — no reducer is needed (C-008).

Key reference modules:
- `src/spec_kitty_events/dossier.py` — provides `ProvenanceRef` value object (import directly, NOT from `__init__.py`)
- `src/spec_kitty_events/mission_audit.py` — example of importing `ProvenanceRef` from peer module (line 14)
- `src/spec_kitty_events/decisionpoint.py` — structural reference for a domain with multiple event types and no reducer

**Import rule**: Import `ProvenanceRef` from `spec_kitty_events.dossier`, NOT from the package root. The `__init__.py` eagerly imports all domain modules — importing from it creates circular imports.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- **Execution**: Worktree allocated by `spec-kitty next --agent <name>`, lane computed from `lanes.json`

## Implementation Command

```bash
spec-kitty agent action implement WP02 --agent <name>
```

---

## Subtask T006: Create Module Skeleton

**Purpose**: Set up `src/spec_kitty_events/retrospective.py` with standard section structure.

**Steps**:
1. Create file `src/spec_kitty_events/retrospective.py`
2. Add module docstring:
   ```python
   """Retrospective event contracts.

   Defines event type constants, payload models, and domain schema version
   for the retrospective contract surface (3.1.0).

   Retrospective events are terminal signals — no reducer or state machine
   is defined. A mission either has a RetrospectiveCompleted, a
   RetrospectiveSkipped, or neither.
   """
   ```
3. Add imports:
   ```python
   from __future__ import annotations
   from typing import FrozenSet, Literal, Optional
   from pydantic import BaseModel, ConfigDict, Field
   from spec_kitty_events.dossier import ProvenanceRef
   ```
4. Define the domain schema version:
   ```python
   RETROSPECTIVE_SCHEMA_VERSION: str = "3.1.0"
   ```

**Validation**:
- [ ] File exists at correct path
- [ ] Imports compile without error
- [ ] `python -c "import spec_kitty_events.retrospective"` succeeds (no circular import)

---

## Subtask T007: Implement RetrospectiveCompletedPayload

**Purpose**: Create the typed payload for retrospective completion (FR-004).

**Steps**:
1. Define the event type constant:
   ```python
   RETROSPECTIVE_COMPLETED: str = "RetrospectiveCompleted"
   ```
2. Define the `TriggerSourceT` type alias for shared use:
   ```python
   TriggerSourceT = Literal["runtime", "operator", "policy"]
   ```
3. Implement the payload model:
   ```python
   class RetrospectiveCompletedPayload(BaseModel):
       """Payload for RetrospectiveCompleted events.

       Emitted when a retrospective step runs and produces a durable outcome.
       """
       model_config = ConfigDict(frozen=True, extra="forbid")

       mission_id: str = Field(..., min_length=1, description="Mission identifier")
       actor: str = Field(..., min_length=1, description="Actor who triggered the retrospective")
       trigger_source: TriggerSourceT = Field(
           ..., description="What initiated the retrospective"
       )
       artifact_ref: Optional[ProvenanceRef] = Field(
           None, description="Reference to retro artifact if one was produced"
       )
       completed_at: str = Field(
           ..., min_length=1, description="ISO 8601 completion timestamp"
       )
   ```

**Field validation rules**:
- `trigger_source` is a `Literal` — only `"runtime"`, `"operator"`, `"policy"` accepted
- `artifact_ref` is `Optional[ProvenanceRef]` — accepts `None` or a valid `ProvenanceRef` instance
- `completed_at` is a string (ISO 8601), not a `datetime` — matches the pattern used by dossier events (e.g., `indexed_at`, `checked_at`)

**Validation**:
- [ ] Minimal construction with `mission_id`, `actor`, `trigger_source`, `completed_at` succeeds
- [ ] Full construction with `artifact_ref=ProvenanceRef(git_sha="abc123")` succeeds
- [ ] `trigger_source="invalid"` raises `ValidationError`
- [ ] `artifact_ref` can be `None` (optional)

---

## Subtask T008: Implement RetrospectiveSkippedPayload

**Purpose**: Create the typed payload for retrospective skip (FR-006).

**Steps**:
1. Define the event type constant:
   ```python
   RETROSPECTIVE_SKIPPED: str = "RetrospectiveSkipped"
   ```
2. Implement the payload model:
   ```python
   class RetrospectiveSkippedPayload(BaseModel):
       """Payload for RetrospectiveSkipped events.

       Emitted when a retrospective step is explicitly skipped.
       """
       model_config = ConfigDict(frozen=True, extra="forbid")

       mission_id: str = Field(..., min_length=1, description="Mission identifier")
       actor: str = Field(..., min_length=1, description="Actor who decided to skip")
       trigger_source: TriggerSourceT = Field(
           ..., description="What would have initiated the retrospective"
       )
       skip_reason: str = Field(
           ..., min_length=1, description="Why the retrospective was skipped"
       )
       skipped_at: str = Field(
           ..., min_length=1, description="ISO 8601 skip decision timestamp"
       )
   ```
3. Define the event types frozen set:
   ```python
   RETROSPECTIVE_EVENT_TYPES: FrozenSet[str] = frozenset({
       RETROSPECTIVE_COMPLETED,
       RETROSPECTIVE_SKIPPED,
   })
   ```

**Validation**:
- [ ] Construction with valid `skip_reason` and `trigger_source` succeeds
- [ ] `skip_reason=""` (empty string) raises `ValidationError` (min_length=1)
- [ ] `trigger_source="auto"` raises `ValidationError` (not in Literal)
- [ ] `RETROSPECTIVE_EVENT_TYPES` has exactly 2 members

---

## Subtask T009: Create Unit Tests

**Purpose**: Create `tests/unit/test_retrospective.py` with comprehensive tests for both payload models.

**Steps**:
1. Create the test file with these test cases:

**RetrospectiveCompletedPayload tests**:
- `test_completed_minimal`: Construct with required fields only (no artifact_ref)
- `test_completed_with_artifact`: Construct with `artifact_ref=ProvenanceRef(git_sha="abc")`
- `test_completed_missing_actor_raises`: Omit `actor`, expect `ValidationError`
- `test_completed_invalid_trigger_source_raises`: Pass `trigger_source="auto"`, expect `ValidationError`
- `test_completed_valid_trigger_sources`: Verify all 3 Literal values accepted ("runtime", "operator", "policy")
- `test_completed_frozen`: Attempt attribute assignment, expect error
- `test_completed_extra_forbid`: Pass unknown field, expect `ValidationError`
- `test_completed_roundtrip`: `model_dump()` → `model_validate()` → equality

**RetrospectiveSkippedPayload tests**:
- `test_skipped_valid`: Construct with valid skip_reason
- `test_skipped_empty_reason_raises`: Pass `skip_reason=""`, expect `ValidationError`
- `test_skipped_missing_reason_raises`: Omit `skip_reason`, expect `ValidationError`
- `test_skipped_invalid_trigger_source_raises`: Pass `trigger_source="manual"`, expect `ValidationError`
- `test_skipped_frozen`: Attempt attribute assignment, expect error
- `test_skipped_extra_forbid`: Pass unknown field, expect `ValidationError`

**Module-level tests**:
- `test_event_types_frozenset`: Assert `RETROSPECTIVE_EVENT_TYPES` contains both type strings
- `test_schema_version`: Assert `RETROSPECTIVE_SCHEMA_VERSION == "3.1.0"`
- `test_no_reducer_exists`: Assert module has no `reduce_` function (C-008)

**Example test helpers**:
```python
def _make_completed(**overrides):
    defaults = {
        "mission_id": "test-mission",
        "actor": "operator-1",
        "trigger_source": "operator",
        "completed_at": "2026-04-13T10:00:00Z",
    }
    defaults.update(overrides)
    return RetrospectiveCompletedPayload(**defaults)

def _make_skipped(**overrides):
    defaults = {
        "mission_id": "test-mission",
        "actor": "operator-1",
        "trigger_source": "runtime",
        "skip_reason": "trivial mission, no retro needed",
        "skipped_at": "2026-04-13T10:00:00Z",
    }
    defaults.update(overrides)
    return RetrospectiveSkippedPayload(**defaults)
```

**Validation**:
- [ ] All tests pass: `pytest tests/unit/test_retrospective.py -v`
- [ ] At least 17 test cases covering both models

---

## Subtask T010: Verify mypy Passes

**Purpose**: Ensure the new module passes strict type checking.

**Steps**:
1. Run: `mypy --strict src/spec_kitty_events/retrospective.py`
2. Fix any type errors
3. Confirm zero errors

**Validation**:
- [ ] `mypy --strict src/spec_kitty_events/retrospective.py` exits with code 0

---

## Definition of Done

1. `src/spec_kitty_events/retrospective.py` exists with all constants, both payload models, and type set
2. `tests/unit/test_retrospective.py` exists with 17+ test cases
3. `pytest tests/unit/test_retrospective.py` passes
4. `mypy --strict src/spec_kitty_events/retrospective.py` passes
5. No circular imports when importing the module
6. No reducer function exists in the module (C-008)

## Risks

- **Circular import**: Mitigated by importing `ProvenanceRef` directly from `spec_kitty_events.dossier`
- **ProvenanceRef nested validation**: `ProvenanceRef` uses `extra="forbid"` — test fixtures must not include unknown fields in the nested object

## Reviewer Guidance

- Verify `ConfigDict(frozen=True, extra="forbid")` is set on both payload models
- Verify `TriggerSourceT` Literal is used (not a free-form string) for `trigger_source`
- Verify `ProvenanceRef` import comes from `spec_kitty_events.dossier`, not from `spec_kitty_events`
- Verify no `reduce_` function exists in the module
- Verify unit tests cover both models' valid construction, field enforcement, immutability, extra-forbid, and Literal validation

## Activity Log

- 2026-04-13T10:18:55Z – claude:opus:implementer:implementer – shell_pid=99465 – Started implementation via action command
