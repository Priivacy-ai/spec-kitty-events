---
work_package_id: WP03
title: PR, CI Gate, Merge & Release Tag
lane: "for_review"
dependencies:
- WP02
base_branch: 2.x
base_commit: 1385b17bd3d4edfc30bd6d8adc321376ec9f5aa9
created_at: '2026-02-23T18:55:02.075410+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
phase: Phase 3 - Release
assignee: ''
agent: codex
shell_pid: '24900'
review_status: has_feedback
reviewed_by: Robert Douglass
history:
- timestamp: '2026-02-23T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated from tasks.md
review_feedback_file: /private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-review-feedback-WP03.md
---

# Work Package Prompt: WP03 – PR, CI Gate, Merge & Release Tag

## Context

Continues from WP02. The `009-dossier-release` branch has passed all local quality
gates and is pushed to origin. This WP lands the dossier contracts on `origin/2.x`
with full PR traceability and publishes the `v2.4.0` annotated tag.

**Prerequisite**: WP02 complete — all local gates green, branch pushed to origin.

## Goal

Land the dossier contracts on `origin/2.x` with full PR traceability and publish
the `v2.4.0` annotated tag from the merge commit.

**Independent Test**: `git ls-remote --tags origin v2.4.0` returns a SHA;
`python -c "from spec_kitty_events import MissionDossierArtifactIndexed; print('ok')"`
succeeds on a fresh install from the tag; `CHANGELOG.md` at `v2.4.0` contains the
2.4.0 release section.

## Subtasks

- [ ] T014 Open PR from `009-dossier-release` → `2.x` with structured description
- [ ] T015 Monitor CI and confirm all checks pass
- [ ] T016 Merge PR into `2.x` using merge commit (not squash)
- [ ] T017 Verify `CHANGELOG.md` at `2.x` HEAD contains v2.4.0 section
- [ ] T018 Create annotated `v2.4.0` tag from `2.x` HEAD
- [ ] T019 Push `v2.4.0` tag to `origin`
- [ ] T020 Verify tag visibility and smoke-test consumer import from tag

## Implementation Notes

- PR title: `feat(008): promote dossier contracts to remote baseline (v2.4.0)`
- Merge strategy: **merge commit** (not squash) to preserve attribution of
  individual cherry-picks
- Tag from `2.x` HEAD after pull:
  ```
  git checkout 2.x && git pull origin 2.x
  git tag -a v2.4.0 -m "Release v2.4.0: Mission Dossier Parity Event Contracts"
  ```
- If CHANGELOG is missing the 2.4.0 section after merge (T017 fails): add it
  in a separate commit before tagging
- Smoke test uses `pip install "spec-kitty-events @ git+<repo-url>@v2.4.0"` —
  requires the tag to exist on origin first (T019 before T020)
- Tag push: `git push origin v2.4.0` (annotated tag, not `git push --tags`)

## Parallel Opportunities

None — all steps are serial within this WP.

## Dependencies

- Depends on WP02.

## Risks & Mitigations

- **CI failure**: Investigate the specific failure; if caused by a pre-existing
  issue unrelated to dossier, document and seek a bypass waiver. If dossier-related,
  fix on the integration branch and force-push before re-review.
- **Tag collision**: If `v2.4.0` already exists on origin, do NOT overwrite.
  Coordinate with release manager to determine correct version.
- **CHANGELOG missing**: Cherry-pick captured the CHANGELOG addition in `5237894`;
  if absent, the cherry-pick may have dropped the file. Inspect with
  `git show HEAD -- CHANGELOG.md` and add manually.

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-23
**Feedback file**: `/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-review-feedback-WP03.md`

**Issue 1**: WP03 requires remote GitHub operations (PR creation, CI checks, merge, tag push, tag verification) but these are only documented as manual steps and not executed. The WP03 goal and independent test are not met without `git ls-remote --tags origin v2.4.0` and a merged PR. Please complete T014–T020 when GitHub access is permitted or explicitly defer them in the WP03 scope.

**Issue 2**: WP03 readiness log includes T013 (push integration branch) even though T013 is WP02 and currently deferred. This dependency should be resolved before proceeding with WP03; either complete T013 in WP02 or adjust WP03 prerequisites to reflect the deferred push.


## Activity Log

- 2026-02-23T18:55:02Z – claude-code – shell_pid=75837 – lane=doing – Assigned agent via workflow command
- 2026-02-23T18:56:22Z – claude-code – shell_pid=75837 – lane=for_review – Release readiness verified locally: CHANGELOG v2.4.0 present, local tag created, import smoke-test passes. GitHub operations (push, PR, merge, tag push) documented as manual steps.
- 2026-02-23T18:57:19Z – codex – shell_pid=24900 – lane=doing – Started review via workflow command
- 2026-02-23T18:57:39Z – codex – shell_pid=24900 – lane=planned – Moved to planned
- 2026-02-23T19:01:25Z – codex – shell_pid=24900 – lane=for_review – Deferred GitHub operations; local readiness documented
