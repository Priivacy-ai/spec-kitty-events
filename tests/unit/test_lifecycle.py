"""Unit tests for mission lifecycle event contracts."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError as PydanticValidationError
from ulid import ULID

from spec_kitty_events.lifecycle import (
    MISSION_CANCELLED,
    MISSION_COMPLETED,
    MISSION_EVENT_TYPES,
    MISSION_STARTED,
    PHASE_ENTERED,
    REVIEW_ROLLBACK,
    SCHEMA_VERSION,
    TERMINAL_MISSION_STATUSES,
    LifecycleAnomaly,
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

_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")


def _make_mission_event(
    event_type: str,
    payload: dict,  # type: ignore[type-arg]
    lamport_clock: int,
    event_id: str | None = None,
    node_id: str = "node-1",
) -> Event:
    """Helper to build a mission event."""
    return Event(
        event_id=event_id or str(ULID()),
        event_type=event_type,
        aggregate_id="mission/M001",
        payload=payload,
        timestamp=datetime.now(timezone.utc),
        node_id=node_id,
        lamport_clock=lamport_clock,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )


# ── MissionStatus Enum ───────────────────────────────────────────────────────


class TestMissionStatus:
    """Tests for MissionStatus enum."""

    def test_enum_values(self) -> None:
        assert MissionStatus.ACTIVE == "active"
        assert MissionStatus.COMPLETED == "completed"
        assert MissionStatus.CANCELLED == "cancelled"

    def test_terminal_statuses(self) -> None:
        assert MissionStatus.COMPLETED in TERMINAL_MISSION_STATUSES
        assert MissionStatus.CANCELLED in TERMINAL_MISSION_STATUSES

    def test_active_not_terminal(self) -> None:
        assert MissionStatus.ACTIVE not in TERMINAL_MISSION_STATUSES

    def test_string_comparison(self) -> None:
        assert MissionStatus.ACTIVE == "active"
        assert MissionStatus.COMPLETED == "completed"
        assert MissionStatus.CANCELLED == "cancelled"

    def test_terminal_statuses_frozen(self) -> None:
        assert isinstance(TERMINAL_MISSION_STATUSES, frozenset)


# ── Constants ─────────────────────────────────────────────────────────────────


class TestConstants:
    """Tests for event type constants."""

    def test_schema_version(self) -> None:
        assert SCHEMA_VERSION == "2.0.0"

    def test_mission_started(self) -> None:
        assert MISSION_STARTED == "MissionStarted"

    def test_mission_completed(self) -> None:
        assert MISSION_COMPLETED == "MissionCompleted"

    def test_mission_cancelled(self) -> None:
        assert MISSION_CANCELLED == "MissionCancelled"

    def test_phase_entered(self) -> None:
        assert PHASE_ENTERED == "PhaseEntered"

    def test_review_rollback(self) -> None:
        assert REVIEW_ROLLBACK == "ReviewRollback"

    def test_mission_event_types_contains_all(self) -> None:
        assert MISSION_STARTED in MISSION_EVENT_TYPES
        assert MISSION_COMPLETED in MISSION_EVENT_TYPES
        assert MISSION_CANCELLED in MISSION_EVENT_TYPES
        assert PHASE_ENTERED in MISSION_EVENT_TYPES
        assert REVIEW_ROLLBACK in MISSION_EVENT_TYPES
        assert len(MISSION_EVENT_TYPES) == 5

    def test_mission_event_types_frozen(self) -> None:
        assert isinstance(MISSION_EVENT_TYPES, frozenset)

    def test_wp_event_not_in_mission_types(self) -> None:
        assert "WPStatusChanged" not in MISSION_EVENT_TYPES


# ── MissionStartedPayload ────────────────────────────────────────────────────


class TestMissionStartedPayload:
    """Tests for MissionStartedPayload model."""

    def test_valid_construction(self) -> None:
        p = MissionStartedPayload(
            mission_id="M001",
            mission_type="software-dev",
            initial_phase="specify",
            actor="user-1",
        )
        assert p.mission_id == "M001"
        assert p.mission_type == "software-dev"
        assert p.initial_phase == "specify"
        assert p.actor == "user-1"

    def test_missing_mission_id(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionStartedPayload(
                mission_type="software-dev",
                initial_phase="specify",
                actor="user-1",
            )  # type: ignore[call-arg]

    def test_missing_mission_type(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionStartedPayload(
                mission_id="M001",
                initial_phase="specify",
                actor="user-1",
            )  # type: ignore[call-arg]

    def test_missing_initial_phase(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionStartedPayload(
                mission_id="M001",
                mission_type="software-dev",
                actor="user-1",
            )  # type: ignore[call-arg]

    def test_missing_actor(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionStartedPayload(
                mission_id="M001",
                mission_type="software-dev",
                initial_phase="specify",
            )  # type: ignore[call-arg]

    def test_empty_mission_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionStartedPayload(
                mission_id="",
                mission_type="software-dev",
                initial_phase="specify",
                actor="user-1",
            )

    def test_empty_actor_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionStartedPayload(
                mission_id="M001",
                mission_type="software-dev",
                initial_phase="specify",
                actor="",
            )

    def test_frozen(self) -> None:
        p = MissionStartedPayload(
            mission_id="M001",
            mission_type="software-dev",
            initial_phase="specify",
            actor="user-1",
        )
        with pytest.raises(Exception):
            setattr(p, "mission_id", "M002")

    def test_round_trip(self) -> None:
        p = MissionStartedPayload(
            mission_id="M001",
            mission_type="software-dev",
            initial_phase="specify",
            actor="user-1",
        )
        dumped = p.model_dump()
        assert isinstance(dumped, dict)
        restored = MissionStartedPayload(**dumped)
        assert restored == p


# ── MissionCompletedPayload ──────────────────────────────────────────────────


class TestMissionCompletedPayload:
    """Tests for MissionCompletedPayload model."""

    def test_valid_construction(self) -> None:
        p = MissionCompletedPayload(
            mission_id="M001",
            mission_type="software-dev",
            final_phase="accept",
            actor="user-1",
        )
        assert p.mission_id == "M001"
        assert p.final_phase == "accept"

    def test_missing_final_phase(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionCompletedPayload(
                mission_id="M001",
                mission_type="software-dev",
                actor="user-1",
            )  # type: ignore[call-arg]

    def test_empty_mission_type_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionCompletedPayload(
                mission_id="M001",
                mission_type="",
                final_phase="accept",
                actor="user-1",
            )

    def test_frozen(self) -> None:
        p = MissionCompletedPayload(
            mission_id="M001",
            mission_type="software-dev",
            final_phase="accept",
            actor="user-1",
        )
        with pytest.raises(Exception):
            setattr(p, "final_phase", "plan")

    def test_round_trip(self) -> None:
        p = MissionCompletedPayload(
            mission_id="M001",
            mission_type="software-dev",
            final_phase="accept",
            actor="user-1",
        )
        restored = MissionCompletedPayload(**p.model_dump())
        assert restored == p


# ── MissionCancelledPayload ──────────────────────────────────────────────────


class TestMissionCancelledPayload:
    """Tests for MissionCancelledPayload model."""

    def test_valid_construction(self) -> None:
        p = MissionCancelledPayload(
            mission_id="M001",
            reason="User requested abort",
            actor="user-1",
        )
        assert p.mission_id == "M001"
        assert p.reason == "User requested abort"
        assert p.cancelled_wp_ids == []

    def test_with_cancelled_wp_ids(self) -> None:
        p = MissionCancelledPayload(
            mission_id="M001",
            reason="Scope change",
            actor="user-1",
            cancelled_wp_ids=["WP01", "WP02"],
        )
        assert p.cancelled_wp_ids == ["WP01", "WP02"]

    def test_empty_cancelled_wp_ids(self) -> None:
        p = MissionCancelledPayload(
            mission_id="M001",
            reason="Timeout",
            actor="user-1",
            cancelled_wp_ids=[],
        )
        assert p.cancelled_wp_ids == []

    def test_missing_reason(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionCancelledPayload(
                mission_id="M001",
                actor="user-1",
            )  # type: ignore[call-arg]

    def test_empty_reason_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionCancelledPayload(
                mission_id="M001",
                reason="",
                actor="user-1",
            )

    def test_frozen(self) -> None:
        p = MissionCancelledPayload(
            mission_id="M001",
            reason="abort",
            actor="user-1",
        )
        with pytest.raises(Exception):
            setattr(p, "reason", "changed")

    def test_round_trip(self) -> None:
        p = MissionCancelledPayload(
            mission_id="M001",
            reason="Scope change",
            actor="user-1",
            cancelled_wp_ids=["WP03"],
        )
        restored = MissionCancelledPayload(**p.model_dump())
        assert restored == p


# ── PhaseEnteredPayload ──────────────────────────────────────────────────────


class TestPhaseEnteredPayload:
    """Tests for PhaseEnteredPayload model."""

    def test_valid_construction(self) -> None:
        p = PhaseEnteredPayload(
            mission_id="M001",
            phase_name="implement",
            previous_phase="plan",
            actor="user-1",
        )
        assert p.phase_name == "implement"
        assert p.previous_phase == "plan"

    def test_previous_phase_none(self) -> None:
        p = PhaseEnteredPayload(
            mission_id="M001",
            phase_name="specify",
            previous_phase=None,
            actor="user-1",
        )
        assert p.previous_phase is None

    def test_previous_phase_omitted(self) -> None:
        p = PhaseEnteredPayload(
            mission_id="M001",
            phase_name="specify",
            actor="user-1",
        )
        assert p.previous_phase is None

    def test_previous_phase_empty_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PhaseEnteredPayload(
                mission_id="M001",
                phase_name="implement",
                previous_phase="",
                actor="user-1",
            )

    def test_empty_phase_name_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PhaseEnteredPayload(
                mission_id="M001",
                phase_name="",
                actor="user-1",
            )

    def test_frozen(self) -> None:
        p = PhaseEnteredPayload(
            mission_id="M001",
            phase_name="plan",
            actor="user-1",
        )
        with pytest.raises(Exception):
            setattr(p, "phase_name", "implement")

    def test_round_trip(self) -> None:
        p = PhaseEnteredPayload(
            mission_id="M001",
            phase_name="implement",
            previous_phase="plan",
            actor="user-1",
        )
        restored = PhaseEnteredPayload(**p.model_dump())
        assert restored == p

    def test_round_trip_with_none_previous(self) -> None:
        p = PhaseEnteredPayload(
            mission_id="M001",
            phase_name="specify",
            actor="user-1",
        )
        restored = PhaseEnteredPayload(**p.model_dump())
        assert restored == p
        assert restored.previous_phase is None


# ── ReviewRollbackPayload ────────────────────────────────────────────────────


class TestReviewRollbackPayload:
    """Tests for ReviewRollbackPayload model."""

    def test_valid_construction(self) -> None:
        p = ReviewRollbackPayload(
            mission_id="M001",
            review_ref="PR-42",
            target_phase="implement",
            actor="reviewer-1",
        )
        assert p.review_ref == "PR-42"
        assert p.target_phase == "implement"
        assert p.affected_wp_ids == []

    def test_with_affected_wp_ids(self) -> None:
        p = ReviewRollbackPayload(
            mission_id="M001",
            review_ref="PR-42",
            target_phase="implement",
            affected_wp_ids=["WP02", "WP03"],
            actor="reviewer-1",
        )
        assert p.affected_wp_ids == ["WP02", "WP03"]

    def test_empty_review_ref_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ReviewRollbackPayload(
                mission_id="M001",
                review_ref="",
                target_phase="implement",
                actor="reviewer-1",
            )

    def test_missing_target_phase(self) -> None:
        with pytest.raises(PydanticValidationError):
            ReviewRollbackPayload(
                mission_id="M001",
                review_ref="PR-42",
                actor="reviewer-1",
            )  # type: ignore[call-arg]

    def test_missing_actor(self) -> None:
        with pytest.raises(PydanticValidationError):
            ReviewRollbackPayload(
                mission_id="M001",
                review_ref="PR-42",
                target_phase="implement",
            )  # type: ignore[call-arg]

    def test_frozen(self) -> None:
        p = ReviewRollbackPayload(
            mission_id="M001",
            review_ref="PR-42",
            target_phase="implement",
            actor="reviewer-1",
        )
        with pytest.raises(Exception):
            setattr(p, "target_phase", "plan")

    def test_round_trip(self) -> None:
        p = ReviewRollbackPayload(
            mission_id="M001",
            review_ref="PR-42",
            target_phase="implement",
            affected_wp_ids=["WP01"],
            actor="reviewer-1",
        )
        restored = ReviewRollbackPayload(**p.model_dump())
        assert restored == p

    def test_model_dump_is_dict(self) -> None:
        p = ReviewRollbackPayload(
            mission_id="M001",
            review_ref="PR-42",
            target_phase="implement",
            actor="reviewer-1",
        )
        dumped = p.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["mission_id"] == "M001"
        assert dumped["review_ref"] == "PR-42"


# ── Reducer Output Models ────────────────────────────────────────────────────


class TestLifecycleAnomaly:
    """Tests for LifecycleAnomaly model."""

    def test_valid_construction(self) -> None:
        a = LifecycleAnomaly(
            event_id="01HV0000000000000000000001",
            event_type="MissionStarted",
            reason="Duplicate MissionStarted",
        )
        assert a.event_id == "01HV0000000000000000000001"
        assert a.reason == "Duplicate MissionStarted"

    def test_frozen(self) -> None:
        a = LifecycleAnomaly(
            event_id="01HV0000000000000000000001",
            event_type="MissionStarted",
            reason="test",
        )
        with pytest.raises(Exception):
            setattr(a, "reason", "changed")


class TestReducedMissionState:
    """Tests for ReducedMissionState model."""

    def test_default_state(self) -> None:
        state = ReducedMissionState()
        assert state.mission_id is None
        assert state.mission_status is None
        assert state.mission_type is None
        assert state.current_phase is None
        assert state.phases_entered == ()
        assert state.wp_states == {}
        assert state.anomalies == ()
        assert state.event_count == 0
        assert state.last_processed_event_id is None

    def test_frozen(self) -> None:
        state = ReducedMissionState()
        with pytest.raises(Exception):
            setattr(state, "mission_id", "M001")


# ── Lifecycle Reducer ────────────────────────────────────────────────────────


class TestReduceLifecycleEvents:
    """Tests for reduce_lifecycle_events()."""

    def test_empty_sequence(self) -> None:
        result = reduce_lifecycle_events([])
        assert result == ReducedMissionState()

    def test_single_mission_started(self) -> None:
        event = _make_mission_event(
            MISSION_STARTED,
            MissionStartedPayload(
                mission_id="M001",
                mission_type="software-dev",
                initial_phase="specify",
                actor="user-1",
            ).model_dump(),
            lamport_clock=1,
        )
        result = reduce_lifecycle_events([event])
        assert result.mission_id == "M001"
        assert result.mission_status == MissionStatus.ACTIVE
        assert result.mission_type == "software-dev"
        assert result.current_phase == "specify"
        assert result.phases_entered == ("specify",)
        assert result.event_count == 1

    def test_full_happy_path(self) -> None:
        events = [
            _make_mission_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    initial_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=1,
            ),
            _make_mission_event(
                PHASE_ENTERED,
                PhaseEnteredPayload(
                    mission_id="M001",
                    phase_name="implement",
                    previous_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=2,
            ),
            _make_mission_event(
                PHASE_ENTERED,
                PhaseEnteredPayload(
                    mission_id="M001",
                    phase_name="review",
                    previous_phase="implement",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=3,
            ),
            _make_mission_event(
                MISSION_COMPLETED,
                MissionCompletedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    final_phase="review",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=4,
            ),
        ]
        result = reduce_lifecycle_events(events)
        assert result.mission_status == MissionStatus.COMPLETED
        assert result.phases_entered == ("specify", "implement", "review")
        assert result.event_count == 4
        assert len(result.anomalies) == 0

    def test_cancellation_path(self) -> None:
        events = [
            _make_mission_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    initial_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=1,
            ),
            _make_mission_event(
                MISSION_CANCELLED,
                MissionCancelledPayload(
                    mission_id="M001",
                    reason="Budget cut",
                    actor="manager-1",
                ).model_dump(),
                lamport_clock=2,
            ),
        ]
        result = reduce_lifecycle_events(events)
        assert result.mission_status == MissionStatus.CANCELLED

    def test_anomaly_event_before_start(self) -> None:
        event = _make_mission_event(
            PHASE_ENTERED,
            PhaseEnteredPayload(
                mission_id="M001",
                phase_name="implement",
                actor="user-1",
            ).model_dump(),
            lamport_clock=1,
        )
        result = reduce_lifecycle_events([event])
        assert len(result.anomalies) == 1
        assert "before MissionStarted" in result.anomalies[0].reason

    def test_anomaly_event_after_terminal(self) -> None:
        events = [
            _make_mission_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    initial_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=1,
            ),
            _make_mission_event(
                MISSION_COMPLETED,
                MissionCompletedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    final_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=2,
            ),
            _make_mission_event(
                PHASE_ENTERED,
                PhaseEnteredPayload(
                    mission_id="M001",
                    phase_name="implement",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=3,
            ),
        ]
        result = reduce_lifecycle_events(events)
        assert result.mission_status == MissionStatus.COMPLETED
        assert len(result.anomalies) == 1
        assert "terminal" in result.anomalies[0].reason.lower()

    def test_f_reducer_001_cancel_beats_reopen(self) -> None:
        """F-Reducer-001: Cancel beats re-open in concurrent group."""
        start = _make_mission_event(
            MISSION_STARTED,
            MissionStartedPayload(
                mission_id="M001",
                mission_type="software-dev",
                initial_phase="specify",
                actor="user-1",
            ).model_dump(),
            lamport_clock=1,
        )
        # Concurrent: same lamport_clock, different nodes
        phase = _make_mission_event(
            PHASE_ENTERED,
            PhaseEnteredPayload(
                mission_id="M001",
                phase_name="implement",
                actor="user-1",
            ).model_dump(),
            lamport_clock=5,
            node_id="alice",
        )
        cancel = _make_mission_event(
            MISSION_CANCELLED,
            MissionCancelledPayload(
                mission_id="M001",
                reason="Abort",
                actor="manager",
            ).model_dump(),
            lamport_clock=5,
            node_id="bob",
        )
        # Order 1: [phase, cancel]
        result1 = reduce_lifecycle_events([start, phase, cancel])
        # Order 2: [cancel, phase]
        result2 = reduce_lifecycle_events([start, cancel, phase])

        assert result1.mission_status == MissionStatus.CANCELLED
        assert result2.mission_status == MissionStatus.CANCELLED
        # Both orderings produce identical state
        assert result1.mission_status == result2.mission_status

    def test_f_reducer_002_rollback_creates_new_event(self) -> None:
        """F-Reducer-002: Rollback updates phase, all events counted."""
        events = [
            _make_mission_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    initial_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=1,
            ),
            _make_mission_event(
                PHASE_ENTERED,
                PhaseEnteredPayload(
                    mission_id="M001",
                    phase_name="implement",
                    previous_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=2,
            ),
            _make_mission_event(
                REVIEW_ROLLBACK,
                ReviewRollbackPayload(
                    mission_id="M001",
                    review_ref="PR-42",
                    target_phase="specify",
                    actor="reviewer-1",
                ).model_dump(),
                lamport_clock=3,
            ),
        ]
        result = reduce_lifecycle_events(events)
        assert result.current_phase == "specify"
        assert result.event_count == 3  # All events counted
        assert "specify" in result.phases_entered
        assert "implement" in result.phases_entered
        # specify appears twice (initial + rollback)
        assert result.phases_entered.count("specify") == 2

    def test_f_reducer_003_idempotent_dedup(self) -> None:
        """F-Reducer-003: Duplicate events produce same result."""
        events = [
            _make_mission_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    initial_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=1,
                event_id="01HV0000000000000000000001",
            ),
            _make_mission_event(
                PHASE_ENTERED,
                PhaseEnteredPayload(
                    mission_id="M001",
                    phase_name="implement",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=2,
                event_id="01HV0000000000000000000002",
            ),
            _make_mission_event(
                MISSION_COMPLETED,
                MissionCompletedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    final_phase="implement",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=3,
                event_id="01HV0000000000000000000003",
            ),
        ]
        # Duplicate every event
        duplicated = events + events
        result_original = reduce_lifecycle_events(events)
        result_duplicated = reduce_lifecycle_events(duplicated)

        assert result_original.mission_status == result_duplicated.mission_status
        assert result_original.current_phase == result_duplicated.current_phase
        assert result_original.phases_entered == result_duplicated.phases_entered
        assert result_original.event_count == result_duplicated.event_count

    def test_mixed_mission_and_wp_events(self) -> None:
        """Mission + WP events produce both mission state and wp_states."""
        from spec_kitty_events.status import Lane, StatusTransitionPayload

        events = [
            _make_mission_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    initial_phase="implement",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=1,
            ),
            Event(
                event_id=str(ULID()),
                event_type="WPStatusChanged",
                aggregate_id="feat/WP01",
                payload=StatusTransitionPayload(
                    feature_slug="feat",
                    wp_id="WP01",
                    from_lane=None,
                    to_lane=Lane.PLANNED,
                    actor="user-1",
                    execution_mode="worktree",
                ).model_dump(),
                timestamp=datetime.now(timezone.utc),
                node_id="node-1",
                lamport_clock=2,
                project_uuid=_PROJECT_UUID,
                correlation_id=str(ULID()),
            ),
        ]
        result = reduce_lifecycle_events(events)
        assert result.mission_status == MissionStatus.ACTIVE
        assert "WP01" in result.wp_states
        assert result.event_count == 2

    def test_duplicate_mission_started_anomaly(self) -> None:
        events = [
            _make_mission_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M001",
                    mission_type="software-dev",
                    initial_phase="specify",
                    actor="user-1",
                ).model_dump(),
                lamport_clock=1,
            ),
            _make_mission_event(
                MISSION_STARTED,
                MissionStartedPayload(
                    mission_id="M002",
                    mission_type="research",
                    initial_phase="question",
                    actor="user-2",
                ).model_dump(),
                lamport_clock=2,
            ),
        ]
        result = reduce_lifecycle_events(events)
        assert result.mission_id == "M001"  # First one wins
        assert len(result.anomalies) == 1
        assert "Duplicate" in result.anomalies[0].reason
