---
work_package_id: WP04
title: Canonical Fixtures and Manifest
lane: "for_review"
dependencies: [WP03]
base_branch: 005-event-contract-conformance-suite-WP03
base_commit: 57c9ad089e6fb61d491586822a2e55354179f1e7
created_at: '2026-02-12T10:54:01.027042+00:00'
subtasks: [T021, T022, T023, T024, T025, T026, T027, T028]
shell_pid: "3104"
agent: "claude-opus"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- date: '2026-02-12'
  action: created
  by: spec-kitty.tasks
---

# WP04 — Canonical Fixtures and Manifest

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

## Objective

Create the fixture directory structure with valid/invalid JSON fixtures for all event types, lane mappings, and edge cases. Create `manifest.json` with expectations. Implement `load_fixtures()` and `FixtureCase` in the conformance package.

## Context

Fixtures serve two purposes:
1. **Conformance testing**: The pytest entry point (WP05) reads the manifest and validates each fixture.
2. **Cross-repo CI**: Consumers can load fixtures to test their own payload handling.

Each fixture category has `valid/` and `invalid/` subdirectories. The `manifest.json` declares expectations so tests are data-driven.

**Key files to create**:
- `src/spec_kitty_events/conformance/fixtures/` directory tree
- Multiple `.json` fixture files
- `src/spec_kitty_events/conformance/fixtures/manifest.json`

**Key files to modify**:
- `src/spec_kitty_events/conformance/__init__.py` — add `load_fixtures`, `FixtureCase`
- `pyproject.toml` — verify package-data glob includes fixtures

## Subtask Guidance

### T021: Create fixture directory structure

**Purpose**: Establish the flat valid/invalid split for each fixture category.

**Steps**:
1. Create directories:
   ```
   src/spec_kitty_events/conformance/fixtures/
   src/spec_kitty_events/conformance/fixtures/events/valid/
   src/spec_kitty_events/conformance/fixtures/events/invalid/
   src/spec_kitty_events/conformance/fixtures/lane_mapping/valid/
   src/spec_kitty_events/conformance/fixtures/lane_mapping/invalid/
   src/spec_kitty_events/conformance/fixtures/edge_cases/valid/
   src/spec_kitty_events/conformance/fixtures/edge_cases/invalid/
   ```
2. Add `__init__.py` to `fixtures/` (empty, needed for package discovery).

**Validation**:
- [ ] All 7 directories exist
- [ ] `__init__.py` exists in `fixtures/`

### T022: Create valid event fixtures for all 9 conformance payload types

**Purpose**: One valid JSON file per conformance payload type, used as positive tests.

**Steps**:
1. For each event type, create a minimal valid payload dict using the Pydantic model's required fields.
2. Files to create (all in `fixtures/events/valid/`):
   - `event.json` — valid `Event` with all required fields including `correlation_id`, `schema_version`
   - `wp_status_changed.json` — valid `StatusTransitionPayload` with `feature_slug`, `wp_id`, `to_lane`, `actor`, `execution_mode`
   - `gate_passed.json` — valid `GatePassedPayload`
   - `gate_failed.json` — valid `GateFailedPayload`
   - `mission_started.json` — valid `MissionStartedPayload`
   - `mission_completed.json` — valid `MissionCompletedPayload`
   - `mission_cancelled.json` — valid `MissionCancelledPayload`
   - `phase_entered.json` — valid `PhaseEnteredPayload`
   - `review_rollback.json` — valid `ReviewRollbackPayload`

**Approach**: Use `ModelClass(**kwargs).model_dump(mode="json")` in a helper script or construct by hand. Ensure ULID fields are valid 26-char strings, timestamps are ISO format, etc.

**Validation**:
- [ ] 9 valid fixture files are present in `fixtures/events/valid/`
- [ ] Each fixture file is valid JSON
- [ ] Each fixture validates against its Pydantic model (i.e., `Model.model_validate(fixture_data)` succeeds)

### T023: Create invalid event fixtures

**Purpose**: Negative test cases that MUST fail validation.

**Steps**:
1. Create files in `fixtures/events/invalid/`:
   - `event_missing_correlation_id.json` — Event payload without `correlation_id`
   - `event_invalid_lamport_clock.json` — Event with `lamport_clock: -1`
   - `wp_status_changed_invalid_lane.json` — payload with `to_lane: "in_review"` (not a valid lane)
   - `wp_status_changed_force_no_reason.json` — payload with `force: true` but no `reason`
   - `gate_failed_invalid_conclusion.json` — payload with `conclusion: "success"` on GateFailed
2. Each file should trigger at least one specific, testable violation.

**Validation**:
- [ ] Each fixture fails Pydantic `model_validate()` with a specific error
- [ ] Error messages are predictable for test assertions

### T024: Create lane mapping fixtures

**Purpose**: Test data for the 7→4 mapping contract.

**Steps**:
1. Create `fixtures/lane_mapping/valid/all_canonical_to_sync_v1.json`:
   ```json
   [
     {"canonical": "planned", "expected_sync": "planned"},
     {"canonical": "claimed", "expected_sync": "planned"},
     {"canonical": "in_progress", "expected_sync": "doing"},
     {"canonical": "for_review", "expected_sync": "for_review"},
     {"canonical": "done", "expected_sync": "done"},
     {"canonical": "blocked", "expected_sync": "doing"},
     {"canonical": "canceled", "expected_sync": "planned"}
   ]
   ```
2. Create `fixtures/lane_mapping/invalid/unknown_lanes.json`:
   ```json
   [
     {"canonical": "in_review", "expected_error": "not a valid Lane"},
     {"canonical": "paused", "expected_error": "not a valid Lane"},
     {"canonical": "", "expected_error": "not a valid Lane"}
   ]
   ```

**Validation**:
- [ ] Valid fixture has exactly 7 entries (one per Lane)
- [ ] Invalid fixture has entries that fail Lane enum construction

### T025: Create edge case fixtures

**Purpose**: Test alias normalization, optional field handling, and schema version boundaries.

**Steps**:
1. Create `fixtures/edge_cases/valid/`:
   - `alias_doing_normalized.json` — `StatusTransitionPayload` with `to_lane: "doing"` (should normalize to `in_progress`)
   - `optional_fields_omitted.json` — `StatusTransitionPayload` with only required fields (no optional)
   - `event_with_all_optional_fields.json` — `Event` with all optional fields populated
2. Create `fixtures/edge_cases/invalid/`:
   - `unsupported_schema_version.json` — `Event` with `schema_version: "99.0.0"` (if validator checks version)
   - `empty_event_type.json` — `Event` with empty `event_type: ""`

**Validation**:
- [ ] Valid edge cases pass validation
- [ ] Invalid edge cases fail with expected errors

### T026: Create `manifest.json`

**Purpose**: Centralized fixture expectations driving test execution.

**Steps**:
1. Create `src/spec_kitty_events/conformance/fixtures/manifest.json`:
   ```json
   {
     "version": "2.0.0",
     "fixtures": [
       {
         "id": "event-valid",
         "path": "events/valid/event.json",
         "expected_result": "valid",
         "event_type": "Event",
         "notes": "Complete Event with all required fields",
         "min_version": "2.0.0"
       },
       ...
     ]
   }
   ```
2. Include one entry per fixture file, covering all valid and invalid cases.
3. Use descriptive `id` values and `notes` for debugging.

**Validation**:
- [ ] `manifest.json` is valid JSON
- [ ] Every fixture file in the directory tree has a corresponding manifest entry
- [ ] Every manifest entry has a resolvable `path`

### T027: Implement `load_fixtures()` and `FixtureCase`

**Purpose**: Public API for loading fixture data from the manifest.

**Steps**:
1. In `src/spec_kitty_events/conformance/__init__.py`, add:
   ```python
   from dataclasses import dataclass
   from typing import Any

   @dataclass(frozen=True)
   class FixtureCase:
       id: str
       payload: dict[str, Any]
       expected_valid: bool
       event_type: str
       notes: str
       min_version: str

   def load_fixtures(category: str) -> list[FixtureCase]:
       """Load canonical fixture cases for a category."""
       ...
   ```
2. Implementation reads `manifest.json`, filters by category prefix in `path`, loads each referenced JSON file, and returns `FixtureCase` objects.
3. Categories: `"events"`, `"lane_mapping"`, `"edge_cases"`.
4. Export `FixtureCase` and `load_fixtures` from `__init__.py` and add to `__all__`.

**Validation**:
- [ ] `load_fixtures("events")` returns fixture cases for all event fixtures
- [ ] Each `FixtureCase` has correct `expected_valid` based on manifest
- [ ] Invalid category raises `ValueError`

### T028: Verify `pyproject.toml` package-data

**Purpose**: Ensure fixture JSON files are bundled when the package is installed.

**Steps**:
1. Verify `pyproject.toml` has:
   ```toml
   [tool.setuptools.package-data]
   spec_kitty_events = ["py.typed", "schemas/*.json", "conformance/fixtures/**/*.json"]
   ```
2. Run `pip install -e ".[dev,conformance]"` and verify fixtures are accessible via `load_fixtures()`.
3. If the `**/*.json` glob doesn't work with setuptools, use explicit patterns:
   ```toml
   spec_kitty_events = [
       "py.typed",
       "schemas/*.json",
       "conformance/fixtures/*.json",
       "conformance/fixtures/events/valid/*.json",
       "conformance/fixtures/events/invalid/*.json",
       "conformance/fixtures/lane_mapping/valid/*.json",
       "conformance/fixtures/lane_mapping/invalid/*.json",
       "conformance/fixtures/edge_cases/valid/*.json",
       "conformance/fixtures/edge_cases/invalid/*.json",
   ]
   ```

**Validation**:
- [ ] After `pip install -e .`, `load_fixtures("events")` returns fixture data
- [ ] Fixtures are present in the installed package

## Definition of Done

- [ ] Fixture directory structure with valid/invalid splits exists
- [ ] Valid fixtures for all event types pass model validation
- [ ] Invalid fixtures fail model validation with expected errors
- [ ] Lane mapping fixtures cover all 7 canonical lanes
- [ ] Edge case fixtures cover alias normalization and optional fields
- [ ] `manifest.json` has entries for every fixture file
- [ ] `load_fixtures()` and `FixtureCase` are implemented and exported
- [ ] `pyproject.toml` bundles fixture JSON files
- [ ] `mypy --strict` passes
- [ ] Full test suite still passes: `python3.11 -m pytest`

## Risks

- **setuptools `**/*.json` glob**: The recursive glob `**/*.json` may not work with all setuptools versions. Fall back to explicit patterns if needed.
- **Fixture staleness**: If models change after fixtures are created, fixtures may become invalid. The conformance tests (WP05) will catch this.
- **ULID generation for fixtures**: Use a fixed valid ULID string (e.g., `"01JXXXXXXXXXXXXXXXXXXXXXXX"` — 26 chars) rather than generating random ones.

## Reviewer Guidance

- Verify manifest.json has one entry per fixture file (no missing, no orphans).
- Spot-check at least one valid and one invalid fixture against the Pydantic model.
- Verify `expected_result` in manifest matches reality (valid fixtures actually pass, invalid actually fail).
- Verify `load_fixtures()` returns correct data structure with payload loaded from JSON.

## Activity Log

- 2026-02-12T10:54:01Z – claude-opus – shell_pid=93397 – lane=doing – Assigned agent via workflow command
- 2026-02-12T11:02:25Z – claude-opus – shell_pid=93397 – lane=for_review – Ready for review: 21 fixture files, manifest.json, FixtureCase + load_fixtures API, 76 new tests, 545 total pass, mypy clean
- 2026-02-12T11:02:30Z – codex – shell_pid=99383 – lane=doing – Started review via workflow command
- 2026-02-12T11:05:15Z – codex – shell_pid=99383 – lane=planned – Moved to planned
- 2026-02-12T11:06:27Z – claude-opus – shell_pid=3104 – lane=doing – Started implementation via workflow command
- 2026-02-12T11:07:31Z – claude-opus – shell_pid=3104 – lane=for_review – Re-review: fixed optional_fields_omitted (only required fields), FixtureCase.payload widened to Any, schema_version renamed to non-semver format case. 545 tests, mypy clean.
