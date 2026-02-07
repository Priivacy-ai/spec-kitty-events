"""Integration tests for error retention policy."""
from datetime import datetime, timedelta
from spec_kitty_events.error_log import ErrorLog
from spec_kitty_events.storage import InMemoryErrorStorage
from spec_kitty_events.models import ErrorEntry


class TestErrorRetentionPolicy:
    """Integration tests for error retention policy."""

    def test_retention_policy_evicts_oldest(self):
        """Test retention policy evicts oldest errors when limit exceeded."""
        # Create storage with max 5 entries
        storage = InMemoryErrorStorage(max_entries=5)
        error_log = ErrorLog(storage)

        # Log 10 errors
        for i in range(10):
            error_log.log_error(ErrorEntry(
                timestamp=datetime.now() + timedelta(seconds=i),
                action_attempted=f"Action {i}",
                error_message=f"Error {i}"
            ))

        # Only last 5 should be retained
        errors = error_log.get_recent_errors(limit=10)
        assert len(errors) == 5

        # Newest first (Action 9, 8, 7, 6, 5)
        assert errors[0].action_attempted == "Action 9"
        assert errors[4].action_attempted == "Action 5"

    def test_retention_policy_exactly_at_limit(self):
        """Test retention policy when exactly at limit (no eviction)."""
        storage = InMemoryErrorStorage(max_entries=5)
        error_log = ErrorLog(storage)

        # Log exactly 5 errors
        for i in range(5):
            error_log.log_error(ErrorEntry(
                timestamp=datetime.now(),
                action_attempted=f"Action {i}",
                error_message="Error"
            ))

        errors = error_log.get_recent_errors(limit=10)
        assert len(errors) == 5  # All retained

    def test_retention_policy_one_over_limit(self):
        """Test retention policy when one entry over limit."""
        storage = InMemoryErrorStorage(max_entries=3)
        error_log = ErrorLog(storage)

        # Log 4 errors (1 over limit)
        for i in range(4):
            error_log.log_error(ErrorEntry(
                timestamp=datetime.now(),
                action_attempted=f"Action {i}",
                error_message="Error"
            ))

        errors = error_log.get_recent_errors(limit=10)
        # Only last 3 retained (Action 0 evicted)
        assert len(errors) == 3
        assert errors[0].action_attempted == "Action 3"  # Newest
        assert errors[2].action_attempted == "Action 1"  # Oldest retained

    def test_retention_policy_multiple_evictions(self):
        """Test retention policy with multiple evictions in sequence."""
        storage = InMemoryErrorStorage(max_entries=2)
        error_log = ErrorLog(storage)

        # Log 5 errors sequentially
        for i in range(5):
            error_log.log_error(ErrorEntry(
                timestamp=datetime.now(),
                action_attempted=f"Action {i}",
                error_message="Error"
            ))

        # Only last 2 retained
        errors = error_log.get_recent_errors(limit=10)
        assert len(errors) == 2
        assert errors[0].action_attempted == "Action 4"
        assert errors[1].action_attempted == "Action 3"

    def test_retention_policy_default_limit(self):
        """Test InMemoryErrorStorage default retention limit (100)."""
        storage = InMemoryErrorStorage()  # Default max_entries=100
        error_log = ErrorLog(storage)

        # Log 150 errors
        for i in range(150):
            error_log.log_error(ErrorEntry(
                timestamp=datetime.now(),
                action_attempted=f"Action {i}",
                error_message="Error"
            ))

        # Only last 100 retained
        errors = error_log.get_recent_errors(limit=200)
        assert len(errors) == 100
        assert errors[0].action_attempted == "Action 149"  # Newest
        assert errors[99].action_attempted == "Action 50"  # Oldest retained
