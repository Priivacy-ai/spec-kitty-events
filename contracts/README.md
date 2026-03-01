# spec-kitty-events Contracts

This directory is the canonical entry point for event contracts published by the
`spec-kitty-events` library.  The contracts are defined in Python using Pydantic v2
models and are available from the top-level package starting with **v2.5.0**.

---

## Mission Audit Lifecycle Contracts (v2.5.0)

The mission-audit lifecycle contracts describe the full audit workflow for a Spec
Kitty mission from request through verdict.

### Python Models

**Source**: [`src/spec_kitty_events/mission_audit.py`](../src/spec_kitty_events/mission_audit.py)

| Symbol | Description |
|---|---|
| `MissionAuditRequestedPayload` | Payload for `mission.audit.requested` |
| `MissionAuditStartedPayload` | Payload for `mission.audit.started` |
| `MissionAuditDecisionRequestedPayload` | Payload for `mission.audit.decision_requested` |
| `MissionAuditCompletedPayload` | Payload for `mission.audit.completed` |
| `MissionAuditFailedPayload` | Payload for `mission.audit.failed` |
| `ReducedMissionAuditState` | Aggregated state after reducing an audit event stream |
| `reduce_mission_audit_events` | Reducer function — `List[Event] → ReducedMissionAuditState` |
| `AuditVerdict` | Enum: `pass`, `fail`, `inconclusive` |
| `AuditSeverity` | Enum: `blocker`, `major`, `minor`, `informational` |
| `AuditStatus` | Enum: audit lifecycle phase |
| `AuditArtifactRef` | Value object — audited artefact reference |
| `PendingDecision` | Value object — outstanding human decision |
| `MissionAuditAnomaly` | Value object — anomaly finding |
| `MISSION_AUDIT_REQUESTED` | Event-type constant: `"mission.audit.requested"` |
| `MISSION_AUDIT_STARTED` | Event-type constant: `"mission.audit.started"` |
| `MISSION_AUDIT_DECISION_REQUESTED` | Event-type constant: `"mission.audit.decision_requested"` |
| `MISSION_AUDIT_COMPLETED` | Event-type constant: `"mission.audit.completed"` |
| `MISSION_AUDIT_FAILED` | Event-type constant: `"mission.audit.failed"` |
| `MISSION_AUDIT_EVENT_TYPES` | Frozenset of all five event-type constants above |
| `TERMINAL_AUDIT_STATUSES` | Frozenset of terminal `AuditStatus` values |
| `AUDIT_SCHEMA_VERSION` | String: current schema version (e.g. `"1.0"`) |

#### Quick start

```python
from spec_kitty_events import (
    MissionAuditRequestedPayload,
    MissionAuditCompletedPayload,
    AuditVerdict,
    MISSION_AUDIT_REQUESTED,
    reduce_mission_audit_events,
)
```

### JSON Schemas

**Source**: [`src/spec_kitty_events/schemas/`](../src/spec_kitty_events/schemas/)

Pre-generated JSON Schema files (Draft 2020-12) for each payload model:

| File | Model |
|---|---|
| `mission_audit_requested_payload.schema.json` | `MissionAuditRequestedPayload` |
| `mission_audit_started_payload.schema.json` | `MissionAuditStartedPayload` |
| `mission_audit_decision_requested_payload.schema.json` | `MissionAuditDecisionRequestedPayload` |
| `mission_audit_completed_payload.schema.json` | `MissionAuditCompletedPayload` |
| `mission_audit_failed_payload.schema.json` | `MissionAuditFailedPayload` |

Load at runtime:

```python
from spec_kitty_events.schemas import load_schema
schema = load_schema("mission_audit_requested_payload")
```

### Conformance Fixtures

**Source**: [`src/spec_kitty_events/conformance/fixtures/mission_audit/`](../src/spec_kitty_events/conformance/fixtures/mission_audit/)

| Subdirectory | Contents |
|---|---|
| `valid/` | 7 valid event payload fixtures (must pass validation) |
| `invalid/` | 4 invalid event payload fixtures (must fail validation) |
| `replay/` | 3 JSONL replay streams + 3 golden reducer output JSON files |

Run the conformance test suite:

```bash
python3.11 -m pytest tests/test_mission_audit_conformance.py -v
```

---

## Feature-Level Contract Documentation

Additional design rationale, decision log, and lane-mapping specs are located in the
feature spec directory:

```
kitty-specs/010-mission-audit-lifecycle-contracts/contracts/
```

See [`kitty-specs/010-mission-audit-lifecycle-contracts/`](../kitty-specs/010-mission-audit-lifecycle-contracts/)
for the full specification, plan, and task breakdown.
