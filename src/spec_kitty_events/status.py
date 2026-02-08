"""Status state model contracts for work-package lane transitions."""

from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from spec_kitty_events.models import SpecKittyEventsError, ValidationError


class Lane(str, Enum):
    """Work-package lifecycle lanes."""

    PLANNED = "planned"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    FOR_REVIEW = "for_review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELED = "canceled"


class ExecutionMode(str, Enum):
    """How a work-package is being executed."""

    WORKTREE = "worktree"
    DIRECT_REPO = "direct_repo"


TERMINAL_LANES: FrozenSet[Lane] = frozenset({Lane.DONE, Lane.CANCELED})

LANE_ALIASES: Dict[str, Lane] = {"doing": Lane.IN_PROGRESS}

WP_STATUS_CHANGED: str = "WPStatusChanged"


def normalize_lane(value: str) -> Lane:
    """Resolve a string to a Lane, handling aliases.

    Args:
        value: A lane value string, either a canonical Lane member value
            or a known alias.

    Returns:
        The corresponding Lane enum member.

    Raises:
        ValidationError: If value is not a valid lane or alias.
    """
    # Check if value is already a Lane member value
    for member in Lane:
        if member.value == value:
            return member

    # Check aliases
    if value in LANE_ALIASES:
        return LANE_ALIASES[value]

    raise ValidationError(
        f"Unknown lane value: {value!r}. "
        f"Valid values: {[m.value for m in Lane]}. "
        f"Aliases: {list(LANE_ALIASES.keys())}"
    )


# ---------------------------------------------------------------------------
# Evidence models
# ---------------------------------------------------------------------------


class RepoEvidence(BaseModel):
    """Evidence of repository changes for a completed work-package."""

    model_config = ConfigDict(frozen=True)

    repo: str = Field(..., min_length=1, description="Repository identifier")
    branch: str = Field(..., min_length=1, description="Branch name")
    commit: str = Field(..., min_length=1, description="Commit SHA or reference")
    files_touched: Optional[List[str]] = Field(
        None, description="List of files modified"
    )


class VerificationEntry(BaseModel):
    """A single verification step (e.g. test run, lint check)."""

    model_config = ConfigDict(frozen=True)

    command: str = Field(..., min_length=1, description="Command that was executed")
    result: str = Field(..., min_length=1, description="Outcome of the command")
    summary: Optional[str] = Field(None, description="Human-readable summary")


class ReviewVerdict(BaseModel):
    """Verdict from a human or automated reviewer."""

    model_config = ConfigDict(frozen=True)

    reviewer: str = Field(..., min_length=1, description="Who reviewed")
    verdict: str = Field(..., min_length=1, description="Verdict string")
    reference: Optional[str] = Field(
        None, description="URL or reference for the review"
    )


class DoneEvidence(BaseModel):
    """Evidence bundle required when a WP transitions to DONE."""

    model_config = ConfigDict(frozen=True)

    repos: List[RepoEvidence] = Field(
        ..., min_length=1, description="At least one repo with changes"
    )
    verification: List[VerificationEntry] = Field(
        default_factory=list, description="Verification steps executed"
    )
    review: ReviewVerdict = Field(..., description="Review verdict")


# ---------------------------------------------------------------------------
# Transition models
# ---------------------------------------------------------------------------


class ForceMetadata(BaseModel):
    """Metadata attached when a transition is forced."""

    model_config = ConfigDict(frozen=True)

    force: bool = Field(True, description="Always True for forced transitions")
    actor: str = Field(..., min_length=1, description="Who forced the transition")
    reason: str = Field(..., min_length=1, description="Why the transition was forced")


class StatusTransitionPayload(BaseModel):
    """Payload for a WPStatusChanged event describing a lane transition."""

    model_config = ConfigDict(frozen=True)

    feature_slug: str = Field(..., min_length=1, description="Feature identifier")
    wp_id: str = Field(..., min_length=1, description="Work-package identifier")
    from_lane: Optional[Lane] = Field(
        None, description="Lane the WP is transitioning from (None for initial)"
    )
    to_lane: Lane = Field(..., description="Lane the WP is transitioning to")
    actor: str = Field(..., min_length=1, description="Who initiated the transition")
    force: bool = Field(False, description="Whether this is a forced transition")
    reason: Optional[str] = Field(
        None, description="Reason for the transition (required when force=True)"
    )
    execution_mode: ExecutionMode = Field(
        ..., description="How the work-package is being executed"
    )
    review_ref: Optional[str] = Field(
        None, description="Reference to an external review"
    )
    evidence: Optional[DoneEvidence] = Field(
        None, description="Evidence bundle (required when to_lane=DONE)"
    )

    @field_validator("from_lane", "to_lane", mode="before")
    @classmethod
    def _normalize_lane_aliases(cls, v: Optional[str]) -> Optional[str]:
        """Resolve lane aliases before Pydantic coerces to Lane enum."""
        if v is None:
            return v
        if isinstance(v, str) and v in LANE_ALIASES:
            return LANE_ALIASES[v].value
        return v

    @model_validator(mode="after")
    def _check_business_rules(self) -> "StatusTransitionPayload":
        """Enforce business rules on the transition payload."""
        if self.force and (self.reason is None or self.reason.strip() == ""):
            raise ValueError(
                "force=True requires a non-empty reason"
            )
        if self.to_lane == Lane.DONE and self.evidence is None:
            raise ValueError(
                "to_lane='done' requires evidence"
            )
        return self


class TransitionError(SpecKittyEventsError):
    """Raised when a status transition violates business rules."""

    def __init__(self, violations: Tuple[str, ...]) -> None:
        self.violations = violations
        super().__init__(f"Invalid transition: {'; '.join(violations)}")
