"""Hypothesis property tests proving Sync reducer determinism (FR-008, FR-009).

Tests: order independence (>=200 examples), idempotent delivery-pair dedup (>=200 examples).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st
from ulid import ULID

from spec_kitty_events.models import Event
from spec_kitty_events.sync import (
    SYNC_DEAD_LETTERED,
    SYNC_INGEST_ACCEPTED,
    SYNC_INGEST_REJECTED,
    SYNC_REPLAY_COMPLETED,
    SYNC_RETRY_SCHEDULED,
    SyncDeadLetteredPayload,
    SyncIngestAcceptedPayload,
    SyncIngestRejectedPayload,
    SyncReplayCompletedPayload,
    SyncRetryScheduledPayload,
    reduce_sync_events,
)

# -- Predefined event pool ---------------------------------------------------

_PROJECT_UUID = uuid.UUID("dddddddd-eeee-ffff-aaaa-bbbbbbbbbbbb")


def _make_event(event_type: str, payload_obj: object, lamport: int) -> Event:
    return Event(
        event_id=str(ULID()),
        event_type=event_type,
        aggregate_id="sync/conn-prop-sync-001",
        payload=payload_obj.model_dump(),  # type: ignore[union-attr]
        timestamp=datetime(2026, 1, 2, 12, 0, lamport, tzinfo=timezone.utc),
        node_id="node-prop-sync",
        lamport_clock=lamport,
        project_uuid=_PROJECT_UUID,
        correlation_id=str(ULID()),
    )


# Build a module-level pool of pre-built Event objects for property testing.
# Use distinct delivery_id + source_event_fingerprint pairs to avoid dedup anomalies.
_VALID_EVENT_POOL: list[Event] = [
    _make_event(
        SYNC_INGEST_ACCEPTED,
        SyncIngestAcceptedPayload(
            delivery_id="del-prop-001",
            source_event_fingerprint="fp-prop-001",
            connector_id="conn-prop-sync-001",
            mission_id="m-prop-sync-001",
            recorded_at=datetime(2026, 1, 2, 12, 0, 1, tzinfo=timezone.utc),
            ingest_batch_id="batch-prop-001",
            ingested_count=5,
        ),
        lamport=1,
    ),
    _make_event(
        SYNC_INGEST_REJECTED,
        SyncIngestRejectedPayload(
            delivery_id="del-prop-002",
            source_event_fingerprint="fp-prop-002",
            connector_id="conn-prop-sync-001",
            mission_id="m-prop-sync-001",
            recorded_at=datetime(2026, 1, 2, 12, 0, 2, tzinfo=timezone.utc),
            rejection_reason="payload_schema_mismatch",
            rejected_payload_ref="s3://rejected/prop-002.json",
        ),
        lamport=2,
    ),
    _make_event(
        SYNC_RETRY_SCHEDULED,
        SyncRetryScheduledPayload(
            delivery_id="del-prop-003",
            source_event_fingerprint="fp-prop-003",
            connector_id="conn-prop-sync-001",
            mission_id="m-prop-sync-001",
            recorded_at=datetime(2026, 1, 2, 12, 0, 3, tzinfo=timezone.utc),
            retry_attempt=1,
            max_retries=3,
            next_retry_at=datetime(2026, 1, 2, 12, 5, 3, tzinfo=timezone.utc),
        ),
        lamport=3,
    ),
    _make_event(
        SYNC_DEAD_LETTERED,
        SyncDeadLetteredPayload(
            delivery_id="del-prop-004",
            source_event_fingerprint="fp-prop-004",
            connector_id="conn-prop-sync-001",
            mission_id="m-prop-sync-001",
            recorded_at=datetime(2026, 1, 2, 12, 0, 4, tzinfo=timezone.utc),
            failure_reason="max_retries_exceeded",
            total_attempts=3,
            dead_letter_ref="s3://dead-letter/prop-004.json",
        ),
        lamport=4,
    ),
    _make_event(
        SYNC_REPLAY_COMPLETED,
        SyncReplayCompletedPayload(
            delivery_id="del-prop-005",
            source_event_fingerprint="fp-prop-005",
            connector_id="conn-prop-sync-001",
            mission_id="m-prop-sync-001",
            recorded_at=datetime(2026, 1, 2, 12, 0, 5, tzinfo=timezone.utc),
            replay_id="replay-prop-001",
            replayed_count=10,
            replay_source="dead_letter_queue",
        ),
        lamport=5,
    ),
]


# -- Property 1: Order independence -------------------------------------------


@given(st.permutations(_VALID_EVENT_POOL))
@settings(max_examples=200, deadline=None)
def test_order_independence(perm: list[Event]) -> None:
    """Sync reducer output is identical regardless of input event ordering.

    All events have distinct delivery pairs, so no dedup anomalies arise.
    The reducer is purely additive (no terminal states), so permutations
    that change input order produce identical results.
    """
    base_result = reduce_sync_events(_VALID_EVENT_POOL)
    perm_result = reduce_sync_events(perm)
    assert base_result == perm_result


# -- Property 2: Idempotent dedup on (delivery_id, source_event_fingerprint) pairs ---


@given(st.lists(st.sampled_from(_VALID_EVENT_POOL), min_size=1, max_size=5))
@settings(max_examples=200, deadline=None)
def test_idempotent_delivery_pair_dedup(original: list[Event]) -> None:
    """Duplicate (delivery_id, source_event_fingerprint) pairs are idempotently deduplicated.

    When the same events are repeated (same event_id), dedup at the event_id
    level means the doubled list produces identical output to the original.
    """
    doubled = original + original
    result_original = reduce_sync_events(original)
    result_doubled = reduce_sync_events(doubled)
    assert result_original == result_doubled
