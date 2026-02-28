# Contract Specification: Mission Audit Lifecycle Events
# This file defines the canonical type signatures and module structure.
# It is a DESIGN ARTIFACT — not production code. Implementation follows in WPs.
#
# Module: src/spec_kitty_events/mission_audit.py

from __future__ import annotations

from enum import Enum
from typing import FrozenSet, List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_events.dossier import ContentHashRef, ProvenanceRef
from spec_kitty_events.models import Event

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------
AUDIT_SCHEMA_VERSION: str = "2.5.0"

# ---------------------------------------------------------------------------
# Event type constants (FR-001)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Enums (FR-008, FR-009, FR-010)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Value objects (FR-011)
# ---------------------------------------------------------------------------
class AuditArtifactRef(BaseModel):
    """Links an audit report to its content hash and provenance."""
    model_config = ConfigDict(frozen=True)

    report_path: str = Field(..., min_length=1)
    content_hash: ContentHashRef
    provenance: ProvenanceRef


class PendingDecision(BaseModel):
    """Tracks an unresolved decision checkpoint within the reducer."""
    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(..., min_length=1)
    question: str
    context_summary: str
    severity: AuditSeverity


# ---------------------------------------------------------------------------
# Payload models (FR-002 through FR-007)
# ---------------------------------------------------------------------------
class MissionAuditRequestedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    trigger_mode: Literal["manual", "post_merge"]
    audit_scope: List[str] = Field(..., min_length=1)
    enforcement_mode: Literal["advisory", "blocking"]


class MissionAuditStartedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    audit_scope_hash: str = Field(..., min_length=1)


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


class MissionAuditCompletedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    verdict: AuditVerdict
    severity: AuditSeverity
    findings_count: int = Field(..., ge=0)
    artifact_ref: AuditArtifactRef
    summary: str


class MissionAuditFailedPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    error_code: str = Field(..., min_length=1)
    error_message: str
    partial_artifact_ref: Optional[AuditArtifactRef] = None


# ---------------------------------------------------------------------------
# Reducer output models (FR-012 through FR-014)
# ---------------------------------------------------------------------------
class MissionAuditAnomaly(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str
    event_id: str
    message: str


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


# ---------------------------------------------------------------------------
# Reducer function (FR-012)
# ---------------------------------------------------------------------------
def reduce_mission_audit_events(events: Sequence[Event]) -> ReducedMissionAuditState:
    """Deterministic reducer: Sequence[Event] → ReducedMissionAuditState.

    Pipeline: sort → dedup → filter(MISSION_AUDIT_EVENT_TYPES) → reduce → freeze.
    """
    ...
