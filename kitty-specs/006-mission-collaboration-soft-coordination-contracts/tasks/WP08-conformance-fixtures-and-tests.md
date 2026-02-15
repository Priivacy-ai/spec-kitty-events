---
work_package_id: "WP08"
subtasks:
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
title: "Conformance Fixtures and Tests"
phase: "Phase 3 - Integration"
lane: "planned"  # DO NOT EDIT - use: spec-kitty agent tasks move-task <WPID> --to <lane>
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP07"]
history:
  - timestamp: "2026-02-15T10:35:14Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
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
1. 5 valid fixture JSON files covering all user stories
2. 2 invalid fixture JSON files for schema rejection
3. Register all 7 fixtures in manifest.json
4. Hypothesis property tests proving reducer determinism
5. Performance benchmark (10K events in <1s)

**Success criteria**:
- All 7 fixtures pass dual-layer validation (Pydantic + JSON Schema)
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

**Fixture format**: Each JSON file contains an array of Event dicts. Events use the canonical envelope mapping:
- `aggregate_id = "mission/M042"` (type-prefixed)
- `correlation_id` = ULID-26 string
- `event_type` = one of `COLLABORATION_EVENT_TYPES`

## Subtasks & Detailed Guidance

### Subtask T043 – Create 5 valid conformance fixtures

- **Purpose**: Provide machine-checkable reference scenarios covering all acceptance criteria.
- **Steps**:
  1. Create directory: `src/spec_kitty_events/conformance/fixtures/collaboration/valid/`
  2. Create 5 fixture files:

  **a) `3-participant-overlap.json`** — Covers: 3+ participants, overlapping intent, warning lifecycle
  - 3 human participants join with `auth_principal_id`
  - All 3 set `DriveIntentSet(active)`
  - 2 share focus on WP03
  - `ConcurrentDriverWarning` emitted (participant_ids = 2 overlapping)
  - `WarningAcknowledged(continue)` from participant 1
  - `WarningAcknowledged(hold)` from participant 2
  - Sequence of ~15-20 events

  **b) `step-collision-llm.json`** — Covers: llm_context participants, step collision
  - 2 `llm_context` participants join
  - Both start execution on same step_id
  - `PotentialStepCollisionDetected` emitted
  - One completes with `success`, other with `skipped`
  - Sequence of ~10-12 events

  **c) `decision-with-comments.json`** — Covers: communication, decision with warning reference
  - 3 participants join
  - `CommentPosted` thread (3 comments, 1 reply)
  - `ConcurrentDriverWarning` emitted
  - `DecisionCaptured` referencing the warning
  - Sequence of ~15 events

  **d) `participant-lifecycle.json`** — Covers: join with auth_principal, heartbeats, session link, leave
  - 1 participant joins with `auth_principal_id`
  - 3 `PresenceHeartbeat` events
  - `SessionLinked` (cli_to_saas)
  - `ParticipantLeft` with reason "explicit"
  - Sequence of ~8 events

  **e) `session-linking.json`** — Covers: multi-session participant
  - 1 participant, 2 sessions (CLI + SaaS)
  - `SessionLinked` event linking them
  - Heartbeats from both sessions (via session_id on heartbeat payload)
  - Sequence of ~8 events

  3. Each fixture must use valid ULID-26 event_ids and correlation_ids, valid UUIDs for project_uuid, monotonically increasing lamport_clocks
  4. All fixtures must pass: `Event(**fixture_event)` and payload model validation

- **Files**: `src/spec_kitty_events/conformance/fixtures/collaboration/valid/*.json` (5 new files)
- **Parallel?**: Yes (with T044)
- **Notes**: Use real ULID format (26 chars, uppercase alphanumeric) for event_id and correlation_id. Use consistent project_uuid across fixture events. Use ISO 8601 timestamps.

### Subtask T044 – Create 2 invalid conformance fixtures

- **Purpose**: Provide negative test cases for schema rejection.
- **Steps**:
  1. Create directory: `src/spec_kitty_events/conformance/fixtures/collaboration/invalid/`
  2. Create 2 fixture files:

  **a) `unknown-participant-strict.json`** — Validates strict-mode rejection
  - 1 participant joins
  - Event from a different `participant_id` (never joined) with `DriveIntentSet`
  - Expected: strict mode raises `UnknownParticipantError`
  - Sequence of 3 events (join + unknown event + known event to verify processing continues in permissive)

  **b) `missing-required-fields.json`** — Validates schema rejection
  - Event with `ParticipantJoined` type but payload missing `participant_id`
  - Event with `FocusChanged` type but payload missing `focus_target`
  - Expected: Pydantic validation error on payload construction
  - Sequence of 2 events (each missing a required field)

- **Files**: `src/spec_kitty_events/conformance/fixtures/collaboration/invalid/*.json` (2 new files)
- **Parallel?**: Yes (with T043)

### Subtask T045 – Register fixtures in manifest.json

- **Purpose**: Add all 7 fixtures to the conformance fixture manifest.
- **Steps**:
  1. Read `src/spec_kitty_events/conformance/fixtures/manifest.json`
  2. Add entries for all 7 collaboration fixtures:
     ```json
     {
       "path": "collaboration/valid/3-participant-overlap.json",
       "event_types": ["ParticipantJoined", "DriveIntentSet", "FocusChanged", "ConcurrentDriverWarning", "WarningAcknowledged"],
       "min_version": "2.1.0",
       "valid": true
     },
     ...
     ```
  3. Include `event_types` listing the event types present in each fixture
  4. Set `min_version` to `"2.1.0"` for all collaboration fixtures
  5. Set `valid: true` for valid fixtures, `valid: false` for invalid
- **Files**: `src/spec_kitty_events/conformance/fixtures/manifest.json`
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
- **Notes**: Mark with `@pytest.mark.benchmark` — non-blocking in CI by default. The 1s threshold is conservative for pure CPU work.

## Test Strategy

- **Conformance**: All fixture JSON files pass dual-layer validation via existing conformance test infrastructure
- **Property tests**: `python3.11 -m pytest tests/property/test_collaboration_determinism.py -v`
- **Benchmark**: `python3.11 -m pytest tests/benchmark/test_collaboration_perf.py -v`
- **Full suite**: `python3.11 -m pytest -x` (verify no regressions)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hypothesis strategy complexity | Flaky or slow tests | Keep event generation simple — small participant pool, random event types |
| Benchmark flakiness on CI | False failures | Use generous 1s threshold (10K pure CPU events should take ~100ms) |
| Invalid fixtures not properly structured | Conformance tests fail | Verify each fixture independently before registering |

## Review Guidance

- Verify all 7 fixtures are valid JSON and follow envelope mapping conventions
- Verify valid fixtures produce correct reduced state when passed through reducer
- Verify invalid fixtures trigger expected errors (strict mode / schema rejection)
- Verify property tests run 200+ examples without failure
- Verify benchmark completes in <1s on reviewer's machine
- Cross-check fixture event_types with manifest.json entries

## Completion

```bash
git add -A && git commit -m "feat(WP08): conformance fixtures, property tests, and benchmark"
spec-kitty agent tasks move-task WP08 --to for_review --note "Ready for review: 7 fixtures, determinism property tests, 10K-event benchmark"
```

## Activity Log

- 2026-02-15T10:35:14Z – system – lane=planned – Prompt created.
