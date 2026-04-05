---
work_package_id: WP05
title: Schemas, Conformance & Replay Gates
dependencies:
  - WP01
  - WP02
  - WP03
  - WP04
requirement_refs:
- FR-003
- FR-005
- FR-007
- FR-008
- FR-010
- FR-011
- FR-012
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- NFR-005
- C-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
agent: "opencode"
shell_pid: "84881"
history:
- timestamp: '2026-04-05T12:40:33Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/spec_kitty_events/conformance/
execution_mode: code_change
owned_files:
- src/spec_kitty_events/schemas/generate.py
- src/spec_kitty_events/schemas/__init__.py
- src/spec_kitty_events/schemas/*.json
- src/spec_kitty_events/conformance/validators.py
- src/spec_kitty_events/conformance/loader.py
- src/spec_kitty_events/conformance/fixtures/events/invalid/**
- src/spec_kitty_events/conformance/fixtures/lane_mapping/**
- src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/**
- src/spec_kitty_events/conformance/fixtures/edge_cases/valid/alias_doing_normalized.json
- src/spec_kitty_events/conformance/fixtures/edge_cases/valid/optional_fields_omitted.json
- src/spec_kitty_events/conformance/fixtures/collaboration/**
- src/spec_kitty_events/conformance/fixtures/glossary/**
- src/spec_kitty_events/conformance/fixtures/mission_next/**
- src/spec_kitty_events/conformance/fixtures/dossier/**
- src/spec_kitty_events/conformance/fixtures/mission_audit/**
- src/spec_kitty_events/conformance/fixtures/decisionpoint/**
- src/spec_kitty_events/conformance/fixtures/connector/**
- src/spec_kitty_events/conformance/fixtures/sync/**
- src/spec_kitty_events/conformance/fixtures/replay/**
- tests/unit/test_schemas.py
- tests/unit/test_fixtures.py
- tests/unit/test_conformance.py
- tests/test_connector_conformance.py
- tests/test_sync_conformance.py
- tests/test_glossary_conformance.py
- tests/test_mission_next_conformance.py
- tests/test_dossier_conformance.py
- tests/test_decisionpoint_conformance.py
- tests/test_mission_audit_conformance.py
- tests/integration/test_schema_drift.py
---

# Work Package Prompt: WP05 - Schemas, Conformance & Replay Gates

## Objective & Success Criteria

- Regenerate committed JSON schemas from the canonicalized source models.
- Make conformance and replay validation derive compatibility policy from the authoritative cutover artifact.
- Rewrite fixtures and manifest entries so canonical payloads pass and pre-cutover payloads fail for every forbidden surface class.
- Keep the release bar explicit: schema drift, conformance validation, and replay validation must all pass.

**Implementation command**: `spec-kitty implement WP05`

## Branch Strategy

- Planning/base branch: `main`
- Final merge target: `main`
- Canonical branch strategy: `Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.`
- Execution note: this WP consolidates the source-model changes from WP01-WP04 and should not start until those dependencies are ready.

## Context & Constraints

- **Depends on**: WP01, WP02, WP03, WP04.
- **Spec**: `kitty-specs/014-mission-contract-cutover/spec.md`
- **Plan**: `kitty-specs/014-mission-contract-cutover/plan.md`
- **Quickstart**: `kitty-specs/014-mission-contract-cutover/quickstart.md`
- The artifact must remain the single policy source. Validators, fixtures, and tests should derive from it rather than duplicating rule lists where avoidable.
- This WP owns the authoritative packaged schemas and conformance fixtures for the release.

## Owned Files

- `src/spec_kitty_events/schemas/generate.py`
- `src/spec_kitty_events/schemas/__init__.py`
- `src/spec_kitty_events/schemas/*.json`
- `src/spec_kitty_events/conformance/validators.py`
- `src/spec_kitty_events/conformance/loader.py`
- `src/spec_kitty_events/conformance/fixtures/events/invalid/**`
- `src/spec_kitty_events/conformance/fixtures/lane_mapping/**`
- `src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/**`
- `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/alias_doing_normalized.json`
- `src/spec_kitty_events/conformance/fixtures/edge_cases/valid/optional_fields_omitted.json`
- `src/spec_kitty_events/conformance/fixtures/collaboration/**`
- `src/spec_kitty_events/conformance/fixtures/glossary/**`
- `src/spec_kitty_events/conformance/fixtures/mission_next/**`
- `src/spec_kitty_events/conformance/fixtures/dossier/**`
- `src/spec_kitty_events/conformance/fixtures/mission_audit/**`
- `src/spec_kitty_events/conformance/fixtures/decisionpoint/**`
- `src/spec_kitty_events/conformance/fixtures/connector/**`
- `src/spec_kitty_events/conformance/fixtures/sync/**`
- `src/spec_kitty_events/conformance/fixtures/replay/**`
- `tests/unit/test_schemas.py`
- `tests/unit/test_fixtures.py`
- `tests/unit/test_conformance.py`
- `tests/test_connector_conformance.py`
- `tests/test_sync_conformance.py`
- `tests/test_glossary_conformance.py`
- `tests/test_mission_next_conformance.py`
- `tests/test_dossier_conformance.py`
- `tests/test_decisionpoint_conformance.py`
- `tests/test_mission_audit_conformance.py`
- `tests/integration/test_schema_drift.py`

## Subtasks & Detailed Guidance

### Subtask T017 - Update schema generation registry and loaders

**Purpose**: Ensure the canonicalized source models and artifact are all represented in generated schema surfaces and schema loading helpers.

**Steps**:

1. Audit `src/spec_kitty_events/schemas/generate.py` for all touched lifecycle, runtime, projection, and envelope models.
2. Add registrations for new or renamed payloads and the cutover artifact if it is represented as a schema surface.
3. Update `src/spec_kitty_events/schemas/__init__.py` if schema loading helpers need to expose new schema names.
4. Keep naming consistent with canonical mission/build terminology.

**Validation**:

- [ ] All touched source models can be emitted as committed schemas.
- [ ] Schema loading helpers recognize the new schema names.

### Subtask T018 - Regenerate committed JSON schemas

**Purpose**: Make committed schemas match the canonicalized codebase.

**Steps**:

1. Regenerate the schema set after T017 is complete.
2. Verify the regenerated output includes:
   - event envelope changes with `build_id`
   - lifecycle/runtime mission contract changes
   - dossier/decisionpoint/mission_audit/status changes
   - cutover artifact schema if packaged as a schema surface
3. Review generated schema names and descriptions for any lingering legacy `feature*` or mission-domain `mission_key` surfaces.

**Validation**:

- [ ] Generated schemas are committed and drift-free.
- [ ] No public generated schema leaks forbidden legacy naming.

### Subtask T019 - Enforce artifact semantics in validators and loaders

**Purpose**: Route conformance validation through the artifact instead of scattered local policy definitions.

**Steps**:

1. Update `src/spec_kitty_events/conformance/validators.py` so validation decisions use the authoritative artifact semantics.
2. Update `src/spec_kitty_events/conformance/loader.py` if fixture metadata or artifact loading needs to participate in gate evaluation.
3. Cover these fail-closed cases explicitly:
   - missing signal
   - wrong accepted major
   - forbidden legacy key
   - forbidden legacy event name
   - forbidden legacy aggregate name
4. Keep helper usage one-directional: validators should consume the artifact, not redefine it.

**Validation**:

- [ ] Conformance validation derives gate semantics from the artifact.
- [ ] All forbidden surface classes are represented.

### Subtask T020 - Rewrite fixtures and manifest entries

**Purpose**: Bring valid, invalid, and replay fixtures to canonical mission/build terminology and explicit fail-closed coverage.

**Steps**:

1. Rewrite relevant entries in `src/spec_kitty_events/conformance/fixtures/manifest.json` to reflect the cutover release and new fixture expectations.
2. Rewrite affected fixtures under `events/`, `mission_next/`, `dossier/`, `mission_audit/`, and shared `replay/` paths.
3. Add invalid fixtures for the exact gate failure classes if they do not already exist.
4. Preserve fixture intent while applying canonical terminology and exact on-wire signal semantics.

**Validation**:

- [ ] Valid fixtures are canonical.
- [ ] Invalid fixtures cover all required fail-closed gate classes.
- [ ] Replay fixtures still represent the intended domain scenarios.

### Subtask T021 - Update conformance, replay, and drift tests

**Purpose**: Make the release bar executable.

**Steps**:

1. Update unit tests around schema loading, fixtures, and generic conformance helpers.
2. Update the domain-specific conformance tests owned by this WP to reflect canonical fixture categories and fail-closed behavior.
3. Update `tests/integration/test_schema_drift.py` so committed schemas remain in sync after regeneration.
4. Ensure replay validation proves canonical outputs and rejection behavior where applicable.

**Validation**:

- [ ] Conformance tests pass using the artifact-driven policy.
- [ ] Replay validation passes.
- [ ] Schema drift tests pass.

## Implementation Sequence

1. T017 first.
2. T018 immediately after.
3. T019 and T020 can overlap once artifact shape and source models are final.
4. T021 closes the loop and proves the release bar.

## Test Strategy

- Run the conformance fixture validation path explicitly.
- Run replay validation explicitly if it is not fully covered by the general test suite.
- Run schema drift validation explicitly.
- Run owned conformance tests to verify canonical and invalid cases.

## Definition of Done

- Committed schemas reflect the canonical codebase.
- Conformance validators derive policy from the artifact.
- Fixtures and manifest entries are canonicalized and cover fail-closed behavior.
- Conformance, replay, and drift tests in the owned files pass.

## Risks & Reviewer Guidance

- Reviewers should inspect whether tests re-state forbidden surface lists instead of consuming the artifact.
- Reviewers should verify negative coverage exists for missing signal, wrong major, forbidden keys, forbidden event names, and forbidden aggregate names.
- Reviewers should reject any leftover legacy fixture examples that imply mixed-version support.

## Activity Log

- 2026-04-05T14:25:19Z – opencode – shell_pid=84881 – Started implementation via action command
- 2026-04-05T14:41:44Z – opencode – shell_pid=84881 – Ready for review
