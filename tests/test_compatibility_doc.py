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
from packaging.version import Version

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


# ---------------------------------------------------------------------------
# COMPATIBILITY.md's section-ordering contract (issue #181, MINOR from the
# adversarial squad pass 2 on PR #152, head 3e25993).
#
# COMPATIBILITY.md:10-11 states: "Sections below are ordered newest-first by
# the release that introduced them." An unreleased `## Known gap (not yet
# closed)` section carries no version number and must precede every released
# section regardless of when the gap it describes will close. Neither half
# was enforced -- a future in-place rework of the open control-character gap
# (added by #119, expected to close when #104 merges) into a normal, dated
# entry while leaving it sitting above `## \`8.0.0\`` would silently violate
# the contract this document states, with no test failing.
#
# Unversioned policy sections (`## Canonical On-Wire Policy`, `## Forbidden
# Legacy Surfaces`, `## Versioning`, `## Quick Reference`, ...) are
# interleaved after the released sections and are deliberately not part of
# assertion 1 -- they carry no version and are not sorted. `##
# \`8.0.0\`` uses backticks; `## Decision Moment V1 (4.0.0)` carries its
# version in parentheses instead -- both spellings must be recognized or the
# checker quietly skips the second one.
# ---------------------------------------------------------------------------

_SECTION_HEADING_RE = re.compile(r"^## (.+)$", re.M)
_HEADING_VERSION_RE = re.compile(r"`(\d+(?:\.\d+){2})`|\((\d+(?:\.\d+){2})\)")
_KNOWN_GAP_HEADING_RE = re.compile(r"^Known gap \(not yet closed\)")


def _heading_version(heading: str) -> str | None:
    """Extract a `X.Y.Z` version from a '## ' heading's text, if present.

    Recognizes both spellings this document uses: backticked (`` `8.0.0` ``)
    and parenthetical (``(4.0.0)``) -- the latter is how `## Decision Moment
    V1 (4.0.0)` states its version, and would be silently skipped by a
    backtick-only pattern.
    """
    match = _HEADING_VERSION_RE.search(heading)
    if match is None:
        return None
    return match.group(1) or match.group(2)


def _parse_section_headings(text: str) -> list[str]:
    """Top-level ('## ') section headings, in document order.

    ``^## `` (exactly two hashes then a space) deliberately excludes '### '
    subsections -- e.g. the `6.1.0`/`6.0.0` entries nested under '##
    Versioning' -- which are not top-level release sections and would
    otherwise appear interleaved out of order with the real ones.
    """
    return _SECTION_HEADING_RE.findall(text)


def _versioned_headings_are_newest_first(headings: list[str]) -> bool:
    parsed = [Version(v) for v in (_heading_version(h) for h in headings) if v is not None]
    return parsed == sorted(parsed, reverse=True)


def _known_gap_precedes_every_versioned_heading(headings: list[str]) -> bool:
    versioned_indices = [i for i, h in enumerate(headings) if _heading_version(h) is not None]
    if not versioned_indices:
        return True
    first_versioned = min(versioned_indices)
    gap_indices = (i for i, h in enumerate(headings) if _KNOWN_GAP_HEADING_RE.match(h))
    return all(i < first_versioned for i in gap_indices)


def test_heading_version_recognizes_both_spellings() -> None:
    assert _heading_version("`8.0.0` -- Sync, legacy-envelope surfaces deleted") == "8.0.0"
    assert _heading_version("Decision Moment V1 (4.0.0)") == "4.0.0"
    assert _heading_version("Canonical On-Wire Policy") is None
    assert _heading_version("Known gap (not yet closed) -- some gap") is None


def test_parse_section_headings_ignores_level_three_subsections() -> None:
    """`### ` subsections (e.g. the `6.1.0`/`6.0.0` entries under '##
    Versioning') are not top-level release sections and must not be parsed
    as one -- ``^## `` matches on exactly two hashes.
    """
    text = "## Versioning\n\n### Post-mission lifecycle events (6.1.0)\n\n## `8.0.0` -- x\n"
    assert _parse_section_headings(text) == ["Versioning", "`8.0.0` -- x"]


def test_versioned_headings_helper_detects_out_of_order_versions() -> None:
    """Proves the ordering check actually rejects a bad ordering, not just
    passes trivially on the current, already-compliant document.
    """
    assert not _versioned_headings_are_newest_first(["`7.0.0` -- first", "`8.0.0` -- second"])
    assert _versioned_headings_are_newest_first(["`8.0.0` -- first", "`7.0.0` -- second"])


def test_known_gap_helper_detects_known_gap_after_versioned_heading() -> None:
    """Proves the precedence check actually rejects a known-gap heading that
    sorts after a versioned one -- the exact drift scenario #181 describes.
    """
    assert not _known_gap_precedes_every_versioned_heading(
        ["`8.0.0` -- first", "Known gap (not yet closed) -- late"]
    )
    assert _known_gap_precedes_every_versioned_heading(
        ["Known gap (not yet closed) -- early", "`8.0.0` -- second"]
    )
    assert _known_gap_precedes_every_versioned_heading(["`8.0.0` -- no gap heading at all"])


def test_compatibility_doc_versioned_sections_are_newest_first() -> None:
    """Assertion 1 of the ordering contract (COMPATIBILITY.md:10-11)."""
    headings = _parse_section_headings(_COMPATIBILITY_PATH.read_text(encoding="utf-8"))
    versions = [_heading_version(h) for h in headings]
    versions = [v for v in versions if v is not None]
    assert versions, "No versioned '## ' headings found in COMPATIBILITY.md"
    assert _versioned_headings_are_newest_first(headings), (
        f"COMPATIBILITY.md's versioned '## ' headings are not newest-first in "
        f"document order: {versions}. Per COMPATIBILITY.md:10-11, released "
        f"sections must be ordered newest-first by the release that "
        f"introduced them."
    )


def test_compatibility_doc_known_gap_precedes_every_versioned_section() -> None:
    """Assertion 2 of the ordering contract (COMPATIBILITY.md:10-14).

    Guards the concrete drift scenario #181 dated: the open
    `to_zeitgeist_attrs` control-character gap (added by #119, expected to
    close when #104 merges) getting reworded in place into a normal,
    versioned entry while staying above '## `8.0.0`' would violate this
    silently were it not for this test. Passes vacuously if the gap has
    since closed and no '## Known gap' heading remains -- that is a valid
    state, not a violation.
    """
    headings = _parse_section_headings(_COMPATIBILITY_PATH.read_text(encoding="utf-8"))
    assert _known_gap_precedes_every_versioned_heading(headings), (
        "A '## Known gap (not yet closed)' heading in COMPATIBILITY.md sorts "
        "after a versioned release section. Per COMPATIBILITY.md:10-14, an "
        "unreleased known-gap section carries no version number and must "
        "precede every released section, regardless of when the gap it "
        "describes will close."
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
