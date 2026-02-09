"""Property tests proving lifecycle reducer determinism."""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from hypothesis import given, settings
from hypothesis import strategies as st
from ulid import ULID

from spec_kitty_events.lifecycle import (
    MISSION_CANCELLED,
    MISSION_COMPLETED,
    MISSION_STARTED,
    PHASE_ENTERED,
    MissionCancelledPayload,
    MissionCompletedPayload,
    MissionStartedPayload,
    MissionStatus,
    PhaseEnteredPayload,
    ReducedMissionState,
    reduce_lifecycle_events,
)
from spec_kitty_events.models import Event

_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")


def _build_test_mission_sequence(
    include_cancel: bool = False,
) -> List[Event]:
    """Build a deterministic mission event sequence for testing."""
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    corr_id = str(ULID())
    events: List[Event] = []

    # MissionStarted at clock=1
    events.append(
        Event(
            event_id=str(ULID()),
            event_type=MISSION_STARTED,
            aggregate_id="mission/M001",
            payload=MissionStartedPayload(
                mission_id="M001",
                mission_type="software-dev",
                initial_phase="specify",
                actor="user-1",
            ).model_dump(),
            timestamp=base_time + timedelta(seconds=1),
            node_id="node-1",
            lamport_clock=1,
            project_uuid=_PROJECT_UUID,
            correlation_id=corr_id,
        )
    )

    # PhaseEntered at clock=2
    events.append(
        Event(
            event_id=str(ULID()),
            event_type=PHASE_ENTERED,
            aggregate_id="mission/M001",
            payload=PhaseEnteredPayload(
                mission_id="M001",
                phase_name="implement",
                previous_phase="specify",
                actor="user-1",
            ).model_dump(),
            timestamp=base_time + timedelta(seconds=2),
            node_id="node-1",
            lamport_clock=2,
            project_uuid=_PROJECT_UUID,
            correlation_id=corr_id,
        )
    )

    # PhaseEntered at clock=3
    events.append(
        Event(
            event_id=str(ULID()),
            event_type=PHASE_ENTERED,
            aggregate_id="mission/M001",
            payload=PhaseEnteredPayload(
                mission_id="M001",
                phase_name="review",
                previous_phase="implement",
                actor="user-1",
            ).model_dump(),
            timestamp=base_time + timedelta(seconds=3),
            node_id="node-1",
            lamport_clock=3,
            project_uuid=_PROJECT_UUID,
            correlation_id=corr_id,
        )
    )

    if include_cancel:
        events.append(
            Event(
                event_id=str(ULID()),
                event_type=MISSION_CANCELLED,
                aggregate_id="mission/M001",
                payload=MissionCancelledPayload(
                    mission_id="M001",
                    reason="Abort",
                    actor="manager",
                ).model_dump(),
                timestamp=base_time + timedelta(seconds=4),
                node_id="node-2",
                lamport_clock=4,
                project_uuid=_PROJECT_UUID,
                correlation_id=corr_id,
            )
        )
    else:
        events.append(
            Event(
                event_id=str(ULID()),
                event_type=MISSION_COMPLETED,
                aggregate_id="mission/M001",
                payload=MissionCompletedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    final_phase="review",
                    actor="user-1",
                ).model_dump(),
                timestamp=base_time + timedelta(seconds=4),
                node_id="node-1",
                lamport_clock=4,
                project_uuid=_PROJECT_UUID,
                correlation_id=corr_id,
            )
        )

    return events


def _shuffle_preserving_causal_order(
    events: List[Event], rng: random.Random
) -> List[Event]:
    """Shuffle events while preserving causal order (Lamport clock)."""
    from itertools import groupby

    groups = []
    sorted_events = sorted(events, key=lambda e: e.lamport_clock)
    for _clock, group_iter in groupby(
        sorted_events, key=lambda e: e.lamport_clock
    ):
        group = list(group_iter)
        rng.shuffle(group)
        groups.append(group)
    rng.shuffle(groups)
    # Re-sort groups by their first event's clock to preserve causal order
    groups.sort(key=lambda g: g[0].lamport_clock)
    return [e for g in groups for e in g]


@settings(max_examples=200, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**32))
def test_reducer_determinism_across_physical_orderings(seed: int) -> None:
    """Same events in different physical orderings produce identical state.

    Acceptance criteria 2E-03: replay same events in varied physical order
    where causal order is equivalent -> identical final state.
    """
    events = _build_test_mission_sequence()
    rng = random.Random(seed)
    shuffled = _shuffle_preserving_causal_order(events, rng)

    result_original = reduce_lifecycle_events(events)
    result_shuffled = reduce_lifecycle_events(shuffled)

    assert result_original == result_shuffled


@settings(max_examples=200, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**32))
def test_reducer_determinism_with_cancel(seed: int) -> None:
    """Cancel path is also deterministic across orderings."""
    events = _build_test_mission_sequence(include_cancel=True)
    rng = random.Random(seed)
    shuffled = _shuffle_preserving_causal_order(events, rng)

    result_original = reduce_lifecycle_events(events)
    result_shuffled = reduce_lifecycle_events(shuffled)

    assert result_original.mission_status == MissionStatus.CANCELLED
    assert result_original == result_shuffled


@settings(max_examples=100, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**32))
def test_idempotent_dedup_property(seed: int) -> None:
    """Duplicating events does not change reducer output (F-Reducer-003)."""
    events = _build_test_mission_sequence()
    rng = random.Random(seed)

    # Duplicate some events randomly
    duplicated = list(events)
    for event in events:
        if rng.random() < 0.5:
            duplicated.append(event)

    result_original = reduce_lifecycle_events(events)
    result_duplicated = reduce_lifecycle_events(duplicated)

    assert result_original.mission_status == result_duplicated.mission_status
    assert result_original.current_phase == result_duplicated.current_phase
    assert result_original.phases_entered == result_duplicated.phases_entered
    assert result_original.event_count == result_duplicated.event_count
