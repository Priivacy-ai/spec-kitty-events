"""Validation tests for quickstart.md examples."""
from datetime import datetime
from typing import List
import ulid
from spec_kitty_events import (
    Event,
    LamportClock,
    ClockStorage,
    EventStore,
    ErrorStorage,
    ErrorEntry,
    is_concurrent,
    state_machine_merge,
    merge_gset,
    merge_counter,
    ErrorLog,
    total_order_key,
)


class InMemoryClockStorage(ClockStorage):
    def __init__(self):
        self._clocks = {}

    def load(self, node_id: str) -> int:
        return self._clocks.get(node_id, 0)

    def save(self, node_id: str, value: int) -> None:
        self._clocks[node_id] = value


class InMemoryEventStore(EventStore):
    def __init__(self):
        self._events = {}

    def save_event(self, event: Event) -> None:
        self._events[event.event_id] = event

    def load_events(self, aggregate_id: str) -> List[Event]:
        events = [e for e in self._events.values() if e.aggregate_id == aggregate_id]
        return sorted(events, key=lambda e: (e.lamport_clock, e.node_id))

    def load_all_events(self) -> List[Event]:
        return sorted(self._events.values(), key=lambda e: (e.lamport_clock, e.node_id))


class InMemoryErrorStorage(ErrorStorage):
    def __init__(self, max_errors=10):
        self._errors = []
        self._max = max_errors

    def append(self, error_entry: ErrorEntry) -> None:
        self._errors.append(error_entry)
        if len(self._errors) > self._max:
            self._errors.pop(0)  # Evict oldest

    def load_recent(self, limit: int) -> List[ErrorEntry]:
        return self._errors[-limit:][::-1]  # Most recent first


class TestQuickstartExamples:
    """Validate examples from quickstart.md."""

    def test_quickstart_storage_adapters(self) -> None:
        """Test Step 1 example (custom in-memory adapters)."""
        clock_storage = InMemoryClockStorage()
        event_store = InMemoryEventStore()

        clock_storage.save("alice", 2)
        assert clock_storage.load("alice") == 2

        event = Event(
            event_id=str(ulid.ULID()),
            event_type="TestEvent",
            aggregate_id="AGG1",
            payload={"state": "doing"},
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=1
        )
        event_store.save_event(event)

        events = event_store.load_events("AGG1")
        assert len(events) == 1

    def test_quickstart_basic_usage(self) -> None:
        """Test basic usage example from quickstart.md (Step 2 & 3)."""
        # Step 2: Initialize Lamport Clock
        clock = LamportClock(
            node_id="alice-laptop",  # Unique stable ID for this node
            storage=InMemoryClockStorage()
        )

        assert clock.current() == 0  # Starting clock

        # Step 3: Emit Events
        event = Event(
            event_id=str(ulid.ULID()),
            event_type="WPStatusChanged",
            aggregate_id="WP01",
            payload={"previous_state": "planned", "state": "doing"},
            timestamp=datetime.now(),
            node_id="alice-laptop",
            lamport_clock=clock.tick(),  # Increments clock to 1
            causation_id=None  # Root event (no parent)
        )

        event_store = InMemoryEventStore()
        event_store.save_event(event)

        assert clock.current() == 1
        events = event_store.load_events("WP01")
        assert len(events) == 1

    def test_quickstart_receive_remote_events(self) -> None:
        """Test receiving remote events example (Step 4)."""
        # Initialize clock
        clock = LamportClock(node_id="alice-laptop", storage=InMemoryClockStorage())
        clock.tick()  # Clock is now 1

        # Simulate receiving event from remote node
        remote_event = Event(
            event_id=str(ulid.ULID()),
            event_type="WPStatusChanged",
            aggregate_id="WP02",
            payload={"state": "for_review"},
            timestamp=datetime.now(),
            node_id="bob-laptop",
            lamport_clock=10,
            causation_id=None
        )

        # Update local clock when receiving
        clock.update(remote_event.lamport_clock)
        assert clock.current() == 11  # max(1, 10) + 1

    def test_quickstart_conflict_detection(self) -> None:
        """Test conflict detection example from quickstart.md (Step 5)."""
        # Two concurrent events (same lamport_clock, same aggregate)
        alice_event = Event(
            event_id=str(ulid.ULID()),
            event_type="WPStatusChanged",
            aggregate_id="WP03",
            payload={"state": "doing"},
            node_id="alice-laptop",
            lamport_clock=5,
            timestamp=datetime.now()
        )

        bob_event = Event(
            event_id=str(ulid.ULID()),
            event_type="WPStatusChanged",
            aggregate_id="WP03",
            payload={"state": "for_review"},
            node_id="bob-laptop",
            lamport_clock=5,
            timestamp=datetime.now()
        )

        # Detect conflict
        assert is_concurrent(alice_event, bob_event) is True

        # Resolve using state-machine merge
        priority_map = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}
        resolution = state_machine_merge([alice_event, bob_event], priority_map)

        assert resolution.merged_event.payload["state"] == "for_review"  # Higher priority wins

    def test_quickstart_crdt_merges(self) -> None:
        """Test CRDT merge examples from quickstart.md (Step 6)."""
        # Merge concurrent tag additions
        tag_events = [
            Event(
                event_id=str(ulid.ULID()),
                event_type="TagAdded",
                aggregate_id="WP01",
                payload={"tags": {"urgent"}},
                timestamp=datetime.now(),
                node_id="alice",
                lamport_clock=5
            ),
            Event(
                event_id=str(ulid.ULID()),
                event_type="TagAdded",
                aggregate_id="WP01",
                payload={"tags": {"backend"}},
                timestamp=datetime.now(),
                node_id="bob",
                lamport_clock=5
            )
        ]
        merged_tags = merge_gset(tag_events)
        assert merged_tags == {"urgent", "backend"}

        # Merge concurrent counter increments
        counter_events = [
            Event(
                event_id=str(ulid.ULID()),
                event_type="CounterIncremented",
                aggregate_id="WP01",
                payload={"delta": 1},
                timestamp=datetime.now(),
                node_id="alice",
                lamport_clock=5
            ),
            Event(
                event_id=str(ulid.ULID()),
                event_type="CounterIncremented",
                aggregate_id="WP01",
                payload={"delta": 3},
                timestamp=datetime.now(),
                node_id="bob",
                lamport_clock=5
            )
        ]
        merged_count = merge_counter(counter_events)
        assert merged_count == 4

    def test_quickstart_error_logging(self) -> None:
        """Test error logging example from quickstart.md (Step 7)."""
        error_log = ErrorLog(storage=InMemoryErrorStorage())

        # Log error when agent fails
        error_log.log_error(ErrorEntry(
            timestamp=datetime.now(),
            action_attempted="Run pytest tests/test_merge.py",
            error_message="AssertionError: Expected 'doing', got 'for_review'",
            resolution="Fixed priority map (was reversed)",
            agent="codex"
        ))

        # Retrieve errors (most recent first)
        recent_errors = error_log.get_recent_errors(limit=5)
        assert len(recent_errors) == 1
        assert recent_errors[0].agent == "codex"
        assert "AssertionError" in recent_errors[0].error_message

    def test_quickstart_complete_example(self) -> None:
        """Test complete example from quickstart.md (Event Emission & Sync)."""
        # Node A: Alice's laptop
        alice_clock = LamportClock(node_id="alice-laptop", storage=InMemoryClockStorage())
        alice_store = InMemoryEventStore()

        # Alice emits event
        alice_event = Event(
            event_id=str(ulid.ULID()),
            event_type="WPStatusChanged",
            aggregate_id="WP01",
            payload={"state": "doing"},
            timestamp=datetime.now(),
            node_id="alice-laptop",
            lamport_clock=alice_clock.tick()  # 1
        )
        alice_store.save_event(alice_event)

        # Node B: Bob's laptop (offline, hasn't seen Alice's event)
        bob_clock = LamportClock(node_id="bob-laptop", storage=InMemoryClockStorage())
        bob_store = InMemoryEventStore()

        # Bob emits concurrent event
        bob_event = Event(
            event_id=str(ulid.ULID()),
            event_type="WPStatusChanged",
            aggregate_id="WP01",
            payload={"state": "for_review"},
            timestamp=datetime.now(),
            node_id="bob-laptop",
            lamport_clock=bob_clock.tick()  # 1 (concurrent with Alice)
        )
        bob_store.save_event(bob_event)

        # Later: Sync happens (both events reach server)
        all_events = [alice_event, bob_event]

        # Detect conflict
        assert is_concurrent(alice_event, bob_event) is True

        # Resolve conflict
        priority_map = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}
        resolution = state_machine_merge(all_events, priority_map)

        # "for_review" has higher priority than "doing"
        assert resolution.merged_event.payload["state"] == "for_review"

        # Sort all events for deterministic replay
        sorted_events = sorted(all_events, key=total_order_key)
        assert len(sorted_events) == 2
        # Both have same clock (1), so sorted by node_id alphabetically
        assert sorted_events[0].node_id == "alice-laptop"
        assert sorted_events[1].node_id == "bob-laptop"
