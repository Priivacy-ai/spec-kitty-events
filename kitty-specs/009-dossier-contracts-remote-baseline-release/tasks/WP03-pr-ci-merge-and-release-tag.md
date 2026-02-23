---
work_package_id: "WP03"
subtasks:
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
title: "PR, CI Gate, Merge & Release Tag"
phase: "Phase 3 - Release"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
history:
  - timestamp: "2026-02-23T17:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – PR, CI Gate, Merge & Release Tag

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

Land the recovered dossier contracts on `origin/2.x` with full PR traceability,
CI validation, and publish the `v2.4.0` annotated release tag from the merge commit.

**Done when all of the following are true**:
1. PR from `009-dossier-release` → `2.x` is merged (merge commit, not squash).
2. `git ls-remote --tags origin v2.4.0` returns a commit SHA.
3. `git show v2.4.0 --stat` shows the dossier files (dossier.py, schemas, fixtures).
4. `CHANGELOG.md` at `v2.4.0` contains the v2.4.0 release section listing all four contracts and the namespace fix.
5. Consumer import smoke-test succeeds from the `v2.4.0` tag.

**Implementation command** (depends on WP02):
```bash
spec-kitty implement WP03 --base WP02
```

---

## Context & Constraints

- **Branch**: `009-dossier-release` must be pushed to `origin` (done in WP02/T013).
- **Merge strategy**: **Merge commit** — do NOT squash. Preserves attribution of the original Feature 008 cherry-picks and the namespace bugfix separately.
- **Tag target**: The `v2.4.0` tag is cut from `2.x` HEAD **after** the PR merges, not from the integration branch SHA.
- **Tag format**: Matches prior releases (`v2.3.0`, `v2.3.1`) — annotated, prefixed `v`.
- **CHANGELOG gate**: If the CHANGELOG is missing the 2.4.0 section after merge, add it in a follow-up commit **before tagging**. The tag must include the CHANGELOG.
- **Tag collision**: If `v2.4.0` already exists on `origin`, do NOT overwrite or force-push the tag. Investigate and coordinate before proceeding.
- **gh CLI**: Use `gh pr create` and `gh pr merge` for PR operations. If `GITHUB_TOKEN` env var is set with limited scopes, prefix with `unset GITHUB_TOKEN &&` to use the keyring token.
- **Plan**: `kitty-specs/009-dossier-contracts-remote-baseline-release/plan.md`
- **Spec**: `kitty-specs/009-dossier-contracts-remote-baseline-release/spec.md`

---

## Subtasks & Detailed Guidance

### Subtask T014 – Open PR from `009-dossier-release` → `2.x`

**Purpose**: Create the PR that will serve as the traceability record for the
dossier contract promotion. The PR description links the recovery commits and
references the feature requirements.

**Steps**:

```bash
unset GITHUB_TOKEN && gh pr create \
  --base 2.x \
  --head 009-dossier-release \
  --title "feat(008): promote dossier contracts to remote baseline (v2.4.0)" \
  --body "$(cat <<'EOF'
## Summary

Promotes the Feature 008 Mission Dossier Parity Event Contracts from git reflog to
\`origin/2.x\` and prepares the \`v2.4.0\` release tag.

### Recovery commits included

- \`5237894\` — feat(008): merge Mission Dossier Parity Event Contracts into 2.x
  - 4 event contracts: \`MissionDossierArtifactIndexed\`, \`MissionDossierArtifactMissing\`,
    \`MissionDossierSnapshotComputed\`, \`MissionDossierParityDriftDetected\`
  - \`dossier.py\` — 422 lines (contracts, reducer, LocalNamespaceTuple)
  - 8 JSON schemas committed to \`schemas/\`
  - 13 conformance fixtures (9 valid, 2 invalid, 2 replay)
  - 571 lines of tests across \`test_dossier_conformance.py\` and \`test_dossier_reducer.py\`
  - \`CHANGELOG.md\` v2.4.0 section
- \`139ca09\` — fix(dossier): namespace mismatch false-positive on step_id variance
  - P1a: Introduced \`_namespace_key()\` for stable 5-field namespace comparison
  - P1b: Fixed reducer loop to skip malformed first events
  - +92 lines of regression tests

### Requirements satisfied

FR-001 through FR-009 from spec.md. All local quality gates passed (WP02):
- ≥1,117 tests, 0 failures
- dossier.py coverage ≥98%
- mypy --strict clean
- 9 valid fixtures pass, 2 invalid rejected
- Both replay scenarios deterministic

### After merge

Cut \`v2.4.0\` annotated tag from the \`2.x\` merge commit.
EOF
)"
```

**Record the PR URL** from the output — include it in the activity log.

**Verify**: `gh pr view` shows the PR as open against `2.x`.

**Files**: No source files modified.

**Parallel?**: No.

---

### Subtask T015 – Monitor CI and confirm all checks pass

**Purpose**: CI validates the recovered implementation in a clean environment.
All checks must be green before merge.

**Steps**:

```bash
# Get PR number from the URL (e.g., #42)
unset GITHUB_TOKEN && gh pr checks <PR_NUMBER> --watch
```

Or monitor via:

```bash
unset GITHUB_TOKEN && gh run list --branch 009-dossier-release --limit 5
unset GITHUB_TOKEN && gh run watch <RUN_ID>
```

**Expected**: All CI checks pass (green). Common checks in this repo: pytest,
mypy, coverage threshold.

**If CI fails**:
1. Identify the specific failing check: `gh run view <RUN_ID> --log-failed`
2. Categorize:
   - **Dossier-related failure** (tests in test_dossier_*.py, mypy error in dossier.py):
     Fix on `009-dossier-release`, push, wait for CI re-run.
   - **Unrelated pre-existing failure** (flaky test, CI config issue not caused by this PR):
     Document clearly in the PR description, seek a bypass waiver from the release manager,
     proceed only with explicit written approval.
3. Do NOT merge with a red CI check without explicit release manager approval.

**Files**: No source files modified (unless a CI-driven fix is needed).

**Parallel?**: No — must follow T014 (PR must exist for CI to run).

---

### Subtask T016 – Merge PR into `2.x` using merge commit

**Purpose**: Land the integration branch onto `2.x` with full commit history
preserved. Merge commit (not squash) is required to maintain attribution.

**Steps**:

```bash
unset GITHUB_TOKEN && gh pr merge <PR_NUMBER> --merge --delete-branch
```

The `--merge` flag uses the standard merge commit strategy.
The `--delete-branch` flag cleans up the remote `009-dossier-release` branch
after a successful merge.

**After merge**:

```bash
git checkout 2.x
git pull origin 2.x
git log --oneline -5
# Verify the merge commit appears at HEAD with the correct parent SHAs
```

**Gate**: `origin/2.x` HEAD is now the merge commit containing the dossier files.

**Files**: No source files modified in this step — git operation only.

**Parallel?**: No — must follow T015.

---

### Subtask T017 – Verify `CHANGELOG.md` at `2.x` HEAD contains v2.4.0 section

**Purpose**: FR-009 and SC-002 require the CHANGELOG to document the release at
the tagged commit. Verify it is present before tagging.

**Steps**:

```bash
# Must be on 2.x with latest pull (done in T016)
grep -A 5 "## \[2\.4\.0\]\|## 2\.4\.0" CHANGELOG.md | head -20
```

**Expected**: Output shows the v2.4.0 section header and at minimum mentions the
four dossier contracts and the namespace fix.

**If the v2.4.0 section is absent**:

The cherry-pick may have dropped the CHANGELOG update. Recover and add it:

```bash
# Show what 5237894 added to CHANGELOG.md
git show 5237894 -- CHANGELOG.md | head -120

# Manually apply the CHANGELOG additions to the current 2.x state
# Edit CHANGELOG.md to add the v2.4.0 section at the top (after the header)
# Then commit:
git add CHANGELOG.md
git commit -m "docs: add v2.4.0 CHANGELOG entry for dossier contracts release"
git push origin 2.x
```

**Files**: `CHANGELOG.md` (modified only if section is absent).

**Parallel?**: No — must follow T016.

---

### Subtask T018 – Create annotated `v2.4.0` tag from `2.x` HEAD

**Purpose**: FR-008 requires an annotated tag pointing to the merge commit on
`2.x`. The tag matches the format of prior releases (`v2.3.0`, `v2.3.1`).

**Steps**:

First, confirm no `v2.4.0` tag exists locally or on origin:

```bash
git tag --list "v2.4.0"                           # must return empty
git ls-remote --tags origin v2.4.0               # must return empty
```

If either returns a SHA: **STOP** — do NOT overwrite. Investigate and coordinate.

If clear, create the annotated tag:

```bash
# Confirm HEAD is the merge commit
git log --oneline -1
# Expected: <sha> Merge pull request #N from .../009-dossier-release

# Create annotated tag
git tag -a v2.4.0 -m "Release v2.4.0: Mission Dossier Parity Event Contracts

Four canonical dossier/parity event contracts:
- MissionDossierArtifactIndexed
- MissionDossierArtifactMissing
- MissionDossierSnapshotComputed
- MissionDossierParityDriftDetected

Includes: dossier reducer, LocalNamespaceTuple, JSON schemas,
conformance fixtures, and namespace mismatch bugfix (step_id variance).

Recovery of Feature 008 implementation onto origin/2.x baseline."
```

**Verify**:

```bash
git show v2.4.0 --stat | head -5
# Must show the merge commit SHA and dossier-related files
```

**Files**: No source files modified — git tag operation only.

**Parallel?**: No — must follow T017.

---

### Subtask T019 – Push `v2.4.0` tag to `origin`

**Purpose**: Make the tag available to all consumers. SC-005 requires the tag
to be visible on `origin`.

**Steps**:

```bash
git push origin v2.4.0
```

**Note**: Push the specific tag (`v2.4.0`), not `--tags` (which would push all
local tags and could push unintended tags).

**Verify**:

```bash
git ls-remote --tags origin v2.4.0
# Must return: <SHA>    refs/tags/v2.4.0
```

**Gate**: The SHA returned must match `git rev-parse v2.4.0`.

**Files**: No source files modified.

**Parallel?**: No — must follow T018.

---

### Subtask T020 – Verify tag visibility and smoke-test consumer import from tag

**Purpose**: SC-001 and SC-006 require that consumers can install from `v2.4.0`
without local patching. This smoke-test proves the tag is correctly structured.

**Steps**:

1. Verify tag visibility from any clone context:

```bash
git ls-remote --tags origin | grep v2.4.0
# Must show: <SHA>    refs/tags/v2.4.0
```

2. Verify `CHANGELOG.md` content at the tag:

```bash
git show v2.4.0:CHANGELOG.md | grep -A 3 "2\.4\.0"
# Must show the v2.4.0 section header
```

3. Verify the four contracts are present in `__init__.py` at the tag:

```bash
git show v2.4.0:src/spec_kitty_events/__init__.py | grep -E "MissionDossier"
# Must list: MissionDossierArtifactIndexed, MissionDossierArtifactMissing,
#            MissionDossierSnapshotComputed, MissionDossierParityDriftDetected
```

4. Consumer import smoke-test (local editable install is already at the tagged state):

```bash
python3.11 -c "
from spec_kitty_events import (
    MissionDossierArtifactIndexed,
    MissionDossierArtifactMissing,
    MissionDossierSnapshotComputed,
    MissionDossierParityDriftDetected,
    reduce_mission_dossier,
)
print('All dossier exports importable: ok')
"
```

**Expected output**: `All dossier exports importable: ok`

**If the import fails**: Check `src/spec_kitty_events/__init__.py` at the tag for
the dossier export block. If absent, the cherry-pick may have not included the
`__init__.py` changes. This requires a hotfix commit, re-tag, and re-push.

**Files**: No source files modified.

**Parallel?**: No — must follow T019.

---

## Test Strategy

WP03 does not run new tests. All test validation happened in WP02. WP03 performs:
- CI confirmation (T015 — CI reruns the full suite on `origin`)
- Import smoke-test (T020 — validates the exported API surface)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| CI fails on unrelated pre-existing issue | Document + release manager waiver required before merge |
| CI fails on dossier-specific issue | Fix on integration branch, push, re-run CI |
| CHANGELOG v2.4.0 section absent after merge | Recover from `git show 5237894 -- CHANGELOG.md`, add manually, commit before tagging |
| Tag collision (v2.4.0 already exists) | STOP — do not overwrite; coordinate with release manager; investigate correct version |
| Consumer import fails from fresh install | Check `__init__.py` at tag; if export block missing, hotfix commit + re-tag |
| `gh` commands fail with scope errors | Prefix with `unset GITHUB_TOKEN &&` to use keyring token |
| `origin/2.x` received new commits before merge | Rebase `009-dossier-release` on `origin/2.x`, re-run WP02 local gate, then retry PR |

---

## Review Guidance

- Confirm merge strategy was **merge commit** (not squash) — check `git log --merges -1` on `2.x`.
- Confirm `v2.4.0` tag points to the merge commit SHA (not the integration branch HEAD).
- Confirm tag is annotated: `git cat-file -t v2.4.0` returns `tag` (not `commit`).
- Confirm CHANGELOG at `v2.4.0` lists all four contracts and the namespace fix.
- Confirm smoke-test import output is `All dossier exports importable: ok`.
- Confirm `git ls-remote --tags origin v2.4.0` returns a SHA.

---

## Activity Log

- 2026-02-23T17:55:00Z – system – lane=planned – Prompt created.
