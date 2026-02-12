"""Unit tests for SyncLaneV1 and the canonical-to-sync mapping contract."""

from types import MappingProxyType

import pytest

from spec_kitty_events import (
    CANONICAL_TO_SYNC_V1,
    SyncLaneV1,
    canonical_to_sync_v1,
)
from spec_kitty_events.status import Lane


class TestSyncLaneV1Enum:
    """Tests for the SyncLaneV1 enum."""

    def test_sync_lane_v1_has_exactly_four_members(self) -> None:
        assert len(SyncLaneV1) == 4

    def test_sync_lane_v1_values(self) -> None:
        assert SyncLaneV1.PLANNED.value == "planned"
        assert SyncLaneV1.DOING.value == "doing"
        assert SyncLaneV1.FOR_REVIEW.value == "for_review"
        assert SyncLaneV1.DONE.value == "done"

    def test_sync_lane_v1_string_lookup(self) -> None:
        assert SyncLaneV1("planned") is SyncLaneV1.PLANNED
        assert SyncLaneV1("doing") is SyncLaneV1.DOING
        assert SyncLaneV1("for_review") is SyncLaneV1.FOR_REVIEW
        assert SyncLaneV1("done") is SyncLaneV1.DONE


class TestCanonicalToSyncV1Mapping:
    """Tests for the CANONICAL_TO_SYNC_V1 mapping constant."""

    def test_canonical_to_sync_v1_mapping_completeness(self) -> None:
        """All 7 Lane members must be present as keys."""
        for lane in Lane:
            assert lane in CANONICAL_TO_SYNC_V1, f"Missing key: {lane}"

    def test_canonical_to_sync_v1_specific_mappings(self) -> None:
        assert CANONICAL_TO_SYNC_V1[Lane.PLANNED] is SyncLaneV1.PLANNED
        assert CANONICAL_TO_SYNC_V1[Lane.CLAIMED] is SyncLaneV1.PLANNED
        assert CANONICAL_TO_SYNC_V1[Lane.IN_PROGRESS] is SyncLaneV1.DOING
        assert CANONICAL_TO_SYNC_V1[Lane.FOR_REVIEW] is SyncLaneV1.FOR_REVIEW
        assert CANONICAL_TO_SYNC_V1[Lane.DONE] is SyncLaneV1.DONE
        assert CANONICAL_TO_SYNC_V1[Lane.BLOCKED] is SyncLaneV1.DOING
        assert CANONICAL_TO_SYNC_V1[Lane.CANCELED] is SyncLaneV1.PLANNED

    def test_canonical_to_sync_v1_output_values_are_sync_lane(self) -> None:
        for value in CANONICAL_TO_SYNC_V1.values():
            assert isinstance(value, SyncLaneV1)

    def test_canonical_to_sync_v1_immutable(self) -> None:
        assert isinstance(CANONICAL_TO_SYNC_V1, MappingProxyType)
        with pytest.raises(TypeError):
            CANONICAL_TO_SYNC_V1[Lane.PLANNED] = SyncLaneV1.DONE  # type: ignore[index]


class TestCanonicalToSyncV1Function:
    """Tests for the canonical_to_sync_v1() function."""

    def test_canonical_to_sync_v1_function(self) -> None:
        for lane in Lane:
            assert canonical_to_sync_v1(lane) is CANONICAL_TO_SYNC_V1[lane]

    def test_canonical_to_sync_v1_in_progress(self) -> None:
        assert canonical_to_sync_v1(Lane.IN_PROGRESS) is SyncLaneV1.DOING

    def test_canonical_to_sync_v1_canceled(self) -> None:
        assert canonical_to_sync_v1(Lane.CANCELED) is SyncLaneV1.PLANNED
