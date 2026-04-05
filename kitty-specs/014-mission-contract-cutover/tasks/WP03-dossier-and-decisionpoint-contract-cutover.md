---
work_package_id: WP03
title: Dossier & Decisionpoint Contract Cutover
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-007
- FR-008
- FR-013
- NFR-001
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
agent: "opencode"
shell_pid: "84881"
history:
- timestamp: '2026-04-05T12:40:33Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/spec_kitty_events/dossier.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/dossier.py
- src/spec_kitty_events/decisionpoint.py
- tests/unit/test_decisionpoint.py
- tests/test_dossier_reducer.py
- tests/test_decisionpoint_reducer.py
- tests/property/test_decisionpoint_determinism.py
---

# Work Package Prompt: WP03 - Dossier & Decisionpoint Contract Cutover

## Objective & Success Criteria

- Remove public mission-domain `feature_slug` and mission-domain `mission_key` usage from dossier and decisionpoint contracts.
- Use `mission_slug` and `mission_type` consistently in payloads, reducers, and reduced outputs.
- Preserve team-scoped `Project` semantics as documented meaning only, not as runtime enforcement inside these modules.

**Implementation command**: `spec-kitty implement WP03`

## Branch Strategy

- Planning/base branch: `main`
- Final merge target: `main`
- Canonical branch strategy: `Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.`
- Execution note: later workspace assignment comes from `lanes.json`; this WP may execute in parallel with WP02 and WP04 once WP01 is complete.

## Context & Constraints

- **Depends on**: WP01. Use the artifact-defined gate semantics as read-only context but do not reimplement the helper here.
- **Spec**: `kitty-specs/014-mission-contract-cutover/spec.md`
- **Plan**: `kitty-specs/014-mission-contract-cutover/plan.md`
- **Data model**: `kitty-specs/014-mission-contract-cutover/data-model.md`
- This WP is about source models and direct tests only. Schema and fixture rewrites happen in WP05.
- Do not rename unrelated uses of `feature` or add compatibility alias fields.

## Owned Files

- `src/spec_kitty_events/dossier.py`
- `src/spec_kitty_events/decisionpoint.py`
- `tests/unit/test_decisionpoint.py`
- `tests/test_dossier_reducer.py`
- `tests/test_decisionpoint_reducer.py`
- `tests/property/test_decisionpoint_determinism.py`

## Subtasks & Detailed Guidance

### Subtask T009 - Canonicalize dossier mission fields

**Purpose**: Replace legacy mission-domain naming in dossier payloads, namespaces, and reduced outputs.

**Steps**:

1. Audit `src/spec_kitty_events/dossier.py` for public `feature_slug` and `mission_key` usage.
2. Replace mission instance terminology with `mission_slug` and workflow/template terminology with `mission_type`.
3. Update any reducer-local variables, namespace objects, or output models so canonical terms persist all the way through serialization.
4. Preserve unrelated dossier semantics such as provenance or content hash handling.

**Validation**:

- [ ] Public dossier payloads and reduced outputs no longer expose legacy mission-domain names.
- [ ] Mission taxonomy matches the plan’s canonical data model.

### Subtask T010 - Canonicalize decisionpoint mission fields

**Purpose**: Replace legacy mission-domain naming in decisionpoint contracts and reduced state.

**Steps**:

1. Audit `src/spec_kitty_events/decisionpoint.py` for public `feature_slug` and any mission-domain workflow identifier using `mission_key`.
2. Rename those surfaces to `mission_slug` and `mission_type` as appropriate.
3. Ensure reduced-state projections and anomaly records do not leak the old names.
4. Keep decision authority and discussion semantics unchanged.

**Validation**:

- [ ] Decisionpoint payloads and outputs use canonical mission naming only.
- [ ] No compatibility alias field remains public.

### Subtask T011 - Update dossier and decisionpoint tests

**Purpose**: Lock the canonical taxonomy into direct reducer and property coverage.

**Steps**:

1. Update `tests/test_dossier_reducer.py` to assert canonical mission field names and outputs.
2. Update `tests/unit/test_decisionpoint.py` and `tests/test_decisionpoint_reducer.py` to assert canonical field names and removed legacy names.
3. Update `tests/property/test_decisionpoint_determinism.py` if field names or serialized state shapes changed.
4. Add negative tests where useful so legacy field names fail validation instead of being silently accepted.

**Validation**:

- [ ] Reducer tests prove canonical output names.
- [ ] Property tests still pass under the new payload shape.

### Subtask T012 - Keep Project semantics documented-only in these modules

**Purpose**: Ensure the source changes do not overclaim enforcement of downstream team-scoped `Project` behavior.

**Steps**:

1. Review touched comments, docstrings, and validation messages in `dossier.py` and `decisionpoint.py`.
2. Where `Project` semantics are mentioned, phrase them as contract meaning or documentation only.
3. Do not add runtime bridge logic, reconciliation logic, or cross-team detection here.
4. Keep the modules focused on event contract representation and projection behavior.

**Validation**:

- [ ] Touched documentation does not imply this repo enforces downstream SaaS reconciliation behavior.
- [ ] No bridge logic or compatibility path is introduced.

## Implementation Sequence

1. T009 and T010 can be done in parallel.
2. T011 follows once field renames are complete.
3. T012 is the final audit pass over touched surfaces.

## Test Strategy

- Run the dossier and decisionpoint reducer/unit/property tests in the owned files.
- Ensure negative cases reject legacy fields rather than silently translating them.

## Definition of Done

- Dossier and decisionpoint public mission-domain surfaces are canonicalized.
- Owned tests assert canonical names and reject legacy ones.
- Touched docstrings/comments keep project semantics descriptive, not enforceable here.

## Risks & Reviewer Guidance

- Reviewers should inspect nested output structures, not just top-level payload fields.
- Reviewers should reject any leftover `feature_slug`/`mission_key` usage on public surfaces.
- Reviewers should verify that this WP stays inside its owned files and leaves fixture/schema work to WP05.

## Activity Log

- 2026-04-05T14:02:26Z – opencode – shell_pid=84881 – Started implementation via action command
- 2026-04-05T14:11:34Z – opencode – shell_pid=84881 – Ready for review
- 2026-04-05T14:12:03Z – codex – shell_pid=84881 – Started review via action command
- 2026-04-05T14:13:35Z – codex – shell_pid=84881 – Moved to planned
- 2026-04-05T14:16:02Z – opencode – shell_pid=84881 – Started implementation via action command
- 2026-04-05T14:18:25Z – opencode – shell_pid=84881 – Ready for review
