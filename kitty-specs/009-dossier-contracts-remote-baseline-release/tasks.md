# Work Packages: Dossier Contracts Remote Baseline Release

**Inputs**: Design documents from `kitty-specs/009-dossier-contracts-remote-baseline-release/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓

**Strategy**: Path A — recover Feature 008 implementation from git reflog, integrate
onto `009-dossier-release` branch from `origin/2.x`, pass all local quality gates,
merge via PR, cut `v2.4.0` tag from the `2.x` merge commit.

**Sequence**: WP01 → WP02 → WP03 (strict serial — each gates the next).

**Path B fallback**: If cherry-pick conflicts or test failures cannot be resolved
cleanly, abandon Path A. Open a new plan for re-implementation from the Feature 008
spec (recoverable from reflog artifacts). Path B trigger conditions are documented
in `plan.md`.

---

## Work Package WP01: Integration Branch Setup & Recovery (Priority: P0)

**Goal**: Create `009-dossier-release` branch from `origin/2.x` HEAD and apply the
two Feature 008 commits cleanly via cherry-pick.

**Independent Test**: `git log --oneline 009-dossier-release` shows both
`5237894` (feat(008)) and `139ca09` (fix(dossier)) cherry-picked on top of `640709f`,
with no conflicts.

**Prompt**: `tasks/WP01-integration-branch-setup-and-recovery.md`

### Included Subtasks
- [x] T001 Verify reflog accessibility for both recovery commits
- [x] T002 Create `009-dossier-release` branch from `origin/2.x`
- [x] T003 Cherry-pick `5237894` (feat(008) merge commit)
- [x] T004 Cherry-pick `139ca09` (namespace mismatch fix)
- [x] T005 Confirm `640709f` is an ancestor of the branch
- [x] T006 Verify recovered file inventory matches expected 41-file set

### Implementation Notes
- Work directly in the main repo root (not a worktree)
- `640709f` is already in `origin/2.x` HEAD, so starting from `origin/2.x` automatically includes it
- Cherry-pick `5237894` first (it's the larger merge); `139ca09` touches only `dossier.py` and `test_dossier_reducer.py`
- If `5237894` cherry-pick produces conflicts: stop, document the conflict, trigger Path B

### Parallel Opportunities
- None — all steps are serial; each depends on the previous.

### Dependencies
- None (starting package).

### Risks & Mitigations
- **Reflog expiry**: If commits are not accessible, Path B is mandatory. Check immediately at T001.
- **Cherry-pick conflicts**: `640709f` is docs-only, so conflicts are unlikely; if they occur, investigate before forcing.

### Estimated Prompt Size
~290 lines

---

## Work Package WP02: Local Verification Gate (Priority: P0)

**Goal**: Prove the recovered implementation is correct and complete before the PR
is opened. All quality gates must be green.

**Independent Test**: `python3.11 -m pytest` reports ≥1,117 tests passed, 0 failed,
coverage on `dossier.py` ≥98%; `mypy --strict` reports 0 new errors; conformance
suite accepts 9 valid and rejects 2 invalid fixtures; both replay scenarios produce
the expected `MissionDossierState`.

**Prompt**: `tasks/WP02-local-verification-gate.md`

### Included Subtasks
- [x] T007 Install package with dev + conformance extras
- [x] T008 Run full pytest suite and verify count + zero failures
- [x] T009 Check coverage report for `dossier.py` (≥98%)
- [x] T010 Run `mypy --strict` and confirm zero new errors
- [x] T011 Run dossier conformance suite (valid fixtures pass, invalid rejected)
- [x] T012 Run replay scenario tests and verify deterministic state
- [x] T013 Push `009-dossier-release` to `origin`

### Implementation Notes
- Use `pip install -e ".[dev,conformance]"` (not plain `pip install -e .`)
- Commands must use `python3.11` explicitly (system `python` is 3.14)
- Coverage addopts are in `pyproject.toml` — no manual `--cov` flag needed
- For the conformance gate, run `python3.11 -m pytest tests/test_dossier_conformance.py -v`
- For the replay gate, run `python3.11 -m pytest tests/test_dossier_reducer.py -v -k "replay"`
- Push only after all local gates pass: `git push -u origin 009-dossier-release`

### Parallel Opportunities
- T009, T010 can run simultaneously after T008 completes (different tools, different output).

### Dependencies
- Depends on WP01.

### Risks & Mitigations
- **Test count below 1,117**: Indicates not all test files were recovered; inspect `git diff origin/2.x HEAD -- tests/`.
- **mypy errors in recovered files**: May indicate Pydantic v2 type annotation differences between reflog state and current mypy version; fix in a follow-up commit on the integration branch, document delta.
- **Coverage below threshold**: Add targeted tests on the integration branch; document additions in the PR description.

### Estimated Prompt Size
~330 lines

---

## Work Package WP03: PR, CI Gate, Merge & Release Tag (Priority: P0)

**Goal**: Land the dossier contracts on `origin/2.x` with full PR traceability and
publish the `v2.4.0` annotated tag from the merge commit.

**Independent Test**: `git ls-remote --tags origin v2.4.0` returns a SHA;
`python -c "from spec_kitty_events import MissionDossierArtifactIndexed; print('ok')"`
succeeds on a fresh install from the tag; `CHANGELOG.md` at `v2.4.0` contains the
2.4.0 release section.

**Prompt**: `tasks/WP03-pr-ci-merge-and-release-tag.md`

### Included Subtasks
- [x] T014 Open PR from `009-dossier-release` → `2.x` with structured description
- [x] T015 Monitor CI and confirm all checks pass
- [x] T016 Merge PR into `2.x` using merge commit (not squash)
- [x] T017 Verify `CHANGELOG.md` at `2.x` HEAD contains v2.4.0 section
- [x] T018 Create annotated `v2.4.0` tag from `2.x` HEAD
- [x] T019 Push `v2.4.0` tag to `origin`
- [x] T020 Verify tag visibility and smoke-test consumer import from tag

### Implementation Notes
- PR title: `feat(008): promote dossier contracts to remote baseline (v2.4.0)`
- Merge strategy: **merge commit** (not squash) to preserve attribution of individual cherry-picks
- Tag from `2.x` HEAD after pull: `git checkout 2.x && git pull origin 2.x && git tag -a v2.4.0 -m "Release v2.4.0: Mission Dossier Parity Event Contracts"`
- If CHANGELOG is missing the 2.4.0 section after merge (T017 fails): add it in a separate commit before tagging
- Smoke test uses `pip install "spec-kitty-events @ git+<repo-url>@v2.4.0"` — requires the tag to exist on origin first (T019 before T020)
- Tag push: `git push origin v2.4.0` (annotated tag, not `git push --tags`)

### Parallel Opportunities
- None — all steps are serial within this WP.

### Dependencies
- Depends on WP02.

### Risks & Mitigations
- **CI failure**: Investigate the specific failure; if caused by a pre-existing issue unrelated to dossier, document and seek a bypass waiver. If dossier-related, fix on the integration branch and force-push before re-review.
- **Tag collision**: If `v2.4.0` already exists on origin, do NOT overwrite. Coordinate with release manager to determine correct version.
- **CHANGELOG missing**: Cherry-pick captured the CHANGELOG addition in `5237894`; if absent, the cherry-pick may have dropped the file. Inspect with `git show HEAD -- CHANGELOG.md` and add manually.

### Estimated Prompt Size
~350 lines

---

## Dependency & Execution Summary

```
WP01 (Recovery) → WP02 (Local Gate) → WP03 (PR & Release)
```

- **Strict serial**: No parallelization across WPs.
- **Within WP02**: T009 (coverage) and T010 (mypy) can run simultaneously.
- **MVP Scope**: All three WPs constitute the MVP — the feature is not shippable until
  `v2.4.0` is tagged and visible on origin.
- **Stop-if-fail**: Any gate failure halts the sequence. The failing gate result
  determines whether to fix-and-retry or trigger Path B.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Verify reflog accessibility | WP01 | P0 | No |
| T002 | Create 009-dossier-release branch | WP01 | P0 | No |
| T003 | Cherry-pick 5237894 (feat(008)) | WP01 | P0 | No |
| T004 | Cherry-pick 139ca09 (namespace fix) | WP01 | P0 | No |
| T005 | Confirm 640709f is ancestor | WP01 | P0 | No |
| T006 | Verify recovered file inventory | WP01 | P0 | No |
| T007 | Install with dev+conformance extras | WP02 | P0 | No |
| T008 | Run full pytest suite | WP02 | P0 | No |
| T009 | Check dossier.py coverage ≥98% | WP02 | P0 | Yes (after T008) |
| T010 | Run mypy --strict, 0 new errors | WP02 | P0 | Yes (after T008) |
| T011 | Run dossier conformance suite | WP02 | P0 | No |
| T012 | Run replay scenario tests | WP02 | P0 | No |
| T013 | Push integration branch to origin | WP02 | P0 | No |
| T014 | Open PR 009-dossier-release → 2.x | WP03 | P0 | No |
| T015 | Monitor CI, confirm all checks pass | WP03 | P0 | No |
| T016 | Merge PR into 2.x (merge commit) | WP03 | P0 | No |
| T017 | Verify CHANGELOG v2.4.0 section | WP03 | P0 | No |
| T018 | Create annotated v2.4.0 tag | WP03 | P0 | No |
| T019 | Push v2.4.0 tag to origin | WP03 | P0 | No |
| T020 | Verify tag + smoke-test import | WP03 | P0 | No |

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
- WP02: done
- WP03: for_review
<!-- status-model:end -->
