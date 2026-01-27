"""Unit tests for Lamport clock."""
import pytest
from spec_kitty_events.clock import LamportClock
from spec_kitty_events.storage import InMemoryClockStorage


class TestLamportClockTick:
    """Tests for tick() method."""

    def test_tick_increments_from_zero(self):
        """Test tick starts at 1 when clock is new."""
        storage = InMemoryClockStorage()
        clock = LamportClock(node_id="node1", storage=storage)
        assert clock.tick() == 1

    def test_tick_increments_sequentially(self):
        """Test tick increments by 1 each time."""
        storage = InMemoryClockStorage()
        clock = LamportClock(node_id="node1", storage=storage)
        assert clock.tick() == 1
        assert clock.tick() == 2
        assert clock.tick() == 3

    def test_tick_persists_to_storage(self):
        """Test tick saves value to storage."""
        storage = InMemoryClockStorage()
        clock = LamportClock(node_id="node1", storage=storage)
        clock.tick()
        # Verify storage has value
        assert storage.load("node1") == 1

    def test_tick_multiple_nodes_independent(self):
        """Test clocks for different nodes are independent."""
        storage = InMemoryClockStorage()
        clock1 = LamportClock(node_id="node1", storage=storage)
        clock2 = LamportClock(node_id="node2", storage=storage)
        clock1.tick()
        clock1.tick()
        clock2.tick()
        assert clock1.current() == 2
        assert clock2.current() == 1


class TestLamportClockUpdate:
    """Tests for update() method."""

    def test_update_with_higher_remote_clock(self):
        """Test update with remote clock > local clock."""
        storage = InMemoryClockStorage()
        clock = LamportClock(node_id="node1", storage=storage)
        clock.tick()  # local = 1
        clock.update(remote_clock=5)  # Should become max(1, 5) + 1 = 6
        assert clock.current() == 6

    def test_update_with_lower_remote_clock(self):
        """Test update with remote clock < local clock."""
        storage = InMemoryClockStorage()
        clock = LamportClock(node_id="node1", storage=storage)
        clock.tick()  # local = 1
        clock.tick()  # local = 2
        clock.tick()  # local = 3
        clock.update(remote_clock=1)  # Should become max(3, 1) + 1 = 4
        assert clock.current() == 4

    def test_update_with_equal_remote_clock(self):
        """Test update with remote clock == local clock."""
        storage = InMemoryClockStorage()
        clock = LamportClock(node_id="node1", storage=storage)
        clock.tick()  # local = 1
        clock.update(remote_clock=1)  # Should become max(1, 1) + 1 = 2
        assert clock.current() == 2

    def test_update_from_zero(self):
        """Test update when local clock is 0 (never ticked)."""
        storage = InMemoryClockStorage()
        clock = LamportClock(node_id="node1", storage=storage)
        clock.update(remote_clock=10)  # Should become max(0, 10) + 1 = 11
        assert clock.current() == 11

    def test_update_persists_to_storage(self):
        """Test update saves value to storage."""
        storage = InMemoryClockStorage()
        clock = LamportClock(node_id="node1", storage=storage)
        clock.update(remote_clock=5)
        # Verify storage has updated value
        assert storage.load("node1") == 6  # max(0, 5) + 1


class TestLamportClockCurrent:
    """Tests for current() method."""

    def test_current_does_not_increment(self):
        """Test current returns value without incrementing."""
        storage = InMemoryClockStorage()
        clock = LamportClock(node_id="node1", storage=storage)
        clock.tick()  # 1
        assert clock.current() == 1
        assert clock.current() == 1  # Still 1, no increment

    def test_current_initial_value_zero(self):
        """Test current returns 0 for new clock."""
        storage = InMemoryClockStorage()
        clock = LamportClock(node_id="node1", storage=storage)
        assert clock.current() == 0
