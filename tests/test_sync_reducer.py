"""Reducer unit tests for Sync lifecycle (FR-007).

Covers: empty stream, happy-path ingest, idempotent dedup,
retry -> dead-letter sequence, replay completion tracking,
cumulative count correctness, and deterministic ordering.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from ulid import ULID

from spec_kitty_events.sync import (
    SYNC_DEAD_LETTERED,
    SYNC_INGEST_ACCEPTED,
    SYNC_INGEST_REJECTED,
    SYNC_REPLAY_COMPLETED,
    SYNC_RETRY_SCHEDULED,
    reduce_sync_events,
)
from spec_kitty_events.models import Event

# ── Constants ──────────────────────────────────────────────────────────────────

_PROJECT_UUID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_NOW = datetime(2026, 2, 27, 12, 0, 0, tzinfo=timezone.utc)


# ── Payload helpers ────────────────────────────────────────────────────────────


def _base_payload(
    delivery_id: str = "del-001",
    fingerprint: str = "fp-abc123",
    lamport_offset: int = 0,
) -> dict[str, Any]:
    """Return a valid sync payload dict with idempotency base fields."""
    return {
        "delivery_id": delivery_id,
        "source_event_fingerprint": fingerprint,
        "connector_id": "conn-001",
        "mission_id": "m-001",
        "recorded_at": datetime(
            2026, 2, 27, 12, 0, lamport_offset, tzinfo=timezone.utc
        ).isoformat(),
    }


def _event(
    event_type: str,
    payload_dict: dict[str, Any],
    *,
    lamport: int = 1,
    event_id: str | None = None,
) -> Event:
    """Factory for constructing test Event instances."""
    return Event(
        event_id=event_id or str(ULID()),
        event_type=event_type,
        aggregate_id="sync/conn-001",
        payload=payload_dict,
        timestamp=datetime(2026, 2, 27, 12, 0, lamport, tzinfo=timezone.utc),
        node_id="node-1",
        lamport_clock=lamport,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )


# ── Named event factories ─────────────────────────────────────────────────────


def _accepted_event(
    lamport: int = 1,
    delivery_id: str = "del-001",
    fingerprint: str = "fp-abc123",
) -> Event:
    d = _base_payload(delivery_id, fingerprint, lamport)
    d["ingest_batch_id"] = "batch-001"
    d["ingested_count"] = 10
    return _event(SYNC_INGEST_ACCEPTED, d, lamport=lamport)


def _rejected_event(
    lamport: int = 2,
    delivery_id: str = "del-002",
    fingerprint: str = "fp-def456",
) -> Event:
    d = _base_payload(delivery_id, fingerprint, lamport)
    d["rejection_reason"] = "Schema mismatch"
    d["rejected_payload_ref"] = "s3://bucket/rejected/001.json"
    return _event(SYNC_INGEST_REJECTED, d, lamport=lamport)


def _retry_event(
    lamport: int = 3,
    delivery_id: str = "del-003",
    fingerprint: str = "fp-ghi789",
) -> Event:
    d = _base_payload(delivery_id, fingerprint, lamport)
    d["retry_attempt"] = 1
    d["max_retries"] = 3
    d["next_retry_at"] = _NOW.isoformat()
    return _event(SYNC_RETRY_SCHEDULED, d, lamport=lamport)


def _dead_lettered_event(
    lamport: int = 4,
    delivery_id: str = "del-003",
    fingerprint: str = "fp-jkl012",
) -> Event:
    d = _base_payload(delivery_id, fingerprint, lamport)
    d["failure_reason"] = "Max retries exceeded"
    d["total_attempts"] = 3
    d["dead_letter_ref"] = "dlq://bucket/dead/001.json"
    return _event(SYNC_DEAD_LETTERED, d, lamport=lamport)


def _replay_event(
    lamport: int = 5,
    delivery_id: str = "del-004",
    fingerprint: str = "fp-mno345",
) -> Event:
    d = _base_payload(delivery_id, fingerprint, lamport)
    d["replay_id"] = "replay-001"
    d["replayed_count"] = 100
    d["replay_source"] = "archive-2026-02"
    return _event(SYNC_REPLAY_COMPLETED, d, lamport=lamport)


# ── Tests: Empty stream ───────────────────────────────────────────────────────


def test_empty_stream() -> None:
    result = reduce_sync_events([])
    assert result.connector_id is None
    assert result.event_count == 0
    assert result.anomalies == ()
    assert result.outcome_log == ()
    assert result.outcome_counts == {
        "accepted_count": 0,
        "rejected_count": 0,
        "retry_count": 0,
        "dead_letter_count": 0,
        "replay_count": 0,
    }


# ── Tests: Happy-path ingest ──────────────────────────────────────────────────


def test_happy_path_accepted_accepted_rejected() -> None:
    """accepted, accepted (different delivery_id), rejected."""
    events = [
        _accepted_event(1, delivery_id="del-001", fingerprint="fp-001"),
        _accepted_event(2, delivery_id="del-002", fingerprint="fp-002"),
        _rejected_event(3, delivery_id="del-003", fingerprint="fp-003"),
    ]
    result = reduce_sync_events(events)
    assert result.connector_id == "conn-001"
    assert result.outcome_counts["accepted_count"] == 2
    assert result.outcome_counts["rejected_count"] == 1
    assert result.anomalies == ()
    assert result.event_count == 3
    assert len(result.outcome_log) == 3


# ── Tests: Idempotent dedup ───────────────────────────────────────────────────


def test_idempotent_dedup_same_delivery_pair() -> None:
    """Same (delivery_id, source_event_fingerprint) pair produces anomaly on second occurrence."""
    e1 = _accepted_event(1, delivery_id="del-001", fingerprint="fp-001")
    # Second event with DIFFERENT event_id but same delivery pair
    e2 = _accepted_event(2, delivery_id="del-001", fingerprint="fp-001")
    result = reduce_sync_events([e1, e2])
    assert result.outcome_counts["accepted_count"] == 1  # only first counted
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "duplicate_delivery_pair"


def test_different_delivery_pairs_no_anomaly() -> None:
    """Different delivery pairs do not trigger dedup anomaly."""
    events = [
        _accepted_event(1, delivery_id="del-001", fingerprint="fp-001"),
        _accepted_event(2, delivery_id="del-001", fingerprint="fp-002"),
        _accepted_event(3, delivery_id="del-002", fingerprint="fp-001"),
    ]
    result = reduce_sync_events(events)
    assert result.anomalies == ()
    assert result.outcome_counts["accepted_count"] == 3


# ── Tests: Retry -> dead-letter sequence ──────────────────────────────────────


def test_retry_dead_letter_sequence() -> None:
    """retry -> dead-letter tracked correctly."""
    events = [
        _retry_event(1, delivery_id="del-001", fingerprint="fp-001"),
        _dead_lettered_event(2, delivery_id="del-001", fingerprint="fp-002"),
    ]
    result = reduce_sync_events(events)
    assert result.outcome_counts["retry_count"] == 1
    assert result.outcome_counts["dead_letter_count"] == 1
    assert result.anomalies == ()


# ── Tests: Replay completion tracking ─────────────────────────────────────────


def test_replay_completion() -> None:
    events = [_replay_event(1)]
    result = reduce_sync_events(events)
    assert result.outcome_counts["replay_count"] == 1
    assert len(result.outcome_log) == 1
    assert result.outcome_log[0][1] == "replay_completed"


# ── Tests: Cumulative count correctness ───────────────────────────────────────


def test_cumulative_counts() -> None:
    """All count fields accumulate correctly across mixed event types."""
    events = [
        _accepted_event(1, delivery_id="d1", fingerprint="f1"),
        _accepted_event(2, delivery_id="d2", fingerprint="f2"),
        _rejected_event(3, delivery_id="d3", fingerprint="f3"),
        _retry_event(4, delivery_id="d4", fingerprint="f4"),
        _retry_event(5, delivery_id="d5", fingerprint="f5"),
        _dead_lettered_event(6, delivery_id="d6", fingerprint="f6"),
        _replay_event(7, delivery_id="d7", fingerprint="f7"),
        _replay_event(8, delivery_id="d8", fingerprint="f8"),
        _replay_event(9, delivery_id="d9", fingerprint="f9"),
    ]
    result = reduce_sync_events(events)
    assert result.outcome_counts == {
        "accepted_count": 2,
        "rejected_count": 1,
        "retry_count": 2,
        "dead_letter_count": 1,
        "replay_count": 3,
    }
    assert result.event_count == 9
    assert len(result.outcome_log) == 9
    assert result.anomalies == ()


# ── Tests: Event dedup by event_id ────────────────────────────────────────────


def test_event_id_dedup() -> None:
    """Duplicate event_ids are deduped (standard event-level dedup)."""
    e1 = _accepted_event(1, delivery_id="d1", fingerprint="f1")
    result_single = reduce_sync_events([e1])
    result_doubled = reduce_sync_events([e1, e1])
    assert result_single == result_doubled
    assert result_single.event_count == 1


# ── Tests: Deterministic ordering ─────────────────────────────────────────────


def test_deterministic_with_reversed_input() -> None:
    """Reducer must sort by (lamport_clock, timestamp, event_id) for determinism."""
    e1 = _accepted_event(1, delivery_id="d1", fingerprint="f1")
    e2 = _rejected_event(2, delivery_id="d2", fingerprint="f2")
    forward = reduce_sync_events([e1, e2])
    reverse = reduce_sync_events([e2, e1])
    assert forward == reverse


# ── Tests: Malformed payload ──────────────────────────────────────────────────


def test_malformed_payload_records_anomaly() -> None:
    events = [
        _event(SYNC_INGEST_ACCEPTED, {"bad": "data"}, lamport=1),
    ]
    result = reduce_sync_events(events)
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "malformed_payload"


def test_malformed_payload_does_not_crash() -> None:
    """Reducer continues after malformed payload."""
    bad = _event(SYNC_INGEST_ACCEPTED, {}, lamport=1)
    good = _accepted_event(2, delivery_id="d1", fingerprint="f1")
    result = reduce_sync_events([bad, good])
    assert result.outcome_counts["accepted_count"] == 1
    assert len(result.anomalies) == 1
    assert result.anomalies[0].kind == "malformed_payload"


# ── Tests: Non-sync events are filtered ──────────────────────────────────────


def test_non_sync_events_filtered_silently() -> None:
    non_sync = Event(
        event_id=str(ULID()),
        event_type="MissionStarted",
        aggregate_id="sync/conn-001",
        payload={"some": "data"},
        timestamp=_NOW,
        node_id="node-1",
        lamport_clock=1,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )
    events = [
        _accepted_event(2, delivery_id="d1", fingerprint="f1"),
        non_sync,
    ]
    result = reduce_sync_events(events)
    assert result.anomalies == ()
    assert result.event_count == 2  # counted before filter


# ── Tests: Reducer output is frozen ───────────────────────────────────────────


def test_reducer_output_is_frozen() -> None:
    result = reduce_sync_events(
        [_accepted_event(1, delivery_id="d1", fingerprint="f1")]
    )
    with pytest.raises(Exception):
        result.connector_id = "changed"  # type: ignore[misc]


# ── Tests: Seen delivery pairs tracking ───────────────────────────────────────


def test_seen_delivery_pairs_tracked() -> None:
    events = [
        _accepted_event(1, delivery_id="d1", fingerprint="f1"),
        _rejected_event(2, delivery_id="d2", fingerprint="f2"),
    ]
    result = reduce_sync_events(events)
    assert ("d1", "f1") in result.seen_delivery_pairs
    assert ("d2", "f2") in result.seen_delivery_pairs
    assert len(result.seen_delivery_pairs) == 2
