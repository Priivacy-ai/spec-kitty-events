# Implementation Plan: Dossier Contracts Remote Baseline Release

**Branch**: `009-dossier-contracts-remote-baseline-release` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/009-dossier-contracts-remote-baseline-release/spec.md`

## Summary

Recover the complete Feature 008 dossier contract implementation from the local git
reflog (commits `5237894` + `139ca09`), integrate it onto a PR branch sourced from
the current `origin/2.x` HEAD (which already includes `640709f`), pass all quality
gates locally, merge via PR, and cut the `v2.4.0` release tag from the merged commit
on `origin/2.x`. Integration strategy: **PR-first**. Fallback to Path B
(re-implementation from the Feature 008 spec) only if cherry-pick or test gates fail.

## Technical Context

**Language/Version**: Python 3.11 (pip, pytest, mypy target); Python 3.14 (system default — do not use)
**Primary Dependencies**: Pydantic v2, jsonschema≥4.21,<5 (`[conformance]` extra), pytest, hypothesis
**Storage**: N/A (no new storage — this is a promotion/release operation)
**Testing**: `python3.11 -m pytest` with `--cov=src/spec_kitty_events`; `mypy --strict`
**Target Platform**: Linux CI + local macOS development
**Project Type**: Single Python library (`src/` layout, editable install)
**Performance Goals**: Full test suite completes in ≤120s; no individual test ≥5s
**Constraints**: mypy --strict zero new errors; coverage ≥98% on `dossier.py`; ≥1,117 tests pass
**Scale/Scope**: 41 files recovered, 3,116 lines; four new event contracts; thirteen conformance fixtures

## Constitution Check

*Constitution file not present — section skipped.*

## Integration Strategy

```
origin/2.x (640709f)
    │
    └── branch: 009-dossier-release
            │
            ├── cherry-pick 5237894  (feat(008): merge Mission Dossier Parity Event Contracts)
            └── cherry-pick 139ca09  (fix(dossier): namespace mismatch false-positive)
                    │
                    └── [local gate: tests + mypy + conformance]
                            │
                            └── PR: 009-dossier-release → 2.x
                                    │
                                    └── [CI gate] → merge → v2.4.0 tag
```

`640709f` (docs: add security position statement) is already an ancestor of the
branch base (`origin/2.x` HEAD), so it is automatically included in the PR and
the final merge commit. No explicit cherry-pick of `640709f` is needed.

## Path B Trigger Conditions

If any of the following occur, abandon Path A and open a new spec-kitty.plan for
Path B (re-implementation using Feature 008 spec recovered from reflog):

1. Cherry-pick of `5237894` or `139ca09` produces unresolvable conflicts.
2. Test suite fails with errors attributable to the recovered code (not upstream).
3. `mypy --strict` reports new errors in recovered files with no clean fix.
4. Coverage on `dossier.py` drops below 95% and cannot be restored without new tests.

## Project Structure

### Documentation (this feature)

```
kitty-specs/009-dossier-contracts-remote-baseline-release/
├── plan.md           ← this file
├── research.md       ← Phase 0 output (recovery context)
└── tasks.md          ← Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (recovered from reflog, not authored here)

```
src/spec_kitty_events/
├── __init__.py                    # +47 lines: dossier exports block
├── dossier.py                     # NEW: 422 lines — contracts, reducer, namespace logic
└── schemas/
    ├── artifact_identity.schema.json
    ├── content_hash_ref.schema.json
    ├── local_namespace_tuple.schema.json
    ├── mission_dossier_artifact_indexed_payload.schema.json
    ├── mission_dossier_artifact_missing_payload.schema.json
    ├── mission_dossier_parity_drift_detected_payload.schema.json
    ├── mission_dossier_snapshot_computed_payload.schema.json
    └── provenance_ref.schema.json

src/spec_kitty_events/conformance/fixtures/dossier/
├── valid/      (9 JSON fixtures)
├── invalid/    (2 JSON fixtures)
└── replay/     (2 JSONL scenario files)

tests/
├── test_dossier_conformance.py    # NEW: 145 lines
└── test_dossier_reducer.py        # NEW/EXTENDED: 426+ lines
```

**Structure Decision**: No new directories created. Recovery populates existing `schemas/`
and `conformance/fixtures/` locations consistent with prior features (005–008).

## Work Packages

### WP01 — Integration Branch Setup & Recovery

**Goal**: Cherry-pick the Feature 008 implementation onto a clean branch from `origin/2.x`.

**Inputs**: Local git reflog with commits `5237894` and `139ca09` still accessible.

**Steps**:

1. Verify reflog accessibility:
   ```
   git show 5237894 --stat    # must succeed
   git show 139ca09 --stat    # must succeed
   ```

2. Create integration branch from current `origin/2.x` HEAD:
   ```
   git checkout -b 009-dossier-release origin/2.x
   ```

3. Cherry-pick the feature 008 merge commit:
   ```
   git cherry-pick 5237894
   ```
   Expected: clean apply. If conflicts arise → trigger Path B.

4. Cherry-pick the namespace mismatch fix:
   ```
   git cherry-pick 139ca09
   ```
   Expected: clean apply (touches only `dossier.py` and `tests/test_dossier_reducer.py`).

5. Confirm `640709f` is an ancestor:
   ```
   git merge-base --is-ancestor 640709f HEAD && echo "included"
   ```
   Must print `included`. If not, cherry-pick `640709f` before proceeding.

**Exit criteria**: Branch `009-dossier-release` exists locally with both commits applied
cleanly and `640709f` confirmed as ancestor.

---

### WP02 — Local Verification Gate

**Goal**: Prove the recovered implementation is correct before opening the PR.

**Inputs**: WP01 complete (branch `009-dossier-release` with commits applied).

**Steps**:

1. Install in editable mode (if not current):
   ```
   pip install -e ".[dev,conformance]"
   ```

2. Run full test suite:
   ```
   python3.11 -m pytest
   ```
   Gate: ≥1,117 tests, 0 failures, 0 errors. Coverage on `dossier.py` ≥98%.

3. Run mypy strict check:
   ```
   mypy --strict src/spec_kitty_events/
   ```
   Gate: 0 new errors (pre-existing baseline errors are acceptable only if they
   existed on `origin/2.x` HEAD before the cherry-picks).

4. Validate conformance fixtures explicitly:
   ```
   python3.11 -m pytest tests/test_dossier_conformance.py -v
   ```
   Gate: All 9 valid fixtures pass; both invalid fixtures rejected with named errors.

5. Validate replay scenarios:
   ```
   python3.11 -m pytest tests/test_dossier_reducer.py -v -k "replay"
   ```
   Gate: Both replay scenarios produce deterministic `MissionDossierState`.

6. Push integration branch to origin:
   ```
   git push -u origin 009-dossier-release
   ```

**Exit criteria**: All gates pass; `origin/009-dossier-release` exists and is current.

**Fallback**: If tests fail due to recovered code errors, assess Path B trigger
conditions. If failures are due to upstream changes in `origin/2.x`, adapt the
cherry-picks and document the delta.

---

### WP03 — PR, CI Gate, Merge & Release Tag

**Goal**: Get the recovery onto `origin/2.x` with full traceability, then cut `v2.4.0`.

**Inputs**: WP02 complete; `origin/009-dossier-release` pushed and gates green.

**Steps**:

1. Open PR: `009-dossier-release` → `2.x`
   - Title: `feat(008): promote dossier contracts to remote baseline (v2.4.0)`
   - Body: reference FR-001–FR-009, link to commits `5237894` and `139ca09`

2. Wait for CI to pass on the PR branch (all checks green).

3. Merge PR into `2.x` (merge commit, not squash — preserve attribution).

4. Fetch merged state locally:
   ```
   git checkout 2.x && git pull origin 2.x
   ```

5. Verify `CHANGELOG.md` at HEAD contains the 2.4.0 section listing all four
   dossier contracts and the namespace-mismatch fix. If not present (cherry-pick
   omitted it), add the CHANGELOG entry in a follow-up commit before tagging.

6. Create annotated tag from `2.x` HEAD:
   ```
   git tag -a v2.4.0 -m "Release v2.4.0: Mission Dossier Parity Event Contracts"
   git push origin v2.4.0
   ```

7. Verify tag on origin:
   ```
   git ls-remote --tags origin v2.4.0   # must return SHA
   git show v2.4.0 --stat               # must show merge commit + dossier files
   ```

8. Smoke-test consumer import (from any machine without local dossier.py):
   ```
   pip install "spec-kitty-events @ git+https://github.com/…@v2.4.0"
   python -c "from spec_kitty_events import MissionDossierArtifactIndexed; print('ok')"
   ```

**Exit criteria**: Tag `v2.4.0` visible on `origin`; consumer import succeeds;
CHANGELOG entry present at tagged commit.

## Quality Gates Summary

| Gate | WP | Criterion | Blocking? |
|------|----|-----------|-----------|
| Reflog accessible | WP01 | `git show 5237894` succeeds | Yes → abort |
| Cherry-picks clean | WP01 | No unresolvable conflicts | Yes → Path B |
| Tests pass | WP02 | ≥1,117 tests, 0 failures | Yes |
| Coverage | WP02 | ≥98% on `dossier.py` | Yes |
| mypy strict | WP02 | 0 new errors | Yes |
| Conformance fixtures | WP02 | 9 valid pass, 2 invalid reject | Yes |
| Replay determinism | WP02 | Both scenarios deterministic | Yes |
| CI green | WP03 | All CI checks pass on PR | Yes |
| Tag visible on origin | WP03 | `git ls-remote` returns SHA | Yes |
| Consumer importable | WP03 | Fresh install import succeeds | Yes |

## Complexity Tracking

*No constitution violations to justify — this is a recovery/release operation with
no new architectural patterns beyond those established in features 001–008.*
