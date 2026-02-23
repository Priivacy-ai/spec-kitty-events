---
work_package_id: WP02
title: Local Verification Gate
lane: "planned"
dependencies:
- WP01
base_branch: main
base_commit: 59bbb3af14be089462c96533d920bd0271dc39dd
created_at: '2026-02-23T00:00:00.000000+00:00'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Verification
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-23T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated from tasks.md
---

# Work Package Prompt: WP02 – Local Verification Gate

## Context

Continues from WP01. The `009-dossier-release` branch now contains the recovered
Feature 008 commits. This WP proves the implementation is correct and complete
before the PR is opened.

**Prerequisite**: WP01 complete — `009-dossier-release` branch exists with both
cherry-picks applied cleanly.

## Goal

Prove the recovered implementation is correct and complete before the PR is opened.
All quality gates must be green.

**Independent Test**: `python3.11 -m pytest` reports ≥1,117 tests passed, 0 failed,
coverage on `dossier.py` ≥98%; `mypy --strict` reports 0 new errors; conformance
suite accepts 9 valid and rejects 2 invalid fixtures; both replay scenarios produce
the expected `MissionDossierState`.

## Subtasks

- [ ] T007 Install package with dev + conformance extras
- [ ] T008 Run full pytest suite and verify count + zero failures
- [ ] T009 Check coverage report for `dossier.py` (≥98%)
- [ ] T010 Run `mypy --strict` and confirm zero new errors
- [ ] T011 Run dossier conformance suite (valid fixtures pass, invalid rejected)
- [ ] T012 Run replay scenario tests and verify deterministic state
- [ ] T013 Push `009-dossier-release` to `origin`

## Implementation Notes

- Use `pip install -e ".[dev,conformance]"` (not plain `pip install -e .`)
- Commands must use `python3.11` explicitly (system `python` is 3.14)
- Coverage addopts are in `pyproject.toml` — no manual `--cov` flag needed
- For the conformance gate: `python3.11 -m pytest tests/test_dossier_conformance.py -v`
- For the replay gate: `python3.11 -m pytest tests/test_dossier_reducer.py -v -k "replay"`
- Push only after all local gates pass: `git push -u origin 009-dossier-release`

## Parallel Opportunities

- T009 (coverage) and T010 (mypy) can run simultaneously after T008 completes
  (different tools, different output).

## Dependencies

- Depends on WP01.

## Risks & Mitigations

- **Test count below 1,117**: Indicates not all test files were recovered; inspect
  `git diff origin/2.x HEAD -- tests/`.
- **mypy errors in recovered files**: May indicate Pydantic v2 type annotation
  differences between reflog state and current mypy version; fix in a follow-up
  commit on the integration branch, document delta.
- **Coverage below threshold**: Add targeted tests on the integration branch;
  document additions in the PR description.
