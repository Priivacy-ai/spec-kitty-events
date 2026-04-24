"""Unit tests for DecisionPoint payload models, constants, and enums (FR-001, FR-002).

Covers: constant values, enum members, payload validation, mandatory audit fields,
authority role constraints, frozen model immutability, V1 discriminated-union
payloads (Opened/Discussing/Resolved), Widened payload, and Overridden extension.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from spec_kitty_events.decision_moment import (
    DiscussingSnapshotKind,
    OriginFlow,
    OriginSurface,
    TerminalOutcome,
    WideningChannel,
)
from spec_kitty_events.decisionpoint import (
    DECISION_POINT_DISCUSSING,
    DECISION_POINT_EVENT_TYPES,
    DECISION_POINT_OPENED,
    DECISION_POINT_OVERRIDDEN,
    DECISION_POINT_RESOLVED,
    DECISION_POINT_WIDENED,
    DECISIONPOINT_SCHEMA_VERSION,
    DecisionAuthorityRole,
    DecisionPointDiscussingAdrPayload,
    DecisionPointDiscussingInterviewPayload,
    DecisionPointDiscussingPayload,
    DecisionPointOpenedAdrPayload,
    DecisionPointOpenedInterviewPayload,
    DecisionPointOpenedPayload,
    DecisionPointOverriddenPayload,
    DecisionPointResolvedAdrPayload,
    DecisionPointResolvedInterviewPayload,
    DecisionPointResolvedPayload,
    DecisionPointState,
    DecisionPointWidenedPayload,
    _EVENT_TO_PAYLOAD,
)


# ── Constants tests (FR-001) ────────────────────────────────────────────────


class TestConstants:
    def test_event_type_values(self) -> None:
        assert DECISION_POINT_OPENED == "DecisionPointOpened"
        assert DECISION_POINT_WIDENED == "DecisionPointWidened"
        assert DECISION_POINT_DISCUSSING == "DecisionPointDiscussing"
        assert DECISION_POINT_RESOLVED == "DecisionPointResolved"
        assert DECISION_POINT_OVERRIDDEN == "DecisionPointOverridden"

    def test_event_types_frozenset(self) -> None:
        assert isinstance(DECISION_POINT_EVENT_TYPES, frozenset)
        assert DECISION_POINT_EVENT_TYPES == frozenset({
            "DecisionPointOpened",
            "DecisionPointWidened",
            "DecisionPointDiscussing",
            "DecisionPointResolved",
            "DecisionPointOverridden",
        })
        assert len(DECISION_POINT_EVENT_TYPES) == 5

    def test_schema_version(self) -> None:
        assert DECISIONPOINT_SCHEMA_VERSION == "3.0.0"

    def test_event_to_payload_contains_all_five(self) -> None:
        assert DECISION_POINT_OPENED in _EVENT_TO_PAYLOAD
        assert DECISION_POINT_WIDENED in _EVENT_TO_PAYLOAD
        assert DECISION_POINT_DISCUSSING in _EVENT_TO_PAYLOAD
        assert DECISION_POINT_RESOLVED in _EVENT_TO_PAYLOAD
        assert DECISION_POINT_OVERRIDDEN in _EVENT_TO_PAYLOAD
        assert len(_EVENT_TO_PAYLOAD) == 5


# ── Enum tests (FR-001) ─────────────────────────────────────────────────────


class TestEnums:
    def test_decision_point_state_members(self) -> None:
        assert DecisionPointState.OPEN.value == "open"
        assert DecisionPointState.WIDENED.value == "widened"
        assert DecisionPointState.DISCUSSING.value == "discussing"
        assert DecisionPointState.RESOLVED.value == "resolved"
        assert DecisionPointState.OVERRIDDEN.value == "overridden"
        assert len(DecisionPointState) == 5

    def test_decision_point_state_includes_widened(self) -> None:
        assert DecisionPointState.WIDENED in DecisionPointState
        assert DecisionPointState.WIDENED.value == "widened"

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


def _valid_adr_payload_dict() -> dict:
    """Return a valid ADR-style payload dict (origin_surface=adr)."""
    return {
        "origin_surface": "adr",
        "decision_point_id": "dp-001",
        "mission_id": "m-001",
        "run_id": "run-001",
        "mission_slug": "mission-x",
        "mission_type": "software-dev",
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


def _valid_payload_dict() -> dict:
    """Backward-compat alias: return valid ADR-style payload dict without origin_surface.

    Used by tests that don't need to specify origin_surface (factories default to ADR).
    """
    d = _valid_adr_payload_dict()
    d.pop("origin_surface")
    return d


def _valid_interview_opened_dict() -> dict:
    """Return a valid interview-origin Opened payload dict."""
    return {
        "origin_surface": "planning_interview",
        "decision_point_id": "dp-001",
        "mission_id": "m-001",
        "run_id": "run-001",
        "mission_slug": "mission-x",
        "mission_type": "software-dev",
        "phase": "P1",
        "origin_flow": "charter",
        "question": "Which approach should we use?",
        "options": ("Option A", "Option B"),
        "input_key": "approach_choice",
        "step_id": "step-001",
        "actor_id": "human-1",
        "actor_type": "human",
        "state_entered_at": _NOW.isoformat(),
        "recorded_at": _NOW.isoformat(),
    }


def _valid_widened_dict() -> dict:
    """Return a valid DecisionPointWidened payload dict."""
    return {
        "origin_surface": "planning_interview",
        "decision_point_id": "dp-001",
        "mission_id": "m-001",
        "run_id": "run-001",
        "mission_slug": "mission-x",
        "mission_type": "software-dev",
        "channel": "slack",
        "teamspace_ref": {"teamspace_id": "ts-001"},
        "default_channel_ref": {"channel_id": "ch-001"},
        "thread_ref": {"channel_id": "ch-001", "thread_ts": "12345.67890"},
        "invited_participants": [],
        "widened_by": "participant-001",
        "widened_at": _NOW.isoformat(),
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
        assert payload.mission_slug == "mission-x"
        assert payload.mission_type == "software-dev"
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
        "mission_slug",
        "mission_type",
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
        data = _valid_adr_payload_dict()
        del data[missing_field]
        with pytest.raises(ValidationError):
            DecisionPointOpenedPayload.model_validate(data)

    def test_empty_alternatives_raises(self) -> None:
        data = _valid_adr_payload_dict()
        data["alternatives_considered"] = ()
        with pytest.raises(ValidationError):
            DecisionPointOpenedPayload.model_validate(data)

    def test_empty_evidence_refs_raises(self) -> None:
        data = _valid_adr_payload_dict()
        data["evidence_refs"] = ()
        with pytest.raises(ValidationError):
            DecisionPointOpenedPayload.model_validate(data)

    def test_empty_string_fields_raise(self) -> None:
        for field in ["decision_point_id", "mission_id", "run_id", "mission_slug",
                       "mission_type",
                       "phase", "actor_id", "rationale"]:
            data = _valid_adr_payload_dict()
            data[field] = ""
            with pytest.raises(ValidationError):
                DecisionPointOpenedPayload.model_validate(data)

    def test_legacy_feature_slug_field_is_rejected(self) -> None:
        data = _valid_adr_payload_dict()
        data["feature_slug"] = "legacy-feature"
        with pytest.raises(ValidationError):
            DecisionPointOpenedPayload.model_validate(data)

    def test_invalid_actor_type_raises(self) -> None:
        data = _valid_adr_payload_dict()
        data["actor_type"] = "robot"
        with pytest.raises(ValidationError):
            DecisionPointOpenedPayload.model_validate(data)

    def test_invalid_authority_role_raises(self) -> None:
        data = _valid_adr_payload_dict()
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


# ── V1: Opened discriminated union ───────────────────────────────────────────


class TestOpenedDiscriminatedUnion:
    def test_adr_shape_validates_to_adr_variant(self) -> None:
        payload = DecisionPointOpenedPayload.model_validate(_valid_adr_payload_dict())
        assert isinstance(payload, DecisionPointOpenedAdrPayload)
        assert payload.origin_surface == OriginSurface.ADR
        assert payload.rationale == "This is the best option"

    def test_interview_shape_validates_to_interview_variant(self) -> None:
        payload = DecisionPointOpenedPayload.model_validate(_valid_interview_opened_dict())
        assert isinstance(payload, DecisionPointOpenedInterviewPayload)
        assert payload.origin_surface == OriginSurface.PLANNING_INTERVIEW
        assert payload.question == "Which approach should we use?"
        assert payload.origin_flow == OriginFlow.CHARTER
        assert payload.input_key == "approach_choice"
        assert payload.step_id == "step-001"
        assert payload.options == ("Option A", "Option B")

    def test_adr_direct_construction_succeeds(self) -> None:
        """DecisionPointOpenedAdrPayload can be constructed directly."""
        payload = DecisionPointOpenedAdrPayload.model_validate(_valid_adr_payload_dict())
        assert payload.origin_surface == OriginSurface.ADR

    def test_interview_direct_construction_succeeds(self) -> None:
        """DecisionPointOpenedInterviewPayload can be constructed directly."""
        payload = DecisionPointOpenedInterviewPayload.model_validate(
            _valid_interview_opened_dict()
        )
        assert payload.origin_surface == OriginSurface.PLANNING_INTERVIEW

    def test_adr_variant_rejects_interview_origin_surface(self) -> None:
        """ADR variant rejects planning_interview origin_surface."""
        data = _valid_adr_payload_dict()
        data["origin_surface"] = "planning_interview"
        with pytest.raises(ValidationError):
            DecisionPointOpenedAdrPayload.model_validate(data)

    def test_interview_variant_missing_question_fails(self) -> None:
        data = _valid_interview_opened_dict()
        del data["question"]
        with pytest.raises(ValidationError):
            DecisionPointOpenedInterviewPayload.model_validate(data)

    def test_interview_variant_missing_origin_flow_fails(self) -> None:
        data = _valid_interview_opened_dict()
        del data["origin_flow"]
        with pytest.raises(ValidationError):
            DecisionPointOpenedInterviewPayload.model_validate(data)

    def test_interview_variant_empty_options_ok(self) -> None:
        """options may be empty tuple for free-form interview questions."""
        data = _valid_interview_opened_dict()
        data["options"] = []
        payload = DecisionPointOpenedInterviewPayload.model_validate(data)
        assert payload.options == ()

    def test_adr_variant_has_no_interview_fields(self) -> None:
        payload = DecisionPointOpenedAdrPayload.model_validate(_valid_adr_payload_dict())
        assert not hasattr(payload, "question")
        assert not hasattr(payload, "options")
        assert not hasattr(payload, "origin_flow")

    def test_interview_variant_has_no_adr_fields(self) -> None:
        payload = DecisionPointOpenedInterviewPayload.model_validate(
            _valid_interview_opened_dict()
        )
        assert not hasattr(payload, "rationale")
        assert not hasattr(payload, "alternatives_considered")
        assert not hasattr(payload, "authority_role")


# ── V1: Widened payload ──────────────────────────────────────────────────────


class TestWidenedPayload:
    def test_valid_widened_construction(self) -> None:
        payload = DecisionPointWidenedPayload.model_validate(_valid_widened_dict())
        assert payload.origin_surface == OriginSurface.PLANNING_INTERVIEW
        assert payload.channel == WideningChannel.SLACK
        assert payload.widened_by == "participant-001"
        assert payload.invited_participants == ()

    def test_missing_thread_ref_fails(self) -> None:
        data = _valid_widened_dict()
        del data["thread_ref"]
        with pytest.raises(ValidationError):
            DecisionPointWidenedPayload.model_validate(data)

    def test_wrong_channel_literal_fails(self) -> None:
        data = _valid_widened_dict()
        data["channel"] = "teams"
        with pytest.raises(ValidationError):
            DecisionPointWidenedPayload.model_validate(data)

    def test_wrong_origin_surface_literal_fails(self) -> None:
        data = _valid_widened_dict()
        data["origin_surface"] = "adr"
        with pytest.raises(ValidationError):
            DecisionPointWidenedPayload.model_validate(data)

    def test_missing_widened_by_fails(self) -> None:
        data = _valid_widened_dict()
        del data["widened_by"]
        with pytest.raises(ValidationError):
            DecisionPointWidenedPayload.model_validate(data)

    def test_empty_widened_by_fails(self) -> None:
        data = _valid_widened_dict()
        data["widened_by"] = ""
        with pytest.raises(ValidationError):
            DecisionPointWidenedPayload.model_validate(data)

    def test_missing_teamspace_ref_fails(self) -> None:
        data = _valid_widened_dict()
        del data["teamspace_ref"]
        with pytest.raises(ValidationError):
            DecisionPointWidenedPayload.model_validate(data)


# ── V1: Discussing discriminated union ───────────────────────────────────────


class TestDiscussingDiscriminatedUnion:
    def test_adr_shape_validates_to_adr_variant(self) -> None:
        payload = DecisionPointDiscussingPayload.model_validate(_valid_adr_payload_dict())
        assert isinstance(payload, DecisionPointDiscussingAdrPayload)
        assert payload.origin_surface == OriginSurface.ADR
        assert payload.rationale == "This is the best option"

    def test_interview_shape_validates_to_interview_variant(self) -> None:
        data = {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-001",
            "mission_id": "m-001",
            "run_id": "run-001",
            "mission_slug": "mission-x",
            "mission_type": "software-dev",
            "snapshot_kind": "participant_contribution",
            "actor_id": "human-1",
            "actor_type": "human",
            "state_entered_at": _NOW.isoformat(),
            "recorded_at": _NOW.isoformat(),
        }
        payload = DecisionPointDiscussingPayload.model_validate(data)
        assert isinstance(payload, DecisionPointDiscussingInterviewPayload)
        assert payload.origin_surface == OriginSurface.PLANNING_INTERVIEW
        assert payload.snapshot_kind == DiscussingSnapshotKind.PARTICIPANT_CONTRIBUTION
        assert payload.contributions == ()

    def test_interview_missing_snapshot_kind_fails(self) -> None:
        data = {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-001",
            "mission_id": "m-001",
            "run_id": "run-001",
            "mission_slug": "mission-x",
            "mission_type": "software-dev",
            "actor_id": "human-1",
            "actor_type": "human",
            "state_entered_at": _NOW.isoformat(),
            "recorded_at": _NOW.isoformat(),
        }
        with pytest.raises(ValidationError):
            DecisionPointDiscussingInterviewPayload.model_validate(data)

    def test_interview_has_no_adr_fields(self) -> None:
        data = {
            "origin_surface": "planning_interview",
            "decision_point_id": "dp-001",
            "mission_id": "m-001",
            "run_id": "run-001",
            "mission_slug": "mission-x",
            "mission_type": "software-dev",
            "snapshot_kind": "digest",
            "actor_id": "human-1",
            "actor_type": "human",
            "state_entered_at": _NOW.isoformat(),
            "recorded_at": _NOW.isoformat(),
        }
        payload = DecisionPointDiscussingInterviewPayload.model_validate(data)
        assert not hasattr(payload, "rationale")
        assert not hasattr(payload, "authority_role")


# ── V1: Resolved discriminated union ─────────────────────────────────────────


def _valid_resolved_interview_base() -> dict:
    """Base dict for interview-origin Resolved payloads."""
    return {
        "origin_surface": "planning_interview",
        "decision_point_id": "dp-001",
        "mission_id": "m-001",
        "run_id": "run-001",
        "mission_slug": "mission-x",
        "mission_type": "software-dev",
        "resolved_by": "participant-001",
        "state_entered_at": _NOW.isoformat(),
        "recorded_at": _NOW.isoformat(),
    }


class TestResolvedDiscriminatedUnion:
    def test_adr_shape_validates_to_adr_variant(self) -> None:
        payload = DecisionPointResolvedPayload.model_validate(_valid_adr_payload_dict())
        assert isinstance(payload, DecisionPointResolvedAdrPayload)
        assert payload.origin_surface == OriginSurface.ADR

    def test_interview_resolved_outcome_succeeds(self) -> None:
        data = {**_valid_resolved_interview_base(),
                "terminal_outcome": "resolved",
                "final_answer": "Option A"}
        payload = DecisionPointResolvedPayload.model_validate(data)
        assert isinstance(payload, DecisionPointResolvedInterviewPayload)
        assert payload.terminal_outcome == TerminalOutcome.RESOLVED
        assert payload.final_answer == "Option A"
        assert payload.other_answer is False

    def test_interview_resolved_other_answer_succeeds(self) -> None:
        data = {**_valid_resolved_interview_base(),
                "terminal_outcome": "resolved",
                "final_answer": "Custom free-form answer",
                "other_answer": True}
        payload = DecisionPointResolvedInterviewPayload.model_validate(data)
        assert payload.other_answer is True
        assert payload.final_answer == "Custom free-form answer"

    def test_interview_deferred_outcome_succeeds(self) -> None:
        data = {**_valid_resolved_interview_base(),
                "terminal_outcome": "deferred",
                "rationale": "Need more info before deciding"}
        payload = DecisionPointResolvedInterviewPayload.model_validate(data)
        assert payload.terminal_outcome == TerminalOutcome.DEFERRED
        assert payload.final_answer is None
        assert payload.rationale == "Need more info before deciding"

    def test_interview_canceled_outcome_succeeds(self) -> None:
        data = {**_valid_resolved_interview_base(),
                "terminal_outcome": "canceled",
                "rationale": "Decision no longer relevant"}
        payload = DecisionPointResolvedInterviewPayload.model_validate(data)
        assert payload.terminal_outcome == TerminalOutcome.CANCELED
        assert payload.final_answer is None

    # Cross-field validator (exhaustive)

    def test_resolved_without_final_answer_fails(self) -> None:
        """terminal=resolved requires final_answer."""
        data = {**_valid_resolved_interview_base(), "terminal_outcome": "resolved"}
        with pytest.raises(ValidationError, match="final_answer is required"):
            DecisionPointResolvedInterviewPayload.model_validate(data)

    def test_resolved_with_empty_final_answer_fails(self) -> None:
        """terminal=resolved with empty string final_answer fails."""
        data = {**_valid_resolved_interview_base(),
                "terminal_outcome": "resolved",
                "final_answer": ""}
        with pytest.raises(ValidationError, match="final_answer is required"):
            DecisionPointResolvedInterviewPayload.model_validate(data)

    def test_deferred_with_final_answer_fails(self) -> None:
        """terminal=deferred must NOT have final_answer."""
        data = {**_valid_resolved_interview_base(),
                "terminal_outcome": "deferred",
                "final_answer": "some answer",
                "rationale": "reason"}
        with pytest.raises(ValidationError, match="final_answer must be absent"):
            DecisionPointResolvedInterviewPayload.model_validate(data)

    def test_canceled_without_rationale_fails(self) -> None:
        """terminal=canceled requires rationale."""
        data = {**_valid_resolved_interview_base(), "terminal_outcome": "canceled"}
        with pytest.raises(ValidationError, match="rationale is required"):
            DecisionPointResolvedInterviewPayload.model_validate(data)

    def test_deferred_with_other_answer_true_fails(self) -> None:
        """terminal=deferred must have other_answer=False."""
        data = {**_valid_resolved_interview_base(),
                "terminal_outcome": "deferred",
                "rationale": "reason",
                "other_answer": True}
        with pytest.raises(ValidationError, match="other_answer must be False"):
            DecisionPointResolvedInterviewPayload.model_validate(data)

    def test_canceled_with_other_answer_true_fails(self) -> None:
        """terminal=canceled must have other_answer=False."""
        data = {**_valid_resolved_interview_base(),
                "terminal_outcome": "canceled",
                "rationale": "reason",
                "other_answer": True}
        with pytest.raises(ValidationError, match="other_answer must be False"):
            DecisionPointResolvedInterviewPayload.model_validate(data)


# ── V1: Overridden with optional origin_surface ───────────────────────────────


class TestOverriddenPayload:
    def test_valid_without_origin_surface(self) -> None:
        """3.x payloads without origin_surface still validate."""
        payload = DecisionPointOverriddenPayload.model_validate(_valid_adr_payload_dict())
        # origin_surface comes from the ADR dict; test without it too
        data = dict(_valid_adr_payload_dict())
        data.pop("origin_surface")
        payload = DecisionPointOverriddenPayload.model_validate(data)
        assert payload.origin_surface is None

    def test_valid_with_adr_origin_surface(self) -> None:
        payload = DecisionPointOverriddenPayload.model_validate(_valid_adr_payload_dict())
        assert payload.origin_surface == OriginSurface.ADR

    def test_valid_with_planning_interview_origin_surface(self) -> None:
        data = dict(_valid_adr_payload_dict())
        data["origin_surface"] = "planning_interview"
        payload = DecisionPointOverriddenPayload.model_validate(data)
        assert payload.origin_surface == OriginSurface.PLANNING_INTERVIEW

    def test_invalid_origin_surface_rejected(self) -> None:
        data = dict(_valid_adr_payload_dict())
        data["origin_surface"] = "invalid_value"
        with pytest.raises(ValidationError):
            DecisionPointOverriddenPayload.model_validate(data)
