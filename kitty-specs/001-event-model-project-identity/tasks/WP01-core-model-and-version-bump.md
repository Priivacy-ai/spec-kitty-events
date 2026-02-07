---
work_package_id: WP01
title: Core Model & Version Bump
lane: "doing"
dependencies: []
base_branch: main
base_commit: 26692accdfc21c2cb56ff84a728e8c1e87d45e46
created_at: '2026-02-07T07:01:58.458299+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 0 - Foundation
assignee: ''
agent: ''
shell_pid: "18753"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-07T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Core Model & Version Bump

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

- Add `project_uuid: uuid.UUID` (required) and `project_slug: Optional[str]` (optional, default `None`) to the `Event` model.
- Serialization via `to_dict()` and deserialization via `from_dict()` must round-trip both fields.
- `project_uuid` validation rejects malformed UUIDs.
- Version bumped from `0.1.0-alpha` to `0.1.1-alpha`.
- `mypy --strict` passes with zero errors.

**Implementation command**: `spec-kitty implement WP01`

## Context & Constraints

- **Spec**: `kitty-specs/001-event-model-project-identity/spec.md` (FR-001 through FR-006, FR-010)
- **Plan**: `kitty-specs/001-event-model-project-identity/plan.md`
- **Data model**: `kitty-specs/001-event-model-project-identity/data-model.md`
- **Research**: `kitty-specs/001-event-model-project-identity/research.md` (Decision 1: uuid.UUID, Decision 4: serialization)
- **Key constraint**: Model is `frozen=True` (Pydantic). New fields inherit immutability.
- **Key constraint**: `to_dict()` uses `model_dump()` (Python mode, not JSON mode). UUID returns as `uuid.UUID` object in dict. This is consistent with how `datetime` is returned.
- **No backward compatibility**: `project_uuid` is required. Events without it will fail validation.

## Subtasks & Detailed Guidance

### Subtask T001 – Add project_uuid and project_slug fields to Event

- **Purpose**: Core model change. Every event in the system must carry project identity.
- **Steps**:
  1. Open `src/spec_kitty_events/models.py`
  2. Add `import uuid` at the top of the file (alongside existing imports)
  3. Add two new fields to the `Event` class, after `causation_id`:

     ```python
     project_uuid: uuid.UUID = Field(
         ...,
         description="UUID of the project this event belongs to"
     )
     project_slug: Optional[str] = Field(
         None,
         description="Human-readable project identifier (optional)"
     )
     ```

  4. `project_uuid` is required (`...` means no default). Pydantic v2 validates UUID format automatically — accepts both `uuid.UUID` objects and UUID-formatted strings.
  5. `project_slug` is optional with `None` default. No format validation — the CLI enforces slug format, not the library.

- **Files**: `src/spec_kitty_events/models.py`
- **Parallel?**: No — T002, T003, T004 depend on this.
- **Notes**: Pydantic v2 `uuid.UUID` support means no custom validator needed. String inputs are coerced to `uuid.UUID` automatically.

### Subtask T002 – Update Event.to_dict() for new fields

- **Purpose**: Ensure serialized events include project identity for transport.
- **Steps**:
  1. The current `to_dict()` is simply `return self.model_dump()`. Pydantic v2 `model_dump()` automatically includes all model fields, so **no code change is needed for `to_dict()` itself**.
  2. Verify that `model_dump()` returns `project_uuid` as a `uuid.UUID` object (Python mode behavior). This is correct — matches how `datetime` is handled.
  3. If you want to confirm: create a quick Event with project_uuid, call `to_dict()`, and check the output type.

- **Files**: `src/spec_kitty_events/models.py` (verify, likely no change needed)
- **Parallel?**: No — depends on T001.
- **Notes**: `model_dump()` in Python mode returns native types. `model_dump(mode='json')` would return strings. We use Python mode (existing behavior).

### Subtask T003 – Update Event.from_dict() for new fields

- **Purpose**: Ensure deserialized events reconstruct project identity.
- **Steps**:
  1. The current `from_dict()` is simply `return cls(**data)`. Pydantic v2 coerces string → `uuid.UUID` automatically, so **no code change is needed for `from_dict()` itself**.
  2. Verify that passing `{"project_uuid": "550e8400-e29b-41d4-a716-446655440000", ...}` results in `event.project_uuid` being a `uuid.UUID` instance.

- **Files**: `src/spec_kitty_events/models.py` (verify, likely no change needed)
- **Parallel?**: No — depends on T001.
- **Notes**: If `project_uuid` is missing from the dict, Pydantic will raise `ValidationError` (expected — it's required).

### Subtask T004 – Update Event.__repr__() for project_uuid

- **Purpose**: Human-readable output should include project identity for debugging.
- **Steps**:
  1. Update `__repr__` in `Event` class to include project_uuid (truncated for readability):

     ```python
     def __repr__(self) -> str:
         """Human-readable representation."""
         return (
             f"Event(event_id={self.event_id[:8]}..., "
             f"type={self.event_type}, "
             f"aggregate={self.aggregate_id}, "
             f"project={str(self.project_uuid)[:8]}..., "
             f"lamport={self.lamport_clock})"
         )
     ```

  2. Show first 8 chars of UUID string for brevity, matching the `event_id` truncation pattern.

- **Files**: `src/spec_kitty_events/models.py`
- **Parallel?**: No — depends on T001.
- **Notes**: This is a display-only change. Does not affect serialization or behavior.

### Subtask T005 – Bump version to 0.1.1-alpha

- **Purpose**: Signal new release with project identity fields.
- **Steps**:
  1. In `pyproject.toml`, change line 3:
     ```toml
     version = "0.1.1-alpha"
     ```
  2. In `src/spec_kitty_events/__init__.py`, change line 16:
     ```python
     __version__ = "0.1.1-alpha"
     ```
  3. Ensure both files have the same version string.

- **Files**: `pyproject.toml`, `src/spec_kitty_events/__init__.py`
- **Parallel?**: Yes — independent of T001–T004.
- **Notes**: Two files to update. Both must match.

## Test Strategy

After completing all subtasks, verify:
```bash
# Type checking must pass
mypy src/spec_kitty_events --strict

# Import and basic creation should work (tests in WP02)
python -c "
import uuid
from spec_kitty_events import Event
from datetime import datetime
e = Event(
    event_id='01ARZ3NDEKTSV4RRFFQ69G5FAV',
    event_type='Test',
    aggregate_id='AGG001',
    timestamp=datetime.now(),
    node_id='test',
    lamport_clock=0,
    project_uuid=uuid.uuid4()
)
print(e)
print(e.to_dict())
print('OK')
"
```

Note: `pytest` will FAIL after this WP because existing tests don't supply `project_uuid` yet. That's expected — WP02 fixes all tests.

## Risks & Mitigations

- **Risk**: mypy --strict fails on `uuid.UUID` usage. **Mitigation**: `uuid` module is fully typed in Python 3.10+; Pydantic v2 type stubs support it.
- **Risk**: `model_dump()` changes behavior with UUID field. **Mitigation**: Pydantic v2 documented behavior — UUID stays as UUID in Python mode.

## Review Guidance

- Verify `project_uuid` field is `uuid.UUID` type (not `str`).
- Verify `project_slug` defaults to `None` (not empty string).
- Verify `__repr__` truncates UUID consistently with event_id pattern.
- Verify version is `0.1.1-alpha` in both `pyproject.toml` and `__init__.py`.
- Run `mypy src/spec_kitty_events --strict` — must pass.
- Confirm `to_dict()` and `from_dict()` don't need code changes (Pydantic handles it).

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
