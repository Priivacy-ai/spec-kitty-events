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
        # Skip replay stream fixtures (JSONL format, loaded via load_replay_stream)
        if entry.get("fixture_type") == "replay_stream":
            continue

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


def load_replay_stream(fixture_id: str) -> List[Dict[str, Any]]:
    """Load a replay stream fixture by manifest ID.

    Args:
        fixture_id: The ``"id"`` value from manifest.json (e.g.
            ``"mission-next-replay-full-lifecycle"``).

    Returns:
        List of Event envelope dicts, one per JSONL line.
        Empty lines are skipped. Each line is parsed with ``json.loads``.

    Raises:
        ValueError: If *fixture_id* is not found or does not have
            ``fixture_type == "replay_stream"`` in the manifest.
        FileNotFoundError: If the fixture file referenced by the manifest
            entry does not exist on disk.
        json.JSONDecodeError: If any non-empty line is not valid JSON.
            No recovery -- malformed JSONL fails hard (no fallback).
    """
    with open(_MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest: Dict[str, Any] = json.load(fh)

    entry: Dict[str, Any] | None = None
    for candidate in manifest["fixtures"]:
        if candidate["id"] == fixture_id:
            entry = candidate
            break

    if entry is None:
        raise ValueError(
            f"Fixture ID not found in manifest: {fixture_id!r}"
        )

    if entry.get("fixture_type") != "replay_stream":
        raise ValueError(
            f"Fixture {fixture_id!r} is not a replay_stream "
            f"(fixture_type={entry.get('fixture_type')!r})"
        )

    full_path = _FIXTURES_DIR / entry["path"]
    if not full_path.exists():
        raise FileNotFoundError(
            f"Replay stream file referenced in manifest does not exist: {full_path}"
        )

    events: List[Dict[str, Any]] = []
    with open(full_path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            events.append(json.loads(stripped))

    return events
