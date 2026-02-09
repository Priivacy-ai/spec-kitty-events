"""Unit tests for CRDT merge functions."""
import uuid
from datetime import datetime
from ulid import ULID
from spec_kitty_events.crdt import merge_gset, merge_counter
from spec_kitty_events.models import Event

TEST_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")


class TestMergeGSet:
    """Tests for merge_gset() function."""

    def test_merge_gset_union(self):
        """Test merge_gset returns union of tag sets."""
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TagAdded",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1,
            payload={"tags": {"bug", "urgent"}},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        e2 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            event_type="TagAdded",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=1,
            payload={"tags": {"bug", "resolved"}},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        result = merge_gset([e1, e2])
        assert result == {"bug", "urgent", "resolved"}

    def test_merge_gset_empty_list(self):
        """Test merge_gset with empty list returns empty set."""
        result = merge_gset([])
        assert result == set()

    def test_merge_gset_missing_tags_key(self):
        """Test merge_gset treats missing 'tags' key as empty set."""
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TagAdded",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1,
            payload={},  # No "tags" key
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        result = merge_gset([e1])
        assert result == set()

    def test_merge_gset_handles_list_input(self):
        """Test merge_gset converts list to set."""
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TagAdded",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1,
            payload={"tags": ["bug", "urgent"]},  # List instead of set
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        result = merge_gset([e1])
        assert result == {"bug", "urgent"}


class TestMergeCounter:
    """Tests for merge_counter() function."""

    def test_merge_counter_sum(self):
        """Test merge_counter sums deltas."""
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="CounterIncremented",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1,
            payload={"delta": 5},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        e2 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            event_type="CounterIncremented",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=1,
            payload={"delta": 3},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        result = merge_counter([e1, e2])
        assert result == 8

    def test_merge_counter_deduplication(self):
        """Test merge_counter deduplicates by event_id."""
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="CounterIncremented",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1,
            payload={"delta": 5},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        # Pass e1 twice
        result = merge_counter([e1, e1])
        assert result == 5  # Counted once

    def test_merge_counter_empty_list(self):
        """Test merge_counter with empty list returns 0."""
        result = merge_counter([])
        assert result == 0

    def test_merge_counter_missing_delta_key(self):
        """Test merge_counter treats missing 'delta' key as 0."""
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="CounterIncremented",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1,
            payload={},  # No "delta" key
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        result = merge_counter([e1])
        assert result == 0

    def test_merge_counter_negative_delta(self):
        """Test merge_counter handles negative deltas."""
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="CounterIncremented",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1,
            payload={"delta": 10},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        e2 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            event_type="CounterDecremented",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=1,
            payload={"delta": -3},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        result = merge_counter([e1, e2])
        assert result == 7  # 10 + (-3)
