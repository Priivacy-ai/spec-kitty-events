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

import re
from pathlib import Path

from spec_kitty_events import __version__

_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMPATIBILITY_PATH = _REPO_ROOT / "COMPATIBILITY.md"

# The single declaration, e.g. ``**Current package version**: `6.1.0` ``
_DECLARATION = re.compile(r"^\*\*Current package version\*\*:\s*`([^`]+)`\s*$", re.M)


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
