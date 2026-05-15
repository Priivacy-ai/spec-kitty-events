"""Executable timestamp-semantics conformance helper.

The canonical event envelope's ``timestamp`` field is the producer-assigned
wall-clock occurrence time of the modelled event. Consumers (SaaS ingestion,
dashboards, audit, sync drains, projections, scorecards) MUST preserve this
value end-to-end and MUST NOT substitute server-receipt, import, drain, or
replay time for it.

This module provides a reusable conformance helper and a typed error so any
downstream repo can prove, with one regression test, that its ingestion path
preserves the producer occurrence time.

See:
- ``kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md``
  (Timestamp Semantics: Rules R-T-01, R-T-02, R-T-03) for the authoritative
  rules.
- ``kitty-specs/executable-event-timestamp-semantics-01KRNME2/contracts/timestamp-semantics.md``
  for the executable contract.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Union

from spec_kitty_events.models import Event

__all__ = [
    "TimestampSubstitutionError",
    "assert_producer_occurrence_preserved",
    "load_timestamp_semantics_fixture",
]


_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "timestamp_semantics"


class TimestampSubstitutionError(Exception):
    """Raised when a consumer substituted receipt/import time for the canonical producer ``timestamp``.

    Attributes:
        field_name: Caller-supplied name of the consumer field/column under check.
        expected: The producer occurrence time from the canonical envelope.
        actual: The value the consumer actually persisted.
    """

    def __init__(
        self,
        *,
        field_name: str,
        expected: datetime,
        actual: datetime,
    ) -> None:
        self.field_name = field_name
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Canonical producer occurrence time was not preserved. "
            f"Field {field_name!r}: expected={expected.isoformat()} "
            f"actual={actual.isoformat()}. The canonical envelope 'timestamp' "
            f"is producer occurrence time and MUST NOT be replaced with "
            f"receipt/import/server time. See "
            f"kitty-specs/teamspace-event-contract-foundation-01KQHDE4/data-model.md "
            f"(Timestamp Semantics)."
        )


def _to_utc(value: datetime) -> datetime:
    """Canonicalise a ``datetime`` to timezone-aware UTC.

    Naive datetimes are treated as UTC (per contract). Aware datetimes are
    converted to UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _extract_envelope_timestamp(envelope: Union[Mapping[str, Any], Event]) -> datetime:
    """Pull the canonical ``timestamp`` out of an envelope dict or ``Event`` instance.

    Accepts ISO-8601 strings (including the ``Z`` suffix) or ``datetime``
    objects. Raises ``KeyError`` if the envelope dict lacks a ``timestamp``
    field, ``TypeError`` if the value is neither a string nor a datetime.
    """
    if isinstance(envelope, Event):
        return _to_utc(envelope.timestamp)

    raw: Any = envelope["timestamp"]
    if isinstance(raw, datetime):
        return _to_utc(raw)
    if isinstance(raw, str):
        # datetime.fromisoformat in Python 3.10 does not accept trailing 'Z'.
        # Normalise to '+00:00' before parsing.
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return _to_utc(parsed)
    raise TypeError(
        f"envelope['timestamp'] must be a datetime or ISO-8601 string; "
        f"got {type(raw).__name__}"
    )


def assert_producer_occurrence_preserved(
    envelope: Union[Mapping[str, Any], Event],
    persisted_occurrence_time: datetime,
    *,
    field_name: str = "persisted_occurrence_time",
) -> None:
    """Assert that the consumer persisted the producer's canonical occurrence time.

    The helper extracts the canonical ``timestamp`` from ``envelope`` and
    compares it (UTC-normalised) to ``persisted_occurrence_time``. If they
    differ, it raises :class:`TimestampSubstitutionError` with the field name,
    expected producer time, and the consumer's substituted value.

    Args:
        envelope: The canonical event envelope as a Pydantic ``Event`` or a
            dict-like mapping (e.g. from JSON). Must contain a ``timestamp``
            field.
        persisted_occurrence_time: The value the consumer persisted as
            canonical event occurrence time. Naive datetimes are treated as
            UTC.
        field_name: Descriptive name of the consumer column/field/attribute
            being checked. Surfaced in the raised error for diagnostics.

    Raises:
        TimestampSubstitutionError: When ``persisted_occurrence_time`` does
            not equal the envelope's producer ``timestamp`` after UTC
            normalisation.

    The helper performs no IO and has no side effects beyond raising. It is
    deterministic and safe to call from any test or production code path.
    """
    expected = _extract_envelope_timestamp(envelope)
    actual = _to_utc(persisted_occurrence_time)
    if expected != actual:
        raise TimestampSubstitutionError(
            field_name=field_name,
            expected=expected,
            actual=actual,
        )


def load_timestamp_semantics_fixture(name: str, *, expectation: str) -> dict[str, Any]:
    """Load a committed timestamp-semantics fixture by name.

    Args:
        name: Bare fixture name without extension, e.g.
            ``"old_producer_recent_receipt"``.
        expectation: Either ``"valid"`` or ``"invalid"``; selects which
            subdirectory under ``fixtures/timestamp_semantics/`` to read.

    Returns:
        The parsed JSON fixture document.

    Raises:
        ValueError: If ``expectation`` is not one of the allowed values.
        FileNotFoundError: If the fixture file does not exist.
    """
    if expectation not in {"valid", "invalid"}:
        raise ValueError(
            f"expectation must be 'valid' or 'invalid'; got {expectation!r}"
        )
    path = _FIXTURE_ROOT / expectation / f"{name}.json"
    with path.open("r", encoding="utf-8") as fh:
        result: dict[str, Any] = json.load(fh)
    return result
