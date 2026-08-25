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

import pytest

from spec_kitty_events.conformance.loader import FixtureCase, load_fixtures
from spec_kitty_events.zeitgeist_attrs import (
    PAYLOAD_MODEL_BY_EVENT_TYPE,
    UnknownVolatileEventTypeError,
    VolatileMoment,
    ZeitgeistAttrsError,
    from_zeitgeist_attrs,
    to_zeitgeist_attrs,
    zeitgeist_ref_for,
)

_ERROR_CLASSES = {
    "UnknownVolatileEventTypeError": UnknownVolatileEventTypeError,
    "ZeitgeistAttrsError": ZeitgeistAttrsError,
    "ZeitgeistAttrsOverflowError": importlib.import_module(
        "spec_kitty_events.zeitgeist_attrs"
    ).ZeitgeistAttrsOverflowError,
}


@pytest.fixture
def zeitgeist_attrs_fixtures():
    return load_fixtures("zeitgeist_attrs")


def test_fixtures_loaded(zeitgeist_attrs_fixtures) -> None:
    """13 valid + 4 invalid fixtures are on disk and manifest-registered."""
    assert len(zeitgeist_attrs_fixtures) == 17
    assert len([f for f in zeitgeist_attrs_fixtures if f.expected_valid]) == 13
    assert len([f for f in zeitgeist_attrs_fixtures if not f.expected_valid]) == 4


def test_every_valid_fixture_covers_one_volatile_event_type(
    zeitgeist_attrs_fixtures,
) -> None:
    valid_types = {
        f.event_type for f in zeitgeist_attrs_fixtures if f.expected_valid
    }
    assert valid_types == set(PAYLOAD_MODEL_BY_EVENT_TYPE)


@pytest.mark.parametrize(
    "fixture",
    [f for f in load_fixtures("zeitgeist_attrs") if f.expected_valid],
    ids=lambda f: f.id,
)
def test_zeitgeist_attrs_both_directions(fixture: FixtureCase) -> None:
    """Golden attrs pin the projection; the decode validates them back."""
    case = fixture.payload
    model = PAYLOAD_MODEL_BY_EVENT_TYPE[fixture.event_type]
    payload = model(**case["payload"])

    # to-direction: bounded projection matches the committed bytes exactly.
    attrs = to_zeitgeist_attrs(payload)
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
        model = PAYLOAD_MODEL_BY_EVENT_TYPE[fixture.event_type]
        payload = model(**case["payload"])
        with pytest.raises(expected_error):
            to_zeitgeist_attrs(payload)
    else:
        assert case["direction"] == "from"
        with pytest.raises(expected_error):
            from_zeitgeist_attrs(fixture.event_type, case["attrs"])
