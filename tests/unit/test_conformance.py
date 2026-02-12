"""Tests for conformance validation API."""

import sys
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import patch
from uuid import uuid4

import pytest

from spec_kitty_events.conformance import (
    ConformanceResult,
    ModelViolation,
    SchemaViolation,
    validate_event,
)
from spec_kitty_events.status import Lane


def _make_ulid() -> str:
    """Generate a valid 26-character ULID-like string."""
    from ulid import ULID
    return str(ULID())


def _make_valid_status_transition() -> Dict[str, Any]:
    """Create a valid StatusTransitionPayload."""
    return {
        "feature_slug": "test",
        "wp_id": "WP01",
        "from_lane": "planned",
        "to_lane": "claimed",
        "actor": "test-agent",
        "execution_mode": "worktree",
    }


def _make_valid_gate_passed() -> Dict[str, Any]:
    """Create a valid GatePassedPayload."""
    return {
        "gate_name": "ci/build",
        "gate_type": "ci",
        "conclusion": "success",
        "external_provider": "github",
        "check_run_id": 12345,
        "check_run_url": "https://github.com/owner/repo/runs/12345",
        "delivery_id": "abc123",
    }


def _make_valid_gate_failed() -> Dict[str, Any]:
    """Create a valid GateFailedPayload."""
    return {
        "gate_name": "ci/build",
        "gate_type": "ci",
        "conclusion": "failure",
        "external_provider": "github",
        "check_run_id": 12345,
        "check_run_url": "https://github.com/owner/repo/runs/12345",
        "delivery_id": "abc123",
    }


def _make_valid_mission_started() -> Dict[str, Any]:
    """Create a valid MissionStartedPayload."""
    return {
        "mission_id": "mission-001",
        "mission_type": "software-dev",
        "initial_phase": "planning",
        "actor": "test-agent",
    }


def _make_valid_mission_completed() -> Dict[str, Any]:
    """Create a valid MissionCompletedPayload."""
    return {
        "mission_id": "mission-001",
        "mission_type": "software-dev",
        "final_phase": "done",
        "actor": "test-agent",
    }


def _make_valid_mission_cancelled() -> Dict[str, Any]:
    """Create a valid MissionCancelledPayload."""
    return {
        "mission_id": "mission-001",
        "reason": "Requirements changed",
        "actor": "test-agent",
    }


def _make_valid_phase_entered() -> Dict[str, Any]:
    """Create a valid PhaseEnteredPayload."""
    return {
        "mission_id": "mission-001",
        "phase_name": "implementation",
        "actor": "test-agent",
    }


def _make_valid_review_rollback() -> Dict[str, Any]:
    """Create a valid ReviewRollbackPayload."""
    return {
        "mission_id": "mission-001",
        "review_ref": "review-123",
        "target_phase": "implementation",
        "actor": "test-agent",
    }


def _make_valid_event() -> Dict[str, Any]:
    """Create a valid Event."""
    return {
        "event_id": _make_ulid(),
        "event_type": "TestEvent",
        "aggregate_id": "test-aggregate",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node_id": "test-node",
        "lamport_clock": 1,
        "project_uuid": str(uuid4()),
        "correlation_id": _make_ulid(),
    }


def test_validate_event_valid_status_transition() -> None:
    """Test validation of a valid StatusTransitionPayload."""
    payload = _make_valid_status_transition()
    result = validate_event("WPStatusChanged", payload)

    assert result.valid is True
    assert result.event_type == "WPStatusChanged"
    assert len(result.model_violations) == 0
    assert len(result.schema_violations) == 0


def test_validate_event_invalid_missing_field() -> None:
    """Test validation fails when required field is missing."""
    payload = _make_valid_status_transition()
    del payload["actor"]  # Remove required field

    result = validate_event("WPStatusChanged", payload)

    assert result.valid is False
    assert len(result.model_violations) > 0
    # Check that the violation mentions the missing field
    violation_fields = [v.field for v in result.model_violations]
    assert "actor" in violation_fields


def test_validate_event_invalid_enum_value() -> None:
    """Test validation fails for invalid enum value."""
    payload = _make_valid_status_transition()
    payload["to_lane"] = "invalid_lane"  # Invalid lane value

    result = validate_event("WPStatusChanged", payload)

    assert result.valid is False
    assert len(result.model_violations) > 0


def test_validate_event_business_rule_force_without_reason() -> None:
    """Test validation fails when force=True but no reason provided."""
    payload = _make_valid_status_transition()
    payload["force"] = True
    # No reason provided

    result = validate_event("WPStatusChanged", payload)

    assert result.valid is False
    assert len(result.model_violations) > 0
    # Check that violation mentions force/reason
    violation_messages = [v.message for v in result.model_violations]
    assert any("reason" in msg.lower() for msg in violation_messages)


def test_validate_event_unknown_type_raises() -> None:
    """Test that unknown event type raises ValueError."""
    payload = _make_valid_status_transition()

    with pytest.raises(ValueError, match="Unknown event type"):
        validate_event("UnknownEventType", payload)


def test_validate_event_strict_without_jsonschema() -> None:
    """Test that strict=True raises ImportError when jsonschema unavailable."""
    payload = _make_valid_status_transition()

    # Create a mock that raises ImportError when trying to import jsonschema
    import spec_kitty_events.conformance.validators as validators_module

    original_validate_with_schema = validators_module._validate_with_schema

    def mock_validate_with_schema(payload: Any, schema_name: str, strict: bool) -> Any:
        # Simulate jsonschema not being available
        if strict:
            raise ImportError(
                "jsonschema is required for strict conformance validation. "
                "Install with: pip install 'spec-kitty-events[conformance]'"
            )
        return ((), True)

    with patch.object(validators_module, "_validate_with_schema", mock_validate_with_schema):
        with pytest.raises(ImportError, match="jsonschema is required"):
            validate_event("WPStatusChanged", payload, strict=True)


def test_validate_event_nonstrict_skips_schema() -> None:
    """Test that strict=False skips schema validation when jsonschema unavailable."""
    payload = _make_valid_status_transition()

    # Create a mock that simulates jsonschema not being available
    import spec_kitty_events.conformance.validators as validators_module

    def mock_validate_with_schema(payload: Any, schema_name: str, strict: bool) -> Any:
        # Simulate jsonschema not being available, gracefully degrade
        return ((), True)

    with patch.object(validators_module, "_validate_with_schema", mock_validate_with_schema):
        result = validate_event("WPStatusChanged", payload, strict=False)

        # Should succeed with model validation only
        assert result.valid is True
        assert result.schema_check_skipped is True
        assert len(result.model_violations) == 0


@pytest.mark.parametrize(
    "event_type,payload_factory",
    [
        ("Event", _make_valid_event),
        ("WPStatusChanged", _make_valid_status_transition),
        ("GatePassed", _make_valid_gate_passed),
        ("GateFailed", _make_valid_gate_failed),
        ("MissionStarted", _make_valid_mission_started),
        ("MissionCompleted", _make_valid_mission_completed),
        ("MissionCancelled", _make_valid_mission_cancelled),
        ("PhaseEntered", _make_valid_phase_entered),
        ("ReviewRollback", _make_valid_review_rollback),
    ],
)
def test_validate_event_all_event_types(
    event_type: str,
    payload_factory: Any,
) -> None:
    """Test validation succeeds for all supported event types."""
    payload = payload_factory()
    result = validate_event(event_type, payload)

    assert result.valid is True, f"Validation failed for {event_type}: {result.model_violations}"
    assert result.event_type == event_type
    assert len(result.model_violations) == 0


def test_model_violation_structure() -> None:
    """Test that ModelViolation has correct structure."""
    payload = _make_valid_status_transition()
    del payload["actor"]

    result = validate_event("WPStatusChanged", payload)

    assert len(result.model_violations) > 0
    violation = result.model_violations[0]
    assert isinstance(violation, ModelViolation)
    assert hasattr(violation, "field")
    assert hasattr(violation, "message")
    assert hasattr(violation, "violation_type")
    assert hasattr(violation, "input_value")


def test_conformance_result_structure() -> None:
    """Test that ConformanceResult has correct structure."""
    payload = _make_valid_status_transition()
    result = validate_event("WPStatusChanged", payload)

    assert isinstance(result, ConformanceResult)
    assert hasattr(result, "valid")
    assert hasattr(result, "model_violations")
    assert hasattr(result, "schema_violations")
    assert hasattr(result, "schema_check_skipped")
    assert hasattr(result, "event_type")
    assert isinstance(result.model_violations, tuple)
    assert isinstance(result.schema_violations, tuple)
    assert isinstance(result.schema_check_skipped, bool)
