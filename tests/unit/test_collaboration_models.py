"""Unit tests for collaboration event constants and identity models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.collaboration import (
    COLLABORATION_EVENT_TYPES,
    COMMENT_POSTED,
    CONCURRENT_DRIVER_WARNING,
    DECISION_CAPTURED,
    DRIVE_INTENT_SET,
    FOCUS_CHANGED,
    PARTICIPANT_INVITED,
    PARTICIPANT_JOINED,
    PARTICIPANT_LEFT,
    POTENTIAL_STEP_COLLISION_DETECTED,
    PRESENCE_HEARTBEAT,
    PROMPT_STEP_EXECUTION_COMPLETED,
    PROMPT_STEP_EXECUTION_STARTED,
    SESSION_LINKED,
    WARNING_ACKNOWLEDGED,
    AuthPrincipalBinding,
    FocusTarget,
    ParticipantIdentity,
    UnknownParticipantError,
)
from spec_kitty_events.models import SpecKittyEventsError


# ── Constants ────────────────────────────────────────────────────────────────


class TestConstants:
    """Tests for the 14 collaboration event type constants."""

    ALL_CONSTANTS = [
        PARTICIPANT_INVITED,
        PARTICIPANT_JOINED,
        PARTICIPANT_LEFT,
        PRESENCE_HEARTBEAT,
        DRIVE_INTENT_SET,
        FOCUS_CHANGED,
        PROMPT_STEP_EXECUTION_STARTED,
        PROMPT_STEP_EXECUTION_COMPLETED,
        CONCURRENT_DRIVER_WARNING,
        POTENTIAL_STEP_COLLISION_DETECTED,
        WARNING_ACKNOWLEDGED,
        COMMENT_POSTED,
        DECISION_CAPTURED,
        SESSION_LINKED,
    ]

    def test_all_constants_are_strings(self) -> None:
        for c in self.ALL_CONSTANTS:
            assert isinstance(c, str), f"{c!r} is not a string"

    def test_all_constants_are_nonempty(self) -> None:
        for c in self.ALL_CONSTANTS:
            assert len(c) > 0, f"Constant is empty"

    def test_frozenset_has_14_elements(self) -> None:
        assert len(COLLABORATION_EVENT_TYPES) == 14

    def test_frozenset_matches_constants(self) -> None:
        assert COLLABORATION_EVENT_TYPES == frozenset(self.ALL_CONSTANTS)

    def test_no_duplicates_among_constants(self) -> None:
        assert len(self.ALL_CONSTANTS) == len(set(self.ALL_CONSTANTS))

    def test_frozenset_is_frozenset_type(self) -> None:
        assert isinstance(COLLABORATION_EVENT_TYPES, frozenset)

    def test_expected_constant_values(self) -> None:
        assert PARTICIPANT_INVITED == "ParticipantInvited"
        assert PARTICIPANT_JOINED == "ParticipantJoined"
        assert PARTICIPANT_LEFT == "ParticipantLeft"
        assert PRESENCE_HEARTBEAT == "PresenceHeartbeat"
        assert DRIVE_INTENT_SET == "DriveIntentSet"
        assert FOCUS_CHANGED == "FocusChanged"
        assert PROMPT_STEP_EXECUTION_STARTED == "PromptStepExecutionStarted"
        assert PROMPT_STEP_EXECUTION_COMPLETED == "PromptStepExecutionCompleted"
        assert CONCURRENT_DRIVER_WARNING == "ConcurrentDriverWarning"
        assert POTENTIAL_STEP_COLLISION_DETECTED == "PotentialStepCollisionDetected"
        assert WARNING_ACKNOWLEDGED == "WarningAcknowledged"
        assert COMMENT_POSTED == "CommentPosted"
        assert DECISION_CAPTURED == "DecisionCaptured"
        assert SESSION_LINKED == "SessionLinked"


# ── ParticipantIdentity ─────────────────────────────────────────────────────


class TestParticipantIdentity:
    """Tests for the ParticipantIdentity model."""

    def test_valid_human_construction(self) -> None:
        pid = ParticipantIdentity(
            participant_id="p-001",
            participant_type="human",
            display_name="Alice",
            session_id="sess-abc",
        )
        assert pid.participant_id == "p-001"
        assert pid.participant_type == "human"
        assert pid.display_name == "Alice"
        assert pid.session_id == "sess-abc"

    def test_valid_llm_context_construction(self) -> None:
        pid = ParticipantIdentity(
            participant_id="p-002",
            participant_type="llm_context",
        )
        assert pid.participant_type == "llm_context"

    def test_optional_fields_default_to_none(self) -> None:
        pid = ParticipantIdentity(
            participant_id="p-003",
            participant_type="human",
        )
        assert pid.display_name is None
        assert pid.session_id is None

    def test_frozen_rejects_assignment(self) -> None:
        pid = ParticipantIdentity(
            participant_id="p-004",
            participant_type="human",
        )
        with pytest.raises(PydanticValidationError):
            pid.participant_id = "changed"  # type: ignore[misc]

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ParticipantIdentity(
                participant_id="",
                participant_type="human",
            )

    def test_invalid_participant_type_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ParticipantIdentity(
                participant_id="p-005",
                participant_type="bot",  # type: ignore[arg-type]
            )

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = ParticipantIdentity(
            participant_id="p-006",
            participant_type="llm_context",
            display_name="Claude",
            session_id="sess-xyz",
        )
        data = original.model_dump()
        restored = ParticipantIdentity.model_validate(data)
        assert restored == original

    def test_model_dump_produces_dict(self) -> None:
        pid = ParticipantIdentity(
            participant_id="p-007",
            participant_type="human",
        )
        dumped = pid.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["participant_id"] == "p-007"
        assert dumped["participant_type"] == "human"


# ── AuthPrincipalBinding ────────────────────────────────────────────────────


class TestAuthPrincipalBinding:
    """Tests for the AuthPrincipalBinding model."""

    def test_valid_construction(self) -> None:
        now = datetime.now(timezone.utc)
        binding = AuthPrincipalBinding(
            auth_principal_id="auth-123",
            participant_id="p-001",
            bound_at=now,
        )
        assert binding.auth_principal_id == "auth-123"
        assert binding.participant_id == "p-001"
        assert binding.bound_at == now

    def test_frozen_rejects_assignment(self) -> None:
        binding = AuthPrincipalBinding(
            auth_principal_id="auth-456",
            participant_id="p-002",
            bound_at=datetime.now(timezone.utc),
        )
        with pytest.raises(PydanticValidationError):
            binding.auth_principal_id = "changed"  # type: ignore[misc]

    def test_empty_auth_principal_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            AuthPrincipalBinding(
                auth_principal_id="",
                participant_id="p-003",
                bound_at=datetime.now(timezone.utc),
            )

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            AuthPrincipalBinding(
                auth_principal_id="auth-789",
                participant_id="",
                bound_at=datetime.now(timezone.utc),
            )

    def test_bound_at_accepts_datetime(self) -> None:
        ts = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        binding = AuthPrincipalBinding(
            auth_principal_id="auth-abc",
            participant_id="p-004",
            bound_at=ts,
        )
        assert binding.bound_at == ts

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = AuthPrincipalBinding(
            auth_principal_id="auth-def",
            participant_id="p-005",
            bound_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        data = original.model_dump()
        restored = AuthPrincipalBinding.model_validate(data)
        assert restored == original


# ── FocusTarget ─────────────────────────────────────────────────────────────


class TestFocusTarget:
    """Tests for the FocusTarget model."""

    def test_valid_wp_target(self) -> None:
        ft = FocusTarget(target_type="wp", target_id="WP01")
        assert ft.target_type == "wp"
        assert ft.target_id == "WP01"

    def test_valid_step_target(self) -> None:
        ft = FocusTarget(target_type="step", target_id="step-3")
        assert ft.target_type == "step"

    def test_valid_file_target(self) -> None:
        ft = FocusTarget(target_type="file", target_id="src/main.py")
        assert ft.target_type == "file"

    def test_frozen_rejects_assignment(self) -> None:
        ft = FocusTarget(target_type="wp", target_id="WP02")
        with pytest.raises(PydanticValidationError):
            ft.target_id = "changed"  # type: ignore[misc]

    def test_hashable_usable_as_dict_key(self) -> None:
        ft = FocusTarget(target_type="wp", target_id="WP01")
        d = {ft: "some_value"}
        assert d[ft] == "some_value"

    def test_equal_instances_have_same_hash(self) -> None:
        ft1 = FocusTarget(target_type="step", target_id="step-1")
        ft2 = FocusTarget(target_type="step", target_id="step-1")
        assert ft1 == ft2
        assert hash(ft1) == hash(ft2)

    def test_different_instances_are_not_equal(self) -> None:
        ft1 = FocusTarget(target_type="wp", target_id="WP01")
        ft2 = FocusTarget(target_type="wp", target_id="WP02")
        assert ft1 != ft2

    def test_empty_target_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            FocusTarget(target_type="wp", target_id="")

    def test_invalid_target_type_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            FocusTarget(
                target_type="directory",  # type: ignore[arg-type]
                target_id="some-id",
            )

    def test_usable_in_set(self) -> None:
        ft1 = FocusTarget(target_type="wp", target_id="WP01")
        ft2 = FocusTarget(target_type="wp", target_id="WP01")
        ft3 = FocusTarget(target_type="step", target_id="step-1")
        s = {ft1, ft2, ft3}
        assert len(s) == 2  # ft1 and ft2 are equal


# ── UnknownParticipantError ─────────────────────────────────────────────────


class TestUnknownParticipantError:
    """Tests for the UnknownParticipantError exception."""

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(UnknownParticipantError):
            raise UnknownParticipantError(
                participant_id="p-unknown",
                event_id="evt-123",
                event_type="ParticipantJoined",
            )

    def test_caught_as_spec_kitty_events_error(self) -> None:
        with pytest.raises(SpecKittyEventsError):
            raise UnknownParticipantError(
                participant_id="p-unknown",
                event_id="evt-456",
                event_type="FocusChanged",
            )

    def test_caught_as_base_exception(self) -> None:
        with pytest.raises(Exception):
            raise UnknownParticipantError(
                participant_id="p-unknown",
                event_id="evt-789",
                event_type="DriveIntentSet",
            )

    def test_attributes_accessible(self) -> None:
        err = UnknownParticipantError(
            participant_id="p-ghost",
            event_id="evt-abc",
            event_type="PresenceHeartbeat",
        )
        assert err.participant_id == "p-ghost"
        assert err.event_id == "evt-abc"
        assert err.event_type == "PresenceHeartbeat"

    def test_message_format(self) -> None:
        err = UnknownParticipantError(
            participant_id="p-ghost",
            event_id="evt-def",
            event_type="CommentPosted",
        )
        msg = str(err)
        assert "p-ghost" in msg
        assert "evt-def" in msg
        assert "CommentPosted" in msg
        assert "Not in mission roster" in msg

    def test_is_subclass_of_spec_kitty_events_error(self) -> None:
        assert issubclass(UnknownParticipantError, SpecKittyEventsError)
