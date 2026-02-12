"""Property tests for lane mapping determinism and totality."""

from hypothesis import given, settings
from hypothesis import strategies as st

from spec_kitty_events.status import (
    CANONICAL_TO_SYNC_V1,
    Lane,
    SyncLaneV1,
    canonical_to_sync_v1,
)


@settings(max_examples=200)
@given(lane=st.sampled_from(list(Lane)))
def test_canonical_to_sync_v1_is_total(lane: Lane) -> None:
    """For any Lane member, canonical_to_sync_v1 returns a SyncLaneV1."""
    result = canonical_to_sync_v1(lane)
    assert isinstance(result, SyncLaneV1)


@settings(max_examples=200)
@given(lane=st.sampled_from(list(Lane)))
def test_canonical_to_sync_v1_is_deterministic(lane: Lane) -> None:
    """Same input always returns the same output."""
    result_a = canonical_to_sync_v1(lane)
    result_b = canonical_to_sync_v1(lane)
    assert result_a is result_b


def test_all_sync_lane_values_reachable() -> None:
    """At least one canonical lane maps to each SyncLaneV1 member."""
    reachable = set(CANONICAL_TO_SYNC_V1.values())
    for sync_lane in SyncLaneV1:
        assert sync_lane in reachable, f"SyncLaneV1.{sync_lane.name} is unreachable"
