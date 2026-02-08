"""Placeholder test to verify pytest runs correctly."""

from importlib.metadata import version

from packaging.version import Version

import spec_kitty_events


def test_placeholder() -> None:
    """Verify pytest is configured correctly and package is importable."""
    assert Version(spec_kitty_events.__version__) == Version(version("spec-kitty-events"))
