"""Mission lifecycle event contracts for the canonical event schema.

This module defines typed payload models for all mission-level lifecycle
events, the MissionStatus enum, event type constants, and the SCHEMA_VERSION
constant. It is part of the canonical event contract (Feature 004).

Sections:
    1. Constants (SCHEMA_VERSION, event type strings)
    2. MissionStatus Enum
    3. Lifecycle Payload Models
    4. Lifecycle Reducer Output Models (added in WP03)
    5. Lifecycle Reducer (added in WP03)
"""

from enum import Enum
from typing import FrozenSet, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ── Section 1: Constants ─────────────────────────────────────────────────────

SCHEMA_VERSION: str = "1.0.0"

# Event type string constants
MISSION_STARTED: str = "MissionStarted"
MISSION_COMPLETED: str = "MissionCompleted"
MISSION_CANCELLED: str = "MissionCancelled"
PHASE_ENTERED: str = "PhaseEntered"
REVIEW_ROLLBACK: str = "ReviewRollback"

MISSION_EVENT_TYPES: FrozenSet[str] = frozenset({
    MISSION_STARTED,
    MISSION_COMPLETED,
    MISSION_CANCELLED,
    PHASE_ENTERED,
    REVIEW_ROLLBACK,
})

# ── Section 2: MissionStatus Enum ────────────────────────────────────────────


class MissionStatus(str, Enum):
    """Mission lifecycle states."""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


TERMINAL_MISSION_STATUSES: FrozenSet[MissionStatus] = frozenset({
    MissionStatus.COMPLETED,
    MissionStatus.CANCELLED,
})

# ── Section 3: Lifecycle Payload Models ──────────────────────────────────────


class MissionStartedPayload(BaseModel):
    """Typed payload for MissionStarted events."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., min_length=1, description="Mission identifier"
    )
    mission_type: str = Field(
        ...,
        min_length=1,
        description="Mission type (e.g., 'software-dev', 'research', 'plan')",
    )
    initial_phase: str = Field(
        ..., min_length=1, description="First phase of the mission"
    )
    actor: str = Field(
        ..., min_length=1, description="Actor who started the mission"
    )


class MissionCompletedPayload(BaseModel):
    """Typed payload for MissionCompleted events."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., min_length=1, description="Mission identifier"
    )
    mission_type: str = Field(
        ..., min_length=1, description="Mission type"
    )
    final_phase: str = Field(
        ..., min_length=1, description="Last phase before completion"
    )
    actor: str = Field(
        ..., min_length=1, description="Actor who completed the mission"
    )


class MissionCancelledPayload(BaseModel):
    """Typed payload for MissionCancelled events."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., min_length=1, description="Mission identifier"
    )
    reason: str = Field(
        ..., min_length=1, description="Reason for cancellation (required)"
    )
    actor: str = Field(
        ..., min_length=1, description="Actor who cancelled the mission"
    )
    cancelled_wp_ids: List[str] = Field(
        default_factory=list,
        description="WP IDs affected by cancellation",
    )


class PhaseEnteredPayload(BaseModel):
    """Typed payload for PhaseEntered events."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., min_length=1, description="Mission identifier"
    )
    phase_name: str = Field(
        ..., min_length=1, description="Phase being entered"
    )
    previous_phase: Optional[str] = Field(
        None, min_length=1, description="Phase being exited (None for initial)"
    )
    actor: str = Field(
        ..., min_length=1, description="Actor triggering phase transition"
    )


class ReviewRollbackPayload(BaseModel):
    """Typed payload for ReviewRollback events."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., min_length=1, description="Mission identifier"
    )
    review_ref: str = Field(
        ...,
        min_length=1,
        description="Reference to the review that triggered rollback",
    )
    target_phase: str = Field(
        ..., min_length=1, description="Phase to roll back to"
    )
    affected_wp_ids: List[str] = Field(
        default_factory=list,
        description="WP IDs affected by rollback",
    )
    actor: str = Field(
        ..., min_length=1, description="Actor triggering rollback"
    )
