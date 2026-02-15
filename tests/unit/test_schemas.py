"""Unit tests for the schemas subpackage loader API."""
from __future__ import annotations

import json
import pytest

from spec_kitty_events.schemas import list_schemas, load_schema, schema_path


def test_list_schemas_returns_all_names() -> None:
    """Test that list_schemas returns all 28 schema names."""
    names = list_schemas()
    assert len(names) == 28
    expected = [
        "auth_principal_binding",
        "comment_posted_payload",
        "concurrent_driver_warning_payload",
        "decision_captured_payload",
        "drive_intent_set_payload",
        "event",
        "focus_changed_payload",
        "focus_target",
        "gate_failed_payload",
        "gate_passed_payload",
        "lane",
        "mission_cancelled_payload",
        "mission_completed_payload",
        "mission_started_payload",
        "participant_identity",
        "participant_invited_payload",
        "participant_joined_payload",
        "participant_left_payload",
        "phase_entered_payload",
        "potential_step_collision_detected_payload",
        "presence_heartbeat_payload",
        "prompt_step_execution_completed_payload",
        "prompt_step_execution_started_payload",
        "review_rollback_payload",
        "session_linked_payload",
        "status_transition_payload",
        "sync_lane_v1",
        "warning_acknowledged_payload",
    ]
    assert names == expected


def test_load_schema_returns_dict() -> None:
    """Test that load_schema returns a dictionary."""
    schema = load_schema("event")
    assert isinstance(schema, dict)


def test_load_schema_has_schema_key() -> None:
    """Test that loaded schema has $schema key."""
    schema = load_schema("event")
    assert "$schema" in schema
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_load_schema_has_id_key() -> None:
    """Test that loaded schema has $id key."""
    schema = load_schema("event")
    assert "$id" in schema
    assert schema["$id"] == "spec-kitty-events/event"


def test_load_schema_nonexistent_raises() -> None:
    """Test that loading nonexistent schema raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_schema("nonexistent")
    assert "No schema found for 'nonexistent'" in str(exc_info.value)
    assert "Available:" in str(exc_info.value)


def test_schema_path_returns_path() -> None:
    """Test that schema_path returns a valid Path object."""
    path = schema_path("event")
    assert path.exists()
    assert path.suffix == ".json"
    assert "event.schema.json" in str(path)


def test_all_schemas_are_valid_json() -> None:
    """Test that all schemas can be loaded and parsed as JSON."""
    names = list_schemas()
    for name in names:
        schema = load_schema(name)
        # Verify it's valid JSON by round-tripping
        json_str = json.dumps(schema)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert "$schema" in parsed
        assert "$id" in parsed
