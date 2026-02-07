"""Unit tests for core data models."""
import uuid
import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError
from spec_kitty_events.models import (
    Event, ErrorEntry, ConflictResolution,
    SpecKittyEventsError, StorageError, ValidationError, CyclicDependencyError
)

TEST_PROJECT_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")


class TestEvent:
    """Tests for Event model."""

    def test_event_creation_valid(self):
        """Test creating a valid event."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Valid ULID
            event_type="TestEvent",
            aggregate_id="AGG001",
            payload={"key": "value"},
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=5,
            causation_id=None,
            project_uuid=TEST_PROJECT_UUID,
        )
        assert event.event_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert event.lamport_clock == 5

    def test_event_validation_empty_event_type(self):
        """Test event validation fails with empty event_type."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="",  # Invalid: empty string
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid=TEST_PROJECT_UUID,
            )

    def test_event_validation_negative_lamport_clock(self):
        """Test event validation fails with negative lamport_clock."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=-1,  # Invalid: negative
                project_uuid=TEST_PROJECT_UUID,
            )

    def test_event_immutability(self):
        """Test event is immutable after creation."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
        )
        with pytest.raises(Exception):  # Pydantic raises FrozenInstanceError
            setattr(event, "lamport_clock", 10)

    def test_event_serialization(self):
        """Test event serialization to dict."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime(2026, 1, 26, 10, 0, 0),
            node_id="test-node",
            lamport_clock=5,
            project_uuid=TEST_PROJECT_UUID,
        )
        data = event.to_dict()
        assert data["event_id"] == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert data["lamport_clock"] == 5

    def test_event_deserialization(self):
        """Test event deserialization from dict."""
        data = {
            "event_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "event_type": "TestEvent",
            "aggregate_id": "AGG001",
            "payload": {},
            "timestamp": datetime(2026, 1, 26, 10, 0, 0),
            "node_id": "test-node",
            "lamport_clock": 5,
            "causation_id": None,
            "project_uuid": TEST_PROJECT_UUID,
        }
        event = Event.from_dict(data)
        assert event.event_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"

    def test_event_project_uuid_required(self):
        """Test event creation fails without project_uuid."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                # project_uuid missing
            )

    def test_event_project_uuid_valid_string(self):
        """Test project_uuid accepts valid UUID string and coerces to uuid.UUID."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=0,
            project_uuid="12345678-1234-5678-1234-567812345678",
        )
        assert isinstance(event.project_uuid, uuid.UUID)
        assert event.project_uuid == TEST_PROJECT_UUID

    def test_event_project_uuid_invalid_string(self):
        """Test project_uuid rejects invalid UUID string."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid="not-a-uuid",
            )

    def test_event_project_uuid_empty_string(self):
        """Test project_uuid rejects empty string."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid="",
            )

    def test_event_project_slug_optional(self):
        """Test project_slug defaults to None when not provided."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
        )
        assert event.project_slug is None

    def test_event_project_slug_with_value(self):
        """Test project_slug accepts string value."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
            project_slug="my-project",
        )
        assert event.project_slug == "my-project"

    def test_event_project_uuid_immutable(self):
        """Test project_uuid is immutable after creation."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
        )
        with pytest.raises(Exception):
            setattr(event, "project_uuid", uuid.uuid4())

    def test_event_serialization_with_project_identity(self):
        """Test to_dict includes project_uuid and project_slug."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime(2026, 1, 26, 10, 0, 0),
            node_id="test-node",
            lamport_clock=5,
            project_uuid=TEST_PROJECT_UUID,
            project_slug="my-project",
        )
        data = event.to_dict()
        assert data["project_uuid"] == TEST_PROJECT_UUID
        assert data["project_slug"] == "my-project"

    def test_event_deserialization_with_project_identity(self):
        """Test from_dict round-trip with project identity fields."""
        data = {
            "event_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "event_type": "TestEvent",
            "aggregate_id": "AGG001",
            "payload": {},
            "timestamp": datetime(2026, 1, 26, 10, 0, 0),
            "node_id": "test-node",
            "lamport_clock": 5,
            "causation_id": None,
            "project_uuid": "12345678-1234-5678-1234-567812345678",
            "project_slug": "my-project",
        }
        event = Event.from_dict(data)
        assert isinstance(event.project_uuid, uuid.UUID)
        assert event.project_uuid == TEST_PROJECT_UUID
        assert event.project_slug == "my-project"


class TestErrorEntry:
    """Tests for ErrorEntry model."""

    def test_error_entry_creation_valid(self):
        """Test creating a valid error entry."""
        entry = ErrorEntry(
            timestamp=datetime.now(),
            action_attempted="Run pytest",
            error_message="AssertionError: test failed",
            resolution="Fixed bug in code",
            agent="codex"
        )
        assert entry.action_attempted == "Run pytest"
        assert entry.agent == "codex"

    def test_error_entry_defaults(self):
        """Test error entry default values."""
        entry = ErrorEntry(
            timestamp=datetime.now(),
            action_attempted="Run pytest",
            error_message="AssertionError"
        )
        assert entry.resolution == ""
        assert entry.agent == "unknown"

    def test_error_entry_validation_empty_action(self):
        """Test error entry validation fails with empty action_attempted."""
        with pytest.raises(PydanticValidationError):
            ErrorEntry(
                timestamp=datetime.now(),
                action_attempted="",  # Invalid: empty string
                error_message="Error"
            )


class TestConflictResolution:
    """Tests for ConflictResolution dataclass."""

    def test_conflict_resolution_creation(self):
        """Test creating a conflict resolution."""
        event1 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node1",
            lamport_clock=5,
            project_uuid=TEST_PROJECT_UUID,
        )
        event2 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=5,
            project_uuid=TEST_PROJECT_UUID,
        )
        resolution = ConflictResolution(
            merged_event=event1,
            resolution_note="Selected node1 via tiebreaker",
            requires_manual_review=False,
            conflicting_events=[event1, event2]
        )
        assert resolution.merged_event == event1
        assert len(resolution.conflicting_events) == 2


class TestExceptions:
    """Tests for custom exceptions."""

    def test_exception_hierarchy(self):
        """Test exception inheritance."""
        assert issubclass(StorageError, SpecKittyEventsError)
        assert issubclass(ValidationError, SpecKittyEventsError)
        assert issubclass(CyclicDependencyError, SpecKittyEventsError)

    def test_exception_raising(self):
        """Test raising custom exceptions."""
        with pytest.raises(SpecKittyEventsError):
            raise StorageError("Storage failed")
