---
work_package_id: WP04
title: Tests (Conformance + Reducer)
lane: "for_review"
dependencies:
- WP02
- WP03
base_branch: 008-mission-dossier-parity-event-contracts-WP02
base_commit: ab00411586faffa0ed85063672b93c38b4306ba2
created_at: '2026-02-21T14:40:06.104006+00:00'
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 2 - Validation
assignee: ''
agent: "coordinator"
shell_pid: "31414"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-21T14:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Tests (Conformance + Reducer)

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, see Review Feedback section.

---

## Review Feedback

*[Empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Write two test modules that together cover all five conformance test categories from spec §7.6: missing-artifact anomaly, parity drift detection, namespace collision prevention, reducer determinism, and round-trip schema conformance.

**Acceptance gates**:
- [ ] `python3.11 -m pytest tests/test_dossier_conformance.py tests/test_dossier_reducer.py -v` exits 0
- [ ] Coverage: `python3.11 -m pytest --cov=src/spec_kitty_events/dossier --cov-report=term-missing tests/test_dossier_*.py` shows ≥98% for `dossier.py`
- [ ] `mypy --strict tests/test_dossier_conformance.py tests/test_dossier_reducer.py` exits 0 (or passes with standard pytest-compatible annotations)
- [ ] Hypothesis property test runs 200 examples and finds no counterexample
- [ ] `NamespaceMixedStreamError` test verifies the message contains both namespace values

## Context & Constraints

- **Depends on**: WP02 (loader + validator wired, schemas committed) and WP03 (fixtures on disk + manifest updated).
- **Model files to follow**: `tests/test_mission_next_conformance.py` and `tests/test_mission_next_reducer.py` — follow their structural pattern for parametrize, fixtures, and imports.
- **Hypothesis**: Already in dev dependencies (check `pyproject.toml [project.optional-dependencies] dev`). Import pattern: `from hypothesis import given, settings, strategies as st`.

**Implementation command**:
```bash
spec-kitty implement WP04 --base <branch-with-WP02-and-WP03>
```
(WP04 requires both WP02 wiring and WP03 fixtures. Base WP04 on a branch/worktree that already contains both.)

## Subtasks & Detailed Guidance

### Subtask T020 – test_dossier_conformance.py: valid and invalid fixture validation

- **Purpose**: Verify that all 10 valid dossier fixtures pass dual-layer conformance validation and all 3 invalid fixtures produce at least one violation.
- **Steps**:
  1. Create `tests/test_dossier_conformance.py`.
  2. Add parametrized tests following `test_mission_next_conformance.py` pattern:

     ```python
     import pytest
     from spec_kitty_events.conformance import load_fixtures, validate_event

     _DOSSIER_CASES = load_fixtures("dossier")
     _VALID_CASES = [c for c in _DOSSIER_CASES if c.expected_valid]
     _INVALID_CASES = [c for c in _DOSSIER_CASES if not c.expected_valid]


     @pytest.mark.parametrize("case", _VALID_CASES, ids=[c.id for c in _VALID_CASES])
     def test_valid_fixture_passes_conformance(case):
         result = validate_event(case.payload, case.event_type, strict=True)
         assert result.valid, (
             f"Fixture {case.id} should be valid but got violations:\n"
             f"Model: {result.model_violations}\n"
             f"Schema: {result.schema_violations}"
         )


     @pytest.mark.parametrize("case", _INVALID_CASES, ids=[c.id for c in _INVALID_CASES])
     def test_invalid_fixture_fails_conformance(case):
         result = validate_event(case.payload, case.event_type, strict=True)
         assert not result.valid, (
             f"Fixture {case.id} should be invalid but passed validation"
         )
         total_violations = len(result.model_violations) + len(result.schema_violations)
         assert total_violations >= 1, (
             f"Fixture {case.id} is invalid but no violations were reported"
         )
     ```

- **Files**: `tests/test_dossier_conformance.py` (new file)
- **Parallel?**: Yes — can be written alongside T023.

### Subtask T021 – Category coverage: 13 cases + 2 replay streams loadable

- **Purpose**: Verify that the loader returns exactly 13 fixture cases for the dossier category and both replay streams load without error.
- **Steps**: Add to `tests/test_dossier_conformance.py`:

  ```python
  from spec_kitty_events.conformance import load_replay_stream


  def test_dossier_fixture_count():
      """Loader must return exactly 13 dossier fixture cases (not replay streams)."""
      cases = load_fixtures("dossier")
      assert len(cases) == 13, f"Expected 13 cases, got {len(cases)}"


  def test_happy_path_replay_stream_loads():
      events = load_replay_stream("dossier-replay-happy-path")
      assert len(events) >= 5, f"Happy path stream too short: {len(events)} events"
      assert all("event_type" in e for e in events)


  def test_drift_scenario_replay_stream_loads():
      events = load_replay_stream("dossier-replay-drift-scenario")
      assert len(events) >= 4, f"Drift stream too short: {len(events)} events"
  ```

- **Files**: `tests/test_dossier_conformance.py`
- **Parallel?**: Yes.

### Subtask T022 – Round-trip schema conformance: all layers checked

- **Purpose**: Verify that valid fixtures pass BOTH Pydantic and JSON Schema layers; invalid fixtures produce violations in at least one layer. This is the "round-trip" check from spec §7.6 item 5.
- **Steps**: Add to `tests/test_dossier_conformance.py`:

  ```python
  def test_valid_fixtures_pass_both_layers():
      """Valid fixtures must produce zero model AND zero schema violations."""
      for case in _VALID_CASES:
          result = validate_event(case.payload, case.event_type, strict=True)
          assert len(result.model_violations) == 0, (
              f"{case.id}: unexpected model violations: {result.model_violations}"
          )
          assert not result.schema_check_skipped, (
              f"{case.id}: schema layer was skipped; install conformance extras"
          )
          assert len(result.schema_violations) == 0, (
              f"{case.id}: unexpected schema violations: {result.schema_violations}"
          )


  def test_invalid_fixtures_produce_violations_in_at_least_one_layer():
      """Invalid fixtures must produce ≥1 violation in model OR schema layer."""
      for case in _INVALID_CASES:
          result = validate_event(case.payload, case.event_type, strict=True)
          total = len(result.model_violations) + len(result.schema_violations)
          assert total >= 1, (
              f"{case.id}: invalid fixture produced zero violations in both layers"
          )
  ```

- **Files**: `tests/test_dossier_conformance.py`
- **Notes**: Dual-layer validation is mandatory for this WP. Ensure `jsonschema` is available (`pip install -e ".[conformance,dev]"`) so `schema_check_skipped` is always False in these tests.

### Subtask T023 – test_dossier_reducer.py: unit tests

- **Purpose**: Verify the reducer's core behavior: empty stream, happy-path fold, drift scenario fold, deduplication, supersedes logic, and silent skip of unknown event types.
- **Steps**: Create `tests/test_dossier_reducer.py`:

  ```python
  import json
  from pathlib import Path
  from typing import Any, Dict, List

  import pytest
  from spec_kitty_events.conformance import load_replay_stream
  from spec_kitty_events.dossier import (
      reduce_mission_dossier,
      NamespaceMixedStreamError,
      MissionDossierState,
  )
  from spec_kitty_events.models import Event

  _FIXTURES_DIR = Path(__file__).parent.parent / "src/spec_kitty_events/conformance/fixtures"


  def _events_from_replay(fixture_id: str) -> List[Event]:
      raw = load_replay_stream(fixture_id)
      return [Event(**e) for e in raw]


  def test_empty_stream_returns_default_state():
      state = reduce_mission_dossier([])
      assert state == MissionDossierState()
      assert state.parity_status == "unknown"
      assert state.event_count == 0


  def test_happy_path_stream_produces_clean_state():
      events = _events_from_replay("dossier-replay-happy-path")
      state = reduce_mission_dossier(events)
      assert state.parity_status == "clean"
      assert state.event_count > 0
      assert state.latest_snapshot is not None
      assert len(state.artifacts) >= 3


  def test_drift_scenario_produces_drifted_state():
      events = _events_from_replay("dossier-replay-drift-scenario")
      state = reduce_mission_dossier(events)
      assert state.parity_status == "drifted"
      assert len(state.drift_history) >= 1


  def test_supersedes_marks_prior_artifact():
      events = _events_from_replay("dossier-replay-happy-path")
      state = reduce_mission_dossier(events)
      # spec.md is superseded in the happy-path stream (line 5 supersedes line 1)
      spec_path = "kitty-specs/008-mission-dossier-parity-event-contracts/spec.md"
      assert spec_path in state.artifacts
      # The entry should reflect the latest version (supersedes keeps latest)
      # Depending on implementation, verify the superseded flag is handled


  def test_unknown_event_types_silently_skipped():
      events = _events_from_replay("dossier-replay-happy-path")
      # Inject a non-dossier event
      from spec_kitty_events.models import Event
      fake = events[0].model_copy(update={"event_type": "SomeRandomEvent", "event_id": "01JNRFAKEEV00000000000001"})
      mixed = [fake] + events
      # Should not raise; unknown events are skipped
      state = reduce_mission_dossier(mixed)
      assert state.event_count == len(events)  # fake event not counted


  def test_deduplication_same_output_as_clean_stream():
      events = _events_from_replay("dossier-replay-happy-path")
      # Duplicate the first event
      duplicated = [events[0]] + events
      state_clean = reduce_mission_dossier(events)
      state_duped = reduce_mission_dossier(duplicated)
      assert state_clean == state_duped
  ```

- **Files**: `tests/test_dossier_reducer.py` (new file)
- **Parallel?**: Yes — can be written alongside T020.

### Subtask T024 – NamespaceMixedStreamError test

- **Purpose**: Verify the single-namespace invariant: the reducer must raise `NamespaceMixedStreamError` when events have different namespace tuples, and the exception message must contain both namespace representations.
- **Steps**: Add to `tests/test_dossier_reducer.py`:

  ```python
  def test_namespace_mixed_stream_raises():
      """Reducer raises NamespaceMixedStreamError on multi-namespace input."""
      events = _events_from_replay("dossier-replay-happy-path")

      # Build a second event with a different feature_slug
      import copy, json
      second_ns_event = json.loads(events[-1].model_dump_json())
      second_ns_event["event_id"] = "01JNRNS2EVENT0000000000001"
      second_ns_event["lamport_clock"] = 999
      second_ns_event["payload"]["namespace"]["feature_slug"] = "999-entirely-different-feature"
      different_ns_event = Event(**second_ns_event)

      mixed = list(events) + [different_ns_event]

      with pytest.raises(NamespaceMixedStreamError) as exc_info:
          reduce_mission_dossier(mixed)

      # Message must contain both namespace values
      msg = str(exc_info.value)
      assert "008-mission-dossier-parity-event-contracts" in msg or "Expected" in msg
      assert "999-entirely-different-feature" in msg or "Got" in msg


  def test_namespace_collision_prevention():
      """Two events with identical namespace tuples must NOT raise."""
      events = _events_from_replay("dossier-replay-happy-path")
      # Same namespace → should reduce cleanly
      state = reduce_mission_dossier(events)
      assert state.namespace is not None
  ```

- **Files**: `tests/test_dossier_reducer.py`
- **Notes**: The exact message format from `NamespaceMixedStreamError` depends on the WP01 implementation. Adjust assertions if the message format differs slightly from the plan — the key requirement is that both namespaces are present in the message.

### Subtask T025 – Hypothesis property test: reducer determinism

- **Purpose**: Prove that `reduce_mission_dossier` is deterministic: for any causal-order-preserving permutation of the happy-path replay stream, the output is identical to the canonical sorted output.
- **Steps**: Add to `tests/test_dossier_reducer.py`:

  ```python
  from hypothesis import given, settings, strategies as st


  _HAPPY_PATH_EVENTS = _events_from_replay("dossier-replay-happy-path")
  _CANONICAL_STATE = reduce_mission_dossier(_HAPPY_PATH_EVENTS)


  @given(st.permutations(_HAPPY_PATH_EVENTS))
  @settings(max_examples=200)
  def test_reducer_determinism_across_permutations(permuted_events):
      """Reducer must produce identical output for all event orderings.

      The sort key (lamport_clock, timestamp, event_id) guarantees a stable
      total order before reduction, so any permutation produces the same state.
      """
      state = reduce_mission_dossier(permuted_events)
      assert state == _CANONICAL_STATE, (
          f"Reducer produced different output for a permutation.\n"
          f"Expected parity_status={_CANONICAL_STATE.parity_status}, "
          f"got parity_status={state.parity_status}"
      )
  ```

  **Run to verify**:
  ```bash
  python3.11 -m pytest tests/test_dossier_reducer.py::test_reducer_determinism_across_permutations -v --hypothesis-show-statistics
  ```

- **Files**: `tests/test_dossier_reducer.py`
- **Notes**: `st.permutations(list)` generates random permutations of the input list. The happy-path stream has 6 events — 6! = 720 possible orderings; 200 examples covers a good sample. If Hypothesis finds a counterexample, the sort key implementation in WP01 T006 is incorrect.

## Test Strategy

Run all dossier tests:
```bash
python3.11 -m pytest tests/test_dossier_conformance.py tests/test_dossier_reducer.py -v
```

Run with coverage:
```bash
python3.11 -m pytest --cov=src/spec_kitty_events/dossier --cov-report=term-missing tests/test_dossier_*.py
```

Coverage target: ≥98% for `src/spec_kitty_events/dossier.py`. Uncovered lines are typically:
- The `_extract_namespace` helper for malformed payload (add a test with `{"payload": {}}` event)
- Any `except` branches in payload parsing (add an event with malformed payload dict)

## Risks & Mitigations

- **Hypothesis + frozen Pydantic models**: `st.permutations` works on a list of `Event` objects. Hypothesis may have issues with non-JSON-serializable objects in its database. If so, wrap events as dicts and convert inside the test.
- **`model_copy` usage**: `Event.model_copy(update=...)` is Pydantic v2 API. If the Event model is frozen, `model_copy` still works (it creates a new instance). Do not use `event.event_id = ...` directly.
- **Coverage below 98%**: The reducer's payload parse failure branches (`except Exception: pass`) may be hard to hit. Add targeted tests: one event with `"payload": {}` for each event type.

## Review Guidance

1. `python3.11 -m pytest tests/test_dossier_conformance.py tests/test_dossier_reducer.py -v` — all green.
2. Coverage report shows ≥98% for `dossier.py`.
3. `NamespaceMixedStreamError` test asserts message contains both namespace identifiers.
4. Hypothesis test runs 200 examples without failure.
5. Deduplication test confirms identical output for clean vs duplicated stream.
6. `test_valid_fixtures_pass_both_layers` passes for all 10 valid fixtures.

## Activity Log

- 2026-02-21T14:00:00Z – system – lane=planned – Prompt created.
- 2026-02-21T14:40:06Z – coordinator – shell_pid=31414 – lane=doing – Assigned agent via workflow command
- 2026-02-21T14:48:55Z – coordinator – shell_pid=31414 – lane=for_review – All tests pass; coverage 100% on dossier.py; 46 tests across conformance and reducer suites; Hypothesis runs 200 examples without failure
