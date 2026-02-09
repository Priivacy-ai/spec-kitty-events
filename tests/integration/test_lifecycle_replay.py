"""Integration tests for lifecycle projection replay correctness.

Acceptance criteria 2E-07 and 2E-08: verify that lifecycle reducer
produces identical output whether events arrive incrementally or
are replayed from scratch.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from ulid import ULID

from spec_kitty_events.lifecycle import (
    MISSION_CANCELLED,
    MISSION_COMPLETED,
    MISSION_STARTED,
    PHASE_ENTERED,
    REVIEW_ROLLBACK,
    MissionCancelledPayload,
    MissionCompletedPayload,
    MissionStartedPayload,
    MissionStatus,
    PhaseEnteredPayload,
    ReducedMissionState,
    ReviewRollbackPayload,
    reduce_lifecycle_events,
)
from spec_kitty_events.models import Event
from spec_kitty_events.status import (
    ExecutionMode,
    Lane,
    StatusTransitionPayload,
    WP_STATUS_CHANGED,
    reduce_status_events,
)

_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_event(
    event_type: str,
    payload: dict,  # type: ignore[type-arg]
    lamport_clock: int,
    corr_id: str,
    node_id: str = "node-1",
) -> Event:
    """Build an Event with defaults for integration tests."""
    return Event(
        event_id=str(ULID()),
        event_type=event_type,
        aggregate_id="mission/M001",
        payload=payload,
        timestamp=_BASE_TIME + timedelta(seconds=lamport_clock),
        node_id=node_id,
        lamport_clock=lamport_clock,
        project_uuid=_PROJECT_UUID,
        correlation_id=corr_id,
    )


def _build_wp_status_payload(
    wp_id: str,
    from_lane: str | None,
    to_lane: str,
) -> dict:  # type: ignore[type-arg]
    """Build a WPStatusChanged payload dict."""
    return StatusTransitionPayload(
        feature_slug="004-test",
        wp_id=wp_id,
        from_lane=Lane(from_lane) if from_lane else None,
        to_lane=Lane(to_lane),
        actor="user-1",
        force=False,
        execution_mode=ExecutionMode.WORKTREE,
    ).model_dump()


def _build_full_event_sequence() -> List[Event]:
    """Build a realistic full mission lifecycle with all event types."""
    corr_id = str(ULID())
    events: List[Event] = []

    # clock=1: MissionStarted
    events.append(
        _make_event(
            MISSION_STARTED,
            MissionStartedPayload(
                mission_id="M001",
                mission_type="software-dev",
                initial_phase="specify",
                actor="user-1",
            ).model_dump(),
            lamport_clock=1,
            corr_id=corr_id,
        )
    )

    # clock=2: WP01 planned
    events.append(
        _make_event(
            WP_STATUS_CHANGED,
            _build_wp_status_payload("WP01", None, "planned"),
            lamport_clock=2,
            corr_id=corr_id,
        )
    )

    # clock=3: WP01 claimed
    events.append(
        _make_event(
            WP_STATUS_CHANGED,
            _build_wp_status_payload("WP01", "planned", "claimed"),
            lamport_clock=3,
            corr_id=corr_id,
        )
    )

    # clock=4: PhaseEntered implement
    events.append(
        _make_event(
            PHASE_ENTERED,
            PhaseEnteredPayload(
                mission_id="M001",
                phase_name="implement",
                previous_phase="specify",
                actor="user-1",
            ).model_dump(),
            lamport_clock=4,
            corr_id=corr_id,
        )
    )

    # clock=5: WP01 in_progress
    events.append(
        _make_event(
            WP_STATUS_CHANGED,
            _build_wp_status_payload("WP01", "claimed", "in_progress"),
            lamport_clock=5,
            corr_id=corr_id,
        )
    )

    # clock=6: WP01 for_review
    events.append(
        _make_event(
            WP_STATUS_CHANGED,
            _build_wp_status_payload("WP01", "in_progress", "for_review"),
            lamport_clock=6,
            corr_id=corr_id,
        )
    )

    # clock=7: ReviewRollback to specify
    events.append(
        _make_event(
            REVIEW_ROLLBACK,
            ReviewRollbackPayload(
                mission_id="M001",
                review_ref="PR-42",
                target_phase="specify",
                affected_wp_ids=["WP01"],
                actor="reviewer-1",
            ).model_dump(),
            lamport_clock=7,
            corr_id=corr_id,
        )
    )

    # clock=8: PhaseEntered implement (again after rollback)
    events.append(
        _make_event(
            PHASE_ENTERED,
            PhaseEnteredPayload(
                mission_id="M001",
                phase_name="implement",
                previous_phase="specify",
                actor="user-1",
            ).model_dump(),
            lamport_clock=8,
            corr_id=corr_id,
        )
    )

    # clock=9: PhaseEntered review
    events.append(
        _make_event(
            PHASE_ENTERED,
            PhaseEnteredPayload(
                mission_id="M001",
                phase_name="review",
                previous_phase="implement",
                actor="user-1",
            ).model_dump(),
            lamport_clock=9,
            corr_id=corr_id,
        )
    )

    # clock=10: MissionCompleted
    events.append(
        _make_event(
            MISSION_COMPLETED,
            MissionCompletedPayload(
                mission_id="M001",
                mission_type="software-dev",
                final_phase="review",
                actor="user-1",
            ).model_dump(),
            lamport_clock=10,
            corr_id=corr_id,
        )
    )

    return events


class TestWPStatusDelegation:
    """2E-07: WP status projection from lifecycle reducer matches
    reduce_status_events() for the same WP events."""

    def test_wp_states_match_delegated_reduction(self) -> None:
        """Lifecycle reducer WP states match direct status reduction."""
        events = _build_full_event_sequence()

        # Reduce via lifecycle reducer (handles both mission + WP events)
        lifecycle_state = reduce_lifecycle_events(events)

        # Reduce WP events directly via status reducer
        wp_events = [e for e in events if e.event_type == WP_STATUS_CHANGED]
        status_state = reduce_status_events(wp_events)

        # WP states must match
        assert lifecycle_state.wp_states == status_state.wp_states

    def test_wp_anomalies_propagated(self) -> None:
        """WP-level anomalies appear in lifecycle reducer output."""
        corr_id = str(ULID())
        events = [
            _make_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M001",
                    mission_type="dev",
                    initial_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=1,
                corr_id=corr_id,
            ),
            # WP event with from_lane mismatch (anomaly)
            _make_event(
                WP_STATUS_CHANGED,
                _build_wp_status_payload("WP01", "claimed", "in_progress"),
                lamport_clock=2,
                corr_id=corr_id,
            ),
        ]
        state = reduce_lifecycle_events(events)
        # Should have anomaly from WP (from_lane mismatch: expected None, got claimed)
        assert len(state.anomalies) > 0
        wp_anomalies = [a for a in state.anomalies if "WP" in a.reason]
        assert len(wp_anomalies) > 0


class TestReplayDeterminism:
    """2E-07/2E-08: Rebuilding projection from scratch produces
    identical output."""

    def test_replay_from_scratch_identical(self) -> None:
        """Two independent replays of same events produce identical state."""
        events = _build_full_event_sequence()

        replay_1 = reduce_lifecycle_events(events)
        replay_2 = reduce_lifecycle_events(list(events))

        assert replay_1 == replay_2

    def test_incremental_accumulation_matches_replay(self) -> None:
        """Feeding events one-by-one into separate reducer calls
        for the full set matches a single replay."""
        events = _build_full_event_sequence()

        # Full replay
        full_state = reduce_lifecycle_events(events)

        # Incremental: reduce with all events (the reducer is stateless,
        # so "incremental" means replaying the growing prefix)
        for i in range(1, len(events) + 1):
            partial_state = reduce_lifecycle_events(events[:i])

        # The final partial state (all events) should match full replay
        assert partial_state == full_state  # type: ignore[possibly-undefined]


class TestFullLifecycleAllEventTypes:
    """Integration test: mission with all event types."""

    def test_full_lifecycle_correct_final_state(self) -> None:
        """Full lifecycle produces correct mission state."""
        events = _build_full_event_sequence()
        state = reduce_lifecycle_events(events)

        assert state.mission_id == "M001"
        assert state.mission_status == MissionStatus.COMPLETED
        assert state.mission_type == "software-dev"
        assert state.current_phase == "review"
        # Phases: specify, implement, specify (rollback), implement, review
        assert state.phases_entered == (
            "specify",
            "implement",
            "specify",
            "implement",
            "review",
        )
        assert state.event_count == 10
        assert len(state.anomalies) == 0

    def test_full_lifecycle_with_cancellation(self) -> None:
        """Mission cancelled mid-flight produces correct state."""
        corr_id = str(ULID())
        events = [
            _make_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M002",
                    mission_type="research",
                    initial_phase="gather",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=1,
                corr_id=corr_id,
            ),
            _make_event(
                PHASE_ENTERED,
                PhaseEnteredPayload(
                    mission_id="M002",
                    phase_name="analyze",
                    previous_phase="gather",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=2,
                corr_id=corr_id,
            ),
            _make_event(
                MISSION_CANCELLED,
                MissionCancelledPayload(
                    mission_id="M002",
                    reason="Budget cut",
                    actor="manager",
                ).model_dump(),
                lamport_clock=3,
                corr_id=corr_id,
            ),
        ]
        state = reduce_lifecycle_events(events)
        assert state.mission_status == MissionStatus.CANCELLED
        assert state.current_phase == "analyze"
        assert state.phases_entered == ("gather", "analyze")
        assert len(state.anomalies) == 0

    def test_events_after_terminal_are_anomalies(self) -> None:
        """Events arriving after terminal state are flagged as anomalies."""
        corr_id = str(ULID())
        events = [
            _make_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M003",
                    mission_type="dev",
                    initial_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=1,
                corr_id=corr_id,
            ),
            _make_event(
                MISSION_COMPLETED,
                MissionCompletedPayload(
                    mission_id="M003",
                    mission_type="dev",
                    final_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=2,
                corr_id=corr_id,
            ),
            # Late PhaseEntered after completion
            _make_event(
                PHASE_ENTERED,
                PhaseEnteredPayload(
                    mission_id="M003",
                    phase_name="implement",
                    previous_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=3,
                corr_id=corr_id,
            ),
        ]
        state = reduce_lifecycle_events(events)
        assert state.mission_status == MissionStatus.COMPLETED
        assert len(state.anomalies) == 1
        assert "terminal" in state.anomalies[0].reason.lower()
