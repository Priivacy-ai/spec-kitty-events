"""Mission Audit Lifecycle Event Contracts domain module.

Provides enums, event type constants, value objects, payload models,
the ReducedMissionAuditState output model, and a reducer stub for the
Mission Audit Lifecycle contract.
"""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet, List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_events.dossier import ContentHashRef, ProvenanceRef
from spec_kitty_events.models import Event
from spec_kitty_events.status import dedup_events, status_event_sort_key

# ── Section 1: Schema Version ─────────────────────────────────────────────────

AUDIT_SCHEMA_VERSION: str = "2.5.0"

# ── Section 2: Event Type Constants ──────────────────────────────────────────

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

# ── Section 3: Enums ──────────────────────────────────────────────────────────


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

# ── Section 4: Value Objects ──────────────────────────────────────────────────


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


class MissionAuditAnomaly(BaseModel):
    """Non-fatal issue recorded during reduction.

    Valid kind values: "event_before_requested", "event_after_terminal",
    "duplicate_decision_id", "unrecognized_event_type".
    """

    model_config = ConfigDict(frozen=True)

    kind: str
    event_id: str
    message: str


# ── Section 5: Payload Models ─────────────────────────────────────────────────


class MissionAuditRequestedPayload(BaseModel):
    """Payload for MissionAuditRequested events (FR-003)."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    trigger_mode: Literal["manual", "post_merge"]
    audit_scope: List[str] = Field(..., min_length=1)
    enforcement_mode: Literal["advisory", "blocking"]


class MissionAuditStartedPayload(BaseModel):
    """Payload for MissionAuditStarted events (FR-004)."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    audit_scope_hash: str = Field(..., min_length=1)


class MissionAuditDecisionRequestedPayload(BaseModel):
    """Payload for MissionAuditDecisionRequested events (FR-005)."""

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
    """Payload for MissionAuditCompleted events (FR-006).

    artifact_ref is required — not Optional. If artifact generation fails,
    the emitter MUST emit MissionAuditFailed instead.
    """

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
    """Payload for MissionAuditFailed events (FR-007)."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    feature_slug: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    error_code: str = Field(..., min_length=1)
    error_message: str
    partial_artifact_ref: Optional[AuditArtifactRef] = None


# ── Section 6: Reducer Output Model ──────────────────────────────────────────


class ReducedMissionAuditState(BaseModel):
    """Deterministic projection output of reduce_mission_audit_events() (FR-012–FR-014, R-005)."""

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


# ── Section 7: Reducer Stub ───────────────────────────────────────────────────


def reduce_mission_audit_events(events: Sequence[Event]) -> ReducedMissionAuditState:
    """Deterministic reducer: Sequence[Event] → ReducedMissionAuditState.

    Pipeline: sort → dedup → filter(MISSION_AUDIT_EVENT_TYPES) → reduce → freeze.
    """
    raise NotImplementedError  # WP02 fills in the full implementation
