# Tasks: Status State Model Contracts

**Feature**: 003-status-state-model-contracts
**Date**: 2026-02-08
**Work Packages**: 4
**Total Subtasks**: 23

## Overview

| WP | Title | Subtasks | Priority | Dependencies | Est. Lines |
|----|-------|----------|----------|--------------|------------|
| WP01 | Enums, Evidence Models, and Public API | T001-T007 (7) | P1 | — | ~450 |
| WP02 | Transition Validation | T008-T012 (5) | P1 | WP01 | ~400 |
| WP03 | Ordering Primitives and Reference Reducer | T013-T018 (6) | P2 | WP01, WP02 | ~500 |
| WP04 | Version Bump, Changelog, and Backward Compat | T019-T023 (5) | P3 | WP01, WP02, WP03 | ~350 |

## Phase 1 — Foundation

### WP01: Enums, Evidence Models, and Public API

**Goal**: Create `src/spec_kitty_events/status.py` with all data types (Lane, ExecutionMode, evidence models, ForceMetadata, StatusTransitionPayload), constants, normalize_lane(), TransitionError, and wire up `__init__.py` exports. Full unit test coverage.

**Prompt**: `tasks/WP01-enums-evidence-models-public-api.md`

- [x] T001: Create status.py with Lane, ExecutionMode enums, constants, normalize_lane()
- [x] T002: Implement evidence models (RepoEvidence, VerificationEntry, ReviewVerdict, DoneEvidence)
- [x] T003: Implement ForceMetadata and StatusTransitionPayload with cross-field validators
- [x] T004: Add TransitionError exception class
- [x] T005: Update __init__.py with 21 new exports
- [x] T006: Write unit tests for enums, normalize_lane, evidence models, payload validators
- [x] T007: Run mypy --strict and verify zero errors

**Parallel opportunities**: T001 and T002 touch separate in-file sections. T006 can start as soon as T001-T004 land.
**Dependencies**: None (first WP).
**Risks**: `Lane(str, Enum)` + Pydantic v2 field validation interaction; mitigate by testing round-trip early.

---

### WP02: Transition Validation

**Goal**: Implement the transition matrix, TransitionValidationResult, and validate_transition() function with full guard conditions. Unit tests covering all legal transitions, all illegal combinations, and all guard conditions.

**Prompt**: `tasks/WP02-transition-validation.md`

**Dependencies**: WP01 (needs Lane, StatusTransitionPayload, constants)

- [x] T008: Implement transition matrix data structure and programmatic rules
- [x] T009: Implement TransitionValidationResult frozen dataclass
- [x] T010: Implement validate_transition() with full guard conditions
- [x] T011: Write unit tests for all legal and illegal transitions (full matrix)
- [x] T012: Write unit tests for guard conditions and force override

**Parallel opportunities**: T008+T009 are independent. T011 and T012 test different aspects.
**Dependencies**: WP01 must be merged to main first.
**Risks**: Transition matrix completeness; mitigate with exhaustive test that iterates all Lane x Lane combinations.

---

## Phase 2 — Ordering & Reduction

### WP03: Ordering Primitives and Reference Reducer

**Goal**: Implement status_event_sort_key(), dedup_events(), reducer output models (WPState, TransitionAnomaly, ReducedStatus), and reduce_status_events() with rollback-aware precedence. Unit tests + Hypothesis property tests for determinism.

**Prompt**: `tasks/WP03-ordering-primitives-reference-reducer.md`

**Dependencies**: WP01 (models), WP02 (validate_transition used internally by reducer)

- [ ] T013: Implement status_event_sort_key()
- [ ] T014: Implement dedup_events()
- [ ] T015: Implement WPState, TransitionAnomaly, ReducedStatus frozen models
- [ ] T016: Implement reduce_status_events() with rollback-aware precedence
- [ ] T017: Write unit tests for sort key, dedup, reducer (happy path, rollback, anomalies, empty)
- [ ] T018: Write property tests for determinism and dedup idempotency

**Parallel opportunities**: T013+T014 are independent helper functions. T015 is independent of T013-T014.
**Dependencies**: WP01 and WP02 must be merged to main first.
**Risks**: Rollback-aware precedence is the most subtle logic; mitigate with dedicated property test generating concurrent events with rollbacks.

---

## Phase 3 — Polish & Release

### WP04: Version Bump, Changelog, and Backward Compat

**Goal**: Bump to 0.3.0-alpha, write CHANGELOG with graduation criteria, verify all existing tests pass unchanged, full mypy --strict clean, finalize consumer integration checklists.

**Prompt**: `tasks/WP04-version-bump-changelog-backward-compat.md`

**Dependencies**: WP01, WP02, WP03 (all code must be complete and merged)

- [ ] T019: Bump version to 0.3.0-alpha in pyproject.toml and __init__.py
- [ ] T020: Write CHANGELOG.md entry with graduation criteria
- [ ] T021: Run full existing test suite and verify zero regressions
- [ ] T022: Run mypy --strict on entire codebase
- [ ] T023: Verify consumer integration checklists

**Parallel opportunities**: T019+T020 are independent edits. T021+T022 are independent verification steps.
**Dependencies**: WP01-WP03 must all be merged to main first.
**Risks**: Low — mostly verification and documentation. Only risk is a missed backward compat issue surfacing during T021.
