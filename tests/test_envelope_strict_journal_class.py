"""``envelope_strict_journal``: a ninth conformance class for the strict
journal profile (F1-T1), sitting alongside -- not inside -- the frozen
eight-class taxonomy in ``tests/test_conformance_classes.py``.

Renata HANDBACK_PACKET_REPAIR finding #2 (MEDIUM): the draft's fixture-root
design (F1.md §4 intro) names ``class_taxonomy/`` entries for a new class
``envelope_strict_journal`` whose reject rows "pin ``expected_error_codes``
as an ordered list" -- plural, because ``validate_strict_envelope`` is
collect-all and can return more than one error per record, unlike the
frozen eight classes' single ``expected_error_code``.

``tests/test_conformance_classes.py`` is a closed module: it hardcodes
``EIGHT_CLASSES``, asserts every ``classes.entries`` row's class is one of
those eight (``test_every_class_has_at_least_one_fixture``), and its
``_validate_for_class`` dispatcher returns a single ``ValidationError``.
Adding a 9th class there would mean editing that already-reviewed,
explicitly-named-eight module just to make it accept a shape (an ordered
*list* of codes) it was never designed to hold. Instead, this module reads
the ``envelope_strict_journal`` fixture files directly from disk (they are
still registered in ``manifest.json``'s top-level ``fixtures`` array, as
every other ``class_taxonomy/`` fixture is, satisfying
``tests/unit/test_fixtures.py``'s every-file-has-a-manifest-entry
invariant) and validates them against the real
``spec_kitty_events.strict.validate_strict_envelope`` entry point.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from spec_kitty_events.strict import validate_strict_envelope

_FIXTURES_ROOT = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "spec_kitty_events"
    / "conformance"
    / "fixtures"
)
_CLASS_DIR = _FIXTURES_ROOT / "class_taxonomy" / "envelope_strict_journal"


def _load_entries() -> list[dict[str, Any]]:
    entries = []
    for path in sorted(_CLASS_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        data["_path"] = path.name
        entries.append(data)
    return entries


_ENTRIES = _load_entries()


def test_envelope_strict_journal_fixtures_exist() -> None:
    assert len(_ENTRIES) == 7


def test_every_entry_declares_class_envelope_strict_journal() -> None:
    for entry in _ENTRIES:
        assert entry["class"] == "envelope_strict_journal", entry["_path"]


@pytest.mark.parametrize("entry", _ENTRIES, ids=lambda e: e["_path"])
def test_envelope_strict_journal_fixture_outcome(entry: dict[str, Any]) -> None:
    errors = validate_strict_envelope(entry["input"])
    actual_codes = [error.code.value for error in errors]

    if entry["expected"] == "valid":
        assert actual_codes == [], (
            f"{entry['_path']}: expected valid (empty tuple) but got {actual_codes}"
        )
    else:
        assert actual_codes == entry["expected_error_codes"], (
            f"{entry['_path']}: expected_error_codes="
            f"{entry['expected_error_codes']!r} but validate_strict_envelope "
            f"returned {actual_codes!r} (order matters -- it is the fixed "
            f"check order documented in strict.validate_strict_envelope's "
            f"docstring)."
        )


def test_covers_at_least_one_row_per_represented_criterion_word() -> None:
    """Coverage gate: at least one fixture id starts with each of the F1
    draft §4 criterion-word prefixes this class was built to represent."""
    ids = {entry["_path"] for entry in _ENTRIES}
    represented_prefixes = (
        "valid_",
        "skew_",
        "unknown_",
        "envelope_extra_",
        "timestamp_",
        "local_appender_",
    )
    for prefix in represented_prefixes:
        assert any(fid.startswith(prefix) for fid in ids), prefix
