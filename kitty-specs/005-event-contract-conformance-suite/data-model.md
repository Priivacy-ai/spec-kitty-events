# Data Model: Event Contract Conformance Suite

**Feature**: 005-event-contract-conformance-suite
**Date**: 2026-02-12

## Existing Entities (unchanged)

### Lane (enum, `status.py`)
7-value string enum representing canonical status lanes.
- Values: `planned`, `claimed`, `in_progress`, `for_review`, `done`, `blocked`, `canceled`
- Terminal lanes: `done`, `canceled`
- Alias: `doing` → `in_progress` (consumer-facing only)

### Event (model, `models.py`)
Core event model (frozen Pydantic v2).
- Required: `event_id`, `event_type`, `aggregate_id`, `timestamp`, `node_id`, `lamport_clock`, `correlation_id`
- Defaulted: `schema_version` ("1.0.0"), `data_tier` (0)
- Optional: `causation_id`, `project_uuid`, `project_slug`, `payload`

### StatusTransitionPayload (model, `status.py`)
Payload for `WPStatusChanged` events (frozen Pydantic v2).
- Required: `feature_slug`, `wp_id`, `to_lane`, `actor`, `execution_mode`
- Optional: `from_lane`, `force`, `reason`, `review_ref`, `evidence`
- Business rules: force requires reason, done requires evidence

### Gate Payloads (models, `gates.py`)
- `GatePassedPayload`: conclusion="success"
- `GateFailedPayload`: conclusion∈{"failure","timed_out","cancelled","action_required"}

### Lifecycle Payloads (models, `lifecycle.py`)
- `MissionStartedPayload`, `MissionCompletedPayload`, `MissionCancelledPayload`
- `PhaseEnteredPayload`, `ReviewRollbackPayload`

## New Entities

### SyncLaneV1 (enum, new in `status.py`)

4-value string enum representing the V1 compatibility sync model.

| Value | String representation |
|-------|----------------------|
| PLANNED | `"planned"` |
| DOING | `"doing"` |
| FOR_REVIEW | `"for_review"` |
| DONE | `"done"` |

**Constraints**: Exactly 4 values. Immutable for V1 lifetime. New sync-lane versions are separate enums.

### CANONICAL_TO_SYNC_V1 (constant, new in `status.py`)

Immutable mapping from `Lane` to `SyncLaneV1`.

| Canonical Lane | Sync Lane V1 |
|----------------|--------------|
| PLANNED | PLANNED |
| CLAIMED | PLANNED |
| IN_PROGRESS | DOING |
| FOR_REVIEW | FOR_REVIEW |
| DONE | DONE |
| BLOCKED | DOING |
| CANCELED | PLANNED |

**Type**: `MappingProxyType[Lane, SyncLaneV1]` (immutable at runtime)

**Invariants**:
- Every `Lane` member MUST have exactly one mapping.
- Output values are restricted to `SyncLaneV1` members.
- Mapping is deterministic and total (no missing keys).

### canonical_to_sync_v1 (function, new in `status.py`)

```
canonical_to_sync_v1(lane: Lane) -> SyncLaneV1
```

Pure function applying the V1 mapping. Raises `KeyError` if lane is not in mapping (should never happen if Lane enum is unchanged).

### ConformanceResult (model, new in `conformance/validators.py`)

Structured validation result from the dual-layer validator.

| Field | Type | Description |
|-------|------|-------------|
| valid | bool | True only when all required layers pass |
| model_violations | tuple[ModelViolation, ...] | Pydantic validation failures |
| schema_violations | tuple[SchemaViolation, ...] | JSON Schema validation failures |
| schema_check_skipped | bool | True if jsonschema not installed |
| event_type | str | The event type that was validated |

### ModelViolation (model, new in `conformance/validators.py`)

| Field | Type | Description |
|-------|------|-------------|
| field | str | Field path (dot-separated) |
| message | str | Human-readable violation description |
| violation_type | str | Pydantic error type (e.g., "missing", "string_type") |
| input_value | object | The actual value that failed |

### SchemaViolation (model, new in `conformance/validators.py`)

| Field | Type | Description |
|-------|------|-------------|
| json_path | str | JSON Path to failing element (e.g., "$.lamport_clock") |
| message | str | Human-readable violation description |
| validator | str | JSON Schema keyword that failed (e.g., "minimum", "required") |
| validator_value | object | The schema constraint value |
| schema_path | tuple[str \| int, ...] | Path within schema to failing keyword |

### Fixture Manifest Entry (JSON, new in `conformance/fixtures/manifest.json`)

| Field | Type | Description |
|-------|------|-------------|
| id | str | Unique fixture identifier |
| path | str | Relative path to fixture file |
| expected_result | str | "valid" or "invalid" |
| event_type | str | Event type this fixture tests |
| notes | str | Description of what this fixture tests |
| min_version | str | Minimum package version this fixture applies to |

## Entity Relationships

```
Lane (7 values) ──canonical_to_sync_v1()──▶ SyncLaneV1 (4 values)
                                               │
Event ──────────────────────────────────────────┤
  └─ payload: StatusTransitionPayload           │
  └─ payload: GatePassedPayload                 │
  └─ payload: GateFailedPayload                 │
  └─ payload: MissionStartedPayload             │
  └─ payload: ...                               │
                                               ▼
                                    ConformanceResult
                                      ├─ model_violations[]
                                      └─ schema_violations[]
```

## Schema Files (generated, one per model)

| File | Source Model |
|------|-------------|
| `event.schema.json` | `Event` |
| `status_transition_payload.schema.json` | `StatusTransitionPayload` |
| `gate_passed_payload.schema.json` | `GatePassedPayload` |
| `gate_failed_payload.schema.json` | `GateFailedPayload` |
| `mission_started_payload.schema.json` | `MissionStartedPayload` |
| `mission_completed_payload.schema.json` | `MissionCompletedPayload` |
| `mission_cancelled_payload.schema.json` | `MissionCancelledPayload` |
| `phase_entered_payload.schema.json` | `PhaseEnteredPayload` |
| `review_rollback_payload.schema.json` | `ReviewRollbackPayload` |
| `lane.schema.json` | `Lane` |
| `sync_lane_v1.schema.json` | `SyncLaneV1` |
