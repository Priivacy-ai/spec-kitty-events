---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "Local Verification Gate"
phase: "Phase 2 - Verification"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-02-23T17:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Local Verification Gate

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.
- **Report progress**: Update the Activity Log as you address each item.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ` ```python `, ` ```bash `

---

## Objectives & Success Criteria

Prove the recovered implementation is correct and complete before opening the PR.
All quality gates must pass on the `009-dossier-release` branch before the push
to `origin`.

**Done when all of the following are true**:
1. `python3.11 -m pytest` reports ≥1,117 tests, 0 failures, 0 errors.
2. Coverage on `src/spec_kitty_events/dossier.py` is ≥98%.
3. `mypy --strict src/spec_kitty_events/` reports 0 new errors (compared to `origin/2.x` baseline).
4. `python3.11 -m pytest tests/test_dossier_conformance.py -v` — all 10 valid fixtures pass; all 3 invalid fixtures are rejected with named errors.
5. `python3.11 -m pytest tests/test_dossier_reducer.py -v -k "replay"` — both replay scenarios produce a deterministic `MissionDossierState`.
6. `git push -u origin 009-dossier-release` succeeds (deferred until remote pushes are permitted).

**Implementation command** (depends on WP01):
```bash
spec-kitty implement WP02 --base WP01
```

---

## Context & Constraints

- **Branch**: `009-dossier-release` (created in WP01; must be current branch).
- **Python version**: Always use `python3.11` explicitly. The system `python` is 3.14 and will give incorrect results with the editable install.
- **Coverage configuration**: `pyproject.toml` includes `addopts = "--cov=src/spec_kitty_events"` — no manual `--cov` flag required for `pytest`.
- **Extras**: The `[conformance]` extra installs `jsonschema>=4.21,<5.0`. Without it, conformance tests will be skipped or fail with import errors.
- **Mypy baseline**: Run mypy on `origin/2.x` first if uncertain about pre-existing errors; new errors are those not present on the base branch.
- **Path B trigger conditions** (from plan.md):
  - Test failures attributable to the recovered code (not upstream issues) → Path B.
  - mypy errors in recovered files with no clean fix → Path B.
  - Coverage <95% that cannot be restored without significant new test writing → Path B.
- **Plan**: `kitty-specs/009-dossier-contracts-remote-baseline-release/plan.md`

---

## Subtasks & Detailed Guidance

### Subtask T007 – Install package with dev + conformance extras

**Purpose**: Ensure the local editable install picks up the recovered `dossier.py`
and the `[conformance]` extra (jsonschema) is available for the conformance suite.

**Steps**:

```bash
pip install -e ".[dev,conformance]"
```

**Verify**:

```bash
python3.11 -c "from spec_kitty_events import MissionDossierArtifactIndexed; print('import ok')"
python3.11 -c "import jsonschema; print(jsonschema.__version__)"  # must be ≥4.21
```

**Gate**: Both imports succeed. If `MissionDossierArtifactIndexed` import fails,
check `src/spec_kitty_events/__init__.py` for the dossier export block — it should
have been added by the cherry-pick.

**Files**: No source files modified.

**Parallel?**: No — must precede all test and mypy steps.

---

### Subtask T008 – Run full pytest suite and verify count + zero failures

**Purpose**: SC-002 requires ≥1,117 tests, 0 failures. This is the primary
regression gate for the entire recovered implementation.

**Steps**:

```bash
python3.11 -m pytest
```

The `pyproject.toml` `addopts` will automatically apply `--cov=src/spec_kitty_events`
and produce a coverage report alongside the test results.

**Expected output** (approximate):
```
===================== 1117+ passed in Xs =====================
```

**If test count is below 1,117**:
```bash
git diff origin/2.x HEAD -- tests/ --stat
# Identify any missing test files
```
If `test_dossier_conformance.py` or `test_dossier_reducer.py` are missing, the
cherry-pick dropped them. Re-apply from reflog:
```bash
git checkout 5237894 -- tests/test_dossier_conformance.py
git checkout 5237894 -- tests/test_dossier_reducer.py
git checkout 139ca09 -- tests/test_dossier_reducer.py  # overwrite with the fixed version
git add tests/ && git commit -m "fix(recovery): restore missing dossier test files"
```

**If tests fail**: Categorize the failure:
- Failure in `test_dossier_*.py` → likely recovered code issue → investigate; may trigger Path B.
- Failure in unrelated tests (pre-existing flakiness on `origin/2.x`) → document, re-run to confirm flakiness, proceed if stable.

**Files**: No source files modified. Produces coverage `.coverage` artifact.

**Parallel?**: No — T009 and T010 depend on the coverage output from this run.

---

### Subtask T009 – Check coverage report for `dossier.py` (≥98%)

**Purpose**: SC-002 requires ≥98% coverage on `dossier.py`. The recovered
implementation was at 100% after `139ca09`; any regression indicates untested paths.

**Steps**:

After T008 completes, inspect the coverage report for `dossier.py`:

```bash
python3.11 -m pytest --cov=src/spec_kitty_events --cov-report=term-missing 2>&1 | grep "dossier"
```

Or generate the full HTML report:
```bash
python3.11 -m pytest --cov=src/spec_kitty_events --cov-report=html
open htmlcov/index.html   # inspect dossier.py line coverage
```

**Gate**: Coverage on `src/spec_kitty_events/dossier.py` ≥98%.

**If coverage is below 98%**:
1. Identify uncovered lines using `--cov-report=term-missing`.
2. Check if `139ca09` regression tests were recovered (T008 investigation).
3. If tests are present but specific paths are still uncovered, add targeted tests
   in a follow-up commit on `009-dossier-release`. Document additions in activity log.
4. If coverage is below 95% and cannot be restored without major new test writing → Path B.

**Files**: No source files modified (unless follow-up tests are added).

**Parallel?**: Yes — can run simultaneously with T010 after T008 completes.

---

### Subtask T010 – Run `mypy --strict` and confirm zero new errors

**Purpose**: The project enforces `mypy --strict` with Python 3.10 target. The
recovered `dossier.py` must be type-correct in the current mypy environment.

**Steps**:

```bash
# Baseline: count errors on origin/2.x before cherry-picks (for comparison if needed)
# (Run this only if uncertain about pre-existing errors; skip if the baseline is known clean)

# Primary gate:
mypy --strict src/spec_kitty_events/
```

**Expected**: Same error count as on `origin/2.x` HEAD before WP01. In a clean
project, this is 0 errors.

**If new errors appear**:
1. Identify which files introduced them: `mypy --strict src/spec_kitty_events/dossier.py`
2. Common causes in Pydantic v2 context (from project memory):
   - `AnyHttpUrl` serializer: add `@field_serializer` returning `str(v)`.
   - `from __future__ import annotations` with type branches: use distinct variable names per branch.
   - `ConfigDict(frozen=True)` already in use — maintain pattern.
3. Fix errors in a follow-up commit on `009-dossier-release`. Document in activity log.
4. If errors cannot be resolved cleanly → assess Path B trigger.

**Files**: Modify `src/spec_kitty_events/dossier.py` only if type errors require fixes.

**Parallel?**: Yes — can run simultaneously with T009 after T008 completes.

---

### Subtask T011 – Run dossier conformance suite (valid fixtures pass, invalid rejected)

**Purpose**: SC-003 requires all 9 valid dossier fixtures to pass and both invalid
fixtures to be rejected with specific, documented field errors.

**Steps**:

```bash
python3.11 -m pytest tests/test_dossier_conformance.py -v
```

**Expected output** (one line per fixture):

```
PASSED tests/test_dossier_conformance.py::test_valid_dossier_artifact_indexed_valid
PASSED tests/test_dossier_conformance.py::test_valid_dossier_artifact_indexed_with_provenance
PASSED tests/test_dossier_conformance.py::test_valid_dossier_artifact_indexed_supersedes
PASSED tests/test_dossier_conformance.py::test_valid_dossier_artifact_missing_required_always
PASSED tests/test_dossier_conformance.py::test_valid_dossier_artifact_missing_required_by_step
PASSED tests/test_dossier_conformance.py::test_valid_dossier_namespace_collision_coverage
PASSED tests/test_dossier_conformance.py::test_valid_dossier_parity_drift_artifact_added
PASSED tests/test_dossier_conformance.py::test_valid_dossier_parity_drift_artifact_mutated
PASSED tests/test_dossier_conformance.py::test_valid_dossier_snapshot_computed_clean
PASSED tests/test_dossier_conformance.py::test_invalid_dossier_artifact_indexed_invalid_class
PASSED tests/test_dossier_conformance.py::test_invalid_dossier_artifact_indexed_missing_path
```

**If a valid fixture fails**: The fixture JSON or its schema may have been recovered
with a conflict. Compare `git show 5237894 -- <fixture-path>` against the current file.

**If an invalid fixture passes** (conformance test is incorrect): Inspect the test
logic in `test_dossier_conformance.py`. The invalid fixture should trigger a
schema validation error; if the schema is too permissive, update the schema.

**Files**: No source files modified unless a schema correction is needed.

**Parallel?**: No — runs after T010 (to ensure schema files are clean).

---

### Subtask T012 – Run replay scenario tests and verify deterministic state

**Purpose**: SC-004 requires both replay scenarios (`dossier_drift_scenario.jsonl`
and `dossier_happy_path.jsonl`) to produce a deterministic `MissionDossierState`.

**Steps**:

```bash
python3.11 -m pytest tests/test_dossier_reducer.py -v -k "replay"
```

**Expected**: Both replay-related tests pass. The `MissionDossierState` produced by
each scenario must match the expected snapshot embedded in the test.

**If replay tests fail**:
1. Check that `tests/test_dossier_reducer.py` is the post-fix version (from `139ca09`,
   not the original `5237894`). The fix adds `_namespace_key()` which affects replay
   behavior for streams with mixed `step_id` values.
2. Inspect the specific assertion failure: is the state incorrect (wrong data) or
   are there extra/missing events (wrong fixture)?
3. Compare the fixture files against `git show 5237894 -- <path>`.

**Files**: No source files modified.

**Parallel?**: No — must follow T011.

---

### Subtask T013 – Push `009-dossier-release` to `origin`

**Purpose**: Make the integration branch available for CI and PR creation in WP03.

**Steps**:

Confirm all local gates passed (T008–T012 all green), then:

```bash
git push -u origin 009-dossier-release
```

**Verify**:

```bash
git branch -vv | grep 009-dossier-release
# Should show: 009-dossier-release ... [origin/009-dossier-release] ...
```

**Gate**: Push succeeds and tracking relationship is established.

**Files**: No source files modified.

**Parallel?**: No — must be the last step after all local gates pass.

---

## Test Strategy

All testing in WP02 uses the existing test suite recovered from reflog. No new tests
are authored in this WP (unless coverage remediation in T009 requires additions).

Key test commands:

```bash
python3.11 -m pytest                                        # full suite
python3.11 -m pytest tests/test_dossier_conformance.py -v  # conformance gate
python3.11 -m pytest tests/test_dossier_reducer.py -v -k "replay"  # replay gate
mypy --strict src/spec_kitty_events/                        # type gate
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Test count below 1,117 | Restore missing test files via `git checkout <sha> -- <path>` |
| mypy errors in dossier.py | Apply minimal type fixes; document in activity log; escalate to Path B if systemic |
| Coverage <98% on dossier.py | Add targeted tests; escalate to Path B if <95% |
| Conformance valid fixture fails | Compare fixture against `git show 5237894` baseline; restore if corrupted |
| Replay scenario non-deterministic | Confirm 139ca09 `_namespace_key()` fix is applied; check fixture event ordering |
| Push rejected by origin | Check branch protection rules; ensure no force-push restriction; escalate if blocked |

---

## Review Guidance

- Confirm all 5 quality gate results: test count ≥1,117, coverage ≥98%, mypy clean, conformance 9+2, replay 2.
- Any follow-up commits made for coverage or mypy fixes must be explicitly listed in the activity log and reviewed.
- The push to `origin/009-dossier-release` must succeed before WP03 can begin.

---

## Activity Log

- 2026-02-23T17:55:00Z – system – lane=planned – Prompt created.
