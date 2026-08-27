#!/usr/bin/env python3
"""Fail if this checkout keeps main's package version while changing ``src/``.

PROGRAM.md §2: "a shared package's version number is spent once — an
in-place amendment to an already-adopted version is forbidden ... bump the
patch number the moment [a consumer has adopted it]." Issue #170 found
``8.2.0`` declared at two distinct trees on ``main`` because a later commit
changed ``from_zeitgeist_attrs``'s decode behaviour under ``src/`` without
bumping the version — this script is the follow-up CI check issue #170 asked
for (issue #175).

Compares the working tree against ``origin/main`` (or ``main`` if there is no
``origin`` remote): if anything under ``src/`` differs and the declared
package version hasn't moved, that is an in-place amendment. Docs-only,
test-only, or config-only changes are unaffected — the version is free to
stay put until something under ``src/`` actually changes.

Deliberately narrower than "walk every commit that ever touched
``pyproject.toml``" (issue #175's literal suggested shape): replayed against
this repo's own history, that walk flags 25 of the 56 commits that have ever
touched ``pyproject.toml``, because a version is legitimately shared by many
ordinary commits before the next bump. Comparing only the current tree
against main's tip, gated on whether ``src/`` actually changed, catches the
real defect without that noise.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)


def _run(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _resolve_base_ref() -> str | None:
    """The commit this checkout will merge into, or None if none is resolvable."""
    for ref in ("origin/main", "main"):
        try:
            _run("rev-parse", "--verify", ref)
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        return ref
    return None


def _version_from_text(text: str, *, where: str) -> str:
    match = _VERSION_RE.search(text)
    if match is None:
        raise RuntimeError(f'no `version = "..."` line found in pyproject.toml at {where}')
    return match.group(1)


def _version_at(ref: str) -> str:
    return _version_from_text(_run("show", f"{ref}:pyproject.toml"), where=ref)


def _current_version() -> str:
    path = _REPO_ROOT / "pyproject.toml"
    return _version_from_text(path.read_text(encoding="utf-8"), where="the working tree")


def check() -> str | None:
    """Return a failure message, or None if the check passes."""
    base_ref = _resolve_base_ref()
    if base_ref is None:
        return None  # no main ref to compare against (e.g. standalone checkout)

    base_sha = _run("rev-parse", base_ref)
    changed = [
        line for line in _run("diff", "--name-only", base_sha, "--", "src/").splitlines() if line
    ]
    if not changed:
        return None  # no functional source changed; keeping the version is fine

    head_version = _current_version()
    base_version = _version_at(base_sha)
    if head_version != base_version:
        return None  # version was bumped

    return (
        f"src/ changed ({len(changed)} file(s)) but pyproject.toml's version "
        f"({head_version!r}) still matches {base_ref}'s tip ({base_sha[:8]}) — "
        "this amends an already-declared version in place. PROGRAM.md §2: bump "
        "the patch number. Changed files:\n  " + "\n  ".join(changed)
    )


def main() -> int:
    message = check()
    if message is None:
        print("version-not-amended: ok")
        return 0
    print(f"version-not-amended: FAIL\n{message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
