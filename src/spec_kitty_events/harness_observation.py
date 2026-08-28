"""HarnessObservation: the volatile, agent-presence event family (F1-T1).

Normative ownership (draft §3.1, ARCHITECTURE.md §4 "each fact has exactly
one owner"): this module is the *single* owner of the harness-observation
vocabulary — the closed :class:`ObservationKind` set, the per-kind field
matrix, the six payload IDs, :data:`FORBIDDEN_OBSERVATION_KEYS`, and the
field grammars/bounds of :class:`HarnessObservationPayload`. Zeitgeist (F3)
owns only the *transport* envelope around this vocabulary (``op``,
``request_id``, relay-side receipt ``ts``, ``ttl_s``, ``epoch``/``seq``,
``LiveFrame``) and must map every ingress op/kind onto exactly one of the
six payload IDs defined here, never define a second closed vocabulary.

HarnessObservation is **volatile**: it is never reduced into mission/WP
state. ``reduce_lifecycle_events``/``reduce_status_events`` already drop
non-member event types, so a stream containing observations reduces to the
same state as the same stream without them (see the R1 replay negative in
the F1 contract-freeze draft §4, pinned by
``tests/integration/test_lifecycle_replay.py`` style goldens).

No time/TTL/user/team identity field exists on this payload by design
(decision 7 in the draft): receipt clock/TTL is server (Zeitgeist) policy;
identity is server-derived from the credential, never a caller-supplied
field ("caller fields never grant authority").
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType
from typing import Literal, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from spec_kitty_events.status import Lane

__all__ = [
    "HARNESS_OBSERVATION",
    "HARNESS_OBSERVATION_CONTRACT_VERSION",
    "ObservationKind",
    "PAYLOAD_ID_BY_KIND",
    "HARNESS_OBSERVATION_PAYLOAD_IDS",
    "FORBIDDEN_OBSERVATION_KEYS",
    "FORBIDDEN_OBSERVATION_KEYS_VERSION",
    "HarnessObservationPayload",
]


HARNESS_OBSERVATION: str = "HarnessObservation"
"""The single ``event_type`` string carrying every observation kind."""

HARNESS_OBSERVATION_CONTRACT_VERSION: str = "1"
"""Embedded in every payload ID (``harness.<kind>.v1``)."""


class ObservationKind(str, Enum):
    """Closed set of harness-observation kinds. Exactly six members.

    Structure over names: if PR #51's exact bytes name these differently,
    only the string values move — the six-kind structure and the per-kind
    field matrix below stay (F1 draft §6.1).
    """

    PRESENCE = "presence"
    LANE_SIGNAL = "lane_signal"
    FOCUS_STARTED = "focus_started"
    FOCUS_HEARTBEAT = "focus_heartbeat"
    FOCUS_PAUSED = "focus_paused"
    FOCUS_ENDED = "focus_ended"


PAYLOAD_ID_BY_KIND: Mapping[ObservationKind, str] = MappingProxyType(
    {
        kind: f"harness.{kind.value}.v{HARNESS_OBSERVATION_CONTRACT_VERSION}"
        for kind in ObservationKind
    }
)
"""Total mapping: every :class:`ObservationKind` to exactly one payload ID."""

HARNESS_OBSERVATION_PAYLOAD_IDS: frozenset[str] = frozenset(PAYLOAD_ID_BY_KIND.values())
"""The six payload ID strings the F1 criterion names ("six payload IDs")."""


FORBIDDEN_OBSERVATION_KEYS: frozenset[str] = frozenset(
    {
        "detail",
        "message",
        "text",
        "prose",
        "body",
        "command_text",
        "stdout",
        "stderr",
        "user",
        "user_id",
        "email",
        "actor",
        "team",
        "team_id",
        "team_slug",
        "deployment",
        "deployment_id",
        "token",
        "authorization",
        "bearer",
        "password",
        "secret",
        "url",
        "runtime_url",
        "branch",
    }
)
"""Closed, versioned set of keys that must never appear anywhere inside a
HarnessObservation envelope (defense in depth, checked by the recursive
walker in :mod:`spec_kitty_events.forbidden_keys`, same primitive as
:data:`spec_kitty_events.forbidden_keys.FORBIDDEN_LEGACY_KEYS`). Prose,
identity, and secrets never belong in a live presence signal."""

FORBIDDEN_OBSERVATION_KEYS_VERSION: str = "v1"
"""Bump on any membership change to :data:`FORBIDDEN_OBSERVATION_KEYS`."""


# Character-class and length bounds only — mirrors zeitgeist's
# editor._IDENT_RE / editor._REF_RE character classes (editor.py:146-147).
# These reject whitespace/control characters, not "prose shaped as a
# hyphenated identifier" — the segment-count *shape* rule
# (editor.py:170-192, _MAX_SEGMENTS, _ident -> "unknown-<digest>") remains
# zeitgeist's single render-side authority, applied at F3/Z3/Z8 ingest.
# F1 deliberately does not restate it (draft §3.3 grammar note, decision 14).
_IDENT = r"^[A-Za-z0-9][A-Za-z0-9._@+-]{0,63}$"
_REF = r"^[A-Za-z0-9][A-Za-z0-9._@+/-]{0,239}$"


# Per-kind field matrix (R = required, O = optional, F = must be absent).
# Transcribed from the F1 contract-freeze draft §3.3 table. Only the seven
# conditionally-varying fields are listed; `harness`/`session_id` are
# required for every kind (enforced directly by their Field(...) defaults)
# and `agent_id`/`repo` are optional for every kind (never constrained here).
_REQUIRED = "R"
_OPTIONAL = "O"
_FORBIDDEN = "F"

_KIND_FIELD_RULES: Mapping[ObservationKind, Mapping[str, str]] = MappingProxyType(
    {
        ObservationKind.PRESENCE: MappingProxyType(
            {
                "mission_slug": _OPTIONAL,
                "wp_id": _OPTIONAL,
                "lane": _FORBIDDEN,
                "activity": _REQUIRED,
                "path": _OPTIONAL,
                "pause_reason": _FORBIDDEN,
                "ended_reason": _FORBIDDEN,
            }
        ),
        ObservationKind.LANE_SIGNAL: MappingProxyType(
            {
                "mission_slug": _REQUIRED,
                "wp_id": _REQUIRED,
                "lane": _REQUIRED,
                "activity": _FORBIDDEN,
                "path": _FORBIDDEN,
                "pause_reason": _FORBIDDEN,
                "ended_reason": _FORBIDDEN,
            }
        ),
        ObservationKind.FOCUS_STARTED: MappingProxyType(
            {
                "mission_slug": _REQUIRED,
                "wp_id": _OPTIONAL,
                "lane": _FORBIDDEN,
                "activity": _FORBIDDEN,
                "path": _FORBIDDEN,
                "pause_reason": _FORBIDDEN,
                "ended_reason": _FORBIDDEN,
            }
        ),
        ObservationKind.FOCUS_HEARTBEAT: MappingProxyType(
            {
                "mission_slug": _REQUIRED,
                "wp_id": _OPTIONAL,
                "lane": _FORBIDDEN,
                "activity": _FORBIDDEN,
                "path": _FORBIDDEN,
                "pause_reason": _FORBIDDEN,
                "ended_reason": _FORBIDDEN,
            }
        ),
        ObservationKind.FOCUS_PAUSED: MappingProxyType(
            {
                "mission_slug": _REQUIRED,
                "wp_id": _OPTIONAL,
                "lane": _FORBIDDEN,
                "activity": _FORBIDDEN,
                "path": _FORBIDDEN,
                "pause_reason": _REQUIRED,
                "ended_reason": _FORBIDDEN,
            }
        ),
        ObservationKind.FOCUS_ENDED: MappingProxyType(
            {
                "mission_slug": _REQUIRED,
                "wp_id": _OPTIONAL,
                "lane": _FORBIDDEN,
                "activity": _FORBIDDEN,
                "path": _FORBIDDEN,
                "pause_reason": _FORBIDDEN,
                "ended_reason": _REQUIRED,
            }
        ),
    }
)


class HarnessObservationPayload(BaseModel):
    """Typed payload for the six HarnessObservation kinds.

    Envelope conventions (validated by ``spec_kitty_events.strict``,
    documented here per draft §3.3): ``event_type="HarnessObservation"``,
    ``aggregate_id="session/<session_id>"``, ``schema_version="3.0.0"``,
    ``timestamp`` = producer occurrence time (R-T-01); ``lamport_clock`` =
    the journal clock value at offer time for ``lane_signal`` and the
    client's local clock otherwise; ``correlation_id`` = the journal
    event's ``event_id`` for ``lane_signal``. No time field in the payload
    (R-T-02); no TTL/expiry field (server receipt clock/TTL is Z3/F3
    policy); no user/team identity (server-derived, Z2a/Z7).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ObservationKind
    harness: str = Field(
        ..., max_length=32, pattern=_IDENT, description="Harness identity, e.g. 'claude', 'codex'."
    )
    session_id: str = Field(..., max_length=128, pattern=_IDENT)
    agent_id: Optional[str] = Field(None, max_length=64, pattern=_IDENT)
    repo: Optional[str] = Field(
        None,
        max_length=120,
        pattern=_REF,
        description="Typed repo-identity slot; derivation is owned by Z6.",
    )
    mission_slug: Optional[str] = Field(None, min_length=1, max_length=120, pattern=_REF)
    wp_id: Optional[str] = Field(None, min_length=1, max_length=32, pattern=_IDENT)
    lane: Optional[Lane] = None
    activity: Optional[Literal["file_edit", "command"]] = None
    path: Optional[str] = Field(None, max_length=240, pattern=_REF)
    pause_reason: Optional[Literal["user", "dnd"]] = None
    ended_reason: Optional[Literal["user", "timeout"]] = None

    @model_validator(mode="after")
    def _per_kind(self) -> "HarnessObservationPayload":
        rules = _KIND_FIELD_RULES[self.kind]
        for field_name, rule in rules.items():
            value = getattr(self, field_name)
            if rule == _REQUIRED and value is None:
                raise ValueError(f"{field_name!r} is required for kind {self.kind.value!r}")
            if rule == _FORBIDDEN and value is not None:
                raise ValueError(f"{field_name!r} must be absent for kind {self.kind.value!r}")
        return self
