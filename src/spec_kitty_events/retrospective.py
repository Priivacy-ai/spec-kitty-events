"""Retrospective event contracts.

Defines event type constants, payload models, and domain schema version
for the retrospective contract surface.

The original 4.0.0 public surface exposed two UpperCamelCase terminal
signals. The 4.1.0 surface keeps those symbols for compatibility and adds
the dot-name lifecycle/proposal events emitted by the Spec Kitty runtime.
"""
from __future__ import annotations

from datetime import datetime
from typing import FrozenSet, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from spec_kitty_events.dossier import ProvenanceRef

# ── Section 1: Schema Version ─────────────────────────────────────────────────

RETROSPECTIVE_SCHEMA_VERSION: str = "4.1.0"

# ── Section 2: Event Type Constants ──────────────────────────────────────────

RETROSPECTIVE_COMPLETED: str = "RetrospectiveCompleted"
RETROSPECTIVE_SKIPPED: str = "RetrospectiveSkipped"

RETROSPECTIVE_REQUESTED_EVENT: str = "retrospective.requested"
RETROSPECTIVE_STARTED_EVENT: str = "retrospective.started"
RETROSPECTIVE_COMPLETED_EVENT: str = "retrospective.completed"
RETROSPECTIVE_SKIPPED_EVENT: str = "retrospective.skipped"
RETROSPECTIVE_FAILED_EVENT: str = "retrospective.failed"
RETROSPECTIVE_PROPOSAL_GENERATED_EVENT: str = "retrospective.proposal.generated"
RETROSPECTIVE_PROPOSAL_APPLIED_EVENT: str = "retrospective.proposal.applied"
RETROSPECTIVE_PROPOSAL_REJECTED_EVENT: str = "retrospective.proposal.rejected"

RETROSPECTIVE_EVENT_NAMES: FrozenSet[str] = frozenset({
    RETROSPECTIVE_REQUESTED_EVENT,
    RETROSPECTIVE_STARTED_EVENT,
    RETROSPECTIVE_COMPLETED_EVENT,
    RETROSPECTIVE_SKIPPED_EVENT,
    RETROSPECTIVE_FAILED_EVENT,
    RETROSPECTIVE_PROPOSAL_GENERATED_EVENT,
    RETROSPECTIVE_PROPOSAL_APPLIED_EVENT,
    RETROSPECTIVE_PROPOSAL_REJECTED_EVENT,
})

RETROSPECTIVE_EVENT_TYPES: FrozenSet[str] = frozenset({
    RETROSPECTIVE_COMPLETED,
    RETROSPECTIVE_SKIPPED,
}) | RETROSPECTIVE_EVENT_NAMES

# ── Section 3: Type Aliases ──────────────────────────────────────────────────

TriggerSourceT = Literal["runtime", "operator", "policy"]
ActorKindT = Literal["human", "agent", "runtime"]
RetrospectiveModeValueT = Literal["autonomous", "human_in_command"]
ModeSourceKindT = Literal[
    "charter_override",
    "explicit_flag",
    "environment",
    "parent_process",
]
ProposalRejectedReasonT = Literal[
    "human_decline",
    "conflict",
    "stale_evidence",
    "invalid_payload",
]

# ── Section 4: Payload Models ────────────────────────────────────────────────


def _assert_iso8601_timestamp(value: object) -> object:
    """Validate an ISO 8601 timestamp across supported Python runtimes.

    Python 3.10's ``datetime.fromisoformat`` rejects a trailing ``Z`` even
    though the fixtures and contract use the RFC 3339 UTC form. Normalize that
    case to ``+00:00`` before parsing.
    """

    if isinstance(value, str):
        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
        datetime.fromisoformat(normalized)
    return value


class RetrospectiveCompletedPayload(BaseModel):
    """Payload for RetrospectiveCompleted events.

    Emitted when a retrospective step runs and produces a durable outcome.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    actor: str = Field(..., min_length=1, description="Actor who triggered the retrospective")
    trigger_source: TriggerSourceT = Field(
        ..., description="What initiated the retrospective"
    )
    artifact_ref: Optional[ProvenanceRef] = Field(
        None, description="Reference to retro artifact if one was produced"
    )
    completed_at: str = Field(
        ..., min_length=1, description="ISO 8601 completion timestamp"
    )

    @field_validator("completed_at", mode="before")
    @classmethod
    def _validate_completed_at_iso8601(cls, v: object) -> object:
        return _assert_iso8601_timestamp(v)


class RetrospectiveSkippedPayload(BaseModel):
    """Payload for RetrospectiveSkipped events.

    Emitted when a retrospective step is explicitly skipped.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    actor: str = Field(..., min_length=1, description="Actor who decided to skip")
    trigger_source: TriggerSourceT = Field(
        ..., description="What would have initiated the retrospective"
    )
    skip_reason: str = Field(
        ..., min_length=1, description="Why the retrospective was skipped"
    )
    skipped_at: str = Field(
        ..., min_length=1, description="ISO 8601 skip decision timestamp"
    )

    @field_validator("skipped_at", mode="before")
    @classmethod
    def _validate_skipped_at_iso8601(cls, v: object) -> object:
        return _assert_iso8601_timestamp(v)


class RetrospectiveActorRef(BaseModel):
    """Actor reference embedded in runtime retrospective events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ActorKindT
    id: str = Field(..., min_length=1)
    profile_id: Optional[str] = None


class RetrospectiveModeSourceSignal(BaseModel):
    """How retrospective execution mode was resolved."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ModeSourceKindT
    evidence: str = Field(..., min_length=1)


class RetrospectiveMode(BaseModel):
    """Resolved retrospective execution mode."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: RetrospectiveModeValueT
    source_signal: RetrospectiveModeSourceSignal


class RetrospectiveRequestedPayload(BaseModel):
    """Payload for ``retrospective.requested`` events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: RetrospectiveMode
    terminus_step_id: str = Field(..., min_length=1)
    requested_by: RetrospectiveActorRef


class RetrospectiveStartedPayload(BaseModel):
    """Payload for ``retrospective.started`` events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    facilitator_profile_id: str = Field(..., min_length=1)
    action_id: str = Field(..., min_length=1)


class RetrospectiveLifecycleCompletedPayload(BaseModel):
    """Payload for ``retrospective.completed`` events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    record_path: str = Field(..., min_length=1)
    record_hash: str = Field(..., min_length=1)
    findings_summary: dict[str, int]
    proposals_count: int = Field(..., ge=0)


class RetrospectiveLifecycleSkippedPayload(BaseModel):
    """Payload for ``retrospective.skipped`` events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    record_path: str = Field(..., min_length=1)
    skip_reason: str = Field(..., min_length=1)
    skipped_by: RetrospectiveActorRef


class RetrospectiveFailedPayload(BaseModel):
    """Payload for ``retrospective.failed`` events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    failure_code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    record_path: Optional[str] = None


class RetrospectiveProposalGeneratedPayload(BaseModel):
    """Payload for ``retrospective.proposal.generated`` events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    record_path: str = Field(..., min_length=1)


class RetrospectiveProposalAppliedPayload(BaseModel):
    """Payload for ``retrospective.proposal.applied`` events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    target_urn: str = Field(..., min_length=1)
    provenance_ref: str = Field(..., min_length=1)
    applied_by: RetrospectiveActorRef


class RetrospectiveProposalRejectedPayload(BaseModel):
    """Payload for ``retrospective.proposal.rejected`` events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    reason: ProposalRejectedReasonT
    detail: str = Field(..., min_length=1)
    rejected_by: RetrospectiveActorRef


# Short aliases matching the runtime-local model names used by the CLI before
# this surface moved into spec-kitty-events.
RequestedPayload = RetrospectiveRequestedPayload
StartedPayload = RetrospectiveStartedPayload
CompletedPayload = RetrospectiveLifecycleCompletedPayload
SkippedPayload = RetrospectiveLifecycleSkippedPayload
FailedPayload = RetrospectiveFailedPayload
ProposalGeneratedPayload = RetrospectiveProposalGeneratedPayload
ProposalAppliedPayload = RetrospectiveProposalAppliedPayload
ProposalRejectedPayload = RetrospectiveProposalRejectedPayload
