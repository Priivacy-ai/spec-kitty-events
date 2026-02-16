---
work_package_id: WP08
title: Reducer Tests — Happy Path & Determinism
lane: "doing"
dependencies: [WP06]
base_branch: 007-glossary-semantic-integrity-contracts-WP06
base_commit: 36b0cdc3f4066d989ad8ab413208b3854c24a655
created_at: '2026-02-16T13:28:41.479700+00:00'
subtasks:
- T037
- T038
- T039
- T040
- T041
- T042
phase: Phase 3 - Testing
assignee: ''
agent: ''
shell_pid: "27558"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-16T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – Reducer Tests — Happy Path & Determinism

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Test the reducer's happy path (full event lifecycle), strictness tracking, deduplication, and determinism invariant.
- Include a Hypothesis property test (200 examples) proving permutation invariance.
- Test clarification lifecycle including burst cap at exactly 3.

**Success**: All tests pass. The Hypothesis test runs 200 permutations without finding a counterexample to determinism.

## Context & Constraints

- **Test file**: `tests/test_glossary_reducer.py` (new file).
- **Hypothesis**: Already in dev dependencies. Use `@settings(max_examples=200)` matching existing pattern.
- **Event factory**: Create helper functions to generate `Event` instances with glossary payloads. These are test utilities, not part of the library.
- **Run**: `python3.11 -m pytest tests/test_glossary_reducer.py -v`

**Implementation command**: `spec-kitty implement WP08 --base WP06`

## Subtasks & Detailed Guidance

### Subtask T037 – Test reducer with empty input

- **Purpose**: Verify the short-circuit path for empty and non-glossary event sequences.
- **Steps**:
  1. Test `reduce_glossary_events([])` returns `ReducedGlossaryState()` with defaults.
  2. Test with events that are all non-glossary types (e.g., `WPStatusChanged`) — returns empty state.
  3. Verify default `current_strictness` is `"medium"`.
  4. Verify `mission_id` is `""`, `event_count` is `0`, `last_processed_event_id` is `None`.
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: Yes.

### Subtask T038 – Test full happy path

- **Purpose**: End-to-end test of the complete glossary event lifecycle.
- **Steps**:
  1. Create a helper function to generate `Event` instances:
     ```python
     def make_glossary_event(
         event_type: str,
         payload: dict,
         event_id: str | None = None,
         lamport_clock: int = 1,
         aggregate_id: str = "mission-001",
     ) -> Event:
         from spec_kitty_events import Event
         import ulid
         return Event(
             event_id=event_id or str(ulid.new()),
             event_type=event_type,
             aggregate_id=aggregate_id,
             payload=payload,
             timestamp=datetime.now(UTC).isoformat(),
             node_id="test-node",
             lamport_clock=lamport_clock,
             correlation_id=str(ulid.new()),
             schema_version="2.0.0",
         )
     ```
  2. Construct event sequence:
     - `GlossaryScopeActivated` (clock=1)
     - `GlossaryStrictnessSet` to `max` (clock=2)
     - `TermCandidateObserved` for "dashboard" (clock=3)
     - `GlossarySenseUpdated` for "dashboard" (clock=4)
     - `SemanticCheckEvaluated` with high severity (clock=5)
     - `GenerationBlockedBySemanticConflict` (clock=6)
  3. Reduce and assert:
     - `active_scopes` has 1 entry
     - `current_strictness` is `"max"`
     - `strictness_history` has 1 entry
     - `term_candidates["dashboard"]` has 1 entry
     - `term_senses["dashboard"]` reflects the update
     - `semantic_checks` has 1 entry
     - `generation_blocks` has 1 entry
     - `event_count` is 6
     - `anomalies` is empty
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: No — foundational test.

### Subtask T039 – Test strictness tracking

- **Purpose**: Verify strictness transitions and history.
- **Steps**:
  1. Test default strictness (no `GlossaryStrictnessSet` event) → `current_strictness == "medium"`.
  2. Test single strictness change: medium → max.
  3. Test multiple changes: medium → max → off → medium. Verify `current_strictness == "medium"` and `strictness_history` has 3 entries in order.
  4. Verify `previous_strictness` values in history payloads.
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: Yes.

### Subtask T040 – Test dedup behavior

- **Purpose**: Verify duplicate events are discarded.
- **Steps**:
  1. Create 2 events with the same `event_id` but different clocks.
  2. Reduce both the original list and the deduplicated list.
  3. Assert both produce identical `ReducedGlossaryState`.
  4. Assert `event_count` reflects deduplicated count.
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: Yes.

### Subtask T041 – Test determinism with Hypothesis

- **Purpose**: Property test proving that any causal-order-preserving permutation produces identical state.
- **Steps**:
  1. Create a fixed set of 8-10 glossary events with incrementing Lamport clocks (ensuring unique sort keys).
  2. Use Hypothesis to generate permutations:
     ```python
     from hypothesis import given, settings
     from hypothesis import strategies as st

     @given(data=st.data())
     @settings(max_examples=200)
     def test_reducer_determinism(data):
         events = [...]  # fixed set
         shuffled = data.draw(st.permutations(events))
         state_original = reduce_glossary_events(events)
         state_shuffled = reduce_glossary_events(shuffled)
         assert state_original == state_shuffled
     ```
  3. Ensure events have unique `(lamport_clock, timestamp, event_id)` tuples for deterministic sorting.
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: No — Hypothesis tests should run exclusively due to execution time.
- **Notes**: This is the most important test in the feature — it proves FR-020 (determinism invariant). If this fails, the sort key or dedup has a bug.

### Subtask T042 – Test clarification lifecycle and burst cap

- **Purpose**: Verify request/resolve pairing and the 3-per-evaluation burst cap.
- **Steps**:
  1. Test request + resolution pair: create request event, then resolution event. Verify `clarifications` has 1 entry with `resolved=True`.
  2. Test burst cap at 3: create 4 clarification requests with the same `semantic_check_event_id`. In strict mode, the 4th should raise. In permissive mode, the 4th should produce an anomaly and only 3 records exist.
  3. Test that resolved clarifications don't count toward cap: create 3 requests, resolve 1, then create a 4th. The 4th should succeed (only 2 active now).
  4. Test that requests for different `semantic_check_event_id` values are independent — 3 for check A and 3 for check B should both succeed (6 total records).
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: No — complex multi-event test.

## Risks & Mitigations

- **Risk**: Hypothesis `st.permutations` may be slow for large event sets. **Mitigation**: Keep event set to 8-10 events. 200 examples should complete in <30 seconds.
- **Risk**: Event equality comparison may fail on non-deterministic fields (e.g., timestamp). **Mitigation**: Use fixed timestamps in test events, or compare `ReducedGlossaryState` field by field.

## Review Guidance

- The Hypothesis test (T041) is the single most critical test. Verify it uses `@settings(max_examples=200)`.
- Burst cap test (T042) must verify the cap applies per `semantic_check_event_id`, not globally.
- All tests must import from `spec_kitty_events` top-level.
- Helper factory functions should be in the test file (not in the library).

## Activity Log

- 2026-02-16T12:00:00Z – system – lane=planned – Prompt created.
