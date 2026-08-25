"""Unit tests for the zeitgeist attrs codecs (E2)."""

from __future__ import annotations

import dataclasses

import pytest

from spec_kitty_events import zeitgeist_attrs
from spec_kitty_events.forbidden_keys import FORBIDDEN_LEGACY_KEYS
from spec_kitty_events.lifecycle import (
    MissionClosedPayload,
    MissionCreatedPayload,
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
)
from spec_kitty_events.status import StatusTransitionPayload
from spec_kitty_events.zeitgeist_attrs import (
    FORBIDDEN_ATTR_KEYS,
    PAYLOAD_MODEL_BY_EVENT_TYPE,
    REF_FIELD_BY_EVENT_TYPE,
    UNBROADCAST_FIELDS,
    VOLATILE_EVENT_TYPES,
    ZEITGEIST_ATTRS_MAX_BYTES,
    ZEITGEIST_ATTRS_MAX_KEYS,
    ZEITGEIST_FORBIDDEN_KEYS_V1,
    UnknownVolatileEventTypeError,
    UnencodableFieldValueError,
    VolatileMoment,
    ZeitgeistAttrsError,
    ZeitgeistAttrsForbiddenKeyError,
    ZeitgeistAttrsOverflowError,
    from_zeitgeist_attrs,
    to_zeitgeist_attrs,
    zeitgeist_ref_for,
)


def _transition(**overrides) -> StatusTransitionPayload:
    fields = dict(
        mission_slug="demo-mission",
        wp_id="WP01",
        to_lane="doing",
        actor="robert",
        execution_mode="worktree",
    )
    fields.update(overrides)
    return StatusTransitionPayload(**fields)


# ── closed vocabulary ────────────────────────────────────────────────────────


def test_volatile_vocabulary_is_the_ephemeral_design_set() -> None:
    assert VOLATILE_EVENT_TYPES == {
        "WPStatusChanged", "MissionCreated", "MissionClosed", "PhaseEntered",
        "MissionRunStarted", "NextStepIssued", "NextStepAutoCompleted",
        "DecisionInputRequested", "DecisionInputAnswered", "MissionRunCompleted",
    }


def test_dispatch_table_covers_exactly_the_volatile_types() -> None:
    assert set(PAYLOAD_MODEL_BY_EVENT_TYPE) == VOLATILE_EVENT_TYPES


def test_every_ref_field_is_a_declared_field_of_its_model() -> None:
    for event_type, ref_field in REF_FIELD_BY_EVENT_TYPE.items():
        model = PAYLOAD_MODEL_BY_EVENT_TYPE[event_type]
        assert ref_field in model.model_fields, event_type


def test_unbroadcast_fields_exist_on_their_models() -> None:
    """The skip lists cannot silently rot when a payload is renamed."""
    for event_type, fields in UNBROADCAST_FIELDS.items():
        model = PAYLOAD_MODEL_BY_EVENT_TYPE[event_type]
        for name in fields:
            assert name in model.model_fields, (event_type, name)


def test_forbidden_keys_union_the_zeitgeist_mirror_and_legacy_set() -> None:
    assert FORBIDDEN_ATTR_KEYS == ZEITGEIST_FORBIDDEN_KEYS_V1 | FORBIDDEN_LEGACY_KEYS


def test_no_declared_field_name_is_forbidden() -> None:
    """Structural guarantee behind "never emit forbidden keys": today's
    vocabulary cannot collide; if a future field does, this fails first."""
    for model in PAYLOAD_MODEL_BY_EVENT_TYPE.values():
        for name in model.model_fields:
            assert name not in FORBIDDEN_ATTR_KEYS, (model.__name__, name)


# ── encode ───────────────────────────────────────────────────────────────────


def test_projection_is_deterministic() -> None:
    first = to_zeitgeist_attrs(_transition())
    second = to_zeitgeist_attrs(_transition())
    assert first == second
    assert list(first) == list(second)


def test_absent_optionals_emit_no_key() -> None:
    attrs = to_zeitgeist_attrs(_transition())
    assert "from_lane" not in attrs
    assert "reason" not in attrs


def test_structured_actor_projects_to_actor_label() -> None:
    structured = _transition(actor={"role": "implementer", "profile": "ox"})
    plain = _transition(actor=structured.actor_label)
    assert to_zeitgeist_attrs(structured)["actor"] == structured.actor_label
    assert to_zeitgeist_attrs(plain)["actor"] == structured.actor_label


def test_nested_actor_flattens_with_dotted_keys() -> None:
    from spec_kitty_events.mission_next import RuntimeActorIdentity

    payload = MissionRunStartedPayload(
        run_id="run-01",
        mission_type="software-dev",
        actor=RuntimeActorIdentity(actor_id="a1", actor_type="llm"),
    )
    attrs = to_zeitgeist_attrs(payload)
    assert attrs["actor.actor_id"] == "a1"
    assert attrs["actor.actor_type"] == "llm"
    # defaulted (empty-string) identity fields ride; absent optionals do not
    assert attrs["actor.display_name"] == ""
    assert "actor.provider" not in attrs


def test_unknown_payload_type_fails_closed() -> None:
    with pytest.raises(UnknownVolatileEventTypeError):
        to_zeitgeist_attrs(MissionStartedPayload(mission_id="m1", mission_type="t",
                                                 initial_phase="p", actor="a"))
    with pytest.raises(UnknownVolatileEventTypeError):
        to_zeitgeist_attrs("not even a model")  # type: ignore[arg-type]


def test_oversize_value_raises_rather_than_truncating() -> None:
    payload = MissionClosedPayload(mission_slug="s" * 241, mission_number=1,
                                   mission_type="software-dev")
    with pytest.raises(ZeitgeistAttrsOverflowError):
        to_zeitgeist_attrs(payload)


def test_key_count_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(zeitgeist_attrs, "ZEITGEIST_ATTRS_MAX_KEYS", 3)
    with pytest.raises(ZeitgeistAttrsOverflowError):
        to_zeitgeist_attrs(_transition())


def test_emit_refuses_a_future_field_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    """If a future vocabulary field collides with the forbidden set, encode
    refuses rather than broadcasting it."""
    monkeypatch.setattr(zeitgeist_attrs, "FORBIDDEN_ATTR_KEYS", frozenset({"wp_id"}))
    with pytest.raises(ZeitgeistAttrsForbiddenKeyError):
        to_zeitgeist_attrs(_transition())


def test_unbroadcast_evidence_never_appears_in_attrs() -> None:
    from spec_kitty_events.status import (
        DoneEvidence, RepoEvidence, ReviewVerdict,
    )

    payload = _transition(
        to_lane="done",
        from_lane="for_review",
        evidence=DoneEvidence(
            repos=[RepoEvidence(repo="r", branch="b", commit="c")],
            verification=[], review=ReviewVerdict(reviewer="robert", verdict="ok"),
        ),
    )
    attrs = to_zeitgeist_attrs(payload)
    assert not any(key.startswith("evidence") for key in attrs)


def test_options_are_not_broadcast() -> None:
    from spec_kitty_events.mission_next import RuntimeActorIdentity

    payload = DecisionInputRequestedPayload(
        run_id="run-01", decision_id="d1", step_id="s1", question="Ship?",
        options=("yes", "no"),
        actor=RuntimeActorIdentity(actor_id="a1", actor_type="human"),
    )
    attrs = to_zeitgeist_attrs(payload)
    assert "options" not in attrs


def test_value_types_without_an_encoding_fail_closed() -> None:
    """The encoder handles str/int/bool/str-Enum/nested models only. If a
    future field introduces any other scalar (float, datetime, ...), emit
    refuses rather than guessing an encoding."""
    payload = MissionClosedPayload(mission_slug="s", mission_number=1,
                                   mission_type="software-dev")
    object.__setattr__(payload, "mission_number", 1.5)  # bypass frozen: force an exotic type
    with pytest.raises(UnencodableFieldValueError):
        to_zeitgeist_attrs(payload)


def test_ref_derival_and_mismatch_fail_closed() -> None:
    assert zeitgeist_ref_for("WPStatusChanged", _transition()) == "demo-mission"
    with pytest.raises(UnknownVolatileEventTypeError):
        zeitgeist_ref_for("MissionClosed", _transition())


def test_bounds_constants_match_the_zeitgeist_frame_contract() -> None:
    assert ZEITGEIST_ATTRS_MAX_KEYS == 16
    assert ZEITGEIST_ATTRS_MAX_BYTES == 240


# ── decode ───────────────────────────────────────────────────────────────────


def test_decode_returns_the_validated_moment() -> None:
    payload = _transition(from_lane="planned")
    attrs = to_zeitgeist_attrs(payload)
    moment = from_zeitgeist_attrs("WPStatusChanged", attrs)
    assert moment == VolatileMoment(kind="WPStatusChanged", ref="demo-mission",
                                    attrs=dict(attrs))


def test_decode_rejects_unknown_keys() -> None:
    with pytest.raises(ZeitgeistAttrsError):
        from_zeitgeist_attrs("WPStatusChanged", {"not_in_schema": "x"})


def test_decode_rejects_non_string_values() -> None:
    with pytest.raises(ZeitgeistAttrsError):
        from_zeitgeist_attrs("MissionClosed", {"mission_number": 12})  # type: ignore[dict-item]


def test_decode_rejects_oversize_values() -> None:
    attrs = to_zeitgeist_attrs(_transition())
    attrs["actor"] = "r" * 241
    with pytest.raises(ZeitgeistAttrsOverflowError):
        from_zeitgeist_attrs("WPStatusChanged", attrs)


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


def test_moment_is_frozen() -> None:
    moment = from_zeitgeist_attrs(
        "WPStatusChanged", to_zeitgeist_attrs(_transition())
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        moment.kind = "MissionClosed"  # type: ignore[misc]
