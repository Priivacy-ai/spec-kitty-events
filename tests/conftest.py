"""Shared pytest fixtures for all tests."""
import pytest
from typing import Any


# In-memory storage adapters will be implemented in WP03
# For now, just define fixture placeholders that will be populated later


@pytest.fixture
def in_memory_event_store() -> Any:
    """Placeholder - will be implemented in WP03."""
    pass


@pytest.fixture
def in_memory_clock_storage() -> Any:
    """Placeholder - will be implemented in WP03."""
    pass


@pytest.fixture
def in_memory_error_storage() -> Any:
    """Placeholder - will be implemented in WP03."""
    pass
