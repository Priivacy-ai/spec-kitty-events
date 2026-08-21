"""Unit tests for the two ValidationErrorCode members added by F1-T1.

F1 (docs contract-freeze draft, section 3.3) requires exactly two new closed
error codes: UNKNOWN_EVENT_TYPE and UNSUPPORTED_SCHEMA_VERSION. These give
consumers a machine-checkable way to route on compatibility classes without
string-matching exception text (today SaaS matches "Unknown event type:").
"""

from __future__ import annotations

from spec_kitty_events.validation_errors import ValidationError, ValidationErrorCode


def test_unknown_event_type_code_exists() -> None:
    assert ValidationErrorCode.UNKNOWN_EVENT_TYPE == "UNKNOWN_EVENT_TYPE"


def test_unsupported_schema_version_code_exists() -> None:
    assert ValidationErrorCode.UNSUPPORTED_SCHEMA_VERSION == "UNSUPPORTED_SCHEMA_VERSION"


def test_closed_enum_has_exactly_seven_members() -> None:
    # 5 pre-existing (FORBIDDEN_KEY, UNKNOWN_LANE, PAYLOAD_SCHEMA_FAIL,
    # ENVELOPE_SHAPE_INVALID, RAW_HISTORICAL_ROW) + 2 new members.
    assert len(ValidationErrorCode) == 7


def test_unknown_event_type_error_constructs() -> None:
    err = ValidationError(
        code=ValidationErrorCode.UNKNOWN_EVENT_TYPE,
        message="unknown event type",
        path=[],
        details={"event_type": "Sparkle", "profile": "journal/v1"},
    )
    assert err.code is ValidationErrorCode.UNKNOWN_EVENT_TYPE
    assert err.details["event_type"] == "Sparkle"


def test_unsupported_schema_version_error_constructs() -> None:
    err = ValidationError(
        code=ValidationErrorCode.UNSUPPORTED_SCHEMA_VERSION,
        message="unsupported schema version",
        path=[],
        details={"found": "2.9.0", "required": "3.0.0"},
    )
    assert err.code is ValidationErrorCode.UNSUPPORTED_SCHEMA_VERSION
    assert err.details["required"] == "3.0.0"
