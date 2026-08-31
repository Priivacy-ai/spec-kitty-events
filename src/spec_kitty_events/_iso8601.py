"""Shared ISO-8601/RFC-3339 timestamp shape normalization.

Private module (spec-kitty-events#143): factored out of ``strict.py``,
``retrospective.py``, and ``conformance/timestamp_semantics.py``, which each
carried a byte-identical ~45-line copy of :data:`_ISO8601_SHAPE_RE` and
:func:`normalize_iso8601_shape` after spec-kitty-events#137. A fix to this
shape-reshape logic (e.g. the 3.10-only narrowing regression and
mixed-basic/extended acceptance widening #137's pass-2 review found) used to
have to be written once per copy and remembered again in every future one;
this module is the one place it lives now. Stays private (leading
underscore) so no public API surface is added -- each importing module
re-exports it under its own existing private name, so no consumer or test
import path changes.
"""

from __future__ import annotations

import re

#: Matches an ISO-8601/RFC-3339 timestamp in either extended
#: (``2026-08-25T09:00:00.123456+00:00``) or basic (``20260825T090000Z``)
#: format, with an optional fractional-second part of *any* digit count and
#: an optional numeric offset. Used only to reshape a match into the one
#: extended-with-6-digit-fraction spelling ``fromisoformat`` accepts
#: identically on every supported interpreter (see
#: ``normalize_iso8601_shape``); a non-match is passed through unchanged so
#: a genuinely malformed string still reaches ``fromisoformat``'s own error.
#: The trailing-``Z`` designator is handled separately, unconditionally,
#: before this regex ever runs -- see ``normalize_iso8601_shape`` -- so this
#: pattern's offset alternative only needs to cover a *numeric* offset.
_ISO8601_SHAPE_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}|\d{8})"
    r"[T ]"
    r"(?P<time>\d{2}:\d{2}:\d{2}|\d{2}:\d{2}|\d{6}|\d{4}|\d{2})"
    r"(?P<frac>[.,]\d+)?"
    r"(?P<offset>[+-]\d{2}:?\d{2})?$"
)


def normalize_iso8601_shape(value: str) -> str:
    """Reshape *value* so ``datetime.fromisoformat`` parses it identically
    on Python 3.10 and 3.11+.

    3.10's ``fromisoformat`` has three gaps 3.11+ closed: it does not
    recognize the ``Z`` UTC designator at all, it only accepts a
    fractional-second part of exactly 0, 3, or 6 digits (rejecting, e.g.,
    Go's ``time.RFC3339Nano`` 9-digit output), and it only accepts the
    ``-``/``:``-separated "extended" format (rejecting basic format like
    ``20260825T090000Z``). All three gaps let the same wire bytes decode on
    one interpreter and raise on the other (spec-kitty-events#122, #135).

    The ``Z`` gap is closed first, unconditionally, exactly as it was
    before the fractional/basic-format reshape below existed: a trailing
    ``Z`` is stripped and replaced with ``+00:00`` so it parses the same way
    on every interpreter. A well-formed value has at most this one trailing
    ``Z``; if another ``z``/``Z`` remains after stripping it, the input was
    already malformed and must not be laundered into something 3.11+'s
    single-stray-character leniency around a trailing ``Z`` would otherwise
    accept (e.g. a doubled ``"...00ZZ"`` or mixed-case ``"...00zZ"``) while
    3.10 rejects it outright -- so that case raises instead of being
    reshaped. Doing this *before and independently of* the regex below
    means a shape the regex does not match (a different separator, reduced
    precision, ...) is never worse off than it was before the regex-based
    reshape existed -- e.g. a lowercase ``t`` date/time separator or a space
    before the ``Z`` both parse identically on 3.10 and 3.11+ once the ``Z``
    has already been rewritten, exactly as on this repo's pre-#122/#135
    ``main``.

    The regex then truncates/pads any fractional part to 6 digits -- the
    precision ``datetime`` itself stores -- inserts the extended-format
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
            raise ValueError(f"timestamp {value!r} is not ISO-8601 (doubled UTC designator)")
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
