# Data Model: Event Model Project Identity

**Feature**: 001-event-model-project-identity
**Date**: 2026-02-07

## Entity: Event

The `Event` model is an immutable Pydantic model (`frozen=True`) representing a single state-change in a distributed event-sourced system.

### Fields

| Field | Type | Required | Default | Validation | Description |
|-------|------|:---:|---------|------------|-------------|
| `event_id` | `str` | Yes | — | ULID format (26 chars) | Unique event identifier |
| `event_type` | `str` | Yes | — | min_length=1 | Event type label |
| `aggregate_id` | `str` | Yes | — | min_length=1 | Entity being modified |
| `payload` | `Dict[str, Any]` | No | `{}` | — | Opaque event data |
| `timestamp` | `datetime` | Yes | — | — | Wall-clock timestamp |
| `node_id` | `str` | Yes | — | min_length=1 | Originating node |
| `lamport_clock` | `int` | Yes | — | >= 0 | Logical clock value |
| `causation_id` | `Optional[str]` | No | `None` | ULID format (26 chars) | Parent event ID |
| **`project_uuid`** | **`uuid.UUID`** | **Yes** | **—** | **Valid UUID** | **Originating project** |
| **`project_slug`** | **`Optional[str]`** | **No** | **`None`** | **—** | **Human-readable project name** |

**New fields** are highlighted in bold.

### Serialization Contract

**`to_dict()` output** (via `model_dump()`):
```
{
    "event_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "event_type": "WPStatusChanged",
    "aggregate_id": "WP001",
    "payload": {"state": "doing"},
    "timestamp": datetime(2026, 2, 7, ...),
    "node_id": "alice",
    "lamport_clock": 5,
    "causation_id": null,
    "project_uuid": UUID("550e8400-e29b-41d4-a716-446655440000"),
    "project_slug": "my-project"
}
```

**`from_dict()` input**: Accepts the same structure. `project_uuid` can be either a `uuid.UUID` object or a UUID string (Pydantic coerces automatically).

### Immutability

All fields including `project_uuid` and `project_slug` are immutable after creation (Pydantic `frozen=True`). Any attempt to modify raises `FrozenInstanceError`.

### Relationships

- **Event → Project**: Many events belong to one project (via `project_uuid`). The library does not enforce referential integrity — that's the SaaS layer's job.
- **Event → Event**: Causal chain via `causation_id` (existing behavior, unchanged).
