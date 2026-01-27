"""Integration tests for clock persistence."""
import pytest
from spec_kitty_events.clock import LamportClock
from spec_kitty_events.storage import InMemoryClockStorage


class TestClockPersistence:
    """Tests for clock persistence across restarts."""

    def test_clock_persists_across_restarts(self):
        """Test clock value persists when object is recreated."""
        storage = InMemoryClockStorage()

        # First session: tick to 5
        clock1 = LamportClock(node_id="node1", storage=storage)
        for _ in range(5):
            clock1.tick()
        assert clock1.current() == 5

        # Simulate restart: create new clock object with same storage
        clock2 = LamportClock(node_id="node1", storage=storage)
        assert clock2.current() == 5  # Loaded from storage
        clock2.tick()
        assert clock2.current() == 6  # Continues from persisted value

    def test_multiple_nodes_persist_independently(self):
        """Test multiple nodes maintain separate persisted clocks."""
        storage = InMemoryClockStorage()

        # Node1 session
        clock1 = LamportClock(node_id="node1", storage=storage)
        clock1.tick()
        clock1.tick()

        # Node2 session
        clock2 = LamportClock(node_id="node2", storage=storage)
        clock2.tick()
        clock2.tick()
        clock2.tick()

        # Recreate both clocks
        clock1_new = LamportClock(node_id="node1", storage=storage)
        clock2_new = LamportClock(node_id="node2", storage=storage)

        assert clock1_new.current() == 2
        assert clock2_new.current() == 3

    def test_update_persists_correctly(self):
        """Test update() persists to storage."""
        storage = InMemoryClockStorage()
        clock1 = LamportClock(node_id="node1", storage=storage)
        clock1.update(remote_clock=100)

        # Recreate clock
        clock2 = LamportClock(node_id="node1", storage=storage)
        assert clock2.current() == 101  # max(0, 100) + 1
