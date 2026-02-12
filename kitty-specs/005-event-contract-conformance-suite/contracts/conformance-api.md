# Conformance Validator API Contract

**Feature**: 005-event-contract-conformance-suite
**Date**: 2026-02-12

## Overview

The conformance validator API provides a callable interface for validating event payloads against the canonical contract. It uses a dual-layer architecture: Pydantic model validation (primary) and JSON Schema validation (secondary drift check).

## Public API Surface

### validate_event

```python
def validate_event(
    payload: dict[str, Any],
    event_type: str,
    *,
    strict: bool = False,
) -> ConformanceResult:
    """Validate an event payload against the canonical contract.

    Args:
        payload: The raw event payload dict to validate.
        event_type: The event type string (e.g., "WPStatusChanged").
        strict: If True, require JSON Schema validation (fail if jsonschema
                not installed). If False, skip schema check gracefully.

    Returns:
        ConformanceResult with separate violation buckets.
    """
```

### ConformanceResult

```python
@dataclass(frozen=True)
class ConformanceResult:
    valid: bool                              # True only when all required layers pass
    model_violations: tuple[ModelViolation, ...]  # Pydantic validation failures
    schema_violations: tuple[SchemaViolation, ...]  # JSON Schema validation failures
    schema_check_skipped: bool               # True if jsonschema not installed and strict=False
    event_type: str                          # The event type that was validated
```

### ModelViolation

```python
@dataclass(frozen=True)
class ModelViolation:
    field: str              # Field path (dot-separated, e.g., "evidence.repos")
    message: str            # Human-readable description
    violation_type: str     # Pydantic error type (e.g., "missing", "string_type")
    input_value: object     # The actual value that failed
```

### SchemaViolation

```python
@dataclass(frozen=True)
class SchemaViolation:
    json_path: str                      # e.g., "$.lamport_clock"
    message: str                        # Human-readable description
    validator: str                      # JSON Schema keyword (e.g., "minimum")
    validator_value: object             # The schema constraint value
    schema_path: tuple[str | int, ...]  # Path within schema to failing keyword
```

## Validation Layers

### Layer 1: Pydantic Model Validation (always active)

1. Resolve `event_type` to the corresponding Pydantic model class.
2. Call `Model.model_validate(payload)`.
3. On `ValidationError`, extract each error into a `ModelViolation`.
4. Business rules (force requires reason, done requires evidence, etc.) are captured here.

### Layer 2: JSON Schema Validation (requires `[conformance]` extra)

1. Load the committed JSON Schema file for the event type.
2. Validate `payload` against the schema using `Draft202012Validator.iter_errors()`.
3. Extract each error into a `SchemaViolation`.
4. If `jsonschema` is not installed:
   - `strict=True`: Raise `ImportError` with install instructions.
   - `strict=False`: Set `schema_check_skipped=True`, skip this layer.

### Pass/Fail Logic

- `valid = True` when:
  - `model_violations` is empty AND
  - (`schema_violations` is empty OR `schema_check_skipped` is True)
- In CI (strict mode): both layers must pass.
- In development (non-strict): Pydantic-only is sufficient.

## Fixture Loading API

### load_fixtures

```python
def load_fixtures(category: str) -> list[FixtureCase]:
    """Load canonical fixture cases for a category.

    Args:
        category: One of "events", "lane_mapping", "edge_cases".

    Returns:
        List of FixtureCase objects with payload, expected result, and metadata.
    """
```

### FixtureCase

```python
@dataclass(frozen=True)
class FixtureCase:
    id: str                  # Unique fixture identifier
    payload: dict[str, Any]  # The test payload
    expected_valid: bool     # Whether validation should pass
    event_type: str          # Event type for this fixture
    notes: str               # Description of what this fixture tests
    min_version: str         # Minimum package version
```

## Consumer CI Integration

```yaml
# In consumer CI (spec-kitty or spec-kitty-saas):
- name: Install with conformance extras
  run: pip install "spec-kitty-events[conformance]>=2.0.0,<3.0.0"

- name: Run conformance suite
  run: pytest --pyargs spec_kitty_events.conformance -v

- name: Validate local payloads (optional)
  run: python -c "
    from spec_kitty_events.conformance import validate_event
    # Consumer-specific payload validation
  "
```
