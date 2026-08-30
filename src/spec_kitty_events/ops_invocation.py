"""Ops/Invocation moment contracts (E2 post-MVP, planning#235, events#78).

Operations tooling (CLI-driven admin actions, service-to-service calls,
anything invoked outside a mission run) needs to share the same Team Kitty
timeline as mission/WP moments without borrowing a mission event kind for
something that is not a mission. This module defines that vocabulary as its
own small, closed family:

* ``OpsInvocationStarted`` — one invocation attempt opened.
* ``OpsInvocationCompleted`` — that attempt concluded, success or failure.

Both join :mod:`spec_kitty_events.zeitgeist_attrs`'s volatile vocabulary
(wiring lives there, not here — this module owns payload shape only, exactly
like :mod:`spec_kitty_events.project_lifecycle`). Per this issue's explicit
scope, no CLI emitter, no SaaS view, and no detail-read service ship here —
only the payload contract, its zeitgeist-attrs projection, and fixtures.

Correlation, idempotency, and retries
--------------------------------------
* ``invocation_id`` is the stable identity across one invocation's *entire*
  lifecycle: the ``Started`` moment that opens it, the ``Completed`` moment
  that closes it, and every retried attempt in between. Consumers group
  moments by ``invocation_id`` first.
* ``attempt`` is a 1-based counter distinguishing individual tries under the
  same ``invocation_id``. The first try is ``attempt=1``. A retry re-emits a
  fresh ``OpsInvocationStarted`` with the *same* ``invocation_id`` and
  ``attempt`` incremented by one — it never mints a new ``invocation_id``,
  and there is no separate ``OpsInvocationRetried`` kind: a retry is just
  another ``Started``/``Completed`` pair under the next attempt number. The
  pair ``(invocation_id, attempt)`` is therefore the unique key for one
  try's ``Started``/``Completed`` correlation, not ``invocation_id`` alone.
* Idempotency is at the envelope layer, standard for every family in this
  package: re-delivery of the same ``event_id`` is a no-op for a consumer
  that keeps an ``event_id`` ledger (see :mod:`spec_kitty_events.status`'s
  ``dedup_events``). Two distinct events sharing an
  ``(invocation_id, attempt)`` pair (e.g. two independently emitted
  ``Completed`` moments for the same attempt) is a producer-side anomaly
  this contract does not detect: no reducer or materialized state ships
  with this issue — that is deferred to the excluded CLI emitter / SaaS
  view / detail service, same as :mod:`spec_kitty_events.project_lifecycle`
  ships payload shape with a prose ordering contract and no reducer.
* A moment's ``detail_ref`` (see
  :data:`spec_kitty_events.zeitgeist_attrs.DETAIL_REF_SYNTAX`) always
  resolves to that *same* moment's own event — never to a sibling attempt or
  to the other half of a Started/Completed pair. A consumer wanting the
  other half still keys on ``(invocation_id, attempt)``, not ``detail_ref``.

Contract versioning
--------------------
``contract_version`` names the version of *this payload shape* (not the
envelope's fixed ``schema_version``; see
:mod:`spec_kitty_events.zeitgeist_attrs`'s ``CONTRACT_VERSIONED_EVENT_TYPES``
wiring). It exists because this contract is explicitly expected to evolve
post-MVP (the emitter and SaaS view this issue defers): a decoder that has
not yet learned a newer shape gets a named, typed rejection on an unknown
version instead of silently misinterpreting attrs from a future revision.
Encode and decode both check the same known-version table, so this package
cannot emit a frame that its own current decoder rejects. Today there is
exactly one known version, ``1``.
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Optional

from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_events.mission_next import RuntimeActorIdentity

# ── Constants ────────────────────────────────────────────────────────────────

OPS_INVOCATION_STARTED: str = "OpsInvocationStarted"
OPS_INVOCATION_COMPLETED: str = "OpsInvocationCompleted"

OPS_INVOCATION_EVENT_TYPES: FrozenSet[str] = frozenset(
    {
        OPS_INVOCATION_STARTED,
        OPS_INVOCATION_COMPLETED,
    }
)

#: The only ``contract_version`` this package currently knows how to decode.
OPS_INVOCATION_CONTRACT_VERSION: int = 1


# ── Enums ────────────────────────────────────────────────────────────────────


class OpsInvocationOutcome(str, Enum):
    """Terminal outcome of one Ops invocation attempt."""

    SUCCESS = "success"
    FAILURE = "failure"


# ── Payload models ──────────────────────────────────────────────────────────


class OpsInvocationStartedPayload(BaseModel):
    """Typed payload for ``OpsInvocationStarted`` events.

    Emitted when an operation is invoked. See the module docstring's
    "Correlation, idempotency, and retries" section for how ``invocation_id``
    and ``attempt`` combine across a retry chain.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    invocation_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Stable identity correlating this invocation's Started/Completed "
            "pair and every retried attempt. Never regenerated on retry."
        ),
    )
    action: str = Field(
        ...,
        min_length=1,
        description="Name of the operation invoked (producer-defined, e.g. 'team.provision').",
    )
    actor: RuntimeActorIdentity = Field(
        ...,
        description="Actor who triggered the invocation.",
    )
    scope: str = Field(
        ...,
        min_length=1,
        description="Bounded, opaque, producer-defined scope identifier the invocation acts on.",
    )
    attempt: int = Field(
        default=1,
        ge=1,
        description=(
            "1-based retry attempt number under invocation_id. A retry re-emits "
            "Started with the same invocation_id and attempt incremented by one."
        ),
    )
    contract_version: int = Field(
        default=OPS_INVOCATION_CONTRACT_VERSION,
        ge=1,
        description="Version of this payload shape (see module docstring's 'Contract versioning').",
    )
    request_summary: Optional[str] = Field(
        None,
        description=(
            "Optional bounded, human-readable gist of the request. Folded into "
            "the derived `summary` attr on broadcast, never carried raw."
        ),
    )

    @property
    def actor_label(self) -> str:
        return self.actor.actor_label


class OpsInvocationCompletedPayload(BaseModel):
    """Typed payload for ``OpsInvocationCompleted`` events.

    Concludes the attempt opened by an ``OpsInvocationStarted`` sharing the
    same ``invocation_id`` and ``attempt``. See the module docstring's
    "Correlation, idempotency, and retries" section.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    invocation_id: str = Field(
        ...,
        min_length=1,
        description="Same identity as the Started moment this Completed concludes.",
    )
    action: str = Field(
        ...,
        min_length=1,
        description="Name of the operation invoked; matches the Started moment's action.",
    )
    actor: RuntimeActorIdentity = Field(
        ...,
        description="Actor context for the completion.",
    )
    scope: str = Field(
        ...,
        min_length=1,
        description="Same scope as the Started moment.",
    )
    outcome: OpsInvocationOutcome = Field(
        ...,
        description="Terminal outcome of this attempt: success or failure.",
    )
    attempt: int = Field(
        default=1,
        ge=1,
        description="Attempt number this Completed concludes; matches the Started moment's attempt.",
    )
    contract_version: int = Field(
        default=OPS_INVOCATION_CONTRACT_VERSION,
        ge=1,
        description="Version of this payload shape (see module docstring's 'Contract versioning').",
    )
    result_summary: Optional[str] = Field(
        None,
        description=(
            "Optional bounded, human-readable gist of the result. Folded into "
            "the derived `summary` attr on broadcast, never carried raw."
        ),
    )

    @property
    def actor_label(self) -> str:
        return self.actor.actor_label


__all__ = [
    "OPS_INVOCATION_STARTED",
    "OPS_INVOCATION_COMPLETED",
    "OPS_INVOCATION_EVENT_TYPES",
    "OPS_INVOCATION_CONTRACT_VERSION",
    "OpsInvocationOutcome",
    "OpsInvocationStartedPayload",
    "OpsInvocationCompletedPayload",
]
