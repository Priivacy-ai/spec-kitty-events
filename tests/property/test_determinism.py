"""Property-based tests for determinism of state-machine merge."""
import uuid
from hypothesis import given, strategies as st, settings
from datetime import datetime
from spec_kitty_events.merge import state_machine_merge
from spec_kitty_events.models import Event
from ulid import ULID


# Strategy for generating random events with state
@st.composite
def event_with_state(draw):
    """Generate random event with state value."""
    states = ["done", "for_review", "doing", "planned"]
    return Event(
        event_id=draw(st.text(min_size=26, max_size=26, alphabet="0123456789ABCDEFGHJKMNPQRSTVWXYZ")),
        event_type="WPStatusChanged",
        aggregate_id="WP001",  # Same aggregate for all (concurrent)
        timestamp=datetime.now(),
        node_id=draw(st.text(min_size=1, max_size=10)),
        lamport_clock=5,  # Same clock for all (concurrent)
        payload={"state": draw(st.sampled_from(states))},
        project_uuid=uuid.uuid4(),
        correlation_id=str(ULID()),
    )


class TestMergeDeterminism:
    """Property-based tests for merge determinism."""

    @settings(deadline=None)
    @given(st.lists(event_with_state(), min_size=1, max_size=10))
    def test_merge_deterministic(self, events):
        """Test merge produces same result for same input (determinism)."""
        priority_map = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}

        # Merge same list twice
        resolution1 = state_machine_merge(events, priority_map)
        resolution2 = state_machine_merge(events, priority_map)

        # Results should be identical
        assert resolution1.merged_event.event_id == resolution2.merged_event.event_id
        assert resolution1.resolution_note == resolution2.resolution_note

    @settings(deadline=None)
    @given(st.lists(event_with_state(), min_size=1, max_size=10))
    def test_merge_order_independent(self, events):
        """Test merge result independent of input order (if events are unique)."""
        priority_map = {"done": 4, "for_review": 3, "doing": 2, "planned": 1}

        # Ensure events have unique (node_id, state) pairs for deterministic tiebreaking
        # In real world, same node cannot create two events at same lamport clock
        seen_keys = set()
        unique_events = []
        for event in events:
            state_value = event.payload.get("state")
            key = (event.node_id, state_value)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_events.append(event)

        if len(unique_events) < 2:
            return  # Need at least 2 unique events

        # Merge in original order
        resolution1 = state_machine_merge(unique_events, priority_map)

        # Merge in reversed order
        resolution2 = state_machine_merge(list(reversed(unique_events)), priority_map)

        # Winner should be same (merge is deterministic, not dependent on input order)
        assert resolution1.merged_event.event_id == resolution2.merged_event.event_id
