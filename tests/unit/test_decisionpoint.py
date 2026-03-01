"""Unit tests for DecisionPoint payload models, constants, and enums (FR-001, FR-002).

Covers: constant values, enum members, payload validation, mandatory audit fields,
authority role constraints, and frozen model immutability.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from spec_kitty_events.decisionpoint import (
    DECISION_POINT_DISCUSSING,
    DECISION_POINT_EVENT_TYPES,
    DECISION_POINT_OPENED,
    DECISION_POINT_OVERRIDDEN,
    DECISION_POINT_RESOLVED,
    DECISIONPOINT_SCHEMA_VERSION,
    DecisionAuthorityRole,
    DecisionPointDiscussingPayload,
    DecisionPointOpenedPayload,
    DecisionPointOverriddenPayload,
    DecisionPointResolvedPayload,
    DecisionPointState,
)


# ── Constants tests (FR-001) ────────────────────────────────────────────────


class TestConstants:
    def test_event_type_values(self) -> None:
        assert DECISION_POINT_OPENED == "DecisionPointOpened"
        assert DECISION_POINT_DISCUSSING == "DecisionPointDiscussing"
        assert DECISION_POINT_RESOLVED == "DecisionPointResolved"
        assert DECISION_POINT_OVERRIDDEN == "DecisionPointOverridden"

    def test_event_types_frozenset(self) -> None:
        assert isinstance(DECISION_POINT_EVENT_TYPES, frozenset)
        assert DECISION_POINT_EVENT_TYPES == frozenset({
            "DecisionPointOpened",
            "DecisionPointDiscussing",
            "DecisionPointResolved",
            "DecisionPointOverridden",
        })
        assert len(DECISION_POINT_EVENT_TYPES) == 4

    def test_schema_version(self) -> None:
        assert DECISIONPOINT_SCHEMA_VERSION == "2.6.0"


# ── Enum tests (FR-001) ─────────────────────────────────────────────────────


class TestEnums:
    def test_decision_point_state_members(self) -> None:
        assert DecisionPointState.OPEN.value == "open"
        assert DecisionPointState.DISCUSSING.value == "discussing"
        assert DecisionPointState.RESOLVED.value == "resolved"
        assert DecisionPointState.OVERRIDDEN.value == "overridden"
        assert len(DecisionPointState) == 4

    def test_decision_authority_role_members(self) -> None:
        assert DecisionAuthorityRole.MISSION_OWNER.value == "mission_owner"
        assert DecisionAuthorityRole.ADVISORY.value == "advisory"
        assert DecisionAuthorityRole.INFORMED.value == "informed"
        assert len(DecisionAuthorityRole) == 3

    def test_state_is_str_enum(self) -> None:
        assert isinstance(DecisionPointState.OPEN, str)
        assert DecisionPointState.OPEN == "open"

    def test_role_is_str_enum(self) -> None:
        assert isinstance(DecisionAuthorityRole.MISSION_OWNER, str)
        assert DecisionAuthorityRole.MISSION_OWNER == "mission_owner"


# ── Payload test helpers ─────────────────────────────────────────────────────

_NOW = datetime.now(timezone.utc)


def _valid_payload_dict() -> dict:
    """Return a valid payload dict usable for all DecisionPoint event types."""
    return {
        "decision_point_id": "dp-001",
        "mission_id": "m-001",
        "run_id": "run-001",
        "feature_slug": "feature-x",
        "phase": "P1",
        "actor_id": "human-1",
        "actor_type": "human",
        "authority_role": "mission_owner",
        "mission_owner_authority_flag": True,
        "mission_owner_authority_path": "/missions/m-001/owner",
        "rationale": "This is the best option",
        "alternatives_considered": ("Option A", "Option B"),
        "evidence_refs": ("ref-001",),
        "state_entered_at": _NOW.isoformat(),
        "recorded_at": _NOW.isoformat(),
    }


# ── Payload validation tests (FR-002) ───────────────────────────────────────


class TestPayloadValidation:
    """Test that all payload models validate mandatory fields."""

    @pytest.mark.parametrize("payload_cls", [
        DecisionPointOpenedPayload,
        DecisionPointDiscussingPayload,
        DecisionPointResolvedPayload,
        DecisionPointOverriddenPayload,
    ])
    def test_valid_payload_succeeds(self, payload_cls: type) -> None:
        payload = payload_cls.model_validate(_valid_payload_dict())
        assert payload.decision_point_id == "dp-001"
        assert payload.mission_id == "m-001"
        assert payload.run_id == "run-001"
        assert payload.feature_slug == "feature-x"
        assert payload.actor_id == "human-1"
        assert payload.actor_type == "human"
        assert payload.authority_role == DecisionAuthorityRole.MISSION_OWNER
        assert payload.mission_owner_authority_flag is True
        assert payload.rationale == "This is the best option"
        assert len(payload.alternatives_considered) == 2
        assert len(payload.evidence_refs) == 1

    @pytest.mark.parametrize("missing_field", [
        "decision_point_id",
        "mission_id",
        "run_id",
        "feature_slug",
        "phase",
        "actor_id",
        "actor_type",
        "authority_role",
        "mission_owner_authority_flag",
        "mission_owner_authority_path",
        "rationale",
        "alternatives_considered",
        "evidence_refs",
        "state_entered_at",
        "recorded_at",
    ])
    def test_missing_mandatory_field_raises(self, missing_field: str) -> None:
        data = _valid_payload_dict()
        del data[missing_field]
        with pytest.raises(ValidationError):
            DecisionPointOpenedPayload.model_validate(data)

    def test_empty_alternatives_raises(self) -> None:
        data = _valid_payload_dict()
        data["alternatives_considered"] = ()
        with pytest.raises(ValidationError):
            DecisionPointOpenedPayload.model_validate(data)

    def test_empty_evidence_refs_raises(self) -> None:
        data = _valid_payload_dict()
        data["evidence_refs"] = ()
        with pytest.raises(ValidationError):
            DecisionPointOpenedPayload.model_validate(data)

    def test_empty_string_fields_raise(self) -> None:
        for field in ["decision_point_id", "mission_id", "run_id", "feature_slug",
                       "phase", "actor_id", "rationale"]:
            data = _valid_payload_dict()
            data[field] = ""
            with pytest.raises(ValidationError):
                DecisionPointOpenedPayload.model_validate(data)

    def test_invalid_actor_type_raises(self) -> None:
        data = _valid_payload_dict()
        data["actor_type"] = "robot"
        with pytest.raises(ValidationError):
            DecisionPointOpenedPayload.model_validate(data)

    def test_invalid_authority_role_raises(self) -> None:
        data = _valid_payload_dict()
        data["authority_role"] = "admin"
        with pytest.raises(ValidationError):
            DecisionPointOpenedPayload.model_validate(data)


# ── Frozen immutability tests ────────────────────────────────────────────────


class TestFrozenModels:
    def test_payload_is_frozen(self) -> None:
        payload = DecisionPointOpenedPayload.model_validate(_valid_payload_dict())
        with pytest.raises(ValidationError):
            payload.rationale = "changed"  # type: ignore[misc]

    def test_all_payload_types_frozen(self) -> None:
        for cls in [DecisionPointOpenedPayload, DecisionPointDiscussingPayload,
                     DecisionPointResolvedPayload, DecisionPointOverriddenPayload]:
            payload = cls.model_validate(_valid_payload_dict())
            assert payload.model_config.get("frozen") is True
