"""Contributor-guidance checks for zeitgeist attrs conformance fixtures."""

from __future__ import annotations

import re
from pathlib import Path


_ZEITGEIST_ATTRS_FIXTURES_DIR = (
    Path(__file__).parent.parent
    / "src"
    / "spec_kitty_events"
    / "conformance"
    / "fixtures"
    / "zeitgeist_attrs"
)
_ALLOCATED_ID_PATTERN = re.compile(r"e2e00000-0000-4000-8000-([0-9]{12})")


def test_readme_next_free_id_is_one_past_the_highest_allocated_fixture_id() -> None:
    """Pin the README's next-free declaration to committed fixture bytes."""
    readme = (_ZEITGEIST_ATTRS_FIXTURES_DIR / "README.md").read_text(encoding="utf-8")
    declared_ids = re.findall(
        r"^\*\*Next free id: `(e2e00000-0000-4000-8000-[0-9]{12})`\*\*$",
        readme,
        flags=re.MULTILINE,
    )
    assert len(declared_ids) == 1, "README must contain exactly one bold 'Next free id' declaration"
    declared = declared_ids[0]

    allocated_ids = [
        match.group(1)
        for path in sorted(_ZEITGEIST_ATTRS_FIXTURES_DIR.rglob("*.json"))
        for match in _ALLOCATED_ID_PATTERN.finditer(path.read_text(encoding="utf-8"))
    ]
    assert allocated_ids, "no allocated zeitgeist_attrs fixture ids found in *.json fixtures"
    highest = max(int(suffix) for suffix in allocated_ids)

    expected_next = f"e2e00000-0000-4000-8000-{highest + 1:012d}"
    assert declared == expected_next, (
        f"README declares next free id {declared!r}, but the highest id allocated "
        f"across *.json fixtures is {highest:012d}, so the next free id should be "
        f"{expected_next!r}"
    )
