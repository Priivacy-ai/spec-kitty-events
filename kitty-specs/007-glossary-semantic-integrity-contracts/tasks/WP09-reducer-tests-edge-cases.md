---
work_package_id: WP09
title: Reducer Tests — Edge Cases & Dual-Mode
lane: "doing"
dependencies: [WP06]
base_branch: 007-glossary-semantic-integrity-contracts-WP06
base_commit: 36b0cdc3f4066d989ad8ab413208b3854c24a655
created_at: '2026-02-16T13:30:30.220933+00:00'
subtasks:
- T043
- T044
- T045
- T046
- T047
- T048
phase: Phase 3 - Testing
assignee: ''
agent: "claude-opus"
shell_pid: "28797"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-16T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 – Reducer Tests — Edge Cases & Dual-Mode

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Test strict/permissive dual-mode behavior for all integrity violations.
- Test edge cases: unactivated scope, unobserved term, concurrent resolution, mid-mission strictness change.
- Verify permissive mode records correct anomalies and continues processing.

**Success**: All edge cases handled correctly in both modes. Permissive mode never raises, always records anomalies. Strict mode always raises with descriptive error messages.

## Context & Constraints

- **Test file**: `tests/test_glossary_reducer.py` (same file as WP08, can use separate test class).
- **Pattern**: Follow `tests/test_collaboration.py` dual-mode test pattern.
- **Imports**: Use `SpecKittyEventsError` from `spec_kitty_events` for strict mode assertions.
- **Run**: `python3.11 -m pytest tests/test_glossary_reducer.py -v`

**Implementation command**: `spec-kitty implement WP09 --base WP06`

## Subtasks & Detailed Guidance

### Subtask T043 – Test strict mode: unactivated scope

- **Purpose**: Verify strict mode raises when an event references a scope that was never activated.
- **Steps**:
  1. Create a `TermCandidateObserved` event with `scope_id="nonexistent"` — no prior `GlossaryScopeActivated`.
  2. Call `reduce_glossary_events([event], mode="strict")`.
  3. Assert `SpecKittyEventsError` is raised with message containing "unactivated scope".
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: Yes.

### Subtask T044 – Test strict mode: unobserved term sense update

- **Purpose**: Verify strict mode raises when `GlossarySenseUpdated` references a term never observed.
- **Steps**:
  1. Create events: `GlossaryScopeActivated` → `GlossarySenseUpdated` for "unknown_term" (no `TermCandidateObserved`).
  2. Call `reduce_glossary_events(events, mode="strict")`.
  3. Assert `SpecKittyEventsError` is raised with message containing "unobserved term".
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: Yes.

### Subtask T045 – Test permissive mode: scope anomaly

- **Purpose**: Verify permissive mode records anomaly for unactivated scope and continues processing.
- **Steps**:
  1. Create events: `TermCandidateObserved` with bad scope (clock=1) → `GlossaryScopeActivated` (clock=2) → `TermCandidateObserved` with good scope (clock=3).
  2. Call `reduce_glossary_events(events, mode="permissive")`.
  3. Assert `state.anomalies` has 1 entry with reason containing "unactivated scope".
  4. Assert `state.term_candidates` still contains the valid term from clock=3.
  5. Assert `state.event_count` is 3 (all events processed).
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: Yes.
- **Notes**: Critical — permissive mode must NOT stop processing after an anomaly. Remaining events must still be processed correctly.

### Subtask T046 – Test permissive mode: unobserved term anomaly

- **Purpose**: Verify permissive mode records anomaly for unobserved term sense update and continues.
- **Steps**:
  1. Create events: `GlossaryScopeActivated` → `GlossarySenseUpdated` for "unknown_term" → `TermCandidateObserved` for "known_term".
  2. Call `reduce_glossary_events(events, mode="permissive")`.
  3. Assert `state.anomalies` has 1 entry with reason containing "unobserved term".
  4. Assert `state.term_senses` contains "unknown_term" (sense update still applied despite anomaly).
  5. Assert `state.term_candidates` contains "known_term" (subsequent event processed).
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: Yes.

### Subtask T047 – Test concurrent clarification resolution

- **Purpose**: Verify last-write-wins for concurrent resolutions of the same clarification.
- **Steps**:
  1. Create events:
     - `GlossaryScopeActivated` (clock=1)
     - `SemanticCheckEvaluated` (clock=2)
     - `GlossaryClarificationRequested` (clock=3, event_id="req-001")
     - `GlossaryClarificationResolved` by actor-A (clock=4, clarification_event_id="req-001", event_id="res-A")
     - `GlossaryClarificationResolved` by actor-B (clock=5, clarification_event_id="req-001", event_id="res-B")
  2. Reduce and verify:
     - `state.clarifications` has 1 record.
     - `record.resolved` is `True`.
     - `record.resolution_event_id` is `"res-B"` (last write wins — higher clock).
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: Yes.
- **Notes**: This tests the deterministic concurrent resolution behavior. The event with higher Lamport clock (processed later in sort order) should win.

### Subtask T048 – Test strictness max→off mid-mission

- **Purpose**: Verify that changing strictness from max to off doesn't remove existing block events.
- **Steps**:
  1. Create events:
     - `GlossaryScopeActivated` (clock=1)
     - `GlossaryStrictnessSet` to `max` (clock=2)
     - `SemanticCheckEvaluated` high severity (clock=3)
     - `GenerationBlockedBySemanticConflict` (clock=4)
     - `GlossaryStrictnessSet` to `off` (clock=5)
  2. Reduce and verify:
     - `state.current_strictness` is `"off"`.
     - `state.generation_blocks` still has 1 entry (not removed).
     - `state.strictness_history` has 2 entries.
     - Block event from clock=4 is preserved as historical record.
- **Files**: `tests/test_glossary_reducer.py`.
- **Parallel?**: Yes.
- **Notes**: Block events are immutable historical records. Changing strictness after the fact does not retroactively modify the event log or the reduced state — it only affects future behavior (which is the CLI runtime's responsibility, not the contract library's).

## Risks & Mitigations

- **Risk**: Permissive mode test (T045) might accidentally pass if the anomaly event is silently discarded. **Mitigation**: Explicitly assert `event_count` includes the anomalous event.
- **Risk**: Concurrent resolution test (T047) depends on sort order. **Mitigation**: Use distinct Lamport clocks to guarantee sort order.

## Review Guidance

- Permissive mode tests (T045, T046) must assert both anomaly recording AND continued processing.
- Strict mode tests (T043, T044) must verify the exact exception type (`SpecKittyEventsError`).
- Concurrent resolution test must verify `resolution_event_id` matches the later event.
- Mid-mission strictness change must verify block events are preserved (not removed).

## Activity Log

- 2026-02-16T12:00:00Z – system – lane=planned – Prompt created.
- 2026-02-16T13:30:30Z – claude-opus – shell_pid=28797 – lane=doing – Assigned agent via workflow command
