"""Conformance tests for the volatile-family zeitgeist attrs codecs (E2).

Wires the ``zeitgeist_attrs`` fixture category into the package's established
fixture-plant architecture (``conformance/fixtures/<category>/{valid,invalid}``
+ ``manifest.json`` + ``load_fixtures()``), mirroring
``tests/test_harness_observation_conformance.py``.

Each *valid* fixture pins both directions of the codec against committed
bytes: ``to`` projects the payload onto the exact golden attrs, and ``from``
validates those same attrs back into a :class:`VolatileMoment`. Each
*invalid* fixture pins one rejection with its exception class named in the
fixture document (``direction`` says which side of the codec it exercises).
"""

from __future__ import annotations

import importlib
from datetime import datetime
from uuid import UUID

import pytest

from spec_kitty_events.conformance import validate_event
from spec_kitty_events.conformance.loader import FixtureCase, load_fixtures
from spec_kitty_events.decisionpoint import (
    DECISION_POINT_OPENED,
    DECISION_POINT_RESOLVED,
    DecisionPointOpenedPayload,
    DecisionPointResolvedPayload,
)
from spec_kitty_events.lifecycle import MissionClosedPayload, MissionStartedPayload
from spec_kitty_events.models import Event
from spec_kitty_events.zeitgeist_attrs import (
    PAYLOAD_MODEL_BY_EVENT_TYPE,
    UnencodableFieldValueError,
    UnknownVolatileEventTypeError,
    VolatileMoment,
    ZeitgeistAttrsError,
    ZeitgeistAttrsForbiddenKeyError,
    _ALLOWED_KEYS_BY_EVENT_TYPE,
    from_zeitgeist_attrs,
    to_zeitgeist_attrs,
    zeitgeist_ref_for,
)

# The discriminated-union event types register a tuple of variant models in
# PAYLOAD_MODEL_BY_EVENT_TYPE (decode cannot know which variant produced a
# frame, so both must be schema-legal); fixtures still need one concrete
# payload instance, built through decisionpoint.py's own discriminating
# factory callables rather than calling the tuple directly.
_PAYLOAD_FACTORY_BY_EVENT_TYPE = {
    DECISION_POINT_OPENED: DecisionPointOpenedPayload,
    DECISION_POINT_RESOLVED: DecisionPointResolvedPayload,
    # MissionStarted has no zeitgeist-attrs codec at all; the
    # mission_started_unknown_type fixture needs a real payload instance to
    # feed to_zeitgeist_attrs so it can demonstrate the reverse-lookup
    # rejection (events#22).
    "MissionStarted": MissionStartedPayload,
}


def _build_payload(event_type: str, fields: dict):
    factory = _PAYLOAD_FACTORY_BY_EVENT_TYPE.get(event_type)
    if factory is not None:
        return factory(**fields)
    return PAYLOAD_MODEL_BY_EVENT_TYPE[event_type](**fields)


_ERROR_CLASSES = {
    "UnknownVolatileEventTypeError": UnknownVolatileEventTypeError,
    "ZeitgeistAttrsError": ZeitgeistAttrsError,
    "ZeitgeistAttrsOverflowError": importlib.import_module(
        "spec_kitty_events.zeitgeist_attrs"
    ).ZeitgeistAttrsOverflowError,
}

# Constants for the envelope fields the fixture documents do not vary: only
# event_id and timestamp affect the projection, so the rest are fixed.
_FIXTURE_BUILD_ID = "build-zeitgeist-attrs-conformance"
_FIXTURE_NODE_ID = "node-conformance"
_FIXTURE_PROJECT_UUID = UUID("550e8400-e29b-41d4-a716-446655440000")


def _fixture_envelope(event_type: str, case: dict) -> Event:
    """Build the journal envelope a fixture document declares."""
    envelope = case["envelope"]
    return Event(
        event_id=envelope["event_id"],
        event_type=event_type,
        aggregate_id=f"agg-{case.get('expected_ref', 'conformance')}",
        timestamp=datetime.fromisoformat(envelope["timestamp"]),
        build_id=_FIXTURE_BUILD_ID,
        node_id=_FIXTURE_NODE_ID,
        lamport_clock=1,
        project_uuid=_FIXTURE_PROJECT_UUID,
        correlation_id=envelope["event_id"],
    )


@pytest.fixture
def zeitgeist_attrs_fixtures():
    return load_fixtures("zeitgeist_attrs")


def test_fixtures_loaded(zeitgeist_attrs_fixtures) -> None:
    """28 valid + 8 invalid fixtures are on disk and manifest-registered."""
    assert len(zeitgeist_attrs_fixtures) == 36
    assert len([f for f in zeitgeist_attrs_fixtures if f.expected_valid]) == 28
    assert len([f for f in zeitgeist_attrs_fixtures if not f.expected_valid]) == 8


def test_fixture_event_ids_are_unique(zeitgeist_attrs_fixtures) -> None:
    """No two fixtures may share an envelope/attrs ``event_id``.

    Team Kitty deduplicates moments on ``(team, event_id)``; a fixture-id
    clash is harmless to load but would silently collapse two distinct
    moments if this directory were ever replayed through that reducer
    (issue #73).
    """
    seen: dict[str, str] = {}
    for fixture in zeitgeist_attrs_fixtures:
        case = fixture.payload
        event_id = (case.get("envelope") or case.get("attrs") or {}).get("event_id")
        if event_id is None:
            continue
        if event_id in seen:
            raise AssertionError(
                f"event_id {event_id!r} used by both {seen[event_id]!r} and {fixture.id!r}"
            )
        seen[event_id] = fixture.id


def test_every_valid_fixture_covers_one_volatile_event_type(
    zeitgeist_attrs_fixtures,
) -> None:
    valid_types = {f.event_type for f in zeitgeist_attrs_fixtures if f.expected_valid}
    assert valid_types == set(PAYLOAD_MODEL_BY_EVENT_TYPE)


def test_codec_fixtures_stay_out_of_the_packaged_event_gate() -> None:
    """In-repo mirror of the packaged gate's own regression guard.

    ``conformance/test_pyargs_entrypoint.py`` guards its ``zeitgeist_attrs``
    exclusion with ``test_zeitgeist_attrs_codec_fixtures_stay_out_of_the_
    event_gate``, but ``pyproject.toml`` sets ``testpaths = ["tests"]``, so
    neither this suite nor CI ever collects that module: a regression in its
    two filter lines would leave every in-repo run green while ``pytest
    --pyargs spec_kitty_events.conformance`` fails every codec entry for
    every downstream consumer. Importing the packaged module's collector and
    pinning the same two facts here puts the guard where it is watched.
    """
    from spec_kitty_events.conformance.test_pyargs_entrypoint import (
        _MANIFEST,
        _event_fixture_entries,
    )

    manifest_paths = {
        f["path"] for f in _MANIFEST["fixtures"] if f["path"].startswith("zeitgeist_attrs/")
    }
    assert manifest_paths, (
        "zeitgeist_attrs codec fixtures vanished from the manifest; if the "
        "category was renamed on purpose, update this guard with it"
    )
    leaked = sorted(
        f["path"] for f in _event_fixture_entries() if f["path"].startswith("zeitgeist_attrs/")
    )
    assert not leaked, (
        "codec fixtures reached the packaged event gate; validating them as "
        "envelopes turns pytest --pyargs spec_kitty_events.conformance red "
        f"for every consumer: {leaked}"
    )


def test_packaged_event_gate_fixture_entries_match_manifest_expectations() -> None:
    """Mirror the packaged event gate inside the default in-repo test suite."""
    from spec_kitty_events.conformance.test_pyargs_entrypoint import (
        _event_fixture_params,
    )

    failures: list[str] = []
    for case in _event_fixture_params():
        result = validate_event(case["payload"], case["event_type"])
        if case["expected_result"] == "valid" and result.model_violations:
            violations = "; ".join(f"{v.field}: {v.message}" for v in result.model_violations)
            failures.append(f"{case['id']} unexpectedly failed: {violations}")
        elif case["expected_result"] == "invalid" and result.valid:
            failures.append(f"{case['id']} unexpectedly passed")

    assert not failures


@pytest.mark.parametrize(
    "fixture",
    [
        f
        for f in load_fixtures("zeitgeist_attrs")
        if f.expected_valid and f.event_type == "WPStatusChanged"
    ],
    ids=lambda f: f.id,
)
def test_wp_status_changed_fixtures_pass_strict_domain_validation(
    fixture: FixtureCase,
) -> None:
    """Every WPStatusChanged codec golden also passes domain transition rules.

    A codec fixture is deliberately excluded from the packaged event gate
    (``test_codec_fixtures_stay_out_of_the_packaged_event_gate`` above), so
    nothing enforces this today — but a payload that no conforming producer
    could ever emit is a latent trap for the next person who wires this
    category into ``validate_event``. Pinned here so a fixture can never
    regress back to one (events#30).
    """
    case = fixture.payload
    result = validate_event(
        {"event_type": fixture.event_type, "payload": case["payload"]},
        fixture.event_type,
        strict=True,
    )
    assert result.valid, (
        f"{fixture.id} pins a payload that fails strict domain validation: "
        f"{[v.message for v in result.model_violations]}"
    )


@pytest.mark.parametrize(
    "fixture",
    [f for f in load_fixtures("zeitgeist_attrs") if f.expected_valid],
    ids=lambda f: f.id,
)
def test_zeitgeist_attrs_both_directions(fixture: FixtureCase) -> None:
    """Golden attrs pin the projection; the decode validates them back."""
    case = fixture.payload
    payload = _build_payload(fixture.event_type, case["payload"])
    envelope = _fixture_envelope(fixture.event_type, case)

    # to-direction: bounded projection matches the committed bytes exactly.
    attrs = to_zeitgeist_attrs(payload, envelope)
    assert attrs == case["expected_attrs"]
    assert zeitgeist_ref_for(fixture.event_type, payload) == case["expected_ref"]

    # from-direction: the same attrs validate into the typed moment view.
    moment = from_zeitgeist_attrs(fixture.event_type, case["expected_attrs"])
    assert isinstance(moment, VolatileMoment)
    assert moment == VolatileMoment(
        kind=fixture.event_type,
        ref=case["expected_ref"],
        attrs=case["expected_attrs"],
    )


@pytest.mark.parametrize(
    "fixture",
    [f for f in load_fixtures("zeitgeist_attrs") if not f.expected_valid],
    ids=lambda f: f.id,
)
def test_zeitgeist_attrs_rejections(fixture: FixtureCase) -> None:
    case = fixture.payload
    expected_error = _ERROR_CLASSES[case["expected_error"]]
    if case["direction"] == "to":
        payload = _build_payload(fixture.event_type, case["payload"])
        envelope = _fixture_envelope(fixture.event_type, case)
        with pytest.raises(expected_error):
            to_zeitgeist_attrs(payload, envelope)
    else:
        assert case["direction"] == "from"
        with pytest.raises(expected_error):
            from_zeitgeist_attrs(fixture.event_type, case["attrs"])


def test_decode_rejects_a_forbidden_key_even_when_schema_legal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forbidden-key-on-ingest (events#22) is not expressible as a JSON
    fixture: every real schema's allowed-key set is already disjoint from
    ``FORBIDDEN_ATTR_KEYS``, so triggering the guard requires monkeypatching
    ``_ALLOWED_KEYS_BY_EVENT_TYPE`` to admit a forbidden name first.
    """
    monkeypatch.setitem(_ALLOWED_KEYS_BY_EVENT_TYPE, "MissionClosed", frozenset({"team"}))
    with pytest.raises(ZeitgeistAttrsForbiddenKeyError):
        from_zeitgeist_attrs("MissionClosed", {"team": "t"})


def test_encode_rejects_an_unencodable_scalar() -> None:
    """Unencodable-scalar (events#22) is not expressible as a JSON fixture:
    every volatile payload model is frozen and schema-validated, so no
    fixture-built payload can carry a field value outside str/int/bool/str-Enum.
    Forcing one on requires bypassing the frozen model with
    ``object.__setattr__``, mirroring the unit-level regression pin.
    """
    payload = MissionClosedPayload(mission_slug="s", mission_number=1, mission_type="software-dev")
    object.__setattr__(payload, "mission_number", 1.5)
    envelope = _fixture_envelope(
        "MissionClosed",
        {
            "envelope": {
                "event_id": "e2e00000-0000-4000-8000-000000000118",
                "timestamp": "2026-08-25T09:00:00+00:00",
            }
        },
    )
    with pytest.raises(UnencodableFieldValueError):
        to_zeitgeist_attrs(payload, envelope)
