"""Reject reintroduction of the retired Team Kitty product spelling."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
SCANNED = (
    ROOT / "src",
    ROOT / "README.md",
    ROOT / "COMPATIBILITY.md",
    ROOT / "contracts" / "README.md",
)
HISTORICAL_MISSION = "team" + "space-event-contract-foundation"
LEGACY_INPUT_KEYS = {
    "team" + "space_id",
    "team" + "space_ref",
    "team" + "space_member_id",
}


def _files() -> list[Path]:
    files: list[Path] = []
    for path in SCANNED:
        if path.is_file():
            files.append(path)
        else:
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.suffix in {".py", ".json", ".md"}
            )
    return files


def test_active_contracts_use_team_kitty_workspace_vocabulary() -> None:
    forbidden_product_spelling = "team" + "space"
    violations: list[str] = []

    for path in _files():
        for line_number, line in enumerate(path.read_text().splitlines(), start=1):
            lowered = line.lower()
            if forbidden_product_spelling not in lowered:
                continue
            if HISTORICAL_MISSION in lowered:
                continue
            if any(key in lowered for key in LEGACY_INPUT_KEYS) and (
                "aliaschoices" in lowered or "read-only v6 migration alias" in lowered
            ):
                continue
            violations.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")

    assert not violations, "Retired product spelling found:\n" + "\n".join(violations)
