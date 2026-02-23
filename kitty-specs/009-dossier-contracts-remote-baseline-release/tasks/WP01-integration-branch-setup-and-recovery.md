---
work_package_id: WP01
title: Integration Branch Setup & Recovery
lane: "for_review"
dependencies: []
base_branch: main
base_commit: 5a24a93249042fe1abba402a2768d4471ed93d33
created_at: '2026-02-23T18:21:35.828350+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Recovery
assignee: ''
agent: claude-code
shell_pid: '7051'
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-23T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated from tasks.md
---

# Work Package Prompt: WP01 – Integration Branch Setup & Recovery

## Context

Feature 009 recovers the Feature 008 dossier contracts implementation from git
reflog and integrates it onto a new branch from `origin/2.x`. This is a
strict serial pipeline: WP01 → WP02 → WP03.

**Strategy**: Path A — recover Feature 008 implementation from git reflog,
integrate onto `009-dossier-release` branch from `origin/2.x`, pass all local
quality gates, merge via PR, cut `v2.4.0` tag from the `2.x` merge commit.

**Path B fallback**: If cherry-pick conflicts or test failures cannot be
resolved cleanly, abandon Path A. Open a new plan for re-implementation from
the Feature 008 spec (recoverable from reflog artifacts). Path B trigger
conditions are documented in `plan.md`.

## Goal

Create `009-dossier-release` branch from `origin/2.x` HEAD and apply the
two Feature 008 commits cleanly via cherry-pick.

**Independent Test**: `git log --oneline 009-dossier-release` shows both
`5237894` (feat(008)) and `139ca09` (fix(dossier)) cherry-picked on top of
`640709f`, with no conflicts.

## Subtasks

- [ ] T001 Verify reflog accessibility for both recovery commits
- [ ] T002 Create `009-dossier-release` branch from `origin/2.x`
- [ ] T003 Cherry-pick `5237894` (feat(008) merge commit)
- [ ] T004 Cherry-pick `139ca09` (namespace mismatch fix)
- [ ] T005 Confirm `640709f` is an ancestor of the branch
- [ ] T006 Verify recovered file inventory matches expected 41-file set

## Implementation Notes

- Work directly in the main repo root (not a worktree)
- `640709f` is already in `origin/2.x` HEAD, so starting from `origin/2.x`
  automatically includes it
- Cherry-pick `5237894` first (it's the larger merge commit); `139ca09`
  touches only `dossier.py` and `test_dossier_reducer.py`
- If `5237894` cherry-pick produces conflicts: stop, document the conflict,
  trigger Path B

## Parallel Opportunities

None — all steps are serial; each depends on the previous.

## Dependencies

None (starting package).

## Risks & Mitigations

- **Reflog expiry**: If commits are not accessible, Path B is mandatory. Check
  immediately at T001.
- **Cherry-pick conflicts**: `640709f` is docs-only, so conflicts are unlikely;
  if they occur, investigate before forcing.

## Activity Log

- 2026-02-23T18:21:36Z – claude-code – shell_pid=7051 – lane=doing – Assigned agent via workflow command
- 2026-02-23T18:24:20Z – claude-code – shell_pid=7051 – lane=for_review – Ready for review: 009-dossier-release branch created from origin/2.x with 5237894 and 139ca09 cherry-picked cleanly. 35 source files recovered (dossier.py, tests, schemas, fixtures). Branch at e8b9feb.
