---
work_package_id: WP03
title: Shared Conformance + Fixture Integration
dependencies:
- WP01
- WP02
requirement_refs:
- FR-012
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
agent: "claude:opus:reviewer:reviewer"
shell_pid: "2336"
history:
- date: '2026-04-13'
  author: spec-kitty.tasks
  action: created
authoritative_surface: src/spec_kitty_events/conformance/fixtures/
execution_mode: code_change
owned_files:
- src/spec_kitty_events/conformance/loader.py
- src/spec_kitty_events/conformance/fixtures/profile_invocation/**
- src/spec_kitty_events/conformance/fixtures/retrospective/**
- src/spec_kitty_events/conformance/fixtures/manifest.json
- tests/test_profile_invocation_conformance.py
- tests/test_retrospective_conformance.py
tags: []
---

# WP03: Shared Conformance + Fixture Integration

## Objective

Extend the conformance infrastructure to support the two new event domains: add fixture categories to the loader, create valid and invalid fixture JSON files, register them in the manifest, and write conformance tests that validate fixtures using direct Pydantic model instantiation.

## Context

The conformance system has two layers: (1) `_VALID_CATEGORIES` whitelist in `loader.py` that gates fixture loading, and (2) fixture JSON files registered in `manifest.json` that are parametrized into tests.

**Important**: WP03 conformance tests use **direct Pydantic model instantiation** from fixture data, NOT the `validate_event()` dispatch function. The dispatch entries are wired in WP04. This keeps WP03 independent of WP04's integration work.

Key reference files:
- `src/spec_kitty_events/conformance/loader.py` — `_VALID_CATEGORIES` frozenset at line 17
- `src/spec_kitty_events/conformance/fixtures/manifest.json` — fixture registry
- `tests/test_dossier_conformance.py` — structural reference for conformance tests
- `src/spec_kitty_events/conformance/fixtures/dossier/` — structural reference for fixture directories

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- **Execution**: Worktree allocated after WP01 and WP02 complete

## Implementation Command

```bash
spec-kitty agent action implement WP03 --agent <name>
```

---

## Subtask T011: Add New Categories to Loader

**Purpose**: Extend `_VALID_CATEGORIES` so `load_fixtures("profile_invocation")` and `load_fixtures("retrospective")` work.

**Steps**:
1. Edit `src/spec_kitty_events/conformance/loader.py`
2. Add `"profile_invocation"` and `"retrospective"` to `_VALID_CATEGORIES`:
   ```python
   _VALID_CATEGORIES = frozenset({
       "events", "lane_mapping", "edge_cases",
       "collaboration", "glossary", "mission_next",
       "dossier", "mission_audit", "decisionpoint",
       "connector", "sync",
       "profile_invocation", "retrospective",  # 3.1.0
   })
   ```
3. Update the `load_fixtures()` docstring to list the new categories

**Validation**:
- [ ] `load_fixtures("profile_invocation")` does not raise `ValueError` (may return empty list until fixtures exist)
- [ ] `load_fixtures("retrospective")` does not raise `ValueError`
- [ ] Existing categories still work unchanged

---

## Subtask T012: Create Profile Invocation Fixtures

**Purpose**: Create 2 valid and 2 invalid JSON fixtures for `ProfileInvocationStarted`.

**Steps**:
1. Create directory: `src/spec_kitty_events/conformance/fixtures/profile_invocation/valid/`
2. Create directory: `src/spec_kitty_events/conformance/fixtures/profile_invocation/invalid/`

3. Create `profile_invocation/valid/profile_invocation_started_minimal.json`:
   ```json
   {
     "mission_id": "01TESTMISSION000000000001",
     "run_id": "01TESTRUN0000000000000001",
     "step_id": "implement",
     "action": "implement WP03",
     "profile_slug": "architect-v2",
     "actor": {
       "actor_id": "claude-opus",
       "actor_type": "llm"
     }
   }
   ```

4. Create `profile_invocation/valid/profile_invocation_started_full.json`:
   ```json
   {
     "mission_id": "01TESTMISSION000000000001",
     "run_id": "01TESTRUN0000000000000001",
     "step_id": "review",
     "action": "review WP03",
     "profile_slug": "reviewer-v1",
     "profile_version": "1.2.0",
     "actor": {
       "actor_id": "claude-opus",
       "actor_type": "llm",
       "display_name": "Claude Opus",
       "provider": "anthropic",
       "model": "claude-opus-4-6"
     },
     "governance_scope": "mission-level"
   }
   ```

5. Create `profile_invocation/invalid/profile_invocation_started_missing_profile_slug.json`:
   ```json
   {
     "mission_id": "01TESTMISSION000000000001",
     "run_id": "01TESTRUN0000000000000001",
     "step_id": "implement",
     "action": "implement WP03",
     "actor": {
       "actor_id": "claude-opus",
       "actor_type": "llm"
     }
   }
   ```

6. Create `profile_invocation/invalid/profile_invocation_started_empty_action.json`:
   ```json
   {
     "mission_id": "01TESTMISSION000000000001",
     "run_id": "01TESTRUN0000000000000001",
     "step_id": "implement",
     "action": "",
     "profile_slug": "architect-v2",
     "actor": {
       "actor_id": "claude-opus",
       "actor_type": "llm"
     }
   }
   ```

**Validation**:
- [ ] 4 fixture files exist in correct directories
- [ ] Valid fixtures parse with `ProfileInvocationStartedPayload(**data)`
- [ ] Invalid fixtures raise `ValidationError` with `ProfileInvocationStartedPayload(**data)`

---

## Subtask T013: Create Retrospective Fixtures

**Purpose**: Create 3 valid and 2 invalid JSON fixtures for retrospective events.

**Steps**:
1. Create directory: `src/spec_kitty_events/conformance/fixtures/retrospective/valid/`
2. Create directory: `src/spec_kitty_events/conformance/fixtures/retrospective/invalid/`

3. Create `retrospective/valid/retrospective_completed_minimal.json`:
   ```json
   {
     "mission_id": "01TESTMISSION000000000001",
     "actor": "operator-1",
     "trigger_source": "operator",
     "completed_at": "2026-04-13T10:00:00Z"
   }
   ```

4. Create `retrospective/valid/retrospective_completed_with_artifact.json`:
   ```json
   {
     "mission_id": "01TESTMISSION000000000001",
     "actor": "runtime-agent",
     "trigger_source": "runtime",
     "artifact_ref": {
       "git_sha": "abc123def456",
       "git_ref": "main",
       "actor_id": "runtime-agent",
       "actor_kind": "llm"
     },
     "completed_at": "2026-04-13T10:00:00Z"
   }
   ```

5. Create `retrospective/valid/retrospective_skipped.json`:
   ```json
   {
     "mission_id": "01TESTMISSION000000000001",
     "actor": "operator-1",
     "trigger_source": "operator",
     "skip_reason": "trivial mission, retrospective not warranted",
     "skipped_at": "2026-04-13T10:00:00Z"
   }
   ```

6. Create `retrospective/invalid/retrospective_completed_missing_actor.json`:
   ```json
   {
     "mission_id": "01TESTMISSION000000000001",
     "trigger_source": "operator",
     "completed_at": "2026-04-13T10:00:00Z"
   }
   ```

7. Create `retrospective/invalid/retrospective_skipped_empty_reason.json`:
   ```json
   {
     "mission_id": "01TESTMISSION000000000001",
     "actor": "operator-1",
     "trigger_source": "runtime",
     "skip_reason": "",
     "skipped_at": "2026-04-13T10:00:00Z"
   }
   ```

**Validation**:
- [ ] 5 fixture files exist in correct directories
- [ ] Valid fixtures parse with respective payload models
- [ ] Invalid fixtures raise `ValidationError` with respective payload models

---

## Subtask T014: Register Fixtures in Manifest

**Purpose**: Add all 9 fixture entries to `manifest.json`.

**Steps**:
1. Edit `src/spec_kitty_events/conformance/fixtures/manifest.json`
2. Add these entries to the `"fixtures"` array:

```json
{
  "id": "profile-invocation-started-valid-minimal",
  "path": "profile_invocation/valid/profile_invocation_started_minimal.json",
  "expected_result": "valid",
  "event_type": "ProfileInvocationStarted",
  "notes": "Valid ProfileInvocationStartedPayload with required fields only",
  "min_version": "3.1.0"
},
{
  "id": "profile-invocation-started-valid-full",
  "path": "profile_invocation/valid/profile_invocation_started_full.json",
  "expected_result": "valid",
  "event_type": "ProfileInvocationStarted",
  "notes": "Valid ProfileInvocationStartedPayload with all optional fields",
  "min_version": "3.1.0"
},
{
  "id": "profile-invocation-started-invalid-missing-slug",
  "path": "profile_invocation/invalid/profile_invocation_started_missing_profile_slug.json",
  "expected_result": "invalid",
  "event_type": "ProfileInvocationStarted",
  "notes": "Missing required profile_slug field",
  "min_version": "3.1.0"
},
{
  "id": "profile-invocation-started-invalid-empty-action",
  "path": "profile_invocation/invalid/profile_invocation_started_empty_action.json",
  "expected_result": "invalid",
  "event_type": "ProfileInvocationStarted",
  "notes": "Empty action string violates min_length=1",
  "min_version": "3.1.0"
},
{
  "id": "retrospective-completed-valid-minimal",
  "path": "retrospective/valid/retrospective_completed_minimal.json",
  "expected_result": "valid",
  "event_type": "RetrospectiveCompleted",
  "notes": "Valid RetrospectiveCompletedPayload without artifact_ref",
  "min_version": "3.1.0"
},
{
  "id": "retrospective-completed-valid-with-artifact",
  "path": "retrospective/valid/retrospective_completed_with_artifact.json",
  "expected_result": "valid",
  "event_type": "RetrospectiveCompleted",
  "notes": "Valid RetrospectiveCompletedPayload with ProvenanceRef artifact",
  "min_version": "3.1.0"
},
{
  "id": "retrospective-skipped-valid",
  "path": "retrospective/valid/retrospective_skipped.json",
  "expected_result": "valid",
  "event_type": "RetrospectiveSkipped",
  "notes": "Valid RetrospectiveSkippedPayload with skip reason",
  "min_version": "3.1.0"
},
{
  "id": "retrospective-completed-invalid-missing-actor",
  "path": "retrospective/invalid/retrospective_completed_missing_actor.json",
  "expected_result": "invalid",
  "event_type": "RetrospectiveCompleted",
  "notes": "Missing required actor field",
  "min_version": "3.1.0"
},
{
  "id": "retrospective-skipped-invalid-empty-reason",
  "path": "retrospective/invalid/retrospective_skipped_empty_reason.json",
  "expected_result": "invalid",
  "event_type": "RetrospectiveSkipped",
  "notes": "Empty skip_reason violates min_length=1",
  "min_version": "3.1.0"
}
```

**Validation**:
- [ ] `manifest.json` is valid JSON after edits
- [ ] 9 new entries added with `min_version: "3.1.0"`
- [ ] All `path` values match actual file locations

---

## Subtask T015: Create Profile Invocation Conformance Tests

**Purpose**: Create `tests/test_profile_invocation_conformance.py` that validates fixtures using direct model instantiation.

**Steps**:
1. Create the test file following the pattern of `tests/test_dossier_conformance.py`:
   ```python
   """Conformance tests for profile invocation event contracts."""
   import pytest
   from spec_kitty_events.conformance.loader import load_fixtures
   from spec_kitty_events.profile_invocation import ProfileInvocationStartedPayload
   from pydantic import ValidationError

   @pytest.fixture
   def profile_invocation_fixtures():
       return load_fixtures("profile_invocation")

   def test_fixtures_loaded(profile_invocation_fixtures):
       """At least 4 fixtures should be loaded (2 valid, 2 invalid)."""
       assert len(profile_invocation_fixtures) >= 4

   @pytest.mark.parametrize("fixture", load_fixtures("profile_invocation"),
                            ids=lambda f: f.id)
   def test_profile_invocation_conformance(fixture):
       """Validate each fixture against ProfileInvocationStartedPayload."""
       if fixture.expected_valid:
           payload = ProfileInvocationStartedPayload(**fixture.payload)
           assert payload.profile_slug  # sanity check
       else:
           with pytest.raises(ValidationError):
               ProfileInvocationStartedPayload(**fixture.payload)
   ```

**Validation**:
- [ ] `pytest tests/test_profile_invocation_conformance.py -v` passes
- [ ] Valid fixtures construct successfully
- [ ] Invalid fixtures raise `ValidationError`

---

## Subtask T016: Create Retrospective Conformance Tests

**Purpose**: Create `tests/test_retrospective_conformance.py` that validates fixtures using direct model instantiation.

**Steps**:
1. Create the test file:
   ```python
   """Conformance tests for retrospective event contracts."""
   import pytest
   from spec_kitty_events.conformance.loader import load_fixtures
   from spec_kitty_events.retrospective import (
       RetrospectiveCompletedPayload,
       RetrospectiveSkippedPayload,
   )
   from pydantic import ValidationError

   _EVENT_TYPE_TO_MODEL = {
       "RetrospectiveCompleted": RetrospectiveCompletedPayload,
       "RetrospectiveSkipped": RetrospectiveSkippedPayload,
   }

   @pytest.fixture
   def retrospective_fixtures():
       return load_fixtures("retrospective")

   def test_fixtures_loaded(retrospective_fixtures):
       """At least 5 fixtures should be loaded (3 valid, 2 invalid)."""
       assert len(retrospective_fixtures) >= 5

   @pytest.mark.parametrize("fixture", load_fixtures("retrospective"),
                            ids=lambda f: f.id)
   def test_retrospective_conformance(fixture):
       """Validate each fixture against the appropriate payload model."""
       model_class = _EVENT_TYPE_TO_MODEL[fixture.event_type]
       if fixture.expected_valid:
           payload = model_class(**fixture.payload)
           assert payload.mission_id  # sanity check
       else:
           with pytest.raises(ValidationError):
               model_class(**fixture.payload)
   ```

**Validation**:
- [ ] `pytest tests/test_retrospective_conformance.py -v` passes
- [ ] Both event types route to correct payload models
- [ ] Valid and invalid fixtures produce expected outcomes

---

## Definition of Done

1. `_VALID_CATEGORIES` includes `"profile_invocation"` and `"retrospective"`
2. 9 fixture JSON files exist in correct directories
3. `manifest.json` has 9 new entries with `min_version: "3.1.0"`
4. Both conformance test files pass
5. `load_fixtures("profile_invocation")` and `load_fixtures("retrospective")` return expected counts
6. Existing conformance tests still pass (no regressions)

## Risks

- **Manifest JSON syntax error**: Manually editing JSON is error-prone. Validate JSON after edits.
- **Fixture path mismatch**: Ensure `path` values in manifest exactly match file locations.

## Reviewer Guidance

- Verify fixture JSON is well-formed and matches the payload model field names exactly
- Verify invalid fixtures target a single validation failure (not multiple compounding errors)
- Verify conformance tests use direct model instantiation, NOT `validate_event()` (that's WP04)
- Verify `min_version` is `"3.1.0"` for all new entries

## Activity Log

- 2026-04-13T10:23:42Z – claude:opus:implementer:implementer – shell_pid=2071 – Started implementation via action command
- 2026-04-13T10:26:48Z – claude:opus:implementer:implementer – shell_pid=2071 – Ready for review: conformance fixtures and tests for profile_invocation and retrospective domains
- 2026-04-13T10:27:06Z – claude:opus:reviewer:reviewer – shell_pid=2336 – Started review via action command
