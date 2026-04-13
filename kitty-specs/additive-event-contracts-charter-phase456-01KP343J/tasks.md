# Tasks: Additive Event Contracts for Charter Phase 4/5/6

**Mission ID**: `01KP343JBG2V7WSWSDJ0HD76BR`
**Date**: 2026-04-13
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Create profile_invocation.py module skeleton with constants and type set | WP01 | [P] | [D] |
| T002 | Implement ProfileInvocationStartedPayload with all fields | WP01 | | [D] |
| T003 | Define reserved constants for COMPLETED and FAILED | WP01 | | [D] |
| T004 | Create unit tests for profile invocation payload models | WP01 | | [D] |
| T005 | Verify mypy --strict passes on profile_invocation.py | WP01 | | [D] |
| T006 | Create retrospective.py module skeleton with constants and type set | WP02 | [D] |
| T007 | Implement RetrospectiveCompletedPayload with ProvenanceRef | WP02 | | [D] |
| T008 | Implement RetrospectiveSkippedPayload with trigger_source Literal | WP02 | | [D] |
| T009 | Create unit tests for retrospective payload models | WP02 | | [D] |
| T010 | Verify mypy --strict passes on retrospective.py | WP02 | | [D] |
| T011 | Add new categories to _VALID_CATEGORIES in loader.py | WP03 | | [D] |
| T012 | Create profile_invocation fixture JSON files (2 valid, 2 invalid) | WP03 | [D] |
| T013 | Create retrospective fixture JSON files (3 valid, 2 invalid) | WP03 | [D] |
| T014 | Register all 9 fixtures in manifest.json | WP03 | | [D] |
| T015 | Create conformance test for profile invocation fixtures | WP03 | [D] |
| T016 | Create conformance test for retrospective fixtures | WP03 | [D] |
| T017 | Register new types in validators.py dispatch maps | WP04 | |
| T018 | Add imports, exports, and __version__ bump in __init__.py | WP04 | |
| T019 | Bump pyproject.toml version to 3.1.0 | WP04 | |
| T020 | Run schema generation and commit new JSON schemas | WP04 | |
| T021 | Run full test suite and validate all gates pass | WP04 | |

## Dependency Graph

```
WP01 ─────┐
           ├──> WP03 ──> WP04
WP02 ─────┘
```

## Work Packages

### WP01: Profile Invocation Domain + Unit Tests

**Prompt**: [tasks/WP01-profile-invocation-domain.md](tasks/WP01-profile-invocation-domain.md)
**Priority**: High (foundation, parallel with WP02)
**Dependencies**: None
**Estimated prompt size**: ~350 lines

**Subtasks**:
- [x] T001 Create profile_invocation.py module skeleton with constants and type set (WP01)
- [x] T002 Implement ProfileInvocationStartedPayload with all fields (WP01)
- [x] T003 Define reserved constants for COMPLETED and FAILED (WP01)
- [x] T004 Create unit tests for profile invocation payload models (WP01)
- [x] T005 Verify mypy --strict passes on profile_invocation.py (WP01)

**Success criteria**: Module exists, payload validates, reserved constants present, all unit tests pass, mypy clean.

---

### WP02: Retrospective Domain + Unit Tests

**Prompt**: [tasks/WP02-retrospective-domain.md](tasks/WP02-retrospective-domain.md)
**Priority**: High (foundation, parallel with WP01)
**Dependencies**: None
**Estimated prompt size**: ~400 lines

**Subtasks**:
- [x] T006 Create retrospective.py module skeleton with constants and type set (WP02)
- [x] T007 Implement RetrospectiveCompletedPayload with ProvenanceRef (WP02)
- [x] T008 Implement RetrospectiveSkippedPayload with trigger_source Literal (WP02)
- [x] T009 Create unit tests for retrospective payload models (WP02)
- [x] T010 Verify mypy --strict passes on retrospective.py (WP02)

**Success criteria**: Module exists, both payloads validate, trigger_source Literal enforced, ProvenanceRef embedding works, all unit tests pass, mypy clean.

---

### WP03: Shared Conformance + Fixture Integration

**Prompt**: [tasks/WP03-conformance-fixtures.md](tasks/WP03-conformance-fixtures.md)
**Priority**: Medium (depends on WP01 + WP02)
**Dependencies**: WP01, WP02
**Estimated prompt size**: ~450 lines

**Subtasks**:
- [x] T011 Add new categories to _VALID_CATEGORIES in loader.py (WP03)
- [x] T012 Create profile_invocation fixture JSON files (2 valid, 2 invalid) (WP03)
- [x] T013 Create retrospective fixture JSON files (3 valid, 2 invalid) (WP03)
- [x] T014 Register all 9 fixtures in manifest.json (WP03)
- [x] T015 Create conformance test for profile invocation fixtures (WP03)
- [x] T016 Create conformance test for retrospective fixtures (WP03)

**Success criteria**: Loader accepts new categories, all fixtures load without error, conformance tests pass via direct model validation, invalid fixtures produce expected violations.

---

### WP04: Package Integration + Schema + Version Bump

**Prompt**: [tasks/WP04-package-integration.md](tasks/WP04-package-integration.md)
**Priority**: Medium (final integration, depends on WP03)
**Dependencies**: WP03
**Estimated prompt size**: ~350 lines

**Subtasks**:
- [ ] T017 Register new types in validators.py dispatch maps (WP04)
- [ ] T018 Add imports, exports, and __version__ bump in __init__.py (WP04)
- [ ] T019 Bump pyproject.toml version to 3.1.0 (WP04)
- [ ] T020 Run schema generation and commit new JSON schemas (WP04)
- [ ] T021 Run full test suite and validate all gates pass (WP04)

**Success criteria**: validate_event() dispatches for all 3 new types, package imports work, both version surfaces read "3.1.0", schema generation has zero drift, full pytest + mypy pass.

---

## Parallelization Summary

- **Lane A**: WP01 → WP03 → WP04
- **Lane B**: WP02 (merges into Lane A before WP03)

WP01 and WP02 are fully independent and can execute in parallel. WP03 and WP04 are sequential.

## MVP Scope

WP01 + WP02 deliver the core contract surfaces. WP03 + WP04 deliver integration and release readiness. All 4 WPs are required for a shippable release.
