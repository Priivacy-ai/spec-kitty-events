"""Integration test demonstrating custom adapter implementation."""
from typing import List, Dict
from spec_kitty_events import (
    EventStore,
    ClockStorage,
    Event,
    LamportClock,
)
from datetime import datetime


class DictEventStore(EventStore):
    """Custom EventStore implementation using dict (example adapter)."""

    def __init__(self) -> None:
        self._events: Dict[str, Event] = {}

    def save_event(self, event: Event) -> None:
        self._events[event.event_id] = event

    def load_events(self, aggregate_id: str) -> List[Event]:
        events = [e for e in self._events.values() if e.aggregate_id == aggregate_id]
        return sorted(events, key=lambda e: (e.lamport_clock, e.node_id))

    def load_all_events(self) -> List[Event]:
        return sorted(self._events.values(), key=lambda e: (e.lamport_clock, e.node_id))


class DictClockStorage(ClockStorage):
    """Custom ClockStorage implementation using dict (example adapter)."""

    def __init__(self) -> None:
        self._clocks: Dict[str, int] = {}

    def load(self, node_id: str) -> int:
        return self._clocks.get(node_id, 0)

    def save(self, node_id: str, clock_value: int) -> None:
        if clock_value < 0:
            raise ValueError(f"Clock value must be ≥ 0, got {clock_value}")
        self._clocks[node_id] = clock_value


class TestCustomAdapters:
    """Integration test for custom adapter implementations."""

    def test_custom_event_store_adapter(self) -> None:
        """Test library works with custom EventStore adapter."""
        store = DictEventStore()

        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1
        )

        store.save_event(e1)
        loaded = store.load_events("AGG001")

        assert len(loaded) == 1
        assert loaded[0].event_id == "01ARZ3NDEKTSV4RRFFQ69G5FA1"

    def test_custom_clock_storage_adapter(self) -> None:
        """Test library works with custom ClockStorage adapter."""
        storage = DictClockStorage()
        clock = LamportClock(node_id="alice", storage=storage)

        clock.tick()
        clock.tick()

        assert clock.current() == 2

        # Verify persistence
        clock2 = LamportClock(node_id="alice", storage=storage)
        assert clock2.current() == 2  # Loaded from storage

    def test_adapters_are_swappable(self) -> None:
        """Test adapters are swappable (dependency injection works)."""
        from spec_kitty_events import InMemoryEventStore

        # Use in-memory adapter
        store1 = InMemoryEventStore()
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=1
        )
        store1.save_event(event)

        # Switch to custom adapter
        store2 = DictEventStore()
        store2.save_event(event)

        # Both work identically
        assert len(store1.load_all_events()) == 1
        assert len(store2.load_all_events()) == 1
