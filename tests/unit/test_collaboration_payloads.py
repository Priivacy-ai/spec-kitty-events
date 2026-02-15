"""Unit tests for collaboration participant lifecycle payload models (WP02)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.collaboration import (
    ParticipantIdentity,
    ParticipantInvitedPayload,
    ParticipantJoinedPayload,
    ParticipantLeftPayload,
    PresenceHeartbeatPayload,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_identity(
    participant_id: str = "p-001",
    participant_type: str = "human",
    display_name: str | None = "Alice",
    session_id: str | None = "sess-abc",
) -> ParticipantIdentity:
    return ParticipantIdentity(
        participant_id=participant_id,
        participant_type=participant_type,  # type: ignore[arg-type]
        display_name=display_name,
        session_id=session_id,
    )


# ── ParticipantInvitedPayload ──────────────────────────────────────────────


class TestParticipantInvitedPayload:
    """Tests for the ParticipantInvitedPayload model."""

    def test_valid_construction(self) -> None:
        identity = _make_identity()
        payload = ParticipantInvitedPayload(
            participant_id="p-001",
            participant_identity=identity,
            invited_by="p-host",
            mission_id="m-100",
        )
        assert payload.participant_id == "p-001"
        assert payload.participant_identity == identity
        assert payload.invited_by == "p-host"
        assert payload.mission_id == "m-100"

    def test_frozen_rejects_assignment(self) -> None:
        payload = ParticipantInvitedPayload(
            participant_id="p-001",
            participant_identity=_make_identity(),
            invited_by="p-host",
            mission_id="m-100",
        )
        with pytest.raises(PydanticValidationError):
            payload.participant_id = "changed"  # type: ignore[misc]

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ParticipantInvitedPayload(
                participant_id="",
                participant_identity=_make_identity(),
                invited_by="p-host",
                mission_id="m-100",
            )

    def test_empty_invited_by_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ParticipantInvitedPayload(
                participant_id="p-001",
                participant_identity=_make_identity(),
                invited_by="",
                mission_id="m-100",
            )

    def test_empty_mission_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ParticipantInvitedPayload(
                participant_id="p-001",
                participant_identity=_make_identity(),
                invited_by="p-host",
                mission_id="",
            )

    def test_embedded_participant_identity(self) -> None:
        identity = _make_identity(
            participant_id="p-002",
            participant_type="llm_context",
            display_name="Claude",
            session_id="sess-xyz",
        )
        payload = ParticipantInvitedPayload(
            participant_id="p-002",
            participant_identity=identity,
            invited_by="p-host",
            mission_id="m-200",
        )
        assert payload.participant_identity.participant_id == "p-002"
        assert payload.participant_identity.participant_type == "llm_context"
        assert payload.participant_identity.display_name == "Claude"
        assert payload.participant_identity.session_id == "sess-xyz"

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = ParticipantInvitedPayload(
            participant_id="p-003",
            participant_identity=_make_identity(participant_id="p-003"),
            invited_by="p-host",
            mission_id="m-300",
        )
        data = original.model_dump()
        restored = ParticipantInvitedPayload.model_validate(data)
        assert restored == original

    def test_model_dump_produces_dict(self) -> None:
        payload = ParticipantInvitedPayload(
            participant_id="p-004",
            participant_identity=_make_identity(participant_id="p-004"),
            invited_by="p-host",
            mission_id="m-400",
        )
        dumped = payload.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["participant_id"] == "p-004"
        assert dumped["invited_by"] == "p-host"
        assert dumped["mission_id"] == "m-400"
        assert isinstance(dumped["participant_identity"], dict)

    def test_missing_required_fields_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ParticipantInvitedPayload(  # type: ignore[call-arg]
                participant_id="p-005",
            )


# ── ParticipantJoinedPayload ───────────────────────────────────────────────


class TestParticipantJoinedPayload:
    """Tests for the ParticipantJoinedPayload model."""

    def test_valid_construction_with_auth(self) -> None:
        identity = _make_identity()
        payload = ParticipantJoinedPayload(
            participant_id="p-001",
            participant_identity=identity,
            mission_id="m-100",
            auth_principal_id="auth-abc",
        )
        assert payload.participant_id == "p-001"
        assert payload.participant_identity == identity
        assert payload.mission_id == "m-100"
        assert payload.auth_principal_id == "auth-abc"

    def test_valid_construction_without_auth(self) -> None:
        payload = ParticipantJoinedPayload(
            participant_id="p-001",
            participant_identity=_make_identity(),
            mission_id="m-100",
        )
        assert payload.auth_principal_id is None

    def test_frozen_rejects_assignment(self) -> None:
        payload = ParticipantJoinedPayload(
            participant_id="p-001",
            participant_identity=_make_identity(),
            mission_id="m-100",
        )
        with pytest.raises(PydanticValidationError):
            payload.mission_id = "changed"  # type: ignore[misc]

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ParticipantJoinedPayload(
                participant_id="",
                participant_identity=_make_identity(),
                mission_id="m-100",
            )

    def test_empty_mission_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ParticipantJoinedPayload(
                participant_id="p-001",
                participant_identity=_make_identity(),
                mission_id="",
            )

    def test_auth_principal_id_defaults_to_none(self) -> None:
        payload = ParticipantJoinedPayload(
            participant_id="p-002",
            participant_identity=_make_identity(participant_id="p-002"),
            mission_id="m-200",
        )
        assert payload.auth_principal_id is None

    def test_embedded_participant_identity(self) -> None:
        identity = _make_identity(
            participant_id="p-llm",
            participant_type="llm_context",
            display_name="GPT",
        )
        payload = ParticipantJoinedPayload(
            participant_id="p-llm",
            participant_identity=identity,
            mission_id="m-300",
        )
        assert payload.participant_identity.participant_type == "llm_context"
        assert payload.participant_identity.display_name == "GPT"

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = ParticipantJoinedPayload(
            participant_id="p-003",
            participant_identity=_make_identity(participant_id="p-003"),
            mission_id="m-300",
            auth_principal_id="auth-xyz",
        )
        data = original.model_dump()
        restored = ParticipantJoinedPayload.model_validate(data)
        assert restored == original

    def test_round_trip_without_auth(self) -> None:
        original = ParticipantJoinedPayload(
            participant_id="p-004",
            participant_identity=_make_identity(participant_id="p-004"),
            mission_id="m-400",
        )
        data = original.model_dump()
        restored = ParticipantJoinedPayload.model_validate(data)
        assert restored == original
        assert restored.auth_principal_id is None

    def test_model_dump_produces_dict(self) -> None:
        payload = ParticipantJoinedPayload(
            participant_id="p-005",
            participant_identity=_make_identity(participant_id="p-005"),
            mission_id="m-500",
        )
        dumped = payload.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["participant_id"] == "p-005"
        assert dumped["auth_principal_id"] is None


# ── ParticipantLeftPayload ─────────────────────────────────────────────────


class TestParticipantLeftPayload:
    """Tests for the ParticipantLeftPayload model."""

    def test_valid_construction_with_reason(self) -> None:
        payload = ParticipantLeftPayload(
            participant_id="p-001",
            mission_id="m-100",
            reason="disconnect",
        )
        assert payload.participant_id == "p-001"
        assert payload.mission_id == "m-100"
        assert payload.reason == "disconnect"

    def test_valid_construction_without_reason(self) -> None:
        payload = ParticipantLeftPayload(
            participant_id="p-001",
            mission_id="m-100",
        )
        assert payload.reason is None

    def test_frozen_rejects_assignment(self) -> None:
        payload = ParticipantLeftPayload(
            participant_id="p-001",
            mission_id="m-100",
        )
        with pytest.raises(PydanticValidationError):
            payload.participant_id = "changed"  # type: ignore[misc]

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ParticipantLeftPayload(
                participant_id="",
                mission_id="m-100",
            )

    def test_empty_mission_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            ParticipantLeftPayload(
                participant_id="p-001",
                mission_id="",
            )

    def test_reason_defaults_to_none(self) -> None:
        payload = ParticipantLeftPayload(
            participant_id="p-002",
            mission_id="m-200",
        )
        assert payload.reason is None

    def test_reason_explicit(self) -> None:
        payload = ParticipantLeftPayload(
            participant_id="p-003",
            mission_id="m-300",
            reason="explicit",
        )
        assert payload.reason == "explicit"

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = ParticipantLeftPayload(
            participant_id="p-004",
            mission_id="m-400",
            reason="timeout",
        )
        data = original.model_dump()
        restored = ParticipantLeftPayload.model_validate(data)
        assert restored == original

    def test_round_trip_without_reason(self) -> None:
        original = ParticipantLeftPayload(
            participant_id="p-005",
            mission_id="m-500",
        )
        data = original.model_dump()
        restored = ParticipantLeftPayload.model_validate(data)
        assert restored == original
        assert restored.reason is None

    def test_model_dump_produces_dict(self) -> None:
        payload = ParticipantLeftPayload(
            participant_id="p-006",
            mission_id="m-600",
            reason="disconnect",
        )
        dumped = payload.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["participant_id"] == "p-006"
        assert dumped["mission_id"] == "m-600"
        assert dumped["reason"] == "disconnect"


# ── PresenceHeartbeatPayload ──────────────────────────────────────────────


class TestPresenceHeartbeatPayload:
    """Tests for the PresenceHeartbeatPayload model."""

    def test_valid_construction_with_session(self) -> None:
        payload = PresenceHeartbeatPayload(
            participant_id="p-001",
            mission_id="m-100",
            session_id="sess-abc",
        )
        assert payload.participant_id == "p-001"
        assert payload.mission_id == "m-100"
        assert payload.session_id == "sess-abc"

    def test_valid_construction_without_session(self) -> None:
        payload = PresenceHeartbeatPayload(
            participant_id="p-001",
            mission_id="m-100",
        )
        assert payload.session_id is None

    def test_frozen_rejects_assignment(self) -> None:
        payload = PresenceHeartbeatPayload(
            participant_id="p-001",
            mission_id="m-100",
        )
        with pytest.raises(PydanticValidationError):
            payload.participant_id = "changed"  # type: ignore[misc]

    def test_empty_participant_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PresenceHeartbeatPayload(
                participant_id="",
                mission_id="m-100",
            )

    def test_empty_mission_id_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            PresenceHeartbeatPayload(
                participant_id="p-001",
                mission_id="",
            )

    def test_session_id_defaults_to_none(self) -> None:
        payload = PresenceHeartbeatPayload(
            participant_id="p-002",
            mission_id="m-200",
        )
        assert payload.session_id is None

    def test_session_id_explicit(self) -> None:
        payload = PresenceHeartbeatPayload(
            participant_id="p-003",
            mission_id="m-300",
            session_id="sess-xyz",
        )
        assert payload.session_id == "sess-xyz"

    def test_round_trip_via_model_dump_validate(self) -> None:
        original = PresenceHeartbeatPayload(
            participant_id="p-004",
            mission_id="m-400",
            session_id="sess-123",
        )
        data = original.model_dump()
        restored = PresenceHeartbeatPayload.model_validate(data)
        assert restored == original

    def test_round_trip_without_session(self) -> None:
        original = PresenceHeartbeatPayload(
            participant_id="p-005",
            mission_id="m-500",
        )
        data = original.model_dump()
        restored = PresenceHeartbeatPayload.model_validate(data)
        assert restored == original
        assert restored.session_id is None

    def test_model_dump_produces_dict(self) -> None:
        payload = PresenceHeartbeatPayload(
            participant_id="p-006",
            mission_id="m-600",
            session_id="sess-final",
        )
        dumped = payload.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["participant_id"] == "p-006"
        assert dumped["mission_id"] == "m-600"
        assert dumped["session_id"] == "sess-final"
