"""Integration test for event emission and clock synchronization."""
import uuid
from datetime import datetime
from ulid import ULID
from spec_kitty_events import (
    Event,
    LamportClock,
    InMemoryClockStorage,
    InMemoryEventStore,
)

TEST_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")


class TestEventEmissionSync:
    """End-to-end test for event emission and synchronization."""

    def test_two_nodes_emit_and_sync(self) -> None:
        """Test two nodes emit events and sync clocks correctly."""
        # Setup: Two nodes (Alice and Bob) with independent clocks
        clock_storage = InMemoryClockStorage()
        event_store = InMemoryEventStore()

        alice_clock = LamportClock(node_id="alice", storage=clock_storage)
        bob_clock = LamportClock(node_id="bob", storage=clock_storage)

        # Alice emits event 1
        corr_id = str(ULID())
        alice_clock.tick()
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=alice_clock.current(),
            payload={"state": "doing"},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=corr_id,
        )
        event_store.save_event(e1)

        # Alice emits event 2
        alice_clock.tick()
        e2 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA2",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=alice_clock.current(),
            causation_id=e1.event_id,  # e2 caused by e1
            payload={"state": "for_review"},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=corr_id,
        )
        event_store.save_event(e2)

        # Bob receives Alice's events and syncs clock
        bob_clock.update(e1.lamport_clock)  # Bob's clock becomes max(0, 1) + 1 = 2
        bob_clock.update(e2.lamport_clock)  # Bob's clock becomes max(2, 2) + 1 = 3

        # Bob emits event 3
        bob_clock.tick()  # Bob's clock becomes 4
        e3 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA3",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="bob",
            lamport_clock=bob_clock.current(),
            causation_id=e2.event_id,  # e3 caused by e2
            payload={"state": "done"},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=corr_id,
        )
        event_store.save_event(e3)

        # Verify: Clock values
        assert alice_clock.current() == 2  # Alice ticked twice
        assert bob_clock.current() == 4  # Bob synced twice, then ticked

        # Verify: Events stored correctly
        all_events = event_store.load_all_events()
        assert len(all_events) == 3
        assert all_events[0].event_id == e1.event_id  # Clock 1
        assert all_events[1].event_id == e2.event_id  # Clock 2
        assert all_events[2].event_id == e3.event_id  # Clock 4

        # Verify: Causation chain
        assert e2.causation_id == e1.event_id
        assert e3.causation_id == e2.event_id

    def test_event_store_idempotency(self) -> None:
        """Test saving same event twice doesn't duplicate."""
        event_store = InMemoryEventStore()

        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            event_type="TestEvent",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=1,
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )

        event_store.save_event(event)
        event_store.save_event(event)  # Save again

        all_events = event_store.load_all_events()
        assert len(all_events) == 1  # Only one copy
