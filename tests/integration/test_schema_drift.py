"""Integration tests for schema generation and drift detection."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def test_schema_drift_check_passes() -> None:
    """Test that --check mode passes when schemas are up to date."""
    result = subprocess.run(
        [sys.executable, "-m", "spec_kitty_events.schemas.generate", "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Schema drift check failed: {result.stderr}"
    assert "up to date" in result.stdout


def test_schema_drift_check_detects_modification() -> None:
    """Test that --check mode detects when a schema file is modified."""
    # Find the schemas directory
    import spec_kitty_events.schemas

    schema_dir = Path(spec_kitty_events.schemas.__file__).parent
    schema_file = schema_dir / "event.schema.json"

    # Read original content
    original_content = schema_file.read_text(encoding="utf-8")

    try:
        # Modify the schema file
        modified_content = original_content.replace(
            '"spec-kitty-events/event"', '"spec-kitty-events/event-modified"'
        )
        schema_file.write_text(modified_content, encoding="utf-8")

        # Run --check mode
        result = subprocess.run(
            [sys.executable, "-m", "spec_kitty_events.schemas.generate", "--check"],
            capture_output=True,
            text=True,
        )

        # Should detect drift and exit with code 1
        assert result.returncode == 1, "Schema drift check should have failed"
        assert "drift detected" in result.stderr.lower()

    finally:
        # Restore original content
        schema_file.write_text(original_content, encoding="utf-8")

    # Verify restoration worked
    verify_result = subprocess.run(
        [sys.executable, "-m", "spec_kitty_events.schemas.generate", "--check"],
        capture_output=True,
        text=True,
    )
    assert (
        verify_result.returncode == 0
    ), f"Schema restoration failed: {verify_result.stderr}"
