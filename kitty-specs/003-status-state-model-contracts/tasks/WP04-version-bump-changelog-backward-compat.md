---
work_package_id: WP04
title: Version Bump, Changelog, and Backward Compat
lane: "doing"
dependencies: []
base_branch: main
base_commit: 56ea49aeff0253fceb680ac0111f8a65f4c8cb63
created_at: '2026-02-08T14:31:53.195873+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 3 - Polish and Release
assignee: ''
agent: ''
shell_pid: "42939"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-08T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Version Bump, Changelog, and Backward Compat

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

## Objectives & Success Criteria

Bump version to `0.3.0-alpha`, write CHANGELOG entry with graduation criteria, verify all existing v0.2.0 tests pass unchanged (zero regressions), run full mypy --strict, and validate the consumer integration checklists.

**Success criteria**:
- `pyproject.toml` version = `"0.3.0-alpha"`
- `__init__.py` `__version__` = `"0.3.0-alpha"`
- CHANGELOG.md has comprehensive 0.3.0-alpha section with all 21 new exports listed
- Graduation criteria documented in CHANGELOG
- All existing tests pass with zero modifications
- `mypy --strict` reports zero errors across entire codebase
- Consumer integration checklists are accurate and actionable

## Context & Constraints

**Reference documents**:
- `kitty-specs/003-status-state-model-contracts/plan.md` — D7 (version bump), consumer checklists
- `kitty-specs/003-status-state-model-contracts/contracts/status-api.md` — full export list for CHANGELOG
- `CHANGELOG.md` — existing format and style to follow

**WP01-WP03 provide**: All code is complete and merged. status.py has all 6 sections, __init__.py has all 21 exports, tests are comprehensive.

**Constraints**:
- Do NOT modify any existing module code (models.py, gates.py, etc.)
- Do NOT modify any existing tests
- Version bump is the ONLY change to pyproject.toml and __init__.py (besides exports already added)

## Subtasks & Detailed Guidance

### Subtask T019 – Bump version to 0.3.0-alpha

**Purpose**: Update version in both canonical locations.

**Steps**:

1. Edit `pyproject.toml`:
   - Change `version = "0.2.0-alpha"` to `version = "0.3.0-alpha"`

2. Edit `src/spec_kitty_events/__init__.py`:
   - Change `__version__ = "0.2.0-alpha"` to `__version__ = "0.3.0-alpha"`

3. Verify consistency: `python3.11 -c "import spec_kitty_events; print(spec_kitty_events.__version__)"` should print `0.3.0-alpha`

**Files**: `pyproject.toml`, `src/spec_kitty_events/__init__.py`
**Parallel?**: Independent of T020.

### Subtask T020 – Write CHANGELOG.md entry

**Purpose**: Document the release with all new exports, breaking changes (none), and graduation criteria.

**Steps**:

1. Read existing `CHANGELOG.md` to understand the format.

2. Add a new section at the TOP (before 0.2.0-alpha):

   ```markdown
   ## [0.3.0-alpha] - 2026-02-XX

   ### Added

   **Status State Model Contracts** — New `status.py` module establishing the library as the
   shared contract authority for feature/WP status lifecycle events.

   #### Enums
   - `Lane` — 7 canonical status lanes: planned, claimed, in_progress, for_review, done, blocked, canceled
   - `ExecutionMode` — worktree | direct_repo execution context

   #### Evidence Models
   - `RepoEvidence` — Repository contribution evidence (repo, branch, commit, files_touched)
   - `VerificationEntry` — Test/verification execution record (command, result, summary)
   - `ReviewVerdict` — Reviewer identity and verdict (reviewer, verdict, reference)
   - `DoneEvidence` — Composite evidence required for done transitions

   #### Transition Models
   - `ForceMetadata` — Actor and reason for forced transitions
   - `StatusTransitionPayload` — Immutable payload for lane transitions with cross-field validation

   #### Validation
   - `TransitionValidationResult` — Result type for transition validation (valid, violations)
   - `validate_transition()` — Pre-flight transition legality check against PRD state machine
   - `TransitionError` — Exception for consumers who want to raise on invalid transitions

   #### Ordering and Reduction
   - `status_event_sort_key()` — Deterministic sort key: (lamport_clock, timestamp, event_id)
   - `dedup_events()` — Remove duplicate events by event_id
   - `reduce_status_events()` — Pure reference reducer with rollback-aware precedence
   - `WPState` — Per-WP reduced state (current_lane, last_event_id, evidence)
   - `TransitionAnomaly` — Record of invalid transition encountered during reduction
   - `ReducedStatus` — Reducer output (wp_states, anomalies, event_count)

   #### Constants
   - `TERMINAL_LANES` — frozenset of terminal lanes (done, canceled)
   - `LANE_ALIASES` — Legacy alias map (doing -> in_progress)
   - `WP_STATUS_CHANGED` — Canonical event_type string

   ### Key Features
   - **Lane alias normalization**: Legacy `doing` accepted on input, normalized to `in_progress`
   - **Data-driven transition matrix**: All legal transitions encoded as data, not branching logic
   - **Rollback-aware reducer**: Reviewer rollback outranks concurrent forward progression (PRD §9.2)
   - **Pure functions**: Reducer has no I/O, no side effects, deterministic output

   ### Backward Compatibility
   - Zero changes to existing modules or exports
   - All v0.2.0 tests pass without modification
   - 21 new exports added alongside existing 37 (total: 58)

   ### Graduation Criteria (alpha → stable)
   - 2+ consumers integrated (spec-kitty CLI and spec-kitty-saas)
   - All property tests green for 30+ days in CI
   - No breaking API changes needed after consumer integration
   - Transition matrix validated against real-world workflow data

   ### Consumer Integration
   See `kitty-specs/003-status-state-model-contracts/plan.md` for detailed integration checklists
   for spec-kitty CLI and spec-kitty-saas.
   ```

3. Replace `2026-02-XX` with the actual release date.

**Files**: `CHANGELOG.md`
**Parallel?**: Independent of T019.

### Subtask T021 – Verify all existing tests pass unchanged

**Purpose**: Prove zero regressions. The entire existing test suite must pass without any modifications.

**Steps**:

1. Run the full test suite:
   ```bash
   python3.11 -m pytest tests/ -v
   ```

2. Verify:
   - All existing unit tests pass (test_models, test_clock, test_conflict, test_topology, test_crdt, test_merge, test_storage, test_error_log, test_gates)
   - All existing property tests pass (test_determinism, test_crdt_laws, test_gates_determinism)
   - All existing integration tests pass
   - All NEW tests pass (test_status, test_status_determinism)

3. Check coverage report:
   ```bash
   python3.11 -m pytest tests/ --cov=src/spec_kitty_events --cov-report=term-missing
   ```
   Verify status.py has high coverage.

4. If any existing test fails, **do NOT modify the existing test**. Fix the issue in the new code instead.

**Files**: None (verification only)
**Parallel?**: Can run alongside T022.

### Subtask T022 – Run mypy --strict on entire codebase

**Purpose**: Verify strict type safety across all modules.

**Steps**:

1. Run:
   ```bash
   python3.11 -m mypy --strict src/spec_kitty_events/
   ```

2. Verify zero errors. Common issues to watch for:
   - Missing type annotations on lambda expressions
   - `Tuple` vs `tuple` (use `Tuple` from typing for 3.10 compat)
   - `Dict` vs `dict` (use `Dict` from typing for 3.10 compat)
   - `FrozenSet` vs `frozenset` (use `FrozenSet` from typing for 3.10 compat)
   - Pydantic validator return types

3. If errors found, fix them without changing existing module code.

**Files**: Various (fix type issues if found)
**Parallel?**: Can run alongside T021.

### Subtask T023 – Verify consumer integration checklists

**Purpose**: Ensure the integration checklists in plan.md are accurate based on the actual implemented API.

**Steps**:

1. Read `kitty-specs/003-status-state-model-contracts/plan.md` — Consumer Integration Checklists section.

2. Verify each checklist item against the actual API:
   - Import paths are correct
   - Function signatures match
   - Model names match
   - Version constraint `>=0.3.0a0` is the correct PEP 440 pre-release format

3. Spot-check by running quick import tests:
   ```python
   python3.11 -c "
   from spec_kitty_events import (
       Lane, ExecutionMode, StatusTransitionPayload,
       validate_transition, reduce_status_events,
       normalize_lane, DoneEvidence, RepoEvidence,
       VerificationEntry, ReviewVerdict,
       WPState, ReducedStatus, TransitionAnomaly,
       TERMINAL_LANES, LANE_ALIASES, WP_STATUS_CHANGED,
   )
   print(f'All {len([Lane, ExecutionMode, StatusTransitionPayload])}+ imports OK')
   print(f'Version: {__import__(\"spec_kitty_events\").__version__}')
   "
   ```

4. If any checklist item is inaccurate, update plan.md.

**Files**: `kitty-specs/003-status-state-model-contracts/plan.md` (edit if needed)
**Parallel?**: Depends on T019-T022 (code must be final).

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing test fails due to import side effects from new status.py | Run existing tests in isolation first to verify no import-time errors |
| mypy errors in new code discovered late | WP01-WP03 each verify mypy; T022 is a final sweep |
| CHANGELOG format inconsistent with existing entries | Follow exact format from v0.2.0-alpha entry |
| PEP 440 version string mismatch between pyproject.toml and consumers | Verify `0.3.0-alpha` in pyproject.toml maps to `0.3.0a0` in pip/PEP 440 |

## Review Guidance

- Verify version is bumped in BOTH pyproject.toml and __init__.py
- Verify CHANGELOG lists all 21 new exports
- Verify graduation criteria are documented
- Verify `python3.11 -m pytest tests/ -v` shows zero failures
- Verify `python3.11 -m mypy --strict src/spec_kitty_events/` shows zero errors
- Verify consumer checklist import paths match actual API

## Activity Log

- 2026-02-08T00:00:00Z – system – lane=planned – Prompt created.
