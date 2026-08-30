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
import re
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


#: Matches an ISO-8601/RFC-3339 timestamp in either extended
#: (``2026-08-25T09:00:00.123456+00:00``) or basic (``20260825T090000Z``)
#: format, with an optional fractional-second part of *any* digit count and
#: an optional numeric offset. Used only to reshape a match into the one
#: extended-with-6-digit-fraction spelling ``fromisoformat`` accepts
#: identically on every supported interpreter (see
#: ``_normalize_iso8601_shape``); a non-match is passed through unchanged so
#: a genuinely malformed string still reaches ``fromisoformat``'s own error.
#: The trailing-``Z`` designator is handled separately, unconditionally,
#: before this regex ever runs — see ``_normalize_iso8601_shape`` — so this
#: pattern's offset alternative only needs to cover a *numeric* offset.
_ISO8601_SHAPE_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}|\d{8})"
    r"[T ]"
    r"(?P<time>\d{2}:\d{2}:\d{2}|\d{2}:\d{2}|\d{6}|\d{4}|\d{2})"
    r"(?P<frac>[.,]\d+)?"
    r"(?P<offset>[+-]\d{2}:?\d{2})?$"
)


def _normalize_iso8601_shape(value: str) -> str:
    """Reshape *value* so ``datetime.fromisoformat`` parses it identically
    on Python 3.10 and 3.11+.

    3.10's ``fromisoformat`` has three gaps 3.11+ closed: it does not
    recognize the ``Z`` UTC designator at all, it only accepts a
    fractional-second part of exactly 0, 3, or 6 digits (rejecting, e.g.,
    Go's ``time.RFC3339Nano`` 9-digit output), and it only accepts the
    ``-``/``:``-separated "extended" format (rejecting basic format like
    ``20260825T090000Z``). All three gaps let the same wire bytes decode on
    one interpreter and raise on the other (spec-kitty-events#122, #135) —
    this helper matters here in particular because it is the packaged
    cross-repo conformance helper other repos import to prove ingestion-path
    timestamp preservation, so a rejection split here fails a producer's
    conformance test purely on interpreter version.

    The ``Z`` gap is closed first, unconditionally, exactly as it was
    before the fractional/basic-format reshape below existed: a trailing
    ``Z`` is stripped and replaced with ``+00:00`` so it parses the same way
    on every interpreter. A well-formed value has at most this one trailing
    ``Z``; if another ``z``/``Z`` remains after stripping it, the input was
    already malformed and must not be laundered into something 3.11+'s
    single-stray-character leniency around a trailing ``Z`` would otherwise
    accept (e.g. a doubled ``"...00ZZ"`` or mixed-case ``"...00zZ"``) while
    3.10 rejects it outright — so that case raises instead of being
    reshaped. Doing this *before and independently of* the regex below
    means a shape the regex does not match (a different separator, reduced
    precision, ...) is never worse off than it was before the regex-based
    reshape existed — e.g. a lowercase ``t`` date/time separator or a space
    before the ``Z`` both parse identically on 3.10 and 3.11+ once the ``Z``
    has already been rewritten, exactly as on this repo's pre-#122/#135
    ``main``.

    The regex then truncates/pads any fractional part to 6 digits — the
    precision ``datetime`` itself stores — inserts the extended-format
    separators when given basic format, pads a reduced-precision time (bare
    hour, or hour:minute with no seconds, in either format) out to
    hour:minute:second, and inserts a colon into a colon-less numeric
    offset. A value that does not match the expected timestamp shape at all
    (already malformed, or a format this repo does not need to handle) is
    returned unchanged, so it still fails ``fromisoformat`` with its
    ordinary ``ValueError``.
    """
    if value.endswith("Z"):
        candidate = value[:-1]
        if "z" in candidate.lower():
            raise ValueError(
                f"envelope['timestamp'] is not ISO-8601 (doubled UTC designator): {value!r}"
            )
        value = f"{candidate}+00:00"
    match = _ISO8601_SHAPE_RE.match(value)
    if match is None:
        return value
    date, time, frac, offset = match.group("date", "time", "frac", "offset")
    if len(date) == 8:
        date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
    if ":" in time:
        if time.count(":") == 1:
            time = f"{time}:00"
    elif len(time) == 2:
        time = f"{time}:00:00"
    elif len(time) == 4:
        time = f"{time[0:2]}:{time[2:4]}:00"
    else:
        time = f"{time[0:2]}:{time[2:4]}:{time[4:6]}"
    fraction = f".{frac[1:][:6].ljust(6, '0')}" if frac else ""
    if offset is None:
        offset = ""
    elif ":" not in offset:
        offset = f"{offset[:3]}:{offset[3:]}"
    return f"{date}T{time}{fraction}{offset}"


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
        # datetime.fromisoformat in Python 3.10 does not accept trailing
        # 'Z', a fractional-second part outside 0/3/6 digits, or basic
        # (no '-'/':') format; 3.11+ accepts all three for the same wire
        # bytes (spec-kitty-events#122, #135). Reshape before parsing.
        parsed = datetime.fromisoformat(_normalize_iso8601_shape(raw))
        return _to_utc(parsed)
    raise TypeError(
        f"envelope['timestamp'] must be a datetime or ISO-8601 string; got {type(raw).__name__}"
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
        raise ValueError(f"expectation must be 'valid' or 'invalid'; got {expectation!r}")
    path = _FIXTURE_ROOT / expectation / f"{name}.json"
    with path.open("r", encoding="utf-8") as fh:
        result: dict[str, Any] = json.load(fh)
    return result
