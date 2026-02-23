# Research: Dossier Contracts Remote Baseline Release

**Feature**: 009-dossier-contracts-remote-baseline-release
**Date**: 2026-02-23
**Status**: Complete — no external research required

## Context

This feature is a recovery-and-promotion operation, not a greenfield implementation.
All technical decisions were resolved during spec and planning based on direct
inspection of the repository state (git log, reflog, source tree) and the Feature 008
implementation record. No external research tasks were generated.

---

## Decision 1: Recovery Strategy (Path A vs Path B)

**Decision**: Path A — recover commits from git reflog, cherry-pick onto integration branch.

**Rationale**:
- Commits `5237894` (feat(008) merge) and `139ca09` (namespace fix) are accessible
  in local reflog. The implementation is complete, passing 1,117 tests, with 41 files
  and 3,116 lines of carefully reviewed code.
- Re-implementation (Path B) would introduce avoidable risk (regression, drift) and
  delay without adding value.
- The wave goal is to ship a remote-visible baseline quickly.

**Alternatives considered**:
- **Path B (re-implement)**: Rejected — implementation exists and is verified.
- **Force-push local 2.x branch**: Rejected — would discard `640709f` (security
  position statement) already on `origin/2.x` and lose PR traceability.

---

## Decision 2: Integration Strategy (PR-first vs Direct Push)

**Decision**: PR-first — recover onto `009-dossier-release`, CI gate, merge via PR,
tag from `2.x` merge commit.

**Rationale**:
- Preserves traceability and review history for a baseline contract promotion.
- Ensures CI validates the recovered state before it becomes part of the permanent branch.
- Tag cut from the `2.x` merge commit (not from a side-branch SHA) matches the
  tagging convention used for prior releases (`v2.3.0`, `v2.3.1`).
- Direct push reserved for emergency production hotfixes only.

**Alternatives considered**:
- **Direct push to 2.x after local gate**: Rejected — baseline contract promotions
  require PR traceability, not just local test confidence.

---

## Decision 3: Handling of Upstream Commit 640709f

**Decision**: No explicit cherry-pick of `640709f` is needed. The integration branch
is based on `origin/2.x` HEAD, which is `640709f`. It is already an ancestor.

**Rationale**:
- `git checkout -b 009-dossier-release origin/2.x` starts from `640709f`.
- All cherry-picked commits land on top of it.
- A `git merge-base --is-ancestor 640709f HEAD` check in WP01 confirms inclusion
  before the local gate runs.

---

## Decision 4: Tag Target (Merge Commit vs Side-Branch SHA)

**Decision**: Tag `v2.4.0` is cut from the `2.x` merge commit, after the PR merges.

**Rationale**:
- Prior releases (`v2.3.0` at `dff7d07`, `v2.3.1` at `65320d6`) are tagged on
  `2.x` merge commits, not integration branch HEADs.
- Consumers pinning `v2.4.0` should receive the `2.x` canonical merge, not a
  side branch that may be deleted after the feature closes.

---

## Decision 5: CHANGELOG Entry Presence

**Decision**: Verify CHANGELOG.md at `2.x` HEAD before tagging. If the cherry-pick
of `5237894` did not include the 2.4.0 CHANGELOG section, add it in a follow-up
commit before cutting the tag.

**Rationale**:
- The feature 008 merge commit includes `CHANGELOG.md` additions for v2.4.0
  (94 lines per the merge stat). These should transfer cleanly via cherry-pick.
- If a conflict or omission occurs, a clean CHANGELOG commit is preferable to
  tagging without documentation.

---

## Key Reflog References

| Commit | Description | Status |
|--------|-------------|--------|
| `5237894` | feat(008): merge Mission Dossier Parity Event Contracts into 2.x | In reflog — accessible |
| `139ca09` | fix(dossier): namespace mismatch false-positive on step_id variance | In reflog — accessible |
| `640709f` | docs: add security position statement | On origin/2.x HEAD — already included |
| `65320d6` | feat: close contract gate with replay fixture stream (v2.3.1) | Tagged as v2.3.1 |

## Recovered Implementation Inventory

Sourced from `git show 5237894 --stat` + `git show 139ca09 --stat`:

| Category | Files | Lines |
|----------|-------|-------|
| Core contract module (`dossier.py`) | 1 new | 422 |
| Namespace fix + regression tests | 1 mod (dossier.py) + 1 mod (test_dossier_reducer.py) | +130 |
| JSON schemas | 8 new | ~1,000 |
| Conformance fixtures (valid) | 9 new JSON | ~200 |
| Conformance fixtures (invalid) | 2 new JSON | ~30 |
| Replay scenarios | 2 new JSONL | ~11 |
| Conformance manifest + loader | 2 mod | ~170 |
| Test files | 2 new | ~571 |
| CHANGELOG.md | 1 mod | +94 |
| pyproject.toml | 1 mod | +5 |
| `__init__.py` (exports) | 1 mod | +47 |
| **Total** | **41 files** | **~3,116** |
