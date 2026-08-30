"""Guard: catch a future in-place amendment of an already-declared package version.

See ``contracts/versioning-and-compatibility.md`` and PROGRAM.md §2 ("a shared
package's version number is spent once"). Issue #170 found ``8.2.0`` declared
at two distinct trees on ``main`` because a later commit changed
``from_zeitgeist_attrs``'s decode behaviour under ``src/`` without bumping the
patch. This is the CI check issue #170 asked for as a follow-up (issue #175).

``scripts/check_version_not_amended.py`` compares the working tree against
``origin/main`` (or ``main``): if ``src/`` differs and the package version
hasn't moved, that's an in-place amendment. Walking the *entire* history of
every commit that ever touched ``pyproject.toml`` (issue #175's literal
suggested shape) was tried and rejected — replayed against this repo's own
history it flags 25 of the 56 commits that have ever touched
``pyproject.toml``, because a version is legitimately shared by many ordinary
commits before the next bump; that check would fail on the very next
unrelated PR. Comparing only against main's tip, gated on whether ``src/``
actually changed, catches the real defect (behaviour drift under an unchanged
version) without that noise.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_version_not_amended as _checker  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "check_version_not_amended.py"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def _init_repo_with_base_commit(root: Path, extra_files: dict[str, str] | None = None) -> None:
    (root / "src").mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n', encoding="utf-8")
    (root / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    for name, content in (extra_files or {}).items():
        (root / name).write_text(content, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "branch", "-M", "main")


def test_passes_when_version_bumped(tmp_path, monkeypatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _init_repo_with_base_commit(root)

    (root / "pyproject.toml").write_text('[project]\nversion = "1.1.0"\n', encoding="utf-8")
    (root / "src" / "mod.py").write_text("x = 2\n", encoding="utf-8")

    monkeypatch.setattr(_checker, "_REPO_ROOT", root)
    assert _checker.check() is None


def test_fails_on_in_place_amendment(tmp_path, monkeypatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _init_repo_with_base_commit(root)

    # src/ changes, version does not — the exact shape of #170's b67b7e0.
    (root / "src" / "mod.py").write_text("x = 2\n", encoding="utf-8")

    monkeypatch.setattr(_checker, "_REPO_ROOT", root)
    message = _checker.check()
    assert message is not None
    assert "mod.py" in message
    assert "1.0.0" in message


def test_passes_when_only_docs_change(tmp_path, monkeypatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _init_repo_with_base_commit(root, extra_files={"README.md": "hello\n"})

    (root / "README.md").write_text("hello world\n", encoding="utf-8")  # docs-only

    monkeypatch.setattr(_checker, "_REPO_ROOT", root)
    assert _checker.check() is None


def test_passes_when_no_main_ref_resolvable(tmp_path, monkeypatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "src").mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n', encoding="utf-8")
    (root / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    # No branch named "main" and no "origin" remote — nothing to compare against.

    monkeypatch.setattr(_checker, "_REPO_ROOT", root)
    assert _checker.check() is None


def test_script_passes_against_this_repo() -> None:
    """Smoke test: the script runs clean against the actual checkout."""
    result = subprocess.run(
        [sys.executable, str(_SCRIPT)], capture_output=True, text=True, cwd=_REPO_ROOT
    )
    assert result.returncode == 0, result.stderr
