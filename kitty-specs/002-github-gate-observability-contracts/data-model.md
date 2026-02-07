# Data Model: GitHub Gate Observability Contracts
*Phase 1 output for feature 002*

## Entities

### GatePayloadBase

Shared base for all gate outcome payloads. Not instantiated directly.

| Field              | Type                 | Required | Constraints                         |
|--------------------|----------------------|----------|-------------------------------------|
| `gate_name`        | `str`                | Yes      | `min_length=1`                      |
| `gate_type`        | `Literal["ci"]`      | Yes      | Constrained to `"ci"`               |
| `conclusion`       | `str`                | Yes      | `min_length=1`                      |
| `external_provider`| `Literal["github"]`  | Yes      | Constrained to `"github"`           |
| `check_run_id`     | `int`                | Yes      | `gt=0`                              |
| `check_run_url`    | `AnyHttpUrl`         | Yes      | Valid HTTP/HTTPS URL                 |
| `delivery_id`      | `str`                | Yes      | `min_length=1` (idempotency key)    |
| `pr_number`        | `Optional[int]`      | No       | `gt=0` when present, `None` default |

**Config**: `frozen=True` (immutable after construction)

### GatePassedPayload(GatePayloadBase)

Represents a CI gate that concluded with `success`. No additional fields.

**Usage**: Attached as `payload` dict to a generic `Event` with `event_type="GatePassed"`.

### GateFailedPayload(GatePayloadBase)

Represents a CI gate that concluded with a failure condition (`failure`, `timed_out`, `cancelled`, `action_required`). No additional fields beyond base.

**Usage**: Attached as `payload` dict to a generic `Event` with `event_type="GateFailed"`.

### UnknownConclusionError(SpecKittyEventsError)

Custom exception raised when the mapping function encounters a conclusion string not in the known set.

| Attribute    | Type  | Description                              |
|-------------|-------|------------------------------------------|
| `conclusion`| `str` | The unrecognized conclusion value        |

## Relationships

```
Event (existing, generic)
  └── payload: Dict[str, Any]
        ├── validated as GatePassedPayload  (when event_type="GatePassed")
        └── validated as GateFailedPayload  (when event_type="GateFailed")

GatePayloadBase (abstract)
  ├── GatePassedPayload
  └── GateFailedPayload
```

## Serialization

Payload models provide:
- `model_dump()` → `Dict[str, Any]` (for attaching to `Event.payload`)
- `model_validate(data)` → `GatePassedPayload | GateFailedPayload` (for reconstructing from stored events)

The `AnyHttpUrl` field serializes to string in `model_dump()` mode.

## State Transitions

N/A — payload models are immutable value objects. No state transitions.

## Conclusion Mapping Table

| Input (str)        | Output              | Side Effects                           |
|--------------------|---------------------|----------------------------------------|
| `"success"`        | `"GatePassed"`      | None                                   |
| `"failure"`        | `"GateFailed"`      | None                                   |
| `"timed_out"`      | `"GateFailed"`      | None                                   |
| `"cancelled"`      | `"GateFailed"`      | None                                   |
| `"action_required"`| `"GateFailed"`      | None                                   |
| `"neutral"`        | `None`              | `logger.info()` + `on_ignored()` call  |
| `"skipped"`        | `None`              | `logger.info()` + `on_ignored()` call  |
| `"stale"`          | `None`              | `logger.info()` + `on_ignored()` call  |
| anything else      | raises error        | `UnknownConclusionError`               |
