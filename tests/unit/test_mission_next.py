"""Unit tests for mission-next runtime event contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.mission_next import (
    DECISION_INPUT_ANSWERED,
    DECISION_INPUT_REQUESTED,
    MISSION_NEXT_EVENT_TYPES,
    MISSION_RUN_COMPLETED,
    MISSION_RUN_STARTED,
    NEXT_STEP_AUTO_COMPLETED,
    NEXT_STEP_ISSUED,
    NEXT_STEP_PLANNED,
    TERMINAL_RUN_STATUSES,
    _COMPLETION_ALIAS,
    DecisionInputAnsweredPayload,
    DecisionInputRequestedPayload,
    MissionNextAnomaly,
    MissionRunCompletedPayload,
    MissionRunStartedPayload,
    MissionRunStatus,
    NextStepAutoCompletedPayload,
    NextStepIssuedPayload,
    ReducedMissionRunState,
    RuntimeActorIdentity,
)


# ── Constants ────────────────────────────────────────────────────────────────


class TestConstants:
    """Tests for event type constants."""

    def test_event_type_values(self) -> None:
        assert MISSION_RUN_STARTED == "MissionRunStarted"
        assert NEXT_STEP_PLANNED == "NextStepPlanned"
        assert NEXT_STEP_ISSUED == "NextStepIssued"
        assert NEXT_STEP_AUTO_COMPLETED == "NextStepAutoCompleted"
        assert DECISION_INPUT_REQUESTED == "DecisionInputRequested"
        assert DECISION_INPUT_ANSWERED == "DecisionInputAnswered"
        assert MISSION_RUN_COMPLETED == "MissionRunCompleted"

    def test_completion_alias(self) -> None:
        assert _COMPLETION_ALIAS == "MissionCompleted"

    def test_frozenset_contains_all_types(self) -> None:
        assert MISSION_RUN_STARTED in MISSION_NEXT_EVENT_TYPES
        assert NEXT_STEP_PLANNED in MISSION_NEXT_EVENT_TYPES
        assert NEXT_STEP_ISSUED in MISSION_NEXT_EVENT_TYPES
        assert NEXT_STEP_AUTO_COMPLETED in MISSION_NEXT_EVENT_TYPES
        assert DECISION_INPUT_REQUESTED in MISSION_NEXT_EVENT_TYPES
        assert DECISION_INPUT_ANSWERED in MISSION_NEXT_EVENT_TYPES
        assert MISSION_RUN_COMPLETED in MISSION_NEXT_EVENT_TYPES
        assert _COMPLETION_ALIAS in MISSION_NEXT_EVENT_TYPES

    def test_frozenset_is_frozen(self) -> None:
        assert isinstance(MISSION_NEXT_EVENT_TYPES, frozenset)

    def test_frozenset_size(self) -> None:
        assert len(MISSION_NEXT_EVENT_TYPES) == 8


# ── MissionRunStatus Enum ────────────────────────────────────────────────────


class TestMissionRunStatus:
    """Tests for MissionRunStatus enum."""

    def test_enum_values(self) -> None:
        assert MissionRunStatus.RUNNING == "running"
        assert MissionRunStatus.COMPLETED == "completed"

    def test_terminal_statuses(self) -> None:
        assert MissionRunStatus.COMPLETED in TERMINAL_RUN_STATUSES

    def test_running_not_terminal(self) -> None:
        assert MissionRunStatus.RUNNING not in TERMINAL_RUN_STATUSES

    def test_terminal_statuses_frozen(self) -> None:
        assert isinstance(TERMINAL_RUN_STATUSES, frozenset)


# ── RuntimeActorIdentity ─────────────────────────────────────────────────────


def _make_actor(**overrides: object) -> RuntimeActorIdentity:
    defaults = {
        "actor_id": "agent-claude",
        "actor_type": "llm",
        "display_name": "Claude",
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "tool": None,
    }
    defaults.update(overrides)
    return RuntimeActorIdentity(**defaults)  # type: ignore[arg-type]


class TestRuntimeActorIdentity:
    """Tests for RuntimeActorIdentity value object."""

    def test_llm_actor(self) -> None:
        actor = _make_actor()
        assert actor.actor_id == "agent-claude"
        assert actor.actor_type == "llm"
        assert actor.display_name == "Claude"
        assert actor.provider == "anthropic"
        assert actor.model == "claude-opus-4-6"

    def test_human_actor(self) -> None:
        actor = _make_actor(actor_id="user-1", actor_type="human")
        assert actor.actor_type == "human"

    def test_service_actor(self) -> None:
        actor = _make_actor(actor_id="svc-ci", actor_type="service")
        assert actor.actor_type == "service"

    def test_invalid_actor_type(self) -> None:
        with pytest.raises(PydanticValidationError):
            _make_actor(actor_type="robot")

    def test_empty_actor_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            _make_actor(actor_id="")

    def test_frozen(self) -> None:
        actor = _make_actor()
        with pytest.raises(Exception):
            actor.actor_id = "new"  # type: ignore[misc]

    def test_default_display_name(self) -> None:
        actor = RuntimeActorIdentity(actor_id="x", actor_type="human")
        assert actor.display_name == ""

    def test_optional_fields_default_none(self) -> None:
        actor = RuntimeActorIdentity(actor_id="x", actor_type="human")
        assert actor.provider is None
        assert actor.model is None
        assert actor.tool is None


# ── Payload Models ───────────────────────────────────────────────────────────


class TestMissionRunStartedPayload:
    """Tests for MissionRunStartedPayload."""

    def test_valid(self) -> None:
        p = MissionRunStartedPayload(
            run_id="run-1", mission_key="feat-login", actor=_make_actor()
        )
        assert p.run_id == "run-1"
        assert p.mission_key == "feat-login"

    def test_missing_run_id(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionRunStartedPayload(
                mission_key="feat-login", actor=_make_actor()
            )  # type: ignore[call-arg]

    def test_frozen(self) -> None:
        p = MissionRunStartedPayload(
            run_id="run-1", mission_key="feat-login", actor=_make_actor()
        )
        with pytest.raises(Exception):
            p.run_id = "new"  # type: ignore[misc]

    def test_round_trip(self) -> None:
        p = MissionRunStartedPayload(
            run_id="run-1", mission_key="feat-login", actor=_make_actor()
        )
        data = p.model_dump()
        p2 = MissionRunStartedPayload(**data)
        assert p == p2


class TestNextStepIssuedPayload:
    """Tests for NextStepIssuedPayload."""

    def test_valid(self) -> None:
        p = NextStepIssuedPayload(
            run_id="run-1", step_id="s1", agent_id="a1", actor=_make_actor()
        )
        assert p.step_id == "s1"
        assert p.agent_id == "a1"

    def test_missing_step_id(self) -> None:
        with pytest.raises(PydanticValidationError):
            NextStepIssuedPayload(
                run_id="run-1", agent_id="a1", actor=_make_actor()
            )  # type: ignore[call-arg]


class TestNextStepAutoCompletedPayload:
    """Tests for NextStepAutoCompletedPayload."""

    def test_valid(self) -> None:
        p = NextStepAutoCompletedPayload(
            run_id="run-1", step_id="s1", agent_id="a1",
            result="success", actor=_make_actor()
        )
        assert p.result == "success"

    def test_missing_result(self) -> None:
        with pytest.raises(PydanticValidationError):
            NextStepAutoCompletedPayload(
                run_id="run-1", step_id="s1", agent_id="a1",
                actor=_make_actor()
            )  # type: ignore[call-arg]


class TestDecisionInputRequestedPayload:
    """Tests for DecisionInputRequestedPayload."""

    def test_valid(self) -> None:
        p = DecisionInputRequestedPayload(
            run_id="run-1", decision_id="d1", step_id="s1",
            question="Which DB?", options=("pg", "mysql"),
            actor=_make_actor()
        )
        assert p.question == "Which DB?"
        assert p.options == ("pg", "mysql")

    def test_missing_question(self) -> None:
        with pytest.raises(PydanticValidationError):
            DecisionInputRequestedPayload(
                run_id="run-1", decision_id="d1", step_id="s1",
                actor=_make_actor()
            )  # type: ignore[call-arg]

    def test_optional_input_key(self) -> None:
        p = DecisionInputRequestedPayload(
            run_id="run-1", decision_id="d1", step_id="s1",
            question="Q?", actor=_make_actor()
        )
        assert p.input_key is None

    def test_with_input_key(self) -> None:
        p = DecisionInputRequestedPayload(
            run_id="run-1", decision_id="input:pw", step_id="s1",
            question="Q?", input_key="pw", actor=_make_actor()
        )
        assert p.input_key == "pw"


class TestDecisionInputAnsweredPayload:
    """Tests for DecisionInputAnsweredPayload."""

    def test_valid(self) -> None:
        p = DecisionInputAnsweredPayload(
            run_id="run-1", decision_id="d1", answer="pg",
            actor=_make_actor(actor_type="human", actor_id="user-1")
        )
        assert p.answer == "pg"

    def test_missing_answer(self) -> None:
        with pytest.raises(PydanticValidationError):
            DecisionInputAnsweredPayload(
                run_id="run-1", decision_id="d1",
                actor=_make_actor()
            )  # type: ignore[call-arg]


class TestMissionRunCompletedPayload:
    """Tests for MissionRunCompletedPayload."""

    def test_valid(self) -> None:
        p = MissionRunCompletedPayload(
            run_id="run-1", mission_key="feat-login", actor=_make_actor()
        )
        assert p.run_id == "run-1"
        assert p.mission_key == "feat-login"

    def test_missing_mission_key(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionRunCompletedPayload(
                run_id="run-1", actor=_make_actor()
            )  # type: ignore[call-arg]


# ── Anomaly Model ────────────────────────────────────────────────────────────


class TestMissionNextAnomaly:
    """Tests for MissionNextAnomaly model."""

    def test_valid(self) -> None:
        a = MissionNextAnomaly(
            event_id="evt1", event_type="MissionRunStarted",
            reason="Duplicate start"
        )
        assert a.reason == "Duplicate start"

    def test_frozen(self) -> None:
        a = MissionNextAnomaly(
            event_id="evt1", event_type="X", reason="Y"
        )
        with pytest.raises(Exception):
            a.reason = "Z"  # type: ignore[misc]


# ── ReducedMissionRunState Defaults ──────────────────────────────────────────


class TestReducedMissionRunStateDefaults:
    """Tests for ReducedMissionRunState default values."""

    def test_empty_state(self) -> None:
        state = ReducedMissionRunState()
        assert state.run_id is None
        assert state.mission_key is None
        assert state.run_status is None
        assert state.current_step_id is None
        assert state.completed_steps == ()
        assert state.pending_decisions == {}
        assert state.answered_decisions == {}
        assert state.anomalies == ()
        assert state.event_count == 0
        assert state.last_processed_event_id is None

    def test_frozen(self) -> None:
        state = ReducedMissionRunState()
        with pytest.raises(Exception):
            state.run_id = "new"  # type: ignore[misc]
