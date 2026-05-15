"""Canonical project / mission / artifact / WP lifecycle event contracts.

This module defines the additional typed payload models needed by Spec Kitty
and TeamSpace to record the full canonical lifecycle:

* Project initialization (``ProjectInitialized``)
* Specify / plan / tasks artifact lifecycle (``SpecifyStarted`` /
  ``SpecifyCompleted`` / ``PlanStarted`` / ``PlanCompleted`` / ``TasksStarted`` /
  ``TasksCompleted``)
* Work-package creation (``WPCreated``)

The existing :mod:`spec_kitty_events.lifecycle` module already covers
mission-level lifecycle (``MissionCreated``, ``MissionStarted``, ...). This
module fills the gap below the mission level (project boot) and the gap
between *mission creation* and *first WP status* (per-artifact lifecycle and
WP creation).

Ordering, idempotency, and replay
---------------------------------

* Every event in this module carries either ``mission_slug`` (the canonical
  mission handle) or ``project_uuid`` (the canonical project handle). Consumers
  group and order events by those handles plus the standard envelope
  ``lamport_clock`` and ``event_id`` keys (see :mod:`spec_kitty_events.status`).
* Each contract is *idempotent on replay*: re-applying the same event by
  ``event_id`` is a no-op for consumers that keep an ``event_id`` ledger. The
  payloads are intentionally minimal and additive; they never carry derived
  state that conflicts with later events.
* Consumers are expected to materialize state as follows:

  1. ``ProjectInitialized`` opens the project aggregate. It MUST precede every
     other event in this module for the same ``project_uuid``.
  2. ``MissionCreated`` (from :mod:`spec_kitty_events.lifecycle`) opens the
     mission aggregate. SpecifyStarted/PlanStarted/TasksStarted events for
     that mission MUST follow ``MissionCreated``.
  3. For each artifact phase the canonical order is
     ``<Phase>Started`` then ``<Phase>Completed``. Re-running a phase emits a
     fresh ``<Phase>Started`` with a higher ``lamport_clock``; replay is
     order-preserving so the latest ``<Phase>Completed`` wins.
  4. ``WPCreated`` events MUST precede the first ``WPStatusChanged`` event for
     the same ``wp_id``. Consumers that see a ``WPStatusChanged`` for an
     unknown WP synthesize a *reconciliation diagnostic*, never silently
     create the WP from status alone.

* Bootstrap forced ``WPStatusChanged`` events with ``to_lane == planned`` and
  ``from_lane in {None, planned}`` are *initialize-only* by the status reducer
  (see :func:`spec_kitty_events.status.is_bootstrap_planned_event`). They never
  regress WP state on replay.

This is the consumer contract that TeamSpace import and the Spec Kitty local
dashboard both materialize from.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import FrozenSet, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# Event type string constants

PROJECT_INITIALIZED: str = "ProjectInitialized"

SPECIFY_STARTED: str = "SpecifyStarted"
SPECIFY_COMPLETED: str = "SpecifyCompleted"

PLAN_STARTED: str = "PlanStarted"
PLAN_COMPLETED: str = "PlanCompleted"

TASKS_STARTED: str = "TasksStarted"
TASKS_COMPLETED: str = "TasksCompleted"

WP_CREATED: str = "WPCreated"


PROJECT_LIFECYCLE_EVENT_TYPES: FrozenSet[str] = frozenset({
    PROJECT_INITIALIZED,
})

ARTIFACT_LIFECYCLE_EVENT_TYPES: FrozenSet[str] = frozenset({
    SPECIFY_STARTED,
    SPECIFY_COMPLETED,
    PLAN_STARTED,
    PLAN_COMPLETED,
    TASKS_STARTED,
    TASKS_COMPLETED,
})

WP_LIFECYCLE_EVENT_TYPES: FrozenSet[str] = frozenset({
    WP_CREATED,
})

CANONICAL_LIFECYCLE_EVENT_TYPES: FrozenSet[str] = (
    PROJECT_LIFECYCLE_EVENT_TYPES
    | ARTIFACT_LIFECYCLE_EVENT_TYPES
    | WP_LIFECYCLE_EVENT_TYPES
)


# Enums


class ArtifactPhase(str, Enum):
    """The three canonical planning-phase artifacts on a mission."""

    SPECIFY = "specify"
    PLAN = "plan"
    TASKS = "tasks"


# Payload models


class ProjectInitializedPayload(BaseModel):
    """Typed payload for ``ProjectInitialized`` events.

    Emitted exactly once when a project is first initialized via
    ``spec-kitty init`` (or equivalent). Establishes the project aggregate
    that subsequent mission/artifact/WP events join.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_uuid: str = Field(
        ...,
        min_length=1,
        description="Canonical machine identity for the project (UUID string).",
    )
    project_slug: Optional[str] = Field(
        None,
        min_length=1,
        description="Human-readable project slug, if any.",
    )
    actor: str = Field(
        ...,
        min_length=1,
        description="Actor that initialized the project (e.g. CLI user or agent).",
    )
    runtime_version: Optional[str] = Field(
        None,
        min_length=1,
        description="CLI / runtime version recorded at init time.",
    )
    initialized_at: Optional[datetime] = Field(
        None,
        description="Wall-clock timestamp when the project was initialized.",
    )


class _ArtifactPhasePayloadBase(BaseModel):
    """Shared fields for artifact-phase lifecycle payloads."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_slug: str = Field(
        ...,
        min_length=1,
        description="Canonical mission slug.",
    )
    mission_number: Optional[int] = Field(
        None,
        ge=1,
        description="Canonical mission number; ``None`` pre-merge.",
    )
    actor: str = Field(
        ...,
        min_length=1,
        description="Actor driving the phase transition.",
    )
    at: Optional[datetime] = Field(
        None,
        description="Wall-clock timestamp for the phase transition.",
    )


class SpecifyStartedPayload(_ArtifactPhasePayloadBase):
    """Specify phase started for a mission."""


class SpecifyCompletedPayload(_ArtifactPhasePayloadBase):
    """Specify phase completed for a mission."""

    artifact_path: str = Field(
        ...,
        min_length=1,
        description="Repo-relative path to the spec artifact (e.g. spec.md).",
    )
    summary: Optional[str] = Field(
        None,
        description="Optional one-line summary of the completed spec.",
    )


class PlanStartedPayload(_ArtifactPhasePayloadBase):
    """Plan phase started for a mission."""


class PlanCompletedPayload(_ArtifactPhasePayloadBase):
    """Plan phase completed for a mission."""

    artifact_path: str = Field(
        ...,
        min_length=1,
        description="Repo-relative path to the plan artifact (e.g. plan.md).",
    )
    summary: Optional[str] = Field(
        None,
        description="Optional one-line summary of the completed plan.",
    )


class TasksStartedPayload(_ArtifactPhasePayloadBase):
    """Tasks phase started for a mission."""


class TasksCompletedPayload(_ArtifactPhasePayloadBase):
    """Tasks phase completed for a mission.

    The terminal event for the planning trio. Consumers MAY treat the next
    ``WPCreated`` events for this mission as part of the same lamport window.
    """

    artifact_path: str = Field(
        ...,
        min_length=1,
        description="Repo-relative path to the tasks artifact (e.g. tasks.md).",
    )
    wp_count: int = Field(
        ...,
        ge=0,
        description="Number of work-packages produced by the tasks phase.",
    )
    summary: Optional[str] = Field(
        None,
        description="Optional one-line summary of the tasks manifest.",
    )


class WPCreatedPayload(BaseModel):
    """Typed payload for ``WPCreated`` events.

    Emitted once per work-package, immediately after the WP task file is
    materialized on disk. Establishes the WP aggregate so that subsequent
    ``WPStatusChanged`` events have a known parent. The first status event
    for a WP MUST follow ``WPCreated`` for the same ``mission_slug`` /
    ``wp_id`` pair.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_slug: str = Field(
        ...,
        min_length=1,
        description="Canonical mission slug owning this WP.",
    )
    mission_number: Optional[int] = Field(
        None,
        ge=1,
        description="Canonical mission number; ``None`` pre-merge.",
    )
    wp_id: str = Field(
        ...,
        min_length=1,
        description="Work-package identifier (e.g. ``WP01``).",
    )
    wp_title: str = Field(
        ...,
        min_length=1,
        description="Human-readable WP title.",
    )
    wp_path: Optional[str] = Field(
        None,
        min_length=1,
        description="Repo-relative path to the WP task file, if persisted on disk.",
    )
    depends_on: List[str] = Field(
        default_factory=list,
        description="IDs of work-packages this WP depends on.",
    )
    actor: str = Field(
        ...,
        min_length=1,
        description="Actor that created the WP.",
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Wall-clock timestamp of WP creation.",
    )


__all__ = [
    "PROJECT_INITIALIZED",
    "SPECIFY_STARTED",
    "SPECIFY_COMPLETED",
    "PLAN_STARTED",
    "PLAN_COMPLETED",
    "TASKS_STARTED",
    "TASKS_COMPLETED",
    "WP_CREATED",
    "PROJECT_LIFECYCLE_EVENT_TYPES",
    "ARTIFACT_LIFECYCLE_EVENT_TYPES",
    "WP_LIFECYCLE_EVENT_TYPES",
    "CANONICAL_LIFECYCLE_EVENT_TYPES",
    "ArtifactPhase",
    "ProjectInitializedPayload",
    "SpecifyStartedPayload",
    "SpecifyCompletedPayload",
    "PlanStartedPayload",
    "PlanCompletedPayload",
    "TasksStartedPayload",
    "TasksCompletedPayload",
    "WPCreatedPayload",
]
