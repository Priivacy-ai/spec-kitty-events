# Contract: Validation Error Shape

**Mission**: `teamspace-event-contract-foundation-01KQHDE4`
**Source spec NFR**: NFR-006 · **Research**: [research.md R-04](../research.md#r-04--structured-error-format-on-rejection)

## Rule

Every rejection produced by the contract package returns a `ValidationError` with a stable, structured shape. The set of error codes is a closed enum that is part of the public contract.

## Shape

```python
class ValidationError(BaseModel):
    code: ValidationErrorCode      # closed enum (str-backed)
    message: str                   # one-line human-readable summary
    path: list[str | int]          # JSON-pointer-like; [] denotes root
    details: dict[str, Any] = {}   # class-specific structured detail
    model_config = ConfigDict(extra="forbid")
```

## Error codes (initial set)

| Code | Meaning | `details` keys (typical) |
|---|---|---|
| `FORBIDDEN_KEY` | A key from the forbidden-key set was found in the input | `{"key": "<offending key>"}` |
| `UNKNOWN_LANE` | A lane reference outside the canonical vocabulary | `{"lane": "<offending value>"}` |
| `PAYLOAD_SCHEMA_FAIL` | The payload failed its typed schema | `{"errors": <pydantic-style list>}` |
| `ENVELOPE_SHAPE_INVALID` | Envelope is missing required fields or has wrong wrapper | `{"missing": [...], "extra": [...]}` |
| `RAW_HISTORICAL_ROW` | Input is a historical local status row, not an envelope | `{"detected_shape": "<short identifier>"}` |

The set is closed for this release. Adding a new code is a contract change subject to the same review process as schema bumps.

## Behavior

- The validator MAY short-circuit on the first failure (return one `ValidationError`) or collect all failures (return a list). Whichever mode is implemented MUST be deterministic: the same input produces the same output sequence every time.
- For the first ship, short-circuit mode is sufficient; "collect all" mode is out of scope unless surfaced by R-04 follow-up during the work-package phase.
- The `path` field uses ordinary JSON Pointer semantics (object keys as strings, array indices as integers). The empty list denotes the root.

## Determinism

`ValidationError` instances for identical inputs MUST be byte-identical when serialized. Tests:

- A determinism test in `tests/test_validation_error.py` validates the same input twice and asserts equal results across all four fields.
- Fixture audit tests pin `expected_error_code` per fixture (per [conformance-fixture-classes.md](./conformance-fixture-classes.md)).

## Integration with existing taxonomy

The package already contains `TransitionError` and `TransitionValidationResult` in `src/spec_kitty_events/status.py`. The new `ValidationError` shape is **layered on top**: existing typed exceptions gain a method (e.g., `as_validation_error() -> ValidationError`) that returns the structured shape. Code that already catches the typed exception keeps working; new consumers prefer the structured form.

## Forbidden patterns

- Returning a free-form string error.
- Returning a dict that omits any required field.
- Producing different `code` values for identical inputs across runs.
- Using a `code` value not in the closed enum (e.g., dynamically generated strings).

## Versioning

Adding a new `code` is a contract change subject to the version-bump rule.
