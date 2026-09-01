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
    fixture = load_timestamp_semantics_fixture("old_producer_recent_receipt", expectation="valid")
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
        assert_producer_occurrence_preserved(envelope, persisted, field_name="last_event_at")

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
    assert_producer_occurrence_preserved(event, datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_helper_envelope_with_datetime_value() -> None:
    """The helper handles an envelope dict whose timestamp is already a datetime."""
    expected = datetime(2026, 1, 1, tzinfo=timezone.utc)
    envelope: dict[str, object] = {"timestamp": expected}
    assert_producer_occurrence_preserved(envelope, expected)


def test_helper_handles_z_suffix_iso_string() -> None:
    """ISO-8601 with a trailing 'Z' is normalised correctly (Python 3.10 compat)."""
    envelope = {"timestamp": "2026-01-01T00:00:00Z"}
    assert_producer_occurrence_preserved(envelope, datetime(2026, 1, 1, tzinfo=timezone.utc))


@pytest.mark.parametrize(
    "timestamp,reshaped",
    [
        pytest.param(
            "2026-01-01T00:00:00.123456789Z",
            "2026-01-01T00:00:00.123456+00:00",
            id="z-suffix-nanosecond-fraction",
        ),
        pytest.param(
            "20260101T000000Z",
            "2026-01-01T00:00:00+00:00",
            id="basic-format-z-suffix",
        ),
        pytest.param(
            "20260101T020000+0200",
            "2026-01-01T02:00:00+02:00",
            id="basic-format-numeric-offset",
        ),
        pytest.param(
            "2026-01-01T00:00Z",
            "2026-01-01T00:00:00+00:00",
            id="extended-minute-precision-z-suffix",
        ),
        pytest.param(
            "2026-01-01T00Z",
            "2026-01-01T00:00:00+00:00",
            id="extended-hour-precision-z-suffix",
        ),
    ],
)
def test_helper_accepts_timestamp_shapes_that_split_by_python_version(
    timestamp: str, reshaped: str
) -> None:
    """spec-kitty-events#135: ``datetime.fromisoformat`` on 3.10 rejects an
    arbitrary-precision fractional-second part (3.10 only accepts 0/3/6
    digits) and basic (no ``-``/``:``) format, both accepted on 3.11+ for
    the same wire bytes. ``_extract_envelope_timestamp`` must accept these
    identically regardless of the interpreter running it, since this is
    the packaged cross-repo conformance helper other repos import.

    Also asserts ``_normalize_iso8601_shape``'s exact output (squad
    finding, 2026-08-27): asserting only that the round-trip preserves
    the producer's occurrence time passes identically with the reshape
    deleted, on any interpreter that already tolerates the shape
    natively — this repo's own test runner included.

    The two reduced-precision cases (squad pass 2 MAJOR, 2026-08-27) guard
    against the seconds component having been mandatory in
    ``_ISO8601_SHAPE_RE``. The basic-format half of that same regression is
    covered directly against ``_normalize_iso8601_shape`` below rather than
    through this test's ``_parse_iso`` — that local helper only replaces a
    trailing ``Z`` and never reshapes basic format, so it cannot itself
    parse a basic reduced-precision value on any interpreter, independent
    of the fix under test.

    ``persisted`` is built from ``reshaped``, not the raw ``timestamp``
    (controller-qa finding, 2026-08-28): this test's own ``_parse_iso``
    only replaces a trailing ``Z``, so feeding it the raw 9-digit-fraction
    or basic-format shapes directly would raise on Python 3.10 (the shapes
    this test exists to prove *don't* raise there once passed through the
    real fix) — that would make the test itself interpreter-dependent,
    independent of whether ``_normalize_iso8601_shape`` is correct.
    ``reshaped`` is already the one spelling ``fromisoformat`` accepts
    identically everywhere, asserted equal to the real helper's output on
    the line above."""
    from spec_kitty_events.conformance.timestamp_semantics import _normalize_iso8601_shape

    assert _normalize_iso8601_shape(timestamp) == reshaped
    envelope = {"timestamp": timestamp}
    persisted = datetime.fromisoformat(reshaped)
    assert_producer_occurrence_preserved(envelope, persisted)


@pytest.mark.parametrize(
    "timestamp,reshaped",
    [
        pytest.param(
            "20260101T0000Z",
            "2026-01-01T00:00:00+00:00",
            id="basic-format-minute-precision-z-suffix",
        ),
        pytest.param(
            "20260101T00Z",
            "2026-01-01T00:00:00+00:00",
            id="basic-format-hour-precision-z-suffix",
        ),
    ],
)
def test_helper_normalizes_basic_format_reduced_precision_shapes(
    timestamp: str, reshaped: str
) -> None:
    """Basic-format half of the reduced-precision regression (squad pass 2
    MAJOR, 2026-08-27), asserted directly against ``_normalize_iso8601_shape``
    rather than through the full envelope round-trip: this test file's own
    ``_parse_iso`` helper only replaces a trailing ``Z`` and never reshapes
    basic format, so it cannot compute an independent expected value for a
    basic-format reduced-precision timestamp on any interpreter — that is a
    limitation of the test helper, not of the fix under test, which the
    unit-level assertion below is unaffected by."""
    from spec_kitty_events.conformance.timestamp_semantics import _normalize_iso8601_shape

    assert _normalize_iso8601_shape(timestamp) == reshaped
    parsed = datetime.fromisoformat(_normalize_iso8601_shape(timestamp))
    assert parsed == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_helper_still_rejects_doubled_z_at_reduced_precision() -> None:
    """Guards the incidental gain the squad flagged as worth keeping (pass 2,
    2026-08-27): closing the reduced-precision gap above must not resurrect
    acceptance of a doubled trailing ``Z`` at any precision.
    ``_normalize_iso8601_shape``'s case-folded residual guard (mirrors
    #132's ``_normalize_occurred_at``, controller-qa finding 2026-08-28)
    now raises directly on a doubled/mixed-case trailing designator,
    before the reshape regex ever runs."""
    from spec_kitty_events.conformance.timestamp_semantics import _normalize_iso8601_shape

    for value in (
        "2026-01-01T00:00:00ZZ",
        "2026-01-01T00:00ZZ",
        "2026-01-01T00ZZ",
        "2026-01-01T00:00:00zZ",
    ):
        with pytest.raises(ValueError):
            _normalize_iso8601_shape(value)


@pytest.mark.parametrize(
    "timestamp,reshaped",
    [
        pytest.param(
            "2026-01-01t00:00:00Z",
            "2026-01-01t00:00:00+00:00",
            id="lowercase-t-separator",
        ),
        pytest.param(
            "2026-01-01T00:00:00 Z",
            "2026-01-01T00:00:00 +00:00",
            id="space-before-z",
        ),
    ],
)
def test_helper_does_not_newly_split_shapes_the_regex_does_not_match(
    timestamp: str, reshaped: str
) -> None:
    """Controller-qa finding, 2026-08-28: a shape the reshape regex
    doesn't match (lowercase ``t`` separator, stray space before ``Z``)
    must still go through the unconditional ``Z``-strip that runs before
    the regex, exactly as ``main`` always did — never worse off than
    before this PR's regex-based reshape existed."""
    from spec_kitty_events.conformance.timestamp_semantics import _normalize_iso8601_shape

    assert _normalize_iso8601_shape(timestamp) == reshaped
    envelope = {"timestamp": timestamp}
    persisted = datetime.fromisoformat(reshaped)
    assert_producer_occurrence_preserved(envelope, persisted)


def test_helper_rejects_a_doubled_trailing_z_timestamp() -> None:
    """A doubled trailing "Z" must be rejected on every interpreter version.

    Stripping only the final "Z" and appending "+00:00" would otherwise turn
    this into "...00Z+00:00", which Python 3.10's laxer ``fromisoformat``
    accepts even though it is not a valid ISO-8601 timestamp
    (spec-kitty-events#55/#107).
    """
    envelope = {"timestamp": "2026-01-01T00:00:00ZZ"}
    with pytest.raises(ValueError, match="not ISO-8601"):
        assert_producer_occurrence_preserved(envelope, datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_helper_raises_on_one_second_drift() -> None:
    """Even a one-second substitution must raise (proves it is exact, not approximate)."""
    envelope = {"timestamp": "2026-01-01T00:00:00+00:00"}
    drifted = datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
    with pytest.raises(TimestampSubstitutionError) as exc_info:
        assert_producer_occurrence_preserved(envelope, drifted, field_name="my_field")
    assert exc_info.value.field_name == "my_field"
    assert exc_info.value.actual == drifted


def test_helper_rejects_a_mixed_case_doubled_z_timestamp() -> None:
    """A doubled UTC designator must be rejected regardless of case: a
    case-sensitive residual check misses a lowercase "z" left behind by a
    mixed-case doubled designator (e.g. "...00zZ"), which would otherwise
    launder it into "...00z+00:00" (spec-kitty-events#124)."""
    envelope = {"timestamp": "2026-01-01T00:00:00zZ"}
    with pytest.raises(ValueError, match="timestamp"):
        assert_producer_occurrence_preserved(envelope, datetime(2026, 1, 1, tzinfo=timezone.utc))


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
