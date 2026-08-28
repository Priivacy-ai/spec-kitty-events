"""Pin ``COMPATIBILITY.md`` to the real package version.

``COMPATIBILITY.md`` is the public compatibility policy for this package and
for its two consumer repos. ``contracts/versioning-and-compatibility.md`` makes
updating it a required artifact on every major bump — but nothing in CI checked
that, and the document spent the whole of ``6.0.0`` and ``6.1.0`` asserting in
present tense that the current release was ``5.0.0`` while ``pyproject.toml``
said otherwise.

These tests close that gap. The document declares its version exactly once, in
a machine-readable line, and that line must equal ``__version__``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from spec_kitty_events import __version__, forbidden_keys, strict

_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMPATIBILITY_PATH = _REPO_ROOT / "COMPATIBILITY.md"
_README_PATH = _REPO_ROOT / "README.md"

# The single declaration, e.g. ``**Current package version**: `6.1.0` ``
_DECLARATION = re.compile(r"^\*\*Current package version\*\*:\s*`([^`]+)`\s*$", re.M)

# README.md's own declaration line, e.g.
# ``**Package Version**: `7.0.0` | **Cutover Contract**: `3.0.0` | ...``
_README_DECLARATION = re.compile(r"^\*\*Package Version\*\*:\s*`([^`]+)`", re.M)


def test_compatibility_doc_exists() -> None:
    """Guard: if the file is renamed, the rest of these tests must not no-op."""
    assert _COMPATIBILITY_PATH.is_file(), f"COMPATIBILITY.md not found at {_COMPATIBILITY_PATH}"


def test_compatibility_doc_declares_version_exactly_once() -> None:
    """Exactly one machine-readable version declaration.

    Two declarations can disagree; zero means the next test silently passes on
    an empty match set.
    """
    matches = _DECLARATION.findall(_COMPATIBILITY_PATH.read_text(encoding="utf-8"))
    assert len(matches) == 1, (
        f"Expected exactly one '**Current package version**: `X.Y.Z`' line in "
        f"COMPATIBILITY.md, found {len(matches)}: {matches}. State the version "
        f"once and reference it elsewhere."
    )


def test_compatibility_doc_version_matches_package() -> None:
    """The declared version equals ``spec_kitty_events.__version__``."""
    match = _DECLARATION.search(_COMPATIBILITY_PATH.read_text(encoding="utf-8"))
    assert match is not None, "No '**Current package version**' declaration in COMPATIBILITY.md"
    declared = match.group(1)
    assert declared == __version__, (
        f"COMPATIBILITY.md declares package version {declared!r} but the package "
        f"is {__version__!r}. Per contracts/versioning-and-compatibility.md, "
        f"COMPATIBILITY.md is a required artifact on every bump — update the "
        f"declaration and add a section describing the release."
    )


def test_promoted_contracts_are_present() -> None:
    """The durable contracts COMPATIBILITY.md links to actually exist.

    ``CHANGELOG.md`` and ``tests/test_lane_vocabulary.py`` both cite
    ``contracts/lane-vocabulary.md`` by that path; those citations dangled for
    three majors while the document lived only in a mission folder.
    """
    missing = [
        name
        for name in ("lane-vocabulary.md", "versioning-and-compatibility.md")
        if not (_REPO_ROOT / "contracts" / name).is_file()
    ]
    assert not missing, (
        f"Missing durable contract(s) under contracts/: {missing}. These are "
        f"referenced by CHANGELOG.md, COMPATIBILITY.md, and "
        f"tests/test_lane_vocabulary.py by repo-root path."
    )


# ---------------------------------------------------------------------------
# README.md's own version declaration (Renata HANDBACK_PACKET_REPAIR finding
# #5, LOW): README.md carries the identical stale-version failure mode
# COMPATIBILITY.md had before test_compatibility_doc_version_matches_package
# was written -- it "spent the whole of 6.0.0 and 6.1.0" asserting 5.0.0.
# README.md was hand-fixed to 7.0.0 in this release; this pin is what keeps
# it from going stale again, mirroring test_compatibility_doc_version_
# matches_package's shape exactly.
# ---------------------------------------------------------------------------


def test_readme_exists() -> None:
    assert _README_PATH.is_file(), f"README.md not found at {_README_PATH}"


def test_readme_declares_version_exactly_once() -> None:
    matches = _README_DECLARATION.findall(_README_PATH.read_text(encoding="utf-8"))
    assert len(matches) == 1, (
        f"Expected exactly one '**Package Version**: `X.Y.Z`' line in "
        f"README.md, found {len(matches)}: {matches}."
    )


def test_readme_version_matches_package() -> None:
    """The declared version equals ``spec_kitty_events.__version__``."""
    match = _README_DECLARATION.search(_README_PATH.read_text(encoding="utf-8"))
    assert match is not None, "No '**Package Version**' declaration in README.md"
    declared = match.group(1)
    assert declared == __version__, (
        f"README.md declares package version {declared!r} but the package "
        f"is {__version__!r}. Per contracts/versioning-and-compatibility.md, "
        f"user-facing docs are a required artifact on every bump -- update "
        f"the declaration."
    )


# ---------------------------------------------------------------------------
# COMPATIBILITY.md's `8.0.0` migration recipe, executed against the
# cutover_boundary fixtures (planning#95, MINOR from PR #84 pass 2).
#
# COMPATIBILITY.md documents an executable contract for callers whose event
# type is outside `strict.STRICT_EVENT_TYPES` (`validate_strict_envelope`
# rejects those with UNKNOWN_EVENT_TYPE regardless of shape, so it isn't an
# option for them): reproduce the removed cutover gate's checks directly --
# a forbidden-key walk, an explicit schema_version check, a forbidden legacy
# aggregate-name prefix check, and a forbidden legacy event-name check. No
# test executed that recipe, so it could drift from the boundary it claims
# to police -- exactly what happened twice on PR #84 (pass 1 omitted the
# aggregate check, pass 2 omitted the event-name check). `_ADMITTED_BY_
# DOCUMENTED_RECIPE` is the recipe transcribed verbatim from
# COMPATIBILITY.md's "8.0.0" section; if the two ever disagree, update both
# together.
# ---------------------------------------------------------------------------

_CUTOVER_BOUNDARY_REJECTED_DIR = (
    _REPO_ROOT
    / "src"
    / "spec_kitty_events"
    / "conformance"
    / "fixtures"
    / "cutover_boundary"
    / "rejected_by_strict_profile"
)

_FORBIDDEN_LEGACY_EVENT_NAMES = frozenset({"FeatureCreated", "FeatureClosed"})


def _admitted_by_documented_recipe(record: dict[str, Any]) -> bool:
    """Mirror COMPATIBILITY.md's documented `8.0.0` migration recipe.

    Returns True only if ``record`` passes every documented check; False as
    soon as one check finds a defect.
    """
    if (
        forbidden_keys.validate_no_forbidden_keys(
            record, forbidden=forbidden_keys.FORBIDDEN_LEGACY_KEYS
        )
        is not None
    ):
        return False
    if record.get("schema_version") != "3.0.0":
        return False
    aggregate_id = record.get("aggregate_id")
    if (
        isinstance(aggregate_id, str)
        and aggregate_id.split("/", 1)[0] in strict.FORBIDDEN_LEGACY_AGGREGATE_NAMES
    ):
        return False
    if record.get("event_type") in _FORBIDDEN_LEGACY_EVENT_NAMES:
        return False
    return True


def _cutover_boundary_rejected_fixtures() -> list[Path]:
    paths = sorted(_CUTOVER_BOUNDARY_REJECTED_DIR.glob("*.json"))
    assert paths, f"No fixtures found under {_CUTOVER_BOUNDARY_REJECTED_DIR}"
    return paths


@pytest.mark.parametrize(
    "fixture_path",
    _cutover_boundary_rejected_fixtures(),
    ids=[p.stem for p in _cutover_boundary_rejected_fixtures()],
)
def test_documented_recipe_rejects_cutover_boundary_fixtures(
    fixture_path: Path,
) -> None:
    """The documented recipe rejects every `rejected_by_strict_profile` fixture.

    These fixtures are the pinned authority for the boundary the removed
    cutover gate used to police. A recipe that admits any of them has
    drifted from that boundary -- as the merged recipe once did for
    ``legacy_event_name.json`` (pass 1: omitted aggregate check; pass 2:
    omitted event-name check, which is the one this fixture needs, since its
    aggregate_id is ``mission/...`` and the aggregate check alone would not
    catch it).
    """
    wrapper: dict[str, Any] = json.loads(fixture_path.read_text(encoding="utf-8"))
    record = wrapper["input"]
    assert not _admitted_by_documented_recipe(record), (
        f"{fixture_path.name}: the documented `8.0.0` migration recipe "
        f"admitted this record, but it is pinned as rejected by the "
        f"cutover boundary. The recipe in COMPATIBILITY.md has drifted -- "
        f"update _admitted_by_documented_recipe (and the doc, if the doc is "
        f"wrong) to match."
    )


@pytest.mark.parametrize("aggregate_id", [None, 42, ["feature", "123"]])
def test_documented_recipe_does_not_raise_on_non_string_aggregate_id(
    aggregate_id: Any,
) -> None:
    """A wire record with a present-but-non-string `aggregate_id` must not raise.

    planning#93 / EXPERIMENTAL-spec-kitty-events#93 (MINOR from PR #84 pass 2):
    the recipe previously used `record.get("aggregate_id", "").split(...)`,
    whose default only applies when the key is *absent* -- a record carrying
    `aggregate_id: null` (or any other non-string) still returns that stored
    value, so `.split` raised `AttributeError` instead of mirroring
    `strict.py`'s own `isinstance(aggregate_id, str)` guard, which treats a
    non-string as not-forbidden rather than raising.
    """
    record = {"schema_version": "3.0.0", "aggregate_id": aggregate_id}
    assert _admitted_by_documented_recipe(record) is True
