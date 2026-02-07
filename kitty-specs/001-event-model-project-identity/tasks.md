# Work Packages: Event Model Project Identity

**Inputs**: Design documents from `kitty-specs/001-event-model-project-identity/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md

**Tests**: Test updates are required (existing tests break without `project_uuid`; new validation tests needed per spec FR-008/FR-009).

**Organization**: 12 subtasks (`T001`–`T012`) roll up into 3 work packages (`WP01`–`WP03`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: Core Model & Version Bump (Priority: P0) 🎯 MVP

**Goal**: Add `project_uuid` and `project_slug` fields to the `Event` model, update serialization methods, and bump library version.
**Independent Test**: `Event(project_uuid=uuid.uuid4(), ...)` succeeds; `Event()` without `project_uuid` raises `ValidationError`; `to_dict()` / `from_dict()` round-trip preserves both fields.
**Prompt**: `tasks/WP01-core-model-and-version-bump.md`
**Estimated prompt size**: ~350 lines

### Included Subtasks
- [x] T001 Add `project_uuid: uuid.UUID` (required) and `project_slug: Optional[str]` (optional) fields to `Event` in `src/spec_kitty_events/models.py`
- [x] T002 Update `Event.to_dict()` to include new fields via `model_dump()`
- [x] T003 Update `Event.from_dict()` to accept new fields (Pydantic coercion handles UUID string → UUID)
- [x] T004 Update `Event.__repr__()` to include `project_uuid` (truncated)
- [x] T005 Bump version from `0.1.0-alpha` to `0.1.1-alpha` in `pyproject.toml` and `src/spec_kitty_events/__init__.py`

### Implementation Notes
- Pydantic v2 natively supports `uuid.UUID` — accepts string input, stores as UUID, serializes via `model_dump()`.
- `to_dict()` currently calls `self.model_dump()` which returns Python-native types (datetime as datetime, UUID as UUID). This is consistent — don't switch to `mode='json'`.
- `from_dict()` calls `cls(**data)` which lets Pydantic coerce string → UUID.
- The model is `frozen=True` — new fields inherit immutability automatically.

### Parallel Opportunities
- T005 (version bump) can proceed in parallel with T001–T004.

### Dependencies
- None (starting package).

### Risks & Mitigations
- **Risk**: `model_dump()` behavior change with UUID fields. **Mitigation**: Pydantic v2 returns `uuid.UUID` object in Python mode, which is consistent with how `datetime` is returned.
- **Risk**: mypy --strict compliance. **Mitigation**: `uuid.UUID` is fully typed in stdlib; `Optional[str]` is straightforward.

---

## Work Package WP02: Update All Tests (Priority: P1)

**Goal**: Add `project_uuid` parameter to all existing `Event()` calls across 10 test files (~86 call sites) and add new validation tests for `project_uuid`.
**Independent Test**: `pytest` passes with 0 failures; mypy --strict passes; new tests cover valid UUID, invalid UUID, missing UUID, and slug scenarios.
**Prompt**: `tasks/WP02-update-all-tests.md`
**Estimated prompt size**: ~500 lines

### Included Subtasks
- [ ] T006 [P] Update `tests/unit/test_models.py` — add `project_uuid` to all 7 `Event()` calls + add new validation tests for project_uuid/project_slug
- [ ] T007 [P] Update `tests/unit/test_conflict.py` — add `project_uuid` to all 25 `Event()` calls
- [ ] T008 [P] Update `tests/unit/test_merge.py` — add `project_uuid` to all 17 `Event()` calls
- [ ] T009 [P] Update `tests/unit/test_crdt.py` — add `project_uuid` to all 10 `Event()` calls
- [ ] T010 [P] Update `tests/unit/test_storage.py` — add `project_uuid` to all 6 `Event()` calls
- [ ] T011 [P] Update `tests/integration/test_quickstart.py` — add `project_uuid` to all 11 `Event()` calls
- [ ] T012 [P] Update remaining test files — `test_conflict_resolution.py` (7), `test_event_emission.py` (4), `test_adapters.py` (2), `test_crdt_laws.py` (2), `test_determinism.py` (1)

### Implementation Notes
- Use a consistent test UUID across files: `TEST_PROJECT_UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")`.
- Add `import uuid` at the top of each test file.
- For Hypothesis property-based tests (`test_crdt_laws.py`, `test_determinism.py`), add `project_uuid=uuid.uuid4()` to the Event construction strategies.
- New tests in T006 should cover: valid UUID4 string, valid UUID object, malformed string, empty string, None, missing field, project_slug with value, project_slug omitted, immutability of project_uuid.

### Parallel Opportunities
- All subtasks T006–T012 are fully parallelizable — each touches different test files.

### Dependencies
- Depends on WP01 (model changes must exist before tests can reference new fields).

### Risks & Mitigations
- **Risk**: Missing an `Event()` call site. **Mitigation**: Run `pytest` after changes — any missed call will fail with "missing required argument: project_uuid".
- **Risk**: Hypothesis strategies need UUID generation. **Mitigation**: Use `uuid.uuid4()` in `@given` decorators or as fixture.

---

## Work Package WP03: Documentation & Changelog (Priority: P2)

**Goal**: Update README quickstart, API overview, CHANGELOG, and validate all documentation examples work against the updated library.
**Independent Test**: Copy README quickstart code into a Python script and run it — should execute without errors and produce an Event with `project_uuid`.
**Prompt**: `tasks/WP03-docs-and-changelog.md`
**Estimated prompt size**: ~250 lines

### Included Subtasks
- [ ] T013 Update README.md quickstart example to include `project_uuid` and `project_slug`
- [ ] T014 Update README.md API overview to list `project_uuid` and `project_slug` as Event fields
- [ ] T015 Update README.md version references from `0.1.0-alpha` to `0.1.1-alpha`
- [ ] T016 Add `0.1.1-alpha` entry to CHANGELOG.md documenting new project identity fields

### Implementation Notes
- The quickstart example in README.md creates an Event on line 63–72. Add `project_uuid` param with `import uuid` at top.
- API overview lists Event fields on line 115 — add `project_uuid` and `project_slug` descriptions.
- Installation references `v0.1.0-alpha` tag — update to `v0.1.1-alpha`.
- CHANGELOG entry should list: added `project_uuid` (required), added `project_slug` (optional), breaking change note.

### Parallel Opportunities
- T013–T015 (README sections) should be done sequentially to avoid conflicts in same file.
- T016 (CHANGELOG) can proceed in parallel with README updates.

### Dependencies
- Depends on WP01 (need model changes to validate examples work).
- Logically follows WP02 (all tests should pass before documenting).

### Risks & Mitigations
- **Risk**: README examples diverge from actual API. **Mitigation**: Run quickstart code against installed library after changes.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03
- **Parallelization**: WP02 subtasks (T006–T012) are all parallel-safe. WP03 T016 can run alongside T013–T015.
- **MVP Scope**: WP01 is the minimal release — the model change is the core deliverable. WP02 is required for CI to pass. WP03 is documentation polish.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Add project_uuid and project_slug fields to Event | WP01 | P0 | No |
| T002 | Update Event.to_dict() for new fields | WP01 | P0 | No |
| T003 | Update Event.from_dict() for new fields | WP01 | P0 | No |
| T004 | Update Event.__repr__() for project_uuid | WP01 | P0 | No |
| T005 | Bump version to 0.1.1-alpha | WP01 | P0 | Yes |
| T006 | Update test_models.py + add validation tests | WP02 | P1 | Yes |
| T007 | Update test_conflict.py (25 calls) | WP02 | P1 | Yes |
| T008 | Update test_merge.py (17 calls) | WP02 | P1 | Yes |
| T009 | Update test_crdt.py (10 calls) | WP02 | P1 | Yes |
| T010 | Update test_storage.py (6 calls) | WP02 | P1 | Yes |
| T011 | Update test_quickstart.py (11 calls) | WP02 | P1 | Yes |
| T012 | Update remaining test files (16 calls) | WP02 | P1 | Yes |
| T013 | Update README quickstart example | WP03 | P2 | No |
| T014 | Update README API overview | WP03 | P2 | No |
| T015 | Update README version references | WP03 | P2 | No |
| T016 | Add CHANGELOG 0.1.1-alpha entry | WP03 | P2 | Yes |
