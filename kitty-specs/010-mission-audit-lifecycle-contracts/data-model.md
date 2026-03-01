# Data Model: Mission Audit Lifecycle Contracts

**Feature**: 010-mission-audit-lifecycle-contracts
**Date**: 2026-02-25
**Module**: `src/spec_kitty_events/mission_audit.py`

## Enums

### AuditVerdict (str, Enum)
Constrained vocabulary for audit outcomes.

| Value | Description |
|---|---|
| `pass` | Audit completed with no findings |
| `pass_with_warnings` | Audit completed with non-blocking findings |
| `fail` | Audit completed with blocking findings |
| `blocked_decision_required` | Audit cannot conclude without human decision |

### AuditSeverity (str, Enum)
Constrained vocabulary for finding severity levels.

| Value | Description |
|---|---|
| `info` | Informational finding |
| `warning` | Non-blocking finding |
| `error` | Blocking finding |
| `critical` | Severe blocking finding |

### AuditStatus (str, Enum)
Reducer state machine positions.

| Value | Description |
|---|---|
| `pending` | Initial state (after Requested, before Started) |
| `running` | Audit execution in progress |
| `awaiting_decision` | Blocked on human decision checkpoint |
| `completed` | Terminal: audit finished successfully |
| `failed` | Terminal: audit finished with error |

**Terminal statuses**: `{completed, failed}` → exposed as `TERMINAL_AUDIT_STATUSES: FrozenSet[AuditStatus]`

## Event Type Constants

| Constant | String Value | Payload Model |
|---|---|---|
| `MISSION_AUDIT_REQUESTED` | `"MissionAuditRequested"` | `MissionAuditRequestedPayload` |
| `MISSION_AUDIT_STARTED` | `"MissionAuditStarted"` | `MissionAuditStartedPayload` |
| `MISSION_AUDIT_DECISION_REQUESTED` | `"MissionAuditDecisionRequested"` | `MissionAuditDecisionRequestedPayload` |
| `MISSION_AUDIT_COMPLETED` | `"MissionAuditCompleted"` | `MissionAuditCompletedPayload` |
| `MISSION_AUDIT_FAILED` | `"MissionAuditFailed"` | `MissionAuditFailedPayload` |

**Family set**: `MISSION_AUDIT_EVENT_TYPES: FrozenSet[str]` containing all five string values.

## Value Objects

### AuditArtifactRef (frozen)
Links an audit report to its content hash and provenance. Composes dossier value objects.

| Field | Type | Constraint | Source |
|---|---|---|---|
| `report_path` | `str` | `min_length=1` | FR-011 |
| `content_hash` | `ContentHashRef` | required | FR-011, imported from dossier.py |
| `provenance` | `ProvenanceRef` | required | FR-011, imported from dossier.py |

### PendingDecision (frozen)
Tracks an unresolved decision checkpoint within the reducer.

| Field | Type | Constraint |
|---|---|---|
| `decision_id` | `str` | `min_length=1` |
| `question` | `str` | required |
| `context_summary` | `str` | required |
| `severity` | `AuditSeverity` | required |

### MissionAuditAnomaly (frozen)
Non-fatal issue recorded during event reduction.

| Field | Type | Constraint |
|---|---|---|
| `kind` | `str` | one of: `"event_before_requested"`, `"event_after_terminal"`, `"duplicate_decision_id"`, `"unrecognized_event_type"` |
| `event_id` | `str` | the offending event's ID |
| `message` | `str` | human-readable description |

## Payload Models (all frozen)

### Common Fields (shared by all 5 payloads)

| Field | Type | Constraint | Source |
|---|---|---|---|
| `mission_id` | `str` | `min_length=1` | FR-002 |
| `run_id` | `str` | `min_length=1` | FR-002 |
| `feature_slug` | `str` | `min_length=1` | FR-002 |
| `actor` | `str` | `min_length=1` | FR-002 |

### MissionAuditRequestedPayload

| Field | Type | Constraint | Source |
|---|---|---|---|
| *(common fields)* | | | FR-002 |
| `trigger_mode` | `Literal["manual", "post_merge"]` | required | FR-003 |
| `audit_scope` | `List[str]` | required, non-empty | FR-003 |
| `enforcement_mode` | `Literal["advisory", "blocking"]` | required | FR-003 |

### MissionAuditStartedPayload

| Field | Type | Constraint | Source |
|---|---|---|---|
| *(common fields)* | | | FR-002 |
| `audit_scope_hash` | `str` | `min_length=1` | FR-004 |

### MissionAuditDecisionRequestedPayload

| Field | Type | Constraint | Source |
|---|---|---|---|
| *(common fields)* | | | FR-002 |
| `decision_id` | `str` | `min_length=1` | FR-005 |
| `question` | `str` | required | FR-005 |
| `context_summary` | `str` | required | FR-005 |
| `severity` | `AuditSeverity` | required | FR-005 |

### MissionAuditCompletedPayload

| Field | Type | Constraint | Source |
|---|---|---|---|
| *(common fields)* | | | FR-002 |
| `verdict` | `AuditVerdict` | required | FR-006 |
| `severity` | `AuditSeverity` | required | FR-006 |
| `findings_count` | `int` | `ge=0` | FR-006 |
| `artifact_ref` | `AuditArtifactRef` | required (not Optional) | FR-006, checklist rev #1 |
| `summary` | `str` | required | FR-006 |

### MissionAuditFailedPayload

| Field | Type | Constraint | Source |
|---|---|---|---|
| *(common fields)* | | | FR-002 |
| `error_code` | `str` | `min_length=1` | FR-007 |
| `error_message` | `str` | required | FR-007 |
| `partial_artifact_ref` | `Optional[AuditArtifactRef]` | default=None | FR-007 |

## Reducer Output Model

### ReducedMissionAuditState (frozen)

| Field | Type | Default | Source |
|---|---|---|---|
| `audit_status` | `AuditStatus` | `AuditStatus.PENDING` | FR-012 |
| `verdict` | `Optional[AuditVerdict]` | `None` | FR-012 |
| `severity` | `Optional[AuditSeverity]` | `None` | FR-012 |
| `findings_count` | `Optional[int]` | `None` | FR-012 |
| `artifact_ref` | `Optional[AuditArtifactRef]` | `None` | FR-012 |
| `partial_artifact_ref` | `Optional[AuditArtifactRef]` | `None` | FR-012 |
| `summary` | `Optional[str]` | `None` | FR-012 |
| `error_code` | `Optional[str]` | `None` | FR-012 |
| `error_message` | `Optional[str]` | `None` | FR-012 |
| `pending_decisions` | `Tuple[PendingDecision, ...]` | `()` | FR-014, R-005 |
| `mission_id` | `Optional[str]` | `None` | FR-012 |
| `run_id` | `Optional[str]` | `None` | FR-012 |
| `feature_slug` | `Optional[str]` | `None` | FR-012 |
| `trigger_mode` | `Optional[str]` | `None` | FR-012 |
| `enforcement_mode` | `Optional[str]` | `None` | FR-012 |
| `audit_scope` | `Optional[Tuple[str, ...]]` | `None` | FR-012 |
| `audit_scope_hash` | `Optional[str]` | `None` | FR-012 |
| `anomalies` | `Tuple[MissionAuditAnomaly, ...]` | `()` | FR-014 |
| `event_count` | `int` | `0` | FR-012 |

## State Machine Transitions

```
                    ┌─ DecisionRequested ─┐
                    │                     │
Requested → Started ├─ Completed ─────────┤ (terminal)
                    │                     │
                    └─ Failed ────────────┘ (terminal)
```

**State mapping**:
- No events → `pending`
- After `Requested` → `pending`
- After `Started` → `running`
- After `DecisionRequested` (while running) → `awaiting_decision`
- After `Completed` → `completed` (terminal)
- After `Failed` → `failed` (terminal)

## Relationships

```
mission_audit.py ──imports──▶ dossier.py (ContentHashRef, ProvenanceRef)
mission_audit.py ──imports──▶ status.py (status_event_sort_key, dedup_events)
mission_audit.py ──imports──▶ models.py (Event)
conformance/validators.py ──imports──▶ mission_audit.py (5 payload models)
conformance/loader.py ──adds category──▶ "mission_audit"
__init__.py ──re-exports──▶ mission_audit.py (~22 symbols)
```
