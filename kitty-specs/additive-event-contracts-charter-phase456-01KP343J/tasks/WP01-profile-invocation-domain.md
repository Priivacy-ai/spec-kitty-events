---
work_package_id: WP01
title: Profile Invocation Domain + Unit Tests
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-007
- FR-008
- FR-013
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- date: '2026-04-13'
  author: spec-kitty.tasks
  action: created
authoritative_surface: src/spec_kitty_events/profile_invocation.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/profile_invocation.py
- tests/unit/test_profile_invocation.py
tags: []
---

# WP01: Profile Invocation Domain + Unit Tests

## Objective

Create the `profile_invocation.py` domain module with constants, a typed payload model for `ProfileInvocationStarted`, reserved constants for future events, and comprehensive unit tests that validate field enforcement, immutability, and reserved-constant rules.

## Context

This module tracks when the spec-kitty runtime begins executing a step under a resolved agent profile. It follows the exact pattern established by 11 existing domain modules in this repo. The key reference modules are:

- `src/spec_kitty_events/mission_next.py` — provides `RuntimeActorIdentity` value object (import directly from this module, NOT from `__init__.py`)
- `src/spec_kitty_events/dossier.py` — structural reference for domain module layout
- `src/spec_kitty_events/mission_audit.py` — example of importing value objects from peer modules

**Import rule**: Import `RuntimeActorIdentity` from `spec_kitty_events.mission_next`, NOT from the package root. The `__init__.py` eagerly imports all domain modules and importing from it would create circular imports.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- **Execution**: Worktree allocated by `spec-kitty next --agent <name>`, lane computed from `lanes.json` after `finalize-tasks`

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent <name>
```

---

## Subtask T001: Create Module Skeleton

**Purpose**: Set up `src/spec_kitty_events/profile_invocation.py` with the standard section structure, module docstring, and imports.

**Steps**:
1. Create file `src/spec_kitty_events/profile_invocation.py`
2. Add module docstring following the established pattern:
   ```python
   """Profile invocation event contracts.

   Defines event type constants, payload model, and domain schema version
   for the profile invocation contract surface (3.1.0).
   """
   ```
3. Add imports:
   ```python
   from __future__ import annotations
   from typing import FrozenSet, Optional
   from pydantic import BaseModel, ConfigDict, Field
   from spec_kitty_events.mission_next import RuntimeActorIdentity
   ```
4. Add Section 1 comment header: `# ── Section 1: Constants ──────`
5. Define the domain schema version:
   ```python
   PROFILE_INVOCATION_SCHEMA_VERSION: str = "3.1.0"
   ```

**Validation**:
- [ ] File exists at correct path
- [ ] Imports compile without error
- [ ] No circular import when running `python -c "import spec_kitty_events.profile_invocation"`

---

## Subtask T002: Implement ProfileInvocationStartedPayload

**Purpose**: Create the typed payload model with all fields defined in spec FR-002.

**Steps**:
1. Define the event type constant:
   ```python
   PROFILE_INVOCATION_STARTED: str = "ProfileInvocationStarted"
   ```
2. Add Section 2 comment header and implement the payload model:
   ```python
   class ProfileInvocationStartedPayload(BaseModel):
       """Payload for ProfileInvocationStarted events.

       Emitted when the runtime begins executing a step under a resolved agent profile.
       """
       model_config = ConfigDict(frozen=True, extra="forbid")

       mission_id: str = Field(..., min_length=1, description="Mission identifier")
       run_id: str = Field(..., min_length=1, description="Run identifier from MissionRunStarted")
       step_id: str = Field(..., min_length=1, description="Step being executed")
       action: str = Field(..., min_length=1, description="Bound action name")
       profile_slug: str = Field(..., min_length=1, description="Resolved agent profile slug")
       profile_version: Optional[str] = Field(
           None, min_length=1, description="Profile version if versioned profiles are in use"
       )
       actor: RuntimeActorIdentity = Field(..., description="Runtime actor identity")
       governance_scope: Optional[str] = Field(
           None, min_length=1, description="Governance scope identifier"
       )
   ```

**Field validation rules**:
- All required `str` fields have `min_length=1` (rejects empty strings)
- Optional `str` fields have `min_length=1` when present (rejects `""` but accepts `None`)
- `actor` field uses nested `RuntimeActorIdentity` model validation
- `extra="forbid"` rejects any field not in the model

**Validation**:
- [ ] `ProfileInvocationStartedPayload(mission_id="m1", run_id="r1", step_id="s1", action="implement WP03", profile_slug="architect-v2", actor=RuntimeActorIdentity(actor_id="a1", actor_type="llm"))` constructs successfully
- [ ] Missing `profile_slug` raises `ValidationError`
- [ ] `action=""` (empty string) raises `ValidationError`
- [ ] Extra field `{"foo": "bar"}` raises `ValidationError`

---

## Subtask T003: Define Reserved Constants

**Purpose**: Forward-declare `ProfileInvocationCompleted` and `ProfileInvocationFailed` as string constants with deferred payload contracts, following the `NextStepPlanned` pattern.

**Steps**:
1. After the `PROFILE_INVOCATION_STARTED` constant, add:
   ```python
   PROFILE_INVOCATION_COMPLETED: str = "ProfileInvocationCompleted"  # Reserved — payload contract deferred
   PROFILE_INVOCATION_FAILED: str = "ProfileInvocationFailed"  # Reserved — payload contract deferred
   ```
2. Define the event types frozen set including all three:
   ```python
   PROFILE_INVOCATION_EVENT_TYPES: FrozenSet[str] = frozenset({
       PROFILE_INVOCATION_STARTED,
       PROFILE_INVOCATION_COMPLETED,  # Reserved — payload deferred
       PROFILE_INVOCATION_FAILED,     # Reserved — payload deferred
   })
   ```

**Validation**:
- [ ] `PROFILE_INVOCATION_COMPLETED` and `PROFILE_INVOCATION_FAILED` are string constants
- [ ] Both are included in `PROFILE_INVOCATION_EVENT_TYPES`
- [ ] `len(PROFILE_INVOCATION_EVENT_TYPES) == 3`
- [ ] No payload models exist for reserved types

---

## Subtask T004: Create Unit Tests

**Purpose**: Create `tests/unit/test_profile_invocation.py` with comprehensive tests for the domain module.

**Steps**:
1. Create the test file with these test cases:

**Valid construction tests**:
- `test_minimal_payload`: Construct with only required fields, verify all values
- `test_full_payload`: Construct with all fields including optional `profile_version` and `governance_scope`
- `test_actor_embedding`: Verify `RuntimeActorIdentity` is correctly nested and accessible

**Field enforcement tests**:
- `test_missing_mission_id_raises`: Omit `mission_id`, expect `ValidationError`
- `test_missing_profile_slug_raises`: Omit `profile_slug`, expect `ValidationError`
- `test_empty_action_raises`: Pass `action=""`, expect `ValidationError` (min_length=1)
- `test_empty_step_id_raises`: Pass `step_id=""`, expect `ValidationError`

**Immutability and extra-forbid tests**:
- `test_frozen_immutability`: Attempt attribute assignment, expect error
- `test_extra_forbid`: Pass unknown field, expect `ValidationError`

**Reserved constant tests**:
- `test_reserved_constants_exist`: Assert `PROFILE_INVOCATION_COMPLETED` and `PROFILE_INVOCATION_FAILED` are strings
- `test_event_types_frozenset`: Assert all 3 types are in `PROFILE_INVOCATION_EVENT_TYPES`
- `test_schema_version`: Assert `PROFILE_INVOCATION_SCHEMA_VERSION == "3.1.0"`

**Roundtrip test**:
- `test_model_dump_roundtrip`: Construct payload, dump to dict, reconstruct from dict, verify equality

**Example test helper**:
```python
def _make_actor(**overrides):
    defaults = {"actor_id": "test-actor", "actor_type": "llm"}
    defaults.update(overrides)
    return RuntimeActorIdentity(**defaults)

def _make_payload(**overrides):
    defaults = {
        "mission_id": "test-mission",
        "run_id": "test-run",
        "step_id": "implement",
        "action": "implement WP03",
        "profile_slug": "architect-v2",
        "actor": _make_actor(),
    }
    defaults.update(overrides)
    return ProfileInvocationStartedPayload(**defaults)
```

**Validation**:
- [ ] All tests pass: `pytest tests/unit/test_profile_invocation.py -v`
- [ ] At least 12 test cases covering all validation paths

---

## Subtask T005: Verify mypy Passes

**Purpose**: Ensure the new module passes strict type checking.

**Steps**:
1. Run: `mypy --strict src/spec_kitty_events/profile_invocation.py`
2. Fix any type errors (common issues: missing return type annotations, untyped imports)
3. Run again to confirm zero errors

**Validation**:
- [ ] `mypy --strict src/spec_kitty_events/profile_invocation.py` exits with code 0
- [ ] Zero errors, zero warnings

---

## Definition of Done

1. `src/spec_kitty_events/profile_invocation.py` exists with all constants, payload model, and type set
2. `tests/unit/test_profile_invocation.py` exists with 12+ test cases
3. `pytest tests/unit/test_profile_invocation.py` passes
4. `mypy --strict src/spec_kitty_events/profile_invocation.py` passes
5. No circular imports when importing the module

## Risks

- **Circular import**: Mitigated by importing `RuntimeActorIdentity` directly from `spec_kitty_events.mission_next`, not from `__init__.py`
- **RuntimeActorIdentity API change**: Low risk; the value object is stable across 14 missions

## Reviewer Guidance

- Verify `ConfigDict(frozen=True, extra="forbid")` is set on the payload model
- Verify reserved constants have `# Reserved` comments
- Verify all `str` fields have `min_length=1`
- Verify imports come from `spec_kitty_events.mission_next`, not from `spec_kitty_events`
- Verify unit tests cover valid construction, field enforcement, immutability, extra-forbid, and reserved constants
