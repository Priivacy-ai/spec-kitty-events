---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Integration Branch Setup & Recovery"
phase: "Phase 1 - Recovery"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-23T17:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Integration Branch Setup & Recovery

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ` ```python `, ` ```bash `

---

## Objectives & Success Criteria

Create the `009-dossier-release` integration branch from `origin/2.x` HEAD and apply
the two Feature 008 recovery commits cleanly.

**Done when**:
- `git log --oneline 009-dossier-release` shows `139ca09` (fix(dossier)) as HEAD,
  `5237894` (feat(008)) as HEAD~1, and `640709f` (docs: add security position statement)
  as HEAD~2 or earlier.
- No cherry-pick conflicts occurred.
- `640709f` is confirmed as an ancestor of the branch.
- The recovered file inventory includes all expected modules, schemas, fixtures, and tests.

**Implementation command** (no dependencies):
```bash
spec-kitty implement WP01
```

---

## Context & Constraints

- **Repo**: `spec-kitty-events`, branch `2.x`, planning repo root.
- **Do not use worktrees**: WP01 is a git operation — work in the repo root directly.
- **Python**: Use `python3.11` for all Python commands. System `python` is 3.14.
- **Key commits in reflog**:
  - `5237894` — `feat(008): merge Mission Dossier Parity Event Contracts into 2.x` (the full implementation: 41 files, 3,116 lines)
  - `139ca09` — `fix(dossier): namespace mismatch false-positive on step_id variance and malformed-first-event` (touches only `dossier.py` + `test_dossier_reducer.py`)
  - `640709f` — `docs: add security position statement` (already at `origin/2.x` HEAD)
- **Path B trigger**: If cherry-pick produces unresolvable conflicts, STOP. Document the conflict, note the trigger in the activity log, and report to the release manager. Do NOT force-push or resolve conflicts blindly.
- **Plan**: `kitty-specs/009-dossier-contracts-remote-baseline-release/plan.md`
- **Spec**: `kitty-specs/009-dossier-contracts-remote-baseline-release/spec.md`

---

## Subtasks & Detailed Guidance

### Subtask T001 – Verify reflog accessibility for both recovery commits

**Purpose**: Confirm both recovery commits are still in the local git reflog before
doing any branch work. If they are not accessible, Path B is mandatory and no further
WP01 work should proceed.

**Steps**:

```bash
git show 5237894 --stat
git show 139ca09 --stat
```

Expected output for `5237894`: stat listing showing ~41 files including `dossier.py`,
`schemas/`, `conformance/fixtures/dossier/`, `test_dossier_conformance.py`, etc.

Expected output for `139ca09`: stat listing showing `src/spec_kitty_events/dossier.py`
and `tests/test_dossier_reducer.py`.

**Gate**: Both commands must succeed (exit code 0). If either returns
`fatal: bad object`, stop immediately and trigger Path B.

**Files**: No files modified — read-only git inspection.

**Parallel?**: No — must succeed before any subsequent step.

---

### Subtask T002 – Create `009-dossier-release` branch from `origin/2.x`

**Purpose**: Establish the integration branch at the correct base (current
`origin/2.x` HEAD, which is `640709f`). This ensures the upstream security position
statement is included as an ancestor before any cherry-picks.

**Steps**:

```bash
# Ensure local state is clean and up to date
git status                          # must show clean working tree
git fetch origin                    # refresh remote refs
git checkout -b 009-dossier-release origin/2.x
```

**Expected**: `git log --oneline -1` shows `640709f docs: add security position statement`.

**Gate**: Branch created successfully and HEAD is `640709f`. If the working tree is
not clean when starting, stash or commit pending changes first.

**Files**: No source files modified — only git branch pointer created.

**Parallel?**: No — must follow T001.

---

### Subtask T003 – Cherry-pick `5237894` (feat(008) merge commit)

**Purpose**: Apply the complete Feature 008 implementation onto the integration
branch. This single cherry-pick brings in `dossier.py`, all JSON schemas, all
conformance fixtures, the conformance loader updates, the CHANGELOG additions,
and `__init__.py` export block.

**Steps**:

```bash
git cherry-pick 5237894
```

**Expected**: Clean apply, no conflicts. Git prints a success message and the
new commit SHA.

**If conflicts occur**: Run `git cherry-pick --abort`, document which files conflicted
in the activity log, and trigger Path B. Do NOT attempt manual conflict resolution
for a large merge commit — the risk of silent data loss is too high.

**Verify after cherry-pick**:

```bash
git diff origin/2.x HEAD --stat | head -30
# Must show dossier.py, schemas/, conformance/fixtures/dossier/, tests/, etc.
ls src/spec_kitty_events/dossier.py          # must exist
ls src/spec_kitty_events/schemas/            # must contain ≥8 files
ls src/spec_kitty_events/conformance/fixtures/dossier/  # must contain valid/, invalid/, replay/
```

**Files** (restored by cherry-pick):
- `src/spec_kitty_events/dossier.py` (new, 422 lines)
- `src/spec_kitty_events/__init__.py` (modified, +47 lines for dossier exports)
- `src/spec_kitty_events/schemas/*.schema.json` (8 new schema files)
- `src/spec_kitty_events/conformance/fixtures/dossier/**` (13 fixture files)
- `src/spec_kitty_events/conformance/fixtures/manifest.json` (modified)
- `src/spec_kitty_events/conformance/loader.py` (modified)
- `src/spec_kitty_events/conformance/validators.py` (modified)
- `src/spec_kitty_events/schemas/generate.py` (modified)
- `tests/test_dossier_conformance.py` (new, 145 lines)
- `tests/test_dossier_reducer.py` (new, 426 lines)
- `tests/unit/test_schemas.py` (modified)
- `CHANGELOG.md` (modified, +94 lines)
- `pyproject.toml` (modified, +5 lines)

**Parallel?**: No — must follow T002.

---

### Subtask T004 – Cherry-pick `139ca09` (namespace mismatch fix)

**Purpose**: Apply the P1a/P1b namespace mismatch bugfix. This commit introduces
`_namespace_key()` (5-field stable tuple for cross-event comparison) and two
regression tests that would have caught both failure modes.

**Steps**:

```bash
git cherry-pick 139ca09
```

**Expected**: Clean apply. `139ca09` touches only two files:
- `src/spec_kitty_events/dossier.py` (+38 lines with `_namespace_key()` and fixed loop)
- `tests/test_dossier_reducer.py` (+92 lines with two regression tests)

**If conflicts occur**: The conflict is in `dossier.py` or `test_dossier_reducer.py`.
Since T003 already applied `5237894` which includes the initial version of these files,
and `139ca09` is a direct fix commit on top, a conflict here is unexpected. If it
occurs: inspect the diff carefully (`git diff`), resolve conservatively (keep both
the original dossier logic from T003 AND the fix from `139ca09`), commit, and
document the resolution in the activity log.

**Verify after cherry-pick**:

```bash
git log --oneline -3
# Expected:
# <sha> fix(dossier): namespace mismatch false-positive ...
# <sha> feat(008): merge Mission Dossier Parity Event Contracts into 2.x
# 640709f docs: add security position statement
```

**Files**: `src/spec_kitty_events/dossier.py`, `tests/test_dossier_reducer.py`.

**Parallel?**: No — must follow T003.

---

### Subtask T005 – Confirm `640709f` is an ancestor of the branch

**Purpose**: FR-007 requires that the security position statement commit be present
in the final merged state. Since the branch was created from `origin/2.x` HEAD
(which IS `640709f`), it should always be an ancestor. This check is a fast
defensive verification.

**Steps**:

```bash
git merge-base --is-ancestor 640709f HEAD
echo "exit code: $?"
# Expected: exit code 0 (= is ancestor)
# If exit code 1: 640709f is NOT an ancestor — cherry-pick it explicitly:
#   git cherry-pick 640709f
```

**Files**: No files modified — read-only check.

**Parallel?**: No — must follow T004.

---

### Subtask T006 – Verify recovered file inventory matches expected 41-file set

**Purpose**: Confirm the cherry-pick captured all expected files. A partial
cherry-pick could silently omit schemas or fixtures, causing conformance failures
in WP02. Catching the gap here is faster than debugging test failures.

**Steps**:

Check key presence of each file category:

```bash
# Core module
ls -la src/spec_kitty_events/dossier.py

# Schemas (expect ≥8 files)
ls src/spec_kitty_events/schemas/*.schema.json | wc -l

# Conformance fixtures
ls src/spec_kitty_events/conformance/fixtures/dossier/valid/*.json | wc -l   # expect 9
ls src/spec_kitty_events/conformance/fixtures/dossier/invalid/*.json | wc -l # expect 2
ls src/spec_kitty_events/conformance/fixtures/dossier/replay/*.jsonl | wc -l # expect 2

# Test files
ls tests/test_dossier_conformance.py
ls tests/test_dossier_reducer.py

# Exports in __init__.py
grep -c "Dossier\|dossier" src/spec_kitty_events/__init__.py  # expect ≥6 matches

# CHANGELOG
grep -c "2\.4\.0" CHANGELOG.md   # expect ≥1 match
```

**Gate**: All counts at or above expected minimums. If any are missing, inspect
`git show 5237894 --stat` to identify the missing files and cherry-pick only
the missing files manually (as a last resort before Path B).

**Files**: No files modified — read-only verification.

**Parallel?**: No — must follow T004.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Reflog expiry before WP01 starts | Check T001 first; if expired, trigger Path B immediately |
| Cherry-pick conflict on large merge commit | Abort and trigger Path B; do not attempt manual merge |
| Unexpected upstream commits on origin/2.x between WP01 and WP03 | Rebase integration branch before PR; re-run WP02 gate |
| File inventory mismatch (T006) | Inspect missing files, attempt targeted fix; escalate to Path B if systemic |

---

## Review Guidance

- Confirm `git log --oneline 009-dossier-release` shows the correct 3-commit history.
- Confirm T006 counts all pass (9 valid fixtures, 2 invalid fixtures, 2 replay files, ≥8 schemas).
- Confirm `640709f` is an ancestor (T005 exit code 0).
- No conflicts were force-resolved; any conflict resolution is explicitly documented in the activity log.

---

## Activity Log

- 2026-02-23T17:55:00Z – system – lane=planned – Prompt created.
