---
work_package_id: WP02
title: Register new fixtures in manifest.json and update conformance count gates
dependencies:
- WP01
requirement_refs:
- FR-003
planning_base_branch: feat/dossier-invalid-fixture-coverage
merge_target_branch: feat/dossier-invalid-fixture-coverage
branch_strategy: Planning artifacts for this mission were generated on feat/dossier-invalid-fixture-coverage. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dossier-invalid-fixture-coverage unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 2 - Wiring
history:
- at: '2026-08-20T15:06:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/spec_kitty_events/conformance/fixtures/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/spec_kitty_events/conformance/fixtures/manifest.json
- tests/test_dossier_conformance.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Register new fixtures in manifest.json and update conformance count gates

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

- Register both fixtures created in WP01 as entries in `src/spec_kitty_events/conformance/fixtures/manifest.json` — the mechanism `load_fixtures()` actually reads (fixtures are **not** directory-scanned; an unregistered fixture file is silently invisible to every test).
- Update the two hardcoded count assertions in `tests/test_dossier_conformance.py` to match the new totals.
- Prove the whole thing works: run the suite and confirm both new fixtures are exercised as new parametrized cases, with zero regressions.
- This WP is the mission's single shared touchpoint — it must not start until **both** of WP01's fixture files exist (hard dependency).

## Context & Constraints

- Mission: `dossier-invalid-fixture-coverage-01M0FSN4`. Full context: `spec.md` (FR-003, NFR-001, NFR-002), `plan.md` (IC-03), `data-model.md` (exact manifest entry field values for both fixtures), `contracts/manifest-entry-contract.md` (the manifest-entry shape contract), `quickstart.md` (the add-a-fixture recipe this WP follows).
- **Dependency**: WP01 must be done first — this WP references the exact filenames WP01 creates (`dossier_artifact_missing_empty_step.json`, `dossier_snapshot_computed_negative_count.json`). Do not fabricate different filenames; if WP01's actual filenames differ from these, use WP01's real output and note the discrepancy in your Activity Log.
- **C-001/C-003 (spec.md)**: no changes to `dossier.py`, JSON Schema files, or `validate_event()`. Your diff must stay within `manifest.json` (2 new array entries) and the 2 integer literals in `tests/test_dossier_conformance.py`.
- Read `src/spec_kitty_events/conformance/loader.py`'s `load_fixtures()` to understand exactly how `manifest.json` entries are consumed (filtered by `path.startswith(category + "/")`), and `tests/test_dossier_conformance.py` in full before editing — understand where the 3 hardcoded count assertions live and how the parametrized pass/fail tests derive their cases from `load_fixtures("dossier")`.

## Branch Strategy

- **Strategy**: Planning artifacts and this WP's changes were generated/implemented on `feat/dossier-invalid-fixture-coverage`; completed changes merge back into the same branch (PR-bound mission).
- **Planning base branch**: `feat/dossier-invalid-fixture-coverage`
- **Merge target branch**: `feat/dossier-invalid-fixture-coverage`

> These fields are populated automatically by `spec-kitty agent mission tasks`. Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T005 – Add both fixtures' entries to `manifest.json`

- **Purpose**: Make `load_fixtures("dossier")` actually see the two new fixture files — this is the step the original spec omitted and the post-spec adversarial review flagged as the mission's central risk.
- **Steps**:
  1. Open `src/spec_kitty_events/conformance/fixtures/manifest.json` and find the existing `dossier/invalid/*` entries for the pattern to follow.
  2. Add exactly two new objects to the `fixtures` array (see `contracts/manifest-entry-contract.md` for the required shape):
     ```json
     {
       "id": "dossier-artifact-missing-empty-step",
       "path": "dossier/invalid/dossier_artifact_missing_empty_step.json",
       "event_type": "MissionDossierArtifactMissing",
       "expected_result": "invalid",
       "notes": "manifest_step is an empty string — violates min_length=1",
       "min_version": "2.4.0"
     },
     {
       "id": "dossier-snapshot-computed-negative-count",
       "path": "dossier/invalid/dossier_snapshot_computed_negative_count.json",
       "event_type": "MissionDossierSnapshotComputed",
       "expected_result": "invalid",
       "notes": "artifact_count is negative (-1) — violates ge=0",
       "min_version": "2.4.0"
     }
     ```
  3. Keep valid JSON (comma placement, no trailing comma if your JSON serializer/formatter is strict).
- **Files**: `src/spec_kitty_events/conformance/fixtures/manifest.json` (edit — append 2 entries)
- **Parallel?**: No — sequential first step of this WP.
- **Notes**: `id` values must be unique across the whole manifest (they already are, by construction).

### Subtask T006 – Bump hardcoded count assertions

- **Purpose**: These 3 hardcoded literals are a deliberate scaffold assertion (not friction to remove) that catches exactly the failure mode where a fixture file exists but its manifest entry doesn't — they must be updated in lockstep with T005, not skipped.
- **Steps**:
  1. Open `tests/test_dossier_conformance.py`.
  2. Find `test_dossier_fixture_count` — change its asserted total from `13` to `15`.
  3. Find `test_dossier_invalid_case_count` — change its asserted total from `3` to `5`.
  4. Leave `test_dossier_valid_case_count` (asserting `10`) **unchanged** — neither new fixture is valid.
  5. Do **not** add any new `def test_...` function — the existing parametrized tests (`test_valid_fixture_passes_conformance`, `test_invalid_fixture_fails_conformance`) will pick up both new fixtures automatically once T005 is done.
- **Files**: `tests/test_dossier_conformance.py` (edit — 2 literal changes only)
- **Parallel?**: Depends on T005 (must know the final counts before editing, though the counts are already fixed at 15/5 by this mission's known scope).
- **Notes**: If you find yourself wanting to add a bespoke test function for either new fixture, stop — that duplicates what parametrization already does generically and was explicitly flagged as a laziness/duplication risk during planning.

### Subtask T007 – Run the full conformance suite

- **Purpose**: Prove the wiring actually works end-to-end.
- **Steps**:
  1. Run:
     ```bash
     pytest tests/test_dossier_conformance.py -v
     ```
  2. Confirm all tests pass, including two new parametrized cases under `test_invalid_fixture_fails_conformance` corresponding to the two new fixtures.
  3. Confirm the three count-assertion tests pass with the new totals (15 total fixtures, 5 invalid, 10 valid).
  4. If anything fails, diagnose before proceeding — do not mark this WP done with a failing suite.
- **Files**: none (verification step only)
- **Parallel?**: No — must run after T005 and T006.
- **Notes**: This also serves as NFR-001 (no regression) verification.

### Subtask T008 – Verify manifest/directory 1:1 consistency

- **Purpose**: Confirm NFR-002 directly — no orphaned fixture file, no dangling manifest entry, for the dossier invalid-fixtures set.
- **Steps**:
  1. Run:
     ```bash
     python3 -c "
     import json, pathlib
     m = json.load(open('src/spec_kitty_events/conformance/fixtures/manifest.json'))
     manifest_paths = {e['path'] for e in m['fixtures'] if e['path'].startswith('dossier/invalid/')}
     dir_files = {f'dossier/invalid/{p.name}' for p in pathlib.Path('src/spec_kitty_events/conformance/fixtures/dossier/invalid').glob('*.json')}
     assert manifest_paths == dir_files, f'Mismatch: manifest-only={manifest_paths - dir_files}, dir-only={dir_files - manifest_paths}'
     print('OK —', len(dir_files), 'invalid dossier fixtures, all registered 1:1')
     "
     ```
  2. Confirm output shows `5` invalid dossier fixtures with no mismatch.
- **Files**: none (verification step only)
- **Parallel?**: No — final step.
- **Notes**: none.

## Test Strategy

- T007 (full `pytest tests/test_dossier_conformance.py`) and T008 (manifest/directory consistency script) together constitute this WP's complete test strategy — both are mandatory, not optional, since they are how NFR-001 and NFR-002 are verified.

## Risks & Mitigations

- **Risk**: This WP's count-bump literals are wrong if WP01 produced different fixture filenames or a different fixture count than planned. **Mitigation**: T005 explicitly references WP01's real output files; if they differ from what's documented here, use the real filenames and note the discrepancy.
- **Risk**: Editing `manifest.json` breaks JSON syntax (trailing comma, mismatched braces). **Mitigation**: T007's full pytest run will fail immediately and loudly if the manifest doesn't parse.

## Review Guidance

- Confirm the diff is scoped to exactly `manifest.json` (2 new entries) and `tests/test_dossier_conformance.py` (2 literal edits) — per spec C-003, no other file should appear in this WP's diff.
- Confirm the `notes` field in each new manifest entry names the specific field/rule broken (not generic prose).
- Confirm `test_dossier_valid_case_count` was left at `10` (not accidentally bumped).
- Confirm the full `pytest tests/test_dossier_conformance.py` run is clean, with both new fixtures visible as new parametrized test IDs — this is your primary evidence of correctness for this WP.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-08-20T15:06:36Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP02 --to <status>` to change WP status.
