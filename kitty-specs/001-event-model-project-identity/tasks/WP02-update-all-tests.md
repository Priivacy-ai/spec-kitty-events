---
work_package_id: WP02
title: Update All Tests
lane: "doing"
dependencies: [WP01]
base_branch: 001-event-model-project-identity-WP01
base_commit: 517c99c138c27cc72fe7e59ad175e59524de0344
created_at: '2026-02-07T07:04:41.398627+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Implementation
assignee: ''
agent: "claude-opus"
shell_pid: "27795"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-07T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Update All Tests

## Important: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **Mark as acknowledged**: When you understand feedback and begin addressing it, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- All existing tests pass with the new required `project_uuid` field.
- New validation tests cover: valid UUID, invalid UUID, empty string, missing field, `project_slug` presence/absence, immutability.
- `pytest` runs with 0 failures and maintains 90%+ coverage.
- `mypy --strict` passes across all test files.

**Implementation command**: `spec-kitty implement WP02 --base WP01`

## Context & Constraints

- **Spec**: FR-008 (update existing tests), FR-009 (new validation tests)
- **Plan**: `kitty-specs/001-event-model-project-identity/plan.md` — Change Impact Analysis table shows all affected files.
- **WP01 must be complete**: The `Event` model must have `project_uuid` before tests can reference it.
- **Consistent test UUID**: Use `TEST_PROJECT_UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")` as a module-level constant in each test file. This keeps diffs minimal and grep-able.
- **Hypothesis tests**: For property-based tests, generate fresh UUIDs with `uuid.uuid4()` per test case (not a shared constant).

## Subtasks & Detailed Guidance

### Subtask T006 – Update test_models.py + add new validation tests

- **Purpose**: Fix existing model tests and add comprehensive validation coverage for project identity fields.
- **Steps**:
  1. Add `import uuid` at the top of `tests/unit/test_models.py`.
  2. Add module-level constant:
     ```python
     TEST_PROJECT_UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
     ```
  3. Add `project_uuid=TEST_PROJECT_UUID` to all 7 existing `Event()` calls in the file:
     - `test_event_creation_valid` (line ~16)
     - `test_event_validation_empty_event_type` (line ~31)
     - `test_event_validation_negative_lamport_clock` (line ~41)
     - `test_event_immutability` (line ~55)
     - `test_event_serialization` (line ~68)
     - `test_event_deserialization` (line ~82 — also add to the dict)
     - `test_conflict_resolution_creation` (lines ~136, ~144 — two Events)
  4. Add new tests to `TestEvent` class:

     ```python
     def test_event_project_uuid_required(self):
         """Test that project_uuid is required."""
         with pytest.raises(PydanticValidationError):
             Event(
                 event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                 event_type="TestEvent",
                 aggregate_id="AGG001",
                 timestamp=datetime.now(),
                 node_id="test-node",
                 lamport_clock=0,
                 # project_uuid intentionally omitted
             )

     def test_event_project_uuid_valid_string(self):
         """Test that project_uuid accepts a valid UUID string."""
         event = Event(
             event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
             event_type="TestEvent",
             aggregate_id="AGG001",
             timestamp=datetime.now(),
             node_id="test-node",
             lamport_clock=0,
             project_uuid="550e8400-e29b-41d4-a716-446655440000",
         )
         assert isinstance(event.project_uuid, uuid.UUID)

     def test_event_project_uuid_invalid_string(self):
         """Test that project_uuid rejects invalid UUID strings."""
         with pytest.raises(PydanticValidationError):
             Event(
                 event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                 event_type="TestEvent",
                 aggregate_id="AGG001",
                 timestamp=datetime.now(),
                 node_id="test-node",
                 lamport_clock=0,
                 project_uuid="not-a-uuid",
             )

     def test_event_project_uuid_empty_string(self):
         """Test that project_uuid rejects empty string."""
         with pytest.raises(PydanticValidationError):
             Event(
                 event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                 event_type="TestEvent",
                 aggregate_id="AGG001",
                 timestamp=datetime.now(),
                 node_id="test-node",
                 lamport_clock=0,
                 project_uuid="",
             )

     def test_event_project_slug_optional(self):
         """Test that project_slug defaults to None."""
         event = Event(
             event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
             event_type="TestEvent",
             aggregate_id="AGG001",
             timestamp=datetime.now(),
             node_id="test-node",
             lamport_clock=0,
             project_uuid=TEST_PROJECT_UUID,
         )
         assert event.project_slug is None

     def test_event_project_slug_with_value(self):
         """Test that project_slug accepts a string value."""
         event = Event(
             event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
             event_type="TestEvent",
             aggregate_id="AGG001",
             timestamp=datetime.now(),
             node_id="test-node",
             lamport_clock=0,
             project_uuid=TEST_PROJECT_UUID,
             project_slug="my-project",
         )
         assert event.project_slug == "my-project"

     def test_event_project_uuid_immutable(self):
         """Test that project_uuid cannot be changed after creation."""
         event = Event(
             event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
             event_type="TestEvent",
             aggregate_id="AGG001",
             timestamp=datetime.now(),
             node_id="test-node",
             lamport_clock=0,
             project_uuid=TEST_PROJECT_UUID,
         )
         with pytest.raises(Exception):
             setattr(event, "project_uuid", uuid.uuid4())

     def test_event_serialization_with_project_identity(self):
         """Test serialization includes project identity fields."""
         event = Event(
             event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
             event_type="TestEvent",
             aggregate_id="AGG001",
             timestamp=datetime(2026, 1, 26, 10, 0, 0),
             node_id="test-node",
             lamport_clock=5,
             project_uuid=TEST_PROJECT_UUID,
             project_slug="test-project",
         )
         data = event.to_dict()
         assert data["project_uuid"] == TEST_PROJECT_UUID
         assert data["project_slug"] == "test-project"

     def test_event_deserialization_with_project_identity(self):
         """Test deserialization restores project identity fields."""
         data = {
             "event_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
             "event_type": "TestEvent",
             "aggregate_id": "AGG001",
             "payload": {},
             "timestamp": datetime(2026, 1, 26, 10, 0, 0),
             "node_id": "test-node",
             "lamport_clock": 5,
             "causation_id": None,
             "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
             "project_slug": "test-project",
         }
         event = Event.from_dict(data)
         assert isinstance(event.project_uuid, uuid.UUID)
         assert str(event.project_uuid) == "550e8400-e29b-41d4-a716-446655440000"
         assert event.project_slug == "test-project"
     ```

- **Files**: `tests/unit/test_models.py`
- **Parallel?**: Yes — independent of other test files.
- **Notes**: The deserialization test verifies string → UUID coercion via `from_dict()`.

### Subtask T007 – Update test_conflict.py (25 calls)

- **Purpose**: Fix all 25 `Event()` calls in conflict detection tests.
- **Steps**:
  1. Add `import uuid` at the top.
  2. Add `TEST_PROJECT_UUID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")` as module constant.
  3. Add `project_uuid=TEST_PROJECT_UUID` to every `Event()` constructor in the file.
  4. This is mechanical — find each `Event(` and add the parameter.
- **Files**: `tests/unit/test_conflict.py`
- **Parallel?**: Yes.
- **Notes**: 25 call sites. Be thorough — `pytest tests/unit/test_conflict.py` should pass with 0 failures after changes.

### Subtask T008 – Update test_merge.py (17 calls)

- **Purpose**: Fix all 17 `Event()` calls in merge tests.
- **Steps**:
  1. Add `import uuid` and `TEST_PROJECT_UUID` constant.
  2. Add `project_uuid=TEST_PROJECT_UUID` to every `Event()` constructor.
- **Files**: `tests/unit/test_merge.py`
- **Parallel?**: Yes.
- **Notes**: 17 call sites. Run `pytest tests/unit/test_merge.py` to verify.

### Subtask T009 – Update test_crdt.py (10 calls)

- **Purpose**: Fix all 10 `Event()` calls in CRDT tests.
- **Steps**:
  1. Add `import uuid` and `TEST_PROJECT_UUID` constant.
  2. Add `project_uuid=TEST_PROJECT_UUID` to every `Event()` constructor.
- **Files**: `tests/unit/test_crdt.py`
- **Parallel?**: Yes.
- **Notes**: 10 call sites.

### Subtask T010 – Update test_storage.py (6 calls)

- **Purpose**: Fix all 6 `Event()` calls in storage adapter tests.
- **Steps**:
  1. Add `import uuid` and `TEST_PROJECT_UUID` constant.
  2. Add `project_uuid=TEST_PROJECT_UUID` to every `Event()` constructor.
- **Files**: `tests/unit/test_storage.py`
- **Parallel?**: Yes.
- **Notes**: 6 call sites.

### Subtask T011 – Update test_quickstart.py (11 calls)

- **Purpose**: Fix all 11 `Event()` calls in the quickstart integration tests. These tests validate README examples.
- **Steps**:
  1. Add `import uuid` and `TEST_PROJECT_UUID` constant.
  2. Add `project_uuid=TEST_PROJECT_UUID` to every `Event()` constructor.
  3. Pay special attention: these tests mirror README code. After WP03 updates the README, these tests should match.
- **Files**: `tests/integration/test_quickstart.py`
- **Parallel?**: Yes.
- **Notes**: 11 call sites. These are the most important integration tests — they validate documented examples work.

### Subtask T012 – Update remaining test files (16 calls across 5 files)

- **Purpose**: Fix the remaining test files that construct Events.
- **Steps**:
  1. For each file below, add `import uuid`, `TEST_PROJECT_UUID` constant, and `project_uuid=TEST_PROJECT_UUID` to all `Event()` calls:

     | File | Event() calls |
     |------|:---:|
     | `tests/integration/test_conflict_resolution.py` | 7 |
     | `tests/integration/test_event_emission.py` | 4 |
     | `tests/integration/test_adapters.py` | 2 |
     | `tests/property/test_crdt_laws.py` | 2 |
     | `tests/property/test_determinism.py` | 1 |

  2. For **Hypothesis property-based tests** (`test_crdt_laws.py`, `test_determinism.py`):
     - Use `project_uuid=uuid.uuid4()` (fresh UUID per test case, not the shared constant).
     - This ensures property-based tests exercise UUID diversity.

- **Files**: 5 files listed above.
- **Parallel?**: Yes — all files are independent.
- **Notes**: Total 16 call sites across 5 files. The Hypothesis tests may construct Events inside `@given` strategies — ensure UUID is generated within the strategy.

## Test Strategy

After all subtasks complete, run the full test suite:

```bash
# Full test suite
pytest

# Type checking
mypy src/spec_kitty_events --strict

# Verify coverage
pytest --cov --cov-report=term-missing
```

**Expected results**:
- All existing tests pass (with `project_uuid` added).
- New validation tests pass (8+ new tests in test_models.py).
- 90%+ coverage maintained.
- mypy --strict passes.

## Risks & Mitigations

- **Risk**: Missing an `Event()` call site. **Mitigation**: `pytest` will catch it — missing required field causes immediate `ValidationError`.
- **Risk**: Hypothesis strategies break. **Mitigation**: Use `uuid.uuid4()` inside the strategy function, not as a fixture.
- **Risk**: Test count mismatch (plan says 25 calls in test_conflict.py but actual may differ). **Mitigation**: Use `grep -c "Event(" <file>` to verify before/after counts.

## Review Guidance

- Run `pytest` — zero failures required.
- Run `mypy src/spec_kitty_events --strict` — zero errors.
- Verify new tests in `test_models.py` cover: required field, string coercion, invalid UUID, empty string, slug optional, slug with value, immutability, serialization round-trip.
- Spot-check 2-3 test files to confirm `project_uuid=TEST_PROJECT_UUID` was added consistently.
- Verify Hypothesis tests use `uuid.uuid4()` (not shared constant).

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
- 2026-02-07T07:04:41Z – claude-opus – shell_pid=19707 – lane=doing – Assigned agent via workflow command
- 2026-02-07T07:15:26Z – claude-opus – shell_pid=19707 – lane=for_review – All 11 test files updated with project_uuid. 8 new validation tests added. 118 tests pass, 100% coverage.
- 2026-02-07T07:15:35Z – claude-opus – shell_pid=27795 – lane=doing – Started review via workflow command
