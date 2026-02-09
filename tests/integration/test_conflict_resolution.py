"""Integration test for conflict resolution workflow."""
import uuid
from datetime import datetime
from ulid import ULID
from spec_kitty_events import (
    Event,
    is_concurrent,
    state_machine_merge,
    InMemoryEventStore,
    topological_sort,
)

TEST_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")


class TestConflictResolution:
    """Integration test for conflict detection and resolution."""

    def test_detect_and_resolve_concurrent_state_changes(self) -> None:
        """Test detecting concurrent events and resolving with state-machine merge."""
        event_store = InMemoryEventStore()

        # Scenario: Alice and Bob both change WP001 status at the same time (clock 5)
        # Alice: doing -> for_review
        # Bob: doing -> done
        # Conflict! Both have clock 5, same aggregate, different states

        corr_id = str(ULID())
        e_alice = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,
            payload={"state": "for_review"},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=corr_id,
        )

        e_bob = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA2",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="bob",
            lamport_clock=5,  # Same clock = concurrent
            payload={"state": "done"},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=corr_id,
        )

        event_store.save_event(e_alice)
        event_store.save_event(e_bob)

        # Step 1: Load events for aggregate
        events = event_store.load_events("WP001")
        assert len(events) == 2

        # Step 2: Detect concurrency
        assert is_concurrent(e_alice, e_bob) is True

        # Step 3: Resolve conflict using state-machine merge
        priority_map = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}
        resolution = state_machine_merge([e_alice, e_bob], priority_map)

        # Step 4: Verify resolution
        assert resolution.merged_event.event_id == e_bob.event_id  # "done" wins (higher priority)
        assert resolution.merged_event.payload["state"] == "done"
        assert len(resolution.conflicting_events) == 2
        assert resolution.requires_manual_review is False
        assert "done" in resolution.resolution_note

    def test_no_conflict_different_aggregates(self) -> None:
        """Test events on different aggregates are not concurrent."""
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA1",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=5,
            payload={"state": "done"},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )

        e2 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FA2",
            event_type="WPStatusChanged",
            aggregate_id="WP002",  # Different aggregate
            timestamp=datetime.now(),
            node_id="bob",
            lamport_clock=5,
            payload={"state": "done"},
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )

        # Not concurrent (different aggregates)
        assert is_concurrent(e1, e2) is False

    def test_topological_sort_causation_chain(self) -> None:
        """Test topological sort respects causation relationships."""
        corr_id = str(ULID())
        e1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5001",
            event_type="WPCreated",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=1,
            causation_id=None,  # Root
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=corr_id,
        )

        e2 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5002",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="alice",
            lamport_clock=2,
            causation_id="01ARZ3NDEKTSV4RRFFQ69G5001",  # Child of e1
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=corr_id,
        )

        e3 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5003",
            event_type="WPStatusChanged",
            aggregate_id="WP001",
            timestamp=datetime.now(),
            node_id="bob",
            lamport_clock=3,
            causation_id="01ARZ3NDEKTSV4RRFFQ69G5002",  # Child of e2
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=corr_id,
        )

        # Sort in reverse order (should produce e1, e2, e3)
        sorted_events = topological_sort([e3, e2, e1])

        assert sorted_events == [e1, e2, e3]  # Parent before child
