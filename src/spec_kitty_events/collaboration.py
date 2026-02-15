"""Collaboration event contracts for Feature 006.

Defines event type constants, identity models, payload models,
reducer output models, and the collaboration reducer for
multi-participant mission coordination.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, FrozenSet, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_events.models import SpecKittyEventsError

# ── Section 1: Constants ─────────────────────────────────────────────────────

PARTICIPANT_INVITED: str = "ParticipantInvited"
PARTICIPANT_JOINED: str = "ParticipantJoined"
PARTICIPANT_LEFT: str = "ParticipantLeft"
PRESENCE_HEARTBEAT: str = "PresenceHeartbeat"
DRIVE_INTENT_SET: str = "DriveIntentSet"
FOCUS_CHANGED: str = "FocusChanged"
PROMPT_STEP_EXECUTION_STARTED: str = "PromptStepExecutionStarted"
PROMPT_STEP_EXECUTION_COMPLETED: str = "PromptStepExecutionCompleted"
CONCURRENT_DRIVER_WARNING: str = "ConcurrentDriverWarning"
POTENTIAL_STEP_COLLISION_DETECTED: str = "PotentialStepCollisionDetected"
WARNING_ACKNOWLEDGED: str = "WarningAcknowledged"
COMMENT_POSTED: str = "CommentPosted"
DECISION_CAPTURED: str = "DecisionCaptured"
SESSION_LINKED: str = "SessionLinked"

COLLABORATION_EVENT_TYPES: FrozenSet[str] = frozenset({
    PARTICIPANT_INVITED,
    PARTICIPANT_JOINED,
    PARTICIPANT_LEFT,
    PRESENCE_HEARTBEAT,
    DRIVE_INTENT_SET,
    FOCUS_CHANGED,
    PROMPT_STEP_EXECUTION_STARTED,
    PROMPT_STEP_EXECUTION_COMPLETED,
    CONCURRENT_DRIVER_WARNING,
    POTENTIAL_STEP_COLLISION_DETECTED,
    WARNING_ACKNOWLEDGED,
    COMMENT_POSTED,
    DECISION_CAPTURED,
    SESSION_LINKED,
})

# ── Section 2: Identity and Target Models ────────────────────────────────────


class ParticipantIdentity(BaseModel):
    """SaaS-minted, mission-scoped participant identity."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="SaaS-minted, mission-scoped unique identifier"
    )
    participant_type: Literal["human", "llm_context"] = Field(
        ..., description="Participant category"
    )
    display_name: Optional[str] = Field(
        None, description="Human-readable name for display"
    )
    session_id: Optional[str] = Field(
        None, description="SaaS-issued session identifier"
    )


class AuthPrincipalBinding(BaseModel):
    """Roster-level auth principal to participant binding."""

    model_config = ConfigDict(frozen=True)

    auth_principal_id: str = Field(
        ..., min_length=1, description="Authenticated identity (opaque to this package)"
    )
    participant_id: str = Field(
        ..., min_length=1, description="Mission-scoped participant identifier"
    )
    bound_at: datetime = Field(
        ..., description="Timestamp when binding was created"
    )


class FocusTarget(BaseModel):
    """Structured focus reference. Hashable for use as dict key."""

    model_config = ConfigDict(frozen=True)

    target_type: Literal["wp", "step", "file"] = Field(
        ..., description="Category of focus target"
    )
    target_id: str = Field(
        ..., min_length=1, description="Identifier within the target type"
    )


class UnknownParticipantError(SpecKittyEventsError):
    """Raised in strict mode for events from non-rostered participants."""

    def __init__(
        self, participant_id: str, event_id: str, event_type: str
    ) -> None:
        self.participant_id = participant_id
        self.event_id = event_id
        self.event_type = event_type
        super().__init__(
            f"Unknown participant {participant_id!r} in event {event_id} "
            f"(type={event_type}). Not in mission roster."
        )


# ── Section 3: Payload Models ──  (populated by WP02-WP04)

# ── Section 4: Reducer Output Models ──────────────────────────────────────


class CollaborationAnomaly(BaseModel):
    """Non-fatal issue encountered during collaboration event reduction."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(..., description="Event that caused the anomaly")
    event_type: str = Field(..., description="Type of the problematic event")
    reason: str = Field(..., description="Human-readable anomaly description")


class WarningEntry(BaseModel):
    """Warning timeline entry in reduced collaboration state."""

    model_config = ConfigDict(frozen=True)

    warning_id: str = Field(..., description="Warning identifier")
    event_id: str = Field(..., description="Event that created this warning")
    warning_type: str = Field(
        ...,
        description="'ConcurrentDriverWarning' or 'PotentialStepCollisionDetected'",
    )
    participant_ids: Tuple[str, ...] = Field(
        ..., description="Affected participants"
    )
    acknowledgements: Dict[str, str] = Field(
        default_factory=dict,
        description="participant_id -> acknowledgement action",
    )


class DecisionEntry(BaseModel):
    """Decision history entry in reduced collaboration state."""

    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(..., description="Decision identifier")
    event_id: str = Field(..., description="Event that captured this decision")
    participant_id: str = Field(..., description="Decision author")
    topic: str = Field(..., description="Decision topic")
    chosen_option: str = Field(..., description="Selected option")
    referenced_warning_id: Optional[str] = Field(
        None, description="Related warning"
    )


class CommentEntry(BaseModel):
    """Comment history entry in reduced collaboration state."""

    model_config = ConfigDict(frozen=True)

    comment_id: str = Field(..., description="Comment identifier")
    event_id: str = Field(..., description="Event that posted this comment")
    participant_id: str = Field(..., description="Comment author")
    content: str = Field(..., description="Comment text")
    reply_to: Optional[str] = Field(None, description="Parent comment_id")


class ReducedCollaborationState(BaseModel):
    """Materialized collaboration state from event reduction."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., description="Mission this state represents"
    )
    participants: Dict[str, ParticipantIdentity] = Field(
        default_factory=dict,
        description="Active participant roster (participant_id -> identity)",
    )
    departed_participants: Dict[str, ParticipantIdentity] = Field(
        default_factory=dict,
        description="Historical departed participants",
    )
    presence: Dict[str, datetime] = Field(
        default_factory=dict,
        description="Last heartbeat timestamp per participant_id",
    )
    active_drivers: FrozenSet[str] = Field(
        default_factory=frozenset,
        description="participant_ids with active drive intent",
    )
    focus_by_participant: Dict[str, FocusTarget] = Field(
        default_factory=dict,
        description="Current focus per participant",
    )
    participants_by_focus: Dict[str, FrozenSet[str]] = Field(
        default_factory=dict,
        description="Reverse index: focus_key -> participant set",
    )
    warnings: Tuple[WarningEntry, ...] = Field(
        default_factory=tuple,
        description="Ordered warning timeline",
    )
    decisions: Tuple[DecisionEntry, ...] = Field(
        default_factory=tuple,
        description="Ordered decision history",
    )
    comments: Tuple[CommentEntry, ...] = Field(
        default_factory=tuple,
        description="Ordered comment history",
    )
    active_executions: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="In-flight step_ids per participant_id",
    )
    linked_sessions: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Linked session_ids per participant_id",
    )
    anomalies: Tuple[CollaborationAnomaly, ...] = Field(
        default_factory=tuple,
        description="Non-fatal issues encountered",
    )
    event_count: int = Field(
        default=0, description="Total events processed"
    )
    last_processed_event_id: Optional[str] = Field(
        None, description="Last event_id in processed sequence"
    )


# ── Section 5: Collaboration Reducer ──  (populated by WP06)
