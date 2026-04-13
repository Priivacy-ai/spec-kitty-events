"""Conformance tests for profile invocation event contracts."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from spec_kitty_events.conformance.loader import load_fixtures
from spec_kitty_events.profile_invocation import ProfileInvocationStartedPayload


@pytest.fixture
def profile_invocation_fixtures():
    return load_fixtures("profile_invocation")


def test_fixtures_loaded(profile_invocation_fixtures):
    """At least 4 fixtures should be loaded (2 valid, 2 invalid)."""
    assert len(profile_invocation_fixtures) >= 4


@pytest.mark.parametrize(
    "fixture",
    load_fixtures("profile_invocation"),
    ids=lambda f: f.id,
)
def test_profile_invocation_conformance(fixture):
    """Validate each fixture against ProfileInvocationStartedPayload."""
    if fixture.expected_valid:
        payload = ProfileInvocationStartedPayload(**fixture.payload)
        assert payload.profile_slug  # sanity check
    else:
        with pytest.raises(ValidationError):
            ProfileInvocationStartedPayload(**fixture.payload)
