# Mission Audit Lifecycle Contracts

## Overview

The canonical contracts for the mission audit lifecycle are defined as Python
event payload models and conformance fixtures in the `spec_kitty_events` package.

## Contract Locations

### Python Event Payload Models

The authoritative Python models are in:

```
src/spec_kitty_events/mission_audit.py
```

Key models:
- `MissionAuditRequestedPayload` — audit requested event payload
- `MissionAuditStartedPayload` — audit started event payload
- `MissionAuditDecisionRequestedPayload` — decision checkpoint payload
- `MissionAuditCompletedPayload` — audit completed event payload
- `MissionAuditFailedPayload` — audit failed event payload

Supporting types:
- `AuditVerdict` — enum: `PASS`, `FAIL`, `INCONCLUSIVE`
- `AuditSeverity` — enum: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `AuditStatus` — enum: `REQUESTED`, `STARTED`, `DECISION_REQUESTED`, `COMPLETED`, `FAILED`
- `AuditArtifactRef` — artifact reference value object
- `PendingDecision` — pending decision value object
- `MissionAuditAnomaly` — anomaly record value object
- `ReducedMissionAuditState` — reducer output state

### JSON Schemas

Generated JSON schemas are committed in:

```
src/spec_kitty_events/schemas/mission_audit_*.json
```

Schemas are generated from the Pydantic models via `TypeAdapter(Model).json_schema()`
and are checked for drift in the conformance test suite.

### Conformance Fixtures

Conformance fixtures (valid and invalid payloads + replay streams) are in:

```
src/spec_kitty_events/conformance/fixtures/mission_audit/
  valid/        # 7 valid fixture cases
  invalid/      # 4 invalid fixture cases
  replay/       # 3 replay streams with golden reducer outputs
```

### Conformance Test Suite

The full conformance test suite is at:

```
tests/test_mission_audit_conformance.py
```

## Public API

All mission audit contracts are exported from `spec_kitty_events` at the
top level (added in v2.5.0):

```python
from spec_kitty_events import (
    MissionAuditRequestedPayload,
    MissionAuditStartedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditCompletedPayload,
    MissionAuditFailedPayload,
    reduce_mission_audit_events,
    AuditVerdict,
    AuditSeverity,
    AuditStatus,
    AuditArtifactRef,
    PendingDecision,
    MissionAuditAnomaly,
    ReducedMissionAuditState,
    MISSION_AUDIT_REQUESTED,
    MISSION_AUDIT_STARTED,
    MISSION_AUDIT_DECISION_REQUESTED,
    MISSION_AUDIT_COMPLETED,
    MISSION_AUDIT_FAILED,
    MISSION_AUDIT_EVENT_TYPES,
    TERMINAL_AUDIT_STATUSES,
    AUDIT_SCHEMA_VERSION,
)
```

## SyncLane Mapping

Mission audit events map to SyncLane v1 as follows (locked; changes require
a 3.0.0 breaking change):

| Event Type | SyncLane |
|---|---|
| `mission_audit.requested` | `planning` |
| `mission_audit.started` | `doing` |
| `mission_audit.decision_requested` | `doing` |
| `mission_audit.completed` | `done` |
| `mission_audit.failed` | `done` |
