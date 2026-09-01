"""Conformance tests for the HarnessObservation payload family.

Renata HANDBACK_PACKET_REPAIR finding #2 (MEDIUM): the negatives inline in
``tests/unit/test_harness_observation.py`` were real coverage but not
reachable through the package's established fixture-plant architecture
(``conformance/fixtures/<category>/{valid,invalid}/*.json`` + ``manifest.json``
+ ``load_fixtures()``) that every other event family uses. This module wires
the ``harness_observation`` category (already registered in
``conformance/loader.py``'s ``_VALID_CATEGORIES`` since the category's
introduction) into that same loader-driven pattern, mirroring
``tests/test_profile_invocation_conformance.py``.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from spec_kitty_events.conformance.loader import load_fixtures
from spec_kitty_events.harness_observation import HarnessObservationPayload


@pytest.fixture
def harness_observation_fixtures():
    return load_fixtures("harness_observation")


def test_fixtures_loaded(harness_observation_fixtures) -> None:
    """6 valid + 5 invalid fixtures are on disk and manifest-registered."""
    assert len(harness_observation_fixtures) == 11
    valid = [f for f in harness_observation_fixtures if f.expected_valid]
    invalid = [f for f in harness_observation_fixtures if not f.expected_valid]
    assert len(valid) == 6
    assert len(invalid) == 5


@pytest.mark.parametrize(
    "fixture",
    load_fixtures("harness_observation"),
    ids=lambda f: f.id,
)
def test_harness_observation_conformance(fixture) -> None:
    """Validate each fixture payload against HarnessObservationPayload."""
    if fixture.expected_valid:
        payload = HarnessObservationPayload(**fixture.payload)
        assert payload.kind is not None  # sanity check
    else:
        with pytest.raises(ValidationError):
            HarnessObservationPayload(**fixture.payload)
