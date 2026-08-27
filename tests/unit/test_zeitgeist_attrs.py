"""Unit tests for the zeitgeist attrs codecs (E2)."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import pytest
from pydantic import BaseModel

from spec_kitty_events import zeitgeist_attrs
from spec_kitty_events.forbidden_keys import FORBIDDEN_LEGACY_KEYS
from spec_kitty_events.lifecycle import (
    MissionClosedPayload,
    MissionStartedPayload,
    PhaseEnteredPayload,
)
from spec_kitty_events.mission_next import (
    DecisionInputAnsweredPayload,
    DecisionInputRequestedPayload,
    MissionRunCompletedPayload,
    MissionRunStartedPayload,
    NextStepAutoCompletedPayload,
    NextStepIssuedPayload,
    RuntimeActorIdentity,
)
from spec_kitty_events.models import Event
from spec_kitty_events.status import StatusTransitionPayload
from spec_kitty_events.zeitgeist_attrs import (
    FORBIDDEN_ATTR_KEYS,
    PAYLOAD_MODEL_BY_EVENT_TYPE,
    PROJECTED_FIELD_BY_EVENT_TYPE,
    REF_FIELD_BY_EVENT_TYPE,
    UNBROADCAST_FIELDS,
    VOLATILE_EVENT_TYPES,
    ZEITGEIST_ATTRS_MAX_BYTES,
    ZEITGEIST_ATTRS_MAX_KEYS,
    ZEITGEIST_ATTR_KEY_MAX_CHARS,
    ZEITGEIST_FORBIDDEN_KEYS_V1,
    UnencodableFieldValueError,
    UnknownVolatileEventTypeError,
    VolatileMoment,
    ZeitgeistAttrsControlCharacterError,
    ZeitgeistAttrsError,
    ZeitgeistAttrsForbiddenKeyError,
    ZeitgeistAttrsOverflowError,
    from_zeitgeist_attrs,
    to_zeitgeist_attrs,
    zeitgeist_ref_for,
)

_EVENT_ID = "01JME2E2E2E2E2E2E2E2E2E2E2"
_CORRELATION_ID = "01JMC0RRC0RRC0RRC0RRC0RRC0"
_PROJECT_UUID = UUID("550e8400-e29b-41d4-a716-446655440000")


def _envelope(
    event_type: str,
    *,
    event_id: str = _EVENT_ID,
    timestamp: datetime = datetime(2026, 8, 25, 9, 0, 0, tzinfo=timezone.utc),
) -> Event:
    return Event(
        event_id=event_id,
        event_type=event_type,
        aggregate_id="agg",
        timestamp=timestamp,
        build_id="build-unit",
        node_id="node-unit",
        lamport_clock=1,
        project_uuid=_PROJECT_UUID,
        correlation_id=_CORRELATION_ID,
    )


def _transition(**overrides) -> StatusTransitionPayload:
    fields = {
        "mission_slug": "demo-mission",
        "wp_id": "WP01",
        "to_lane": "doing",
        "actor": "robert",
        "execution_mode": "worktree",
    }
    fields.update(overrides)
    return StatusTransitionPayload(**fields)


def _identity() -> RuntimeActorIdentity:
    return RuntimeActorIdentity(
        actor_id="rob@robshouse.net",
        actor_type="human",
        display_name="Robert Douglass",
        provider=None,
        model=None,
        tool=None,
    )


# ── closed vocabulary ────────────────────────────────────────────────────────


def test_volatile_vocabulary_is_the_ephemeral_design_set() -> None:
    assert VOLATILE_EVENT_TYPES == {
        "WPStatusChanged", "MissionCreated", "MissionClosed", "PhaseEntered",
        "MissionRunStarted", "NextStepIssued", "NextStepAutoCompleted",
        "DecisionInputRequested", "DecisionInputAnswered", "MissionRunCompleted",
        "DecisionPointOpened", "DecisionPointResolved",
        "SpecifyStarted", "SpecifyCompleted",
        "PlanStarted", "PlanCompleted",
        "TasksStarted", "TasksCompleted",
    }


def test_dispatch_table_covers_exactly_the_volatile_types() -> None:
    assert set(PAYLOAD_MODEL_BY_EVENT_TYPE) == VOLATILE_EVENT_TYPES


def test_every_ref_field_is_a_declared_field_of_its_model() -> None:
    for event_type, ref_field in REF_FIELD_BY_EVENT_TYPE.items():
        for model in zeitgeist_attrs._payload_types(event_type):
            assert ref_field in model.model_fields, event_type


def test_unbroadcast_fields_exist_on_their_models() -> None:
    """The skip lists cannot silently rot when a payload is renamed.

    A discriminated-union event type's skip set is the union of every
    variant's own prose/nested fields, so a given name need only exist on
    at least one variant (e.g. ``rationale`` exists on the ADR variant of
    ``DecisionPointResolved`` but not the interview one).
    """
    for event_type, fields in UNBROADCAST_FIELDS.items():
        variants = zeitgeist_attrs._payload_types(event_type)
        for name in fields:
            assert any(name in model.model_fields for model in variants), (event_type, name)


def test_every_structured_actor_family_projects_to_a_single_label() -> None:
    """No family broadcasts a structured actor field-for-field: producer-
    asserted identity would duplicate what the relay attests itself.
    Families whose ``actor`` is a plain (optionally absent) string need no
    projection — the value itself rides under the ``actor`` key."""
    for event_type in VOLATILE_EVENT_TYPES:
        for model in zeitgeist_attrs._payload_types(event_type):
            field = model.model_fields.get("actor")
            if field is None:
                continue
            base = zeitgeist_attrs._unwrap_optional(field.annotation)
            if not (isinstance(base, type) and issubclass(base, BaseModel)):
                continue
            assert PROJECTED_FIELD_BY_EVENT_TYPE[event_type].get("actor") == "actor_label", (
                event_type,
                field.annotation,
            )


def test_actor_label_is_exactly_the_opaque_machine_id() -> None:
    """Identifiers only: the label never derives from free text."""
    assert _identity().actor_label == "rob@robshouse.net"
    bare = RuntimeActorIdentity(actor_id="svc-1", actor_type="service")
    assert bare.actor_label == "svc-1"


def test_oversize_display_name_never_drops_the_moment() -> None:
    """Regression pin: a label sourced from unbounded prose made any oversize
    display name raise at the bound and silently kill the whole broadcast."""
    identity = RuntimeActorIdentity(
        actor_id="svc-1",
        actor_type="service",
        display_name="Dr. " + "X" * 250,
    )
    payload = MissionRunStartedPayload(
        run_id="run-01", mission_type="software-dev", actor=identity
    )
    attrs = to_zeitgeist_attrs(payload, _envelope("MissionRunStarted"))
    assert attrs["actor"] == "svc-1"
    assert "Dr." not in " ".join(attrs.values())


def test_forbidden_keys_union_the_zeitgeist_mirror_and_legacy_set() -> None:
    assert FORBIDDEN_ATTR_KEYS == ZEITGEIST_FORBIDDEN_KEYS_V1 | FORBIDDEN_LEGACY_KEYS


def _reachable_nested_models(event_type: str, model: type[BaseModel]):
    """Every nested ``BaseModel`` *model*'s top-level fields actually walk
    into, mirroring :func:`zeitgeist_attrs._schema_keys_for_model` exactly: a
    field the kind's ``UNBROADCAST_FIELDS`` skips, or that
    ``PROJECTED_FIELD_BY_EVENT_TYPE`` redirects to a scalar attribute
    (e.g. ``actor`` -> ``actor_label``), is never walked into by encode or
    decode either, so it contributes no reachable nested model here. One
    level: a second level of nesting is not a silent-leak risk because
    :func:`zeitgeist_attrs._encode_fields` hard-raises on it rather than
    emitting anything (EXPERIMENTAL-spec-kitty-events#21).
    """
    skip = UNBROADCAST_FIELDS.get(event_type, frozenset())
    projected = PROJECTED_FIELD_BY_EVENT_TYPE.get(event_type, {})
    for name, field in model.model_fields.items():
        if name in skip or name in projected:
            continue
        annotation = zeitgeist_attrs._unwrap_optional(field.annotation)
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            yield annotation


def test_no_declared_field_name_is_forbidden() -> None:
    """Structural guarantee behind "never emit forbidden keys", extended to
    every nested-model subfield encode/decode actually walk into — not just
    a payload's top-level fields. A top-level-only walk stays green even if
    a future *reachable* nested field collides with a forbidden name
    (EXPERIMENTAL-spec-kitty-events#21). Today's vocabulary cannot collide;
    if a future field does, this fails first."""
    for event_type in PAYLOAD_MODEL_BY_EVENT_TYPE:
        for model in zeitgeist_attrs._payload_types(event_type):
            for name in model.model_fields:
                assert name not in FORBIDDEN_ATTR_KEYS, (model.__name__, name)
            for nested in _reachable_nested_models(event_type, model):
                for name in nested.model_fields:
                    assert name not in FORBIDDEN_ATTR_KEYS, (nested.__name__, name)


def _forbidden_collisions(event_type: str, model: type[BaseModel]) -> list[str]:
    return [
        name
        for nested in _reachable_nested_models(event_type, model)
        for name in nested.model_fields
        if name in FORBIDDEN_ATTR_KEYS
    ]


def test_reachable_nested_model_collision_fails_the_structural_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pins that the extension in ``test_no_declared_field_name_is_forbidden``
    actually fires — not just a mechanism that never executes, since no
    payload in today's vocabulary has a reachable (non-skipped,
    non-projected) nested model. A field on a nested, *reachable* model that
    collides with a forbidden name is caught; the identical field on a
    *skipped* nested model (mirroring ``ClosureMessageRef.url`` under
    ``DecisionPointResolved``'s ``closure_message``, which is unreachable
    today only because it is skipped) is correctly left alone
    (EXPERIMENTAL-spec-kitty-events#21)."""

    class _Nested(BaseModel):
        url: str

    class _FuturePayload(BaseModel):
        x: str
        nested: _Nested

    assert _forbidden_collisions("FutureType", _FuturePayload) == ["url"]

    monkeypatch.setitem(zeitgeist_attrs.UNBROADCAST_FIELDS, "FutureTypeSkipped", frozenset({"nested"}))
    assert _forbidden_collisions("FutureTypeSkipped", _FuturePayload) == []


def test_schema_keys_unwrap_optional_nested_models() -> None:
    """Regression pin (EXPERIMENTAL-spec-kitty-events#21): the decode schema
    builder must nest into a subfield typed ``Optional[BaseModel]`` (both the
    ``typing.Optional[X]`` and the PEP 604 ``X | None`` spelling) exactly as
    it does for a required nested model — matching what :func:`_encode_fields`
    actually emits, since encode checks the *value*, not the static
    annotation, and a payload can carry ``None`` for that field. A decode
    schema built from the bare (non-unwrapped) annotation would silently stop
    matching the keys encode emits the moment a nested field is loosened to
    ``Optional``.
    """

    class _Inner(BaseModel):
        a: str
        b: str

    class _OptionalSpelling(BaseModel):
        x: str
        nested: Optional[_Inner] = None

    class _Pep604Spelling(BaseModel):
        x: str
        nested: _Inner | None = None

    for fake_type, model in (
        ("_OptionalSpelling", _OptionalSpelling),
        ("_Pep604Spelling", _Pep604Spelling),
    ):
        keys = zeitgeist_attrs._schema_keys_for_model(fake_type, model)
        assert keys == {"x", "nested.a", "nested.b"}, (fake_type, keys)


# ── encode ───────────────────────────────────────────────────────────────────


def test_projection_is_deterministic() -> None:
    first = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    second = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    assert first == second
    assert list(first) == list(second)


def test_envelope_identity_leads_the_projection() -> None:
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    assert list(attrs)[:2] == ["event_id", "occurred_at"]
    assert attrs["event_id"] == _EVENT_ID
    assert attrs["occurred_at"] == "2026-08-25T09:00:00+00:00"


def test_occurred_at_comes_from_the_envelope_not_receipt_time() -> None:
    envelope = _envelope("MissionClosed")
    payload = MissionClosedPayload(mission_slug="s", mission_number=1,
                                   mission_type="software-dev")
    attrs = to_zeitgeist_attrs(payload, envelope)
    assert attrs["occurred_at"] == envelope.timestamp.isoformat()


def test_encode_canonicalises_a_naive_timestamp_to_utc() -> None:
    """#100: a naive Event.timestamp is idiomatic in this repo (Event has no
    tz-aware validator, and conformance/timestamp_semantics._to_utc treats
    naive as UTC) but from_zeitgeist_attrs (#62) rejects a naive occurred_at
    on decode. Encode must canonicalise rather than emit the naive value
    as-is, so the codec's own output always round-trips."""
    envelope = _envelope(
        "WPStatusChanged", timestamp=datetime(2026, 8, 25, 9, 0, 0)
    )
    attrs = to_zeitgeist_attrs(_transition(), envelope)
    assert attrs["occurred_at"] == "2026-08-25T09:00:00+00:00"

    moment = from_zeitgeist_attrs("WPStatusChanged", attrs)
    assert moment.attrs["occurred_at"] == "2026-08-25T09:00:00+00:00"


def test_envelope_event_type_must_match_the_payload_family() -> None:
    with pytest.raises(ZeitgeistAttrsError):
        to_zeitgeist_attrs(_transition(), _envelope("MissionCreated"))


def test_absent_optionals_emit_no_key() -> None:
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    assert "from_lane" not in attrs
    assert "review_ref" not in attrs


def test_structured_actor_projects_to_actor_label() -> None:
    structured = _transition(actor={"role": "implementer", "profile": "ox"})
    plain = _transition(actor=structured.actor_label)
    assert to_zeitgeist_attrs(structured, _envelope("WPStatusChanged"))["actor"] == structured.actor_label
    assert to_zeitgeist_attrs(plain, _envelope("WPStatusChanged"))["actor"] == structured.actor_label


def test_mission_run_actor_rides_as_one_label_never_as_identity_breakdown() -> None:
    payload = MissionRunStartedPayload(
        run_id="run-01",
        mission_type="software-dev",
        actor=_identity(),
    )
    attrs = to_zeitgeist_attrs(payload, _envelope("MissionRunStarted"))
    assert attrs["actor"] == "rob@robshouse.net"
    assert not any(key.startswith("actor.") for key in attrs)


def test_mission_level_actor_rides_as_an_opaque_identifier() -> None:
    """The mission-level moments can say WHO: the optional plain-string
    ``actor`` rides under the same ``actor`` key every other family uses,
    and an absent actor emits no key (pre-8.0 producers stay valid)."""
    from spec_kitty_events.lifecycle import MissionCreatedPayload

    created = MissionCreatedPayload(
        mission_slug="demo-mission",
        mission_number=12,
        mission_type="software-dev",
        target_branch="main",
        wp_count=3,
        friendly_name="Demo",
        purpose_tldr="Demo",
        purpose_context="Demo",
        actor="rob@robshouse.net",
    )
    attrs = to_zeitgeist_attrs(created, _envelope("MissionCreated"))
    assert attrs["actor"] == "rob@robshouse.net"
    moment = from_zeitgeist_attrs("MissionCreated", attrs)
    assert moment.attrs["actor"] == "rob@robshouse.net"

    closed = MissionClosedPayload(
        mission_slug="demo-mission", mission_number=12,
        mission_type="software-dev", actor="merge-agent",
    )
    closed_attrs = to_zeitgeist_attrs(closed, _envelope("MissionClosed"))
    assert closed_attrs["actor"] == "merge-agent"


def test_mission_run_identity_keys_admitted_both_directions() -> None:
    """The live CLI emitter injects mission_id/mission_slug post-hoc into the
    six mission-run payloads; both keys must ride and decode as identifiers."""
    payload = MissionRunStartedPayload(
        run_id="run-01",
        mission_type="software-dev",
        actor=_identity(),
        mission_id="mission-demo",
        mission_slug="demo-mission",
    )
    attrs = to_zeitgeist_attrs(payload, _envelope("MissionRunStarted"))
    assert attrs["mission_id"] == "mission-demo"
    assert attrs["mission_slug"] == "demo-mission"
    moment = from_zeitgeist_attrs("MissionRunStarted", attrs)
    assert moment.attrs["mission_slug"] == "demo-mission"

    bare = MissionRunStartedPayload(
        run_id="run-01", mission_type="software-dev", actor=_identity()
    )
    bare_attrs = to_zeitgeist_attrs(bare, _envelope("MissionRunStarted"))
    assert "mission_id" not in bare_attrs and "mission_slug" not in bare_attrs


def test_no_volatile_projection_emits_dotted_keys() -> None:
    """The flat key space must stay flat: dotted names are how producer-
    asserted identity sneaks past a flat-key check."""
    payloads = [
        (_transition(actor={"role": "implementer", "profile": "ox"}), "WPStatusChanged"),
        (MissionRunStartedPayload(run_id="r", mission_type="t", actor=_identity()), "MissionRunStarted"),
        (
            NextStepIssuedPayload(
                run_id="r", step_id="s", agent_id="a", actor=_identity()
            ),
            "NextStepIssued",
        ),
        (
            NextStepAutoCompletedPayload(
                run_id="r", step_id="s", agent_id="a", result="success", actor=_identity()
            ),
            "NextStepAutoCompleted",
        ),
        (
            DecisionInputRequestedPayload(
                run_id="r", decision_id="d", step_id="s", question="Ship?",
                options=("yes",), actor=_identity(),
            ),
            "DecisionInputRequested",
        ),
        (
            __import__("spec_kitty_events.mission_next", fromlist=["DecisionInputAnsweredPayload"]).DecisionInputAnsweredPayload(
                run_id="r", decision_id="d", answer="yes", actor=_identity(),
            ),
            "DecisionInputAnswered",
        ),
        (
            MissionRunCompletedPayload(run_id="r", mission_type="t", actor=_identity()),
            "MissionRunCompleted",
        ),
    ]
    for payload, event_type in payloads:
        attrs = to_zeitgeist_attrs(payload, _envelope(event_type))
        assert not any("." in key for key in attrs), (event_type, sorted(attrs))


def test_prose_never_reaches_the_broadcast() -> None:
    """Identifiers only, with one deliberate, scoped exception: none of the
    raw free-text payload fields ever ride the wire under their own key,
    and no *non-summary* attr value carries prose (the 72 h relay is
    public-ish real estate; the journal is where prose lives). The single
    sanctioned exception is the derived ``summary`` attr itself — the
    bounded moment-attribute projection this module now owns (issue #77)
    folds a deterministic, truncated slice of specific prose fields into
    that one key, and nowhere else."""
    from spec_kitty_events.lifecycle import MissionCreatedPayload

    payload = MissionCreatedPayload(
        mission_slug="demo-mission",
        mission_number=12,
        mission_type="software-dev",
        target_branch="main",
        wp_count=3,
        friendly_name="Board approved 40M for the rollout",
        purpose_tldr="Bob Smith (bob@acme.com) is the counterparty contact.",
        purpose_context="Broadcast through the team relay for 72 hours.",
    )
    attrs = to_zeitgeist_attrs(payload, _envelope("MissionCreated"))
    non_summary_blob = " ".join(v for k, v in attrs.items() if k != "summary")
    assert "friendly_name" not in attrs and "40M" not in non_summary_blob
    assert "purpose_tldr" not in attrs and "bob@acme.com" not in non_summary_blob
    # purpose_context never feeds the summary builder, so it stays out entirely.
    assert "purpose_context" not in attrs and "72 hours" not in attrs["summary"]
    assert attrs["summary"] == (
        "Board approved 40M for the rollout; Bob Smith (bob@acme.com) is the counterparty contact."
    )


def test_decision_question_and_answer_stay_local() -> None:
    requested = DecisionInputRequestedPayload(
        run_id="run-01", decision_id="dec-01", step_id="step-07",
        question="Ship WP01 to done now?", options=("yes", "no"),
        actor=_identity(),
    )
    attrs = to_zeitgeist_attrs(requested, _envelope("DecisionInputRequested"))
    assert "question" not in attrs and "options" not in attrs

    answered = DecisionInputAnsweredPayload(
        run_id="run-01", decision_id="dec-01", answer="yes, but keep it quiet",
        actor=_identity(),
    )
    attrs = to_zeitgeist_attrs(answered, _envelope("DecisionInputAnswered"))
    assert "answer" not in attrs
    assert "keep it quiet" not in " ".join(attrs.values())


def test_unknown_payload_type_fails_closed() -> None:
    with pytest.raises(UnknownVolatileEventTypeError):
        to_zeitgeist_attrs(
            MissionStartedPayload(mission_id="m1", mission_type="t",
                                  initial_phase="p", actor="a"),
            _envelope("MissionStarted"),
        )
    with pytest.raises(UnknownVolatileEventTypeError):
        to_zeitgeist_attrs("not even a model", _envelope("WPStatusChanged"))  # type: ignore[arg-type]


def test_oversize_value_raises_rather_than_truncating() -> None:
    payload = MissionClosedPayload(mission_slug="s" * 241, mission_number=1,
                                   mission_type="software-dev")
    with pytest.raises(ZeitgeistAttrsOverflowError):
        to_zeitgeist_attrs(payload, _envelope("MissionClosed"))


def test_emit_rejects_lone_surrogates_with_typed_error() -> None:
    payload = _transition(actor="\ud800")
    with pytest.raises(ZeitgeistAttrsError, match="attr 'actor' value"):
        to_zeitgeist_attrs(payload, _envelope("WPStatusChanged"))


def test_key_count_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(zeitgeist_attrs, "ZEITGEIST_ATTRS_MAX_KEYS", 3)
    with pytest.raises(ZeitgeistAttrsOverflowError):
        to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))


def test_emit_refuses_a_future_field_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    """If a future vocabulary field collides with the forbidden set, encode
    refuses rather than broadcasting it."""
    monkeypatch.setattr(zeitgeist_attrs, "FORBIDDEN_ATTR_KEYS", frozenset({"wp_id"}))
    with pytest.raises(ZeitgeistAttrsForbiddenKeyError):
        to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))


def test_emit_refuses_a_forbidden_name_under_a_nested_dotted_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nested one-level projection (``<field>.<sub>``) leaking a forbidden
    name under its trailing segment is refused even though the full dotted
    string is never itself added to ``FORBIDDEN_ATTR_KEYS``
    (EXPERIMENTAL-spec-kitty-events#21)."""
    real_encode_fields = zeitgeist_attrs._encode_fields
    monkeypatch.setattr(
        zeitgeist_attrs, "_encode_fields",
        lambda *a, **k: {**real_encode_fields(*a, **k), "actor.token": "leaked"},
    )
    with pytest.raises(ZeitgeistAttrsForbiddenKeyError, match=r"actor\.token"):
        to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))


def test_unbroadcast_evidence_never_appears_in_attrs() -> None:
    from spec_kitty_events.status import DoneEvidence, RepoEvidence, ReviewVerdict

    payload = _transition(
        to_lane="done",
        from_lane="for_review",
        evidence=DoneEvidence(
            repos=[RepoEvidence(repo="r", branch="b", commit="c")],
            verification=[], review=ReviewVerdict(reviewer="robert", verdict="ok"),
        ),
    )
    attrs = to_zeitgeist_attrs(payload, _envelope("WPStatusChanged"))
    assert not any(key.startswith("evidence") for key in attrs)


def test_value_types_without_an_encoding_fail_closed() -> None:
    """The encoder handles str/int/bool/str-Enum/nested models only. If a
    future field introduces any other scalar (float, datetime, ...), emit
    refuses rather than guessing an encoding."""
    payload = MissionClosedPayload(mission_slug="s", mission_number=1,
                                   mission_type="software-dev")
    object.__setattr__(payload, "mission_number", 1.5)  # bypass frozen: force an exotic type
    with pytest.raises(UnencodableFieldValueError):
        to_zeitgeist_attrs(payload, _envelope("MissionClosed"))


class _NestedLeaf(BaseModel):
    label: str


class _NestedOuter(BaseModel):
    inner: _NestedLeaf


class _DoublyNestedPayload(BaseModel):
    inner_model: _NestedOuter


def test_encode_refuses_nesting_deeper_than_one_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression pin for events#22: no volatile payload nests a model inside
    a model today, so `_encode_fields`'s deeper-than-one-level guard is
    otherwise unreachable through the public API. A synthetic payload wired
    into the dispatch table exercises it directly."""
    monkeypatch.setitem(
        zeitgeist_attrs.PAYLOAD_MODEL_BY_EVENT_TYPE,
        "SyntheticDoublyNested",
        _DoublyNestedPayload,
    )
    payload = _DoublyNestedPayload(inner_model=_NestedOuter(inner=_NestedLeaf(label="x")))
    with pytest.raises(UnencodableFieldValueError, match="nesting deeper than one level"):
        to_zeitgeist_attrs(payload, _envelope("SyntheticDoublyNested"))


def test_ref_derival_and_mismatch_fail_closed() -> None:
    assert zeitgeist_ref_for("WPStatusChanged", _transition()) == "demo-mission"
    with pytest.raises(UnknownVolatileEventTypeError):
        zeitgeist_ref_for("MissionClosed", _transition())


def test_phase_entered_ref_derives_from_mission_id_when_slug_is_absent() -> None:
    """mission_slug is optional display/back-compat; mission_id is the
    identity (PhaseEnteredPayload's own field description). A valid payload
    without the compat field must still yield a ref."""
    payload = PhaseEnteredPayload(
        mission_id="mission-demo", phase_name="build", actor="robert",
        mission_slug=None,
    )
    assert zeitgeist_ref_for("PhaseEntered", payload) == "mission-demo"


def test_phase_entered_ref_ignores_mission_slug_when_present() -> None:
    """mission_id is the identity regardless of the compat field's value —
    ref derivation does not silently prefer the display slug."""
    payload = PhaseEnteredPayload(
        mission_id="mission-demo", phase_name="build", actor="robert",
        mission_slug="a-totally-different-slug",
    )
    assert zeitgeist_ref_for("PhaseEntered", payload) == "mission-demo"


def test_ref_over_bound_raises_rather_than_emitting_unbounded() -> None:
    """The module documents the frame ref as carrying the same ≤240-byte
    bound as an attrs entry independently of attrs; zeitgeist_ref_for must
    enforce it, not just to_zeitgeist_attrs."""
    payload = _transition(mission_slug="s" * 241)
    with pytest.raises(ZeitgeistAttrsOverflowError):
        zeitgeist_ref_for("WPStatusChanged", payload)


def test_ref_derival_admits_a_multibyte_value_within_the_stricter_byte_bound() -> None:
    """Mirrors test_encode_admits_a_multibyte_value_within_the_stricter_byte_bound:
    a multi-byte ref that fits under the byte bound must still be returned."""
    payload = _transition(mission_slug="é" * 100)
    assert zeitgeist_ref_for("WPStatusChanged", payload) == "é" * 100


def test_ref_derival_rejects_multibyte_over_the_byte_bound_though_under_240_chars() -> None:
    """Mirrors test_encode_rejects_a_multibyte_value_over_the_byte_bound_though_under_240_chars:
    the ASCII-only ``"s" * 241`` case above cannot distinguish a UTF-8-byte
    bound from a character-count bound (spec-kitty-events#70) — this pins
    the byte semantics zeitgeist_ref_for's docstring claims."""
    value = "é" * 121  # 121 characters, 242 UTF-8 bytes
    assert len(value) <= 240
    assert len(value.encode("utf-8")) > ZEITGEIST_ATTRS_MAX_BYTES
    payload = _transition(mission_slug=value)
    with pytest.raises(ZeitgeistAttrsOverflowError):
        zeitgeist_ref_for("WPStatusChanged", payload)


def test_bounds_constants_match_the_zeitgeist_frame_contract() -> None:
    assert ZEITGEIST_ATTRS_MAX_KEYS == 16
    assert ZEITGEIST_ATTRS_MAX_BYTES == 240
    assert ZEITGEIST_ATTR_KEY_MAX_CHARS == 64


def test_encode_rejects_a_key_over_the_64_char_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression pin for spec-kitty-events#16: a >64-char key must not
    reach the wire, even though it is well under the 240-byte value bound
    the old combined scan checked it against."""
    monkeypatch.setattr(
        zeitgeist_attrs, "_encode_fields", lambda *a, **k: {"a" * 65: "v"}
    )
    with pytest.raises(ZeitgeistAttrsOverflowError):
        to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))


def test_encode_admits_a_multibyte_value_within_the_stricter_byte_bound() -> None:
    """Encode's byte bound is intentionally stricter than the relay's
    240-character bound (spec-kitty-events#16); a multi-byte value that
    fits under both must still encode."""
    payload = MissionClosedPayload(
        mission_slug="é" * 100, mission_number=1, mission_type="software-dev"
    )
    attrs = to_zeitgeist_attrs(payload, _envelope("MissionClosed"))
    assert attrs["mission_slug"] == "é" * 100


def test_encode_rejects_a_multibyte_value_over_the_byte_bound_though_under_240_chars() -> None:
    """The stricter 240-UTF-8-byte encode bound can reject a value that is
    within the relay's true 240-*character* bound — over-rejecting here is
    the accepted safe side of spec-kitty-events#16."""
    value = "é" * 121  # 121 characters, 242 UTF-8 bytes
    assert len(value) <= 240
    assert len(value.encode("utf-8")) > ZEITGEIST_ATTRS_MAX_BYTES
    payload = MissionClosedPayload(
        mission_slug=value, mission_number=1, mission_type="software-dev"
    )
    with pytest.raises(ZeitgeistAttrsOverflowError):
        to_zeitgeist_attrs(payload, _envelope("MissionClosed"))


# ── decode ───────────────────────────────────────────────────────────────────


def test_decode_returns_the_validated_moment() -> None:
    payload = _transition(from_lane="planned")
    attrs = to_zeitgeist_attrs(payload, _envelope("WPStatusChanged"))
    moment = from_zeitgeist_attrs("WPStatusChanged", attrs)
    assert moment == VolatileMoment(kind="WPStatusChanged", ref="demo-mission",
                                    attrs=dict(attrs))


def test_decode_admits_envelope_identity_attrs() -> None:
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    moment = from_zeitgeist_attrs("WPStatusChanged", attrs)
    assert moment.attrs["event_id"] == _EVENT_ID
    assert moment.attrs["occurred_at"] == "2026-08-25T09:00:00+00:00"


def test_decode_rejects_malformed_occurred_at() -> None:
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["occurred_at"] = "yesterday"
    with pytest.raises(ZeitgeistAttrsError, match="occurred_at"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_empty_event_id() -> None:
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["event_id"] = ""
    with pytest.raises(ZeitgeistAttrsError, match="event_id"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


@pytest.mark.parametrize(
    "bad_event_id", ["x", "not-a-ulid", "../../etc/passwd", "I" * 26]
)
def test_decode_rejects_an_event_id_that_is_not_a_ulid_or_uuid(
    bad_event_id: str,
) -> None:
    """spec-kitty-events#62: the envelope's own contract
    (``normalize_event_id``) requires a 26-char Crockford-base32 ULID, a
    36-char hyphenated UUID, or a 32-char bare hex UUID; decode must reject
    anything else rather than admit an undedupable moment."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["event_id"] = bad_event_id
    with pytest.raises(ZeitgeistAttrsError, match="event_id"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_canonicalizes_event_id_case() -> None:
    """Two spellings of the same ULID must decode to the same canonical
    ``event_id`` so ``(team, event_id)`` dedup actually dedupes
    (spec-kitty-events#62)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["event_id"] = _EVENT_ID.lower()
    moment = from_zeitgeist_attrs("WPStatusChanged", attrs)
    assert moment.attrs["event_id"] == _EVENT_ID


def test_decode_rejects_a_timezone_naive_occurred_at() -> None:
    """spec-kitty-events#62: the encoder only ever emits an aware
    ``datetime``'s ``isoformat()``; a naive value would make every
    comparison against an aware "now" (the 72-hour feed window, the
    staleness guard) raise ``TypeError`` at render time instead of being
    rejected here at the codec seam."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["occurred_at"] = "2026-08-25T09:00:00"
    with pytest.raises(ZeitgeistAttrsError, match="occurred_at"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_a_bare_date_occurred_at() -> None:
    """A date-only string parses via ``datetime.fromisoformat`` but is
    timezone-naive, so it is rejected same as any other naive value
    (spec-kitty-events#62 — this supersedes the prior deliberate accept)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["occurred_at"] = "2026-08-25"
    with pytest.raises(ZeitgeistAttrsError, match="occurred_at"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_accepts_a_timezone_aware_occurred_at_with_nonzero_offset() -> None:
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["occurred_at"] = "2026-08-25T09:00:00-05:00"
    moment = from_zeitgeist_attrs("WPStatusChanged", attrs)
    assert moment.attrs["occurred_at"] == "2026-08-25T09:00:00-05:00"


def test_decode_rejects_unknown_keys() -> None:
    with pytest.raises(ZeitgeistAttrsError):
        from_zeitgeist_attrs("WPStatusChanged", {"not_in_schema": "x"})


def test_decode_rejects_non_string_values() -> None:
    with pytest.raises(ZeitgeistAttrsError):
        from_zeitgeist_attrs("MissionClosed", {"mission_number": 12})  # type: ignore[dict-item]


def test_decode_rejects_oversize_values() -> None:
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "r" * 241
    with pytest.raises(ZeitgeistAttrsOverflowError):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_lone_surrogates_with_typed_error() -> None:
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "\ud800"
    with pytest.raises(ZeitgeistAttrsError, match="attr 'actor' value"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_a_newline_in_a_value_with_typed_error() -> None:
    """A bare LF/CR could forge extra frame lines for whatever renders the
    moment next (issue #25, lens: security)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "actor\nrumor: fake status line"
    with pytest.raises(ZeitgeistAttrsControlCharacterError, match="attr 'actor' value"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_an_ansi_escape_in_a_value_with_typed_error() -> None:
    """A bare ESC could smuggle ANSI into whatever terminal or log renders
    the moment next (issue #25, lens: security)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "\x1b[31mactor\x1b[0m"
    with pytest.raises(ZeitgeistAttrsControlCharacterError, match="attr 'actor' value"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_a_c1_next_line_control_with_typed_error() -> None:
    """``U+0085`` NEL is a C1 control, outside the C0+DEL range #25 covered
    but inside zeitgeist's ``clean_field`` ``isprintable()`` doctrine
    (issue #63)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "actor\x85rumor"
    with pytest.raises(ZeitgeistAttrsControlCharacterError, match="attr 'actor' value"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_a_c1_csi_introducer_with_typed_error() -> None:
    """``U+009B`` CSI is a C1 control that xterm-family terminals in UTF-8
    mode can interpret as a bare ANSI CSI introducer — the same
    ANSI-smuggling shape ESC carries, without ever using ``U+001B``
    (issue #63)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "\x9b[31mactor"
    with pytest.raises(ZeitgeistAttrsControlCharacterError, match="attr 'actor' value"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_a_unicode_line_separator_with_typed_error() -> None:
    """``U+2028`` LINE SEPARATOR is a line terminator in JavaScript source
    and several log/JSONL readers — the "forge an extra line" shape one
    encoding up from a bare LF (issue #63)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "actor rumor: fake status line"
    with pytest.raises(ZeitgeistAttrsControlCharacterError, match="attr 'actor' value"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_a_unicode_paragraph_separator_with_typed_error() -> None:
    """``U+2029`` PARAGRAPH SEPARATOR, same family as ``U+2028`` (issue
    #63)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "actor rumor"
    with pytest.raises(ZeitgeistAttrsControlCharacterError, match="attr 'actor' value"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_a_right_to_left_override_with_typed_error() -> None:
    """``U+202E`` RIGHT-TO-LEFT OVERRIDE is the trojan-source shape: rendered
    text reads differently from the stored bytes, in a field whose whole
    job is to say who did something (issue #63)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "actor‮rumor"
    with pytest.raises(ZeitgeistAttrsControlCharacterError, match="attr 'actor' value"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_a_zero_width_space_with_typed_error() -> None:
    """``U+200B`` ZERO WIDTH SPACE is an invisible ``Cf``-adjacent formatting
    character that ``isprintable()`` also rejects (issue #63)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "actor​rumor"
    with pytest.raises(ZeitgeistAttrsControlCharacterError, match="attr 'actor' value"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_admits_an_ordinary_space_and_printable_unicode() -> None:
    """Space is printable, so ordinary values with plain spaces and
    printable non-ASCII text are unaffected by the widened check (issue
    #63)."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    attrs["actor"] = "a name with spaces café"
    moment = from_zeitgeist_attrs("WPStatusChanged", attrs)
    assert moment.attrs["actor"] == "a name with spaces café"


def test_decode_admits_a_multibyte_value_within_the_byte_bound() -> None:
    """A multi-byte value that fits the relay's 240-UTF-8-byte bound (and
    therefore also its 240-character bound, since bytes >= chars) decodes."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    value = "é" * 100  # 100 characters, 200 UTF-8 bytes — relay-valid
    assert len(value.encode("utf-8")) <= ZEITGEIST_ATTRS_MAX_BYTES
    attrs["actor"] = value
    moment = from_zeitgeist_attrs("WPStatusChanged", attrs)
    assert moment.attrs["actor"] == value


def test_decode_rejects_a_multibyte_value_over_the_byte_bound_though_under_240_chars() -> None:
    """spec-kitty-events#16: the relay's `EventArgs` schema bounds values by
    UTF-8 bytes (`maxUtf8Bytes: 240`) *and* by characters (`maxLength: 240`)
    independently (zeitgeist commit 30d3ab4415, closing zeitgeist#20), so a
    value at 121 characters / 242 UTF-8 bytes is relay-*invalid* — decode
    must reject it, matching encode's already-correct byte bound."""
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    value = "é" * 121  # 121 characters, 242 UTF-8 bytes — relay-invalid
    assert len(value) <= 240
    assert len(value.encode("utf-8")) > ZEITGEIST_ATTRS_MAX_BYTES
    attrs["actor"] = value
    with pytest.raises(ZeitgeistAttrsOverflowError):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_a_key_over_the_64_char_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_key = "a" * 65
    monkeypatch.setattr(
        zeitgeist_attrs, "_ALLOWED_KEYS_BY_EVENT_TYPE",
        dict(zeitgeist_attrs._ALLOWED_KEYS_BY_EVENT_TYPE),
    )
    monkeypatch.setitem(
        zeitgeist_attrs._ALLOWED_KEYS_BY_EVENT_TYPE,
        "WPStatusChanged",
        frozenset({long_key}),
    )
    with pytest.raises(ZeitgeistAttrsOverflowError):
        from_zeitgeist_attrs("WPStatusChanged", {long_key: "v"})


def test_decode_rejects_unknown_event_type() -> None:
    with pytest.raises(UnknownVolatileEventTypeError):
        from_zeitgeist_attrs("MissionStarted", {"mission_id": "m1"})


def test_decode_forbidden_guard_wins_when_a_key_is_schema_legal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defense-in-depth ordering: even if the closed key set ever admitted a
    forbidden name, the forbidden-key check still refuses it."""
    monkeypatch.setitem(
        zeitgeist_attrs._ALLOWED_KEYS_BY_EVENT_TYPE, "MissionClosed", frozenset({"team"})
    )
    with pytest.raises(ZeitgeistAttrsForbiddenKeyError):
        from_zeitgeist_attrs("MissionClosed", {"team": "t"})


def test_decode_forbidden_guard_catches_a_nested_dotted_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Symmetric with the encode-side check: an inbound dotted key whose
    trailing segment is forbidden is refused even if the closed schema for
    the kind admits the full dotted string (EXPERIMENTAL-spec-kitty-events#21)."""
    monkeypatch.setitem(
        zeitgeist_attrs._ALLOWED_KEYS_BY_EVENT_TYPE, "MissionClosed", frozenset({"actor.token"})
    )
    with pytest.raises(ZeitgeistAttrsForbiddenKeyError, match=r"actor\.token"):
        from_zeitgeist_attrs("MissionClosed", {"actor.token": "t"})


def test_decode_key_count_overflow_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decode-side bound: more entries than the frame allows never decode,
    regardless of how small each one is."""
    monkeypatch.setattr(zeitgeist_attrs, "_ALLOWED_KEYS_BY_EVENT_TYPE",
                        dict(zeitgeist_attrs._ALLOWED_KEYS_BY_EVENT_TYPE))
    monkeypatch.setitem(
        zeitgeist_attrs._ALLOWED_KEYS_BY_EVENT_TYPE,
        "WPStatusChanged",
        frozenset({f"k{i}" for i in range(20)}),
    )
    attrs = {f"k{i}": "v" for i in range(zeitgeist_attrs.ZEITGEIST_ATTRS_MAX_KEYS + 1)}
    with pytest.raises(ZeitgeistAttrsOverflowError):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_rejects_structurally_incomplete_attrs() -> None:
    """Regression pin (events#19): every kind here has a required ref field
    on emit, so an empty mapping is not a moment `to_zeitgeist_attrs` could
    ever have produced and must not decode as one."""
    with pytest.raises(ZeitgeistAttrsError):
        from_zeitgeist_attrs("MissionClosed", {})


def test_decode_rejects_a_schema_legal_subset_missing_required_keys() -> None:
    """events#19: `{"to_lane": "done"}` is a legal key/value pair for
    WPStatusChanged but omits mission_slug/wp_id/actor/execution_mode/force/
    event_id/occurred_at, none of which to_zeitgeist_attrs ever omits."""
    with pytest.raises(ZeitgeistAttrsError, match="missing keys"):
        from_zeitgeist_attrs("WPStatusChanged", {"to_lane": "done"})


def test_decode_requires_the_ref_key_when_the_family_guarantees_one() -> None:
    attrs = to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged"))
    del attrs["mission_slug"]
    with pytest.raises(ZeitgeistAttrsError, match="missing keys"):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


def test_decode_tolerates_the_optional_compat_field_absent_and_still_derives_ref() -> None:
    """PhaseEntered's ``mission_slug`` is a genuinely optional back-compat
    field, unlike ``mission_id`` (the required ref field), so decode must
    not require its presence -- but ref still resolves via ``mission_id``,
    not ``None``."""
    from spec_kitty_events.lifecycle import PhaseEnteredPayload

    payload = PhaseEnteredPayload(
        mission_id="mission-demo", phase_name="build", actor="robert"
    )
    attrs = to_zeitgeist_attrs(payload, _envelope("PhaseEntered"))
    assert "mission_slug" not in attrs
    moment = from_zeitgeist_attrs("PhaseEntered", attrs)
    assert moment.ref == "mission-demo"


def test_required_keys_exclude_optional_typed_fields_pydantic_still_requires() -> None:
    """MissionCreatedPayload.mission_number is `Optional[int] = Field(...)`:
    pydantic requires the kwarg be passed, but the payload may still pass
    None, in which case to_zeitgeist_attrs omits the key. Decode must not
    require a key that a legitimate encode can omit."""
    assert "mission_number" not in zeitgeist_attrs._REQUIRED_KEYS_BY_EVENT_TYPE["MissionCreated"]
    assert "mission_slug" in zeitgeist_attrs._REQUIRED_KEYS_BY_EVENT_TYPE["MissionCreated"]


def test_moment_is_frozen() -> None:
    moment = from_zeitgeist_attrs(
        "WPStatusChanged",
        to_zeitgeist_attrs(_transition(), _envelope("WPStatusChanged")),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        moment.kind = "MissionClosed"  # type: ignore[misc]
