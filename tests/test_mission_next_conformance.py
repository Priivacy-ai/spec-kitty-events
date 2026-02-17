"""Conformance tests for mission-next runtime event contracts."""

from __future__ import annotations

import pytest

from spec_kitty_events.conformance.loader import load_fixtures, load_replay_stream
from spec_kitty_events.conformance.validators import validate_event
from spec_kitty_events.mission_next import (
    MissionRunStatus,
    reduce_mission_next_events,
)
from spec_kitty_events.models import Event


class TestMissionNextConformanceValid:
    """Tests that valid mission-next fixtures pass validation."""

    def test_mission_run_started_valid(self) -> None:
        fixtures = load_fixtures("mission_next")
        case = next(f for f in fixtures if f.id == "mission-next-run-started-valid")
        result = validate_event(case.payload, case.event_type, strict=True)
        assert result.valid, f"Violations: {result.model_violations}"

    def test_next_step_issued_valid(self) -> None:
        fixtures = load_fixtures("mission_next")
        case = next(f for f in fixtures if f.id == "mission-next-step-issued-valid")
        result = validate_event(case.payload, case.event_type, strict=True)
        assert result.valid, f"Violations: {result.model_violations}"

    def test_next_step_auto_completed_valid(self) -> None:
        fixtures = load_fixtures("mission_next")
        case = next(f for f in fixtures if f.id == "mission-next-step-auto-completed-valid")
        result = validate_event(case.payload, case.event_type, strict=True)
        assert result.valid, f"Violations: {result.model_violations}"

    def test_decision_input_requested_valid(self) -> None:
        fixtures = load_fixtures("mission_next")
        case = next(f for f in fixtures if f.id == "mission-next-decision-requested-valid")
        result = validate_event(case.payload, case.event_type, strict=True)
        assert result.valid, f"Violations: {result.model_violations}"

    def test_decision_input_answered_valid(self) -> None:
        fixtures = load_fixtures("mission_next")
        case = next(f for f in fixtures if f.id == "mission-next-decision-answered-valid")
        result = validate_event(case.payload, case.event_type, strict=True)
        assert result.valid, f"Violations: {result.model_violations}"

    def test_mission_run_completed_valid(self) -> None:
        fixtures = load_fixtures("mission_next")
        case = next(f for f in fixtures if f.id == "mission-next-run-completed-valid")
        result = validate_event(case.payload, case.event_type, strict=True)
        assert result.valid, f"Violations: {result.model_violations}"


class TestMissionNextConformanceInvalid:
    """Tests that invalid mission-next fixtures fail validation."""

    def test_missing_run_id(self) -> None:
        fixtures = load_fixtures("mission_next")
        case = next(f for f in fixtures if f.id == "mission-next-run-started-missing-run-id")
        result = validate_event(case.payload, case.event_type, strict=True)
        assert not result.valid

    def test_missing_step_id(self) -> None:
        fixtures = load_fixtures("mission_next")
        case = next(f for f in fixtures if f.id == "mission-next-step-issued-missing-step-id")
        result = validate_event(case.payload, case.event_type, strict=True)
        assert not result.valid

    def test_missing_question(self) -> None:
        fixtures = load_fixtures("mission_next")
        case = next(f for f in fixtures if f.id == "mission-next-decision-requested-missing-question")
        result = validate_event(case.payload, case.event_type, strict=True)
        assert not result.valid


class TestMissionCompletedAliasConformance:
    """Tests that MissionCompleted event type (lifecycle) still validates."""

    def test_lifecycle_mission_completed_still_works(self) -> None:
        """Ensure the existing lifecycle MissionCompleted mapping is preserved."""
        payload = {
            "mission_id": "M001",
            "mission_type": "software-dev",
            "final_phase": "deliver",
            "actor": "user-1",
        }
        result = validate_event(payload, "MissionCompleted")
        assert result.valid, f"Violations: {result.model_violations}"

    def test_mission_run_completed_validates(self) -> None:
        """MissionRunCompleted event type validates against run payload."""
        payload = {
            "run_id": "run-1",
            "mission_key": "feat-login",
            "actor": {
                "actor_id": "agent-claude",
                "actor_type": "llm",
            },
        }
        result = validate_event(payload, "MissionRunCompleted")
        assert result.valid, f"Violations: {result.model_violations}"


class TestMissionNextReplayFixture:
    """Tests for the canonical replay fixture stream."""

    def test_replay_full_lifecycle(self) -> None:
        """Load stream, reduce through mission-next reducer, assert expected state."""
        envelopes = load_replay_stream("mission-next-replay-full-lifecycle")
        events = [Event(**env) for env in envelopes]
        state = reduce_mission_next_events(events)

        assert state.run_id == "replay-run-001"
        assert state.mission_key == "replay-mission"
        assert state.run_status == MissionRunStatus.COMPLETED
        assert state.completed_steps == ("step-setup-env", "step-configure-db")
        assert state.anomalies == ()
        assert state.event_count == 8

    def test_replay_events_individually_valid(self) -> None:
        """Each envelope deserializes as valid Event with correct metadata."""
        envelopes = load_replay_stream("mission-next-replay-full-lifecycle")
        correlation_id: str | None = None

        for i, env in enumerate(envelopes):
            event = Event(**env)
            assert event.lamport_clock == i + 1
            if correlation_id is None:
                correlation_id = event.correlation_id
            else:
                assert event.correlation_id == correlation_id

    def test_replay_causal_chain(self) -> None:
        """First event has no cause; each subsequent event's causation_id is the previous event_id."""
        envelopes = load_replay_stream("mission-next-replay-full-lifecycle")
        events = [Event(**env) for env in envelopes]

        assert events[0].causation_id is None
        for i in range(1, len(events)):
            assert events[i].causation_id == events[i - 1].event_id
