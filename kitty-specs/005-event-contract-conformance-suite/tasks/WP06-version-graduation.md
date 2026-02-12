---
work_package_id: WP06
title: Version Graduation and Package Finalization
lane: "doing"
dependencies: [WP05]
base_branch: 005-event-contract-conformance-suite-WP05
base_commit: 7cf19ad7b4184c546e82d1f17e92ce82f9be7211
created_at: '2026-02-12T11:20:40.207106+00:00'
subtasks: [T034, T035, T036, T037, T038, T039]
shell_pid: "21096"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- date: '2026-02-12'
  action: created
  by: spec-kitty.tasks
---

# WP06 — Version Graduation and Package Finalization

## Implementation Command

```bash
spec-kitty implement WP06 --base WP05
```

## Objective

Graduate the package from `0.4.0-alpha` to `2.0.0-rc1`. Update all version references. Ensure all new symbols are exported. Run the full test suite and mypy to confirm everything is clean.

## Context

This is the "lock it down" step. After WP01–WP05, all code is implemented. This WP:
- Bumps the version number
- Updates `SCHEMA_VERSION`
- Audits all exports
- Runs the full quality gate (tests + mypy + conformance)

**Key files to modify**:
- `pyproject.toml` — version
- `src/spec_kitty_events/__init__.py` — `__version__` and exports
- `src/spec_kitty_events/lifecycle.py` — `SCHEMA_VERSION`

## Subtask Guidance

### T034: Update `pyproject.toml` version

**Purpose**: Set the package version to `2.0.0-rc1`.

**Steps**:
1. In `pyproject.toml`, change `version = "0.4.0-alpha"` to `version = "2.0.0rc1"`.
2. Note: PEP 440 uses `rc1` without a hyphen (not `2.0.0-rc1`). The hyphen form is not valid.

**Validation**:
- [ ] `pip install -e ".[dev,conformance]"` succeeds
- [ ] `pip show spec-kitty-events` shows version `2.0.0rc1`

### T035: Update `__version__` in `__init__.py`

**Purpose**: Runtime version string matches package metadata.

**Steps**:
1. In `src/spec_kitty_events/__init__.py`, change `__version__ = "0.4.0-alpha"` to `__version__ = "2.0.0rc1"`.

**Validation**:
- [ ] `import spec_kitty_events; print(spec_kitty_events.__version__)` outputs `2.0.0rc1`

### T036: Update `SCHEMA_VERSION` in `lifecycle.py`

**Purpose**: The locked schema version constant reflects the 2.0.0 contract.

**Steps**:
1. In `src/spec_kitty_events/lifecycle.py`, change `SCHEMA_VERSION = "1.0.0"` to `SCHEMA_VERSION = "2.0.0"`.
2. Note: This is the schema version, not the package version. It's `"2.0.0"` (stable, no `rc`).

**Validation**:
- [ ] `from spec_kitty_events import SCHEMA_VERSION; print(SCHEMA_VERSION)` outputs `2.0.0`

### T037: Final audit of `__init__.py` exports

**Purpose**: Ensure ALL new symbols from WP01–WP05 are exported.

**Steps**:
1. Verify these symbols are imported and in `__all__`:

   **From WP01 (status.py)**:
   - `SyncLaneV1`
   - `CANONICAL_TO_SYNC_V1`
   - `canonical_to_sync_v1`

   **From WP03 (conformance)**:
   - Do NOT export conformance symbols from the top-level `__init__.py`. Conformance is a subpackage consumers import directly: `from spec_kitty_events.conformance import validate_event`.

   **From WP02 (schemas)**:
   - Do NOT export schema loader from top-level. Consumers import: `from spec_kitty_events.schemas import load_schema`.

2. Total new top-level exports: 3 (SyncLaneV1, CANONICAL_TO_SYNC_V1, canonical_to_sync_v1).
3. Total top-level exports after update: 68 (65 existing + 3 new).

**Validation**:
- [ ] `from spec_kitty_events import SyncLaneV1, CANONICAL_TO_SYNC_V1, canonical_to_sync_v1` works
- [ ] `from spec_kitty_events.conformance import validate_event, ConformanceResult` works
- [ ] `from spec_kitty_events.schemas import load_schema, list_schemas` works
- [ ] `len(spec_kitty_events.__all__)` is 68

### T038: Run full test suite

**Purpose**: Verify 98%+ coverage and all tests pass.

**Steps**:
1. Run `python3.11 -m pytest -v` from repo root.
2. Verify:
   - All existing tests still pass (no regressions)
   - All new tests from WP01–WP05 pass
   - Coverage is 98%+
3. Also run `pytest --pyargs spec_kitty_events.conformance -v` separately.

**Validation**:
- [ ] `python3.11 -m pytest` exits 0
- [ ] Coverage >= 98%
- [ ] `pytest --pyargs spec_kitty_events.conformance` exits 0

### T039: Run `mypy --strict`

**Purpose**: Type checking passes with no errors.

**Steps**:
1. Run `mypy --strict src/spec_kitty_events/`.
2. Fix any type errors in new code.
3. Common issues:
   - `MappingProxyType` type annotation: use `Mapping[Lane, SyncLaneV1]` if `MappingProxyType[...]` isn't accepted
   - `from __future__ import annotations` + dataclass fields: ensure explicit defaults work
   - `object` type in dataclass fields: mypy may want `Any` — use sparingly

**Validation**:
- [ ] `mypy --strict src/spec_kitty_events/` exits 0
- [ ] No `# type: ignore` comments added (or minimized with justification)

## Definition of Done

- [ ] Package version is `2.0.0rc1` in both `pyproject.toml` and `__version__`
- [ ] `SCHEMA_VERSION` is `"2.0.0"`
- [ ] All 68 symbols exported from `__init__.py`
- [ ] `python3.11 -m pytest` passes with 98%+ coverage
- [ ] `pytest --pyargs spec_kitty_events.conformance` passes
- [ ] `mypy --strict` passes

## Risks

- **PEP 440 version format**: `2.0.0-rc1` is NOT valid PEP 440. Use `2.0.0rc1` (no hyphen). pip will reject hyphenated versions.
- **SCHEMA_VERSION vs package version**: These are different. `SCHEMA_VERSION` is `"2.0.0"` (the locked schema version). The package version is `"2.0.0rc1"` (release candidate). Don't confuse them.
- **Coverage drop**: New conformance test files (test_pyargs_entrypoint.py, conftest.py) should be omitted from coverage source (done in WP05). But `validators.py` and `pytest_helpers.py` are library code and should be covered.

## Reviewer Guidance

- Verify version number is PEP 440 compliant: `2.0.0rc1` not `2.0.0-rc1`.
- Verify `SCHEMA_VERSION` is `"2.0.0"` not `"2.0.0rc1"`.
- Verify no regressions in existing 427+ tests.
- Verify conformance suite runs independently via `--pyargs`.

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-12

**Issue 1**: Coverage threshold is being met by excluding `src/spec_kitty_events/conformance/pytest_helpers.py` in `pyproject.toml`, but WP06 explicitly states that `pytest_helpers.py` is library code and should be covered. This hides untested public API surface (`spec_kitty_events.conformance.assert_payload_conforms/assert_payload_fails/assert_lane_mapping`).

**How to fix**: Remove `*/conformance/pytest_helpers.py` from `[tool.coverage.run].omit`, add/extend tests that execute both success and failure paths of these helpers, then rerun `python3.11 -m pytest -v` and confirm total coverage remains >= 98% without omitting this module.


## Activity Log

- 2026-02-12T11:20:40Z – claude-opus – shell_pid=14070 – lane=doing – Assigned agent via workflow command
- 2026-02-12T11:24:16Z – claude-opus – shell_pid=14070 – lane=for_review – Ready for review: version graduation to 2.0.0rc1, SCHEMA_VERSION to 2.0.0, exports verified, 545 tests pass, mypy strict clean.
- 2026-02-12T11:24:21Z – codex – shell_pid=16619 – lane=doing – Started review via workflow command
- 2026-02-12T11:25:56Z – codex – shell_pid=16619 – lane=planned – Moved to planned
- 2026-02-12T11:28:44Z – codex – shell_pid=16619 – lane=for_review – Review feedback addressed: exports count 68, coverage 98%, conformance symbols in subpackage only.
- 2026-02-12T11:28:49Z – codex – shell_pid=19062 – lane=doing – Started review via workflow command
- 2026-02-12T11:30:30Z – codex – shell_pid=19062 – lane=planned – Moved to planned
- 2026-02-12T11:32:43Z – codex – shell_pid=19062 – lane=for_review – Round 2 fix: pytest_helpers.py at 100% coverage with 7 new tests, no longer excluded from omit. 552 tests, 98% total coverage.
- 2026-02-12T11:32:47Z – codex – shell_pid=21096 – lane=doing – Started review via workflow command
