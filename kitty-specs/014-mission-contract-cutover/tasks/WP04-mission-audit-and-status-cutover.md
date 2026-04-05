---
work_package_id: WP04
title: Mission Audit & Status Cutover
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-007
- FR-008
- NFR-001
- NFR-004
- C-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
agent: "opencode"
shell_pid: "84881"
history:
- timestamp: '2026-04-05T12:40:33Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/spec_kitty_events/mission_audit.py
execution_mode: code_change
owned_files:
- src/spec_kitty_events/mission_audit.py
- src/spec_kitty_events/status.py
- tests/unit/test_mission_audit.py
- tests/unit/test_status.py
- tests/test_mission_audit_reducer.py
- tests/property/test_mission_audit_determinism.py
- tests/property/test_status_determinism.py
---

# Work Package Prompt: WP04 - Mission Audit & Status Cutover

## Objective & Success Criteria

- Replace public mission-domain `feature*` naming in mission-audit and status-domain contract surfaces.
- Use `mission_slug`, `mission_number`, and `mission_type` where those modules describe mission identity.
- Keep historical rewrite expectations explicit without introducing runtime compatibility aliasing.

**Implementation command**: `spec-kitty implement WP04`

## Branch Strategy

- Planning/base branch: `main`
- Final merge target: `main`
- Canonical branch strategy: `Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.`
- Execution note: this WP can run in parallel with WP02 and WP03 after WP01 is complete.

## Context & Constraints

- **Depends on**: WP01.
- **Spec**: `kitty-specs/014-mission-contract-cutover/spec.md`
- **Plan**: `kitty-specs/014-mission-contract-cutover/plan.md`
- **Data model**: `kitty-specs/014-mission-contract-cutover/data-model.md`
- Touch only mission-domain public surfaces in these modules. Do not rename unrelated status concepts or non-mission uses of `feature`.
- Leave schema regeneration and conformance fixture rewrites to WP05.

## Owned Files

- `src/spec_kitty_events/mission_audit.py`
- `src/spec_kitty_events/status.py`
- `tests/unit/test_mission_audit.py`
- `tests/unit/test_status.py`
- `tests/test_mission_audit_reducer.py`
- `tests/property/test_mission_audit_determinism.py`
- `tests/property/test_status_determinism.py`

## Subtasks & Detailed Guidance

### Subtask T013 - Canonicalize mission_audit mission fields

**Purpose**: Replace legacy mission-domain identity fields in mission-audit payloads, reduced state, and helper outputs.

**Steps**:

1. Audit `src/spec_kitty_events/mission_audit.py` for public `feature_slug` usage and any related legacy mission identifiers.
2. Replace mission instance naming with `mission_slug`.
3. Add or rename mission numeric and workflow/template fields to `mission_number` and `mission_type` where the audit contract needs them.
4. Keep verdict, artifact reference, and audit trigger semantics unchanged.

**Validation**:

- [ ] Mission-audit public payloads no longer expose legacy `feature_slug`.
- [ ] Canonical fields line up with the plan’s data model.

### Subtask T014 - Canonicalize mission-domain status surfaces only

**Purpose**: Update `status.py` only where it exposes mission-domain legacy naming, while preserving unrelated status concepts.

**Steps**:

1. Audit `src/spec_kitty_events/status.py` for public mission-domain fields or helpers that still use `feature_slug` or similar legacy mission terms.
2. Rename only the mission-domain surfaces to canonical mission terminology.
3. Leave lane, verification, and unrelated status concepts intact unless they directly carry mission-domain public fields.
4. Keep the cutover narrow and deliberate so unrelated status APIs do not churn.

**Validation**:

- [ ] Mission-domain public fields in `status.py` are canonicalized.
- [ ] Unrelated status vocabulary remains unchanged.

### Subtask T015 - Update mission_audit and status tests

**Purpose**: Prove the canonical field set and cutover semantics in direct tests.

**Steps**:

1. Update `tests/unit/test_mission_audit.py` and `tests/test_mission_audit_reducer.py` for canonical field names and reduced outputs.
2. Update `tests/unit/test_status.py` and `tests/property/test_status_determinism.py` if mission-domain public fields changed there.
3. Update `tests/property/test_mission_audit_determinism.py` for renamed fields and serialized outputs.
4. Add explicit negative coverage where useful so legacy field names do not validate.

**Validation**:

- [ ] Owned tests assert canonical mission naming.
- [ ] Determinism tests still pass.

### Subtask T016 - Reflect rewrite semantics without runtime bridges

**Purpose**: Keep historical rewrite guidance visible in touched code paths without accepting legacy payloads on runtime paths.

**Steps**:

1. Review touched comments, anomaly text, or examples in `mission_audit.py` and `status.py`.
2. Where historical rewrite behavior is relevant, describe it as offline migration/rewrite behavior only.
3. Do not add alias fields, normalization logic, or permissive fallback validation.

**Validation**:

- [ ] No runtime compatibility bridge is introduced.
- [ ] Historical rewrite semantics are clearly offline-only.

## Implementation Sequence

1. T013 and T014 can proceed in parallel.
2. T015 follows after source field changes are complete.
3. T016 is a final audit for comments/messages/examples.

## Test Strategy

- Run mission-audit and status unit/reducer/property tests from the owned set.
- Keep test assertions explicit about legacy-name rejection and canonical-name acceptance.

## Definition of Done

- Mission-audit and status mission-domain public surfaces are canonicalized.
- Owned tests pass with canonical field names.
- No runtime bridge or compatibility alias is added.

## Risks & Reviewer Guidance

- Reviewers should confirm only mission-domain public surfaces were renamed in `status.py`.
- Reviewers should inspect validation and anomaly text for hidden bridge behavior.
- Reviewers should ensure fixture and schema work is deferred to WP05.

## Activity Log

- 2026-04-05T14:19:27Z – opencode – shell_pid=84881 – Started implementation via action command
- 2026-04-05T14:24:31Z – opencode – shell_pid=84881 – Ready for review
- 2026-04-05T14:24:40Z – opencode – shell_pid=84881 – Started review via action command
