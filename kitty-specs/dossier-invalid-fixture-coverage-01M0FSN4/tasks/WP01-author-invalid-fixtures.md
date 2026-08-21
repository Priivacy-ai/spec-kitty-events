---
work_package_id: WP01
title: Author invalid fixtures for MissionDossierArtifactMissing and MissionDossierSnapshotComputed
dependencies: []
requirement_refs:
- FR-001
- FR-002
planning_base_branch: feat/dossier-invalid-fixture-coverage
merge_target_branch: feat/dossier-invalid-fixture-coverage
branch_strategy: Planning artifacts for this mission were generated on feat/dossier-invalid-fixture-coverage. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dossier-invalid-fixture-coverage unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dossier-invalid-fixture-coverage-01M0FSN4
base_commit: 5a7c8e7894ed0aa5219428499d0d375882a12e4b
created_at: '2026-08-21T10:37:11.959749+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Fixture authoring
history:
- at: '2026-08-20T15:06:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/conformance/fixtures/dossier/invalid/
create_intent:
- src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_artifact_missing_empty_step.json
- src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_snapshot_computed_negative_count.json
execution_mode: code_change
model: ''
owned_files:
- src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_artifact_missing_empty_step.json
- src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_snapshot_computed_negative_count.json
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Author invalid fixtures for MissionDossierArtifactMissing and MissionDossierSnapshotComputed

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `opencode`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `<div>`, `<script>`
Use language identifiers in code blocks: `python`, `bash`

---

## Objectives & Success Criteria

- Create two new invalid conformance fixture JSON files: one for `MissionDossierArtifactMissing`, one for `MissionDossierSnapshotComputed`.
- Each fixture must be a minimally-modified copy of an existing valid sibling fixture, with **exactly one** field changed to violate a real, actively-enforced Pydantic constraint on the target payload model — not a docstring-only convention.
- Each fixture must be locally confirmed to genuinely fail `validate_event()` before this WP is considered done. A fixture that "looks broken" but Pydantic silently coerces or ignores is not acceptable.
- This WP creates files only — it does **not** register them in `manifest.json` or touch `tests/test_dossier_conformance.py`. That is WP02's job (which depends on this WP completing first).

## Context & Constraints

- Mission: `dossier-invalid-fixture-coverage-01M0FSN4`. Full context: `kitty-specs/dossier-invalid-fixture-coverage-01M0FSN4/spec.md` (FR-001, FR-002), `plan.md` (IC-01, IC-02), `data-model.md` (exact field values for both fixtures), `research.md` (why these specific violations were chosen over alternatives).
- Charter (`.kittify/charter/charter.md`): conformance fixtures are part of the public contract surface and require deliberate compatibility review — do not deviate from the exact field values specified in `data-model.md` without flagging it in your Activity Log.
- **C-001 (spec.md)**: this is a fixtures-only change. Do NOT touch `src/spec_kitty_events/dossier.py`, any file under `src/spec_kitty_events/schemas/`, or `src/spec_kitty_events/conformance/validators.py`. All required constraint surface already exists in those files — read them for reference only.
- Reference the exact existing valid fixtures you're copying from:
  - `src/spec_kitty_events/conformance/fixtures/dossier/valid/dossier_artifact_missing_required_always.json`
  - `src/spec_kitty_events/conformance/fixtures/dossier/valid/dossier_snapshot_computed_clean.json`
- Reference the payload models for the constraints you're violating: `src/spec_kitty_events/dossier.py`, classes `MissionDossierArtifactMissingPayload` (line ~133) and `MissionDossierSnapshotComputedPayload` (line ~154).

## Branch Strategy

- **Strategy**: Planning artifacts and this WP's changes were generated/implemented on `feat/dossier-invalid-fixture-coverage`; completed changes merge back into the same branch (PR-bound mission — that branch itself will be opened as a PR against `main`).
- **Planning base branch**: `feat/dossier-invalid-fixture-coverage`
- **Merge target branch**: `feat/dossier-invalid-fixture-coverage`

> These fields are populated automatically by `spec-kitty agent mission tasks`. Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T001 – Write `dossier_artifact_missing_empty_step.json`

- **Purpose**: Give `MissionDossierArtifactMissing` its first invalid-fixture coverage (currently has valid fixtures only).
- **Steps**:
  1. Read `src/spec_kitty_events/conformance/fixtures/dossier/valid/dossier_artifact_missing_required_always.json` as your starting point.
  2. Copy it to `src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_artifact_missing_empty_step.json`.
  3. Change **only** the `manifest_step` field from `"required_always"` to `""` (empty string). Leave `namespace`, `expected_identity`, and `checked_at` exactly as in the valid sibling.
  4. Do not add, remove, or rename any other field.
- **Files**: `src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_artifact_missing_empty_step.json` (new)
- **Parallel?**: Yes — independent of T003/T004 (different file, different payload type).
- **Notes**: The violated constraint is `manifest_step: str = Field(..., min_length=1, ...)` in `dossier.py`. Confirm this is the *only* thing wrong with the fixture — see T002.

### Subtask T002 – Locally validate the T001 fixture fails

- **Purpose**: Prove the fixture genuinely fails validation before it's committed — do not rely on CI to discover a fixture that accidentally passes.
- **Steps**:
  1. Run:
     ```bash
     python3 -c "
     import json
     from spec_kitty_events.conformance.validators import validate_event
     payload = json.load(open('src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_artifact_missing_empty_step.json'))
     result = validate_event(payload, 'MissionDossierArtifactMissing')
     assert not result.is_valid, 'Fixture unexpectedly passed validation'
     print('OK — fails as expected:', result.violations)
     "
     ```
  2. Confirm the reported violation is specifically about `manifest_step` (min_length), not some other field.
  3. If the fixture unexpectedly passes, or fails for the wrong reason, fix the fixture (not the model/schema — those are out of scope for this WP) and re-run.
- **Files**: none (verification step only)
- **Parallel?**: Depends on T001 completing first (same fixture).
- **Notes**: If `validate_event` isn't importable directly in your shell, run this from the repo root with the package installed in editable mode, or via `pytest` with a throwaway one-off test — do not leave a throwaway test file behind.

### Subtask T003 – Write `dossier_snapshot_computed_negative_count.json`

- **Purpose**: Give `MissionDossierSnapshotComputed` its first invalid-fixture coverage.
- **Steps**:
  1. Read `src/spec_kitty_events/conformance/fixtures/dossier/valid/dossier_snapshot_computed_clean.json` as your starting point.
  2. Copy it to `src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_snapshot_computed_negative_count.json`.
  3. Change **only** the `artifact_count` field from `3` to `-1`. Leave `namespace`, `snapshot_hash`, `anomaly_count`, `computed_at`, and `algorithm` exactly as in the valid sibling.
  4. Do not use an invalid `algorithm` literal instead — that was explicitly considered and rejected during planning (see `research.md`) because it would duplicate the existing enum-violation category already covered by `dossier_artifact_indexed_invalid_class.json`.
- **Files**: `src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_snapshot_computed_negative_count.json` (new)
- **Parallel?**: Yes — independent of T001/T002.
- **Notes**: The violated constraint is `artifact_count: int = Field(..., ge=0)` in `dossier.py`.

### Subtask T004 – Locally validate the T003 fixture fails

- **Purpose**: Same as T002, for the SnapshotComputed fixture.
- **Steps**:
  1. Run the equivalent local check:
     ```bash
     python3 -c "
     import json
     from spec_kitty_events.conformance.validators import validate_event
     payload = json.load(open('src/spec_kitty_events/conformance/fixtures/dossier/invalid/dossier_snapshot_computed_negative_count.json'))
     result = validate_event(payload, 'MissionDossierSnapshotComputed')
     assert not result.is_valid, 'Fixture unexpectedly passed validation'
     print('OK — fails as expected:', result.violations)
     "
     ```
  2. Confirm the reported violation is specifically about `artifact_count` (ge=0).
- **Files**: none (verification step only)
- **Parallel?**: Depends on T003 completing first.
- **Notes**: none beyond T002's.

## Test Strategy

- This WP does not run the full `pytest` suite (the fixtures aren't registered in `manifest.json` yet — that's WP02). The only required verification here is the ad-hoc local `validate_event()` check in T002/T004.

## Risks & Mitigations

- **Risk**: Silent pass due to Pydantic coercion or an unconstrained field (several dossier timestamp fields are plain `str` with no format validator — do not choose a timestamp field as your violation target). **Mitigation**: T002/T004's explicit local check catches this before commit.
- **Risk**: Accidentally changing more than one field, making the fixture's violation ambiguous. **Mitigation**: Diff your new fixture against its valid sibling before finishing — exactly one field should differ.

## Review Guidance

- Confirm both new fixture files are minimally-modified copies of their valid siblings (one field different, nothing else).
- Confirm the violation on each fixture matches what's documented in `data-model.md` (`manifest_step: ""` / `artifact_count: -1`), not a substitute violation.
- Confirm no files outside `owned_files` were touched (in particular, no edits to `dossier.py`, schemas, `validators.py`, `manifest.json`, or `tests/test_dossier_conformance.py` — those are WP02's surface).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-08-20T15:06:36Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP01 --to <status>` to change WP status.
