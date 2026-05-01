"""Tests for the structured ValidationError shape (WP02 / NFR-006)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.status import TransitionError
from spec_kitty_events.validation_errors import (
    ValidationError,
    ValidationErrorCode,
    lifecycle_error_to_validation_error,
    transition_error_to_validation_error,
)


# ---------------------------------------------------------------------------
# Shape tests
# ---------------------------------------------------------------------------


def test_validation_error_minimum_fields() -> None:
    err = ValidationError(code=ValidationErrorCode.UNKNOWN_LANE, message="x")
    assert err.code is ValidationErrorCode.UNKNOWN_LANE
    assert err.message == "x"
    assert err.path == []
    assert err.details == {}


def test_validation_error_full_fields() -> None:
    err = ValidationError(
        code=ValidationErrorCode.FORBIDDEN_KEY,
        message="forbidden key found",
        path=["payload", "tags", 2, "feature_slug"],
        details={"key": "feature_slug"},
    )
    assert err.code is ValidationErrorCode.FORBIDDEN_KEY
    assert err.message == "forbidden key found"
    assert err.path == ["payload", "tags", 2, "feature_slug"]
    assert err.details == {"key": "feature_slug"}


def test_validation_error_rejects_extra_fields() -> None:
    with pytest.raises(PydanticValidationError):
        ValidationError(  # type: ignore[call-arg]
            code=ValidationErrorCode.UNKNOWN_LANE,
            message="x",
            extra=1,
        )


def test_validation_error_rejects_unknown_code() -> None:
    with pytest.raises(PydanticValidationError):
        ValidationError(code="NOT_A_CODE", message="x")  # type: ignore[arg-type]


def test_validation_error_is_frozen() -> None:
    err = ValidationError(code=ValidationErrorCode.UNKNOWN_LANE, message="x")
    with pytest.raises(Exception):
        err.message = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Closed-enum and determinism
# ---------------------------------------------------------------------------


def test_validation_error_codes_are_closed_set() -> None:
    expected = {
        "FORBIDDEN_KEY",
        "UNKNOWN_LANE",
        "PAYLOAD_SCHEMA_FAIL",
        "ENVELOPE_SHAPE_INVALID",
        "RAW_HISTORICAL_ROW",
    }
    actual = {member.value for member in ValidationErrorCode}
    assert actual == expected


def test_determinism() -> None:
    a = ValidationError(
        code=ValidationErrorCode.UNKNOWN_LANE,
        message="x",
        details={"a": 1, "b": 2},
    )
    b = ValidationError(
        code=ValidationErrorCode.UNKNOWN_LANE,
        message="x",
        details={"a": 1, "b": 2},
    )
    assert a == b
    assert a.model_dump_json() == b.model_dump_json()
    # Byte-identical serialization across two independent constructions.
    assert a.model_dump_json().encode("utf-8") == b.model_dump_json().encode("utf-8")


# ---------------------------------------------------------------------------
# Helper: transition_error_to_validation_error
# ---------------------------------------------------------------------------


def test_transition_error_to_validation_error_has_required_fields() -> None:
    err = TransitionError(("Transition planned -> done is not allowed",))
    ve = transition_error_to_validation_error(err)
    assert isinstance(ve, ValidationError)
    assert ve.code is ValidationErrorCode.UNKNOWN_LANE
    assert "Transition planned -> done is not allowed" in ve.message
    assert ve.path == []
    assert ve.details == {
        "violations": ["Transition planned -> done is not allowed"],
    }


def test_transition_error_to_validation_error_preserves_multiple_violations() -> None:
    err = TransitionError(("v1", "v2", "v3"))
    ve = transition_error_to_validation_error(err)
    assert ve.details["violations"] == ["v1", "v2", "v3"]


def test_transition_error_to_validation_error_rejects_empty() -> None:
    err = TransitionError(())
    with pytest.raises(ValueError, match="closed ValidationErrorCode"):
        transition_error_to_validation_error(err)


# ---------------------------------------------------------------------------
# Helper: lifecycle_error_to_validation_error
# ---------------------------------------------------------------------------


class _PretendValidationError(Exception):
    """Stub envelope-shape exception (its class name contains 'Validation')."""


def test_lifecycle_error_to_validation_error_envelope_shape() -> None:
    err = _PretendValidationError("missing required field 'lane'")
    ve = lifecycle_error_to_validation_error(err)
    assert ve.code is ValidationErrorCode.ENVELOPE_SHAPE_INVALID
    assert ve.message == "missing required field 'lane'"
    assert ve.details == {"errors": ["missing required field 'lane'"]}


def test_lifecycle_error_to_validation_error_envelope_shape_via_message() -> None:
    err = RuntimeError("envelope is missing required wrapper")
    ve = lifecycle_error_to_validation_error(err)
    assert ve.code is ValidationErrorCode.ENVELOPE_SHAPE_INVALID


def test_lifecycle_error_to_validation_error_raw_historical_row() -> None:
    err = RuntimeError("input looks like a historical local status row")
    ve = lifecycle_error_to_validation_error(err)
    assert ve.code is ValidationErrorCode.RAW_HISTORICAL_ROW
    assert ve.details == {"detected_shape": "local_status_row"}


def test_lifecycle_error_to_validation_error_unmapped_raises() -> None:
    err = RuntimeError("totally unrelated failure")
    with pytest.raises(ValueError, match="closed ValidationErrorCode"):
        lifecycle_error_to_validation_error(err)


# ---------------------------------------------------------------------------
# JSON serialization sanity
# ---------------------------------------------------------------------------


def test_validation_error_serializes_code_as_string() -> None:
    err = ValidationError(code=ValidationErrorCode.FORBIDDEN_KEY, message="x")
    payload = err.model_dump()
    assert payload["code"] == "FORBIDDEN_KEY"
    json_payload = err.model_dump_json()
    assert '"code":"FORBIDDEN_KEY"' in json_payload
