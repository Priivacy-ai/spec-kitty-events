"""Unit tests for storage adapters."""
import pytest
from datetime import datetime
from spec_kitty_events.storage import (
    EventStore,
    ClockStorage,
    ErrorStorage,
    InMemoryEventStore,
    InMemoryClockStorage,
    InMemoryErrorStorage,
)
from spec_kitty_events.models import Event, ErrorEntry


class TestEventStore:
    """Tests for EventStore ABC and InMemoryEventStore."""

    def test_cannot_instantiate_abc(self):
        """Test EventStore ABC cannot be instantiated."""
        with pytest.raises(TypeError):
            EventStore()  # type: ignore

    def test_in_memory_save_and_load(self):
        """Test in-memory event store saves and loads events."""
        store = InMemoryEventStore()
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=5
        )
        store.save_event(event)
        loaded = store.load_events("AGG001")
        assert len(loaded) == 1
        assert loaded[0].event_id == event.event_id

    def test_in_memory_idempotency(self):
        """Test saving same event_id twice overwrites (no duplicate)."""
        store = InMemoryEventStore()
        event1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=5
        )
        event2 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Same event_id
            event_type="UpdatedEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=6
        )
        store.save_event(event1)
        store.save_event(event2)
        loaded = store.load_all_events()
        assert len(loaded) == 1  # Only one event
        assert loaded[0].event_type == "UpdatedEvent"  # Overwritten

    def test_in_memory_sorting(self):
        """Test events sorted by (lamport_clock, node_id)."""
        store = InMemoryEventStore()
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            event_type="E1",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=5
        )
        e2 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA2",
            event_type="E2",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=5
        )
        e3 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA3",
            event_type="E3",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=3
        )
        store.save_event(e1)
        store.save_event(e2)
        store.save_event(e3)
        loaded = store.load_events("AGG001")
        # Expected order: e3 (clock=3), e2 (clock=5, node=node1), e1 (clock=5, node=node2)
        assert loaded[0].event_id == e3.event_id
        assert loaded[1].event_id == e2.event_id
        assert loaded[2].event_id == e1.event_id


class TestClockStorage:
    """Tests for ClockStorage ABC and InMemoryClockStorage."""

    def test_cannot_instantiate_abc(self):
        """Test ClockStorage ABC cannot be instantiated."""
        with pytest.raises(TypeError):
            ClockStorage()  # type: ignore

    def test_in_memory_save_and_load(self):
        """Test in-memory clock storage saves and loads values."""
        storage = InMemoryClockStorage()
        storage.save("node1", 42)
        assert storage.load("node1") == 42

    def test_in_memory_initial_value_zero(self):
        """Test loading non-existent clock returns 0."""
        storage = InMemoryClockStorage()
        assert storage.load("node-never-saved") == 0

    def test_in_memory_overwrite(self):
        """Test saving overwrites previous value."""
        storage = InMemoryClockStorage()
        storage.save("node1", 10)
        storage.save("node1", 20)
        assert storage.load("node1") == 20

    def test_in_memory_negative_clock_rejected(self):
        """Test saving negative clock value raises ValueError."""
        storage = InMemoryClockStorage()
        with pytest.raises(ValueError, match="must be ≥ 0"):
            storage.save("node1", -1)


class TestErrorStorage:
    """Tests for ErrorStorage ABC and InMemoryErrorStorage."""

    def test_cannot_instantiate_abc(self):
        """Test ErrorStorage ABC cannot be instantiated."""
        with pytest.raises(TypeError):
            ErrorStorage()  # type: ignore

    def test_in_memory_append_and_load(self):
        """Test in-memory error storage appends and loads entries."""
        storage = InMemoryErrorStorage()
        entry = ErrorEntry(
            timestamp=datetime.now(),
            action_attempted="Run pytest",
            error_message="AssertionError"
        )
        storage.append(entry)
        loaded = storage.load_recent(limit=10)
        assert len(loaded) == 1
        assert loaded[0].action_attempted == "Run pytest"

    def test_in_memory_reverse_chronological_order(self):
        """Test load_recent returns newest first."""
        storage = InMemoryErrorStorage()
        e1 = ErrorEntry(
            timestamp=datetime(2026, 1, 26, 10, 0, 0),
            action_attempted="Action 1",
            error_message="Error 1"
        )
        e2 = ErrorEntry(
            timestamp=datetime(2026, 1, 26, 11, 0, 0),
            action_attempted="Action 2",
            error_message="Error 2"
        )
        e3 = ErrorEntry(
            timestamp=datetime(2026, 1, 26, 12, 0, 0),
            action_attempted="Action 3",
            error_message="Error 3"
        )
        storage.append(e1)
        storage.append(e2)
        storage.append(e3)
        loaded = storage.load_recent(limit=10)
        # Newest first
        assert loaded[0].action_attempted == "Action 3"
        assert loaded[1].action_attempted == "Action 2"
        assert loaded[2].action_attempted == "Action 1"

    def test_in_memory_retention_policy(self):
        """Test retention policy evicts oldest when limit exceeded."""
        storage = InMemoryErrorStorage(max_entries=3)
        for i in range(5):
            entry = ErrorEntry(
                timestamp=datetime.now(),
                action_attempted=f"Action {i}",
                error_message=f"Error {i}"
            )
            storage.append(entry)
        loaded = storage.load_recent(limit=10)
        # Only last 3 entries retained (Action 2, 3, 4)
        assert len(loaded) == 3
        assert loaded[0].action_attempted == "Action 4"  # Newest
        assert loaded[2].action_attempted == "Action 2"  # Oldest retained

    def test_in_memory_load_recent_limit(self):
        """Test load_recent respects limit parameter."""
        storage = InMemoryErrorStorage()
        for i in range(10):
            storage.append(ErrorEntry(
                timestamp=datetime.now(),
                action_attempted=f"Action {i}",
                error_message="Error"
            ))
        loaded = storage.load_recent(limit=3)
        assert len(loaded) == 3
        assert loaded[0].action_attempted == "Action 9"  # Newest

    def test_in_memory_load_recent_invalid_limit(self):
        """Test load_recent rejects invalid limit."""
        storage = InMemoryErrorStorage()
        with pytest.raises(ValueError, match="must be ≥ 1"):
            storage.load_recent(limit=0)
