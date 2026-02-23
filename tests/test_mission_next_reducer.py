"""Tests for mission-next reducer — happy path, anomalies, alias, and edge cases."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from spec_kitty_events import (
    Event,
    ReducedMissionRunState,
    reduce_mission_next_events,
)
from spec_kitty_events.mission_next import (
    DECISION_INPUT_ANSWERED,
    DECISION_INPUT_REQUESTED,
    MISSION_NEXT_EVENT_TYPES,
    MISSION_RUN_COMPLETED,
    MISSION_RUN_STARTED,
    NEXT_STEP_AUTO_COMPLETED,
    NEXT_STEP_ISSUED,
    NEXT_STEP_PLANNED,
    _COMPLETION_ALIAS,
    MissionRunStatus,
)

UTC = timezone.utc
_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")

_clock_counter = 0


def _make_actor_dict(
    actor_id: str = "agent-claude",
    actor_type: str = "llm",
) -> dict:  # type: ignore[type-arg]
    return {
        "actor_id": actor_id,
        "actor_type": actor_type,
        "display_name": "Claude",
        "provider": "anthropic",
        "model": "claude-opus-4-6",
    }


def make_event(
    event_type: str,
    payload: dict,  # type: ignore[type-arg]
    event_id: str | None = None,
    lamport_clock: int | None = None,
    aggregate_id: str = "run/run-001",
) -> Event:
    """Factory for creating test Event instances."""
    global _clock_counter
    if lamport_clock is None:
        _clock_counter += 1
        lamport_clock = _clock_counter
    if event_id is None:
        event_id = f"01HX{lamport_clock:022d}"
    corr_id = f"01CX{lamport_clock:022d}"
    return Event(
        event_id=event_id,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload,
        timestamp=datetime(2024, 1, 1, 0, 0, lamport_clock % 60, tzinfo=UTC).isoformat(),
        node_id="test-node",
        lamport_clock=lamport_clock,
        correlation_id=corr_id,
        project_uuid=_PROJECT_UUID,
        schema_version="2.0.0",
    )


# ── Empty Input ──────────────────────────────────────────────────────────────


class TestReducerEmptyInput:
    """Tests for reducer short-circuit paths."""

    def test_empty_list(self) -> None:
        state = reduce_mission_next_events([])
        assert state == ReducedMissionRunState()
        assert state.event_count == 0

    def test_non_mission_next_events(self) -> None:
        event = make_event("WPStatusChanged", {"wp_id": "WP01"}, lamport_clock=1)
        state = reduce_mission_next_events([event])
        assert state == ReducedMissionRunState()


# ── Happy Path ───────────────────────────────────────────────────────────────


class TestReducerHappyPath:
    """End-to-end reducer test matching actual runtime execution order."""

    def test_full_lifecycle(self) -> None:
        """start → step_issued(S1) → step_auto_completed(S1) →
        step_issued(S2) → decision_requested(d1, S2) →
        decision_answered(d1) → step_auto_completed(S2) →
        mission_run_completed"""
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "feat-login", "actor": actor,
            }, lamport_clock=1),
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1", "actor": actor,
            }, lamport_clock=2),
            make_event(NEXT_STEP_AUTO_COMPLETED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1",
                "result": "success", "actor": actor,
            }, lamport_clock=3),
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-1", "step_id": "S2", "agent_id": "a1", "actor": actor,
            }, lamport_clock=4),
            make_event(DECISION_INPUT_REQUESTED, {
                "run_id": "run-1", "decision_id": "d1", "step_id": "S2",
                "question": "Which DB?", "options": ["pg", "mysql"], "actor": actor,
            }, lamport_clock=5),
            make_event(DECISION_INPUT_ANSWERED, {
                "run_id": "run-1", "decision_id": "d1", "answer": "pg",
                "actor": _make_actor_dict("user-1", "human"),
            }, lamport_clock=6),
            make_event(NEXT_STEP_AUTO_COMPLETED, {
                "run_id": "run-1", "step_id": "S2", "agent_id": "a1",
                "result": "success", "actor": actor,
            }, lamport_clock=7),
            make_event(MISSION_RUN_COMPLETED, {
                "run_id": "run-1", "mission_key": "feat-login", "actor": actor,
            }, lamport_clock=8),
        ]

        state = reduce_mission_next_events(events)

        assert state.run_id == "run-1"
        assert state.mission_key == "feat-login"
        assert state.run_status == MissionRunStatus.COMPLETED
        assert state.current_step_id is None
        assert state.completed_steps == ("S1", "S2")
        assert "d1" not in state.pending_decisions
        assert "d1" in state.answered_decisions
        assert state.answered_decisions["d1"].answer == "pg"
        assert state.anomalies == ()
        assert state.event_count == 8


# ── Duplicate Start ──────────────────────────────────────────────────────────


class TestDuplicateStart:
    """Tests that duplicate MissionRunStarted is anomalied (first wins)."""

    def test_duplicate_start(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-2", "mission_key": "mk2", "actor": actor,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_id == "run-1"
        assert state.mission_key == "mk1"
        assert len(state.anomalies) == 1
        assert "Duplicate" in state.anomalies[0].reason


# ── Event After Terminal ─────────────────────────────────────────────────────


class TestEventAfterTerminal:
    """Tests that events after terminal state produce anomalies."""

    def test_event_after_completed(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(MISSION_RUN_COMPLETED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=2),
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1", "actor": actor,
            }, lamport_clock=3),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_status == MissionRunStatus.COMPLETED
        assert len(state.anomalies) == 1
        assert "terminal" in state.anomalies[0].reason.lower()


# ── Event Before Start ───────────────────────────────────────────────────────


class TestEventBeforeStart:
    """Tests that events before MissionRunStarted produce anomalies."""

    def test_step_before_start(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1", "actor": actor,
            }, lamport_clock=1),
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_id == "run-1"
        assert len(state.anomalies) == 1
        assert "before" in state.anomalies[0].reason.lower()


# ── Duplicate Decision Request ───────────────────────────────────────────────


class TestDuplicateDecisionRequest:
    """Tests that duplicate decision requests produce anomalies."""

    def test_duplicate_decision_id(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(DECISION_INPUT_REQUESTED, {
                "run_id": "run-1", "decision_id": "d1", "step_id": "S1",
                "question": "Q1?", "actor": actor,
            }, lamport_clock=2),
            make_event(DECISION_INPUT_REQUESTED, {
                "run_id": "run-1", "decision_id": "d1", "step_id": "S1",
                "question": "Q1?", "actor": actor,
            }, lamport_clock=3),
        ]
        state = reduce_mission_next_events(events)
        assert len(state.anomalies) == 1
        assert "Duplicate decision" in state.anomalies[0].reason


# ── Decision Lifecycle ───────────────────────────────────────────────────────


class TestDecisionLifecycle:
    """Tests that answering a decision clears it from pending."""

    def test_request_then_answer(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(DECISION_INPUT_REQUESTED, {
                "run_id": "run-1", "decision_id": "d1", "step_id": "S1",
                "question": "Q?", "actor": actor,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert "d1" in state.pending_decisions
        assert "d1" not in state.answered_decisions

        # Now add the answer
        events.append(make_event(DECISION_INPUT_ANSWERED, {
            "run_id": "run-1", "decision_id": "d1", "answer": "yes",
            "actor": _make_actor_dict("user-1", "human"),
        }, lamport_clock=3))
        state = reduce_mission_next_events(events)
        assert "d1" not in state.pending_decisions
        assert "d1" in state.answered_decisions


# ── Terminal Idempotency ─────────────────────────────────────────────────────


class TestTerminalIdempotency:
    """Tests that double completion produces anomaly."""

    def test_double_completion(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(MISSION_RUN_COMPLETED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=2),
            make_event(MISSION_RUN_COMPLETED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=3),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_status == MissionRunStatus.COMPLETED
        assert len(state.anomalies) == 1
        assert "idempotency" in state.anomalies[0].reason.lower()


# ── Step Tracking ────────────────────────────────────────────────────────────


class TestStepTracking:
    """Tests step state management (current step, completed steps)."""

    def test_issued_sets_current(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1", "actor": actor,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert state.current_step_id == "S1"
        assert state.completed_steps == ()

    def test_completed_clears_current_and_adds_to_completed(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1", "actor": actor,
            }, lamport_clock=2),
            make_event(NEXT_STEP_AUTO_COMPLETED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1",
                "result": "success", "actor": actor,
            }, lamport_clock=3),
        ]
        state = reduce_mission_next_events(events)
        assert state.current_step_id is None
        assert state.completed_steps == ("S1",)


# ── Event Dedup ──────────────────────────────────────────────────────────────


class TestEventDedup:
    """Tests that duplicate event_id events are deduplicated."""

    def test_same_event_id_deduped(self) -> None:
        actor = _make_actor_dict()
        eid = "01HX0000000000000000000001"
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, event_id=eid, lamport_clock=1),
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, event_id=eid, lamport_clock=1),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_id == "run-1"
        assert state.anomalies == ()
        assert state.event_count == 1


# ── Completion Alias ─────────────────────────────────────────────────────────


class TestCompletionAlias:
    """Tests that 'MissionCompleted' event_type is accepted as MissionRunCompleted."""

    def test_mission_completed_alias_accepted(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(_COMPLETION_ALIAS, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_status == MissionRunStatus.COMPLETED
        assert state.anomalies == ()


# ── NextStepPlanned Ignored ──────────────────────────────────────────────────


class TestNextStepPlannedIgnored:
    """Tests that NextStepPlanned events are silently skipped."""

    def test_next_step_planned_silently_skipped(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(NEXT_STEP_PLANNED, {
                "some": "data",
            }, lamport_clock=2),
            make_event(MISSION_RUN_COMPLETED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=3),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_status == MissionRunStatus.COMPLETED
        assert state.anomalies == ()
        assert state.event_count == 3


# ── P0: Lifecycle MissionCompleted Must Not Terminate Run ─────────────────────


class TestLifecycleMissionCompletedDoesNotTerminateRun:
    """P0 fix: lifecycle MissionCompleted payload must not falsely terminate a run."""

    def test_lifecycle_payload_rejected_as_alias(self) -> None:
        """A MissionCompleted event with lifecycle-shaped payload (mission_id,
        mission_type, final_phase, actor=str) should be rejected by the alias
        gate and recorded as an anomaly — not terminate the run."""
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            # Lifecycle-shaped MissionCompleted — no run_id, no RuntimeActorIdentity
            make_event(_COMPLETION_ALIAS, {
                "mission_id": "M001",
                "mission_type": "software-dev",
                "final_phase": "deliver",
                "actor": "user-1",
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        # Run should still be RUNNING, not COMPLETED
        assert state.run_status == MissionRunStatus.RUNNING
        assert len(state.anomalies) == 1
        assert "alias ignored" in state.anomalies[0].reason.lower()
        assert "lifecycle" in state.anomalies[0].reason.lower()

    def test_run_scoped_alias_still_accepted(self) -> None:
        """A MissionCompleted event with run-scoped payload (run_id, mission_key,
        actor=RuntimeActorIdentity) should still terminate the run."""
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(_COMPLETION_ALIAS, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_status == MissionRunStatus.COMPLETED
        assert state.anomalies == ()

    def test_mixed_stream_lifecycle_and_run_events(self) -> None:
        """When lifecycle and mission-next events coexist in a stream,
        lifecycle MissionCompleted must not corrupt the run projection."""
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1", "actor": actor,
            }, lamport_clock=2),
            # Lifecycle completion for the mission — should be anomaly, not terminal
            make_event(_COMPLETION_ALIAS, {
                "mission_id": "M001",
                "mission_type": "software-dev",
                "final_phase": "deliver",
                "actor": "user-1",
            }, lamport_clock=3),
            # Run continues
            make_event(NEXT_STEP_AUTO_COMPLETED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1",
                "result": "success", "actor": actor,
            }, lamport_clock=4),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_status == MissionRunStatus.RUNNING
        assert state.completed_steps == ("S1",)
        assert len(state.anomalies) == 1


# ── P1: Run-ID Consistency Guard ─────────────────────────────────────────────


class TestRunIdConsistency:
    """P1 fix: events with mismatched run_id should be anomalied and skipped."""

    def test_step_issued_wrong_run_id(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-OTHER", "step_id": "S1", "agent_id": "a1", "actor": actor,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert state.current_step_id is None  # not applied
        assert len(state.anomalies) == 1
        assert "run_id mismatch" in state.anomalies[0].reason

    def test_step_completed_wrong_run_id(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1", "actor": actor,
            }, lamport_clock=2),
            make_event(NEXT_STEP_AUTO_COMPLETED, {
                "run_id": "run-OTHER", "step_id": "S1", "agent_id": "a1",
                "result": "success", "actor": actor,
            }, lamport_clock=3),
        ]
        state = reduce_mission_next_events(events)
        assert state.current_step_id == "S1"  # not cleared
        assert state.completed_steps == ()  # not added
        assert len(state.anomalies) == 1

    def test_decision_requested_wrong_run_id(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(DECISION_INPUT_REQUESTED, {
                "run_id": "run-OTHER", "decision_id": "d1", "step_id": "S1",
                "question": "Q?", "actor": actor,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert state.pending_decisions == {}
        assert len(state.anomalies) == 1

    def test_decision_answered_wrong_run_id(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(DECISION_INPUT_REQUESTED, {
                "run_id": "run-1", "decision_id": "d1", "step_id": "S1",
                "question": "Q?", "actor": actor,
            }, lamport_clock=2),
            make_event(DECISION_INPUT_ANSWERED, {
                "run_id": "run-OTHER", "decision_id": "d1", "answer": "yes",
                "actor": _make_actor_dict("user-1", "human"),
            }, lamport_clock=3),
        ]
        state = reduce_mission_next_events(events)
        assert "d1" in state.pending_decisions  # not cleared
        assert state.answered_decisions == {}
        assert len(state.anomalies) == 1

    def test_completion_wrong_run_id(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(MISSION_RUN_COMPLETED, {
                "run_id": "run-OTHER", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_status == MissionRunStatus.RUNNING  # not terminated
        assert len(state.anomalies) == 1
        assert "run_id mismatch" in state.anomalies[0].reason


# ── P1: Malformed Payload Resilience ─────────────────────────────────────────


class TestMalformedPayloadResilience:
    """P1 fix: malformed payloads produce anomalies instead of crashing."""

    def test_malformed_start_payload(self) -> None:
        events = [
            make_event(MISSION_RUN_STARTED, {
                "bad": "payload",
            }, lamport_clock=1),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_id is None
        assert len(state.anomalies) == 1
        assert "Invalid MissionRunStarted" in state.anomalies[0].reason

    def test_malformed_step_issued_payload(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(NEXT_STEP_ISSUED, {
                "garbage": True,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert state.current_step_id is None
        assert len(state.anomalies) == 1
        assert "Invalid NextStepIssued" in state.anomalies[0].reason

    def test_malformed_step_completed_payload(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(NEXT_STEP_AUTO_COMPLETED, {
                "nope": 42,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert len(state.anomalies) == 1
        assert "Invalid NextStepAutoCompleted" in state.anomalies[0].reason

    def test_malformed_decision_requested_payload(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(DECISION_INPUT_REQUESTED, {}, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert len(state.anomalies) == 1
        assert "Invalid DecisionInputRequested" in state.anomalies[0].reason

    def test_malformed_decision_answered_payload(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(DECISION_INPUT_ANSWERED, {
                "only_partial": "data",
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert len(state.anomalies) == 1
        assert "Invalid DecisionInputAnswered" in state.anomalies[0].reason

    def test_malformed_completion_payload(self) -> None:
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(MISSION_RUN_COMPLETED, {
                "invalid": True,
            }, lamport_clock=2),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_status == MissionRunStatus.RUNNING  # not terminated
        assert len(state.anomalies) == 1
        assert "Invalid MissionRunCompleted" in state.anomalies[0].reason

    def test_bad_event_does_not_stop_subsequent_processing(self) -> None:
        """After a malformed event, the reducer continues processing."""
        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=1),
            make_event(NEXT_STEP_ISSUED, {"garbage": True}, lamport_clock=2),
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1", "actor": actor,
            }, lamport_clock=3),
            make_event(MISSION_RUN_COMPLETED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=4),
        ]
        state = reduce_mission_next_events(events)
        assert state.run_status == MissionRunStatus.COMPLETED
        assert state.current_step_id == "S1"  # second issued was valid
        assert len(state.anomalies) == 1  # only the bad one


# ── Determinism ──────────────────────────────────────────────────────────────


class TestDeterminism:
    """Property test proving reducer determinism across physical orderings."""

    @given(st.randoms())
    @settings(max_examples=200)
    def test_deterministic_across_permutations(self, rng: object) -> None:
        import random as _rng_mod
        rng_inst = _rng_mod.Random()

        actor = _make_actor_dict()
        events = [
            make_event(MISSION_RUN_STARTED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=10),
            make_event(NEXT_STEP_ISSUED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1", "actor": actor,
            }, lamport_clock=20),
            make_event(NEXT_STEP_AUTO_COMPLETED, {
                "run_id": "run-1", "step_id": "S1", "agent_id": "a1",
                "result": "success", "actor": actor,
            }, lamport_clock=30),
            make_event(MISSION_RUN_COMPLETED, {
                "run_id": "run-1", "mission_key": "mk1", "actor": actor,
            }, lamport_clock=40),
        ]

        canonical = reduce_mission_next_events(events)

        shuffled = list(events)
        rng_inst.shuffle(shuffled)
        result = reduce_mission_next_events(shuffled)

        assert result.run_id == canonical.run_id
        assert result.run_status == canonical.run_status
        assert result.completed_steps == canonical.completed_steps
        assert result.event_count == canonical.event_count
