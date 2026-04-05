---
work_package_id: WP06
title: Public Docs, Exports & Release Versioning
dependencies:
- WP05
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-013
- NFR-003
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
agent: "opencode"
shell_pid: "84881"
history:
- timestamp: '2026-04-05T12:40:33Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: README.md
execution_mode: code_change
owned_files:
- README.md
- COMPATIBILITY.md
- pyproject.toml
- tests/integration/test_quickstart.py
---

# Work Package Prompt: WP06 - Public Docs, Exports & Release Versioning

## Objective & Success Criteria

- Publish the breaking release surface clearly.
- Update public exports and version notes to describe the cutover.
- Rewrite README and compatibility guidance to the canonical mission/build taxonomy and fail-closed rollout model.
- Bump the package version to `3.0.0` only after the contract surface is finalized.

**Implementation command**: `spec-kitty implement WP06`

## Branch Strategy

- Planning/base branch: `main`
- Final merge target: `main`
- Canonical branch strategy: `Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.`
- Execution note: this WP should run after WP05 so docs and release messaging reflect the final artifact fields and validation rules.

## Context & Constraints

- **Depends on**: WP05.
- **Spec**: `kitty-specs/014-mission-contract-cutover/spec.md`
- **Plan**: `kitty-specs/014-mission-contract-cutover/plan.md`
- **Quickstart**: `kitty-specs/014-mission-contract-cutover/quickstart.md`
- Public docs must describe the exact artifact-driven gate semantics. Do not document approximate or repo-local alternatives.
- This WP owns release messaging and version metadata, not source-model or schema internals. Package-surface alias cleanup needed to keep imports working belongs to the earlier owning WP.

## Owned Files

- `README.md`
- `COMPATIBILITY.md`
- `pyproject.toml`
- `tests/integration/test_quickstart.py`

## Subtasks & Detailed Guidance

### Subtask T022 - Update public release notes and package metadata messaging

**Purpose**: Make the published release messaging reflect the breaking cutover without promoting repo-local helper code into a public runtime dependency.

**Steps**:

1. Update release-facing notes in the owned documentation files to describe the breaking cutover accurately.
2. Keep repo-local helper implementation reference-only unless there is a clear, explicit public-consumer need already established by the approved contract.
3. Remove or rewrite release messaging that still implies additive-only `2.x` semantics where the release is now a breaking cutover.

**Validation**:

- [ ] Release-facing notes describe the breaking release accurately.
- [ ] The owned release messaging does not accidentally promote repo-local helper code into a runtime dependency.

### Subtask T023 - Rewrite README.md with canonical taxonomy and gate semantics

**Purpose**: Make README the public explanation of the cutover contract.

**Steps**:

1. Rewrite mission-domain terminology to use `mission_slug`, `mission_number`, and `mission_type`.
2. Explain the exact on-wire compatibility signal semantics chosen in WP05.
3. Explain `build_id` versus `node_id` clearly.
4. Remove any text that implies mixed old/new operation or compatibility aliasing.

**Validation**:

- [ ] README uses canonical mission/build terminology throughout.
- [ ] README describes the exact signal and identity split without contradiction.

### Subtask T024 - Rewrite COMPATIBILITY.md with fail-closed rollout policy

**Purpose**: Make the release and rollout policy explicit and unambiguous.

**Steps**:

1. State that all live ingestion paths fail closed from day one.
2. State that missing signal, wrong accepted major, forbidden legacy keys, forbidden legacy event names, and forbidden legacy aggregate names are rejection conditions.
3. State that offline migration/rewrite workflows may read legacy data only to rewrite it into canonical form.
4. State the cross-repo release gates for `spec-kitty-events`, `spec-kitty-saas`, and `spec-kitty`.

**Validation**:

- [ ] COMPATIBILITY.md describes the same artifact semantics as the final code and fixtures.
- [ ] No compatibility bridge language remains.

### Subtask T025 - Bump package version to 3.0.0

**Purpose**: Mark the release as breaking and make that visible in package metadata.

**Steps**:

1. Update `pyproject.toml` from `2.9.0` to `3.0.0`.
2. Check version references in touched release notes or package metadata comments.

**Validation**:

- [ ] Package metadata reports `3.0.0` consistently.

### Subtask T026 - Update doc-driven integration coverage

**Purpose**: Keep public examples and quickstart-driven validation aligned with the published contract.

**Steps**:

1. Review `tests/integration/test_quickstart.py` for any embedded version numbers, field names, or example payloads that changed.
2. Update the test to reflect the canonical mission/build terms and fail-closed guidance.
3. Keep the coverage focused on published usage, not on source-model internals already covered elsewhere.

**Validation**:

- [ ] Quickstart/integration coverage matches the new public docs and examples.

## Implementation Sequence

1. T022 after the code surface is stable.
2. T023 and T024 in parallel using the finalized artifact semantics.
3. T025 near the end of the WP.
4. T026 closes the loop with doc-driven integration coverage.

## Test Strategy

- Run the doc-driven integration coverage you own.
- Verify public docs match the final artifact semantics before handoff.

## Definition of Done

- Public exports and release notes reflect the breaking cutover.
- README and COMPATIBILITY.md are canonical and fail-closed.
- Package version is `3.0.0` everywhere it is publicly surfaced.
- Owned integration coverage passes.

## Risks & Reviewer Guidance

- Reviewers should compare docs directly against the finalized artifact semantics from WP05.
- Reviewers should reject any leftover wording that suggests compatibility aliases, local/dev exceptions, or mixed-version rollout.
- Reviewers should verify the version bump does not land without corresponding public documentation updates.

## Activity Log

- 2026-04-05T14:42:19Z – opencode – shell_pid=84881 – Started implementation via action command
- 2026-04-05T14:45:44Z – opencode – shell_pid=84881 – Ready for review
- 2026-04-05T14:45:52Z – opencode – shell_pid=84881 – Started review via action command
- 2026-04-05T14:46:08Z – opencode – shell_pid=84881 – Review passed: public docs, quickstart examples, and package metadata reflect the 3.0 fail-closed cutover
