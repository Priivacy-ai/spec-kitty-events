"""Pin the canonical lane vocabulary as a single source of truth.

These tests guard against silent drift of the canonical ``Lane`` enum and
prevent parallel lane-vocabulary definitions from sneaking into the package.

Cross-repo handshake: downstream consumers validate their event-boundary
translations against the package's public ``Lane`` enum. They do not import
``EXPECTED_CANONICAL_LANES`` from this test module, and they may carry
host-internal states that are translated before persistence or wire emission.

Refs: FR-001, FR-002, C-002, SC-003 of mission
``teamspace-event-contract-foundation-01KQHDE4``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import FrozenSet, Set

from spec_kitty_events import Lane
from spec_kitty_events.diary import Lane as DiaryLane

# ---------------------------------------------------------------------------
# Pinned canonical vocabulary
# ---------------------------------------------------------------------------
#
# This set MUST stay in lockstep with the ``Lane`` enum in
# ``src/spec_kitty_events/status.py``. Any intentional change to the canonical
# vocabulary requires a deliberate edit here AND a major-version bump per the
# contract in ``contracts/lane-vocabulary.md``. Drift between the enum and this
# set is treated as a contract violation by ``test_canonical_lane_set_is_pinned``.

EXPECTED_CANONICAL_LANES: FrozenSet[str] = frozenset(
    {
        "genesis",
        "planned",
        "claimed",
        "in_progress",
        "for_review",
        "in_review",
        "approved",
        "done",
        "blocked",
        "canceled",
    }
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_in_review_is_canonical() -> None:
    """``in_review`` is a member of the canonical ``Lane`` vocabulary."""
    assert Lane.IN_REVIEW.value == "in_review"
    assert Lane.IN_REVIEW in Lane
    # Round-trip via Lane(value) — defends the import surface.
    assert Lane("in_review") is Lane.IN_REVIEW


def test_canonical_lane_set_is_pinned() -> None:
    """The canonical lane set has not silently drifted from the pinned contract."""
    actual = frozenset(member.value for member in Lane)
    assert actual == EXPECTED_CANONICAL_LANES, (
        f"Lane vocabulary drifted. "
        f"New: {sorted(actual - EXPECTED_CANONICAL_LANES)}, "
        f"Removed: {sorted(EXPECTED_CANONICAL_LANES - actual)}. "
        f"Update EXPECTED_CANONICAL_LANES in this file ONLY when the "
        f"canonical vocabulary intentionally changes (which is a contract "
        f"change subject to the major-bump rule)."
    )


def test_diary_lane_vocabulary_is_pinned() -> None:
    """The diary FSM vocabulary is pinned exactly (issue #41).

    ``spec_kitty_events.diary.Lane`` is the CLI's work-package FSM
    vocabulary, moved verbatim from ``specify_cli/status/models.py`` so the
    CLI and the repo dossier reduce ``status.events.jsonl`` with one
    implementation. It is deliberately a SECOND, distinct vocabulary: it adds
    ``uninitialized`` -- the non-display read sentinel for a WP absent from
    the reduced snapshot -- which the envelope-level canonical ``Lane``
    intentionally does not carry. Unifying the two is an envelope contract
    change subject to the major-bump rule, not something a reducer move may
    do silently; until then BOTH sets are pinned here so neither can drift.
    """
    expected = EXPECTED_CANONICAL_LANES | {"uninitialized"}
    actual = frozenset(member.value for member in DiaryLane)
    assert actual == expected, (
        f"Diary lane vocabulary drifted. "
        f"New: {sorted(actual - expected)}, "
        f"Removed: {sorted(expected - actual)}. "
        f"The diary vocabulary is the CLI's pinned FSM set "
        f"(canonical lanes + 'uninitialized'); changing it requires a "
        f"deliberate edit here AND in contracts/lane-vocabulary.md terms."
    )
    # The non-display sentinels stay excluded from board summaries.
    from spec_kitty_events.diary import NON_DISPLAY_LANES

    assert {lane.value for lane in NON_DISPLAY_LANES} == {"genesis", "uninitialized"}


def test_lane_vocabulary_is_single_source_of_truth() -> None:
    """No duplicate canonical-lane definition lives elsewhere in the package.

    Scans ``src/spec_kitty_events/`` for any string literal matching a known
    canonical lane value (e.g., ``"in_review"``) outside of the authoritative
    source ``status.py``. The intent is to prevent a future contributor from
    quietly introducing a parallel lane list (e.g. another ``str, Enum`` with
    the same string values) that would drift from ``Lane``.

    Allow-list: the canonical source ``status.py`` and its ``schemas/``
    sibling, which is generated from ``status.py`` and therefore mirrors the
    same vocabulary by construction.
    """
    package_root = Path(__file__).resolve().parent.parent / "src" / "spec_kitty_events"
    assert package_root.is_dir(), f"Package root not found at {package_root}"

    # Files allowed to contain canonical lane string literals.
    allowed_files: Set[Path] = {
        (package_root / "status.py").resolve(),
        # diary.py legitimately hosts the CLI's second, separately pinned FSM
        # vocabulary (canonical lanes + 'uninitialized'); see
        # test_diary_lane_vocabulary_is_pinned above, which holds it to that
        # exact set so the allow-list entry cannot hide drift.
        (package_root / "diary.py").resolve(),
    }

    # Lane values whose strings could plausibly be common English words
    # (e.g. ``"done"``, ``"approved"``, ``"blocked"``, ``"canceled"``,
    # ``"planned"``, ``"claimed"``) and would produce noisy false positives if
    # we scanned for them naively. We restrict the scan to the lane values
    # that are unique enough to be high-signal.
    high_signal_lane_values = {
        "in_review",
        "for_review",
        "in_progress",
    }

    offenders: list[str] = []
    pattern = re.compile(
        r'["\'](' + "|".join(re.escape(v) for v in high_signal_lane_values) + r')["\']'
    )

    for py_file in package_root.rglob("*.py"):
        resolved = py_file.resolve()
        if resolved in allowed_files:
            continue
        # Skip the schemas/ directory — JSON Schemas are generated from
        # the canonical Lane enum and legitimately mirror its values.
        if "schemas" in py_file.parts:
            continue
        try:
            text = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            # Skip matches inside docstring examples (``>>>``) — those are
            # illustrative, not authoritative.
            line = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
            stripped = line.lstrip()
            if stripped.startswith(">>>") or stripped.startswith("..."):
                continue
            offenders.append(
                f"{py_file.relative_to(package_root.parent.parent)}:{line_no} -> {match.group(0)}"
            )

    assert not offenders, (
        "Found canonical lane string literals outside the authoritative "
        "source `src/spec_kitty_events/status.py`. The canonical lane "
        "vocabulary must be defined exactly once. Offenders:\n  - "
        + "\n  - ".join(offenders)
        + "\n\nIf one of these is a legitimate reference (e.g., a docstring "
        "or alias map), add it to the allow-list in this test or import the "
        "value from `Lane` instead of using a bare string literal."
    )
