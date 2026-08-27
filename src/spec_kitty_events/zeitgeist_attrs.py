"""Zeitgeist attrs codecs for the volatile mission/WP event families (E2).

The Ephemeral Team Status design broadcasts mission/WP moments through each
team's Zeitgeist relay as *opaque bounded attributes*: one ``event`` frame is
``{kind, ref?, attrs}`` where ``attrs`` must be a flat ``str:str`` mapping
with at most 16 keys, at most 64 characters per key, and at most 240
characters per value, and no forbidden key anywhere (zeitgeist issue:
``EventArgs {kind: ident, ref?: string≤240, attrs: {str:str}, ≤16 keys,
keys≤64 chars, values≤240 chars}``; design page
``ephemeral-team-status.html``, "The vocabulary" paragraph).

The relay's ``EventArgs`` schema bounds ``attrs`` keys at ≤64 *characters*
(``propertyNames.maxLength``, ASCII-only pattern so chars==bytes there) and
bounds values (and the frame's ``ref``) at ≤240 characters *and*
independently at ≤240 UTF-8 bytes (``maxLength: 240`` **and**
``maxUtf8Bytes: 240`` both present on ``attrs``'s ``additionalProperties``
and on ``ref``, in ``managed_control.schema.json`` and
``managed_live.schema.json`` since zeitgeist commit ``30d3ab4415``,
"Enforce event field byte limits", closing zeitgeist#20). The relay checks
both clauses independently (``capabilities.py``'s validator), so the
UTF-8-byte bound is the one that actually binds — a character count can
satisfy ≤240 chars while still exceeding 240 bytes, and the relay rejects
that. :func:`to_zeitgeist_attrs` enforces the 240-UTF-8-byte bound on
values and the 64-character bound on keys, both exactly matching the
relay's, since encode is where an over-length attr must be caught before
it ever reaches the wire. :func:`from_zeitgeist_attrs` checks the same
240-UTF-8-byte bound on values (not a character count — a value within
240 characters can still be relay-invalid at >240 bytes) and the
64-character bound on keys, so it does not accept an inbound frame the
relay itself would never forward (spec-kitty-events#16).

This module is the single owner of the mapping between this package's
volatile payload vocabulary and that wire shape:

* :func:`to_zeitgeist_attrs` — project one volatile payload *and its
  envelope* onto bounded attrs.
* :func:`from_zeitgeist_attrs` — validate inbound attrs against the same
  closed per-kind key vocabulary and return them as a
  :class:`VolatileMoment` (kind + ref + attrs), the typed view a consumer
  renders from.

Projection, not reconstruction
------------------------------
Attrs carry the *moment*: identity and transition facts. A relayed moment
deliberately does NOT rebuild the journal payload — two classes of field are
declared in :data:`UNBROADCAST_FIELDS` and stay local:

* fields whose shape cannot fit flat bounded strings —
  ``StatusTransitionPayload.evidence`` (structured evidence lists; this also
  keeps decode honest: ``to_lane ∈ {approved, done}`` payloads *require*
  evidence, so no decoder could rebuild them from attrs without fabricating
  audit data) and ``DecisionInputRequestedPayload.options`` (display hints
  of unbounded length);
* free-text prose — ``friendly_name`` / ``purpose_tldr`` /
  ``purpose_context``, a decision's ``question`` and ``answer``, and a
  forced transition's ``reason``. A moment is identifiers and transition
  facts; it renders from slugs, ids, lanes, and the actor label. Prose is
  stakeholder-facing text that would otherwise live on the team relay for
  the whole retention window.

Everything else the family declares rides in attrs; any carried value over
the bound raises rather than truncates: an oversize payload simply does not
broadcast (the CLI fan-out seam is fire-and-forget; a dropped moment is
lost *by design*, exactly like a downed relay or an expired budget).

Envelope identity rides too
---------------------------
The relay stamps receipt time and no id of its own onto what it forwards,
so :func:`to_zeitgeist_attrs` takes the event envelope as its second
parameter and carries ``event_id`` and ``occurred_at`` as explicit attrs.
Team Kitty deduplicates moments on ``(team, event_id)`` and renders their
declared occurrence time — neither is recoverable from receipt metadata.

Actor narrowing
---------------
Every family projects its ``actor`` to a single label string under the key
``actor``: :class:`~spec_kitty_events.status.StatusTransitionPayload` via
its ``actor_label`` property, and the mission-run family via
:class:`~spec_kitty_events.mission_next.RuntimeActorIdentity.actor_label` —
exactly the opaque ``actor_id``, never ``display_name`` or any other
free-text field. The mission-level payloads
(``MissionCreated`` / ``MissionClosed``) carry that label directly as their
optional plain-string ``actor`` field, so it rides under the same key with
no projection at all. A structured actor never rides field-for-field: the
relay has no actor member (it attests identity itself from the credential),
so broadcasting producer-asserted ids, providers, or model names would
re-introduce under dotted keys exactly what zeitgeist forbids flatly, while
duplicating the server-attested value.

Forbidden keys
--------------
:data:`FORBIDDEN_ATTR_KEYS` unions the legacy keys this package already
rejects (:data:`~spec_kitty_events.forbidden_keys.FORBIDDEN_LEGACY_KEYS`)
with a mirror of zeitgeist's direction-agnostic ingress set
(``capabilities.FORBIDDEN_KEYS_V1``, mirrored here by value with a version
suffix — zeitgeist owns transport policy, this package owns vocabulary, and
neither imports the other; same idiom as the harness-observation bounds
that mirror zeitgeist ``FIELD_MAX``). :func:`to_zeitgeist_attrs` refuses to
emit any of them. Keys are checked as flat strings; dotted keys would be
distinct strings from their segments, though today's vocabulary emits none.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel

from spec_kitty_events.forbidden_keys import FORBIDDEN_LEGACY_KEYS
from spec_kitty_events.lifecycle import (
    MISSION_CLOSED,
    MISSION_CREATED,
    PHASE_ENTERED,
    MissionClosedPayload,
    MissionCreatedPayload,
    PhaseEnteredPayload,
)
from spec_kitty_events.mission_next import (
    DECISION_INPUT_ANSWERED,
    DECISION_INPUT_REQUESTED,
    MISSION_RUN_COMPLETED,
    MISSION_RUN_STARTED,
    NEXT_STEP_AUTO_COMPLETED,
    NEXT_STEP_ISSUED,
    DecisionInputAnsweredPayload,
    DecisionInputRequestedPayload,
    MissionRunCompletedPayload,
    MissionRunStartedPayload,
    NextStepAutoCompletedPayload,
    NextStepIssuedPayload,
)
from spec_kitty_events.models import Event
from spec_kitty_events.status import WP_STATUS_CHANGED, StatusTransitionPayload

__all__ = [
    "FORBIDDEN_ATTR_KEYS",
    "PAYLOAD_MODEL_BY_EVENT_TYPE",
    "PROJECTED_FIELD_BY_EVENT_TYPE",
    "REF_FIELD_BY_EVENT_TYPE",
    "UNBROADCAST_FIELDS",
    "VOLATILE_EVENT_TYPES",
    "ZEITGEIST_ATTRS_MAX_BYTES",
    "ZEITGEIST_ATTRS_MAX_KEYS",
    "ZEITGEIST_ATTR_KEY_MAX_CHARS",
    "ZEITGEIST_FORBIDDEN_KEYS_V1",
    "UnencodableFieldValueError",
    "UnknownVolatileEventTypeError",
    "VolatileMoment",
    "ZeitgeistAttrsControlCharacterError",
    "ZeitgeistAttrsError",
    "ZeitgeistAttrsForbiddenKeyError",
    "ZeitgeistAttrsOverflowError",
    "from_zeitgeist_attrs",
    "to_zeitgeist_attrs",
    "zeitgeist_ref_for",
]


ZEITGEIST_ATTRS_MAX_KEYS: int = 16
"""Maximum number of entries in one attrs mapping (zeitgeist EventArgs)."""

ZEITGEIST_ATTRS_MAX_BYTES: int = 240
"""Maximum size of one attr value: 240 UTF-8 bytes, checked on both encode
and decode. The relay's schema also carries an independent ≤240-character
bound (``maxLength``), but UTF-8 byte count is always ≥ character count, so
enforcing the byte bound here also guarantees the character bound — a
value can never pass this check while still exceeding the relay's
character bound (spec-kitty-events#16). The frame's ``ref`` carries the
same pair of bounds independently."""

ZEITGEIST_ATTR_KEY_MAX_CHARS: int = 64
"""Maximum character length of one attr key, enforced on both encode and
decode (zeitgeist EventArgs ``propertyNames.maxLength``; JSON Schema
``maxLength`` counts characters, not UTF-8 bytes — spec-kitty-events#16)."""

#: Mirror of zeitgeist ``capabilities.FORBIDDEN_KEYS_V1`` (by value; see the
#: module docstring for why this is a mirror, not an import).
ZEITGEIST_FORBIDDEN_KEYS_V1: frozenset[str] = frozenset(
    {
        "token", "authorization", "bearer", "password", "detail", "team",
        "team_id", "deployment", "deployment_id", "membership", "role",
        "user_id", "url", "runtime_url",
    }
)

#: Keys :func:`to_zeitgeist_attrs` will never emit.
FORBIDDEN_ATTR_KEYS: frozenset[str] = ZEITGEIST_FORBIDDEN_KEYS_V1 | FORBIDDEN_LEGACY_KEYS


@dataclasses.dataclass(frozen=True)
class VolatileMoment:
    """The typed view of one broadcast moment: a full ``event`` frame body.

    ``kind`` is the frame's event type, ``ref`` its aggregate identity
    (≤240 bytes), ``attrs`` the validated bounded projection. Consumers
    render from this; nobody re-parses raw attr strings outside this
    module's vocabulary.

    ``ref`` is ``None`` only when the family's ref field is itself
    ``Optional`` and was absent from the encode (today, only
    ``PhaseEntered``'s back-compat ``mission_slug``) — :func:`from_zeitgeist_attrs`
    requires the ref key whenever the family's payload guarantees it, so a
    family with a required ref field never decodes to ``ref=None``.
    """

    kind: str
    ref: str | None
    attrs: Mapping[str, str]


class ZeitgeistAttrsError(ValueError):
    """Base class for zeitgeist-attrs codec failures."""


class UnknownVolatileEventTypeError(ZeitgeistAttrsError):
    """The payload or event type is not part of the volatile vocabulary."""


class UnencodableFieldValueError(ZeitgeistAttrsError):
    """A field's value has no bounded flat-string encoding."""


class ZeitgeistAttrsOverflowError(ZeitgeistAttrsError):
    """The projected attrs would exceed the zeitgeist attrs bound."""


class ZeitgeistAttrsForbiddenKeyError(ZeitgeistAttrsError):
    """Encoding would emit a key in :data:`FORBIDDEN_ATTR_KEYS`."""


class ZeitgeistAttrsControlCharacterError(ZeitgeistAttrsError):
    """A value carries a C0 control character (or DEL)."""


#: The event families the Ephemeral Team Status design moves to ``volatile``
#: (design page "The vocabulary"; epic E2). Mirrored by the support matrix.
VOLATILE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        WP_STATUS_CHANGED,
        MISSION_CREATED,
        MISSION_CLOSED,
        PHASE_ENTERED,
        MISSION_RUN_STARTED,
        NEXT_STEP_ISSUED,
        NEXT_STEP_AUTO_COMPLETED,
        DECISION_INPUT_REQUESTED,
        DECISION_INPUT_ANSWERED,
        MISSION_RUN_COMPLETED,
    }
)

#: Closed dispatch table: event type -> payload model. ``NextStepPlanned`` is
#: deliberately absent — its payload contract is reserved, not defined
#: (``mission_next.py``), so there is nothing to encode yet.
PAYLOAD_MODEL_BY_EVENT_TYPE: Mapping[str, type[BaseModel]] = {
    WP_STATUS_CHANGED: StatusTransitionPayload,
    MISSION_CREATED: MissionCreatedPayload,
    MISSION_CLOSED: MissionClosedPayload,
    PHASE_ENTERED: PhaseEnteredPayload,
    MISSION_RUN_STARTED: MissionRunStartedPayload,
    NEXT_STEP_ISSUED: NextStepIssuedPayload,
    NEXT_STEP_AUTO_COMPLETED: NextStepAutoCompletedPayload,
    DECISION_INPUT_REQUESTED: DecisionInputRequestedPayload,
    DECISION_INPUT_ANSWERED: DecisionInputAnsweredPayload,
    MISSION_RUN_COMPLETED: MissionRunCompletedPayload,
}

#: Per-type fields that never ride the relay: structured shapes that cannot
#: fit flat bounded attrs, and free-text prose (see "Projection, not
#: reconstruction" above). Everything else MUST survive.
UNBROADCAST_FIELDS: Mapping[str, frozenset[str]] = {
    WP_STATUS_CHANGED: frozenset({"evidence", "reason"}),
    MISSION_CREATED: frozenset({"friendly_name", "purpose_tldr", "purpose_context"}),
    DECISION_INPUT_REQUESTED: frozenset({"options", "question"}),
    DECISION_INPUT_ANSWERED: frozenset({"answer"}),
}

#: Per-type field projections: attr key -> canonical attribute carried under
#: that key. Every family carries its structured actor as the single
#: ``actor_label`` string (see "Actor narrowing" above).
PROJECTED_FIELD_BY_EVENT_TYPE: Mapping[str, Mapping[str, str]] = {
    WP_STATUS_CHANGED: {"actor": "actor_label"},
    MISSION_RUN_STARTED: {"actor": "actor_label"},
    NEXT_STEP_ISSUED: {"actor": "actor_label"},
    NEXT_STEP_AUTO_COMPLETED: {"actor": "actor_label"},
    DECISION_INPUT_REQUESTED: {"actor": "actor_label"},
    DECISION_INPUT_ANSWERED: {"actor": "actor_label"},
    MISSION_RUN_COMPLETED: {"actor": "actor_label"},
}

#: Envelope-sourced attrs every kind carries alongside its payload fields:
#: the deduplication identity and the declared occurrence time (see
#: "Envelope identity rides too" above).
ENVELOPE_ATTR_KEYS: frozenset[str] = frozenset({"event_id", "occurred_at"})


# ── encode ───────────────────────────────────────────────────────────────────


def _encode_scalar(field: str, value: Any) -> str:
    """Encode one leaf value as its bounded string form."""
    if isinstance(value, bool):  # before int: bool subclasses int
        return "true" if value else "false"
    if isinstance(value, Enum):
        raw = value.value
        encoded = raw if isinstance(raw, str) else str(raw)
    elif isinstance(value, str):
        encoded = value
    elif isinstance(value, int):
        encoded = str(value)
    else:
        raise UnencodableFieldValueError(
            f"field {field!r} of type {type(value).__name__} has no "
            "bounded flat-string encoding"
        )
    return encoded


def _encode_fields(
    model: BaseModel,
    prefix: str = "",
    skip: frozenset[str] = frozenset(),
    projected: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Flatten one payload (or nested value object) into string entries.

    ``skip`` names top-level fields that never ride the relay; they are
    excluded *before* encoding so an unencodable shape there cannot fail the
    projection. ``projected`` maps a top-level field to the canonical
    attribute carried instead of it (see
    :data:`PROJECTED_FIELD_BY_EVENT_TYPE`). A projection target must be a
    scalar attribute — a nested model under it would still recurse and emit
    dotted keys, which no table entry does.
    """
    entries: dict[str, str] = {}
    for name in type(model).model_fields:
        if not prefix:
            if name in skip:
                continue
            source = (projected or {}).get(name, name)
        else:
            source = name
        value = getattr(model, source)
        if value is None:
            continue  # absent optional: no key, decode restores the default
        key = f"{prefix}{name}"
        if isinstance(value, BaseModel):
            if prefix:
                raise UnencodableFieldValueError(
                    f"field {key!r}: nesting deeper than one level is not encodable"
                )
            entries.update(_encode_fields(value, prefix=f"{key}."))
            continue
        entries[key] = _encode_scalar(key, value)
    return entries


def _reject_control_characters(subject: str, value: str) -> None:
    """Refuse a value carrying a C0 control character (``U+0000``-``U+001F``)
    or DEL (``U+007F``).

    This is the decode-seam hardening `EXPERIMENTAL-spec-kitty-events#25`_
    asks for: an inbound attrs mapping is opaque wire data from a relay a
    hostile teammate or hostile relay frame can shape, and free-text keys
    (the actor label, ``review_ref``, ...) carry it verbatim into
    :class:`VolatileMoment`. A bare newline could forge extra frame lines
    for whatever renders the moment next; a bare ESC could smuggle ANSI
    into a terminal or log. Zeitgeist's own ingest doctrine strips these
    (``editor.clean_field``); this module rejects instead of stripping,
    matching the rest of this file's fail-closed contract (over-bound
    values raise rather than truncate).

    .. _EXPERIMENTAL-spec-kitty-events#25: https://github.com/spec-kitty/EXPERIMENTAL-spec-kitty-events/issues/25
    """
    bad = sorted({f"U+{ord(ch):04X}" for ch in value if ord(ch) < 0x20 or ord(ch) == 0x7F})
    if bad:
        raise ZeitgeistAttrsControlCharacterError(
            f"{subject} contains control characters: {bad}"
        )


def _utf8_size(subject: str, value: str) -> int:
    """Return UTF-8 byte size, preserving the typed attrs error contract."""
    try:
        return len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ZeitgeistAttrsError(f"{subject} is not UTF-8 encodable") from exc


def to_zeitgeist_attrs(payload: BaseModel, envelope: Event) -> dict[str, str]:
    """Project one volatile payload and its envelope onto bounded attrs.

    Deterministic: iteration follows declaration order — the two envelope
    attrs first (``event_id``, ``occurred_at``), then the payload's fields —
    so the same event always yields byte-identical attrs.

    Args:
        payload: The volatile-family payload carried by *envelope*.
        envelope: The journal envelope this payload was emitted under. Its
            ``event_id`` and ``timestamp`` become the ``event_id`` and
            ``occurred_at`` attrs (ISO-8601); its ``event_type`` must name
            the same volatile family as *payload*.

    Raises:
        UnknownVolatileEventTypeError: *payload* is not a volatile-family
            payload model.
        ZeitgeistAttrsError: *envelope* declares a different event type.
        UnencodableFieldValueError: a carried field has no string encoding.
        ZeitgeistAttrsForbiddenKeyError: an emitted key is forbidden.
        ZeitgeistAttrsOverflowError: the projection exceeds the key-count,
            key-length, or value-length bounds. No truncation is ever
            applied.
    """
    event_type = next(
        (k for k, v in PAYLOAD_MODEL_BY_EVENT_TYPE.items() if type(payload) is v),
        None,
    )
    if event_type is None:
        raise UnknownVolatileEventTypeError(
            f"{type(payload).__name__} is not a volatile-family payload; "
            f"known: {sorted(PAYLOAD_MODEL_BY_EVENT_TYPE)}"
        )
    if envelope.event_type != event_type:
        raise ZeitgeistAttrsError(
            f"envelope declares event_type {envelope.event_type!r} but the "
            f"payload is a {event_type} payload"
        )

    # Envelope identity first, so the projection order is stable across
    # producers regardless of how each family's payload fields evolve.
    attrs = {
        "event_id": envelope.event_id,
        "occurred_at": envelope.timestamp.isoformat(),
    }
    attrs.update(
        _encode_fields(
            payload,
            skip=UNBROADCAST_FIELDS.get(event_type, frozenset()),
            projected=PROJECTED_FIELD_BY_EVENT_TYPE.get(event_type),
        )
    )

    bad_keys = sorted(attrs.keys() & FORBIDDEN_ATTR_KEYS)
    if bad_keys:
        raise ZeitgeistAttrsForbiddenKeyError(
            f"refusing to emit forbidden attr keys: {bad_keys}"
        )
    oversized_keys = sorted(
        key for key in attrs if len(key) > ZEITGEIST_ATTR_KEY_MAX_CHARS
    )
    if oversized_keys:
        raise ZeitgeistAttrsOverflowError(
            f"attr keys exceed the {ZEITGEIST_ATTR_KEY_MAX_CHARS}-char bound: "
            f"{oversized_keys}"
        )
    oversized_values = sorted(
        key
        for key, value in attrs.items()
        if _utf8_size(f"attr {key!r} value", value) > ZEITGEIST_ATTRS_MAX_BYTES
    )
    if oversized_values:
        raise ZeitgeistAttrsOverflowError(
            f"attr values exceed the {ZEITGEIST_ATTRS_MAX_BYTES}-byte bound: "
            f"{oversized_values}"
        )
    if len(attrs) > ZEITGEIST_ATTRS_MAX_KEYS:
        raise ZeitgeistAttrsOverflowError(
            f"projection has {len(attrs)} attrs; the bound is "
            f"{ZEITGEIST_ATTRS_MAX_KEYS}"
        )
    return attrs


# ── frame ref ────────────────────────────────────────────────────────────────

#: The payload field each family uses as the frame's aggregate identity.
#: ``PhaseEnteredPayload`` uses ``mission_id`` (required) rather than
#: ``mission_slug`` (optional display/back-compat; see the field's own
#: description) — that field alone can be absent on an otherwise-valid
#: payload, which would otherwise make identity loss the normal producer
#: outcome rather than an edge case.
REF_FIELD_BY_EVENT_TYPE: Mapping[str, str] = {
    WP_STATUS_CHANGED: "mission_slug",
    MISSION_CREATED: "mission_slug",
    MISSION_CLOSED: "mission_slug",
    PHASE_ENTERED: "mission_id",
    MISSION_RUN_STARTED: "run_id",
    NEXT_STEP_ISSUED: "run_id",
    NEXT_STEP_AUTO_COMPLETED: "run_id",
    DECISION_INPUT_REQUESTED: "run_id",
    DECISION_INPUT_ANSWERED: "run_id",
    MISSION_RUN_COMPLETED: "run_id",
}


def zeitgeist_ref_for(event_type: str, payload: BaseModel) -> str | None:
    """Return the frame ``ref`` for a volatile payload, or ``None``.

    Raises:
        UnknownVolatileEventTypeError: *event_type* is unknown or *payload*
            is not that event type's payload model.
        ZeitgeistAttrsOverflowError: the ref exceeds
            :data:`ZEITGEIST_ATTRS_MAX_BYTES` (the frame's ``ref`` carries
            the same bound as an attrs entry; see the module docstring).
    """
    model = PAYLOAD_MODEL_BY_EVENT_TYPE.get(event_type)
    if model is None or type(payload) is not model:
        raise UnknownVolatileEventTypeError(
            f"{type(payload).__name__} is not the payload of volatile event "
            f"type {event_type!r}; known: {sorted(PAYLOAD_MODEL_BY_EVENT_TYPE)}"
        )
    value = getattr(payload, REF_FIELD_BY_EVENT_TYPE[event_type], None)
    if value is None:
        return None
    ref = str(value)
    if _utf8_size(f"{event_type} ref", ref) > ZEITGEIST_ATTRS_MAX_BYTES:
        raise ZeitgeistAttrsOverflowError(
            f"{event_type} ref exceeds the {ZEITGEIST_ATTRS_MAX_BYTES}-byte bound"
        )
    return ref


# ── decode ───────────────────────────────────────────────────────────────────


def _unwrap_optional(annotation: Any) -> Any:
    """See through ``Optional[X]`` to the payload annotation beneath it.

    Handles both spellings pydantic resolves ``model_fields`` annotations
    to: ``typing.Optional``/``typing.Union`` (``get_origin`` is
    ``typing.Union``) and the PEP 604 ``X | None`` form (``get_origin`` is
    ``types.UnionType``) — the two are distinct origins at runtime, and
    several payload models in this package use the ``X | None`` spelling.
    """
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        args = tuple(a for a in get_args(annotation) if a is not type(None))
        if len(args) == 1:
            return args[0]
    return annotation


def _schema_keys(event_type: str, model: type[BaseModel]) -> frozenset[str]:
    """Every payload-sourced attr key the kind's projection may carry.

    Mirrors :func:`_encode_fields`: skipped fields contribute nothing,
    projected fields contribute their plain field name (the projection
    target is always a scalar attribute), and a nested value object
    contributes its ``<field>.<sub>`` keys.
    """
    skip = UNBROADCAST_FIELDS.get(event_type, frozenset())
    projected = PROJECTED_FIELD_BY_EVENT_TYPE.get(event_type, {})
    keys: set[str] = set()
    for name, field in model.model_fields.items():
        if name in skip:
            continue
        if name in projected:
            keys.add(name)
            continue
        annotation = _unwrap_optional(field.annotation)
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            keys.update(f"{name}.{sub}" for sub in annotation.model_fields)
        else:
            keys.add(name)
    return frozenset(keys)


_ALLOWED_KEYS_BY_EVENT_TYPE: Mapping[str, frozenset[str]] = {
    event_type: _schema_keys(event_type, model) | ENVELOPE_ATTR_KEYS
    for event_type, model in PAYLOAD_MODEL_BY_EVENT_TYPE.items()
}


def _required_schema_keys(event_type: str, model: type[BaseModel]) -> frozenset[str]:
    """The subset of :func:`_schema_keys` decode can insist on.

    A key is required only when :func:`to_zeitgeist_attrs` can never omit
    it: a projected actor-label key (:data:`PROJECTED_FIELD_BY_EVENT_TYPE`
    — every current entry projects a *required* nested actor identity via a
    property that always returns a non-empty label) or a payload field
    whose annotation does not admit ``None``. A field pydantic marks
    required but whose type is ``Optional`` (e.g.
    ``MissionCreatedPayload.mission_number``) can still be passed as
    explicit ``None`` and vanish from the wire on encode, so it is never
    required here — requiring it would reject attrs :func:`to_zeitgeist_attrs`
    genuinely produces. A nested, non-optional, non-projected value object
    would need its own required sub-keys computed recursively; no kind in
    today's vocabulary has one, so that case is left unhandled rather than
    guessed at.
    """
    skip = UNBROADCAST_FIELDS.get(event_type, frozenset())
    projected = PROJECTED_FIELD_BY_EVENT_TYPE.get(event_type, {})
    keys: set[str] = set()
    for name, field in model.model_fields.items():
        if name in skip:
            continue
        if name in projected:
            keys.add(name)
            continue
        annotation = field.annotation
        unwrapped = _unwrap_optional(annotation)
        if isinstance(unwrapped, type) and issubclass(unwrapped, BaseModel):
            continue
        if unwrapped is annotation:
            keys.add(name)
    return frozenset(keys)


_REQUIRED_KEYS_BY_EVENT_TYPE: Mapping[str, frozenset[str]] = {
    event_type: _required_schema_keys(event_type, model) | ENVELOPE_ATTR_KEYS
    for event_type, model in PAYLOAD_MODEL_BY_EVENT_TYPE.items()
}


def from_zeitgeist_attrs(
    event_type: str, attrs: Mapping[str, str]
) -> VolatileMoment:
    """Validate inbound attrs against the kind's closed key vocabulary.

    The attrs are opaque on the wire; this function is the only place that
    gives them back their meaning. It enforces the shape :func:`to_zeitgeist_attrs`
    guarantees on emit — flat ``str:str``, within the bound, no forbidden
    keys, no keys outside the kind's schema, and every key the kind's
    payload can never omit on a successful encode (its non-``Optional``
    fields, the projected actor-label key, and the envelope's ``event_id``/
    ``occurred_at``) actually present — and wraps the result, with the
    frame's identity, in a :class:`VolatileMoment` for rendering.

    This validates presence and shape, not value correctness: beyond being
    ``str``-typed and within the byte bound, a present value's format is
    opaque — an int-typed field's string need not parse as an int, an
    enum-typed field's string need not be one of its members — because
    values are not reparsed here, only rendered later by a consumer that
    knows the kind. An inbound mapping missing an *optional* payload key
    (one whose annotation admits ``None``) decodes with that key absent,
    since rebuilding the journal payload remains impossible by design
    ("Projection, not reconstruction").

    Raises:
        UnknownVolatileEventTypeError: *event_type* is not in the volatile
            vocabulary.
        ZeitgeistAttrsError: a value is not ``str``, a key is outside the
            kind's closed key set, a key the kind's payload always carries
            on encode is missing, or an ``event_id``/``occurred_at`` attr is
            present but malformed (empty, or not ISO-8601, respectively).
        ZeitgeistAttrsControlCharacterError: a value carries a C0 control
            character or DEL.
        ZeitgeistAttrsForbiddenKeyError: a forbidden key is present.
        ZeitgeistAttrsOverflowError: the bound is exceeded.
    """
    if event_type not in PAYLOAD_MODEL_BY_EVENT_TYPE:
        raise UnknownVolatileEventTypeError(
            f"{event_type!r} is not a volatile event type; "
            f"known: {sorted(PAYLOAD_MODEL_BY_EVENT_TYPE)}"
        )

    for key, value in attrs.items():
        if not isinstance(value, str):
            raise ZeitgeistAttrsError(f"attr {key!r}: expected str, got {type(value).__name__}")
        _reject_control_characters(f"attr {key!r} value", value)

    allowed = _ALLOWED_KEYS_BY_EVENT_TYPE[event_type]
    unknown = sorted(attrs.keys() - allowed)
    if unknown:
        raise ZeitgeistAttrsError(
            f"attrs carry keys outside the {event_type} schema: {unknown}"
        )

    bad_keys = sorted(attrs.keys() & FORBIDDEN_ATTR_KEYS)
    if bad_keys:
        raise ZeitgeistAttrsForbiddenKeyError(f"forbidden attr keys: {bad_keys}")

    oversized_keys = sorted(
        key for key in attrs if len(key) > ZEITGEIST_ATTR_KEY_MAX_CHARS
    )
    if oversized_keys:
        raise ZeitgeistAttrsOverflowError(
            f"attr keys exceed the {ZEITGEIST_ATTR_KEY_MAX_CHARS}-char bound: "
            f"{oversized_keys}"
        )
    # UTF-8 byte counts, matching the relay's `maxUtf8Bytes` clause — the
    # actually-binding one, since byte count >= char count means satisfying
    # it also satisfies the relay's independent `maxLength` (character)
    # clause (spec-kitty-events#16). A char-count check here would
    # under-reject a value the relay itself rejects (e.g. "é" * 121 is 121
    # characters but 242 UTF-8 bytes, over the relay's byte bound). This
    # also catches a lone surrogate with a typed error, same as before.
    oversized_values = sorted(
        key
        for key, value in attrs.items()
        if _utf8_size(f"attr {key!r} value", value) > ZEITGEIST_ATTRS_MAX_BYTES
    )
    if oversized_values:
        raise ZeitgeistAttrsOverflowError(
            f"attr values exceed the {ZEITGEIST_ATTRS_MAX_BYTES}-byte bound: "
            f"{oversized_values}"
        )
    if len(attrs) > ZEITGEIST_ATTRS_MAX_KEYS:
        raise ZeitgeistAttrsOverflowError(
            f"{len(attrs)} attrs exceed the bound of {ZEITGEIST_ATTRS_MAX_KEYS}"
        )

    missing = sorted(_REQUIRED_KEYS_BY_EVENT_TYPE[event_type] - attrs.keys())
    if missing:
        raise ZeitgeistAttrsError(
            f"attrs are missing keys the {event_type} schema always carries "
            f"on encode: {missing}"
        )

    event_id = attrs.get("event_id")
    if event_id is not None and not event_id:
        raise ZeitgeistAttrsError("attr 'event_id' must not be empty")
    occurred_at = attrs.get("occurred_at")
    if occurred_at is not None:
        try:
            datetime.fromisoformat(occurred_at)
        except ValueError as exc:
            raise ZeitgeistAttrsError(
                f"attr 'occurred_at' is not ISO-8601: {occurred_at!r}"
            ) from exc

    return VolatileMoment(kind=event_type, ref=attrs.get(REF_FIELD_BY_EVENT_TYPE[event_type]), attrs=dict(attrs))
