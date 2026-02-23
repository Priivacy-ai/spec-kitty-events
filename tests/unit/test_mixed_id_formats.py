"""Tests for mixed ULID/UUID event ID formats across dedup, sort, reducers, and storage."""
import uuid
from datetime import datetime
from typing import List

import pytest
from ulid import ULID

from spec_kitty_events.models import Event
from spec_kitty_events.status import (
    ExecutionMode,
    Lane,
    StatusTransitionPayload,
    WP_STATUS_CHANGED,
    dedup_events,
    reduce_status_events,
    status_event_sort_key,
)
from spec_kitty_events.lifecycle import (
    MISSION_STARTED,
    MISSION_COMPLETED,
    reduce_lifecycle_events,
)
from spec_kitty_events.storage import InMemoryEventStore
from spec_kitty_events.conformance.validators import validate_event

TEST_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
ULID_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
UUID_HYPHEN = "550e8400-e29b-41d4-a716-446655440000"
UUID_BARE = "550E8400E29B41D4A716446655440000"
# After normalization, UUID_BARE becomes the same as UUID_HYPHEN


def _make_event(
    event_id: str = ULID_ID,
    event_type: str = "TestEvent",
    lamport_clock: int = 0,
    correlation_id: str = "01JMYYYYYYYYYYYYYYYYYYYYYY",
    **kwargs: object,
) -> Event:
    defaults = {
        "event_id": event_id,
        "event_type": event_type,
        "aggregate_id": "WP-001",
        "payload": {},
        "timestamp": datetime(2026, 1, 15, 10, 0, 0),
        "node_id": "test-node",
        "lamport_clock": lamport_clock,
        "project_uuid": TEST_PROJECT_UUID,
        "correlation_id": correlation_id,
    }
    defaults.update(kwargs)
    return Event(**defaults)  # type: ignore[arg-type]


def _status_payload(
    from_lane: Lane | None,
    to_lane: Lane,
) -> dict[str, object]:
    return StatusTransitionPayload(
        feature_slug="feat-001",
        wp_id="WP-001",
        from_lane=from_lane,
        to_lane=to_lane,
        actor="test-agent",
        execution_mode=ExecutionMode.WORKTREE,
    ).model_dump()


class TestDedupNormalizesBareUUID:
    """Dedup correctly handles UUID normalization at Event construction time."""

    def test_dedup_normalizes_bare_uuid(self) -> None:
        """Same UUID in bare and hyphenated form deduplicates to one event."""
        e1 = _make_event(
            event_id=UUID_BARE,
            event_type=WP_STATUS_CHANGED,
            lamport_clock=1,
            payload=_status_payload(None, Lane.PLANNED),
        )
        e2 = _make_event(
            event_id=UUID_HYPHEN,
            event_type=WP_STATUS_CHANGED,
            lamport_clock=1,
            payload=_status_payload(None, Lane.PLANNED),
        )
        # Both normalize to the same canonical form at construction
        assert e1.event_id == e2.event_id
        result = dedup_events([e1, e2])
        assert len(result) == 1


class TestSortKeyDeterministicMixedFormats:
    """status_event_sort_key is stable with ULID + UUID event_ids."""

    def test_sort_key_deterministic_mixed_formats(self) -> None:
        """Sort keys are deterministic across ULID and UUID event IDs."""
        e_ulid = _make_event(
            event_id=ULID_ID,
            event_type=WP_STATUS_CHANGED,
            lamport_clock=1,
            payload=_status_payload(None, Lane.PLANNED),
        )
        e_uuid = _make_event(
            event_id=UUID_HYPHEN,
            event_type=WP_STATUS_CHANGED,
            lamport_clock=2,
            payload=_status_payload(Lane.PLANNED, Lane.CLAIMED),
        )
        keys = [status_event_sort_key(e) for e in [e_ulid, e_uuid]]
        # Should be sortable without error
        sorted_keys = sorted(keys)
        assert sorted_keys[0] <= sorted_keys[1]


class TestReduceStatusMixedIds:
    """Status reducer produces correct output with mixed ULID/UUID streams."""

    def test_reduce_status_mixed_ids(self) -> None:
        """Status reducer handles events with ULID and UUID event IDs."""
        e1 = _make_event(
            event_id=ULID_ID,
            event_type=WP_STATUS_CHANGED,
            lamport_clock=1,
            payload=_status_payload(None, Lane.PLANNED),
        )
        e2 = _make_event(
            event_id=UUID_HYPHEN,
            event_type=WP_STATUS_CHANGED,
            lamport_clock=2,
            payload=_status_payload(Lane.PLANNED, Lane.CLAIMED),
        )
        result = reduce_status_events([e1, e2])
        assert result.wp_states["WP-001"].current_lane == Lane.CLAIMED
        assert len(result.anomalies) == 0


class TestReduceLifecycleMixedIds:
    """Lifecycle reducer handles mixed ID formats."""

    def test_reduce_lifecycle_mixed_ids(self) -> None:
        """Lifecycle reducer works with UUID-format event IDs."""
        corr = str(ULID())
        e1 = _make_event(
            event_id=UUID_HYPHEN,
            event_type=MISSION_STARTED,
            lamport_clock=1,
            correlation_id=corr,
            payload={
                "mission_id": "M-001",
                "mission_type": "software-dev",
                "initial_phase": "planning",
                "actor": "test-agent",
            },
        )
        e2 = _make_event(
            event_id=ULID_ID,
            event_type=MISSION_COMPLETED,
            lamport_clock=2,
            correlation_id=corr,
            payload={
                "mission_id": "M-001",
                "mission_type": "software-dev",
                "final_phase": "planning",
                "actor": "test-agent",
            },
        )
        result = reduce_lifecycle_events([e1, e2])
        assert result.mission_status is not None
        assert result.mission_status.value == "completed"
        assert len(result.anomalies) == 0


class TestStorageRoundTripUUID:
    """InMemoryEventStore save/load with UUID event_ids."""

    def test_storage_round_trip_uuid(self) -> None:
        """Events with UUID event_ids survive save/load cycle."""
        store = InMemoryEventStore()
        event = _make_event(event_id=UUID_HYPHEN, lamport_clock=1)
        store.save_event(event)
        loaded: List[Event] = store.load_events("WP-001")
        assert len(loaded) == 1
        assert loaded[0].event_id == "550e8400-e29b-41d4-a716-446655440000"


class TestValidateEventUUIDBothLayers:
    """validate_event() returns valid=True for UUID-format events on both layers."""

    def test_validate_event_uuid_hyphenated(self) -> None:
        """UUID-format event validates on both Pydantic and JSON Schema layers."""
        payload = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "event_type": "TestEvent",
            "aggregate_id": "test-aggregate",
            "payload": {},
            "timestamp": "2026-01-15T10:00:00Z",
            "node_id": "test-node",
            "lamport_clock": 1,
            "causation_id": None,
            "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "correlation_id": "01JMYYYYYYYYYYYYYYYYYYYYYY",
            "schema_version": "1.0.0",
            "data_tier": 0,
        }
        result = validate_event(payload, "Event")
        assert result.valid, (
            f"model_violations={result.model_violations}, "
            f"schema_violations={result.schema_violations}"
        )

    def test_validate_event_uuid_bare(self) -> None:
        """Bare UUID-format event validates on both layers."""
        payload = {
            "event_id": "550e8400e29b41d4a716446655440000",
            "event_type": "TestEvent",
            "aggregate_id": "test-aggregate",
            "payload": {},
            "timestamp": "2026-01-15T10:00:00Z",
            "node_id": "test-node",
            "lamport_clock": 1,
            "causation_id": None,
            "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "correlation_id": "01JMYYYYYYYYYYYYYYYYYYYYYY",
            "schema_version": "1.0.0",
            "data_tier": 0,
        }
        result = validate_event(payload, "Event")
        assert result.valid, (
            f"model_violations={result.model_violations}, "
            f"schema_violations={result.schema_violations}"
        )


class TestValidateEventNonStringId:
    """validate_event() returns model violations (not TypeError) for non-string IDs."""

    def test_validate_event_int_event_id(self) -> None:
        """Integer event_id produces model violations, not TypeError."""
        payload = {
            "event_id": 123,
            "event_type": "TestEvent",
            "aggregate_id": "test-aggregate",
            "payload": {},
            "timestamp": "2026-01-15T10:00:00Z",
            "node_id": "test-node",
            "lamport_clock": 1,
            "causation_id": None,
            "project_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "correlation_id": "01JMYYYYYYYYYYYYYYYYYYYYYY",
            "schema_version": "1.0.0",
            "data_tier": 0,
        }
        result = validate_event(payload, "Event")
        assert not result.valid
        assert len(result.model_violations) > 0
