---
work_package_id: WP03
title: Conformance Validator API
lane: "doing"
dependencies: [WP02]
base_branch: 005-event-contract-conformance-suite-WP02
base_commit: 1382e91bdfa19cefd94d3943317aa2591f2a9351
created_at: '2026-02-12T10:39:25.027797+00:00'
subtasks: [T014, T015, T016, T017, T018, T019, T020]
shell_pid: "84319"
agent: "codex"
history:
- date: '2026-02-12'
  action: created
  by: spec-kitty.tasks
---

# WP03 — Conformance Validator API

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

## Objective

Create the `src/spec_kitty_events/conformance/` subpackage with the dual-layer validator. Implement `ConformanceResult`, `ModelViolation`, `SchemaViolation`, `validate_event()`, and the event-type-to-model resolver.

## Context

Per the conformance-api contract and research (R3, R4):
- **Layer 1 (Pydantic)**: Always active. Catches business rules + structure.
- **Layer 2 (JSON Schema)**: Requires `jsonschema` package. Catches schema drift.
- **Graceful degradation**: If `jsonschema` not installed and `strict=False`, skip Layer 2 and set `schema_check_skipped=True`.

**Key files to create**:
- `src/spec_kitty_events/conformance/__init__.py`
- `src/spec_kitty_events/conformance/validators.py`
- `tests/unit/test_conformance.py`

## Subtask Guidance

### T014: Create `conformance/__init__.py` with public API surface

**Purpose**: Package entry point exposing the validator API.

**Steps**:
1. Create `src/spec_kitty_events/conformance/__init__.py`.
2. Re-export from validators:
   ```python
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
   ```
3. Note: `load_fixtures` and `FixtureCase` will be added in WP04.

**Validation**:
- [ ] `from spec_kitty_events.conformance import validate_event` works
- [ ] `from spec_kitty_events.conformance import ConformanceResult` works

### T015: Create `validators.py` with result models

**Purpose**: Define the structured result types for the dual-layer validator.

**Steps**:
1. Create `src/spec_kitty_events/conformance/validators.py`.
2. Define frozen dataclasses (match existing project pattern of immutable types):

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class ModelViolation:
    """A single Pydantic model validation failure."""
    field: str
    message: str
    violation_type: str
    input_value: object


@dataclass(frozen=True)
class SchemaViolation:
    """A single JSON Schema validation failure."""
    json_path: str
    message: str
    validator: str
    validator_value: object
    schema_path: Tuple[str | int, ...]


@dataclass(frozen=True)
class ConformanceResult:
    """Result of validating an event payload against the canonical contract."""
    valid: bool
    model_violations: Tuple[ModelViolation, ...]
    schema_violations: Tuple[SchemaViolation, ...]
    schema_check_skipped: bool
    event_type: str
```

3. Use `Tuple` (not `tuple`) for Python 3.10 compatibility under `from __future__ import annotations`.
4. All fields immutable (frozen dataclass).

**Validation**:
- [ ] `ConformanceResult(valid=True, model_violations=(), schema_violations=(), schema_check_skipped=False, event_type="Event")` creates successfully
- [ ] Frozen: attempting to set a field raises `FrozenInstanceError`
- [ ] mypy passes

### T016: Implement event-type-to-model resolver

**Purpose**: Map event type strings to their corresponding Pydantic model classes.

**Steps**:
1. In `validators.py`, define a registry:
   ```python
   from spec_kitty_events.models import Event
   from spec_kitty_events.status import StatusTransitionPayload
   from spec_kitty_events.gates import GatePassedPayload, GateFailedPayload
   from spec_kitty_events.lifecycle import (
       MissionStartedPayload, MissionCompletedPayload,
       MissionCancelledPayload, PhaseEnteredPayload,
       ReviewRollbackPayload,
   )

   _EVENT_TYPE_TO_MODEL: dict[str, type[BaseModel]] = {
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
   ```
2. Also map event types to schema names for Layer 2:
   ```python
   _EVENT_TYPE_TO_SCHEMA: dict[str, str] = {
       "Event": "event",
       "WPStatusChanged": "status_transition_payload",
       "GatePassed": "gate_passed_payload",
       "GateFailed": "gate_failed_payload",
       "MissionStarted": "mission_started_payload",
       "MissionCompleted": "mission_completed_payload",
       "MissionCancelled": "mission_cancelled_payload",
       "PhaseEntered": "phase_entered_payload",
       "ReviewRollback": "review_rollback_payload",
   }
   ```

**Validation**:
- [ ] All 9 event types are mapped
- [ ] Unknown event type raises a clear error in `validate_event()`

### T017: Implement Pydantic validation layer (Layer 1)

**Purpose**: Validate payloads via `model_validate()` and extract violations.

**Steps**:
1. In `validators.py`, implement:
   ```python
   def _validate_with_model(
       payload: dict[str, Any],
       model_class: type[BaseModel],
   ) -> Tuple[ModelViolation, ...]:
       """Run Pydantic model validation and extract violations."""
       try:
           model_class.model_validate(payload)
           return ()
       except PydanticValidationError as exc:
           violations: list[ModelViolation] = []
           for error in exc.errors():
               field_path = ".".join(str(loc) for loc in error["loc"])
               violations.append(ModelViolation(
                   field=field_path,
                   message=error["msg"],
                   violation_type=error["type"],
                   input_value=error.get("input", None),
               ))
           return tuple(violations)
   ```
2. Import `ValidationError as PydanticValidationError` from `pydantic` (not from `spec_kitty_events.models`).

**Validation**:
- [ ] Valid payload returns empty tuple
- [ ] Invalid payload returns `ModelViolation` with correct field and message
- [ ] Business rules caught (e.g., force=True without reason)

### T018: Implement JSON Schema validation layer (Layer 2)

**Purpose**: Validate payloads against committed JSON Schema files using `jsonschema`.

**Steps**:
1. In `validators.py`, implement with graceful degradation:
   ```python
   def _validate_with_schema(
       payload: dict[str, Any],
       schema_name: str,
       *,
       strict: bool,
   ) -> Tuple[Tuple[SchemaViolation, ...], bool]:
       """Run JSON Schema validation. Returns (violations, skipped)."""
       try:
           from jsonschema import Draft202012Validator
       except ImportError:
           if strict:
               raise ImportError(
                   "jsonschema is required for strict conformance checking. "
                   "Install with: pip install spec-kitty-events[conformance]"
               ) from None
           return (), True  # skipped

       from spec_kitty_events.schemas import load_schema
       schema = load_schema(schema_name)
       validator = Draft202012Validator(schema)

       violations: list[SchemaViolation] = []
       for error in validator.iter_errors(payload):
           violations.append(SchemaViolation(
               json_path=error.json_path,
               message=error.message,
               validator=error.validator,
               validator_value=error.validator_value,
               schema_path=tuple(error.absolute_schema_path),
           ))
       violations.sort(key=lambda v: v.json_path)
       return tuple(violations), False
   ```

**Validation**:
- [ ] With `jsonschema` installed: valid payload returns empty violations, `skipped=False`
- [ ] With `jsonschema` installed: invalid payload returns `SchemaViolation` instances
- [ ] Without `jsonschema` and `strict=False`: returns `(), True`
- [ ] Without `jsonschema` and `strict=True`: raises `ImportError`

### T019: Implement `validate_event()` function

**Purpose**: The main public API combining both layers.

**Steps**:
1. In `validators.py`:
   ```python
   def validate_event(
       payload: dict[str, Any],
       event_type: str,
       *,
       strict: bool = False,
   ) -> ConformanceResult:
       """Validate an event payload against the canonical contract."""
       if event_type not in _EVENT_TYPE_TO_MODEL:
           raise ValueError(
               f"Unknown event type: {event_type!r}. "
               f"Known types: {sorted(_EVENT_TYPE_TO_MODEL)}"
           )

       model_class = _EVENT_TYPE_TO_MODEL[event_type]
       model_violations = _validate_with_model(payload, model_class)

       schema_name = _EVENT_TYPE_TO_SCHEMA.get(event_type)
       if schema_name is not None:
           schema_violations, skipped = _validate_with_schema(
               payload, schema_name, strict=strict,
           )
       else:
           schema_violations, skipped = (), True

       valid = (
           len(model_violations) == 0
           and (len(schema_violations) == 0 or skipped)
       )

       return ConformanceResult(
           valid=valid,
           model_violations=model_violations,
           schema_violations=schema_violations,
           schema_check_skipped=skipped,
           event_type=event_type,
       )
   ```

**Validation**:
- [ ] Valid payload: `result.valid is True`, both violation tuples empty
- [ ] Invalid payload: `result.valid is False`, violations populated
- [ ] Unknown event type: raises `ValueError`
- [ ] `strict=True` without jsonschema: raises `ImportError`

### T020: Unit tests for validator

**Purpose**: Comprehensive tests for the conformance validator.

**Steps**:
1. Create `tests/unit/test_conformance.py`.
2. Test cases:
   - `test_validate_event_valid_status_transition`: Construct a valid `WPStatusChanged` payload dict, assert `result.valid is True`.
   - `test_validate_event_invalid_missing_field`: Omit a required field, assert violation with correct field name.
   - `test_validate_event_invalid_enum_value`: Use an invalid lane value, assert violation.
   - `test_validate_event_business_rule_force_without_reason`: Set `force=True` without `reason`, assert model violation.
   - `test_validate_event_unknown_type_raises`: Pass an unknown event type, assert `ValueError`.
   - `test_validate_event_strict_without_jsonschema`: Mock `jsonschema` import to fail, assert `ImportError` with `strict=True`.
   - `test_validate_event_nonstrict_skips_schema`: Mock `jsonschema` import to fail with `strict=False`, assert `schema_check_skipped is True`.
   - `test_validate_event_schema_violations_populated`: Pass a payload that fails JSON Schema but passes Pydantic (edge case — may need contrived example).
   - `test_validate_event_all_event_types`: Parametrize across all 9 event types with valid payloads.

**Validation**:
- [ ] All tests pass: `python3.11 -m pytest tests/unit/test_conformance.py -v`
- [ ] `mypy --strict` passes on `conformance/` module

## Definition of Done

- [ ] `src/spec_kitty_events/conformance/` subpackage exists
- [ ] `ConformanceResult`, `ModelViolation`, `SchemaViolation` are frozen dataclasses
- [ ] `validate_event()` works with dual-layer validation
- [ ] Graceful degradation when `jsonschema` not installed
- [ ] All 9 event types are resolvable
- [ ] Unit tests cover valid, invalid, strict, non-strict, and all event types
- [ ] `mypy --strict` passes on new files
- [ ] Full test suite still passes: `python3.11 -m pytest`

## Risks

- **Pydantic ValidationError import**: Import `ValidationError` from `pydantic` directly (not from `spec_kitty_events.models` which re-exports a custom `ValidationError`). Use alias: `from pydantic import ValidationError as PydanticValidationError`.
- **`from __future__ import annotations` and mypy**: Use `Tuple` from `typing` for Python 3.10 compat. If using distinct variable names in type branches, follow the pattern from MEMORY.md.
- **Constructing valid test payloads**: Each event type has different required fields. Use `model_dump()` on a valid model instance to generate test payloads, then mutate for invalid cases.

## Reviewer Guidance

- Verify both validation layers execute independently (Layer 1 failure doesn't skip Layer 2).
- Verify `valid` field logic: must be `False` if model_violations is non-empty, regardless of schema result.
- Verify graceful degradation: `schema_check_skipped=True` when jsonschema absent and `strict=False`.
- Spot-check test payloads against the model definitions in `status.py`, `gates.py`, `lifecycle.py`.

## Activity Log

- 2026-02-12T10:39:25Z – claude-opus – shell_pid=80468 – lane=doing – Assigned agent via workflow command
- 2026-02-12T10:44:17Z – claude-opus – shell_pid=80468 – lane=for_review – Ready for review: conformance/ subpackage with dual-layer validator, 9 event types, 18 new tests, 468 total pass, mypy clean
- 2026-02-12T10:44:30Z – codex – shell_pid=84319 – lane=doing – Started review via workflow command
