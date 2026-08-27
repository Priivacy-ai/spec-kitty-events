"""Cross-repo drill (spec-kitty-events#17): proves the local mirror of
zeitgeist's ``FORBIDDEN_KEYS_V1`` (``zeitgeist_attrs.py``) has not drifted
from the zeitgeist repo it was mirrored from.

This package deliberately never imports zeitgeist as a runtime dependency
(``zeitgeist_attrs`` module docstring: "zeitgeist owns transport policy,
this package owns vocabulary, and neither imports the other"). Importing
the package would also pull in zeitgeist's runtime deps (fastapi, uvicorn,
mcp) for no other reason than this one drill. So this drill reads
``zeitgeist/capabilities.py`` as TEXT from the sibling checkout and parses
the two module-level constants with ``ast`` — no import, no execution of
zeitgeist code.

Skips (does not fail) when no sibling zeitgeist checkout is available:
``$SK_HOME`` defaults to ``/work``, matching the sibling-checkout layout
every sk-* VM in this programme uses (planning's ``bin/ci-run.sh``), but
that layout is not guaranteed for every consumer of this package.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from spec_kitty_events.zeitgeist_attrs import (
    ZEITGEIST_FORBIDDEN_KEYS_V1,
    ZEITGEIST_FORBIDDEN_KEYS_VERSION,
)


def _zeitgeist_capabilities_path() -> Path | None:
    sk_home = Path(os.environ.get("SK_HOME", "/work"))
    path = sk_home / "zeitgeist" / "zeitgeist" / "capabilities.py"
    return path if path.is_file() else None


def _module_level_value(source: str, name: str) -> ast.expr:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            return node.value
    raise AssertionError(f"{name} not found as a module-level assignment")


def _literal_eval_frozenset_call(node: ast.expr) -> frozenset:
    if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "frozenset":
        node = node.args[0]
    return frozenset(ast.literal_eval(node))


def test_forbidden_keys_v1_matches_zeitgeist_source() -> None:
    path = _zeitgeist_capabilities_path()
    if path is None:
        pytest.skip(
            "no sibling zeitgeist checkout at $SK_HOME/zeitgeist/zeitgeist/capabilities.py "
            "(SK_HOME defaults to /work) -- this drill reads zeitgeist's source directly "
            "since this repo never imports the zeitgeist package (spec-kitty-events#17)"
        )
    source = path.read_text()

    zeitgeist_keys = _literal_eval_frozenset_call(_module_level_value(source, "FORBIDDEN_KEYS_V1"))
    assert zeitgeist_keys == ZEITGEIST_FORBIDDEN_KEYS_V1, (
        "zeitgeist's FORBIDDEN_KEYS_V1 has diverged from the mirror in "
        "zeitgeist_attrs.ZEITGEIST_FORBIDDEN_KEYS_V1 -- update the mirror and its "
        "provenance comment together (spec-kitty-events#17)"
    )

    zeitgeist_version = ast.literal_eval(_module_level_value(source, "FORBIDDEN_KEYS_VERSION"))
    assert zeitgeist_version == ZEITGEIST_FORBIDDEN_KEYS_VERSION, (
        "zeitgeist bumped FORBIDDEN_KEYS_VERSION without a matching bump to "
        "zeitgeist_attrs.ZEITGEIST_FORBIDDEN_KEYS_VERSION -- treat this as a new "
        "version to mirror, not a patch to V1 (spec-kitty-events#17)"
    )
