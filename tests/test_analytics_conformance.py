"""Conformance tests for analytics event contracts."""
from __future__ import annotations

import pytest

from spec_kitty_events.analytics import (
    DiffSummaryRecordedPayload,
    TokenUsageRecordedPayload,
)
from spec_kitty_events.conformance import load_fixtures, validate_event

_ANALYTICS_CASES = load_fixtures("analytics")
_VALID_CASES = [c for c in _ANALYTICS_CASES if c.expected_valid]
_INVALID_CASES = [c for c in _ANALYTICS_CASES if not c.expected_valid]


@pytest.mark.parametrize("case", _VALID_CASES, ids=[c.id for c in _VALID_CASES])
def test_valid_analytics_fixture_passes_conformance(case: object) -> None:
    from spec_kitty_events.conformance.loader import FixtureCase

    assert isinstance(case, FixtureCase)
    result = validate_event(case.payload, case.event_type, strict=True)
    assert result.valid, (
        f"Fixture {case.id} should be valid but got violations:\n"
        f"Model: {result.model_violations}\n"
        f"Schema: {result.schema_violations}"
    )


@pytest.mark.parametrize("case", _INVALID_CASES, ids=[c.id for c in _INVALID_CASES])
def test_invalid_analytics_fixture_fails_conformance(case: object) -> None:
    from spec_kitty_events.conformance.loader import FixtureCase

    assert isinstance(case, FixtureCase)
    result = validate_event(case.payload, case.event_type, strict=True)
    assert not result.valid, (
        f"Fixture {case.id} should be invalid but passed validation"
    )
    assert len(result.model_violations) >= 1, (
        f"Fixture {case.id} is invalid but no model_violations were reported"
    )


def test_analytics_fixture_count() -> None:
    assert len(_ANALYTICS_CASES) == 4


@pytest.mark.parametrize(
    "model_class,schema_name",
    [
        (TokenUsageRecordedPayload, "token_usage_recorded_payload"),
        (DiffSummaryRecordedPayload, "diff_summary_recorded_payload"),
    ],
    ids=["token_usage_recorded", "diff_summary_recorded"],
)
def test_analytics_schema_drift(model_class: type, schema_name: str) -> None:
    from spec_kitty_events.schemas import load_schema
    from spec_kitty_events.schemas.generate import generate_schema

    generated = generate_schema(schema_name, model_class)
    committed = load_schema(schema_name)
    assert generated == committed
