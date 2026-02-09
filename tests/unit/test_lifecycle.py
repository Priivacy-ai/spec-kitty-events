"""Unit tests for mission lifecycle event contracts."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.lifecycle import (
    MISSION_CANCELLED,
    MISSION_COMPLETED,
    MISSION_EVENT_TYPES,
    MISSION_STARTED,
    PHASE_ENTERED,
    REVIEW_ROLLBACK,
    SCHEMA_VERSION,
    TERMINAL_MISSION_STATUSES,
    MissionCancelledPayload,
    MissionCompletedPayload,
    MissionStartedPayload,
    MissionStatus,
    PhaseEnteredPayload,
    ReviewRollbackPayload,
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
        assert SCHEMA_VERSION == "1.0.0"

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
