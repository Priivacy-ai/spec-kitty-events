"""Shared pytest fixtures for all tests."""
import pytest
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ulid import ULID

from spec_kitty_events import Event


def make_event(**overrides: Any) -> Event:
    """Build an Event with defaults for all required fields.

    Callers override specific fields as needed. This avoids updating
    every Event() call when new required fields are added.
    """
    defaults: dict[str, Any] = {
        "event_id": str(ULID()),
        "event_type": "TestEvent",
        "aggregate_id": "test-001",
        "payload": {},
        "timestamp": datetime.now(timezone.utc),
        "node_id": "test-node",
        "lamport_clock": 0,
        "project_uuid": uuid4(),
        "correlation_id": str(ULID()),
    }
    defaults.update(overrides)
    return Event(**defaults)


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
