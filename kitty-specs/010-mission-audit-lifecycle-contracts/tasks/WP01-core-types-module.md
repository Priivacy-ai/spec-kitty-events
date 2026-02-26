---
work_package_id: WP01
title: Core Types Module
lane: "for_review"
dependencies: []
base_branch: main
base_commit: a7ba75c9d083900f32eaf9c041d9657e316c0dd2
created_at: '2026-02-26T12:28:54.064323+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Core Types
assignee: ''
agent: claude-sonnet
shell_pid: '28510'
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-25T00:00:00Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Core Types Module

## Goal

Create `src/spec_kitty_events/mission_audit.py` with all enums, event type constants, value objects, payload models, and the `ReducedMissionAuditState` output model plus a stub reducer signature. This is the foundational contract that every downstream WP depends on — WP02 (reducer) and WP03 (conformance) cannot start until this lands.

**Independent Test**: `from spec_kitty_events import mission_audit; mypy --strict src/spec_kitty_events/mission_audit.py` returns zero errors. Each payload model round-trips through `model_validate(model.model_dump(mode="json"))`.

## Context

Feature 010 adds five canonical mission-audit lifecycle event contracts (`MissionAuditRequested`, `Started`, `DecisionRequested`, `Completed`, `Failed`) with a deterministic reducer, conformance fixtures, and full public API export. Target release is `spec-kitty-events 2.5.0` — purely additive, zero breaking changes.

**Existing patterns to follow**:
- Every event family has a dedicated module (e.g., `dossier.py`, `mission_next.py`). `mission_audit.py` follows the same pattern.
- All models use `ConfigDict(frozen=True)` (FR-019).
- Value objects from `dossier.py` (`ContentHashRef`, `ProvenanceRef`) are imported and composed — never duplicated (FR-020).
- The reducer pipeline uses `status_event_sort_key` and `dedup_events` from `status.py` — stub the function body now; WP02 fills it in.

**Branch**: `010-mission-audit-lifecycle-contracts` from `2.x`.

## Subtasks

### T001 — Create enums + constants in `mission_audit.py`

Create the file `src/spec_kitty_events/mission_audit.py` with:

1. File header:
   ```python
   from __future__ import annotations
   ```

2. Imports block:
   ```python
   from enum import Enum
   from typing import FrozenSet, List, Literal, Optional, Sequence, Tuple

   from pydantic import BaseModel, ConfigDict, Field

   from spec_kitty_events.dossier import ContentHashRef, ProvenanceRef
   from spec_kitty_events.models import Event
   from spec_kitty_events.status import dedup_events, status_event_sort_key
   ```

3. Schema version constant:
   ```python
   AUDIT_SCHEMA_VERSION: str = "2.5.0"
   ```

4. Event type constants (FR-001):
   ```python
   MISSION_AUDIT_REQUESTED: str = "MissionAuditRequested"
   MISSION_AUDIT_STARTED: str = "MissionAuditStarted"
   MISSION_AUDIT_DECISION_REQUESTED: str = "MissionAuditDecisionRequested"
   MISSION_AUDIT_COMPLETED: str = "MissionAuditCompleted"
   MISSION_AUDIT_FAILED: str = "MissionAuditFailed"

   MISSION_AUDIT_EVENT_TYPES: FrozenSet[str] = frozenset({
       MISSION_AUDIT_REQUESTED,
       MISSION_AUDIT_STARTED,
       MISSION_AUDIT_DECISION_REQUESTED,
       MISSION_AUDIT_COMPLETED,
       MISSION_AUDIT_FAILED,
   })
   ```

5. Enums (FR-008, FR-009, FR-010):
   ```python
   class AuditVerdict(str, Enum):
       PASS = "pass"
       PASS_WITH_WARNINGS = "pass_with_warnings"
       FAIL = "fail"
       BLOCKED_DECISION_REQUIRED = "blocked_decision_required"

   class AuditSeverity(str, Enum):
       INFO = "info"
       WARNING = "warning"
       ERROR = "error"
       CRITICAL = "critical"

   class AuditStatus(str, Enum):
       PENDING = "pending"
       RUNNING = "running"
       AWAITING_DECISION = "awaiting_decision"
       COMPLETED = "completed"
       FAILED = "failed"

   TERMINAL_AUDIT_STATUSES: FrozenSet[AuditStatus] = frozenset({
       AuditStatus.COMPLETED,
       AuditStatus.FAILED,
   })
   ```

### T002 — Add frozen value objects to `mission_audit.py`

Add the following frozen Pydantic models after the enums:

1. `AuditArtifactRef` — links an audit report to its content hash and provenance. Composes dossier types (FR-011):
   ```python
   class AuditArtifactRef(BaseModel):
       """Links an audit report to its content hash and provenance."""
       model_config = ConfigDict(frozen=True)

       report_path: str = Field(..., min_length=1)
       content_hash: ContentHashRef
       provenance: ProvenanceRef
   ```
   **Critical**: Field name is `content_hash` (not `hash`) to avoid shadowing Python builtins.

2. `PendingDecision` — tracks an unresolved decision checkpoint:
   ```python
   class PendingDecision(BaseModel):
       """Tracks an unresolved decision checkpoint within the reducer."""
       model_config = ConfigDict(frozen=True)

       decision_id: str = Field(..., min_length=1)
       question: str
       context_summary: str
       severity: AuditSeverity
   ```

3. `MissionAuditAnomaly` — non-fatal issue recorded during reduction (follows `LifecycleAnomaly`, `MissionNextAnomaly`, `CollaborationAnomaly` pattern from R-006):
   ```python
   class MissionAuditAnomaly(BaseModel):
       model_config = ConfigDict(frozen=True)

       kind: str
       event_id: str
       message: str
   ```
   Valid `kind` values: `"event_before_requested"`, `"event_after_terminal"`, `"duplicate_decision_id"`, `"unrecognized_event_type"`.

### T003 — Add 5 frozen payload models to `mission_audit.py`

All payloads share common fields (FR-002):
- `mission_id: str = Field(..., min_length=1)`
- `run_id: str = Field(..., min_length=1)`
- `feature_slug: str = Field(..., min_length=1)`
- `actor: str = Field(..., min_length=1)`

Add each with `model_config = ConfigDict(frozen=True)`:

1. **`MissionAuditRequestedPayload`** (FR-003):
   ```python
   class MissionAuditRequestedPayload(BaseModel):
       model_config = ConfigDict(frozen=True)
       mission_id: str = Field(..., min_length=1)
       run_id: str = Field(..., min_length=1)
       feature_slug: str = Field(..., min_length=1)
       actor: str = Field(..., min_length=1)
       trigger_mode: Literal["manual", "post_merge"]
       audit_scope: List[str] = Field(..., min_length=1)
       enforcement_mode: Literal["advisory", "blocking"]
   ```

2. **`MissionAuditStartedPayload`** (FR-004):
   ```python
   class MissionAuditStartedPayload(BaseModel):
       model_config = ConfigDict(frozen=True)
       mission_id: str = Field(..., min_length=1)
       run_id: str = Field(..., min_length=1)
       feature_slug: str = Field(..., min_length=1)
       actor: str = Field(..., min_length=1)
       audit_scope_hash: str = Field(..., min_length=1)
   ```

3. **`MissionAuditDecisionRequestedPayload`** (FR-005):
   ```python
   class MissionAuditDecisionRequestedPayload(BaseModel):
       model_config = ConfigDict(frozen=True)
       mission_id: str = Field(..., min_length=1)
       run_id: str = Field(..., min_length=1)
       feature_slug: str = Field(..., min_length=1)
       actor: str = Field(..., min_length=1)
       decision_id: str = Field(..., min_length=1)
       question: str
       context_summary: str
       severity: AuditSeverity
   ```

4. **`MissionAuditCompletedPayload`** (FR-006):
   ```python
   class MissionAuditCompletedPayload(BaseModel):
       model_config = ConfigDict(frozen=True)
       mission_id: str = Field(..., min_length=1)
       run_id: str = Field(..., min_length=1)
       feature_slug: str = Field(..., min_length=1)
       actor: str = Field(..., min_length=1)
       verdict: AuditVerdict
       severity: AuditSeverity
       findings_count: int = Field(..., ge=0)
       artifact_ref: AuditArtifactRef      # required — not Optional (FR-006)
       summary: str
   ```

5. **`MissionAuditFailedPayload`** (FR-007):
   ```python
   class MissionAuditFailedPayload(BaseModel):
       model_config = ConfigDict(frozen=True)
       mission_id: str = Field(..., min_length=1)
       run_id: str = Field(..., min_length=1)
       feature_slug: str = Field(..., min_length=1)
       actor: str = Field(..., min_length=1)
       error_code: str = Field(..., min_length=1)
       error_message: str
       partial_artifact_ref: Optional[AuditArtifactRef] = None
   ```

### T004 — Add `ReducedMissionAuditState` frozen output model + reducer stub

1. Add the frozen output model (FR-012 through FR-014, R-005):
   ```python
   class ReducedMissionAuditState(BaseModel):
       model_config = ConfigDict(frozen=True)

       audit_status: AuditStatus = AuditStatus.PENDING
       verdict: Optional[AuditVerdict] = None
       severity: Optional[AuditSeverity] = None
       findings_count: Optional[int] = None
       artifact_ref: Optional[AuditArtifactRef] = None
       partial_artifact_ref: Optional[AuditArtifactRef] = None
       summary: Optional[str] = None
       error_code: Optional[str] = None
       error_message: Optional[str] = None
       pending_decisions: Tuple[PendingDecision, ...] = ()
       mission_id: Optional[str] = None
       run_id: Optional[str] = None
       feature_slug: Optional[str] = None
       trigger_mode: Optional[str] = None
       enforcement_mode: Optional[str] = None
       audit_scope: Optional[Tuple[str, ...]] = None
       audit_scope_hash: Optional[str] = None
       anomalies: Tuple[MissionAuditAnomaly, ...] = ()
       event_count: int = 0
   ```

   Note: `audit_scope` is `Optional[Tuple[str, ...]]` in the state (not `List[str]`) — the reducer converts the list to a tuple for immutability.

2. Add the reducer stub — body implemented in WP02:
   ```python
   def reduce_mission_audit_events(events: Sequence[Event]) -> ReducedMissionAuditState:
       """Deterministic reducer: Sequence[Event] → ReducedMissionAuditState.

       Pipeline: sort → dedup → filter(MISSION_AUDIT_EVENT_TYPES) → reduce → freeze.
       """
       ...
   ```

## Acceptance Criteria

- [ ] `from spec_kitty_events import mission_audit` succeeds with no import errors
- [ ] `mypy --strict src/spec_kitty_events/mission_audit.py` reports zero errors
- [ ] Each of the 5 payload models round-trips: `model_validate(model.model_dump(mode="json"))` produces identical data
- [ ] All 5 payload models reject missing required fields with `ValidationError`
- [ ] `MissionAuditCompletedPayload(findings_count=-1, ...)` raises `ValidationError` (ge=0 constraint)
- [ ] `MissionAuditRequestedPayload(trigger_mode="invalid", ...)` raises `ValidationError` (Literal constraint)
- [ ] `MissionAuditCompletedPayload(enforcement_mode="invalid", ...)` raises `ValidationError` (Literal constraint)
- [ ] All frozen models raise `TypeError` on attribute assignment after construction
- [ ] `AuditArtifactRef` with real `ContentHashRef` and `ProvenanceRef` instances round-trips cleanly
- [ ] `MISSION_AUDIT_EVENT_TYPES` contains exactly 5 string values
- [ ] `TERMINAL_AUDIT_STATUSES` contains `{AuditStatus.COMPLETED, AuditStatus.FAILED}`
- [ ] `ReducedMissionAuditState()` (no args) constructs with all defaults (audit_status=pending, event_count=0, empty tuples)

## Implementation Notes

- **Python target**: Python ≥3.10, mypy strict targeting 3.10. Always start with `from __future__ import annotations`.
- **`from __future__ import annotations`** changes how Pydantic resolves forward refs — use distinct variable names per type branch to satisfy mypy strict mode; avoid shadowing.
- **Import order**: `status.py` imports (`dedup_events`, `status_event_sort_key`) are needed for the reducer in WP02 — import them now even though the stub body is `...`.
- **No duplication**: `ContentHashRef` and `ProvenanceRef` come from `spec_kitty_events.dossier` — do not redefine them (FR-020).
- **`artifact_ref` in `MissionAuditCompletedPayload`**: This is required (not `Optional`). If artifact generation fails, the emitter MUST emit `MissionAuditFailed` instead — this is a locked decision from plan.md.
- **`audit_scope` field type**: In payload it is `List[str]` (JSON-serializable); in `ReducedMissionAuditState` it is `Optional[Tuple[str, ...]]` (immutable). The reducer (WP02) converts between them.
- **Stub body**: The `reduce_mission_audit_events` function body is `...` (Ellipsis). WP02 fills in the full implementation.

## Test Commands

```bash
# Quick smoke test after creating the file
python3.11 -c "
from spec_kitty_events import mission_audit
from spec_kitty_events.mission_audit import (
    AuditVerdict, AuditSeverity, AuditStatus,
    MISSION_AUDIT_REQUESTED, MISSION_AUDIT_EVENT_TYPES,
    TERMINAL_AUDIT_STATUSES, AUDIT_SCHEMA_VERSION,
    MissionAuditRequestedPayload, MissionAuditStartedPayload,
    MissionAuditDecisionRequestedPayload,
    MissionAuditCompletedPayload, MissionAuditFailedPayload,
    AuditArtifactRef, PendingDecision, MissionAuditAnomaly,
    ReducedMissionAuditState, reduce_mission_audit_events,
)
print('All imports OK')
assert len(MISSION_AUDIT_EVENT_TYPES) == 5
assert AUDIT_SCHEMA_VERSION == '2.5.0'
state = ReducedMissionAuditState()
assert state.audit_status == AuditStatus.PENDING
assert state.event_count == 0
print('Smoke test passed')
"

# mypy strict check
mypy --strict src/spec_kitty_events/mission_audit.py
```

## Files to Create/Modify

| File | Action |
|---|---|
| `src/spec_kitty_events/mission_audit.py` | **CREATE** — complete module with enums, constants, value objects, payload models, output model, reducer stub |

No other files are modified in WP01.

## Dependencies

- **Depends on**: Nothing — this is the starting package.
- **Unblocks**: WP02 (reducer + tests) and WP03 (conformance integration) — both can start in parallel after WP01 lands.

## Completion Steps

When all subtasks are done and acceptance criteria pass:

1. Run the smoke test and mypy check (commands above).
2. Commit: `git add src/spec_kitty_events/mission_audit.py && git commit -m "feat(010): core types module — enums, value objects, payload models, reducer stub"`
3. Update this WP file's `lane` from `planned` → `for_review` and append to `history`.

## Activity Log

- 2026-02-26T12:28:54Z – claude-sonnet – shell_pid=28510 – lane=doing – Assigned agent via workflow command
- 2026-02-26T12:31:48Z – claude-sonnet – shell_pid=28510 – lane=for_review – Ready for review: mission_audit.py created with all enums, value objects (AuditArtifactRef, PendingDecision, MissionAuditAnomaly), 5 payload models, ReducedMissionAuditState, and reducer stub. All acceptance criteria pass: imports OK, mypy --strict zero errors, round-trips clean, Literal/ge constraints enforced, frozen immutability confirmed.
