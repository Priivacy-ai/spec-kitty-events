---
work_package_id: WP08
title: Conformance Fixtures and Tests
lane: "doing"
dependencies: [WP07]
base_branch: 006-mission-collaboration-soft-coordination-contracts-WP07
base_commit: 3a4f5aea7b57215afe836762312c639af5903d81
created_at: '2026-02-15T11:23:00.134060+00:00'
subtasks:
- T043
- T044
- T045
- T046
- T047
phase: Phase 3 - Integration
assignee: ''
agent: "claude-coordinator"
shell_pid: "88847"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-15T10:35:14Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – Conformance Fixtures and Tests

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create conformance fixtures and advanced tests:
1. 5 valid conformance payload fixture JSON files (single payload format)
2. 2 invalid conformance payload fixture JSON files for schema rejection
3. Register all 7 fixtures in manifest.json using current manifest schema + include fixture paths in package data
4. Hypothesis property tests proving reducer determinism
5. Performance benchmark (10K events in <1s)

**Success criteria**:
- Valid fixtures pass dual-layer validation (Pydantic + JSON Schema); invalid fixtures fail as expected
- Property tests prove determinism across 200+ orderings (strict and permissive)
- Benchmark processes 10K events in <1s (50 participants, mixed types)
- All existing tests still pass

## Context & Constraints

**Reference documents**:
- Fixture strategy: `kitty-specs/006-.../research.md` (R8, R12)
- Existing fixtures: `src/spec_kitty_events/conformance/fixtures/manifest.json`
- Existing property tests: `tests/property/` directory

**Prerequisites**: WP07 must be merged (schemas and validators available)

**Implementation command**: `spec-kitty implement WP08 --base WP07`

**Fixture format**:
- Conformance fixtures follow the current harness contract: one payload object per fixture file + manifest `event_type`.
- Multi-event collaboration sequences (join → intent → warning → ack) belong in reducer test fixtures under `tests/fixtures/` and are asserted by reducer tests, not `validate_event()` manifest tests.

## Subtasks & Detailed Guidance

### Subtask T043 – Create 5 valid conformance payload fixtures

- **Purpose**: Provide machine-checkable payload fixtures compatible with the current conformance validator (`validate_event(payload, event_type)`).
- **Steps**:
  1. Create directory: `src/spec_kitty_events/conformance/fixtures/collaboration/valid/`
  2. Create 5 payload fixture files, one payload object per file:
  - `participant_joined_valid.json` (`ParticipantJoinedPayload`)
  - `drive_intent_set_valid.json` (`DriveIntentSetPayload`)
  - `focus_changed_valid.json` (`FocusChangedPayload`)
  - `concurrent_driver_warning_valid.json` (`ConcurrentDriverWarningPayload`)
  - `warning_acknowledged_valid.json` (`WarningAcknowledgedPayload`)
  3. Keep collaboration sequence coverage in reducer fixtures (for example `tests/fixtures/collaboration/3-participant-overlap.json`) consumed by reducer tests, not conformance manifest tests
  4. All conformance fixtures must pass model + schema validation via `validate_event()`

- **Files**: `src/spec_kitty_events/conformance/fixtures/collaboration/valid/*.json` (5 new files), `tests/fixtures/collaboration/*.json` (reducer scenario fixtures)
- **Parallel?**: Yes (with T044)
- **Notes**: Conformance fixtures are payload-only (no envelope fields). Envelope-level checks continue to live in `events/valid/event.json` and related fixtures.

### Subtask T044 – Create 2 invalid conformance payload fixtures

- **Purpose**: Provide negative test cases for schema rejection.
- **Steps**:
  1. Create directory: `src/spec_kitty_events/conformance/fixtures/collaboration/invalid/`
  2. Create 2 fixture files:
  - `participant_joined_missing_participant_id.json` (missing required field)
  - `focus_changed_missing_focus_target.json` (missing required field)
  3. Keep strict-mode unknown-participant behavior in reducer scenario fixtures/tests (not payload-level conformance)

- **Files**: `src/spec_kitty_events/conformance/fixtures/collaboration/invalid/*.json` (2 new files)
- **Parallel?**: Yes (with T043)

### Subtask T045 – Register fixtures in manifest.json and package data

- **Purpose**: Add all 7 fixtures to the conformance fixture manifest.
- **Steps**:
  1. Read `src/spec_kitty_events/conformance/fixtures/manifest.json`
  2. Add entries for all 7 collaboration fixtures using current manifest keys:
     ```json
     {
       "id": "collab-participant-joined-valid",
       "path": "collaboration/valid/participant_joined_valid.json",
       "expected_result": "valid",
       "event_type": "ParticipantJoined",
       "min_version": "2.1.0",
       "notes": "Valid collaboration payload fixture"
     },
     ...
     ```
  3. Use `event_type` (singular) and `expected_result` (`valid`/`invalid`) to match the existing pyargs conformance harness
  4. Set `min_version` to `"2.1.0"` for all collaboration fixtures
  5. Update `pyproject.toml` `[tool.setuptools.package-data]` to include:
     - `conformance/fixtures/collaboration/valid/*.json`
     - `conformance/fixtures/collaboration/invalid/*.json`
- **Files**: `src/spec_kitty_events/conformance/fixtures/manifest.json`, `pyproject.toml`
- **Parallel?**: No — depends on T043, T044

### Subtask T046 – Property tests for reducer determinism

- **Purpose**: Prove the collaboration reducer is deterministic across event orderings.
- **Steps**:
  1. Create `tests/property/test_collaboration_determinism.py`
  2. Implement Hypothesis strategies:
     ```python
     @st.composite
     def collaboration_event_sequence(draw):
         """Generate a valid collaboration event sequence."""
         # Generate 2-5 participant IDs
         # Generate ParticipantJoined for each
         # Generate 5-20 random collaboration events from rostered participants
         # Assign monotonically increasing lamport_clocks
         # Return the event list
     ```
  3. Write property tests:
     ```python
     @given(events=collaboration_event_sequence())
     @settings(max_examples=200)
     def test_reducer_deterministic_strict(events):
         """Reducer produces same output for any ordering of the same events."""
         result1 = reduce_collaboration_events(events, mode="strict")
         shuffled = list(events)
         random.shuffle(shuffled)
         result2 = reduce_collaboration_events(shuffled, mode="strict")
         assert result1 == result2

     @given(events=collaboration_event_sequence())
     @settings(max_examples=200)
     def test_reducer_deterministic_permissive(events):
         """Same for permissive mode."""
         result1 = reduce_collaboration_events(events, mode="permissive")
         shuffled = list(events)
         random.shuffle(shuffled)
         result2 = reduce_collaboration_events(shuffled, mode="permissive")
         assert result1 == result2
     ```
  4. Use consistent `project_uuid` and `correlation_id` across generated events
  5. Run: `python3.11 -m pytest tests/property/test_collaboration_determinism.py -v`
- **Files**: `tests/property/test_collaboration_determinism.py` (new)
- **Parallel?**: Yes (with T043-T045, T047)
- **Notes**: The existing `tests/property/` directory has lifecycle determinism tests — follow the same pattern. Import `hypothesis.strategies as st` and `from hypothesis import given, settings`.

### Subtask T047 – Performance benchmark

- **Purpose**: Verify the reducer handles 10K events in <1s.
- **Steps**:
  1. Create `tests/benchmark/test_collaboration_perf.py`
  2. Implement benchmark:
     ```python
     import time
     import pytest

     @pytest.mark.benchmark
     def test_10k_events_under_1s():
         """10K-event synthetic benchmark with 50 participants."""
         # Generate 50 ParticipantJoined events
         # Generate 9950 mixed collaboration events
         # (heartbeats, focus changes, drive intent, comments, etc.)
         # Use seeded roster for strict mode
         events = _generate_benchmark_events(n_participants=50, n_events=10000)
         roster = _build_roster(events)

         start = time.monotonic()
         state = reduce_collaboration_events(events, mode="strict", roster=roster)
         elapsed = time.monotonic() - start

         assert elapsed < 1.0, f"Reducer took {elapsed:.3f}s for 10K events (threshold: 1.0s)"
         assert state.event_count == 10000
     ```
  3. Create `tests/benchmark/` directory if it doesn't exist
  4. Helper `_generate_benchmark_events()` should create a realistic event type distribution:
     - ~5% ParticipantJoined/Left
     - ~30% PresenceHeartbeat
     - ~20% DriveIntentSet/FocusChanged
     - ~15% PromptStepExecution Started/Completed
     - ~10% Warnings/Acks
     - ~10% Comments/Decisions
     - ~10% SessionLinked
  5. Run: `python3.11 -m pytest tests/benchmark/test_collaboration_perf.py -v`
- **Files**: `tests/benchmark/test_collaboration_perf.py` (new)
- **Parallel?**: Yes (with T043-T046)
- **Notes**: Mark with `@pytest.mark.benchmark` and run this marker separately from default regression suite (`-m "not benchmark"`).

## Test Strategy

- **Conformance**: All fixture JSON files pass dual-layer validation via existing conformance test infrastructure
- **Property tests**: `python3.11 -m pytest tests/property/test_collaboration_determinism.py -v`
- **Benchmark**: `python3.11 -m pytest tests/benchmark/test_collaboration_perf.py -v`
- **Full suite (default gate)**: `python3.11 -m pytest -x -m "not benchmark"` (verify no regressions)
- **Benchmark suite (separate gate or manual)**: `python3.11 -m pytest -m benchmark`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hypothesis strategy complexity | Flaky or slow tests | Keep event generation simple — small participant pool, random event types |
| Benchmark flakiness on CI | False failures | Run benchmark marker separately from default suite (`-m benchmark`) |
| Invalid fixtures not properly structured | Conformance tests fail | Verify each fixture independently before registering |

## Review Guidance

- Verify all 7 conformance fixtures are payload-only and align to manifest `event_type`
- Verify reducer sequence scenarios are covered by reducer tests using `tests/fixtures/collaboration/`
- Verify invalid fixtures trigger expected errors (strict mode / schema rejection)
- Verify property tests run 200+ examples without failure
- Verify benchmark completes in <1s on reviewer's machine
- Cross-check manifest keys (`event_type`, `expected_result`) with conformance harness expectations

## Completion

```bash
git add -A && git commit -m "feat(WP08): conformance fixtures, property tests, and benchmark"
spec-kitty agent tasks move-task WP08 --to for_review --note "Ready for review: 7 fixtures, determinism property tests, 10K-event benchmark"
```

## Activity Log

- 2026-02-15T10:35:14Z – system – lane=planned – Prompt created.
- 2026-02-15T11:23:00Z – claude-coordinator – shell_pid=88847 – lane=doing – Assigned agent via workflow command
