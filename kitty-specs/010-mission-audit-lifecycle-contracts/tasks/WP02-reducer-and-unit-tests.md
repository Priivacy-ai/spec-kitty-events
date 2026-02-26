---
work_package_id: WP02
title: Reducer Implementation + Unit Tests
lane: "for_review"
dependencies:
- WP01
base_branch: main
base_commit: cee0731b0016e2eb66c2aabd9a8ec5f7d186d9c3
created_at: '2026-02-26T12:35:56.800294+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
phase: Phase 2 - Reducer
assignee: ''
agent: claude-sonnet
shell_pid: '34022'
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-25T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Reducer Implementation + Unit Tests

## Goal

Implement the `reduce_mission_audit_events()` pure function in `src/spec_kitty_events/mission_audit.py` with the full pipeline (sort → dedup → filter → fold → freeze), complete state machine transitions, anomaly detection, and `pending_decisions` management. Write comprehensive unit tests and Hypothesis property tests verifying all acceptance scenarios.

**Independent Test**: `python3.11 -m pytest tests/unit/test_mission_audit.py tests/test_mission_audit_reducer.py tests/property/test_mission_audit_determinism.py -v` — all pass.

## Context

WP01 created `src/spec_kitty_events/mission_audit.py` with all types and a stub reducer body (`...`). WP02 fills in that stub with a complete, correct implementation and validates it thoroughly.

**Existing patterns to follow**:
- `reduce_mission_dossier()` in `dossier.py` and `reduce_mission_next_events()` in `mission_next.py` are the canonical examples. The audit reducer follows the same pipeline pattern.
- The reducer uses `status_event_sort_key` and `dedup_events` already imported in `mission_audit.py` (from WP01).
- Golden-file replay fixtures are committed JSON files — future CI compares byte-for-byte.
- Property tests use `@settings(deadline=None)` to avoid Hypothesis deadline failures under pytest-cov instrumentation.

**Branch**: `010-mission-audit-lifecycle-contracts` — the WP01 worktree has already committed the core types module. WP02 adds the reducer body and tests.

## Subtasks

### T005 — Implement `reduce_mission_audit_events()` pipeline

Replace the `...` stub body with the full implementation in `src/spec_kitty_events/mission_audit.py`:

```python
def reduce_mission_audit_events(events: Sequence[Event]) -> ReducedMissionAuditState:
    """Deterministic reducer: Sequence[Event] → ReducedMissionAuditState.

    Pipeline: sort → dedup → filter(MISSION_AUDIT_EVENT_TYPES) → reduce → freeze.
    """
    # Step 1: Sort by (timestamp, lamport_clock) for determinism
    sorted_events = sorted(events, key=status_event_sort_key)

    # Step 2: Deduplicate by event_id
    deduped_events = dedup_events(sorted_events)

    # Step 3: Count events after dedup (before filter) — event_count is post-dedup
    event_count = len(deduped_events)

    # Step 4: Filter to mission-audit family only
    audit_events = [e for e in deduped_events if e.event_type in MISSION_AUDIT_EVENT_TYPES]

    # Step 5: Mutable accumulator for the fold
    state: dict = {
        "audit_status": AuditStatus.PENDING,
        "verdict": None,
        "severity": None,
        "findings_count": None,
        "artifact_ref": None,
        "partial_artifact_ref": None,
        "summary": None,
        "error_code": None,
        "error_message": None,
        "pending_decisions": [],
        "mission_id": None,
        "run_id": None,
        "feature_slug": None,
        "trigger_mode": None,
        "enforcement_mode": None,
        "audit_scope": None,
        "audit_scope_hash": None,
        "anomalies": [],
        "event_count": event_count,
    }
    requested_seen = False
    terminal_seen = False

    for event in audit_events:
        event_type = event.event_type
        event_id = event.event_id
        payload_dict = event.payload if isinstance(event.payload, dict) else {}

        # Anomaly: unrecognized event type (within family — defensive)
        if event_type not in MISSION_AUDIT_EVENT_TYPES:
            state["anomalies"].append(MissionAuditAnomaly(
                kind="unrecognized_event_type",
                event_id=event_id,
                message=f"Unrecognized event type in audit family: {event_type!r}",
            ))
            continue

        # Anomaly: event after terminal
        if terminal_seen:
            state["anomalies"].append(MissionAuditAnomaly(
                kind="event_after_terminal",
                event_id=event_id,
                message=f"Event {event_type!r} arrived after terminal state",
            ))
            continue

        # Anomaly: event before Requested (except Requested itself)
        if not requested_seen and event_type != MISSION_AUDIT_REQUESTED:
            state["anomalies"].append(MissionAuditAnomaly(
                kind="event_before_requested",
                event_id=event_id,
                message=f"Event {event_type!r} arrived before MissionAuditRequested",
            ))
            # Still process state transitions for robustness — do not skip

        if event_type == MISSION_AUDIT_REQUESTED:
            requested_seen = True
            payload = MissionAuditRequestedPayload.model_validate(payload_dict)
            state["mission_id"] = payload.mission_id
            state["run_id"] = payload.run_id
            state["feature_slug"] = payload.feature_slug
            state["trigger_mode"] = payload.trigger_mode
            state["enforcement_mode"] = payload.enforcement_mode
            state["audit_scope"] = tuple(payload.audit_scope)
            # status stays PENDING after Requested

        elif event_type == MISSION_AUDIT_STARTED:
            payload = MissionAuditStartedPayload.model_validate(payload_dict)
            state["audit_scope_hash"] = payload.audit_scope_hash
            if not state["mission_id"]:
                state["mission_id"] = payload.mission_id
                state["run_id"] = payload.run_id
                state["feature_slug"] = payload.feature_slug
            state["audit_status"] = AuditStatus.RUNNING

        elif event_type == MISSION_AUDIT_DECISION_REQUESTED:
            payload = MissionAuditDecisionRequestedPayload.model_validate(payload_dict)
            # Anomaly: duplicate decision_id
            existing_ids = [d.decision_id for d in state["pending_decisions"]]
            if payload.decision_id in existing_ids:
                state["anomalies"].append(MissionAuditAnomaly(
                    kind="duplicate_decision_id",
                    event_id=event_id,
                    message=f"Duplicate decision_id: {payload.decision_id!r}",
                ))
            else:
                state["pending_decisions"].append(PendingDecision(
                    decision_id=payload.decision_id,
                    question=payload.question,
                    context_summary=payload.context_summary,
                    severity=payload.severity,
                ))
            state["audit_status"] = AuditStatus.AWAITING_DECISION

        elif event_type == MISSION_AUDIT_COMPLETED:
            payload = MissionAuditCompletedPayload.model_validate(payload_dict)
            state["verdict"] = payload.verdict
            state["severity"] = payload.severity
            state["findings_count"] = payload.findings_count
            state["artifact_ref"] = payload.artifact_ref
            state["summary"] = payload.summary
            state["pending_decisions"] = []  # implicit resolution on terminal
            state["audit_status"] = AuditStatus.COMPLETED
            terminal_seen = True

        elif event_type == MISSION_AUDIT_FAILED:
            payload = MissionAuditFailedPayload.model_validate(payload_dict)
            state["error_code"] = payload.error_code
            state["error_message"] = payload.error_message
            state["partial_artifact_ref"] = payload.partial_artifact_ref
            state["pending_decisions"] = []  # implicit resolution on terminal
            state["audit_status"] = AuditStatus.FAILED
            terminal_seen = True

    # Step 6: Freeze and return
    return ReducedMissionAuditState(
        audit_status=state["audit_status"],
        verdict=state["verdict"],
        severity=state["severity"],
        findings_count=state["findings_count"],
        artifact_ref=state["artifact_ref"],
        partial_artifact_ref=state["partial_artifact_ref"],
        summary=state["summary"],
        error_code=state["error_code"],
        error_message=state["error_message"],
        pending_decisions=tuple(state["pending_decisions"]),
        mission_id=state["mission_id"],
        run_id=state["run_id"],
        feature_slug=state["feature_slug"],
        trigger_mode=state["trigger_mode"],
        enforcement_mode=state["enforcement_mode"],
        audit_scope=state["audit_scope"],
        audit_scope_hash=state["audit_scope_hash"],
        anomalies=tuple(state["anomalies"]),
        event_count=state["event_count"],
    )
```

**Critical notes**:
- `event_count` = number of events **after dedup** (post-step 2) — NOT after filter. This matches the dossier reducer pattern.
- `audit_scope` stored as `Optional[Tuple[str, ...]]` in state (converted from `List[str]` in payload).
- `pending_decisions` cleared to empty list on any terminal event (Completed or Failed).
- Anomaly for `event_before_requested`: record anomaly but still process the state transition (do not skip the event).

### T006 — Implement state machine transitions

The state machine is embedded within the fold above (T005). Verify the transitions match:

| Event | Pre-condition | Resulting `audit_status` |
|---|---|---|
| `MissionAuditRequested` | any | `pending` (unchanged) |
| `MissionAuditStarted` | any | `running` |
| `MissionAuditDecisionRequested` | `running` or `awaiting_decision` | `awaiting_decision` |
| `MissionAuditCompleted` | any non-terminal | `completed` (terminal) |
| `MissionAuditFailed` | any non-terminal | `failed` (terminal) |

Note: The state machine in WP02 does NOT enforce strict pre-conditions (e.g., Started requires Running) — it records anomalies but still applies transitions. This keeps the reducer non-crashing on malformed streams.

### T007 — Implement anomaly detection

Four anomaly `kind` values, recorded as `MissionAuditAnomaly` instances in the `anomalies` list:

1. **`event_before_requested`**: Any event other than `MissionAuditRequested` arrives before a `MissionAuditRequested` has been seen. Record anomaly AND still process the transition.

2. **`event_after_terminal`**: Any event arrives after `AuditStatus.COMPLETED` or `AuditStatus.FAILED`. Record anomaly and skip processing (do not apply transitions).

3. **`duplicate_decision_id`**: A `MissionAuditDecisionRequested` event has a `decision_id` already present in `pending_decisions`. Record anomaly and do NOT add the duplicate entry. Still update status to `awaiting_decision`.

4. **`unrecognized_event_type`**: An event in `MISSION_AUDIT_EVENT_TYPES` that does not match any known type. This is a defensive guard — in practice all five types are handled, but defensive coverage is required.

Anomaly ordering: anomalies are appended in event processing order (deterministic given sorted+deduped input).

### T008 — Implement pending_decisions management

- On `MissionAuditDecisionRequested`: if `decision_id` is new, append a `PendingDecision` to the list. If duplicate, record anomaly and skip append.
- On `MissionAuditCompleted` or `MissionAuditFailed`: clear `pending_decisions` to `[]` (implicit resolution).
- At end of fold: `pending_decisions` is converted `tuple()` for the frozen output model.
- No `answered_decisions` field — decision resolution is implicit (this is a locked decision from plan.md).

### T009 — Write unit tests in `tests/unit/test_mission_audit.py`

Create the file with these test cases:

```python
"""Unit tests for mission_audit module — payload validation, round-trip, edge cases.

Covers T009: payload validation (round-trip, required fields, Literal constraints,
Field constraints, enum validation, AuditArtifactRef composition, frozen immutability,
PendingDecision construction).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from spec_kitty_events.dossier import ContentHashRef, ProvenanceRef
from spec_kitty_events.mission_audit import (
    AUDIT_SCHEMA_VERSION,
    MISSION_AUDIT_EVENT_TYPES,
    TERMINAL_AUDIT_STATUSES,
    AuditArtifactRef,
    AuditSeverity,
    AuditStatus,
    AuditVerdict,
    MissionAuditCompletedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditFailedPayload,
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    PendingDecision,
    ReducedMissionAuditState,
)
```

**Tests to include** (name them descriptively):

1. **5 payload round-trips** — one per payload model. For each: construct with valid data, serialize with `model.model_dump(mode="json")`, round-trip via `ModelClass.model_validate(data)`, assert all fields equal. Use `MissionAuditCompletedPayload` with a full `AuditArtifactRef` (containing real `ContentHashRef` and `ProvenanceRef`).

2. **Required field rejection × 5** — for each payload type, omit one required field (e.g., omit `mission_id` from `MissionAuditRequestedPayload`, omit `verdict` from `MissionAuditCompletedPayload`, omit `decision_id` from `MissionAuditDecisionRequestedPayload`, omit `error_code` from `MissionAuditFailedPayload`, omit `audit_scope_hash` from `MissionAuditStartedPayload`). Assert `pytest.raises(ValidationError)`.

3. **Literal constraint rejection × 2**:
   - `MissionAuditRequestedPayload(trigger_mode="invalid", ...)` → `ValidationError`
   - `MissionAuditRequestedPayload(enforcement_mode="unknown", ...)` → `ValidationError`

4. **Field constraint rejection × 2**:
   - `MissionAuditCompletedPayload(findings_count=-1, ...)` → `ValidationError` (ge=0 violated)
   - `MissionAuditRequestedPayload(mission_id="", ...)` → `ValidationError` (min_length=1 violated)

5. **Enum validation × 3**:
   - Invalid `AuditVerdict` string → `ValidationError`
   - Invalid `AuditSeverity` string → `ValidationError`
   - Invalid `AuditStatus` string in any context → `ValidationError`

6. **`AuditArtifactRef` composition** — Construct with real `ContentHashRef` and `ProvenanceRef`, round-trip through `model_dump(mode="json")` and `model_validate()`. Assert `content_hash.hash` survives round-trip.

7. **Frozen immutability × 5** — for each frozen model (RequestedPayload, CompletedPayload, AuditArtifactRef, PendingDecision, ReducedMissionAuditState): construct a valid instance, attempt attribute assignment (`instance.mission_id = "x"`), assert `TypeError` is raised.

8. **`PendingDecision` construction** — Construct a valid `PendingDecision`, assert all fields accessible, assert frozen (assignment raises `TypeError`).

9. **`ReducedMissionAuditState` defaults** — `ReducedMissionAuditState()` with no args. Assert `audit_status == AuditStatus.PENDING`, `event_count == 0`, `anomalies == ()`, `pending_decisions == ()`.

10. **Constants** — Assert `len(MISSION_AUDIT_EVENT_TYPES) == 5`, `AUDIT_SCHEMA_VERSION == "2.5.0"`, `TERMINAL_AUDIT_STATUSES == {AuditStatus.COMPLETED, AuditStatus.FAILED}`.

### T010 — Write reducer unit tests in `tests/test_mission_audit_reducer.py`

Create the file with these test cases:

```python
"""Reducer unit tests for mission_audit (T010).

Covers: happy-path pass, happy-path fail, decision checkpoint, empty stream,
deduplication, 4 anomaly scenarios, terminal clears pending, partial artifact,
3 golden-file replay scenarios.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from spec_kitty_events.dossier import ContentHashRef, ProvenanceRef
from spec_kitty_events.mission_audit import (
    MISSION_AUDIT_COMPLETED,
    MISSION_AUDIT_DECISION_REQUESTED,
    MISSION_AUDIT_FAILED,
    MISSION_AUDIT_REQUESTED,
    MISSION_AUDIT_STARTED,
    AuditArtifactRef,
    AuditSeverity,
    AuditStatus,
    AuditVerdict,
    MissionAuditCompletedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditFailedPayload,
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    reduce_mission_audit_events,
)
from spec_kitty_events.models import Event
```

**Helper**: Write an `_event(event_type, payload_obj, *, lamport=1)` factory that constructs an `Event` with deterministic `event_id` (ULID or `str(uuid4())`), `timestamp`, `aggregate_id="audit/run-001"`, `node_id="node-1"`, `project_uuid`, and `correlation_id`. Use `payload_obj.model_dump()` for the payload dict.

**Helper**: Write common fixture data (`_ARTIFACT_REF`, `_CONTENT_HASH_REF`, `_PROVENANCE_REF`) to reuse across tests.

**Tests to include**:

1. `test_empty_stream` — `reduce_mission_audit_events([])` returns `ReducedMissionAuditState()` with defaults.

2. `test_happy_path_pass` — Requested → Started → Completed(pass, severity=info, findings_count=0) → assert `audit_status=completed`, `verdict=pass`, `artifact_ref` populated, `anomalies=()`, `event_count=3`.

3. `test_happy_path_fail` — Requested → Started → Failed(error_code="TIMEOUT") → assert `audit_status=failed`, `verdict=None`, `error_code="TIMEOUT"`, `event_count=3`.

4. `test_decision_checkpoint` — Requested → Started → DecisionRequested(decision_id="dec-1") → assert `audit_status=awaiting_decision`, `len(pending_decisions)==1`. Then add Completed → assert `pending_decisions==()`, `audit_status=completed`.

5. `test_deduplication` — Build a 3-event stream. Double every event (identical `event_id`). Assert result equals reducing the original 3-event stream. Assert `event_count` equals the deduplicated count (3), not the doubled count (6).

6. `test_anomaly_event_before_requested` — Feed `MissionAuditStarted` before any `MissionAuditRequested`. Assert exactly one anomaly with `kind="event_before_requested"`.

7. `test_anomaly_event_after_terminal` — Feed Requested → Started → Completed, then feed another `MissionAuditStarted`. Assert exactly one anomaly with `kind="event_after_terminal"` (the post-terminal event is recorded as anomaly, `audit_status` remains `completed`).

8. `test_anomaly_duplicate_decision_id` — Feed DecisionRequested twice with same `decision_id`. Assert `kind="duplicate_decision_id"` anomaly, `len(pending_decisions)==1` (no duplicate added).

9. `test_anomaly_unrecognized_type` — This is harder to trigger since filter step removes non-audit events; instead test that an event where `event_type` is not in the handled branches but IS in `MISSION_AUDIT_EVENT_TYPES` triggers the defensive guard. (In practice, if all 5 types are handled, this branch is unreachable — test it by temporarily using a mock or subclassing. Alternatively, test that a non-audit event is silently ignored by the filter step and does not appear in anomalies.)

10. `test_terminal_clears_pending_decisions` — Feed DecisionRequested, then Completed. Assert `pending_decisions == ()` after Completed.

11. `test_partial_artifact_on_failure` — Feed Failed with `partial_artifact_ref` populated. Assert `partial_artifact_ref` is not None in state, `verdict` is None.

12–14. **Golden-file replay × 3** — Load 3 JSONL replay streams from `tests/fixtures/mission_audit_golden/`. For each: parse events, reduce, serialize output with `model_dump(mode="json", round_trip=True)`, compare against committed golden JSON file. On first run (golden file absent), write it and mark test as skipped. On subsequent runs, assert exact match.

**Golden files location**: `tests/fixtures/mission_audit_golden/` — create this directory. The three streams correspond to:
- `replay_pass.jsonl` + `replay_pass_output.json` (Requested → Started → Completed pass)
- `replay_fail.jsonl` + `replay_fail_output.json` (Requested → Started → Failed)
- `replay_decision_checkpoint.jsonl` + `replay_decision_checkpoint_output.json` (Requested → Started → DecisionRequested → Completed)

Generate and commit the golden output files as part of this WP so future CI can compare against them.

### T011 — Write Hypothesis property tests in `tests/property/test_mission_audit_determinism.py`

```python
"""Hypothesis property tests proving mission-audit reducer determinism.

Tests: order independence (≥200 examples), idempotent dedup (≥200 examples),
monotonic event_count (≥200 examples).
"""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
```

**Three property tests**:

1. **Order independence** (`@settings(max_examples=200, deadline=None)`): Generate a list of 1–8 `Event` objects from a fixed mission-audit event sequence. Shuffle the list into two permutations. Assert `reduce_mission_audit_events(perm_a) == reduce_mission_audit_events(perm_b)`.

   Strategy: use `st.permutations(base_events)` where `base_events` is a predefined list of valid audit events.

2. **Idempotent dedup** (`@settings(max_examples=200, deadline=None)`): Generate a list of 1–5 unique events. Double every event (append a copy with the same `event_id`). Assert `reduce_mission_audit_events(doubled) == reduce_mission_audit_events(original)`.

3. **Monotonic event_count** (`@settings(max_examples=200, deadline=None)`): Generate a list of 1–8 events (may contain duplicates). Reduce. Assert `result.event_count <= len(input_events)` (dedup can only reduce or maintain count, never increase).

**Implementation note**: Hypothesis strategies for `Event` objects can be simple — use a predefined pool of valid events and sample from it. Avoid complex strategies that generate Pydantic models dynamically (this leads to flakiness). Use `st.sampled_from(VALID_EVENT_POOL)` where `VALID_EVENT_POOL` is a module-level list of pre-built `Event` instances.

## Acceptance Criteria

- [ ] `reduce_mission_audit_events([])` returns `ReducedMissionAuditState()` with defaults
- [ ] Happy-path pass: Requested→Started→Completed → `audit_status=completed`, `verdict=pass`, `anomalies=()`, `event_count=3`
- [ ] Happy-path fail: Requested→Started→Failed → `audit_status=failed`, `verdict=None`
- [ ] Decision checkpoint: pending_decisions populated on DecisionRequested, cleared on Completed/Failed
- [ ] Deduplication: doubled event stream produces same result as single-copy stream, `event_count` reflects deduplicated count
- [ ] Anomaly `event_before_requested` recorded when non-Requested event arrives first
- [ ] Anomaly `event_after_terminal` recorded when event arrives after Completed/Failed
- [ ] Anomaly `duplicate_decision_id` recorded for repeated decision_id; no duplicate entry in pending_decisions
- [ ] Partial artifact: `partial_artifact_ref` preserved in failed state
- [ ] Golden-file replay: 3 streams produce exact match against committed output files
- [ ] `event_count` equals post-dedup count (not post-filter count)
- [ ] All unit tests in `tests/unit/test_mission_audit.py` pass
- [ ] Hypothesis property tests pass ≥200 examples for all three properties
- [ ] `mypy --strict src/spec_kitty_events/mission_audit.py` — zero errors
- [ ] `python3.11 -m pytest tests/unit/test_mission_audit.py tests/test_mission_audit_reducer.py tests/property/test_mission_audit_determinism.py -v` — all pass

## Implementation Notes

- **Install first**: Run `python3.11 -m pip install -e ".[dev]"` immediately after entering the worktree.
- **Reducer body location**: The `reduce_mission_audit_events` function stub is at the bottom of `src/spec_kitty_events/mission_audit.py` (created by WP01). Replace the `...` body in place — do not duplicate the function signature.
- **mypy strict**: The reducer uses type narrowing via `if event_type == MISSION_AUDIT_REQUESTED:` — be explicit about payload type after `model_validate`. Assign to a typed local variable (`payload: MissionAuditRequestedPayload = MissionAuditRequestedPayload.model_validate(payload_dict)`) rather than using dynamic dispatch to satisfy mypy.
- **`event_count` semantics**: Count events AFTER dedup (step 2), BEFORE filter (step 3). This is the canonical count.
- **`from __future__ import annotations`**: Already present in `mission_audit.py` from WP01. Do NOT add it again.
- **Golden files**: Use `json.dumps(state.model_dump(mode="json"), sort_keys=True, indent=2)` for golden file serialization. Load with `json.loads(path.read_text())`. Compare dicts, not strings, to avoid whitespace brittleness.
- **Hypothesis strategies**: Module-level pool of pre-built `Event` objects is simpler and more reliable than generating Event objects dynamically from strategies.
- **`@settings(deadline=None)`**: Required on all Hypothesis tests due to Pydantic model construction overhead under pytest-cov.

## Test Commands

```bash
# Install editable package in worktree first
python3.11 -m pip install -e ".[dev]"

# Run WP02 tests
python3.11 -m pytest tests/unit/test_mission_audit.py tests/test_mission_audit_reducer.py tests/property/test_mission_audit_determinism.py -v

# mypy check
mypy --strict src/spec_kitty_events/mission_audit.py

# Full suite (no regressions)
python3.11 -m pytest tests/ -v --tb=short
```

## Files to Create/Modify

| File | Action |
|---|---|
| `src/spec_kitty_events/mission_audit.py` | **MODIFY** — replace `...` reducer stub with full implementation |
| `tests/unit/test_mission_audit.py` | **CREATE** — payload validation unit tests |
| `tests/test_mission_audit_reducer.py` | **CREATE** — reducer unit tests + golden-file replay |
| `tests/property/test_mission_audit_determinism.py` | **CREATE** — Hypothesis property tests |
| `tests/fixtures/mission_audit_golden/replay_pass.jsonl` | **CREATE** — golden replay input |
| `tests/fixtures/mission_audit_golden/replay_pass_output.json` | **CREATE** — golden reducer output |
| `tests/fixtures/mission_audit_golden/replay_fail.jsonl` | **CREATE** — golden replay input |
| `tests/fixtures/mission_audit_golden/replay_fail_output.json` | **CREATE** — golden reducer output |
| `tests/fixtures/mission_audit_golden/replay_decision_checkpoint.jsonl` | **CREATE** — golden replay input |
| `tests/fixtures/mission_audit_golden/replay_decision_checkpoint_output.json` | **CREATE** — golden reducer output |

No other files are modified in WP02.

## Dependencies

- **Depends on**: WP01 (core types module — enums, value objects, payload models, `ReducedMissionAuditState`, reducer stub).
- **Unblocks**: WP04 (conformance tests need the working reducer to exercise replay→reduce flow).
- **Runs in parallel with**: WP03 (conformance integration has no dependency on the reducer implementation).

## Completion Steps

When all subtasks are done and acceptance criteria pass:

1. Run the full test command (above) and mypy.
2. Commit: `git add src/ tests/ && git commit -m "feat(010): reducer implementation + unit tests — WP02"`
3. Mark subtasks done: `spec-kitty agent tasks mark-status T005 T006 T007 T008 T009 T010 T011 --status done`
4. Rebase on main: `git rebase main`
5. Move to review: `spec-kitty agent tasks move-task WP02 --to for_review --note "Reducer implemented, all tests pass, mypy clean"`

## Activity Log

- 2026-02-26T12:35:56Z – claude-sonnet – shell_pid=34022 – lane=doing – Assigned agent via workflow command
- 2026-02-26T12:44:55Z – claude-sonnet – shell_pid=34022 – lane=for_review – Reducer implemented, 45 tests pass, mypy --strict clean. Golden replay × 3 committed. Merged WP01 branch to get core types.
