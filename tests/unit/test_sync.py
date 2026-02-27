"""Unit tests for Sync payload models, constants, and enums (FR-001, FR-002, FR-005).

Covers: constant values, enum members, payload validation, mandatory fields,
idempotency fields, ExternalReferenceLinkedPayload, and frozen model immutability.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from spec_kitty_events.sync import (
    EXTERNAL_REFERENCE_LINKED,
    SYNC_DEAD_LETTERED,
    SYNC_EVENT_TYPES,
    SYNC_INGEST_ACCEPTED,
    SYNC_INGEST_REJECTED,
    SYNC_REPLAY_COMPLETED,
    SYNC_RETRY_SCHEDULED,
    SYNC_SCHEMA_VERSION,
    ExternalReferenceLinkedPayload,
    SyncDeadLetteredPayload,
    SyncIngestAcceptedPayload,
    SyncIngestRejectedPayload,
    SyncOutcome,
    SyncReplayCompletedPayload,
    SyncRetryScheduledPayload,
)

# ── Constants tests (FR-001) ────────────────────────────────────────────────


class TestConstants:
    def test_event_type_values(self) -> None:
        assert SYNC_INGEST_ACCEPTED == "SyncIngestAccepted"
        assert SYNC_INGEST_REJECTED == "SyncIngestRejected"
        assert SYNC_RETRY_SCHEDULED == "SyncRetryScheduled"
        assert SYNC_DEAD_LETTERED == "SyncDeadLettered"
        assert SYNC_REPLAY_COMPLETED == "SyncReplayCompleted"

    def test_event_types_frozenset(self) -> None:
        assert isinstance(SYNC_EVENT_TYPES, frozenset)
        assert SYNC_EVENT_TYPES == frozenset({
            "SyncIngestAccepted",
            "SyncIngestRejected",
            "SyncRetryScheduled",
            "SyncDeadLettered",
            "SyncReplayCompleted",
        })
        assert len(SYNC_EVENT_TYPES) == 5

    def test_schema_version(self) -> None:
        assert SYNC_SCHEMA_VERSION == "2.7.0"

    def test_external_reference_linked_constant(self) -> None:
        assert EXTERNAL_REFERENCE_LINKED == "ExternalReferenceLinked"


# ── Enum tests (FR-001) ─────────────────────────────────────────────────────


class TestEnums:
    def test_sync_outcome_members(self) -> None:
        assert SyncOutcome.ACCEPTED.value == "accepted"
        assert SyncOutcome.REJECTED.value == "rejected"
        assert SyncOutcome.RETRY_SCHEDULED.value == "retry_scheduled"
        assert SyncOutcome.DEAD_LETTERED.value == "dead_lettered"
        assert SyncOutcome.REPLAY_COMPLETED.value == "replay_completed"
        assert len(SyncOutcome) == 5

    def test_outcome_is_str_enum(self) -> None:
        assert isinstance(SyncOutcome.ACCEPTED, str)
        assert SyncOutcome.ACCEPTED == "accepted"


# ── Payload test helpers ─────────────────────────────────────────────────────

_NOW = datetime.now(timezone.utc)


def _idempotency_fields() -> dict:
    """Return a dict of common idempotency base fields shared by all sync payloads."""
    return {
        "delivery_id": "del-001",
        "source_event_fingerprint": "fp-abc123",
        "connector_id": "conn-001",
        "mission_id": "m-001",
        "recorded_at": _NOW.isoformat(),
    }


def _accepted_payload() -> dict:
    d = _idempotency_fields()
    d["ingest_batch_id"] = "batch-001"
    d["ingested_count"] = 42
    return d


def _rejected_payload() -> dict:
    d = _idempotency_fields()
    d["rejection_reason"] = "Schema mismatch"
    d["rejected_payload_ref"] = "s3://bucket/rejected/001.json"
    return d


def _retry_payload() -> dict:
    d = _idempotency_fields()
    d["retry_attempt"] = 1
    d["max_retries"] = 3
    d["next_retry_at"] = _NOW.isoformat()
    return d


def _dead_lettered_payload() -> dict:
    d = _idempotency_fields()
    d["failure_reason"] = "Max retries exceeded"
    d["total_attempts"] = 3
    d["dead_letter_ref"] = "dlq://bucket/dead/001.json"
    return d


def _replay_payload() -> dict:
    d = _idempotency_fields()
    d["replay_id"] = "replay-001"
    d["replayed_count"] = 100
    d["replay_source"] = "archive-2026-02"
    return d


def _ext_ref_payload() -> dict:
    return {
        "link_id": "link-001",
        "connector_id": "conn-001",
        "external_provider": "github.com",
        "external_ref_type": "pull_request",
        "external_ref_id": "PR-42",
        "external_ref_url": "https://github.com/org/repo/pull/42",
        "internal_aggregate_type": "work_package",
        "internal_aggregate_id": "WP01",
        "mission_id": "m-001",
        "linked_by": "human-1",
        "recorded_at": _NOW.isoformat(),
    }


# ── Payload validation tests (FR-002) ───────────────────────────────────────


class TestPayloadValidation:
    """Test that all payload models validate mandatory fields incl. idempotency."""

    def test_accepted_valid(self) -> None:
        p = SyncIngestAcceptedPayload.model_validate(_accepted_payload())
        assert p.delivery_id == "del-001"
        assert p.source_event_fingerprint == "fp-abc123"
        assert p.connector_id == "conn-001"
        assert p.ingest_batch_id == "batch-001"
        assert p.ingested_count == 42

    def test_rejected_valid(self) -> None:
        p = SyncIngestRejectedPayload.model_validate(_rejected_payload())
        assert p.rejection_reason == "Schema mismatch"
        assert p.rejected_payload_ref == "s3://bucket/rejected/001.json"

    def test_retry_valid(self) -> None:
        p = SyncRetryScheduledPayload.model_validate(_retry_payload())
        assert p.retry_attempt == 1
        assert p.max_retries == 3

    def test_dead_lettered_valid(self) -> None:
        p = SyncDeadLetteredPayload.model_validate(_dead_lettered_payload())
        assert p.failure_reason == "Max retries exceeded"
        assert p.total_attempts == 3
        assert p.dead_letter_ref == "dlq://bucket/dead/001.json"

    def test_replay_valid(self) -> None:
        p = SyncReplayCompletedPayload.model_validate(_replay_payload())
        assert p.replay_id == "replay-001"
        assert p.replayed_count == 100
        assert p.replay_source == "archive-2026-02"

    def test_external_reference_linked_valid(self) -> None:
        p = ExternalReferenceLinkedPayload.model_validate(_ext_ref_payload())
        assert p.link_id == "link-001"
        assert p.connector_id == "conn-001"
        assert p.external_provider == "github.com"
        assert p.external_ref_type == "pull_request"
        assert p.external_ref_id == "PR-42"
        assert p.internal_aggregate_type == "work_package"
        assert p.internal_aggregate_id == "WP01"
        assert p.mission_id == "m-001"
        assert p.linked_by == "human-1"

    @pytest.mark.parametrize("missing_field", [
        "delivery_id",
        "source_event_fingerprint",
        "connector_id",
        "mission_id",
        "recorded_at",
        "ingest_batch_id",
        "ingested_count",
    ])
    def test_accepted_missing_mandatory_field_raises(self, missing_field: str) -> None:
        data = _accepted_payload()
        del data[missing_field]
        with pytest.raises(ValidationError):
            SyncIngestAcceptedPayload.model_validate(data)

    @pytest.mark.parametrize("missing_field", [
        "delivery_id",
        "source_event_fingerprint",
        "connector_id",
        "mission_id",
        "recorded_at",
        "rejection_reason",
        "rejected_payload_ref",
    ])
    def test_rejected_missing_mandatory_field_raises(self, missing_field: str) -> None:
        data = _rejected_payload()
        del data[missing_field]
        with pytest.raises(ValidationError):
            SyncIngestRejectedPayload.model_validate(data)

    @pytest.mark.parametrize("missing_field", [
        "link_id",
        "connector_id",
        "external_provider",
        "external_ref_type",
        "external_ref_id",
        "external_ref_url",
        "internal_aggregate_type",
        "internal_aggregate_id",
        "mission_id",
        "linked_by",
        "recorded_at",
    ])
    def test_ext_ref_missing_mandatory_field_raises(self, missing_field: str) -> None:
        data = _ext_ref_payload()
        del data[missing_field]
        with pytest.raises(ValidationError):
            ExternalReferenceLinkedPayload.model_validate(data)

    def test_zero_ingested_count_raises(self) -> None:
        data = _accepted_payload()
        data["ingested_count"] = 0
        with pytest.raises(ValidationError):
            SyncIngestAcceptedPayload.model_validate(data)

    def test_zero_retry_attempt_raises(self) -> None:
        data = _retry_payload()
        data["retry_attempt"] = 0
        with pytest.raises(ValidationError):
            SyncRetryScheduledPayload.model_validate(data)

    def test_zero_total_attempts_raises(self) -> None:
        data = _dead_lettered_payload()
        data["total_attempts"] = 0
        with pytest.raises(ValidationError):
            SyncDeadLetteredPayload.model_validate(data)

    def test_negative_replayed_count_raises(self) -> None:
        data = _replay_payload()
        data["replayed_count"] = -1
        with pytest.raises(ValidationError):
            SyncReplayCompletedPayload.model_validate(data)


# ── Frozen immutability tests ────────────────────────────────────────────────


class TestFrozenModels:
    def test_accepted_is_frozen(self) -> None:
        p = SyncIngestAcceptedPayload.model_validate(_accepted_payload())
        with pytest.raises(ValidationError):
            p.delivery_id = "changed"  # type: ignore[misc]

    def test_all_payload_types_frozen(self) -> None:
        payloads = [
            (SyncIngestAcceptedPayload, _accepted_payload()),
            (SyncIngestRejectedPayload, _rejected_payload()),
            (SyncRetryScheduledPayload, _retry_payload()),
            (SyncDeadLetteredPayload, _dead_lettered_payload()),
            (SyncReplayCompletedPayload, _replay_payload()),
            (ExternalReferenceLinkedPayload, _ext_ref_payload()),
        ]
        for cls, data in payloads:
            payload = cls.model_validate(data)
            assert payload.model_config.get("frozen") is True
