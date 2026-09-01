"""Packaged codec runner for the ``zeitgeist_attrs`` fixture category (E2).

``test_pyargs_entrypoint.py`` deliberately excludes ``zeitgeist_attrs/``
fixtures from its generic event gate: a document there is a ``{payload,
expected_attrs, envelope?}`` codec specification, not an event envelope (see
``_event_fixture_entries``'s docstring). That exclusion's docstring claimed
"both codec directions are exercised by
``tests/test_zeitgeist_attrs_conformance.py``" -- but that module lives
under ``tests/``, which ``pyproject.toml``'s ``testpaths = ["tests"]`` never
ships in the wheel. A consumer running ``pytest --pyargs
spec_kitty_events.conformance`` collected every event-gate test and none of
the 36 ``zeitgeist_attrs/`` fixtures shipped alongside them
(spec-kitty-events#145).

This module drives the same two codec directions
(:func:`~spec_kitty_events.zeitgeist_attrs.to_zeitgeist_attrs` /
:func:`~spec_kitty_events.zeitgeist_attrs.from_zeitgeist_attrs`) through the
packaged :func:`~spec_kitty_events.conformance.loader.load_fixtures`, so the
fixtures that travel in the wheel are exercised where consumers run them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, cast
from uuid import UUID

import pytest

from spec_kitty_events.conformance.loader import FixtureCase, load_fixtures
from spec_kitty_events.decisionpoint import (
    DECISION_POINT_OPENED,
    DECISION_POINT_RESOLVED,
    DecisionPointOpenedPayload,
    DecisionPointResolvedPayload,
)
from spec_kitty_events.lifecycle import MissionStartedPayload
from spec_kitty_events.mission_next import RuntimeActorIdentity
from spec_kitty_events.models import Event
from spec_kitty_events.ops_invocation import OpsInvocationStartedPayload
from spec_kitty_events.zeitgeist_attrs import (
    PAYLOAD_MODEL_BY_EVENT_TYPE,
    UnknownContractVersionError,
    UnknownVolatileEventTypeError,
    VolatileMoment,
    ZeitgeistAttrsError,
    ZeitgeistAttrsOverflowError,
    from_zeitgeist_attrs,
    to_zeitgeist_attrs,
    zeitgeist_ref_for,
)

# The discriminated-union event types register a tuple of variant models in
# PAYLOAD_MODEL_BY_EVENT_TYPE (decode cannot know which variant produced a
# frame, so both must be schema-legal); a fixture still needs one concrete
# payload instance, built through decisionpoint.py's own discriminating
# factory callables rather than calling the tuple directly. Mirrors
# tests/test_zeitgeist_attrs_conformance.py's in-repo table.
_PAYLOAD_FACTORY_BY_EVENT_TYPE: dict[str, Callable[..., Any]] = {
    DECISION_POINT_OPENED: DecisionPointOpenedPayload,
    DECISION_POINT_RESOLVED: DecisionPointResolvedPayload,
    # MissionStarted has no zeitgeist-attrs codec at all; the
    # mission_started_unknown_type fixture needs a real payload instance to
    # feed to_zeitgeist_attrs so it can demonstrate the reverse-lookup
    # rejection (events#22).
    "MissionStarted": MissionStartedPayload,
}


def _build_payload(event_type: str, fields: dict[str, Any]) -> Any:
    factory = _PAYLOAD_FACTORY_BY_EVENT_TYPE.get(event_type)
    if factory is not None:
        return factory(**fields)
    return cast("Callable[..., Any]", PAYLOAD_MODEL_BY_EVENT_TYPE[event_type])(**fields)


_ERROR_CLASSES: dict[str, type[Exception]] = {
    "UnknownContractVersionError": UnknownContractVersionError,
    "UnknownVolatileEventTypeError": UnknownVolatileEventTypeError,
    "ZeitgeistAttrsError": ZeitgeistAttrsError,
    "ZeitgeistAttrsOverflowError": ZeitgeistAttrsOverflowError,
}

# Envelope fields the fixture documents do not vary: only event_id and
# timestamp affect the projection, so the rest are fixed.
_FIXTURE_BUILD_ID = "build-zeitgeist-attrs-codec-packaged"
_FIXTURE_NODE_ID = "node-conformance-packaged"
_FIXTURE_PROJECT_UUID = UUID("550e8400-e29b-41d4-a716-446655440000")


def _fixture_envelope(event_type: str, case: dict[str, Any]) -> Event:
    """Build the journal envelope a fixture document declares."""
    envelope = case["envelope"]
    return Event(  # type: ignore[call-arg]  # Optional Field(None, ...) defaults; runtime-verified
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


def test_zeitgeist_attrs_fixtures_present() -> None:
    """The packaged fixtures this runner depends on are actually on disk.

    Guards against the category silently going empty (e.g. a manifest
    filter regression) and this runner passing vacuously.
    """
    fixtures = load_fixtures("zeitgeist_attrs")
    assert fixtures, "zeitgeist_attrs category is empty; nothing for this runner to exercise"
    assert any(f.expected_valid for f in fixtures)
    assert any(not f.expected_valid for f in fixtures)


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


def test_decode_rewrites_derived_detail_ref_to_canonical_event_id() -> None:
    """A noncanonical but self-consistent wire frame decodes consistently.

    ``event_id`` is canonicalized on decode, so the derived ``detail_ref``
    must follow it rather than preserving the wire spelling (events#223).
    """
    event_id = "E2E00000-0000-4000-8000-900000000022"
    payload = OpsInvocationStartedPayload(  # type: ignore[call-arg]  # Optional Field(None, ...) defaults
        invocation_id="inv-01",
        action="team.provision",
        actor=RuntimeActorIdentity(actor_id="svc-1", actor_type="service"),  # type: ignore[call-arg]
        scope="team-01",
        contract_version=1,
    )
    envelope = _fixture_envelope(
        "OpsInvocationStarted",
        {"envelope": {"event_id": event_id, "timestamp": "2026-08-25T09:00:00+00:00"}},
    )
    attrs = to_zeitgeist_attrs(payload, envelope)
    attrs["event_id"] = event_id
    attrs["detail_ref"] = f"OpsInvocationStarted:{event_id}"

    moment = from_zeitgeist_attrs("OpsInvocationStarted", attrs)
    canonical_event_id = event_id.lower()
    assert moment.attrs["event_id"] == canonical_event_id
    assert moment.attrs["detail_ref"] == f"OpsInvocationStarted:{canonical_event_id}"
