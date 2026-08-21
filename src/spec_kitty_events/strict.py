"""Strict journal profile: a deterministic, structured envelope validator.

F1-T1 (7.0.0) publishes a *strict* profile over the existing canonical
envelope and lifecycle/WP contracts, opted into by new producers/readers
(the F2 journal, D1 projector, Z1 client) without changing :class:`Event`
itself — which stays lenient so today's local-CLI readers and the legacy
emitter keep working unchanged (decision 3, ``COMPATIBILITY.md``).

:func:`validate_strict_envelope` is the single public entry point. It is
pure (no I/O, no mutation), deterministic (same input -> byte-identical
output, same order every call), and *collect-all* for the checks that can
run independently, so a caller sees every defect in one pass rather than
one exception per submission.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Tuple

from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events.conformance.validators import validate_event
from spec_kitty_events.forbidden_keys import FORBIDDEN_LEGACY_KEYS, find_forbidden_keys
from spec_kitty_events.harness_observation import (
    FORBIDDEN_OBSERVATION_KEYS,
    HARNESS_OBSERVATION,
)
from spec_kitty_events.lifecycle import MISSION_EVENT_TYPES
from spec_kitty_events.models import Event
from spec_kitty_events.project_lifecycle import (
    PLAN_COMPLETED,
    PLAN_STARTED,
    PROJECT_INITIALIZED,
    SPECIFY_COMPLETED,
    SPECIFY_STARTED,
    TASKS_COMPLETED,
    TASKS_STARTED,
    WP_CREATED,
)
from spec_kitty_events.status import WP_STATUS_CHANGED
from spec_kitty_events.validation_errors import ValidationError, ValidationErrorCode

__all__ = [
    "STRICT_PROFILE_ID",
    "STRICT_ENVELOPE_KEYS",
    "STRICT_EVENT_TYPES",
    "STRICT_TIMESTAMP_RULES",
    "validate_strict_envelope",
]


STRICT_PROFILE_ID: str = "journal/v1"

# The 14 Event fields (models.py); ALL must be present under the strict
# profile — nullable ones (causation_id, project_slug) as explicit null,
# defaulted ones (schema_version, data_tier) explicit (draft §3.2, decision
# 13). One rule, no subset list to maintain.
STRICT_ENVELOPE_KEYS: frozenset[str] = frozenset(
    {
        "event_id", "event_type", "aggregate_id", "payload", "timestamp",
        "build_id", "node_id", "lamport_clock", "causation_id",
        "project_uuid", "project_slug", "correlation_id",
        "schema_version", "data_tier",
    }
)

# 9 mission + 1 WP-lane + 8 project/artifact + 1 observation = 19 (draft
# §3.2, exhaustive; excluded names are listed in that section's prose).
STRICT_EVENT_TYPES: frozenset[str] = frozenset(
    MISSION_EVENT_TYPES
    | {WP_STATUS_CHANGED}
    | {
        WP_CREATED,
        PROJECT_INITIALIZED,
        SPECIFY_STARTED,
        SPECIFY_COMPLETED,
        PLAN_STARTED,
        PLAN_COMPLETED,
        TASKS_STARTED,
        TASKS_COMPLETED,
    }
    | {HARNESS_OBSERVATION}
)

STRICT_TIMESTAMP_RULES: str = "iso8601-tz-aware"

_REQUIRED_SCHEMA_VERSION = "3.0.0"


def _envelope_shape_error(**details: object) -> ValidationError:
    return ValidationError(
        code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
        message="envelope shape invalid",
        path=[],
        details=dict(details),
    )


def _parse_iso8601(value: str) -> datetime | None:
    """Best-effort ISO-8601 parse. Returns None when unparsable."""
    text = value
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def validate_strict_envelope(record: Any) -> Tuple[ValidationError, ...]:
    """Validate a raw JSON-shaped envelope against the strict journal profile.

    Deterministic, collect-all, pure. Empty tuple == accepted. Check order
    (fixed, each emits at most one error per finding):

    1. wrapper is a JSON object
    2. every STRICT_ENVELOPE_KEYS member present (explicit null counts)
    3. no key outside STRICT_ENVELOPE_KEYS
    4. forbidden keys anywhere (recursive walk; FORBIDDEN_LEGACY_KEYS,
       plus FORBIDDEN_OBSERVATION_KEYS when event_type == HarnessObservation)
    5. schema_version present, str, == "3.0.0"
    6. event_type in STRICT_EVENT_TYPES
    7. timestamp is str, ISO-8601, tz-aware
    8. Event.model_validate(record)
    9. validate_event(record, event_type, strict=False) model violations

    Steps 1-7 all run (collect-all); steps 8-9 are skipped when any of 1-3
    or 5-6 failed (no cascading noise from a record already known to be
    unusable at the envelope/type level).
    """
    errors: list[ValidationError] = []

    # Step 1: wrapper is a JSON object.
    if not isinstance(record, Mapping):
        errors.append(_envelope_shape_error(wrapper=type(record).__name__))
        return tuple(errors)

    # Step 2: every key present (explicit null counts as present).
    missing = sorted(key for key in STRICT_ENVELOPE_KEYS if key not in record)
    envelope_shape_failed = False
    if missing:
        errors.append(_envelope_shape_error(missing=missing))
        envelope_shape_failed = True

    # Step 3: no key outside the closed set.
    extra = sorted(key for key in record if key not in STRICT_ENVELOPE_KEYS)
    if extra:
        errors.append(_envelope_shape_error(extra=extra))
        envelope_shape_failed = True

    # Step 4: forbidden keys anywhere (recursive walk over the whole record).
    forbidden_set = FORBIDDEN_LEGACY_KEYS
    if record.get("event_type") == HARNESS_OBSERVATION:
        forbidden_set = FORBIDDEN_LEGACY_KEYS | FORBIDDEN_OBSERVATION_KEYS
    errors.extend(find_forbidden_keys(record, forbidden=forbidden_set))

    # Step 5: schema_version present, str, exact match.
    type_failed = False
    schema_version = record.get("schema_version")
    if not isinstance(schema_version, str) or schema_version != _REQUIRED_SCHEMA_VERSION:
        errors.append(
            ValidationError(
                code=ValidationErrorCode.UNSUPPORTED_SCHEMA_VERSION,
                message="unsupported schema_version for the strict journal profile",
                path=["schema_version"],
                details={"found": schema_version, "required": _REQUIRED_SCHEMA_VERSION},
            )
        )
        type_failed = True

    # Step 6: event_type admitted by the profile.
    event_type = record.get("event_type")
    if event_type not in STRICT_EVENT_TYPES:
        errors.append(
            ValidationError(
                code=ValidationErrorCode.UNKNOWN_EVENT_TYPE,
                message="event_type is not admitted by the strict journal profile",
                path=["event_type"],
                details={"event_type": event_type, "profile": STRICT_PROFILE_ID},
            )
        )
        type_failed = True

    # Step 7: timestamp shape (only when the key is present at all — its
    # absence is already reported by step 2 and we do not want a second,
    # confusing error about the same missing field).
    if "timestamp" in record:
        timestamp_value = record["timestamp"]
        if not isinstance(timestamp_value, str):
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
                    message="timestamp must be an ISO-8601 string",
                    path=["timestamp"],
                    details={"reason": "not_string"},
                )
            )
        else:
            parsed = _parse_iso8601(timestamp_value)
            if parsed is None:
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
                        message="timestamp is not a parsable ISO-8601 value",
                        path=["timestamp"],
                        details={"reason": "unparsable"},
                    )
                )
            elif parsed.tzinfo is None:
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
                        message="timestamp must be timezone-aware",
                        path=["timestamp"],
                        details={"reason": "naive"},
                    )
                )

    if envelope_shape_failed or type_failed:
        # No cascading noise: a record already known unusable at the
        # envelope/type level is not also run through the (much more
        # detailed, and potentially misleading) model layers.
        return tuple(errors)

    # Step 8: Event.model_validate(record).
    try:
        Event.model_validate(dict(record))
    except PydanticValidationError as exc:
        for err in exc.errors():
            loc = list(err["loc"])
            if loc and loc[0] == "payload":
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.PAYLOAD_SCHEMA_FAIL,
                        message=err["msg"],
                        path=[str(part) for part in loc],
                        details={"type": err["type"]},
                    )
                )
            else:
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.ENVELOPE_SHAPE_INVALID,
                        message=err["msg"],
                        path=[str(part) for part in loc],
                        details={"type": err["type"]},
                    )
                )

    # Step 9: typed payload / semantic validation via the existing registry.
    # event_type is known to be a str member of STRICT_EVENT_TYPES here:
    # type_failed is False, so step 6 above confirmed membership.
    assert isinstance(event_type, str)
    result = validate_event(dict(record), event_type, strict=False)
    for violation in result.model_violations:
        if violation.violation_type == "transition_rule":
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.UNKNOWN_LANE,
                    message=violation.message,
                    path=["payload"],
                    details={"violation_type": violation.violation_type},
                )
            )
        else:
            field_parts = [part for part in violation.field.split(".") if part]
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.PAYLOAD_SCHEMA_FAIL,
                    message=violation.message,
                    path=["payload", *field_parts],
                    details={"violation_type": violation.violation_type},
                )
            )

    return tuple(errors)
