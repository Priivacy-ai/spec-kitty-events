"""Property tests for status reducer determinism and dedup idempotency."""

import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import List

from hypothesis import given, settings, strategies as st
from ulid import ULID

from spec_kitty_events import (
    Event,
    Lane,
    ExecutionMode,
    StatusTransitionPayload,
    WP_STATUS_CHANGED,
    dedup_events,
    reduce_status_events,
    status_event_sort_key,
)

_PROJECT_UUID = uuid.UUID("12345678-1234-1234-1234-123456789012")


def _make_lifecycle_events(wp_id: str, base_clock: int = 1) -> List[Event]:
    """Create a valid lifecycle for a WP: planned -> claimed -> in_progress -> for_review."""
    transitions = [
        (None, Lane.PLANNED),
        (Lane.PLANNED, Lane.CLAIMED),
        (Lane.CLAIMED, Lane.IN_PROGRESS),
        (Lane.IN_PROGRESS, Lane.FOR_REVIEW),
    ]
    events: List[Event] = []
    for i, (from_l, to_l) in enumerate(transitions):
        eid = f"01HV{base_clock + i:022d}"
        payload = StatusTransitionPayload(
            feature_slug="test",
            wp_id=wp_id,
            from_lane=from_l,
            to_lane=to_l,
            actor="a",
            execution_mode=ExecutionMode.WORKTREE,
        )
        events.append(
            Event(
                event_id=eid,
                event_type=WP_STATUS_CHANGED,
                aggregate_id=f"test/{wp_id}",
                payload=payload.model_dump(),
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc)
                + timedelta(seconds=i),
                node_id="n",
                lamport_clock=base_clock + i,
                project_uuid=_PROJECT_UUID,
                correlation_id=str(ULID()),
            )
        )
    return events


class TestReducerDeterminism:
    """Property tests for reducer determinism."""

    @settings(deadline=None, max_examples=50)
    @given(seed=st.integers(min_value=0, max_value=10000))
    def test_reduce_deterministic_under_permutation(self, seed: int) -> None:
        """Reducer produces same output regardless of input order."""
        events = _make_lifecycle_events("WP01")
        result1 = reduce_status_events(events)
        shuffled = list(events)
        random.Random(seed).shuffle(shuffled)
        result2 = reduce_status_events(shuffled)
        assert result1.wp_states == result2.wp_states

    @settings(deadline=None, max_examples=50)
    @given(seed=st.integers(min_value=0, max_value=10000))
    def test_dedup_idempotent(self, seed: int) -> None:
        """Dedup applied twice yields same result as once."""
        events = _make_lifecycle_events("WP01")
        # Add some duplicates
        duped = events + [events[0], events[2]]
        random.Random(seed).shuffle(duped)
        once = dedup_events(duped)
        twice = dedup_events(once)
        assert [e.event_id for e in once] == [e.event_id for e in twice]

    @settings(deadline=None, max_examples=50)
    @given(seed=st.integers(min_value=0, max_value=10000))
    def test_sort_key_total_order(self, seed: int) -> None:
        """Sort key produces a strict total order on events with distinct keys."""
        events = _make_lifecycle_events("WP01")
        random.Random(seed).shuffle(events)
        sorted_events = sorted(events, key=status_event_sort_key)
        keys = [status_event_sort_key(e) for e in sorted_events]
        for i in range(len(keys) - 1):
            assert keys[i] < keys[i + 1], "Sort key must produce total order"
