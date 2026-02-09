"""Unit tests for gate payload models and conclusion mapping."""

import logging
import uuid
from datetime import datetime

import pydantic
import pytest
from ulid import ULID

from spec_kitty_events import (
    Event,
    GateFailedPayload,
    GatePassedPayload,
    GatePayloadBase,
    UnknownConclusionError,
    map_check_run_conclusion,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_PAYLOAD_DATA: dict = {
    "gate_name": "ci/build",
    "gate_type": "ci",
    "conclusion": "success",
    "external_provider": "github",
    "check_run_id": 123456,
    "check_run_url": "https://github.com/org/repo/runs/123456",
    "delivery_id": "delivery-abc-123",
}

VALID_FAILED_PAYLOAD_DATA: dict = {**VALID_PAYLOAD_DATA, "conclusion": "failure"}


# ---------------------------------------------------------------------------
# Payload model construction
# ---------------------------------------------------------------------------


class TestGatePassedPayloadConstruction:
    """Test GatePassedPayload valid construction and field access."""

    def test_valid_construction(self) -> None:
        payload = GatePassedPayload(**VALID_PAYLOAD_DATA)
        assert payload.gate_name == "ci/build"
        assert payload.gate_type == "ci"
        assert payload.conclusion == "success"
        assert payload.external_provider == "github"
        assert payload.check_run_id == 123456
        assert str(payload.check_run_url) == "https://github.com/org/repo/runs/123456"
        assert payload.delivery_id == "delivery-abc-123"
        assert payload.pr_number is None

    def test_with_pr_number(self) -> None:
        payload = GatePassedPayload(**VALID_PAYLOAD_DATA, pr_number=42)
        assert payload.pr_number == 42

    def test_pr_number_none_is_valid(self) -> None:
        payload = GatePassedPayload(**VALID_PAYLOAD_DATA, pr_number=None)
        assert payload.pr_number is None


class TestGateFailedPayloadConstruction:
    """Test GateFailedPayload valid construction."""

    def test_valid_construction(self) -> None:
        payload = GateFailedPayload(**VALID_FAILED_PAYLOAD_DATA)
        assert payload.conclusion == "failure"
        assert payload.gate_name == "ci/build"


class TestConclusionDiscrimination:
    """Verify each payload class enforces its allowed conclusion values."""

    @pytest.mark.parametrize(
        "invalid_conclusion",
        ["failure", "timed_out", "cancelled", "action_required", "neutral", "skipped", "stale"],
    )
    def test_gate_passed_rejects_non_success_conclusions(
        self,
        invalid_conclusion: str,
    ) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "conclusion": invalid_conclusion})

    @pytest.mark.parametrize(
        "invalid_conclusion",
        ["success", "neutral", "skipped", "stale"],
    )
    def test_gate_failed_rejects_non_failure_conclusions(
        self,
        invalid_conclusion: str,
    ) -> None:
        with pytest.raises(pydantic.ValidationError):
            GateFailedPayload(**{**VALID_PAYLOAD_DATA, "conclusion": invalid_conclusion})


# ---------------------------------------------------------------------------
# Required field enforcement
# ---------------------------------------------------------------------------


class TestRequiredFieldEnforcement:
    """Verify missing required fields raise ValidationError."""

    @pytest.mark.parametrize("omitted_field", [
        "gate_name",
        "gate_type",
        "conclusion",
        "external_provider",
        "check_run_id",
        "check_run_url",
        "delivery_id",
    ])
    def test_missing_required_field_raises(self, omitted_field: str) -> None:
        data = {**VALID_PAYLOAD_DATA}
        del data[omitted_field]
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**data)

    @pytest.mark.parametrize("omitted_field", [
        "gate_name",
        "gate_type",
        "conclusion",
        "external_provider",
        "check_run_id",
        "check_run_url",
        "delivery_id",
    ])
    def test_missing_required_field_raises_failed_payload(self, omitted_field: str) -> None:
        data = {**VALID_PAYLOAD_DATA}
        del data[omitted_field]
        with pytest.raises(pydantic.ValidationError):
            GateFailedPayload(**data)


# ---------------------------------------------------------------------------
# Field constraint validation
# ---------------------------------------------------------------------------


class TestFieldConstraints:
    """Test Pydantic field constraints reject invalid data."""

    def test_gate_name_empty_rejects(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "gate_name": ""})

    def test_conclusion_empty_rejects(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "conclusion": ""})

    def test_delivery_id_empty_rejects(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "delivery_id": ""})

    def test_gate_type_wrong_literal_rejects(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "gate_type": "not_ci"})

    def test_external_provider_wrong_literal_rejects(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "external_provider": "gitlab"})

    def test_check_run_id_zero_rejects(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "check_run_id": 0})

    def test_check_run_id_negative_rejects(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "check_run_id": -1})

    @pytest.mark.parametrize("invalid_check_run_id", ["123", True, 12.0])
    def test_check_run_id_non_strict_int_rejects(self, invalid_check_run_id: object) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "check_run_id": invalid_check_run_id})

    def test_check_run_url_invalid_rejects(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "check_run_url": "not-a-url"})

    def test_pr_number_zero_rejects(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "pr_number": 0})

    def test_pr_number_negative_rejects(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "pr_number": -1})

    @pytest.mark.parametrize("invalid_pr_number", ["42", True, 42.0])
    def test_pr_number_non_strict_int_rejects(self, invalid_pr_number: object) -> None:
        with pytest.raises(pydantic.ValidationError):
            GatePassedPayload(**{**VALID_PAYLOAD_DATA, "pr_number": invalid_pr_number})


# ---------------------------------------------------------------------------
# Frozen immutability
# ---------------------------------------------------------------------------


class TestFrozenImmutability:
    """Verify payload models are immutable after construction."""

    def test_gate_passed_is_frozen(self) -> None:
        payload = GatePassedPayload(**VALID_PAYLOAD_DATA)
        with pytest.raises(pydantic.ValidationError):
            payload.gate_name = "changed"  # type: ignore[misc]

    def test_gate_failed_is_frozen(self) -> None:
        payload = GateFailedPayload(**VALID_FAILED_PAYLOAD_DATA)
        with pytest.raises(pydantic.ValidationError):
            payload.gate_name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


class TestSerializationRoundTrip:
    """Verify model_dump/model_validate round-trip."""

    def test_gate_passed_roundtrip(self) -> None:
        payload = GatePassedPayload(**VALID_PAYLOAD_DATA, pr_number=42)
        dumped = payload.model_dump()
        assert isinstance(dumped, dict)
        assert isinstance(dumped["check_run_url"], str)
        reconstructed = GatePassedPayload.model_validate(dumped)
        assert reconstructed == payload

    def test_gate_failed_roundtrip(self) -> None:
        payload = GateFailedPayload(**VALID_FAILED_PAYLOAD_DATA)
        dumped = payload.model_dump()
        reconstructed = GateFailedPayload.model_validate(dumped)
        assert reconstructed == payload

    def test_roundtrip_without_pr_number(self) -> None:
        payload = GatePassedPayload(**VALID_PAYLOAD_DATA)
        dumped = payload.model_dump()
        assert dumped.get("pr_number") is None
        reconstructed = GatePassedPayload.model_validate(dumped)
        assert reconstructed.pr_number is None


# ---------------------------------------------------------------------------
# Type discrimination
# ---------------------------------------------------------------------------


class TestTypeDiscrimination:
    """Verify isinstance checks for type narrowing."""

    def test_passed_is_base(self) -> None:
        payload = GatePassedPayload(**VALID_PAYLOAD_DATA)
        assert isinstance(payload, GatePayloadBase)

    def test_failed_is_base(self) -> None:
        payload = GateFailedPayload(**VALID_FAILED_PAYLOAD_DATA)
        assert isinstance(payload, GatePayloadBase)

    def test_passed_is_not_failed(self) -> None:
        payload = GatePassedPayload(**VALID_PAYLOAD_DATA)
        assert isinstance(payload, GatePassedPayload)
        assert not isinstance(payload, GateFailedPayload)

    def test_failed_is_not_passed(self) -> None:
        payload = GateFailedPayload(**VALID_FAILED_PAYLOAD_DATA)
        assert isinstance(payload, GateFailedPayload)
        assert not isinstance(payload, GatePassedPayload)


# ---------------------------------------------------------------------------
# Integration with generic Event
# ---------------------------------------------------------------------------


class TestEventIntegration:
    """Verify payload model_dump works as Event.payload."""

    def test_gate_payload_as_event_payload(self) -> None:
        gate_payload = GatePassedPayload(**VALID_PAYLOAD_DATA)
        event = Event(
            event_id="01HXYZ" + "A" * 20,
            event_type="GatePassed",
            aggregate_id="project-1",
            payload=gate_payload.model_dump(),
            timestamp=datetime.now(),
            node_id="worker-1",
            lamport_clock=1,
            project_uuid=uuid.uuid4(),
            correlation_id=str(ULID()),
        )
        assert event.payload["gate_name"] == "ci/build"
        assert event.event_type == "GatePassed"
        assert isinstance(event.payload["check_run_url"], str)


# ---------------------------------------------------------------------------
# Conclusion mapping
# ---------------------------------------------------------------------------


class TestMapCheckRunConclusion:
    """Test map_check_run_conclusion for all known values and edge cases."""

    @pytest.mark.parametrize("conclusion,expected", [
        ("success", "GatePassed"),
        ("failure", "GateFailed"),
        ("timed_out", "GateFailed"),
        ("cancelled", "GateFailed"),
        ("action_required", "GateFailed"),
        ("neutral", None),
        ("skipped", None),
        ("stale", None),
    ])
    def test_known_conclusions(self, conclusion: str, expected: str | None) -> None:
        result = map_check_run_conclusion(conclusion)
        assert result == expected

    def test_unknown_conclusion_raises(self) -> None:
        with pytest.raises(UnknownConclusionError) as exc_info:
            map_check_run_conclusion("bogus_value")
        assert exc_info.value.conclusion == "bogus_value"
        assert "bogus_value" in str(exc_info.value)

    @pytest.mark.parametrize("bad_case", ["SUCCESS", "Failure", "TIMED_OUT", "Neutral"])
    def test_rejects_non_lowercase(self, bad_case: str) -> None:
        with pytest.raises(UnknownConclusionError):
            map_check_run_conclusion(bad_case)

    def test_empty_string_raises(self) -> None:
        with pytest.raises(UnknownConclusionError):
            map_check_run_conclusion("")

    @pytest.mark.parametrize("conclusion", ["neutral", "skipped", "stale"])
    def test_on_ignored_callback_invoked(self, conclusion: str) -> None:
        calls: list[tuple[str, str]] = []

        def callback(c: str, reason: str) -> None:
            calls.append((c, reason))

        result = map_check_run_conclusion(conclusion, on_ignored=callback)
        assert result is None
        assert len(calls) == 1
        assert calls[0] == (conclusion, "non_blocking")

    @pytest.mark.parametrize("conclusion", ["success", "failure", "timed_out"])
    def test_no_callback_for_blocking_conclusions(self, conclusion: str) -> None:
        calls: list[tuple[str, str]] = []
        result = map_check_run_conclusion(
            conclusion, on_ignored=lambda c, r: calls.append((c, r))
        )
        assert result is not None
        assert len(calls) == 0

    def test_logs_ignored_conclusion(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="spec_kitty_events.gates"):
            map_check_run_conclusion("neutral")
        assert "neutral" in caplog.text

    def test_no_callback_default_ok(self) -> None:
        result = map_check_run_conclusion("skipped")
        assert result is None

    def test_unknown_conclusion_error_attributes(self) -> None:
        err = UnknownConclusionError("weird_value")
        assert err.conclusion == "weird_value"
        assert "weird_value" in str(err)
        assert "Known values" in str(err)
