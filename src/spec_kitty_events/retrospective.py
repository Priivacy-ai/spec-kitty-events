"""Retrospective event contracts.

Defines event type constants, payload models, and domain schema version
for the retrospective contract surface.

The original 4.0.0 public surface exposed two UpperCamelCase terminal
signals. The 4.1.0 surface keeps those symbols for compatibility and adds
the dot-name lifecycle/proposal events emitted by the Spec Kitty runtime.
"""

from __future__ import annotations

import re
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

RETROSPECTIVE_EVENT_NAMES: FrozenSet[str] = frozenset(
    {
        RETROSPECTIVE_REQUESTED_EVENT,
        RETROSPECTIVE_STARTED_EVENT,
        RETROSPECTIVE_COMPLETED_EVENT,
        RETROSPECTIVE_SKIPPED_EVENT,
        RETROSPECTIVE_FAILED_EVENT,
        RETROSPECTIVE_PROPOSAL_GENERATED_EVENT,
        RETROSPECTIVE_PROPOSAL_APPLIED_EVENT,
        RETROSPECTIVE_PROPOSAL_REJECTED_EVENT,
    }
)

RETROSPECTIVE_EVENT_TYPES: FrozenSet[str] = (
    frozenset(
        {
            RETROSPECTIVE_COMPLETED,
            RETROSPECTIVE_SKIPPED,
        }
    )
    | RETROSPECTIVE_EVENT_NAMES
)

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


#: Matches an ISO-8601/RFC-3339 timestamp in either extended
#: (``2026-08-25T09:00:00.123456+00:00``) or basic (``20260825T090000Z``)
#: format, with an optional fractional-second part of *any* digit count and
#: an optional numeric offset. Used only to reshape a match into the one
#: extended-with-6-digit-fraction spelling ``fromisoformat`` accepts
#: identically on every supported interpreter (see
#: ``_normalize_iso8601_shape``); a non-match is passed through unchanged so
#: a genuinely malformed string still reaches ``fromisoformat``'s own error.
#: The trailing-``Z`` designator is handled separately, unconditionally,
#: before this regex ever runs — see ``_normalize_iso8601_shape`` — so this
#: pattern's offset alternative only needs to cover a *numeric* offset.
_ISO8601_SHAPE_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}|\d{8})"
    r"[T ]"
    r"(?P<time>\d{2}:\d{2}:\d{2}|\d{2}:\d{2}|\d{6}|\d{4}|\d{2})"
    r"(?P<frac>[.,]\d+)?"
    r"(?P<offset>[+-]\d{2}:?\d{2})?$"
)


def _normalize_iso8601_shape(value: str) -> str:
    """Reshape *value* so ``datetime.fromisoformat`` parses it identically
    on Python 3.10 and 3.11+.

    3.10's ``fromisoformat`` has three gaps 3.11+ closed: it does not
    recognize the ``Z`` UTC designator at all, it only accepts a
    fractional-second part of exactly 0, 3, or 6 digits (rejecting, e.g.,
    Go's ``time.RFC3339Nano`` 9-digit output), and it only accepts the
    ``-``/``:``-separated "extended" format (rejecting basic format like
    ``20260825T090000Z``). All three gaps let the same wire bytes decode on
    one interpreter and raise on the other (spec-kitty-events#122, #135).

    The ``Z`` gap is closed first, unconditionally, exactly as it was
    before the fractional/basic-format reshape below existed: a trailing
    ``Z`` is stripped and replaced with ``+00:00`` so it parses the same way
    on every interpreter. A well-formed value has at most this one trailing
    ``Z``; if another ``z``/``Z`` remains after stripping it, the input was
    already malformed and must not be laundered into something 3.11+'s
    single-stray-character leniency around a trailing ``Z`` would otherwise
    accept (e.g. a doubled ``"...00ZZ"`` or mixed-case ``"...00zZ"``) while
    3.10 rejects it outright — so that case raises instead of being
    reshaped. Doing this *before and independently of* the regex below
    means a shape the regex does not match (a different separator, reduced
    precision, ...) is never worse off than it was before the regex-based
    reshape existed — e.g. a lowercase ``t`` date/time separator or a space
    before the ``Z`` both parse identically on 3.10 and 3.11+ once the ``Z``
    has already been rewritten, exactly as on this repo's pre-#122/#135
    ``main``.

    The regex then truncates/pads any fractional part to 6 digits — the
    precision ``datetime`` itself stores — inserts the extended-format
    separators when given basic format, pads a reduced-precision time (bare
    hour, or hour:minute with no seconds, in either format) out to
    hour:minute:second, and inserts a colon into a colon-less numeric
    offset. A value that does not match the expected timestamp shape at all
    (already malformed, or a format this repo does not need to handle) is
    returned unchanged, so it still fails ``fromisoformat`` with its
    ordinary ``ValueError``.
    """
    if value.endswith("Z"):
        candidate = value[:-1]
        if "z" in candidate.lower():
            raise ValueError(f"doubled UTC designator in timestamp: {value!r}")
        value = f"{candidate}+00:00"
    match = _ISO8601_SHAPE_RE.match(value)
    if match is None:
        return value
    date, time, frac, offset = match.group("date", "time", "frac", "offset")
    if len(date) == 8:
        date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
    if ":" in time:
        if time.count(":") == 1:
            time = f"{time}:00"
    elif len(time) == 2:
        time = f"{time}:00:00"
    elif len(time) == 4:
        time = f"{time[0:2]}:{time[2:4]}:00"
    else:
        time = f"{time[0:2]}:{time[2:4]}:{time[4:6]}"
    fraction = f".{frac[1:][:6].ljust(6, '0')}" if frac else ""
    if offset is None:
        offset = ""
    elif ":" not in offset:
        offset = f"{offset[:3]}:{offset[3:]}"
    return f"{date}T{time}{fraction}{offset}"


def _assert_iso8601_timestamp(value: object) -> object:
    """Validate an ISO 8601 timestamp across supported Python runtimes.

    Python 3.10's ``datetime.fromisoformat`` rejects a trailing ``Z``, a
    fractional-second part outside 0/3/6 digits, and basic (no ``-``/``:``)
    format, all accepted on 3.11+ for the same wire bytes. Normalize before
    parsing so the same input is accepted identically on every supported
    interpreter (spec-kitty-events#122, #135).
    """

    if isinstance(value, str):
        datetime.fromisoformat(_normalize_iso8601_shape(value))
    return value


class RetrospectiveCompletedPayload(BaseModel):
    """Payload for RetrospectiveCompleted events.

    Emitted when a retrospective step runs and produces a durable outcome.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1, description="Mission identifier")
    actor: str = Field(..., min_length=1, description="Actor who triggered the retrospective")
    trigger_source: TriggerSourceT = Field(..., description="What initiated the retrospective")
    artifact_ref: Optional[ProvenanceRef] = Field(
        None, description="Reference to retro artifact if one was produced"
    )
    completed_at: str = Field(..., min_length=1, description="ISO 8601 completion timestamp")

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
    skip_reason: str = Field(..., min_length=1, description="Why the retrospective was skipped")
    skipped_at: str = Field(..., min_length=1, description="ISO 8601 skip decision timestamp")

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
