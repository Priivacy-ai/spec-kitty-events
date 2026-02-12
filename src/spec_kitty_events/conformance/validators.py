"""Dual-layer validation for spec-kitty-events contracts.

This module provides conformance validation combining:
1. Pydantic model validation (primary layer)
2. JSON Schema validation (optional secondary layer)

The validator gracefully degrades if jsonschema is unavailable, unless
strict=True is specified.
"""

from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Type, Union

from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.gates import GateFailedPayload, GatePassedPayload
from spec_kitty_events.lifecycle import (
    MissionCancelledPayload,
    MissionCompletedPayload,
    MissionStartedPayload,
    PhaseEnteredPayload,
    ReviewRollbackPayload,
)
from spec_kitty_events.models import Event
from spec_kitty_events.status import StatusTransitionPayload


@dataclass(frozen=True)
class ModelViolation:
    """A violation detected by Pydantic model validation."""

    field: str
    message: str
    violation_type: str
    input_value: object


@dataclass(frozen=True)
class SchemaViolation:
    """A violation detected by JSON Schema validation."""

    json_path: str
    message: str
    validator: str
    validator_value: object
    schema_path: Tuple[Union[str, int], ...]


@dataclass(frozen=True)
class ConformanceResult:
    """Result of dual-layer conformance validation."""

    valid: bool
    model_violations: Tuple[ModelViolation, ...]
    schema_violations: Tuple[SchemaViolation, ...]
    schema_check_skipped: bool
    event_type: str


# Event type to Pydantic model mapping
_EVENT_TYPE_TO_MODEL: Dict[str, Type[Any]] = {
    "Event": Event,
    "WPStatusChanged": StatusTransitionPayload,
    "GatePassed": GatePassedPayload,
    "GateFailed": GateFailedPayload,
    "MissionStarted": MissionStartedPayload,
    "MissionCompleted": MissionCompletedPayload,
    "MissionCancelled": MissionCancelledPayload,
    "PhaseEntered": PhaseEnteredPayload,
    "ReviewRollback": ReviewRollbackPayload,
}

# Event type to JSON Schema file name mapping
_EVENT_TYPE_TO_SCHEMA: Dict[str, str] = {
    "Event": "event.schema.json",
    "WPStatusChanged": "status_transition_payload.schema.json",
    "GatePassed": "gate_passed_payload.schema.json",
    "GateFailed": "gate_failed_payload.schema.json",
    "MissionStarted": "mission_started_payload.schema.json",
    "MissionCompleted": "mission_completed_payload.schema.json",
    "MissionCancelled": "mission_cancelled_payload.schema.json",
    "PhaseEntered": "phase_entered_payload.schema.json",
    "ReviewRollback": "review_rollback_payload.schema.json",
}


def _validate_with_model(
    payload: Dict[str, Any],
    model_class: Type[Any],
) -> Tuple[ModelViolation, ...]:
    """Validate payload using Pydantic model.

    Args:
        payload: The event payload to validate.
        model_class: The Pydantic model class to validate against.

    Returns:
        Tuple of ModelViolation instances (empty if valid).
    """
    try:
        model_class.model_validate(payload)
        return ()
    except PydanticValidationError as e:
        violations = []
        for error in e.errors():
            # Build field path from loc tuple
            field_path = ".".join(str(loc) for loc in error["loc"])
            violations.append(
                ModelViolation(
                    field=field_path,
                    message=error["msg"],
                    violation_type=error["type"],
                    input_value=error.get("input"),
                )
            )
        return tuple(violations)


def _validate_with_schema(
    payload: Dict[str, Any],
    schema_name: str,
    strict: bool,
) -> Tuple[Tuple[SchemaViolation, ...], bool]:
    """Validate payload using JSON Schema.

    Args:
        payload: The event payload to validate.
        schema_name: Name of the schema file in the schemas package.
        strict: If True, raise ImportError when jsonschema is unavailable.
                If False, skip validation and return empty violations.

    Returns:
        Tuple of (violations, skipped) where violations is a tuple of
        SchemaViolation instances and skipped indicates if validation
        was skipped due to missing jsonschema.

    Raises:
        ImportError: If strict=True and jsonschema is unavailable.
    """
    try:
        import json

        import jsonschema  # type: ignore[import-untyped]
        from jsonschema import Draft202012Validator
    except ImportError:
        if strict:
            raise ImportError(
                "jsonschema is required for strict conformance validation. "
                "Install with: pip install 'spec-kitty-events[conformance]'"
            )
        # Graceful degradation
        return ((), True)

    # Load schema from package
    try:
        schema_path = importlib.resources.files("spec_kitty_events.schemas").joinpath(
            schema_name
        )
        schema_json = schema_path.read_text()
        schema = json.loads(schema_json)
    except Exception as e:
        # If we can't load schema, treat as validation error
        return (
            (
                SchemaViolation(
                    json_path="$",
                    message=f"Failed to load schema: {e}",
                    validator="schema_loading",
                    validator_value=schema_name,
                    schema_path=(),
                ),
            ),
            False,
        )

    # Validate with jsonschema
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(payload))

    if not errors:
        return ((), False)

    violations = []
    for error in errors:
        # Build JSON path from absolute_path
        json_path = "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in error.absolute_path)
        if json_path == "$":
            json_path = "$"  # Root path

        violations.append(
            SchemaViolation(
                json_path=json_path,
                message=error.message,
                validator=error.validator,
                validator_value=error.validator_value,
                schema_path=tuple(error.absolute_schema_path),
            )
        )

    return (tuple(violations), False)


def validate_event(
    event_type: str,
    payload: Dict[str, Any],
    strict: bool = False,
) -> ConformanceResult:
    """Validate an event payload against its contract.

    This function performs dual-layer validation:
    1. Pydantic model validation (always performed)
    2. JSON Schema validation (optional, requires jsonschema package)

    Args:
        event_type: The event type string (e.g., "WPStatusChanged").
        payload: The event payload dictionary to validate.
        strict: If True, require jsonschema and fail if unavailable.
                If False, skip schema validation if jsonschema is missing.

    Returns:
        ConformanceResult with validation status and any violations found.

    Raises:
        ValueError: If event_type is not recognized.
        ImportError: If strict=True and jsonschema is unavailable.
    """
    if event_type not in _EVENT_TYPE_TO_MODEL:
        raise ValueError(
            f"Unknown event type: {event_type!r}. "
            f"Known types: {list(_EVENT_TYPE_TO_MODEL.keys())}"
        )

    model_class = _EVENT_TYPE_TO_MODEL[event_type]
    schema_name = _EVENT_TYPE_TO_SCHEMA[event_type]

    # Layer 1: Pydantic validation
    model_violations = _validate_with_model(payload, model_class)

    # Layer 2: JSON Schema validation
    schema_violations, schema_skipped = _validate_with_schema(
        payload, schema_name, strict
    )

    # Determine overall validity
    valid = len(model_violations) == 0 and (
        len(schema_violations) == 0 or schema_skipped
    )

    return ConformanceResult(
        valid=valid,
        model_violations=model_violations,
        schema_violations=schema_violations,
        schema_check_skipped=schema_skipped,
        event_type=event_type,
    )
