"""Conformance test suite for spec-kitty-events.

Run: pytest --pyargs spec_kitty_events.conformance
"""
from spec_kitty_events.conformance.validators import (
    ConformanceResult,
    ModelViolation,
    SchemaViolation,
    validate_event,
)

__all__ = [
    "ConformanceResult",
    "ModelViolation",
    "SchemaViolation",
    "validate_event",
]
