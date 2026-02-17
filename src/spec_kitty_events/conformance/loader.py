"""Canonical fixture loading for spec-kitty-events conformance testing.

Provides FixtureCase (frozen dataclass) and load_fixtures() for data-driven
conformance tests. Reads from the bundled manifest.json and fixture JSON files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_MANIFEST_PATH = _FIXTURES_DIR / "manifest.json"

_VALID_CATEGORIES = frozenset({"events", "lane_mapping", "edge_cases", "collaboration", "glossary", "mission_next"})


@dataclass(frozen=True)
class FixtureCase:
    """A single fixture test case loaded from the manifest."""

    id: str
    payload: Any
    expected_valid: bool
    event_type: str
    notes: str
    min_version: str


def load_fixtures(category: str) -> List[FixtureCase]:
    """Load canonical fixture cases for a category.

    Args:
        category: One of ``"events"``, ``"lane_mapping"``, or ``"edge_cases"``.

    Returns:
        List of :class:`FixtureCase` instances with payloads loaded from JSON.

    Raises:
        ValueError: If *category* is not one of the recognised categories.
        FileNotFoundError: If the manifest or a referenced fixture file is missing.
    """
    if category not in _VALID_CATEGORIES:
        raise ValueError(
            f"Unknown fixture category: {category!r}. "
            f"Valid categories: {sorted(_VALID_CATEGORIES)}"
        )

    with open(_MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest: Dict[str, Any] = json.load(fh)

    fixtures: List[FixtureCase] = []

    entries: List[Dict[str, Any]] = manifest["fixtures"]
    for entry in entries:
        fixture_path: str = entry["path"]
        # Filter by category prefix in path
        if not fixture_path.startswith(category + "/"):
            continue

        # Resolve full path to the fixture JSON file
        full_path = _FIXTURES_DIR / fixture_path
        if not full_path.exists():
            raise FileNotFoundError(
                f"Fixture file referenced in manifest does not exist: {full_path}"
            )

        with open(full_path, "r", encoding="utf-8") as fh:
            payload: Any = json.load(fh)

        fixtures.append(
            FixtureCase(
                id=entry["id"],
                payload=payload,
                expected_valid=entry["expected_result"] == "valid",
                event_type=entry["event_type"],
                notes=entry["notes"],
                min_version=entry["min_version"],
            )
        )

    return fixtures
