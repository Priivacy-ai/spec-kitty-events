"""Unit tests for mission lifecycle event contracts."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError as PydanticValidationError
from ulid import ULID

from spec_kitty_events.lifecycle import (
    FOLLOW_UP_RECORDED,
    MISSION_CLOSED,
    MISSION_CANCELLED,
    MISSION_COMPLETED,
    MISSION_CREATED,
    MISSION_EVENT_TYPES,
    MISSION_REOPENED,
    MISSION_STARTED,
    PHASE_ENTERED,
    REVIEW_ROLLBACK,
    SCHEMA_VERSION,
    TERMINAL_MISSION_STATUSES,
    FollowUpRecordedPayload,
    LifecycleAnomaly,
    MissionClosedPayload,
    MissionCancelledPayload,
    MissionCompletedPayload,
    MissionCreatedPayload,
    MissionReopenedPayload,
    MissionStartedPayload,
    MissionStatus,
    PhaseEnteredPayload,
    ReducedMissionState,
    ReviewRollbackPayload,
    reduce_lifecycle_events,
)
from spec_kitty_events.models import Event

_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")


def _mission_created_payload(**overrides: object) -> MissionCreatedPayload:
    """Return a valid MissionCreated payload for lifecycle contract tests."""
    payload: dict[str, object] = {
        "mission_id": "01KTESTMISSIONID0000000000",
        "mission_slug": "mission-contract-cutover",
        "mission_number": 14,
        "mission_type": "software-dev",
        "target_branch": "main",
        "wp_count": 3,
        "friendly_name": "Mission Contract Cutover",
        "purpose_tldr": "Keep mission creation readable to product leadership.",
        "purpose_context": "This mission makes new work readable at a product and leadership level so teams can understand practical intent without parsing technical implementation detail.",
    }
    payload.update(overrides)
    return MissionCreatedPayload(**payload)


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
        build_id="build-test",
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
        assert SCHEMA_VERSION == "3.0.0"

    def test_mission_started(self) -> None:
        assert MISSION_STARTED == "MissionStarted"

    def test_mission_created(self) -> None:
        assert MISSION_CREATED == "MissionCreated"

    def test_mission_closed(self) -> None:
        assert MISSION_CLOSED == "MissionClosed"

    def test_mission_completed(self) -> None:
        assert MISSION_COMPLETED == "MissionCompleted"

    def test_mission_cancelled(self) -> None:
        assert MISSION_CANCELLED == "MissionCancelled"

    def test_phase_entered(self) -> None:
        assert PHASE_ENTERED == "PhaseEntered"

    def test_review_rollback(self) -> None:
        assert REVIEW_ROLLBACK == "ReviewRollback"

    def test_mission_reopened(self) -> None:
        assert MISSION_REOPENED == "MissionReopened"

    def test_follow_up_recorded(self) -> None:
        assert FOLLOW_UP_RECORDED == "FollowUpRecorded"

    def test_mission_event_types_contains_all(self) -> None:
        assert MISSION_CREATED in MISSION_EVENT_TYPES
        assert MISSION_CLOSED in MISSION_EVENT_TYPES
        assert MISSION_STARTED in MISSION_EVENT_TYPES
        assert MISSION_COMPLETED in MISSION_EVENT_TYPES
        assert MISSION_CANCELLED in MISSION_EVENT_TYPES
        assert PHASE_ENTERED in MISSION_EVENT_TYPES
        assert REVIEW_ROLLBACK in MISSION_EVENT_TYPES
        assert MISSION_REOPENED in MISSION_EVENT_TYPES
        assert FOLLOW_UP_RECORDED in MISSION_EVENT_TYPES
        assert len(MISSION_EVENT_TYPES) == 9

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


# ── MissionCreatedPayload ────────────────────────────────────────────────────


class TestMissionCreatedPayload:
    """Tests for MissionCreatedPayload model."""

    def test_valid_construction(self) -> None:
        payload = _mission_created_payload()
        assert payload.mission_slug == "mission-contract-cutover"
        assert payload.mission_number == 14
        assert payload.mission_type == "software-dev"

    def test_missing_mission_type(self) -> None:
        with pytest.raises(PydanticValidationError):
            _mission_created_payload(mission_type=None)  # type: ignore[arg-type]


# ── MissionClosedPayload ─────────────────────────────────────────────────────


class TestMissionClosedPayload:
    """Tests for MissionClosedPayload model."""

    def test_valid_construction(self) -> None:
        payload = MissionClosedPayload(
            mission_slug="mission-contract-cutover",
            mission_number=14,
            mission_type="software-dev",
        )
        assert payload.mission_slug == "mission-contract-cutover"
        assert payload.mission_number == 14
        assert payload.mission_type == "software-dev"

    def test_rejects_legacy_catalog_fields(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionClosedPayload(
                mission_slug="mission-contract-cutover",
                mission_number=14,
                mission_type="software-dev",
                mission_id="M014",
            )


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

    def test_catalog_events_validate_without_affecting_lifecycle_projection(self) -> None:
        events = [
            _make_mission_event(
                MISSION_CREATED,
                _mission_created_payload().model_dump(),
                lamport_clock=1,
            ),
            _make_mission_event(
                MISSION_CLOSED,
                MissionClosedPayload(
                    mission_slug="mission-contract-cutover",
                    mission_number=14,
                    mission_type="software-dev",
                ).model_dump(),
                lamport_clock=2,
            ),
        ]

        result = reduce_lifecycle_events(events)

        assert result.mission_status is None
        assert result.mission_id is None
        assert result.current_phase is None
        assert result.anomalies == ()
        assert result.event_count == 2

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

    def test_mission_closed_does_not_alias_to_mission_completed(self) -> None:
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
                MISSION_CLOSED,
                MissionClosedPayload(
                    mission_slug="mission-contract-cutover",
                    mission_number=14,
                    mission_type="software-dev",
                ).model_dump(),
                lamport_clock=2,
            ),
        ]

        result = reduce_lifecycle_events(events)

        assert result.mission_status == MissionStatus.ACTIVE
        assert result.anomalies == ()

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
                aggregate_id="mission/WP01",
                payload=StatusTransitionPayload(
                    mission_slug="mission-001",
                    wp_id="WP01",
                    from_lane=None,
                    to_lane=Lane.PLANNED,
                    actor="user-1",
                    execution_mode="worktree",
                ).model_dump(),
                timestamp=datetime.now(timezone.utc),
                build_id="build-test",
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


# ── Post-mission reducer semantics (MissionReopened / FollowUpRecorded) ───────


class TestPostMissionReducerSemantics:
    """reduce_lifecycle_events() post-completion semantics.

    Contract: MissionReopened and FollowUpRecorded are valid ONLY after the
    mission reached a terminal state. Post-completion → no anomaly; a re-open
    leaves terminal (REOPENED), a follow-up is a recorded fact (status
    unchanged). Pre-completion → the event itself is the anomaly.
    """

    def _started(self, lamport: int = 1) -> Event:
        return _make_mission_event(
            MISSION_STARTED,
            MissionStartedPayload(
                mission_id="M001",
                mission_type="software-dev",
                initial_phase="specify",
                actor="user-1",
            ).model_dump(),
            lamport_clock=lamport,
        )

    def _completed(self, lamport: int = 2) -> Event:
        return _make_mission_event(
            MISSION_COMPLETED,
            MissionCompletedPayload(
                mission_id="M001",
                mission_type="software-dev",
                final_phase="review",
                actor="user-1",
            ).model_dump(),
            lamport_clock=lamport,
        )

    def _reopened(self, lamport: int = 3) -> Event:
        return _make_mission_event(
            MISSION_REOPENED,
            MissionReopenedPayload(
                mission_id="M001",
                mission_slug="mission-reopen-followup",
                reason="Operator requested re-open to land follow-up fix",
                reopened_by="stijn",
                reopened_at="2026-06-14T12:00:00+00:00",
            ).model_dump(),
            lamport_clock=lamport,
        )

    def _follow_up(self, lamport: int = 3) -> Event:
        return _make_mission_event(
            FOLLOW_UP_RECORDED,
            FollowUpRecordedPayload(
                mission_id="M001",
                mission_slug="mission-reopen-followup",
                follow_up_type="commit",
                commit_sha="a" * 40,
                recorded_by="stijn",
                recorded_at="2026-06-14T12:00:00+00:00",
            ).model_dump(),
            lamport_clock=lamport,
        )

    def test_reopen_after_completion_is_not_anomaly(self) -> None:
        result = reduce_lifecycle_events(
            [self._started(), self._completed(), self._reopened()]
        )
        assert result.anomalies == ()
        # Re-open transitions the mission OUT of terminal.
        assert result.mission_status == MissionStatus.REOPENED
        assert result.mission_status not in TERMINAL_MISSION_STATUSES
        assert result.event_count == 3

    def test_follow_up_after_completion_is_not_anomaly_and_status_unchanged(
        self,
    ) -> None:
        result = reduce_lifecycle_events(
            [self._started(), self._completed(), self._follow_up()]
        )
        assert result.anomalies == ()
        # FollowUpRecorded is a recorded fact: status stays terminal.
        assert result.mission_status == MissionStatus.COMPLETED
        assert result.event_count == 3

    def test_reopen_before_completion_is_anomaly(self) -> None:
        result = reduce_lifecycle_events([self._started(), self._reopened(lamport=2)])
        assert result.mission_status == MissionStatus.ACTIVE
        assert len(result.anomalies) == 1
        assert result.anomalies[0].event_type == MISSION_REOPENED
        assert "before completion" in result.anomalies[0].reason

    def test_follow_up_before_completion_is_anomaly(self) -> None:
        result = reduce_lifecycle_events(
            [self._started(), self._follow_up(lamport=2)]
        )
        assert result.mission_status == MissionStatus.ACTIVE
        assert len(result.anomalies) == 1
        assert result.anomalies[0].event_type == FOLLOW_UP_RECORDED
        assert "before completion" in result.anomalies[0].reason

    def test_reopen_then_complete_again_processes_normally(self) -> None:
        """After a valid re-open, status is non-terminal so a fresh
        MissionCompleted is applied without a post-terminal anomaly."""
        result = reduce_lifecycle_events(
            [
                self._started(),
                self._completed(lamport=2),
                self._reopened(lamport=3),
                self._completed(lamport=4),
            ]
        )
        assert result.anomalies == ()
        assert result.mission_status == MissionStatus.COMPLETED
        assert result.event_count == 4

    def test_invalid_reopen_payload_after_completion_is_anomaly(self) -> None:
        bad = _make_mission_event(
            MISSION_REOPENED,
            {"mission_id": "M001"},  # missing required fields
            lamport_clock=3,
        )
        result = reduce_lifecycle_events([self._started(), self._completed(), bad])
        assert result.mission_status == MissionStatus.COMPLETED
        assert len(result.anomalies) == 1
        assert "Invalid MissionReopened payload" == result.anomalies[0].reason

    def test_invalid_follow_up_payload_after_completion_is_anomaly(self) -> None:
        bad = _make_mission_event(
            FOLLOW_UP_RECORDED,
            {"mission_id": "M001", "follow_up_type": "commit"},  # missing commit_sha
            lamport_clock=3,
        )
        result = reduce_lifecycle_events([self._started(), self._completed(), bad])
        assert result.mission_status == MissionStatus.COMPLETED
        assert len(result.anomalies) == 1
        assert "Invalid FollowUpRecorded payload" == result.anomalies[0].reason

    def test_follow_up_does_not_leave_terminal_for_next_guard(self) -> None:
        """A follow-up keeps the mission terminal, so a later by-design
        anomaly event (e.g. PhaseEntered) is still flagged."""
        late_phase = _make_mission_event(
            PHASE_ENTERED,
            PhaseEnteredPayload(
                mission_id="M001",
                phase_name="implement",
                actor="user-1",
            ).model_dump(),
            lamport_clock=4,
        )
        result = reduce_lifecycle_events(
            [self._started(), self._completed(), self._follow_up(), late_phase]
        )
        assert result.mission_status == MissionStatus.COMPLETED
        assert len(result.anomalies) == 1
        assert "terminal" in result.anomalies[0].reason.lower()


# ── MissionReopenedPayload ───────────────────────────────────────────────────


class TestMissionReopenedPayload:
    """Tests for MissionReopenedPayload model."""

    def _valid(self, **overrides: object) -> dict:  # type: ignore[type-arg]
        payload: dict = {  # type: ignore[type-arg]
            "mission_id": "01KTESTMISSIONID0000000000",
            "mission_slug": "mission-reopen-followup",
            "reason": "Operator requested re-open to land follow-up fix",
            "reopened_by": "stijn",
            "reopened_at": "2026-06-14T12:00:00+00:00",
        }
        payload.update(overrides)
        return payload

    def test_valid_construction(self) -> None:
        p = MissionReopenedPayload(**self._valid())
        assert p.mission_id == "01KTESTMISSIONID0000000000"
        assert p.mission_slug == "mission-reopen-followup"
        assert p.reason.startswith("Operator")
        assert p.reopened_by == "stijn"
        assert p.cleared_merge is None

    def test_optional_cleared_merge_accepted(self) -> None:
        p = MissionReopenedPayload(
            **self._valid(
                cleared_merge={
                    "merged_at": "2026-06-10T00:00:00+00:00",
                    "merged_commit": "abc123",
                }
            )
        )
        assert p.cleared_merge == {
            "merged_at": "2026-06-10T00:00:00+00:00",
            "merged_commit": "abc123",
        }

    def test_missing_mission_id(self) -> None:
        payload = self._valid()
        del payload["mission_id"]
        with pytest.raises(PydanticValidationError):
            MissionReopenedPayload(**payload)  # type: ignore[arg-type]

    def test_missing_reason(self) -> None:
        payload = self._valid()
        del payload["reason"]
        with pytest.raises(PydanticValidationError):
            MissionReopenedPayload(**payload)  # type: ignore[arg-type]

    def test_empty_reason_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionReopenedPayload(**self._valid(reason=""))

    def test_missing_reopened_by(self) -> None:
        payload = self._valid()
        del payload["reopened_by"]
        with pytest.raises(PydanticValidationError):
            MissionReopenedPayload(**payload)  # type: ignore[arg-type]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(PydanticValidationError):
            MissionReopenedPayload(**self._valid(unexpected="x"))

    def test_frozen(self) -> None:
        p = MissionReopenedPayload(**self._valid())
        with pytest.raises(Exception):
            setattr(p, "reason", "changed")

    def test_round_trip(self) -> None:
        p = MissionReopenedPayload(
            **self._valid(cleared_merge={"merged_commit": "abc123"})
        )
        restored = MissionReopenedPayload(**p.model_dump(mode="json"))
        assert restored == p


# ── FollowUpRecordedPayload ──────────────────────────────────────────────────


class TestFollowUpRecordedPayload:
    """Tests for FollowUpRecordedPayload model."""

    def _commit(self, **overrides: object) -> dict:  # type: ignore[type-arg]
        payload: dict = {  # type: ignore[type-arg]
            "mission_id": "01KTESTMISSIONID0000000000",
            "mission_slug": "mission-reopen-followup",
            "follow_up_type": "commit",
            "commit_sha": "a" * 40,
            "pr_number": None,
            "recorded_by": "stijn",
            "recorded_at": "2026-06-14T12:00:00+00:00",
        }
        payload.update(overrides)
        return payload

    def _pr(self, **overrides: object) -> dict:  # type: ignore[type-arg]
        payload: dict = {  # type: ignore[type-arg]
            "mission_id": "01KTESTMISSIONID0000000000",
            "mission_slug": "mission-reopen-followup",
            "follow_up_type": "pr",
            "commit_sha": None,
            "pr_number": 1926,
            "recorded_by": "stijn",
            "recorded_at": "2026-06-14T12:00:00+00:00",
        }
        payload.update(overrides)
        return payload

    def test_valid_commit(self) -> None:
        p = FollowUpRecordedPayload(**self._commit())
        assert p.follow_up_type == "commit"
        assert p.commit_sha == "a" * 40
        assert p.pr_number is None

    def test_valid_pr(self) -> None:
        p = FollowUpRecordedPayload(**self._pr())
        assert p.follow_up_type == "pr"
        assert p.pr_number == 1926
        assert p.commit_sha is None

    def test_invalid_follow_up_type_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            FollowUpRecordedPayload(**self._commit(follow_up_type="branch"))

    def test_commit_type_requires_commit_sha(self) -> None:
        with pytest.raises(PydanticValidationError):
            FollowUpRecordedPayload(**self._commit(commit_sha=None))

    def test_pr_type_requires_pr_number(self) -> None:
        with pytest.raises(PydanticValidationError):
            FollowUpRecordedPayload(**self._pr(pr_number=None))

    def test_pr_number_must_be_positive(self) -> None:
        with pytest.raises(PydanticValidationError):
            FollowUpRecordedPayload(**self._pr(pr_number=0))

    def test_missing_mission_id(self) -> None:
        payload = self._commit()
        del payload["mission_id"]
        with pytest.raises(PydanticValidationError):
            FollowUpRecordedPayload(**payload)  # type: ignore[arg-type]

    def test_missing_recorded_by(self) -> None:
        payload = self._commit()
        del payload["recorded_by"]
        with pytest.raises(PydanticValidationError):
            FollowUpRecordedPayload(**payload)  # type: ignore[arg-type]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(PydanticValidationError):
            FollowUpRecordedPayload(**self._commit(unexpected="x"))

    def test_frozen(self) -> None:
        p = FollowUpRecordedPayload(**self._commit())
        with pytest.raises(Exception):
            setattr(p, "follow_up_type", "pr")

    def test_round_trip_commit(self) -> None:
        p = FollowUpRecordedPayload(**self._commit())
        restored = FollowUpRecordedPayload(**p.model_dump(mode="json"))
        assert restored == p

    def test_round_trip_pr(self) -> None:
        p = FollowUpRecordedPayload(**self._pr())
        restored = FollowUpRecordedPayload(**p.model_dump(mode="json"))
        assert restored == p


# ── Conformance registry presence ────────────────────────────────────────────


class TestPostMissionRegistryPresence:
    """The new events must be reachable through the conformance model map."""

    def test_events_registered_in_model_map(self) -> None:
        from spec_kitty_events.conformance.validators import _EVENT_TYPE_TO_MODEL

        assert _EVENT_TYPE_TO_MODEL[MISSION_REOPENED] is MissionReopenedPayload
        assert _EVENT_TYPE_TO_MODEL[FOLLOW_UP_RECORDED] is FollowUpRecordedPayload

    def test_validate_event_accepts_valid_payloads(self) -> None:
        from spec_kitty_events.conformance import validate_event

        reopened = {
            "mission_id": "01KTESTMISSIONID0000000000",
            "mission_slug": "mission-reopen-followup",
            "reason": "land follow-up",
            "reopened_by": "stijn",
            "reopened_at": "2026-06-14T12:00:00+00:00",
            "cleared_merge": None,
        }
        result = validate_event(reopened, MISSION_REOPENED)
        assert not result.model_violations

        follow_up = {
            "mission_id": "01KTESTMISSIONID0000000000",
            "mission_slug": "mission-reopen-followup",
            "follow_up_type": "pr",
            "commit_sha": None,
            "pr_number": 1926,
            "recorded_by": "stijn",
            "recorded_at": "2026-06-14T12:00:00+00:00",
        }
        result = validate_event(follow_up, FOLLOW_UP_RECORDED)
        assert not result.model_violations

    def test_validate_event_flags_invalid_discriminator(self) -> None:
        from spec_kitty_events.conformance import validate_event

        bad = {
            "mission_id": "01KTESTMISSIONID0000000000",
            "mission_slug": "mission-reopen-followup",
            "follow_up_type": "commit",
            "commit_sha": None,
            "pr_number": None,
            "recorded_by": "stijn",
            "recorded_at": "2026-06-14T12:00:00+00:00",
        }
        result = validate_event(bad, FOLLOW_UP_RECORDED)
        assert result.model_violations
