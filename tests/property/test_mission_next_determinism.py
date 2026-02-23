"""Property tests proving mission-next reducer determinism."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from hypothesis import given, settings
from hypothesis import strategies as st
from ulid import ULID

from spec_kitty_events.mission_next import (
    DECISION_INPUT_ANSWERED,
    DECISION_INPUT_REQUESTED,
    MISSION_RUN_COMPLETED,
    MISSION_RUN_STARTED,
    NEXT_STEP_AUTO_COMPLETED,
    NEXT_STEP_ISSUED,
    DecisionInputAnsweredPayload,
    DecisionInputRequestedPayload,
    MissionRunCompletedPayload,
    MissionRunStartedPayload,
    MissionRunStatus,
    NextStepAutoCompletedPayload,
    NextStepIssuedPayload,
    ReducedMissionRunState,
    RuntimeActorIdentity,
    reduce_mission_next_events,
)
from spec_kitty_events.models import Event

_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")


def _actor() -> RuntimeActorIdentity:
    return RuntimeActorIdentity(
        actor_id="agent-claude", actor_type="llm",
        display_name="Claude", provider="anthropic", model="claude-opus-4-6",
    )


def _build_test_run_sequence() -> List[Event]:
    """Build a deterministic run event sequence for testing."""
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    corr_id = str(ULID())
    actor = _actor()
    events: List[Event] = []

    events.append(Event(
        event_id=str(ULID()), event_type=MISSION_RUN_STARTED,
        aggregate_id="run/run-1",
        payload=MissionRunStartedPayload(
            run_id="run-1", mission_key="feat-login", actor=actor,
        ).model_dump(),
        timestamp=base_time + timedelta(seconds=1),
        node_id="node-1", lamport_clock=1,
        project_uuid=_PROJECT_UUID, correlation_id=corr_id,
    ))

    events.append(Event(
        event_id=str(ULID()), event_type=NEXT_STEP_ISSUED,
        aggregate_id="run/run-1",
        payload=NextStepIssuedPayload(
            run_id="run-1", step_id="S1", agent_id="a1", actor=actor,
        ).model_dump(),
        timestamp=base_time + timedelta(seconds=2),
        node_id="node-1", lamport_clock=2,
        project_uuid=_PROJECT_UUID, correlation_id=corr_id,
    ))

    events.append(Event(
        event_id=str(ULID()), event_type=NEXT_STEP_AUTO_COMPLETED,
        aggregate_id="run/run-1",
        payload=NextStepAutoCompletedPayload(
            run_id="run-1", step_id="S1", agent_id="a1",
            result="success", actor=actor,
        ).model_dump(),
        timestamp=base_time + timedelta(seconds=3),
        node_id="node-1", lamport_clock=3,
        project_uuid=_PROJECT_UUID, correlation_id=corr_id,
    ))

    events.append(Event(
        event_id=str(ULID()), event_type=NEXT_STEP_ISSUED,
        aggregate_id="run/run-1",
        payload=NextStepIssuedPayload(
            run_id="run-1", step_id="S2", agent_id="a1", actor=actor,
        ).model_dump(),
        timestamp=base_time + timedelta(seconds=4),
        node_id="node-1", lamport_clock=4,
        project_uuid=_PROJECT_UUID, correlation_id=corr_id,
    ))

    events.append(Event(
        event_id=str(ULID()), event_type=DECISION_INPUT_REQUESTED,
        aggregate_id="run/run-1",
        payload=DecisionInputRequestedPayload(
            run_id="run-1", decision_id="d1", step_id="S2",
            question="Which DB?", options=("pg",), actor=actor,
        ).model_dump(),
        timestamp=base_time + timedelta(seconds=5),
        node_id="node-1", lamport_clock=5,
        project_uuid=_PROJECT_UUID, correlation_id=corr_id,
    ))

    human = RuntimeActorIdentity(actor_id="user-1", actor_type="human")
    events.append(Event(
        event_id=str(ULID()), event_type=DECISION_INPUT_ANSWERED,
        aggregate_id="run/run-1",
        payload=DecisionInputAnsweredPayload(
            run_id="run-1", decision_id="d1", answer="pg", actor=human,
        ).model_dump(),
        timestamp=base_time + timedelta(seconds=6),
        node_id="node-1", lamport_clock=6,
        project_uuid=_PROJECT_UUID, correlation_id=corr_id,
    ))

    events.append(Event(
        event_id=str(ULID()), event_type=NEXT_STEP_AUTO_COMPLETED,
        aggregate_id="run/run-1",
        payload=NextStepAutoCompletedPayload(
            run_id="run-1", step_id="S2", agent_id="a1",
            result="success", actor=actor,
        ).model_dump(),
        timestamp=base_time + timedelta(seconds=7),
        node_id="node-1", lamport_clock=7,
        project_uuid=_PROJECT_UUID, correlation_id=corr_id,
    ))

    events.append(Event(
        event_id=str(ULID()), event_type=MISSION_RUN_COMPLETED,
        aggregate_id="run/run-1",
        payload=MissionRunCompletedPayload(
            run_id="run-1", mission_key="feat-login", actor=actor,
        ).model_dump(),
        timestamp=base_time + timedelta(seconds=8),
        node_id="node-1", lamport_clock=8,
        project_uuid=_PROJECT_UUID, correlation_id=corr_id,
    ))

    return events


class TestMissionNextDeterminism:
    """Determinism property tests for mission-next reducer."""

    @given(st.randoms())
    @settings(max_examples=200)
    def test_deterministic_across_physical_orderings(
        self, rng: random.Random,
    ) -> None:
        """Reducer output is identical regardless of physical event ordering."""
        events = _build_test_run_sequence()

        canonical = reduce_mission_next_events(events)

        shuffled = list(events)
        rng.shuffle(shuffled)
        result = reduce_mission_next_events(shuffled)

        assert result.run_id == canonical.run_id
        assert result.mission_key == canonical.mission_key
        assert result.run_status == canonical.run_status
        assert result.completed_steps == canonical.completed_steps
        assert len(result.anomalies) == len(canonical.anomalies)
        assert result.event_count == canonical.event_count

    @given(st.randoms())
    @settings(max_examples=100)
    def test_idempotent_dedup(self, rng: random.Random) -> None:
        """Duplicated events produce identical state via dedup."""
        events = _build_test_run_sequence()

        canonical = reduce_mission_next_events(events)

        # Double each event
        doubled = events + events
        rng.shuffle(doubled)
        result = reduce_mission_next_events(doubled)

        assert result.run_id == canonical.run_id
        assert result.run_status == canonical.run_status
        assert result.completed_steps == canonical.completed_steps
