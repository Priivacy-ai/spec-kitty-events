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

---

## Teamspace Projection Inputs (2026-04-21)

The Private Teamspace / shared Teamspace work does **not** add team-routing state
to the canonical event envelope in `spec-kitty-events`.

### Ownership Boundary

The canonical envelope remains build-scoped and repository/project-scoped:

| Concern | Canonical owner |
|---|---|
| `build_id` checkout identity | event envelope |
| `node_id` causal emitter identity | event envelope |
| `project_uuid` / `project_slug` | event envelope |
| Private-vs-team routing, repository sharing, approval, disconnect | host product layer (`spec-kitty`, `spec-kitty-saas`) |

The important invariant for Teamspace is that `build_id` stays the only canonical
build identity. Team routing is intentionally **not** part of the shared contract.

### Mission Progress

For Teamspace v1, mission progress percentage is derived from canonical
work-package lane data already present in the shared contract:

- `WPStatusChanged` / status-transition payloads carry `from_lane`, `to_lane`,
  `mission_slug`, and `wp_id`.
- Consumers are expected to compute mission progress from the live distribution
  of work-package lanes rather than wait for a separate "progress percentage"
  event.

### Build Presentation State Inputs

For Teamspace v1, the shared contract does **not** mint SaaS-specific states such
as `private`, `shared`, or `disconnected`, and it does not mint a new
`merged_local_only` event family.

Instead, consumers combine:

- canonical event-envelope `build_id`
- host-owned build lifecycle signals (`BuildRegistered`, `BuildHeartbeat`, sync status)
- recent mission completion derived from work-package transitions

to classify surfaced Teamspace rows such as `active`, `recently_completed`, or
`merged_local_only`.

This keeps the reusable event contract free of team-boundary policy while still
giving hosts enough canonical inputs to build the Teamspace projection.
