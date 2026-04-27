"""Conformance tests for retrospective event contracts."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from spec_kitty_events.conformance.loader import load_fixtures
from spec_kitty_events.retrospective import (
    RetrospectiveCompletedPayload,
    RetrospectiveFailedPayload,
    RetrospectiveLifecycleCompletedPayload,
    RetrospectiveLifecycleSkippedPayload,
    RetrospectiveProposalAppliedPayload,
    RetrospectiveProposalGeneratedPayload,
    RetrospectiveProposalRejectedPayload,
    RetrospectiveRequestedPayload,
    RetrospectiveSkippedPayload,
    RetrospectiveStartedPayload,
)

_EVENT_TYPE_TO_MODEL = {
    "RetrospectiveCompleted": RetrospectiveCompletedPayload,
    "RetrospectiveSkipped": RetrospectiveSkippedPayload,
    "retrospective.requested": RetrospectiveRequestedPayload,
    "retrospective.started": RetrospectiveStartedPayload,
    "retrospective.completed": RetrospectiveLifecycleCompletedPayload,
    "retrospective.skipped": RetrospectiveLifecycleSkippedPayload,
    "retrospective.failed": RetrospectiveFailedPayload,
    "retrospective.proposal.generated": RetrospectiveProposalGeneratedPayload,
    "retrospective.proposal.applied": RetrospectiveProposalAppliedPayload,
    "retrospective.proposal.rejected": RetrospectiveProposalRejectedPayload,
}


@pytest.fixture
def retrospective_fixtures():
    return load_fixtures("retrospective")


def test_fixtures_loaded(retrospective_fixtures):
    """At least 5 fixtures should be loaded (3 valid, 2 invalid)."""
    assert len(retrospective_fixtures) >= 5


@pytest.mark.parametrize(
    "fixture",
    load_fixtures("retrospective"),
    ids=lambda f: f.id,
)
def test_retrospective_conformance(fixture):
    """Validate each fixture against the appropriate payload model."""
    model_class = _EVENT_TYPE_TO_MODEL[fixture.event_type]
    if fixture.expected_valid:
        payload = model_class(**fixture.payload)
        assert payload.model_dump()  # sanity check
    else:
        with pytest.raises(ValidationError):
            model_class(**fixture.payload)
