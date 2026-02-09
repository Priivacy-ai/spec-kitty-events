"""Unit tests for core data models."""
import uuid
import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError
from ulid import ULID
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
            correlation_id=str(ULID()),
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
                correlation_id=str(ULID()),
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
                correlation_id=str(ULID()),
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
            correlation_id=str(ULID()),
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
            correlation_id=str(ULID()),
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
            "correlation_id": str(ULID()),
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
            correlation_id=str(ULID()),
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
                correlation_id=str(ULID()),
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
                correlation_id=str(ULID()),
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
            correlation_id=str(ULID()),
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
            correlation_id=str(ULID()),
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
            correlation_id=str(ULID()),
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
            correlation_id=str(ULID()),
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
            "correlation_id": str(ULID()),
        }
        event = Event.from_dict(data)
        assert isinstance(event.project_uuid, uuid.UUID)
        assert event.project_uuid == TEST_PROJECT_UUID
        assert event.project_slug == "my-project"


class TestCorrelationId:
    """Tests for the correlation_id field (T007)."""

    def test_correlation_id_valid_ulid(self) -> None:
        """Valid 26-char ULID string accepted."""
        corr = str(ULID())
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=corr,
        )
        assert event.correlation_id == corr

    def test_correlation_id_too_short_rejected(self) -> None:
        """String shorter than 26 chars rejected."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid=TEST_PROJECT_UUID,
                correlation_id="SHORT",
            )

    def test_correlation_id_too_long_rejected(self) -> None:
        """String longer than 26 chars rejected."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid=TEST_PROJECT_UUID,
                correlation_id="A" * 27,
            )

    def test_correlation_id_required(self) -> None:
        """Missing correlation_id rejected."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid=TEST_PROJECT_UUID,
                # correlation_id omitted
            )

    def test_correlation_id_round_trip(self) -> None:
        """to_dict/from_dict preserves correlation_id."""
        corr = str(ULID())
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime(2026, 1, 26, 10, 0, 0),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=corr,
        )
        restored = Event.from_dict(event.to_dict())
        assert restored.correlation_id == corr


class TestSchemaVersion:
    """Tests for the schema_version field (T007)."""

    def test_schema_version_default(self) -> None:
        """Default value is '1.0.0'."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        assert event.schema_version == "1.0.0"

    def test_schema_version_valid_semver(self) -> None:
        """Valid semver '2.1.3' accepted."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
            schema_version="2.1.3",
        )
        assert event.schema_version == "2.1.3"

    def test_schema_version_invalid_two_part(self) -> None:
        """Invalid '1.0' rejected (pattern mismatch)."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid=TEST_PROJECT_UUID,
                correlation_id=str(ULID()),
                schema_version="1.0",
            )

    def test_schema_version_invalid_v_prefix(self) -> None:
        """Invalid 'v1.0.0' rejected (pattern mismatch)."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid=TEST_PROJECT_UUID,
                correlation_id=str(ULID()),
                schema_version="v1.0.0",
            )

    def test_schema_version_round_trip(self) -> None:
        """to_dict/from_dict preserves schema_version."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime(2026, 1, 26, 10, 0, 0),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
            schema_version="2.0.0",
        )
        restored = Event.from_dict(event.to_dict())
        assert restored.schema_version == "2.0.0"


class TestDataTier:
    """Tests for the data_tier field (T007)."""

    def test_data_tier_default(self) -> None:
        """Default value is 0."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
        )
        assert event.data_tier == 0

    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_data_tier_valid_values(self, tier: int) -> None:
        """Values 0-4 accepted."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
            data_tier=tier,
        )
        assert event.data_tier == tier

    def test_data_tier_negative_rejected(self) -> None:
        """Value -1 rejected (ge=0)."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid=TEST_PROJECT_UUID,
                correlation_id=str(ULID()),
                data_tier=-1,
            )

    def test_data_tier_five_rejected(self) -> None:
        """Value 5 rejected (le=4)."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid=TEST_PROJECT_UUID,
                correlation_id=str(ULID()),
                data_tier=5,
            )

    def test_data_tier_non_integer_rejected(self) -> None:
        """Non-integer rejected."""
        with pytest.raises(PydanticValidationError):
            Event(
                event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                event_type="TestEvent",
                aggregate_id="AGG001",
                timestamp=datetime.now(),
                node_id="test-node",
                lamport_clock=0,
                project_uuid=TEST_PROJECT_UUID,
                correlation_id=str(ULID()),
                data_tier="high",  # type: ignore[arg-type]
            )

    def test_data_tier_round_trip(self) -> None:
        """to_dict/from_dict preserves data_tier."""
        event = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime(2026, 1, 26, 10, 0, 0),
            node_id="test-node",
            lamport_clock=0,
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
            data_tier=3,
        )
        restored = Event.from_dict(event.to_dict())
        assert restored.data_tier == 3


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
            correlation_id=str(ULID()),
        )
        event2 = Event(
            event_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            event_type="TestEvent",
            aggregate_id="AGG001",
            timestamp=datetime.now(),
            node_id="node2",
            lamport_clock=5,
            project_uuid=TEST_PROJECT_UUID,
            correlation_id=str(ULID()),
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
