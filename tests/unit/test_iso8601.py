"""spec-kitty-events#143: pins the private ISO-8601 shape-normalization
helper to exactly one implementation.

``strict.py``, ``retrospective.py``, and ``conformance/timestamp_semantics.py``
each carried a byte-identical ~45-line copy of this helper after
spec-kitty-events#137 (issue #135's own recommendation to factor it out was
not taken at the time). Consolidated into the private ``_iso8601`` module;
each of the three modules re-exports it under its existing local name
(``_normalize_iso8601_shape``) so no consumer import path changes. This test
asserts all three resolve to the *same function object*, so a future
copy-paste at any of these call sites is caught immediately rather than
silently drifting again.
"""

from __future__ import annotations

from spec_kitty_events._iso8601 import normalize_iso8601_shape
from spec_kitty_events.conformance.timestamp_semantics import (
    _normalize_iso8601_shape as _timestamp_semantics_normalize,
)
from spec_kitty_events.retrospective import _normalize_iso8601_shape as _retrospective_normalize
from spec_kitty_events.strict import _normalize_iso8601_shape as _strict_normalize


def test_all_three_call_sites_resolve_to_the_same_function_object() -> None:
    assert _strict_normalize is normalize_iso8601_shape
    assert _retrospective_normalize is normalize_iso8601_shape
    assert _timestamp_semantics_normalize is normalize_iso8601_shape


def test_shared_helper_still_reshapes_basic_format_with_fractional_seconds() -> None:
    """Smoke test on the shared helper directly -- the exhaustive behavior
    matrix (3.10 gaps, doubled-Z rejection, basic/extended, precision
    padding) stays covered where it always was: each of the three
    consumers' own test files, which import this same function under
    their local name and are unaffected by where it now lives."""
    assert (
        normalize_iso8601_shape("20260825T090000.123456789Z") == "2026-08-25T09:00:00.123456+00:00"
    )
