"""Property-based tests for CRDT laws using Hypothesis."""
import uuid
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone
from spec_kitty_events.crdt import merge_gset, merge_counter
from spec_kitty_events.models import Event


# Fixed timestamp to avoid slow generation
FIXED_TIMESTAMP = datetime(2026, 1, 27, 0, 0, 0, tzinfo=timezone.utc)


# Strategy for generating random events
@st.composite
def event_with_tags(draw):
    """Generate random event with tag set."""
    # Use integers for event_id to ensure uniqueness and avoid duplicates
    event_num = draw(st.integers(min_value=0, max_value=999999))
    event_id = f"{event_num:026d}"
    return Event(
        event_id=event_id,
        event_type="TagAdded",
        aggregate_id="AGG001",
        timestamp=FIXED_TIMESTAMP,
        node_id=draw(st.text(min_size=1, max_size=10)),
        lamport_clock=draw(st.integers(min_value=0, max_value=100)),
        payload={"tags": draw(st.sets(st.text(min_size=1, max_size=10), max_size=5))},
        project_uuid=uuid.uuid4(),
    )


@st.composite
def event_with_delta(draw):
    """Generate random event with counter delta."""
    # Use integers for event_id to ensure uniqueness and avoid duplicates
    event_num = draw(st.integers(min_value=0, max_value=999999))
    event_id = f"{event_num:026d}"
    return Event(
        event_id=event_id,
        event_type="CounterIncremented",
        aggregate_id="AGG001",
        timestamp=FIXED_TIMESTAMP,
        node_id=draw(st.text(min_size=1, max_size=10)),
        lamport_clock=draw(st.integers(min_value=0, max_value=100)),
        payload={"delta": draw(st.integers(min_value=-100, max_value=100))},
        project_uuid=uuid.uuid4(),
    )


class TestGSetLaws:
    """Property-based tests for GSet CRDT laws."""

    @settings(deadline=None)
    @given(st.lists(event_with_tags(), max_size=10, unique_by=lambda e: e.event_id))
    def test_gset_commutative(self, events):
        """Test merge_gset is commutative: merge(A, B) = merge(B, A)."""
        if len(events) < 2:
            return  # Need at least 2 events

        # Split into two groups
        mid = len(events) // 2
        group_a = events[:mid]
        group_b = events[mid:]

        # Merge in different orders
        result1 = merge_gset(group_a + group_b)
        result2 = merge_gset(group_b + group_a)

        assert result1 == result2

    @settings(deadline=None)
    @given(st.lists(event_with_tags(), max_size=10, unique_by=lambda e: e.event_id))
    def test_gset_associative(self, events):
        """Test merge_gset is associative: merge(merge(A, B), C) = merge(A, merge(B, C))."""
        if len(events) < 3:
            return  # Need at least 3 events

        # Split into three groups
        third = len(events) // 3
        group_a = events[:third]
        group_b = events[third:2*third]
        group_c = events[2*third:]

        # Merge with different association
        result1 = merge_gset(group_a + group_b).union(merge_gset(group_c))
        result2 = merge_gset(group_a).union(merge_gset(group_b + group_c))

        # Note: We union results because merge_gset returns set, not list of events
        # For true associativity test, we verify final merged set is same
        all_merged = merge_gset(events)
        assert result1 == all_merged
        assert result2 == all_merged

    @settings(deadline=None)
    @given(st.lists(event_with_tags(), min_size=1, max_size=10, unique_by=lambda e: e.event_id))
    def test_gset_idempotent(self, events):
        """Test merge_gset is idempotent: merge(A, A) = merge(A)."""
        result1 = merge_gset(events)
        result2 = merge_gset(events + events)  # Duplicate list

        assert result1 == result2


class TestCounterLaws:
    """Property-based tests for Counter CRDT laws."""

    @settings(deadline=None)
    @given(st.lists(event_with_delta(), max_size=10, unique_by=lambda e: e.event_id))
    def test_counter_commutative(self, events):
        """Test merge_counter is commutative: merge(A, B) = merge(B, A)."""
        if len(events) < 2:
            return

        mid = len(events) // 2
        group_a = events[:mid]
        group_b = events[mid:]

        result1 = merge_counter(group_a + group_b)
        result2 = merge_counter(group_b + group_a)

        assert result1 == result2

    @settings(deadline=None)
    @given(st.lists(event_with_delta(), max_size=10, unique_by=lambda e: e.event_id))
    def test_counter_associative(self, events):
        """Test merge_counter is associative."""
        if len(events) < 3:
            return

        third = len(events) // 3
        group_a = events[:third]
        group_b = events[third:2*third]
        group_c = events[2*third:]

        # All should equal total merge
        all_merged = merge_counter(events)
        partial1 = merge_counter(group_a + group_b) + merge_counter(group_c)
        partial2 = merge_counter(group_a) + merge_counter(group_b + group_c)

        # Note: Deduplication makes this tricky - only works if groups don't overlap
        # For proper test, we verify totals match
        assert partial1 == all_merged
        assert partial2 == all_merged

    @settings(deadline=None)
    @given(st.lists(event_with_delta(), min_size=1, max_size=10, unique_by=lambda e: e.event_id))
    def test_counter_idempotent(self, events):
        """Test merge_counter is idempotent: merge(A, A) = merge(A)."""
        result1 = merge_counter(events)
        result2 = merge_counter(events + events)  # Duplicate list (deduplication handles this)

        assert result1 == result2
