"""Determinism audit for the eight-class conformance fixture suite.

Walks every JSON fixture under the eight class directories described in
``src/spec_kitty_events/conformance/README.md`` and asserts each
timestamp-shaped string matches the pinned anchor and each ULID-shaped
string matches the pinned ULID prefix.

Per R-06, fixtures must use repository-pinned values:

* Timestamps: ``2026-01-01T00:00:00+00:00``.
* ULIDs: 26-character Crockford-base32 IDs starting with the pinned prefix
  ``01J0000000000000000000`` (e.g., ``01J0000000000000000000FIX1``,
  ``01J0000000000000000000MIS1``).

Failure messages name the offending fixture path and value so a developer
can locate the drift quickly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

import pytest

# ---------------------------------------------------------------------------
# Pinned anchors (R-06)
# ---------------------------------------------------------------------------

PINNED_TIMESTAMP: str = "2026-01-01T00:00:00+00:00"
PINNED_ULID_PREFIX: str = "01J0000000000000000000"

# Class directories that are governed by the eight-class fixture taxonomy.
# Other directories under ``fixtures/`` are pre-existing fixture suites with
# their own conventions (different determinism rules) and are not audited
# here. The eight-class layout lives under ``class_taxonomy/`` so it can
# coexist with the legacy fixture tree without disturbing the existing
# loader (which filters by event-type-category prefix).
CLASS_DIRS: tuple[str, ...] = (
    "class_taxonomy/envelope_valid_canonical",
    "class_taxonomy/envelope_valid_historical_synthesized",
    "class_taxonomy/envelope_invalid_unknown_lane",
    "class_taxonomy/envelope_invalid_forbidden_key",
    "class_taxonomy/envelope_invalid_payload_schema",
    "class_taxonomy/envelope_invalid_shape",
    "class_taxonomy/historical_row_raw",
    "class_taxonomy/lane_mapping_legacy/valid",
    "class_taxonomy/lane_mapping_legacy/invalid",
)

# A 26-char Crockford-base32 string. Crockford-base32 excludes I, L, O, U.
_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

# Anything that *looks* like an ISO-8601 datetime (date+time+offset).
_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$"
)


_FIXTURES_ROOT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "spec_kitty_events"
    / "conformance"
    / "fixtures"
)


def _iter_class_fixture_paths() -> Iterator[Path]:
    """Yield every JSON fixture path under the eight class directories."""
    for sub in CLASS_DIRS:
        directory = _FIXTURES_ROOT / sub
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.json")):
            yield path


def _walk_strings(value: Any, _path: tuple[str | int, ...] = ()) -> Iterator[
    tuple[tuple[str | int, ...], str]
]:
    """Yield ``(json_pointer_tuple, string_value)`` for every string leaf."""
    if isinstance(value, str):
        yield _path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _walk_strings(v, _path + (k,))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk_strings(v, _path + (i,))


def _collect_fixture_paths() -> list[Path]:
    return list(_iter_class_fixture_paths())


@pytest.mark.parametrize(
    "fixture_path",
    _collect_fixture_paths(),
    ids=lambda p: str(p.relative_to(_FIXTURES_ROOT)),
)
def test_fixture_uses_pinned_determinism(fixture_path: Path) -> None:
    """Every string in every class-directory fixture honors R-06."""
    with fixture_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    rel = fixture_path.relative_to(_FIXTURES_ROOT)
    for pointer, value in _walk_strings(data):
        # Timestamp check: any string that *looks* like a datetime must
        # match the pinned anchor exactly.
        if _TIMESTAMP_RE.match(value):
            assert value == PINNED_TIMESTAMP, (
                f"Non-pinned timestamp in fixture {rel} at "
                f"{'/'.join(str(p) for p in pointer)}: {value!r} "
                f"(expected {PINNED_TIMESTAMP!r}; see R-06)"
            )

        # ULID check: any 26-char Crockford-base32 string must start with
        # the pinned prefix.
        if _ULID_RE.match(value):
            assert value.startswith(PINNED_ULID_PREFIX), (
                f"Non-pinned ULID in fixture {rel} at "
                f"{'/'.join(str(p) for p in pointer)}: {value!r} "
                f"(expected prefix {PINNED_ULID_PREFIX!r}; see R-06)"
            )


def test_fixture_corpus_non_empty() -> None:
    """The eight-class fixture corpus must not be empty."""
    paths = _collect_fixture_paths()
    assert paths, (
        "No fixtures found under the eight-class taxonomy directories. "
        f"Searched: {CLASS_DIRS}"
    )
