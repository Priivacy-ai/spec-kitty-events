---
work_package_id: WP02
title: Lifecycle & Mission-Next Contract Cutover
dependencies:
- WP01
requirement_refs:
- C-002
- FR-001
- FR-002
- FR-003
- FR-004
- FR-008
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
agent: "codex"
shell_pid: "84881"
history:
- timestamp: '2026-04-05T12:40:33Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/spec_kitty_events/lifecycle.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/lifecycle.py
- src/spec_kitty_events/mission_next.py
- tests/unit/test_lifecycle.py
- tests/unit/test_mission_next.py
- tests/test_mission_next_reducer.py
- tests/property/test_lifecycle_determinism.py
- tests/property/test_mission_next_determinism.py
- tests/integration/test_lifecycle_replay.py
---

# Work Package Prompt: WP02 - Lifecycle & Mission-Next Contract Cutover

## Objective & Success Criteria

- Introduce canonical mission catalog events `MissionCreated` and `MissionClosed`.
- Keep `MissionCompleted` lifecycle-only.
- Keep `MissionRunCompleted` runtime-only.
- Rename runtime mission workflow/template fields from `mission_key` to `mission_type`.
- Remove the `MissionCompleted` runtime alias path entirely.

**Implementation command**: `spec-kitty implement WP02`

## Branch Strategy

- Planning/base branch: `main`
- Final merge target: `main`
- Canonical branch strategy: `Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.`
- Execution note: worktree allocation happens later from `lanes.json`; this WP should assume WP01 is already available as its dependency base.

## Context & Constraints

- **Depends on**: WP01. Use the authoritative cutover artifact and exact signal semantics established there; do not invent a local version gate.
- **Spec**: `kitty-specs/014-mission-contract-cutover/spec.md`
- **Plan**: `kitty-specs/014-mission-contract-cutover/plan.md`
- Mission catalog events and runtime mission-run events must have one meaning each. Reject solutions that preserve ambiguous aliasing.
- Do not rewrite conformance fixtures or JSON schemas here; source models and direct tests only.

## Owned Files

- `src/spec_kitty_events/lifecycle.py`
- `src/spec_kitty_events/mission_next.py`
- `tests/unit/test_lifecycle.py`
- `tests/unit/test_mission_next.py`
- `tests/test_mission_next_reducer.py`
- `tests/property/test_lifecycle_determinism.py`
- `tests/property/test_mission_next_determinism.py`
- `tests/integration/test_lifecycle_replay.py`

## Subtasks & Detailed Guidance

### Subtask T005 - Add MissionCreated and MissionClosed lifecycle catalog contracts

**Purpose**: Make mission catalog creation and closure explicit public event contracts instead of overloading existing lifecycle names.

**Steps**:

1. In `src/spec_kitty_events/lifecycle.py`, add canonical event constants for `MissionCreated` and `MissionClosed`.
2. Add or rename typed payload models so catalog creation and closure use canonical mission fields:
   - `mission_slug`
   - `mission_number`
   - `mission_type`
3. Update any lifecycle reducer registration or event-family sets so these new names participate correctly.
4. Make sure catalog-level semantics are distinct from runtime progression semantics.

**Validation**:

- [ ] Lifecycle code can validate/catalog these canonical event names.
- [ ] Payloads use canonical mission naming only.

### Subtask T006 - Preserve lifecycle-only MissionCompleted semantics

**Purpose**: Ensure `MissionCompleted` has exactly one meaning after the cutover.

**Steps**:

1. Audit `MissionCompletedPayload` and related reducer logic in `lifecycle.py`.
2. Remove any code path, docstring, or validation assumption that treats `MissionCompleted` as a catalog terminal event.
3. Update unit and property tests so lifecycle completion semantics remain valid while catalog closure is now represented elsewhere.
4. Add a negative test where useful to prove catalog closure does not reuse `MissionCompleted`.

**Validation**:

- [ ] `MissionCompleted` remains lifecycle-only.
- [ ] Lifecycle reducer outputs/tests align with that single meaning.

### Subtask T007 - Rename mission_key to mission_type in mission_next

**Purpose**: Align runtime mission-run payloads and reduced state with the canonical workflow/template identifier.

**Steps**:

1. In `src/spec_kitty_events/mission_next.py`, rename runtime payload fields and reduced-state fields from `mission_key` to `mission_type` where they represent workflow/template identity.
2. Update any comments, reducer temporary variables, and state output names so the terminology is consistent end to end.
3. Keep existing runtime actor semantics untouched.
4. Update unit and reducer tests to assert `mission_type` rather than `mission_key`.

**Validation**:

- [ ] Runtime payload models accept canonical `mission_type`.
- [ ] Reduced mission-run state no longer leaks `mission_key`.

### Subtask T008 - Remove the runtime MissionCompleted alias path

**Purpose**: Eliminate the old runtime normalization behavior that mapped `MissionCompleted` to `MissionRunCompleted`.

**Steps**:

1. Remove `_COMPLETION_ALIAS` and any alias event-family registration in `mission_next.py`.
2. Remove normalization logic that previously reinterpreted `MissionCompleted` as `MissionRunCompleted`.
3. Update reducer, replay, and determinism tests so runtime completion only accepts `MissionRunCompleted`.
4. Add a negative test path showing that `MissionCompleted` is not treated as a runtime alias anymore.

**Validation**:

- [ ] `MISSION_NEXT_EVENT_TYPES` contains only canonical runtime event names.
- [ ] Replay/reducer tests no longer normalize or silently ignore the alias path.
- [ ] Runtime completion semantics are unambiguous.

## Implementation Sequence

1. Land T005 so canonical catalog events exist.
2. Tighten T006 lifecycle completion semantics.
3. Apply T007 mission-next field renames.
4. Finish with T008 alias removal and negative tests.

## Test Strategy

- Run direct unit tests for `lifecycle.py` and `mission_next.py`.
- Run reducer and determinism/property tests for both domains.
- Run the replay-oriented integration test if it exercises lifecycle or mission-next semantics.

## Definition of Done

- `MissionCreated` and `MissionClosed` are first-class lifecycle catalog events.
- `MissionCompleted` is lifecycle-only.
- `MissionRunCompleted` is runtime-only.
- `mission_key` is removed from mission-next public contract surfaces and replaced with `mission_type`.
- Direct tests for the owned files pass.

## Risks & Reviewer Guidance

- Reviewers should reject any leftover runtime alias compatibility path, even if hidden behind a helper or warning.
- Reviewers should inspect reducer output field names, not just payload classes.
- Reviewers should confirm this WP does not attempt fixture or schema rewrites that belong to WP05.

## Activity Log

- 2026-04-05T13:27:24Z – opencode – shell_pid=84881 – Started implementation via action command
- 2026-04-05T13:38:21Z – opencode – shell_pid=84881 – Ready for review
- 2026-04-05T13:39:00Z – codex – shell_pid=84881 – Started review via action command
- 2026-04-05T13:40:38Z – codex – shell_pid=84881 – Moved to planned
