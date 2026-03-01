# WP03 Release Readiness: PR, CI Gate, Merge & Release Tag

## Local Verifications Complete

| Subtask | Gate | Result |
|---------|------|--------|
| T017 | CHANGELOG.md has v2.4.0 section | **Present**: "2.4.0 — Mission Dossier Parity Event Contracts (2026-02-21)" |
| T018 | Annotated v2.4.0 tag created locally | **Done**: `git tag -a v2.4.0 -m "Release v2.4.0: Mission Dossier Parity Event Contracts"` |
| T020 | Smoke-test import | **Pass**: `from spec_kitty_events import MissionDossierArtifactIndexedPayload` succeeds |

## Deferred GitHub Steps

GitHub operations are deferred for this sprint. The items below are recorded
for a future release pass.

| Subtask | Action | Command |
|---------|--------|---------|
| T013 (WP02) | Push integration branch | `git push -u origin 009-dossier-release` |
| T014 | Open PR 009-dossier-release -> 2.x | `gh pr create --title "feat(008): promote dossier contracts to remote baseline (v2.4.0)" --base 2.x` |
| T015 | Monitor CI | `gh pr checks <PR-NUMBER>` |
| T016 | Merge PR (merge commit, not squash) | `gh pr merge <PR-NUMBER> --merge` |
| T019 | Push tag to origin | `git push origin v2.4.0` |
| T020 | Verify tag on origin | `git ls-remote --tags origin v2.4.0` |

## Release Checklist

- [x] `009-dossier-release` branch exists with both cherry-picks (WP01)
- [x] 1117 tests pass, 0 failures (WP02)
- [x] dossier.py 100% coverage (WP02)
- [x] mypy --strict: 0 issues (WP02)
- [x] 23/23 conformance tests pass (WP02)
- [x] 25/25 reducer tests pass (WP02)
- [x] CHANGELOG.md contains v2.4.0 section
- [x] Local v2.4.0 annotated tag created
- [x] `MissionDossierArtifactIndexedPayload` import smoke-test passes
- [ ] Push branch to origin (deferred)
- [ ] Open and merge PR (deferred)
- [ ] Push tag to origin (deferred)
