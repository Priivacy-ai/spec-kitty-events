---
work_package_id: WP04
title: Package Integration + Schema + Version Bump
dependencies:
- WP03
requirement_refs:
- C-005
- FR-009
- FR-010
- FR-011
- NFR-002
- NFR-003
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
agent: "claude:opus:implementer:implementer"
shell_pid: "2532"
history:
- date: '2026-04-13'
  author: spec-kitty.tasks
  action: created
authoritative_surface: src/spec_kitty_events/__init__.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/conformance/validators.py
- src/spec_kitty_events/__init__.py
- src/spec_kitty_events/schemas/profile_invocation_started_payload.schema.json
- src/spec_kitty_events/schemas/retrospective_completed_payload.schema.json
- src/spec_kitty_events/schemas/retrospective_skipped_payload.schema.json
- pyproject.toml
tags: []
---

# WP04: Package Integration + Schema + Version Bump

## Objective

Wire the new domain modules into the package-wide integration surfaces: register event types in the conformance validator dispatch, add imports and exports to `__init__.py`, bump both version surfaces to `3.1.0`, generate JSON schemas, and validate that the entire test suite passes.

## Context

This is the final integration WP. All domain modules (WP01, WP02) and conformance fixtures (WP03) must be complete before this WP starts. The work touches shared files that all consumers depend on.

Key files to modify:
- `src/spec_kitty_events/conformance/validators.py` — dispatch maps at lines 134-206 and 209-281
- `src/spec_kitty_events/__init__.py` — imports, exports, `__version__`, `__all__`
- `pyproject.toml` — package version

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- **Execution**: Worktree allocated after WP03 completes

## Implementation Command

```bash
spec-kitty agent action implement WP04 --agent <name>
```

---

## Subtask T017: Register New Types in Validator Dispatch

**Purpose**: Add the 3 new event types to `_EVENT_TYPE_TO_MODEL` and `_EVENT_TYPE_TO_SCHEMA` in `validators.py`.

**Steps**:
1. Edit `src/spec_kitty_events/conformance/validators.py`
2. Add imports at the top (after existing domain imports):
   ```python
   from spec_kitty_events.profile_invocation import (
       ProfileInvocationStartedPayload,
   )
   from spec_kitty_events.retrospective import (
       RetrospectiveCompletedPayload,
       RetrospectiveSkippedPayload,
   )
   ```
3. Add entries to `_EVENT_TYPE_TO_MODEL` (after the sync section):
   ```python
   # Profile invocation contracts (3.1.0)
   "ProfileInvocationStarted": ProfileInvocationStartedPayload,
   # Retrospective contracts (3.1.0)
   "RetrospectiveCompleted": RetrospectiveCompletedPayload,
   "RetrospectiveSkipped": RetrospectiveSkippedPayload,
   ```
4. Add entries to `_EVENT_TYPE_TO_SCHEMA` (after the sync section):
   ```python
   # Profile invocation contracts (3.1.0)
   "ProfileInvocationStarted": "profile_invocation_started_payload",
   # Retrospective contracts (3.1.0)
   "RetrospectiveCompleted": "retrospective_completed_payload",
   "RetrospectiveSkipped": "retrospective_skipped_payload",
   ```

**Validation**:
- [ ] `validate_event({"mission_id": "m", "run_id": "r", "step_id": "s", "action": "a", "profile_slug": "p", "actor": {"actor_id": "a", "actor_type": "llm"}}, "ProfileInvocationStarted")` returns a `ConformanceResult` with `valid=True`
- [ ] `validate_event(...)` no longer raises `ValueError` for the 3 new event types
- [ ] Existing dispatch still works for all prior event types

---

## Subtask T018: Add Imports, Exports, and Version Bump in __init__.py

**Purpose**: Re-export all new symbols and bump `__version__`.

**Steps**:
1. Edit `src/spec_kitty_events/__init__.py`
2. Bump the version constant:
   ```python
   __version__ = "3.1.0"
   ```
3. Add import block after the sync imports section (around line 345):
   ```python
   # Profile invocation contracts (3.1.0)
   from spec_kitty_events.profile_invocation import (
       PROFILE_INVOCATION_SCHEMA_VERSION as PROFILE_INVOCATION_SCHEMA_VERSION,
       PROFILE_INVOCATION_STARTED as PROFILE_INVOCATION_STARTED,
       PROFILE_INVOCATION_COMPLETED as PROFILE_INVOCATION_COMPLETED,
       PROFILE_INVOCATION_FAILED as PROFILE_INVOCATION_FAILED,
       PROFILE_INVOCATION_EVENT_TYPES as PROFILE_INVOCATION_EVENT_TYPES,
       ProfileInvocationStartedPayload as ProfileInvocationStartedPayload,
   )

   # Retrospective contracts (3.1.0)
   from spec_kitty_events.retrospective import (
       RETROSPECTIVE_SCHEMA_VERSION as RETROSPECTIVE_SCHEMA_VERSION,
       RETROSPECTIVE_COMPLETED as RETROSPECTIVE_COMPLETED,
       RETROSPECTIVE_SKIPPED as RETROSPECTIVE_SKIPPED,
       RETROSPECTIVE_EVENT_TYPES as RETROSPECTIVE_EVENT_TYPES,
       RetrospectiveCompletedPayload as RetrospectiveCompletedPayload,
       RetrospectiveSkippedPayload as RetrospectiveSkippedPayload,
   )
   ```
   Note: Use `as` re-exports to satisfy mypy `--strict` implicit re-export rules.

4. Add new symbols to `__all__` list:
   ```python
   # Profile invocation contracts (3.1.0)
   "PROFILE_INVOCATION_SCHEMA_VERSION",
   "PROFILE_INVOCATION_STARTED",
   "PROFILE_INVOCATION_COMPLETED",
   "PROFILE_INVOCATION_FAILED",
   "PROFILE_INVOCATION_EVENT_TYPES",
   "ProfileInvocationStartedPayload",
   # Retrospective contracts (3.1.0)
   "RETROSPECTIVE_SCHEMA_VERSION",
   "RETROSPECTIVE_COMPLETED",
   "RETROSPECTIVE_SKIPPED",
   "RETROSPECTIVE_EVENT_TYPES",
   "RetrospectiveCompletedPayload",
   "RetrospectiveSkippedPayload",
   ```

**Validation**:
- [ ] `from spec_kitty_events import ProfileInvocationStartedPayload` works
- [ ] `from spec_kitty_events import RetrospectiveCompletedPayload` works
- [ ] `from spec_kitty_events import PROFILE_INVOCATION_EVENT_TYPES` works
- [ ] `spec_kitty_events.__version__ == "3.1.0"`
- [ ] All symbols in `__all__` are importable

---

## Subtask T019: Bump pyproject.toml Version

**Purpose**: Update the package metadata version to match `__version__`.

**Steps**:
1. Edit `pyproject.toml`
2. Change `version = "3.0.0"` to `version = "3.1.0"`

**Validation**:
- [ ] `pyproject.toml` shows `version = "3.1.0"`
- [ ] `spec_kitty_events.__version__` matches `pyproject.toml` version

---

## Subtask T020: Generate and Commit JSON Schemas

**Purpose**: Auto-generate JSON schema files for the 3 new payload models.

**Steps**:
1. The schema generator at `src/spec_kitty_events/schemas/generate.py` must know about the new models. Check if it auto-discovers models from imports or needs explicit registration.
2. If explicit registration is needed, add the new payload models to the generator's model list (check the pattern used by existing domain models in `generate.py`).
3. Run the schema generator:
   ```bash
   python -m spec_kitty_events.schemas.generate
   ```
4. Verify 3 new schema files were created:
   - `src/spec_kitty_events/schemas/profile_invocation_started_payload.schema.json`
   - `src/spec_kitty_events/schemas/retrospective_completed_payload.schema.json`
   - `src/spec_kitty_events/schemas/retrospective_skipped_payload.schema.json`
5. Run the drift check:
   ```bash
   python -m spec_kitty_events.schemas.generate --check
   ```
   Must exit with code 0 (zero drift).

**Validation**:
- [ ] 3 new `.schema.json` files exist
- [ ] `python -m spec_kitty_events.schemas.generate --check` passes (zero drift)
- [ ] Schema files contain the expected field definitions

---

## Subtask T021: Full Test Suite Validation

**Purpose**: Run the complete validation pipeline to ensure no regressions.

**Steps**:
1. Run the full test suite:
   ```bash
   pytest -x -v
   ```
   Must pass with zero failures.

2. Run strict type checking:
   ```bash
   mypy --strict src/spec_kitty_events/
   ```
   Must pass with zero errors.

3. Run schema drift check:
   ```bash
   python -m spec_kitty_events.schemas.generate --check
   ```
   Must pass with zero drift.

4. Verify both version surfaces:
   ```bash
   python -c "import spec_kitty_events; print(spec_kitty_events.__version__)"
   ```
   Must print `3.1.0`.

5. Verify dispatch works for new types:
   ```bash
   python -c "
   from spec_kitty_events.conformance.validators import validate_event
   result = validate_event({
       'mission_id': 'm1', 'run_id': 'r1', 'step_id': 's1',
       'action': 'implement', 'profile_slug': 'arch-v2',
       'actor': {'actor_id': 'a1', 'actor_type': 'llm'}
   }, 'ProfileInvocationStarted')
   assert result.valid, f'Violations: {result.model_violations}'
   print('ProfileInvocationStarted: OK')

   result = validate_event({
       'mission_id': 'm1', 'actor': 'op1',
       'trigger_source': 'operator',
       'completed_at': '2026-04-13T10:00:00Z'
   }, 'RetrospectiveCompleted')
   assert result.valid, f'Violations: {result.model_violations}'
   print('RetrospectiveCompleted: OK')

   result = validate_event({
       'mission_id': 'm1', 'actor': 'op1',
       'trigger_source': 'runtime',
       'skip_reason': 'trivial', 'skipped_at': '2026-04-13T10:00:00Z'
   }, 'RetrospectiveSkipped')
   assert result.valid, f'Violations: {result.model_violations}'
   print('RetrospectiveSkipped: OK')
   "
   ```

**Validation**:
- [ ] `pytest -x -v` passes (zero failures)
- [ ] `mypy --strict src/spec_kitty_events/` passes (zero errors)
- [ ] Schema drift check passes
- [ ] `__version__` reads `"3.1.0"`
- [ ] `validate_event()` dispatches correctly for all 3 new types

---

## Definition of Done

1. `validators.py` has dispatch entries for all 3 new event types
2. `__init__.py` exports all new symbols and `__version__ == "3.1.0"`
3. `pyproject.toml` version is `"3.1.0"`
4. 3 JSON schema files are generated and committed
5. Full `pytest` suite passes
6. `mypy --strict` passes on entire package
7. Schema drift check passes
8. `validate_event()` works end-to-end for all 3 new types

## Risks

- **Schema generator registration**: If the generator doesn't auto-discover new models from imports, the models must be added to its explicit list. Check `src/spec_kitty_events/schemas/generate.py` for the registration pattern.
- **Import ordering in __init__.py**: New imports must come after all existing domain imports to avoid forward-reference issues.

## Reviewer Guidance

- Verify `__version__` and `pyproject.toml` both read `"3.1.0"` (P2a review finding)
- Verify imports in `validators.py` come from domain modules directly, not from `__init__.py`
- Verify `__all__` list includes all 12 new symbols
- Verify the `as` re-export pattern is used in `__init__.py` for mypy compliance
- Run `python -m spec_kitty_events.schemas.generate --check` to verify zero drift
- Run the full test suite to verify no regressions

## Activity Log

- 2026-04-13T10:29:19Z – claude:opus:implementer:implementer – shell_pid=2532 – Started implementation via action command
