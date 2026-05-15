"""Conformance test suite for spec-kitty-events.

Run: pytest --pyargs spec_kitty_events.conformance
"""
from spec_kitty_events.conformance.loader import (
    FixtureCase,
    load_fixtures,
    load_replay_stream,
)
from spec_kitty_events.conformance.pytest_helpers import (
    assert_lane_mapping,
    assert_payload_conforms,
    assert_payload_fails,
)
from spec_kitty_events.conformance.timestamp_semantics import (
    TimestampSubstitutionError,
    assert_producer_occurrence_preserved,
    load_timestamp_semantics_fixture,
)
from spec_kitty_events.conformance.validators import (
    ConformanceResult,
    ModelViolation,
    SchemaViolation,
    validate_event,
)

__all__ = [
    "ConformanceResult",
    "FixtureCase",
    "ModelViolation",
    "SchemaViolation",
    "TimestampSubstitutionError",
    "assert_lane_mapping",
    "assert_payload_conforms",
    "assert_payload_fails",
    "assert_producer_occurrence_preserved",
    "load_fixtures",
    "load_replay_stream",
    "load_timestamp_semantics_fixture",
    "validate_event",
]
