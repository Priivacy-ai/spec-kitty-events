"""Keep local-only state out of the contract-image build context."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _patterns(path: Path) -> set[str]:
    patterns = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            patterns.add(line.rstrip("/"))
    return patterns


def _covered_by_dockerignore(git_pattern: str, docker_patterns: set[str]) -> bool:
    """Translate repo-wide gitignore syntax to this file's recursive Docker form.

    An ignored parent covers every descendant pattern: for example,
    ``**/.claude`` deliberately subsumes Git's ``.claude/commands/`` entry.
    """
    if git_pattern.startswith("!"):
        return False

    parts = git_pattern.lstrip("/").split("/")
    candidates = [f"**/{'/'.join(parts[:end])}" for end in range(1, len(parts) + 1)]
    return any(candidate in docker_patterns for candidate in candidates)


def test_dockerignore_covers_every_gitignore_pattern() -> None:
    git_patterns = _patterns(ROOT / ".gitignore")
    docker_patterns = _patterns(ROOT / ".dockerignore")

    uncovered = sorted(
        pattern
        for pattern in git_patterns
        if not _covered_by_dockerignore(pattern, docker_patterns)
    )

    assert not uncovered, (
        ".dockerignore must cover every .gitignore pattern so a future COPY . . cannot admit "
        f"local-only state; add recursive Docker patterns for: {uncovered!r}"
    )


def test_dockerignore_coverage_requires_an_exact_pattern_or_ignored_parent() -> None:
    assert _covered_by_dockerignore(".claude/commands", {"**/.claude"})
    assert not _covered_by_dockerignore(".new-agent/state", {"**/.claude"})


def test_dockerignore_covers_provenance_sensitive_extras() -> None:
    docker_patterns = _patterns(ROOT / ".dockerignore")
    required = {
        "**/.env",
        "**/.git",
        "**/.kittify/encoding-provenance",
        "**/node_modules",
    }

    assert required <= docker_patterns, (
        "provenance- or credential-sensitive Docker exclusions disappeared: "
        f"{sorted(required - docker_patterns)!r}"
    )
