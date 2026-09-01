"""P1 (F1 contract-freeze draft F1.md §4): built-wheel content test.

Builds a real (non-editable) wheel using the exact ``[build-system]``
backend already declared in ``pyproject.toml`` (``setuptools.build_meta``)
with no network access, and asserts the artifacts F1-T1's acceptance
criteria names are actually inside it: ``support_matrix.json``, the
``HarnessObservation`` JSON schema, and the new
``harness_observation/{valid,invalid,replay}`` fixture files. An editable
install (what the rest of this test session runs against) never exercises
``[tool.setuptools.package-data]`` the way a real distribution does, so
this is the only test in the suite that would catch a stale/wrong
package-data glob (the exact defect Renata's finding #2 flagged: three
``harness_observation/*`` globs were added to ``pyproject.toml`` ahead of
any file existing to match them).

Uses ``setuptools.build_meta.build_wheel`` directly, not the ``build`` PEP
517 orchestrator package, so no dependency beyond the project's own
already-declared ``[build-system] requires = ["setuptools>=61.0", "wheel"]``
is needed -- only ``setuptools``/``wheel`` must be present in the running
interpreter (install offline via
``UV_OFFLINE=1 uv pip install setuptools wheel`` if this test skips).
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent

_REQUIRED_MEMBERS = (
    "spec_kitty_events/support_matrix.json",
    "spec_kitty_events/schemas/harness_observation_payload.schema.json",
    "spec_kitty_events/schemas/mission_reopened_payload.schema.json",
    "spec_kitty_events/schemas/follow_up_recorded_payload.schema.json",
    "spec_kitty_events/conformance/fixtures/harness_observation/valid/presence_minimal.json",
    "spec_kitty_events/conformance/fixtures/harness_observation/invalid/missing_kind.json",
    "spec_kitty_events/conformance/fixtures/harness_observation/replay/lifecycle_with_observations.jsonl",
    "spec_kitty_events/conformance/fixtures/harness_observation/replay/lifecycle_with_observations_output.json",
    "spec_kitty_events/conformance/fixtures/class_taxonomy/envelope_strict_journal/valid_mission_started_with_slug.json",
    # E2: volatile mission/WP moment codecs ship their fixture goldens.
    "spec_kitty_events/zeitgeist_attrs.py",
    "spec_kitty_events/conformance/fixtures/zeitgeist_attrs/valid/wp_status_changed_planned_doing.json",
    "spec_kitty_events/conformance/fixtures/zeitgeist_attrs/invalid/wp_status_changed_unknown_attr.json",
)


def _build_backend_available() -> bool:
    result = subprocess.run(
        [sys.executable, "-c", "import setuptools.build_meta, wheel"],
        capture_output=True,
    )
    return result.returncode == 0


@pytest.mark.skipif(
    not _build_backend_available(),
    reason=(
        "setuptools/wheel not importable in this interpreter -- install "
        "offline via `UV_OFFLINE=1 uv pip install setuptools wheel` to run "
        "this test."
    ),
)
def test_built_wheel_contains_f1_t1_package_data(tmp_path: Path) -> None:
    build_script = (
        f"from setuptools.build_meta import build_wheel\nprint(build_wheel({str(tmp_path)!r}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", build_script],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Wheel build failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    wheel_name = result.stdout.strip().splitlines()[-1]
    wheel_path = tmp_path / wheel_name
    assert wheel_path.is_file(), f"Expected wheel at {wheel_path}"

    with zipfile.ZipFile(wheel_path) as zf:
        names = set(zf.namelist())

    missing = [member for member in _REQUIRED_MEMBERS if member not in names]
    assert not missing, (
        f"Built wheel {wheel_name} is missing F1-T1 package-data member(s): "
        f"{missing}. Check [tool.setuptools.package-data] globs in "
        f"pyproject.toml against the files actually on disk."
    )
