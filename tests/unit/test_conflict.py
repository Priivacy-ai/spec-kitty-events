"""Unit tests for conflict detection."""
import pytest
from datetime import datetime
from spec_kitty_events.conflict import is_concurrent, total_order_key
from spec_kitty_events.models import Event


class TestIsConcurrent:
    """Tests for is_concurrent() function."""

    def test_concurrent_same_clock_same_aggregate(self):
        """Test events are concurrent if same clock and same aggregate."""
        e1 = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=5
        )
        e2 = Event(
            event_id="01HZQK9F9X0000000000000002",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=5
        )
        assert is_concurrent(e1, e2) is True

    def test_not_concurrent_different_aggregate(self):
        """Test events not concurrent if different aggregate (even if same clock)."""
        e1 = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=5
        )
        e2 = Event(
            event_id="01HZQK9F9X0000000000000002",
            event_type="TestEvent",
            aggregate_id="WP002",  # Different aggregate
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=5
        )
        assert is_concurrent(e1, e2) is False

    def test_not_concurrent_different_clock(self):
        """Test events not concurrent if different lamport_clock."""
        e1 = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=5
        )
        e2 = Event(
            event_id="01HZQK9F9X0000000000000002",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=6  # Different clock
        )
        assert is_concurrent(e1, e2) is False

    def test_not_concurrent_same_event(self):
        """Test event is not concurrent with itself."""
        e1 = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=5
        )
        assert is_concurrent(e1, e1) is False


class TestTotalOrderKey:
    """Tests for total_order_key() function."""

    def test_total_order_key_format(self):
        """Test total_order_key returns (lamport_clock, node_id) tuple."""
        event = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=5
        )
        key = total_order_key(event)
        assert key == (5, "node1")

    def test_total_order_sorting_by_clock(self):
        """Test events sort by lamport_clock first."""
        e1 = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=3
        )
        e2 = Event(
            event_id="01HZQK9F9X0000000000000002",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=1
        )
        e3 = Event(
            event_id="01HZQK9F9X0000000000000003",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node3",
            lamport_clock=2
        )
        events = [e1, e2, e3]
        sorted_events = sorted(events, key=total_order_key)
        assert sorted_events == [e2, e3, e1]  # Clock order: 1, 2, 3

    def test_total_order_tiebreaker_by_node_id(self):
        """Test events with same clock sort by node_id."""
        e1 = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node_charlie",
            lamport_clock=5
        )
        e2 = Event(
            event_id="01HZQK9F9X0000000000000002",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node_alice",
            lamport_clock=5
        )
        e3 = Event(
            event_id="01HZQK9F9X0000000000000003",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node_bob",
            lamport_clock=5
        )
        events = [e1, e2, e3]
        sorted_events = sorted(events, key=total_order_key)
        # Alphabetical by node_id
        assert sorted_events == [e2, e3, e1]  # alice, bob, charlie

    def test_total_order_deterministic(self):
        """Test sorting is deterministic (same input, same output)."""
        events = [
            Event(
                event_id=f"01HZQK9F9X000000000000{i:04d}",
                event_type="TestEvent",
                aggregate_id="WP001",
                timestamp=datetime.now(),
                node_id=f"node{i % 3}",
                lamport_clock=i % 5
            )
            for i in range(10)
        ]
        sorted1 = sorted(events, key=total_order_key)
        sorted2 = sorted(events, key=total_order_key)
        assert sorted1 == sorted2  # Deterministic


class TestTopologicalSort:
    """Tests for topological_sort() function."""

    def test_topological_sort_linear_chain(self):
        """Test topological sort with linear parent-child chain."""
        from spec_kitty_events.topology import topological_sort

        e1 = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1,
            causation_id=None  # Root
        )
        e2 = Event(
            event_id="01HZQK9F9X0000000000000002",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=2,
            causation_id="01HZQK9F9X0000000000000001"  # Child of e1
        )
        e3 = Event(
            event_id="01HZQK9F9X0000000000000003",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=3,
            causation_id="01HZQK9F9X0000000000000002"  # Child of e2
        )
        # Input in reverse order
        sorted_events = topological_sort([e3, e2, e1])
        # Expected order: e1, e2, e3 (parent before child)
        assert sorted_events == [e1, e2, e3]

    def test_topological_sort_multiple_roots(self):
        """Test topological sort with multiple root events."""
        from spec_kitty_events.topology import topological_sort

        e1 = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1,
            causation_id=None  # Root 1
        )
        e2 = Event(
            event_id="01HZQK9F9X0000000000000002",
            event_type="TestEvent",
            aggregate_id="WP002",
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=1,
            causation_id=None  # Root 2
        )
        sorted_events = topological_sort([e2, e1])
        # Both are roots, order doesn't matter (both valid)
        assert len(sorted_events) == 2
        assert e1 in sorted_events
        assert e2 in sorted_events

    def test_topological_sort_cyclic_dependency(self):
        """Test topological sort raises error on cycle."""
        from spec_kitty_events.topology import topological_sort
        from spec_kitty_events.models import CyclicDependencyError

        # Create cycle: e1 -> e2 -> e3 -> e1
        e1 = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1,
            causation_id="01HZQK9F9X0000000000000003"  # Points to e3
        )
        e2 = Event(
            event_id="01HZQK9F9X0000000000000002",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=2,
            causation_id="01HZQK9F9X0000000000000001"
        )
        e3 = Event(
            event_id="01HZQK9F9X0000000000000003",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=3,
            causation_id="01HZQK9F9X0000000000000002"
        )
        with pytest.raises(CyclicDependencyError, match="Cyclic dependency detected"):
            topological_sort([e1, e2, e3])

    def test_topological_sort_empty_list(self):
        """Test topological sort with empty input."""
        from spec_kitty_events.topology import topological_sort

        assert topological_sort([]) == []

    def test_topological_sort_external_parent(self):
        """Test topological sort with event referencing external parent."""
        from spec_kitty_events.topology import topological_sort

        # e1 references an external parent (not in the list)
        e1 = Event(
            event_id="01HZQK9F9X0000000000000001",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=2,
            causation_id="01HZQK9F9X0000000000999999"  # External parent not in list
        )
        e2 = Event(
            event_id="01HZQK9F9X0000000000000002",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=3,
            causation_id="01HZQK9F9X0000000000000001"  # Child of e1
        )
        # Should still work - external parent treated as root
        sorted_events = topological_sort([e1, e2])
        assert sorted_events == [e1, e2]
