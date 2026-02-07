---
work_package_id: WP03
title: Documentation & Changelog
lane: "doing"
dependencies: [WP01]
base_branch: 001-event-model-project-identity-WP01
base_commit: 517c99c138c27cc72fe7e59ad175e59524de0344
created_at: '2026-02-07T07:04:43.015763+00:00'
subtasks:
- T013
- T014
- T015
- T016
phase: Phase 2 - Polish
assignee: ''
agent: ''
shell_pid: "19778"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-07T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Documentation & Changelog

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

- README quickstart shows `project_uuid` in the Event creation example.
- README API overview lists `project_uuid` and `project_slug` as Event fields.
- README version references updated to `0.1.1-alpha`.
- CHANGELOG has a `0.1.1-alpha` entry documenting the project identity fields.
- README quickstart code executes without errors when copied verbatim.

**Implementation command**: `spec-kitty implement WP03 --base WP01`

## Context & Constraints

- **Spec**: FR-007 (README quickstart), SC-004 (examples execute successfully)
- **Quickstart reference**: `kitty-specs/001-event-model-project-identity/quickstart.md`
- **Current README**: 196 lines. Quickstart example at lines 47–73, API overview at lines 113–133.
- **Current CHANGELOG**: 76 lines. Latest entry is `0.1.0-alpha`.
- **Validation**: After changes, quickstart code must run against the library. This WP can be implemented after WP01 (model exists) and ideally after WP02 (tests pass).

## Subtasks & Detailed Guidance

### Subtask T013 – Update README quickstart example

- **Purpose**: Developers copying the quickstart must see and use `project_uuid`.
- **Steps**:
  1. Open `README.md`.
  2. In the "Basic Event Emission" section (lines ~47–73), update the example:
     - Add `import uuid` to the import block (line ~48).
     - Add `project_uuid=uuid.uuid4(),` to the `Event()` constructor (after `payload` or at end).
     - Optionally add `project_slug="my-project",` to show usage.
  3. The updated example should look like:

     ```python
     from datetime import datetime
     import uuid
     from spec_kitty_events import (
         Event,
         LamportClock,
         InMemoryClockStorage,
         InMemoryEventStore,
     )

     # Setup
     clock_storage = InMemoryClockStorage()
     event_store = InMemoryEventStore()
     clock = LamportClock(node_id="alice", storage=clock_storage)

     # Emit event
     clock.tick()
     event = Event(
         event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
         event_type="WPStatusChanged",
         aggregate_id="WP001",
         timestamp=datetime.now(),
         node_id="alice",
         lamport_clock=clock.current(),
         payload={"state": "doing"},
         project_uuid=uuid.uuid4(),
         project_slug="my-project",
     )
     event_store.save_event(event)
     ```

- **Files**: `README.md` (lines ~47–73)
- **Parallel?**: No — T014 and T015 also edit README.
- **Notes**: Keep the example minimal. `project_uuid=uuid.uuid4()` is the simplest way to show it. In practice, the CLI generates this from config.yaml.

### Subtask T014 – Update README API overview

- **Purpose**: The API overview must document the new Event fields.
- **Steps**:
  1. In the "API Overview" section (line ~115), update the Event description:

     From:
     ```
     - `Event`: Immutable event with causal metadata (lamport_clock, causation_id)
     ```

     To:
     ```
     - `Event`: Immutable event with causal metadata (lamport_clock, causation_id, project_uuid, project_slug)
     ```

  2. This is a one-line change in the API overview.

- **Files**: `README.md` (line ~115)
- **Parallel?**: No — same file as T013.
- **Notes**: Keep it brief — the API overview is a summary, not full docs.

### Subtask T015 – Update README version references

- **Purpose**: Version references in installation instructions must match the new version.
- **Steps**:
  1. Update the "Status" line (line ~6):
     ```
     **Status**: Alpha (v0.1.1-alpha)
     ```
  2. Update the pip install command (line ~23):
     ```bash
     pip install git+https://github.com/Priivacy-ai/spec-kitty-events.git@v0.1.1-alpha
     ```
  3. Update the pyproject.toml example (line ~31):
     ```toml
     "spec-kitty-events @ git+https://github.com/Priivacy-ai/spec-kitty-events.git@v0.1.1-alpha",
     ```
  4. Update the Roadmap "Current" label (line ~176):
     ```
     **v0.1.1-alpha** (Current):
     ```
  5. Add a new roadmap bullet for project identity:
     ```
     - ✅ Project identity (project_uuid, project_slug)
     ```

- **Files**: `README.md` (lines ~6, ~23, ~31, ~176)
- **Parallel?**: No — same file as T013/T014.
- **Notes**: 4 locations to update. Search for `0.1.0-alpha` to find all occurrences.

### Subtask T016 – Add CHANGELOG 0.1.1-alpha entry

- **Purpose**: Document what changed in this release for downstream consumers.
- **Steps**:
  1. Open `CHANGELOG.md`.
  2. Add a new entry at the top (after the header, before the `0.1.0-alpha` entry):

     ```markdown
     ## [0.1.1-alpha] - 2026-02-07

     ### Added
     - `project_uuid` field on `Event` model (required, `uuid.UUID` type)
     - `project_slug` field on `Event` model (optional, `str` type, defaults to `None`)

     ### Changed
     - `Event` now requires `project_uuid` in all constructors (breaking change from 0.1.0-alpha)
     - `to_dict()` / `from_dict()` include project identity fields
     - `__repr__()` displays truncated project UUID

     ### Breaking Changes
     - All `Event()` constructors must now include `project_uuid` parameter
     - This is a coordinated release with spec-kitty CLI and spec-kitty-saas
     ```

- **Files**: `CHANGELOG.md`
- **Parallel?**: Yes — independent of README changes.
- **Notes**: Follow the existing CHANGELOG format (Keep a Changelog style).

## Test Strategy

Validate documentation accuracy:

```bash
# Run the README quickstart example as a script
python -c "
from datetime import datetime
import uuid
from spec_kitty_events import (
    Event,
    LamportClock,
    InMemoryClockStorage,
    InMemoryEventStore,
)
clock_storage = InMemoryClockStorage()
event_store = InMemoryEventStore()
clock = LamportClock(node_id='alice', storage=clock_storage)
clock.tick()
event = Event(
    event_id='01ARZ3NDEKTSV4RRFFQ69G5FAV',
    event_type='WPStatusChanged',
    aggregate_id='WP001',
    timestamp=datetime.now(),
    node_id='alice',
    lamport_clock=clock.current(),
    payload={'state': 'doing'},
    project_uuid=uuid.uuid4(),
    project_slug='my-project',
)
event_store.save_event(event)
print('Quickstart OK:', event)
"
```

## Risks & Mitigations

- **Risk**: README examples don't match actual API after changes. **Mitigation**: Run the quickstart validation script above.
- **Risk**: Version tag `v0.1.1-alpha` doesn't exist on GitHub yet. **Mitigation**: Documentation updates reference the version; tag is created at release time.

## Review Guidance

- Copy the README quickstart code and run it — must succeed.
- Verify all `0.1.0-alpha` references are updated to `0.1.1-alpha` in README (search the file).
- Verify CHANGELOG entry is at the top and follows existing format.
- Verify API overview mentions both `project_uuid` and `project_slug`.

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
