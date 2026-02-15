"""Collaboration event contracts for Feature 006.

Defines event type constants, identity models, payload models,
reducer output models, and the collaboration reducer for
multi-participant mission coordination.
"""

from __future__ import annotations

from datetime import datetime
from typing import FrozenSet, Literal, Optional

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

# ── Section 4: Reducer Output Models ──  (populated by WP05)

# ── Section 5: Collaboration Reducer ──  (populated by WP06)
