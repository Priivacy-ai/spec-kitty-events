"""Unit tests for ErrorLog class."""
import pytest
from datetime import datetime
from spec_kitty_events.error_log import ErrorLog
from spec_kitty_events.storage import InMemoryErrorStorage
from spec_kitty_events.models import ErrorEntry


class TestErrorLog:
    """Tests for ErrorLog class."""

    def test_log_error_and_retrieve(self):
        """Test logging and retrieving a single error."""
        storage = InMemoryErrorStorage()
        error_log = ErrorLog(storage)

        entry = ErrorEntry(
            timestamp=datetime.now(),
            action_attempted="Run pytest",
            error_message="AssertionError: test failed"
        )
        error_log.log_error(entry)

        errors = error_log.get_recent_errors(limit=10)
        assert len(errors) == 1
        assert errors[0].action_attempted == "Run pytest"

    def test_log_multiple_errors_reverse_chronological_order(self):
        """Test retrieving multiple errors in reverse chronological order."""
        storage = InMemoryErrorStorage()
        error_log = ErrorLog(storage)

        e1 = ErrorEntry(
            timestamp=datetime(2026, 1, 26, 10, 0, 0),
            action_attempted="Action 1",
            error_message="Error 1"
        )
        e2 = ErrorEntry(
            timestamp=datetime(2026, 1, 26, 11, 0, 0),
            action_attempted="Action 2",
            error_message="Error 2"
        )
        e3 = ErrorEntry(
            timestamp=datetime(2026, 1, 26, 12, 0, 0),
            action_attempted="Action 3",
            error_message="Error 3"
        )

        error_log.log_error(e1)
        error_log.log_error(e2)
        error_log.log_error(e3)

        errors = error_log.get_recent_errors(limit=10)
        # Newest first
        assert len(errors) == 3
        assert errors[0].action_attempted == "Action 3"
        assert errors[1].action_attempted == "Action 2"
        assert errors[2].action_attempted == "Action 1"

    def test_get_recent_errors_limit(self):
        """Test get_recent_errors respects limit parameter."""
        storage = InMemoryErrorStorage()
        error_log = ErrorLog(storage)

        for i in range(10):
            error_log.log_error(ErrorEntry(
                timestamp=datetime.now(),
                action_attempted=f"Action {i}",
                error_message="Error"
            ))

        errors = error_log.get_recent_errors(limit=3)
        assert len(errors) == 3

    def test_get_recent_errors_invalid_limit(self):
        """Test get_recent_errors raises error on invalid limit."""
        storage = InMemoryErrorStorage()
        error_log = ErrorLog(storage)

        with pytest.raises(ValueError, match="must be ≥ 1"):
            error_log.get_recent_errors(limit=0)

    def test_get_recent_errors_empty_log(self):
        """Test get_recent_errors returns empty list when no errors logged."""
        storage = InMemoryErrorStorage()
        error_log = ErrorLog(storage)

        errors = error_log.get_recent_errors(limit=10)
        assert errors == []

    def test_error_log_delegates_to_storage(self):
        """Test ErrorLog delegates to storage adapter (no internal state)."""
        storage = InMemoryErrorStorage()
        error_log = ErrorLog(storage)

        entry = ErrorEntry(
            timestamp=datetime.now(),
            action_attempted="Action",
            error_message="Error"
        )
        error_log.log_error(entry)

        # Verify storage has the entry (ErrorLog doesn't store internally)
        assert len(storage.load_recent(limit=10)) == 1
