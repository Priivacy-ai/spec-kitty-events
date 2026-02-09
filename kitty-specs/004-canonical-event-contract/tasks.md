# Tasks: Canonical Event Contract Consolidation

**Feature**: 004-canonical-event-contract
**Created**: 2026-02-09
**Work Packages**: 4
**Total Subtasks**: 26

## Work Package Summary

| WP | Title | Subtasks | Priority | Dependencies | Est. Lines |
|----|-------|----------|----------|--------------|------------|
| WP01 | Event Envelope Extension + Test Migration | T001-T007 (7) | P1 | None | ~450 |
| WP02 | Lifecycle Payload Models | T008-T013 (6) | P1 | WP01 | ~400 |
| WP03 | Lifecycle Reducer + Precedence Rules | T014-T020 (7) | P1 | WP02 | ~500 |
| WP04 | Exports + Version Bump + Integration Tests | T021-T026 (6) | P2 | WP03 | ~350 |

## Dependency Graph

```
WP01 (envelope) → WP02 (payloads) → WP03 (reducer) → WP04 (exports + version)
```

All WPs are sequential — each builds on the previous. WP01 must land first because the new required `correlation_id` field breaks all existing tests.

---

## WP01: Event Envelope Extension + Test Migration

**Goal**: Add correlation_id, schema_version, and data_tier fields to the Event model and update all existing tests to pass with the new required field.

**Priority**: P1 (foundation — everything depends on this)
**Dependencies**: None
**Prompt**: `tasks/WP01-event-envelope-extension.md`
**Estimated prompt size**: ~450 lines

**Subtasks**:

- [x] T001: Add correlation_id, schema_version, data_tier fields to Event model in `src/spec_kitty_events/models.py`
- [x] T002: Create test helper function in `tests/conftest.py` for constructing Event objects with sensible defaults for new fields
- [x] T003: Update unit test files (7 files, ~78 Event() calls): test_conflict.py, test_merge.py, test_models.py, test_crdt.py, test_storage.py, test_status.py, test_gates.py
- [x] T004: Update integration test files (4 files, ~24 Event() calls): test_quickstart.py, test_conflict_resolution.py, test_event_emission.py, test_adapters.py
- [x] T005: Update property test files (3 files, ~4 Event() calls): test_crdt_laws.py, test_determinism.py, test_status_determinism.py
- [x] T006: Update docstring examples in source modules: merge.py, crdt.py, conflict.py, topology.py
- [x] T007: Add unit tests for new Event fields: correlation_id validation, schema_version pattern validation, data_tier range validation, default values, round-trip serialization

**Parallel opportunities**: T003/T004/T005 can be done in parallel (different files). T006 is independent of test updates.

**Risks**: Missing an Event() construction site causes test failure. Use comprehensive grep to find all sites.

---

## WP02: Lifecycle Payload Models

**Goal**: Create the `lifecycle.py` module with all mission-level event type constants, MissionStatus enum, and typed payload models for all lifecycle event types.

**Priority**: P1 (contract surface)
**Dependencies**: WP01
**Prompt**: `tasks/WP02-lifecycle-payload-models.md`
**Estimated prompt size**: ~400 lines

**Subtasks**:

- [ ] T008: Create `src/spec_kitty_events/lifecycle.py` with module docstring and section structure
- [ ] T009: Implement MissionStatus enum (str, Enum) with ACTIVE, COMPLETED, CANCELLED + TERMINAL_MISSION_STATUSES frozenset
- [ ] T010: Implement SCHEMA_VERSION constant and event type string constants (MISSION_STARTED, MISSION_COMPLETED, MISSION_CANCELLED, PHASE_ENTERED, REVIEW_ROLLBACK) + MISSION_EVENT_TYPES frozenset
- [ ] T011: Implement MissionStartedPayload and MissionCompletedPayload frozen models
- [ ] T012: Implement MissionCancelledPayload, PhaseEnteredPayload, and ReviewRollbackPayload frozen models
- [ ] T013: Add comprehensive unit tests in `tests/unit/test_lifecycle.py`: valid construction, missing required fields, field validation, round-trip serialization, frozen enforcement

**Parallel opportunities**: T011 and T012 can be done in parallel (different models). T013 can start once T009-T012 land.

**Risks**: Pydantic v2 `(str, Enum)` pattern must match the existing `Lane` enum from Feature 003.

---

## WP03: Lifecycle Reducer + Precedence Rules

**Goal**: Implement the lifecycle reducer function with cancel-beats-re-open precedence, rollback handling, and all three test fixtures (F-Reducer-001, F-Reducer-002, F-Reducer-003).

**Priority**: P1 (core acceptance criteria 2E-03 through 2E-06)
**Dependencies**: WP02
**Prompt**: `tasks/WP03-lifecycle-reducer.md`
**Estimated prompt size**: ~500 lines

**Subtasks**:

- [ ] T014: Implement LifecycleAnomaly and ReducedMissionState frozen models in lifecycle.py
- [ ] T015: Implement reduce_lifecycle_events() core pipeline: sort → dedup → partition → reduce mission events → delegate WP events → merge
- [ ] T016: Implement cancel-beats-re-open precedence within concurrent event groups (F-Reducer-001)
- [ ] T017: Implement rollback handling: ReviewRollback updates current_phase, never overwrites events (F-Reducer-002)
- [ ] T018: Verify idempotent dedup via existing dedup_events() reuse (F-Reducer-003)
- [ ] T019: Add unit tests for reducer: empty sequence, single event, full mission lifecycle, anomaly detection, all 3 fixture scenarios
- [ ] T020: Add property tests in `tests/property/test_lifecycle_determinism.py`: reducer determinism across 100 random physical orderings

**Parallel opportunities**: T016/T017/T018 are independent precedence implementations. T019/T020 can start once T015 lands.

**Risks**: Composition with reduce_status_events() requires WP status events to be filtered correctly. Test with mixed event types.

---

## WP04: Exports + Version Bump + Integration Tests

**Goal**: Wire up all new exports in __init__.py, bump version to 0.4.0-alpha, add integration tests for projection replay, and verify quality gates (mypy, coverage).

**Priority**: P2 (polish and release readiness)
**Dependencies**: WP03
**Prompt**: `tasks/WP04-exports-version-integration.md`
**Estimated prompt size**: ~350 lines

**Subtasks**:

- [ ] T021: Add all 17 new exports to `src/spec_kitty_events/__init__.py` and update `__all__`
- [ ] T022: Bump version to 0.4.0-alpha in pyproject.toml and __init__.py
- [ ] T023: Add integration tests for projection replay correctness (acceptance criteria 2E-07, 2E-08): build projection incrementally vs from-scratch replay, assert identical output
- [ ] T024: Verify mypy --strict passes on all new and modified files
- [ ] T025: Verify test coverage remains at 99%+ with `python3.11 -m pytest`
- [ ] T026: Run full test suite, verify all existing tests still pass (backward compat), fix any remaining issues

**Parallel opportunities**: T021/T022 are independent file edits. T024/T025/T026 are sequential verification steps.

**Risks**: Coverage may drop if lifecycle.py has untested branches. Add targeted tests for edge cases.

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: for_review
<!-- status-model:end -->
