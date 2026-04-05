---
work_package_id: WP01
title: Cutover Artifact & Envelope Foundation
dependencies: []
requirement_refs:
- C-002
- FR-005
- FR-006
- FR-012
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-014-mission-contract-cutover
base_commit: 6fbebd6b946e5f1b8bcecf686f381db9f798641c
created_at: '2026-04-05T13:00:59.185881+00:00'
subtasks:
- T001
- T002
- T003
- T004
shell_pid: "84881"
agent: "codex"
history:
- timestamp: '2026-04-05T12:40:33Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/spec_kitty_events/
execution_mode: code_change
owned_files:
- src/spec_kitty_events/models.py
- src/spec_kitty_events/cutover.py
- src/spec_kitty_events/conformance/fixtures/manifest.json
- tests/unit/test_models.py
- tests/unit/test_cutover.py
- tests/integration/test_event_emission.py
---

# Work Package Prompt: WP01 - Cutover Artifact & Envelope Foundation

## Objective & Success Criteria

- Establish one authoritative machine-readable cutover artifact under the packaged `spec-kitty-events` surface.
- Encode the exact on-wire signal binding, exact required cutover value, accepted-major policy, forbidden legacy keys, forbidden legacy event names, and forbidden legacy aggregate names in one place.
- Make repo-local helper logic interpret that artifact instead of scattered constant lists.
- Extend the canonical `Event` envelope so `build_id` is required and `node_id` remains the causal emitter identity only.
- Leave downstream runtime enforcement implementation to consuming repos while making the artifact executable and testable in this repo.

**Implementation command**: `spec-kitty implement WP01`

## Branch Strategy

- Planning/base branch: `main`
- Final merge target: `main`
- Canonical branch strategy: `Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.`
- Execution note: implementation worktrees are assigned later from `lanes.json`; do not improvise a branch layout inside this prompt.

## Context & Constraints

- **Spec**: `kitty-specs/014-mission-contract-cutover/spec.md`
- **Plan**: `kitty-specs/014-mission-contract-cutover/plan.md`
- **Data model**: `kitty-specs/014-mission-contract-cutover/data-model.md`
- **Research**: `kitty-specs/014-mission-contract-cutover/research.md`
- **Contracts**: `kitty-specs/014-mission-contract-cutover/contracts/`
- This is a hard cutover. No compatibility aliases, downgrade mode, or local/dev runtime exception may be introduced.
- The artifact must be the single policy source. Do not hand-maintain parallel gate lists in helper code or tests when they can be derived from the artifact.
- If you evaluate an existing release-authority surface and it cannot cleanly encode the full policy, add a dedicated artifact rather than splitting the rule across multiple places.

## Owned Files

- `src/spec_kitty_events/models.py`
- `src/spec_kitty_events/cutover.py` (new if needed)
- `src/spec_kitty_events/conformance/fixtures/manifest.json` (only if this existing packaged manifest is promoted to the authoritative artifact)
- `tests/unit/test_models.py`
- `tests/unit/test_cutover.py` (new if needed)
- `tests/integration/test_event_emission.py`

Do not modify files outside this list. Schema generation, broad fixture rewrites, public exports, and docs belong to later WPs. If the existing packaged manifest is chosen as the authoritative artifact, structural changes needed to promote it belong here.

## Subtasks & Detailed Guidance

### Subtask T001 - Choose and place the authoritative cutover artifact surface

**Purpose**: Decide where the single machine-readable cutover artifact lives in the packaged release and make that location authoritative.

**Steps**:

1. Inspect the release-authority candidates named in planning artifacts, especially existing packaged manifest-style surfaces.
2. Evaluate the candidate against the full policy requirements:
   - exact signal field name
   - exact signal location on wire
   - exact required cutover value
   - accepted-major policy
   - forbidden legacy keys
   - forbidden legacy event names
   - forbidden legacy aggregate names
3. If an existing surface can encode all of that without becoming overloaded or ambiguous, extend it.
4. Otherwise introduce a dedicated packaged cutover artifact under `src/spec_kitty_events/` and document that it is now authoritative.
5. Ensure the artifact shape aligns with `kitty-specs/014-mission-contract-cutover/contracts/cutover_contract_artifact.schema.json`.

**Files**:

- `src/spec_kitty_events/cutover.py` or equivalent packaged artifact location
- `src/spec_kitty_events/conformance/fixtures/manifest.json` if that manifest is promoted to release-authority status
- `src/spec_kitty_events/models.py` only if the chosen location requires a typed wrapper or loader reference there

**Validation**:

- [ ] One authoritative packaged artifact exists or one existing authoritative surface is extended cleanly.
- [ ] The artifact location can be loaded by repo-local code without consulting docs or duplicated constants.
- [ ] The artifact can express all required gate semantics from the plan.

### Subtask T002 - Implement artifact interpreter/helper semantics

**Purpose**: Make the artifact executable inside `spec-kitty-events` so later validators and tests can enforce policy from data instead of prose.

**Steps**:

1. Add a small helper module or typed artifact model that loads and validates the chosen artifact shape.
2. Implement helper operations for:
   - reading the canonical signal field name and location
   - comparing the required cutover value
   - comparing accepted major version
   - detecting forbidden legacy keys
   - detecting forbidden legacy event names
   - detecting forbidden legacy aggregate names
3. Keep the helper focused on classification and validation primitives. It should not become a cross-repo runtime bridge.
4. Prefer clear function names such as `is_pre_cutover_payload`, `assert_canonical_cutover_signal`, or similarly direct semantics that match the spec.
5. Make failure modes explicit and intentionally hard-failing when the artifact is malformed or the payload is not canonical.

**Files**:

- `src/spec_kitty_events/cutover.py`
- `tests/unit/test_cutover.py`

**Validation**:

- [ ] Missing signal is classified as pre-cutover.
- [ ] Wrong accepted major is classified as pre-cutover.
- [ ] Forbidden key, event name, and aggregate name each fail independently.
- [ ] Canonical payloads that satisfy all conditions pass.

### Subtask T003 - Extend Event with build_id and preserve node_id semantics

**Purpose**: Update the canonical event envelope so checkout identity and causal emitter identity are distinct public contract fields.

**Steps**:

1. In `src/spec_kitty_events/models.py`, add required `build_id` to `Event` with clear description language matching the plan.
2. Keep `node_id` required, but tighten its description to causal emitter identity only.
3. Check constructors, serializers, and reprs so the new field is preserved without conflating it with `node_id`.
4. Keep schema-version handling consistent with the artifact’s eventual signal binding. If `schema_version` is the chosen cutover signal, do not invent a second version field here.
5. Ensure there is no helper or docstring path that still implies `node_id` identifies the checkout.

**Files**:

- `src/spec_kitty_events/models.py`

**Validation**:

- [ ] `Event` requires `build_id`.
- [ ] `Event` still requires `node_id`.
- [ ] Public descriptions distinguish checkout identity from causal ordering identity.
- [ ] Existing event serialization remains deterministic apart from the new required field.

### Subtask T004 - Add foundation tests for artifact semantics and envelope split

**Purpose**: Lock the artifact and envelope behavior down before downstream contract families build on it.

**Steps**:

1. Extend `tests/unit/test_models.py` to cover `build_id` requirement and `node_id` retention on `Event`.
2. Add focused unit tests in `tests/unit/test_cutover.py` for helper classification behavior:
   - canonical payload
   - missing signal
   - wrong accepted major
   - forbidden key present
   - forbidden event name present
   - forbidden aggregate name present
3. Update `tests/integration/test_event_emission.py` so event creation paths include `build_id` and preserve Lamport ordering behavior.
4. Keep test fixtures local to these files; later conformance/fixture rewrites happen in WP05.

**Validation**:

- [ ] Unit tests prove the artifact helper is fail-closed.
- [ ] Integration test coverage proves `Event` construction and emission paths now carry `build_id`.
- [ ] No tests rely on runtime compatibility aliasing.

## Implementation Sequence

1. Finish T001 first so the artifact location is settled.
2. Implement T002 helper semantics against that location.
3. Land T003 envelope changes.
4. Finish with T004 tests to stabilize the foundation.

## Test Strategy

- Run the directly touched unit and integration tests for artifact and event model behavior.
- Keep test assertions specific to the exact artifact fields and fail-closed semantics described above.
- Do not attempt schema regeneration or conformance fixture rewrites in this WP.

## Definition of Done

- One authoritative artifact location exists and is machine-readable.
- Repo-local helper code can derive the exact gate semantics from the artifact.
- `Event` requires `build_id` and clearly preserves `node_id` semantics.
- Foundation tests pass for the owned files.

## Risks & Reviewer Guidance

- Reviewers should reject any solution that duplicates gate policy in helper constants when the artifact can express it.
- Reviewers should reject any implementation that adds a compatibility bridge or soft-failure path.
- Reviewers should verify that `build_id` and `node_id` are described and enforced as distinct concepts.

## Activity Log

- 2026-04-05T13:00:59Z – opencode – shell_pid=84881 – Started implementation via action command
- 2026-04-05T13:08:42Z – opencode – shell_pid=84881 – Ready for review
- 2026-04-05T13:09:25Z – codex – shell_pid=84881 – Started review via action command
- 2026-04-05T13:11:44Z – codex – shell_pid=84881 – Moved to planned
