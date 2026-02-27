# Research: Mission Audit Lifecycle Contracts

**Feature**: 010-mission-audit-lifecycle-contracts
**Date**: 2026-02-25
**Status**: Complete

## R-001: Reducer Pipeline Pattern

**Decision**: Reuse the established reducer pipeline from lifecycle.py / dossier.py / mission_next.py.

**Rationale**: All existing reducers in spec-kitty-events follow the same pipeline: sort → dedup → partition → reduce → freeze. The audit reducer has no reason to deviate. Reusing `status_event_sort_key` (Lamport clock ordering) and `dedup_events` (event_id deduplication) from `status.py` ensures consistency and avoids reimplementation.

**Alternatives considered**:
- Custom sort/dedup: Rejected — would duplicate proven logic and diverge from established patterns.

## R-002: Actor Field Type

**Decision**: `actor: str` (simple actor identifier string) for all five payload models.

**Rationale**: The spec (FR-002) lists `actor` as a common field without specifying a structured type. Mission-audit events are system-level post-merge audit operations. Unlike mission_next (which uses `RuntimeActorIdentity` for rich agent metadata), audit events need only identify *who triggered* the audit. A simple string is sufficient and avoids coupling audit contracts to mission-next value objects.

**Alternatives considered**:
- `RuntimeActorIdentity` (from mission_next.py): Rejected — adds unnecessary coupling between audit and mission-next families. If audit needs structured actor info in the future, it can define its own `AuditActorIdentity` (breaking change, 3.x scope).
- `AuditActorIdentity` (new structured type): Rejected — over-engineering for current requirements. The spec doesn't specify structured actor data.

## R-003: AuditArtifactRef Composition with Dossier Value Objects

**Decision**: `AuditArtifactRef` composes `ContentHashRef` and `ProvenanceRef` from `dossier.py` via import — no duplication.

**Rationale**: FR-011 and FR-020 are explicit: the audit artifact reference must compose existing dossier value objects. `ContentHashRef` provides hash/algorithm/size/encoding. `ProvenanceRef` provides source_event_ids/git_sha/git_ref/actor metadata. Both are frozen Pydantic models already exported from `__init__.py`.

**Alternatives considered**:
- Duplicate the value objects in mission_audit.py: Rejected by FR-020 (explicit prohibition).
- Create audit-specific hash/provenance types: Rejected — identical semantics, would fragment the contract surface.

## R-004: Conformance Fixture Layout

**Decision**: `conformance/fixtures/mission_audit/{valid,invalid,replay}/` directory structure with entries in `manifest.json`.

**Rationale**: Follows the exact pattern established by dossier (10 valid + 3 invalid + 3 replay) and mission_next fixtures. The audit family requires 7 valid + 3 invalid + 3 replay (FR-016). Replay streams use JSONL format (one Event envelope per line).

**Fixture plan**:

### Valid fixtures (7)
| ID | Event Type | Notes |
|---|---|---|
| `mission-audit-requested-manual` | MissionAuditRequested | Manual trigger, advisory enforcement |
| `mission-audit-requested-post-merge` | MissionAuditRequested | Post-merge trigger, blocking enforcement |
| `mission-audit-started-valid` | MissionAuditStarted | With scope hash |
| `mission-audit-decision-requested-valid` | MissionAuditDecisionRequested | Warning severity, with decision_id |
| `mission-audit-completed-pass` | MissionAuditCompleted | Verdict=pass, populated artifact_ref |
| `mission-audit-completed-fail` | MissionAuditCompleted | Verdict=fail, severity=error, findings_count>0 |
| `mission-audit-failed-valid` | MissionAuditFailed | Error code + partial artifact ref |

### Invalid fixtures (4)
| ID | Event Type | Missing/Invalid Field |
|---|---|---|
| `mission-audit-completed-missing-verdict` | MissionAuditCompleted | Missing `verdict` field |
| `mission-audit-completed-missing-artifact-ref` | MissionAuditCompleted | Missing `artifact_ref` field (locked: required, not Optional) |
| `mission-audit-requested-bad-trigger` | MissionAuditRequested | Invalid `trigger_mode` value |
| `mission-audit-decision-missing-id` | MissionAuditDecisionRequested | Missing `decision_id` field |

### Replay streams (3 JSONL)
| ID | Scenario | Terminal State |
|---|---|---|
| `mission-audit-replay-pass` | Requested → Started → Completed(pass) | completed |
| `mission-audit-replay-fail` | Requested → Started → Failed | failed |
| `mission-audit-replay-decision-checkpoint` | Requested → Started → DecisionRequested → Completed(pass_with_warnings) | completed |

### Reducer output snapshots (3 JSON)
One golden-file per replay stream, committed for determinism verification.

## R-005: ReducedMissionAuditState Fields

**Decision**: Frozen model with fields derived from the spec's reducer requirements (FR-012 through FR-014) and established patterns (lifecycle.py, mission_next.py).

**Fields**:
| Field | Type | Source |
|---|---|---|
| `audit_status` | `AuditStatus` | State machine: pending → running → {awaiting_decision, completed, failed} |
| `verdict` | `Optional[AuditVerdict]` | From MissionAuditCompleted (None if failed/incomplete) |
| `severity` | `Optional[AuditSeverity]` | From MissionAuditCompleted |
| `findings_count` | `Optional[int]` | From MissionAuditCompleted |
| `artifact_ref` | `Optional[AuditArtifactRef]` | From MissionAuditCompleted |
| `partial_artifact_ref` | `Optional[AuditArtifactRef]` | From MissionAuditFailed |
| `summary` | `Optional[str]` | From MissionAuditCompleted |
| `error_code` | `Optional[str]` | From MissionAuditFailed |
| `error_message` | `Optional[str]` | From MissionAuditFailed |
| `pending_decisions` | `Tuple[PendingDecision, ...]` | Full decision objects from DecisionRequested; cleared on terminal |
| `mission_id` | `Optional[str]` | From first MissionAuditRequested |
| `run_id` | `Optional[str]` | From first MissionAuditRequested |
| `feature_slug` | `Optional[str]` | From first MissionAuditRequested |
| `trigger_mode` | `Optional[str]` | From MissionAuditRequested |
| `enforcement_mode` | `Optional[str]` | From MissionAuditRequested |
| `audit_scope` | `Optional[Tuple[str, ...]]` | From MissionAuditRequested |
| `audit_scope_hash` | `Optional[str]` | From MissionAuditStarted |
| `anomalies` | `Tuple[MissionAuditAnomaly, ...]` | Non-fatal issues |
| `event_count` | `int` | Count of processed events (post-dedup) |

## R-006: MissionAuditAnomaly Fields

**Decision**: Frozen dataclass following `LifecycleAnomaly` / `MissionNextAnomaly` / `CollaborationAnomaly` pattern.

**Fields**:
| Field | Type | Description |
|---|---|---|
| `kind` | `str` | Anomaly classification (e.g., "event_before_requested", "event_after_terminal", "duplicate_decision_id", "unrecognized_event_type") |
| `event_id` | `str` | The event that triggered the anomaly |
| `message` | `str` | Human-readable description |

## R-007: Conformance Loader Extension

**Decision**: Add `"mission_audit"` to `_VALID_CATEGORIES` in `loader.py`.

**Rationale**: The loader filters fixtures by category prefix in path. Adding the category enables `load_fixtures("mission_audit")` and replay stream loading via `load_replay_stream("mission-audit-replay-pass")`.

## R-008: Schema Generation

**Decision**: Generate 5 JSON Schema files in `schemas/` directory matching existing pattern, plus register 5 entries in `_EVENT_TYPE_TO_SCHEMA` mapping.

**Schema files**:
- `mission_audit_requested_payload.json`
- `mission_audit_started_payload.json`
- `mission_audit_decision_requested_payload.json`
- `mission_audit_completed_payload.json`
- `mission_audit_failed_payload.json`

## R-009: Version Bump Strategy

**Decision**: Bump `pyproject.toml` version from `2.4.0` to `2.5.0` and update `__version__` in `__init__.py`. Add `AUDIT_SCHEMA_VERSION: str = "2.5.0"` constant in `mission_audit.py`.

**Rationale**: FR-018 mandates schema version `"2.5.0"`. This is a minor version bump (additive feature, no breaking changes). Existing `SCHEMA_VERSION` in lifecycle.py remains `"2.0.0"` (unchanged).

## R-010: Public API Export Count

**Decision**: Add 23 new exports to `__init__.py`, bringing total from ~88 to ~111.

**New exports**:
- 5 event type constants: `MISSION_AUDIT_REQUESTED`, `MISSION_AUDIT_STARTED`, `MISSION_AUDIT_DECISION_REQUESTED`, `MISSION_AUDIT_COMPLETED`, `MISSION_AUDIT_FAILED`
- 1 frozenset: `MISSION_AUDIT_EVENT_TYPES`
- 3 enums: `AuditVerdict`, `AuditSeverity`, `AuditStatus`
- 2 value objects: `AuditArtifactRef`, `PendingDecision`
- 5 payload models: `MissionAuditRequestedPayload`, `MissionAuditStartedPayload`, `MissionAuditDecisionRequestedPayload`, `MissionAuditCompletedPayload`, `MissionAuditFailedPayload`
- 1 anomaly type: `MissionAuditAnomaly`
- 1 reducer output: `ReducedMissionAuditState`
- 1 reducer function: `reduce_mission_audit_events`
- 1 version constant: `AUDIT_SCHEMA_VERSION`
- 1 terminal statuses: `TERMINAL_AUDIT_STATUSES`
