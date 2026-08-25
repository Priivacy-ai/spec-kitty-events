"""Zeitgeist attrs codecs for the volatile mission/WP event families (E2).

The Ephemeral Team Status design broadcasts mission/WP moments through each
team's Zeitgeist relay as *opaque bounded attributes*: one ``event`` frame is
``{kind, ref?, attrs}`` where ``attrs`` must be a flat ``str:str`` mapping
with at most 16 keys and at most 240 bytes per key and per value, and no
forbidden key anywhere (zeitgeist issue: ``EventArgs {kind: ident,
ref?: string≤240, attrs: {str:str}, ≤16 keys, ≤240 B each}``; design page
``ephemeral-team-status.html``, "The vocabulary" paragraph).

This module is the single owner of the mapping between this package's
volatile payload vocabulary and that wire shape:

* :func:`to_zeitgeist_attrs` — project a volatile payload onto bounded attrs.
* :func:`from_zeitgeist_attrs` — validate inbound attrs against the same
  closed per-kind key vocabulary and return them as a
  :class:`VolatileMoment` (kind + ref + attrs), the typed view a consumer
  renders from.

Projection, not reconstruction
------------------------------
Attrs carry the *moment*: identity, transition facts, actor. A relayed
moment deliberately does NOT rebuild the journal payload — two fields whose
shape cannot fit flat bounded strings are declared in
:data:`UNBROADCAST_FIELDS` and stay local:

* ``StatusTransitionPayload.evidence`` — structured evidence lists live in
  the journal only. This also keeps decode honest: ``to_lane ∈ {approved,
  done}`` payloads *require* evidence, so no decoder could rebuild them
  from attrs without fabricating audit data.
* ``DecisionInputRequestedPayload.options`` — suggested answers are display
  hints of unbounded length.

Everything else the family declares rides in attrs; any carried value over
the bound raises rather than truncates: an oversize payload simply does not
broadcast (the CLI fan-out seam is fire-and-forget; a dropped moment is
lost *by design*, exactly like a downed relay or an expired budget).

Actor narrowing
---------------
``StatusTransitionPayload.actor`` accepts ``str | Dict[str, Any]``. Attrs
carry ``actor_label`` — the canonical display form the package already
defines for reducers and logs — so a structured actor projects to its label
string. The mission-run family's
:class:`~spec_kitty_events.mission_next.RuntimeActorIdentity` is fully
scalar and rides field-for-field as ``actor.<field>`` keys.

Forbidden keys
--------------
:data:`FORBIDDEN_ATTR_KEYS` unions the legacy keys this package already
rejects (:data:`~spec_kitty_events.forbidden_keys.FORBIDDEN_LEGACY_KEYS`)
with a mirror of zeitgeist's direction-agnostic ingress set
(``capabilities.FORBIDDEN_KEYS_V1``, mirrored here by value with a version
suffix — zeitgeist owns transport policy, this package owns vocabulary, and
neither imports the other; same idiom as the harness-observation bounds
that mirror zeitgeist ``FIELD_MAX``). :func:`to_zeitgeist_attrs` refuses to
emit any of them. Dotted keys (``actor.actor_id``) are distinct strings from
their segments, matching zeitgeist's flat key-only check.
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any, Mapping, Optional, Type

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
from spec_kitty_events.status import WP_STATUS_CHANGED, StatusTransitionPayload

__all__ = [
    "FORBIDDEN_ATTR_KEYS",
    "PAYLOAD_MODEL_BY_EVENT_TYPE",
    "PROJECTED_FIELD_BY_EVENT_TYPE",
    "REF_FIELD_BY_EVENT_TYPE",
    "UNBROADCAST_FIELDS",
    "VOLATILE_EVENT_TYPES",
    "VolatileMoment",
    "ZEITGEIST_ATTRS_MAX_BYTES",
    "ZEITGEIST_ATTRS_MAX_KEYS",
    "ZEITGEIST_FORBIDDEN_KEYS_V1",
    "UnknownVolatileEventTypeError",
    "UnencodableFieldValueError",
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
"""Maximum UTF-8 size of one attr key or value (zeitgeist EventArgs; the
frame's ``ref`` carries the same bound independently)."""

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
    (≤240 bytes; ``None`` when the family has no single identity field),
    ``attrs`` the validated bounded projection. Consumers render from this;
    nobody re-parses raw attr strings outside this module's vocabulary.
    """

    kind: str
    ref: Optional[str]
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
PAYLOAD_MODEL_BY_EVENT_TYPE: Mapping[str, Type[BaseModel]] = {
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

#: Per-type fields that never ride the relay because their shape (structured
#: lists) cannot fit the flat bounded attrs. Everything else MUST survive.
UNBROADCAST_FIELDS: Mapping[str, frozenset[str]] = {
    WP_STATUS_CHANGED: frozenset({"evidence"}),
    DECISION_INPUT_REQUESTED: frozenset({"options"}),
}

#: Per-type field projections: attr key -> canonical attribute carried under
#: that key. ``actor`` rides as ``actor_label`` (see module docstring).
PROJECTED_FIELD_BY_EVENT_TYPE: Mapping[str, Mapping[str, str]] = {
    WP_STATUS_CHANGED: {"actor": "actor_label"},
}


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
    :data:`PROJECTED_FIELD_BY_EVENT_TYPE`).
    """
    entries: dict[str, str] = {}
    for name, field in type(model).model_fields.items():
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


def to_zeitgeist_attrs(payload: BaseModel) -> dict[str, str]:
    """Project one volatile payload onto bounded, flat ``str:str`` attrs.

    Deterministic: iteration follows the model's declaration order, so the
    same payload always yields byte-identical attrs (and insertion-ordered
    dicts compare equal regardless).

    Raises:
        UnknownVolatileEventTypeError: *payload* is not a volatile-family
            payload model.
        UnencodableFieldValueError: a carried field has no string encoding.
        ZeitgeistAttrsForbiddenKeyError: an emitted key is forbidden.
        ZeitgeistAttrsOverflowError: the projection exceeds the key-count or
            byte bounds. No truncation is ever applied.
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

    attrs = _encode_fields(
        payload,
        skip=UNBROADCAST_FIELDS.get(event_type, frozenset()),
        projected=PROJECTED_FIELD_BY_EVENT_TYPE.get(event_type),
    )

    bad_keys = sorted(attrs.keys() & FORBIDDEN_ATTR_KEYS)
    if bad_keys:
        raise ZeitgeistAttrsForbiddenKeyError(
            f"refusing to emit forbidden attr keys: {bad_keys}"
        )
    oversized = sorted(
        key
        for key, value in attrs.items()
        if len(key.encode("utf-8")) > ZEITGEIST_ATTRS_MAX_BYTES
        or len(value.encode("utf-8")) > ZEITGEIST_ATTRS_MAX_BYTES
    )
    if oversized:
        raise ZeitgeistAttrsOverflowError(
            f"attr entries exceed the {ZEITGEIST_ATTRS_MAX_BYTES}-byte bound: "
            f"{oversized}"
        )
    if len(attrs) > ZEITGEIST_ATTRS_MAX_KEYS:
        raise ZeitgeistAttrsOverflowError(
            f"projection has {len(attrs)} attrs; the bound is "
            f"{ZEITGEIST_ATTRS_MAX_KEYS}"
        )
    return attrs


# ── frame ref ────────────────────────────────────────────────────────────────

#: The payload field each family uses as the frame's aggregate identity.
REF_FIELD_BY_EVENT_TYPE: Mapping[str, str] = {
    WP_STATUS_CHANGED: "mission_slug",
    MISSION_CREATED: "mission_slug",
    MISSION_CLOSED: "mission_slug",
    PHASE_ENTERED: "mission_slug",
    MISSION_RUN_STARTED: "run_id",
    NEXT_STEP_ISSUED: "run_id",
    NEXT_STEP_AUTO_COMPLETED: "run_id",
    DECISION_INPUT_REQUESTED: "run_id",
    DECISION_INPUT_ANSWERED: "run_id",
    MISSION_RUN_COMPLETED: "run_id",
}


def zeitgeist_ref_for(event_type: str, payload: BaseModel) -> Optional[str]:
    """Return the frame ``ref`` for a volatile payload, or ``None``.

    Raises:
        UnknownVolatileEventTypeError: *event_type* is unknown or *payload*
            is not that event type's payload model.
    """
    model = PAYLOAD_MODEL_BY_EVENT_TYPE.get(event_type)
    if model is None or type(payload) is not model:
        raise UnknownVolatileEventTypeError(
            f"{type(payload).__name__} is not the payload of volatile event "
            f"type {event_type!r}; known: {sorted(PAYLOAD_MODEL_BY_EVENT_TYPE)}"
        )
    value = getattr(payload, REF_FIELD_BY_EVENT_TYPE[event_type], None)
    return None if value is None else str(value)


# ── decode ───────────────────────────────────────────────────────────────────


def _schema_keys(event_type: str, model: Type[BaseModel]) -> frozenset[str]:
    """Every attr key the kind's projection may legally carry."""
    skip = UNBROADCAST_FIELDS.get(event_type, frozenset())
    keys: set[str] = set()
    for name, field in model.model_fields.items():
        if name in skip:
            continue
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            keys.update(f"{name}.{sub}" for sub in annotation.model_fields)
        else:
            keys.add(name)
    return frozenset(keys)


_ALLOWED_KEYS_BY_EVENT_TYPE: Mapping[str, frozenset[str]] = {
    event_type: _schema_keys(event_type, model)
    for event_type, model in PAYLOAD_MODEL_BY_EVENT_TYPE.items()
}


def from_zeitgeist_attrs(
    event_type: str, attrs: Mapping[str, str]
) -> VolatileMoment:
    """Validate inbound attrs against the kind's closed key vocabulary.

    The attrs are opaque on the wire; this function is the only place that
    gives them back their meaning. It enforces exactly what :func:`to_zeitgeist_attrs`
    guarantees on emit — flat ``str:str``, within the bound, no forbidden
    keys, no keys outside the kind's schema — and wraps the result, with the
    frame's identity, in a :class:`VolatileMoment` for rendering. It does
    **not** rebuild the journal payload (see "Projection, not
    reconstruction" above).

    Raises:
        UnknownVolatileEventTypeError: *event_type* is not in the volatile
            vocabulary.
        ZeitgeistAttrsError: a value is not ``str`` or a key is outside the
            kind's closed key set.
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

    allowed = _ALLOWED_KEYS_BY_EVENT_TYPE[event_type]
    unknown = sorted(attrs.keys() - allowed)
    if unknown:
        raise ZeitgeistAttrsError(
            f"attrs carry keys outside the {event_type} schema: {unknown}"
        )

    bad_keys = sorted(attrs.keys() & FORBIDDEN_ATTR_KEYS)
    if bad_keys:
        raise ZeitgeistAttrsForbiddenKeyError(f"forbidden attr keys: {bad_keys}")

    oversized = sorted(
        key
        for key, value in attrs.items()
        if len(key.encode("utf-8")) > ZEITGEIST_ATTRS_MAX_BYTES
        or len(value.encode("utf-8")) > ZEITGEIST_ATTRS_MAX_BYTES
    )
    if oversized:
        raise ZeitgeistAttrsOverflowError(
            f"attr entries exceed the {ZEITGEIST_ATTRS_MAX_BYTES}-byte bound: "
            f"{oversized}"
        )
    if len(attrs) > ZEITGEIST_ATTRS_MAX_KEYS:
        raise ZeitgeistAttrsOverflowError(
            f"{len(attrs)} attrs exceed the bound of {ZEITGEIST_ATTRS_MAX_KEYS}"
        )

    return VolatileMoment(kind=event_type, ref=attrs.get(REF_FIELD_BY_EVENT_TYPE[event_type]), attrs=dict(attrs))

