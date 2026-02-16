"""Glossary semantic integrity event contracts for Feature 007.

Defines event type constants, value objects, payload models,
reducer output models, and the glossary reducer for
mission-level semantic integrity enforcement.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_events.models import SpecKittyEventsError

# ── Section 1: Constants ─────────────────────────────────────────────────────

GLOSSARY_SCOPE_ACTIVATED: str = "GlossaryScopeActivated"
TERM_CANDIDATE_OBSERVED: str = "TermCandidateObserved"
SEMANTIC_CHECK_EVALUATED: str = "SemanticCheckEvaluated"
GLOSSARY_CLARIFICATION_REQUESTED: str = "GlossaryClarificationRequested"
GLOSSARY_CLARIFICATION_RESOLVED: str = "GlossaryClarificationResolved"
GLOSSARY_SENSE_UPDATED: str = "GlossarySenseUpdated"
GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT: str = "GenerationBlockedBySemanticConflict"
GLOSSARY_STRICTNESS_SET: str = "GlossaryStrictnessSet"

GLOSSARY_EVENT_TYPES: FrozenSet[str] = frozenset({
    GLOSSARY_SCOPE_ACTIVATED,
    TERM_CANDIDATE_OBSERVED,
    SEMANTIC_CHECK_EVALUATED,
    GLOSSARY_CLARIFICATION_REQUESTED,
    GLOSSARY_CLARIFICATION_RESOLVED,
    GLOSSARY_SENSE_UPDATED,
    GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT,
    GLOSSARY_STRICTNESS_SET,
})

# ── Section 2: Value Objects ─────────────────────────────────────────────────


class SemanticConflictEntry(BaseModel):
    """Single conflict finding within a semantic check evaluation."""

    model_config = ConfigDict(frozen=True)

    term: str = Field(..., min_length=1, description="The conflicting term surface text")
    nature: Literal["overloaded", "drift", "ambiguous"] = Field(
        ..., description="Classification of the conflict"
    )
    severity: Literal["low", "medium", "high"] = Field(
        ..., description="Severity level of this conflict"
    )
    description: str = Field(..., description="Human-readable explanation of the conflict")


# ── Section 3: Payload Models ────────────────────────────────────────────────


class GlossaryScopeActivatedPayload(BaseModel):
    """Payload for GlossaryScopeActivated event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    scope_id: str = Field(..., min_length=1, description="Unique scope identifier")
    scope_type: Literal[
        "spec_kitty_core", "team_domain", "audience_domain", "mission_local"
    ] = Field(..., description="Scope category")
    glossary_version_id: str = Field(
        ..., min_length=1, description="Version of the glossary being activated"
    )


class TermCandidateObservedPayload(BaseModel):
    """Payload for TermCandidateObserved event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    scope_id: str = Field(..., min_length=1, description="Scope the term was observed in")
    step_id: str = Field(..., min_length=1, description="Mission step that produced the term")
    term_surface: str = Field(
        ..., min_length=1, description="Raw text form of the observed term"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0–1.0)"
    )
    actor: str = Field(..., min_length=1, description="Identity of the observing actor")
    step_metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Mission primitive metadata for the step (no hardcoded step names)",
    )


class GlossarySenseUpdatedPayload(BaseModel):
    """Payload for GlossarySenseUpdated event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    scope_id: str = Field(..., min_length=1, description="Scope of the term")
    term_surface: str = Field(..., min_length=1, description="Term being updated")
    before_sense: Optional[str] = Field(
        None, description="Previous sense value (None if first definition)"
    )
    after_sense: str = Field(..., min_length=1, description="New sense value")
    reason: str = Field(..., description="Why the sense was changed")
    actor: str = Field(..., min_length=1, description="Actor who made the change")


class GlossaryStrictnessSetPayload(BaseModel):
    """Payload for GlossaryStrictnessSet event (mission-wide policy change)."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    new_strictness: Literal["off", "medium", "max"] = Field(
        ..., description="The new strictness mode"
    )
    previous_strictness: Optional[Literal["off", "medium", "max"]] = Field(
        None, description="Previous mode (None if initial setting)"
    )
    actor: str = Field(..., min_length=1, description="Actor who changed the setting")


class SemanticCheckEvaluatedPayload(BaseModel):
    """Payload for SemanticCheckEvaluated event (step-level semantic check)."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    scope_id: str = Field(..., min_length=1, description="Scope checked against")
    step_id: str = Field(..., min_length=1, description="Step being evaluated")
    conflicts: Tuple[SemanticConflictEntry, ...] = Field(
        ..., description="List of detected conflicts"
    )
    severity: Literal["low", "medium", "high"] = Field(
        ..., description="Overall check severity (max of conflicts)"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall confidence score"
    )
    recommended_action: Literal["block", "warn", "pass"] = Field(
        ..., description="Action recommendation based on severity and strictness"
    )
    effective_strictness: Literal["off", "medium", "max"] = Field(
        ..., description="Strictness mode used for this evaluation"
    )
    step_metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Mission primitive metadata (no hardcoded step names)",
    )


class GlossaryClarificationRequestedPayload(BaseModel):
    """Payload for GlossaryClarificationRequested event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    scope_id: str = Field(..., min_length=1, description="Scope context")
    step_id: str = Field(..., min_length=1, description="Step that triggered clarification")
    semantic_check_event_id: str = Field(
        ...,
        min_length=1,
        description="Event ID of triggering SemanticCheckEvaluated (burst-window key)",
    )
    term: str = Field(..., min_length=1, description="The ambiguous term")
    question: str = Field(..., description="Clarification question text")
    options: Tuple[str, ...] = Field(..., description="Available answer options")
    urgency: Literal["low", "medium", "high"] = Field(
        ..., description="Urgency level"
    )
    actor: str = Field(..., min_length=1, description="Actor who triggered the request")


class GlossaryClarificationResolvedPayload(BaseModel):
    """Payload for GlossaryClarificationResolved event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    clarification_event_id: str = Field(
        ...,
        min_length=1,
        description="Event ID of the originating clarification request",
    )
    selected_meaning: str = Field(
        ..., min_length=1, description="The chosen or entered meaning"
    )
    actor: str = Field(..., min_length=1, description="Identity of the resolving actor")


class GenerationBlockedBySemanticConflictPayload(BaseModel):
    """Payload for GenerationBlockedBySemanticConflict event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    step_id: str = Field(..., min_length=1, description="Step that was blocked")
    conflict_event_ids: Tuple[str, ...] = Field(
        ...,
        min_length=1,
        description="Event IDs of unresolved SemanticCheckEvaluated events",
    )
    blocking_strictness: Literal["medium", "max"] = Field(
        ..., description="Policy mode that triggered the block (never 'off')"
    )
    step_metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Mission primitive metadata",
    )

# ── Section 4: Reducer Output Models ─────────────────────────────────────────

# ── Section 5: Glossary Reducer ──────────────────────────────────────────────
