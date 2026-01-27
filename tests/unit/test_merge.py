"""Unit tests for state-machine merge logic."""
import pytest
from datetime import datetime
from spec_kitty_events.merge import state_machine_merge
from spec_kitty_events.models import Event, ValidationError


class TestStateMachineMerge:
    """Tests for state_machine_merge() function."""

    def test_merge_selects_highest_priority(self):
        """Test merge selects event with highest priority state."""
        priority_map = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}

        e1 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEF",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,
            payload={"state": "doing"}  # Priority 2
        )
        e2 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEG",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="bob",
            lamport_clock=5,
            payload={"state": "done"}  # Priority 4 (highest)
        )
        e3 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEH",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="charlie",
            lamport_clock=5,
            payload={"state": "for_review"}  # Priority 3
        )

        resolution = state_machine_merge([e1, e2, e3], priority_map)

        assert resolution.merged_event.event_id == "01HRN7QMQJT8XVKP9YZ2ABCDEG"  # e2 has highest priority
        assert resolution.merged_event.payload["state"] == "done"
        assert len(resolution.conflicting_events) == 3

    def test_merge_tiebreaker_by_node_id(self):
        """Test merge uses node_id as tiebreaker when priorities are equal."""
        priority_map = {"done": 4}

        e1 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEF",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="charlie",  # Later alphabetically
            lamport_clock=5,
            payload={"state": "done"}
        )
        e2 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEG",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",  # Earlier alphabetically (wins)
            lamport_clock=5,
            payload={"state": "done"}
        )

        resolution = state_machine_merge([e1, e2], priority_map)

        assert resolution.merged_event.event_id == "01HRN7QMQJT8XVKP9YZ2ABCDEG"  # alice < charlie
        assert "alice" in resolution.resolution_note

    def test_merge_single_event(self):
        """Test merge with single event (no conflict)."""
        priority_map = {"planned": 1}

        e1 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEF",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,
            payload={"state": "planned"}
        )

        resolution = state_machine_merge([e1], priority_map)

        assert resolution.merged_event == e1
        assert "no conflict" in resolution.resolution_note

    def test_merge_same_state_all_events(self):
        """Test merge when all events have same state."""
        priority_map = {"done": 4}

        e1 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEF",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,
            payload={"state": "done"}
        )
        e2 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEG",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="bob",
            lamport_clock=5,
            payload={"state": "done"}
        )

        resolution = state_machine_merge([e1, e2], priority_map)

        assert resolution.merged_event.payload["state"] == "done"
        assert resolution.merged_event.event_id == "01HRN7QMQJT8XVKP9YZ2ABCDEF"  # alice < bob
        assert "same state" in resolution.resolution_note
        assert "alice" in resolution.resolution_note  # Tiebreaker winner

    def test_merge_different_clocks_raises_error(self):
        """Test merge raises error when events have different lamport_clocks."""
        priority_map = {"done": 4, "planned": 1}

        e1 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEF",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,  # Different clock
            payload={"state": "done"}
        )
        e2 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEG",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="bob",
            lamport_clock=6,  # Different clock
            payload={"state": "planned"}
        )

        with pytest.raises(ValidationError, match="different lamport_clocks"):
            state_machine_merge([e1, e2], priority_map)

    def test_merge_different_aggregates_raises_error(self):
        """Test merge raises error when events have different aggregate_ids."""
        priority_map = {"done": 4}

        e1 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEF",
            event_type="WPStatusChanged",
            aggregate_id="WP001",  # Different aggregate
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,
            payload={"state": "done"}
        )
        e2 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEG",
            event_type="WPStatusChanged",
            aggregate_id="WP002",  # Different aggregate
            timestamp=datetime.now(),
            node_id="bob",
            lamport_clock=5,
            payload={"state": "done"}
        )

        with pytest.raises(ValidationError, match="different aggregate_ids"):
            state_machine_merge([e1, e2], priority_map)

    def test_merge_missing_state_key_raises_error(self):
        """Test merge raises error when event missing state key in payload."""
        priority_map = {"done": 4}

        e1 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEF",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,
            payload={}  # No "state" or "status" key
        )

        with pytest.raises(ValidationError, match="missing 'state' or 'status' in payload"):
            state_machine_merge([e1], priority_map)

    def test_merge_state_not_in_priority_map_raises_error(self):
        """Test merge raises error when state value not in priority_map."""
        priority_map = {"done": 4, "planned": 1}  # "invalid_state" not in map

        e1 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEF",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,
            payload={"state": "invalid_state"}
        )

        with pytest.raises(ValidationError, match="not in priority_map"):
            state_machine_merge([e1], priority_map)

    def test_merge_empty_list_raises_error(self):
        """Test merge raises error on empty event list."""
        priority_map = {"done": 4}

        with pytest.raises(ValidationError, match="Cannot merge empty event list"):
            state_machine_merge([], priority_map)

    def test_merge_custom_state_key(self):
        """Test merge with custom state_key parameter."""
        priority_map = {"active": 2, "inactive": 1}

        e1 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEF",
            event_type="StatusChanged",
            aggregate_id="USER001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,
            payload={"status": "active"}  # Using "status" instead of "state"
        )

        resolution = state_machine_merge([e1], priority_map, state_key="status")

        assert resolution.merged_event.payload["status"] == "active"

    def test_merge_fallback_to_status_key(self):
        """Test merge falls back to 'status' key when using default state_key and 'state' not found."""
        priority_map = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}

        e1 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEF",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,
            payload={"status": "doing"}  # Using "status" not "state"
        )
        e2 = Event(
            event_id="01HRN7QMQJT8XVKP9YZ2ABCDEG",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="bob",
            lamport_clock=5,
            payload={"status": "done"}  # Using "status" not "state"
        )

        # Using default state_key (no explicit parameter), should fallback to "status"
        resolution = state_machine_merge([e1, e2], priority_map)

        assert resolution.merged_event.event_id == "01HRN7QMQJT8XVKP9YZ2ABCDEG"  # e2 has higher priority
        assert resolution.merged_event.payload["status"] == "done"
        assert len(resolution.conflicting_events) == 2
