"""Conformance tests for the executable timestamp-semantics helper.

Mission: executable-event-timestamp-semantics-01KRNME2

These tests pin three behaviours of
``spec_kitty_events.conformance.assert_producer_occurrence_preserved``:

1. A consumer that preserves the producer's canonical timestamp passes,
   including the "old producer, recent receipt" historical-backfill scenario
   that exposed the original Teamspace Pulse bug.
2. The equality edge case (producer time equals receipt time for a live
   event) is also accepted.
3. A consumer that substitutes receipt time for the canonical timestamp
   fails with the typed ``TimestampSubstitutionError`` and the raised error
   carries the expected attributes.

The helper accepts both Pydantic ``Event`` instances and plain dict envelopes,
and treats timezone-naive datetimes as UTC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from spec_kitty_events.conformance import (
    TimestampSubstitutionError,
    assert_producer_occurrence_preserved,
    load_timestamp_semantics_fixture,
)
from spec_kitty_events.models import Event


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# --- Fixture-driven tests -----------------------------------------------------


def test_old_producer_recent_receipt_helper_passes() -> None:
    """The "old producer, recent receipt" scenario must pass when the consumer preserves producer time."""
    fixture = load_timestamp_semantics_fixture(
        "old_producer_recent_receipt", expectation="valid"
    )
    envelope = fixture["envelope"]
    persisted = _parse_iso(fixture["consumer_simulation"]["persisted_occurrence_time"])
    # Sanity: receipt time and producer time differ by ~134 days.
    received = _parse_iso(fixture["consumer_simulation"]["received_at"])
    producer = _parse_iso(envelope["timestamp"])
    assert (received - producer).days >= 30
    # Should not raise.
    assert_producer_occurrence_preserved(envelope, persisted)


def test_live_event_producer_equals_receipt_helper_passes() -> None:
    """The live-event edge case (producer == receipt) must be accepted."""
    fixture = load_timestamp_semantics_fixture(
        "live_event_producer_equals_receipt", expectation="valid"
    )
    envelope = fixture["envelope"]
    persisted = _parse_iso(fixture["consumer_simulation"]["persisted_occurrence_time"])
    # Should not raise.
    assert_producer_occurrence_preserved(envelope, persisted)


def test_consumer_substituted_receipt_time_helper_raises() -> None:
    """The "bad consumer" scenario must raise TimestampSubstitutionError with full attributes."""
    fixture = load_timestamp_semantics_fixture(
        "consumer_substituted_receipt_time", expectation="invalid"
    )
    envelope = fixture["envelope"]
    persisted = _parse_iso(fixture["consumer_simulation"]["persisted_occurrence_time"])
    expected_producer = _parse_iso(envelope["timestamp"])

    with pytest.raises(TimestampSubstitutionError) as exc_info:
        assert_producer_occurrence_preserved(
            envelope, persisted, field_name="last_event_at"
        )

    err = exc_info.value
    assert err.field_name == "last_event_at"
    assert err.expected == expected_producer
    assert err.actual == persisted
    # Message must surface both timestamps and the canonical rule reference.
    message = str(err)
    assert "last_event_at" in message
    assert expected_producer.isoformat() in message
    assert persisted.isoformat() in message
    assert "producer occurrence time was not preserved" in message


# --- Behavioural unit tests ---------------------------------------------------


def test_helper_accepts_naive_datetime_as_utc() -> None:
    """A naive datetime passed in for ``persisted_occurrence_time`` is treated as UTC."""
    envelope = {"timestamp": "2026-01-01T00:00:00+00:00"}
    # Same instant, naive.
    naive_persisted = datetime(2026, 1, 1, 0, 0, 0)
    assert_producer_occurrence_preserved(envelope, naive_persisted)


def test_helper_accepts_event_instance() -> None:
    """The helper accepts a Pydantic ``Event`` instance, not just a dict."""
    event = Event(
        event_id="01J6XW9KQT7M0YB3N4R5CQZ2EX",
        event_type="WPStatusChanged",
        aggregate_id="wp-event-instance-001",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        build_id="build-helper-event-instance",
        node_id="node-fixture-producer-1",
        lamport_clock=1,
        causation_id=None,
        project_uuid=UUID("00000000-0000-0000-0000-000000000001"),
        project_slug=None,
        correlation_id="01J6XW9KQT7M0YB3N4R5CQZ2EX",
    )
    assert_producer_occurrence_preserved(
        event, datetime(2026, 1, 1, tzinfo=timezone.utc)
    )


def test_helper_envelope_with_datetime_value() -> None:
    """The helper handles an envelope dict whose timestamp is already a datetime."""
    expected = datetime(2026, 1, 1, tzinfo=timezone.utc)
    envelope: dict[str, object] = {"timestamp": expected}
    assert_producer_occurrence_preserved(envelope, expected)


def test_helper_handles_z_suffix_iso_string() -> None:
    """ISO-8601 with a trailing 'Z' is normalised correctly (Python 3.10 compat)."""
    envelope = {"timestamp": "2026-01-01T00:00:00Z"}
    assert_producer_occurrence_preserved(
        envelope, datetime(2026, 1, 1, tzinfo=timezone.utc)
    )


def test_helper_raises_on_one_second_drift() -> None:
    """Even a one-second substitution must raise (proves it is exact, not approximate)."""
    envelope = {"timestamp": "2026-01-01T00:00:00+00:00"}
    drifted = datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
    with pytest.raises(TimestampSubstitutionError) as exc_info:
        assert_producer_occurrence_preserved(envelope, drifted, field_name="my_field")
    assert exc_info.value.field_name == "my_field"
    assert exc_info.value.actual == drifted


def test_error_attributes_round_trip() -> None:
    """Constructing TimestampSubstitutionError directly preserves attributes and __str__."""
    expected = datetime(2026, 1, 1, tzinfo=timezone.utc)
    actual = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)
    err = TimestampSubstitutionError(
        field_name="completed_at",
        expected=expected,
        actual=actual,
    )
    assert err.field_name == "completed_at"
    assert err.expected == expected
    assert err.actual == actual
    msg = str(err)
    assert "completed_at" in msg
    assert expected.isoformat() in msg
    assert actual.isoformat() in msg


# --- Public surface re-export -------------------------------------------------


def test_helper_and_error_are_reexported_from_conformance() -> None:
    """The new symbols MUST be importable from the conformance package root."""
    import spec_kitty_events.conformance as conformance

    assert hasattr(conformance, "assert_producer_occurrence_preserved")
    assert hasattr(conformance, "TimestampSubstitutionError")
    assert hasattr(conformance, "load_timestamp_semantics_fixture")
    assert "assert_producer_occurrence_preserved" in conformance.__all__
    assert "TimestampSubstitutionError" in conformance.__all__
